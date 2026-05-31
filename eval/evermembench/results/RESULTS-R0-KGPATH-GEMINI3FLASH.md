# Wave 2 R0 Sanity — KG path retrieval standalone on Gemini-3-flash backbone

**Status:** PENDING — bench in flight, numbers will be filled on completion.

**Date:** 2026-05-31

**Branch / PR:** `feat/wave-2-r0-sanity-kg-gemini` / TBD

**Goal:** Validate backbone portability of KG path retrieval mechanism (PR #379).
PR #379 measured **+2.81pp F_MH lift** on gpt-4.1-mini. This R0 confirms the same
mechanism replicates on **Gemini-3-flash-preview** (D70 SOTA primary recommendation,
PR #397).

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

### Defensive preconditions (validated pre-dispatch)

- [x] `set -a; source /root/.openclaw/.env; set +a` before CLI
- [x] Preflight 1: `gemini-3-flash-preview` real 5-token chat completion (billing path)
- [x] Preflight 2: `gemini-2.5-flash` real 5-token chat completion (judge billing path)
- [x] `NOX_DB_PATH` isolated to per-batch RUN_DIR (no prod DB touch)
- [x] `NOX_ALLOW_PROD_INGEST=1` defense flag set
- [x] tmux session for long-running op (per `[[long-running-batch-use-tmux]]`)
- [x] Pre-warmed source DBs verified: chunks ≥ 10k, kg_entities ≥ 500, kg_relations ≥ 1.5k per batch

## Baseline References (already published)

### Gemini-3-flash bare (no KG, no other knobs) — D70 baseline, PR #397

| Metric | Value |
|---|---|
| Overall | **63.28%** |
| F_MH | **6.02%** |
| MA composite | **88.42%** |
| Source | `RESULTS-BACKBONE-MATRIX.json` |

### gpt-4.1-mini + KG path — Lab Q1 #4 / PR #379 (original measurement)

| Metric | Bare | KG path | Delta |
|---|---|---|---|
| Overall | ~51.7% | ~51.8% | +0.12pp |
| F_MH | 4.42% | 7.23% | **+2.81pp** |
| MA composite | ~88% | ~88% | ~neutral |
| Coverage (KG path triggered) | — | 90.84% | — |
| Source | Phase H v2 baseline | PR #379 RESULTS-PHASEKG-FULL.md | — |

## Predicted if KG path replicates +2.81pp

| Metric | Predicted | Note |
|---|---|---|
| Overall | ~63.40% | KG path neutral on overall (PR #379 pattern) |
| F_MH | ~8.83% | +2.81pp lift if mechanism backbone-invariant |
| MA composite | ~88.42% | Neutral on MA |
| Coverage | ~90.84% | Identical to PR #379 (DB unchanged) |

## Gate (HONEST — load-bearing for Tier 1 GO/NO-GO)

| F_MH lift | Decision |
|---|---|
| ≥ +1.5pp | **REPLICATES** → GO Tier 1 paralelo (IterB+KG / +AC / +MQ) |
| < +1.5pp | **NO-REPLICATE** → BLOCK Tier 1 dispatch, re-baseline single-stage knobs on Gemini first |

## Results (5-batch sequential)

**TBD — bench in flight.** Numbers fill on completion. Per-batch and aggregate.

### Per-batch breakdown

| Batch | Overall | F_MH | F_SH | F_TP | F_HL | MA_C | MA_P | MA_U | MA comp | Coverage | Cost ($) | Latency p50 (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 004 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 005 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 010 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 011 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 016 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| **Mean** | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| **95% CI** | TBD | TBD | — | — | — | — | — | — | TBD | — | — | — |

### Aggregate (5-batch mean)

| Metric | KG path Gemini-3-flash | Bare Gemini-3-flash (D70) | Delta | 95% CI |
|---|---|---|---|---|
| Overall | TBD | 63.28% | TBD | TBD |
| **F_MH** | TBD | **6.02%** | **TBD** | **TBD** |
| MA composite | TBD | 88.42% | TBD | TBD |
| Coverage | TBD | — | — | — |
| Cost / query | TBD | — | — | — |

## Gate verdict

**TBD.**

## Cross-references

- D70 backbone matrix Gemini-3-flash baseline: `RESULTS-BACKBONE-MATRIX.json`, PR #397
- Lab Q1 #4 KG path original (gpt-4.1-mini): PR #379, `RESULTS-PHASEKG-FULL.md`
- Q3 IterB Gemini POC: PR #419, `RESULTS-Q3-ITERB-POC.md`
- Wave 2 composability matrix plan: TBD link to ROADMAP entry

## Honest framing

- KG path is a **retrieval-stage** mechanism: rewrites top-k via 1-hop entity neighbor boost.
  Mechanism does NOT depend on the final-answer LLM. Backbone-invariance is the
  expected outcome.
- LoCoMo cross-bench (D72) demonstrated F_MH composition is **generation-bound**, not
  retrieval-bound, on dense-context corpora. KG path effect on EverMemBench is a
  retrieval signal recovery (1-hop neighbors of entity-mentioned chunks fill MH gaps
  the BM25/vector top-20 misses). Backbone Gemini-3-flash vs gpt-4.1-mini changes
  the **answer synthesis** but the **retrieved evidence set** should be identical
  modulo embedding-driven rank shuffles (here embed model unchanged at gemini-embedding-001).
- Therefore: if KG path lift **fails to replicate**, the most likely failure modes are
  (a) Gemini-3-flash synthesizes MH answers differently and the +2.81pp on gpt-4.1-mini
  was actually answer-side gain not retrieval-side (would invalidate D72 framing), or
  (b) measurement noise — 5-batch CI must include zero.
