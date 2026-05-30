# LoCoMo Few-shot bench results

> **Status: PENDING FULL RUN ON VPS**
>
> Adapters modified in PR `feat/few-shot-cross-bench`. Run instructions below.

## Design

Few-shot layer adds 3 category-specific in-context examples before the real question.
No additional LLM calls — prompt-only modification (gate 3: latency neutral).

Builds on SOTA-push Variant A (`--sota-push`):
- Session-date injection for temporal questions (same `session_date_map` logic)
- Explicit 'D Month YYYY' date format hint
- 3 examples per category (temporal / single_hop / multi_hop / adversarial / commonsense)

## Gate

1. F1 lift ≥ +3pp vs SOTA-push baseline (51.85%)
2. No category regression ≥ -5pp (adversarial floor: 65.78% - 5pp = 60.78%)
3. Latency neutral (no new LLM calls — prompt size only)
4. Cost ≤ +20% (prompt token overhead ~300 tokens/query on gpt-4.1-mini ≈ +$0.30/1986q)

## Baseline (SOTA push, PR #404)

| Category | n | F1 |
|---|---:|---:|
| temporal | 321 | 44.21% |
| single_hop | 841 | 55.18% |
| commonsense | 96 | 23.77% |
| multi_hop | 282 | 38.16% |
| adversarial | 446 | 65.78% |
| **Overall** | **1986** | **51.85%** |

## VPS run command

```bash
# Smoke 100q first (budget ~$0.10)
python3 eval/locomo/adapter_nox_mem.py \
    --locomo-json /root/.openclaw/fewshot-bench-<uuid>/data/locomo10.json \
    --workdir /root/.openclaw/fewshot-bench-<uuid>/locomo-work \
    --out /root/.openclaw/fewshot-bench-<uuid>/locomo-fewshot-smoke.jsonl \
    --api-port 18941 \
    --max-questions 100 \
    --seed 42 \
    --generator gpt-4.1-mini \
    --few-shot

# Full bench (n=1986, ~$0.80)
python3 eval/locomo/adapter_nox_mem.py \
    --locomo-json /root/.openclaw/fewshot-bench-<uuid>/data/locomo10.json \
    --workdir /root/.openclaw/fewshot-bench-<uuid>/locomo-work \
    --out /root/.openclaw/fewshot-bench-<uuid>/locomo-fewshot-full.jsonl \
    --api-port 18941 \
    --max-questions 0 \
    --generator gpt-4.1-mini \
    --few-shot
```

## Results

_To be filled after VPS run._

| Category | n | SOTA push F1 | Few-shot F1 | delta |
|---|---:|---:|---:|---:|
| temporal | 321 | 44.21% | TBD | TBD |
| single_hop | 841 | 55.18% | TBD | TBD |
| commonsense | 96 | 23.77% | TBD | TBD |
| multi_hop | 282 | 38.16% | TBD | TBD |
| adversarial | 446 | 65.78% | TBD | TBD |
| **Overall** | **1986** | **51.85%** | **TBD** | **TBD** |
