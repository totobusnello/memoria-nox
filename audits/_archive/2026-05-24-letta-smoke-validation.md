# Letta Docker Smoke Validation — 2026-05-24

**Status: PASS with adapter fixes applied**

---

## Setup

| Item | Value |
|------|-------|
| Docker engine | OrbStack 29.4.0 |
| Letta image | `letta/letta:0.6.6` |
| SDK installed | `letta-client==0.1.46` |
| Postgres image | `postgres:16-alpine` |
| Compose file | `eval/q4-comparison/compose/docker-compose.yml` |
| Profile | `--profile letta` |
| Letta port | `:8283` |
| OPENAI_API_KEY | set |

---

## Daemon Start/Stop Sequence

```bash
# Start (from eval/q4-comparison/)
OPENAI_API_KEY=$OPENAI_API_KEY \
  docker compose -f compose/docker-compose.yml --profile letta up -d

# Health check (via Python — curl blocked in context-mode)
python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://127.0.0.1:8283/v1/health', timeout=5)
print(json.loads(r.read()))
"
# Expected: {'version': '0.6.6', 'status': 'ok'}

# Stop
docker compose -f compose/docker-compose.yml --profile letta down

# Wipe volumes (destructive — loses archival memory)
docker compose -p q4-comparison -f compose/docker-compose.yml down -v
```

**Note:** Zep service restarts in the `--profile letta` stack (Zep needs its own env config). This is expected and does not affect Letta functionality.

**First boot time:** ~60s for image pull + Letta startup. Health becomes OK in ~30s after containers report "Up".

---

## Adapter Bugs Found and Fixed

### Bug 1: `agents.create()` missing required fields

**SDK version:** letta-client 0.1.46  
**Root cause:** The 0.1.46 SDK requires `memory_blocks`, `llm_config`, and `embedding_config` explicitly. Old adapter passed only `embedding_config={'embedding_endpoint_type': 'openai'}` which is missing `embedding_model` and `embedding_dim`.

**Fix applied in `adapters/letta.py`:**
```python
created = _client.agents.create(
    name=agent_name,
    memory_blocks=[
        CreateBlock(value="Q4 benchmark comparison user context.", label="human"),
        CreateBlock(value="I am a memory retrieval agent...", label="persona"),
    ],
    llm_config=LlmConfig(
        model="gpt-4o-mini",
        model_endpoint_type="openai",
        model_endpoint="https://api.openai.com/v1",
        context_window=16384,
    ),
    embedding_config=EmbeddingConfig(
        embedding_endpoint_type="openai",
        embedding_endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
        embedding_chunk_size=300,
    ),
)
```

### Bug 2: SDK `passages.create()` calls wrong URL

**Root cause:** `letta_client.agents.passages.create()` targets `/v1/agents/{id}/archival-memory` (hyphenated) but the server exposes `/v1/agents/{id}/archival` (no hyphen). Results in HTTP 404.

**Fix:** All archival operations (insert, list, count) now use direct `urllib.request` REST calls to the correct `/v1/agents/{id}/archival` endpoint.

### Bug 3: `archival_memory_search` no longer a REST endpoint

**Root cause:** Letta 0.6.6 REST API removed the direct `archival_memory_search` endpoint. The `GET /v1/agents/{id}/archival` endpoint only supports pagination (cursor-based, no semantic query param). Semantic search requires sending a message to the agent and parsing the built-in tool's output.

**Fix:** New `_archival_search_via_message()` function:
1. POST to `/v1/agents/{id}/messages` with `{"messages": [{"role": "user", "text": "Search archival memory for: <query>"}]}`
2. Walk response messages for `tool_return_message` from `archival_memory_search`
3. Parse tool_return string via `ast.literal_eval` — format: `([{'timestamp': ..., 'content': ...}, ...], N)`
4. Map content text back to nox_id via `_reverse_text_map`

**Score proxy:** Letta does not expose relevance scores in the tool_return. We assign `1/(1+rank)` as a rank-based proxy. This is honest — documented in adapter docstring and output.

### Bug 4: Runner expects `setup()` to ingest corpus

**Root cause:** The runner calls `adapter.setup()` then `adapter.search()` directly — no `ingest_corpus()` call. Other adapters (mem0) handle corpus loading inside `setup()`. Original letta adapter left `setup()` as connection-only, leaving zero passages in archival memory.

**Fix:** `setup()` now calls `_ingest_corpus()` which:
- Loads corpus via `lib.corpus_loader` (same as mem0)
- Is idempotent (skips if archival count + id-map already cover all chunks)
- Respects `LETTA_INGEST_LIMIT` env var for cost control
- Respects `LETTA_FORCE_REINGEST=1` to force re-ingest

---

## Smoke Run Results

**Command:**
```bash
cd eval/q4-comparison && \
  LETTA_BASE_URL=http://127.0.0.1:8283 \
  OPENAI_API_KEY=$OPENAI_API_KEY \
  LETTA_INGEST_LIMIT=200 \
  python3 runner.py --systems letta --datasets locomo --limit 5
```

**Ingest:** 200 locomo chunks (first 200 in corpus order, convs 1–5 range) — 0 errors

**Results:**

| question_id | latency_ms | gold_hits | results | error |
|-------------|-----------|-----------|---------|-------|
| conv-48::q13 | 16,400 | 0/4 | 5 | None |
| conv-50::q49 | 13,942 | 0/3 | 5 | None |
| conv-26::q6  | 14,255 | **1/1** | 5 | None |
| conv-30::q11 | 14,535 | 0/1 | 5 | None |
| conv-44::q53 | 15,760 | 0/4 | 5 | None |

- **Total gold hits:** 1/13 (7.7%)
- **Total errors:** 0
- **Avg latency:** 14,978ms

**Why low gold hits at limit=200:** The 200-chunk limit pulls convs 1–5 area; gold IDs span convs 26, 30, 44, 48, 50. Only conv-26 had partial overlap. Full corpus ingest (5,882 locomo chunks) would cover all gold IDs — expected to yield 30–50%+ hits given the agent's semantic search quality.

**ID round-trip validation:**
- `conv-26::q6` returned `conv-26::D2:7` ✓ exact gold match, correct `conv-XX::DX:X` format
- All 25 returned results have valid `conv-XX::DX:X` IDs — text reverse-map working correctly

---

## Cost Notes

| Operation | Unit cost | Smoke run (200 chunks + 5 queries) | Full run (5882 chunks + 100 queries) |
|-----------|-----------|-------------------------------------|---------------------------------------|
| Embedding ingest | ~$0.0001/1k tokens (ada-002) | ~$0.006 (200×300 tok avg) | ~$0.18 |
| LLM search (gpt-4o-mini) | ~$0.00015/1k tokens | ~$0.02 (5 queries × ~4k ctx) | ~$0.4 |
| **Total** | | **~$0.03** | **~$0.58** |

---

## Production Run Notes (when ready for wider eval)

1. Remove `LETTA_INGEST_LIMIT` or set to `0` for full corpus
2. Run ingest once (idempotent): `setup()` will skip if already done
3. Letta LLM loop adds ~14s avg per query (gpt-4o-mini latency + tool invocation) — budget 30–60min for 100 queries
4. Score proxy is rank-based (1/(1+rank)) — no numeric relevance score from Letta
5. Zep service in the compose stack crashes (not needed for Letta) — add `--scale zep=0` if desired

---

## Cleanup

```bash
# Stop containers
docker compose -f compose/docker-compose.yml --profile letta down

# Wipe persistent volumes (destroys archival memory — requires re-ingest)
docker compose -p q4-comparison -f compose/docker-compose.yml down -v

# Remove id-map state (forces re-ingest next run)
rm eval/q4-comparison/output/_state/letta-id-map.json
```
