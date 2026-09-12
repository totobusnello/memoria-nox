# Zep OSS Docker Smoke Validation — 2026-05-24

**Status: GATED — OpenAI key required for search**
**Environment:** Docker 29.4.0 (OrbStack), macOS, Python 3.12, zep-python 2.0.2
**Zep image:** `ghcr.io/getzep/zep:0.27.2`
**Date:** 2026-05-23 (evening BRT)

---

## Summary

Zep 0.27.2 OSS cannot run the Q4 benchmark at zero cost. All search paths require
OpenAI embeddings regardless of extractor configuration. This invalidates the
original spec assumption that Zep "uses FastEmbed local" — that capability does not
exist in the only publicly available image (`0.27.2`).

Two infrastructure fixes were discovered and applied to `compose/docker-compose.yml`
and a new `compose/zep-config.yaml` was created. The runner was fixed to support
`ingest_corpus()` adapters. However, search remains blocked.

**Decision required from Toto:** accept OpenAI embedding cost for Zep smoke (~$0.02
for limit=5, ~$0.50 for full n=100 locomo+longmemeval), or gate Zep as "infrastructure
blocked" in the Q4 comparison table.

---

## Infrastructure Fixes Applied (docker-compose.yml + compose/)

### Fix 1: postgres:16-alpine → pgvector/pgvector:pg16

**Root cause:** Zep 0.27.2 calls `CREATE EXTENSION vector` at startup to set up HNSW
indexes for message embeddings. `postgres:16-alpine` does not ship `pgvector`.

**Symptom:** Zep fatal at startup:
```
storage error: failed to ensure postgres schema setup (original error: error creating
table ... type "vector" does not exist (SQLSTATE=42704))
```

**Fix:** Changed `image: postgres:16-alpine` → `image: pgvector/pgvector:pg16`.

### Fix 2: ZEP_OPENAI_API_KEY required even with extractors disabled

**Root cause:** Zep 0.27.2 startup code validates `ZEP_OPENAI_API_KEY` env var as a
mandatory pre-flight check, before loading config. This runs even when all
`Extractors.*.Enabled: false` in config.

**Symptom:** Zep fatal at startup:
```
ZEP_OPENAI_API_KEY is not set
```

**Fix:** Added `ZEP_OPENAI_API_KEY: ${OPENAI_API_KEY:-no-llm-not-used}` to compose
environment and switched to a `--config /app/zep-config.yaml` mount to pass a full
Zep config (all extractors disabled). With this fix, Zep 0.27.2 starts successfully
and `/healthz` returns `200`.

### Fix 3: ZEP_STORE_TYPE env var ignored — config file required

**Root cause:** Zep 0.27.2 does not map `ZEP_STORE_TYPE` from env vars to the
`Store.Type` config field via the expected pattern. The env var is silently ignored.

**Symptom:** Zep fatal:
```
store.type must be set
```

**Fix:** Mount a full `zep-config.yaml` via `--config` flag. `compose/zep-config.yaml`
is the new config source of truth for the stack.

---

## SDK/API Compatibility Issue

`zep-python==2.0.2` (the version pinned in the adapter) uses API path prefix `api/v2`.
Zep 0.27.2 server only exposes `api/v1`. All SDK calls return `404 page not found`.

`zep-python==1.5.0` (the v1 API SDK) has a pydantic v1/v2 incompatibility on Python 3.12:
```
pydantic.v1.errors.ConfigError: unable to infer type for attribute "uuid"
```

**Resolution path:** The adapter should be rewritten to use `requests` directly against
the `api/v1` REST endpoints (no SDK dependency). The v1 endpoints work correctly for
session creation (`POST /api/v1/sessions`) and message ingest
(`POST /api/v1/sessions/:id/memory`).

---

## Search Blocker: OpenAI Embeddings Required

Zep 0.27.2's search API (`POST /api/v1/sessions/:id/search`) vectorizes every query
via OpenAI's Embedding API before querying the HNSW index. This is true for all
`search_type` values (`message`, `mmr`).

Without a valid OpenAI key, search fails:
```
storage error: failed to embed query (original error: API returned unexpected status
code: 401: Incorrect API key provided)
```

There is no keyword/BM25 search path in Zep 0.27.2.

**FastEmbed claim:** The compose YAML comment ("OSS Zep can run with local-only
embeddings via FastEmbed") was incorrect. FastEmbed is not present in the 0.27.2
image. It may have been added in a later unreleased CE build (v1.0.0+), but
`ghcr.io/getzep/zep:v1.0.0` is not publicly available on ghcr.io.

---

## What DID Work

| Step | Status |
|------|--------|
| `docker compose up -d postgres` | OK — pgvector/pg16 starts healthy |
| `docker compose up -d zep` (with fixes) | OK — `/healthz` returns 200 |
| `smoke_test.py --systems zep` | OK — `Zep OSS healthy at http://127.0.0.1:8000` |
| `POST /api/v1/sessions` (raw requests) | OK — session created |
| `POST /api/v1/sessions/:id/memory` (raw requests) | OK — messages ingested |
| `POST /api/v1/sessions/:id/search` | FAIL — 401 from OpenAI embed call |

---

## Runner Changes

`eval/q4-comparison/runner.py` was updated to support corpus pre-loading for adapters
with `ingest_corpus()`:

- New `load_corpus(path)` function — reads JSONL corpus file
- New `--corpus-file` CLI arg — explicit corpus JSONL path
- New `--skip-ingest` CLI arg — reuse previously ingested data
- `run_system()` now calls `adapter.ingest_corpus(chunks)` after `setup()` when
  the adapter has this method and corpus chunks are provided
- Auto-detect: single-dataset runs auto-resolve `cache/<dataset>.jsonl` if present

This fixes the existing bug where Zep's `ingest_corpus()` was never called, causing
all searches to return empty (confirmed in prior `zep.json` output: 5/5 empty results).

---

## Recommended Path Forward

### Option A: Gate Zep (recommended if cost matters)

Add Zep to the Q4 table with status `INFRASTRUCTURE_BLOCKED` and note:
- Zep 0.27.2 OSS requires OpenAI API key for search (no local embedding option)
- FastEmbed capability only available in unreleased CE builds (v1.0.0+)
- Will re-evaluate when Zep publishes a CE image with local embedding

### Option B: Use OpenAI key for Zep smoke

Cost estimate:
- text-embedding-3-small at $0.02/1M tokens
- locomo corpus: ~5882 chunks × ~150 tokens avg = ~880k tokens → ~$0.018
- limit=5 smoke: ~150 tokens × 5 queries = ~750 tokens (negligible)
- Full n=100: same corpus ingest (~$0.018) + 100 query embeddings (~negligible)
- **Total: ~$0.02 for full locomo run**

If approved, update `compose/zep-config.yaml` to set `Extractors.Messages.Embeddings.Enabled: true`
and pass `OPENAI_API_KEY` to the container, then rewrite adapter with raw `requests` calls.

### Option C: Downgrade to Zep CE with local embeddings

Monitor `ghcr.io/getzep/zep` for a CE release tag with FastEmbed. The v1.0.0 tag was
released on GitHub but not yet on the container registry. Check back in 1-2 weeks.

---

## Teardown Sequence

```bash
# After smoke run (or to clean up failed run)
cd eval/q4-comparison
docker compose -f compose/docker-compose.yml down
# To also wipe postgres data (reset between benchmark runs):
docker compose -f compose/docker-compose.yml down -v
```

Container state during a run:
- `q4-postgres` — pgvector/pgvector:pg16, port 5432 (local only)
- `q4-zep` — ghcr.io/getzep/zep:0.27.2, port 8000 (local only)
- Network: `q4-comparison_default` (bridge, created by compose)

Both containers have `restart: unless-stopped` — they survive Docker daemon restarts.
Use `docker compose down` to stop cleanly before system sleep/shutdown if needed.

---

## Files Changed

| File | Change |
|------|--------|
| `eval/q4-comparison/compose/docker-compose.yml` | Fix 1+2+3 (pgvector image, ZEP_OPENAI_API_KEY, config mount) |
| `eval/q4-comparison/compose/zep-config.yaml` | New — Zep 0.27.2 config with all extractors disabled |
| `eval/q4-comparison/runner.py` | Add `ingest_corpus()` support + `--corpus-file` + `--skip-ingest` |
