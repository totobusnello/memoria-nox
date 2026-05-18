# staged-migrations — v11 + v19

Schema migrations for nox-mem. All additive. Zero breaking changes. Zero impact on existing data.

---

## 1. What's in v11 — Telemetry Foundation

Adds 3 new tables (no modifications to existing tables):

| Table | Sprint | Purpose |
|---|---|---|
| `answer_telemetry` | P1 (PR #18) | Per-query answer quality: retrieval count, citation count, latency, fallback flag, cost |
| `agent_events` | P2 (PR #24) | Hook auto-capture: pre_compact / session lifecycle events with JSON payload + redaction count |
| `provider_telemetry` | A3 (PR #25) | Per-call provider cost tracking: embed / complete / health_check with tokens + latency |

Total new indexes: **7**
`PRAGMA user_version`: 10 → 11

### Sprints unblocked by v11

- **P1** (answer_telemetry): citation accuracy tracking and hallucination detection pipeline
- **P2** (agent_events): pre_compact hook + session-boundary capture
- **A3** (provider_telemetry): provider abstraction cost dashboard + quota alerting

---

## 2. What's in v19 — Confidence, Provenance, Temporal

Adds columns to two existing tables via `ALTER TABLE ADD COLUMN` (all nullable or with safe defaults):

### `chunks` (L3 — PR #15)

| Column | Type | Default | Values |
|---|---|---|---|
| `confidence` | REAL | 0.8 | 0.0–1.0 (CHECK enforced) |
| `provenance_kind` | TEXT | NULL | `observed` \| `declared` \| `inferred` \| `derived` \| `user-marked` \| NULL |

### `kg_relations` (L2 — PR #13, L4)

| Column | Type | Default | Values |
|---|---|---|---|
| `confidence` | REAL | 0.7 | 0.0–1.0 (CHECK enforced) |
| `superseded_by_relation_id` | INTEGER FK | NULL | FK → kg_relations(id) ON DELETE SET NULL |
| `superseded_at` | INTEGER | NULL | epoch_ms |
| `superseded_reason` | TEXT | NULL | `auto_supersede_temporal` \| `manual_resolution` \| `stale_link_reconciliation` \| `dismiss` \| NULL |
| `created_at` | INTEGER | now_ms | epoch_ms |
| `updated_at` | INTEGER | now_ms | epoch_ms |
| `extraction_method` | TEXT | NULL | `regex_only` \| `gemini_only` \| `regex_primary_gemini_secondary` \| `frontmatter` \| `manual` \| NULL |

New indexes: **3** (`idx_kg_relations_confidence`, `idx_kg_relations_superseded`, `idx_kg_relations_created`)

`PRAGMA user_version`: 11 → 19

> Note: versions 12–18 are reserved for other overnight sprints (graph pruning, eval harness, etc.). The version numbers are intentional gaps — they are not missing migrations.

### Sprints unblocked by v19

- **L3** (chunks.confidence + provenance_kind): confidence-weighted retrieval scoring
- **L2** (kg_relations): temporal supersession chain + relation lifecycle management
- **L4** (extraction_method): regex-first extraction pipeline with method attribution

---

## 3. Application Procedure

**MANDATORY: wrap every migration in `withOpAudit()`** (CLAUDE.md rule #6). This creates an atomic VACUUM INTO snapshot before mutation and records the operation in `ops_audit`.

```typescript
import { withOpAudit } from '../src/lib/op-audit';
import { readFileSync } from 'fs';

// Apply v11
await withOpAudit('migrate_v11', async (db) => {
  const sql = readFileSync('staged-migrations/v11.sql', 'utf8');
  db.exec(sql);
});

// Apply v19 (only after v11 succeeds)
await withOpAudit('migrate_v19', async (db) => {
  const sql = readFileSync('staged-migrations/v19.sql', 'utf8');
  db.exec(sql);
});
```

Or via sqlite3 CLI (dev/staging only, no withOpAudit wrapper):

```bash
# Verify current version first
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "PRAGMA user_version;"
# Should return 10 before v11, 11 before v19

sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db < staged-migrations/v11.sql
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db < staged-migrations/v19.sql
```

---

## 4. Validation

Run test files after each migration:

```bash
sqlite3 /path/to/nox-mem.db < staged-migrations/v11-tests.sql
sqlite3 /path/to/nox-mem.db < staged-migrations/v19-tests.sql
```

All lines should read `PASS: ...`. Any `FAIL:` line indicates a problem.

Also confirm via HTTP:

```bash
curl http://127.0.0.1:18802/api/health | jq '.schemaVersion'
# Expected: 19
```

---

## 5. Rollback Strategy

### v11 rollback — safe and supported

`v11-rollback.sql` drops all 3 telemetry tables. No data from existing tables is touched. Run:

```bash
sqlite3 /path/to/nox-mem.db < staged-migrations/v11-rollback.sql
```

### v19 rollback — forward-only (NOT recommended in prod)

SQLite `DROP COLUMN` is unreliable with CHECK constraints and partial indexes. **v19 is designed as forward-only.**

If rollback is truly required:
1. `VACUUM INTO '/var/backups/nox-mem/pre-rollback-v19-<ts>.db'`
2. Build a v18-schema DB manually (see `v19-rollback.sql` for column list)
3. Use `safeRestore()` from `src/lib/op-audit.ts` — never `cp` directly (stale WAL risk)

Preferred alternative: disable the L2/L3/L4 feature code while keeping the schema columns in place. The columns are all nullable or defaulted — zero operational impact when unused.

---

## 6. Schema Versioning

```
v10  (current baseline — retention_days + pain + section)
 │
v11  ← this migration (telemetry tables)
 │
v12–v18  (reserved for other overnight sprints)
 │
v19  ← this migration (confidence + provenance columns)
```

`PRAGMA user_version` is the authoritative version. Never modify it manually outside a migration transaction.

---

## 7. Safety Checklist Before Applying to Prod

- [ ] `source /root/.openclaw/.env` set (Gemini key available for post-migration vectorize)
- [ ] `curl http://127.0.0.1:18802/api/health` confirms service is UP
- [ ] Current `PRAGMA user_version` matches expected pre-migration value
- [ ] `withOpAudit()` wrapper creates snapshot successfully (check disk space first: `df -h /var/backups/`)
- [ ] Run `*-tests.sql` and verify all PASS
- [ ] Confirm `sectionDistribution.compiled == 183` unchanged post-migration (v19 must not disturb existing sections)
