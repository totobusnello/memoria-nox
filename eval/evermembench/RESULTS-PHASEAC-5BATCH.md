# EverMemBench Phase AC — Adaptive Query Classifier 5-batch (Lab Q1 #1)

> **Status:** PENDING — auto-generated after parallel-phaseAC.sh completes.
> Run `python eval/evermembench/aggregate_phaseAC.py --run-dirs <5 RUN_DIRs>
> --output eval/evermembench/RESULTS-PHASEAC-5BATCH.md` after bench finishes
> and the placeholder content below will be replaced with real numbers.

This document is a placeholder skeleton; the live results are written by
`aggregate_phaseAC.py` after the 5-batch parallel run.

## Methodology

- **Implementation:** Option A heuristic classifier (spec PR #373 §2)
  - Pure-regex score over 6 features (entity_count / conjunctions /
    comparative / abstract_reasoning / token_count / temporal_chain)
  - PT-BR variants for São Paulo register (depois que / antes de / por que /
    como se compara / qual a diferença entre)
  - Threshold = 4 (per spec default)
  - Latency: <5 ms / query measured (target 1 ms in spec §1.4)
- **Backbone:** gpt-4.1-mini (OpenAI direct), cross-backbone parity bar
- **Judge:** gemini-2.5-flash (same as Phase D / H)
- **Adapter:** `phaseAC` mode (`eval/evermembench/adapter_nox_mem.py`)
- **Reranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (Phase G config)
- **Pre-warmed DBs:** Phase B winning runs (skip add+vectorize)
- **Parallelism:** 5 batches on ports 18830–18834
- **Batches:** 004, 005, 010, 011, 016 (matches Phase H v2 5-batch / Phase G 5-batch)
- **top_k:** 20 (per Phase D over-fetch standard)

## Comparison baselines

- **Phase H v2 5-batch** — gpt-4.1-mini, rerank OFF always, no classifier
  → 51.68% overall, F_MH 3.21%, MA mean 73.34%
- **Phase G 5-batch** — gemini, rerank ON always, no classifier
  → 61.26% overall, F_MH 6.83%, MA mean 79.59%
- **Phase D 5-batch** — gemini, rerank OFF, baseline
  → 62.22% overall, F_MH 5.22%, MA mean 83.14%
- **MemOS GPT-4.1-mini Table 4** — cross-backbone parity bar
  → 42.55% overall, F_MH 18.88%

## Gate criteria (spec PR #373 §5.3)

Per spec, all four conditions must be met to ship `NOX_ADAPTIVE_CLASSIFIER=1`
as default:

- **Gate A:** Overall ≥ Phase H v2 51.68% (cross-backbone parity preserved)
- **Gate B:** F_MH ≥ Phase H v2 3.21% (multi-hop not regressed; aim to lift
  toward Phase G 6.83% on the multi_hop-routed subset)
- **Gate C:** MA_C/P/U mean ≥ Phase H v2 73.34% (MA preserved on factual
  routes, -0.5 pp tolerance)
- **Gate D:** Activation rate within 10–60% audit band (spec §7.1)

## Pending results

Will be filled by `aggregate_phaseAC.py` post-run.

```
python eval/evermembench/aggregate_phaseAC.py \
    --run-dirs /root/.openclaw/evermembench-runs/phaseAC-004-XXX \
               /root/.openclaw/evermembench-runs/phaseAC-005-XXX \
               /root/.openclaw/evermembench-runs/phaseAC-010-XXX \
               /root/.openclaw/evermembench-runs/phaseAC-011-XXX \
               /root/.openclaw/evermembench-runs/phaseAC-016-XXX \
    --output eval/evermembench/RESULTS-PHASEAC-5BATCH.md \
    --json-output eval/evermembench/RESULTS-PHASEAC-5BATCH.json
```
