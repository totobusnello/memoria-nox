# LoCoMo Cross-Bench — Methodology

This document explains the design choices behind `eval/locomo/`, what makes the
results comparable (or not) to published LoCoMo numbers, and the caveats a
reader should keep in mind when citing them.

## 1. What we measure

**Two metric families:**

1. **End-to-end QA F1** (LoCoMo paper §4.2, official metric).
   Score the generated answer (gpt-4.1-mini) against the gold answer using
   SQuAD-style token F1, with per-category specialisations (multi_hop split,
   adversarial refusal-correct).
2. **Retrieval-only evidence-hit-at-K** (our addition).
   Score the retrieved chunks against the gold `dia_id` evidence spans.
   Treat a record as a HIT if any retrieved chunk's `dia_id` appears in the
   gold evidence list. This isolates the **retrieval-quality** signal from
   the generator-quality signal — useful when generator calls fail or to
   diagnose F_MH gap drivers (retrieval-bound vs generation-bound).

The harness runs in either mode. Default is end-to-end; pass `--no-generator`
to skip the generator (graceful degradation when OpenAI quota is exhausted).

## 2. Why per-CONVERSATION (not per-question) ingest

LongMemEval (PR #378) uses **per-question** isolated DBs because each LME
question has a DIFFERENT haystack of unrelated sessions — that's the entire
LME design.

LoCoMo is the opposite: all ~199 QA pairs of a conversation share the SAME
corpus (that conversation's ~588 turns). Per-question ingest would re-vectorize
the same 70-ish chunks 199 times — pure waste.

Our pipeline ingests each conversation ONCE (~30s including vectorize), then
serves all its QA pairs (~1s each) against the same in-memory corpus. Total
wallclock for n=1986 is ~10 conv × 30s setup + 1986 × ~1s = ~40 min instead
of ~10 hours.

**Trade-off:** the API server is restarted between conversations (one DB per
conv). This is a conscious choice to avoid leaking chunks across conversations
(which would game the metric — gold dia_ids from another conv could
accidentally match by token similarity).

## 3. Category mapping (numeric → name)

The released LoCoMo dataset (`snap-research/LoCoMo/data/locomo10.json`) uses
integer category labels 1..5. There is NO mapping documented in the dataset
itself. We derived the mapping from the LoCoMo paper §3 and the eval scripts
in `task_eval/{evaluation,gpt_utils,gemini_utils}.py`:

| int | name | scoring | evidence |
|----:|------|---------|----------|
| 1 | multi_hop | F1 with sub-answer split on `;` (partial credit) | `evaluation.py` if line['category'] in [1] → `f1(output, answer)` |
| 2 | temporal | F1, question augmented with "Use DATE of CONVERSATION..." | `gpt_utils.py` if qa['category'] == 2: questions.append(... + ' Use DATE...') |
| 3 | commonsense | F1, gold pre-split on `;` (first sub-answer) | `evaluation.py` if line['category'] == 3: answer = answer.split(';')[0] |
| 4 | single_hop | F1 | `evaluation.py` if line['category'] in [2, 3, 4] → `f1_score(output, answer)` |
| 5 | adversarial | 1 if response indicates abstention, else 0 | `gpt_utils.py` cat 5 MCQ + `evaluation.py` 'no information available' check |

Distribution (verified on locomo10.json):

| Category | n | share |
|---|---:|---:|
| multi_hop | 282 | 14.2% |
| temporal | 321 | 16.2% |
| commonsense | 96 | 4.8% |
| single_hop | 841 | 42.3% |
| adversarial | 446 | 22.5% |
| **total** | **1986** | **100%** |

## 4. Generator configuration (Phase H v2 parity)

When generation is enabled:

- **Generator:** `gpt-4.1-mini` (cross-backbone parity with EverMemBench
  Phase H v2 + LongMemEval PR #378; comparable to Mem0 paper's `gpt-4o-mini`
  baseline numbers).
- **Embedding:** Gemini `gemini-embedding-001` (3072d, nox-mem prod default).
- **Hybrid search:** FTS5 BM25 + Gemini dense + RRF (k=60) — Phase H v2 baseline.
- **No knobs:** `NOX_RERANKER_ENABLED=0`, `NOX_TEMPORAL_PATH=shadow`,
  `NOX_SALIENCE_MODE=shadow`. No Wave A/B/C (KG path, MAP, MQ expansion,
  AC classifier). This is a BASELINE cross-bench, not a knob bench.
- **top_k:** 20 retrieval, top-10 context window per prompt.
- **Temperature:** 0.

## 5. Comparability of published baselines

The "published baselines" table in `RESULTS-LOCOMO.md` mixes generators:

| Baseline | Generator | Year | Method |
|---|---|---|---|
| Full Context | GPT-4 | 2024 | truncated conversation as context |
| Observation RAG | GPT-3.5 | 2024 | RAG over auto observations |
| Summary RAG | GPT-4 | 2024 | RAG over session summaries |
| RAG baseline | GPT-4o-mini | 2025 | standard chunk RAG (Mem0 paper) |
| LangMem | GPT-4o-mini | 2025 | LangGraph memory |
| Zep | GPT-4o-mini | 2025 | Zep memory layer |
| Mem0 (graph) | GPT-4o-mini | 2025 | Mem0 with KG |
| Mem0 | GPT-4o-mini | 2025 | Mem0 SOTA |
| **nox-mem (ours)** | **gpt-4.1-mini** | 2026 | hybrid FTS5+Gemini+RRF |

gpt-4.1-mini and gpt-4o-mini are in the same generation tier; our headline
number is the closest direct comparison to the Mem0 paper's reproduction.

**Honest caveats** (lesson cravada Sat 2026-05-24: "honest cross-system framing"):

- Mem0 paper's LoCoMo reproduction may use different question selection
  (the paper doesn't state if it's full n=1986 or a sample).
- Published numbers use F1 mixed across all categories, but cat 3
  (commonsense, 4.8% share) and cat 5 (adversarial, 22.5% share) have
  different scoring families — averaging them as if they were one F1 is
  itself a simplification.
- Our retrieval-only mode (`evidence_hit@10`) is NOT the same metric as
  the published F1; the table annotates this clearly.

## 6. Known weak spots (predicted)

Based on per-category fingerprints from EverMemBench Phase H v2 and
LongMemEval cross-bench (PR #378), we expect on LoCoMo:

- **single_hop:** strong (60-75% F1 / hit@10)
- **multi_hop:** weak (45-55% F1 / hit@10) — the F_MH backbone-invariant
  gap is the headline gap vs MemOS / Mem0
- **temporal:** weak (40-50% F1 / hit@10) — known weakness; PR #181 v2
  spike patch is shadow-mode in baseline, not active
- **commonsense:** medium (50-65%) — depends on whether the question
  needs facts from the conversation or general knowledge
- **adversarial:** strong (75-85%) — we tell the generator to refuse if
  context lacks the answer; refusal detection is robust

These predictions are based on the 100-q retrieval-only smoke (PR
`feat/locomo-bench-harness`):

| Category | n=20 | evidence_hit@10 |
|---|---:|---:|
| adversarial | 20 | 80.0% |
| multi_hop | 20 | 80.0% |
| single_hop | 20 | 70.0% |
| commonsense | 18 | 55.6% |
| temporal | 20 | 55.0% |

multi_hop and adversarial both at 80% on retrieval-only — the F_MH
backbone-invariant gap (cravada from PR #372/#377/#378) appears to be
generation-bound on LoCoMo, NOT retrieval-bound. This is a NEW finding
from this bench (since EverMemBench / LongMemEval suggested retrieval-
bound).

## 7. Cost model

Per-record cost estimate (gpt-4.1-mini April-2026 pricing):

| Component | Tokens | Rate | $/qa |
|---|---:|---|---:|
| Generator input (prompt + top-10 chunks) | ~3000 | $0.40/1M | $0.0012 |
| Generator output (answer, ~50 tokens) | ~50 | $1.60/1M | $0.00008 |
| Gemini embed (per conv, amortised over ~199 qa) | ~100/qa | $0.15/1M | $0.000015 |
| **Total per qa (with generator)** | | | **~$0.0013** |
| **Per qa (retrieval-only, no generator)** | | | **~$0.000015** |

For n=1986: ~$2.60 with generator, ~$0.03 without. Both well under the $7
cap.

## 8. Reproducibility

```bash
# On VPS:
git clone --depth 1 https://github.com/snap-research/LoCoMo.git /tmp/locomo-repo
cd /root/.openclaw/workspace/tools/nox-mem
git checkout feat/locomo-bench-harness
bash eval/locomo/run-bench.sh smoke         # 100 qa stratified
NO_GENERATOR=1 bash eval/locomo/run-bench.sh full   # 1986 qa retrieval-only
```

Seed = 42 (stratified sample). Phase H v2 baseline config. Same git SHA
recorded in `run-meta.json`.
