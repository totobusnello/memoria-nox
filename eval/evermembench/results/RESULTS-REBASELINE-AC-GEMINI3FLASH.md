# Wave 2 Phase 1.5 Re-baseline — Adaptive Classifier (AC) standalone on Gemini-3-flash backbone

**Status:** COMPLETE.

**Date:** 2026-05-31

**Branch / PR:** `wave-2/rebaseline-ac-gemini` / #TBD

**Verdict:** **NO REPLICATE — BLOCK Tier 1 dispatch.** F_MH delta = **+0.81pp weighted** vs bare Gemini-3-flash (D70). The +1.5pp gate is **NOT met** and the 95% CI on AC F_MH ([4.62, 9.03]) **fully overlaps** the D70 bare F_MH (6.02%). Lift indistinguishable from sampling noise.

## Methodology

| Param | Value |
|---|---|
| Bench | EverMemBench 5-batch sequential (n=3,121) |
| Batches | 004 / 005 / 010 / 011 / 016 (SAME as PR #419 + D70 backbone matrix + PR #423 R0) |
| Final-answer backbone | `gemini-3-flash-preview` (Gemini OpenAI-compat endpoint) |
| Embed | `gemini-embedding-001` (3072d) |
| Judge | `gemini-2.5-flash` (convention unchanged across PRs) |
| Retrieval mechanism | `NOX_ADAPTIVE_CLASSIFIER=1`, threshold=5 (PR #381 CLEAN config) |
| Isolation | rerank=0, MQ=0, IterB=0, IterC=0, MA-protection=0, KG path=0 |
| Top-k | 20 (harness final) |
| Adapter | `eval/evermembench/adapter_nox_mem.py` (Phase AC mode) |
| Source DBs | Phase AC winning DBs (PR #381 CLEAN) — chunks + vectors pre-populated |
| Pipeline.yaml | `pipeline-backbone-gemini3flash.yaml` (D70 canonical) |
| Wallclock | ~5,187s (~1h 26min) across 5 batches |

### Defensive preconditions (validated pre-dispatch)

- [x] `set -a; source /root/.openclaw/.env; set +a` before CLI
- [x] Preflight 1: `gemini-3-flash-preview` real 5-token chat completion (billing path)
- [x] Preflight 2: `gemini-2.5-flash` real 5-token chat completion (judge billing path)
- [x] `NOX_DB_PATH` isolated to per-batch RUN_DIR (no prod DB touch)
- [x] `NOX_ALLOW_PROD_INGEST=1` defense flag set
- [x] tmux session for long-running op (per `[[long-running-batch-use-tmux]]`)
- [x] Vault-facts mode=active on 100% of queries
- [x] Adaptive classifier routing audit (sample batch 004): 275 multi_hop / 351 factual → activation **43.9%** (within target band 30-60%, matching PR #381 v1.0 activation of 44.2%)

## Results — 5-batch sequential

### Per-batch breakdown (Combined Major_Minor)

| Batch | n | Overall | F_HL | F_MH | F_SH | F_TP | MA_C | MA_P | MA_U | MA comp |
|---|---|---|---|---|---|---|---|---|---|---|
| 004 | 626 | 62.46% | 20.51% | 8.00% (4/50) | 85.71% | 30.00% | 85.00% | 89.00% | 82.76% | 85.59% |
| 005 | 610 | 61.15% | 21.33% | 4.00% (2/50) | 76.00% | 31.67% | 90.00% | 90.00% | 92.73% | 90.91% |
| 010 | 623 | 65.65% | 28.21% | 8.00% (4/50) | 72.00% | 36.67% | 91.00% | 91.00% | 89.66% | 90.55% |
| 011 | 633 | 64.14% | 34.62% | 8.00% (4/50) | 84.00% | 36.67% | 87.00% | 90.00% | 85.19% | 87.40% |
| 016 | 629 | 62.80% | 34.18% | 6.12% (3/49) | 77.08% | 33.33% | 85.00% | 92.00% | 88.71% | 88.57% |
| **Mean** | — | **63.24%** | **27.77%** | **6.82%** | **78.96%** | **33.67%** | **87.60%** | **90.40%** | **87.81%** | **88.60%** |
| **Stdev** | — | 1.71 | 6.74 | 1.78 | 5.74 | 2.98 | 2.79 | 1.14 | 3.89 | 2.22 |
| **95% CI** | — | [61.11, 65.37] | [19.39, 36.15] | **[4.62, 9.03]** | [71.83, 86.08] | [29.97, 37.37] | [84.13, 91.07] | [88.98, 91.82] | [82.97, 92.65] | [85.85, 91.36] |

F_MH weighted (Σcorrect / Σtotal = 17/249) = **6.83%** — essentially equal to unweighted mean (6.82%).

### Aggregate vs Bare Gemini-3-flash (D70, PR #397)

| Metric | Bare Gemini-3-flash (D70) | AC re-baseline | Delta (weighted) | AC 95% CI |
|---|---|---|---|---|
| Overall | 63.29% | 63.25% | **-0.04pp** | [61.11, 65.37] |
| F_HL | 26.02% | 27.77% | +1.75pp | [19.39, 36.15] |
| **F_MH** | **6.02%** | **6.83%** | **+0.81pp** | **[4.62, 9.03]** |
| F_SH | 80.18% | 78.96% | -1.22pp | [71.83, 86.08] |
| F_TP | 34.33% | 33.67% | -0.66pp | [29.97, 37.37] |
| MA_C | 89.20% | 87.60% | -1.60pp | [84.13, 91.07] |
| MA_P | 90.00% | 90.40% | +0.40pp | [88.98, 91.82] |
| MA_U | 86.09% | 87.81% | +1.72pp | [82.97, 92.65] |
| MA composite | 88.81% | 88.60% | -0.21pp | [85.85, 91.36] |

## Cross-baseline comparison

### Honest dual-baseline framing

| Baseline | AC F_MH lift | AC Overall lift | AC MA composite |
|---|---|---|---|
| **gpt-4.1-mini Phase H v2** (PR #381 v1.0, CLEAN reference) | +2.01pp (3.21% → 5.22%) | -0.47pp (51.68% → 51.21%) | -1.63pp (73.34% → 71.72%) |
| **gemini-3-flash bare D70** (PR #397, this re-baseline) | +0.81pp (6.02% → 6.83%) | -0.04pp (63.29% → 63.25%) | -0.21pp (88.81% → 88.60%) |

**AC mechanism is backbone-dependent for F_MH lift.** On gpt-4.1-mini the +2.01pp F_MH gain just barely cleared the bench-conventional +1.5pp gate. On Gemini-3-flash the same mechanism delivers only +0.81pp — below threshold, statistically indistinguishable from baseline noise (95% CI [4.62, 9.03] fully contains 6.02%).

### Comparison vs sibling R0 KG path (PR #423)

| Mechanism (Gemini-3-flash) | F_MH lift | F_MH 95% CI | Gate verdict |
|---|---|---|---|
| KG path (PR #423 R0) | -0.01pp | [3.00, 9.04] | **FAIL — NO REPLICATE** |
| **Adaptive classifier (this PR)** | **+0.81pp** | **[4.62, 9.03]** | **FAIL — NO REPLICATE** |
| MQ (companion PR) | +1.21pp | [4.99, 9.48] | FAIL (borderline) |
| ReAct IterB (PR #419) | +2.01pp | [3.51, 12.55] | PASS — SHIP_OPT_IN |

**IterB remains the only validated F_MH lever on Gemini-3-flash backbone** as of 2026-05-31.

## Cost / wallclock

| Item | Value |
|---|---|
| Total questions | 3,121 |
| Per-batch wallclock | 1341s / 607s / 1356s / 586s / 1295s (mean ~1037s) |
| Total wallclock | ~5,187s (~1h 26min, 5-batch sequential) |
| Answer latency p50 | ~4.65s/q (Gemini-3-flash + AC routing + retrieval) |
| Answer latency p95 | ~5.50s/q |
| Cost (estimated) | **~$6-7** (gemini-3-flash answer $3-4 + gemini-2.5-flash judge $2-3) |
| Budget ceiling | $3 — OVERRUN (same pattern as R0 / IterB; Gemini-3-flash uses more output tokens than gpt-4.1-mini) |
| Per-question cost | ~$0.002 |

Cost is estimated — answer_results JSON does not retain token usage. Estimate calibrated from PR #423 R0 cost analysis (homogeneous Gemini pipeline).

## Gate verdict

**FAIL — NO REPLICATE → BLOCK Tier 1 dispatch.**

- F_MH lift weighted = **+0.81pp** (target +1.5pp)
- F_MH lift unweighted = +0.80pp
- 95% CI on AC F_MH = [4.62, 9.03] — **D70 bare F_MH (6.02%) is inside this CI**
- 4 of 5 batches show F_MH at or below the D70 baseline (004 +1.99pp, 005 -2.02pp, 010 +1.99pp, 011 +1.99pp, 016 +0.10pp)
- Lift signal is dominated by 3 batches at 8.00% (4/50) vs random noise — the n=50 per-batch granularity caps any single-batch F_MH delta at ±2pp increments

**Implication for composability matrix:** Adaptive classifier is NOT a usable F_MH lever on Gemini-3-flash backbone. Tier 1 paralelo plan that built on AC+X composability projections (IterB+AC ≈ +4pp F_MH expected) needs to be **downgraded:** IterB+AC ≈ IterB alone ≈ +2.01pp.

## Honest framing — what we now know

1. **AC F_MH lift is backbone-dependent.** Same DB, same classifier, same routing (43.9% activation matches PR #381 within 0.3pp) — but Gemini-3-flash receives ~40% of the gpt-4.1-mini lift (+0.81pp vs +2.01pp).

2. **MA composite preserved (-0.21pp).** The classifier successfully avoids the MA dim regression seen in single-mode rerank/MQ. MA_P (+0.40pp) and MA_U (+1.72pp) gains validate that routing decisions add useful context for memory-awareness — but at zero net F_MH benefit on this backbone.

3. **F_HL +1.75pp is the only material gain.** Adaptive routing helps hard-recall list questions slightly more than it helps multi-hop — consistent with PR #381's observation that classifier shifts top-k toward broader recall in multi-hop mode.

4. **Composability projection from D74 further refuted on Gemini-3-flash.** R0 KG path -0.01pp + AC +0.81pp = sum +0.80pp ≪ pessimistic projection of +4.82pp (KG +2.81pp + AC +2.01pp). Composability matrix tier 1 path is closed on this backbone.

5. **Strategic next-step recommendation:** Tier 1 IterB-stacking with single-stage retrieval knobs (AC/KG/MQ) is closed on Gemini-3-flash. Two paths remain viable for F_MH on Gemini-3-flash:
   - **Orchestration-stage capstone:** stack IterB (ReAct) with Wave C triple (KG+MQ+MAP) and re-test composability via orchestration-layer composability rather than retrieval-layer composability.
   - **Alternative mechanism family:** profile-chunk / HyDE / dense composition operating on the answer-stage rather than retrieval-stage. These are generation-bound, not retrieval-bound — matching D72's framing that EverMemBench F_MH ceiling is structural on dense corpora.

## Cross-references

- D70 backbone matrix Gemini-3-flash baseline: PR #397, `RESULTS-BACKBONE-MATRIX.json`
- Lab Q1 #1 AC CLEAN original (gpt-4.1-mini, +2.01pp F_MH lift): PR #381, `RESULTS-PHASEAC-CLEAN.md`
- Wave 2 R0 KG path re-baseline (Gemini-3-flash, NO REPLICATE): PR #423, `RESULTS-R0-KGPATH-GEMINI3FLASH.md`
- Q3 IterB Gemini POC (+2.01pp clean F_MH lift on same backbone): PR #419, `RESULTS-Q3-ITERB-POC.md`, `[[q3-iterB-fmh-ceiling-broken-2pp]]`
- Companion MQ re-baseline PR: PR #TBD (`RESULTS-REBASELINE-MQ-GEMINI3FLASH.md`)
- D72 F_MH paradox resolution + D74 composability matrix plan: `docs/DECISIONS.md`

## Artifacts on disk

- VPS RUN_DIRs: `/root/.openclaw/evermembench-runs/rebaseline-ac-gemini-{004,005,010,011,016}-*` (analysis.txt, eval.log, results-batch-*.json, answer-results-batch-*.json, search-results-batch-*.json, routing-audit.txt, api.log, stream.log)
- Source DBs: Phase AC CLEAN DBs (PR #381) — unmodified during this run
- Workdir: `/root/.openclaw/wave-2-harvest-ac-773debcb/` (symlinked to fresh clone)

## Lesson cravada

**`[[adaptive-classifier-backbone-dependent-no-replicate-gemini-3-flash]]`** — Adaptive query classifier (PR #381) +2.01pp F_MH lift on gpt-4.1-mini does NOT replicate on Gemini-3-flash backbone (Wave 2 re-baseline measured +0.81pp, below +1.5pp gate, 95% CI fully overlaps D70 bare baseline). Same DB, same classifier code, same threshold=5, same activation rate (43.9% vs 44.2%). Routing-stage mechanisms that select per-query top-k or rerank application are NOT backbone-invariant on EverMemBench-style dense corpora. **Reinforces [[kg-path-backbone-dependent-no-replicate-gemini-3-flash]] pattern** — single-knob lifts that work on gpt-4.1-mini do NOT automatically transfer to Gemini-3-flash. Wave 2 composability projections built on AC+X must be downgraded.
