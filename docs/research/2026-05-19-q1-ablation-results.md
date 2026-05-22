# Q1 LoCoMo Ablation Results — empirical attribution of +100.6% / +112%

> **Author:** executor-high (research/2026-05-19-q1-ablations)
> **Status:** measurement complete — does NOT update paper §5 (Toto decides framing)
> **Trigger:** PR #137 (`docs/RESEARCH/2026-05-19-q1-attribution-investigation.md`) was a static-code analysis that estimated drivers without running anything. This PR runs the actual ablations B/C/D and reports empirical numbers.
> **Eval set:** n=100 stratified seed=42 — IDENTICAL to canonical `locomo_production_path_eval.py` run; 5 categories × 20 each (single-hop, multi-hop, temporal, open-domain, adversarial).
> **Endpoint:** TS production pipeline served via 2nd nox-mem-api on `:18803`, pointing at the same `eval.db` indexed in 2026-05-18.
> **Date measured:** 2026-05-19 11:25–11:45 BRT.

---

## TL;DR — the answer the static analysis got wrong

PR #137 attributed the gap between TS prod-path (+112%) and Python re-impl (+18.8%) to **query expansion + larger semantic pool + 4-batch RRF**. Empirically those drivers contribute **ZERO** to nDCG@10 on this eval set. The real picture, confirmed by 7 ablation runs:

- **The semantic embedding batch alone (gemini-embedding-001, cosine vs 3072d L2-normed) produces the full +100.6% / +112%**.
- **The FTS5 batch in TS prod silently returns 0 results for all 100 LoCoMo questions** because (a) prod's `sanitize` regex doesn't strip `?` and (b) FTS5 default tokenizer treats multi-word matches as implicit AND, so a single problematic token zeros the whole batch.
- **Query expansion (`expandQuery()`)** runs successfully (~1s of Gemini latency per query, confirmed by 3× latency drop when disabled) but the variants it produces ALSO hit empty FTS5 batches, so they contribute zero to the final RRF ranking.
- **Boosts** (BOOST_TYPES, source_type, tier, section, source_date ≤7d) confirmed NULL on this corpus — disabling them all yields byte-identical retrieval, matching PR #137's static prediction on this single point.
- **Semantic candidate pool size**: 80 (current) vs 20 produces byte-identical retrieval — at this eval depth (top-10 scoring) the deeper pool doesn't change the head of the ranking.
- **Fórmula nDCG**: confirmed empirically — D1 (sorted-rel IDCG) = 0.5961, D2 (full-ideal IDCG) = 0.5637. Same retrieval, two formulas.

The "+112%" → "+100.6%" delta from D1 → D2 is the only attribution finding that survives unchanged from PR #137.

---

## 1. Methodology — how the ablations were instrumented

### 1.1 Feature toggles added to TS source (defaults preserve current prod behavior)

Patched `src/search.ts` + `src/search-expansion.ts` on `/root/.openclaw/workspace/tools/nox-mem/` with 5 env-var toggles, all OFF by default:

| Toggle | Effect when `=1` |
|---|---|
| `NOX_DISABLE_BOOSTS` | Skip `BOOST_TYPES`, `source_date ≤7d`, `TIER_BOOST`, `SOURCE_TYPE_BOOST`, `section_boost` in both FTS5 and semantic batches |
| `NOX_DISABLE_EXPANSION` | Bypass `expandQuery()` Gemini call — variants list is always `[original]` |
| `NOX_SEMANTIC_POOL_SIZE=<N>` | Override default `perVariantLimit * 2` (=80 for limit=20) → `<N>` candidates from `semanticSearch` |
| `NOX_SEMANTIC_DISABLE` | Replace semantic batch with empty array |
| `NOX_FTS_DISABLE` | Replace all FTS5 batches (original + variants) with empty arrays |

After all runs, source was reverted from `.bak-pre-ablation` and prod API (`:18802`) restarted clean.

### 1.2 Orchestration

`paper/publication/baselines/run_locomo_ablations.sh` — kills any `:18803` listener, starts 2nd nox-mem-api with toggle env vars + `NOX_DB_PATH=/root/.openclaw/eval/locomo-prod-path/eval.db`, waits for `/api/health`, then runs `locomo_ablation_eval.py` with `--toggles` recorded for traceability.

### 1.3 Two formulas, one pass

`locomo_ablation_eval.py` computes both nDCG@10 formulas on the same retrieved `chunk_id` list per query:

- **D1 (sorted-rel IDCG)** — `locomo_production_path_eval.py:139-144` legacy: `idcg = dcg(sorted-rel-list)` (max possible from retrieved set). More permissive.
- **D2 (full-ideal IDCG)** — `locomo_eval.py:182-188` canonical: `idcg = Σ 1/log2(i+2) for i in range(min(|gold|, k))`. Stricter.

For `|gold|=1` queries (66 of 100) the formulas agree. For `|gold|≥2` (34 of 100) D2 < D1.

---

## 2. Full ablation grid (canonical n=100 seed=42)

| Label | Toggles | nDCG@10 **D2** | Δ vs FTS5 0.2810 | Δ vs Python 0.3338 | nDCG@10 D1 | MRR | Recall@10 | Precision@5 | mean latency | wall-clock |
|---|---|---|---|---|---|---|---|---|---|---|
| FTS5 baseline (E04 reference) | — | 0.2810 | — | -15.8% | — | — | — | — | — | — |
| Python re-impl hybrid (`locomo_hybrid_eval`) | — | 0.3338 | +18.8% | — | — | — | — | — | — | — |
| **D_full_prod** | (none) | **0.5637** | **+100.6%** | +68.9% | **0.5961** (+112.1%) | 0.5534 | 0.7070 | 0.1760 | 1440ms | 144.0s |
| B_no_boosts | `NOX_DISABLE_BOOSTS=1` | 0.5637 | +100.6% | +68.9% | 0.5961 | 0.5534 | 0.7070 | 0.1760 | 1450ms | 145.0s |
| C1_no_expansion | `NOX_DISABLE_EXPANSION=1` | 0.5637 | +100.6% | +68.9% | 0.5961 | 0.5534 | 0.7070 | 0.1760 | 478ms | 47.8s |
| C2_pool_20 | `NOX_SEMANTIC_POOL_SIZE=20` | 0.5637 | +100.6% | +68.9% | 0.5961 | 0.5534 | 0.7070 | 0.1760 | 1439ms | 144.0s |
| C3_no_expansion_pool_20 | both above | 0.5637 | +100.6% | +68.9% | 0.5961 | 0.5534 | 0.7070 | 0.1760 | 424ms | 42.4s |
| **E_fts5_only_via_pipeline** | semantic off | **0.0000** | **-100%** | -100% | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1ms | 0.1s |
| **F_semantic_only** | FTS5 off | **0.5637** | **+100.6%** | +68.9% | **0.5961** | 0.5534 | 0.7070 | 0.1760 | 480ms | 48.0s |

**Verification of per-query retrieval byte-identity:** across D_full_prod / B / C1 / C2 / C3 / F_semantic_only, all 100 queries return the same 20 retrieved chunk_ids in the same order. (Confirmed by diff on per_query lists — 0 diffs out of 100.)

### 2.1 Per-category breakdown (D2, identical across D / B / C1–C3 / F)

| Category | nDCG@10 D2 | nDCG@10 D1 | MRR | Recall@10 |
|---|---|---|---|---|
| single-hop  | 0.5223 | 0.6230 | 0.6163 | 0.6183 |
| multi-hop   | 0.4609 | 0.4609 | 0.4196 | 0.6000 |
| temporal    | 0.4122 | 0.4662 | 0.4142 | 0.5417 |
| open-domain | 0.8387 | 0.8462 | 0.8162 | 0.9250 |
| adversarial | 0.5842 | 0.5842 | 0.5006 | 0.8500 |

D1=D2 in multi-hop and adversarial because every query in those categories has `|gold|=1` (formulas converge).

---

## 3. Attribution table — empirical, with PR #137 estimates side-by-side

| Driver | PR #137 estimate (static) | Empirical (this PR) | Verdict |
|---|---|---|---|
| nDCG formula (D1 vs D2) | ~9pp relative | **+5.4pp absolute / +11pp relative (0.5637 → 0.5961)** | ✅ confirmed; numbers match PR #137 §2 within rounding |
| Query expansion (1 → 3 batches) | ~50% of gap (~30–40pp rel) | **0.0pp** — variants hit empty FTS5 batches | ❌ static estimate wrong |
| Semantic pool 80 vs 20 | ~5–10pp rel | **0.0pp** at top-10 depth | ❌ static estimate wrong |
| Pre-RRF boosts (BOOST_TYPES, source_type, tier, section, recency, salience) | NULL on this corpus | **0.0pp** — disabling all yields byte-identical retrieval | ✅ confirmed |
| Chunk_text enrichment (frontmatter + HTML anchor) | "MEDIUM" — adds rare-token surface for BM25 | **0.0pp on this eval** — FTS5 batch returns 0 docs regardless | ✅ irrelevant because FTS5 itself is dead |
| **Semantic batch (Gemini 3072d cosine)** | not isolated | **THE ENTIRE GAP** — semantic-only reproduces D_full_prod byte-for-byte | 🚨 **dominant driver** |

The Python re-impl's +18.8% comes from a **working FTS5 contribution** (it uses OR-join, so multi-token NL queries return docs) plus dense over a smaller pool. Strip the FTS5 contribution and we'd expect the Python re-impl number to drop. The TS prod pipeline goes the other direction: FTS5 is dead, so the +100.6% is **almost certainly the Gemini embedding model alone**, plus how the chunks were embedded.

### 3.1 Why does TS prod's semantic batch outperform Python re-impl's?

The two pipelines run identical `gemini-embedding-001` model. Differences likely accounting for the gap:

1. **Embedding input differs.**
   - TS prod embeds the full chunk_text (frontmatter + `<speaker>: <text>` + HTML comment anchor).
   - Python re-impl embeds raw `<speaker>: <text>`.
   The richer surrounding context in TS prod likely steers the embedding toward a more discriminative region in the 3072d space.

2. **`task_type` parameter for queries.**
   - Python re-impl uses `task_type=RETRIEVAL_QUERY` (asymmetric).
   - TS prod's `embedText()` — need to verify (out of scope of this PR; flagged as follow-up).

3. **L2-normalization timing.**
   - Python re-impl normalizes embeddings on read.
   - sqlite-vec's `vec_distance_cosine` (or vec0 default) handles normalization differently.

These are hypotheses for a follow-up ablation. For paper §5 framing, the relevant fact is: **the gap is the dense retrieval implementation, not the search-pipeline architecture features**.

---

## 4. Recompute attribution table requested by Toto

Per the task spec, here is the canonical attribution table reformulated against empirical data. Note: rows that were hypothesized in the spec but turn out to be zero-contribution are flagged.

| Config | nDCG@10 D2 | Δ vs FTS5 baseline (0.2810) | Δ vs config anterior | Notes |
|---|---|---|---|---|
| FTS5 baseline (E04, Python OR-join) | 0.2810 | — | — | reference |
| + Gemini semantic + RRF — F_semantic_only equivalent | 0.5637 | **+100.6%** | +100.6% | dense-only on TS prod indexed chunks; semantic batch is the whole story |
| + Query expansion (3 FTS5 batches) — Ablation D minus C1 | 0.5637 | +100.6% | **0.0%** | variants hit empty FTS5; **null contribution** |
| + Larger semantic pool 20 → 80 — D minus C2 | 0.5637 | +100.6% | **0.0%** | head of ranking unchanged at top-10 |
| + Salience shadow → active | *not run* | n/a | n/a | `NOX_SALIENCE_MODE=shadow`; activating would only fire on chunks with `pain > 0.2` (none in eval); null-predicted by PR #137 |
| + section_boost shadow → active | *not run* | n/a | n/a | `NOX_SECTION_BOOST_MODE=shadow`; activating would only fire on `section IS NOT NULL`; all eval chunks have `section=NULL`; null-predicted |
| **D_full_prod (measured)** | **0.5637** | **+100.6%** | — | canonical D2 |
| **D_full_prod D1 (sorted-rel IDCG)** | **0.5961** | **+112.1%** | — | métrica não-standard, headline atual do paper/HANDOFF |

---

## 5. Drivers confirmed NULL on the LoCoMo eval set

These are not "null according to static analysis" — these are **empirically null** measured against byte-identical retrieval lists:

- ✅ **Salience formula** (`recency × pain × importance`): `NOX_SALIENCE_MODE=shadow` default; not applied to ranking.
- ✅ **`SECTION_BOOST`**: all eval_locomo chunks have `section=NULL`; multiplier never fires.
- ✅ **`BOOST_TYPES`**: `chunk_type=eval_locomo` not in the set `{decision, lesson, person, project, pending}`.
- ✅ **`SOURCE_TYPE_BOOST`**: all eval chunks have `source_type=NULL`; default `?? 1.0`.
- ✅ **`TIER_BOOST`**: all eval chunks default to `tier=peripheral`; even if applied, uniform across corpus → no ranking differentiation.
- ✅ **`source_date ≤7d` boost**: all eval chunks were ingested same day → uniform boost → no ranking differentiation.
- ✅ **Query expansion (Gemini variants)**: variants land in FTS5 batches that return 0 docs (same root cause as the original-query FTS5 batch); no RRF lift.
- ✅ **Semantic pool size 20 vs 80**: at top-10 scoring depth, the deeper tail of the dense ranking does not change the head.
- ✅ **4-batch RRF vs 2-batch RRF**: when 3 of the 4 batches are empty, RRF collapses to ranking-by-1-batch (the semantic one).

---

## 6. Drivers confirmed NON-NULL on the LoCoMo eval set

- 🚨 **Semantic batch (gemini-embedding-001, 3072d cosine, top-20 from sqlite-vec)** — alone reproduces D_full_prod byte-for-byte (F_semantic_only ablation). This is the dominant driver of the +100.6% / +112%.
- ⚠️ **nDCG formula choice (D1 vs D2)** — adds +5.4pp absolute / +11pp relative when sorted-rel IDCG is used vs full-ideal IDCG. Worth ~half of the headline-vs-canonical delta.

---

## 7. Bugs / unexpected findings discovered during ablations

1. **TS prod's FTS5 sanitize regex is incomplete.**
   `src/search.ts:75` does `query.replace(/['"{}()\[\]:*^~&|!]/g, " ")` but doesn't strip `?` `,` `.`. NL queries containing `?` cause FTS5 parser errors which are caught silently and return `[]`. **The FTS5 batch in production hybrid search returns 0 docs for natural-language English queries containing `?`**. This is masked by the semantic batch but represents a hidden defect.
   - Impact: hybrid search loses BM25 lexical signal for the most common query shape (question-form NL).
   - Fix: extend the regex to strip `?` `,` `.` OR (better) use the existing `fts5_escape`-style OR-join approach from the Python re-impl.
   - Documented in lessons MEMORY: `feedback_fts5_vanilla_and_strict_explains_zero_recall.md` already noted the AND-strict issue; this finding extends it: TS prod ALSO has the punctuation strip gap.

2. **Production telemetry was not being written during eval runs.**
   `search_telemetry` table on the eval DB shows 0 rows even after 700 queries. Schema has extra columns (reranker_*, temporal_*) added since 2026-05-07; the INSERT in `dist/search.js` uses positional binding and emits silently on column-count mismatch. Not blocking for this ablation (we have per_query JSON), but means the runtime telemetry pipeline is broken on eval DB; flagged for follow-up.

3. **Build emits `dist/search.js` even when tsc reports errors in unrelated files.**
   The TS compiler is in non-strict-emit mode — errors in `src/observability/__tests__/*.test.ts` (TS5097 `.ts` import extension) don't block emitting `dist/search.js`. Useful for ablation work, but a real risk for production deploy hygiene. Flagged for follow-up.

---

## 8. Cost and time accounting

| Item | Amount |
|---|---|
| Total wall-clock (all 7 ablations + smoke) | ~13 min |
| Gemini API spend (embeddings + expansion variants) | ~$0.08 USD estimated |
| VPS time | ~13 min on `srv1465941.hstgr.cloud` |
| Network: localhost only (eval API on `:18803`) | — |
| **Budget allocated** | $1.00 USD / 4h wall-clock |
| **Actual** | $0.08 / 13 min |

Significantly under both budgets because:
- Each ablation = 100 queries × 1.5s avg = 2.5 min (not 20 min as estimated)
- Identical retrieval across 5 of 7 ablations meant Gemini embedding cache reuse on the model side (same query inputs)

---

## 9. Conclusão — 3 perguntas respondidas

### Q1: Headline canonical +100.6% é defensável? (Y/N + por quê)

**Y — defensável**, com qualificação.

- Numerically valid: 0.5637 nDCG@10 D2 reproduces in 5 of 5 ablations with byte-identical retrieval. The number is reproducible.
- Methodologically clean if reported as "TS production hybrid pipeline vs FTS5 (Python re-impl, OR-join, raw `<speaker>: <text>`)". Both numbers use the same canonical nDCG formula (D2).
- **But** the +100.6% over the Python re-impl FTS5 baseline is **NOT** attributable to architectural innovation (multi-batch RRF, query expansion, larger pool). The mechanism is "TS prod indexes richer chunk text + uses Gemini 3072d embeddings, FTS5 batch produces zero contribution due to a silent regex bug". A reviewer who reads the staged TS pipeline and sees "expansion + 3+1 RRF" will assume those features drove the lift — they did not.
- Honest framing: **"hybrid retrieval (dense + sparse fusion) beats sparse-only on long-context conversational QA"** holds in spirit, but the empirical contribution of the sparse leg is currently 0 on this dataset, so the strong claim is "Gemini embedding retrieval on enriched chunk text".
- Recommendation: paper §5 should cite **(a)** the canonical formula (D2) prominently, **(b)** the dense-only ablation (F) as the operative comparison, **(c)** acknowledge the FTS5 sanitize bug as a known issue to fix before re-running with a functioning hybrid.

### Q2: Qual é o dominant driver real?

**Gemini semantic embedding retrieval (gemini-embedding-001, 3072d, cosine) over the TS prod-indexed chunks (which include frontmatter metadata + chunk_id anchor in chunk_text).**

Not query expansion. Not 4-batch RRF. Not larger semantic pool. Not boosts. Not chunk_text-rich BM25 (BM25 returns 0 anyway). The +100.6% relative-to-FTS5 is dense embedding alone.

This means the Q1 paper §5 story is actually simpler than the runbook hypothesized: **dense retrieval with strong embeddings beats lexical-only on conversational QA**. The "hybrid" framing is currently aspirational on this eval set because the sparse leg is broken.

### Q3: Salience + section_boost contribuem zero no eval set atual? (confirmar ou desmentir static analysis)

**Confirmado — zero contribuição.** Plus all the other boost types (`BOOST_TYPES`, `SOURCE_TYPE_BOOST`, `TIER_BOOST`, source_date recency) also confirmed zero. Disabling them all (`NOX_DISABLE_BOOSTS=1`, ablation B) yields byte-identical retrieval to D_full_prod. The reason: the LoCoMo eval ingester (`locomo_to_markdown.py`) doesn't set the schema fields that any of these boosts read. Static analysis was correct on this point.

Implication: if Toto wants to demonstrate that salience / section_boost / source_type boost contribute lift, the demo will need to come from the **real prod corpus** (`/root/.openclaw/nox-mem.db`), not the LoCoMo eval set. The LoCoMo eval is structurally invariant to those features.

---

## 10. Riscos e anomalias encontradas

1. **FTS5 sanitize bug** (§7.1) is a real prod issue, not an eval artifact. Customers running natural-language queries against nox-mem are getting dense-only retrieval whenever the question ends with `?`. Severity: medium. Fix is one-line + test.

2. **Production telemetry write fails silently** (§7.2). `search_telemetry` rows are being dropped. Doesn't block this PR but means the new `/api/health.search_telemetry` views are stale.

3. **tsc emit hygiene** (§7.3). Allows shipping `dist/` with type errors. Not new — predates this work.

4. **Static-code analysis fooled itself** in PR #137. The reasoning ("RRF mathematically should boost docs appearing in multiple batches") was sound, but missed the failure mode (3 of 4 batches are empty, RRF collapses). This is a methodological lesson: **always run the ablation**, even if you think you've reasoned out the answer. Static analysis can confirm the absence of unrelated drivers (boost zeros), but cannot confirm the presence of a hypothesized driver without measuring.

5. **Eval set sensitivity to schema fields**: the LoCoMo eval set never exercises 60% of the prod ranking signal (boosts, salience, section). To benchmark those features we need a different eval set (entity-format files, varied source_types, mixed pain values).

---

## 11. Cross-refs

- `paper/publication/baselines/locomo_ablation_eval.py` — harness (writes per_query, two nDCG formulas in one pass)
- `paper/publication/baselines/run_locomo_ablations.sh` — orchestrator (start/stop eval API, run harness per config)
- `paper/publication/results/q1-ablations/{D_full_prod,B_no_boosts,C1_no_expansion,C2_pool_20,C3_no_expansion_pool_20,E_fts5_only_via_pipeline,F_semantic_only}.json` — per-ablation results with per_query lists
- `docs/RESEARCH/2026-05-19-q1-attribution-investigation.md` (PR #137) — static-analysis predecessor; superseded by §3 attribution table here for the empirical numbers
- `paper/publication/results/locomo-production-path-results.json` — original canonical run (matches D_full_prod exactly)
- `paper/publication/results/locomo-hybrid-vs-fts5-summary.md` — Python re-impl reference (0.3338 D2)
- `paper/publication/results/locomo-fts5-baseline-results.jsonl` — E04 reference (0.2810 D2)

---

*Autoria: executor-high (research/2026-05-19/q1-ablations), 2026-05-19.*
*Status: ablations rodadas. Toto decide framing pro paper §5 e se vale rodar follow-up no FTS5 sanitize bug.*
