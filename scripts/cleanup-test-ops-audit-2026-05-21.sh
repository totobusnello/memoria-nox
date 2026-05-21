#!/usr/bin/env bash
# scripts/cleanup-test-ops-audit-2026-05-21.sh
#
# One-time cleanup: remove test ops (op_name LIKE 'test-%') from ops_audit.
#
# CONTEXT:
#   Test fixtures invoking withOpAudit() populated the real ops_audit table without
#   isolation. Per audit 2026-05-21 (Issue #3), 20 historical test rows pollute
#   /api/health.opsAudit byDbSource=unknown bucket. The reporting filter
#   (op_name NOT LIKE 'test-%') in src/lib/op-audit.ts:getOpAuditStats handles new
#   ingest, but historical rows still occupy storage and break ad-hoc queries.
#
# RUN ORDER:
#   This MUST run AFTER migrate-opsaudit-started-at-2026-05-21.sh and BEFORE
#   `systemctl restart nox-mem-api`. The migration drops all triggers and leaves
#   the table trigger-less; this script does the DELETE while triggers are absent,
#   then the API restart reinstalls them idempotently via ensureAuditTable().
#
# WHAT THIS DOES:
#   1. Detects whether trg_ops_audit_no_delete is present (post-migration: no).
#      - If present: snapshot via withOpAudit, drop trigger inside txn, DELETE,
#        recreate trigger, COMMIT.
#      - If absent: manual VACUUM INTO snapshot, then plain DELETE.
#   2. Validates: zero test-% rows remain.
#
# SAFETY:
#   - Pre-op snapshot in /var/backups/nox-mem/pre-op/
#   - Atomic transaction
#   - Recovery: safeRestore('/var/backups/nox-mem/pre-op/<latest>.db')
#
# Note: this is the ONE LEGITIMATE break in the append-only invariant. The append-only
# guarantee exists to prevent a compromised CLI from erasing its trail; test rows
# never had legitimate audit value (they're test fixtures), so cleaning them is
# an integrity REPAIR, not a CWE-693 violation.
#
# Usage on VPS:
#   set -a; source /root/.openclaw/.env; set +a
#   bash /root/.openclaw/workspace/tools/nox-mem/scripts/cleanup-test-ops-audit-2026-05-21.sh

set -euo pipefail

VPS_REPO="${VPS_REPO:-/root/.openclaw/workspace/tools/nox-mem}"
DB_PATH="${NOX_DB_PATH:-${VPS_REPO}/nox-mem.db}"
SNAPSHOT_DIR="${NOX_PRE_OP_SNAPSHOT_DIR:-/var/backups/nox-mem/pre-op}"

cd "$VPS_REPO"

echo "==> Cleanup: ops_audit test-% rows"
echo "    DB:        $DB_PATH"
echo "    Date:      $(date -Iseconds)"
echo ""

# Locate vec0 extension — chunks table triggers reference it, must be loaded in every
# sqlite3 CLI session that touches schema or runs in same DB.
VEC0_SO="${VEC0_SO:-${VPS_REPO}/node_modules/sqlite-vec-linux-x64/vec0.so}"
if [ ! -f "$VEC0_SO" ]; then
  echo "✗ vec0 extension not found at $VEC0_SO — set VEC0_SO env to override"
  exit 6
fi

# ─── 1. Pre-flight counts ──────────────────────────────────────────────────────
echo "── Pre-cleanup state ──"
sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.headers on
.mode column
SELECT op_name, status, COUNT(*) AS count
FROM ops_audit
WHERE op_name LIKE 'test-%'
GROUP BY 1, 2
ORDER BY 1, 2;
SQL

BEFORE_TEST=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit WHERE op_name LIKE 'test-%'")
BEFORE_TOTAL=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit")

echo ""
echo "    Test rows:  $BEFORE_TEST"
echo "    Total rows: $BEFORE_TOTAL"
echo ""

if [ "$BEFORE_TEST" = "0" ]; then
  echo "    ✓ No test-% rows — cleanup is a no-op. Exiting."
  exit 0
fi

# ─── 2. Detect trigger state ───────────────────────────────────────────────────
HAS_NO_DELETE_TRIGGER=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='trg_ops_audit_no_delete'")
echo "    no-delete trigger present: $HAS_NO_DELETE_TRIGGER"
echo ""

# ─── 3. Manual VACUUM INTO snapshot ────────────────────────────────────────────
echo "── Creating manual VACUUM INTO snapshot ──"
TS=$(date -u +%Y%m%d%H%M%S)
PID=$$
UUID=$(cat /proc/sys/kernel/random/uuid | head -c 8)
SNAPSHOT_PATH="${SNAPSHOT_DIR}/cleanup-test-ops-audit-${TS}-${PID}-${UUID}.db"
mkdir -p "$SNAPSHOT_DIR"
chmod 0700 "$SNAPSHOT_DIR" || true

sqlite3 "$DB_PATH" "VACUUM INTO '${SNAPSHOT_PATH}'"
chmod 0600 "$SNAPSHOT_PATH"

INTEGRITY=$(sqlite3 "$SNAPSHOT_PATH" "PRAGMA integrity_check" | head -1)
if [ "$INTEGRITY" != "ok" ]; then
  echo "✗ Snapshot integrity_check failed: $INTEGRITY"
  rm -f "$SNAPSHOT_PATH"
  exit 2
fi

SNAPSHOT_SIZE=$(stat -c%s "$SNAPSHOT_PATH")
echo "    Snapshot OK: $SNAPSHOT_PATH ($SNAPSHOT_SIZE bytes)"
echo ""

# ─── 4. Run the cleanup ────────────────────────────────────────────────────────
echo "── Running cleanup ──"

if [ "$HAS_NO_DELETE_TRIGGER" = "1" ]; then
  # Trigger present: must toggle inside a transaction.
  sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.bail on
BEGIN IMMEDIATE;
DROP TRIGGER IF EXISTS trg_ops_audit_no_delete;
DELETE FROM ops_audit WHERE op_name LIKE 'test-%';
CREATE TRIGGER IF NOT EXISTS trg_ops_audit_no_delete
  BEFORE DELETE ON ops_audit
  BEGIN SELECT RAISE(ABORT, 'ops_audit is append-only (CWE-693 protection)'); END;
COMMIT;
SQL
else
  # Trigger absent (post-migration): plain DELETE works.
  sqlite3 "$DB_PATH" <<SQL
.load $VEC0_SO
.bail on
BEGIN IMMEDIATE;
DELETE FROM ops_audit WHERE op_name LIKE 'test-%';
COMMIT;
SQL
fi

# ─── 5. Post-cleanup validation ────────────────────────────────────────────────
echo ""
echo "── Post-cleanup state ──"
AFTER_TEST=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit WHERE op_name LIKE 'test-%'")
AFTER_TOTAL=$(sqlite3 "$DB_PATH" ".load $VEC0_SO" "SELECT COUNT(*) FROM ops_audit")

echo "    Test rows:  $AFTER_TEST (was $BEFORE_TEST)"
echo "    Total rows: $AFTER_TOTAL (was $BEFORE_TOTAL)"
echo "    Snapshot:   $SNAPSHOT_PATH"
echo ""

if [ "$AFTER_TEST" != "0" ]; then
  echo "✗ FAIL: $AFTER_TEST test rows still present"
  exit 3
fi

EXPECTED_AFTER=$((BEFORE_TOTAL - BEFORE_TEST))
if [ "$AFTER_TOTAL" != "$EXPECTED_AFTER" ]; then
  echo "✗ FAIL: row count drift — expected $EXPECTED_AFTER, got $AFTER_TOTAL"
  exit 4
fi

echo "✓ Cleanup successful: removed $BEFORE_TEST test-% rows"
echo ""
echo "Next:"
echo "  - systemctl restart nox-mem-api (reinstalls all triggers idempotently)"
echo "  - Verify: curl /api/health | jq .opsAudit"
