# Sklik MCP

[![PyPI version](https://badge.fury.io/py/sklik-mcp.svg)](https://pypi.org/project/sklik-mcp/)
[![CI](https://github.com/rawbark/seznam-ads-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rawbark/seznam-ads-mcp/actions)
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
git clone https://github.com/rawbark/seznam-ads-mcp
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
        "SKLIK_API_TOKEN": "your-token-here"
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
| `SKLIK_API_TOKEN` | — (required) | Your Sklik API token |
| `SKLIK_ENDPOINT` | `https://api.sklik.cz/drak/json/v5` | Drak JSON endpoint |
| `SKLIK_FENIX_ENDPOINT` | `https://api.sklik.cz/fenix/v1` | Fénix REST endpoint |
| `SKLIK_REQUEST_TIMEOUT_S` | `30` | HTTP timeout |
| `SKLIK_LOG_LEVEL` | `INFO` | Python log level |

## Tools

See [docs/tools.md](docs/tools.md) for the full tool catalogue.

## Development

```bash
git clone https://github.com/rawbark/seznam-ads-mcp
cd seznam-ads-mcp
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## Status

**Alpha (v0.1.0)** — first integration smoke against live Sklik API on **2026-04-30**.

What's verified working: login, account selection, listing campaigns / ad groups / ads / keywords, account-level stats overview, retargeting lists, listing conversions.

What's known broken or missing in v0.1.0:
- **Per-entity stats** (campaigns/groups/ads/keywords) — Sklik uses an async report-query model we haven't implemented. Tracked for v0.2.
- **Negative keywords** — guessed method names returned 404. Real ones TBD. Tracked for v0.1.1.
- **Fénix (Seznam Nákupy)** — uses OAuth2 token exchange, not direct Bearer. Tracked for v0.1.2.

See [docs/tools.md](docs/tools.md) for the full per-tool verification matrix.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built for the Czech PPC community. Inspired by [Pipeboard's Meta Ads MCP](https://github.com/pipeboard-co/meta-ads-mcp). Thanks to the Sklik team for the API.
