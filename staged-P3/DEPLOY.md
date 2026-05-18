# P3 — Temporal Queries Deployment Guide

## What this implements

`--as-of <date>` and `--changed-since <date>` temporal filters for nox-mem search,
applied as hard SQL pre-filters (not ranking boosts) across CLI, HTTP API, and MCP.

## Files to deploy on VPS

### 1. New file — `src/lib/dates.ts` (or `src/dates.ts` matching VPS path)

Deploy: `staged-P3/edits/dates.ts`

### 2. Replace/patch — `src/search.ts`

Deploy: `staged-P3/edits/search.ts`

Key changes vs staged-1.7a:
- `TemporalFilter` interface (`asOf?: Date`, `changedSince?: Date`)
- `SearchOptions` extends `TemporalFilter`
- `buildTemporalClause()` → SQL WHERE fragment generator
- `search()` → FTS5 query includes `${temporal.sql}` in WHERE
- `searchSemantic()` → post-vector chunk id temporal filter via SQL IN
- `searchHybrid()` → passes `filter` through to both
- `SearchResult` gains `created_at` and `updated_at` fields

### 3. Patch — `src/index.ts` (CLI)

See `staged-P3/edits/index.ts` for the exact replacement of the `search` command block.

Added flags:
- `--as-of <date>` — time-travel query
- `--changed-since <date>` — recent-changes query

Also add `import { parseFlexibleDate } from "./dates.js";` near CLI imports.

### 4. Patch — `src/api-server.ts` (HTTP API)

See `staged-P3/edits/api-server.ts` for the `/api/search` case replacement.

New params accepted:
- GET: `?as_of=7d&changed_since=2026-05-01`
- POST body: `{ "q": "...", "as_of": "7d", "changed_since": "2026-05-01" }`

Also add `import { parseFlexibleDate } from "./dates.js";`.

### 5. Patch — MCP search tool

See `staged-P3/edits/mcp-search-tool.ts`.

Find `nox_mem_search` tool definition and:
- Add `as_of` and `changed_since` to `inputSchema.properties`
- Replace handler to parse and pass temporal filter to `searchHybrid()`

### 6. Tests

Deploy: `staged-P3/tests/temporal.test.ts`
→ Target path: `src/lib/search/__tests__/temporal.test.ts`

Run: `node --test --require ts-node/register src/lib/search/__tests__/temporal.test.ts`
Or after build: `node --test dist/lib/search/__tests__/temporal.test.js`

## Architecture note on KG temporal filtering

KG entities (`kg_entities`) and relations (`kg_relations`) do NOT have `created_at`/`updated_at`
in schema v18. Temporal filtering applies to **chunks only**.

The hybrid search flow fetches KG candidate chunks via `evidence_chunk_id` FK, but KG-path
queries (`/api/kg/path`, `kg-path` CLI) are separate endpoints not covered by this filter.

This is NOT a BLOCKED condition — hybrid search (the primary retrieval path) fully
respects temporal filters. KG-path temporal filtering would require schema changes and
is deferred to a future P-series spec.

## Usage examples

### CLI
```bash
nox-mem search "deployment decisions" --as-of 2026-04-01
nox-mem search "OpenClaw fixes" --changed-since 7d
nox-mem search "schema migration" --as-of 2026-05-01 --changed-since 30d
nox-mem search "recent lessons" --changed-since 1w --no-hybrid
```

### HTTP API
```bash
curl "http://localhost:18802/api/search?q=deployment&as_of=2026-04-01"
curl "http://localhost:18802/api/search?q=fixes&changed_since=7d"
curl -X POST http://localhost:18802/api/search \
  -H 'Content-Type: application/json' \
  -d '{"q":"schema","as_of":"2026-05-01","changed_since":"30d"}'
```

### MCP (via Claude)
```json
{ "name": "nox_mem_search", "arguments": { "query": "deployment", "as_of": "2026-04-01" } }
{ "name": "nox_mem_search", "arguments": { "query": "fixes", "changed_since": "7d" } }
```

## Constraints respected

- NO schema changes (chunks already have `created_at`, `updated_at` from schema v18)
- NO ranking changes (filter is WHERE clause, not score boost)
- P3 is distinct from E13 temporal boost (E13 boosts recency in ranking; P3 hard-filters)
- `deleted_at` guarded with COALESCE — safe even if column doesn't exist in older schema versions
- `created_at IS NULL` treated as "always existed" (safe for legacy chunks without timestamps)
