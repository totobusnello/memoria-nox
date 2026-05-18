---
title: IDE Plugins
description: Native IDE integrations for 14 editors — autocomplete, search sidebar, and hover definitions.
sidebar:
  order: 3
---

Full source: [`integrations/ide/`](https://github.com/totobusnello/memoria-nox/tree/main/integrations/ide)

## Status

IDE plugins are currently in **stub / spec** stage (P4). The MCP integration works today in all editors listed below. Native plugins (autocomplete, sidebar UI) are specced and in active development.

## Supported editors

| Editor | MCP today | Native plugin |
|---|---|---|
| Claude Code | Yes | N/A (MCP native) |
| Cursor | Yes | Spec ready |
| Cline | Yes | Spec ready |
| Continue | Yes | Spec ready |
| Aider | Yes | CLI integration |
| VS Code | Yes (via Cline/Continue) | Extension spec ready |
| Neovim | Yes (via MCP bridge) | Lua plugin spec |
| Emacs | Yes (via MCP bridge) | elisp spec |
| JetBrains IDEs | Planned | Plugin spec |
| Zed | Yes (via MCP) | Extension spec |
| Windsurf | Yes | Spec ready |
| Amp | Yes | Spec ready |
| Goose | Yes | Spec ready |
| Copilot | Planned | — |

## MCP setup for editors

All editors with MCP support use the same config. See [MCP Integration](/memoria-nox/integrations/mcp) for the universal setup.

## Native plugin features (planned)

When native plugins ship (P4 Tier A), they will provide:

- **Autocomplete** — inline memory suggestions as você type
- **Search sidebar** — full hybrid search UI inside the editor
- **Hover definitions** — hover over an entity name to see KG context
- **Ingest shortcut** — select text and send directly to memory
- **Context injection** — automatically inject relevant memories into agent context

## VS Code extension (spec)

The VS Code extension will ship as `memoria-nox.vscode` on the marketplace.

Config in `.vscode/settings.json`:

```json
{
  "nox-mem.baseUrl": "http://127.0.0.1:18802",
  "nox-mem.autoIngest": true,
  "nox-mem.sidebarEnabled": true
}
```
