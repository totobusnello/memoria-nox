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

---

## 11. MemOS Table 4 — Complete Reference Matrix

**Source:** Hu et al. (2026), arXiv:2602.01313 §4.2, Table 4 (page 7).  
**Title:** *Evaluating Long-Horizon Memory for Multi-Party Collaborative Dialogues.*  
**Extracted:** 2026-05-28 (PR docs/memos-table-4-complete-extraction).

**Note on backbones:** Table 4 contains exactly **3 backbones** — GPT-4.1-mini, Llama-4-Scout-17B-16E-Instruct, and Gemini-3-Flash. (gpt-4o, gpt-4.1, claude-sonnet, gemini-2.5-pro are NOT in Table 4.) Per paper §4.1: *"all memory-augmented systems use GPT-4.1-mini as the answer model"* for the primary results — Table 4 is the cross-backbone ablation, not the full leaderboard.

**Cross-check:** GPT-4.1-mini + MemOS values match PR #368 extraction exactly (F_SH 71.36±6.1, F_MH 18.88±4.8, Average 42.55±1.9). Confirmed.

Gray subscripts = half-widths of 95% bootstrap CIs (B=10,000). Parenthesized values = delta vs Full Context baseline on same backbone.

### 11.1 GPT-4.1-mini backbone

Full Context baseline: **37.44±1.8**

| Method | F_SH (Single) | F_MH (Multi) | F_TP (Temp) | MA_C (Const) | MA_P (Proact) | MA_U (Update) | P_Style | P_Skill | P_Role | Average |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full Context | 83.57±4.9 | 2.41±1.8 | 7.00±2.8 | 63.43±4.7 | 25.06±4.1 | 42.54±5.0 | 39.20±7.4 | 35.50±7.1 | 38.27±6.9 | 37.44±1.8 |
| + MemoBase | 60.09±6.6 | 12.85±4.2 | **18.00±4.1** | 64.68±4.6 | 36.77±4.6 | 30.60±5.6 | 17.05±5.4 | 29.59±5.8 | 38.78±6.9 | 34.27±1.9 (-3.18) |
| + Mem0 | 55.40±6.6 | 11.24±3.8 | 6.33±2.8 | 66.17±4.6 | **52.46±4.7** | **51.87±5.0** | 22.73±6.5 | 31.36±7.1 | 36.22±6.9 | 37.09±1.9 (-0.36) |
| + Zep | 73.71±5.9 | 8.03±3.4 | 13.00±3.8 | 67.16±4.6 | 47.54±4.7 | 43.66±6.0 | 26.70±6.5 | **35.50±7.1** | 44.39±6.9 | 39.97±1.9 (+2.52) |
| **+ MemOS** | **71.36±6.1** | **18.88±4.8** | 15.67±4.0 | **69.90±4.5** | 51.99±4.7 | 45.15±6.0 | **28.98±6.5** | 32.54±7.1 | **48.47±7.1** | **42.55±1.9 (+5.11)** |

### 11.2 Llama-4-Scout-17B-16E-Instruct backbone

Full Context baseline: **40.18±1.5**

| Method | F_SH (Single) | F_MH (Multi) | F_TP (Temp) | MA_C (Const) | MA_P (Proact) | MA_U (Update) | P_Style | P_Skill | P_Role | Average |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full Context | 77.93±5.6 | 0.00±0.0 | 1.67±1.5 | 60.45±4.7 | 43.79±4.7 | 67.91±5.9 | 27.84±6.8 | 39.64±7.4 | 42.35±6.9 | 40.18±1.5 |
| + MemoBase | 57.75±6.5 | 5.62±3.0 | **12.00±3.8** | **67.41±4.6** | 54.10±4.7 | 27.61±5.4 | 21.02±6.0 | 47.34±7.7 | 42.86±6.6 | 37.30±1.8 (-2.88) |
| + Mem0 | 56.34±6.5 | 3.21±2.2 | 3.67±2.8 | 66.17±4.3 | 63.00±4.7 | **45.90±5.0** | 23.30±6.0 | 51.48±7.7 | 44.39±6.9 | 39.72±1.8 (-0.46) |
| + Zep | **71.36±6.1** | 4.02±2.4 | 7.00±2.8 | **67.41±4.5** | 52.69±4.7 | 35.45±5.0 | **27.84±6.8** | 46.15±7.7 | 46.43±7.1 | 39.82±1.8 (-0.36) |
| **+ MemOS** | 67.61±6.1 | **6.43±3.0** | 11.33±3.5 | **67.41±4.5** | 47.54±4.7 | 38.43±5.0 | 23.86±6.2 | **53.25±7.7** | **50.00±7.1** | **42.44±1.9 (+2.27)** |

### 11.3 Gemini-3-Flash backbone

Full Context baseline: **72.61±1.6**

| Method | F_SH (Single) | F_MH (Multi) | F_TP (Temp) | MA_C (Const) | MA_P (Proact) | MA_U (Update) | P_Style | P_Skill | P_Role | Average |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full Context | 97.65±2.1 | 26.51±5.4 | 45.00±5.7 | 96.77±1.7 | 98.36±1.2 | 100.00±0.0 | 67.05±6.8 | 53.25±7.7 | 68.88±6.6 | 72.61±1.6 |
| + MemoBase | 56.34±6.6 | 6.43±3.0 | 17.67±4.2 | 85.32±3.3 | **91.10±2.6** | 84.33±4.3 | 38.07±7.4 | 53.85±7.2 | 69.39±6.9 | 55.83±1.8 (-16.78) |
| + Mem0 | 56.34±6.6 | 5.62±3.0 | 2.67±1.8 | 79.60±3.9 | 84.54±3.4 | 85.45±4.1 | 36.93±7.1 | 56.21±7.4 | 61.73±6.6 | 52.12±1.8 (-20.48) |
| + Zep | 68.54±6.1 | 6.02±3.0 | 11.00±3.5 | **85.82±3.4** | 82.44±3.3 | 78.36±4.9 | 34.66±6.8 | 60.95±7.4 | 66.33±6.6 | 54.90±1.8 (-17.71) |
| **+ MemOS** | **69.01±6.1** | **10.84±3.8** | **20.67±4.7** | 81.84±3.7 | 87.59±3.0 | **90.67±3.3** | **38.64±7.1** | **62.72±7.5** | **71.43±6.4** | **59.27±1.8 (-13.38)** |

### 11.4 Cross-backbone analysis

#### MemOS best score per sub-dim

| Sub-dim | Best backbone | Best value | Weakest backbone | Weakest value | Gap |
|---|---|---:|---|---:|---:|
| F_SH (Single-hop) | GPT-4.1-mini | 71.36% | Llama-4-Scout | 67.61% | 3.75 pp |
| F_MH (Multi-hop) | GPT-4.1-mini | 18.88% | Llama-4-Scout | 6.43% | 12.45 pp |
| F_TP (Temporal) | Gemini-3-Flash | 20.67% | GPT-4.1-mini | 15.67% | 5.00 pp |
| MA_C (Constraint) | GPT-4.1-mini | 69.90% | Gemini-3-Flash | 81.84% | — (Gemini wins) |
| MA_P (Proactivity) | Gemini-3-Flash | 87.59% | GPT-4.1-mini | 51.99% | 35.60 pp |
| MA_U (Update) | Gemini-3-Flash | 90.67% | GPT-4.1-mini | 45.15% | 45.52 pp |
| P_Style | Gemini-3-Flash | 38.64% | Llama-4-Scout | 23.86% | 14.78 pp |
| P_Skill | Gemini-3-Flash | 62.72% | GPT-4.1-mini | 32.54% | 30.18 pp |
| P_Role | Gemini-3-Flash | 71.43% | GPT-4.1-mini | 48.47% | 22.96 pp |
| **Average** | **GPT-4.1-mini** | **42.55%** | **Gemini-3-Flash** | **59.27%** | — |

#### Key findings for paper §5

1. **Gemini-3-Flash Full Context is a hard bar to beat via retrieval.** At 72.61%, it is the strongest backbone but memory-augmented systems all *regress* vs Full Context (-13 to -21 pp). This is the dominant pattern: on a strong enough backbone, RAG-style memory degrades average accuracy because it truncates context that the full-context model uses for profile/awareness tasks.

2. **GPT-4.1-mini is the best backbone FOR memory augmentation.** MemOS +5.11 pp over Full Context — the only positive delta in the entire table. Weaker baseline (37.44%) means retrieval adds net value. This is the baseline nox-mem targets in Phase H.

3. **Multi-hop (F_MH) is the weakest dim across ALL backbones.** MemOS peaks at 18.88% (GPT-4.1-mini) and falls to 6.43% (Llama-4-Scout). Even oracle evidence barely helps (Table 5: oracle F_MH = 97.99%). Root cause per §4.2: attribution requires stitching across speakers/groups/days — no current memory system addresses this structurally.

4. **Temporal (F_TP) is consistently weak.** 7.00–20.67% range across all systems. Per §4.2, temporal questions require version-semantics reasoning, not just timestamp matching. Target for future nox-mem Lab work (temporal spike v2, PR #181, addresses a subset of this).

5. **Profile Understanding improves with stronger backbone.** P_Style/P_Skill/P_Role all roughly double from GPT-4.1-mini → Gemini-3-Flash under MemOS (28.98/32.54/48.47 → 38.64/62.72/71.43). Signals that retrieval is not the bottleneck for profile dims — reasoning is.

6. **Llama-4-Scout is the weakest backbone overall.** F_MH = 0.00% Full Context (refuses to answer when evidence is fragmented). Per §4.2: *"LLaMA-4 reaches only 37.35% even under oracle conditions, frequently refusing to answer when evidence appears fragmented."* Not a viable target for cross-backbone narrative.

#### Implication for Phase H / paper §5.4

The cross-backbone target is GPT-4.1-mini (+5.11 pp is the bar). Gemini-3-Flash is a misleading comparison because memory-augmented systems universally regress on it — nox-mem being close to or above MemOS on Gemini-3-Flash would not be a meaningful win. The correct narrative is: *"nox-mem matches or exceeds MemOS on GPT-4.1-mini, the only backbone where memory augmentation produces net positive results."*
