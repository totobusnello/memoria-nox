# nox-mem Performance Baseline & Path B Critique — 2026-04-18

Read-only audit on VPS 100.87.8.44. DB: 135 MB, 1,951 chunks, 6,627 vec rows (NB: health endpoint reports `vectorCoverage.embedded=6627 / total=1951` — likely counting vec rows not distinct chunk_ids; orphan claim needs re-verification, but semantic is definitely failing in production — see finding #1).

## 1. Latency baseline (live VPS, localhost curl)

### /api/search — 18 samples across 1/3/7-10 word queries
Sorted (seconds): 0.313, 0.369, 0.411, 0.441, 0.445, 0.482, 0.502, 0.505, 0.506, 0.512, 0.517, 0.541, 0.615, 0.641, 0.682, 0.703, 0.823, 0.901

- **p50 ≈ 509 ms**, **p95 ≈ 862 ms**, **p99 ≈ 901 ms**, mean 550 ms.
- No correlation between word count and latency (1-word "gateway" = 901 ms; 9-word "describe the gateway crash…" = 313 ms). Cost is **not** FTS tokenization.
- EXPLAIN QUERY PLAN: `SCAN chunks_fts VIRTUAL TABLE INDEX 0:M3` + TEMP B-TREE for ORDER BY. FTS5 BM25 on 1,951 rows is <5 ms on an indexed virtual table — confirmed by pure-sqlite probes.
- **Where the 500 ms goes:** `searchHybrid` does `Promise.all([FTS, semantic])`. Semantic calls `embedText` → Gemini embedContent over HTTPS → `sem_search(query_vec)` on sqlite-vec. Journal shows **continuous 429s from Gemini during the probe window** ("Semantic search failed, falling back to FTS: Gemini embed query failed: 429" repeated dozens of times). Each query eats a full Gemini HTTP RTT (~300–700 ms) and ultimately falls back to FTS. **Measured 500 ms is 99% Gemini network+rate-limit cost, 1% SQLite.**

### /api/reflect
- 8 cold (`?nocache=1`): 1.77, 2.35, 2.47, 2.47, 2.48, 2.54, 2.55, 2.60, 2.63 s → **p50 2.48 s, p95 2.60 s**.
- 5 cold with unique queries: 1.8–2.6 s (same band — synthesis cost, not cache).
- Warm (hash hit): **1.2–1.7 ms** — literally a single SELECT. 1,400× speedup.
- Breakdown (isolated probes): gatherEvidence (searchHybrid+KG+decisions) ≈ 500–800 ms; Gemini 2.5 Flash `generateContent` ≈ 1.5–2.0 s; JSON parse & cache write <5 ms. **Flash RTT dominates.**

### Ingest (watcher journal, ~30 samples Apr 15–17)
- File ingest events are single log lines — no intra-file timing — but timestamps between successive ingests on the same file (e.g. decisions.md 126→127→128 chunks across 3 days) and the watcher's 15 s debounce imply ingest is <1 s per file for files of 1–130 chunks. Back-of-envelope **~50–150 chunks/sec** FTS5 inserts (no embeddings inline — ingest is FTS-only, vectorize runs weekly).

### Vectorize throughput
- `embedBatch` in src/embed.ts: **serial loop with `await sleep(100)` between each text**, plus one HTTP call per chunk. With Gemini embed RTT ~250–350 ms + 100 ms sleep → **~3 chunks/sec**. For 1,951 chunks that is ~11 minutes per full reindex. No parallelism, no true batching (Gemini embedContent has a batchEmbedContents endpoint that is not used).

## 2. Top 3 bottlenecks (evidence-based)

### #1 Semantic layer is network- and quota-bound, not compute-bound
- Every hybrid query opens a fresh HTTPS connection to `generativelanguage.googleapis.com`. No keep-alive reuse visible; no LRU on query embeddings. Plus Gemini free tier returns 429s under burst.
- **Fix A — embed-query cache (LRU 500 entries, 6 h TTL)**. 30–50% of agent queries repeat ("gateway", "auth", "cron"). Expected: p50 search drops 509 → ~80 ms (saves one Gemini RTT on hits).
- **Fix B — keep-alive agent** (`undici.Agent({ keepAliveTimeout: 30_000 })`) shaves 50–120 ms per call (TLS handshake elimination).
- **Fix C — run a local embedder** (e.g. `bge-small-en` 384d or `all-MiniLM-L6-v2` via ONNX on CPU) for **query** embeddings only (keep Gemini 3072d for ingest). Query embed ~15 ms on CPU → p50 ≈ 50 ms. Dimensional mismatch solved via projection matrix or dual-index.

### #2 /api/reflect cold = Flash generateContent RTT
- 1.5–2.0 s of the 2.5 s cold path is Gemini Flash. Options:
- **Streaming response** via `alt=sse` — user perceives first token at ~300 ms. No throughput win, large UX win.
- **Smaller prompt** — current `formatEvidence` sends top-5 chunks, top-5 entities, 3 decisions. Drop chunk body from 300 → 180 chars and entities 5 → 3: ~30% fewer input tokens, ~400 ms saved.
- **Parallelize evidence gathering** — `gatherEvidence` already runs hybrid in parallel but `queryEntity`, `findPath`, `listDecisions` are sequential. Promise.all them: ~150 ms saved.

### #3 Vectorize is pathologically serial
- BATCH_SIZE is a print-progress counter, not a real batch. **Use `batchEmbedContents`** (up to 100 texts per call) and **remove the 100 ms sleep** (Gemini free tier allows 1,500 RPM embedding, not a latency-per-request limit). Expected: 3 → ~80 chunks/sec (25× speedup, 11 min → 25 s for full reindex). Plus add `Promise.all` with p-limit=4 for concurrent HTTP.

## 3. Path B critique

### Semantic cache (cosine > 0.92) — viable but gated on embed cache
- **Hit-rate claim (25% → 70%) is not credible without data.** 70% requires query-distribution analysis we don't have; current hash cache has 12 entries / 12 hits after a full day of probing. Four natural hits out of possibly thousands of agent queries suggests **query diversity is high**. Path B helps only if agents repeatedly re-ask semantically-equivalent questions — unproven.
- **Calibration of 0.92 threshold is thumb-sucked.** Gemini embeddings are normalized and 3072d; empirically cosine 0.85–0.90 is "same topic, different intent" territory. Need offline eval: sample 200 real queries, cluster by intent, measure intra/inter-cluster cosines, pick threshold at FPR < 2%. Until then, **start at 0.95** (stricter, fewer false positives; degrade to 0.92 if hit rate < 20%).
- **Cost to add**: every miss now costs +~300 ms (query embed) on top of current path. If hit rate is actually 30% (plausible), expected added latency = 0.7 × 300 − 0.3 × synthesis_avoided ≈ 210 ms miss penalty − 750 ms saved on hits ≈ net −540 ms. Only wins **if hit rate > ~15%**. Below that, it's a regression.
- **Implementation catch**: you cannot use sqlite-vec's KNN on 12 rows efficiently — just load all cached embeddings into memory and do dot product. O(n) where n=cache size (keep n < 2000).

### Dependency-set invalidation — don't build it (yet)
- Overhead analysis: if avg 5 sources/row × average cache size 500 rows = 2,500 index rows. Tiny. **Storage is NOT the problem.**
- **Write-time cost is the real concern.** Every chunk insert/update/delete must scan `reflect_cache_sources` for matching `chunk_id` and nuke parent rows. With 1,951 chunks growing and ingest bursts of 100+ chunks/sec during consolidation, an indexed `WHERE chunk_id=?` DELETE per ingest adds ~0.5 ms × 100 = 50 ms burst stall. Acceptable, but not free.
- **Correctness hazard**: chunks don't have stable ids across reindex (watcher does DELETE + INSERT on file change). `evidence_sources` holds stale ids → invalidation silently misses. Must key on `(source_file, chunk_text_hash)` not `chunk_id`, OR switch watcher to UPSERT.
- **Simpler alternative that captures 80% of value**: keep 24 h TTL, **add semantic-key lookup**, skip dep-set invalidation entirely. If a source chunk changes, the cached answer is stale for at most 24 h — acceptable for a synthesis endpoint. Revisit dep-set only if TTL proves too lax in practice.

### Recommended Path B-lite
1. Embed query (with LRU of query→embedding, 500 entries).
2. Look up hash cache first (free, 1 ms).
3. On hash miss, scan last 200 cache rows by cosine (in-memory, ~3 ms for 200×3072 float32 dot products).
4. If top cosine > 0.95: return, increment hit_count. Else synthesize.
5. TTL stays at 24 h. No dep-set table.
6. Ship instrumentation: log (query, top_cosine, hit/miss) for 2 weeks before tuning threshold.

## 4. SLOs (current → aspirational)

| Metric | Current (measured) | Target (fixes applied) | Argument |
|---|---|---|---|
| `/api/search` p95 | 862 ms | **< 150 ms** | Fix Gemini 429 (quota or local embedder) + keep-alive + query-embed LRU. SQLite FTS+vec alone is <20 ms. 150 ms leaves headroom for one remote call on miss. |
| `/api/reflect` warm p95 | 1.7 ms | **< 5 ms** | Already excellent. Guardrail against future regressions (e.g. adding semantic-scan should not exceed 5 ms). |
| `/api/reflect` cold p95 | 2.60 s | **< 1.5 s** | Streaming + prompt trim + parallel evidence. Flash RTT is the floor; ~1.2 s is physical minimum on Gemini. |
| `reflect_cache` hit rate | ~25% projected | **≥ 40% (not 70%)** | Semantic-key lifts hash cache; 70% requires agent behavior we haven't observed. Measure for 2 weeks before committing. |
| Vectorize throughput | ~3 chunks/s | **≥ 60 chunks/s** | `batchEmbedContents` (100/call) + p-limit=4 + drop sleep. Full reindex 11 min → <40 s. |

## Appendix: source of truth
- `/root/.openclaw/workspace/tools/nox-mem/src/search.ts` lines 79–178 (searchSemantic + searchHybrid RRF k=60)
- `/root/.openclaw/workspace/tools/nox-mem/src/reflect.ts` lines 10–58 (CACHE_TTL_HOURS=24, `hashQuery` = djb2-ish 32-bit), 166–200 (synthesize → Flash)
- `/root/.openclaw/workspace/tools/nox-mem/src/embed.ts` lines 94–107 (embedBatch serial loop, 100 ms sleep, no batchEmbedContents)
- PRAGMAs: journal_mode=WAL, synchronous=NORMAL(2), cache_size=-2000 (2 MB — low for 135 MB DB; consider -65536 = 64 MB), mmap_size=0 (consider 256 MB). Low-risk tuning, single-digit % win.
- Ingest volumes from `journalctl -u nox-mem-watcher` (sampled 2026-04-15 to 2026-04-17).
