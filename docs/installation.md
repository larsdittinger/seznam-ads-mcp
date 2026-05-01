# Installation

## Prerequisites

- Python 3.11+ (3.12 recommended)
- A Sklik account with API access enabled (email sklik@firma.seznam.cz)
- Your API token from Sklik web admin → Nastavení → API token

## Install

### uvx (recommended for end users)

```bash
uvx sklik-mcp
```

This pulls the latest published version on demand. No persistent install needed.

### uv tool (persistent)

```bash
uv tool install sklik-mcp
sklik-mcp  # in PATH after install
```

### Pip

```bash
pip install sklik-mcp
sklik-mcp
```

### From source

```bash
git clone https://github.com/larsdittinger/seznam-ads-mcp
cd seznam-ads-mcp
uv sync
uv run sklik-mcp
```

## Client configuration

### Claude Desktop

Linux: `~/.config/Claude/claude_desktop_config.json`
macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sklik": {
      "command": "uvx",
      "args": ["sklik-mcp"],
      "env": { "SKLIK_API_TOKEN": "your-token" }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add sklik --command uvx --args sklik-mcp --env SKLIK_API_TOKEN=your-token
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sklik": {
      "command": "uvx",
      "args": ["sklik-mcp"],
      "env": { "SKLIK_API_TOKEN": "your-token" }
    }
  }
}
```

## Verify

After configuring, restart your MCP client. You should see `sklik-mcp` in the tool list. Try asking the model:

> *"Show me my active Sklik campaigns"*

If you see an authentication error, double-check the token. If you see "API not enabled", email sklik@firma.seznam.cz.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Sklik API token is required" | `SKLIK_API_TOKEN` env var not set or empty |
| 401 SessionError on every call | Token revoked or wrong account; regenerate in Sklik admin |
| 403 AccessError | Need to switch_account first, or token doesn't manage that account |
| Empty results | Check `current_account` — you may be impersonating a different account |
