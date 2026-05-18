# memoria-nox in Roo Code (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10.

## Connect (automated — P4)

```bash
nox-mem connect roo
```

## Manual setup (works today)

Config: `~/.config/roo/settings.json`

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
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Roo Code agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **Fork of Cline shape.** Roo Code uses the same `mcpServers` JSON shape as Cline (including `disabled` and `autoApprove` fields). The P4 T10 batch shares a `_shared/json-mcp-servers.ts` helper for both.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
