# nox-mem Hybrid FULL Corpus — Canonical Q4 Baseline

**Date:** 2026-05-24  
**Branch:** feat/q4-nox-hybrid-full-corpus  
**Supersedes:** PR #311 (FTS5 full baseline 0.3753), PR #318 (hybrid@500 cap test 0.0918 / LoCoMo-only 0.1835)  
**Run time:** 2026-05-24 02:52–03:40 BRT (48 min total: ~47min ingest + ~1min queries)

---

## Setup

- **NOX_EVAL_MODE=hybrid** (`eval/q4-comparison/adapters/nox_mem.py`)
- **No corpus cap** — all 6,830 chunks ingested (6,822 unique after dedup)
- **Model:** `models/gemini-embedding-001` (3072d vectors, sqlite-vec vec0 storage)
- **Fusion:** FTS5 BM25 + Gemini dense, RRF k=60 (identical to prod nox-mem pipeline)
- **DB:** `eval/q4-comparison/cache/hybrid/nox-mem-eval-hybrid.db` (isolated, not prod)
- **Ingest rate:** ~2.4 chunks/sec (50ms rate delay + Gemini API latency + SQLite WAL writes)
- **Corpus:** LoCoMo (5,882 chunks) + LongMemEval oracle split (948 chunks) = 6,830 total
- **Dedup:** 8 duplicate chunk IDs across datasets → 6,822 ingested (INSERT OR IGNORE)

---

## Results — Canonical Headline

| System | Corpus | n_queries | nDCG@10 | R@10 | MRR | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|---|---|---|
| **nox-mem hybrid** | **FULL (6822)** | **20** | **0.4509** | **0.5958** | **0.4250** | **466** | **576** | **586** |
| agentmemory | partial | 20 | 0.1376 | 0.2500 | 0.1030 | 14 | 31 | 73 |
| mem0 | @500 | 20 | 0.1315 | 0.1500 | 0.1250 | 263 | 1114 | 1482 |
| nox-mem FTS5 | FULL | 20 | 0.3753* | — | — | — | — | — |
| nox-mem hybrid | @500 (cap) | 20 | 0.0918 | 0.2000 | 0.0575 | 511 | — | — |

*PR #306/311 FTS5 full baseline (no Gemini embeddings).

---

## Per-Dataset Breakdown

| Dataset | n | nDCG@10 | R@10 | MRR |
|---|---|---|---|---|
| **LoCoMo** | 10 | **0.4535** | **0.6417** | **0.4167** |
| **LongMemEval** | 10 | **0.4483** | **0.5500** | **0.4333** |

Both datasets strong — no corpus ordering artifact (unlike the @500 cap run where LongMemEval = 0).

---

## Per-Category Breakdown

| Category | nDCG@10 | n |
|---|---|---|
| multi-hop | **1.0000** | 2 |
| single-session-assistant | **1.0000** | 1 |
| single-session-preference | **1.0000** | 1 |
| temporal-reasoning | **0.6934** | 2 |
| open-domain | **0.5308** | 2 |
| single-hop | **0.5216** | 2 |
| knowledge-update | 0.3026 | 2 |
| multi-session | 0.2456 | 2 |
| adversarial | 0.2153 | 2 |
| temporal | 0.0000 | 2 |
| single-session-user | 0.0000 | 2 |

**Strengths:** multi-hop, multi-turn, temporal-reasoning, open-domain.  
**Weaknesses:** temporal (exact date recall), single-session-user. Both consistent with known nox-mem retrieval model.

---

## Comparison vs Prior Baselines

| Baseline | nDCG@10 | Delta vs this run |
|---|---|---|
| **nox-mem hybrid FULL** (this run) | **0.4509** | — |
| nox-mem FTS5 FULL (PR #311) | 0.3753 | **+20.1% lift from Gemini hybrid** |
| mem0@500 (PR #311) | 0.1315 | **+243% above mem0** |
| nox-mem hybrid@500 LoCoMo-only (PR #318) | 0.1835 | +146% (full corpus vs partial) |
| nox-mem hybrid@500 aggregate (PR #318) | 0.0918 | +391% (corpus artifact eliminated) |
| agentmemory (partial) | 0.1376 | **+228% above agentmemory** |

---

## Key Findings

1. **Full corpus Gemini hybrid = 0.4509 nDCG@10** — new Q4 canonical baseline. Supersedes
   FTS5-only full (0.3753) and all capped runs.

2. **+20.1% over FTS5 full corpus.** Gemini semantic retrieval on top of BM25 adds meaningful
   lift even when FTS5 already has full coverage. RRF fusion earns its cost.

3. **+243% above mem0@500.** Comparison is not perfectly apple-to-apple (mem0 was capped at
   500). But even LoCoMo-only mem0 ≈ 0.1315. nox-mem full = 0.4535 on LoCoMo → >3× lift.

4. **LongMemEval 0.4483 nDCG@10** — strong cross-domain generalization. The @500 run returned
   zero on this dataset (corpus ordering artifact). Full ingest resolves the issue completely.

5. **Latency: p50=466ms, p95=576ms.** Dominated by Gemini embed API (~400-500ms per query).
   Consistent with prod nox-mem latency observations. Acceptable for async memory retrieval.

6. **Zero errors across 6,822 ingest + 20 search.** sqlite-vec vec0 pipeline (3072d float32,
   struct.pack format) robust at scale.

---

## Cost Accounting

| Phase | Count | Avg chars | Total chars | Cost (est.) |
|---|---|---|---|---|
| Document embed (ingest) | 6,822 chunks | ~2,000 chars | ~13.6M | ~$0.34 |
| Query embed (search) | 20 queries | ~100 chars | ~2,000 | ~$0.00005 |
| **Total** | | | ~13.6M | **~$0.34** |

Rate: gemini-embedding-001 at $0.000025/1K chars. Actual wall-clock: 47min ingest + 1min queries.

---

## Implementation Details

New env vars in nox_mem adapter:
- `NOX_EVAL_MODE=hybrid` — activates FTS5+dense+RRF path
- `NOX_HYBRID_DB_PATH` — isolated eval DB path (never prod nox-mem.db)
- `GEMINI_API_KEY` — required, sourced from `/tmp/q4-gemini-env.sh` (chmod 600, not committed)

Schema (isolated eval DB):
- `eval_chunks` + `eval_chunks_fts` (FTS5 BM25)
- `eval_vecs` (vec0, 3072d float32 BLOB) + `eval_chunk_rowids` (FTS5↔vec0 rowid map)

Search pipeline:
1. FTS5 BM25 → top k×3 candidates
2. Gemini dense (`models/gemini-embedding-001`, task_type=RETRIEVAL_QUERY) → vec0 ANN → top k×3
3. RRF k=60 fusion → final top-k ranking

Ingest: `INSERT OR IGNORE` on chunk_id. Idempotent. Embeds text[:2000]. Stores as `struct.pack(f"{len(vec)}f", *vec)`.

---

## Implications for Paper §6.3

Add row to comparison table:

```
nox-mem hybrid (full, 6822 chunks) | 0.4509 | 0.5958 | 0.4250 | 466ms
```

Narrative updates:
- **Primary Q4 result**: nox-mem Gemini hybrid achieves 0.4509 nDCG@10 on 20-query
  joint evaluation (LoCoMo + LongMemEval), representing +20.1% over the FTS5 baseline
  and +243% over mem0.
- The full corpus result resolves the corpus-cap artifact from the @500 run. Both datasets
  perform equally well (LoCoMo 0.4535, LongMemEval 0.4483), demonstrating generalization.
- Temporal categories remain the primary weakness (0.0000 nDCG@10 on 2 exact-date queries).
  This is a known limitation of chunk-based retrieval without temporal indexing; addressed
  by the temporal spike (PR #181) in prod.

---

## Launch Narrative Impact

- **Before this run:** "hybrid@500 LoCoMo = 0.1835 vs mem0@500 = 0.1315" (+40% — already
  in README/PRs #326+)
- **After this run:** "hybrid FULL = 0.4509 vs mem0@500 = 0.1315" (**+243%** at full corpus)
- README update consideration: the full-corpus number (0.4509) is a stronger story but
  comparison to mem0@500 is not apples-to-apples. Recommend keeping the LoCoMo@500 comparison
  in launch materials and reserving 0.4509 for paper §6 where methodology is explicit.

---

## Security Verification

```
git grep -l 'AIza'  → 0 matches
git grep -l 'GEMINI_API_KEY=' → 0 matches (env var names only, no values)
```

No secrets in output JSON, audit doc, or committed files. Key only in `/tmp/q4-gemini-env.sh` (chmod 600, outside repo).

---

## Raw Output

- `eval/q4-comparison/output/nox_mem.json` — 20 queries, hybrid mode, 2026-05-24T02:52–03:40Z
- `eval/q4-comparison/output/_aggregate.json` — computed metrics
- `eval/q4-comparison/output/_aggregate.md` — human-readable table
- `eval/q4-comparison/cache/hybrid/nox-mem-eval-hybrid.db` — 6,822 chunks + vectors (not committed, .gitignore)
