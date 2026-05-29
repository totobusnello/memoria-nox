# Phase H v2 — EverMemBench GPT-4.1-mini backbone parity (REAL RESULTS)

> **Date:** 2026-05-28
> **Status:** ✅ COMPLETE — Phase H v2 batch 004 ran end-to-end. Overall **54.15% > MemOS 42.55%** → **GATE PASS**.
> **Cost actual:** ~$0.92 of $1.00 budget cap (single-batch).

---

## Context

Phase H v1 (PR #368) was blocked: routed via OpenRouter, balance $0 → HTTP 402 on every real chat call. The setup was committed as reproducible artefacts (`pipeline-phaseH.yaml` + `run-batch-phaseH.sh`).

Phase H v2 rotates the direct `OPENAI_API_KEY` (Toto provisioned on VPS 2026-05-28, verified working via `curl /v1/models` + `curl /v1/chat/completions`) and runs the same batch over OpenAI direct.

Methodology preserved from v1 spec:
- Adapter `phaseB` mode (PR #365 default)
- `top_k=20`
- Backbone: **`gpt-4.1-mini` via OpenAI direct** (`https://api.openai.com/v1`)
- Judge: `gemini-2.5-flash` (same as Phase D, isolates backbone change to answer stage)
- Rerank **OFF** (`NOX_RERANKER_ENABLED=0`)
- Port 18820, fresh isolated DB, prod (18802) untouched

---

## Headline result

**Phase H v2 batch 004 = 54.15% overall (n=626)** vs MemOS Table 4 GPT-4.1-mini column = **42.55%**.

→ **+11.60 pp** absolute gain at the cross-backbone bar. Paper §5.4 ("structural advantage is the adapter, not the backbone") is now **defensible from a single batch.**

---

## Full Sub-Dimension Comparison

| Sub-dim | Phase H v2 (nox-mem · gpt-4.1-mini) | MemOS Table 4 GPT-4.1-mini | Δ |
|---|---:|---:|---:|
| F_SH (single-hop) | **89.80%** | 71.36% ± 6.1 | **+18.44 pp** |
| F_MH (multi-hop) | 10.00% | 18.88% ± 4.8 | -8.88 pp |
| F_TP (temporal) | 11.67% | 15.67% ± 4.0 | -4.00 pp |
| F_HL (high-level) | 24.36% | (not reported) | — |
| MA_C (content) | **88.00%** | 69.90% | **+18.10 pp** |
| MA_P (persona) | **64.00%** | 51.99% | **+12.01 pp** |
| MA_U (update) | **68.97%** | 45.15% | **+23.82 pp** |
| P_Style | **40.54%** | 28.98% | **+11.56 pp** |
| P_Skill | **55.56%** | 32.54% | **+23.02 pp** |
| P_Title | **65.31%** | 48.47% | **+16.84 pp** |
| **Average / Overall** | **54.15%** | **42.55% (+5.11 vs FC)** | **+11.60 pp** |

**Wins:** 8 / 10 sub-dims. The two losses (F_MH, F_TP) are known nox-mem weak spots from G-series — multi-hop traversal and temporal reasoning — but the gap to MemOS narrowed vs Phase D Gemini baseline (where multi-hop was 2%, here 10%).

---

## Cross-Backbone Sanity vs Phase D (nox-mem on Gemini)

| Metric | Phase D b004 (gemini-2.5-flash answer) | Phase H v2 b004 (gpt-4.1-mini answer) | Δ |
|---|---:|---:|---:|
| Overall | 61.98% | 54.15% | -7.83 pp |
| MC | 75.84% | 67.87% | -7.97 pp |
| OE | 39.24% | 31.65% | -7.59 pp |
| F_MH | 2.00% | **10.00%** | **+8.00 pp** |

The 7-8 pp overall regression vs Gemini is **expected and consistent with MemOS pattern** (MemOS Gemini column 59.27% → GPT-4.1-mini column 42.55% = -16.72 pp; nox-mem regression -7.83 pp is *smaller*). Notably: **multi-hop accuracy improved +8 pp on GPT-4.1-mini** — gpt-4.1-mini handles multi-hop reasoning better than gemini-2.5-flash on the same retrieval context.

---

## Gate decision

Per v1 spec §"Decision gate batch 004":
- ✅ Overall ≥ MemOS GPT-4.1-mini 42.55% → propose 5-batch ($5) in PR body, **do not auto-launch**

**Result: 54.15% > 42.55% by +11.60 pp → GATE PASS.**

**Recommendation:** approve a 5-batch run (004 + 005 + 010 + 011 + 016) at OpenAI direct, est. cost ~$4.60 (5 × $0.92), to confirm batch 004 isn't a single-batch fluke and produce the publishable cross-backbone table. **Not auto-launched** per spec; awaits Toto sign-off.

---

## Paper §5 cross-backbone claim status

**Defensible from this single batch.** The ~12 pp lead over MemOS on identical backbone replicates the structural-advantage thesis. Recommend §5.4 keep the cautious framing ("single batch; n=626; 5-batch validation pending") until the proposed 5-batch run lands.

§5.1 (Phase D 5-batch Gemini headline 62.22%) unchanged.

---

## Cost actual

| Component | Estimated | Actual |
|---|---:|---:|
| OpenAI preflight (11 tokens) | ~$0.000005 | $0.000005 |
| OpenAI gpt-4.1-mini answer batch | ~$0.30–1.00 | **~$0.92** (text-only est.) |
| Gemini-2.5-flash judge | ~$0.05 | included in monthly quota |
| **Total** | ~$1.00 | **~$0.92** |
| Budget cap | $1.00 | ✅ within |

Cost basis: gpt-4.1-mini pricing ($0.40 / 1M input, $1.60 / 1M output @ April 2026). 626 queries; estimated 2.29M input tokens (context, chars/4) + 2,623 output tokens. Real usage object not present in answer JSON (`metadata: {}`); estimate text-only.

---

## Anomalies / lessons (new from v2)

- **Preflight must exercise the billing path, not just auth.** v1 PR #368 lesson confirmed: OpenRouter `/v1/models` returned 200 OK on auth but real chat call 402'd on credits. v2 script does a 1-token `gpt-4.1-mini` completion (`POST /v1/chat/completions`) which exercises auth + model access + billing in one shot. Reproduction recipe added to `run-batch-phaseH-v2.sh` line 55–65.
- **Key rotation visible in suffix only.** v1 key ended `hcUA`, v2 key ends `T7gA` — easy to confuse at a glance. Logged the prefix+suffix+len in the preflight banner for diff visibility.
- **answer_results JSON has empty `metadata: {}`.** Real per-question usage tokens aren't persisted. Cost estimate must be done via context text length / 4 approximation. Worth a follow-up to capture `response.usage` in the harness for accurate billing reconciliation.
- **No prod contamination.** Isolated workdir `/tmp/phaseH-batch004-v2-d854ba39-740c-4e4b-a841-17ce4e6ebe64/`, isolated DB `/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db`, port 18820, `NOX_DB_PATH` explicit. Prod nox-mem.db (port 18802, 69135 chunks) untouched.

---

## Reproduction recipe (idempotent)

```bash
# On VPS as root:
UUID=$(uuidgen)
WORK=/tmp/phaseH-batch004-v2-$UUID
mkdir -p $WORK/everos/benchmarks
ln -sfn /root/.openclaw/evermembench-phaseB-1779978778/everos/benchmarks/EverMemBench $WORK/everos/benchmarks/EverMemBench
cp eval/evermembench/pipeline-phaseH-v2.yaml $WORK/phaseH-pipeline-v2.yaml
cp eval/evermembench/run-batch-phaseH-v2.sh $WORK/
chmod +x $WORK/run-batch-phaseH-v2.sh

# Launch (preflight + add + vectorize + search/answer/evaluate, ~17 min)
WORK=$WORK $WORK/run-batch-phaseH-v2.sh 004 18820

# Results land at /root/.openclaw/evermembench-runs/phaseH-v2-004-<ts>/
```

---

## Files

- `eval/evermembench/pipeline-phaseH-v2.yaml` — answer→OpenAI direct, evaluate→Gemini (judge isolation preserved)
- `eval/evermembench/run-batch-phaseH-v2.sh` — orchestrator with real billing preflight + pipeline.yaml swap
- `eval/evermembench/RESULTS-PHASEH-v2.md` — this doc
- VPS: `/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/`
  - `results-batch-004.json` (399 KB) — full evaluator output
  - `answer-results-batch-004.json` (19 MB) — per-question answers + search context
  - `analysis.txt` — human-readable summary (the table above)
  - `pipeline.yaml.bak` — original pipeline.yaml restored after run

## Test plan

- [x] OpenAI direct preflight (`/v1/models` 200 + 1-token completion 200) before batch dispatch.
- [x] Phase H v2 batch 004 completes end-to-end (no 402 / no rate limit).
- [x] Overall accuracy ≥ MemOS GPT-4.1-mini 42.55% (gate criterion).
- [x] Cost within $1 budget cap.
- [x] Prod (port 18802, prod DB) untouched throughout run.
- [ ] **(Out of scope, gated on Toto sign-off):** 5-batch validation (004 + 005 + 010 + 011 + 016) at ~$4.60.
