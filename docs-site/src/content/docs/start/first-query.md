---
title: First Query
description: Ingest your first documents and run a hybrid search.
sidebar:
  order: 2
---

## Ingest a directory

```bash
# Markdown files, entity files, and graphify output all handled automatically
nox-mem ingest ~/notes
```

The ingest router (`ingest-router.ts`) detects file type and routes to the correct handler:
- **Entity files** (`memory/entities/<type>/<slug>.md`) → `ingestEntityFile()` — produces N+2 chunks with section boosts (compiled ×2.0, frontmatter ×1.5, timeline ×0.8)
- **Plain markdown** → `ingestFile()`
- **Graphify AST** → graph-aware chunker

## Run a hybrid search

```bash
nox-mem search "what is the salience formula?"
```

The search pipeline runs three layers in sequence:

1. **FTS5 BM25** — keyword recall (fast, zero-cost)
2. **Gemini semantic** — embedding similarity (3072-dimensional)
3. **RRF fusion** — Reciprocal Rank Fusion with `k=60` merges both ranked lists

```
[Query]
   │
   ├─► FTS5 BM25 ──────────────────────────┐
   │                                       ├─► RRF (k=60) ─► ranked results
   └─► Gemini embedding → vec search ──────┘
```

## Get a grounded answer

```bash
nox-mem answer "how does pain affect ranking?"
```

The answer primitive (P1) retrieves relevant chunks, composes a cited response, and attaches source references so you can verify every claim.

## Check corpus stats

```bash
nox-mem stats
# chunks: 69,298
# embedded: 69,295 (99.99%)
# kg_entities: 15,646
# kg_relations: 21,533
```

Or via the HTTP API:

```bash
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

## Build the knowledge graph

```bash
nox-mem kg-build
```

Extracts entities and relations from chunks using Gemini 2.5 Flash. Runs nightly automatically; invoke manually after a large ingest.

## Next step

→ [Configuration](/memoria-nox/start/configuration)
