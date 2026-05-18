---
title: Architecture Overview
description: Schema V10, hybrid search stack, and all interface surfaces.
sidebar:
  order: 1
---

## System at a glance

memoria-nox is a single-file SQLite memory engine with three query surfaces (CLI, MCP, HTTP) and a three-layer hybrid search pipeline.

```
INGEST SOURCES
──────────────
Markdown files ──┐
Entity files  ──┤── routeIngest() ──► SQLite (nox-mem.db)
Graphify AST  ──┘    (ingest-router.ts)
CLI / MCP     ──────────────────────►

QUERY SURFACES                     SEARCH ENGINE
──────────────                     ─────────────
CLI (26+ cmds) ──────────────────► FTS5 BM25
MCP (16 tools) ──────────────────► Gemini semantic (3072d)
HTTP API :18802 ─────────────────► RRF fusion (k=60)
```

## Database schema (V10)

| Table | Purpose |
|---|---|
| `chunks` | Canonical text chunks with metadata |
| `chunks_fts` | FTS5 virtual table for BM25 keyword search |
| `vec_chunks` | sqlite-vec 3072-dimensional embeddings |
| `vec_chunk_map` | Maps vec row IDs back to chunk IDs |
| `kg_entities` | Knowledge graph entities (~15,646) |
| `kg_relations` | KG relations via FK IDs (~21,533) |
| `ops_audit` | Append-only operation audit log |
| `search_telemetry` | Query logs (opt-in via `NOX_SEARCH_LOG_TEXT=1`) |

### Schema evolution

- **v8** — `retention_days` typed retention (feedback/person = NULL never-decay, lesson 180d, decision/project 365d)
- **v9** — `pain` REAL DEFAULT 0.2 — severity scale 0.1 (trivial) → 1.0 (prod-outage)
- **v10** — `section` TEXT + `section_boost` REAL — entity file format (compiled/frontmatter/timeline)
- **v11** — `search_telemetry` with 4 telemetry columns
- **v19–v22** — confidence, provenance, viewer events, conflict audit (in `staged-migrations/`)

## Hybrid search pipeline

```
[Query text]
     │
     ├─► FTS5 BM25 (keyword)
     │        │ top-N candidates
     │        ▼
     └─► Gemini embedding → vec search (semantic)
              │ top-N candidates
              ▼
         RRF fusion (k=60)
              │
         + section boost (compiled ×2.0, frontmatter ×1.5, timeline ×0.8)
         + salience score (recency × pain × importance) [shadow mode]
              ▼
         ranked results
```

## Interfaces

### CLI — 26+ subcommands

Entry point is `dist/index.js` (not `cli.js` — common confusion).

Key commands: `search`, `answer`, `ingest`, `ingest-entity`, `reindex`, `vectorize`, `kg-build`, `kg-prune`, `cross-search`, `reflect`, `crystallize`, `stats`, `serve`, `mcp`

```bash
nox-mem --help        # full command list
nox-mem search "..."  # hybrid search
nox-mem answer "..."  # grounded answer with citations
nox-mem stats         # corpus stats
```

### MCP server — 16 tools

`nox_mem_search`, `nox_mem_answer`, `stats`, `kg_build`, `cross_search`, `reflect`, `crystallize`, and 9 more. See [MCP Integration](/memoria-nox/integrations/mcp).

### HTTP API — port 18802

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Corpus stats, vector coverage, salience, opsAudit |
| `/api/search` | POST | Hybrid search |
| `/api/answer` | POST | Grounded answer |
| `/api/kg` | GET | KG entity list |
| `/api/kg/path` | GET | KG path query |
| `/api/cross-kg` | GET | Cross-agent KG search |
| `/api/reflect` | POST | Memory reflection |
| `/api/crystallize` | POST | Crystallize memories |
| `/api/crystallize/validate` | POST | Preview crystallization |

Full spec: [openapi/openapi.yaml](https://github.com/totobusnello/memoria-nox/blob/main/docs/openapi/openapi.yaml)

## Operational cadence

```
nightly 23:00 BRT:  reindex → consolidate → vectorize → kg-build → kg-prune → session-distill
*/30min:            semantic canary smoke test → Discord alert on failure
*/15min:            5 schema invariants check → Discord alert on violation
*/5min:             /api/health probe
```

## Safety model

Every destructive operation (`reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune`) is gated by `withOpAudit()` which:
1. Creates an atomic snapshot in `/var/backups/nox-mem/pre-op/` (7-day retention, ACL 0600)
2. Records to `ops_audit` (append-only — DELETE and UPDATE of terminal rows are blocked by DB triggers)
3. Supports `--dry-run` mode (JSON preview, no mutation)

See [Operations → Disaster Recovery](/memoria-nox/operations/disaster-recovery) for recovery procedures.
