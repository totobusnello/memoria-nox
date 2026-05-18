# memoria-nox in Cline (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing. CLI-based capture recommended.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10.

## Connect (automated — P4)

```bash
nox-mem connect cline
```

## Manual setup (works today)

Cline config lives inside the VS Code extension directory (path varies by Cline version):

`~/.vscode/extensions/saoudrizwan.claude-dev-*/settings/cline_mcp_settings.json`

Add to the `mcpServers` object:

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

Reload VS Code window after editing. Check Cline's MCP panel to confirm `nox-mem` connected.

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Cline agent
- [ ] Hooks / auto-capture — not available (no native hook API)
- [ ] Persona routing — not available

## Recommended capture workflow

```bash
# After a coding session, ingest changed files
nox-mem ingest . --since 4h

# Or ingest a specific file
nox-mem ingest src/lib/search.ts
```

## Quirks

- **Extension dir varies by Cline version.** `nox-mem connect cline` auto-detects the version-stamped path via glob. If you have multiple Cline versions installed, it targets the most recently modified one.
- The `disabled: false` and `autoApprove: []` fields are Cline-specific — do not remove them.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T10
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
- CLI recipes: [`../cli/recipes.md`](../cli/recipes.md)
