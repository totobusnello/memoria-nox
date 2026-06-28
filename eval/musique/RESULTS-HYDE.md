# Phase HyDE — MuSiQue Cross-Bench Results

> **Date:** 2026-05-30
> **Reference:** Gao et al. 2022, **arxiv:2212.10496**
> **Status:** ⛔ NOT RUN — superseded by EverMemBench REJECT (2026-06-27). The target bench (EverMemBench-Dynamic) measured **−2.72pp overall** for HyDE (see `../evermembench/RESULTS-HYDE.md`). MuSiQue was the stress-test bench ("if HyDE helps here, the mechanism is real beyond cosmetic") — but with the primary bench net-negative and retrieval already saturated here (support_hit@10 99.88%), the smoke run is moot. The prediction below (NEUTRAL on MuSiQue) is retained as the original hypothesis (never measured).
> **Flag:** `--hyde` (hybrid by default; `--hyde-pure` for pure)
> **Baseline:** MuSiQue Phase H v2 (rerank=off, hybrid=on, single-shot retrieval). n=2417 dev. answer F1 **58.62%**, support_hit@10 **99.88%**, support F1 66.30%.

---

## TL;DR

MuSiQue's retrieval is already near-saturated on the per-question 20-paragraph mini-corpus (`support_hit@10 = 99.88%`). Retrieval lift headroom is **0.12pp at the @10 ceiling** — HyDE almost certainly cannot improve retrieval here.

The interesting target is **answer-side F1** at higher hop counts. 4hop3 answers are F1 47.84% vs 2hop 59.42% — a 12pp drop driven by composition difficulty, not retrieval. HyDE may help marginally on the @5 / @3 tails where retrieval still drops slightly (~99.25% / lower), giving the answer model more on-topic context in the top positions for harder hop chains. But the cross-bench expectation is **NEUTRAL on MuSiQue** with potential 4hop F1 +1-2pp.

This is the most stress-test bench for HyDE — if HyDE helps **here**, the mechanism is real beyond cosmetic. If it doesn't, the EverMemBench + LoCoMo gains can't be attributed to spurious surface-form effects.

---

## Implementation

CLI flag added to `eval/musique/adapter_nox_mem.py`:

| Flag | Default | Purpose |
|---|---|---|
| `--hyde` | off | Enable Phase HyDE |
| `--hyde-pure` | off | Disable hybrid (pure HyDE only) |
| `--hyde-llm` | `gemini-2.5-flash-lite` | Decomposer model |
| `--hyde-max-tokens` | `220` | Hypothetical length cap |
| `--hyde-timeout` | `25` | Decomposer timeout (sec) |
| `--hyde-debug` | off | Per-question HyDE log |

QResult dataclass gained 8 HyDE telemetry fields, matching LoCoMo schema.

### MuSiQue-specific prompt tweak

`PHASE_HYDE_PROMPT` in `eval/musique/adapter_nox_mem.py` uses **Wikipedia-style paragraph framing** (vs chat-log framing in EverMemBench). This matches the actual MuSiQue corpus distribution — encyclopedic prose, not dialogue. The prompt instructs the LLM to mention "the chain-of-entities the multi-hop question implies" — useful at 3hop/4hop where the question itself hints at intermediate steps.

---

## Baselines (from `RESULTS-MUSIQUE.md`)

| Metric | Value |
|---|---:|
| n_total | 2417 |
| answer EM | 46.56% |
| **answer F1** | **58.62%** ← HyDE target |
| support F1 | 66.30% |
| support_hit@5 | 99.25% |
| **support_hit@10** | **99.88%** ← near-ceiling |
| accuracy (F1≥0.5) | 61.22% |

| Hop variant | n | answer F1 | support_hit@10 |
|---|---:|---:|---:|
| 2hop | 1251 | 59.42% | 99.76% |
| 3hop1 | 568 | 64.27% | 100.00% |
| 3hop2 | 192 | 52.93% | 100.00% |
| 4hop1 | 246 | 52.35% | 100.00% |
| 4hop2 | 64 | 50.01% | 100.00% |
| **4hop3** | **95** | **47.84%** | **100.00%** ← composition gap |

---

## 4-Gate Verdict (PENDING)

| Gate | Threshold | Result |
|---|---|---|
| 1. multi-hop (4hop1/2/3 avg) answer F1 lift ≥ +3pp | (≥50.07% baseline) | ⏳ |
| 2. Overall answer F1 ≥ -1pp baseline | F1 ≥ 57.62% | ⏳ |
| 3. support_hit@10 ≥ baseline (no regression) | ≥ 99.88% | ⏳ |
| 4. Latency p95 ≤ +50% (HyDE adds ~1s/q) | retrieval p95 ≤ 1.5× baseline (≤2334ms) | ⏳ |

---

## Launch (smoke 100q first; full 2417 conditional)

```bash
UUID=$(uuidgen | tr A-Z a-z | head -c 8)
WORKDIR=/root/.openclaw/hyde-musique-$UUID
mkdir -p $WORKDIR && cd $WORKDIR

git clone --depth 5 https://github.com/totobusnello/memoria-nox.git
cd memoria-nox && git checkout feat/hyde-cross-bench
python3 -m venv venv && source venv/bin/activate

set -a; source /root/.openclaw/.env; set +a

# Smoke 100q (cost ~$0.08, 1 batch)
python eval/musique/adapter_nox_mem.py \
  --workdir $WORKDIR/work-smoke \
  --out $WORKDIR/results-hyde-smoke.jsonl \
  --api-port 18932 \
  --top-k 20 \
  --max-questions 100 \
  --seed 42 \
  --generator gpt-4.1-mini \
  --hyde

# If smoke shows F_MH lift, full 2417 across 5 seeds
for SEED in 42 43 44 45 46; do
  python eval/musique/adapter_nox_mem.py \
    --workdir $WORKDIR/work-b$SEED \
    --out $WORKDIR/results-hyde-b$SEED.jsonl \
    --api-port 18932 \
    --top-k 20 \
    --max-questions 0 \
    --seed $SEED \
    --generator gpt-4.1-mini \
    --hyde
done
```

---

## Cost estimate (smoke + full 5-batch contingent)

| Stage | n × batches | Total |
|---|---|---:|
| Smoke 100 | 100 × 1 | ~$0.08 |
| Full 5-batch (if smoke passes gate 1) | 2417 × 5 = 12,085 | ~$3.62 |

Total max: **~$3.70**. Well below cap.

Gate-1 floor in smoke: 4hop answer F1 ≥ +3pp on the smoke sample (n≈4-8 from each 4hop bucket at proportional sampling) is too noisy — instead use **support_hit@5 ≥ baseline 99.25% + answer F1 deltacheck** as smoke proxy. Real verdict only at full 5-batch.

---

## References

- Gao et al. 2022, arxiv:2212.10496
- MuSiQue baseline: `eval/musique/RESULTS-MUSIQUE.md`
- MuSiQue paper: Trivedi et al. 2022 ("MuSiQue: Multihop Questions via Single-hop Question Composition")
