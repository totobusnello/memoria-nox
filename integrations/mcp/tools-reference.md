# MCP Tools Reference

Complete documentation for all tools exposed by the nox-mem MCP server.

**Transport:** JSON-RPC 2.0 over stdio  
**Server entry:** `nox-mem mcp`  
**Write-op gate:** `NOX_MCP_ALLOW_WRITES=1` required for `kg_conflicts_resolve`, `kg_conflicts_dismiss`, `chunk_mark`, `chunk_supersede`

---

## Table of contents

**Core retrieval**
- [nox_mem_search](#nox_mem_search)
- [nox_mem_answer](#nox_mem_answer)
- [reflect](#reflect)
- [cross_search](#cross_search)

**Ingest**
- [nox_mem_ingest](#nox_mem_ingest)

**Knowledge graph**
- [kg_build](#kg_build)
- [kg_query](#kg_query)
- [kg_path](#kg_path)

**Consolidation**
- [crystallize](#crystallize)

**Observability**
- [nox_mem_stats](#nox_mem_stats)
- [health](#health)
- [procedures](#procedures)

**Archive (A2)**
- [archive_export](#archive_export)
- [archive_import](#archive_import)

**Confidence marking (L3 — staged)**
- [chunk_mark](#chunk_mark)
- [chunk_supersede](#chunk_supersede)

**KG conflict detection (L2 — specced, pending impl)**
- [kg_conflicts_list](#kg_conflicts_list)
- [kg_conflicts_resolve](#kg_conflicts_resolve)
- [kg_conflicts_dismiss](#kg_conflicts_dismiss)

---

## nox_mem_search

Hybrid memory search: FTS5 BM25 + Gemini semantic (3072d) + RRF fusion (k=60). Language-aware weights: PT queries tilt dense up (×1.15), FTS down (×0.85).

**Input schema:**
```json
{
  "query": "string — natural language, keywords, or entity names (required)",
  "limit": "number — results to return, default 5, max 20",
  "as_of": "string — time-travel filter: ISO 8601 or relative ('7d', '1w', '2h', '15m')",
  "changed_since": "string — recency filter: ISO 8601 or relative ('7d', '1w', '2h', '15m')"
}
```

**Output schema:**
```json
[
  {
    "id": "number",
    "content": "string",
    "source_file": "string",
    "chunk_type": "string",
    "section": "string | null",
    "pain": "number (0.1–1.0)",
    "score": "number",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
]
```

**Example call:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "nox_mem_search",
    "arguments": {
      "query": "salience formula pain recency",
      "limit": 5,
      "as_of": "7d"
    }
  },
  "id": 1
}
```

**Example response:**
```json
{
  "content": [{
    "type": "text",
    "text": "[{\"id\":4821,\"content\":\"salience = recency × pain × importance...\",\"source_file\":\"memory/entities/decision/salience-v2.md\",\"chunk_type\":\"decision\",\"section\":\"compiled\",\"pain\":0.8,\"score\":0.94}]"
  }]
}
```

**Errors:**
- `as_of` or `changed_since` is not a valid ISO date or recognized relative shorthand → `isError: true`, `reason: "invalid_date"`

**Required env:** `GEMINI_API_KEY` (for semantic leg), `NOX_DB_PATH`

---

## nox_mem_answer

Grounded answer with citations from the nox-mem corpus. Anti-hallucination guard built-in: if cited markers `[chunk_N]` are not in the retrieval set, the answer is retried once. Returns structured JSON.

**Input schema:**
```json
{
  "question": "string — max 2000 chars (required)",
  "top_k": "integer — chunks to retrieve, default 8, max 20",
  "max_tokens": "integer — response token budget, default 1500, max 8192",
  "provider": "string — LLM provider override (e.g. 'openai')",
  "model": "string — model override (e.g. 'gpt-4o')",
  "temperature": "number — 0–1, default provider setting",
  "no_citations": "boolean — strip [chunk_N] markers from final answer, default false"
}
```

**Output schema (content[0].text, parsed JSON):**
```json
{
  "answer": "string — response text with [chunk_N] citations",
  "citations": [
    {
      "marker": "string — e.g. [chunk_1]",
      "chunk_id": "number",
      "content": "string — chunk text excerpt",
      "source_file": "string",
      "chunk_type": "string"
    }
  ],
  "metadata": {
    "latency_ms": "number",
    "tokens_in": "number",
    "tokens_out": "number",
    "provider": "string",
    "model": "string",
    "retrieval_count": "number",
    "fallback_used": "boolean"
  }
}
```

**Error response (isError: true):**
```json
{
  "error": true,
  "reason": "retrieval_empty | hallucination_after_retry | llm_error | invalid_input | internal_error",
  "message": "string",
  "metadata": {}
}
```

**Example call:**
```json
{
  "name": "nox_mem_answer",
  "arguments": {
    "question": "How does pain affect search ranking?",
    "top_k": 8
  }
}
```

**Required env:** `GEMINI_API_KEY` (default LLM + embedding), `NOX_DB_PATH`

**Benchmark:** p95 = 101.74ms total (mock LLM @ 100ms, PR #40).

---

## reflect

Check reflect cache before issuing a Gemini query. Returns a cached response if a semantically similar question (cosine ≥ 0.88) was answered recently. Exact hit: ~30× speedup. Semantic hit: ~4× speedup.

**Input schema:**
```json
{
  "query": "string (required)"
}
```

**Output schema:**
```json
{
  "hit": "boolean",
  "response": "string | null — cached answer if hit",
  "similarity": "number | null — cosine similarity if semantic hit"
}
```

**Required env:** `GEMINI_API_KEY`, `NOX_DB_PATH`

---

## cross_search

Search across multiple agent DBs simultaneously. Returns ranked results merged from all connected stores.

**Input schema:**
```json
{
  "query": "string (required)",
  "limit": "number — per-agent limit, default 5",
  "agents": "string[] — agent names to include (default: all registered)"
}
```

**Output schema:**
```json
[
  {
    "agent": "string",
    "id": "number",
    "content": "string",
    "source_file": "string",
    "score": "number"
  }
]
```

**Required env:** `NOX_DB_PATH` (base), agent DB paths registered in agent registry

---

## nox_mem_ingest

Ingest a file or directory into nox-mem. The ingest router auto-detects entity files (`compiled`/`frontmatter`/`timeline` sections) vs plain markdown.

**Input schema:**
```json
{
  "path": "string — file or directory path (required)",
  "since": "string — only ingest files modified after this relative time ('1h', '1d', '7d')",
  "dry_run": "boolean — preview what would be ingested, no writes"
}
```

**Output schema:**
```json
{
  "ingested": "number — chunks created",
  "skipped": "number",
  "errors": "string[]"
}
```

**Required env:** `GEMINI_API_KEY` (for vectorize), `NOX_DB_PATH`

---

## kg_build

Extract entities and relations from recent chunks using Gemini 2.5 Flash. Results land in `kg_entities` and `kg_relations`.

**Input schema:**
```json
{
  "since": "string — process chunks updated after this time ('1d', '7d', default: unprocessed)",
  "limit": "number — max chunks to process, default 100",
  "dry_run": "boolean"
}
```

**Output schema:**
```json
{
  "entities_created": "number",
  "relations_created": "number",
  "chunks_processed": "number"
}
```

**Required env:** `GEMINI_API_KEY`, `NOX_DB_PATH`

**Caution:** KG extraction uses `gemini-2.5-flash` (full, not lite) — higher quota than embeddings. Monitor quota if running at scale.

---

## kg_query

Query the knowledge graph. Returns entities matching a name or type filter.

**Input schema:**
```json
{
  "name": "string — entity name or partial match",
  "type": "string — entity type filter (e.g. 'person', 'decision', 'project')",
  "limit": "number — default 10"
}
```

**Output schema:**
```json
[
  {
    "id": "number",
    "canonical_name": "string",
    "type": "string",
    "description": "string",
    "confidence": "number",
    "relations": [
      {
        "predicate": "string",
        "target": "string",
        "relation_type": "string"
      }
    ]
  }
]
```

**Required env:** `NOX_DB_PATH`

---

## kg_path

Find the shortest path between two entities in the knowledge graph.

**Input schema:**
```json
{
  "from": "string — source entity name (required)",
  "to": "string — target entity name (required)",
  "max_hops": "number — default 4"
}
```

**Output schema:**
```json
{
  "path": [
    {
      "entity": "string",
      "predicate": "string | null"
    }
  ],
  "hops": "number",
  "found": "boolean"
}
```

**Required env:** `NOX_DB_PATH`

---

## crystallize

Consolidate low-salience chunks into a single high-salience summary chunk. Wrapped in `withOpAudit()` — creates a pre-op snapshot.

**Input schema:**
```json
{
  "topic": "string — consolidation topic / seed query (required)",
  "limit": "number — chunks to consider, default 20",
  "dry_run": "boolean — preview only, no writes"
}
```

**Output schema:**
```json
{
  "created_chunk_id": "number | null",
  "source_chunk_ids": "number[]",
  "dry_run_preview": "string | null"
}
```

**Required env:** `GEMINI_API_KEY`, `NOX_DB_PATH`

---

## nox_mem_stats

Return summary statistics for the current nox-mem store.

**Input schema:** `{}` (no input required)

**Output schema:**
```json
{
  "total_chunks": "number",
  "embedded_chunks": "number",
  "vector_coverage_pct": "number",
  "kg_entities": "number",
  "kg_relations": "number",
  "db_size_mb": "number",
  "schema_version": "number",
  "salience_mode": "shadow | active"
}
```

**Required env:** `NOX_DB_PATH`

---

## health

Return the full health payload from `/api/health`. Includes vector coverage, section distribution, salience mode, ops audit status, and schema version.

**Input schema:** `{}` (no input required)

**Output schema:** mirrors `GET /api/health` JSON response.

**Required env:** `NOX_DB_PATH`, `NOX_API_PORT`

---

## procedures

List available runbooks / procedures stored in nox-mem.

**Input schema:**
```json
{
  "filter": "string — optional keyword filter"
}
```

**Output schema:**
```json
[
  {
    "id": "number",
    "title": "string",
    "content": "string",
    "chunk_type": "string"
  }
]
```

**Required env:** `NOX_DB_PATH`

---

## archive_export

Export the nox-mem store to a portable archive (A2). AES-256-GCM encryption with scrypt key derivation. Round-trip preserves nDCG@10 ± 0.001.

**Input schema:**
```json
{
  "output_path": "string — destination .noxarchive path (required)",
  "passphrase_env": "string — env var name holding passphrase (never accept passphrase as direct arg)",
  "include_embeddings": "boolean — default true",
  "include_ops_audit": "boolean — default true",
  "dry_run": "boolean"
}
```

**Output schema:**
```json
{
  "output_path": "string",
  "chunks_exported": "number",
  "kg_entities_exported": "number",
  "kg_relations_exported": "number",
  "size_bytes": "number",
  "manifest_sha256": "string"
}
```

**Required env:** `NOX_DB_PATH`, passphrase env var if encrypting

**Security:** never pass passphrase as a direct argument (visible in `ps aux`). Always use `passphrase_env` pointing to an env var.

---

## archive_import

Import a previously exported archive into the current store (A2). Merge mode: existing chunks/entities skipped on hash collision.

**Input schema:**
```json
{
  "input_path": "string — source .noxarchive path (required)",
  "passphrase_env": "string — env var name if archive is encrypted",
  "on_conflict": "string — 'skip' (default) or 'error'",
  "dry_run": "boolean"
}
```

**Output schema:**
```json
{
  "chunks_imported": "number",
  "chunks_skipped": "number",
  "kg_entities_imported": "number",
  "kg_relations_imported": "number",
  "errors": "string[]"
}
```

**Required env:** `NOX_DB_PATH`, passphrase env var if archive is encrypted

---

## chunk_mark

Mark a chunk as `canonical` (Toto-affirmed), `refuted` (negated), or `stale` (no longer trustworthy). Updates `chunks.confidence` and `chunks.provenance_kind`. Appends an `ops_audit` row.

**Status:** L3 staged — pending deploy. Requires `NOX_MCP_ALLOW_WRITES=1`.

**Input schema:**
```json
{
  "id": "number — chunk id to mark (required)",
  "kind": "string — 'canonical' | 'refuted' | 'stale' (required)",
  "notes": "string — optional note logged to ops_audit.details"
}
```

**Output schema:**
```json
{
  "chunk_id": "number",
  "kind": "string",
  "confidence_before": "number",
  "confidence_after": "number",
  "ops_audit_id": "number"
}
```

**Confidence values:**
- `canonical` → `1.0`
- `refuted` → `0.05`
- `stale` → unchanged confidence, `provenance_kind = 'user-marked'`

**Required env:** `NOX_DB_PATH`, `NOX_MCP_ALLOW_WRITES=1`

---

## chunk_supersede

Mark a chunk as superseded by a newer chunk. Sets `chunks.superseded_by` FK. The older chunk remains in the DB for audit; ranking de-prioritizes it when `NOX_RANKING_CONFIDENCE=active`.

**Status:** L3 staged — pending deploy. Requires `NOX_MCP_ALLOW_WRITES=1`.

**Input schema:**
```json
{
  "id": "number — older chunk id being replaced (required)",
  "by_id": "number — newer chunk id replacing it (required)",
  "notes": "string — optional context",
  "reason": "string — 'auto_supersede_temporal' | 'manual_resolution' | 'stale_link_reconciliation' | 'dismiss'"
}
```

**Output schema:**
```json
{
  "chunk_id": "number",
  "superseded_by": "number",
  "ops_audit_id": "number"
}
```

**Required env:** `NOX_DB_PATH`, `NOX_MCP_ALLOW_WRITES=1`

---

## kg_conflicts_list

List unresolved KG conflicts (opposing relations on the same subject+predicate).

**Status:** L2 specced, implementation pending. Spec: `specs/2026-05-17-L2-conflict-detection.md`.

**Input schema:**
```json
{
  "type": "string — 'direct' | 'temporal' (default: all)",
  "limit": "number — default 20",
  "json": "boolean — force JSON output"
}
```

**Output schema:**
```json
[
  {
    "id": "number",
    "conflict_type": "string",
    "source_entity": "string",
    "predicate": "string",
    "relation_ids": "number[]",
    "status": "unresolved | auto_resolved | manual_resolved | dismissed",
    "created_at": "string"
  }
]
```

**Required env:** `NOX_DB_PATH`

---

## kg_conflicts_resolve

Resolve a KG conflict by selecting which relation to keep.

**Status:** L2 specced, implementation pending. Requires `NOX_MCP_ALLOW_WRITES=1`.

**Input schema:**
```json
{
  "conflict_id": "number (required)",
  "keep_relation_id": "number — relation to keep (required unless keep_both)",
  "keep_both": "boolean — keep both relations (sets status=resolved, no suppression)",
  "note": "string — optional resolution note"
}
```

**Output schema:**
```json
{
  "conflict_id": "number",
  "status": "manual_resolved",
  "kept_relation_id": "number | null"
}
```

**Required env:** `NOX_DB_PATH`, `NOX_MCP_ALLOW_WRITES=1`

---

## kg_conflicts_dismiss

Dismiss a KG conflict as not actionable (e.g. intentional ambiguity).

**Status:** L2 specced, implementation pending. Requires `NOX_MCP_ALLOW_WRITES=1`.

**Input schema:**
```json
{
  "conflict_id": "number (required)",
  "note": "string — optional dismissal reason"
}
```

**Output schema:**
```json
{
  "conflict_id": "number",
  "status": "dismissed"
}
```

**Required env:** `NOX_DB_PATH`, `NOX_MCP_ALLOW_WRITES=1`
