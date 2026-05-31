# HotPotQA SP-F1 LLM Extractor — Results

> **SP-F1 +5.96pp GATE PASS | joint_F1 +5.66pp GATE PASS**

## Summary

```
RESULTS (n=7405, HotPotQA distractor dev)

  ans_F1:              73.34%   (unchanged from PR #408)
  ans_EM:              59.10%

  --- Supporting Facts ---
  baseline  sp_F1:    55.28%   (token-overlap heuristic, PR #408)
  llm       sp_F1:    61.24%   (gpt-4.1-mini extractor)
  Δ sp_F1:          +5.96pp

  baseline  sp_EM:    4.24%
  llm       sp_EM:    26.10%

  --- Joint Metrics ---
  baseline  joint_F1: 42.95%
  llm       joint_F1: 48.61%
  Δ joint_F1:       +5.66pp

  baseline  joint_EM: 2.62%
  llm       joint_EM: 18.38%

  --- SP LLM Extraction Stats ---
  LLM calls:          7382  (99.7% of questions)
  Fallback (heuristic):23  (0.3%)
  Errors:             19
  Latency p50:        797ms p50
  Wall-clock:         119.4min
```

## Gate Evaluation

| Gate | Target | Result | Pass? |
|---|---|---|---|
| SP-F1 lift ≥ +5pp | ≥59.22% | 61.24% (+5.96pp) | PASS |
| Joint-F1 lift ≥ +3pp | ≥46.97% | 48.61% (+5.66pp) | PASS |
| Latency overhead ≤ +1s | ≤1000ms/q | 797ms p50 | PASS |
| Cost ≤ $3 for full bench | ≤$3 | ~$1.56 est. | PASS |

## Per Question Type

| Type | n | base sp_F1 | llm sp_F1 | Δ | base joint_F1 | llm joint_F1 | Δ | ans_F1 |
|---|---|---|---|---|---|---|---|---|
| bridge | 5918 | 52.93% | 57.82% | +4.89pp | 40.48% | 45.33% | +4.85pp | 71.40% |
| comparison | 1487 | 64.63% | 74.85% | +10.22pp | 52.81% | 61.68% | +8.87pp | 81.06% |

## Methodology

- **Input:** PR #408 JSONL (7405 answers already generated — no re-inference)
- **SP extractor:** `eval/hotpotqa/lib/sp_extractor.py`
- **Model:** gpt-4.1-mini @ temp=0, max_tokens=256
- **Fallback:** token-overlap heuristic on LLM error/timeout
- **Paragraph rendering:** chunk body split into sentences, capped at 12/para
- **Scoring:** official HotPotQA scorer (hotpot_evaluate_v1.py re-implementation)

## Competitive Position Update

| System | ans_F1 | sp_F1 | joint_F1 | Notes |
|---|---|---|---|---|
| DPR + FiD (SOTA reader ~2021) | 65-72 | 75-82 | 50-58 | specialized multi-hop |
| **nox-mem PR #408 baseline** | **73.37** | **55.29** | **42.97** | token-overlap SP heuristic |
| **nox-mem SP-LLM extractor (this PR)** | **73.34** | **61.24** | **48.61** | LLM SP + same ans |

> Output: `/root/.openclaw/hotpot-sp-bench-SPLLM01/RESULTS-FULL-7K-SP-LLM.jsonl`
