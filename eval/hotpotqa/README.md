# HotPotQA bench harness — nox-mem classical multi-hop QA

> Built 2026-05-29. Validates nox-mem against the most-cited classical
> multi-hop QA benchmark (HotPotQA dev-distractor, ~7405 questions).

## What

**HotPotQA** (Yang et al. 2018, [arxiv:1809.09600](https://arxiv.org/abs/1809.09600))
is a multi-hop QA benchmark. Each question requires combining facts from
**2 supporting paragraphs** mixed with **8 distractor paragraphs** (Wikipedia
intros). Standard eval = **distractor setting**: model receives all 10
paragraphs and must (a) identify the supporting ones AND (b) answer the
question from them.

Three metric families (per `hotpot_evaluate_v1.py`):
- **Answer**: EM + token-level F1 on the predicted answer
- **Supporting facts (sp)**: EM + F1 on the predicted `(title, sent_idx)` set
- **Joint**: `ans_em * sp_em` (joint EM), `ans_f1 * sp_f1` (joint F1)

Published baselines (single-shot retrieval+reader systems):
| System | ans_F1 | sp_F1 | joint_F1 |
|---|---|---|---|
| DrQA (paper baseline, 2018) | 27.1 | 25.1 | 7.0 |
| DPR-based RAG (2020-2021) | 45-50 | 50-55 | 25-30 |
| SOTA reader (FiD, GraphRetriever) | 70-75 | 80-85 | 55-65 |
| Modern memory systems (Mem0/Zep claimed) | 50-65 | n/a | n/a |

## Why nox-mem on HotPotQA

1. **Foundation validation** — HotPotQA is the canonical multi-hop benchmark.
   A modern memory system should perform competitive with single-shot RAG.
2. **Cross-benchmark portability** — Pairs with EverMemBench (group chat) +
   LongMemEval (single-session long) + LoCoMo (planned) to cover the 3-axis
   memory eval matrix.
3. **Honest framing** — nox-mem is built for *episodic* memory recall, not
   *Wikipedia QA reading comprehension*. Expected performance: competitive
   with modern memory systems (50-65% F1), sub-SOTA vs purpose-built reader
   models. Q3 Iterative Retrieval (planned) targets 30-50% closure of the
   remaining gap to FiD-class systems.

## File map

```
eval/hotpotqa/
├── adapter_nox_mem.py             # per-question DB + nox-mem ingest + search + gpt-4.1-mini answer
├── run-bench.sh                   # orchestrator (smoke | full | dry)
├── lib/
│   ├── __init__.py
│   ├── corpus_loader.py           # HotPotQA dev-distractor parser → HotpotQuestion dataclass
│   ├── scorer.py                  # F1 / EM / supporting-facts (port of hotpot_evaluate_v1.py)
│   └── aggregate.py               # JSONL → summary JSON (per-type / per-level / latency)
├── results/                       # per-run output JSONL + RESULTS-*.json
└── RESULTS-HOTPOTQA.md            # final report (filled in after run)
```

## How

### 1. Preconditions

- nox-mem v3.8 deployed on VPS at `/root/.openclaw/workspace/tools/nox-mem/`
- `/root/.openclaw/.env` exports `OPENAI_API_KEY` + `GEMINI_API_KEY`
- Port 18900 free (smoke + full both use 18900; prod is 18802)
- ~10GB free disk under `/root/.openclaw/` (per-question DBs ~1MB each but
  worktree + dataset = ~600MB)

### 2. Smoke (n=200, ~30min, ~$0.20)

```bash
cd /root/.openclaw/workspace/tools/nox-mem/eval/hotpotqa
./run-bench.sh smoke
```

This will:
1. Source `/root/.openclaw/.env`
2. Preflight gpt-4.1-mini + gemini-2.5-flash-lite (5-token completion each)
3. Download `hotpot_dev_distractor_v1.json` if not cached
4. Run 200 stratified-shuffle questions through per-q isolated DBs
5. Aggregate → `results/RESULTS-SMOKE-200.json`

Smoke pass threshold: **ans_F1 ≥ 50%**. If smoke <40%, iterate adapter
(chunking, prompt, top_k) before paying for full bench.

### 3. Full bench (n=7405 dev, ~5-7h, ~$7-10)

```bash
./run-bench.sh full
```

Or budget-capped midrun:

```bash
./run-bench.sh full --n 3000 --resume
```

Output: `results/RESULTS-FULL-7K-DEV.{jsonl,json}`.

### 4. Aggregate only (from existing JSONL)

```bash
python3 lib/aggregate.py \
  --in results/RESULTS-FULL-7K-DEV.jsonl \
  --out-json results/RESULTS-FULL-7K-DEV.json \
  --config '{"mode":"full","top_k":5,"generator":"gpt-4.1-mini"}'
```

## Configuration matrix

| Variable | Default | Meaning |
|---|---|---|
| `NOX_DB_PATH` | (per-q `/root/.openclaw/hotpotqa-bench-<uuid>/work/q-<qid>/hotpot.db`) | Per-question isolated DB |
| `NOX_API_PORT` | 18900 | nox-mem API port (NEVER 18802) |
| `NOX_RERANKER_ENABLED` | 0 | Phase H v2 baseline — no cross-encoder |
| `NOX_MEM_BIN` | `nox-mem` (from PATH) | CLI binary |
| `HOTPOT_GENERATOR` | `gpt-4.1-mini` | Answer LLM |
| `HOTPOT_TOP_K` | 5 | retrieval top-k for answer context |
| `HOTPOT_BUDGET_CAP` | 12 (USD) | hard budget cap for full bench |

## Mechanics & safety

- **Per-question isolation** (paper requirement): each question gets its own
  fresh DB. After retrieval the DB is deleted. No cross-question leak.
- **Prod-DB guard**: `refuse_if_prod()` blocks any DB path that resolves to
  `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` and any API port `18802`.
- **op-audit ALLOWED_PREFIXES** compliance: workdir must be under
  `/root/.openclaw/`. Local-mac `/tmp/` paths are blocked.
- **Schema bootstrap**: V1-V7 via `nox-mem stats`, V8-V18 + KG via direct
  `sqlite3` ALTERs (matches longmemeval + evermembench adapters).
- **Vectorize fallback**: if vectorize fails (Gemini quota, network), the
  pipeline continues with FTS5-only search — non-fatal.
- **Cost log**: each generator call writes its `usage` block to the JSONL;
  aggregate.py computes total cost.

## Predicted result (honest framing)

```
nox-mem single-shot retrieval baseline on HotPotQA distractor (Phase H v2):
  ans_F1: <X.X>%  (target ≥ 50%)
  ans_EM: <X.X>%
  sp_F1:  <X.X>%
  joint_F1: <X.X>%
  per-type: comparison vs bridge breakdown
  per-level: easy / medium / hard

Position: competitive with modern memory systems (Mem0 / Zep claimed range
50-65% F1); sub-SOTA reader models (FiD ~70-75% F1).

Q3 Iterative Retrieval (planned 2026-Q3) targets +10-15pp F1 by adding a
second retrieval pass conditioned on the first answer attempt — predicted
to close 30-50% of the remaining gap to FiD-class systems.
```

## Open work after first full run

- [ ] LLM-based supporting-fact extraction (current is overlap-based; +5-10pp sp_F1 expected)
- [ ] `fullwiki` setting (5M paragraphs; tests Wikipedia-scale retrieval — separate harness)
- [ ] Composability with Lab Q1 #4 KG path retrieval (HotPotQA entities are Wikipedia titles — natural fit)
- [ ] Cross-benchmark dashboard panel (EverMemBench + LongMemEval + HotPotQA single-pane)

## References

- HotPotQA: [arxiv:1809.09600](https://arxiv.org/abs/1809.09600), [hotpotqa.github.io](https://hotpotqa.github.io/)
- Official eval script: [hotpot_evaluate_v1.py](https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py)
- nox-mem cross-bench methodology: `eval/longmemeval/CROSSBENCH-METHODOLOGY.md`
- Phase H v2 baseline config (this harness inherits): `eval/evermembench/RESULTS-PHASEH-v2-5BATCH.md`
