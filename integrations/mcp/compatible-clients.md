# MCP-Compatible Clients

nox-mem's MCP server uses the standard JSON-RPC 2.0 stdio transport defined by the [Model Context Protocol](https://modelcontextprotocol.io) spec. Any client implementing MCP can use it.

## Tier A — deep integration (nox-mem maintained)

| Client | Setup guide | Notes |
|---|---|---|
| Claude Code (CLI) | [`claude-code.md`](claude-code.md) | P2 hooks support, persona routing, P4 `connect` command |
| Claude Desktop | [`claude-desktop.md`](claude-desktop.md) | macOS / Windows, env vars must be hardcoded |

## Tier B — MCP passive (via `nox-mem connect <ide>`)

All 10 Tier B IDEs listed in [`../ide/README.md`](../ide/README.md) work with the standard MCP stdio block. See individual IDE files for config path and format details.

## MCP-compatible clients (community)

The following clients support MCP and can use the nox-mem server with the standard config block. nox-mem does not maintain these integrations.

| Client | Config key | Format | Notes |
|---|---|---|---|
| **Cursor** | `mcpServers` | JSON | See [`../ide/cursor.md`](../ide/cursor.md) |
| **Cline** | `mcpServers` | JSON | See [`../ide/cline.md`](../ide/cline.md) |
| **Windsurf** | `mcpServers` | JSON | See [`../ide/windsurf.md`](../ide/windsurf.md) |
| **Continue** | `experimental.modelContextProtocolServers` | JSON | Key may rename; see [`../ide/continue.md`](../ide/continue.md) |
| **Roo Code** | `mcpServers` | JSON | See [`../ide/roo-code.md`](../ide/roo-code.md) |
| **Zed** | `context_servers` | JSONC | See [`../ide/zed.md`](../ide/zed.md) |
| **JetBrains AI** | `mcpClients` (sidecar) | JSON | See [`../ide/jetbrains-ai.md`](../ide/jetbrains-ai.md) |
| **Goose** | `extensions.mcp` | YAML | See [`../ide/goose.md`](../ide/goose.md) |
| **Aider** | `mcp:` | YAML | See [`../ide/aider.md`](../ide/aider.md) |
| **Gemini CLI** | `mcp.servers[]` | YAML | See [`../ide/gemini-cli.md`](../ide/gemini-cli.md) |
| **OpenCode** | `mcpServers` | JSON | See [`../ide/opencode.md`](../ide/opencode.md) |
| **Codex** | `[mcp_servers.nox-mem]` | TOML | See [`../ide/codex.md`](../ide/codex.md) |
| **LangChain** | custom | — | Use HTTP API (`/api/search`, `/api/answer`) directly |
| **LlamaIndex** | custom | — | Use HTTP API directly |
| **CrewAI** | custom | — | Use HTTP API directly |
| **AutoGen** | custom | — | Use HTTP API directly |

## HTTP API as alternative

For clients that do not support MCP, use the HTTP API directly:

```bash
# Search
curl -s "http://127.0.0.1:18802/api/search?q=shadow+discipline&limit=5" | jq .

# Answer
curl -s -X POST http://127.0.0.1:18802/api/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the salience formula?"}' | jq .

# KG query
curl -s "http://127.0.0.1:18802/api/kg?q=salience" | jq .
```

Full HTTP API reference: `docs/openapi/` or `GET /api/health` for live status.

## Generic MCP config block

Copy this into any client that supports `mcpServers`:

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "npx",
      "args": ["-y", "nox-mem", "mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "NOX_DB_PATH": "${HOME}/.nox-mem/nox-mem.db",
        "NOX_API_PORT": "18802"
      }
    }
  }
}
```

## Sandboxed clients (Flatpak / Snap)

If the client is sandboxed (Flatpak on Linux, Snap on Linux), it may not reach `127.0.0.1:18802`. Solutions:

1. Use the LAN IP of the nox-mem host instead of `127.0.0.1`
2. Grant filesystem access: `flatpak override --user --filesystem=host <app-id>`
3. Use the `nox-mem connect <ide>` command — it detects sandboxing automatically and suggests the fix

Affected IDEs: Zed (Flatpak), JetBrains (Snap). See individual IDE files.
