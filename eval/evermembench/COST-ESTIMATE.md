# EverMemBench Cost Estimate — Phased Budget Proposal

**Date:** 2026-05-27
**Source data:** observed batch 004 size (10,222 messages, 626 QA), EverMemBench `pipeline.yaml` model config, OpenRouter pricing as of 2026-05-27

## 1. Pricing Assumptions

Models used (from `eval/config/pipeline.yaml`):
- **Answer generation:** `openai/gpt-4.1-mini` (all questions, MC + OE)
- **Open-ended judge:** `google/gemini-3-flash-preview` (OE questions only)

OpenRouter pricing (2026-05-27, prepay credits):
- `gpt-4.1-mini`: ~$0.40 / 1M input tokens, ~$1.60 / 1M output tokens
- `gemini-3-flash-preview`: ~$0.075 / 1M input, ~$0.30 / 1M output

Per-question token estimates (worst-case):
- Answer gen: 1.5k input (retrieved memories + question + system prompt) + 200 output = ~$0.001 / question
- OE judge: 1k input + 100 output = ~$0.00011 / question

## 2. Per-Batch Cost (observed batch 004)

| Stage | Cost driver | Cost |
|-------|-------------|------|
| Add | nox-mem CLI ingest (local Gemini embedding via env, NOT billed in benchmark) | $0.00 |
| Search | nox-mem HTTP `/api/search` (local) | $0.00 |
| Answer (626 questions × $0.001) | gpt-4.1-mini | **~$0.63** |
| Evaluate (estimated 50% OE × 313 × $0.00011) | gemini-3-flash-preview | **~$0.04** |
| **Batch 004 total** | | **~$0.67** |

If question split is MC-heavier (e.g., 80/20), OE judge cost drops further (~$0.02). Headline number bounded by Answer stage.

## 3. Full 5-Batch Cost

Assuming similar QA counts across batches (~500-700 each = ~3000 total questions):

| Item | Quantity | Unit | Total |
|------|----------|------|-------|
| Answer gen | 3000 | $0.001 | **~$3.00** |
| OE judge | ~1500 | $0.00011 | **~$0.17** |
| **Full 5-batch total** | | | **~$3.17 USD** |

Conservative ceiling with retries + longer contexts: **~$5 USD**. **Well under the $3-per-stage cost cap** (the task spec said >$3 for Add alone would warrant stopping; the actual blocker is Answer stage at ~$3, still acceptable).

## 4. Time Estimate

| Stage | Wall-clock per batch | 5 batches |
|-------|----------------------|-----------|
| Add (ingest 10k msgs + Gemini embed) | 20-40 min | ~2-3 hours |
| Search (626 queries × ~1s) | 10-15 min | ~1 hour |
| Answer (626 × ~3s gpt-4.1-mini call, concurrency=1) | 30-45 min | ~3 hours |
| Evaluate (~313 OE × ~2s, concurrency=20) | 1-2 min | ~10 min |
| **Per-batch total** | ~60-90 min | **~6-8 hours** |

Parallelizable if VPS has bandwidth: run 2-3 batches concurrently with separate `NOX_DB_PATH` per batch. Halves wall time.

## 5. Phased Approach (RECOMMENDED)

**Phase 1: Smoke + batch 004 only (~$0.70, ~1.5 hours)**
- Validate full pipeline end-to-end on the smallest/canonical batch.
- Compare against EverOS published numbers for batch 004 (Table X in paper).
- Gate: if nox-mem accuracy is within 10pp of EverOS systems' median → expand. If wildly off → debug before spending more.

**Phase 2: Remaining 4 batches (005, 010, 011, 016) (~$2.50, ~5-6 hours)**
- Run sequential or parallel depending on VPS capacity.
- Aggregate via `tools/analyze_results.py` per-category breakdown.

**Phase 3: bge-reranker-v2-m3 evaluation (separate Lab Q1 spec)**
- Re-run Phase 1+2 with reranker enabled. Cost identical (~$3 more in API spend).
- Compare nDCG@10 + accuracy deltas to justify reranker inclusion in v1.1.

**TOTAL Lab Q1 budget for EverMemBench track: ~$6-7 USD across Phases 1+2 with reranker ablation.**

## 6. Cost Triggers to Stop

- If Add stage on batch 004 takes >2h wall time → infrastructure issue, investigate.
- If Answer stage rate-limits hit OpenRouter and require >10 retries per question → reconsider concurrency settings.
- If accuracy on batch 004 < 30% → domain mismatch is structural; do not expand. Document, write up, redirect Lab Q1 capacity to bge-reranker.

## 7. Out-of-Scope Costs

- **HuggingFace dataset download:** free, anonymous, ~30 MB total all 5 batches.
- **VPS compute:** sunk cost (existing nox-mem deployment).
- **Gemini embedding quota:** free-tier 3M/d covers 10k-msg ingest easily; no incremental cost.
- **EverOS clone:** ~6 MB, free.

## 8. Comparison Table

| Track | Cost | Wall time | Value |
|-------|------|-----------|-------|
| EverMemBench Phase 1 (batch 004) | ~$0.70 | ~1.5 h | Validate harness end-to-end, sanity-check vs EverOS |
| EverMemBench Phase 2 (all 5 batches) | ~$2.50 | ~5-6 h | Publishable accuracy table for paper §C |
| bge-reranker-v2-m3 ablation | ~$3 (re-run) | ~5-6 h | Direct nDCG@10 lift evidence |
| **Lab Q1 EverMemBench + reranker total** | **~$6-7** | **~12-15 h** | Closes benchmark gap; reranker decision |

**Cost verdict: negligible. The blocker is implementation/test time, not budget. Authorize Phase 1 immediately upon OpenRouter key.**
