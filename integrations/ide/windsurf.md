# memoria-nox in Windsurf (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10.

## Connect (automated — P4)

```bash
nox-mem connect windsurf
```

## Manual setup (works today)

Config: `~/.codeium/windsurf/mcp_config.json`

> Note: the path is `.codeium`, not `.windsurf` — this is correct.

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

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Windsurf agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **Config path is `.codeium/windsurf/`**, not `.windsurf/`. The P4 `detect.ts` resolves this correctly. Do not confuse it with Codeium's other config paths.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
