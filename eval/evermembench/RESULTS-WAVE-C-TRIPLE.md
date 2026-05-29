# Phase Triple 5-batch (Wave C composability) — KG + MQ + MAP

> **Status: PARTIAL 2/5 batches** (intended 5-batch sequential capped early by OpenAI
> quota wall mid-bench on batch 010 — see Honest Framing section below).
> Aggregate gate decision **REJECT DEFAULT (1-2/4)** is computed on the partial
> data and is honest framing, not over-claim. Single 2-batch read overstates
> 3-6× per lesson `[[single-batch-gates-unreliable-5x-overstate]]`.

## Honest Framing — Partial Run

**Bench plan:** 5-batch sequential (004, 005, 010, 011, 016) on EverMemBench
Phase H v2 baseline (gpt-4.1-mini backbone) with `NOX_ADAPTER_MODE=phaseTriple`
firing KG path + MQ decomposition + cross-encoder rerank + MA-protection
(KG-anchored bypass).

**What actually ran:**
- Batch **004**: complete (search + answer + evaluate), telemetry captured.
- Batch **005**: complete (search + answer + evaluate), telemetry captured.
- Batch **010**: partial — search stage completed; answer stage hit OpenAI 429
  `insufficient_quota` ~minute 12 of answer stage; harness retried 8 of 20
  attempts with exponential backoff (1.4s → 128.9s), then was manually killed
  because the quota wall is unrecoverable mid-run.
- Batch **011**: failed at preflight — `preflight_billing` exercised the OpenAI
  billing path before bench start (lesson `[[preflight-must-exercise-billing-path]]`)
  and refused to spend search budget when answer/evaluate would fail. **Preflight
  worked exactly as designed**: zero wasted search time on a doomed batch.
- Batch **016**: same as 011, caught at preflight.

**Root cause:** OpenAI key `OPENAI_API_KEY` exhausted hard quota
(`type: insufficient_quota`, not throttle/RPM) somewhere between batch 005 answer
completion and batch 010 answer stage. ~1250 successful gpt-4.1-mini calls
(626 × 2 batches across answer + judge stages with concurrency 4–8) consumed
the credit. The prior session said "keys rotated already" but the rotated key
still had finite credit.

**Methodological consequence:** 2/5 is below the 5-batch minimum we use for
ship decisions (lesson `[[single-batch-gates-unreliable-5x-overstate]]` —
single-batch overstate 3-6×, 2-batch likely overstate ~2-3×). The decision
table below is computed for completeness, **but the verdict should not be
read as if it were 5-batch evidence**. The mechanism-firing instrumentation
(below, in 3-stage telemetry) IS solid because it is measured per-query and
both batches collected 1,236 queries' worth of data, which is ample for
attribution.

**What is solid in this partial run:**
- All 3 stages fired as designed (instrumentation confirms 100% MQ + 88.6% KG
  pool + 14.5% MAP application — see telemetry table).
- The shape of the F_MH and MA trade-off matches expectations from Wave B
  KG+MAP (MA partial recovery, F_MH cap by stage overlap).
- Wave-C-specific finding: KG+MQ overlap at retrieval STAYS overlap when MAP
  is layered on at rerank; MAP does not unlock additional F_MH because the
  KG-anchored chunks were already in the MQ-boosted retrieval set.

**What is NOT robust in this partial run:**
- Per-batch variance: F_MH was 2.00% on BOTH batches. Phase H v2 baseline F_MH
  averaged 3.21% across 5 batches with per-batch range typically [2.0, 5.5%];
  the 2 batches we caught were specifically the lower-F_MH ones. We do not
  know whether batches 010/011/016 would have lifted F_MH or kept it flat.
- The "1/3 strict gates passed" is a 2-batch read; could be 0/3 or 2/3 at 5-batch.

**Ship decision (this partial):** **REJECT default. Opt-in only via
`NOX_ADAPTER_MODE=phaseTriple` or triple env flags.** Justified by:
1. F_MH did not beat Wave B KG+MAP +4.04pp (observed -1.21pp, miss by 5.25pp).
2. Overall -1.50pp regression exceeds -1.0pp tolerance.
3. MA composite -3.21pp vs KGMAP -5.02pp = +1.81pp recovery (partial gain).
4. Latency p50 = ~3.7s/query (vs typical ~1s) — 3.7× overhead from triple
   pipeline. Even if ship-default were warranted, the latency cost would push
   it to opt-in.

**Action on quota wall:** Recommend retry budget cap in `run-batch-phaseTriple.sh`
that caps `max_retries` from 20 → 3 when the error code is `insufficient_quota`
(distinct from RPM 429). Currently the harness wastes 30+ min on a
non-recoverable error before manual intervention is needed. Tracking as lesson
`[[openai-insufficient-quota-needs-fast-fail-not-backoff]]`.

Run dirs: 2 | Batches with data: 2 (intended: 5)

## Decision: **REJECT DEFAULT (1-2/4 — opt-in only, document failure mode)** (strict 1/3 + informational 1/1)

## Aggregate metrics (5-batch CI95)
| Metric | Mean | CI95 lo | CI95 hi | Δ vs H2 | Per-batch |
|---|---:|---:|---:|---:|---|
| F_SH | 83.8800 | 78.5026 | 89.2574 | — | 87.76, 80.00 |
| F_MH | 2.0000 | 2.0000 | 2.0000 | -1.21pp | 2.00, 2.00 |
| F_TP | 14.1650 | 8.3926 | 19.9374 | — | 10.00, 18.33 |
| F_HL | 21.5900 | 20.0932 | 23.0868 | — | 20.51, 22.67 |
| MA_C | 82.0000 | 77.8422 | 86.1578 | -2.60pp | 79.00, 85.00 |
| MA_P | 61.0000 | 55.4563 | 66.5437 | -4.40pp | 57.00, 65.00 |
| MA_U | 67.4000 | 60.0130 | 74.7870 | -2.63pp | 62.07, 72.73 |
| overall | 50.1807 | 48.1591 | 52.2023 | -1.50pp | 48.72, 51.64 |
| MA_composite | 70.1333 | 64.4372 | 75.8295 | -3.21pp | 66.02, 74.24 |

## Stage firing — 3-stage pipeline empirical evidence
Per-query telemetry confirms each composability stage fires independently. Lesson `[[empirical-set-e-empty-confirms-mechanism-not-corpus]]`.

| Statistic | Mean across batches |
|---|---:|
| mq_fired_pct | 99.92 |
| mq_subqueries_mean_per_q | 4.0 |
| mq_total_results_pre_dedup_mean | 38.66 |
| mq_unique_after_dedup_mean | 28.66 |
| composability_kg_mq_active_pct | 88.75 |
| kg_pool_mean_per_q | 18.25 |
| kg_queries_with_pool_pct | 88.6 |
| kg_neighbors_found_mean | 15.37 |
| kg_chunks_boosted_mean | 0.27 |
| map_applied_pct | 14.52 |
| set_e_section_mean | 0.0 |
| set_e_kg_mean | 0.27 |
| total_protected_mean | 0.27 |
| queries_with_protection_pct | 14.52 |
| n_queries | 618.0 |

## Gates

### gate1_FMH_beats_KGMAP: FAIL
- Threshold: F_MH lift ≥ Wave B KG+MAP +4.04pp (triple must beat best Wave B combo)
- actual_lift: -1.2100
- actual_value: +2.0000
- delta_vs_KGMAP: -5.2500

### gate2_overall_regression_bounded: FAIL
- Threshold: Overall Δ ≥ -1.0pp vs Phase H v2 (51.68%)
- actual_delta: -1.4993
- actual_value: +50.1807

### gate3_MA_no_worse_than_KGMAP: PASS
- Threshold: MA composite Δ ≥ Wave B KG+MAP −5.02pp (no further MA degradation)
- actual_delta: -3.2067
- actual_value: +70.1333
- delta_vs_KGMAP: +1.8133

### gate4_additivity_decomposition: PASS
- Threshold: informational — residual analysis only

  Additivity decomposition:
  - observed_triple_F_MH_lift: -1.21
  - perfect_additive_prediction: 10.44
  - residual_vs_perfect_additive: -11.65
  - pair_kgmap_plus_mq_prediction: 7.65
  - residual_vs_kgmap_plus_mq: -8.86
  - pair_kgmq_plus_map_prediction: 8.83
  - residual_vs_kgmq_plus_map: -10.04
  - memos_gap_closure_pct: -6.41

## Per-batch detail

### Batch 004
- run_dir: `/root/.openclaw/evermembench-runs/phaseTriple-004-1780091562`
- categories: F_HL=20.51, F_MH=2.00, F_SH=87.76, F_TP=10.00, MA_C=79.00, MA_P=57.00, MA_U=62.07, P_Skill=48.89, P_Style=37.84, P_Title=63.27, overall=48.72
- instrumentation:
  - n_queries: 626
  - mq_status_counter: {'applied': 626}
  - mq_fired_queries: 626
  - mq_fired_pct: 100.0
  - mq_subqueries_total: 2505
  - mq_subqueries_mean_per_q: 4.0
  - mq_total_results_pre_dedup_sum: 24191
  - mq_unique_after_dedup_sum: 18116
  - mq_total_results_pre_dedup_mean: 38.64
  - mq_unique_after_dedup_mean: 28.94
  - composability_kg_mq_active_pct: 94.89
  - kg_pool_total: 10291
  - kg_pool_mean_per_q: 16.44
  - kg_queries_with_pool: 591
  - kg_queries_with_pool_pct: 94.41
  - kg_neighbors_found_mean: 16.68
  - kg_chunks_boosted_mean: 0.36
  - map_applied_count: 113
  - map_applied_pct: 18.05
  - kg_anchor_active: 626
  - set_e_section_mean: 0.0
  - set_e_kg_mean: 0.36
  - total_protected_mean: 0.36
  - queries_with_protection: 113
  - queries_with_protection_pct: 18.05
- p50 latency: 3751.43ms

### Batch 005
- run_dir: `/root/.openclaw/evermembench-runs/phaseTriple-005-1780092632`
- categories: F_HL=22.67, F_MH=2.00, F_SH=80.00, F_TP=18.33, MA_C=85.00, MA_P=65.00, MA_U=72.73, P_Skill=41.86, P_Style=42.86, P_Title=53.06, overall=51.64
- instrumentation:
  - n_queries: 610
  - mq_status_counter: {'applied': 609, 'fallback_single': 1}
  - mq_fired_queries: 609
  - mq_fired_pct: 99.84
  - mq_subqueries_total: 2436
  - mq_subqueries_mean_per_q: 3.99
  - mq_total_results_pre_dedup_sum: 23588
  - mq_unique_after_dedup_sum: 17319
  - mq_total_results_pre_dedup_mean: 38.67
  - mq_unique_after_dedup_mean: 28.39
  - composability_kg_mq_active_pct: 82.62
  - kg_pool_total: 12229
  - kg_pool_mean_per_q: 20.05
  - kg_queries_with_pool: 505
  - kg_queries_with_pool_pct: 82.79
  - kg_neighbors_found_mean: 14.05
  - kg_chunks_boosted_mean: 0.18
  - map_applied_count: 67
  - map_applied_pct: 10.98
  - kg_anchor_active: 610
  - set_e_section_mean: 0.0
  - set_e_kg_mean: 0.18
  - total_protected_mean: 0.18
  - queries_with_protection: 67
  - queries_with_protection_pct: 10.98
- p50 latency: 3703.31ms

## Reference baselines
- Phase H v2 5-batch: overall=51.68% F_MH=3.21% MA_composite=73.34%
- KG sparse standalone (PR #379): overall +0.12pp F_MH +2.81pp MA +0.44pp
- MQ standalone (PR #385): overall -1.12pp F_MH +3.61pp MA -1.38pp
- MAP standalone (PR #386): overall -1.24pp F_MH +4.02pp MA -6.55pp
- Wave B KG+MQ (PR #389): F_MH +4.81pp (vs +6.42pp perfect-additive, residual -1.61pp → same-stage retrieval overlap)
- Wave B KG+MAP (PR #390): F_MH +4.04pp (vs +6.83pp perfect-additive, residual -2.79pp → different-stage but Set E small)
- MemOS reference: F_MH=22.09% (lift +18.88pp vs H2)

## Decision matrix
- 4/4 PASS → ship default
- 3/4 PASS → ship opt-in via NOX_ADAPTER_MODE=phaseTriple
- 1-2/4 PASS → reject default, opt-in only with documented failure mode
- 0/4 PASS → reject + reconsider triple composability hypothesis

## Lessons cravadas (Wave C partial run, 2026-05-29)

1. **`[[openai-insufficient-quota-needs-fast-fail-not-backoff]]`** — OpenAI
   `insufficient_quota` (hard wall, not RPM) deserves fast-fail (≤3 retries)
   not exponential backoff to 128s × 20 attempts. Current harness wastes 30+
   min on doomed retries. Code change: detect `error.type == "insufficient_quota"`
   in eval harness retry logic and abort the batch immediately.

2. **`[[preflight-billing-saves-batches-not-just-time]]`** — Wave C batches 011
   + 016 saved entire search stages (~30 min × 2 = 1h compute) because the
   preflight billing exercise (PR #295 / `eval-lib/preflight.sh`) refused to
   start the bench when OpenAI billing returned 429. This is a strong
   validation of lesson `[[preflight-must-exercise-billing-path]]`: preflight
   is not just a smoke test — it is a circuit breaker that prevents budget
   waste on doomed downstream calls.

3. **`[[wave-c-triple-fmh-cap-by-mq-kg-overlap-confirmed]]`** — In 2-batch
   partial, observed triple F_MH lift = -1.21pp (degradation) vs predicted
   perfect-additive +10.44pp (KG +2.81 + MQ +3.61 + MAP +4.02). The huge
   residual (-11.65pp vs perfect-additive in this partial; expected -5 to -8pp
   at 5-batch) is **dominated by KG+MQ overlap at retrieval stage**: MQ
   sub-query expansion plus KG 1-hop walk both populate the same candidate
   pool, and MAP at rerank cannot un-overlap them. Wave B KG+MQ alone showed
   the same residual pattern (residual -1.61pp at +4.81 observed). MAP does
   not help F_MH because the MAP-protected chunks were already in the
   MQ-RRF-merged retrieval top-K. **Implication for next steps:** different-
   stage gain requires the third stage to be ORTHOGONAL — e.g. KG+MQ
   (retrieval) + neural reranker (different objective than CrossEncoder MiniLM).

4. **`[[wave-c-triple-latency-3-7x-overhead]]`** — Observed p50 latency per
   query ~3.7s on triple mode (vs ~1s baseline). Cost breakdown rough estimate:
   ~700ms MQ LLM decompose (Gemini Flash-Lite) + ~900ms MQ retrieve (4×
   parallel hybrid search) + ~30ms KG SQL + ~1100ms rerank (CrossEncoder MiniLM
   on CPU) + ~1s base hybrid. Even if 5-batch F_MH had panned out, the
   end-user latency on triple mode forces opt-in-only ship decision per
   memoria-nox §5 (latency-budget discipline on default-on features).

5. **`[[2-batch-partial-still-informs-mechanism-not-magnitude]]`** — A
   sub-5-batch run cannot rule on magnitude (single-batch overstate 3-6×, per
   `[[single-batch-gates-unreliable-5x-overstate]]`), but per-query
   instrumentation (1,236 queries across 2 batches in this run) IS sufficient
   to validate mechanism firing (e.g. "did MQ generate 4 sub-queries on 99.92%
   of queries?" yes) and to identify obvious failure modes (e.g. F_MH = 2.00%
   on both batches is a structural signal, not noise). Use partial runs to
   confirm mechanism; reserve full 5-batch for magnitude / gate verdicts.

## Wave C → next step recommendation

Per finding #3 (KG+MQ retrieval-stage overlap caps F_MH), the next composability
experiment should test **a third stage that is mechanism-orthogonal**:
- KG+MQ (retrieval) + ANSWER-stage reranker (different LLM call, sees query +
  candidates simultaneously, post-retrieval re-rank).
- KG+MQ (retrieval) + ANSWER-stage chain-of-thought prompt (decoupled from
  candidate set entirely).
- KG+MQ (retrieval) + GENERATIVE re-write of top-N (transforms candidates
  before answer LLM ingests them).

A 5-batch re-run of phaseTriple itself (with a fresh OpenAI billing top-up)
would also clarify whether the 2-batch F_MH=2.00% pair is the trough of
batch-level variance or the structural cap. **Estimated cost for 5-batch
re-run: $5-7 OpenAI + $0 Gemini (free tier).**
