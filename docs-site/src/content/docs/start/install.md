---
title: Installation
description: Install memoria-nox CLI, MCP server, and HTTP API in one command.
sidebar:
  order: 1
---

## Requirements

- **Node.js 20+** (ships with SQLite via `better-sqlite3`, no system SQLite required)
- **npm** or **pnpm**
- An embedding provider key — Gemini default; OpenAI and local models supported

## Install

```bash
npm install -g nox-mem
```

Verify:

```bash
nox-mem --version
nox-mem --help
```

## Set your embedding provider

```bash
# Gemini (default, recommended)
export GEMINI_API_KEY=your-key-here

# OpenAI alternative
export OPENAI_API_KEY=your-key-here
export NOX_EMBEDDING_PROVIDER=openai

# Local (Ollama)
export NOX_EMBEDDING_PROVIDER=local
export NOX_EMBEDDING_BASE_URL=http://localhost:11434
```

## Initialize a memory store

```bash
nox-mem init ~/my-memory
```

This creates `~/my-memory/nox-mem.db` — a single SQLite file that holds all chunks, vectors, and knowledge graph relations.

## Start the HTTP API

```bash
nox-mem serve
# Listening on http://127.0.0.1:18802
```

## Start the MCP server

Add to your Claude / Cursor / Cline MCP config:

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "nox-mem",
      "args": ["mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

16 tools are exposed: `nox_mem_search`, `nox_mem_answer`, `kg_build`, `cross_search`, `reflect`, and more. See [MCP Integration](/memoria-nox/integrations/mcp) for the full reference.

## Next step

→ [First Query](/memoria-nox/start/first-query)
