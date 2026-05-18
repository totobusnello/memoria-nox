# memoria-nox in Aider (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing. CLI-based integration recommended.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11.

## Connect (automated — P4)

```bash
nox-mem connect aider
```

## Manual setup (works today)

Config: `~/.aider.conf.yml`

```yaml
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

- [x] MCP server accessible from Aider
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Recommended integration approach

Aider excels at file-level code changes. Pair with nox-mem:

```bash
# Before an Aider session: pull relevant context
nox-mem search "authentication implementation patterns" --limit 5

# After a session: ingest changed files
git diff --name-only HEAD | xargs nox-mem ingest
```

## Quirks

- **Top-level list.** The `mcp:` key is a top-level YAML list, not nested. The P4 YAML merger appends to this list correctly.
- **Comment preservation.** Existing YAML comments in `.aider.conf.yml` survive the merge via `keepCstNodes` mode.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T11
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
- CLI recipes: [`../cli/recipes.md`](../cli/recipes.md)
