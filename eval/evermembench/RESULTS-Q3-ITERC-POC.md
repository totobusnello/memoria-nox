# Q3 IterC POC — Self-Ask 5-batch Results

**Verdict:** DOCUMENTED_INSUFFICIENT (2/4 gates pass)

Phase IterC POC implements Self-Ask (Press et al. 2022, arxiv:2210.03350) — the cheapest of Q3's three orchestration-stage candidates per PR #393 spec. Goal: validate whether moving the mechanism from retrieval-stage stacking (Waves A/B/C, F_MH ceiling ≈7.25%) to orchestration-stage opens a new lift axis on F_MH.

## Headline 5-batch metrics (sequential 004,005,010,011,016)

| Metric | Phase H v2 5-batch | Phase IterC 5-batch | Δ vs H v2 | MemOS GPT-4.1-mini | Δ vs MemOS |
|---|---:|---:|---:|---:|---:|
| overall | 51.68 | 53.13 | +1.45pp | 42.55 | +10.58pp |
| F_SH | 80.97 | 70.89 | -10.08pp | 71.36 | -0.47pp |
| F_MH | 3.21 | 2.81 | -0.40pp | 18.88 | -16.07pp |
| F_TP | 15.00 | 18.00 | +3.00pp | 15.67 | +2.33pp |
| F_HL | 22.68 | 58.52 | +35.84pp | n/a | n/a |
| MA_C | 84.60 | 81.80 | -2.80pp | 69.90 | +11.90pp |
| MA_P | 65.40 | 62.20 | -3.20pp | 51.99 | +10.21pp |
| MA_U | 70.03 | 62.95 | -7.08pp | 45.15 | +17.80pp |
| MA_composite | 73.34 | 68.98 | -4.36pp | n/a | n/a |
| P_Style | 39.78 | 33.10 | -6.68pp | 28.98 | +4.12pp |
| P_Skill | 49.77 | 47.00 | -2.77pp | 32.54 | +14.46pp |
| P_Title | 56.05 | 53.25 | -2.80pp | 48.47 | +4.78pp |

## 4-Gate verdict matrix

| Gate | Threshold | Observed | Pass |
|---|---|---|---|
| 1. F_MH lift | ≥ +2.00pp | -0.40pp | FAIL |
| 2. Overall regression | ≥ -2.00pp | +1.45pp | PASS |
| 3. MA composite | ≥ -3.00pp | -4.36pp | FAIL |
| 4. Latency p95 | ≤ 5000ms | 3688ms | PASS |

**Total:** 2/4 gates pass → **DOCUMENTED_INSUFFICIENT**.

**Decision rule:** 1-2/4 PASS = mechanism documented but insufficient. Inspect Set E to decide whether Q3 IterB (ReAct) should rerun with isolated knob or pivot.

## Set E (per-query instrumentation)

- Queries total: 3121
- IterC applied: 3120 (100.0%)
- Decomposer fallback (single-query): 1
- IterC errors total: 1
- Sub-answer errors total: 0

**Sub-question counts:**
- mean N = 3.00 (range 3-4)
- mean per-sub-Q overlap (Jaccard) = 0.180 (p50 0.128)
  - Low overlap → sub-Qs span distinct facets (Self-Ask sweet spot)
  - High overlap (>0.5) → decomposition redundant, less benefit expected

**Latency breakdown:**
- decompose: mean 645ms, p95 768ms
- retrieve (N parallel): mean 782ms, p95 1212ms
- synthesis (N parallel sub-answers): mean 1343ms, p95 1998ms
- total search_duration_ms: mean 2770ms, p50 2129ms, p95 3688ms, p99 21134ms

## Composition outlook with Wave A/B/C retrieval knobs

Self-Ask operates at the orchestration stage. Wave A/B/C mechanisms (KG path, MA-protection, MQ, rerank) operate at the retrieval stage. The hypothesis (per PR #393 spec §1) is that the two stages are partially orthogonal — so composition should be approximately additive minus an interaction penalty.

F_MH lift was zero or negative — Wave A/B/C ⊕ IterC composition irrelevant for this knob. Pivot to Q3 IterB (ReAct) directly per decision rule.

## Per-batch breakdown

| Batch | Overall | F_MH | F_SH | F_TP | MA_C | MA_P | MA_U |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 53.99 | 6.00 | 71.43 | 11.67 | 80.00 | 65.00 | 63.79 |
| 005 | 54.43 | 4.00 | 70.00 | 20.00 | 87.00 | 60.00 | 69.09 |
| 010 | 53.61 | 0.00 | 58.00 | 30.00 | 80.00 | 62.00 | 53.45 |
| 011 | 52.13 | 2.00 | 80.00 | 8.33 | 85.00 | 60.00 | 70.37 |
| 016 | 51.51 | 2.04 | 75.00 | 20.00 | 77.00 | 64.00 | 58.06 |

## Sample Self-Ask decompositions

### Sample 1
- **Query:** After SQL optimization of the data submission API, what was the peak CPU usage observed during the final 300 concurrent user stress test?
  1. *Sub-Q:* What was the date and time of the final 300 concurrent user stress test after SQL optimization of the data submission API?
     *Sub-A:* 2025-10-22 16:45:20
  2. *Sub-Q:* What was the peak CPU usage observed during the final 300 concurrent user stress test?
     *Sub-A:* UNKNOWN
  3. *Sub-Q:* Was the data submission API optimized using SQL before the final 300 concurrent user stress test?
     *Sub-A:* Got a lead! I split a large query into two smaller ones and aggregated the d

### Sample 2
- **Query:** In the competitive analysis task for the supply chain carbon footprint project, after Huilan Chen completed the analysis of key competitors (especially EcoTrace), which document management system did 
  1. *Sub-Q:* What is the name of the document management system used for the supply chain carbon footprint project?
     *Sub-A:* Jira and Confluence
  2. *Sub-Q:* Which document management system did Huilan Chen upload the final report to after completing the analysis of key competitors?
     *Sub-A:* UNKNOWN
  3. *Sub-Q:* Did Huilan Chen complete the analysis of key competitors, specifically EcoTrace, for the supply chain carbon footprint project?
     *Sub-A:* Yes, Huilan Chen completed the analysis report on key competitors, specifically focusing on EcoTrace.

### Sample 3
- **Query:** After completing the configuration of the production environment domain name and SSL certificate, where did Jing Lu upload the final Nginx configuration file and test report?
  1. *Sub-Q:* What is the name of the production environment domain name that was configured?
     *Sub-A:* UNKNOWN
  2. *Sub-Q:* What is the name of the SSL certificate that was configured?
     *Sub-A:* UNKNOWN
  3. *Sub-Q:* Where did Jing Lu upload the final Nginx configuration file and test report after completing the configuration of the production environment domain name and SSL certificate?
     *Sub-A:* UNKNOWN

### Sample 4
- **Query:** After completing the analysis of the GHG Protocol and the differences across the manufacturing, retail, and energy sectors, what is the full title of the report that Peng Hou finally uploaded to Confl
  1. *Sub-Q:* What is the full title of the report that Peng Hou uploaded to Confluence?
     *Sub-A:* UNKNOWN
  2. *Sub-Q:* Did Peng Hou complete the analysis of the GHG Protocol?
     *Sub-A:* UNKNOWN
  3. *Sub-Q:* Did Peng Hou complete the analysis of the differences across the manufacturing, retail, and energy sectors?
     *Sub-A:* Peng Hou did not complete the analysis; he was still refining the differences in industry templates for manufacturing and retail as of 2025-02-06.

### Sample 5
- **Query:** When discussing the design of calculation trigger APIs for the carbon emissions accounting platform, which optional parameter did Ruiqing Jiang suggest adding to flexibly calculate only specific emiss
  1. *Sub-Q:* What was the context of the discussion regarding calculation trigger APIs for the carbon emissions accounting platform?
     *Sub-A:* The discussion regarding calculation trigger APIs for the carbon emissions accounting platform was in the context of completing the API for triggering carbon emission calculation tasks, including retr
  2. *Sub-Q:* Which optional parameter did Ruiqing Jiang suggest adding to the calculation trigger APIs?
     *Sub-A:* task_id
  3. *Sub-Q:* What was the purpose of adding the suggested optional parameter to the calculation trigger APIs?
     *Sub-A:* UNKNOWN

## Ship recommendation

**DOCUMENT + DEFER.** Mechanism shows partial wins; gate-strict criterion not met. Consider deeper isolation analysis (Set E sub-Q overlap + per-sub-A error rate) before greenlighting IterB.
