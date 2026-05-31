# HotPotQA Few-shot FULL — REJECT default

**Bench:** HotPotQA dev-distractor FULL (n=7405)
**Mode:** Few-shot prompting (gpt-4.1-mini, NOX_FEWSHOT_ENABLED=1)
**Wallclock:** 25220s = 7h00m
**Errors:** 3/7405 (0.04%)
**Source aggregator:** `eval/hotpotqa/lib/aggregate.py`
**Runner workdir:** `/root/.openclaw/fewshot-runner-32f11f2e/`
**Completed:** 2026-05-30 20:17 UTC

## Headline (vs PR #408 baseline ans_F1 73.37%)

| Metric | Baseline | Few-shot FULL | Δ |
|---|---:|---:|---:|
| ans_EM | 58.96% | 58.99% | +0.03pp (noise) |
| **ans_F1** | **73.37%** | **73.10%** | **-0.27pp** ❌ |
| SP_EM | 4.24% | 4.24% | unchanged |
| SP_F1 | 55.29% | 55.30% | +0.01pp |
| joint_EM | 2.66% | 2.66% | unchanged |
| joint_F1 | 42.97% | 42.85% | -0.12pp |

## Verdict — REJECT default

3/3 metrics are within ±0.3pp sampling noise. Smoke n=200 had shown +9.05pp ans_F1 lift, but full n=7405 mean-reverts to noise. **Smoke-overstated lift confirmed; full bench shows no real effect.**

Same pattern as Phase G rerank smoke vs 5-batch (see `[[single-batch-gates-unreliable-5x-overstate]]`) — sample-bias lift collapses on larger n.

## Mechanism interpretation

Few-shot prompting (3 manually curated worked examples in system prompt) attempted to teach gpt-4.1-mini "how to reason over distractor paragraphs by composing bridge entities." Hypothesized lift mechanism: better template-following + reduced ambiguity in bridge extraction.

**Why it didn't generalize on full bench:**
- gpt-4.1-mini is already strong on HotPotQA-style reasoning (zero-shot 73.37% above DPR+FiD SOTA band)
- 3 examples = too narrow a regime to shift the per-question accuracy distribution
- Distractor paragraphs vary too widely; templates don't transfer

## Latency footprint

| Metric | Value |
|---|---:|
| retrieval p50 | 743ms |
| retrieval p95 | 1273ms |
| generation p50 | 539ms |
| generation p95 | 1054ms |
| ingest p50 | 221ms |

No meaningful latency penalty from few-shot examples (system prompt adds ~600 tokens). Cost similar to baseline.

## Library preserved

Few-shot harness in `eval/hotpotqa/adapter_nox_mem.py` + `eval/locomo/adapter_nox_mem.py` (PR #412 merged). Both default OFF. Reusable for future benchmarks where few-shot might still help (untested e.g. SQuAD, TriviaQA, NaturalQuestions).

Activate via:
```bash
NOX_FEWSHOT_ENABLED=1 bash run-bench.sh
```

## Cross-bench correlation

LoCoMo Few-shot (PR #416): F1 49.18% → 43.93% = **-5.25pp REGRESSION** on full.
HotPotQA Few-shot (this): ans_F1 -0.27pp = **noise**.

Both REJECT default. Few-shot mechanism doesn't help on benchmarks where gpt-4.1-mini already performs at frontier. Hypothesis for future: few-shot may help on harder OOD or low-resource benchmarks; defer testing until such bench arises.

## Wave 1 Sat 2026-05-30 final scoreboard

| Track | Verdict | Mechanism |
|---|---|---|
| ✅ Q3 IterB ReAct Gemini-3 (PR #419) | SHIP_OPT_IN | F_MH +2.01pp clean lift |
| ✅ HotPotQA SP-F1 LLM extractor (PR #413) | SHIP both gates | joint_F1 +5.66pp |
| ❌ Few-shot LoCoMo F1 (PR #416) | REJECT | -5.25pp regression |
| ❌ Few-shot HotPotQA (this) | REJECT noise | -0.27pp within sampling |
| ❌ LoCoMo temporal-aware (PR #417) | REJECT default | +0.21pp marginal, 87.5% queries no-date |
| ⏳ HyDE (PR #415) | pending | conflict resolution Sun |
| ⏸️ Adaptive top_k | aborted | agent truncated output, no full bench |

## How to apply

1. **No GTM messaging change** — REJECT means no claim to publish.
2. **Lesson cravar:** `[[few-shot-noise-on-full-distractor-bench]]` — few-shot reverts to noise on full HotPotQA when base backbone already strong.
3. **Library kept** — gated opt-in for future bench experimentation.
4. **Wave 2 design implication:** prioritize mechanisms that change retrieval/orchestration (like IterB ReAct, KG path), not pure prompt engineering, on benches where backbone is already strong.

## Source
- Runner: `/root/.openclaw/fewshot-runner-32f11f2e-60e9-4833-a99e-77f3237ef`
- Raw jsonl: 13MB (preserved on VPS for audit)
- Aggregator output: `RESULTS-FEWSHOT-FULL.json` (this directory)
