# LoCoMo Few-shot bench results

> **Status: REJECTED (smoke gate failure) — verdict 2026-05-30 BRT**
>
> Few-shot smoke n=100 shows F1 regression vs SOTA-push baseline. Full n=1986 run NOT executed (smoke gate fail).
> Adapter shipped in PR #412; default OFF (opt-in only).

## TL;DR

- Smoke n=100 mean F1 **43.93%** (95% CI Wilson [32.80%, 51.79%])
- SOTA-push baseline (PR #404) overall F1 **51.85%** (n=1986)
- Δ = **-7.92pp** vs baseline — gate ≥+3pp **FAIL**
- 2 categories regress beyond -5pp floor: adversarial -5.78pp, temporal -5.56pp
- Retrieval evidence_hit@10 healthy at 68.37% (retrieval not the bottleneck)
- Cost: $0.039 generation, $0.000 embed (smoke run only)
- Latency: retrieval p50 720ms, generation p50 616ms (no new LLM calls, prompt-only)

**Verdict: REJECT for default. Keep `--few-shot` flag as opt-in research vector; smoke shows the in-context examples introduce category-specific noise (notably adversarial + temporal regression) that net-erodes overall F1 on gpt-4.1-mini at n=100.**

## Design

Few-shot layer adds 3 category-specific in-context examples before the real question.
No additional LLM calls — prompt-only modification (gate 3: latency neutral, confirmed).

Builds on SOTA-push Variant A (`--sota-push`):
- Session-date injection for temporal questions (same `session_date_map` logic)
- Explicit 'D Month YYYY' date format hint
- 3 examples per category (temporal / single_hop / multi_hop / adversarial / commonsense)

## Gates (executed)

| # | Gate | Threshold | Smoke result | Pass? |
|---|---|---|---|:---:|
| 1 | F1 lift vs SOTA-push baseline 51.85% | ≥ +3pp | -7.92pp (CI overlaps baseline upper bound) | FAIL |
| 2 | No category regression ≥ -5pp | floor for each | adversarial -5.78pp, temporal -5.56pp REGRESS | FAIL |
| 3 | Latency neutral | retrieval+generation steady | 720ms / 616ms p50 — OK | PASS |
| 4 | Cost ≤ +20% prompt | smoke n=100 = $0.039 | within budget | PASS |

## Smoke results (n=100, seed=42, gpt-4.1-mini)

### Overall

| Metric | Value |
|---|---:|
| mean F1 | 43.93% |
| accuracy (F1 ≥ 0.5) | 42.00% |
| F1 95% CI Wilson | [32.80%, 51.79%] |
| evidence_hit@10 | 68.37% |
| evidence_hit@20 | 74.49% |
| evidence_recall@10 | 59.69% |
| n_errors | 0 |

### Per-category vs baseline (PR #404 SOTA push)

| Category | n smoke | SOTA push F1 | Few-shot F1 | delta | gate (-5pp floor) |
|---|---:|---:|---:|---:|:---:|
| temporal | 20 | 44.21% | 38.65% | -5.56pp | REGRESS |
| single_hop | 20 | 55.18% | 58.67% | +3.49pp | OK |
| commonsense | 20 | 23.77% | 29.02% | +5.25pp | OK |
| multi_hop | 20 | 38.16% | 33.31% | -4.85pp | marginal |
| adversarial | 20 | 65.78% | 60.00% | -5.78pp | REGRESS |
| **Overall** | **100** | **51.85%** | **43.93%** | **-7.92pp** | **FAIL** |

### Retrieval per-category (evidence_hit@10)

| Category | n | hit@10 | recall@10 |
|---|---:|---:|---:|
| adversarial | 20 | 80.00% | 77.50% |
| commonsense | 18 | 55.56% | 38.89% |
| multi_hop | 20 | 80.00% | 57.50% |
| single_hop | 20 | 70.00% | 70.00% |
| temporal | 20 | 55.00% | 52.50% |

Retrieval is NOT the bottleneck — evidence is being found. Generation-side few-shot examples appear to bias gpt-4.1-mini toward over-extraction on adversarial (false positives) and confuse the date-format heuristic on temporal.

### Latency (ms)

| Stage | p50 | p95 | p99 | mean | n |
|---|---:|---:|---:|---:|---:|
| ingest_ms | 2697 | 3649 | 3649 | 2805 | 100 |
| vectorize_ms | 33410 | 36970 | 36970 | 32647 | 100 |
| retrieval_ms | 720 | 1070 | 1390 | 757 | 100 |
| generation_ms | 616 | 1476 | 2721 | 819 | 100 |

Latency gate PASS — no new LLM calls, prompt size delta absorbed by generator without measurable wall-time penalty.

### Cost

| Bucket | Value |
|---|---:|
| Generation input tokens | 96,451 |
| Generation output tokens | 467 |
| Embedding tokens | 0 |
| Cost gen (USD) | $0.0393 |
| Cost embed (USD) | $0.0000 |
| Cost total smoke (USD) | **$0.0393** |

Estimated full bench cost would be ~$0.78 (linear scaling 100→1986q). Not executed.

## Decision rationale

Per spec gate matrix:
- Gate 1 fail (F1 lift -7.92pp vs +3pp threshold)
- Gate 2 fail (2 categories regress ≥-5pp)

Spec says: "If smoke F1 ≥ 53% → run full 1986q." Smoke F1 = 43.93%. **Full run skipped.**

The few-shot prompts as constructed in PR #412 do not generalize to LoCoMo at n=100. Two failure modes observed:
1. **Adversarial regression** — examples appear to push gpt-4.1-mini toward extracting an answer when correct response is unanswerable.
2. **Temporal regression** — despite session_date_map being injected via SOTA-push, the 3 temporal examples seem to interfere with date-parsing heuristics gpt-4.1-mini learned from the base sota-push prompt.

PR #412 adapter remains opt-in via `--few-shot`; this run is the negative evidence justifying default OFF on LoCoMo.

## Run provenance

- VPS: 187.77.234.79
- Runner dir: `/root/.openclaw/fewshot-runner-32f11f2e-60e9-4833-a99e-77f3237ef`
- Adapter commit: `2c34b45` (PR #412 merged)
- Generator: gpt-4.1-mini-2025-04-14
- Dataset: locomo10.json (10 conversations, 100 questions sampled with seed=42)
- nox-mem binary: `/usr/local/bin/nox-mem` (prod-installed)
- Date executed: 2026-05-30 BRT
- Elapsed: 502s end-to-end (8.4min)

## Next vectors (not in this PR)

If revisiting few-shot LoCoMo in future:
1. Drop adversarial examples (let SOTA-push baseline carry that category)
2. Re-tune temporal examples to NOT contradict SOTA-push date-format hint
3. Test with gpt-4o or gpt-4o-mini (different in-context-learning profile vs gpt-4.1-mini)
4. Cross-check with the EverMemBench Lab Q1 #2 (MA opt-in pattern) for category-gated few-shot
