# EverMemBench Phase KG (Lab Q1 #4) — phaseKG-5batch

**Batches:** 004, 005, 010, 011, 016 (n=5)

## Headline

- **Phase KG (Lab Q1 #4) overall: 51.80%** (95% CI: 50.27–53.34%) (n=5 batches)
- vs **Phase H v2 (5-batch)** (51.68%): **+0.12 pp**
- vs **MemOS GPT-4.1-mini** (42.55%): **+9.25 pp**

## Sub-dimension breakdown

> MA_C / MA_P / MA_U are MANDATORY rows — per `[[memory-awareness-dimension-must-be-audited]]`.
> Regressions vs any baseline are highlighted in **bold** with ⚠️.

| sub-dim | dimension | Phase KG (Lab Q1 #4) mean | stdev | 95% CI | Δ vs Phase H v2 (5-batch) | Δ vs MemOS GPT-4.1-mini |
|---|---:|---:|---:|---:|---:|---:|
| **Overall** |  |  |  |  |  |  |
| overall | Overall | 51.80% | 1.23 pp | 50.27–53.34% | +0.12 pp | +9.25 pp |
| **Fine-grained Recall** |  |  |  |  |  |  |
| F_SH | Fine-grained Recall | 81.37% | 5.99 pp | 73.94–88.80% | +0.40 pp | +10.01 pp |
| F_MH | Fine-grained Recall | 6.02% | 3.15 pp | 2.11–9.93% | +2.81 pp | **-12.86 pp ⚠️** |
| F_TP | Fine-grained Recall | 14.67% | 5.19 pp | 8.22–21.11% | -0.33 pp | **-1.00 pp ⚠️** |
| F_HL | Fine-grained Recall | 22.13% | 4.19 pp | 16.93–27.34% | **-0.55 pp ⚠️** | — |
| **Memory Awareness** |  |  |  |  |  |  |
| MA_C | Memory Awareness | 84.60% | 1.14 pp | 83.18–86.02% | +0.00 pp | +14.70 pp |
| MA_P | Memory Awareness | 66.60% | 4.98 pp | 60.42–72.78% | +1.20 pp | +14.61 pp |
| MA_U | Memory Awareness | 70.15% | 11.28 pp | 56.15–84.16% | +0.12 pp | +25.00 pp |
| **Profile Understanding** |  |  |  |  |  |  |
| P_Style | Profile Understanding | 39.88% | 5.48 pp | 33.07–46.69% | +0.10 pp | +10.90 pp |
| P_Skill | Profile Understanding | 47.88% | 4.99 pp | 41.68–54.07% | **-1.89 pp ⚠️** | +15.34 pp |
| P_Title | Profile Understanding | 55.25% | 7.84 pp | 45.52–64.98% | **-0.80 pp ⚠️** | +6.78 pp |

## Per-batch detail

| metric | 004 | 005 | 010 | 011 | 016 | mean | stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| overall | 53.19 | 50.66 | 51.04 | 51.03 | 53.10 | 51.80 | 1.23 |
| F_SH | 87.76 | 78.00 | 76.00 | 88.00 | 77.08 | 81.37 | 5.99 |
| F_MH | 10.00 | 6.00 | 2.00 | 8.00 | 4.08 | 6.02 | 3.15 |
| F_TP | 8.33 | 20.00 | 13.33 | 11.67 | 20.00 | 14.67 | 5.19 |
| F_HL | 21.79 | 18.67 | 28.21 | 17.95 | 24.05 | 22.13 | 4.19 |
| MA_C | 86.00 | 85.00 | 84.00 | 83.00 | 85.00 | 84.60 | 1.14 |
| MA_P | 67.00 | 60.00 | 66.00 | 66.00 | 74.00 | 66.60 | 4.98 |
| MA_U | 68.97 | 81.82 | 51.72 | 74.07 | 74.19 | 70.15 | 11.28 |
| P_Style | 40.54 | 39.29 | 48.39 | 33.33 | 37.84 | 39.88 | 5.48 |
| P_Skill | 51.11 | 39.53 | 52.17 | 48.84 | 47.73 | 47.88 | 4.99 |
| P_Title | 65.31 | 46.94 | 60.00 | 56.00 | 48.00 | 55.25 | 7.84 |

## Gate summary vs Phase H v2 (5-batch)

| sub-dim | mean Δ | CI lower Δ | verdict |
|---|---:|---:|---|
| overall | +0.12 pp | -1.41 pp | REJECT |
| F_SH | +0.40 pp | -7.03 pp | REJECT |
| F_MH | +2.81 pp | -1.10 pp | REJECT |
| F_TP | -0.33 pp | -6.78 pp | REJECT |
| F_HL | -0.55 pp | -5.75 pp | REJECT |
| MA_C | +0.00 pp | -1.42 pp | REJECT |
| MA_P | +1.20 pp | -4.98 pp | REJECT |
| MA_U | +0.12 pp | -13.88 pp | REJECT |
| P_Style | +0.10 pp | -6.71 pp | REJECT |
| P_Skill | -1.89 pp | -8.09 pp | REJECT |
| P_Title | -0.80 pp | -10.53 pp | REJECT |


## KG Coverage & Latency

| batch | queries | kg_applied | with_entity | with_neighbor | with_boost | kg_ms p50 | kg_ms p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 626 | 594 | 594 | 591 | 99 | 48.16ms | 99.98ms |
| 005 | 610 | 505 | 505 | 505 | 88 | 104.51ms | 260.10ms |
| 010 | 623 | 608 | 608 | 602 | 125 | 6.94ms | 20.67ms |
| 011 | 633 | 618 | 618 | 612 | 140 | 88.98ms | 230.15ms |
| 016 | 629 | 529 | 529 | 525 | 71 | 11.42ms | 37.92ms |
| **TOTAL** | **3121** | **2854** (91.4%) | **2854** (91.4%) | **2835** (90.8%) | **523** (16.8%) | — | — |


## Lab Q1 #4 Gate Decisions (vs Phase H v2 5-batch)

| Gate | Pass | Observed |
|---|---|---|
| F_MH lift ≥ +2pp (5-batch) | ✅ | observed +2.81pp (6.02% vs 3.21%) |
| MA lift ≥ +1pp (avg of MA_C, MA_P, MA_U) | ❌ | observed +0.44pp (73.78% vs 73.34%) |
| Overall non-regression (≥ 0pp) | ✅ | observed +0.12pp (51.80% vs 51.68%) |
| Coverage ≥ 30% queries with ≥1 neighbor | ✅ | observed 90.84% (2835/3121) |

**Gate summary:** 3 / 4 conditions met.

**Decision:** Partial — document trade-offs and consider Approach B (N-hop walk) or KG enrichment per spec §9 Q2.
