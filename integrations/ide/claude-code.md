# memoria-nox in Claude Code (Tier A)

> Tier A: full official support, deep integration, maintained by core team.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T7.

## Connect (automated — P4)

```bash
nox-mem connect claude-code
```

What this does:
- Merges `mcpServers.nox-mem` block into `~/.claude/settings.json`
- Adds P2 hooks block (`PreToolUse` / `PostToolUse` / `Notification`) when P2 is merged
- Adds persona routing key (default: all agents; override with `--agent atlas`)
- Backs up existing config before any write

## Manual setup (works today)

Add to `~/.claude/settings.json`:

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

Then restart Claude Code. Run `/mcp` to confirm `nox-mem` appears in the list.

## Features (planned per P4 spec T7)

- [ ] `mcpServers.nox-mem` block injection
- [ ] P2 hooks block (PreToolUse/PostToolUse/Notification) — degrades to "Tier A-shallow" until P2 merges
- [ ] Persona routing key (`--agent atlas|boris|cipher|forge|lex`)
- [ ] `nox-mem connect --scope project` writes to `./.claude/settings.json` (project-local)
- [ ] `nox-mem connect --re-link-hooks` re-applies hooks block after P2 merges
- [ ] Cross-agent leases (L3) — feature-flagged, enabled when L3 ready

## Configuration

Environment variables used by the MCP server:

| Variable | Default | Notes |
|---|---|---|
| `NOX_DB_PATH` | `./nox-mem.db` | Path to SQLite store |
| `NOX_API_PORT` | `18802` | HTTP API port (Chrome squats 18800) |
| `GEMINI_API_KEY` | required | Embedding provider key |
| `NOX_SALIENCE_MODE` | `shadow` | `shadow` or `active` (needs 7d baseline) |
| `NOX_EMBED_PROVIDER` | `gemini` | `gemini`, `openai`, or `local` |

## Available MCP tools

All 16+ tools are available. Key tools for Claude Code workflows:

- `nox_mem_search` — hybrid search (FTS5 + semantic + RRF). Supports `as_of` and `changed_since` temporal filters.
- `nox_mem_answer` — grounded answer with citations, anti-hallucination guard
- `kg_build` — extract entities + relations from recent chunks
- `reflect` — check reflect cache before asking Gemini
- `cross_search` — search across multiple agent DBs

Full reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md).

## Troubleshooting

**`nox-mem` not listed in `/mcp`**
- Check `~/.claude/settings.json` for `mcpServers.nox-mem`
- Verify `npx nox-mem mcp` runs without error in terminal
- Confirm `GEMINI_API_KEY` is set in the env block (not just shell env)

**Tools return empty results**
- Run `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — `embedded` should equal `total`
- Check `NOX_DB_PATH` points to your actual database

**P2 hooks not firing**
- P2 (Claude Code hooks auto-capture) is a separate sprint. Until merged: MCP-only mode, manual `nox-mem ingest <file>` for capture.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md`
- P2 spec (hooks): `specs/2026-05-17-P2-hooks-autocapture.md`
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
- MCP setup guide: [`../mcp/claude-code.md`](../mcp/claude-code.md)
- CONFIGURATION.md: `docs/CONFIGURATION.md`
