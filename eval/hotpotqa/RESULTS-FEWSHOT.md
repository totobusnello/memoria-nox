# HotPotQA Few-shot bench results

> **Status: PENDING FULL RUN ON VPS**
>
> Adapters modified in PR `feat/few-shot-cross-bench`. Run instructions below.

## Design

Few-shot layer adds 3 in-context examples (2 bridge + 1 comparison) before the real question.
No additional LLM calls — prompt-only modification (gate 3: latency neutral).

Examples cover:
- Bridge (entity answer): film director example
- Comparison (yes/no): country comparison example
- Bridge (place name): headquarters location example

## Gate

1. ans_F1 lift ≥ +3pp vs Phase H v2 baseline (73.37%)
2. No category regression ≥ -5pp (bridge floor: 71.42% - 5pp = 66.42%; comparison floor: 81.12% - 5pp = 76.12%)
3. Latency neutral (no new LLM calls — prompt size only)
4. Cost ≤ +20% (prompt token overhead ~250 tokens/query on gpt-4.1-mini ≈ +$1.40/7405q)

## Baseline (Phase H v2, PR #408)

| Metric | Value |
|---|---:|
| ans_F1 | 73.37% |
| ans_EM | 59.12% |
| ans_prec | 77.14% |
| ans_recall | 73.11% |
| sp_F1 | 55.29% |
| joint_F1 | 42.97% |

| Type | ans_F1 | sp_F1 |
|---|---:|---:|
| bridge | 71.42% | 52.94% |
| comparison | 81.12% | 64.67% |

## VPS run command

```bash
# Smoke 200q first (budget ~$0.05)
python3 eval/hotpotqa/adapter_nox_mem.py \
    --dataset /root/.openclaw/fewshot-bench-<uuid>/data/hotpot_dev_distractor_v1.json \
    --workdir /root/.openclaw/fewshot-bench-<uuid>/hotpotqa-work \
    --out /root/.openclaw/fewshot-bench-<uuid>/hotpotqa-fewshot-smoke.jsonl \
    --api-port 18942 \
    --n 200 \
    --shuffle \
    --seed 42 \
    --generator gpt-4.1-mini \
    --few-shot

# Full bench (n=7405, ~$2.00)
python3 eval/hotpotqa/adapter_nox_mem.py \
    --dataset /root/.openclaw/fewshot-bench-<uuid>/data/hotpot_dev_distractor_v1.json \
    --workdir /root/.openclaw/fewshot-bench-<uuid>/hotpotqa-work \
    --out /root/.openclaw/fewshot-bench-<uuid>/hotpotqa-fewshot-full.jsonl \
    --api-port 18942 \
    --n 0 \
    --generator gpt-4.1-mini \
    --few-shot
```

## Results

_To be filled after VPS run._

| Metric | Phase H v2 | Few-shot | delta |
|---|---:|---:|---:|
| ans_F1 | 73.37% | TBD | TBD |
| ans_EM | 59.12% | TBD | TBD |
| sp_F1 | 55.29% | TBD | TBD |
| joint_F1 | 42.97% | TBD | TBD |

| Type | H v2 ans_F1 | Few-shot ans_F1 | delta |
|---|---:|---:|---:|
| bridge | 71.42% | TBD | TBD |
| comparison | 81.12% | TBD | TBD |
