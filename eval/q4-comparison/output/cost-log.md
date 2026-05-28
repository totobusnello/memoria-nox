# Q4 Cross-System Benchmark — Cost Log

> Actual spend per system run. Sat 2026-05-24 → ongoing.

## 2026-05-27/28 LightRAG @ LIMIT=2000 (task #14)

| Item | Estimate | Actual |
|---|---:|---:|
| Gemini embeddings (3072d, ~2000 docs) | $0.03 | ~$0.03 |
| Gemini 2.5 Flash KG extraction (~2000 chunks × 1.5k in / 800 out) | $0.71 | ~$0.65 |
| Gemini 2.5 Flash merge LLM (collisions amortized) | $0.13 | ~$0.10 |
| Gemini 2.5 Flash mix-mode query rewrites (20 q × 4 modes) | $0.40 | ~$0.35 |
| Community report batch | $0.50 | ~$0.45 |
| Misc retry/cache writes | $0.05 | ~$0.05 |
| **Total LightRAG @ 2000** | **~$1.82 + $2.50 community = ~$4.30** | **~$1.63** |

**Notes:**
- Cache (`/private/tmp/lightrag-q4-*/cache/lightrag/`) = ~340 MB on disk. Re-runs at $0 (LLM responses cached).
- LIMIT=2000 == ~20% of LoCoMo + LongMemEval corpus (consistent with agentmemory 20%, mem0 500-cap).
- Full corpus (9882 chunks) would take ~10h wall-clock + ~$25 cost. Deferred.
- Actual ingest rate observed: **17 docs/min sustained** (original "30 docs/min" estimate was off).
- Search phase: 20 queries × ~11s p50 latency = ~3.7 min total. Mix mode (4 query types) drove the latency.

## Other systems (historical)

- **HippoRAG2 full** (PR #355 merged 2026-05-24): ~$2.06 (vs $9-11 estimate, 5× cheaper).
- **AgentMemory full** (PR #338): ~$0 (local SDK, no LLM calls except embedding via OpenAI which was capped).
- **Zep OSS Docker** (PR #346): ~$1.30 OpenAI embed (forced for Zep ingest).
- **Mem0 cap=500**: $0 — within free tier.
- **nox_mem full**: $0 — Gemini embedding cache from prod (no fresh embedding spend).

