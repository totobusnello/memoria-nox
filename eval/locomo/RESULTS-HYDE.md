# Phase HyDE — LoCoMo Cross-Bench Results

> **Date:** 2026-05-30
> **Reference:** Gao et al. 2022, **arxiv:2212.10496**
> **Status:** ⛔ NOT RUN — superseded by EverMemBench REJECT (2026-06-27). The target bench (EverMemBench-Dynamic) measured **−2.72pp overall** for HyDE (helps MC +2.31pp, hurts open-ended −10.97pp; see `../evermembench/RESULTS-HYDE.md`). With the primary bench net-negative, running LoCoMo to confirm a likely-negative is not worth the cost. The prediction below is retained as the original hypothesis (never measured).
> **Flag:** `--hyde` (hybrid mode by default; add `--hyde-pure` for pure-HyDE)
> **Baseline:** LoCoMo Phase H v2 (rerank=off, hybrid=on, no Wave A/B/C). `n=1986`. Constrained-gen F1 50.38%, retrieval evidence_hit@10 74.52% (per `RESULTS-LOCOMO.md`).
> **PR:** `feat/hyde-cross-bench`

---

## TL;DR

LoCoMo's retrieval ceiling is `evidence_hit@10 = 74.52%`. The naive→constrained-gen jump (+15.48pp F1) showed verbosity was real but composition gap remained. HyDE targets the **retrieval side** — the unrecovered 25.48% of evidence misses. Predicted lift: retrieval `evidence_hit@10` +2-4pp + downstream F1 +1-3pp.

Multi-hop F1 39.29% is the primary target — HyDE helps when the question's surface form is far from the chunk distribution.

---

## Implementation

CLI flag added to `eval/locomo/adapter_nox_mem.py`:

| Flag | Default | Purpose |
|---|---|---|
| `--hyde` | off | Enable Phase HyDE retrieval-stage knob |
| `--hyde-pure` | off | Disable hybrid (pure HyDE — hypothetical only) |
| `--hyde-llm` | `gemini-2.5-flash-lite` | Decomposer model |
| `--hyde-max-tokens` | `220` | Hypothetical length cap |
| `--hyde-timeout` | `25` | Decomposer timeout (sec) |
| `--hyde-debug` | off | Log HyDE status per QA |

### Pipeline (per QA)

1. `hyde_generate_hypothetical(qa.augmented_question)` → declarative passage P
2. **Hybrid (default):** sequential `search_api(raw)` + `search_api(P)`, both top_k, RRF-union via `hyde_rrf_merge` (k=60), truncate to top_k
3. **Pure (`--hyde-pure`):** single `search_api(P)`, no merge
4. On LLM failure → `hyde_status="fallback_single"`, baseline single-query path runs

QAResult dataclass gained 8 HyDE telemetry fields (`hyde_applied`, `hyde_status`, `hyde_error`, `hyde_generate_ms`, `hyde_retrieve_ms`, `hyde_hypothetical_chars`, `hyde_hypothetical_preview`, `hyde_hybrid`) — exposed in JSONL for downstream scorer aggregation.

### Sync HyDE helper

LoCoMo adapter uses `urllib` (sync) not `aiohttp` — so HyDE helper is sync. Per QA: 1 LLM call (sequential) + 1-2 search_api calls (sequential). Hybrid adds one extra `/api/search` call vs baseline. Per query overhead ≈ 1× LLM + 1× extra search ≈ 1.0-1.3s.

---

## Baselines (from `RESULTS-LOCOMO.md`)

| Run | Metric | Value |
|---|---|---:|
| Phase H v2 retrieval-only | evidence_hit@10 | 74.52% |
| Phase H v2 constrained-gen | overall F1 | 50.38% |
| Phase H v2 constrained-gen | single_hop F1 | 55.41% |
| Phase H v2 constrained-gen | **multi_hop F1** | **39.29%** ← HyDE target |
| Phase H v2 constrained-gen | temporal F1 | 28.27% |
| Phase H v2 constrained-gen | commonsense F1 | 21.86% |
| Mem0 SOTA | overall F1 | 66.88% |

---

## 4-Gate Verdict (PENDING)

| Gate | Threshold | Result |
|---|---|---|
| 1. multi_hop F1 lift ≥ +3pp | mh F1 ≥ 42.29% | ⏳ |
| 2. Overall ≥ -1pp baseline | F1 ≥ 49.38% | ⏳ |
| 3. evidence_hit@10 ≥ +0pp (no regression) | ≥ 74.52% | ⏳ |
| 4. Latency p95 ≤ +50% (HyDE adds ~1s) | retrieval p95 ≤ 1.5× baseline | ⏳ |

---

## Launch (Sun morning slot)

```bash
# VPS workdir
UUID=$(uuidgen | tr A-Z a-z | head -c 8)
WORKDIR=/root/.openclaw/hyde-locomo-$UUID
mkdir -p $WORKDIR && cd $WORKDIR

git clone --depth 5 https://github.com/totobusnello/memoria-nox.git
cd memoria-nox && git checkout feat/hyde-cross-bench
python3 -m venv venv && source venv/bin/activate
pip install -r eval/locomo/requirements.txt 2>/dev/null || true

set -a; source /root/.openclaw/.env; set +a

# Single batch (validates signal, ~$0.20)
python eval/locomo/adapter_nox_mem.py \
  --locomo-json data/locomo10.json \
  --workdir $WORKDIR/work \
  --out $WORKDIR/results-hyde-b1.jsonl \
  --api-port 18931 \
  --top-k 20 \
  --max-questions 0 \
  --seed 42 \
  --generator gpt-4.1-mini \
  --hyde

# Full 5-batch (vary --seed 42..46)
for SEED in 42 43 44 45 46; do
  python eval/locomo/adapter_nox_mem.py \
    --locomo-json data/locomo10.json \
    --workdir $WORKDIR/work-b$SEED \
    --out $WORKDIR/results-hyde-b$SEED.jsonl \
    --api-port 18931 \
    --top-k 20 \
    --max-questions 0 \
    --seed $SEED \
    --generator gpt-4.1-mini \
    --hyde
done
```

---

## Cost estimate (5-batch full)

| Component | Per-QA | × n=1986 × 5 | Total |
|---|---|---|---|
| HyDE LLM (gemini-flash-lite) | ~$0.0001 | 9,930 | ~$0.99 |
| Answer gen (gpt-4.1-mini constrained) | ~$0.0003 | 9,930 | ~$2.98 |
| **Total estimated** | | | **~$3.97** |

Below $8 cap. HyDE adds ~25% to total cost.

---

## References

- Gao et al. 2022, arxiv:2212.10496
- LoCoMo baseline: `eval/locomo/RESULTS-LOCOMO.md`
- LoCoMo F1 SOTA push (variant A): `eval/locomo/RESULTS-LOCOMO-SOTA-PUSH.md`
