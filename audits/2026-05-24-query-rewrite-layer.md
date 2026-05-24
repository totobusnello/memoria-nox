# Query Rewrite Layer — match mem0 LLM concentration at sparse coverage

**Date:** 2026-05-24
**Branch:** `feat/q4-query-rewrite-layer`
**Refs:** PR #318 (hybrid@500 baseline), `[[concentration-vs-coverage]]`,
Lab Q1 v2 PR #303 (P1 concentration paradox).

---

## Motivation

PR #318 (Gemini hybrid@500) closed +97% of the FTS5→mem0 gap but still trailed
mem0 by 0.0397 on aggregate (0.0918 vs 0.1315, n=20). The post-mortem narrowed
mem0's edge to **LLM-driven semantic concentration**: each retrieval pass is
re-expressed through a model that surfaces synonyms, entities, and intent that
sparse keyword/dense retrieval misses on small corpora.

This audit documents a parity move — bolting an LLM rewrite layer on top of
nox-mem's existing FTS5+dense+RRF hybrid — so we can isolate whether the gap
is (a) concentration or (b) something structural (mem0's chunker, OpenAI
embeddings, etc.). The layer is **opt-in** behind `NOX_QUERY_REWRITE=1`; the
default hybrid path is untouched.

---

## Architecture

Pipeline (per search request, when rewrite is ON):

```
       user query Q
            │
            ├──► hybrid single pass (FTS5 + Gemini dense + RRF)  ──► S0
            │
            ├──► Gemini Flash Lite rewrite                       ──► [V1, V2, V3]
            │         (prompt: "expand into N semantic variants")
            │
            ├──► hybrid pass (V1) ──► S1
            ├──► hybrid pass (V2) ──► S2
            └──► hybrid pass (V3) ──► S3

            merged = Σ Si  (per-chunk RRF score sum)
            top-k by merged
```

Implementation: `eval/q4-comparison/adapters/nox_mem.py`

| Function | Role |
|---|---|
| `_query_rewrite_enabled()` | reads `NOX_QUERY_REWRITE` env flag |
| `_rewrite_query(q)` | calls Gemini Flash Lite via REST `generateContent`, parses JSON array, dedupes, caches per-process |
| `_parse_rewrite_response()` | JSON parser w/ 3-tier fallback (direct → regex array → newline split, all reject pure-punctuation lines) |
| `_hybrid_single_pass(q, k_fetch, genai)` | extracted single-pass FTS5+dense+RRF (re-used per variant) |
| `_search_hybrid_local(q, k)` | runs baseline pass; if rewrite enabled, runs N variant passes and sums RRF scores |

Rewrite model defaults: `gemini-2.5-flash-lite`, **N=3 variants**,
temperature 0.4, `responseMimeType=application/json`. Overridable via
`NOX_QUERY_REWRITE_MODEL` / `NOX_QUERY_REWRITE_N` (capped 1..6).

Graceful degradation: any network/auth/parse error inside `_rewrite_query`
returns `[]`, so the search silently falls back to the baseline single pass.
Errors are counted (max 5 stderr lines) and surfaced via
`get_rewrite_stats()`.

### Key design choices

1. **Original query always runs as pass S0.** The variants only *augment* —
   they never replace the user's literal phrasing. This guards against
   rewrites that drift off-topic.
2. **Sum, not max.** Chunks that appear in multiple variants are boosted by
   the sum of their RRF contributions. This is the same fusion shape RRF
   already uses inside a single pass — we just fuse across passes, too.
3. **k_fetch = k × 3 per pass.** Each leg fetches 30 results so the
   cross-pass fusion has enough candidates to reward agreement.
4. **Per-process cache** on the exact query string. Re-asking the same
   question costs $0 after the first call. Matches realistic memory-API
   access patterns (same user re-asks similar Q's intra-session).

---

## Cost

| Item | Value |
|---|---|
| Model | `gemini-2.5-flash-lite` |
| Avg input tokens / call | ~150 (prompt template + ≤30-token query) |
| Avg output tokens / call | ~80 (3 variants × ~25 tokens each) |
| Per-query cost (May 2026 list pricing) | **≈ $0.00005** |
| Smoke run (20 queries × 1 LLM call each) | **≈ $0.001** |
| Cache hit rate (repeated identical Q) | 100% — $0 incremental |

This is **~3 orders of magnitude cheaper** than the per-query embed cost
(Gemini 3072d embed-001 dominates at ~$0.000025 per leg; the rewrite layer is
a rounding error). Cost is dominated by the 3 *extra* embeds (the dense leg
re-runs for each variant) — still well under $0.001 per query.

The layer is **off by default** so it never burns quota without an explicit
flip. Lab Q1 P1 budget envelope (TBD) is the gating discussion.

---

## Smoke results — REGRESSION

Smoke run (2026-05-24, 20 queries × 4 passes each, 500-chunk hybrid cap,
gemini-2.5-flash-lite for rewrite, gemini-embedding-001 for dense):

| Variant | nDCG@10 | MRR | R@10 | p50 | Δ vs PR #318 | Δ vs mem0@500 |
|---|---:|---:|---:|---:|---:|---:|
| PR #318 hybrid@500 (baseline) | **0.0918** | 0.0575 | 0.2000 | 511ms | — | -0.0397 |
| mem0@500 (PR #311) | **0.1315** | — | — | n/a | +0.0397 | — |
| **hybrid@500 + rewrite (this PR)** | **0.0810** | 0.0446 | 0.2000 | 2651ms | **-0.0108 (-11.8%)** | **-0.0505** |

**Per-dataset breakdown:**

| Dataset | n | nDCG@10 (rewrite) | nDCG@10 (PR #318) | Δ |
|---|---:|---:|---:|---:|
| LoCoMo | 10 | **0.1620** | 0.1835 | **-0.0215 (-11.7%)** |
| LongMemEval | 10 | 0.0000 | 0.0000 | 0 (corpus not ingested) |

**Per-category (n=2 each — noisy, indicative only):**

| Category | nox-mem rewrite |
|---|---:|
| open-domain | **0.4281** |
| adversarial | **0.2153** |
| multi-hop | 0.1667 |
| knowledge-update / multi-session / single-hop / temporal / single-session-* | 0.0000 |

**Note on LongMemEval @500:** as documented in PR #318, the 500-chunk
cap is exhausted by LoCoMo alone (LoCoMo has 5,882 chunks total).
LongMemEval session IDs are not in the DB, so the 10 LongMemEval queries
return 0 regardless. The clean comparison is the LoCoMo-only slice.

### Verdict: layer does NOT help at @500 — small but consistent regression

- Aggregate nDCG@10 **fell 11.8%** (0.0918 → 0.0810).
- LoCoMo-only nDCG@10 **fell 11.7%** (0.1835 → 0.1620).
- MRR also fell (0.0575 → 0.0446).
- R@10 unchanged (0.2000) — the same chunks are retrieved, just rank lower.
- Latency 5.2× (511ms → 2651ms p50) from the extra 3 passes + 1 LLM call.

### Why it regressed — three hypotheses

1. **Variant noise dominates at sparse coverage.** With only 500 chunks
   in the index, each variant pass surfaces a *different* near-neighbour
   cluster from the dense leg. The cross-pass RRF sum then promotes
   chunks that look broadly "topical" over chunks that *exactly* match
   the original query's anchor entities. At sparse coverage, the original
   query is the highest-precision signal we have — diluting it loses MRR.
2. **Prompt under-specifies rewriting policy.** The current prompt says
   "expand into N semantically related variants." mem0 likely runs a
   different shape: it concentrates by **summarising the corpus** at
   ingest, not by expanding the query at search. So the parity is false:
   we re-implemented the wrong half of the mechanism.
3. **3072d Gemini embeddings already overcover semantically.** Unlike
   keyword retrieval (FTS5) which benefits from synonym expansion,
   Gemini 3072d dense already captures synonyms. Adding 3 paraphrased
   variants is redundant — and the dilution dominates the marginal gain.

### Implication for Lab Q1 P1 (concentration paradox)

This is a **negative result with strong information**: the simplest
parity move (query-side rewriting) does NOT close the gap. That sharpens
the Lab Q1 P1 hypothesis:

- mem0's edge at @500 is most likely **ingest-side concentration**
  (LLM summarising chunks before storage), not query-side rewriting.
- Next experiment for P1: implement an **ingest-time chunk summariser**
  (Gemini Flash Lite per chunk, store both raw + summary, embed the
  summary) and re-run the @500 comparison.
- Alternative: a **rerank-time** rewriter that takes the top-100 hybrid
  results and re-ranks them against a single concentrated query —
  vs the current pre-search expansion which fans out before ranking.

The layer is preserved (off by default) for future ablations — e.g.
on full-coverage runs where the noise dilution argument may invert.

---

## Tests

`eval/q4-comparison/test/test_query_rewrite.py` — 15 cases, all offline (LLM
fully mocked, $0 to run, ~0.3s wall-clock):

1. JSON parsing — bare, fenced, embedded-in-text, garbage rejection
2. `_rewrite_query` calls REST endpoint with key in **query param** (never URL path), N variants returned, prompt embeds query
3. Dedup — variants identical to original (case-insensitive) are filtered
4. Per-process cache — repeat calls hit the cache, only 1 HTTP call
5. Graceful degradation — network error returns `[]`
6. No-key disable — missing `GEMINI_API_KEY` short-circuits before any HTTP
7. `_hybrid_single_pass` returns a per-chunk RRF dict
8. Baseline (rewrite off) — LLM endpoint is **never called**
9. Rewrite on + variants → toy chunks from variant topics appear in top-k
10. Rewrite failure during search → baseline still returns results (no crash)
11. Diversity — variants differ from original
12. `get_rewrite_stats()` exposes counters

Existing `test_nox_mem_ingest.py` (12 cases) still passes — no regressions.

---

## Implications for Lab Q1 P1 (concentration paradox)

The smoke result above lands the **middle branch** of the original
three-way hypothesis: rewrite ≈ baseline (slightly worse, actually).
This was the most-feared outcome but it's the most-useful for Lab Q1 P1
because it eliminates the simplest explanation for mem0's lead.

**Updated P1 priority order:**

1. (highest) **Ingest-side concentration**: implement chunk summarisation
   at ingest, store summary alongside raw, embed the summary. Re-run @500.
   If this closes the gap, we have the mechanism.
2. **Chunker comparison**: mem0 uses smaller, more focused chunks. Run an
   ablation where nox-mem re-chunks LoCoMo with mem0's chunker (sentence-
   level vs message-level). Isolate the chunker contribution.
3. **OpenAI vs Gemini embed**: swap embed model holding everything else
   constant. If mem0's lead drops, the embed model is part of the story.
4. (lowest) **Query rewrite at search time**: only revisit if 1-3 fail to
   close the gap and corpus density goes up. The redundancy argument
   should weaken once the index has thousands of near-duplicates.

The layer is preserved (off by default) so future runs can re-test it
under different conditions (e.g. corpus@5k+, multi-hop-heavy datasets).
The baseline numbers in the paper stay reproducible because
`NOX_QUERY_REWRITE=0` is the default.

---

## Files changed

- `eval/q4-comparison/adapters/nox_mem.py` — added rewrite layer + extracted `_hybrid_single_pass`
- `eval/q4-comparison/test/test_query_rewrite.py` — 15 new test cases (LLM mocked)
- `audits/2026-05-24-query-rewrite-layer.md` — this document
