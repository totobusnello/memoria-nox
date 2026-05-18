# memoria-nox in Cursor (Tier A)

> Tier A: full official support, deep integration, maintained by core team.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T8.

## Connect (automated — P4)

```bash
nox-mem connect cursor
```

What this does:
- Merges `mcpServers.nox-mem` into `~/.cursor/mcp.json`
- Records log-tail shim path in manifest (feature-flagged off until Cursor log format is stable)
- Backs up existing config before any write

## Manual setup (works today)

Add to `~/.cursor/mcp.json`:

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

Restart Cursor. Open Settings → MCP to confirm `nox-mem` appears.

## Features (planned per P4 spec T8)

- [ ] `mcpServers.nox-mem` block injection
- [ ] Log-tail shim for passive capture via `~/.cursor/logs/` (feature-flagged until format frozen)
- [ ] Persona awareness via MCP context (shallow — no native hook API in Cursor)
- [ ] Drift-aware disconnect

## Limitations vs Claude Code

Cursor has no native hook API. Passive capture relies on tailing `~/.cursor/logs/` (log-tail shim, T8). Until that ships, ingest manually:

```bash
nox-mem ingest ~/projects/my-project --since 1d
```

## Configuration

Same env vars as Claude Code. Key:

| Variable | Default | Notes |
|---|---|---|
| `NOX_DB_PATH` | `./nox-mem.db` | Point to your actual store |
| `GEMINI_API_KEY` | required | Required for semantic search |

## Troubleshooting

**`nox-mem` not listed in Cursor MCP settings**
- Confirm `~/.cursor/mcp.json` is valid JSON
- Run `npx nox-mem mcp` in terminal to check for startup errors

**Config path varies by platform**
- macOS: `~/.cursor/mcp.json`
- Linux: `~/.cursor/mcp.json` (same)
- Windows: out of scope for v1 (macOS/Linux only per P4 spec §13)

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T8
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
- CLI recipes: [`../cli/recipes.md`](../cli/recipes.md)
