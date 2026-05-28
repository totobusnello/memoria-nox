# Phase G Cost Estimate

Phase G runs against the **same** Gemini-2.5-Flash backbone as Phase D + F.
Per-token costs are unchanged.

| Stage                                                                     | Per-batch cost (est.) |
|---------------------------------------------------------------------------|----------------------:|
| Ingest (Add) — SKIPPED, DB reused from Phase D                            | $0.00                 |
| Vectorize — SKIPPED, vectors reused from Phase D                          | $0.00                 |
| Search — 626 × hybrid retrieval (BM25 + Gemini embed)                     | ~$0.05                |
| Answer — 626 × Gemini-2.5-Flash answer call                               | ~$0.50                |
| Evaluate — 237 × Gemini-2.5-Flash LLM judge on open-ended                 | ~$0.20                |
| Rerank — MiniLM CPU compute                                               | $0.00 (local)         |
| **Batch 004 single-batch gate**                                           | **~$0.75**            |
| 5-batch full (004/005/010/011/016) if gate passes                         | ~$3.00 additional     |

## Hard cap

Total Phase G allowance: **$5.00** (Toto raised total cap to $10; Phase F
consumed ~$0.80, ~$9.20 remaining).

Stop trigger: if batch 004 single-batch overall accuracy regresses > 2 pp
below Phase D 61.98% **AND** multi-hop did not gain ≥ 3 pp, do not launch
5-batch — file results as Phase G negative result.

## Compute disclosure

- Reranker model size: ~22 MB (MiniLM)
- Reranker pre-warm: free, one-time HuggingFace download
- Per-query rerank time: ~3 s warm-cache CPU predict (50 chunks × 300 tokens
  at max_length=512)
- Total rerank overhead per batch 004 (626 queries × 3 s): ~30 min wall —
  fits in budget vs Phase F 1.7 h estimate that killed budget.
