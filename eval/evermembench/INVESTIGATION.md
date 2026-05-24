# EverMemBench — Investigation Report

**Date:** 2026-05-24  
**Source:** github.com/EverMind-AI/EverOS @ `benchmarks/EverMemBench/`  
**Paper:** arXiv:2602.01313 — *EverMemBench: A Comprehensive Benchmark for Long-Term Memory in Conversational AI*  
**Dataset:** huggingface.co/datasets/EverMind-AI/EverMemBench-Dynamic (~46 MB, 642 downloads)

---

## 1. Dataset Format

Multi-person **group chat** conversations spanning ~250 days per topic.  
Five batches, each a separate `user_id`: `004`, `005`, `010`, `011`, `016`.

```
dataset/{batch_id}/
  dialogue.json     # multi-turn group chat, organized by date → group → messages
  qa_{batch_id}.json  # QA questions for that batch
```

### `dialogue.json` structure
```json
{
  "date": "2025-01-09",
  "groups": {
    "Group 1": [
      {
        "speaker": "Weihua Zhang",
        "content": "...",
        "time": "2025-01-09T10:30:00",
        "group": "Group 1"
      }
    ]
  }
}
```

### `qa_{batch}.json` — two supported formats
**Format 1 (primary):**
```json
{ "qars": [
    { "id": "F_SH_Top004_001", "Q": "...", "A": "...",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."} }
  ]
}
```
Options = `null` for open-ended questions. Two types: `multiple_choice` (MC) and `open_ended` (OE).

---

## 2. Evaluation Protocol

Four sequential stages:

```
Add → Search → Answer → Evaluate
```

| Stage | What it does | Output |
|-------|--------------|--------|
| **Add** | Ingest group chat messages into memory system | (side-effect) |
| **Search** | For each QA question, query memory system top-k | `search_results_{uid}.json` |
| **Answer** | LLM generates answer from retrieved memories | `answer_results_{uid}.json` |
| **Evaluate** | Judge scores answer against gold | `evaluation_results_{uid}.json` |

### Adapter interface (abstract)
```python
class BaseAdapter(ABC):
    async def add(self, dataset: Dataset, user_id: str, ...) -> AddResult
    async def search(self, query: str, user_id: str, top_k: int, ...) -> SearchResult
```

`SearchResult` must return:
- `retrieved_memories: List[str]`
- `context: str` — formatted string for LLM answer prompt

For nox-mem: `add` = batch ingest to nox-mem DB; `search` = call HTTP `POST /api/search` or CLI search.

---

## 3. Judge LLM

**Two-tier evaluation:**

| Question type | Method | Model |
|---------------|--------|-------|
| `multiple_choice` | Direct string match (predicted letter == correct letter) — **zero LLM cost** | None |
| `open_ended` | LLM judge via OpenRouter | `google/gemini-3-flash-preview` (evaluate stage) |

**Answer generation** (both types): `openai/gpt-4.1-mini` via OpenRouter.  
API access: OpenRouter (`LLM_API_KEY=sk-or-v1-...` + `LLM_BASE_URL=https://openrouter.ai/api/v1`).

**All inference routed via OpenRouter** — NOT OpenAI direct, NOT Google AI Studio direct.

---

## 4. Primary Metric

`accuracy` = `correct / total_questions` (float, reported as %)

Broken down by:
- `question_type`: MC vs OE
- `question_id` category prefix (major/minor/hierarchical via `analyze_results.py`)

**Not** nDCG@10. **Not** MRR. Pure accuracy — fundamentally different from LongMemEval/LoCoMo methodology.

Implication: **not directly comparable** to our existing Q2/Q3/Q4 nDCG@10 numbers. Needs separate reporting track.

---

## 5. Reproduction Requirements

### Mandatory
- Python >= 3.11
- `pip install -r requirements.txt` (aiohttp, openai, PyYAML, rich, aiolimiter)
- OpenRouter API key (for answer generation + OE judge)
- nox-mem HTTP API running at `:18802` (or configurable port)

### Optional (for full parity)
- HuggingFace `datasets` library to download `EverMemBench-Dynamic` directly
- Alternatively: clone EverOS repo and use local `dataset/` folder

### Not required
- Any cloud memory system account (nox-mem runs locally)
- EverCore/Mem0/Zep API keys

---

## 6. Cost Estimate Per Full Run

5 batches × ~N questions per batch.  
Dataset has 3 configs: `dialogues`, plus QA sets (est. 100–300 questions per batch based on analogous benchmarks).

| LLM call | Model | Est. qty | Cost/call | Est. total |
|----------|-------|----------|-----------|------------|
| Answer gen (MC + OE) | gpt-4.1-mini | ~1,000 q | ~$0.001 | ~$1.00 |
| OE judge (~50% of Qs) | gemini-3-flash-preview | ~500 q | ~$0.0001 | ~$0.05 |
| **Total** | | | | **~$1–2 USD** |

Ingest (Add stage) — no LLM calls in nox-mem search path. Vectorize = Gemini embed quota usage, not billed.

**Cost verdict: negligible.** $1–2 per full run. The blocker is implementation time, not budget.

---

## 7. Blockers

| Blocker | Severity | Notes |
|---------|----------|-------|
| **Domain mismatch** | HIGH | EverMemBench = multi-person group chat; nox-mem ingests personal notes/entities. Add stage needs a custom ingestion path that maps group chat messages to chunks — different from `ingest-entity` or `ingestFile()` |
| **OpenRouter key** | LOW | Need `sk-or-v1-*` key; Toto probably has or can create one |
| **HF dataset access** | NONE | Public dataset, no auth required |
| **Metric gap** | MEDIUM | Accuracy != nDCG@10; must communicate separately in paper/GTM |
| **Add stage isolation** | MEDIUM | Each batch needs clean nox-mem DB; harness must use `NOX_DB_PATH` override per batch to avoid cross-contamination |

---

## 8. Comparability with LongMemEval / LoCoMo

| Dimension | LongMemEval | LoCoMo | EverMemBench |
|-----------|-------------|--------|--------------|
| Metric | nDCG@10 | % (judge accuracy) | % (accuracy, MC direct + OE judge) |
| Memory type | Single-user notes | Personal conversations | Multi-person group chat |
| nox-mem fit | HIGH (native use case) | MEDIUM | LOW (requires domain adaptation) |
| Narrativa | "best hybrid retrieval" | "recalls personal history" | "understands group dynamics" |

---

## 9. Lab Q1 Recommendation

**Go — with caveats. Priority: AFTER bge-reranker.**

Rationale:
- Cost ~$1–2/run = negligible, no budget blocker
- Closes the "benchmark gap" narrative gap (only competitor publishing proprietary bench results)
- Accuracy metric is MC-heavy → high potential score even with imperfect OE retrieval
- But: Add stage domain adaptation (group chat → nox-mem chunks) is 1–2 days of real work
- Metric difference (accuracy vs nDCG@10) must be called out honestly in paper §C2

**Order:** bge-reranker (direct nDCG@10 gain) → EverMemBench adaptation (narrative/GTM). Parallelizable if Lab capacity allows.

**EverMemBench alone does NOT replace Q4 cross-system comparison** — keep both tracks separate.

---

## 10. Files Generated

- `eval/evermembench/INVESTIGATION.md` — this file
- `eval/evermembench/adapter_nox_mem.py` — adapter skeleton
- `eval/evermembench/README.md` — next steps + run instructions
