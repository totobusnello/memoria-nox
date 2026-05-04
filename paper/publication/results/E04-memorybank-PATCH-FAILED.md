# E04 — MemoryBank Eval: Schema Mismatch — IR Metrics Not Computable

**Date:** 2026-05-04
**Sprint:** W2
**VPS session:** N/A — aborted after schema inspection
**Status:** PATCH-FAILED — data dir bug fixed, full eval blocked by missing gold labels

---

## What Was Fixed

### Bug: Wrong data directory discovery (lines 499-510, now 499-548)

The original `download_memorybank()` glob fallback sorted all JSON-containing directories
alphabetically and picked the first one. In the actual repo layout that resolved to:

```
/tmp/memorybank-repo/SiliconFriend-ChatGLM-BELLE/train/BELLE/run_config/
```

which contains only 2 training config JSONs (small, non-session data).

**Fix applied:** `_load_from_eval_data()` added (lines ~408-490 of patched adapter).
`download_memorybank()` now checks `clone_dir/eval_data/` **first** before the glob.
The glob itself was also hardened to skip `train/` and `run_config/` path components
and raised the size threshold from 100 to 500 bytes.

**Smoke test result:** After patch, discovery finds 15 users (sessions) instead of 2 config files.
The `download-only` command now reports 15 sessions discovered.

---

## Why Full IR Eval Cannot Proceed

### Real schema (eval_data/en/)

| File | Content |
|---|---|
| `memory_bank_en.json` | 15 users × 10 days × 17-52 turns. Each turn: `{query, response}`. No `memory_items`. |
| `probing_questions_en.jsonl` | 15 lines, one per user. Each line: `{username: [q1,...,q7]}`. 100 total questions. **No gold answers. No question types. No memory_ids.** |

### What the adapter was designed for

| Expected field | Purpose | Present? |
|---|---|---|
| `memory_items[].memory_id` | Discrete retrievable fact IDs | NO |
| `qa_pairs[].memory_ids` | Gold relevance links for nDCG | NO |
| `qa_pairs[].answer` | Answer for substring fallback relevance | NO |
| `qa_pairs[].question_type` | Stratification into 5 types | NO |

### Impact on metrics

nDCG@10, MRR, Recall@10, Precision@5 all require knowing which retrieved chunks
are relevant to a query. Without gold answers or memory_ids, relevance cannot be
determined without an external oracle (LLM-as-judge), which is out of scope for W2.

The 100 probing questions ARE real benchmark queries from the MemoryBank paper
(Zhong et al., 2023), but the paper evaluates them with a generation model
(ChatGPT/ChatGLM with MemoryBank retrieval), not with IR metrics against
ground-truth relevant chunks. The benchmark was never designed as an IR benchmark
with gold retrieval labels.

---

## Assessment

MemoryBank is a **generation-quality benchmark**, not an IR retrieval benchmark:
- Input: user question + retrieved memory context
- Output: qualitative judge rating of the generated response
- There are no precomputed gold chunk IDs to compare against

This is fundamentally incompatible with the nDCG/MRR/Recall framework used for
BEIR and LOCOMO. Adapting MemoryBank for IR eval would require generating
gold answers via LLM and running LLM-as-judge for relevance — a multi-hour
LLM annotation task outside W2 scope.

---

## BEIR Session Status (at time of inspection)

- `tmux ls` on VPS: `beir-trec` session alive
- Load avg at inspection time: checked before any eval was launched
- No memorybank-eval session was created (smoke test on local schema inspection only)
- BEIR not disturbed

---

## Corpus Coverage for §5.3

| Corpus | Type | Status |
|---|---|---|
| BEIR TREC-COVID | Domain-specific IR | Running (ETA 2026-05-05 01:00-04:00 BRT) |
| LOCOMO | Conversational episodic | Complete (E04-locomo-summary.md) |
| MemoryBank | Conversational episodic | **BLOCKED** — generation benchmark, no IR gold labels |

Critic C5 ("only one conversational corpus") is addressed by LOCOMO.
MemoryBank cannot substitute as a second conversational IR corpus without
LLM-as-judge annotation.

---

## §5.3 Prose (as-is, no MemoryBank metrics)

> "We evaluated nox-mem on two external corpora beyond the in-domain benchmark.
> On LOCOMO (n=50 human dialogues, 248 QA pairs, seed=42), nox-mem hybrid
> retrieval achieves nDCG@10=[LOCOMO_NDCG] versus the BM25 baseline
> nDCG@10=[LOCOMO_BM25]. MemoryBank (Zhong et al., 2023) was evaluated as
> a third corpus candidate; inspection of the benchmark revealed that its
> probing questions lack gold retrieval labels (the evaluation protocol requires
> a generation model judge, not IR metrics), making it incompatible with the
> nDCG/MRR/Recall framework used in this paper. BEIR TREC-COVID results are
> reported in §5.1."

---

## Files Changed

| File | Change |
|---|---|
| `baselines/memorybank_adapter.py` | Added `_load_from_eval_data()` (~85 lines); patched `download_memorybank()` to prefer `eval_data/` dir and harden glob fallback |
| `results/E04-memorybank-PATCH-FAILED.md` | This file |
