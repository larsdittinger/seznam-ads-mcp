# Sklik MCP — Design Document

**Date:** 2026-04-30
**Status:** Approved (sections 1-4)
**Authors:** Claude + user

## Goal

Build an open-source MCP (Model Context Protocol) server that lets Claude (and other MCP-compatible clients) manage Seznam Sklik advertising accounts via natural language. The server exposes Sklik's Drak (XML-RPC/JSON) and Fénix (REST) APIs as MCP tools, enabling end-to-end campaign management — read, write, create, and analyze.

## Non-Goals

- Web UI / dashboard (this is a tool server, not a frontend)
- Hosted / remote HTTP transport in MVP (future epic)
- AI-driven optimization heuristics (delegated to the LLM client)
- Other Seznam ads surfaces (Sklik only)

## Audience & Use Cases

- Czech PPC agencies managing many Sklik accounts (e.g. Ethia)
- In-house marketers running Sklik alongside Meta/Google Ads
- Czech open-source community (no comparable MCP exists today)

Primary use cases:
1. **Q1/quarterly audit** — "find campaigns spending without conversions in the last 30 days"
2. **Cross-platform comparison** — "compare ROAS Sklik vs Meta last 30d weekly" (paired with another MCP)
3. **Routine ops** — pause underperformers, add negative keywords, build reports
4. **Campaign creation** — bootstrap new campaigns from a brief

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Scope | Full (read + write + create) | User will use it for full management |
| API coverage | Drak + Fénix | E-shop clients need shopping ads |
| Multi-account | Yes, via impersonation (`userId`) | Agencies manage many accounts |
| Distribution | Local stdio MCP only | MVP simplicity; remote later |
| Language | Python 3.11+ | FastMCP, good asyncio, modern type hints |
| Package mgmt | `uv` | Fast, modern, deterministic |
| MCP framework | FastMCP (`mcp` SDK) | Standard, decorator-based |
| Sklik client | Custom (NOT `seznam/sklik-api-python-client`) | The official client is Python 2 and unmaintained; building a thin client over JSON API with `requests` is simpler and modern |
| License | MIT | Standard for community projects |
| Repo public | GitHub (yes) | Open-source, with landing-page README |

## Architecture

### Project layout

```
seznam-ads-mcp/
├── pyproject.toml              # uv metadata, entry point: sklik-mcp = sklik_mcp.server:main
├── README.md                   # GitHub landing page (CZ + EN, install & usage)
├── LICENSE                     # MIT
├── .env.example                # SKLIK_API_TOKEN=...
├── .gitignore
├── .github/workflows/ci.yml    # ruff + mypy + pytest on PRs
├── docs/
│   ├── installation.md         # Claude Desktop, Claude Code, Cursor configs
│   ├── tools.md                # Auto-generated tool catalogue
│   └── superpowers/specs/      # Design docs (this file lives here)
├── src/sklik_mcp/
│   ├── __init__.py             # __version__
│   ├── server.py               # FastMCP instance + tool registration + main()
│   ├── core/
│   │   ├── __init__.py
│   │   ├── client.py           # SklikClient: JSON-RPC over HTTPS, session mgmt, retry
│   │   ├── config.py           # Pydantic settings, env loading
│   │   ├── session.py          # SessionState: holds session token + active impersonation user_id
│   │   ├── errors.py           # Sklik error → MCP error mapping with Czech-friendly messages
│   │   └── formatting.py       # Money (Kč), date, percent helpers
│   └── tools/
│       ├── __init__.py
│       ├── accounts.py         # list_managed_accounts, switch_account, current_account
│       ├── campaigns.py        # list/get/create/update/pause/resume/remove
│       ├── ad_groups.py        # CRUD for ad groups
│       ├── ads.py              # CRUD for text/banner/dynamic ads
│       ├── keywords.py         # CRUD + match types + bidding
│       ├── negative_keywords.py
│       ├── stats.py            # get_stats with flexible group-by/filter/granularity
│       ├── retargeting.py      # retargeting lists + audiences
│       ├── conversions.py      # conversion definitions
│       └── fenix/
│           ├── __init__.py
│           ├── client.py       # REST client (requests-based)
│           ├── product_groups.py
│           └── shopping_stats.py
└── tests/
    ├── conftest.py
    ├── unit/                   # mocked HTTP layer
    │   ├── test_client.py
    │   ├── test_session.py
    │   ├── test_errors.py
    │   └── tools/
    │       └── test_*.py
    └── integration/            # real API, gated by SKLIK_API_TOKEN_TEST env var
        └── test_smoke.py
```

### Layering

```
┌─────────────────────────────────────────┐
│ FastMCP server (server.py)              │  ← MCP protocol, transport
├─────────────────────────────────────────┤
│ tools/* (thin wrappers)                 │  ← arg validation, calls core, formats output
├─────────────────────────────────────────┤
│ core/client.py + core/session.py        │  ← HTTP + session management
├─────────────────────────────────────────┤
│ requests / Sklik JSON API (api.sklik.cz)│
└─────────────────────────────────────────┘
```

**Rule:** `core/` knows nothing about MCP. `tools/` is the only layer importing from FastMCP. This keeps core unit-testable without an MCP test harness.

## Sklik API integration

### Endpoint

JSON API: `POST https://api.sklik.cz/drak/json/v5/<method.name>`

The API is XML-RPC over HTTP with a JSON encoding. Each method call is a POST to a URL ending in the method name (e.g. `/campaigns.list`), with a JSON array body containing the positional parameters.

### Authentication

```
POST /client.loginByToken
Body: [{"token": "<API_TOKEN>"}]

Response: {"status": 200, "session": "<session-string>", ...}
```

The session string is then prepended to every subsequent call as the first parameter:

```
POST /campaigns.list
Body: [{"session": "<session>", "userId": <impersonated_user_id_or_omit>}, {<filter>}, {<options>}]
```

### Status codes

- `200` OK
- `206` Warning (partial success — surface as warning to LLM)
- `400` Argument error
- `401` Session error → re-login + retry once
- `403` Access denied
- `404` Not found
- `406` Invalid data
- `409` No-action (e.g. pausing already-paused campaign)

### Multi-account / impersonation

A single API token belongs to one user. That user may have access to additional Sklik accounts (managed by them as "převtělení"). The flow:

1. After login, call `client.get` to list user info
2. Call `users.list` (or similar — confirm method name during implementation) to enumerate accounts the user can impersonate
3. Tool `switch_account(user_id)` sets `SessionState.active_user_id`
4. All subsequent calls include `userId` in the first-param struct

The default state has no impersonation (uses the token owner's own account).

## Core components

### `core/client.py` — `SklikClient`

```python
class SklikClient:
    def __init__(self, token: str, endpoint: str = DRAK_JSON_V5):
        self.token = token
        self.endpoint = endpoint
        self.session: SessionState = SessionState()
        self._http = requests.Session()

    def login(self) -> None:
        """POST /client.loginByToken, store session string."""

    def call(self, method: str, *params: dict) -> dict:
        """
        Make a JSON call. Auto-prepends auth struct (session + optional userId).
        On 401 SessionError: re-login once, retry. On other errors: raise.
        """

    def set_active_account(self, user_id: int | None) -> None:
        """Set impersonation target."""
```

Key behaviors:
- Lazy login on first `call()`
- Single retry on 401
- Map all non-2xx Sklik statuses to typed exceptions (see errors.py)
- Returns `dict` (the Sklik response body, with `status` removed since it's already validated)

### `core/session.py` — `SessionState`

```python
@dataclass
class SessionState:
    session_token: str | None = None
    active_user_id: int | None = None
    token_owner_user_id: int | None = None  # set after login
```

Pure data class. Mutated by `SklikClient`. No I/O.

### `core/errors.py`

```python
class SklikError(Exception): ...
class ArgumentError(SklikError): ...
class SessionError(SklikError): ...      # 401
class AccessError(SklikError): ...       # 403
class NotFoundError(SklikError): ...     # 404
class InvalidDataError(SklikError): ...  # 406
class NoActionWarning(Warning): ...      # 409
```

Tools catch these and convert to MCP-friendly messages with Czech context (e.g. "Nemáte oprávnění k tomuto účtu — zkontrolujte, že vlastník účtu API token autorizoval.").

### `core/config.py`

Pydantic settings model loaded from `.env`:

```python
class Settings(BaseSettings):
    sklik_api_token: str
    sklik_endpoint: str = "https://api.sklik.cz/drak/json/v5"
    fenix_endpoint: str = "https://api.sklik.cz/fenix/v1"  # confirm during impl
    log_level: str = "INFO"
    request_timeout_s: int = 30
```

## Tool catalogue (initial inventory)

Tools are organized by domain. Each tool docstring is the description the LLM sees — written in English with Czech terminology hints in parentheses (e.g. "Get statistics (statistiky/přehled výkonu)").

### accounts.py
- `list_managed_accounts()` — list accounts the API token can impersonate (převtělení)
- `switch_account(user_id: int)` — set active impersonation target
- `current_account()` — show currently active account

### campaigns.py
- `list_campaigns(status_filter, name_contains, limit)` — list kampaní
- `get_campaign(campaign_id)`
- `create_campaign(name, daily_budget, ...)`
- `update_campaign(campaign_id, **fields)`
- `pause_campaign(campaign_id)`
- `resume_campaign(campaign_id)`
- `remove_campaign(campaign_id)` — soft delete

### ad_groups.py
- `list_ad_groups(campaign_id?)`
- `get_ad_group(group_id)`
- `create_ad_group(...)`, `update_ad_group(...)`, `pause/resume/remove`

### ads.py
- `list_ads(group_id?)`
- `get_ad(ad_id)`
- `create_text_ad(...)`, `create_dynamic_ad(...)`
- `update_ad(...)`, `pause/resume/remove`

### keywords.py
- `list_keywords(group_id?, status?)`
- `add_keywords(group_id, keywords: list[KeywordInput])` — batch
- `update_keyword(keyword_id, max_cpc?, status?)`
- `pause/resume/remove`

### negative_keywords.py
- `list_negative_keywords(scope: campaign|group, id)`
- `add_negative_keywords(scope, id, keywords)`
- `remove_negative_keyword(neg_id)`

### stats.py
- `get_stats(entity, entity_id, date_from, date_to, granularity, group_by?)` — the most-used tool, must be flexible
- `get_account_overview(date_from, date_to)` — pre-built rollup for "how's the account doing"

### retargeting.py
- `list_retargeting_lists()`
- `create_retargeting_list(...)`, `update`, `remove`

### conversions.py
- `list_conversions()`
- `get_conversion_stats(conversion_id, date_from, date_to)`

### fenix/product_groups.py
- `list_product_groups(campaign_id)`
- `update_product_group_bid(...)`

### fenix/shopping_stats.py
- `get_shopping_stats(date_from, date_to, group_by)`

Total: ~35 tools across 9 modules. Each tool file ≤300 lines.

## Error handling

- `SklikClient` raises typed exceptions
- Tool wrapper catches them, returns MCP error response with Czech-language hint where the error is user-actionable
- Unexpected errors logged to stderr (NEVER stdout — corrupts JSON-RPC) and re-raised as generic MCP error

## Testing strategy

### Unit tests (`tests/unit/`)
- Mock `requests.Session.post` at the boundary
- Test `SklikClient.call`: auth struct injection, 401 retry, error mapping
- Test each tool: arg validation, correct method name, correct params shape, output formatting

### Integration tests (`tests/integration/`)
- Gated by `SKLIK_API_TOKEN_TEST` env var (skip if absent)
- Smoke test: login → list_campaigns → get_stats → logout
- Run only locally + manually triggered CI workflow (not on every PR)

### CI
- GitHub Actions: ruff (format + lint), mypy (strict), pytest (unit only)
- Matrix: Python 3.11, 3.12, 3.13

## Distribution

### Installation methods (in README)

1. **uvx (recommended):** `uvx sklik-mcp` (when published to PyPI)
2. **From GitHub:** `uv tool install git+https://github.com/<user>/seznam-ads-mcp`
3. **Local dev:** `git clone && uv sync && uv run sklik-mcp`

### Claude Desktop config example

```json
{
  "mcpServers": {
    "sklik": {
      "command": "uvx",
      "args": ["sklik-mcp"],
      "env": {
        "SKLIK_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

### README structure (landing page)

1. Hero: badge row (PyPI, license, CI), tagline in CZ + EN
2. What is this? — 3 sentences
3. Quick start — install + Claude Desktop config snippet
4. Capabilities — bulleted list with examples ("Show me underperforming campaigns last week")
5. Configuration — env vars table
6. Tool reference — link to docs/tools.md
7. Development — uv setup, tests, contribution
8. License + acknowledgements

## Localization

Tool names: English (LLM convention). Tool descriptions: English with Czech terminology in parentheses where it differs significantly. Error messages and user-facing strings: Czech (target audience is CZ).

Examples:
- Tool name: `pause_campaign`
- Description: "Pause a campaign (pozastavit kampaň). The campaign will stop spending immediately."
- Error: "Kampaň ID 12345 neexistuje nebo k ní nemáte přístup."

## Open questions (resolve during implementation)

1. Exact Fénix REST endpoint and auth — needs API explorer session
2. Sklik rate limits — not documented; back off on 429 if observed
3. Some methods are paid (per Sklik changelog) — surface this in tool descriptions where known

## Out of scope (future)

- Remote HTTP MCP deployed on Hetzner (separate epic)
- OAuth flow for end users
- Multi-tenant config for hosted version
- AI-driven recommendations (delegated to LLM client)

## Acceptance criteria for MVP

- [ ] All ~35 tools implemented and registered with FastMCP
- [ ] Unit test coverage ≥80% on `core/` and ≥60% on `tools/`
- [ ] CI green on Python 3.11/3.12/3.13
- [ ] README renders well on GitHub with install + usage
- [ ] Manual smoke test passes against a real Sklik sandbox or production account
- [ ] `uvx --from . sklik-mcp` runs and registers tools in Claude Desktop
