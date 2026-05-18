# memoria-nox in Gemini CLI (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11.

## Connect (automated — P4)

```bash
nox-mem connect gemini-cli
```

## Manual setup (works today)

Config: `~/.gemini/config.yaml`

```yaml
mcp:
  servers:
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

- [x] MCP server accessible from Gemini CLI agent
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **Comment preservation.** The P4 `connect` merger uses the `yaml` lib in `keepCstNodes` mode so existing YAML comments survive the merge byte-identical.
- Gemini CLI and nox-mem both use Gemini APIs. Your `GEMINI_API_KEY` is shared. Budget accordingly.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
