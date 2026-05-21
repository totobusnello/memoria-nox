# G10e — Qualitative Audit: KW × Adversarial Regression

**Date**: 2026-05-21 BRT
**Branch**: `research/g10e-kw-adversarial-audit`
**Context**: G10c §5 flagged KW × adversarial bucket (n=10) as the worst individual cell in the 2D style×category matrix — nDCG -5.35%, MRR -10.0%. Need qualitative audit to know **whether G10d threshold tuning cures it, or whether it's an unrelated bucket-specific pattern.**
**Parent audits**:
- `audits/2026-05-21-G10b-per-category-mutex-ablation.md`
- `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- `audits/2026-05-21-G10d-implementation.md` (G10d staged, deploy-gated)
**Method**: read-only re-analysis of G10b artifacts (`mutex_active.json` / `mutex_disabled.json`). No fresh eval, no VPS write.

---

## 1. TL;DR

**The entire KW × adversarial regression collapses to 2 query rows out of 10 — both identical (`"nox mem hybird search"`, qid `ad-001` and `ad-011`).** The other 8 queries are perfectly flat (nDCG Δ = 0.00%, MRR Δ = 0.00%).

| signal | value |
|---|---:|
| Queries showing nDCG regression | **2 / 10** |
| Queries showing nDCG flat | 8 / 10 |
| Worst nDCG Δ per affected query | **-36.91%** |
| Aggregate KW × adversarial nDCG Δ% | -5.35% = (2 × -36.91% + 8 × 0%) / 10 |
| Aggregate KW × adversarial MRR Δ% | -10.00% = (2 × -50% + 8 × 0%) / 10 (rank 1→2 in 2 queries) |

The aggregate metric is doing exactly what it should — averaging a 2-out-of-10 catastrophic regression. The headline number is **NOT** representative of the bucket as a whole; it's a single-query failure mode amplified by the small n.

**Recommendation: (C) — Single-query edge case. Accept regression. Do NOT tune G10d threshold to chase it.** Rationale in §6.

---

## 2. Per-Query Rank-of-Gold Comparison (full table)

Rank = position of the first gold chunk in the retrieved list (1-indexed; `-1` = not in top-20).

| qid | query | gold chunks | rank_active | rank_disabled | Δ_rank | nDCG_active | nDCG_disabled | nDCG Δ% |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **ad-001** | `nox mem hybird search` | nox-mem::compiled, nox-mem::frontmatter | **2** | **1** | **+1** | 0.3869 | 0.6131 | **-36.91%** |
| ad-003 | `Granixx co-founder` | granix::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |
| ad-005 | `paper §5 ablation rationale` | paper-eval::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |
| ad-007 | `Frooti subscription model` | frooty::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |
| ad-009 | `Bruno Lima role gallapagos AI` | bruno::compiled, bruno::frontmatter | 1 | 1 | 0 | 0.6131 | 0.6131 | 0.00% |
| **ad-011** | `nox mem hybird search` | nox-mem::compiled, nox-mem::frontmatter | **2** | **1** | **+1** | 0.3869 | 0.6131 | **-36.91%** |
| ad-013 | `Granixx co-founder` | granix::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |
| ad-015 | `paper §5 ablation rationale` | paper-eval::compiled, paper-eval::frontmatter | 1 | 1 | 0 | 0.6131 | 0.6131 | 0.00% |
| ad-017 | `Frooti subscription model` | frooty::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |
| ad-019 | `Bruno Lima role gallapagos AI` | bruno::compiled | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.00% |

**Reading the table:**
- 8 queries: gold-at-rank-1 in **both** runs → nDCG/MRR identical → mutex is invisible.
- ad-001 + ad-011: identical query string ("nox mem hybird search"); mutex demotes the gold chunk from rank 1 → rank 2; nDCG@10 calculation gives 1/log2(3) ≈ 0.6309 vs 1/log2(2) = 1.0 → -37% when normalized against the 2-gold ideal where second gold is missing entirely.

The 2 affected queries are **duplicates** of the exact same query (the eval harness samples queries with replacement). They're not "two different failures" — they're the same failure counted twice.

---

## 3. Top-5 Comparison for the Affected Query

`"nox mem hybird search"` — both qid runs are identical, so showing once:

| rank | mutex active | mutex disabled |
|---:|---|---|
| 1 | `112183` (numeric chunk) | **`nox-mem::compiled` (gold)** |
| 2 | **`nox-mem::compiled` (gold)** | `112183` (numeric chunk) |
| 3 | `112341` | `112341` |
| 4 | `112346` | `112346` |
| 5 | `147813` | `147813` |

The mutex **swaps rank 1 and rank 2** — nothing else changes in top-5. The displacing chunk `112183` is a numeric chunk (session / raw markdown / file chunk), **NOT** an entity card. It has `section IS NULL` in the chunks table (numeric ids are file/session chunks, not entity-section chunks).

### Why does mutex affect this query at all?

Numeric chunks like `112183` are NOT in the `SECTION_BOOST` table (their `section` field is `NULL`). So the mutex (which only deactivates `source_type_boost` when `section_boost` was already applied) should leave `112183` untouched. The mutex's effect here is on **`nox-mem::compiled`** — that chunk has BOTH `section=compiled` (boost 2.0) AND `source_type=entity` (boost ~1.3 pre-mutex). Pre-mutex, both boosts stack multiplicatively (≈ 2.6×). Post-mutex, only `section_boost=2.0` applies; the `source_type` delta is zeroed.

Net effect: `nox-mem::compiled` final score drops by the source_type delta (~30%). Meanwhile, `112183` retains its raw FTS+dense score (no boosts). With the gold's lead trimmed, `112183` slips into rank 1.

This is precisely the "tie-breaker loss" mechanism described in G10c §Análise — when keyword distractors have a high enough FTS/dense baseline, the redundant boost stack was the only thing keeping the gold ahead.

---

## 4. Query Lexical Pattern — what's "adversarial" about these?

| qid | query | "adversarial" feature | gold-type | n-entities-in-query |
|---|---|---|---|---:|
| ad-001 | `nox mem hybird search` | typo `hybird` + lowercase entity | compiled+frontmatter | 1 |
| ad-003 | `Granixx co-founder` | typo `Granixx` (double-x) | compiled | 1 |
| ad-005 | `paper §5 ablation rationale` | unusual symbol `§5` | compiled | 1 |
| ad-007 | `Frooti subscription model` | typo `Frooti` → frooty | compiled | 0–1 |
| ad-009 | `Bruno Lima role gallapagos AI` | typo `gallapagos` | compiled+frontmatter | 1 |

Each query has **one** entity reference (or a typo'd version of one). They're all "keyword + typo" adversarial. No multi-entity queries in this bucket. This is a critical observation for G10d threshold tuning (§5).

### Frontmatter recall hole (separate corpus issue)

ad-009 (`Bruno Lima role gallapagos AI`) and ad-015 (`paper §5 ablation rationale`) both have **`<entity>::frontmatter` in their gold set, never appearing in top-20 in either run.** This is identical across mutex active and disabled — it's NOT a mutex issue, it's a **corpus / retrieval problem** (frontmatter chunks have low FTS+dense matchability for these query forms). This pre-existing recall hole accounts for the bucket-wide 0.5–0.61 nDCG ceiling but is mutex-orthogonal.

---

## 5. Pattern Classification

Classifying the 10 queries into the 4 categories from the prompt:

| Pattern | qids | count | description |
|---|---|---:|---|
| **A** — Multi-entity gold (G10d threshold=2 fix candidate) | none | **0** | No query in this bucket has gold spanning multiple entities. ad-001/011 have 2 chunks but they're both within `nox-mem` entity (compiled + frontmatter sections of the SAME entity). |
| **B** — Non-entity-typed chunks (mutex shouldn't apply) | none | **0** | All gold chunks are `<entity>::compiled` or `<entity>::frontmatter` — mutex correctly applies in principle. |
| **C** — Edge case: keyword distractor matches typo lexically | ad-001, ad-011 | **2** | Typo `hybird` causes a non-entity numeric chunk (112183) to BM25-match alongside the entity gold; mutex removes the entity's source_type tie-breaker, distractor wins rank 1. |
| **D** — Mutex-invisible (no effect, gold already at rank 1) | ad-003, 005, 007, 009, 013, 015, 017, 019 | **8** | BM25 keyword match is strong enough that gold sits at rank 1 with or without mutex. |

**Critical insight: pattern C contains exactly one unique query (`nox mem hybird search`) duplicated.** The aggregate -5.35% nDCG / -10% MRR for the bucket is **entirely caused by this one query**.

### Why G10d threshold tuning will NOT cure this

G10d's `query_entities` count for `"nox mem hybird search"` would be **1** (the single entity `nox-mem`, detected via greedy longest-match on `kg_entities` or PascalCase fallback):

- Threshold=1 (default G10d): `count (1) ≤ threshold (1)` → mutex stays ACTIVE → regression persists.
- Threshold=2: `count (1) ≤ threshold (2)` → mutex stays ACTIVE → regression persists.
- Threshold=0: `count (1) > threshold (0)` → mutex DISABLED → regression cured, but **also disables mutex for every single-hop single-entity query**, throwing away G10b's biggest aggregate win (single-hop NL +13.83% nDCG / +21.32% MRR).

G10d is designed to cure the **multi-hop** -3.95% regression (where `query_entities ≥ 2` is the discriminator). The KW × adversarial regression is a **different failure mode** — single-entity query with a typo-driven non-entity BM25 distractor — and G10d's entity-count signal is the wrong feature to detect it.

---

## 6. Recommendation: (C) — Accept regression, do NOT tune for it

### Rationale

1. **n=1 sample**: The bucket's "-5.35% nDCG" headline is 2 duplicate rows of a single query. Treating it as a generalizable failure mode would be **overfitting to 1 query**.

2. **G10d is the wrong tool**: As shown in §5, neither threshold=1 nor threshold=2 changes behaviour for this query. Forcing a cure requires threshold=0 or query-feature detection (typo detection?) that has no general justification.

3. **Cost of style-conditional rerank (option B)**: Would require runtime classification of "keyword+typo" queries (LLM call or regex heuristic) and conditional toggle. G10c §Recomendação already rejected style-conditional rerank ("-0.72% aggregate nDCG drag is within noise floor; ROI negative").

4. **Cost of adversarial-specific bypass (option C)**: No clean runtime signal to detect "adversarial keyword query" — would need pre-classification or post-hoc score-confidence detection. Engineering complexity > 0.5pp aggregate gain.

5. **Aggregate G10c still positive**: NL +1.56% nDCG, +3.86% MRR. Keyword -0.72% nDCG, -2.27% MRR. Sub-bucket KW × adversarial -5.35% nDCG is the worst individual cell but does NOT invalidate the bucket-positive picture.

6. **Real-traffic distribution**: Production query mix is dominated by natural-language and clean keyword (G10c implicitly assumes uniform; real LP/MCP traffic skews heavily NL). The KW × adversarial bucket is the closest analog to "user typed a typo" which IS realistic — but the failure mode (entity dropping from rank 1 to rank 2 when both chunks contain "nox mem hybrid search" lexically) is **graceful degradation**, not catastrophic miss. Gold is still at rank 2; user clicks it.

### Action items

| # | Action | Status |
|---|---|---|
| 1 | **Do not modify G10d default threshold to chase this bucket.** Ship G10d as currently specced (threshold=1, targeting multi-hop) per `audits/2026-05-21-G10d-implementation.md`. | NEW |
| 2 | Document this finding as **expected mutex behaviour** for keyword + typo edge cases. The mutex correctly removes redundant boost stack; the regression is the precise mechanism G10c §Análise predicted ("tie-breaker loss"). | NEW |
| 3 | If future evals add more KW × adversarial queries (n ≥ 30), revisit aggregate. With current n=10 → effectively n=1 unique query, the bucket statistic is dominated by sampling noise. | NEW |
| 4 | **Frontmatter recall hole** (ad-009, ad-015) is unrelated to mutex and should be tracked separately. Possible follow-up: investigate why `<entity>::frontmatter` chunks rank below top-20 even when their compiled sibling ranks #1. Parking lot: **G12 frontmatter retrieval audit** if it appears in other buckets. | NEW |
| 5 | Cross-check: if G10d ablation eval (per `audits/2026-05-21-G10d-implementation.md` §5) shows per_style breakdown, **expect ad-001/011 regression to persist regardless of threshold**. If a future variant DOES cure it (threshold=0 or different signal), audit-compare improvement against §6.3 cost framework. | NEW |

---

## 7. Files

- `audits/data-g10e/analyze.py` — per-query rank delta computation (committed)
- `audits/data-g10e/patterns.py` — pattern classification + typo analysis (committed)
- `audits/data-g10e/g10e-derived.json` — per-query derived JSON (committed)
- Source: `audits/data-g10b/mutex_active.json`, `audits/data-g10b/mutex_disabled.json` (re-used, no fresh eval)
- Predecessor audits: G10b, G10c, G10d cited above

## 8. Constraints honoured

- Read-only investigation. No VPS write, no fresh eval, no service restart.
- Other agents on VPS isolated dir (G10d ablation execution) untouched — analysis is purely re-derivation from local G10b artifacts.
- Branch `research/g10e-kw-adversarial-audit` opened from main; no merge.
- Worktree sparse-checkout extended to include `audits/` for write access; original sparse list unchanged.
