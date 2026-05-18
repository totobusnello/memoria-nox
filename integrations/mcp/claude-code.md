# MCP setup — Claude Code CLI

Connect nox-mem to Claude Code (the `claude` CLI, formerly Claude Code).

## Prerequisites

```bash
npm install -g nox-mem
nox-mem init ~/my-memory   # if you haven't already
```

## Option A — Automated (P4, when available)

```bash
nox-mem connect claude-code
```

This merges the MCP block into `~/.claude/settings.json` with backup-first safety, and optionally adds P2 hooks.

## Option B — Manual config today

Edit `~/.claude/settings.json`:

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

Claude Code expands `${GEMINI_API_KEY}` and `${HOME}` from your shell environment.

## Verify

```bash
# Start a new Claude Code session
claude

# Inside the session, check MCP tools
/mcp
```

`nox-mem` should appear with all tools listed. If it shows as disconnected, run:

```bash
npx nox-mem mcp   # check for startup errors
```

## Project-level MCP (scope: project)

To register nox-mem only for a specific project, add to `.claude/settings.json` in the project root:

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "npx",
      "args": ["-y", "nox-mem", "mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "NOX_DB_PATH": "./.nox-mem/nox-mem.db",
        "NOX_API_PORT": "18802"
      }
    }
  }
}
```

With P4: `nox-mem connect claude-code --scope project`

## P2 hooks (auto-capture — when P2 merges)

P2 adds hooks to Claude Code that automatically ingest files you read/edit during a session, with five privacy layers (PII redaction, gitignore-respect, size limits, extension blocklist, A1 privacy filter).

Once P2 merges, `nox-mem connect claude-code` will add the hooks block automatically. For now, capture manually:

```bash
# After a session, ingest files changed in the last 4 hours
nox-mem ingest . --since 4h
```

## Troubleshooting

**Tools show but search returns nothing**
- Ensure `nox-mem serve` is running for the HTTP API: `curl http://127.0.0.1:18802/api/health`
- Check `NOX_DB_PATH` resolves correctly: `ls $(echo $NOX_DB_PATH)`

**`permissions.allow` array warnings**
- Claude Code is sensitive to unknown keys in `settings.json`. The nox-mem MCP block only adds to `mcpServers` — it does not touch `permissions.allow`.

## Cross-refs

- IDE deep integration: [`../ide/claude-code.md`](../ide/claude-code.md)
- Tools reference: [`tools-reference.md`](tools-reference.md)
- P2 spec (hooks): `specs/2026-05-17-P2-hooks-autocapture.md`
