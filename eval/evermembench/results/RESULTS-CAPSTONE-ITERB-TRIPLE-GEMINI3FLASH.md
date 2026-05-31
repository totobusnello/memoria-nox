# Wave 2 Phase 2 Capstone — IterB ReAct + Wave C Triple Gemini-3-flash

**Status:** RUNNING (results pending bench completion)
**Spec:** Tests if orchestration-stage stacking (IterB ReAct wrapping Wave C triple retrieval per round) breaks the retrieval-stage F_MH ceiling on Gemini-3-flash backbone.

## Architecture Note (Critical)

The adapter at `eval/evermembench/adapter_nox_mem.py` was **deliberately designed in PR #419** (IterB POC) to short-circuit MQ/KG/MAP/rerank when IterB is on. See comment at lines 2261-2263:

> `# Phase MQ / IterC / KG / MAP / rerank are NOT stacked on top —`
> `# POC isolates orchestration-stage ReAct signal vs Phase H v2.`

For this capstone, the adapter was patched to remove the `not iterb_used_path` guards at lines 2906 (KG boost) and 3063 (cross-encoder rerank), allowing KG + MAP + rerank to **layer** on top of IterB's RRF-merged candidate pool. MQ stays guarded because IterB subsumes its role (per-round retrieve IS sub-query decomposition).

This is the most architecturally sound interpretation of "IterB + Wave C triple composability."

## Test Config

| Parameter | Value |
|---|---|
| Final-answer backbone | `gemini-3-flash-preview` |
| ReAct orchestrator | `gemini-2.5-flash-lite` (per spec, NOT default gpt-4.1-mini) |
| Judge | `gemini-2.5-flash` |
| Adapter mode | `phaseTriple` (KG+MAP+rerank composability) |
| IterB override | `NOX_ITERB_ENABLED=1` |
| Rerank model | `BAAI/bge-reranker-v2-m3` (force-set; bypasses Xenova default) |
| KG path | enabled, KG-extracted DBs (phaseKG-XXX, 560-624 entities/batch) |
| MAP protection | enabled, KG-anchor mode |
| MQ | disabled (subsumed by IterB per-round retrieve) |
| Batches | 004 / 005 / 010 / 011 / 016 (n=3121, frozen since #397) |
| Max rounds | 5 |
| Per-round top-k | 10 |
| Cost ceiling | $0.01/query |

## Baselines (Load-Bearing)

| Baseline | Source | F_MH | Overall | MA composite |
|---|---|---:|---:|---:|
| IterB-alone Gemini-3-flash | PR #419 D74 | 8.03% | 62.70% | 84.89% |
| Gemini-3-flash bare | PR #397 D70 | 6.02% | 63.28% | 88.42% |
| MemOS GPT-4.1-mini Table 4 | paper | 3.21% | 42.55% | — |

## Honest Gate (Decides D75 + Phase 2 Verdict)

| Outcome | Condition (vs IterB-alone) | Verdict |
|---|---|---|
| F_MH ≥+1.5pp | composability lifts ceiling | SHIP_DEFAULT_CANDIDATE |
| F_MH +1.0pp to +1.5pp | similar to D74 IterB pattern | SHIP_OPT_IN |
| F_MH 0 to +1pp | orchestration-stage also bounded | CLOSED_NO_GAIN |
| F_MH <0 | mechanism conflict | INTERFERENCE (paper insight) |

## Results — PENDING

Will be populated by `aggregate_capstone_5batch.py` once 5-batch sequential run completes.

### Per-batch (placeholder)

| Batch | Overall | F_MH | F_SH | F_TP | F_HL | MA_C | MA_P | MA_U | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 004 | pending | | | | | | | | |
| 005 | pending | | | | | | | | |
| 010 | pending | | | | | | | | |
| 011 | pending | | | | | | | | |
| 016 | pending | | | | | | | | |
| **Mean** | | | | | | | | | |
| **95% CI** | | | | | | | | | |

### Set E IterB instrumentation (placeholder)

- IterB applied %: pending (target 99%+)
- Mean rounds: pending (PR #419 baseline 4.25)
- Termination distribution: pending
- Round-2 chunk overlap Jaccard: pending (PR #419 baseline 0.257)
- KG applied %: pending
- Rerank applied %: pending
- MAP applied %: pending

### Verdict

Pending bench completion.

## References

- PR #419 D74 — IterB ReAct Gemini-3-flash baseline (8.03% F_MH ceiling break)
- PR #397 D70 — Backbone Matrix Gemini-3-flash bare (6.02% F_MH)
- PR #399 — Wave C Triple gpt-4.1-mini standalone (Triple +4.02pp vs Phase H v2)
- PR #423 — R0 KG path Gemini-3-flash sanity (NO_REPLICATE)
- PR #424 — AC re-baseline Gemini-3-flash (NO_REPLICATE marginal)
- PR #425 — MQ re-baseline Gemini-3-flash (borderline +1.21pp)

## Strategic Implication

This capstone is the final Wave 2 experiment testing if **orchestration-stage stacking** can break the F_MH ceiling that **retrieval-stage stacking** (Wave A/B/C) cannot break on Gemini-3-flash. The outcome refines our understanding of where the EverMemBench F_MH ceiling lives:

- **If composability lifts F_MH** → ceiling is at *single-stage retrieval*, not orchestration; suggests broader F_MH lever via richer per-round retrieval (HyDE candidate, multi-stage reasoners)
- **If composability doesn't lift** → F_MH ceiling structural at corpus/query level; ReAct alone (PR #419) is the canonical F_MH lever; further gains require benchmark or generation-stage changes
- **If interference** → mechanism conflict; important paper finding on what NOT to stack
