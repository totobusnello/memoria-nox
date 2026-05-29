# LoCoMo Cross-Bench Harness (Python)

Cross-bench validation of nox-mem on the LoCoMo benchmark
([Maharana et al., 2024](https://arxiv.org/abs/2402.17753),
[snap-research/LoCoMo](https://github.com/snap-research/LoCoMo)).

This Python harness lives alongside the older TypeScript stubs
(`parser.ts` / `run.ts` / `score.ts`) and is the one used by PR
`feat/locomo-bench-harness` (2026-05-29) for cross-bench validation
matching the Phase H v2 EverMemBench + LongMemEval pattern (PR #378).

## Layout

```
eval/locomo/
├── README-CROSSBENCH.md          # this file
├── adapter_nox_mem.py            # per-conv ingest + per-q retrieve + gpt-4.1-mini answer
├── run-bench.sh                  # orchestrator (smoke / full / subset / resume)
├── lib/
│   ├── corpus_loader.py          # LoCoMo JSON → markdown sessions; QA records
│   ├── scorer.py                 # F1 + adversarial + multi-hop split (LoCoMo paper §4.2)
│   └── aggregate.py              # JSON + markdown report + published-baseline table
├── data/                         # local cache (locomo10.json copied here at first run)
├── results/                      # raw .jsonl outputs and aggregate snapshots
└── RESULTS-LOCOMO.{md,json}      # canonical headline (overwritten by run-bench.sh)
```

## Dataset acquisition

LoCoMo dataset (CC BY-NC 4.0):

```
git clone --depth 1 https://github.com/snap-research/LoCoMo.git /tmp/locomo-repo
# Provides /tmp/locomo-repo/data/locomo10.json (≈2.7 MB)
```

`run-bench.sh` auto-clones if `${LOCOMO_REPO}/data/locomo10.json` is missing.

**Stats** (verified 2026-05-29 on locomo10.json):

| Field | Value |
|---|---:|
| Conversations | 10 |
| Sessions / conv | 19–32 (avg 27.2) |
| Turns / conv | 369–689 (avg 588.2) |
| QA pairs total | 1,986 |
| Category 1 (multi_hop) | 282 |
| Category 2 (temporal) | 321 |
| Category 3 (commonsense) | 96 |
| Category 4 (single_hop) | 841 |
| Category 5 (adversarial) | 446 |

## Category mapping

Canonical mapping (extracted from `task_eval/evaluation.py` + `gpt_utils.py`):

| int | name        | scoring                                                    |
|----:|-------------|------------------------------------------------------------|
| 1   | multi_hop   | F1 with sub-answer split on `;` (partial credit)           |
| 2   | temporal    | F1, question augmented with "Use DATE of CONVERSATION..."  |
| 3   | commonsense | F1, gold pre-split on `;` (first sub-answer)               |
| 4   | single_hop  | F1                                                          |
| 5   | adversarial | 1 if response is a refusal substring, else 0               |

## Pipeline

**Per-conversation** ingest (10 isolated DBs total, NOT per-question):

1. Fresh isolated DB `${WORKDIR}/locomo-bench.db`.
2. `lib/corpus_loader.write_conversation_md_files` writes one .md per session;
   each turn embeds `dia_id: D<sess>:<turn>` for evidence traceback.
3. `nox-mem ingest <file.md>` per session.
4. `nox-mem vectorize` once at conversation end.
5. Start nox-mem-api on port `${API_PORT}` (default 18840) pointed at this DB.
6. For each QA pair of the conversation:
   - POST `/api/search` with augmented question, `limit=top_k`.
   - Build context from top-10 chunks.
   - Call gpt-4.1-mini generator with context + question.
   - Write JSONL record (gold, prediction, retrieval metadata).
7. Stop API; loop to next conversation.

This is **much faster** than LongMemEval's per-question pattern because
LoCoMo questions share their conversation's corpus.

## Configuration

Defaults (Phase H v2 baseline, mirrors PR #378 / PR #345):

| Var | Default | Effect |
|---|---|---|
| `NOX_RERANKER_ENABLED` | `0` | rerank OFF |
| `NOX_TEMPORAL_PATH` | `shadow` | temporal patch shadow-mode |
| `NOX_SALIENCE_MODE` | `shadow` | salience shadow-mode |
| `TOP_K` | 20 | search depth |
| Generator | `gpt-4.1-mini` | cross-backbone parity |
| Embedding | `gemini-embedding-001` (from nox-mem) | 3072d dense |

NO Wave A/B/C knobs (KG path, MAP, MQ expansion, adaptive classifier).
This is BASELINE cross-bench, not knob bench.

## Usage

### Smoke (100 qa stratified, ~15-30 min)

```bash
ssh root@<vps>
cd /root/.openclaw/workspace/tools/nox-mem
git fetch origin && git checkout feat/locomo-bench-harness
bash eval/locomo/run-bench.sh smoke
```

### Full bench (1986 qa, ~3-5 h)

```bash
bash eval/locomo/run-bench.sh full
```

### Custom N

```bash
bash eval/locomo/run-bench.sh subset 500
```

### Resume

```bash
WORKDIR=/root/.openclaw/locomo-bench-XXXX/work \
MODE=resume \
bash eval/locomo/run-bench.sh resume
```

## Outputs

- `eval/locomo/RESULTS-LOCOMO.md` — markdown report with overall F1,
  per-category breakdown, latency, cost, published-baseline comparison.
- `eval/locomo/RESULTS-LOCOMO.json` — structured aggregate (schema
  `locomo-aggregate/v1`).
- `${WORKDIR}/../results/results-<mode>.jsonl` — per-QA raw records.
- `${WORKDIR}/../results/run-meta.json` — run metadata.

## Safety

`adapter_nox_mem.py::refuse_if_prod()` aborts if:
- DB path resolves to prod `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`.
- API port is `18802` (prod).
- DB path is NOT under `/var/backups/` or `/root/.openclaw/` (op-audit
  ALLOWED_PREFIXES — workdir under `/tmp/*` would be rejected by nox-mem
  op-audit P1 guard regardless).

## Published baselines (overall F1)

Comparison table embedded in `RESULTS-LOCOMO.md`:

| System | Generator | Overall F1 | Source |
|---|---|---:|---|
| Full Context (paper) | GPT-4 | 42.39% | Maharana et al. 2024 |
| Observation RAG | GPT-3.5-turbo | 32.03% | Maharana et al. 2024 |
| Summary RAG | GPT-4 | 40.53% | Maharana et al. 2024 |
| RAG baseline (Mem0 paper) | GPT-4o-mini | 35.47% | Chhikara et al. 2025 |
| LangMem | GPT-4o-mini | 50.21% | Chhikara et al. 2025 |
| Zep | GPT-4o-mini | 50.40% | Chhikara et al. 2025 |
| Mem0 (graph) | GPT-4o-mini | 56.10% | Chhikara et al. 2025 |
| Mem0 | GPT-4o-mini | 66.88% | Chhikara et al. 2025 (SOTA) |

NOTE on comparability: paper baselines used GPT-4 / Claude-3-Sonnet;
later baselines (Mem0/Zep/LangMem) used GPT-4o-mini. We use **gpt-4.1-mini**
for cross-backbone parity with Phase H v2. Not exactly apples-to-apples
but on the same order of magnitude as gpt-4o-mini (the Mem0 reference
generator).

## Reference

- LoCoMo paper: https://arxiv.org/abs/2402.17753
- LoCoMo repo: https://github.com/snap-research/LoCoMo
- Mem0 paper (reproduces baselines): https://arxiv.org/abs/2504.19413
- nox-mem Phase H v2 baseline: see `paper/paper-tecnico-nox-mem.md`
- LongMemEval crossbench template: `eval/longmemeval/CROSSBENCH-METHODOLOGY.md`
