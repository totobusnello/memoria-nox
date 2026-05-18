# MCP setup — Claude Desktop

Connect nox-mem to Claude Desktop (macOS / Windows).

## Prerequisites

```bash
npm install -g nox-mem
nox-mem init ~/my-memory   # if you haven't already
```

## Configuration

Edit Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "npx",
      "args": ["-y", "nox-mem", "mcp"],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY",
        "NOX_DB_PATH": "/Users/yourname/.nox-mem/nox-mem.db",
        "NOX_API_PORT": "18802"
      }
    }
  }
}
```

> Note: Claude Desktop env block does not expand `${HOME}` — use the absolute path directly.

## Restart and verify

1. Fully quit Claude Desktop (not just close the window)
2. Reopen Claude Desktop
3. Click the MCP icon (plug icon) in the message input bar
4. Confirm `nox-mem` appears with a green status

## Test it

In a Claude Desktop conversation:

```
Search my memory for "shadow discipline"
```

Claude should call `nox_mem_search` and return results from your store.

## Troubleshooting

**"nox-mem: failed to start"**
- Open Terminal and run `npx nox-mem mcp` — check for error output
- Confirm `GEMINI_API_KEY` is a valid key (not `${GEMINI_API_KEY}` — Claude Desktop does not expand shell vars)
- Check `NOX_DB_PATH` is an absolute path and the file exists

**Tools appear but return empty results**
- Confirm `nox-mem serve` is running (separate process for HTTP API)
- Run `curl http://127.0.0.1:18802/api/health` to verify the API is up

**"Not logged in" or API key errors**
- Claude Desktop MCP env variables are isolated from your shell env — you must hardcode the API key in the config (or use a wrapper script that sources your `.env`)

## Wrapper script approach (safer)

If you prefer not to put the key in the config file:

`~/.local/bin/nox-mem-mcp.sh`:
```bash
#!/bin/bash
set -a
source "$HOME/.openclaw/.env"
set +a
exec npx nox-mem mcp
```

```bash
chmod +x ~/.local/bin/nox-mem-mcp.sh
```

Then in the config:
```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "/Users/yourname/.local/bin/nox-mem-mcp.sh"
    }
  }
}
```

## Cross-refs

- Tools reference: [`tools-reference.md`](tools-reference.md)
- Compatible clients: [`compatible-clients.md`](compatible-clients.md)
- CONFIGURATION.md: `docs/CONFIGURATION.md`
