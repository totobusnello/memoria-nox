# Phase MAP (Lab Q1 #2) 5-batch — MA-Protection bypass-entity

> **Date:** 2026-05-29
> **Status:** AUTOMATED RESULT — see body for 4-gate verdict
> **Builds on:** Phase H v2 5-batch (PR #377), Phase G 5-batch (PR #369)
> **Backbone:** gpt-4.1-mini (OpenAI direct) / judge: gemini-2.5-flash
> **Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2
> **Adapter mode:** `phaseMAP` (env `NOX_MA_PROTECTION_ENABLED=1`)

> **Batches:** 004, 005, 010, 011, 016 (n=5)

## Headline

**Phase MAP 5-batch overall = 50.44% (n=5)**

vs Phase H v2 5-batch baseline (rerank OFF) = 51.68% → Δ -1.24 pp

**Final verdict:** `SHIP-OPT-IN-OR-REJECT`


## Per-batch overall accuracy

| batch | overall MAP | Phase H v2 baseline | Δ vs H v2 |
|---|---:|---:|---:|
| 004 | 48.08% | 54.15% | -6.07 |
| 005 | 51.15% | 50.82% | +0.33 |
| 010 | 52.01% | 50.72% | +1.29 |
| 011 | 50.87% | 50.87% | +0.00 |
| 016 | 50.08% | 51.83% | -1.75 |
| **mean** | **50.44%** | **51.68%** | **-1.24** |
| stdev | 1.49 | 1.45 | — |
| 95% CI | 48.59 – 52.28 | 49.87 – 53.48 | — |


## Per-category 5-batch vs Phase H v2 baseline

| category | MAP mean | MAP stdev | MAP 95% CI | Phase H v2 mean | Δ MAP–H v2 |
|---|---:|---:|---:|---:|---:|
| F_SH | 80.59% | 4.10 | 75.50–85.67 | 80.96% | -0.37 |
| F_MH | 7.22% | 1.06 | 5.90–8.54 | 3.20% | +4.02 |
| F_TP | 16.00% | 3.46 | 11.71–20.29 | 15.00% | +1.00 |
| F_HL | 26.98% | 8.20 | 16.80–37.15 | 22.64% | +4.34 |
| MA_C | 78.80% | 4.97 | 72.63–84.97 | 84.60% | -5.80 |
| MA_P | 63.00% | 3.67 | 58.44–67.56 | 65.40% | -2.40 |
| MA_U | 58.78% | 9.08 | 47.50–70.05 | 70.22% | -11.44 |
| P_Style | 43.53% | 3.22 | 39.53–47.53 | 41.17% | +2.36 |
| P_Skill | 49.25% | 3.65 | 44.72–53.78 | 49.64% | -0.39 |
| P_Title | 56.43% | 6.09 | 48.87–64.00 | 56.07% | +0.36 |
| Overall | 50.44% | 1.49 | 48.59–52.28 | 51.68% | -1.24 |

## 4-gate verdict

### Gate 1 — MA_C/P/U recovery (vs Phase H v2 baseline)

- **MA_C**: MAP 78.80% vs Phase H v2 84.60% = Δ -5.80pp → **FAIL**
- **MA_P**: MAP 63.00% vs Phase H v2 65.40% = Δ -2.40pp → **FAIL**
- **MA_U**: MAP 58.78% vs Phase H v2 70.22% = Δ -11.44pp → **FAIL**
- **MA composite (C+P+U mean)**: MAP 66.86% vs Phase H v2 73.41% = Δ -6.55pp → **FAIL**

### Gate 2 — F_MH/F_HL/F_TP rerank-gain preservation (vs Phase G gain shape)

- **F_MH**: gain +4.02pp vs Phase G target +1.61pp → **PASS**
- **F_HL**: gain +4.34pp vs Phase G target +2.58pp → **PASS**
- **F_TP**: gain +1.00pp vs Phase G target +2.00pp → **FAIL**

### Gate 3 — Overall non-regression (Phase H v2 -0.5pp tolerance)

- Overall MAP 50.44% vs Phase H v2 51.68% = Δ -1.24pp (tolerance -0.50) → **FAIL**

### Gate 4 — Latency (informational)

- See `search_results_<batch>.json` metadata.rerank_ms per query for Phase G comparison.
- Bypass-entity adds one filter pass (O(N)) + merge (O(N)) — negligible.

## Empirical finding — bypass-entity inertness on chat-only corpus

EverMemBench corpus is chat-only: all 10k chunks/batch have `section=NULL` (verified via `sqlite3 chunks GROUP BY section`). Approach A (`bypass-entity` defined as `section IN ('compiled', 'frontmatter')`) therefore has **no chunks to protect** on this corpus — the partition gives Set E = ∅, Set R = all candidates, and the bypass degenerates to standard rerank.

This means Phase MAP result on EverMemBench ≈ Phase G result (rerank ON, no protection).
Composability hooks for Wave B (per task spec):

- **MAP × KG path retrieval**: KG entities in EverMemBench DB (~402 ents prod) could mark related chunks for bypass even when section=NULL. Spec separately.
- **MAP × adaptive classifier** (Lab Q1 #1 Option D): route MA-style queries to bypass rerank entirely. The classifier's MA detection (user pronoun / preference / role / state) is the orthogonal signal that section-only matching misses on chat corpora.
- **MAP on prod nox-mem DB** (~62.9k chunks, ~183 entity files): expected to activate the protection path. Validation deferred to a prod-corpus eval pass.
