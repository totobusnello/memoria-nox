# IDE Integrations

nox-mem integrates with 13 IDEs across two tiers. The `nox-mem connect <ide>` command (P4 sprint, spec: `specs/2026-05-18-P4-implementation-kickoff.md`) automates the config merge for all of them.

---

## Tier definitions

### Tier A — Deep integration (3 IDEs)

Full official support. Maintained by the core team.

- MCP server registered in IDE config
- P2 hooks for zero-manual-ingest auto-capture (when P2 merges)
- Persona routing (Atlas/Boris/Cipher/Forge/Lex) for multi-agent setups
- Drift-aware disconnect: `nox-mem disconnect <ide>` preserves your user edits

| IDE | Config path (macOS) | MCP block key | Hooks |
|---|---|---|---|
| **Claude Code** | `~/.claude/settings.json` | `mcpServers` | yes (P2: PreToolUse/PostToolUse/Notification) |
| **Cursor** | `~/.cursor/mcp.json` | `mcpServers` | no native hook API |
| **Codex** | `~/.codex/config.toml` | `[mcp_servers.nox-mem]` | partial (CLI events) |

### Tier B — MCP passive (10 IDEs)

MCP block injection + disconnect only. No hooks, no persona routing. Community-maintained or limited official support.

| IDE | Config path (macOS) | MCP block key | Format |
|---|---|---|---|
| **Cline** | `~/.vscode/extensions/cline*/settings.json` | `mcpServers` | JSON |
| **Gemini CLI** | `~/.gemini/config.yaml` | `mcp.servers[]` | YAML |
| **OpenCode** | `~/.config/opencode/config.json` | `mcpServers` | JSON |
| **Goose** | `~/.config/goose/config.yaml` | `extensions.mcp` | YAML |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` | JSON |
| **Continue** | `~/.continue/config.json` | `experimental.modelContextProtocolServers` | JSON |
| **Aider** | `~/.aider.conf.yml` | `mcp:` | YAML |
| **Roo Code** | `~/.config/roo/settings.json` | `mcpServers` | JSON |
| **Zed** | `~/.config/zed/settings.json` | `context_servers` | JSONC |
| **JetBrains AI** | `~/Library/Application Support/JetBrains/<IDE><ver>/options/` sidecar | `mcpClients` | JSON sidecar |

> Note: Vim, Emacs, Sublime Text, NeoVim, and Helix are out-of-scope for v1 per `specs/2026-05-17-P4-connect-ide.md` §17. Recommended approach for those editors: use `nox-mem search --json` from a shell command or hotkey binding.

---

## How `nox-mem connect` works (P4)

1. Detects IDE config path (auto-detects all 13 IDEs)
2. Backs up config to `<config>.nox-mem-backup-<ts>.json` — **backup failure aborts the merge**
3. Deep-merges the nox-mem MCP block — existing `mcpServers.<other>` entries survive untouched
4. Writes manifest entry to `~/.nox-mem/connections.json` (schemaHash + configHash + backupPath)
5. On `disconnect`: detects user edits since connect (drift detection), prompts `[k]eep / [r]estore / [d]iff / [a]bort`

```bash
# List detected IDEs on this machine
nox-mem connect --list

# Preview what would be written (no changes)
nox-mem connect cursor --dry-run

# Connect
nox-mem connect cursor

# Disconnect (preserves your edits by default)
nox-mem disconnect cursor
```

**Status:** P4 implementation pending (est. 28–32h). Spec: `specs/2026-05-18-P4-implementation-kickoff.md`.

---

## IDE files

- [Claude Code](claude-code.md) — Tier A
- [Cursor](cursor.md) — Tier A
- [Codex](codex.md) — Tier A
- [Cline](cline.md) — Tier B
- [Gemini CLI](gemini-cli.md) — Tier B
- [OpenCode](opencode.md) — Tier B
- [Goose](goose.md) — Tier B
- [Windsurf](windsurf.md) — Tier B
- [Continue](continue.md) — Tier B
- [Aider](aider.md) — Tier B
- [Roo Code](roo-code.md) — Tier B
- [Zed](zed.md) — Tier B
- [JetBrains AI](jetbrains-ai.md) — Tier B
