#!/usr/bin/env bash
# protect-audit-db.sh — G8: Harden nox-mem audit DB against file-level deletion.
#
# Gap from THREAT-MODEL.md §8 / G8:
#   "SQL triggers prevent DELETE FROM ops_audit, but `rm nox-mem.db` or
#    `sed -i` bypasses. chattr +i not yet automated for audit DBs."
#
# What this script does:
#   1. Creates a dedicated audit.db (separate from nox-mem.db) via SQLite ATTACH.
#      ops_audit + confidence_eval_log → audit.db (main DB stays writable).
#   2. Sets 0600 perms on both nox-mem.db and audit.db.
#   3. Sets chattr +i (immutable) on audit.db to block rm/sed/overwrite.
#   4. Optionally removes +i for backup windows and restores after.
#
# Usage:
#   protect-audit-db.sh harden     — apply all hardening
#   protect-audit-db.sh unprotect  — temporarily remove +i (for backup)
#   protect-audit-db.sh reprotect  — re-apply +i after backup
#   protect-audit-db.sh status     — check current state
#
# Ref: THREAT-MODEL.md G8 (medium priority).
#      CLAUDE.md regra #6 (withOpAudit snapshot rules).
#      Lesson 2026-05-01 (sed -i on .db corrupts page boundaries).
#
# Prerequisites:
#   - e2fsprogs (chattr / lsattr) — installed on most Debian/Ubuntu VPS
#   - sqlite3 CLI
#   - Run as root (or with CAP_LINUX_IMMUTABLE capability)

set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────

NOX_WORKSPACE="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}"
DB_DIR="${NOX_WORKSPACE}/tools/nox-mem"
MAIN_DB="${DB_DIR}/nox-mem.db"
AUDIT_DB="${DB_DIR}/audit.db"
BACKUP_DIR="/var/backups/nox-mem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[info]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[ok]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
log_error()   { echo -e "${RED}[error]${NC} $*" >&2; }

# ─── Preflight checks ─────────────────────────────────────────────────────────

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (needs CAP_LINUX_IMMUTABLE for chattr +i)."
    exit 1
  fi
}

check_deps() {
  local missing=()
  for cmd in sqlite3 chattr lsattr; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Missing required commands: ${missing[*]}"
    log_error "Install with: apt-get install e2fsprogs sqlite3"
    exit 1
  fi
}

check_db_exists() {
  if [[ ! -f "$MAIN_DB" ]]; then
    log_error "Main DB not found: $MAIN_DB"
    log_error "Set OPENCLAW_WORKSPACE env var or check the path."
    exit 1
  fi
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

is_immutable() {
  local file="$1"
  [[ -f "$file" ]] && lsattr "$file" 2>/dev/null | grep -q '^....i'
}

remove_immutable() {
  local file="$1"
  if is_immutable "$file"; then
    chattr -i "$file"
    log_info "Removed immutable flag from $file"
  fi
}

set_immutable() {
  local file="$1"
  if ! is_immutable "$file"; then
    chattr +i "$file"
    log_ok "Set immutable flag (+i) on $file"
  else
    log_info "$file already immutable"
  fi
}

set_perms() {
  local file="$1"
  chmod 0600 "$file"
  chown root:root "$file" 2>/dev/null || true
  log_ok "Set 0600 root:root on $file"
}

# ─── Audit DB creation ────────────────────────────────────────────────────────

create_audit_db() {
  if [[ -f "$AUDIT_DB" ]]; then
    log_info "audit.db already exists at $AUDIT_DB"
    return 0
  fi

  log_info "Creating audit.db at $AUDIT_DB"

  # Create audit.db with ops_audit and confidence_eval_log attached
  # Note: we CREATE the tables in audit.db and then nox-mem should be
  # updated to ATTACH audit.db for audit operations.
  sqlite3 "$AUDIT_DB" <<'SQLEOF'
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

-- ops_audit table (mirrors schema in src/lib/op-audit.ts)
CREATE TABLE IF NOT EXISTS ops_audit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  op          TEXT    NOT NULL,
  started_at  INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
  ended_at    INTEGER,
  status      TEXT    NOT NULL DEFAULT 'started'
              CHECK (status IN ('started','success','failed','crashed')),
  snapshot_path TEXT,
  metadata    TEXT,
  error_msg   TEXT,
  pid         INTEGER NOT NULL DEFAULT 0,
  ran_by      TEXT    NOT NULL DEFAULT 'unknown'
);

-- Append-only trigger: block DELETE
CREATE TRIGGER IF NOT EXISTS trg_ops_audit_no_delete
  BEFORE DELETE ON ops_audit
  BEGIN
    SELECT RAISE(ABORT, 'ops_audit is append-only (CWE-693)');
  END;

-- Append-only trigger: block UPDATE of terminal rows
CREATE TRIGGER IF NOT EXISTS trg_ops_audit_no_update_terminal
  BEFORE UPDATE ON ops_audit
  WHEN OLD.status IN ('success', 'failed', 'crashed')
  BEGIN
    SELECT RAISE(ABORT, 'ops_audit: terminal rows are immutable');
  END;

-- confidence_eval_log (mirrors v22 migration)
CREATE TABLE IF NOT EXISTS confidence_eval_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id            TEXT NOT NULL,
  query_id          TEXT NOT NULL,
  variant           TEXT NOT NULL CHECK (variant IN ('A', 'B', 'C', 'D')),
  ndcg_at_10        REAL NOT NULL CHECK (ndcg_at_10 >= 0),
  delta_vs_baseline REAL NOT NULL,
  ran_at            TEXT NOT NULL,
  notes             TEXT,
  created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000)
);

CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_no_delete
  BEFORE DELETE ON confidence_eval_log
  BEGIN
    SELECT RAISE(ABORT, 'confidence_eval_log is append-only');
  END;

CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_no_update
  BEFORE UPDATE ON confidence_eval_log
  BEGIN
    SELECT RAISE(ABORT, 'confidence_eval_log is append-only');
  END;

PRAGMA user_version = 1;
SQLEOF

  log_ok "audit.db created at $AUDIT_DB"
}

# ─── Subcommands ──────────────────────────────────────────────────────────────

cmd_harden() {
  check_root
  check_deps
  check_db_exists

  log_info "=== G8: Hardening nox-mem audit DBs ==="
  log_info "Main DB:  $MAIN_DB"
  log_info "Audit DB: $AUDIT_DB"

  # Step 1: Create audit.db if needed
  create_audit_db

  # Step 2: Set 0600 perms on both DBs
  remove_immutable "$MAIN_DB"
  set_perms "$MAIN_DB"

  remove_immutable "$AUDIT_DB"
  set_perms "$AUDIT_DB"

  # Step 3: Apply chattr +i to audit.db (immutable — blocks rm/sed/overwrite)
  # Note: we do NOT apply +i to main DB because nox-mem needs to write it.
  set_immutable "$AUDIT_DB"

  # Step 4: Ensure backup dir has secure perms
  mkdir -p "$BACKUP_DIR"
  chmod 0700 "$BACKUP_DIR"
  log_ok "Backup dir secured: $BACKUP_DIR (0700)"

  log_info ""
  log_ok "=== Hardening complete ==="
  log_info "audit.db is now immutable. Use '$0 unprotect' before backups."
  log_info "Main DB is 0600 but NOT immutable (nox-mem needs write access)."
}

cmd_unprotect() {
  check_root
  check_deps

  if [[ ! -f "$AUDIT_DB" ]]; then
    log_warn "audit.db not found at $AUDIT_DB — nothing to unprotect."
    exit 0
  fi

  if is_immutable "$AUDIT_DB"; then
    chattr -i "$AUDIT_DB"
    log_ok "Removed +i from audit.db — safe to backup now."
    log_warn "Remember to run '$0 reprotect' after backup."
  else
    log_info "audit.db is not immutable — no action needed."
  fi
}

cmd_reprotect() {
  check_root
  check_deps

  if [[ ! -f "$AUDIT_DB" ]]; then
    log_error "audit.db not found at $AUDIT_DB"
    exit 1
  fi

  set_immutable "$AUDIT_DB"
  log_ok "audit.db is immutable again."
}

cmd_status() {
  check_deps

  echo ""
  echo "=== G8: nox-mem DB Hardening Status ==="
  echo ""

  for db_path in "$MAIN_DB" "$AUDIT_DB"; do
    if [[ ! -f "$db_path" ]]; then
      echo "  $(basename "$db_path"): NOT FOUND"
      continue
    fi

    local perms immutable
    perms=$(stat -c '%a %U:%G' "$db_path" 2>/dev/null || stat -f '%A %Su:%Sg' "$db_path" 2>/dev/null)
    if is_immutable "$db_path"; then
      immutable="YES (+i)"
    else
      immutable="no"
    fi

    echo "  $(basename "$db_path"):"
    echo "    Path:      $db_path"
    echo "    Perms:     $perms"
    echo "    Immutable: $immutable"
    echo ""
  done

  # Backup dir
  if [[ -d "$BACKUP_DIR" ]]; then
    local bperms
    bperms=$(stat -c '%a %U:%G' "$BACKUP_DIR" 2>/dev/null || stat -f '%A %Su:%Sg' "$BACKUP_DIR" 2>/dev/null)
    echo "  Backup dir: $BACKUP_DIR ($bperms)"
  else
    echo "  Backup dir: NOT FOUND ($BACKUP_DIR)"
  fi
  echo ""
}

# ─── Main ─────────────────────────────────────────────────────────────────────

COMMAND="${1:-help}"

case "$COMMAND" in
  harden)     cmd_harden ;;
  unprotect)  cmd_unprotect ;;
  reprotect)  cmd_reprotect ;;
  status)     cmd_status ;;
  help|--help|-h)
    echo "Usage: $0 {harden|unprotect|reprotect|status}"
    echo ""
    echo "  harden      Apply full hardening (create audit.db, 0600 perms, chattr +i)"
    echo "  unprotect   Temporarily remove +i from audit.db (before backup)"
    echo "  reprotect   Re-apply +i to audit.db (after backup)"
    echo "  status      Show current state of DBs"
    echo ""
    echo "Environment:"
    echo "  OPENCLAW_WORKSPACE  (default: /root/.openclaw/workspace)"
    exit 0
    ;;
  *)
    log_error "Unknown command: $COMMAND"
    echo "Run '$0 help' for usage."
    exit 1
    ;;
esac
