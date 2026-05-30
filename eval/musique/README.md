# MuSiQue Bench — nox-mem Extreme Multi-Hop Harness

> Eval harness for running nox-mem retrieval + gpt-4.1-mini single-shot
> answering on the [MuSiQue](https://github.com/StonyBrookNLP/musique) extreme
> multi-hop QA benchmark (Trivedi et al. TACL 2022, arxiv:2108.00573).
>
> Sibling of `eval/locomo/` (LoCoMo crossbench) and `eval/longmemeval/`
> (LongMemEval crossbench). Follows the **shared corpus_loader canonical
> pattern** (lesson cravada Sat 2026-05-24).

## Why MuSiQue

MuSiQue is the **hardest** standardized multi-hop QA benchmark. Unlike HotpotQA
where shortcut chains often work, MuSiQue authors specifically engineered
distractor paragraphs to defeat single-shot RAG:

- **2-4 sequential hops** required to reach the answer.
- **20 paragraphs per question**, of which only 2-4 are supporting; the rest
  are confusable distractors (same surface keywords, different entity).
- Vanilla RAG sits at ~15-25% F1; specialized iterative methods reach 35-40% F1
  (IRCoT, Trivedi et al. 2023).
- Paper's trained transformer baselines (Longformer EX(SA)) hit 49.7% F1
  on the answerable dev set.

For nox-mem this is the benchmark to flex our retrieval foundation against
extreme multi-hop. **Single-shot today**; **iterative (Q3 Iterative Retrieval)
predicted to close 50%+ of gap** to specialized RAG SOTA.

## Files

| File | Purpose |
|---|---|
| `adapter_nox_mem.py` | Per-question pipeline: ingest 20 paragraphs → vectorize → API search → gpt-4.1-mini answer |
| `lib/corpus_loader.py` | MuSiQue dataset parser; SINGLE SOURCE OF TRUTH for data shape |
| `lib/scorer.py` | Official MuSiQue answer F1/EM + support F1 (mirrors `metrics/answer.py`, `metrics/support.py`) |
| `lib/aggregate.py` | JSONL → results JSON + markdown w/ published-baseline table |
| `run-bench.sh` | Orchestrator: dataset → preflight → adapter → aggregate |
| `RESULTS-MUSIQUE.md` | Headline results (regenerated each run) |
| `RESULTS-MUSIQUE.json` | Machine-readable aggregate |
| `results/RESULTS-FULL-<n>q.json` | Full-dev snapshot artifacts |

## Setup

### Dataset

Auto-downloaded by `run-bench.sh` via `gdown` (Google Drive). Lives at
`/tmp/musique-repo/data/musique_ans_v1.0_dev.jsonl` (~2417 questions, dev set).

Manual fallback:

```bash
git clone --depth 1 https://github.com/StonyBrookNLP/musique.git /tmp/musique-repo
cd /tmp/musique-repo
pip install --user gdown
python3 -m gdown -O musique_v1.0.zip "https://drive.google.com/uc?id=1tGdADlNjWFaHLeZZGShh2IRcpO6Lv24h"
unzip -q musique_v1.0.zip
ls data/
```

### VPS prereqs

- `/usr/local/bin/nox-mem` (CLI) — entry point `dist/index.js`
- `/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js` — built API server
- `/root/.openclaw/.env` — must have `OPENAI_API_KEY` + `GEMINI_API_KEY`
- Port `18890` free (NOT `18802` — prod)

## Usage

### Smoke (100 questions, stratified by hop variant)

```bash
bash eval/musique/run-bench.sh smoke
```

Expected runtime: ~25-35 min (~14-20s/question on VPS 4 vCPU, dominated
by ingest + vectorize per fresh DB).

### Full musique_ans dev (~2417 questions)

```bash
bash eval/musique/run-bench.sh full
```

Expected runtime: ~12-18 hours. Use `tmux` + standalone script per
`feedback_long_running_batch_use_tmux`. Cost: ~$5-8 (well under $10 cap).

### Custom subset

```bash
bash eval/musique/run-bench.sh subset 500
```

### Resume after stall

```bash
bash eval/musique/run-bench.sh resume
```

Resumes from `--out` JSONL; skips already-completed `qid`s.

### Retrieval-only (no OpenAI generator)

```bash
NO_GENERATOR=1 bash eval/musique/run-bench.sh smoke
```

Emits `support_hit_at_10` instead of `answer_f1`. Useful when OpenAI quota
exhausted or for pure-retrieval ablation.

### Full (unanswerable) variant

```bash
DATASET=full bash eval/musique/run-bench.sh smoke
```

Switches to `musique_full_v1.0_dev.jsonl` (4834 questions, 50% answerable
/ 50% unanswerable for IDK-discrimination eval). Note: aggregation does
not yet compute `group_*` sufficiency metrics; only answer_f1 + support_f1.

## Phase H v2 baseline configuration

The adapter forces these env vars before launching the API server:

```
NOX_RERANKER_ENABLED=0       # no neural rerank (baseline)
NOX_TEMPORAL_PATH=shadow     # temporal spike shadow only
NOX_SALIENCE_MODE=shadow     # salience shadow only
NOX_API_PORT=18890           # isolated, not prod 18802
```

This matches the LoCoMo / EverMemBench / LongMemEval baselines for
cross-bench comparability.

## Safety guards

- `refuse_if_prod()` aborts if `NOX_DB_PATH` resolves to prod or if port =
  18802.
- Workdir MUST start with `/root/.openclaw/` or `/var/backups/` (op-audit
  ALLOWED_PREFIXES).
- Adapter calls `nox-mem ingest --allow-prod` only because workdir is
  isolated; flag bypasses the lint-style "don't ingest into prod" guard.
- No `--no-verify`; commits use `COMMIT_TO_NON_MAIN_OK=1` only on the
  feature branch.

## Cost expectations

| Mode | n questions | gen tokens (rough) | embed tokens (rough) | est. cost |
|---|---:|---:|---:|---:|
| Smoke (100q) | 100 | ~1.6M in / 800 out | ~150k | ~$0.65 |
| Subset 500 | 500 | ~8M in / 4k out | ~750k | ~$3.30 |
| Full (~2417q) | 2417 | ~38M in / 20k out | ~3.5M | ~$15 |

NOTE: Full-bench cost exceeds the $10 cap. Recommend running `subset 1500`
as the headline "competitive number" run, or splitting full into two
resume-able sessions and verifying cost mid-way.

## Honest framing

MuSiQue was specifically engineered to defeat single-shot RAG. Our baseline
is **nox-mem retrieval + gpt-4.1-mini single-shot answer generation** —
no iterative re-querying, no intermediate-hop reasoning, no decomposition.

Expected baseline: **20-40% answer F1**.

If we hit >30% on a stratified subset, that's competitive with mid-tier
specialized methods (IRCoT 35.8%, paper EE 42.3%). Anything >40% would be
notable for a single-shot system.

The headline framing for the PR is:
> nox-mem **single-shot** retrieval baseline on MuSiQue: X% answer F1.
> Q3 Iterative Retrieval (planned) predicted to close 50%+ of gap to
> specialized iterative SOTA (IRCoT 35.8% F1).

## Cross-bench portfolio (Lab Q1 2026)

| Benchmark | Harness | Status |
|---|---|---|
| EverMemBench | `eval/evermembench/` | Done — Phase H v2 51.68% (PR #372 + #377) |
| LongMemEval | `eval/longmemeval/` | Done — task acc 68.16% (PR #378) |
| LoCoMo | `eval/locomo/` | Done — gated (PR #396) |
| **MuSiQue** | **`eval/musique/`** | **This PR** |
| HotPotQA | `eval/hotpotqa/` | Parallel sibling (different agent) |

## References

- Trivedi, Balasubramanian, Khot, Sabharwal. *"MuSiQue: Multi-hop Questions via
  Single-hop Question Composition."* TACL 2022. arxiv:2108.00573.
  github.com/StonyBrookNLP/musique
- Trivedi, Balasubramanian, Khot, Sabharwal. *"Interleaving Retrieval with
  Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions."*
  ACL 2023. arxiv:2212.10509 (IRCoT, 35.8% F1 on MuSiQue subset).
- LoCoMo harness `eval/locomo/README.md` (template for this harness)
- LongMemEval crossbench `eval/longmemeval/run_crossbench.py` (template for
  per-question ingest pattern)
