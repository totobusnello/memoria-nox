---
title: MCP Server
description: 16 MCP tools for Claude Code, Cursor, Cline, and any MCP-compatible runtime.
sidebar:
  order: 2
---

Full source: [`integrations/mcp/`](https://github.com/totobusnello/memoria-nox/tree/main/integrations/mcp)

## Setup

Add to your MCP configuration file:

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "nox-mem",
      "args": ["mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key-here",
        "NOX_DB_PATH": "/path/to/your/nox-mem.db"
      }
    }
  }
}
```

**Claude Code** (`~/.claude/mcp.json`), **Cursor** (`.cursor/mcp.json`), **Cline** (settings → MCP servers) all use this format.

## 16 available tools

| Tool | Description |
|---|---|
| `nox_mem_search` | Hybrid search (FTS5 + semantic + RRF) |
| `nox_mem_answer` | Grounded answer with citations |
| `nox_mem_ingest` | Ingest content into memory |
| `nox_mem_ingest_entity` | Ingest structured entity file |
| `stats` | Corpus statistics |
| `kg_build` | Build / update knowledge graph |
| `kg_search` | Search knowledge graph entities |
| `kg_path` | Find path between two entities |
| `cross_search` | Search across multiple memory stores |
| `reflect` | Memory reflection and consolidation |
| `crystallize` | Crystallize raw memories into structured knowledge |
| `crystallize_validate` | Preview crystallization without committing |
| `health` | Full health check |
| `reindex` | Trigger reindex (with dry-run support) |
| `vectorize` | Trigger vectorization of unembedded chunks |
| `procedures` | List available procedures |

## Usage example (in Claude Code)

Once the MCP server is configured, use tools directly in conversation:

```
Use nox_mem_search to find everything about the salience formula
```

```
Use nox_mem_answer to answer: what is the pain field used for?
```

```
Use stats to check corpus coverage
```

## Tool schema (nox_mem_search)

```json
{
  "name": "nox_mem_search",
  "description": "Hybrid search over the memory corpus using FTS5 BM25 + Gemini embeddings + RRF fusion.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query" },
      "limit": { "type": "number", "default": 10 },
      "noHybrid": { "type": "boolean", "default": false }
    },
    "required": ["query"]
  }
}
```
