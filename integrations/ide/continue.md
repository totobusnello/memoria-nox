# memoria-nox in Continue (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T12.

## Connect (automated — P4)

```bash
nox-mem connect continue
```

## Manual setup (works today)

Config: `~/.continue/config.json`

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "npx",
          "args": ["-y", "nox-mem", "mcp"],
          "env": {
            "GEMINI_API_KEY": "${GEMINI_API_KEY}",
            "NOX_DB_PATH": "${HOME}/.nox-mem/nox-mem.db",
            "NOX_API_PORT": "18802"
          }
        }
      }
    ]
  }
}
```

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Continue agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **`experimental.modelContextProtocolServers` key may rename.** Continue v0.10+ is likely to move this to a stable top-level key. The P4 `continue.ts` merger emits a warn-banner on `connect` and `nox-mem connect --list` flags `schemaDriftWarning: true` for this IDE. Follow the Continue changelog.
- When Continue renames the key, run `nox-mem disconnect continue && nox-mem connect continue` to re-merge to the new path.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T12
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
