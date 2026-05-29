# Lab Q1 #2 — MA-Protection Mechanism for Cross-Encoder Rerank

**Status:** SPEC (não implementado) — Lab Q1 priority #2, sequenced após Lab Q1 #1 (query classifier)
**Date:** 2026-05-28
**Author:** Toto (via agent session 2026-05-28 evening BRT)
**Branch spec:** `spec/ma-protection-rerank-lab-q1`

**Cross-links:**
- `specs/2026-05-21-neural-reranker-design.md` — D01-v3 reranker design (Lab Q1 #1 dependency)
- `specs/2026-05-07-D01-cross-encoder-reranker.md` — D01 v1/v2 CUT history (root cause context)
- `docs/DECISIONS.md §2` — Q5 Qwen3-Reranker rationale; rerank as opt-in
- `docs/ROADMAP.md` — Lab pillar placement
- Memory `[[memory-awareness-dimension-must-be-audited]]` — MA hidden cost pattern
- Memory `[[cross-encoder-trade-off-shape]]` — 5-batch trade-off magnitudes (updated with MA dim)
- Memory `[[phase-g-minilm-multi-hop-breakthrough]]` — Phase G empirical case
- Memory `[[entity-file-format]]` — section_boost origin + compiled/frontmatter/timeline semantics

---

## 1. Problem Statement

### 1.1 Root cause

Phase G (EverMemBench 5-batch, PR #369) established the cross-encoder rerank trade-off shape
conclusively:

| Dimension | Phase D (rerank OFF) | Phase G (rerank ON) | Delta |
|---|---:|---:|---:|
| F_MH (multi-hop) | 5.22% | 6.83% | +1.61pp |
| F_HL (high-level) | — | — | +2.58pp |
| F_TP (temporal) | — | — | +2.00pp |
| F_SH (single-hop) | — | — | +0.40pp |
| MC (multi-choice) | — | — | -2.63pp |
| **MA_C (Constancy)** | 81.40% | 77.40% | **-4.00pp** |
| **MA_P (Proactivity)** | 83.00% | 80.20% | **-2.80pp** |
| **MA_U (Update)** | 85.02% | 81.18% | **-3.84pp** |
| Overall | 62.22% | 61.26% | -0.96pp |

The Memory Awareness (MA) regression is **structural**, not noise: it was invisible in
single-batch eval (batch 004) due to selection bias (batch 004 had lowest MA among 5 batches),
but revealed consistently across 5-batch methodology.

### 1.2 Mechanism

Cross-encoder rerank (MiniLM-L-6-v2 Phase G; bge-reranker-v2-m3 target for D01-v3) rescores
candidates by **query-chunk semantic relevance**. This is correct for factual recall but
**structurally wrong for Memory Awareness dimensions**:

- **MA_C (Constancy):** queries like "what's my name / role / preference" → the correct chunk
  is a `compiled`-section entity profile entry. The query does NOT lexically overlap with the
  profile chunk ("name: Toto, role: board advisor, FII Treviso lead"). Cross-encoder downgrades it.
- **MA_P (Proactivity):** queries require surfacing relevant *past context* without explicit query
  match. Entity/compiled chunks are the most relevant but least lexically similar. Rerank pushes
  them to positions 8-20.
- **MA_U (Update):** current-state preference requires the *latest* compiled chunk, not the
  historically most-similar one. Cross-encoder has no temporal awareness; it ranks all chunks by
  cosine proximity to query, not by currency.

### 1.3 Quantification

Phase G 5-batch data (RESULTS-PHASEG-5BATCH.md):

- ~13% of top-K relevant chunks in MA evaluation queries are entity-formatted
  (`section IN ('compiled', 'frontmatter')`)
- After cross-encoder rerank, ~85% of those entity chunks are displaced beyond position 10 in
  the Phase G results (estimated from per-batch MA_C/P/U per-position analysis)
- `section_boost` (compiled=2.0, frontmatter=1.5) is applied at FTS5/dense scoring stage;
  after RRF fusion, the boost is baked into the pre-rerank rank. **Cross-encoder then ignores
  it entirely** — the rerank score is query-chunk similarity only.

### 1.4 Architectural gap

The current nox-mem pipeline has no mechanism to propagate `section_boost` through rerank.
The `chunks` table has `section` TEXT + `section_boost` REAL columns (Schema v10, 2026-04-23),
but they are consumed only by FTS5 and dense scoring, not by the reranker layer.

```
Current:
  FTS5 BM25 ──┐                          ┌─ section_boost applied here
  Gemini vec ─┤─ RRF fusion (k=60) ──────┤─ section_boost baked into RRF rank
              └─────────────────────────→ top-N candidates (section_boost preserved as rank position)
                                           │
                             cross-encoder rerank ← section_boost IGNORED here
                                           │
                                        top-K results (section_boost protection BROKEN)
```

---

## 2. Protection Mechanism Options

### Option A — Rerank-bypass for entity chunks

**Mechanism:** Partition the pre-rerank candidate pool into two sets:
- **Set E** (entity chunks): `section_boost > 1.0` OR `section IN ('compiled', 'frontmatter')`
- **Set R** (regular chunks): remainder

Retain Set E at their bi-encoder ranks unchanged. Apply cross-encoder rerank only to Set R.
Merge: interleave Set E (at original positions) + top-K-from-Set-R reranked.

**Pseudocode:**
```python
entity_set = [c for c in candidates if c.section_boost and c.section_boost > 1.0]
regular_set = [c for c in candidates if c not in entity_set]

# Rerank only regular chunks
reranked_regular = cross_encoder.rerank(query, regular_set)

# Merge: preserve entity positions, fill remaining slots with top reranked regular
merged = merge_preserving_entity_positions(entity_set, reranked_regular, top_k)
```

**Pros:**
- Simple — single filter condition, no parameter tuning
- Entity chunks keep bi-encoder rank (which already respects section_boost from RRF)
- Zero additional inference calls

**Cons:**
- If a non-entity chunk is truly more relevant than an entity chunk, the entity chunk still
  blocks it (over-protection risk in non-MA queries)
- Merge strategy needs careful implementation: if entity_set is large (>top_k), merge behavior
  undefined — needs cap

**Open question:** Should entity chunk identity be based on `section_boost > 1.0` or
`section IN ('compiled', 'frontmatter')`? Both are equivalent today (schema v10 enforces them
together), but `section` column is more semantically explicit and less prone to float comparison.
Recommendation: use `section IN ('compiled', 'frontmatter')`.

---

### Option B — Section-boost-aware reranking

**Mechanism:** Modify the rerank score to include `section_boost` as a multiplicative post-factor:

```python
effective_score = cross_encoder_score * section_boost_factor(chunk.section)
```

Where `section_boost_factor`:
- `compiled` → 1.4×  (NOT 2.0× — rerank scores are calibrated differently than BM25)
- `frontmatter` → 1.2×
- `timeline` → 0.9×
- `NULL/legacy` → 1.0×

Note: the original section_boost values (2.0/1.5/0.8) were tuned for BM25 score magnitude,
not for cross-encoder logit scale (-10 to +10 range). Using 2.0× on cross-encoder scores
would catastrophically promote entity chunks regardless of relevance.

**New column proposal:** `rerank_boost REAL DEFAULT 1.0` in `chunks` schema, populated at
ingest time alongside `section_boost`. Allows independent tuning for rerank stage.

**Pros:**
- Graduated approach — entity chunks get preference but can still be displaced if truly
  irrelevant to query
- Preserves ranking continuity through pipeline
- Composable with any cross-encoder model (model-agnostic multiplier)

**Cons:**
- Requires parameter tuning: `rerank_boost` magnitudes need ablation to find optimal values
- Adds schema column (minor migration)
- Current `section_boost` magnitudes (2.0/1.5) were tuned for FTS5/dense, NOT rerank —
  re-tuning needed separately. Risk: tuning for MA may hurt non-MA categories.

---

### Option C — Hard-anchor entity chunks

**Mechanism:** After cross-encoder rerank, force the top-N entity chunks (by original
bi-encoder rank) to always appear in final top-K:

```python
reranked_all = cross_encoder.rerank(query, all_candidates)

# Anchor: ensure top-N entity chunks survive in final results
entity_anchors = top_n_entity_chunks_by_biencoder_rank(candidates, N=3)
final = anchor_then_fill(entity_anchors, reranked_all, top_k=10)
```

**Pros:**
- Simplest possible guarantee for MA chunks
- No rerank score modification

**Cons:**
- Brittle: `N=3` is a magic number. Too low → MA regression persists for queries needing 5+
  entity chunks. Too high → non-entity chunks crowded out even when clearly more relevant.
- Query-agnostic anchor is philosophically wrong: a temporal query needs timeline chunks
  anchored, not compiled chunks.
- Top-N threshold interacts with query type — adversarial and multi-hop queries would suffer
  if entity chunks are always anchored.

---

### Option D — Adaptive bypass via query classifier (Lab Q1 #1 integration)

**Mechanism:** Gate the MA protection on query classification:

```
query
  │
  ├─ classifier (Lab Q1 #1)
  │     ├─ "MA query" (constancy/proactivity/update) → Option A (bypass rerank entirely)
  │     ├─ "multi-hop" query → standard rerank (Phase G behavior, no protection)
  │     └─ "single-hop / factual" → standard rerank
  │
  └─ results
```

**Classifier signals for "MA query":**
- Query mentions user pronoun or possessive ("my", "meu", "minha", "I", "eu")
- Query asks for preferences, habits, role, relationships
- Query has no explicit temporal anchor but asks about "current state"

**Pros:**
- Best-of-both: hard-recall categories keep full rerank benefit; MA queries get protection
- Estimated gain: Option D ≥ Option A in hard-recall dims, ≥ Phase D in MA dims
- Architecturally aligned with Lab Q1 #1 (classifier) milestone

**Cons:**
- Depends on Lab Q1 #1 being implemented first — Lab Q1 #2 cannot ship Phase Q1.3 without it
- Classifier accuracy drives MA recovery: if classifier misclassifies 20% of MA queries as
  "factual", those still regress
- More moving parts, harder to ablate in isolation

---

### Recommendation

**Default shipping path:** Option A first (Phase Q1.1), then evaluate.

Rationale:
1. Option A requires no schema changes, no parameter tuning, no external dependencies.
2. The protection criterion (`section IN ('compiled', 'frontmatter')`) is already a first-class
   schema concept — not a hack.
3. Option A is falsifiable in a single 5-batch run (~$3).
4. If Option A fully recovers MA AND doesn't regress hard-recall dims → done.
5. If Option A creates over-protection (hard-recall dims regress because entity chunks block
   better regular chunks) → try Option B with conservative `rerank_boost` values.
6. Option D is the aspirational target but requires Lab Q1 #1 first.

---

## 3. Integration Points

### 3.1 `eval/evermembench/adapter_nox_mem.py`

The rerank section (lines ~694-730) performs cross-encoder rerank after API call. This is
where **Option A** is most naturally implemented for eval:

```python
# After fetching candidates from API (already include section metadata):
if self.reranker_enabled and candidates:
    if self.ma_protection_mode == "bypass-entity":
        entity_chunks = [c for c in candidates if c.get("section") in ("compiled", "frontmatter")]
        regular_chunks = [c for c in candidates if c not in entity_chunks]
        reranked_regular = _apply_cross_encoder(self, query, regular_chunks)
        candidates = _merge_entity_first(entity_chunks, reranked_regular, top_k)
    elif self.ma_protection_mode == "score-boost":
        candidates = _apply_cross_encoder_with_section_boost(self, query, candidates)
    else:
        candidates = _apply_cross_encoder(self, query, candidates)  # Phase G default
```

**New env var:** `NOX_MA_PROTECTION_MODE` — values: `"none"` (default, Phase G behavior),
`"bypass-entity"` (Option A), `"score-boost"` (Option B), `"hard-anchor"` (Option C).

The adapter needs the API to return `section` field per chunk. Verify `/api/search` response
already includes `section` in chunk metadata — if not, add it as non-breaking field addition.

### 3.2 `src/lib/rerank.ts` (create if not exists)

Currently there is no canonical `rerank.ts` module in `src/lib/` — rerank lives only in the
Python eval adapter. For the nox-mem TypeScript pipeline, create `src/lib/rerank.ts`:

```typescript
export type MAProtectionMode = "none" | "bypass-entity" | "score-boost" | "hard-anchor";

export interface RerankOptions {
  topK: number;
  maProtectionMode: MAProtectionMode;
  sectionBoostFactors?: Record<string, number>;  // for Option B
  anchorTopN?: number;  // for Option C
}

export async function rerankCandidates(
  query: string,
  candidates: Chunk[],  // includes section + section_boost from DB
  opts: RerankOptions
): Promise<Chunk[]>
```

This module is called by:
- `/api/search?rerank=on` handler in `src/api-server.ts`
- `nox-mem search --rerank` CLI handler

### 3.3 `src/api-server.ts`

`/api/search` handler: add opt-in rerank flag with MA protection passthrough:

```
GET /api/search?q=<query>&rerank=on&ma_protection=bypass-entity&top_k=20
```

Response: include `section` field in each result chunk (needed for Option A adapter eval).

### 3.4 Schema (no changes for Option A)

Option A: zero schema changes. `section` column (Schema v10) already populated.

Option B only: add `rerank_boost REAL DEFAULT 1.0` to `chunks` table. Populate at ingest in
`src/ingest-entity.ts`:

```
compiled     → rerank_boost = 1.4
frontmatter  → rerank_boost = 1.2
timeline     → rerank_boost = 0.9
NULL/legacy  → rerank_boost = 1.0
```

Migration: `ALTER TABLE chunks ADD COLUMN rerank_boost REAL DEFAULT 1.0` +
backfill UPDATE from `section` column (safe, no reindex needed).

---

## 4. Benchmark Plan

### 4.1 Modes to evaluate

| Mode ID | Description | Expected delta vs Phase D |
|---|---|---|
| `phase-d` | Rerank OFF (baseline, 62.22%) | — |
| `phase-g` | Rerank ON, no protection (61.26%) | -0.96pp overall, -3 to -4pp MA |
| `option-a` | Rerank ON + bypass-entity | MA recovery target: ≥ Phase D; hard-recall: ≥ Phase G |
| `option-b` | Rerank ON + score-boost (rerank_boost col) | MA partial recovery; needs param sweep |
| `option-c` | Rerank ON + hard-anchor (N=3) | MA recovery; risk on multi-hop/adversarial |

### 4.2 Execution

- **Batches:** 5-batch (same 5 batch IDs as Phase G: 004/005/010/011/016) for apples-to-apples
- **Budget:** ~$3.00 per mode (5 batches × ~$0.60/batch)
- **Priority order:** Option A first ($3) → if MA fully recovered and overall ≥ Phase D → done.
  Else Option B ($3) → Option C ($3 validation only if A+B both fail).
- **Total budget:** $3-9 depending on how many modes need evaluation.

### 4.3 Gate criteria (per mode)

A mode PASSES and becomes the shipping candidate if ALL three hold:

1. **MA non-regression gate:** MA_C ≥ 81.40% AND MA_P ≥ 83.00% AND MA_U ≥ 85.02%
   (recover to Phase D baseline — no MA loss vs rerank-off).
2. **Hard-recall preservation gate:** F_MH + F_HL + F_TP average Δ ≥ +0pp vs Phase D
   (do not lose the rerank gain in hard-recall categories).
3. **Overall gate:** Overall ≥ 62.00% (Phase D ± 0.22pp tolerance for batch variance).

If no mode passes all three gates, the verdict is: **rerank cannot be made MA-safe with
current chunk identity signals** → escalate to Option D (requires Lab Q1 #1 classifier).

### 4.4 Per-category breakdown required

The eval report must include:
- MA_C / MA_P / MA_U per-batch variance (σ) — to detect if MA recovery is structural or
  batch-specific
- F_MH / F_HL / F_TP / F_SH per-batch (same as Phase G reporting)
- MC and OE (head-precision categories)
- 95% CI on overall score

### 4.5 Isolation requirements

- Same DB snapshot as Phase G (`/tmp/evermembench-phaseG-<ts>.db` or equivalent)
- `NOX_MA_PROTECTION_MODE` env var controls mode (no code forks)
- Each mode runs in separate adapter instance (no state leak between modes)

---

## 5. Deployment Phasing

### Phase Q1.1 — Option A behind flag (target: Lab Q1 sprint 1)

**Scope:**
- Add `NOX_MA_PROTECTION_MODE=bypass-entity` env support in Python adapter
- Add `ma_protection` param to `/api/search` endpoint
- Ensure `section` field returned in API response per chunk
- Run 5-batch eval with Option A

**Ship condition:** benchmark gate passes (§4.3).

**Flag default:** `NOX_MA_PROTECTION_MODE=none` (backward-compatible, Phase G behavior preserved).

**PR deliverables:**
1. `eval/evermembench/adapter_nox_mem.py` — MA protection modes
2. `src/api-server.ts` — `section` in response + `ma_protection` param
3. `RESULTS-PHASEG-OPTION-A.md` — 5-batch results

### Phase Q1.2 — Option B if Option A fails MA gate (target: Lab Q1 sprint 2, conditional)

**Scope:**
- Schema migration: `ALTER TABLE chunks ADD COLUMN rerank_boost REAL DEFAULT 1.0`
- Backfill rerank_boost from section
- `src/lib/rerank.ts` score-boost implementation
- Ablation to tune `rerank_boost` magnitudes (compiled: 1.2-1.6× sweep)

**Gating condition:** Option A 5-batch shows MA gate fail OR overall gate fail.

### Phase Q1.3 — Option D integration (target: after Lab Q1 #1 classifier ships)

**Scope:**
- Integrate query classifier output with MA protection decision
- Route MA-type queries (possessive/preference/role/state) → bypass-entity
- Route multi-hop/factual queries → standard rerank
- Validate: classifier accuracy on MA vs non-MA split must be ≥ 85% to justify routing

**Dependency:** Lab Q1 #1 (query classifier) must be deployed and validated first.
This phase provides the adaptive layer that closes remaining MemOS Table 4 gap.

---

## 6. Risks and Open Questions

### 6.1 Entity chunk identity definition

**Q:** Should Option A use `section_boost > 1.0` or `section IN ('compiled', 'frontmatter')`?

**A (recommended):** Use `section IN ('compiled', 'frontmatter')`. Reasons:
- `section` is an explicit semantic marker; `section_boost` is a numeric signal that could
  drift if magnitudes are ever re-tuned independently
- Avoids float comparison (section_boost=1.5 vs 1.500001 after float round-trip)
- More readable in logs and debug output

### 6.2 Merge strategy when entity_set.length > top_k

If there are more entity chunks than `top_k` (unusual but possible for entity-heavy queries),
Option A needs a defined behavior:

**Proposed:** Apply bi-encoder rank within entity_set to select top-top_k entity chunks.
This defers to the original hybrid RRF ordering, which already respects section_boost.

### 6.3 MA_U (Update) needs more than position protection

MA_U (Update awareness) requires the model to know that preference X changed to Y.
Even if compiled chunks survive rerank (Option A), if the compiled chunk doesn't reflect the
update (because the entity file was not re-ingested after the update), MA_U stays broken.

This is a **data freshness problem**, not a rerank problem. Option A can recover what was
measurably lost in Phase G; it cannot fully solve MA_U if entity files are stale.

**Implication:** MA_U recovery in benchmark may be partial even with Option A. Track MA_U
separately from MA_C/P in evaluation report. If MA_U doesn't recover, file separate spec
for "entity file update trigger on preference/state change".

### 6.4 Option B section_boost magnitude tuning

The existing `section_boost` values (compiled=2.0, frontmatter=1.5) were calibrated against
BM25 scores (typical range: 0-30) and dense scores (cosine: -1 to +1). Cross-encoder logits
range -10 to +10. Applying 2.0× to cross-encoder scores would give compiled chunks an
effective score of +20 (beyond max) — catastrophic over-promotion.

For Option B, calibrate separately:
- Start with `rerank_boost` values at 1.1-1.5× range
- Use MA_C/P gate + hard-recall gate as joint optimization target
- Do not derive `rerank_boost` from `section_boost` arithmetically

### 6.5 Latency impact

Option A adds one filter + merge pass over `top_k` candidates (O(N), N≤50). Negligible.
Option B adds one multiply per candidate after rerank (O(N)). Negligible.
Option C adds one anchor merge (O(N)). Negligible.
No latency risk for any option.

---

## 7. Future Work

### 7.1 Composability with adaptive classifier (Lab Q1 #1)

Option D (§2) is the long-term target. The expected behavior after Lab Q1 #1 + Q1 #2 full
integration:

```
query → classifier
  ├─ MA query (user pronoun/preference/role/state) → bypass rerank entirely → MA protected
  ├─ multi-hop query (high cross-query dependency) → full rerank → F_MH/F_HL gain preserved
  └─ factual single-hop → rerank with bypass-entity → Option A behavior
```

Estimated combined gain vs Phase D: +1-2pp overall (Lab Q1 #1 hypothesis), MA ≥ Phase D.

### 7.2 MA_U timeline-aware rerank (separate spec, Q2)

MA_U (Update) awareness requires not just protecting entity chunks from displacement, but
**preferring the most recently updated compiled chunk** when multiple entity versions exist.
This is a separate problem requiring `updated_at` awareness in rerank merge logic.

Scope: separate spec `2026-Q2-timeline-aware-rerank.md`. Not part of Lab Q1.

### 7.3 Profile chunk "must-survive-rerank" marker at index time

Option A's entity chunk definition is query-time derived (from `section` column). A complementary
index-time approach: when ingesting compiled entity chunks, set a `must_survive_rerank` boolean
flag. This makes the protection intent explicit in the data model and survives any future
pipeline refactors.

Depends on: Option A validation proving the concept is worth hardening.

---

## 8. Summary: Recommended Path

```
Phase Q1.1 (now):
  → Implement Option A (bypass-entity) in adapter + API
  → Run 5-batch EverMemBench with Option A
  → If MA gate passes + overall ≥ Phase D: SHIP Option A as default when rerank=on
  → If gate fails: proceed to Phase Q1.2 (Option B tuning)

Phase Q1.2 (conditional):
  → Add rerank_boost column, tune 1.2-1.5× for compiled/frontmatter
  → Re-run 5-batch with Option B
  → Gate: same criteria (§4.3)

Phase Q1.3 (after Lab Q1 #1 classifier):
  → Integrate adaptive routing (Option D)
  → Final target: MA ≥ Phase D + hard-recall ≥ Phase G + overall ≥ Phase D
```

**Non-goals for this spec:**
- Implementation code (spec only — code in Phase Q1.1 PR)
- New benchmark runs (tracked in Phase Q1.1 execution)
- Changes to `section_boost` values or reindex pipeline
