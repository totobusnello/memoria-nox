# Path E+F+H Combo — KG Traversal + RRF Tune + Top-K Expansion

**Date:** 2026-05-24
**Branch:** `feat/q4-path-efh-combo`
**Mission:** Close gap to mem0@500 (Δ -0.0397 nDCG@10) WITHOUT changing the embedding model.
**Baseline:** PR #318 — `nox_mem` hybrid@500 = 0.0918 nDCG@10 vs `mem0`@500 = 0.1315.

---

## TL;DR

**VERDICT: NEUTRAL → close-as-documented negative result, with one isolated salvage.**

- Best aggregate config (E+F or F alone) = **0.0940 nDCG@10 (+2.4% vs baseline)**.
- Gap to mem0@500 still **-0.0375** (vs baseline gap -0.0397). Material closure failed.
- **The entire +0.0022 gain comes from F (RRF k=20), not E (KG).** F-only achieves the exact same aggregate as E+F combined.
- E (KG traversal at retrieval time) is **dead-weight at this corpus scale**: zero metric change AND +600ms p50 latency.
- H (top-k expansion to 50) causes **G10b-discipline regression**: adversarial -7.9% / -13.8% depending on whether E is also on.
- Per-category: F (RRF k=20) lifts **open-domain +5.4%** cleanly with **no regressions** — only salvageable lever.

**Recommendation:** Do not ship E or H. Park F (RRF k tune) as an isolated Lab Q1 line. Document negative result for E (1-hop traversal with hub-entity centrality), motivating Lab Q1 P1 chunk-summarisation work where entity discrimination is higher.

---

## Why this combo (hypothesis)

mem0's 0.1315 advantage at the 500-chunk cap is a **density × concentration** effect, not a model-quality effect: their OpenAI-default pipeline extracts compact summary memories per ingest, then matches queries against that compressed surface. nox-mem with FTS5+dense+RRF doesn't have an equivalent compaction step at small corpus sizes, so the surface area shrinks faster than recall.

Three structural advantages we already have but **don't currently exploit at retrieval time** in the @500 hybrid pipeline:

| Lever | Hypothesis | Mem0 has it? |
|---|---|---|
| **E** KG traversal at query time | 1-hop entity expansion adds latent edges between query and corpus | No |
| **F** RRF `k` tuning | Default `k=60` is the defensive Hard Mutex value; at small corpus, lower `k` strengthens top-1 emphasis | Effectively yes |
| **H** Top-k expansion | 30 → 50 candidates → more material for KG rerank | Limited by their 500 cap |

All three are **retrieval-time mechanics**, no model change, no ingest change. Bounded blast radius: env flags only, baseline reverts to byte-identical PR #318 when all flags unset.

---

## Setup

- **DB:** `eval/q4-comparison/cache/efh/nox-mem-hybrid-500.db` — first 500 LoCoMo chunks from the PR #338 full hybrid DB. Subset built by `scripts/build_efh_500_db.py` (no re-embedding cost; same 3072-dim Gemini vectors).
- **KG:** built inline via `scripts/build_efh_kg.py` using `gemini-2.5-flash-lite` for entity/relation extraction.
  - **583 unique entities, 1248 relations, 1821 chunk-entity links** on 498/500 chunks (99.6% success rate).
  - Entity-type distribution: 246 concept, 86 object, 81 other, 72 event, 50 person, 36 place + smaller categories.
- **Queries:** 20 (10 LoCoMo + 10 LongMemEval) from `eval/{locomo,longmemeval}/dry-run-sample.json` (same as PR #318).
- **Adapter:** `eval/q4-comparison/adapters/nox_mem.py` modified with env-flagged knobs.
  - All unset → behaves byte-identically to PR #318.
- **Smoke baseline gate:** `scripts/smoke_baseline_efh.py` confirmed refactored adapter reproduces PR #318 = **0.0918 within ±0.0000** (exact 4-decimal match).

### Gold-coverage reality check

> **Structural ceiling:** the @500 cap intrinsically limits what ANY retrieval strategy can achieve, because most gold chunk IDs are outside the 500-chunk subset.

| Dataset | n_queries | total gold IDs | gold-IDs-in-corpus | queries-with-≥1-gold-in-corpus |
|---|---:|---:|---:|---:|
| LoCoMo | 10 | 21 | 4 (19.0%) | 4 |
| LongMemEval | 10 | 18 | 0 (0.0%) | 0 |
| **Aggregate** | **20** | **39** | **4 (10.3%)** | **4** |

The 4 LoCoMo queries with corpus-resident gold all reference **Melanie** or **Caroline** — both successfully extracted into the KG. Practical implication: KG path was exercised on these 4 queries, but the **1-hop neighbourhood of Melanie/Caroline covers 131-236 of the 583 entities** (22-40%) → too broad, no discrimination signal.

---

## Configs

| # | Label | Knobs | Hypothesis | Status |
|---|---|---|---|---|
| 1 | baseline | (all default — replays PR #318) | reference | baseline |
| 2 | E_kg | `NOX_RETRIEVAL_KG=1` | KG alone lifts in-corpus queries | falsified |
| 3 | EF_kg_rrf20 | + `NOX_RRF_K=20` | combo wins | partial: F drives all gain |
| 4 | EFH_kg_rrf20_expand50 | + `NOX_TOP_K_EXPAND=50` | H amplifies E+F | regression |
| 5 | F_only_rrf20 | `NOX_RRF_K=20` (isolate F) | RRF tune is the real driver | confirmed |
| 6 | H_only_expand50 | `NOX_TOP_K_EXPAND=50` (isolate H) | H is the regression source | confirmed |

Configs 5+6 are diagnostic isolators added after the initial 4-run showed E+F = E (no gain attributable to F) but E+F-vs-E only differs by F. F-only proves F is the entire gain.

---

## Results — aggregate (n=20)

| Config | nDCG@10 | MRR | R@10 | hit@10 | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|
| 1_baseline | **0.0918** | 0.0575 | 0.2000 | 0.2000 | 426.6 | 1201.7 |
| 2_E_kg | 0.0918 | 0.0575 | 0.2000 | 0.2000 | 1036.3 | 1721.3 |
| 3_EF_kg_rrf20 | **0.0940** | 0.0600 | 0.2000 | 0.2000 | 1065.6 | 1741.0 |
| 4_EFH_kg_rrf20_expand50 | 0.0913 | 0.0571 | 0.2000 | 0.2000 | 1089.6 | 1740.3 |
| 5_F_only_rrf20 | **0.0940** | 0.0600 | 0.2000 | 0.2000 | 429.4 | 646.0 |
| 6_H_only_expand50 | 0.0902 | 0.0558 | 0.2000 | 0.2000 | 419.7 | 1218.6 |

**Reference:** mem0@500 = 0.1315 (PR #311). Best E+F+H config still **-0.0375 below mem0**.

## Per-dataset

| Config | LoCoMo nDCG@10 | LongMemEval nDCG@10 |
|---|---:|---:|
| baseline | 0.1835 | 0.0000 |
| E (KG) | 0.1835 | 0.0000 |
| **E+F** | **0.1879** | 0.0000 |
| E+F+H | 0.1826 | 0.0000 |
| **F only** | **0.1879** | 0.0000 |
| H only | 0.1805 | 0.0000 |

LongMemEval = 0 across all configs — gold IDs are outside the 500-chunk subset (corpus loader order exhausts at LoCoMo). This is the same structural ceiling noted in PR #318 audit.

On LoCoMo-only: F (and E+F) hit 0.1879, **beating mem0@500 (0.1315) by +0.0564** on the LoCoMo slice — but this was already PR #318's framing.

## Per-category breakdown

| Category | n | baseline | E_kg | EF_rrf20 | EFH | F_only | H_only |
|---|---:|---:|---:|---:|---:|---:|---:|
| adversarial | 2 | 0.1934 | 0.1934 | 0.1934 | **0.1667 ⚠** | 0.1934 | **0.1781 ⚠** |
| multi-hop | 2 | 0.3155 | 0.3155 | 0.3155 | 0.3155 | 0.3155 | 0.3155 |
| open-domain | 2 | 0.4088 | 0.4088 | **0.4307 ✓** | **0.4307 ✓** | **0.4307 ✓** | 0.4088 |
| (all other 7 categories: 0.0000 across the board — 0 gold-in-corpus) | | | | | | | |

## Per-category regression check (G10b discipline applied)

- **2_E_kg:** no >5% deltas — neutral on every category.
- **3_EF_kg_rrf20:** open-domain +5.4% (single win). No regressions.
- **4_EFH_kg_rrf20_expand50:** open-domain +5.4% WIN, adversarial **-13.8% ⚠ REGRESSION**.
- **5_F_only_rrf20:** open-domain +5.4% (single win). No regressions. **Cleanest config.**
- **6_H_only_expand50:** adversarial **-7.9% ⚠ REGRESSION**, no offsetting win.

---

## Diagnosis — why E (KG) failed

Direct evidence from per-query diagnostic dump (4 LoCoMo queries with gold-in-corpus):

| Query | Query entities | 1-hop |E ∪ N| | Gold rank w/o KG | Gold rank w/ KG |
|---|---|---:|---:|---:|
| "When is Melanie planning on going camping?" | melanie, camping | 131 | 2 | 2 |
| "What did Melanie realize after the charity race?" | melanie, charity race | 132 | 4 | 4 |
| "Why did Caroline choose the adoption agency?" | caroline, adoption agency | 233 | 5 | 5 |
| "What happened to Caroline's son on their road trip?" | caroline, son, road trip | 236 | 5 | 5 |

**Identical ranks pre/post KG boost.** Why:
1. 1-hop neighbourhood of "Melanie" or "Caroline" expands to 131-236 of 583 entities (22-40% of KG).
2. The chunks already top-ranked by hybrid (FTS5+dense+RRF) are ALSO linked to Melanie/Caroline.
3. Both correct and incorrect candidates get boosted 1.5×. Relative order preserved.

**This is the "hub entity centrality" failure mode**: when the query targets a corpus-wide hub entity, 1-hop traversal degenerates to "everything is related." Discrimination requires entity-frequency weighting (TF-IDF on KG) or 2+-hop semantic distance constraints — neither in scope for this combo.

---

## Diagnosis — why H (expansion) failed

Expanding internal candidate pool 30 → 50 surfaces additional **weak FTS5/dense matches** that weren't in the original top-30. These extra candidates dilute the top-10 selection by giving Marginal RRF scores more room to fluctuate. Result:
- Adversarial -7.9% (H-alone) / -13.8% (E+F+H) — the adversarial queries are precisely those where the marginal candidates are misleading.
- open-domain unchanged from F (gain comes from F, not H).

This is consistent with the **G10b lesson** that aggregate metrics hide category-specific damage from candidate-pool growth.

---

## Verdict

**Mission failed: the Path E+F+H combo did NOT close the gap to mem0@500.**

- Best aggregate: **0.0940** (configs E+F or F-only equivalently).
- Gap to mem0@500: **-0.0375** (vs baseline gap -0.0397). Closure of -0.0022, far below the -0.0397 target.
- Best per-category lift: open-domain +5.4% (attributable entirely to F = RRF k=20).
- Net regression risk: H causes adversarial -7.9% to -13.8% across configs.

**Salvage:** F-only (RRF k=20) is a clean, low-risk lever:
- Same aggregate gain as full E+F+H combo (0.0940)
- p50 latency unchanged (~430ms vs E paths ~1050ms)
- Zero per-category regressions
- Single env flag, trivial rollback

E and H are **dead-weight at @500 corpus scale**. Document and park.

---

## Next steps

1. **Ship NOTHING from this PR to prod**. The aggregate gain is too small to ship to a user-facing endpoint, even via the F-only lever. The Mission target was mem0-parity, not +2%.
2. **Park F (RRF k tune) as a Lab Q1 parameter sweep** — test on the FULL 6822-chunk corpus where the hybrid baseline is 0.4509 (PR #338). The +2.4% lift might compound or vanish at scale.
3. **Document negative result for E** — chunk-summarisation (Lab Q1 P1 in the roadmap) is the more promising path. 1-hop KG traversal needs entity discrimination it doesn't have at retrieval-time.
4. **Add audit cross-reference** to PR #337's query-rewrite negative-result audit. Both share the lesson: extra LLM calls at query time, without architectural support, don't beat dense embeddings at small corpus.

---

## Implementation diff summary

`eval/q4-comparison/adapters/nox_mem.py`:
- `_RRF_K = 60` → `_rrf_k()` reading `NOX_RRF_K` (1..200 cap, default 60).
- `k * 3` candidate fetch → `_top_k_expand()` reading `NOX_TOP_K_EXPAND` (10..500, default 30).
- New `_extract_query_entities()` — Gemini Flash Lite query entity extractor, per-process cache.
- New `_kg_one_hop()` — resolves seed entity IDs + 1-hop neighbours via `kg_relations`.
- New `_kg_chunks_for_entities()` — chunked SQL batches of 400 (under 999-param SQLite limit).
- KG boost applied AFTER hybrid fusion, BEFORE final top-k cut. Multiplicative (`score *= 1.5`) applied **once per matching chunk** — no stacking (lesson `[[temporal-spike-patched-regressed-2026-05-20]]`).
- All knobs default to original values → baseline reverts to byte-identical PR #318 behaviour.
- New `get_kg_stats()` for observability (call count, errors, cache size).

`eval/q4-comparison/scripts/`:
- `build_efh_500_db.py` — subsets PR #338 full hybrid DB to first 500 LoCoMo chunks. Idempotent. ~30s. $0 cost.
- `build_efh_kg.py` — Gemini Flash Lite KG extraction. Idempotent. ~11 min. ~$0.02 cost.
- `smoke_baseline_efh.py` — verifies refactored adapter reproduces PR #318 = 0.0918 within ±0.01.
- `run_efh_ablation.py` — 6-config × 20-query ablation. Writes `output/efh_ablation_results.json` + raw per-query JSON.

`audits/2026-05-24-path-efh-combo.md` — this file.

---

## Critical guardrails (lessons in code)

1. **Eval DB pollution trap caught at smoke** — `setup()` with `NOX_EVAL_MODE=hybrid` resumes ingest when `_hybrid_schema_ready()` returns True but no `NOX_MEM_INGEST_LIMIT` is set. First smoke run grew the @500 DB from 500 → 2156 chunks before crashing on a vec0 UNIQUE constraint. Fix: smoke + ablation scripts now both set `NOX_MEM_INGEST_LIMIT=500` explicitly, and DB was rebuilt clean before measurements. Memory `[[eval-harness-must-explicit-isolate-db]]` reinforced.
2. **No stacked boosts** — KG factor applied *once* per matching chunk (`scores[cid] *= boost`). No score-of-score loop, no anchor-inference fallback that re-boosts already-boosted chunks. Lesson `[[temporal-spike-patched-regressed-2026-05-20]]` (-32% nDCG regression from stacked layer self-reinforcement).
3. **Per-category regression check enforced** — required before any config gets shipped. G10b's lesson: aggregate wins can hide single-category regressions (G10b: single-hop +8.22% but multi-hop -3.95%). Applied here, caught H regression on adversarial that would have been invisible at aggregate.
4. **Always isolate the lever** — initial 4-config run showed E+F = 0.0940 but E = 0.0918, suggesting F drove the gain. The added F-only and H-only configs proved it conclusively. Lesson: ablations should isolate every single lever before crediting a combo.
5. **Cost reproducibility** — DB subset reuses Gemini vectors from PR #338 (free). KG extraction is the only $$, capped by the 500-chunk corpus and rate-limited at 10 RPS. Total cost-to-reproduce this audit: **~$0.02**.

---

## Cost actuals

- DB subset (`build_efh_500_db.py`): **$0** (no embeddings — pure SQL subset).
- KG extraction (`build_efh_kg.py`): 498 successful chunks × ~500 tokens × $0.075/1M = **~$0.02** (Gemini Flash Lite).
- Ablation runs (6 configs × 20 queries): 120 query embeddings + 20 KG-entity-extraction Flash-Lite calls per config (cached) = ~$0.0001 in real spend. **<$0.001 effective.**
- Failed smoke run #1 (DB pollution): wasted ~5 min of Gemini quota on partial ingest before crash. Recovered via DB rebuild.
- **Total session cost:** **~$0.025** actual + $0 sunk on prior PR #338 embeddings.

---

## Cross-references

- Baseline: PR #318 (`feat(q4): Gemini hybrid@500 cap test — H1/H2 verdict`)
- Negative-result template: PR #337 (`feat(q4): query rewrite layer — negative result vs mem0 at sparse coverage`)
- Discipline memories: `[[temporal-spike-patched-regressed-2026-05-20]]`, `[[g10b-per-category-mutex-2026-05-21]]`, `[[eval-harness-must-explicit-isolate-db]]`, `[[neural-reranker-evolution-vector]]` (Lab Q1)
- Lab Q1 P1 chunk summariser: motivation reinforced — entity-frequency-weighted KG traversal would be a different but more promising line if pursued
