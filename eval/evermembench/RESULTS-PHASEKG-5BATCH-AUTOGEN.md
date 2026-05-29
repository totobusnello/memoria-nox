# EverMemBench Phase KG (Lab Q1 #4) — phaseKG-5batch

**Batches:** 004, 005, 010, 011, 016 (n=5)

## Headline

- **Phase KG (Lab Q1 #4) overall: 51.74%** (95% CI: 50.14–53.34%) (n=5 batches)
- vs **Phase H v2 (5-batch)** (51.68%): **+0.06 pp**
- vs **MemOS GPT-4.1-mini** (42.55%): **+9.19 pp**

## Sub-dimension breakdown

> MA_C / MA_P / MA_U are MANDATORY rows — per `[[memory-awareness-dimension-must-be-audited]]`.
> Regressions vs any baseline are highlighted in **bold** with ⚠️.

| sub-dim | dimension | Phase KG (Lab Q1 #4) mean | stdev | 95% CI | Δ vs Phase H v2 (5-batch) | Δ vs MemOS GPT-4.1-mini |
|---|---:|---:|---:|---:|---:|---:|
| **Overall** |  |  |  |  |  |  |
| overall | Overall | 51.74% | 1.29 pp | 50.14–53.34% | +0.06 pp | +9.19 pp |
| **Fine-grained Recall** |  |  |  |  |  |  |
| F_SH | Fine-grained Recall | 81.37% | 5.99 pp | 73.94–88.80% | +0.40 pp | +10.01 pp |
| F_MH | Fine-grained Recall | 5.62% | 3.84 pp | 0.85–10.38% | +2.41 pp | **-13.26 pp ⚠️** |
| F_TP | Fine-grained Recall | 15.67% | 5.35 pp | 9.03–22.31% | +0.67 pp | -0.00 pp |
| F_HL | Fine-grained Recall | 22.13% | 4.19 pp | 16.93–27.34% | **-0.55 pp ⚠️** | — |
| **Memory Awareness** |  |  |  |  |  |  |
| MA_C | Memory Awareness | 84.60% | 1.14 pp | 83.18–86.02% | +0.00 pp | +14.70 pp |
| MA_P | Memory Awareness | 66.20% | 5.12 pp | 59.85–72.55% | +0.80 pp | +14.21 pp |
| MA_U | Memory Awareness | 70.50% | 10.58 pp | 57.37–83.63% | +0.47 pp | +25.35 pp |
| **Profile Understanding** |  |  |  |  |  |  |
| P_Style | Profile Understanding | 39.88% | 5.48 pp | 33.07–46.69% | +0.10 pp | +10.90 pp |
| P_Skill | Profile Understanding | 47.44% | 4.60 pp | 41.73–53.15% | **-2.33 pp ⚠️** | +14.90 pp |
| P_Title | Profile Understanding | 54.45% | 7.43 pp | 45.23–63.67% | **-1.60 pp ⚠️** | +5.98 pp |

## Per-batch detail

| metric | 004 | 005 | 010 | 011 | 016 | mean | stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| overall | 53.19 | 50.66 | 50.72 | 51.03 | 53.10 | 51.74 | 1.29 |
| F_SH | 87.76 | 78.00 | 76.00 | 88.00 | 77.08 | 81.37 | 5.99 |
| F_MH | 10.00 | 6.00 | 0.00 | 8.00 | 4.08 | 5.62 | 3.84 |
| F_TP | 8.33 | 20.00 | 18.33 | 11.67 | 20.00 | 15.67 | 5.35 |
| F_HL | 21.79 | 18.67 | 28.21 | 17.95 | 24.05 | 22.13 | 4.19 |
| MA_C | 86.00 | 85.00 | 84.00 | 83.00 | 85.00 | 84.60 | 1.14 |
| MA_P | 67.00 | 60.00 | 64.00 | 66.00 | 74.00 | 66.20 | 5.12 |
| MA_U | 68.97 | 81.82 | 53.45 | 74.07 | 74.19 | 70.50 | 10.58 |
| P_Style | 40.54 | 39.29 | 48.39 | 33.33 | 37.84 | 39.88 | 5.48 |
| P_Skill | 51.11 | 39.53 | 50.00 | 48.84 | 47.73 | 47.44 | 4.60 |
| P_Title | 65.31 | 46.94 | 56.00 | 56.00 | 48.00 | 54.45 | 7.43 |

## Gate summary vs Phase H v2 (5-batch)

| sub-dim | mean Δ | CI lower Δ | verdict |
|---|---:|---:|---|
| overall | +0.06 pp | -1.54 pp | REJECT |
| F_SH | +0.40 pp | -7.03 pp | REJECT |
| F_MH | +2.41 pp | -2.36 pp | REJECT |
| F_TP | +0.67 pp | -5.97 pp | REJECT |
| F_HL | -0.55 pp | -5.75 pp | REJECT |
| MA_C | +0.00 pp | -1.42 pp | REJECT |
| MA_P | +0.80 pp | -5.55 pp | REJECT |
| MA_U | +0.47 pp | -12.66 pp | REJECT |
| P_Style | +0.10 pp | -6.71 pp | REJECT |
| P_Skill | -2.33 pp | -8.04 pp | REJECT |
| P_Title | -1.60 pp | -10.82 pp | REJECT |


## KG Coverage & Latency

| batch | queries | kg_applied | with_entity | with_neighbor | with_boost | kg_ms p50 | kg_ms p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 626 | 594 | 594 | 591 | 99 | 48.16ms | 99.98ms |
| 005 | 610 | 505 | 505 | 505 | 88 | 104.51ms | 260.10ms |
| 010 | 623 | 0 | 0 | 0 | 0 | 0.00ms | 0.00ms |
| 011 | 633 | 618 | 618 | 612 | 140 | 88.98ms | 230.15ms |
| 016 | 629 | 529 | 529 | 525 | 71 | 11.42ms | 37.92ms |
| **TOTAL** | **3121** | **2246** (72.0%) | **2246** (72.0%) | **2233** (71.5%) | **398** (12.8%) | — | — |


## Lab Q1 #4 Gate Decisions (vs Phase H v2 5-batch)

| Gate | Pass | Observed |
|---|---|---|
| F_MH lift ≥ +2pp (5-batch) | ✅ | observed +2.41pp (5.62% vs 3.21%) |
| MA lift ≥ +1pp (avg of MA_C, MA_P, MA_U) | ❌ | observed +0.42pp (73.77% vs 73.34%) |
| Overall non-regression (≥ 0pp) | ✅ | observed +0.06pp (51.74% vs 51.68%) |
| Coverage ≥ 30% queries with ≥1 neighbor | ✅ | observed 71.55% (2233/3121) |

**Gate summary:** 3 / 4 conditions met.

**Decision:** Partial — document trade-offs and consider Approach B (N-hop walk) or KG enrichment per spec §9 Q2.
