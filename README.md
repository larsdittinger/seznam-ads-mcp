# Sklik MCP

[![PyPI version](https://badge.fury.io/py/sklik-mcp.svg)](https://pypi.org/project/sklik-mcp/)
[![CI](https://github.com/larsdittinger/seznam-ads-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/larsdittinger/seznam-ads-mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **MCP server pro Seznam Sklik.** Spravujte kampaně, sestavy, klíčová slova a výkon přes Claude (nebo jakéhokoliv MCP klienta).
>
> **MCP server for Seznam Sklik advertising.** Manage campaigns, ad groups, keywords, and performance from Claude (or any MCP client) in natural language.

## Co to umí / What it does

- **Kampaně** — list, create, update, pause, resume, remove
- **Sestavy + inzeráty + klíčová slova** — full CRUD
- **Vylučující slova** — campaign + group scope
- **Statistiky** — flexible reporting (hourly/daily/weekly/monthly)
- **Retargeting + konverze**
- **Seznam Nákupy (Fénix)** — product groups + shopping stats
- **Multi-account** — switch between client accounts (převtělení)

## Quick start

### 1. Get a Sklik API token

In Sklik web admin: **Nastavení → API token**. You must be logged in as the account owner (not impersonated). For production access, email **sklik@firma.seznam.cz** to enable API.

### 2. Install

```bash
# With uv (recommended)
uvx sklik-mcp

# Or globally
uv tool install sklik-mcp

# From source
git clone https://github.com/larsdittinger/seznam-ads-mcp
cd seznam-ads-mcp
uv sync
uv run sklik-mcp
```

### 3. Configure your MCP client

#### Claude Desktop / Claude Code

Add to your config (`~/.config/Claude/claude_desktop_config.json` on Linux, similar on macOS/Windows):

```json
{
  "mcpServers": {
    "sklik": {
      "command": "uvx",
      "args": ["sklik-mcp"],
      "env": {
        "SKLIK_API_TOKEN": "your-drak-token-here",
        "SKLIK_FENIX_TOKEN": "your-v1-refresh-token-here"
      }
    }
  }
}
```

#### Cursor / other MCP clients

See the client's docs — it's a standard stdio MCP server invoked as `sklik-mcp` with `SKLIK_API_TOKEN` in the environment.

## Příklady / Examples

Once installed, ask Claude:

- *"Ukaž mi všechny aktivní kampaně se spendem za posledních 7 dní"*
- *"Najdi sestavy s CTR pod 1 % a spendem nad 1000 Kč"*
- *"Pozastav kampaň ID 12345"*
- *"Přidej vylučující slova `zdarma`, `levně` do kampaně 12345"*
- *"Porovnej výkon kampaní k1 a k2 za duben po týdnech"*

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `SKLIK_API_TOKEN` | — (required) | Drak JSON-RPC API token (campaigns, ads, keywords, …) |
| `SKLIK_FENIX_TOKEN` | — (optional) | Refresh JWT for the unified `/v1/` API (Sklik Nákupy / Fénix). When unset, the Fénix tools are not registered. |
| `SKLIK_ENDPOINT` | `https://api.sklik.cz/drak/json/v5` | Drak JSON endpoint |
| `SKLIK_FENIX_ENDPOINT` | `https://api.sklik.cz/v1` | Sklik /v1 endpoint |
| `SKLIK_REQUEST_TIMEOUT_S` | `30` | HTTP timeout |
| `SKLIK_LOG_LEVEL` | `INFO` | Python log level |

**Drak token:** Sklik web admin → Nastavení → API token (must be the account owner, not impersonated).

**Fénix refresh token:** Log in to https://www.sklik.cz/, generate a refresh token from the API section. The MCP exchanges it for a short-lived access token automatically and re-exchanges before expiry.

## Tools

See [docs/tools.md](docs/tools.md) for the full tool catalogue.

## Development

```bash
git clone https://github.com/larsdittinger/seznam-ads-mcp
cd seznam-ads-mcp
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## Status

**Alpha (v0.1.0)** — verified end-to-end against the live Sklik API on **2026-05-01**.

End-to-end test on a real account: created a fulltext campaign with ad
group, text ad, three keywords, and a retargeting list; paused/resumed
each; set negative keywords; removed everything; account ended where it
started.

Verified working (full CRUD round-trips):
- Accounts — `current_account`, `list_managed_accounts`, `switch_account`
- Campaigns / ad groups / text ads / keywords — list, get, create, update, pause, resume, remove
- Negative keywords — set-whole-list at the campaign level (the v5 API does not expose them any other way)
- Retargeting lists — list, create, update, remove
- Account-level stats overview (`get_account_overview`) and `list_conversions`

Known limitations in v0.1.0:
- **Per-entity stats** (campaigns/groups/ads/keywords) and **`get_conversion_stats`** — Sklik exposes these via an async report-query model (`<entity>.createReport` → poll → `<entity>.readReport`) that we haven't implemented yet. Tracked for v0.2.
- **`create_dynamic_ad`** — wire shape not fully confirmed; treat as experimental. Tracked for v0.1.x.
- **Fénix (Seznam Nákupy)** — wired against the unified `/v1/` API with proper OAuth2 refresh→access token exchange and the real `/nakupy/` endpoints (per the published OpenAPI spec). Live end-to-end smoke against a fresh refresh token is still pending.

See [docs/tools.md](docs/tools.md) for the full per-tool verification matrix.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built for the Czech PPC community. Inspired by [Pipeboard's Meta Ads MCP](https://github.com/pipeboard-co/meta-ads-mcp). Thanks to the Sklik team for the API.
