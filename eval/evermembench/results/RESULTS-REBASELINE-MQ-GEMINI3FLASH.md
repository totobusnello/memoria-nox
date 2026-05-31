# Wave 2 Phase 1.5 Re-baseline — Multi-Query Expansion (MQ) standalone on Gemini-3-flash backbone

**Status:** COMPLETE.

**Date:** 2026-05-31

**Branch / PR:** `wave-2/rebaseline-mq-gemini` / #TBD

**Verdict:** **NO REPLICATE (BORDERLINE) — BLOCK Tier 1 dispatch.** F_MH delta = **+1.21pp weighted** vs bare Gemini-3-flash (D70). The +1.5pp gate is **NOT met** and the 95% CI on MQ F_MH ([4.99, 9.48]) **fully overlaps** the D70 bare F_MH (6.02%). Closest to threshold of the three Wave 2 re-baselines, but still below gate and statistically indistinguishable from baseline.

## Methodology

| Param | Value |
|---|---|
| Bench | EverMemBench 5-batch sequential (n=3,121) |
| Batches | 004 / 005 / 010 / 011 / 016 (SAME as PR #419 + D70 backbone matrix + PR #423 R0) |
| Final-answer backbone | `gemini-3-flash-preview` (Gemini OpenAI-compat endpoint) |
| Embed | `gemini-embedding-001` (3072d) |
| Judge | `gemini-2.5-flash` (convention unchanged across PRs) |
| Retrieval mechanism | `NOX_MQ_ENABLED=1`, N=4 sub-queries, RRF k=60 (PR #385 config) |
| Decomposer | `gemini-2.5-flash-lite` (sub-query LLM) |
| Isolation | rerank=0, AC=0, IterB=0, IterC=0, MA-protection=0, KG path=0 |
| Top-k | 20 (harness final) |
| Adapter | `eval/evermembench/adapter_nox_mem.py` (Phase MQ mode) |
| Source DBs | Phase MQ winning DBs (PR #385) — chunks + vectors pre-populated |
| Pipeline.yaml | `pipeline-backbone-gemini3flash.yaml` (D70 canonical) |
| Wallclock | ~4,956s (~1h 23min) across 5 batches |

### Defensive preconditions (validated pre-dispatch)

- [x] `set -a; source /root/.openclaw/.env; set +a` before CLI
- [x] Preflight 1: `gemini-3-flash-preview` real 5-token chat completion (billing path)
- [x] Preflight 2: `gemini-2.5-flash-lite` real 5-token decomposer chat completion (billing path)
- [x] Preflight 3: `gemini-2.5-flash` real 5-token judge chat completion (billing path)
- [x] `NOX_DB_PATH` isolated to per-batch RUN_DIR (no prod DB touch)
- [x] `NOX_ALLOW_PROD_INGEST=1` defense flag set
- [x] tmux session for long-running op (per `[[long-running-batch-use-tmux]]`)
- [x] Vault-facts mode=active per-sub-query (decomposer fires ~4 sub-questions per main query, all hit vault-facts pipeline)
- [x] Decomposer producing semantically distinct sub-questions verified via api.log inspection (sample: 4 atomic sub-questions per main query, covering entity / action / temporal / deliverable)

## Results — 5-batch sequential

### Per-batch breakdown (Combined Major_Minor)

| Batch | n | Overall | F_HL | F_MH | F_SH | F_TP | MA_C | MA_P | MA_U | MA comp |
|---|---|---|---|---|---|---|---|---|---|---|
| 004 | 626 | 63.90% | 20.51% | 8.00% (4/50) | 83.67% | 41.67% | 81.00% | 91.00% | 89.66% | 87.22% |
| 005 | 610 | 61.31% | 22.67% | 4.00% (2/50) | 76.00% | 31.67% | 90.00% | 90.00% | 92.73% | 90.91% |
| 010 | 623 | 64.37% | 29.49% | 8.00% (4/50) | 72.00% | 36.67% | 89.00% | 87.00% | 89.66% | 88.55% |
| 011 | 633 | 63.98% | 33.33% | 8.00% (4/50) | 84.00% | 36.67% | 87.00% | 90.00% | 85.19% | 87.40% |
| 016 | 629 | 63.59% | 31.65% | 8.16% (4/49) | 81.25% | 28.33% | 90.00% | 93.00% | 88.71% | 90.57% |
| **Mean** | — | **63.43%** | **27.53%** | **7.23%** | **79.38%** | **35.00%** | **87.40%** | **90.20%** | **89.19%** | **88.93%** |
| **Stdev** | — | 1.22 | 5.65 | 1.81 | 5.22 | 5.14 | 3.78 | 2.17 | 2.70 | 1.73 |
| **95% CI** | — | [61.92, 64.94] | [20.52, 34.54] | **[4.99, 9.48]** | [72.90, 85.87] | [28.62, 41.38] | [82.71, 92.09] | [87.51, 92.89] | [85.84, 92.54] | [86.78, 91.08] |

F_MH weighted (Σcorrect / Σtotal = 18/249) = **7.23%** — identical to unweighted mean.

### Aggregate vs Bare Gemini-3-flash (D70, PR #397)

| Metric | Bare Gemini-3-flash (D70) | MQ re-baseline | Delta (weighted) | MQ 95% CI |
|---|---|---|---|---|
| Overall | 63.29% | 63.44% | **+0.15pp** | [61.92, 64.94] |
| F_HL | 26.02% | 27.53% | +1.51pp | [20.52, 34.54] |
| **F_MH** | **6.02%** | **7.23%** | **+1.21pp** | **[4.99, 9.48]** |
| F_SH | 80.18% | 79.38% | -0.80pp | [72.90, 85.87] |
| F_TP | 34.33% | 35.00% | +0.67pp | [28.62, 41.38] |
| MA_C | 89.20% | 87.40% | -1.80pp | [82.71, 92.09] |
| MA_P | 90.00% | 90.20% | +0.20pp | [87.51, 92.89] |
| MA_U | 86.09% | 89.19% | **+3.10pp** | [85.84, 92.54] |
| MA composite | 88.81% | 88.93% | +0.12pp | [86.78, 91.08] |

## Cross-baseline comparison

### Honest dual-baseline framing

| Baseline | MQ F_MH lift | MQ Overall lift | MQ MA composite |
|---|---|---|---|
| **gpt-4.1-mini Phase H v2** (PR #385, original CLEAN) | +3.61pp (3.21% → 6.82%) | -1.12pp (51.68% → 50.56%) | -1.38pp (73.34% → 71.97%) |
| **gemini-3-flash bare D70** (PR #397, this re-baseline) | +1.21pp (6.02% → 7.23%) | +0.15pp (63.29% → 63.44%) | +0.12pp (88.81% → 88.93%) |

**MQ mechanism is backbone-dependent for F_MH lift.** On gpt-4.1-mini the +3.61pp F_MH gain was the biggest single-knob lift to date. On Gemini-3-flash the same mechanism delivers only +1.21pp — ~34% of the gpt-4.1-mini lift, below the +1.5pp gate, statistically indistinguishable from baseline noise.

**Note: MQ does NOT regress MA composite on Gemini-3-flash** (+0.12pp) unlike gpt-4.1-mini (-1.38pp). The MA dim trade-off was an artifact of gpt-4.1-mini's prompt sensitivity to query dilution — Gemini-3-flash's larger context model is more robust to MQ's RRF union expansion.

### Comparison vs sibling Wave 2 re-baselines

| Mechanism (Gemini-3-flash) | F_MH lift | F_MH 95% CI | Gate verdict |
|---|---|---|---|
| KG path (PR #423 R0) | -0.01pp | [3.00, 9.04] | **FAIL — NO REPLICATE** |
| AC (companion PR) | +0.81pp | [4.62, 9.03] | **FAIL — NO REPLICATE** |
| **MQ (this PR)** | **+1.21pp** | **[4.99, 9.48]** | **FAIL (borderline) — NO REPLICATE** |
| ReAct IterB (PR #419) | +2.01pp | [3.51, 12.55] | **PASS — SHIP_OPT_IN** |

MQ is **closest to threshold** of the three retrieval/routing-stage Wave 2 re-baselines (KG / AC / MQ), but still below gate. **IterB remains the only validated F_MH lever on Gemini-3-flash backbone** as of 2026-05-31.

## Cost / wallclock

| Item | Value |
|---|---|
| Total questions | 3,121 |
| Per-batch wallclock | 1145s / 949s / 948s / 959s / 955s (mean ~991s) |
| Total wallclock | ~4,956s (~1h 23min, 5-batch sequential) |
| Answer latency p50 | ~4.64s/q (Gemini-3-flash + 4-way decomposition + per-sub-query retrieval + RRF) |
| Answer latency p95 | ~5.51s/q |
| Cost (estimated) | **~$6-7** (gemini-3-flash answer $3-4 + decomposer flash-lite $0.30 + judge $2-3) |
| Budget ceiling | $3 — OVERRUN (same pattern as R0 / AC / IterB) |
| Per-question cost | ~$0.002 |

Cost is estimated — answer_results JSON does not retain token usage. Decomposer cost is sub-linear (flash-lite at $0.0001/q × 3,121 ≈ $0.30).

## Gate verdict

**FAIL (borderline) — NO REPLICATE → BLOCK Tier 1 dispatch.**

- F_MH lift weighted = **+1.21pp** (target +1.5pp, miss by 0.29pp)
- F_MH lift unweighted = +1.21pp (identical to weighted)
- 95% CI on MQ F_MH = [4.99, 9.48] — **D70 bare F_MH (6.02%) is inside this CI**
- 4 of 5 batches show F_MH at 8.00-8.16% (all in same +2.00pp delta band); only batch 005 (4.00%) significantly below
- Lift signal is dominated by per-batch granularity: at n=50/batch, F_MH discretizes to 2pp increments — distinguishing +1.21pp from +1.5pp threshold requires more batches than 5

**Implication for composability matrix:** MQ is borderline NOT a usable F_MH lever on Gemini-3-flash backbone standalone. Tier 1 paralelo plan that built on MQ+X composability projections (IterB+MQ ≈ +5.62pp F_MH expected) needs to be **downgraded:** IterB+MQ ≈ IterB + ~+1pp ≈ ~+3pp at best.

## Honest framing — what we now know

1. **MQ F_MH lift is backbone-dependent.** Same decomposer, same RRF, same N=4 sub-queries — but Gemini-3-flash receives ~34% of the gpt-4.1-mini lift (+1.21pp vs +3.61pp).

2. **MA preservation flips backbone-positive.** On gpt-4.1-mini, MQ regressed MA composite -1.38pp (decomposition diluted profile/clarification queries). On Gemini-3-flash, MA composite is preserved (+0.12pp) — the larger backbone is more robust to query dilution. MA_U +3.10pp is the strongest single MA gain across Wave 2 mechanisms.

3. **F_HL +1.51pp is material.** Multi-query expansion helps hard-recall list questions almost as much as it helps multi-hop. This is consistent with the mechanism rationale (richer candidate pool → broader recall).

4. **Composability projection from D74 further refuted on Gemini-3-flash.** R0 KG (-0.01pp) + AC (+0.81pp) + MQ (+1.21pp) = sum +2.01pp ≪ pessimistic projection of +8.43pp. Even if all three were independent and additive (they are not), composability matrix tier 1 path is closed on this backbone.

5. **Strategic next-step recommendation:** Tier 1 IterB-stacking with single-stage retrieval knobs (AC/KG/MQ) is closed on Gemini-3-flash. Two paths remain viable for F_MH on Gemini-3-flash:
   - **Orchestration-stage capstone** (preferred given MQ borderline): stack IterB (ReAct) with Wave C triple (KG+MQ+MAP) and re-test composability via orchestration-layer composability rather than retrieval-layer. MQ's borderline result here suggests stacking could push into +2-3pp territory.
   - **Alternative mechanism family:** profile-chunk / HyDE / dense composition operating on the answer-stage rather than retrieval-stage. Generation-bound, matching D72's framing.

## Cross-references

- D70 backbone matrix Gemini-3-flash baseline: PR #397, `RESULTS-BACKBONE-MATRIX.json`
- Lab Q1 #3 MQ original (gpt-4.1-mini, +3.61pp F_MH lift): PR #385, `RESULTS-PHASEMQ-5BATCH.md`
- Wave 2 R0 KG path re-baseline (Gemini-3-flash, NO REPLICATE): PR #423, `RESULTS-R0-KGPATH-GEMINI3FLASH.md`
- Wave 2 AC re-baseline (companion PR, NO REPLICATE): PR #TBD, `RESULTS-REBASELINE-AC-GEMINI3FLASH.md`
- Q3 IterB Gemini POC (+2.01pp clean F_MH lift on same backbone): PR #419, `RESULTS-Q3-ITERB-POC.md`, `[[q3-iterB-fmh-ceiling-broken-2pp]]`
- D72 F_MH paradox resolution + D74 composability matrix plan: `docs/DECISIONS.md`

## Artifacts on disk

- VPS RUN_DIRs: `/root/.openclaw/evermembench-runs/r1-mq-gemini-{004,005,010,011,016}-*` (analysis.txt, eval.log, results-batch-*.json, answer-results-batch-*.json, search-results-batch-*.json, api.log, stream.log)
- Source DBs: Phase MQ DBs (PR #385) — unmodified during this run
- Workdir: `/root/.openclaw/wave-2-harvest-mq-*/` (symlinked to fresh clone)

## Lesson cravada

**`[[multi-query-backbone-dependent-no-replicate-gemini-3-flash]]`** — Multi-query expansion (PR #385) +3.61pp F_MH lift on gpt-4.1-mini (biggest single-knob retrieval lift on that backbone) does NOT replicate on Gemini-3-flash backbone (Wave 2 re-baseline measured +1.21pp, below +1.5pp gate, 95% CI fully overlaps D70 bare baseline). Same decomposer, same RRF, same N=4 sub-queries. **MA preservation flips backbone-positive on Gemini-3-flash** (+0.12pp vs gpt-4.1-mini's -1.38pp regression) — Gemini-3-flash robust to query-dilution side effects. **Reinforces [[kg-path-backbone-dependent-no-replicate-gemini-3-flash]] and [[adaptive-classifier-backbone-dependent-no-replicate-gemini-3-flash]] pattern** — retrieval-stage mechanisms that lift F_MH on gpt-4.1-mini do NOT automatically transfer to Gemini-3-flash. Single-knob retrieval lifts are backbone-conditional on EverMemBench-style dense corpora.
