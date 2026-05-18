# memoria-nox in JetBrains AI (Tier B)

> Tier B: MCP block injection only. No hooks, no persona routing.

## Status

P4 implementation pending. Spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T13.

## Connect (automated — P4)

```bash
nox-mem connect jetbrains-ai
```

`connect` auto-detects all installed JetBrains products with the AI plugin via plugin directory scan (IDEA, WebStorm, GoLand, PyCharm, and others).

## Manual setup (works today)

JetBrains AI plugin config is split across an XML file and a JSON sidecar.

**CRITICAL: Never touch the XML file.** Only edit the JSON sidecar. The P4 T13 merger enforces this contractually (unit test asserts XML mtime unchanged after connect/disconnect).

JSON sidecar location (macOS, example for IntelliJ IDEA 2024.1):
`~/Library/Application Support/JetBrains/IntelliJIdea2024.1/options/mcpServers.json`

```json
{
  "mcpClients": {
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

- [x] MCP server accessible from JetBrains AI plugin
- [ ] Hooks / auto-capture — not available
- [ ] Persona routing — not available

## Quirks

- **XML + JSON hybrid config.** JetBrains AI uses `aiAssistant.xml` (main config, never touch) plus a `mcpServers.json` sidecar (safe to edit). The P4 T13 merger only writes to the JSON sidecar.
- **Path varies by IDE and version.** Replace `IntelliJIdea2024.1` with your actual product+version directory. `nox-mem connect jetbrains-ai` scans for all installed products automatically.
- **Snap sandboxing on Linux.** Similar to Zed Flatpak: if JetBrains IDE is installed via Snap, it may not reach `127.0.0.1`. The sandbox probe (`src/lib/connect/sandbox-probe.ts`) detects `/snap` and suggests the LAN IP fix.
- **`mcpClients` key** (not `mcpServers`). JetBrains AI uses its own key name in the sidecar.

## Cross-refs

- P4 spec: `specs/2026-05-18-P4-implementation-kickoff.md` task T13
- Sandbox probe: `src/lib/connect/sandbox-probe.ts` (T14)
- MCP tools reference: [`../mcp/tools-reference.md`](../mcp/tools-reference.md)
