# memoria-nox in Codex (Tier A)

> Tier A: full official support, deep integration, maintained by core team.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T9.

## Connect (automated — P4)

```bash
nox-mem connect codex
```

What this does:
- Merges `[mcp_servers.nox-mem]` block into `~/.codex/config.toml`
- Attempts CLI-event integration (best-effort; warn-not-fail below minimum Codex CLI version)
- Backs up existing config before any write

## Manual setup (works today)

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.nox-mem]
command = "npx"
args = ["-y", "nox-mem", "mcp"]

[mcp_servers.nox-mem.env]
GEMINI_API_KEY = "${GEMINI_API_KEY}"
NOX_DB_PATH = "${HOME}/.nox-mem/nox-mem.db"
NOX_API_PORT = "18802"
```

## Features (planned per P4 spec T9)

- [ ] TOML `[mcp_servers.nox-mem]` block injection (via `toml.ts` merger, comment-preserving)
- [ ] CLI-event integration for passive capture (best-effort, min Codex version TBD at T9)
- [ ] Shallow persona awareness (MCP context only)
- [ ] Drift-aware disconnect

## Limitations vs Claude Code

Codex CLI event hooks are partial. The T9 implementation is best-effort: if the Codex CLI version is below the documented minimum, `connect` writes the MCP block and logs a warning — it does not fail. Check `nox-mem connect codex --dry-run` for the version check result.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `NOX_DB_PATH` | `./nox-mem.db` | Point to your actual store |
| `GEMINI_API_KEY` | required | Required for semantic search |

## Troubleshooting

**TOML format errors**
- `nox-mem connect codex --dry-run` prints a unified diff before writing
- The merger preserves TOML comments and indentation

**CLI event integration not working**
- Check `nox-mem connect --list` — `pendingCliEvents: true` means your Codex version is below the minimum
- Fall back to manual `nox-mem ingest` for now

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T9
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
