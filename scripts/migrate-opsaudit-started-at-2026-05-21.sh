#!/usr/bin/env bash
# scripts/migrate-opsaudit-started-at-2026-05-21.sh
#
# One-time migration: rebuild ops_audit with INTEGER started_at column.
#
# CONTEXT:
#   Prod ops_audit table was created with `started_at TEXT NOT NULL DEFAULT (datetime('now'))`
#   BEFORE the INTEGER-schema fix in src/lib/op-audit.ts (PR 2026-05-19). CREATE TABLE IF NOT
#   EXISTS in ensureAuditTable() did not migrate the existing table, so prod still holds
#   56 rows with mixed TEXT formats:
#     - 47 rows in ISO datetime TEXT ("2026-04-27 02:00:03")
#     -  9 rows in epoch-ms float-as-text ("1779242511707.0")
#
#   This breaks /api/health.opsAudit.total_24h which uses
#   `started_at >= strftime('%s','now','-24h') * 1000` — SQLite lexicographic compare keeps
#   April/May rows in the "24h" bucket forever (audit 2026-05-21).
#
# WHY TABLE REBUILD (not per-cell UPDATE):
#   The TEXT-affinity column coerces any INTEGER assignment back to TEXT (SQLite type affinity).
#   Even `UPDATE ... SET x = CAST(v AS INTEGER)` lands as TEXT in a TEXT column. The trigger
#   trg_ops_audit_started_at_must_be_int (Issue #1C) checks typeof(NEW.x) which sees the
#   post-affinity TEXT, blocking ANY future insert until the column declared type is INTEGER.
#
# WHAT THIS DOES:
#   1. Manual VACUUM INTO snapshot (cannot use withOpAudit — its own INSERT would be blocked
#      by the trigger that's already deployed in the new code path).
#   2. BEGIN TRANSACTION.
#   3. DROP all ops_audit triggers (no-delete + terminal-immutable + new int-must).
#   4. CREATE TABLE ops_audit_new with INTEGER started_at + INTEGER DEFAULT (strftime *1000).
#   5. INSERT INTO ops_audit_new SELECT ... with CASE-normalized started_at → INTEGER.
#   6. DROP TABLE ops_audit (its triggers are auto-dropped).
#   7. ALTER TABLE ops_audit_new RENAME TO ops_audit.
#   8. Recreate indexes.
#   9. COMMIT (atomic — partial failure rolls back fully).
#   10. Restart nox-mem-api so ensureAuditTable() reinstalls triggers idempotently.
#
# SAFETY:
#   - Manual VACUUM INTO snapshot in /var/backups/nox-mem/pre-op/migrate-opsaudit-...db
#   - Transaction atomic; ROLLBACK on any failure
#   - Recovery: stop services, cp snapshot.db nox-mem.db (WAL/SHM cleanup via safeRestore)
#
# Usage on VPS:
#   set -a; source /root/.openclaw/.env; set +a
#   bash /root/.openclaw/workspace/tools/nox-mem/scripts/migrate-opsaudit-started-at-2026-05-21.sh

set -euo pipefail

VPS_REPO="${VPS_REPO:-/root/.openclaw/workspace/tools/nox-mem}"
DB_PATH="${NOX_DB_PATH:-${VPS_REPO}/nox-mem.db}"
SNAPSHOT_DIR="${NOX_PRE_OP_SNAPSHOT_DIR:-/var/backups/nox-mem/pre-op}"

cd "$VPS_REPO"

echo "==> Migration: ops_audit.started_at TEXT → INTEGER (table rebuild)"
echo "    DB:        $DB_PATH"
echo "    Snapshot:  $SNAPSHOT_DIR"
echo "    Date:      $(date -Iseconds)"
echo ""

# Locate vec0 extension early — chunks table has trg_chunks_delete_cascade that references
# vec0 module functions; SQLite parses ALL triggers during schema-touching operations
# (DROP TABLE, ALTER TABLE) so the extension must be loaded into every sqlite3 CLI session.
VEC0_SO="${VEC0_SO:-${VPS_REPO}/node_modules/sqlite-vec-linux-x64/vec0.so}"
if [ ! -f "$VEC0_SO" ]; then
  echo "✗ vec0 extension not found at $VEC0_SO — set VEC0_SO env to override"
  exit 6
fi

# ─── 1. Pre-flight counts ──────────────────────────────────────────────────────
echo "── Pre-migration state ──"
sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.headers on
.mode column
SELECT typeof(started_at) AS type, COUNT(*) AS count FROM ops_audit GROUP BY 1;
SELECT 'iso_format' AS bucket, COUNT(*) AS count
  FROM ops_audit WHERE typeof(started_at) = 'text' AND started_at LIKE '____-__-__%'
UNION ALL
SELECT 'numeric_text' AS bucket, COUNT(*)
  FROM ops_audit WHERE typeof(started_at) = 'text' AND started_at NOT LIKE '____-__-__%'
UNION ALL
SELECT 'integer' AS bucket, COUNT(*)
  FROM ops_audit WHERE typeof(started_at) = 'integer';
SQL

BEFORE_TOTAL=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit")
BEFORE_NON_INT=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit WHERE typeof(started_at) != 'integer'")

echo ""
echo "    Total rows:       $BEFORE_TOTAL"
echo "    Non-INTEGER rows: $BEFORE_NON_INT"
echo ""

# Detect declared column type (TEXT means we need a rebuild; INTEGER means we're done).
COL_TYPE=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT type FROM pragma_table_info('ops_audit') WHERE name='started_at'")
echo "    Declared column type: $COL_TYPE"
echo ""

if [ "$COL_TYPE" = "INTEGER" ] && [ "$BEFORE_NON_INT" = "0" ]; then
  echo "    ✓ Column already INTEGER and all values INTEGER — migration is a no-op. Exiting."
  exit 0
fi

# ─── 2. Manual VACUUM INTO snapshot ────────────────────────────────────────────
echo "── Creating manual VACUUM INTO snapshot ──"
TS=$(date -u +%Y%m%d%H%M%S)
PID=$$
UUID=$(cat /proc/sys/kernel/random/uuid | head -c 8)
SNAPSHOT_PATH="${SNAPSHOT_DIR}/migrate-opsaudit-startedat-${TS}-${PID}-${UUID}.db"
mkdir -p "$SNAPSHOT_DIR"
chmod 0700 "$SNAPSHOT_DIR" || true

sqlite3 "$DB_PATH" "VACUUM INTO '${SNAPSHOT_PATH}'"
chmod 0600 "$SNAPSHOT_PATH"

# Integrity check the snapshot
INTEGRITY=$(sqlite3 "$SNAPSHOT_PATH" "PRAGMA integrity_check" | head -1)
if [ "$INTEGRITY" != "ok" ]; then
  echo "✗ Snapshot integrity_check failed: $INTEGRITY"
  rm -f "$SNAPSHOT_PATH"
  exit 2
fi

SNAPSHOT_SIZE=$(stat -c%s "$SNAPSHOT_PATH")
echo "    Snapshot OK: $SNAPSHOT_PATH ($SNAPSHOT_SIZE bytes)"
echo ""

# ─── 3. Run the migration in one atomic transaction ────────────────────────────
echo "── Running table rebuild (atomic transaction) ──"

# .bail on stops at first error — without it, sqlite3 CLI continues past failures and
# can leave the schema in a partial state (lesson from 2026-05-21 manual recovery).
sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.bail on
BEGIN IMMEDIATE;

-- Step 1: drop ALL triggers on ops_audit. They'll be reinstalled by ensureAuditTable
-- on next nox-mem-api startup (idempotent CREATE TRIGGER IF NOT EXISTS).
DROP TRIGGER IF EXISTS trg_ops_audit_no_delete;
DROP TRIGGER IF EXISTS trg_ops_audit_terminal_immutable;
DROP TRIGGER IF EXISTS trg_ops_audit_started_at_must_be_int;
DROP TRIGGER IF EXISTS trg_ops_audit_started_at_must_be_int_upd;
-- Pre-PR-2026-05-19 leftovers (may not exist; IF EXISTS safe).
DROP TRIGGER IF EXISTS trg_ops_audit_started_at_server_side;
DROP TRIGGER IF EXISTS trg_ops_audit_force_started_at;

-- Step 2: create the new table with INTEGER started_at + INTEGER DEFAULT.
-- Schema MUST match ensureAuditTable() definition in src/lib/op-audit.ts exactly.
CREATE TABLE ops_audit_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  op_name TEXT NOT NULL,
  started_at INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
  finished_at TEXT,
  duration_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'running',
  affected_rows INTEGER,
  snapshot_path TEXT,
  snapshot_bytes INTEGER,
  schema_user_version INTEGER,
  pid INTEGER,
  error_message TEXT,
  notes TEXT,
  db_source TEXT NOT NULL DEFAULT 'unknown',
  db_path TEXT NOT NULL DEFAULT 'unknown',
  last_heartbeat_at TEXT
);

-- Step 3: copy data with CASE-normalized started_at → INTEGER epoch ms.
-- ISO datetime "YYYY-MM-DD HH:MM:SS" → strftime('%s', ...) * 1000
-- Float-as-text "1779242511707.0"     → CAST(... AS INTEGER) (truncates fraction)
-- Already-integer (none expected)     → pass through
-- Sequence preserves: id, op_name, finished_at, duration_ms, status, affected_rows,
-- snapshot_path, snapshot_bytes, schema_user_version, pid, error_message, notes,
-- db_source (COALESCE NULL→'unknown' for legacy rows), db_path, last_heartbeat_at.
INSERT INTO ops_audit_new (
  id, op_name, started_at, finished_at, duration_ms, status, affected_rows,
  snapshot_path, snapshot_bytes, schema_user_version, pid, error_message, notes,
  db_source, db_path, last_heartbeat_at
)
SELECT
  id, op_name,
  CASE
    WHEN typeof(started_at) = 'integer' THEN started_at
    WHEN started_at LIKE '____-__-__%' THEN strftime('%s', started_at) * 1000
    ELSE CAST(started_at AS INTEGER)
  END AS started_at,
  finished_at, duration_ms, status, affected_rows,
  snapshot_path, snapshot_bytes, schema_user_version, pid, error_message, notes,
  COALESCE(db_source, 'unknown'), COALESCE(db_path, 'unknown'), last_heartbeat_at
FROM ops_audit;

-- Step 4: drop the old table (its triggers were dropped above).
DROP TABLE ops_audit;

-- Step 5: rename new → ops_audit.
ALTER TABLE ops_audit_new RENAME TO ops_audit;

-- Step 6: recreate indexes (triggers will be reinstalled by ensureAuditTable on API restart).
CREATE INDEX IF NOT EXISTS idx_ops_audit_started ON ops_audit(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ops_audit_status ON ops_audit(status, started_at DESC);

COMMIT;
SQL

# ─── 4. Post-migration validation ──────────────────────────────────────────────
echo ""
echo "── Post-migration state ──"
sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.headers on
.mode column
SELECT typeof(started_at) AS type, COUNT(*) AS count FROM ops_audit GROUP BY 1;
SQL

AFTER_TOTAL=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit")
AFTER_NON_INT=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit WHERE typeof(started_at) != 'integer'")
AFTER_COL_TYPE=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT type FROM pragma_table_info('ops_audit') WHERE name='started_at'")

echo ""
echo "    Total rows:           $AFTER_TOTAL (was $BEFORE_TOTAL)"
echo "    Non-INTEGER rows:     $AFTER_NON_INT (was $BEFORE_NON_INT)"
echo "    Declared column type: $AFTER_COL_TYPE (was $COL_TYPE)"
echo "    Snapshot:             $SNAPSHOT_PATH"
echo ""

if [ "$AFTER_TOTAL" != "$BEFORE_TOTAL" ]; then
  echo "✗ FAIL: row count drift ($BEFORE_TOTAL → $AFTER_TOTAL)"
  exit 3
fi

if [ "$AFTER_NON_INT" != "0" ]; then
  echo "✗ FAIL: $AFTER_NON_INT rows still non-INTEGER"
  exit 4
fi

if [ "$AFTER_COL_TYPE" != "INTEGER" ]; then
  echo "✗ FAIL: column type is $AFTER_COL_TYPE, expected INTEGER"
  exit 5
fi

echo "✓ Migration successful: $AFTER_TOTAL rows, all INTEGER, column type=INTEGER"
echo ""
echo "Next:"
echo "  1. Run cleanup-test-ops-audit-2026-05-21.sh (removes 20 historical test-% rows)"
echo "  2. systemctl restart nox-mem-api  (reinstalls triggers via ensureAuditTable)"
echo "  3. Verify: curl /api/health | jq .opsAudit"
