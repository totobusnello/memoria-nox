# EverMemBench Phase AC CLEAN rerun — Lab Q1 #1 adaptive classifier (threshold=5)

**Status:** Complete (clean, sequential dispatch).
**Date:** 2026-05-29
**Branch:** `feat/lab-q1-1-adaptive-classifier-clean-rerun`
**Threshold:** 5 (raised from contaminated v1's threshold=4)
**Cost actual:** ~$2.30 of $5 budget cap (5 batches @ ~$0.46 each)

---

## TL;DR

Lab Q1 #1 adaptive classifier **CLEAN 5-batch rerun**, threshold=5, sequential dispatch (no VPS OOM, no concurrent agents).

- **Overall 51.21%** (vs Phase H v2 **51.68%** = **-0.47pp**, statistical tie)
- **F_MH 5.22%** (vs Phase H v2 **3.21%** = **+2.01pp marginal lift**)
- **MA mean 71.72%** (vs Phase H v2 **73.34%** = **-1.63pp regression**)
- **Activation 44.2%** (target band 30-60%, **PASS**)
- **0% search errors** across all 5 batches
- **Cost ~$2.30**, well under $5 budget

**Verdict: 2/4 gates passed (mean-only) / 1/4 (CI-strict)**

**Paper §5.3 recommendation:** **Opt-in only** — do NOT ship default. Adaptive classifier at threshold=5 + MiniLM rerank does NOT beat Phase H v2 (no rerank) baseline on overall accuracy. F_MH lift is real (+2.01pp) but does not compensate for MA regression (-1.63pp) or overall flat-line (-0.47pp).

---

## Context

PR #380 (merged commit `2a52249`) shipped adaptive classifier implementation. First bench attempt (Phase AC v1) was **CONTAMINATED** by:

1. VPS OOM from 5 parallel rerank api-servers (>15GB total RAM)
2. Concurrent KG agent (Lab Q1 #4 PR #379) cross-contamination
3. Threshold=4 yielded 75.7% activation (too aggressive vs target 30-60%)
4. Search disconnects bypassed classifier code path

Contaminated result: 41.93% overall, 3.62% F_MH (1/4 gates met marginally).

This **CLEAN rerun** addresses all contamination sources:

- **Sequential dispatch:** 1 batch at a time on port 18840 (isolated)
- **No concurrent agents:** verified zero other bench processes on VPS
- **Threshold=5:** raised to reduce activation 75% → target ~44%
- **Pre-warmed DBs:** copied from prior phaseAC runs (10k chunks each)
- **Preflight billing check:** real gpt-4.1-mini completion before each batch
- **Search error rate audit:** confirmed 0% per batch

---

## Per-batch results

| batch | total | correct | accuracy | activation | search errors |
|---|---:|---:|---:|---:|---:|
| 004 | 626 | 317 | 50.64% | 43.9% | 0 (0.0000) |
| 005 | 610 | 326 | 53.44% | 48.2% | 0 (0.0000) |
| 010 | 623 | 317 | 50.88% | 44.8% | 0 (0.0000) |
| 011 | 633 | 326 | 51.50% | 43.0% | 0 (0.0000) |
| 016 | 629 | 312 | 49.60% | 41.3% | 0 (0.0000) |
| **5-batch weighted** | **3121** | **1598** | **51.21%** | **44.2%** | **0** |

- Per-batch mean: **51.21%** | stdev: **1.42pp**
- 95% CI (t-dist, n=5, dof=4): **49.45 – 52.98%** (±1.76pp)
- Min: 49.60% (016) / Max: 53.44% (005)
- Activation rate band: 41.3 – 48.2% (target 30-60%)

---

## Sub-dimension breakdown

| sub-dim | dimension | mean | stdev | 95% CI | vs Phase H v2 | vs Phase G 5-batch | vs Phase AC v1 contam | vs MemOS gpt-4.1-mini |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Overall** |  |  |  |  |  |  |  |  |
| overall | Overall | 51.21% | 1.42pp | 49.45–52.98% | **-0.47pp** | -10.05pp | **+9.28pp** | **+8.66pp** |
| **Fine-grained Recall** |  |  |  |  |  |  |  |  |
| F_SH | Fine-grained Recall | 80.94% | 6.58pp | 72.77–89.11% | -0.03pp | +3.22pp | -0.84pp | +9.58pp |
| F_MH | Fine-grained Recall | 5.22% | 3.35pp | 1.06–9.39% | **+2.01pp** | -1.61pp | **+1.60pp** | -13.66pp |
| F_TP | Fine-grained Recall | 13.67% | 4.47pp | 8.12–19.22% | -1.33pp | -14.33pp | -2.33pp | -2.00pp |
| F_HL | Fine-grained Recall | 22.41% | 3.18pp | 18.46–26.35% | -0.27pp | -33.78pp | -19.42pp | — |
| **Memory Awareness** |  |  |  |  |  |  |  |  |
| MA_C | Memory Awareness | 80.80% | 3.63pp | 76.29–85.31% | **-3.80pp** | -3.60pp | **+18.20pp** | +10.90pp |
| MA_P | Memory Awareness | 66.60% | 4.16pp | 61.44–71.76% | **+1.20pp** | -13.60pp | **+19.20pp** | +14.61pp |
| MA_U | Memory Awareness | 67.75% | 10.28pp | 54.99–80.51% | **-2.28pp** | -13.41pp | **+32.99pp** | +22.60pp |
| **Profile Understanding** |  |  |  |  |  |  |  |  |
| P_Style | Profile Understanding | 43.26% | 6.99pp | 34.58–51.93% | +3.48pp | +0.31pp | **+15.43pp** | +14.33pp |
| P_Skill | Profile Understanding | 49.25% | 6.24pp | 41.51–57.00% | -0.52pp | -10.03pp | **+13.55pp** | +16.72pp |
| P_Title | Profile Understanding | 56.48% | 8.07pp | 46.46–66.51% | +0.43pp | -11.26pp | **+10.95pp** | +8.01pp |

**MA aggregate (mean of MA_C/MA_P/MA_U):** 71.72% vs baseline 73.34% = **-1.63pp** (within tolerance band ±0.5pp = **FAIL**).

---

## 4-gate verdict

### Gate A — Overall ≥ Phase H v2 51.68% (cross-backbone parity)

**Verdict: FAIL (mean) / REJECT (CI)**

- mean: **51.21%** vs baseline **51.68%** = **-0.47pp**
- 95% CI lower: 49.45% (below baseline)
- statistical tie (within ±1.42pp stdev), but FAILS the strict gate

### Gate B — F_MH ≥ Phase H v2 3.21% (cross-backbone bar)

**Verdict: PASS (mean) / REJECT (CI)**

- mean: **5.22%** vs baseline **3.21%** = **+2.01pp marginal lift**
- 95% CI lower: 1.06% (below baseline)
- mean PASSES, but CI lower below baseline → strict CI gate FAILS
- Δ vs contaminated Phase AC v1 (3.62%): **+1.60pp improvement** (threshold=5 better than 4)
- Δ vs Phase G Gemini (6.83%): -1.61pp (Phase G dominates F_MH but at huge MA cost)

### Gate C — MA_C/P/U mean within 0.5pp of 73.34% baseline

**Verdict: FAIL**

- mean: **71.72%** vs baseline **73.34%** = **-1.63pp**
- exceeds 0.5pp tolerance band
- Driver: MA_C -3.80pp (78% baseline), MA_U -2.28pp (mostly recovered from contaminated -35.27pp); MA_P actually +1.20pp lift

### Gate D — Activation rate in 30-60% target band

**Verdict: PASS**

- mean: **44.2%** (within band)
- distribution: [41.3, 43.0, 43.9, 44.8, 48.2]
- threshold=5 yielded activation in target band (vs contaminated 75.7% at threshold=4)
- Successfully reduced over-activation by ~31pp

### Final verdict: **2/4 gates (mean) | 1/4 gates (CI-strict)**

---

## Comparison vs Phase AC v1 contaminated (threshold=4)

The CLEAN rerun **massively improves over the contaminated baseline**:

| metric | Phase AC v1 contaminated | Phase AC clean (threshold=5) | Δ |
|---|---:|---:|---:|
| overall | 41.93% | **51.21%** | **+9.28pp** |
| F_MH | 3.62% | **5.22%** | **+1.60pp** |
| F_TP | 16.00% | 13.67% | -2.33pp |
| MA_C | 62.60% | **80.80%** | **+18.20pp** |
| MA_P | 47.40% | **66.60%** | **+19.20pp** |
| MA_U | 34.76% | **67.75%** | **+32.99pp** |
| P_Style | 27.83% | **43.26%** | **+15.43pp** |
| P_Skill | 35.70% | **49.25%** | **+13.55pp** |
| P_Title | 45.53% | **56.48%** | **+10.95pp** |
| Activation | 75.7% | **44.2%** | **-31.5pp** (target band) |

**Conclusion:** Threshold=5 + clean dispatch fixed the over-activation problem and recovered MA dimensions. But still doesn't beat Phase H v2 (no rerank) on overall.

---

## Routing distribution (5-batch, threshold=5)

- **Total queries:** 3,121
- **multi_hop (rerank applied):** 1,360 (43.6%)
- **factual (rerank skipped):** 1,761 (56.4%)
- **unknown/unavailable:** 1 (negligible)

Classifier correctly routes ~44% of queries to rerank — well within target band 30-60%.

---

## Cost

| batch | OpenAI cost (estimate) | wall time |
|---|---:|---:|
| 004 | ~$0.46 | 807s |
| 005 | ~$0.45 | 855s |
| 010 | ~$0.45 | 809s |
| 011 | ~$0.46 | 1395s (longer Answer stage, possibly rate limits) |
| 016 | ~$0.46 | 1401s (longer Answer stage) |
| **Total** | **~$2.28** | ~5267s (~88min sequential) |

Well under $5 budget cap.

---

## Paper §5.3 narrative recommendation

### Decision: **Opt-in only, NOT default**

**Rationale:**

1. Overall accuracy does NOT exceed Phase H v2 baseline (-0.47pp). The classifier failed Gate A — its primary purpose was to deliver Phase G's F_MH lift while preserving Phase H v2's MA. It does neither cleanly:
   - F_MH lift: +2.01pp (modest, real)
   - MA preservation: -1.63pp (within band-edge regression)
   - Overall: statistical tie -0.47pp

2. Trade-off does not net positive at population level. Workloads where F_MH dominates evaluation may benefit; workloads where MA dominates suffer.

3. **Honest framing:** Classifier is a useful **opt-in tool for known multi-hop-heavy retrievals**, but should not ship as default ON. Doc as `NOX_ADAPTIVE_CLASSIFIER=1` opt-in flag; default OFF.

### Paper text suggestion (concise):

> Lab Q1 #1 prototyped a heuristic adaptive classifier (Option A per spec PR #373) that routes per-query between cross-encoder rerank (for multi-hop) and bi-encoder retrieval (for factual). Clean 5-batch evaluation on EverMemBench (n=3121 questions, gpt-4.1-mini backbone, threshold=5) yielded overall accuracy 51.21% (vs Phase H v2 baseline 51.68%, statistical tie), with marginal F_MH lift (+2.01pp) offset by marginal MA regression (-1.63pp). The classifier does not pass Gate A (overall parity) or Gate C (MA preservation); it does pass Gate B (F_MH lift) and Gate D (activation band). **We ship the classifier as opt-in (`NOX_ADAPTIVE_CLASSIFIER=1`), not default**, and recommend per-workload evaluation before enabling.

---

## Lessons cravados

### 1. Threshold tuning shows narrow operating band

- threshold=4: 75.7% activation, overall 41.93% (over-rerank, MA collapse)
- threshold=5: 44.2% activation, overall 51.21% (target band, slight MA regression)
- threshold=6+ untested but predicted activation <30% (below target band, no F_MH lift)

The heuristic is binary-classifier-sensitive: ±1 threshold changes activation by ~30pp. Future Lab Q1 work should explore continuous gating (e.g., score-weighted rerank probability) rather than hard threshold.

### 2. Clean methodology recoverable from contamination (+9.28pp delta)

The contaminated bench overstated regression by ~9pp because OOM + concurrent agents truncated search results and bypassed classifier. **Lesson reinforced: bench infrastructure must be sequential, isolated, with explicit error monitoring.**

### 3. Marginal Gate B passage is a soft positive signal

F_MH +2.01pp is real but small. Phase G (always rerank Gemini) hit +3.62pp lift over Phase H v2 baseline at much higher MA cost. The adaptive classifier extracts ~55% of Phase G's F_MH lift while preserving 95% of Phase H v2's MA — modest tradeoff, fragile.

### 4. Per-batch wall time varies (807s – 1401s)

Batches 011 and 016 took ~1400s vs 800s for 004/005/010. Hypothesis: OpenAI API rate-limit backoff during Answer stage. Future cost estimation should account for variance.

### 5. Activation rate is the most reliable signal

Even when overall accuracy variance is high, activation rate distribution stays tight (41-48%, stdev 2.6pp). The classifier is **deterministic and reproducible** — variance comes from downstream rerank quality, not classifier decisions.

---

## Cleanup

- ✅ Killed `nox-mem-api` on port 18840 (zero post-bench processes)
- ✅ Prod `nox-mem-api` on port 18802 still healthy (69135 chunks)
- ✅ Audit artifacts preserved at `/root/.openclaw/evermembench-runs/ac-clean-{004,005,010,011,016}-*/`
- ✅ Restored installed adapter from `nox_mem_adapter.py.bak-pre-ac-clean-1780052851`

---

## Reproduction

Workdir on VPS: `/root/.openclaw/lab-q1-1-AC-clean-7f62f006/`
- `nox-mem/` — Node code copied from VPS prod (`/root/.openclaw/workspace/tools/nox-mem/`)
- `memoria-nox-fresh/` — fresh clone with PR #380 (`2a52249`)
- `run-batch-ac-clean.sh` — sequential per-batch runner (threshold=5)
- `aggregate_ac_clean.py` — 5-batch aggregation + 4-gate verdict

Per-batch runs at `/root/.openclaw/evermembench-runs/ac-clean-{batch}-{ts}/`:
- `nox-mem.db` — isolated DB (10k chunks)
- `api.log` — api-server stdout
- `eval.log` — harness stdout (classifier decisions visible)
- `results-batch-{batch}.json` — evaluation results
- `answer-results-batch-{batch}.json` — Answer stage outputs
- `search-results-batch-{batch}.json` — Search results with classifier metadata
- `routing-audit.txt` — per-batch routing summary + search error rate
- `analysis.txt` — per-category breakdown
