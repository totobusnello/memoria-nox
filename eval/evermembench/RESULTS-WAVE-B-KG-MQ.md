# EverMemBench Phase KGMQ (Wave B composability) — phaseKGMQ-5batch

**Batches:** 004, 005, 010, 011, 016 (n=5)

## Headline

- **Phase KGMQ (Wave B composability) overall: 49.71%** (95% CI: 47.95–51.46%) (n=5 batches)
- vs **Phase H v2 (5-batch)** (51.68%): **-1.97 pp**
- vs **MemOS GPT-4.1-mini** (42.55%): **+7.16 pp**

## Sub-dimension breakdown

> MA_C / MA_P / MA_U are MANDATORY rows — per `[[memory-awareness-dimension-must-be-audited]]`.
> Regressions vs any baseline are highlighted in **bold** with ⚠️.

| sub-dim | dimension | Phase KGMQ (Wave B composability) mean | stdev | 95% CI | Δ vs Phase H v2 (5-batch) | Δ vs MemOS GPT-4.1-mini |
|---|---:|---:|---:|---:|---:|---:|
| **Overall** |  |  |  |  |  |  |
| overall | Overall | 49.71% | 1.41 pp | 47.95–51.46% | **-1.97 pp ⚠️** | +7.16 pp |
| **Fine-grained Recall** |  |  |  |  |  |  |
| F_SH | Fine-grained Recall | 71.30% | 5.81 pp | 64.09–78.51% | **-9.67 pp ⚠️** | -0.06 pp |
| F_MH | Fine-grained Recall | 8.02% | 3.14 pp | 4.12–11.93% | +4.81 pp | **-10.86 pp ⚠️** |
| F_TP | Fine-grained Recall | 15.67% | 5.22 pp | 9.19–22.14% | +0.67 pp | -0.00 pp |
| F_HL | Fine-grained Recall | 19.80% | 6.04 pp | 12.30–27.31% | **-2.88 pp ⚠️** | — |
| **Memory Awareness** |  |  |  |  |  |  |
| MA_C | Memory Awareness | 81.60% | 2.88 pp | 78.02–85.18% | **-3.00 pp ⚠️** | +11.70 pp |
| MA_P | Memory Awareness | 62.80% | 3.42 pp | 58.55–67.05% | **-2.60 pp ⚠️** | +10.81 pp |
| MA_U | Memory Awareness | 69.43% | 5.96 pp | 62.03–76.84% | **-0.60 pp ⚠️** | +24.28 pp |
| **Profile Understanding** |  |  |  |  |  |  |
| P_Style | Profile Understanding | 39.62% | 7.06 pp | 30.85–48.39% | -0.16 pp | +10.64 pp |
| P_Skill | Profile Understanding | 46.13% | 5.64 pp | 39.13–53.13% | **-3.64 pp ⚠️** | +13.59 pp |
| P_Title | Profile Understanding | 55.70% | 9.54 pp | 43.85–67.55% | -0.35 pp | +7.23 pp |

## Per-batch detail

| metric | 004 | 005 | 010 | 011 | 016 | mean | stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| overall | 49.36 | 51.80 | 49.60 | 49.92 | 47.85 | 49.71 | 1.41 |
| F_SH | 75.51 | 66.00 | 64.00 | 76.00 | 75.00 | 71.30 | 5.81 |
| F_MH | 8.00 | 12.00 | 4.00 | 10.00 | 6.12 | 8.02 | 3.14 |
| F_TP | 10.00 | 16.67 | 23.33 | 16.67 | 11.67 | 15.67 | 5.22 |
| F_HL | 15.38 | 14.67 | 29.49 | 17.95 | 21.52 | 19.80 | 6.04 |
| MA_C | 81.00 | 85.00 | 78.00 | 84.00 | 80.00 | 81.60 | 2.88 |
| MA_P | 57.00 | 66.00 | 64.00 | 64.00 | 63.00 | 62.80 | 3.42 |
| MA_U | 65.52 | 80.00 | 67.24 | 66.67 | 67.74 | 69.43 | 5.96 |
| P_Style | 45.95 | 46.43 | 38.71 | 29.17 | 37.84 | 39.62 | 7.06 |
| P_Skill | 55.56 | 44.19 | 43.48 | 46.51 | 40.91 | 46.13 | 5.64 |
| P_Title | 65.31 | 59.18 | 50.00 | 62.00 | 42.00 | 55.70 | 9.54 |

## Gate summary vs Phase H v2 (5-batch)

| sub-dim | mean Δ | CI lower Δ | verdict |
|---|---:|---:|---|
| overall | -1.97 pp | -3.73 pp | REJECT |
| F_SH | -9.67 pp | -16.88 pp | REJECT |
| F_MH | +4.81 pp | +0.91 pp | **SHIP** |
| F_TP | +0.67 pp | -5.81 pp | REJECT |
| F_HL | -2.88 pp | -10.38 pp | REJECT |
| MA_C | -3.00 pp | -6.58 pp | REJECT |
| MA_P | -2.60 pp | -6.85 pp | REJECT |
| MA_U | -0.60 pp | -8.00 pp | REJECT |
| P_Style | -0.16 pp | -8.93 pp | REJECT |
| P_Skill | -3.64 pp | -10.64 pp | REJECT |
| P_Title | -0.35 pp | -12.20 pp | REJECT |


## Composability Coverage (KG + MQ firing rate)

| batch | queries | mq_applied | kg_applied | both | avg sub-Q N | decompose p50 | kg p50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 626 | 610 | 594 | 579 | 4.00 | 913ms | 30ms |
| 005 | 610 | 610 | 505 | 505 | 4.00 | 882ms | 39ms |
| 010 | 623 | 622 | 608 | 607 | 4.00 | 880ms | 7ms |
| 011 | 633 | 632 | 618 | 617 | 4.00 | 844ms | 42ms |
| 016 | 629 | 626 | 529 | 527 | 4.00 | 822ms | 7ms |
| **TOTAL** | **3121** | **3100** (99.3%) | **2854** (91.4%) | **2835** (90.8%) | **4.00** | **863ms** | **29ms** |


## Sample Decompositions (for paper / sanity)

### Sample 1

**Original query:** After SQL optimization of the data submission API, what was the peak CPU usage observed during the final 300 concurrent user stress test?

**Sub-queries:**

- What was the peak CPU usage observed during the final stress test?
- What was the duration of the final stress test?
- How many concurrent users were simulated during the final stress test?
- Was the data submission API subjected to SQL optimization prior to the final stress test?

### Sample 2

**Original query:** In the competitive analysis task for the supply chain carbon footprint project, after Huilan Chen completed the analysis of key competitors (especially EcoTrace), which document management system did she upload the final report to?

**Sub-queries:**

- What is the competitive analysis task for the supply chain carbon footprint project?
- Which key competitors were analyzed, with a specific focus on EcoTrace?
- Who is Huilan Chen in the context of this project?
- What document management system was used to upload the final report after the competitor analysis?

### Sample 3

**Original query:** After completing the configuration of the production environment domain name and SSL certificate, where did Jing Lu upload the final Nginx configuration file and test report?

**Sub-queries:**

- What is the specific directory path where Jing Lu uploaded the final Nginx configuration file?
- What is the name of the final Nginx configuration file that Jing Lu uploaded?
- What is the specific directory path where Jing Lu uploaded the test report?
- What is the name of the test report that Jing Lu uploaded?

### Sample 4

**Original query:** After completing the analysis of the GHG Protocol and the differences across the manufacturing, retail, and energy sectors, what is the full title of the report that Peng Hou finally uploaded to Confluence?

**Sub-queries:**

- What is the GHG Protocol?
- What are the differences across the manufacturing, retail, and energy sectors regarding the GHG Protocol?
- What is the full title of the report Peng Hou uploaded to Confluence?
- Did Peng Hou complete the analysis of the GHG Protocol and its sector differences before uploading the report to Confluence?

### Sample 5

**Original query:** When discussing the design of calculation trigger APIs for the carbon emissions accounting platform, which optional parameter did Ruiqing Jiang suggest adding to flexibly calculate only specific emission categories?

**Sub-queries:**

- What is the purpose of the calculation trigger APIs in the carbon emissions accounting platform?
- What are the general design considerations for calculation trigger APIs?
- What specific optional parameter did Ruiqing Jiang suggest for the calculation trigger APIs?
- What is the intended functionality of the suggested optional parameter in relation to calculating specific emission categories?

### Sample 6

**Original query:** During the design process of the energy consumption monitoring system, when Guohua Yin reviewed the draft of the alarm list, what specific function did he suggest adding to help operations colleagues quickly pinpoint issues?

**Sub-queries:**

- What was the context of Guohua Yin's review of the alarm list draft?
- What specific aspect of the alarm list draft did Guohua Yin focus on during his review?
- What was the suggested addition by Guohua Yin to the alarm list?
- What was the intended benefit of Guohua Yin's suggested addition for operations colleagues?



## Wave B 4-Gate Composability Decision

| Gate | Pass | Observed |
|---|---|---|
| F_MH lift ≥ +5.5pp vs Phase H v2 (additivity floor) | FAIL | observed +4.81pp (8.02% vs H v2 3.21%) |
| F_MH ≥ Phase MQ alone (combo > strongest single knob) | PASS | observed +1.20pp (8.02% vs MQ 6.82%) |
| Overall regression ≤ MQ alone (-1.12pp) + 0.5pp tolerance | FAIL | observed -0.85pp (49.71% vs MQ 50.56%) |
| MA composite ≥ Phase MQ alone − 0.5pp tolerance | FAIL | observed -0.69pp (71.28% vs MQ 71.97%) |

**Gate summary:** 1 / 4 conditions met.

## Additivity Verification

| Quantity | Value |
|---|---:|
| Phase H v2 baseline F_MH | 3.21% |
| Phase KG sparse F_MH | 6.02% (+2.81pp) |
| Phase MQ alone F_MH | 6.82% (+3.61pp) |
| **Additive prediction** (KG + MQ stack) | **9.63%** |
| **Phase KGMQ actual** | **8.02%** |
| Additivity residual (actual − predicted) | **-1.61pp** |

**Interpretation: PARTIAL ADDITIVITY** — combo shows diminishing returns. Interaction penalty larger than 1pp tolerance. Document trade-off.

## Strategic Interpretation

- **MemOS F_MH gap closure:** 30.7% of the 15.67pp baseline gap (KG alone closed 17%, MQ alone closed 23%, additive prediction was 41%).
- **Cost:** ~$0.0001/query (decomposer) + $0 (KG SQL+regex).
- **Latency overhead:** ~863ms decompose + ~29ms KG = ~892ms total retrieval-side.
- **Composability firing rate:** 90.8% of queries had BOTH mechanisms active (mq_applied AND kg_applied).

## Comparative Table (vs siblings + MemOS)

| System | Overall | F_MH | Δ F_MH vs H v2 | MA mean | Cost/query |
|---|---:|---:|---:|---:|---:|
| Phase H v2 (baseline) | 51.68% | 3.21% | — | 73.34% | $0 |
| Phase KG sparse (PR #379) | 51.80% | 6.02% | +2.81pp | 73.78% | $0 |
| Phase MQ (PR #385) | 50.56% | 6.82% | +3.61pp | 71.97% | ~$0.0001/q |
| **Phase KGMQ (this run)** | **49.71%** | **8.02%** | **+4.81pp** | **71.28%** | ~$0.0001/q |
| Additive prediction | ~50.68% | ~9.63% | +6.42pp | — | — |
| MemOS GPT-4.1-mini (target) | 42.55% | 18.88% | +15.67pp | 55.68% | unknown |

**Decision:** REJECT composability default — mechanisms compete more than they compose. Document failure mode in paper §5.

## Implications for Paper §5

- **Composability nuance:** additive prediction overshot by -1.61pp. Paper §5 should document interaction effects + recommend single-knob deployment for multi-hop workloads.
