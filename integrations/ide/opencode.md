# memoria-nox in OpenCode (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10.

## Connect (automated — P4)

```bash
nox-mem connect opencode
```

## Manual setup (works today)

Config: `~/.config/opencode/config.json` (XDG base dir)

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

- [x] MCP server accessible from OpenCode agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **XDG path resolution.** `nox-mem connect opencode` resolves `$XDG_CONFIG_HOME` with fallback to `~/.config/`. On macOS this is always `~/.config/opencode/config.json`.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
