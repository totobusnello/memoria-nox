# E04 LOCOMO — Hybrid (FTS5 + Gemini + RRF) vs FTS5 baseline

> ⚠️ **STATUS: pipeline ready, results PENDING `GEMINI_API_KEY`.**
> This document will be regenerated automatically by `locomo_hybrid_eval.py full`
> once the key is provided. Run wall-clock ETA: 5–10 min, cost ≈ \$0.05–0.10.

## What this is

A self-contained Python re-implementation of memoria-nox's hybrid retrieval
architecture (FTS5 BM25 + Gemini `gemini-embedding-001` 3072d dense + RRF k=60),
evaluated on the **same 100-query stratified subset of LOCOMO** used by the
E04 FTS5 baseline. Same `seed=42`, same metric functions, same gold mapping.

## What this is NOT

1. **NOT a test of memoria-nox production code paths.** It validates the
   architectural shape — that FTS5 + dense + RRF yields uplift over FTS5-only
   on conversational long-context retrieval. Production-path validation
   requires running the same 100 queries through `nox-mem search` against an
   isolated DB; that is a separate work item.
2. **NOT a full LOCOMO run** — n=100 stratified (20 per category × 5),
   not the full 1,986 questions. Same subset as E04 for apples-to-apples Δ.
3. **NOT a head-to-head against other hybrid stacks** (e.g. nox-mem +
   e5-multilingual, or BEIR-trained dense retrievers). That is the
   E04-companion work item.

## How to reproduce

```bash
export GEMINI_API_KEY=AIza...                       # from https://aistudio.google.com/app/apikey
cd paper/publication/baselines
python3 locomo_hybrid_eval.py full
# Output (auto-overwrites):
#   /tmp/locomo10.json                              (corpus cache)
#   /tmp/locomo-hybrid-eval.db                      (turns + embeddings cache)
#   ../results/locomo-hybrid-results.jsonl          (100 lines, same shape as FTS5)
#   ../results/locomo-hybrid-vs-fts5-summary.md     (this file, regenerated)
```

Idempotent: re-running `full` skips re-embedding already-embedded turns.

## Reference numbers (FTS5 baseline E04, for comparison)

These are the numbers Hybrid will be compared against. From
`paper/publication/results/locomo-fts5-baseline-results.jsonl` (n=100, seed=42):

| Metric | FTS5 baseline |
|---|---|
| nDCG@10 | 0.2810 |
| MRR | 0.2795 |
| Recall@10 | 0.3792 |
| Precision@5 | 0.0780 |

Per-category (n=20 each):

| Category | FTS5 nDCG@10 | FTS5 MRR | FTS5 Recall@10 |
|---|---|---|---|
| 1. single-hop | 0.1179 | 0.1663 | 0.1625 |
| 2. multi-hop | 0.3708 | 0.3272 | 0.5250 |
| 3. temporal | 0.2887 | 0.3017 | 0.3833 |
| 4. open-domain | 0.3746 | 0.3539 | 0.5250 |
| 5. adversarial | 0.2531 | 0.2483 | 0.3000 |

## Hybrid pipeline (what gets executed when key is provided)

1. **FTS5 branch** — reused via `from locomo_eval import …`. Identical
   tokenizer (`unicode61 remove_diacritics 2`), BM25 ranking, OR-joined
   phrase tokens, top-20 candidates per query. Zero divergence from E04.
2. **Dense branch** — Gemini `gemini-embedding-001`:
   - Documents (5,882 turns): `taskType=RETRIEVAL_DOCUMENT`,
     `outputDimensionality=3072`, L2-normed at write, stored as
     `BLOB` in `/tmp/locomo-hybrid-eval.db`.
   - Queries (100): `taskType=RETRIEVAL_QUERY`, same dim, same normalisation.
   - Top-20 by cosine similarity (cosine = dot product after L2-norm).
3. **Fusion** — Reciprocal Rank Fusion (Cormack, Clarke, Büttcher 2009)
   with k=60. Per-doc score = Σ 1/(k + rank_i + 1) across both rankings
   (1-indexed). Top-10 after fusion → fed to metric computation.
4. **Metrics** — `ndcg_at_k`, `mrr`, `recall_at_k`, `precision_at_k`
   imported from `locomo_eval.py` (zero re-implementation, zero drift).
5. **CI** — 95% confidence interval on mean nDCG@10 via normal
   approximation (n=100 sufficient).

## Output shape (when results land)

`paper/publication/results/locomo-hybrid-results.jsonl` — 100 lines, same
schema as FTS5 baseline:

```json
{"query": "...", "category": 1, "category_name": "single-hop",
 "ndcg_at_10": 0.XX, "mrr": 0.XX, "recall_at_10": 0.XX,
 "precision_at_5": 0.XX, "n_gold": N, "n_retrieved": 10}
```

Drop-in compatible with any downstream analysis tooling that already
consumes `locomo-fts5-baseline-results.jsonl`.

## Caveats (re-stated, copy to paper §5.2 if cited)

1. **Python re-implementation, NOT production code path.** Validates the
   *shape* of the hybrid retrieval. nox-mem TypeScript pipeline path
   validation is separate.
2. **Sample n=100, same seed=42 as E04** — direct comparison, not full corpus.
3. **Embedding cache local to script** (SQLite BLOB). Production nox-mem
   uses `vec_chunks` + `vec_chunk_map` (sqlite-vec). Retrieval semantics
   identical; persistence layer differs.
4. **Binary gold relevance** — chunk-id match against query evidence list.
   LOCOMO does not provide graded relevance judgments.
5. **Embedding model + dim match production** (`gemini-embedding-001`, 3072d).
6. **RRF k=60 matches production** nox-mem fusion constant.

## Next steps after first successful run

- [ ] Confirm Hybrid nDCG@10 uplift vs FTS5 (expected positive on multi-hop
      and adversarial categories where lexical surface overlap is weakest)
- [ ] Bootstrap CI on Δ nDCG@10 to test if uplift is statistically significant
- [ ] Optional: ablate (FTS-only, dense-only, hybrid) to isolate dense vs RRF contribution
- [ ] Roll forward into paper §5.2 prose update

## Files

- Adapter: `paper/publication/baselines/locomo_hybrid_eval.py`
- Reused baseline adapter: `paper/publication/baselines/locomo_eval.py`
- FTS5 baseline results: `paper/publication/results/locomo-fts5-baseline-results.jsonl`
- Hybrid per-query results (pending): `paper/publication/results/locomo-hybrid-results.jsonl`
- This summary (auto-regenerated on each `full` run): this file.
