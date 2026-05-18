#!/usr/bin/env bash
# verify-audit-hardening.sh — G8: 5-step operational verification of audit DB hardening.
#
# Run after protect-audit-db.sh harden to confirm all controls are active.
# Designed for inclusion in the deployment checklist (DEPLOY-WAVE-B.md Phase G8).
#
# Exit code: 0 = all checks pass, 1 = one or more checks failed.

set -uo pipefail

NOX_WORKSPACE="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}"
DB_DIR="${NOX_WORKSPACE}/tools/nox-mem"
MAIN_DB="${DB_DIR}/nox-mem.db"
AUDIT_DB="${DB_DIR}/audit.db"

PASS=0
FAIL=0

check() {
  local desc="$1"
  local result="$2"  # "ok" or error message
  if [[ "$result" == "ok" ]]; then
    echo "  [PASS] $desc"
    ((PASS++)) || true
  else
    echo "  [FAIL] $desc — $result"
    ((FAIL++)) || true
  fi
}

echo ""
echo "=== G8: Audit DB Hardening Verification ==="
echo "    MAIN_DB:  $MAIN_DB"
echo "    AUDIT_DB: $AUDIT_DB"
echo ""

# ── Step 1: audit.db exists ────────────────────────────────────────────────────
if [[ -f "$AUDIT_DB" ]]; then
  check "Step 1: audit.db exists" "ok"
else
  check "Step 1: audit.db exists" "file not found at $AUDIT_DB"
fi

# ── Step 2: audit.db is immutable (+i) ────────────────────────────────────────
if [[ -f "$AUDIT_DB" ]]; then
  if lsattr "$AUDIT_DB" 2>/dev/null | grep -q '^....i'; then
    check "Step 2: audit.db has chattr +i (immutable)" "ok"
  else
    check "Step 2: audit.db has chattr +i (immutable)" "immutable flag not set — run: chattr +i $AUDIT_DB"
  fi
else
  check "Step 2: audit.db has chattr +i (immutable)" "skipped (file missing)"
fi

# ── Step 3: Both DBs are 0600 ─────────────────────────────────────────────────
for db_path in "$MAIN_DB" "$AUDIT_DB"; do
  db_name=$(basename "$db_path")
  if [[ -f "$db_path" ]]; then
    perms=$(stat -c '%a' "$db_path" 2>/dev/null || stat -f '%A' "$db_path" 2>/dev/null)
    if [[ "$perms" == "600" ]]; then
      check "Step 3: $db_name has 0600 perms" "ok"
    else
      check "Step 3: $db_name has 0600 perms" "got $perms — run: chmod 0600 $db_path"
    fi
  else
    check "Step 3: $db_name has 0600 perms" "skipped (file missing)"
  fi
done

# ── Step 4: ops_audit append-only trigger exists in audit.db ──────────────────
if [[ -f "$AUDIT_DB" ]]; then
  trigger_count=$(sqlite3 "$AUDIT_DB" \
    "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_ops_audit%'" 2>/dev/null || echo "0")
  if [[ "$trigger_count" -ge 2 ]]; then
    check "Step 4: ops_audit append-only triggers present ($trigger_count triggers)" "ok"
  else
    check "Step 4: ops_audit append-only triggers present" "found $trigger_count triggers (expected >= 2) — re-run protect-audit-db.sh harden"
  fi
else
  check "Step 4: ops_audit append-only triggers present" "skipped (audit.db missing)"
fi

# ── Step 5: rm attempt on audit.db is blocked ─────────────────────────────────
if [[ -f "$AUDIT_DB" ]]; then
  if [[ $EUID -eq 0 ]]; then
    # Try rm — should fail if +i is set
    if rm -f "$AUDIT_DB" 2>/dev/null; then
      # rm succeeded — +i not working
      check "Step 5: rm of audit.db is blocked by chattr +i" "CRITICAL: rm succeeded! Immutable flag not active. Re-apply: chattr +i $AUDIT_DB"
    else
      check "Step 5: rm of audit.db is blocked by chattr +i" "ok"
    fi
  else
    # Non-root: can't test rm, but check flag
    if lsattr "$AUDIT_DB" 2>/dev/null | grep -q '^....i'; then
      check "Step 5: rm of audit.db is blocked by chattr +i" "ok (inferred from +i flag; root test skipped)"
    else
      check "Step 5: rm of audit.db is blocked by chattr +i" "immutable flag not set (non-root; cannot test rm directly)"
    fi
  fi
else
  check "Step 5: rm of audit.db is blocked by chattr +i" "skipped (audit.db missing)"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "  ACTION REQUIRED: Run 'protect-audit-db.sh harden' to fix failures."
  exit 1
else
  echo "  All checks passed. Audit DB hardening is active."
  exit 0
fi
