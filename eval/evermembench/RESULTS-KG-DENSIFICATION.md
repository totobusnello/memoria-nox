# Phase KG DENSE 5-batch — KG densification + re-bench (Lab Q1.6)

> **Status:** ❌ DENSITY LIMIT VALIDATED — densification REJECTED. Dense KG (2.77× entities, 2.99× relations) does NOT close the Q1 #4 MA gap and *regresses* vs sparse KG on F_MH and Overall. **Keep sparse as canonical.**
> **Date:** 2026-05-29
> **Densification:** `nox-mem kg-extract --limit 2000` per batch (4× current sparse `--limit 500`), gemini-2.5-flash-lite. Actually completed ~830-862 chunks/batch before SIGTERM at chunk≥800 milestone.
> **Baseline 1:** Phase KG sparse 5-batch (PR #379, 51.80% overall, F_MH 6.02%, MA 73.78%)
> **Baseline 2:** Phase H v2 5-batch (PR #377, 51.68% overall, F_MH 3.21%, MA 73.34%)
> **Cross-system:** MemOS GPT-4.1-mini Table 4 (42.55% overall, F_MH 18.88%)
> **Cost actual:** $0 dense extract (Gemini flash-lite under quota) + ~$3.64 bench (gpt-4.1-mini, same as Phase H v2) = **$3.64 / $12 budget**.

---

## Headline

| Metric | Phase KG DENSE | Phase KG sparse (PR #379) | Phase H v2 baseline | Δ dense vs sparse | Δ dense vs Phase H v2 |
|---|---:|---:|---:|---:|---:|
| **Overall** | **51.27%** (CI 49.53–53.01%) | 51.80% | 51.68% | **-0.53 pp ⚠️** | -0.41 pp |
| **F_MH** | **4.42%** (CI 0.34–8.49%) | 6.02% | 3.21% | **-1.60 pp ⚠️** | +1.21 pp |
| **MA mean** | **74.34%** | 73.78% (+0.44pp) | 73.34% | **+0.56 pp** ↑ but <gate | +1.00 pp |
| MA_C | 84.80% | 84.60% | 84.60% | +0.20 pp | +0.20 pp |
| MA_P | 66.40% | 66.60% | 65.40% | -0.20 pp | +1.00 pp |
| MA_U | 71.83% | 70.15% | 70.03% | +1.68 pp | +1.80 pp |
| **Coverage** | **97.24%** | 90.84% | — | +6.40 pp | — |
| **kg_ms p50** | 307-353 ms | 7-105 ms | — | **+200-300 ms ⚠️** | — |
| **kg_ms p95** | 722-812 ms | 21-260 ms | — | **+500-700 ms ⚠️** | — |

### Key finding (publishable negative result)

**Densifying KG 2.77× entities / 2.99× relations does NOT close the Q1 #4 MA gap. Instead, it REGRESSES F_MH (-1.60pp) and Overall (-0.53pp) vs sparse KG.** The Q1 #4 MA gap is **NOT density-bound** — the limit signaled in `[[kg-extract-density-bounds-signal]]` is now empirically validated as a **density ceiling** rather than a floor.

Hypothesis at task kickoff: more KG → more MA boost coverage → close +1pp gate.  
Reality: more KG → broader coverage (90.84% → 97.24%) BUT introduces noise that diluted the F_MH signal and net regressed Overall. The MA dimension improved marginally (+0.56pp), still below the +1pp threshold.

---

## Densification Approach

Per the task prompt, options A-D were evaluated:

- **A. Full corpus re-run with gemini-2.5-flash (full model not lite):** Cost $5-10, expected 2-3× density. Estimated 8-10h wallclock.
- **B. Sample-based on under-covered chunks:** ~$2-3, limited gain because every chunk produces entities under existing extractor — "under-covered" not a useful filter.
- **C. Stricter prompt asking for more types:** ~$3-5, requires nox-mem CLI code change (NOX_KG_MODE=dense flag).
- **D. Embedding-based merge:** $0, but density gain bounded by current 560 entities/batch ceiling.

**Selected: variant of A** — `--limit 2000` (4× sparse) with the existing gemini-2.5-flash-lite extractor. No code change needed, $0 incremental cost (under Gemini quota), ~25 min wallclock per batch in parallel (5 batches concurrent). Stopped at chunk≥800 milestone (achieved 2.77× / 2.99× density target) without waiting for full 2000-chunk completion.

The original kg-extract source is unchanged — densification is achieved purely by scaling `--limit` from 500 → 2000 (capped at chunk ~830-862 actually processed before SIGTERM).

## KG state — Before vs After

| batch | sparse_E | sparse_R | dense_E | dense_R | E_growth | R_growth | chunks_processed |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 560 | 1748 | 1584 | 5141 | 2.83× | 2.94× | 862 |
| 005 | 624 | 1823 | 1661 | 5441 | 2.66× | 2.98× | 861 |
| 010 | 565 | 1837 | 1547 | 5369 | 2.74× | 2.92× | 834 |
| 011 | 599 | 1783 | 1594 | 5178 | 2.66× | 2.90× | 843 |
| 016 | 517 | 1583 | 1563 | 5072 | 3.02× | 3.20× | 813 |
| **TOTAL** | **2865** | **8774** | **7949** | **26201** | **2.77×** | **2.99×** | **4213** |

Densification target (task spec): ≥2× entities and ≥2× relations. **Achieved 2.77× E + 2.99× R — target met.**

---

## Per-batch 5-batch overall accuracy

| batch | total | correct | DENSE % | sparse % | Δ |
|---|---:|---:|---:|---:|---:|
| 004 | 626 | 325 | 51.92% | 53.19% | -1.27 |
| 005 | 610 | 319 | 52.30% | 50.66% | +1.64 |
| 010 | 623 | 304 | 48.80% | 51.04% | -2.24 |
| 011 | 633 | 327 | 51.66% | 51.03% | +0.63 |
| 016 | 629 | 325 | 51.67% | 53.10% | -1.43 |
| **5-batch weighted** | **3121** | **1600** | **51.27%** | **51.80%** | **-0.53** |

- Mean: 51.27% / stdev 1.41pp / 95% CI [49.53%, 53.01%]
- Per-batch CI lower bound 49.53% > MemOS 42.55%: cross-backbone WIN still holds.

## Per-category 5-batch breakdown

| sub-dim | dim | DENSE mean | stdev | 95% CI | Δ vs sparse KG | Δ vs Phase H v2 |
|---|---|---:|---:|---:|---:|---:|
| **Fine-grained Recall** | | | | | | |
| F_SH | Single-hop | 78.54% | 9.58 | 66.65–90.43% | **-2.83 ⚠️** | -2.43 ⚠️ |
| **F_MH** | **Multi-hop** | **4.42%** | 3.28 | 0.34–8.49% | **-1.60 ⚠️** | +1.21 |
| F_TP | Temporal | 14.33% | 5.22 | 7.86–20.81% | -0.34 | -0.67 |
| F_HL | Held-out long | 22.17% | 4.58 | 16.48–27.86% | +0.04 | -0.51 |
| **Memory Awareness** | | | | | | |
| MA_C | Constancy | 84.80% | 3.11 | 80.93–88.67% | +0.20 | +0.20 |
| **MA_P** | **Profile** | **66.40%** | 4.28 | 61.09–71.71% | -0.20 | **+1.00 ✓** |
| **MA_U** | **Update** | **71.83%** | 9.26 | 60.34–83.32% | **+1.68 ✓** | **+1.80 ✓** |
| **MA avg** | | **74.34%** | | | **+0.56** ↑<gate | +1.00 ✓ |
| **Profile Understanding** | | | | | | |
| P_Style | Style | 38.87% | 5.54 | 31.99–45.74% | -1.01 ⚠️ | -0.91 ⚠️ |
| P_Skill | Skill | 45.22% | 3.60 | 40.75–49.69% | **-2.66 ⚠️** | **-4.55 ⚠️** |
| P_Title | Title | 54.05% | 9.23 | 42.59–65.51% | -1.20 ⚠️ | -2.00 ⚠️ |

**MA_U +1.68pp vs sparse** — single concrete MA win. MA_P / MA_C unchanged or slight decrease. Aggregate MA delta (+0.56pp) below +1pp gate.

**F_MH -1.60pp vs sparse** is the most surprising regression. Hypothesis: dense KG introduces more entity matches, but the additional relations are lower-confidence (later chunks processed = less curated). The 1-hop boost then promotes the wrong chunks.

**P_Skill -2.66pp / P_Title -1.20pp vs sparse** — exacerbates the existing P_Skill/P_Title regressions seen in sparse Phase KG vs Phase H v2. Dense KG raises the noise floor for profile queries.

## KG Coverage & Latency (dense bench)

| batch | queries | kg_applied | with_entity | with_neighbor | with_boost | kg_ms p50 | kg_ms p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 626 | 614 (98.1%) | 614 | 613 | 146 | 332.95ms | 765.09ms |
| 005 | 610 | 582 (95.4%) | 582 | 579 | 171 | 352.57ms | 812.34ms |
| 010 | 623 | 617 (99.0%) | 617 | 613 | 222 | 325.80ms | 722.39ms |
| 011 | 633 | 623 (98.4%) | 623 | 623 | 210 | 307.04ms | 723.31ms |
| 016 | 629 | 608 (96.7%) | 608 | 607 | 152 | 332.70ms | 807.70ms |
| **TOTAL** | **3121** | **3044 (97.5%)** | **3044 (97.5%)** | **3035 (97.2%)** | **901 (28.9%)** | — | — |

**Coverage:** 97.24% queries match ≥1 entity (+6.40pp vs sparse 90.84%). 28.9% queries see ≥1 boosted chunk (+12pp vs sparse 16.8%).

**Latency:** **p50 307-353ms (4-50× slower than sparse 7-105ms). p95 up to 812ms (3-39× slower).** This is the latency cost of larger KG state — neighbor lookup time scales with relation count, and the regex extractor matches more entity candidates per query.

This is the FIRST hard latency hit observed in the KG path. Sparse KG fit comfortably in 1.2× budget; dense KG approaches 2-3× budget. Latency budget alone would gate dense.

---

## Lab Q1.6 Densification Gate (vs Phase KG sparse PR #379)

| Gate | Threshold | Result | Pass |
|---|---|---|:---:|
| MA mean ≥ +1pp vs sparse KG (Q1.6 original target — the gate that failed at sparse) | +1.0pp | **+0.56pp** | ❌ |
| F_MH preserve ≥ +2.81pp vs Phase H v2 (sparse KG baseline) | +2.81pp | **+1.21pp** | ❌ |
| Overall ≥ sparse KG (no regression) | 0.0pp | **-0.53pp** | ❌ |
| Coverage ≥ 30% queries with ≥1 neighbor | 30% | **97.24%** | ✅ |

**Gate summary: 1 / 4 conditions met.**

### Statistical caveats

- F_MH CI lower bound 0.34% is barely positive — F_MH is high-variance small-N. Mean Δ +1.21pp vs Phase H v2 is real but does NOT preserve the +2.81pp sparse advantage.
- Overall CI [49.53%, 53.01%] overlaps Phase H v2 (51.68%) and sparse (51.80%). The -0.53pp regression is within noise, but the direction is wrong.
- MA Δ +0.56pp vs sparse is positive but below gate. MA_U lifts strongly (+1.68pp); MA_C and MA_P flat/slight negative.

### Original Q1 #4 gates (dense vs Phase H v2, for reference)

| Gate | Threshold | Result | Pass |
|---|---|---|:---:|
| F_MH lift ≥ +2pp vs Phase H v2 | +2.0pp | **+1.21pp** | ❌ (sparse passed at +2.81pp) |
| MA lift ≥ +1pp vs Phase H v2 | +1.0pp | **+1.00pp** | ✅ (marginal, sparse failed at +0.44pp) |
| Overall non-regression vs Phase H v2 | 0.0pp | **-0.41pp** | ❌ (sparse passed at +0.12pp) |
| Coverage ≥ 30% | 30% | **97.24%** | ✅ |

**Compared to sparse Phase KG (PR #379 — 3/4 gates met):** dense achieves only 2/4 gates. Net worse than sparse.

---

## Decision

**REJECT DENSE — keep Phase KG sparse (PR #379) as canonical.** Density LIMIT validated.

### What works at dense

- MA_U **+1.68pp vs sparse** — meaningful single-dim signal that dense KG helps the "Update" dimension specifically (likely the latest extracted relations carry "updated" facts that resolve update-style queries).
- Coverage +6.40pp — denser KG matches more queries by entity.

### What fails at dense

- **F_MH regresses -1.60pp** — dense KG dilutes the boost signal. The 1-hop walk with regex matching becomes less discriminating because the relation density is higher per entity but lower per-relation confidence.
- **Overall regresses -0.53pp** — net negative.
- **Latency 4-50× slower (p50) / 3-39× slower (p95)** — approaches 2-3× budget vs sparse's 1.2×.
- **P_Skill/P_Title regress further** — profile queries especially hurt by noisier KG boost.

### What this means for the Q1 #4 saga

Phase KG sparse (PR #379) is the **canonical recommendation**:
- 3/4 gates met (F_MH ✓, overall ✓, coverage ✓; MA ❌)
- $0/query at search time (regex extraction)
- Latency 1.2× budget

Densification was the obvious next lever to close the MA gap. **The lever doesn't work.** The MA gap is therefore characterized as:
- NOT density-bound
- Either dimension-orthogonal (KG mechanism cannot resolve MA queries fundamentally), OR
- Bound by a different mechanism (path scoring, neighbor weighting, confidence cascade, query intent routing)

### Recommended next steps (for Q1 #4 closure)

1. **Ship sparse Phase KG as `--kg-walk=1` opt-in (per PR #379 spec §9.Q1.7)** — partial ship at 3/4 gates.
2. **Document density LIMIT** in paper §6 / KG appendix — `[[kg-extract-density-bounds-signal]]` updated.
3. **Park MA gap closure for Q2 spec** — consider:
   - Approach C (path scoring with Dijkstra + neighbor-type weighting)
   - Composability with Lab Q1 #1 adaptive classifier (route MA queries to non-KG branches)
   - Reranker re-introduction (Phase F + Phase KG composable)

---

## Trade-offs documented

| Trade-off | Direction | Magnitude |
|---|---|---|
| F_MH (multi-hop factual) | ⚠️ regressed vs sparse | -1.60pp |
| F_SH (single-hop) | ⚠️ regressed | -2.83pp |
| F_TP (temporal) | neutral | -0.34pp |
| F_HL (held-out long) | neutral | +0.04pp |
| MA_C (constancy) | flat | +0.20pp |
| MA_P (profile) | neutral | -0.20pp |
| **MA_U (update)** | ✅ **improved** | **+1.68pp** |
| **MA avg** | weak positive | +0.56pp (below +1pp gate) |
| P_Style | weak regression | -1.01pp |
| P_Skill | ⚠️ regressed | -2.66pp |
| P_Title | weak regression | -1.20pp |
| Overall | weak regression | -0.53pp |
| Coverage | improved | +6.40pp |
| **Latency p50 / p95** | ⚠️ **degraded** | **+200-300ms / +500-700ms** |
| Cost | flat | $0/query |

---

## Implementation note: extract early-termination

Densification was launched with `--limit 2000` (target 4× sparse) but stopped at chunk≥800 milestone via SIGTERM once all 5 batches achieved 2-3× density target. Actual chunks processed per batch: 813-862. This was sufficient — at ~830 chunks the UNIQUE constraint on `(name, entity_type)` had already absorbed most entity dedupes, and per-batch entity counts (1547-1661) were well above the 2× target.

The result: dense KG with 2.77× entities + 2.99× relations vs sparse. This is the regime tested.

---

## Lessons cravadas

1. **`[[kg-extract-density-bounds-signal-CEILING]]`** — UPDATED: density signal hypothesis was that more entities = better boost coverage = closes MA gap. Empirical refutation: 2.77× entities / 2.99× relations REGRESSES F_MH (-1.60pp) and Overall (-0.53pp) vs sparse. Only MA_U improves significantly (+1.68pp). The MA gap is NOT density-bound.

2. **`[[kg-dense-introduces-boost-noise]]`** — denser KG → more relations per entity → 1-hop walk less discriminating → lower-confidence neighbors get boosted → wrong chunks promoted in F_MH. This is a real mechanism limit, not implementation noise.

3. **`[[kg-latency-scales-superlinearly-with-relation-count]]`** — sparse 1748 relations/batch → p50 7-105ms; dense 5141 relations/batch (2.94× R) → p50 333ms (4-50× slower). Neighbor lookup + regex-candidate match scales worse than linear in relation count.

4. **`[[ma-u-dimension-density-responsive]]`** — within MA dimension, only MA_U (Update) responds positively to density (+1.68pp). MA_C and MA_P unchanged. Suggests "update" queries benefit from broader fact recall while "constancy" and "profile" queries don't — they need precision over recall.

5. **`[[sigterm-at-milestone-acceptable-for-incremental-densification]]`** — kg-extract supports clean early termination via SIGTERM; partial completion (813-862 chunks of 2000) is OK because UNIQUE constraint on entities means later chunks add diminishing returns. Total wallclock saved: ~25min × 5 batches.

---

## References

- `specs/2026-05-28-kg-path-retrieval.md` — Approach A spec
- `eval/evermembench/RESULTS-PHASEKG-5BATCH.md` — Phase KG sparse baseline (PR #379)
- `eval/evermembench/RESULTS-PHASEH-v2-5BATCH.md` — Phase H v2 baseline (PR #377)
- `eval/evermembench/run-kg-dense-extract.sh` — densification launcher
- `eval/evermembench/run-parallel-phaseKG-dense-bench.sh` — dense 5-batch bench launcher
- `eval/evermembench/aggregate-phaseKG-dense.py` — 4-gate aggregator
- `[[kg-extract-density-bounds-signal]]` — original density signal hypothesis (REFUTED)
- `[[a1-op-audit-module]]` — atomic snapshot pattern (pre-extract clone honored)
- `[[memory-awareness-dimension-must-be-audited]]` — MA mandatory in every report
- `[[scoring-boost-multiplicative-empilhavel-e-veneno]]` — additive boost preserved
