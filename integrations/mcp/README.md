# MCP Server — Installation Guide

nox-mem ships a Model Context Protocol server exposing 16+ tools over JSON-RPC 2.0 (stdio transport). Any MCP-compatible client can call these tools to search memory, build the knowledge graph, get grounded answers, and manage the archive.

---

## Quick install (Claude Code)

```bash
# 1. Install nox-mem globally
npm install -g nox-mem

# 2. Start the API server (keep it running — MCP and HTTP share the same DB)
nox-mem serve

# 3. Register in ~/.claude/settings.json
nox-mem connect claude-code

# 4. Verify in Claude Code: /mcp
```

---

## Start the MCP server manually

```bash
# stdio (used by IDE agents — this is what the IDE spawns)
nox-mem mcp

# Verify it starts cleanly (should print JSON-RPC ready to stdout)
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | nox-mem mcp
```

---

## Environment variables required

| Variable | Default | Required | Notes |
|---|---|---|---|
| `GEMINI_API_KEY` | — | yes (default provider) | BYO — never proxied |
| `NOX_DB_PATH` | `./nox-mem.db` | no | Point to your actual store |
| `NOX_API_PORT` | `18802` | no | Must match the HTTP API port |
| `NOX_EMBED_PROVIDER` | `gemini` | no | `gemini`, `openai`, or `local` |
| `NOX_SALIENCE_MODE` | `shadow` | no | `active` requires 7d baseline |
| `NOX_MCP_ALLOW_WRITES` | `0` | no | Set to `1` to enable write ops (KG conflict resolve, etc.) |

Load all env vars before starting:

```bash
set -a; source ~/.openclaw/.env; set +a
nox-mem mcp
```

---

## MCP server config block (generic)

Use this pattern for any MCP-compatible client not covered by a dedicated guide:

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

---

## Available tools (summary)

| Tool | Category | Status |
|---|---|---|
| `nox_mem_search` | Search | Operational — P3 temporal filters added |
| `nox_mem_answer` | Answer | Operational — P1, p95=101.74ms |
| `nox_mem_stats` | Observability | Operational |
| `nox_mem_ingest` | Ingest | Operational |
| `kg_build` | Knowledge graph | Operational |
| `cross_search` | Cross-agent | Operational |
| `reflect` | Caching | Operational |
| `crystallize` | Consolidation | Operational |
| `kg_query` | Knowledge graph | Operational |
| `kg_path` | Knowledge graph | Operational |
| `procedures` | Runbooks | Operational |
| `health` | Observability | Operational |
| `archive_export` | Archive (A2) | Operational |
| `archive_import` | Archive (A2) | Operational |
| `chunk_mark` | Confidence (L3) | Staged (pending deploy) |
| `chunk_supersede` | Confidence (L3) | Staged (pending deploy) |
| `kg_conflicts_list` | Lab (L2) | Specced, pending impl |
| `kg_conflicts_resolve` | Lab (L2) | Specced, pending impl |
| `kg_conflicts_dismiss` | Lab (L2) | Specced, pending impl |

Full documentation with schemas and examples: [`tools-reference.md`](tools-reference.md).

---

## Guides by client

- [Claude Desktop](claude-desktop.md)
- [Claude Code CLI](claude-code.md)
- [All MCP-compatible clients](compatible-clients.md)
