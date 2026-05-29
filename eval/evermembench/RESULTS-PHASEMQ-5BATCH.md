# EverMemBench Phase MQ (Lab Q1 #3) — phaseMQ-5batch

**Batches:** 004, 005, 010, 011, 016 (n=5)

## Headline

- **Phase MQ (Lab Q1 #3) overall: 50.56%** (95% CI: 48.98–52.15%) (n=5 batches)
- vs **Phase H v2 (5-batch)** (51.68%): **-1.12 pp**
- vs **MemOS GPT-4.1-mini** (42.55%): **+8.01 pp**

## Sub-dimension breakdown

> MA_C / MA_P / MA_U are MANDATORY rows — per `[[memory-awareness-dimension-must-be-audited]]`.
> Regressions vs any baseline are highlighted in **bold** with ⚠️.

| sub-dim | dimension | Phase MQ (Lab Q1 #3) mean | stdev | 95% CI | Δ vs Phase H v2 (5-batch) | Δ vs MemOS GPT-4.1-mini |
|---|---:|---:|---:|---:|---:|---:|
| **Overall** |  |  |  |  |  |  |
| overall | Overall | 50.56% | 1.28 pp | 48.98–52.15% | **-1.12 pp ⚠️** | +8.01 pp |
| **Fine-grained Recall** |  |  |  |  |  |  |
| F_SH | Fine-grained Recall | 76.54% | 10.22 pp | 63.85–89.23% | **-4.43 pp ⚠️** | +5.18 pp |
| F_MH | Fine-grained Recall | 6.82% | 5.40 pp | 0.12–13.53% | +3.61 pp | **-12.06 pp ⚠️** |
| F_TP | Fine-grained Recall | 14.33% | 2.24 pp | 11.56–17.11% | **-0.67 pp ⚠️** | **-1.34 pp ⚠️** |
| F_HL | Fine-grained Recall | 22.15% | 4.67 pp | 16.36–27.95% | **-0.53 pp ⚠️** | — |
| **Memory Awareness** |  |  |  |  |  |  |
| MA_C | Memory Awareness | 81.00% | 1.87 pp | 78.68–83.32% | **-3.60 pp ⚠️** | +11.10 pp |
| MA_P | Memory Awareness | 66.80% | 3.49 pp | 62.46–71.14% | +1.40 pp | +14.81 pp |
| MA_U | Memory Awareness | 68.09% | 7.76 pp | 58.46–77.71% | **-1.94 pp ⚠️** | +22.94 pp |
| **Profile Understanding** |  |  |  |  |  |  |
| P_Style | Profile Understanding | 38.13% | 11.00 pp | 24.47–51.79% | **-1.65 pp ⚠️** | +9.15 pp |
| P_Skill | Profile Understanding | 46.11% | 3.93 pp | 41.23–50.99% | **-3.66 pp ⚠️** | +13.57 pp |
| P_Title | Profile Understanding | 56.07% | 8.99 pp | 44.91–67.23% | +0.02 pp | +7.60 pp |

## Per-batch detail

| metric | 004 | 005 | 010 | 011 | 016 | mean | stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| overall | 51.12 | 51.64 | 48.96 | 51.66 | 49.44 | 50.56 | 1.28 |
| F_SH | 85.71 | 70.00 | 64.00 | 88.00 | 75.00 | 76.54 | 10.22 |
| F_MH | 10.00 | 14.00 | 4.00 | 0.00 | 6.12 | 6.82 | 5.40 |
| F_TP | 11.67 | 16.67 | 13.33 | 13.33 | 16.67 | 14.33 | 2.24 |
| F_HL | 25.64 | 20.00 | 28.21 | 16.67 | 20.25 | 22.15 | 4.67 |
| MA_C | 78.00 | 81.00 | 81.00 | 82.00 | 83.00 | 81.00 | 1.87 |
| MA_P | 61.00 | 67.00 | 69.00 | 70.00 | 67.00 | 66.80 | 3.49 |
| MA_U | 60.34 | 78.18 | 60.34 | 72.22 | 69.35 | 68.09 | 7.76 |
| P_Style | 48.65 | 50.00 | 32.26 | 35.42 | 24.32 | 38.13 | 11.00 |
| P_Skill | 48.89 | 39.53 | 47.83 | 48.84 | 45.45 | 46.11 | 3.93 |
| P_Title | 65.31 | 53.06 | 48.00 | 66.00 | 48.00 | 56.07 | 8.99 |

## Gate summary vs Phase H v2 (5-batch)

| sub-dim | mean Δ | CI lower Δ | verdict |
|---|---:|---:|---|
| overall | -1.12 pp | -2.70 pp | REJECT |
| F_SH | -4.43 pp | -17.12 pp | REJECT |
| F_MH | +3.61 pp | -3.09 pp | REJECT |
| F_TP | -0.67 pp | -3.44 pp | REJECT |
| F_HL | -0.53 pp | -6.32 pp | REJECT |
| MA_C | -3.60 pp | -5.92 pp | REJECT |
| MA_P | +1.40 pp | -2.94 pp | REJECT |
| MA_U | -1.94 pp | -11.57 pp | REJECT |
| P_Style | -1.65 pp | -15.31 pp | REJECT |
| P_Skill | -3.66 pp | -8.54 pp | REJECT |
| P_Title | +0.02 pp | -11.14 pp | REJECT |


## MQ Coverage & Latency

| batch | queries | mq_applied | fallback | error | avg sub-Q N | decompose p50 | decompose p95 | retrieve p50 | pre-dedup avg | unique avg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 004 | 626 | 623 | 3 | 3 | 4.00 | 1052ms | 2965ms | 1461ms | 38.6 | 28.9 |
| 005 | 610 | 602 | 8 | 8 | 4.00 | 1054ms | 2190ms | 1281ms | 38.7 | 28.4 |
| 011 | 633 | 610 | 23 | 23 | 4.00 | 1266ms | 5295ms | 2519ms | 38.6 | 28.3 |
| 016 | 629 | 625 | 4 | 4 | 4.00 | 1032ms | 2528ms | 1696ms | 38.5 | 28.3 |
| **TOTAL** | **2498** | **2460** (98.5%) | **38** (1.5%) | **38** (1.5%) | **4.00** | **1085ms** | **3248ms** | **1677ms** | — | — |


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

**Original query:** After Weijun Xue announced the completion of the "Health Records and Chronic Disease Management System" user manual, what was the version number of the document he released?

**Sub-queries:**

- Who is Weijun Xue?
- What is the "Health Records and Chronic Disease Management System"?
- What does it mean for a user manual to be completed?
- What was the version number of the document released after the completion announcement?



## Lab Q1 #3 Gate Decisions (vs Phase H v2 5-batch)

| Gate | Pass | Observed |
|---|---|---|
| F_MH lift ≥ +3pp (5-batch) | ✅ | observed +3.61pp (6.82% vs 3.21%) |
| Overall regression ≤ -1pp | ❌ | observed -1.12pp (50.56% vs 51.68%) |
| MA dim regression ≤ -2pp (avg of MA_C, MA_P, MA_U) | ✅ | observed -1.38pp (71.96% vs 73.34%) |
| Latency p50 ≤ 2× baseline (decompose overhead) | ✅ | observed 1.68× baseline (+1085ms decompose p50) |

**Gate summary:** 3 / 4 conditions met.

### Comparative table (vs siblings)

| System | Overall | F_MH | Δ F_MH vs Phase H v2 | Cost/query |
|---|---:|---:|---:|---:|
| Phase H v2 (baseline) | 51.68% | 3.21% | — | $0 |
| Phase MQ (this run) | 50.56% | 6.82% | +3.61pp | ~$0.0001/q LLM |
| MemOS (target) | 42.55% | 18.88% | +15.67pp | unknown |

**Decision:** Partial — document trade-off and ship opt-in (env-gated `NOX_MQ_ENABLED=1`).

## Composability Hooks (Wave B)

- **MQ + KG path:** if both fire on multi-hop queries, RRF score from MQ union and additive KG boost are non-conflicting. Run combined ablation in Wave B with adapter mode `phaseMQ` + `NOX_KG_PATH_ENABLED=1`.
- **MQ + rerank (Phase G):** rerank operates on the final candidate set; if MQ produces a richer pool, rerank can extract bridge facts. Risk: MQ may dilute top-rank relevance pre-rerank.
- **MQ + adaptive classifier (Lab Q1 #1):** classifier routes only multi-hop queries through MQ → zero-overhead for single-hop, full lift on multi-hop. This is the spec §4.5 default deployment.
