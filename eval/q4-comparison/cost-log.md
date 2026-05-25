# Q4 Cost Log

| Run | Date | Systems | Corpus | Cost (USD) | Notes |
|---|---|---|---|---:|---|
| **Zep OSS cross-system** | **2026-05-24** | **zep (Docker, OpenAI embed)** | **6,830/6,830 chunks** | **~$0.07** | **OpenAI text-embedding-3-small @ $0.020/1M tok × ~3.5M tok. ~5min ingest+embed (watermill async) + ~5min parallel search (16 workers). n=20 queries. nDCG@10=0.3909 (LoCoMo 0.4529 / LongMemEval 0.3290). Unblocks "Zep GATED" in COMPARISON.md.** |
| **nox_mem hybrid FULL** | **2026-05-24** | **nox_mem (hybrid)** | **6,822/6,830 chunks** | **~$0.34** | **Gemini embedding-001 @ $0.000025/1K chars × ~13.6M chars. 47min ingest + 1min queries. Canonical Q4 baseline.** |
| nox_mem hybrid @500 (cap) | 2026-05-24 | nox_mem (hybrid) | 500/6830 chunks | ~$0.003 | PR #318 cap test. LoCoMo only (LongMemEval never reached). |
| Sat wider partial | 2026-05-23 | nox_mem + mem0 (500-cap) + agentmemory (partial) | nox_mem: full; mem0: 500/6830; agentmemory: 1401/6830 | ~$0.07 | mem0 OpenAI embed 500 chunks × ~$0.0001/embed ≈ $0.05; nox_mem FTS5 = $0.00; agentmemory = $0.00 |
| Previous smoke | 2026-05-23 | nox_mem + mem0 (n=20) + agentmemory (n=5) | partial | ~$0.10 | Earlier partial runs from session |

## Cost breakdown — 2026-05-23 wider partial

- **nox_mem**: $0.00 — FTS5 local eval DB, no API calls
- **mem0 (500-cap)**: ~$0.05 — 500 × OpenAI `text-embedding-3-small` embeds (no LLM extraction, `MEM0_SKIP_LLM_EXTRACTION=1` default)
- **agentmemory**: $0.00 — iii-engine local REST, no external API
- **zep/letta/evermind**: $0.00 — skipped
- **Total**: ~$0.05–0.07

## Cost to run full corpus

| System | Est. full cost | Blocker |
|---|---|---|
| mem0 (full 6830 chunks) | ~$0.68 (embed only) / ~$13–15 (embed + LLM extraction) | OpenAI rate limit + time (~2h) |
| agentmemory (full 6830 chunks) | $0.00 | Time (~2h at 100/min ingest rate) |
| Zep | $0.00 | Docker required |
| Letta | ~$0.10 | LETTA_API_KEY + Docker |
| nox_mem (prod mode) | $0.00 (Gemini flash-lite) | VPS availability for Gemini hybrid |
