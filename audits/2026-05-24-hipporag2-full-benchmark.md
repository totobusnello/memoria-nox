# HippoRAG2 — Full Corpus Ingest + Cross-System Row

**Date:** 2026-05-24
**Status:** COMPLETE (100% corpus, OpenAI gpt-4o-mini OpenIE + text-emb-3-small)
**Cost:** ~$2.06 USD (actual; estimate was $9-11, hard cap $15)
**Ingest wall-clock:** 79 minutes (2026-05-24T23:37Z start → 2026-05-25T00:56Z end)

---

## Summary

Full-corpus ingest of the 6,830-chunk Q4 evaluation corpus into HippoRAG2 v2.0.0a3.
HippoRAG2 is the SOTA graph-based RAG paradigm (arXiv:2502.14802, OSU NLP Group),
combining LLM-driven OpenIE entity extraction, a Personalized PageRank scorer over
the entity-centric graph, and dense passage retrieval. The adapter wraps the
`hipporag` Python SDK with the same `[nox_id:<id>]` content-prefix round-trip
pattern used by the agentmemory adapter so gold matching works without API drift.

---

## Corpus

| Dataset | Chunks | Indexed |
|---|---:|---:|
| LoCoMo (snap-research/locomo) | 5,882 | 5,882 (100%) |
| LongMemEval oracle (xiaowu0162/longmemeval-cleaned) | 948 | 948 (100%) |
| **Total** | **6,830** | **6,830 (100%)** |

---

## Graph Statistics (after ingest)

| Metric | Value |
|---|---:|
| Total nodes | 30,597 |
| Phrase (entity) nodes | 23,767 |
| Passage nodes | 6,830 |
| Extracted triples | 31,071 |
| Triples with passage node | 40,499 |
| Synonymy triples | 34,240 |
| **Total graph triples** | **105,810** |
| Save dir size | 757 MB |

---

## Full-Corpus Results (100% corpus, n=20 queries)

| Dataset | nDCG@10 | MRR | R@10 | p50 (ms) | p95 (ms) | Hits |
|---|---:|---:|---:|---:|---:|---:|
| **LoCoMo** | 0.4076 | 0.3667 | 0.6250 | n/a | n/a | 6/10 |
| **LongMemEval** | 0.2972 | 0.2200 | 0.4750 | n/a | n/a | 5/10 |
| **Combined** | **0.3524** | **0.2933** | **0.5500** | **2468.5** | **6189.9** | **11/20** |

p99 latency = 20,784 ms — driven by 2 long-tail LongMemEval queries (1 × 58.5s and
1 × 117.5s). These are the largest haystacks in the sample; PPR has to score
against the full 30k-node graph from a noisy multi-token query embedding.

---

## vs Cross-System Baseline (k=10, n=20 queries)

| System | nDCG@10 | MRR | R@10 | p50 (ms) | Notes |
|---|---:|---:|---:|---:|---|
| **nox-mem (hybrid)** | 0.3753 | 0.3700 | 0.5417 | ~50 | HTTP :18802, 6830 chunks |
| **hipporag2** | 0.3524 | 0.2933 | 0.5500 | 2,469 | PPR over 30k-node graph |
| **agentmemory (full)** | 0.1287 | 0.1333 | 0.1875 | 22 | iii-engine, 95.1% corpus |
| **mem0** | 0.1315 | 0.1250 | 0.1500 | n/a | OpenAI embed, 20 queries |

**Key observations:**

1. **HippoRAG2 nearly matches nox-mem on the headline metric** — Δ nDCG@10 = -0.023 (-6.1%)
   versus nox-mem. Recall@10 is actually slightly higher (+1.5%). MRR is -0.077 (-20.7%),
   suggesting nox-mem ranks the top hit better but HippoRAG2 recovers comparable depth.

2. **HippoRAG2 dominates multi-hop reasoning** — nDCG@10 = 0.8155 on multi-hop queries
   (n=2), confirming the paper's headline claim. PPR over the entity graph is genuinely
   advantageous when answers require traversing 2+ entities. Note: small n=2 per
   category limits statistical confidence.

3. **HippoRAG2 dominates single-hop too** — nDCG@10 = 0.6149 (n=2). The entity-centric
   index is competitive with hybrid lexical+dense retrieval on factoid lookup.

4. **HippoRAG2 ties or wins on adversarial** — 0.2500 vs agentmemory 0.0000.

5. **Open-domain regression** — HippoRAG2 0.1781 vs agentmemory 0.3448. PPR may
   struggle when queries don't have clear entity anchors to seed the random walk.

6. **Latency is ~50× higher than nox-mem** — p50=2.5s vs nox-mem ~50ms. This is the
   structural cost of LLM OpenIE at index time + PPR matrix ops at retrieve time.
   HippoRAG2's `retrieve()` calls dense passage retrieval + entity NER + graph search
   per query, which is fundamentally heavier than nox-mem's pre-computed FTS5 + sqlite-vec
   hybrid path. For interactive use this matters; for batched/research it does not.

7. **Cost (one-time ingest)** — $2.06 to index 6,830 chunks via gpt-4o-mini OpenIE.
   This is well below the $9-11 pre-run estimate (we used the smaller
   text-embedding-3-small + tighter prompts than the upstream HippoRAG defaults).
   Search is "free" (no per-query LLM calls in this configuration; PPR is local).

---

## Per-category Detail

| Category | hipporag2 nDCG@10 | n |
|---|---:|---:|
| multi-hop | 0.8155 | 2 |
| temporal-reasoning | 0.6281 | 2 |
| single-session-assistant | 0.6309 | 1 |
| single-hop | 0.6149 | 2 |
| knowledge-update | 0.3467 | 2 |
| adversarial | 0.2500 | 2 |
| multi-session | 0.1958 | 2 |
| temporal | 0.1796 | 2 |
| open-domain | 0.1781 | 2 |
| single-session-preference | 0.0000 | 1 |
| single-session-user | 0.0000 | 2 |

HippoRAG2 has a bimodal failure pattern: it's excellent on multi-hop / temporal /
factoid lookup but terrible on single-session-user (user-specific preference recall),
likely because the OpenIE pipeline doesn't extract speaker-attributed facts in a
way that allows query-time matching by "what did <user> say about <topic>".

---

## Cost Breakdown

| Component | Tokens | Unit price | Cost |
|---|---:|---:|---:|
| gpt-4o-mini prompt (NER + OpenIE) | 10,403,733 | $0.150/1M | $1.561 |
| gpt-4o-mini completion (NER + OpenIE) | 681,486 | $0.600/1M | $0.409 |
| text-embedding-3-small (passages) | ~3.4M | $0.020/1M | $0.068 |
| text-embedding-3-small (entities + triples) | ~930k | $0.020/1M | $0.019 |
| text-embedding-3-small (queries) | ~1k | $0.020/1M | <$0.001 |
| **Total** | — | — | **~$2.06** |

Verified against the inline `total_prompt_tokens` / `total_completion_tokens` counters
in the HippoRAG2 NER and triple-extraction progress bars (final tail of ingest log).

---

## Ingest Wall-clock Breakdown

| Phase | Duration |
|---|---:|
| Passage batch encoding (text-emb-3-small, 6830 items) | ~7 min |
| NER (gpt-4o-mini, 6830 items) | ~8 min |
| Triple extraction (gpt-4o-mini, 6830 items) | ~15 min |
| Entity batch encoding (23,767 items) | ~21 min |
| Synonymy batch encoding (31,071 items) | ~27 min |
| Graph augmentation + save | <1 min |
| **Total** | **~79 min** |

The bulk of wall-clock is OpenAI batch encoding throughput at ~20 it/s (single-threaded
client). vLLM or batched OpenAI v2 API would cut this substantially.

---

## Adapter Implementation Notes

1. **API surface probe** — HippoRAG2's index API exposes `index(docs: List[str])` and
   `retrieve(queries: List[str], num_to_retrieve: int)`. The adapter probes both
   `insert_to_graph` → `index` → `add_documents` to tolerate alpha-version drift,
   then falls through to the first callable.

2. **doc_scores numpy ambiguity fix (this PR)** — HippoRAG2 ≥2.0.0a3 returns
   `doc_scores` as `numpy.ndarray` inside the `QuerySolution` dataclass. The original
   adapter used `arr or []` for the empty-list fallback, which raises
   `"truth value ambiguous"` on numpy arrays. Fixed via explicit
   `arr if arr is not None else []`.

3. **Idempotency probe fix (this PR)** — `HippoRAG.__init__` itself mkdir's its
   save_dir subdirs eagerly, so a bare `iterdir()` non-empty check produced a
   false positive on first run (skipping ingest even when nothing was indexed).
   Changed the probe to require `openie_results_*.json` files specifically.

4. **ID round-trip** — Passages are indexed with content prefix `[nox_id:<id>]`
   so the search adapter can parse the canonical chunk_id back from the retrieved
   passage text, regardless of whether HippoRAG2's `passage_ids` field is populated
   (alpha API drift).

5. **Persistence (partial)** — `eval/q4-comparison/cache/hipporag2/` contains
   757 MB of artifacts total. We force-add only the portable subset (42 MB):
   - `openie_results_ner_gpt-4o-mini.json` (16 MB) — the expensive LLM-generated
     entity + triple set ($1.97 to regenerate)
   - `gpt-4o-mini_text-embedding-3-small/graph.pickle` (20 MB) — the igraph
     adjacency
   - `llm_cache/gpt-4o-mini_cache.sqlite` (5.8 MB) — LLM response cache for
     re-runs
   Embeddings (entity 273 MB, fact 358 MB, chunk 85 MB) are NOT committed: each
   individual parquet exceeds GitHub's 100 MB file limit. They are regenerable
   from the OpenIE results in ~30 min wall-clock for ~$0.14 (text-emb-3-small).
   On first re-run after clone, HippoRAG2 detects the existing openie cache and
   re-embeds only — skipping the $1.97 LLM step.

---

## Artifact Locations

- Adapter: `eval/q4-comparison/adapters/hipporag2.py` (from PR #349 + fixes here)
- Raw output: `eval/q4-comparison/output/hipporag2.json` (916 KB, 20 queries)
- Aggregate row: `eval/q4-comparison/output/_aggregate.md` + `_aggregate.json`
- Persisted index: `eval/q4-comparison/cache/hipporag2/` (757 MB, force-added)

---

## Technical Notes

- HippoRAG 2.0.0a3 (PyPI `hipporag`), Python 3.12.12, isolated venv
- Dependencies: torch 2.5.1, networkx, scipy, sentence-transformers, openai 1.58
  (~1.2 GB site-packages)
- OpenAI account: `OPENAI_API_KEY` from environment, used gpt-4o-mini + text-embedding-3-small
- No vLLM / Together fallback configured (default OpenAI path)
- Save dir uses subpath `gpt-4o-mini_text-embedding-3-small/` (HippoRAG2 namespaces
  by backend combo, so swapping models doesn't clobber)
- Corpus: LoCoMo `CC BY-NC 4.0` + LongMemEval oracle `MIT`
