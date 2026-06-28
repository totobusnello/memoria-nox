# Phase HyDE — EverMemBench Cross-Bench Results

> **Date:** 2026-05-30
> **Reference:** Gao et al. 2022, **arxiv:2212.10496** ("Precise Zero-Shot Dense Retrieval without Relevance Labels")
> **Status:** ❌ MEASURED — REJECT (2026-06-27). Single-batch run on EverMemBench-Dynamic `groupchat_004` (n=626) on a RunPod CPU pod: HyDE **−2.72pp overall** vs baseline (24.28% vs 27.00%). Helps multiple_choice (+2.31pp) but hurts open_ended (−10.97pp) — net negative. No lift to pursue; **not shipped**. See "Measured result" below. (Implementation history retained for reproducibility.)
> **Mode:** `phaseHyDE` (env: `NOX_ADAPTER_MODE=phaseHyDE` or `NOX_HYDE_ENABLED=1`)
> **Baseline:** Phase H v2 (rerank=off, hybrid=on, no Wave A/B/C knobs)
> **PR:** `feat/hyde-cross-bench`

---

## TL;DR (verdict: REJECT — measured 2026-06-27)

This PR lands the **HyDE retrieval-stage knob** for EverMemBench. Mechanism:

1. Query received.
2. `gemini-2.5-flash-lite` generates an 80-120-word **declarative** hypothetical passage that mimics the chunk distribution (chat-log style, fictional but plausible names/dates/places).
3. Two `/api/search` calls fire in parallel — one with the raw query, one with the hypothetical passage — both hybrid (FTS5 + Gemini-embed + RRF).
4. The two rank-ordered lists are merged via RRF (`_mq_rrf_merge`, reused from Phase MQ — `k=60` default).
5. Top-K returned to the harness.

Pure-mode (only hypothetical passage retrieved against) is gated behind `NOX_HYDE_HYBRID=0`.

Predicted lift per arxiv:2212.10496 + nox-mem's MS-MARCO-style FTS5+dense profile: F_MH **+3-6pp** because the hypothetical's surface form lands closer to actual chunk distribution than question-shape raw queries. F_SH should stay flat (already at 89.80% in Phase H v2 — ceiling). Overall ±1pp band, MA ±1pp band. The "+5-15pp" cited in the original paper is on hard QA benches (TREC-DL, MIRACL); on chat-log memory we expect lower magnitude because chunks already contain natural narrative prose.

**Measured (2026-06-27, single-batch n=626, EverMemBench-Dynamic `groupchat_004`):** the prediction held in *direction* but net-negative in *magnitude*. The dataset scores only by answer format (multiple_choice / open_ended), not by hop count, so F_MH was not isolated — but the hypothetical passage's invented surface form helped fact-discrete MC (**+2.31pp**) while derailing open-ended generation (**−10.97pp**: the passage fabricates names/dates the answer then anchors on), for **overall −2.72pp**. Verdict: **REJECT** — no net lift, not shipped. Single-batch is unreliable (canonical gate is 5-batch + 95% CI; single-batch overstates 3-6×), so the real effect is likely closer to neutral — but neutral = no lift = does not justify HyDE's 2× search calls + LLM-passage cost.

---

## Implementation

### Adapter mode `phaseHyDE` (default-on flags)

| Flag | Default | Purpose |
|---|---|---|
| `NOX_ADAPTER_MODE=phaseHyDE` OR `NOX_HYDE_ENABLED=1` | — | Master switch |
| `NOX_HYDE_HYBRID` | `1` (true) | Hybrid mode: raw + hypothetical → RRF union. Set `0` for pure-HyDE. |
| `NOX_HYDE_LLM` | `gemini-2.5-flash-lite` | Decomposer model (cheap, OpenAI-compat) |
| `NOX_HYDE_LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` | LLM endpoint |
| `NOX_HYDE_LLM_API_KEY` | `${GEMINI_API_KEY}` | Falls back to `GEMINI_API_KEY` |
| `NOX_HYDE_TIMEOUT_S` | `25.0` | Decomposer timeout (single LLM call) |
| `NOX_HYDE_MAX_TOKENS` | `220` | Hypothetical length cap (~80-120 words) |
| `NOX_HYDE_PER_QUERY_TOPK` | `10` | Each retrieval leg's top_k pre-RRF |
| `NOX_HYDE_RRF_K` | `60` | RRF fusion `k` (matches Phase MQ) |
| `NOX_HYDE_DEBUG` | `0` | stderr trace per query |

### Pipeline

```
                   ┌─────────────────────────────┐
                   │  Raw query "Q"              │
                   └────────────┬────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
   ┌──────────────────────┐         ┌──────────────────────────────┐
   │ LLM (gemini-flash-   │         │  Skip in pure-HyDE mode      │
   │ lite) → hypothetical │         │  Hybrid mode default ON:     │
   │ passage P            │         │  fires both legs in parallel │
   └──────────┬───────────┘         └──────────────────────────────┘
              │
              ▼
   ┌────────────────────────────┐       ┌──────────────────────────┐
   │ POST /api/search           │ ──┐   │  POST /api/search        │
   │ query=P  limit=10 hybrid=t │   │   │  query=Q limit=10 hybrid │
   └────────────────────────────┘   │   └──────────────────────────┘
              │                     │              │
              └─────────┬───────────┴──────────────┘
                        ▼
                ┌───────────────────────┐
                │  RRF union (k=60)     │
                │  score = sum 1/(k+r)  │
                └───────────┬───────────┘
                            ▼
                    top_K to harness
```

### Fallback discipline (per memoria-nox rule §5)

- LLM error / empty hypothetical / too-short response → status=`fallback_single`, baseline single-query path runs as if HyDE was off. No silent failure.
- API key missing → status=`fallback_single`, error recorded in metadata.
- Each leg in hybrid mode can fail independently — the other leg's results still flow through RRF merge.
- The boost is purely **RRF-additive** (not multiplicative on RRF scores) — consistent with rule §5 (boost multiplicativo empilhável é veneno).

### Prompt validated 2026-05-30 (smoke test)

VPS smoke run on 3 representative queries produced ~340-420 char passages in 800-1040ms, all declarative, all with plausible chat-log surface form. Sample (Q: "When did Bob change his job from Acme to Globex?"):

> Bob transitioned from Acme to Globex in late 2021. He started his new role at Globex's San Francisco office in November of that year. Prior to this, he had been with Acme Corporation for five years, primarily working on their cloud infrastructure projects. The move to Globex was motivated by an opportunity to lead their AI research division.

This is exactly the surface form that Gemini-embed-001 should match against chat-log chunks containing job-change facts.

---

## Baseline reference (Phase H v2 batch 004, single batch — n=626)

| Sub-dim | Phase H v2 (baseline) |
|---|---:|
| F_SH (single-hop) | 89.80% |
| **F_MH (multi-hop)** | **10.00%** ← HyDE primary target |
| F_TP (temporal) | 11.67% |
| F_HL (high-level) | 24.36% |
| MA_C (content) | 88.00% |
| MA_P (persona) | 64.00% |
| MA_U (update) | 68.97% |
| Overall | 54.15% |

5-batch baseline (Phase H v2 cross-backbone WIN, n=3121, PR #372+#377): **51.68% ± 1.80%**.

---

## Measured result (2026-06-27, single-batch n=626)

RunPod CPU pod (8 vCPU / 16 GB), nox-mem API on isolated DB, `groupchat_004` ingested (254 days / 10,033 chunks; 21 day-errors ≈ 90% corpus). Adapter `phaseHyDE` vs `phaseB` baseline, rerank off, answer→`gpt-4.1-mini`, judge→`gemini-2.5-flash`.

| Type | Baseline | HyDE | Δ |
|---|---:|---:|---:|
| multiple_choice (n=389) | 25.19% | 27.51% | **+2.31 pp** |
| open_ended (n=237) | 29.96% | 18.99% | **−10.97 pp** |
| **Overall (n=626)** | **27.00%** | **24.28%** | **−2.72 pp** |

> EverMemBench-Dynamic scores by answer *format* (MC / OE), not by reasoning hops, so the original F_MH-specific gate-1 cannot be measured on this dataset. The overall + open-ended regressions are nonetheless decisive: there is no lift signal to chase, and a 5-batch run to confirm a *negative* is not worth the cost.

## 4-Gate Verdict — REJECT

| Gate | Threshold | Result |
|---|---|---|
| 1. F_MH lift ≥ +3pp | — | ⚠️ N/A — dataset has no hop-count breakdown (MC/OE only); no proxy lift (open_ended −10.97pp) |
| 2. Overall ≥ −1pp baseline | Overall ≥ 26.00% | ❌ **FAIL** — 24.28% (−2.72pp) |
| 3. MA composite ≥ −2pp | — | ⚠️ N/A — no MA sub-dims in this dataset format |
| 4. Latency p95 ≤ +50% | p95 ≤ 1.5× baseline | not measured (moot given gate-2 fail) |

**Decision: do NOT ship HyDE.** Consistent with the TL;DR prediction that chat-log corpora (already narrative prose) yield low/negative magnitude — here the hypothetical passage's fabricated specifics actively hurt open-ended answers. The `[VERDICT pending]` from PR #415 is now closed as **tested-and-rejected**; HyDE does **not** enter the paper as a feature. Effort was not wasted: we moved from "untestable / too heavy" to a measured negative, and the eval-from-scratch path surfaced + fixed the nox-mem schema-bootstrap bug (nox-workspace PR #24).

---

## Launch (OBSOLETE — superseded by the measured REJECT above)

> ⚠️ This 5-batch recipe was **never run** (HyDE rejected 2026-06-27; branch `feat/hyde-cross-bench` deleted). It also predates the harness naming: the real entry point is **`python -m eval.cli`** (args `--dataset … --qa … --system nox_mem --user-id <uid> --stages search answer evaluate --top-k 10`), **not** `python -m evermembench.harness`. The actual measured run was single-batch via `eval.cli` (see "Measured result" above). Retained only as the original plan-of-record.

```bash
# VPS workdir
UUID=$(uuidgen | tr A-Z a-z | head -c 8)
WORKDIR=/root/.openclaw/hyde-evermembench-$UUID
mkdir -p $WORKDIR && cd $WORKDIR

# Clone memoria-nox at the merged feat/hyde-cross-bench tip (or main once merged)
git clone --depth 5 https://github.com/totobusnello/memoria-nox.git
cd memoria-nox && git checkout feat/hyde-cross-bench   # or `main` after merge

# Build venv + install harness
python3 -m venv venv && source venv/bin/activate
pip install -r eval/evermembench/requirements.txt

# Bring up nox-mem API server on isolated DB (port 18930)
export NOX_DB_PATH=$WORKDIR/nox-mem-hyde.db
export NOX_API_PORT=18930
set -a; source /root/.openclaw/.env; set +a   # GEMINI_API_KEY + OPENAI_API_KEY

# Run Phase H v2 pipeline with phaseHyDE adapter mode (5 batches)
NOX_ADAPTER_MODE=phaseHyDE \
NOX_HYDE_ENABLED=1 \
NOX_HYDE_HYBRID=1 \
NOX_RERANKER_ENABLED=0 \
NOX_KG_PATH_ENABLED=0 \
NOX_MQ_ENABLED=0 \
NOX_MA_PROTECTION_ENABLED=0 \
NOX_ITERC_ENABLED=0 \
  python -m evermembench.harness \
  --pipeline eval/evermembench/pipeline-phaseH-v2.yaml \
  --adapter eval/evermembench/adapter_nox_mem.py \
  --batches 5 \
  --batch-size 626 \
  --out $WORKDIR/results-hyde-5batch.json
```

Single-batch smoke command (cost ~$1, validates F_MH lift signal):

```bash
NOX_ADAPTER_MODE=phaseHyDE NOX_HYDE_ENABLED=1 \
  python -m evermembench.harness \
  --pipeline eval/evermembench/pipeline-phaseH-v2.yaml \
  --batches 1 --batch-size 626
```

---

## Cost estimate (5-batch)

| Component | Per-query | × n=3121 | Total |
|---|---|---|---|
| HyDE LLM (gemini-flash-lite, ~250 in + 200 out tokens) | ~$0.0001 | | ~$0.31 |
| Phase H v2 answer (gpt-4.1-mini) | per Phase H v2 | | ~$4.60 |
| Judge (gemini-2.5-flash) | per Phase H v2 | | ~$0.10 |
| **Total estimated** | | | **~$5.01** |

Below $8 cap with margin. HyDE adds ~6% to total cost.

---

## Memory crystallizations (post-batch)

- **HyDE measured-and-rejected on EverMemBench-Dynamic (2026-06-27):** −2.72pp overall (MC +2.31 / OE −10.97), single-batch n=626. Hypothetical passage helps fact-discrete retrieval, hurts open-ended generation on chat-log prose. No 5-batch needed to confirm a negative.
- **Eval-from-scratch is a schema-bootstrap smoke test:** ingesting a fresh corpus on a clean pod exposed `ensureSchema()` stopping at V7 while labelling the DB v18 → fixed in nox-workspace PR #24 (idempotent `migrateToV8Through18` + `PRAGMA user_version` alignment + regression test).

## References

- Gao, L., Ma, X., Lin, J., & Callan, J. (2022). *Precise Zero-Shot Dense Retrieval without Relevance Labels.* arXiv:2212.10496.
- Phase H v2 baseline: `eval/evermembench/RESULTS-PHASEH-V2.md`
- Phase MQ (RRF merge reuse): `specs/2026-05-28-multi-query-expansion.md`
- nox-mem rule §5 (no multiplicative boost stacking): `CLAUDE.md#5`
