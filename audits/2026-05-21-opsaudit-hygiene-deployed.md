# opsAudit Hygiene — Issues #1 + #3 Deployed (2026-05-21)

> **Status:** SHIPPED. Issues #1 (started_at type chaos) + #3 (test ops + db_source NULL noise) fixed in code + data. /api/health.opsAudit now reports realistic 24h numbers.

## Summary

| Issue | Severity | Fix | Outcome |
|---|---|---|---|
| #1 started_at TEXT chaos | metric noise | code (CAST + trigger) + data (table rebuild) | 56/56 rows INTEGER, column type=INTEGER, regression-blocking trigger installed |
| #3 test ops pollution | metric noise | code (NOT LIKE 'test-%' filter) + data (DELETE 20 rows) | 0 test-% rows in ops_audit |

Issue #3B (require explicit `db_source` in `withOpAudit` signature) intentionally deferred — refactor touches all callers; #3A reporting filter solves the immediate metric problem.

## Before / after

### typeof(started_at) distribution

| state | type | count |
|---|---|---|
| **before** | text | 56 |
| **after** | integer | 36 |

(36 = 56 − 20 test-% cleanup rows.)

### TEXT format breakdown (pre-migration only)

| bucket | count |
|---|---|
| `iso_format` (`"2026-04-27 02:00:03"`) | 47 |
| `numeric_text` (`"1779242511707.0"`) | 9 |
| `integer` | 0 |

### /api/health.opsAudit

**Before:**
```json
{
  "total_24h": 48,
  "success_24h": ~22,
  "failed_24h": 10,
  "crashed_24h": 12,
  "byDbSource": {
    "main": { ... },
    "unknown": { "total": ~33, "crashed": 12, "failed": 10, ... }
  }
}
```

(numbers from audit `2026-05-21-opsAudit-investigation.md` — false-positive 24h window held April/May rows due to TEXT-vs-INT lexicographic compare.)

**After:**
```json
{
  "total_24h": 1,
  "success_24h": 1,
  "failed_24h": 0,
  "crashed_24h": 0,
  "last_op": {
    "op_name": "daily-main",
    "status": "success",
    "finished_at": "2026-05-21 06:00:23"
  },
  "byDbSource": {
    "main": { "total": 1, "success": 1, "failed": 0, "crashed": 0, "running": 0 }
  }
}
```

Real 24h window = 1 op (the nightly `daily-main` consolidation). No `unknown` bucket. No test pollution. Honest.

### Trigger state

| trigger | before | after |
|---|---|---|
| `trg_ops_audit_no_delete` | ✓ | ✓ |
| `trg_ops_audit_terminal_immutable` | ✓ | ✓ |
| `trg_ops_audit_started_at_must_be_int` | — | ✓ (Issue #1C) |
| `trg_ops_audit_started_at_must_be_int_upd` | — | ✓ (Issue #1C) |

### Column schema

| column | before | after |
|---|---|---|
| `started_at` type | `TEXT NOT NULL DEFAULT (datetime('now'))` | `INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000)` |

## Changes

### Code

- **`src/lib/op-audit.ts`** (replaces VPS version)
  - `ensureAuditTable()` — adds `trg_ops_audit_started_at_must_be_int` BEFORE INSERT trigger + `_upd` BEFORE UPDATE OF started_at trigger; aborts if `typeof(NEW.started_at) != 'integer'`.
  - `getOpAuditStats()` — wraps `started_at` comparisons in `CAST(... AS INTEGER)` (6 sites: total/success/failed/crashed counters + last_op SELECT + byDbSource GROUP BY) and adds `op_name NOT LIKE 'test-%'` filter to all 24h queries.
  - `reapZombies()` — same defensive CAST for the running-row threshold.
  - `withOpAudit()` INSERT — wraps `started_at` parameter in `CAST(? AS INTEGER)` to defeat TEXT-affinity column coercion + better-sqlite3's REAL-binding default.

### Data migrations

- **`scripts/migrate-opsaudit-started-at-2026-05-21.sh`** — full table rebuild (CREATE ops_audit_new + INSERT SELECT with CASE-normalized started_at + DROP ops_audit + RENAME). Atomic, idempotent (detects already-INTEGER column type).
- **`scripts/cleanup-test-ops-audit-2026-05-21.sh`** — VACUUM INTO snapshot + DELETE WHERE op_name LIKE 'test-%'. Auto-detects trigger state for trigger-toggle vs plain DELETE.

### Deploy guide

- **`staged-1.7a/DEPLOY-OPSAUDIT-HYGIENE.md`** — pre-flight commands, deploy sequence (push code → build → migrate → cleanup → restart API), validation, recovery, and lessons cravadas.

## Deployment timeline (2026-05-21, BRT)

| time | event |
|---|---|
| 10:50 | Audit ack'd, branch `fix/opsaudit-hygiene-issues-1-3` created in worktree |
| 10:53 | `op-audit.ts` patched + pushed to VPS, `npx tsc` rebuilt `dist/lib/op-audit.js` (~7 CAST, 6 NOT LIKE, 2 trigger refs) |
| 10:53 | First migration attempt — failed: `trg_ops_audit_started_at_must_be_int` rejected withOpAudit's own INSERT because better-sqlite3 binds Date.now() as REAL |
| 10:57 | Code fix: wrap INSERT parameter in `CAST(? AS INTEGER)`; rebuild |
| 10:58 | Second migration attempt — failed: TEXT column affinity coerces INTEGER back to TEXT before trigger sees it; `UPDATE` migration impossible |
| 11:02 | Migration script rewritten as table rebuild. Third attempt — failed: `sqlite3` CLI lacked `vec0` extension (chunks table has trg_chunks_delete_cascade referencing it); error during DROP TABLE left `ops_audit_new` populated but rename failed because CLI didn't `.bail on` |
| 11:03 | Manual recovery (one-shot): `.load vec0.so + ALTER TABLE ops_audit_new RENAME TO ops_audit + CREATE INDEX` — all 56 rows recovered with INTEGER started_at |
| 11:08 | Cleanup script ran (post-migration, no triggers present) — DELETE 20 test-% rows, 36 remaining |
| 11:09 | `systemctl restart nox-mem-api` — triggers reinstalled via `ensureAuditTable()` |
| 11:09 | Validation: /api/health.opsAudit.total_24h = 1, no test-% rows, all 4 triggers present, trigger rejects TEXT inserts |
| 11:14 | Idempotency verified: both scripts detect no-op state and exit cleanly on re-run |

## Snapshots preserved

`/var/backups/nox-mem/pre-op/` (1.2GB each, 0600, 7d retention via cron):

- `migrate-opsaudit-startedat-int-main-20260521135341-...db` (pre-first-attempt)
- `migrate-opsaudit-startedat-int-main-20260521135848-...db` (pre-second-attempt)
- `migrate-opsaudit-startedat-20260521140248-...db` (pre-table-rebuild, the canonical pre-migration snapshot)
- `cleanup-test-ops-audit-20260521140836-...db` (pre-test-cleanup)

## Validation checklist

- [x] `typeof(started_at) = 'integer'` for ALL rows (36/36)
- [x] Column declared type = `INTEGER` (verified via `pragma_table_info`)
- [x] Zero `op_name LIKE 'test-%'` rows
- [x] All 4 expected triggers present
- [x] Trigger rejects TEXT INSERT (sanity test confirmed `SQLITE_CONSTRAINT_TRIGGER`)
- [x] withOpAudit INSERT with `CAST(? AS INTEGER)` succeeds (sanity row id=73 inserted, value=integer, then cleaned up)
- [x] /api/health.opsAudit shows realistic 24h count (total_24h=1, was 48)
- [x] Migration script idempotent (detects INTEGER column, exits)
- [x] Cleanup script idempotent (detects 0 test-% rows, exits)
- [x] nox-mem-api running, no crashes since restart (PID 1943170)

## Lessons cravadas

See `staged-1.7a/DEPLOY-OPSAUDIT-HYGIENE.md` for full text. TL;DR:

1. `.load vec0.so` is mandatory in any sqlite3 CLI session touching nox-mem.db schema.
2. TEXT column affinity coerces INTEGER values back to TEXT — full table rebuild required for typeof checks.
3. `sqlite3` CLI defaults `.bail off` — partial migrations possible; always `.bail on`.
4. better-sqlite3 binds JS `number` as REAL — wrap params in `CAST(? AS INTEGER)` for INTEGER columns with trigger checks.

## Cross-links

- `audits/2026-05-21-opsAudit-investigation.md` — origin investigation
- `[[withopaudit-trigger-raise-ignore-swallows-insert]]` — prior 2026-05-19 trigger fix
- `[[validate-features-with-db-not-logs]]` — same lesson again (DB declares one thing, code expects another)
