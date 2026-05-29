# Lab Q2 — Profile-Chunk Identification Mechanism

**Status:** SPEC (não implementado) — Lab Q2 priority, sequenced após Wave C triple bench results
**Date:** 2026-05-29
**Author:** Toto (via agent session 2026-05-29 evening BRT)
**Branch spec:** `spec/profile-chunk-identification-q2`

**Cross-links:**
- `specs/2026-05-28-ma-protection-rerank.md` — MA-protection Q1 #2 origin (Approach A bypass-entity)
- `docs/DECISIONS.md §D68` — Wave B dual finding (orthogonal-stages hypothesis)
- `docs/ROADMAP.md` — Wave C row + Lab Q2 placement
- Memory `[[lab-q1-wave-b-kgmap-3of4-gates-ship-opt-in]]` — KG+MAP partial recovery +1.53pp, remaining gap -5.02pp
- Memory `[[ma-recovery-needs-profile-chunks-not-entity-chunks]]` — Q2 future direction crystallized
- Memory `[[lab-q1-2-ma-protection-corpus-mismatch]]` — standalone MAP corpus-inert (Set E empty)
- Memory `[[memory-awareness-dimension-must-be-audited]]` — MA hidden cost pattern (Phase G learning)

---

## 1. Problem Statement

### 1.1 Wave B residual gap

Wave B closure 2026-05-29 (D68) shipped 2 opt-ins:
- **PR #389 KG+MQ:** same-stage overlap (90.8% co-fire), REJECT default
- **PR #390 KG+MAP:** different-stage additive on F_MH (+4.04pp), **partial MA recovery (+1.53pp vs MAP alone, but still -5.02pp vs Phase H v2 baseline)**

The remaining MA gap (**-5.02pp**) is mechanistically structural, not residual noise. Wave B
proved KG anchor mechanism fires on chat corpora (Set E 0.33 chunks/q × 90.7% queries), but
**MA recovery is still partial** — not because mechanism is broken, but because **KG anchor
identifies the wrong chunk class for MA queries**.

### 1.2 Two chunk classes, one mechanism

Wave B KG+MAP protects chunks identified via `kg_relations` walk — i.e., **entity-relation
evidence chunks**. These are chunks where the model has learned a structured fact like
"entity_A has relation_X with entity_B".

But MA dim queries on EverMemBench (Constancy / Proactivity / Update) typically hit a
**different chunk class — profile chunks** — content that describes the user/persona
properties directly without relational structure. Examples:

| Query type | Target chunk class | KG anchor coverage |
|---|---|---:|
| "what's my user's email?" | profile (user metadata flat text) | Low (no kg_relations on email property) |
| "what's the user's role?" | profile (persona description) | Low (role rarely modeled as kg_relation) |
| "what does the user prefer?" | profile + recent timeline | Low (preferences rarely structured) |
| "what's the latest user state?" | profile recent (currency-sensitive) | Low (no temporal kg_relation) |
| "what's the company stack?" | entity_relation (entity-relation walk) | **High** (KG covers this) |
| "who works with whom?" | entity_relation | **High** (KG covers this) |

KG entity-walk excels at structured relational facts (which Wave B KG path standalone +2.81pp
F_MH proves). It under-covers profile chunks, which are dominantly **flat metadata text**.

### 1.3 Quantification

Wave B KG+MAP measurements:
- KG pool size mean: **19.76 chunks/q** (KG identifies ~20 candidates per query)
- queries_with_kg_pool: **90.7%** (KG covers vast majority of queries)
- queries_with_protected: **16.8%** (KG-anchor chunks hit top-K candidate set)
- protected/q mean: **0.33** chunks
- MA composite gap remaining: **-5.02pp** vs Phase H v2 baseline (73.34% → 68.32%)

The 16.8% protection rate vs 90.7% coverage signal: **most KG-identified chunks are NOT in the
top-K rerank candidate set for MA queries**. The MA queries pull profile chunks into top-K via
embedding similarity, but KG anchor doesn't recognize those profile chunks as protectable.

---

## 2. Three Candidate Approaches

### 2.1 Approach A — Section markers `profile` (corpus-dependent)

**Mechanism:** Add `profile` section marker to nox-mem entity file format alongside existing
`compiled` / `frontmatter` / `timeline`. Update MAP bypass criterion to:

```
bypass_protection = (section IN ('compiled', 'frontmatter', 'profile'))
                   OR (chunk_id IN kg_evidence_chunks_for_query_entities)
```

**Pros:**
- Explicit schema, deterministic firing
- Reuses existing MAP infrastructure (PR #386 + PR #390)
- Compatible with nox-mem prod entity-file format (183 entities)

**Cons:**
- Requires corpus to have profile section markers (EverMemBench chat corpus does NOT)
- Doesn't close MA gap on chat-only corpora (same problem as PR #386 standalone)
- Requires entity file format extension (schema migration)

**Coverage estimate on EverMemBench:** 0% (chat corpus has no profile section markers)
**Coverage estimate on nox-mem prod:** ~40% MA queries (entity profiles populate `compiled`
section per entity-file format; `profile`-specific section would be ~10-15% additional)

**Verdict:** Useful for nox-mem prod but does NOT close EverMemBench MA gap. **Reject as
primary Q2 direction**; consider as nox-mem prod enhancement only.

### 2.2 Approach B — Embedding cluster detection (corpus-agnostic, unsupervised)

**Mechanism:** At index time, cluster all chunk embeddings (Gemini-001 3072d) using DBSCAN or
HDBSCAN. Identify clusters that represent **user-profile content** via heuristics:
- Cluster centroid near reference profile-chunk embedding template
- Cluster member chunks have high lexical overlap with persona/user/profile keywords
- Cluster member chunks are dominantly `chunk_type='user'` (não assistant turns)

Tag clusters as `profile_cluster_id` in chunk metadata. Extend MAP bypass to:

```
bypass_protection = (section IN ('compiled', 'frontmatter'))
                   OR (chunk_id IN kg_evidence_chunks_for_query_entities)
                   OR (chunk.profile_cluster_id IS NOT NULL)
```

**Pros:**
- Corpus-agnostic (works on any embedding-indexed corpus)
- No schema change required
- Unsupervised — no manual labels
- Captures dominant profile-chunk class even when corpus has no section markers

**Cons:**
- HDBSCAN tuning sensitivity (eps, min_samples parameters)
- Clustering compute cost at index time (~minutes for 60k chunks)
- Profile clusters might overlap with other chunk classes (false positives)
- Hard to validate cluster quality without labeled ground truth

**Coverage estimate:** ~60-80% MA queries (depends on cluster purity; if profile chunks form
1-3 dominant clusters, coverage is high)

**Verdict:** Most promising for corpus-agnostic MA recovery. **Recommended as Approach 1.**

### 2.3 Approach C — Query intent classifier (orthogonal stage, supervised-light)

**Mechanism:** Train lightweight query classifier (gemini-flash-lite few-shot OR heuristic
keyword matcher) to detect MA-class queries at query time. Examples:

```
MA queries:
- "what's my [name | email | role | preference | ...]"
- "what does the user [prefer | think | want]"
- "who am I"
- "what's the latest [status | state | situation]"
```

Route MA queries through **dedicated profile retrieval path**:
1. Standard hybrid search (FTS5 + Gemini embed + RRF)
2. NO cross-encoder rerank (rerank harms MA per Phase G learning)
3. OR: rerank with profile-chunk bypass (combine with Approach B clusters)

This is a stage-orthogonal mechanism: query classification → routing → retrieval (different
pipeline stage than MAP rerank-bypass).

**Pros:**
- Truly orthogonal-stage mechanism (validates D68 hypothesis at scale)
- Can use Adaptive Classifier infrastructure (PR #381 already shipped)
- Heuristic version requires no model training (just keyword + pattern matching)
- Composable with Approach B (classifier triggers cluster lookup)

**Cons:**
- Requires query distribution analysis to identify MA-class patterns
- Heuristic version is brittle to query phrasing variation
- LLM version costs token budget (~$0.0001-0.001/query depending on model)
- Adds latency at query time (~100-500ms classifier overhead)

**Coverage estimate:** ~70-90% MA queries (depends on classifier recall)

**Verdict:** Highest ceiling potential. **Recommended as Approach 2 + composability layer
on top of Approach B.**

---

## 3. Decision Matrix

| Criterion | Weight | Approach A (section) | Approach B (cluster) | Approach C (classifier) |
|---|---:|---:|---:|---:|
| EverMemBench MA gap closure | 30% | 0% (chat corpus) | 60-80% | 70-90% |
| nox-mem prod MA gap closure | 20% | ~40% | 60-70% | 60-70% |
| Implementation cost | 15% | Low (~1 week) | Medium (~2-3 weeks) | Medium (~2 weeks) |
| Latency overhead | 10% | None (index-time) | None (index-time) | 100-500ms/query |
| Composability with KG+MAP | 15% | High (additive bypass) | High (additive bypass) | Medium (routing change) |
| Corpus generality | 10% | Low (entity-file required) | High (embedding only) | High (query only) |
| **Total weighted score** | 100% | **22.5/100** | **63.5/100** | **66.5/100** |

**Recommended Q2 direction:** **Approach C (classifier) + Approach B (cluster) composable
pipeline**. Approach A reserved as nox-mem prod-only enhancement.

---

## 4. Recommended Architecture (Composable Q2 Pipeline)

### 4.1 Query-time flow

```
User query
   ↓
[1] Heuristic + LLM query classifier
   → MA-class? (Y/N + class type: C / P / U)
   ↓
[2a] N → Standard hybrid retrieval (current pipeline)
[2b] Y → MA-routed retrieval:
        - FTS5 + Gemini embed + RRF
        - Top-K = 30 (vs 20 standard)
        - Skip cross-encoder rerank OR rerank w/ profile-cluster bypass
[3] If KG path active: append KG anchor chunks (PR #379)
[4] If MAP active: protect KG anchor + profile-cluster chunks (PR #390 + Q2 extension)
[5] Answer generation (gpt-4.1-mini)
```

### 4.2 Index-time flow

```
Chunk ingest
   ↓
[1] Embed (Gemini-001 3072d) — existing
[2] Section + entity metadata — existing
[3] Profile-cluster detection (HDBSCAN over corpus embeddings)
   → Assign profile_cluster_id to chunks in profile clusters
[4] Store profile_cluster_id in chunks metadata
```

### 4.3 Schema extension

```sql
ALTER TABLE chunks ADD COLUMN profile_cluster_id INTEGER NULL;
CREATE INDEX idx_chunks_profile_cluster ON chunks(profile_cluster_id) WHERE profile_cluster_id IS NOT NULL;
```

Backwards-compatible (NULL default; existing chunks unchanged until reindex).

### 4.4 Adapter mode

`NOX_ADAPTER_MODE=phaseProfile` activates:
- Approach C heuristic + LLM classifier
- Approach B profile_cluster_id bypass in MAP
- Optional: skip rerank for MA-classified queries entirely

Composes with phaseKGMAP / phaseTriple: classifier routing happens BEFORE retrieval, then
retrieval + rerank protection layers stack on top.

---

## 5. 5-Batch Eval Plan

### 5.1 Phase configurations

| Phase | Components | Hypothesis |
|---|---|---|
| **Phase ProfileC** | Approach C only (classifier routing, skip rerank for MA) | Baseline isolated effect |
| **Phase ProfileB** | Approach B only (cluster bypass in MAP, no classifier) | Cluster mechanism alone |
| **Phase ProfileBC** | Approach B + C composable | Combined target |
| **Phase ProfileTripleBC** | KG + MQ + MAP + Approach B + Approach C | Wave D stretch (full pipeline composability) |

### 5.2 Gate matrix (4 gates)

1. **MA composite recovery ≥ Phase H v2 -2pp:** target ≥ 71.34% (closes ~60% of -5.02pp Wave B gap)
2. **F_MH non-regression ≥ Wave C triple bench result:** target ≥ +4pp lift preserved
3. **Overall regression ≤ -1pp vs Phase H v2:** target ≥ 50.68%
4. **Latency overhead ≤ +500ms vs current best opt-in:** classifier + cluster lookup ceiling

### 5.3 Set E instrumentation

Per query:
- `classifier_fired` (boolean) + class predicted (C/P/U/non-MA)
- `profile_cluster_chunks_in_topk` (count)
- `kg_anchor_chunks_in_topk` (count)
- `bypass_total` (union of section + KG + profile_cluster bypass triggers)

### 5.4 Sequencing

- Wave C triple bench (in-flight 2026-05-29) **must complete first** to establish triple baseline
- Phase ProfileC + Phase ProfileB run in parallel (different env flags, different stages)
- Phase ProfileBC merges learnings
- Phase ProfileTripleBC final composability test

### 5.5 Cost estimate

- Phase ProfileC: ~$5 (classifier LLM cost + standard bench)
- Phase ProfileB: ~$3 (index-time cluster compute + standard bench)
- Phase ProfileBC: ~$5 (combined)
- Phase ProfileTripleBC: ~$6-7 (full pipeline, more chunks evaluated)
- **Q2 total budget: ~$20-25**

---

## 6. Open Questions

1. **Profile-cluster identification ground truth:** How to validate cluster quality without labeled MA queries? Options:
   - Manual inspection of 5-10 batches × top clusters (~2hr eval work)
   - Use known nox-mem prod entity profiles as anchor templates
   - Adversarial test: synthesize 50 MA queries, measure top-K profile-cluster coverage

2. **Classifier model choice:** gemini-flash-lite vs gpt-4.1-mini vs pure heuristic?
   - Flash-lite: $0.0001/q, ~500ms latency, decent recall
   - GPT-4.1-mini: $0.001/q, ~800ms latency, better recall
   - Heuristic: $0/q, ~10ms latency, weaker recall on edge cases
   - **Recommendation:** start with heuristic baseline, escalate to flash-lite if recall < 70%

3. **DBSCAN vs HDBSCAN:** which clustering algorithm?
   - HDBSCAN: handles varying cluster densities, robust to noise
   - DBSCAN: simpler, requires eps tuning
   - **Recommendation:** HDBSCAN with `min_cluster_size=20, min_samples=5` starting point

4. **Profile-cluster compute cost at index time:** for nox-mem prod (~62k chunks), HDBSCAN
   takes ~3-5 min on VPS 4vCPU. Acceptable for nightly reindex; OK as one-time backfill.

5. **MA dim weighting:** EverMemBench MA composite is mean of MA_C / MA_P / MA_U. Should
   Approach C classifier distinguish between subtypes for differential routing? Hypothesis:
   MA_U (Update) needs temporal-aware retrieval (lesson `[[e13-temporal-aware-ranking]]`);
   MA_C / MA_P are more profile-static. **Q2 deeper investigation.**

---

## 7. NÃO FAZEMOS

- Skip Wave C results before designing Approach BC final eval matrix — Wave C might reveal that triple already closes MA gap further, changing Q2 priority
- Train custom embedding model for profile chunks (premature; HDBSCAN on Gemini-001 embeds is cheaper baseline)
- Add profile-cluster_id as required schema field (must be backwards-compatible NULL-default)
- Ship Approach A (section markers) as primary Q2 — it's a nox-mem prod enhancement, not a corpus-general MA recovery solution
- Use classifier routing to skip ALL post-retrieval refinement for MA queries — KG anchor still adds value for MA_P (proactivity) cases

---

## 8. Success Criteria (Q2 close)

- **Min:** Phase ProfileBC closes ≥50% of Wave B MA gap (-5.02pp → -2.5pp or better) on EverMemBench 5-batch
- **Target:** Phase ProfileBC closes ≥70% of Wave B MA gap (-5.02pp → -1.5pp or better)
- **Stretch:** Phase ProfileTripleBC closes ≥80% Wave B gap WHILE preserving Wave C F_MH triple gain (~+5pp vs Phase H v2)
- **F_MH gap closure target:** Wave C triple result + Q2 Profile ≥ 40-50% MemOS closure

---

## 9. Related Work (cross-reference)

- D01 cross-encoder reranker (Lab Q1 history) — established MA cost mechanism
- E13 temporal-aware ranking — MA_U specifically benefits from temporal signals
- Approach A (entity-file section markers) — applicable to nox-mem prod via spec backport
- PR #379 / #385 / #386 / #389 / #390 — Lab Q1 + Wave B foundation
- arxiv:2602.01313 MemOS Table 4 — backbone comparison baseline; MA dimensions reported
- LongMemEval — secondary cross-bench validation (PR #378)

---

## 10. Ownership & Timeline

- **Owner:** Toto (research) + Claude Code (impl)
- **Target Q2 spec freeze:** 2026-06-07 (after Wave C results + paper §5 revision)
- **Target Phase ProfileC + ProfileB POC bench:** 2026-06-15
- **Target Phase ProfileBC 5-batch bench:** 2026-06-22
- **Target Phase ProfileTripleBC stretch bench:** 2026-06-30

---

*Spec drafted 2026-05-29 evening BRT during Wave B closure + Wave C dispatch. Sequenced as
post-Wave-C deliverable per ROADMAP v4.7 Wave C row dependencies.*
