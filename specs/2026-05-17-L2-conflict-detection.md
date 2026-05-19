# L2 — KG conflict / contradiction detection (memanto-inspired)

**ID:** L2 (Lab, NOT pillar)
**Status:** 📋 SPEC — implementation-ready, blocked on schema extension (Phase 0)
**Owner:** Toto (decisão); Maestro (execução)
**Data:** 2026-05-17
**Origem:** Six Gaps #5 from memanto positioning ("Conflict detection — contradictions silently coexist"). Lab L2 turns the gap into a differentiator on our KG substrate.
**Tagline alignment:** *Pain-weighted hybrid memory with shadow discipline — yours by design.* Conflict detection is a **shadow-first** capability with append-only audit and no destructive auto-resolution by default.

**Cross-link:** `docs/ROADMAP.md` §Lab L2; `CLAUDE.md` regra crítica #5 (ranking shadow ≥7d); `CLAUDE.md` regra crítica #6 (destructive ops gated by `withOpAudit`); `specs/2026-05-06-E13-temporal-aware-ranking.md` (temporal section_boost pattern); `specs/2026-05-06-E05b-reason-ranking-boost.md` (relation_reason enum precedent).

---

## 1. Motivação

### memanto Gap #5

memanto markets "Conflict detection — contradictions silently coexist" as one of six gaps in incumbent memory systems. From their positioning materials, the implementation is **text-level / embedding-based**: two chunks with embeddings above a similarity threshold but opposing semantic content trigger a flag.

This is a hard problem in their substrate because chunks are flat text — there is no notion of *who said what about which entity*. Embedding contradiction detectors need an NLI model and produce false positives on paraphrase, negation polarity, hedge language, etc.

### Why our KG is the ideal substrate

memoria-nox already has the structure memanto has to reconstruct:

- **15.646 entities** (typed nodes)
- **21.533 relations** (typed edges: `source_entity_id INTEGER FK`, `target_entity_id INTEGER FK`, `predicate TEXT`, `relation_reason` enum 7, `evidence_chunk_id FK`)
- **Bipartite grounding**: every relation points back to the chunk that produced it
- **Predicate-as-key semantics**: `(subject, predicate)` is the natural primary axis for contradiction — "X has property P=A" vs "X has property P=B" is a SQL `GROUP BY` away.

memanto detects contradictions at the **text level** (embedding similarity + opposing semantics — expensive, fuzzy).
memoria-nox detects contradictions at the **relation level** (structured, semantic, deterministic, SQL-first).

**Differentiator framing:** structured contradictions are detected with `O(N)` SQL over relations and rationalized via evidence chunks. No NLI model, no embedding round-trip, no probabilistic threshold tuning. Where memanto must guess, we can prove.

### Scope of v1

v1 ships **Type 1 (direct contradiction)** end-to-end. Type 3 (temporal supersession) ships **gated on the schema extension** (Phase 0). Types 2 and 4 are deferred to L2.1 to keep v1 boring, demoable, and falsifiable.

---

## 2. Types of conflict

| Type | Name | Definition | v1? |
|---|---|---|---|
| **1** | **Direct contradiction** | Same `(source_entity_id, predicate)` resolves to `>1` distinct `target_entity_id` (or scalar object) where the predicate is **functional** (cardinality ≤1) | ✅ ship |
| **2** | Logical conflict | Two predicates declared mutually exclusive (e.g. `is_deprecated` AND `is_recommended` on same entity) | ❌ defer L2.1 |
| **3** | **Temporal supersession** | Same `(subject, predicate)` with different objects at different times — the newer fact supersedes the older; older is not "wrong", just stale | ✅ ship (gated on Phase 0 schema extension) |
| **4** | Indirect / transitive | Contradiction emerges via inference across multiple hops (`A → B`, `B → C`, `A ↛ C` declared explicitly) | ❌ defer L2.1+ |

### Type 1 — formal definition

Predicate `P` is **functional** if `(subject, P) → object` is a partial function (max 1 object per subject). Examples in our corpus:

- `is_deployed_at` (a tool is deployed to one VPS at a time)
- `belongs_to_project` (an entity belongs to one project)
- `has_status` (one current status)
- `has_owner` (one owner — though debatable)

Non-functional predicates (`uses`, `mentions`, `depends_on`) are **excluded from Type 1 detection** by being absent from the `functional_predicates` registry (see §4.1).

### Type 3 — formal definition

Given two relations `R1, R2` with same `(source_entity_id, predicate)` but different `target_entity_id`:

- If predicate is **temporal-natured** (registry entry `temporal_supersedes=true`), the newer one (by `created_at`) supersedes the older.
- Newer is marked as canonical, older is marked `superseded_by_relation_id = newer.id`.

Examples: `has_status`, `is_running_version`, `points_to_branch`.

---

## 3. Schema additions (Phase 0 — blocker)

### 3.1 `kg_relations` extension

Open finding from P3: **kg_entities and kg_relations have no `created_at`/`updated_at`**. This is required for Type 3 and strongly desirable for Type 1 (tie-breaking, auto-resolution recency window).

```sql
-- Migration: schema_v{next}_kg_temporal_and_conflicts.sql
ALTER TABLE kg_relations ADD COLUMN created_at INTEGER NOT NULL DEFAULT (unixepoch());
ALTER TABLE kg_relations ADD COLUMN updated_at INTEGER NOT NULL DEFAULT (unixepoch());
ALTER TABLE kg_relations ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0
  CHECK (confidence >= 0.0 AND confidence <= 1.0);
ALTER TABLE kg_relations ADD COLUMN superseded_by_relation_id INTEGER NULL
  REFERENCES kg_relations(id) ON DELETE SET NULL;
ALTER TABLE kg_relations ADD COLUMN superseded_at INTEGER NULL;
ALTER TABLE kg_relations ADD COLUMN superseded_reason TEXT NULL
  CHECK (superseded_reason IN ('auto_temporal','auto_confidence','manual','conflict_resolution') OR superseded_reason IS NULL);

CREATE INDEX idx_kg_relations_subject_predicate
  ON kg_relations(source_entity_id, predicate) WHERE superseded_by_relation_id IS NULL;
CREATE INDEX idx_kg_relations_superseded
  ON kg_relations(superseded_by_relation_id) WHERE superseded_by_relation_id IS NOT NULL;

-- Backfill: existing rows get created_at = COALESCE(evidence_chunk.created_at, unixepoch())
UPDATE kg_relations
SET created_at = COALESCE(
  (SELECT c.created_at FROM chunks c WHERE c.id = kg_relations.evidence_chunk_id),
  unixepoch()
)
WHERE created_at = (SELECT MAX(created_at) FROM kg_relations);  -- only newly defaulted rows
```

### 3.2 `kg_entities` extension (minimal)

```sql
ALTER TABLE kg_entities ADD COLUMN created_at INTEGER NOT NULL DEFAULT (unixepoch());
ALTER TABLE kg_entities ADD COLUMN updated_at INTEGER NOT NULL DEFAULT (unixepoch());
```

### 3.3 `kg_conflicts` table (new)

```sql
CREATE TABLE kg_conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conflict_type TEXT NOT NULL CHECK (conflict_type IN ('direct','temporal','logical','transitive')),
  source_entity_id INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
  predicate TEXT NOT NULL,
  -- relations involved (1..N, denormalized via junction below)
  detected_at INTEGER NOT NULL DEFAULT (unixepoch()),
  detected_by TEXT NOT NULL CHECK (detected_by IN ('nightly_job','on_demand','on_insert')),
  status TEXT NOT NULL DEFAULT 'unresolved'
    CHECK (status IN ('unresolved','auto_resolved','manually_resolved','dismissed','stale')),
  resolution_action TEXT NULL
    CHECK (resolution_action IN ('supersede','merge','keep_both','dismiss_false_positive') OR resolution_action IS NULL),
  resolved_at INTEGER NULL,
  resolved_by TEXT NULL,  -- 'auto' | user id | 'system'
  notes TEXT NULL,
  shadow_mode INTEGER NOT NULL DEFAULT 1  -- 1=shadow (no ranking effect), 0=live
);

CREATE TABLE kg_conflict_relations (
  conflict_id INTEGER NOT NULL REFERENCES kg_conflicts(id) ON DELETE CASCADE,
  relation_id INTEGER NOT NULL REFERENCES kg_relations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('canonical','superseded','candidate')),
  PRIMARY KEY (conflict_id, relation_id)
);

CREATE INDEX idx_kg_conflicts_status ON kg_conflicts(status) WHERE status = 'unresolved';
CREATE INDEX idx_kg_conflicts_subject ON kg_conflicts(source_entity_id, predicate);
```

### 3.4 `functional_predicates` registry (config, not table)

Lives in `config/kg-functional-predicates.json` (versioned in repo, loaded at startup). Initial set seeded from corpus analysis:

```json
{
  "functional": [
    "is_deployed_at",
    "belongs_to_project",
    "has_status",
    "has_owner",
    "has_version",
    "is_running_version"
  ],
  "temporal_supersedes": [
    "has_status",
    "is_running_version",
    "points_to_branch",
    "has_owner"
  ],
  "version": 1
}
```

Reasoning kept in config (not DB) so seed list evolves via PR review, not silent DML.

---

## 4. Detection algorithm

SQL-first. No LLM, no embeddings in v1.

### 4.1 Type 1 — direct contradiction

```sql
-- Pseudo-SQL (functional_predicates injected from config)
WITH active AS (
  SELECT id, source_entity_id, predicate, target_entity_id, confidence, created_at, evidence_chunk_id
  FROM kg_relations
  WHERE superseded_by_relation_id IS NULL
    AND predicate IN (:functional_predicates)
)
SELECT
  source_entity_id,
  predicate,
  COUNT(DISTINCT target_entity_id) AS distinct_targets,
  GROUP_CONCAT(id) AS relation_ids
FROM active
GROUP BY source_entity_id, predicate
HAVING COUNT(DISTINCT target_entity_id) > 1;
```

Complexity: `O(R)` over active relations (R=21.533 today → trivial). Index `idx_kg_relations_subject_predicate` covers the predicate filter + group.

### 4.2 Type 3 — temporal supersession

Subset of Type 1 results where predicate is in `temporal_supersedes`. Detection produces a *candidate* — auto-resolution rules in §6 decide whether to materialize the supersession.

### 4.3 When detection runs

| Trigger | Cadence | Scope |
|---|---|---|
| **Nightly cron** | 03:30 BRT (after backup-all 02:00) | Full corpus |
| **On-demand** | `nox-mem conflicts scan` | Full or `--subject <entity>` |
| **On-insert** (Phase 2, deferred) | After `kg-extract` batch commit | Touched `(subject, predicate)` pairs only |

Phase 2 on-insert is documented but **not in v1** to keep ingest path off the critical path. Nightly + on-demand cover the SLO.

### 4.4 Detection job lifecycle

Wrapped in `withOpAudit('kg-conflict-scan', ...)` (CLAUDE.md regra #6). Status transitions: `started → success | failed | crashed`. Snapshot **not** required because detection is read-only and only writes to `kg_conflicts` (additive, append-only via trigger — see §10).

---

## 5. Resolution UX

### 5.1 CLI

```bash
# List unresolved conflicts
nox-mem conflicts list [--type direct|temporal] [--limit N] [--json]

# Show one conflict in detail (entities, relations, evidence chunks)
nox-mem conflicts show <conflict_id>

# Resolve: choose one relation as canonical, supersede the others
nox-mem conflicts resolve <conflict_id> --keep <relation_id> [--note "..."]

# Resolve: keep both (mark as not-a-contradiction, e.g. multi-role entity)
nox-mem conflicts resolve <conflict_id> --keep-both [--note "..."]

# Dismiss as false positive (won't be re-flagged for same predicate+subject for 30d)
nox-mem conflicts dismiss <conflict_id> [--note "..."]

# Force re-scan
nox-mem conflicts scan [--subject <entity_name_or_id>] [--dry-run]
```

`--dry-run` on `resolve`/`scan` produces JSON preview without mutation (CLAUDE.md regra #6).

### 5.2 HTTP API (port 18802)

```
GET    /api/kg/conflicts?status=unresolved&type=direct&limit=50
GET    /api/kg/conflicts/:id
POST   /api/kg/conflicts/:id/resolve       { keep: <relation_id> | "both", note?: "..." }
POST   /api/kg/conflicts/:id/dismiss       { note?: "..." }
POST   /api/kg/conflicts/scan              { subject?: <entity>, dry_run?: bool }
```

Response includes hydrated entities + evidence chunks for UI consumption (dashboard page already planned).

### 5.3 MCP tools

```
kg_conflicts_list        — same shape as CLI list
kg_conflicts_resolve     — write op, requires user confirmation in client
kg_conflicts_dismiss     — write op
kg_conflicts_scan        — read-or-write depending on dry_run
```

MCP write ops are gated by `NOX_MCP_ALLOW_WRITES=1` (existing pattern).

---

## 6. Auto-resolution v1 (conservative)

Auto-resolution runs **after detection** as a separate phase, opt-in via `NOX_KG_AUTO_RESOLVE=1` (default off in v1 shadow rollout).

### 6.1 Type 1 — confidence + recency gate

For each direct-contradiction conflict with exactly 2 candidate relations `R_new` (newer `created_at`) and `R_old`:

```
IF R_new.confidence >= R_old.confidence + 0.20
   AND (R_new.created_at - R_old.created_at) > 30 * 86400  -- >30 days gap
   AND R_new is NOT user-marked (resolved_by user historically)
   AND R_old is NOT user-marked
THEN
  mark R_old.superseded_by_relation_id = R_new.id
  mark R_old.superseded_reason = 'auto_confidence'
  conflict.status = 'auto_resolved'
  conflict.resolution_action = 'supersede'
ELSE
  conflict.status = 'unresolved'  -- await human
```

### 6.2 Type 3 — temporal gate

```
IF predicate ∈ temporal_supersedes
   AND newer is single (no further ambiguity)
   AND R_old is NOT user-marked
THEN
  supersede with reason = 'auto_temporal'
ELSE
  flag unresolved
```

### 6.3 Hard constraint — never override the user

Relations with `resolved_by IS NOT NULL` (i.e. previously touched by a human resolution) are **never** auto-superseded. They can only be changed by another manual resolve. This is the response to risk #2.

---

## 7. Ranking integration

### 7.1 Weight on superseded relations

```
superseded_relation_weight = 0.1  (90% demote, not zero — evidence still discoverable)
```

Applied **only** in the SPO injection scoring path (`E03a`-style boost lookup), not in FTS5 / vector retrieval. Superseded relations remain searchable; they just don't reinforce ranking.

### 7.2 Unresolved conflicts

While `kg_conflicts.status = 'unresolved'`:

- **Both relations stay at full weight** (don't pick winners we don't know).
- Surface a `conflict_flag` in API search response payload so callers can render "⚠ conflicting info" (UI affordance, not a ranker decision).

### 7.3 Shadow mode

While `kg_conflicts.shadow_mode = 1` (default for ≥7 days post-deploy per CLAUDE.md #5):

- Detection runs, conflicts are persisted, telemetry collected.
- `superseded_relation_weight = 1.0` (no ranking effect).
- `/api/health.kgConflicts` exposes counts and rate.
- After 7d baseline, decision gate flips `shadow_mode` to 0 with explicit op-audit row.

---

## 8. Telemetry

`/api/health.kgConflicts`:

```json
{
  "schemaVersion": "v{next}",
  "lastScanAt": "2026-05-17T03:30:14Z",
  "lastScanDurationMs": 412,
  "totals": {
    "unresolved": 17,
    "auto_resolved": 4,
    "manually_resolved": 3,
    "dismissed": 2
  },
  "byType": { "direct": 24, "temporal": 2 },
  "topPredicates": [
    { "predicate": "has_status", "count": 8 },
    { "predicate": "is_deployed_at", "count": 5 }
  ],
  "shadowMode": true,
  "rankingActive": false
}
```

Logged events (new) in `kg_telemetry` (or extend existing):

- `kg.conflict.detected`  — `{conflict_id, type, subject, predicate, n_candidates}`
- `kg.conflict.resolved`  — `{conflict_id, action, resolved_by, latency_ms_since_detected}`
- `kg.conflict.dismissed` — `{conflict_id, reason}`
- `kg.conflict.scan`      — `{scan_id, duration_ms, found, by}`

---

## 9. Tests plan

### 9.1 Fixtures (`tests/fixtures/kg-conflicts/`)

| Fixture | Type | Expected detection |
|---|---|---|
| `direct-positive-1.sql` | Type 1 | 1 conflict, 2 relations |
| `direct-positive-many.sql` | Type 1 | 1 conflict, 3 relations |
| `direct-negative-nonfunctional.sql` | — | 0 conflicts (predicate not in registry) |
| `direct-negative-supersededAlready.sql` | — | 0 conflicts (one is superseded_by) |
| `temporal-supersede-auto.sql` | Type 3 | 1 auto_resolved |
| `temporal-supersede-tooclose.sql` | Type 3 | 1 unresolved (gap <30d) |
| `user-marked-protected.sql` | Type 1 | 1 unresolved (user-marked, never auto-overrides) |
| `confidence-gate-below.sql` | Type 1 | 1 unresolved (Δconf <0.20) |
| `confidence-gate-above.sql` | Type 1 | 1 auto_resolved |

### 9.2 Test types

- **Unit:** `parseFunctionalPredicates`, `shouldAutoResolve` decision matrix, `withOpAudit` integration.
- **Integration:** end-to-end fixture → scan → assert `kg_conflicts` rows.
- **Property-based:** invariant — after any sequence of resolve/dismiss ops, `(source_entity_id, predicate)` in `functional_predicates` has at most 1 active relation.
- **Precision/recall on cured set:** 50 manually labeled `(subject, predicate)` pairs (target ≥90% precision, ≥80% recall on Type 1).
- **Boundary tests:** auto-resolution edges (Δconf = 0.19 vs 0.20; gap = 29d vs 31d).
- **Regression:** nDCG@10 unchanged with `shadow_mode=1` (R01a harness); after activation, no regression beyond noise band.

### 9.3 Schema invariants canary

Extend `check-schema-invariants.sh` (cron */15min):

- Every `kg_conflicts.relation_id` resolves to existing relation
- No `relation.superseded_by_relation_id` cycles (chain length ≤2 in v1)
- `resolved_at IS NOT NULL ⟺ status IN ('auto_resolved','manually_resolved','dismissed')`

---

## 10. Definition of Done

1. Schema migration applied; `created_at` backfill validated (no NULLs in `kg_relations.created_at`).
2. Type 1 detection precision **≥90%** on 50-pair cured set; recall **≥80%**.
3. End-to-end manual resolve works via CLI **and** HTTP **and** MCP (3 channels green).
4. Shadow mode runs ≥7 days with `/api/health.kgConflicts` populated; **no nDCG@10 regression** (R01a baseline, within noise band ±1.5pp).
5. Append-only audit: `DELETE`/`UPDATE` of terminal `kg_conflicts` rows blocked by trigger (mirror `ops_audit` pattern, CLAUDE.md regra #6).

---

## 11. NÃO-fazemos (v1)

- **No Type 2 (logical conflict).** Requires mutual-exclusion registry — defer L2.1.
- **No Type 4 (transitive).** Requires multi-hop reasoner — defer L2.2.
- **No auto-resolution of user-marked relations.** Ever. Hard constraint.
- **No LLM fuzzy matching for "is this really a contradiction?".** SQL-first only; predicate registry is the truth.
- **No cross-corpus contradiction detection.** Single-instance only.
- **No automatic deletion of superseded relations.** Demote-only (weight × 0.1). Discovery preserved.
- **No on-insert detection** in v1. Nightly + on-demand only.
- **No ranking effect during shadow window.** `superseded_relation_weight = 1.0` until flip.

---

## 12. Riscos

| # | Risco | Mitigação |
|---|---|---|
| 1 | **False-positive flood** — registry too permissive, dashboard buried in noise | Conservative seed list (6 predicates); precision gate ≥90% on cured set blocks expansion; `dismiss` action with 30d re-suppression for same `(subject, predicate)` |
| 2 | **User-marked relation silently superseded** by auto-resolution | Hard rule §6.3 — `resolved_by IS NOT NULL` is immutable except by another manual resolve; covered by `user-marked-protected.sql` fixture |
| 3 | **Performance on 100k+ relation graphs** — full scan O(N) becomes too slow | Index `idx_kg_relations_subject_predicate` partial WHERE `superseded_by IS NULL`; Phase 2 incremental on-insert (deferred but designed); SLO: nightly scan <30s at 100k |
| 4 | **Temporal `created_at` backfill is wrong** — falls back to `unixepoch()` when no evidence chunk, collapsing all old relations to "today" | Backfill prefers `evidence_chunk.created_at`; rows with neither chunk nor explicit time get `created_at = MIN(unixepoch(), schema_migration_ts)` and are excluded from Type 3 auto-resolution for 30d post-migration |
| 5 | **Conflicting relations both correct** — multi-role entity legitimately has two `has_owner` values | `resolve --keep-both` action; predicate registry can be PR-narrowed if a predicate produces persistent false positives |
| 6 | **Auto-resolution oscillation** if confidence is recomputed periodically | Confidence is set at extraction time and immutable in v1; future recompute requires explicit migration and re-detection pass |
| 7 | **Predicate normalization drift** — extractor emits `is_deployed_at` and `deployed_at` for same semantic | Detection joins on **canonical** predicate (lowercase, underscore); pre-existing `predicate_aliases` table (if absent, add as part of Phase 0) |

---

## 13. Shadow rollout plan

Hard requirement from CLAUDE.md regra crítica #5 (ranking changes shadow ≥7d).

### Phase 0 — schema (D-0)
- Migration applied
- Backfill validated
- `functional_predicates.json` committed
- No detection job running

### Phase 1 — shadow detection (D+0 to D+7)
- Nightly scan enabled
- `/api/health.kgConflicts` live
- `shadow_mode = 1` on all rows
- Auto-resolution **disabled** (`NOX_KG_AUTO_RESOLVE` unset)
- Manual resolve CLI/HTTP/MCP enabled (humans can act, but no ranking effect)
- **Gate check D+7:** precision ≥90% on 50 cured pairs, no nDCG@10 regression in R01a, conflict volume <100 unresolved

### Phase 2 — auto-resolution shadow (D+7 to D+14)
- `NOX_KG_AUTO_RESOLVE=1` (still shadow_mode=1 — auto fills `superseded_by` but ranking unaffected)
- Monitor auto-resolution precision via Toto manual review of 20 auto_resolved rows
- **Gate check D+14:** ≥95% of auto_resolved confirmed correct on manual review

### Phase 3 — ranking activation (D+14)
- `superseded_relation_weight = 0.1`
- `shadow_mode = 0` on new conflicts
- R01a regression monitored daily for 7d post-flip
- Rollback path: set `superseded_relation_weight = 1.0` in config + restart api (no DB mutation needed)

---

## 14. Open questions

1. **Predicate normalization registry** — does `predicate_aliases` exist today or is it part of Phase 0? (Audit needed; if absent, lightweight table `kg_predicate_aliases(alias TEXT PRIMARY KEY, canonical TEXT NOT NULL)`).
2. **Confidence source for legacy relations** — `confidence = 1.0` default is optimistic. Should we backfill `0.5` for pre-migration relations to prevent them dominating auto-resolution? Decision: **yes**, default `1.0` for new extractions, backfill `0.7` for pre-migration (configurable).
3. **`has_owner` functionality** — is it truly functional? An entity can have a primary + secondary owner. Recommend dropping from seed list and re-adding post-corpus-review.
4. **Dashboard surface** — add `Conflicts` page to agent-hub-dashboard or initial CLI-only? Recommend CLI + HTTP first; dashboard in follow-up.
5. **Phase 2 on-insert detection** — defer to L2.1 or include as opt-in flag in v1? Recommend defer (keeps ingest critical path clean).

---

## 15. Effort estimate

| Phase | Work | Estimate |
|---|---|---|
| Phase 0 | Schema migration + backfill + `functional_predicates.json` | 2h |
| Phase 1 | Detection SQL + nightly job + `withOpAudit` wrap + `/api/health.kgConflicts` | 3h |
| Phase 1 | CLI `conflicts list/show/scan/dismiss/resolve` | 2h |
| Phase 1 | HTTP API endpoints | 1.5h |
| Phase 1 | MCP tools (3) | 1h |
| Phase 1 | Fixtures + unit + integration tests (50 cured pairs labeled) | 3h |
| Phase 2 | Auto-resolution logic + boundary tests | 1.5h |
| Phase 3 | Shadow gate analysis + ranking flip | 0.5h |
| **Total** | | **~14.5h** (1.5 working days + 14d shadow window) |

---

*Spec gerado overnight 2026-05-17 sob a tagline "Pain-weighted hybrid memory with shadow discipline — yours by design."*
