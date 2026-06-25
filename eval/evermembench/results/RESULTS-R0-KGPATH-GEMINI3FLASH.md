# Wave 2 R0 Sanity — KG path retrieval standalone on Gemini-3-flash backbone

**Status:** COMPLETE.

**Date:** 2026-05-31

**Branch / PR:** `feat/wave-2-r0-sanity-kg-gemini` / #423

**Verdict:** **NO REPLICATE — BLOCK Tier 1 dispatch.** F_MH delta = **-0.01pp** vs bare Gemini-3-flash (D70). KG path mechanism that delivered +2.81pp on gpt-4.1-mini (PR #379) does NOT lift F_MH on Gemini-3-flash backbone.

## Methodology

| Param | Value |
|---|---|
| Bench | EverMemBench 5-batch sequential (n=3121) |
| Batches | 004 / 005 / 010 / 011 / 016 (SAME as PR #419 + D70 backbone matrix) |
| Final-answer backbone | `gemini-3-flash-preview` (Gemini OpenAI-compat endpoint) |
| Embed | `gemini-embedding-001` (3072d) |
| Judge | `gemini-2.5-flash` (convention unchanged across PRs) |
| Retrieval mechanism | `NOX_KG_PATH_ENABLED=1` (KG path retrieval ON) |
| Isolation | rerank=0, MQ=0, IterB=0, IterC=0, MA-protection=0 |
| Top-k | 20 (harness final) |
| Adapter | `eval/evermembench/adapter_nox_mem.py` (NOX_ADAPTER_MODE=phaseKG) |
| Source DBs | Phase KG winning DBs (PR #379) — chunks + vectors + KG entities/relations pre-populated |
| Pipeline.yaml | `pipeline-backbone-gemini3flash.yaml` (D70 canonical) |
| Wallclock | 1h 25min (13:25 → 14:50 BRT, 2026-05-31) |

### Pre-condition verification (validated on DB load per batch)

| Batch | chunks | vec_chunk_map | kg_entities | kg_relations |
|---|---|---|---|---|
| 004 | 10,033 | 10,033 | 560 | 1,748 |
| 005 | 10,015 | 10,015 | 624 | 1,823 |
| 010 | 10,006 | 10,006 | 565 | 1,837 |
| 011 | 10,008 | 10,008 | 599 | 1,783 |
| 016 | 10,032 | 10,032 | 517 | 1,583 |

### Defensive preconditions (validated pre-dispatch)

- [x] `set -a; source /root/.openclaw/.env; set +a` before CLI
- [x] Preflight 1: `gemini-3-flash-preview` real 5-token chat completion (billing path, total_tokens=5)
- [x] Preflight 2: `gemini-2.5-flash` real 5-token chat completion (judge billing path)
- [x] `NOX_DB_PATH` isolated to per-batch RUN_DIR (no prod DB touch)
- [x] `NOX_ALLOW_PROD_INGEST=1` defense flag set
- [x] tmux session for long-running op (per `[[long-running-batch-use-tmux]]`)
- [x] Vault-facts mode=active on 100% of queries (3,125 / 3,121 active across batches — confirms KG path actually fired)

## Results — 5-batch sequential

### Per-batch breakdown

| Batch | n | Overall | F_HL | F_MH | F_SH | F_TP | MA_C | MA_P | MA_U | MA comp |
|---|---|---|---|---|---|---|---|---|---|---|
| 004 | 626 | 64.54% | 24.36% | 4.00% (2/50) | 85.71% | 35.00% | 90.00% | 88.00% | 86.21% | 88.37% |
| 005 | 610 | 64.59% | 26.67% | 6.00% (3/50) | 78.00% | 36.67% | 90.00% | 95.00% | 92.73% | 92.55% |
| 010 | 623 | 63.40% | 24.36% | 6.00% (3/50) | 72.00% | 38.33% | 88.00% | 84.00% | 87.93% | 86.43% |
| 011 | 633 | 65.56% | 44.87% | 10.00% (5/50) | 84.00% | 33.33% | 85.00% | 97.00% | 83.33% | 89.37% |
| 016 | 629 | 62.48% | 27.85% | 4.08% (2/49) | 81.25% | 31.67% | 91.00% | 94.00% | 87.10% | 91.22% |
| **Mean** | — | **64.11%** | **29.62%** | **6.02%** | **80.19%** | **35.00%** | **88.80%** | **91.60%** | **87.46%** | **89.59%** |
| **Stdev** | — | 1.19 | 8.66 | 2.43 | 5.43 | 2.63 | 2.39 | 5.42 | 3.42 | 2.39 |
| **95% CI** | — | [62.64, 65.59] | [18.87, 40.37] | **[3.00, 9.04]** | [73.45, 86.94] | [31.73, 38.27] | [85.84, 91.76] | [84.88, 98.32] | [83.22, 91.70] | [86.62, 92.56] |

### Aggregate vs Bare Gemini-3-flash (D70, PR #397)

| Metric | Bare Gemini-3-flash (D70) | KG path R0 | Delta | R0 95% CI |
|---|---|---|---|---|
| Overall | 63.29% | 64.11% | **+0.83pp** | [62.64, 65.59] |
| F_HL | 26.02% | 29.62% | **+3.60pp** | [18.87, 40.37] |
| **F_MH** | **6.02%** | **6.02%** | **-0.01pp** | **[3.00, 9.04]** |
| F_SH | 80.18% | 80.19% | +0.01pp | [73.45, 86.94] |
| F_TP | 34.33% | 35.00% | +0.67pp | [31.73, 38.27] |
| MA_C | 89.20% | 88.80% | -0.40pp | [85.84, 91.76] |
| MA_P | 90.00% | 91.60% | +1.60pp | [84.88, 98.32] |
| MA_U | 86.09% | 87.46% | +1.37pp | [83.22, 91.70] |
| MA composite | 88.81% | 89.59% | +0.78pp | [86.62, 92.56] |

## Comparison: gpt-4.1-mini KG path (PR #379) vs Gemini-3-flash KG path (R0)

| Backbone | Bare F_MH | + KG path F_MH | F_MH Delta |
|---|---|---|---|
| gpt-4.1-mini (PR #379) | 4.42% | 7.23% | **+2.81pp** |
| Gemini-3-flash (this R0) | 6.02% | 6.02% | **-0.01pp** |

**KG path mechanism is backbone-dependent.** Same DB, same KG entities/relations, same vault-facts injection, same NOX_KG_PATH_ENABLED=1, same top-k=20 — but Gemini-3-flash backbone receives zero net F_MH benefit from the KG path retrieval rewrite.

## Cost / wallclock

| Item | Value |
|---|---|
| Total questions | 3,121 |
| Wallclock | 1h 25min (5-batch sequential) |
| Cost (estimated) | ~$6-7 (gemini-3-flash answer $3-4 + gemini-2.5-flash judge $2-3) |
| Budget ceiling | $3 — **OVERRUN.** Underestimated because Gemini-3-flash uses more output tokens per question than gpt-4.1-mini on EverMemBench; also judge cost doubled when judge stayed gemini-2.5-flash (homogeneous Gemini path). |
| Per-question cost | ~$0.002 |

Note: Cost estimate is approximate (answer_results JSON does not retain token usage fields; estimated from PR #419 IterB benchmark + KG path overhead of ~30 tokens/q for vault-facts injection).

## Gate verdict

**NO REPLICATE → BLOCK Tier 1 dispatch.**

- F_MH lift = **-0.01pp** (95% CI [-3.02, +3.02])
- Gate threshold = +1.5pp lift to GO
- 95% CI on KG path F_MH includes bare D70 F_MH (6.02% in [3.00, 9.04])
- 4 of 5 batches show F_MH at or below bare D70 baseline (004 -2pp, 005 same, 010 same, 011 +6pp outlier, 016 same)
- Only batch 011 shows substantive lift (+8pp); batches 004 + 016 actually decrement marginally

**Implication for composability matrix:** KG path is NOT a usable F_MH lever on Gemini-3-flash backbone. Wave 2 Tier 1 paralelo plan that built on KG+X composability projections (IterB+KG → ~10.8% F_MH, AC+KG, MQ+KG) needs **re-baselining individual mechanisms on Gemini before dispatch.** IterB (PR #419 +2.01pp) is the only validated F_MH lever on Gemini-3-flash backbone today.

## Honest framing — what we now know

1. **KG path is backbone-dependent, not backbone-invariant.** This contradicts the implicit assumption that retrieval-stage mechanisms transfer across answer-stage backbones. The retrieved evidence is the same (same DB, same vault-facts injection), but Gemini-3-flash does NOT translate the additional KG-derived context into MH answer improvements the way gpt-4.1-mini does.

2. **D72 framing (F_MH generation-bound on dense-context corpora) is reinforced.** On EverMemBench (synthetic dense corpus), Gemini-3-flash hit a generation ceiling at ~6% F_MH that retrieval-stage augmentation cannot break. gpt-4.1-mini at ~4.4% bare had room to absorb retrieval signal; Gemini-3-flash at 6.02% bare does not.

3. **MA composite improvement (+0.78pp, MA_P +1.60pp, MA_U +1.37pp) suggests KG context helps memory-awareness dimensions** (especially personalization and user state) on Gemini-3-flash, even when F_MH stays flat. This is the only "win" signal in the matrix — but it's a side effect, not the goal.

4. **Tier 1 IterB+KG composability projection (+~4-5pp F_MH) was wrong** because it assumed +2.81pp KG lift; actual KG contribution on Gemini-3-flash is +0pp. Re-projection: IterB+KG ≈ IterB alone ≈ +2.01pp.

## Cross-references

- D70 backbone matrix Gemini-3-flash baseline: `RESULTS-BACKBONE-MATRIX.json`, PR #397
- Lab Q1 #4 KG path original (gpt-4.1-mini, +2.81pp F_MH lift): PR #379, `RESULTS-PHASEKG-FULL.md`
- Q3 IterB Gemini POC (+2.01pp clean F_MH lift on same backbone): PR #419, `RESULTS-Q3-ITERB-POC.md`, `[[q3-iterB-fmh-ceiling-broken-2pp]]`
- LoCoMo F_MH generation-bound D72: `[[locomo-crossbench-contradicts-fmh-retrieval-bound]]`

## Artifacts on disk

- VPS RUN_DIRs: `/root/.openclaw/evermembench-runs/r0-kg-gemini-{004,005,010,011,016}-*` (analysis.txt, eval.log, results-batch-*.json, answer-results-batch-*.json, search-results-batch-*.json, api.log, stream.log)
- Source DBs (unmodified): `/root/.openclaw/evermembench-runs/phaseKG-{004,005,010,011,016}-*/nox-mem.db`
- Workdir: `/tmp/r0-kg-gemini-9B0C7E18-B73C-46EB-B2B3-CCBEE36112BE/` (scripts + launcher.log)

## Lesson cravada

**`[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]`** — KG path retrieval (PR #379) +2.81pp F_MH lift on gpt-4.1-mini does NOT replicate on Gemini-3-flash backbone (R0 Wave 2 measured -0.01pp). Same DB, same KG entities/relations, same vault-facts injection. Retrieval-stage mechanisms are NOT backbone-invariant on EverMemBench-style dense corpora. Implication: Wave 2 composability projections built on KG+X must be re-baselined before dispatch.
