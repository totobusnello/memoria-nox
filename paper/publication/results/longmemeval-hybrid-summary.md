# Q2 LongMemEval — Hybrid (FTS5 + Gemini + RRF) — Python self-contained

**Run date:** 2026-05-18 19:29 -03
**Dataset:** `xiaowu0162/longmemeval-cleaned` (MIT (xiaowu0162/longmemeval-cleaned))
**Revision:** `98d7416c24...`
**Split:** `oracle` (evidence-only, smallest)
**Subset:** stratified n=100 over 6 base categories, seed=42
**Embedding model:** `gemini-embedding-001` (3072d, L2-normed)
**Fusion:** RRF with k=60, top-10 after fusion
**Per-branch candidates:** FTS5 top-20, dense top-20

## ⚠️ Caveats (read before citing)

1. **Python re-implementation, NOT production nox-mem code path.** This script reproduces the *architectural shape* of memoria-nox's hybrid retrieval (FTS5 BM25 + Gemini 3072d dense + RRF k=60). It does NOT execute nox-mem's TypeScript pipeline. Production-path validation requires running `npx tsx eval/longmemeval/run.ts` on the VPS — separate work item per Q2 spec.
2. **Retrieval-only metric, not task-accuracy.** The Q2 LongMemEval harness in `eval/longmemeval/` is designed for end-to-end task-accuracy via LLM-as-judge (paper standard). This script measures the *retrieval substrate* only (nDCG/MRR/Recall/Precision against `answer_session_ids` as binary relevance). Use it to validate the retrieval pipeline shape; use `run.ts` + `score.ts` for headline task-accuracy.
3. **Gold relevance is session-level (`answer_session_ids`), not turn-level.** A retrieved chunk is correct iff its `session_id` appears in `answer_session_ids`. This matches the paper's gold encoding and the harness D4 decision (per-session ingestion).
4. **Per-question scoping.** Each question has its own isolated haystack — retrieval is scoped to that question's `haystack_session_ids` only. This is the LongMemEval-correct setup (the paper measures needle-in-haystack within the bundled history), and differs from Q1 LoCoMo where the corpus is shared across questions of the same conversation.
5. **Sample n=100, not full 500 questions.** The oracle split has ~500 questions across 6 categories + abstention variants. n=100 is the same stratification target as Q1 LoCoMo for cross-benchmark cost/time parity. Multi-seed CI is a follow-up.

## Aggregate metrics

| Metric | Value | 95% CI |
|---|---|---|
| nDCG@10 | **1.0000** | [1.0000, 1.0000] |
| MRR | **1.0000** | [1.0000, 1.0000] |
| Recall@10 | **1.0000** | — |
| Precision@5 | **0.3260** | — |

## Per-category breakdown

| Category | n | nDCG@10 | MRR | Recall@10 | Precision@5 |
|---|---|---|---|---|---|
| single-session-user | 17 | 1.0000 | 1.0000 | 1.0000 | 0.2000 |
| single-session-assistant | 17 | 1.0000 | 1.0000 | 1.0000 | 0.2000 |
| single-session-preference | 17 | 1.0000 | 1.0000 | 1.0000 | 0.2000 |
| temporal-reasoning | 17 | 1.0000 | 1.0000 | 1.0000 | 0.4471 |
| knowledge-update | 16 | 1.0000 | 1.0000 | 1.0000 | 0.4000 |
| multi-session | 16 | 1.0000 | 1.0000 | 1.0000 | 0.5250 |

## Answer vs Abstention split

| Variant | n | nDCG@10 | MRR | Recall@10 |
|---|---|---|---|---|
| answer | 94 | 1.0000 | 1.0000 | 1.0000 |
| abstention | 6 | 1.0000 | 1.0000 | 1.0000 |

Note: for `_abs` (abstention) questions the gold is still a session id, so retrieval can still match. The semantic interpretation differs (the *generator* should refuse to answer even when the right session is retrieved), but for a retrieval-only metric this orthogonal split is informational rather than directly comparable.

## Methodology

**FTS5 branch:** SQLite virtual table with `unicode61 remove_diacritics 2` tokenizer, BM25 ranking, OR-joined phrase tokens, top-20 candidates. Scoped to one question's haystack via `WHERE question_id = ?`.

**Dense branch:** Gemini `gemini-embedding-001` with `outputDimensionality=3072`. Document embeddings use `taskType=RETRIEVAL_DOCUMENT`; query embeddings use `RETRIEVAL_QUERY`. Embeddings L2-normed at write time so cosine = dot product. Top-20 by cosine.

**Fusion:** Reciprocal Rank Fusion (Cormack et al., 2009) with k=60. score(doc) = Σ 1/(k + rank_i + 1) across both rankings. Top-10 after fusion → metrics.

**Sampling:** stratified by base category (6 levels), `_abs` variants folded into their parent for sampling and tracked separately on output. Per-category LCG shuffle (Numerical Recipes constants) with seed `SEED + sum(ord(c) for c in cat)` for cross-category independence. Target n=100 distributed evenly (16-17 per cat).

**Gold encoding:** chunk `c` is relevant iff `c.session_id ∈ answer_session_ids` for that question. Multiple gold sessions per question are typical for multi-session and temporal-reasoning categories.

**Citation:** Di Wu et al. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. ICLR 2025. arXiv:2410.10813.

## Reproducibility

```bash
export GEMINI_API_KEY=AIza...
cd paper/publication/baselines
python3 longmemeval_hybrid_eval.py full
```

Output JSONL (one row per question):
`paper/results/longmemeval-hybrid-results.jsonl`
