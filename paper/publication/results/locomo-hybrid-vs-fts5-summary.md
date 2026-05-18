# E04 LOCOMO — Hybrid (FTS5 + Gemini + RRF) vs FTS5 baseline

**Run date:** 2026-05-18 19:16 -03
**Dataset:** snap-research/locomo (CC BY-NC 4.0), `data/locomo10.json`
**Subset:** n=100 stratified (20 per category × 5), seed=42
**Embedding model:** `gemini-embedding-001` (3072d, L2-normed)
**Fusion:** RRF with k=60, top-10 after fusion
**Candidates per branch:** FTS5 top-20, dense top-20

## ⚠️ Caveats (read before citing)

1. **Python re-implementation, NOT production code path.** This script reproduces the *architectural shape* of memoria-nox's hybrid retrieval (FTS5 BM25 + Gemini 3072d dense + RRF k=60). It does NOT execute nox-mem's production TypeScript pipeline. Production-path validation requires running the same queries through `nox-mem search` against an isolated DB — separate work item.
2. **Sample n=100, not full 1986 questions.** Same stratified seed=42 subset as E04 FTS5 baseline, enabling apples-to-apples comparison.
3. **Embedding cache local to this script** (`/tmp/locomo-hybrid-eval.db`). Production nox-mem reuses embeddings across queries via `vec_chunks` table — same effective behaviour for retrieval, different persistence.
4. **Gold relevance is binary** (chunk-id match against query evidence list). LoCoMo does not provide graded judgments.

## Aggregate metrics (n=100)

| Metric | FTS5 baseline (E04) | **Hybrid (this run)** | Δ absolute | Δ relative |
|---|---|---|---|---|
| nDCG@10 | 0.2810 | **0.3338** | +0.0527 | +18.8% |
| MRR | 0.2795 | **0.3200** | +0.0405 | +14.5% |
| Recall@10 | 0.3792 | **0.4403** | +0.0612 | +16.1% |
| Precision@5 | 0.0780 | **0.0960** | +0.0180 | +23.1% |

### 95% CI on nDCG@10 (normal approx, n=100)

- FTS5 baseline: **0.2810** [0.2067, 0.3553]
- Hybrid:        **0.3338** [0.2564, 0.4111]

## Per-category nDCG@10 (n=20 per cat)

| Category | FTS5 | Hybrid | Δ abs | Δ % |
|---|---|---|---|---|
| 1. single-hop | 0.1179 | **0.1775** | +0.0596 | +50.5% |
| 2. multi-hop | 0.3708 | **0.4167** | +0.0459 | +12.4% |
| 3. temporal | 0.2887 | **0.2851** | -0.0036 | -1.2% |
| 4. open-domain | 0.3746 | **0.4578** | +0.0832 | +22.2% |
| 5. adversarial | 0.2531 | **0.3318** | +0.0787 | +31.1% |

## Hybrid per-category — all metrics

| Category | n | nDCG@10 | MRR | Recall@10 | Precision@5 |
|---|---|---|---|---|---|
| 1. single-hop | 20 | 0.1775 | 0.2201 | 0.2517 | 0.0800 |
| 2. multi-hop | 20 | 0.4167 | 0.4171 | 0.4750 | 0.0900 |
| 3. temporal | 20 | 0.2851 | 0.2389 | 0.4500 | 0.1100 |
| 4. open-domain | 20 | 0.4578 | 0.4208 | 0.6000 | 0.1200 |
| 5. adversarial | 20 | 0.3318 | 0.3030 | 0.4250 | 0.0800 |

## Methodology

**FTS5 branch:** identical to E04 baseline — `unicode61 remove_diacritics 2`, BM25 ranking, OR-joined phrase tokens (`fts5_escape` reused via import), top-20 candidates.

**Dense branch:** Gemini `gemini-embedding-001` with `outputDimensionality=3072`. Document embeddings use `taskType=RETRIEVAL_DOCUMENT`; query embeddings use `RETRIEVAL_QUERY`. Embeddings are L2-normed at write time so cosine = dot product. Top-20 by cosine similarity.

**Fusion:** Reciprocal Rank Fusion (Cormack et al., 2009) with k=60. Score per doc = Σ 1/(k + rank_i) across both rankings. Top-10 after fusion → fed to metric computation.

**Metrics:** nDCG@10, MRR, Recall@10, Precision@5 — same functions as E04 (imported from `locomo_eval.py`).

## Reproducibility

```bash
export GEMINI_API_KEY=AIza...
cd paper/publication/baselines
python3 locomo_hybrid_eval.py full
```

Output: `paper/results/locomo-hybrid-results.jsonl` (100 JSONL lines, same shape as FTS5 baseline).
