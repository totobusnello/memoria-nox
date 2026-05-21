# G12 — Frontmatter Retrieval Audit

**Date**: 2026-05-21 BRT
**Branch**: `research/g12-frontmatter-retrieval-audit`
**Context**: G10e §4 flagged that `<entity>::frontmatter` gold chunks NEVER appear in top-20 for at least 2 queries (ad-009, ad-015). This audit extends to all queries with frontmatter gold, audits the corpus, and classifies root cause.
**Parent audit**: `audits/2026-05-21-G10e-kw-adversarial-qualitative-audit.md` §4
**Method**: read-only re-analysis of G10b artifacts (`mutex_active.json` / `mutex_disabled.json`) + SQLite inspection of g9.db (`/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db`) + source pull of `search.ts` / `search-dedup.ts`. No fresh eval, no VPS write.

---

## 1. TL;DR

**Five queries in g9 eval set have `<entity>::frontmatter` in their gold set. All FIVE have the frontmatter gold OOT (out of top-20) in BOTH mutex runs.** This is invariant to the G10 mutex; the mechanism is **corpus quality** (impoverished YAML stub text) plus **dedup Layer-4 cap=2 per file** plus **typo-driven FTS5 AND-strict zero matches**, with section_boost=1.5 unable to compensate.

| signal | value |
|---|---:|
| Queries with frontmatter in gold | **5** (ad-001, ad-009, ad-011, ad-012, ad-015) |
| Unique queries (de-duped by query text) | **4** (ad-001/ad-011 are the same query "nox mem hybird search") |
| Queries where gold frontmatter is in top-20 (active) | **0 / 5** |
| Queries where gold frontmatter is in top-20 (disabled) | **0 / 5** |
| Mutex Δ (mutex_active vs mutex_disabled) | **0** queries change frontmatter rank |
| FTS5 zero-result queries (AND-strict) | **3 / 4** unique (typo / `§5` / NL) |
| Gold frontmatter chunks where actual text < 130 chars | **4 / 4** unique entities |

**Recommendation: (C+A combined)** — bump frontmatter `section_boost` from 1.5 → 2.0 to match `compiled` (cheap), but the dominant fix is **(D) corpus schema**: enrich frontmatter chunks with the entity's `description:` YAML field so they carry searchable content. See §6 for effort estimates.

---

## 2. All Frontmatter-Gold Queries (n=5, 4 unique)

Extracted via `jq` against `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/queries.jsonl`:

| qid | category | style | query | gold (frontmatter only) |
|---|---|---|---|---|
| ad-001 | adversarial | keyword | `nox mem hybird search` | `nox-mem::frontmatter` |
| ad-009 | adversarial | keyword | `Bruno Lima role gallapagos AI` | `bruno::frontmatter` |
| ad-011 | adversarial | keyword | `nox mem hybird search` | `nox-mem::frontmatter` (duplicate of ad-001) |
| ad-012 | adversarial | natural-language | `What did Ana Castro lead recently?` | `ana::frontmatter` |
| ad-015 | adversarial | keyword | `paper §5 ablation rationale` | `paper-eval::frontmatter` |

All 5 queries live in the **adversarial** category; 4 are `keyword` style, 1 is `natural-language`. There are no frontmatter-gold queries outside `adversarial`. This is interesting on its own: the eval designers used frontmatter gold specifically in the bucket meant to stress robustness, but it became a structural recall trap.

Data: `audits/data-g12/frontmatter-gold-queries.tsv`.

---

## 3. Per-Query Rank-of-Gold (both mutex runs)

Source: `audits/data-g10b/{mutex_active,mutex_disabled}.json`, joined against gold chunk IDs.

| qid | gold frontmatter chunk | rank_active | rank_disabled | top-5 sections (active) |
|---|---|---|---|---|
| ad-001 | `nox-mem::frontmatter` | **OOT** | **OOT** | numeric, compiled, numeric, numeric, numeric |
| ad-009 | `bruno::frontmatter` | **OOT** | **OOT** | compiled, compiled, numeric ×3 |
| ad-011 | `nox-mem::frontmatter` | **OOT** | **OOT** | numeric, compiled, numeric, numeric, numeric |
| ad-012 | `ana::frontmatter` | **OOT** | **OOT** | compiled, compiled¹, compiled¹, frontmatter¹, frontmatter¹ |
| ad-015 | `paper-eval::frontmatter` | **OOT** | **OOT** | compiled, compiled, numeric ×3 |

¹ For ad-012 the 4 chunks at rank 2-5 all have `source_file = memory/entities/people/ana.md` (same as gold) — see §5b mechanism.

**Reading**: mutex active vs disabled is a **null factor** for frontmatter recall — the gold never makes top-20 regardless. The bottleneck is upstream of any section/source_type boost arithmetic.

Data: `audits/data-g12/ranks-output.txt`.

---

## 4. Section Distribution in g9.db

```sql
SELECT section, COUNT(*) FROM chunks GROUP BY section ORDER BY 2 DESC;
```

| section | chunk count | % of corpus |
|---|---:|---:|
| NULL (legacy / non-entity) | 68,246 | 98.74% |
| `timeline` | 584 | 0.84% |
| `frontmatter` | 333 | 0.48% |
| `compiled` | 332 | 0.48% |

**Embedding coverage**: 100% across all sections (verified via JOIN with `vec_chunk_map`).

**Critical schema observation**: `frontmatter` (333) ≠ `compiled` (332) by 1 — i.e., one entity has an extra frontmatter chunk. Investigation of `memory/entities/people/ana.md` shows 5 chunks total (1 compiled + 3 frontmatter + 1 compiled). The 3 frontmatter chunks are NOT all the entity's own frontmatter — they include `event::*` chunks that the entity-ingester routes back to the *people/ana.md* `source_file`. This means **multiple chunks share the same source_file**, which interacts with dedup Layer 4 (§5b).

```sql
SELECT source_file, COUNT(*) AS n, GROUP_CONCAT(section, "|") FROM chunks
WHERE source_file LIKE "memory/entities/%/{ana,bruno,nox-mem,paper-eval}.md"
GROUP BY source_file;
```

| source_file | n | sections |
|---|---:|---|
| `memory/entities/people/ana.md` | 5 | compiled \| frontmatter ×3 \| compiled |
| `memory/entities/people/bruno.md` | 5 | compiled \| frontmatter ×4 |
| `memory/entities/projects/nox-mem.md` | 8 | compiled ×3 \| frontmatter ×2 \| timeline ×3 |
| `memory/entities/projects/paper-eval.md` | 9 | compiled \| frontmatter ×2 \| timeline ×6 |

---

## 5. Mechanism analysis

### 5a. Frontmatter chunk text is **impoverished**

Full text of the 4 unique gold frontmatter chunks (verified via SQL):

```
chunk_id: "nox-mem::frontmatter"      | 106 chars
---
name: nox-mem
type: project
status: stale
last_review: 2026-05-15
---

chunk_id: "bruno::frontmatter"        | 107 chars
---
name: Bruno Lima
type: person
status: active
last_review: 2026-04-24
---

chunk_id: "ana::frontmatter"          | 105 chars
---
name: Ana Castro
type: person
status: active
last_review: 2026-05-03
---

chunk_id: "paper-eval::frontmatter"   | 112 chars
---
name: paper-eval
type: project
status: stale
last_review: 2026-04-23
---
```

These chunks have **no descriptive content** — only YAML metadata stubs (name / type / status / last_review). They cannot match query phrases like "hybrid search", "role galapagos AI", "lead recently", or "§5 ablation rationale" on FTS5 lexical grounds; the only matchable token is the entity name itself (`nox-mem`, `Bruno Lima`, `Ana Castro`, `paper-eval`). Semantic embeddings of ~100-char metadata stubs encode "this is a project named X with status Y" — semantically distant from the queries.

**Contrast** — the non-gold frontmatter chunk that DID enter top-20 in ad-001 (chunk 216184, `memory/entities/systems/nox-mem.md`):

```
chunk_id: <implicit>                   | 143 chars
---
name: nox-mem
description: Sistema de memória tiered do OpenClaw — chunks + embeddings + KG + FTS5 hybrid
type: system
retention: never
---
```

This chunk has `description: ... FTS5 hybrid` — strong semantic signal for "hybrid search" query, plus FTS5 token matches on "hybrid". It surfaces at rank 12 (active) / 8 (disabled). The **schema difference between rich and stub frontmatter is the dominant variable**, not boost arithmetic.

### 5b. Dedup Layer 4: max 2 chunks per source_file (ad-012 mechanism)

Source: `src/search-dedup.ts:24` — `MAX_PER_FILE_FINAL = 2`.

Hybrid pipeline returns up to 60 results before dedup (preDedup = `Math.max(limit*3, 15)` with limit=20 → 60). Then `dedupe(preDedup, 20)` caps **at most 2 chunks per `source_file`** in the final list.

For `ad-012 (What did Ana Castro lead recently?)`:
- Rank 1 final: `ana::compiled` from `memory/entities/people/ana.md` → file count = 1
- Rank 2 final: `session::2026-05-17::7efd20b6a0` ALSO from `memory/entities/people/ana.md` → file count = 2 (cap hit)
- Anywhere `ana::frontmatter` (id 225189, same `source_file`) sits in preDedup, **Layer 4 drops it on the floor**.

This is a real architectural cause for ad-012. For ad-001/011/009/015 it does NOT apply (only 1 chunk from the gold's source_file makes it into final), so the dominant cause there is §5a (impoverished text).

### 5c. FTS5 AND-strict + typos = zero matches

The query sanitize regex (`src/search.ts:333`) keeps `\p{L}\p{N}\s` and converts everything else to space, so `paper §5` → `paper 5`. FTS5 then runs AND-strict over the surviving tokens:

| query | sanitized tokens | FTS5 hits (direct SQL) |
|---|---|---:|
| `nox mem hybird search` | `nox mem hybird search` | **0** (typo "hybird" absent from corpus) |
| `Bruno Lima role gallapagos AI` | `Bruno Lima role gallapagos AI` | **0** (typo "gallapagos") |
| `paper §5 ablation rationale` | `paper 5 ablation rationale` | **0** (no chunk has all 4 tokens) |
| `What did Ana Castro lead recently?` | `What did Ana Castro lead recently` | **0** (filler verbs/adverbs not in any chunk) |
| `Bruno Lima` (entity only) | `Bruno Lima` | 5 (incl. `bruno::frontmatter` at rank 2) |
| `Ana Castro` (entity only) | `Ana Castro` | 5 (incl. `ana::frontmatter` at rank 2) |

So in 4/4 unique evaluated queries, **FTS5 path contributes nothing**, and the entire retrieval falls to semantic search. The semantic path then has to rank `<entity>::frontmatter` ahead of competing content — but per §5a, the gold chunks have ~100 chars of metadata that does not encode the query's intent.

### 5d. Section_boost can't compensate

Even if a gold frontmatter chunk's raw semantic score were 80% of its compiled twin, `section_boost=1.5` (vs `compiled=2.0`) compounds the deficit:

- `score_compiled = base_compiled × (1 + 1.0)` = `2× base_compiled`  (section_boost=2.0 → delta=1.0)
- `score_frontmatter = base_frontmatter × (1 + 0.5)` = `1.5× base_frontmatter` (section_boost=1.5 → delta=0.5)

If `base_frontmatter / base_compiled ≈ 0.5` (impoverished text matching less of the query), the boosted ratio is `(0.5 × 1.5) / 2.0 = 0.375` — frontmatter is at 37.5% of compiled's score. Section_boost is a multiplicative tweak; it can't rescue a chunk whose underlying lexical/semantic signal is fractional.

Even bumping `frontmatter: 1.5 → 2.0` (matching `compiled`) only gets the ratio to `(0.5 × 2.0) / 2.0 = 0.5`, still well behind.

---

## 6. Hypothesis classification per query

Per the prompt's hypothesis schema (A=sanitize, B=embedding gap, C=boost insufficient, D=other):

| qid | classification | mechanism |
|---|---|---|
| ad-001 / ad-011 | **D (corpus content) + C (boost insufficient)** | gold `nox-mem::frontmatter` has no "hybrid search" content; competing `systems/nox-mem.md::frontmatter` (chunk 216184) has `description: ... FTS5 hybrid` and DOES enter top-20 (rank 8-12). FTS5 fails on typo "hybird" → semantic-only path. |
| ad-009 | **D (corpus content)** | gold `bruno::frontmatter` has `name: Bruno Lima / type: person`; query about Galapagos role overwhelms semantically with 10+ Galapagos files. Boost adjustment cannot promote stub metadata over rich documents. |
| ad-012 | **D (corpus content) + LAYER-4 dedup** | gold `ana::frontmatter` blocked by `MAX_PER_FILE_FINAL=2`: same source_file already has `ana::compiled` + `session::2026-05-17::7efd20b6a0` at ranks 1-2 of the final list. |
| ad-015 | **D (corpus content)** | gold `paper-eval::frontmatter` has only `name: paper-eval / type: project / status: stale`; query about "§5 ablation rationale" matches the literal paper file `archive/paper/paper-tecnico-nox-mem.md` (chunk 148078 at rank 9) which has actual §5 content. |

**No query maps to A (sanitize)** — the regex is Unicode-correct and well-tested (per `feedback_unicode_aware_sanitize_for_fts5`).
**No query maps to B (embedding gap)** — all 4 gold chunks have vec embeddings (verified via `vec_chunk_map` JOIN).

**Dominant root cause is D (corpus content)** in 5/5 queries, with secondary contributions from dedup (1/5) and boost ceiling (2/5).

---

## 7. Recommendations + effort estimates

Ordered by ROI (impact-per-engineering-hour):

### R1 (high ROI). **Enrich entity frontmatter with `description:` field** — corpus schema fix

The 4 gold-bearing entities (`projects/nox-mem`, `projects/paper-eval`, `people/ana`, `people/bruno`) lack a `description:` field in their YAML frontmatter. Add one:

```yaml
# memory/entities/people/bruno.md
---
name: Bruno Lima
description: Galapagos AI advisor — leads M&A AI initiatives at Galapagos Capital
type: person
status: active
last_review: 2026-04-24
---
```

This single-line schema addition makes the frontmatter chunk match its query's intent both lexically and semantically. Compare with `systems/nox-mem.md` which HAS `description:` and DID surface (chunk 216184 at rank 8-12 for ad-001).

**Effort**: ~2 hours (script: scan `memory/entities/**/*.md`, identify entries missing `description:`, prompt Gemini to draft, human review, commit, re-ingest via entity router).
**Risk**: low — additive change, no retrieval logic touched.
**Expected impact**: 3-4 of the 5 frontmatter-OOT queries enter top-10. Aggregate adversarial bucket nDCG est. +2-4 pp.

### R2 (medium ROI). **Bump `frontmatter` section_boost 1.5 → 2.0** — match compiled

Current: `SECTION_BOOST = { compiled: 2.0, frontmatter: 1.5, timeline: 0.8 }` (`src/search.ts:129-133`).

The rationale for 1.5 (YAML medium signal) presumes frontmatter has SOME content. Once R1 lands and frontmatter carries `description:`, the equivalence to `compiled` is defensible.

**Effort**: ~5 min code change + shadow-mode eval per CLAUDE.md §5 (rule: ranking changes need shadow-mode for ≥1 week baseline).
**Risk**: low-medium — will promote non-gold frontmatter chunks too (e.g., chunk 216184). Need ablation on full eval set to confirm aggregate positive.
**Expected impact**: incremental +0.5-1 pp aggregate nDCG IF R1 lands first. Without R1, ineffective (multiplying zero by anything is zero).

### R3 (medium ROI). **Relax `MAX_PER_FILE_FINAL` for entity files** — dedup carve-out

Layer 4 is correct for sprawling non-entity files (8 chunks from one paper.md saturating results), but **entity files are designed to have multiple sections that complement each other** (compiled = truth, frontmatter = metadata, timeline = events). All three may legitimately be relevant for a single query.

Proposed: `MAX_PER_FILE_FINAL = 3` for chunks where `section IS NOT NULL`, keep 2 otherwise.

```ts
// src/search-dedup.ts:90-99 patch sketch
const maxForFile = (r: SearchResult) =>
  (r as any).section != null ? 3 : MAX_PER_FILE_FINAL;
...
if (c < maxForFile(r)) {
  final.push(r);
  ...
}
```

**Effort**: ~30 min code + unit test + ablation eval.
**Risk**: low — only loosens cap by 1 chunk for ~1.8% of corpus (entity files); cannot suppress non-entity diversity.
**Expected impact**: ad-012 likely moves to top-5. Others unchanged (different mechanism).

### R4 (low ROI). **Investigate ingest path for nesting of frontmatter chunk_id**

Observed: every entity chunk's `chunk_text` starts with `chunk_id: "<id>"` literally inserted at byte 0 (e.g., `chunk_id: "ana::frontmatter"\n---\nname: ...`). This is presumably the entity ingester writing a header for self-identification. But it adds ~30 chars of constant noise to every chunk, diluting BM25 token weights and embedding signal.

**Effort**: ~1 hour to confirm intent + safe to strip OR move outside chunk_text into `metadata` JSON column.
**Risk**: medium — changing chunk_text invalidates ALL embeddings; must re-vectorize.
**Expected impact**: marginal, ~1 pp; not worth the re-vectorize cost unless other reasons accumulate.

### Recommendation summary

**Ship R1 + R3** (the corpus fix and the dedup carve-out). Land R2 only after R1 stabilizes in shadow-mode. Skip R4 unless a larger schema refactor is on the table.

---

## 8. Files

- `audits/data-g12/frontmatter-gold-queries.tsv` — 5 queries identified
- `audits/data-g12/active-retrieved.tsv` — top-20 per query, mutex active
- `audits/data-g12/disabled-retrieved.tsv` — top-20 per query, mutex disabled
- `audits/data-g12/rank-analyzer.py` — Python script computing ranks
- `audits/data-g12/ranks-output.txt` — final rank table

Source files consulted (pulled read-only via scp):

- `/tmp/g12-search.ts` (production `src/search.ts` snapshot, 669 lines)
- `/tmp/g12-dedupe.ts` (production `src/search-dedup.ts` snapshot, 102 lines)

Predecessor audits cited: `audits/2026-05-21-G10e-kw-adversarial-qualitative-audit.md` §4, G10b/G10c.

---

## 9. Constraints honoured

- Read-only investigation. No VPS write, no fresh eval, no service restart, no API write call.
- Other agents on VPS isolated dir (G10d / future ablations) untouched — all SQL ran against `g9.db` read-only.
- Branch `research/g12-frontmatter-retrieval-audit` opened from worktree main HEAD; no merge.
- Worktree sparse-checkout extended to include `audits/` and `src/` for read access; no source edits.
- Pre-commit hook active; will run on commit.

---

## 10. Open follow-ups

- **R1 corpus enrichment** is the same intervention that would also help any future queries asking about an entity's identity/purpose. Recommend doing this BEFORE EverMemBench / LongMemEval re-runs to avoid systematic recall holes.
- The eval design itself may want revisiting: putting `<entity>::frontmatter` in gold for adversarial keyword queries with typos creates an unwinnable case until the corpus carries description text. Either enrich corpus (R1) or revise gold to drop frontmatter from adversarial bucket.
- The `chunk_id: "<id>"` literal prefix in chunk_text (R4) deserves its own design discussion. Not blocking, but worth a 1-pager when the next schema refactor lands.

---

## 11. Post-audit clarification — R1 closed as not-applicable to live corpus (2026-05-21 EOD)

After R3 deployed (PR #206) and survey of the live entity-file corpus, R1 was re-scoped and **closed as not-applicable**. The audit's R1 recommendation assumed the 4 gold-bearing entities (`projects/nox-mem`, `projects/paper-eval`, `people/ana`, `people/bruno`) existed as files on disk with stub frontmatter that could be enriched. **They don't exist on disk.**

### Verification

```bash
ssh root@187.77.234.79 'find /root/.openclaw -name "bruno.md" -o -path "*people/ana.md" \
                       -o -name "paper-eval*" -o -name "nox-mem.md" -path "*projects*"' 2>&1
# (only systems/nox-mem.md exists — projects/nox-mem.md, projects/paper-eval.md,
#  people/ana.md, people/bruno.md are all ABSENT)
```

The chunks for those entities appear in `g9.db` (eval DB) but the source files were never on disk in the live workspace, OR were removed before this audit. They are **orphan chunks**.

### Live entity corpus state

Survey of `/root/.openclaw/workspace/memory/entities/**/*.md` (2026-05-21):

```
total entity files: 183
files with `description:` field: 183 / 183 (sampled 5, all rich descriptions)
```

The live corpus is NOT impoverished in the way the audit assumed — every entity file already carries a meaningful `description:` extracted from the body during entity-ingest. The "stub YAML" pattern flagged in §3-§6 was specific to the 4 orphan eval-fixture entities, not the production corpus.

### Why R1 is not actioned

1. **Manufacturing corpus to match eval fixtures is gaming the test**, not improving retrieval. The 5 adversarial queries that go OOT are stressing robustness on entities that aren't in the live workspace.
2. **`systems/nox-mem.md` already exists** with a rich description covering nox-mem context. Creating a duplicate `projects/nox-mem.md` to match the eval `nox-mem::frontmatter` gold chunk would duplicate the system entity under a different tier — confusion over clarity.
3. **Adversarial OOT is expected behaviour** for an adversarial bucket. Single-hop, multi-hop, and open-domain remain healthy (per G10d ablation, D51). Closing adversarial fixture gaps via corpus manipulation is anti-pattern.
4. **The 4 entities (especially `people/ana`, `people/bruno`)** are real people whose framing is Toto's call — drafting stubs from context would risk false framing of human entities. Skipped explicitly.

### Future trigger

If a future eval set replaces g9.db and the orphan entities disappear, the 5 affected queries vanish and R1 becomes moot retroactively. If Toto separately decides he wants `projects/nox-mem.md` or `projects/paper-eval.md` as first-class project entities (distinct from `systems/nox-mem.md`), he creates them on his own framing and re-ingest produces the chunks naturally.

### Cross-references

- Decision: see DECISIONS.md D52 (L4 plural normalisation) which has cross-ref to this clarification
- R3 deployed: PR #206 + 2026-05-21 EOD SCP to VPS (cap=2→3 for `section != NULL` chunks)
- R2 (frontmatter section_boost 1.5 → 2.0) remains conditional on R1 — also closed by extension since R1 is moot
- Audit PR #205 (this file's original commit)
- Audit PR #211 (L4 extraction_method NULL finding) — separate concern, watchpoint 2026-05-24
