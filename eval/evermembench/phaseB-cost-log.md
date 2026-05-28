# EverMemBench Path B — Cost log

Cap: $10 USD (raised from $5 mid-session). Soft target: $8.

| Stage | Batches | Est cost | Notes |
|---|---|---|---|
| Phase B run (PR #364, batch 004 only) | 004 | ~$0.75 | Measured prior |
| Phase C run (batch 004 only) | 004 | ~$0.65 | Measured prior |
| Phase D run (this session, batch 004, top-k=20) | 004 | ~$0.75 | Single-batch search+answer+evaluate; took 1070s wall |
| Phase 3 run (4 batches parallel, top-k=20) | 005/010/011/016 | ~$2.80 | 4 batches × ~$0.70; concurrent Gemini calls |
| **Total realised** | | **~$4.95** | Within $10 cap, near soft target $8 |

## Stage-level timings

| Batch | Wall-time | Stage breakdown |
|---|---|---|
| 004 (Phase D) | ~1070s | vec ~10min + search ~3min + answer ~14min + eval ~3min |
| 005 (Phase 3) | 1043s | parallel — same shape |
| 010 (Phase 3) | 1063s | |
| 011 (Phase 3) | 1077s | |
| 016 (Phase 3) | 1071s | |

Phase 3 wall ~18min (parallel) vs estimated 4×25min serial = strong parallelism benefit.

## Notes on budget reasoning

Original prompt budget was $5 hard cap with $4 hard-stop. Mid-session Toto raised cap to $10 with $8 soft target. With cap relaxed:
- All 5 batches completed Phase D + Phase 3 with top_k=20 (winner variant from Phase D gate)
- ~$4.95 total realised; no Phase E (e1/e2/e3) attempted given Phase D gate WINS clearly and Phase 3 confirmed 5-batch generalisation
- ~$5 budget headroom remaining for follow-up work (e.g. Phase E exploration if multi-hop weakness needs addressing)

## Why no Phase E in this session

Phase 3 aggregate revealed **5-batch nox-mem = 62.22% — beats MemOS (59.27%) by +2.95** in honest comparison.
- Multi-hop (F_MH) is structurally weak at 5.22% — but Phase E top_k=30 unlikely to fix it (top_k 10→20 only moved F_MH from 0→2 on batch 004)
- The right next iteration is multi-query expansion or cross-encoder reranking — both are larger engineering investments deferred to future work
- Skipping E preserves budget headroom and matches Toto's guidance: "don't burn budget on speculative iterations if the data doesn't justify"

## GPT-4.1-mini bonus run — SKIPPED

OpenRouter key not configured in env. Skipped per prompt fallback instruction.
