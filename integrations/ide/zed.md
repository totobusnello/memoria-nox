# memoria-nox in Zed (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T13.

## Connect (automated — P4)

```bash
nox-mem connect zed
```

## Manual setup (works today)

Config: `~/.config/zed/settings.json` (JSONC — comments allowed)

```jsonc
{
  "context_servers": {
    "nox-mem": {
      "command": {
        "path": "npx",
        "args": ["-y", "nox-mem", "mcp"],
        "env": {
          "GEMINI_API_KEY": "${GEMINI_API_KEY}",
          "NOX_DB_PATH": "${HOME}/.nox-mem/nox-mem.db",
          "NOX_API_PORT": "18802"
        }
      }
    }
  }
}
```

## Features (Tier B — MCP passive)

- [x] MCP server accessible from Zed AI assistant
- [ ] Hooks / auto-capture — not available (possible via Flatpak extension host on Linux)
- [ ] Persona routing — not available

## Quirks

- **JSONC format.** Zed `settings.json` is JSONC (comments allowed). The P4 merger uses `jsonc-parser` edits API to preserve your existing comments byte-identical. Do not let other tools touch this file with a plain JSON formatter.
- **Flatpak sandboxing on Linux.** If Zed is installed via Flatpak, it cannot reach `127.0.0.1:18802` by default. `nox-mem connect zed` detects `/var/lib/flatpak` and suggests the fix:
  - Change `NOX_API_PORT` env to your LAN IP (e.g. `192.168.1.x:18802`)
  - Or grant filesystem access: `flatpak override --user --filesystem=host dev.zed.Zed`
- **`context_servers` key** (not `mcpServers`). Zed uses its own key name.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T13
- Flatpak sandbox probe: `src/lib/connect/sandbox-probe.ts` (T14)
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
