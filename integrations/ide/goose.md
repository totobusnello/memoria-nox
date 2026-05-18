# memoria-nox in Goose (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11.

## Connect (automated — P4)

```bash
nox-mem connect goose
```

## Manual setup (works today)

Config: `~/.config/goose/config.yaml`

```yaml
extensions:
  mcp:
    - name: nox-mem
      command: npx
      args:
        - -y
        - nox-mem
        - mcp
      env:
        GEMINI_API_KEY: ${GEMINI_API_KEY}
        NOX_DB_PATH: ${HOME}/.nox-mem/nox-mem.db
        NOX_API_PORT: "18802"
```

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Goose agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **Nested under `extensions`.** The MCP block lives at `extensions.mcp[]`, not at the top level. The P4 YAML merger handles this path correctly.
- **Comment preservation.** YAML comments in `config.yaml` survive the merge via `keepCstNodes` mode.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
