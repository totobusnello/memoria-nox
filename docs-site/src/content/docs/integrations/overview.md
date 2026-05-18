---
title: Integrations Overview
description: Connect memoria-nox to your editor, agent runtime, or CI pipeline.
sidebar:
  order: 1
---

Full source: [`integrations/`](https://github.com/totobusnello/memoria-nox/tree/main/integrations)

## Integration surfaces

| Surface | Description | Status |
|---|---|---|
| **MCP server** | 16 tools for any MCP-compatible agent runtime | Live |
| **CLI** | 26+ subcommands for scripting and automation | Live |
| **HTTP API** | REST + OpenAPI 3.1 spec | Live |
| **IDE plugins** | Native plugins for 14 editors | Stub / spec |
| **Mobile** | iOS / Android capture | Specced (P6) |
| **Browser extension** | Capture from web | Specced (P7) |

## Quick start by use case

### I'm using Claude Code / Claude Desktop

Add the MCP server to your config. See [MCP Integration](/memoria-nox/integrations/mcp).

### I'm using VS Code / Cursor / Cline

Use the MCP integration — all these editors support MCP. See [MCP Integration](/memoria-nox/integrations/mcp).

For native IDE plugins (autocomplete, sidebar), see [IDE Plugins](/memoria-nox/integrations/ide).

### I'm scripting / automating

Use the CLI. See [CLI Recipes](/memoria-nox/integrations/cli).

### I'm building an app

Use one of the [SDKs](/memoria-nox/sdks/overview) or call the [HTTP API](/memoria-nox/api/openapi-spec) directly.
