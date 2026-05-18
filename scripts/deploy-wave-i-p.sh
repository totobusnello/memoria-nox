#!/usr/bin/env bash
# deploy-wave-i-p.sh — Idempotent rsync deploy for Wave I+P staged dirs
#
# Modes:
#   default (no flags)  : DRY-RUN — shows what would change, no mutations
#   --apply             : APPLY — rsync real, requires dry-run within last 5 min
#   --validate          : VALIDATE — post-deploy health checks only
#
# Usage:
#   ./scripts/deploy-wave-i-p.sh               # dry-run
#   ./scripts/deploy-wave-i-p.sh --apply       # apply (after dry-run)
#   ./scripts/deploy-wave-i-p.sh --validate    # validate VPS state
#
# Dirs NOT touched by this script (per spec):
#   staged-1.6/, staged-1.7a/, staged-1.8/     — apply LAST with care
#   staged-migrations/                          — v11/v23/v24 already applied
#   staged-P5/, staged-P3/, staged-P1/          — handlers on VPS, only wire-up missing
#
# Author: auto-generated 2026-05-18

set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
VPS_HOST="root@187.77.234.79"
VPS_NX="/root/.openclaw/workspace/tools/nox-mem"
VPS_BACKUP_DIR="/var/backups/nox-mem/pre-op"
VPS_LOG="/var/log/nox-mem-deploy-wave-i-p.log"
VPS_API="http://127.0.0.1:18802"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="/tmp/nox-mem-wave-i-p-dryrun.lock"
LOCK_MAX_AGE_SECONDS=300   # 5 minutes

# ---------------------------------------------------------------------------
# COLOR HELPERS
# ---------------------------------------------------------------------------
RED='\033[0;31m'
YLW='\033[0;33m'
GRN='\033[0;32m'
BLU='\033[0;34m'
CYN='\033[0;36m'
RST='\033[0m'
BOLD='\033[1m'

log()       { echo -e "${BLU}[INFO]${RST}  $*"; }
warn()      { echo -e "${YLW}[WARN]${RST}  $*"; }
error()     { echo -e "${RED}[ERROR]${RST} $*" >&2; }
success()   { echo -e "${GRN}[OK]${RST}    $*"; }
header()    { echo -e "\n${BOLD}${CYN}=== $* ===${RST}"; }

die() { error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# MODE DETECTION
# ---------------------------------------------------------------------------
MODE="dryrun"
for arg in "$@"; do
  case "$arg" in
    --apply)    MODE="apply" ;;
    --validate) MODE="validate" ;;
    --help|-h)
      sed -n '/^# /p' "$0" | head -20
      exit 0
      ;;
    *) die "Unknown flag: $arg. Use --apply, --validate, or no flags for dry-run." ;;
  esac
done

# ---------------------------------------------------------------------------
# PRE-FLIGHT CHECKS (required for dry-run + apply; skipped for validate-only)
# ---------------------------------------------------------------------------
preflight_checks() {
  header "PRE-FLIGHT CHECKS"

  # 1. SSH connectivity
  log "Checking SSH connectivity to VPS..."
  if ssh -o ConnectTimeout=10 -o BatchMode=yes "$VPS_HOST" echo OK 2>/dev/null; then
    success "SSH OK"
  else
    die "Cannot reach VPS via SSH ($VPS_HOST). Aborting."
  fi

  # 2. nox-mem API health
  log "Checking nox-mem API health..."
  local schema_ver
  schema_ver=$(ssh "$VPS_HOST" "curl -sf ${VPS_API}/api/health | jq -r '.schemaVersion // empty'" 2>/dev/null) || true
  if [[ -z "$schema_ver" ]]; then
    die "nox-mem API not responding at ${VPS_API}/api/health on VPS. Service may be down."
  fi
  success "API OK — schemaVersion=${schema_ver}"

  # 3. Free disk on backup dir
  log "Checking free disk space on VPS /var/backups..."
  local free_kb
  free_kb=$(ssh "$VPS_HOST" "df -k /var/backups | awk 'NR==2{print \$4}'" 2>/dev/null) || free_kb=0
  local free_gb=$(( free_kb / 1048576 ))
  if (( free_kb < 5242880 )); then  # < 5 GB
    die "Insufficient disk space on VPS /var/backups: ${free_gb}GB available (need ≥5GB)."
  fi
  success "Disk OK — ${free_gb}GB free on /var/backups"

  # 4. Pre-existing snapshot check (advisory only for dry-run, required for apply)
  log "Looking for pre-op snapshot..."
  local snapshot
  snapshot=$(ssh "$VPS_HOST" "ls ${VPS_BACKUP_DIR}/wave-i-p-deploy-*.db 2>/dev/null | tail -1") || snapshot=""
  if [[ -n "$snapshot" ]]; then
    success "Snapshot found: $snapshot"
  else
    if [[ "$MODE" == "apply" ]]; then
      warn "No wave-i-p-deploy-* snapshot found in ${VPS_BACKUP_DIR}."
      warn "A fresh snapshot will be created before apply begins."
    else
      warn "No snapshot yet (expected — run --apply to create one)."
    fi
  fi

  echo ""
}

# ---------------------------------------------------------------------------
# SNAPSHOT CREATION ON VPS
# ---------------------------------------------------------------------------
create_snapshot() {
  local label="${1:-wave-i-p-deploy}"
  local ts
  ts=$(date -u +%Y%m%d-%H%M%S)
  local snap_path="${VPS_BACKUP_DIR}/${label}-${ts}-$$.db"

  header "CREATING SNAPSHOT"
  log "Snapshot path: $snap_path"

  ssh "$VPS_HOST" bash -s -- "$snap_path" "$VPS_NX" <<'ENDSSH'
    snap_path="$1"
    vps_nx="$2"
    db_path="${vps_nx}/data/nox-mem.db"
    snap_dir="$(dirname "$snap_path")"

    mkdir -p "$snap_dir"
    chmod 0700 "$snap_dir"

    if [[ ! -f "$db_path" ]]; then
      echo "ERROR: DB not found at $db_path" >&2
      exit 1
    fi

    # VACUUM INTO creates a clean, consistent snapshot
    sqlite3 "$db_path" "VACUUM INTO '${snap_path}';"
    chmod 0600 "$snap_path"
    echo "Snapshot created: $snap_path ($(du -sh "$snap_path" | cut -f1))"
ENDSSH

  success "Snapshot created: $snap_path"
  LAST_SNAPSHOT="$snap_path"
}

# ---------------------------------------------------------------------------
# DEPLOY TABLE — maps local staged path → VPS destination
# Each entry: "LOCAL_EDITS_SUBPATH|VPS_DEST|MODE|INCLUDE_FILTER"
#   MODE: new_only (--ignore-existing), merge (default rsync), specific_files
#   INCLUDE_FILTER: rsync --include/--exclude patterns or "all"
# ---------------------------------------------------------------------------
# Ordered by priority (privacy → cors → wire-up-adapters → G* → prometheus)
declare -a DEPLOY_TABLE=(
  # --- PRIVACY ---
  "staged-privacy/edits/privacy|${VPS_NX}/src/privacy|merge|all"

  # --- CORS ---
  "staged-cors/edits/src/api/cors.ts|${VPS_NX}/src/api/cors.ts|file|all"
  "staged-cors/edits/src/api/__tests__/cors.test.ts|${VPS_NX}/src/api/__tests__/cors.test.ts|file|all"

  # --- WIRE-UP ADAPTERS: src/api (only new server-deps-*.ts + health-confidence-adapter.ts) ---
  "staged-wire-up-adapters/edits/src/api/server-deps-a2.ts|${VPS_NX}/src/api/server-deps-a2.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/server-deps-l2-l3.ts|${VPS_NX}/src/api/server-deps-l2-l3.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/server-deps-p1.ts|${VPS_NX}/src/api/server-deps-p1.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/server-deps-p2.ts|${VPS_NX}/src/api/server-deps-p2.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/server-deps-p5.ts|${VPS_NX}/src/api/server-deps-p5.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/health-confidence-adapter.ts|${VPS_NX}/src/api/health-confidence-adapter.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/__tests__/server-deps-a2.test.ts|${VPS_NX}/src/api/__tests__/server-deps-a2.test.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/__tests__/server-deps-l2-l3.test.ts|${VPS_NX}/src/api/__tests__/server-deps-l2-l3.test.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/__tests__/server-deps-p1.test.ts|${VPS_NX}/src/api/__tests__/server-deps-p1.test.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/__tests__/server-deps-p2.test.ts|${VPS_NX}/src/api/__tests__/server-deps-p2.test.ts|file|all"
  "staged-wire-up-adapters/edits/src/api/__tests__/server-deps-p5.test.ts|${VPS_NX}/src/api/__tests__/server-deps-p5.test.ts|file|all"

  # --- WIRE-UP ADAPTERS: src/lib (new dirs only — do NOT overwrite existing) ---
  "staged-wire-up-adapters/edits/src/lib/deps|${VPS_NX}/src/lib/deps|new_only|all"
  "staged-wire-up-adapters/edits/src/lib/viewer/broadcast-singleton.ts|${VPS_NX}/src/lib/viewer/broadcast-singleton.ts|file|all"
  "staged-wire-up-adapters/edits/src/lib/confidence/db-shim-singleton.ts|${VPS_NX}/src/lib/confidence/db-shim-singleton.ts|file|all"
  "staged-wire-up-adapters/edits/src/lib/archive/server-deps.ts|${VPS_NX}/src/lib/archive/server-deps.ts|file|all"
  "staged-wire-up-adapters/edits/src/lib/conflict/db-singleton.ts|${VPS_NX}/src/lib/conflict/db-singleton.ts|file|all"
  "staged-wire-up-adapters/edits/src/lib/hooks/server-deps.ts|${VPS_NX}/src/lib/hooks/server-deps.ts|file|all"

  # --- G4: input validation ---
  "staged-G4/edits/src/api/answer.ts|${VPS_NX}/src/api/answer.ts|file|all"
  "staged-G4/edits/src/api/answer.validate-patch.ts|${VPS_NX}/src/api/answer.validate-patch.ts|file|all"
  "staged-G4/edits/src/api/__tests__/validate.test.ts|${VPS_NX}/src/api/__tests__/validate.test.ts|file|all"

  # --- G5: error sanitizer ---
  "staged-G5/edits/src/lib/error-sanitizer|${VPS_NX}/src/lib/error-sanitizer|merge|all"
  "staged-G5/edits/scripts/audit-stack-leak.sh|${VPS_NX}/scripts/audit-stack-leak.sh|file|all"

  # --- G6: localhost auth guard ---
  "staged-G6/edits/src/lib/auth|${VPS_NX}/src/lib/auth|merge|all"

  # --- G7: streaming memory unpack ---
  "staged-G7/edits/src/lib/archive/unpack-streaming.ts|${VPS_NX}/src/lib/archive/unpack-streaming.ts|file|all"
  "staged-G7/edits/src/lib/archive/__tests__/streaming-memory.test.ts|${VPS_NX}/src/lib/archive/__tests__/streaming-memory.test.ts|file|all"

  # --- G8: audit DB hardening scripts ---
  "staged-G8/edits/scripts/protect-audit-db.sh|${VPS_NX}/scripts/protect-audit-db.sh|file|all"
  "staged-G8/edits/scripts/verify-audit-hardening.sh|${VPS_NX}/scripts/verify-audit-hardening.sh|file|all"

  # --- G10: op-audit extension (ran-at guard) — migration SQL NOT included (already applied) ---
  "staged-G10/edits/src/lib/op-audit-extension|${VPS_NX}/src/lib/op-audit-extension|merge|all"

  # --- G11: events-stream-limited ---
  "staged-G11/edits/src/api/events-stream-limited.ts|${VPS_NX}/src/api/events-stream-limited.ts|file|all"
  "staged-G11/edits/src/lib/viewer/__tests__/events-stream-limited.test.ts|${VPS_NX}/src/lib/viewer/__tests__/events-stream-limited.test.ts|file|all"

  # --- G12: safe error message ---
  "staged-G12/edits/src/lib/api|${VPS_NX}/src/lib/api|merge|all"

  # --- G13: rate-limit dry-run fix ---
  "staged-G13/edits/src/lib/hooks/rate-limit-dryrun-fix.ts|${VPS_NX}/src/lib/hooks/rate-limit-dryrun-fix.ts|file|all"
  "staged-G13/edits/src/lib/hooks/__tests__/rate-limit-dryrun.test.ts|${VPS_NX}/src/lib/hooks/__tests__/rate-limit-dryrun.test.ts|file|all"

  # --- G14: v24 migration SQL — SKIP (already applied per spec) ---
  # (migration files intentionally excluded)
  "staged-G14/edits/__tests__/v24-triggers.test.ts|${VPS_NX}/__tests__/v24-triggers.test.ts|file|all"

  # --- G15: conflict audit FK check ---
  "staged-G15/edits/src/lib/conflict|${VPS_NX}/src/lib/conflict|merge|all"

  # --- G16: export locking ---
  "staged-G16/edits/src/lib/archive/export-locking.ts|${VPS_NX}/src/lib/archive/export-locking.ts|file|all"
  "staged-G16/edits/src/lib/archive/__tests__/export-locking.test.ts|${VPS_NX}/src/lib/archive/__tests__/export-locking.test.ts|file|all"

  # --- G17: rate-limit constant time ---
  "staged-G17/edits/src/lib/hooks/rate-limit-constant-time.ts|${VPS_NX}/src/lib/hooks/rate-limit-constant-time.ts|file|all"
  "staged-G17/edits/src/lib/hooks/__tests__/rate-limit-constant-time.test.ts|${VPS_NX}/src/lib/hooks/__tests__/rate-limit-constant-time.test.ts|file|all"

  # --- PROMETHEUS: observability ---
  "staged-prometheus/edits/src/observability|${VPS_NX}/src/observability|merge|all"
)

# ---------------------------------------------------------------------------
# BUILD RSYNC ARGS FOR AN ENTRY
# ---------------------------------------------------------------------------
# Returns rsync args array (minus src/dst)
build_rsync_args() {
  local mode="$1"
  local is_dry="$2"  # "yes" or "no"

  local args=(-avz --checksum)

  if [[ "$is_dry" == "yes" ]]; then
    args+=(-n)
  fi

  case "$mode" in
    new_only)
      args+=(--ignore-existing)
      ;;
    file)
      # single-file copy — handled separately
      ;;
    merge)
      # default: overwrite with checksumming
      ;;
  esac

  echo "${args[@]}"
}

# ---------------------------------------------------------------------------
# DRY-RUN SUMMARY
# ---------------------------------------------------------------------------
run_dryrun() {
  header "DRY-RUN MODE — no files will be modified"
  echo "  Scanning ${#DEPLOY_TABLE[@]} deploy entries..."
  echo ""

  local total_new=0
  local total_modified=0
  local total_bytes=0
  local entry_num=0

  for entry in "${DEPLOY_TABLE[@]}"; do
    IFS='|' read -r local_rel vps_dest mode _filter <<< "$entry"
    local local_abs="${REPO_ROOT}/${local_rel}"
    entry_num=$(( entry_num + 1 ))

    if [[ ! -e "$local_abs" ]]; then
      warn "  [${entry_num}] MISSING locally: ${local_rel} — skipping"
      continue
    fi

    echo -e "  ${BOLD}[${entry_num}]${RST} ${local_rel}"
    echo "       → ${vps_dest}"
    echo "       mode: ${mode}"

    # For 'file' mode, determine src/dst correctly
    if [[ "$mode" == "file" ]]; then
      # Single file copy
      local vps_dir
      vps_dir=$(dirname "$vps_dest")
      local rsync_out
      rsync_out=$(rsync -avzn --checksum \
        -e "ssh -o BatchMode=yes" \
        "$local_abs" \
        "${VPS_HOST}:${vps_dest}" 2>&1) || true
    else
      # Directory copy
      local rsync_out
      local extra_args=()
      [[ "$mode" == "new_only" ]] && extra_args+=(--ignore-existing)

      rsync_out=$(rsync -avzn --checksum "${extra_args[@]}" \
        -e "ssh -o BatchMode=yes" \
        "${local_abs}/" \
        "${VPS_HOST}:${vps_dest}/" 2>&1) || true
    fi

    # Parse rsync output
    local new_files
    new_files=$(echo "$rsync_out" | grep -E '^[^.][^f].*\.(ts|js|sql|sh|md)$' | wc -l | tr -d ' ')
    local total_line
    total_line=$(echo "$rsync_out" | grep "Total transferred" | head -1 || echo "")
    local sent_bytes
    sent_bytes=$(echo "$rsync_out" | grep "sent " | awk '{print $2}' | head -1 || echo "0")

    # Files that would be sent (non-zero transfer in dry-run)
    local would_transfer
    would_transfer=$(echo "$rsync_out" | grep -v '^$' | grep -v '^sending\|^sent\|^total\|^\./' | grep -E '\.(ts|js|sql|sh|md|json)' || echo "(none)")

    if [[ "$would_transfer" != "(none)" && -n "$would_transfer" ]]; then
      echo "       would transfer:"
      echo "$would_transfer" | sed 's/^/         /'
      total_new=$(( total_new + $(echo "$would_transfer" | wc -l | tr -d ' ') ))
    else
      echo "       (no changes — already in sync)"
    fi
    echo ""
  done

  echo ""
  echo -e "${BOLD}Dry-run summary:${RST}"
  echo "  Entries scanned : ${#DEPLOY_TABLE[@]}"
  echo "  Files to deploy : ~${total_new} (unique across entries)"
  echo ""
  echo -e "${YLW}To apply these changes, run:${RST}"
  echo "  ./scripts/deploy-wave-i-p.sh --apply"
  echo ""

  # Write lock file so --apply knows dry-run was done recently
  echo "$(date +%s)" > "$LOCK_FILE"
  success "Lock file written: $LOCK_FILE (valid for ${LOCK_MAX_AGE_SECONDS}s)"
}

# ---------------------------------------------------------------------------
# APPLY
# ---------------------------------------------------------------------------
log_vps() {
  local msg="$1"
  ssh "$VPS_HOST" "echo '$(date -u +"%Y-%m-%dT%H:%M:%SZ") ${msg}' >> ${VPS_LOG}" 2>/dev/null || true
}

run_apply() {
  header "APPLY MODE"

  # Verify dry-run lock
  if [[ -f "$LOCK_FILE" ]]; then
    local lock_ts
    lock_ts=$(cat "$LOCK_FILE")
    local now
    now=$(date +%s)
    local age=$(( now - lock_ts ))
    if (( age > LOCK_MAX_AGE_SECONDS )); then
      die "Dry-run lock is stale (${age}s old, max ${LOCK_MAX_AGE_SECONDS}s). Re-run without --apply first."
    fi
    success "Dry-run lock valid (${age}s ago)"
  else
    die "No dry-run lock found at $LOCK_FILE. Run dry-run first (without --apply)."
  fi

  # Pre-apply snapshot
  create_snapshot "wave-i-p-deploy"

  echo ""
  log_vps "[wave-i-p] apply-start entries=${#DEPLOY_TABLE[@]}"
  log "Deploying ${#DEPLOY_TABLE[@]} entries to VPS..."
  echo ""

  local entry_num=0
  local success_count=0
  local skip_count=0
  local fail_count=0

  for entry in "${DEPLOY_TABLE[@]}"; do
    IFS='|' read -r local_rel vps_dest mode _filter <<< "$entry"
    local local_abs="${REPO_ROOT}/${local_rel}"
    entry_num=$(( entry_num + 1 ))

    if [[ ! -e "$local_abs" ]]; then
      warn "  [${entry_num}/${#DEPLOY_TABLE[@]}] SKIP (not found locally): ${local_rel}"
      skip_count=$(( skip_count + 1 ))
      log_vps "[wave-i-p] SKIP ${local_rel} (not found)"
      continue
    fi

    log "  [${entry_num}/${#DEPLOY_TABLE[@]}] ${local_rel} → ${vps_dest}"

    local rsync_exit=0

    if [[ "$mode" == "file" ]]; then
      rsync -avz --checksum \
        -e "ssh -o BatchMode=yes" \
        "$local_abs" \
        "${VPS_HOST}:${vps_dest}" || rsync_exit=$?
    else
      local extra_args=()
      [[ "$mode" == "new_only" ]] && extra_args+=(--ignore-existing)

      # Ensure remote dir exists
      ssh "$VPS_HOST" "mkdir -p '${vps_dest}'" 2>/dev/null || true

      rsync -avz --checksum "${extra_args[@]}" \
        -e "ssh -o BatchMode=yes" \
        "${local_abs}/" \
        "${VPS_HOST}:${vps_dest}/" || rsync_exit=$?
    fi

    if (( rsync_exit == 0 )); then
      success "    deployed"
      log_vps "[wave-i-p] OK ${local_rel} → ${vps_dest}"
      success_count=$(( success_count + 1 ))
    else
      error "    FAILED (rsync exit ${rsync_exit})"
      log_vps "[wave-i-p] FAIL ${local_rel} rsync_exit=${rsync_exit}"
      fail_count=$(( fail_count + 1 ))
    fi

    echo ""
  done

  echo ""
  header "APPLY COMPLETE"
  echo "  Success : ${success_count}"
  echo "  Skipped : ${skip_count}"
  echo "  Failed  : ${fail_count}"
  echo "  Log     : ${VPS_LOG} (on VPS)"
  echo ""

  if (( fail_count > 0 )); then
    warn "Some entries failed — check log on VPS: ssh ${VPS_HOST} 'tail -50 ${VPS_LOG}'"
  fi

  log_vps "[wave-i-p] apply-done ok=${success_count} skip=${skip_count} fail=${fail_count}"

  # Cleanup lock after apply
  rm -f "$LOCK_FILE"

  echo ""
  log "Run validation: ./scripts/deploy-wave-i-p.sh --validate"
}

# ---------------------------------------------------------------------------
# VALIDATE
# ---------------------------------------------------------------------------
run_validate() {
  header "POST-DEPLOY VALIDATION"

  local checks_pass=0
  local checks_fail=0

  # 1. API health returns 200 + schemaVersion=24
  log "Check 1: API health + schemaVersion..."
  local schema_ver
  schema_ver=$(ssh "$VPS_HOST" "curl -sf ${VPS_API}/api/health | jq -r '.schemaVersion // empty'" 2>/dev/null) || schema_ver=""
  if [[ "$schema_ver" == "24" ]]; then
    success "API healthy — schemaVersion=24"
    checks_pass=$(( checks_pass + 1 ))
  elif [[ -n "$schema_ver" ]]; then
    warn "API alive but schemaVersion=${schema_ver} (expected 24)"
    checks_fail=$(( checks_fail + 1 ))
  else
    error "API not responding"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 2. privacy/filter.ts exists
  log "Check 2: privacy/filter.ts..."
  if ssh "$VPS_HOST" "test -f '${VPS_NX}/src/privacy/filter.ts'" 2>/dev/null; then
    success "${VPS_NX}/src/privacy/filter.ts exists"
    checks_pass=$(( checks_pass + 1 ))
  else
    error "${VPS_NX}/src/privacy/filter.ts NOT FOUND"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 3. cors.ts exists
  log "Check 3: cors.ts..."
  if ssh "$VPS_HOST" "test -f '${VPS_NX}/src/api/cors.ts'" 2>/dev/null; then
    success "${VPS_NX}/src/api/cors.ts exists"
    checks_pass=$(( checks_pass + 1 ))
  else
    error "${VPS_NX}/src/api/cors.ts NOT FOUND"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 4. service still running
  log "Check 4: nox-mem API process..."
  local pids
  pids=$(ssh "$VPS_HOST" "pgrep -af 'node.*api-server' 2>/dev/null || true")
  if [[ -n "$pids" ]]; then
    success "nox-mem API process running: $pids"
    checks_pass=$(( checks_pass + 1 ))
  else
    error "No nox-mem API process found (pgrep node.*api-server returned empty)"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 5. wire-up adapters: deps registry
  log "Check 5: deps-registry.ts..."
  if ssh "$VPS_HOST" "test -f '${VPS_NX}/src/lib/deps/deps-registry.ts'" 2>/dev/null; then
    success "${VPS_NX}/src/lib/deps/deps-registry.ts exists"
    checks_pass=$(( checks_pass + 1 ))
  else
    warn "${VPS_NX}/src/lib/deps/deps-registry.ts not found (may still need wire-up)"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 6. G5 error-sanitizer
  log "Check 6: error-sanitizer/sanitize.ts..."
  if ssh "$VPS_HOST" "test -f '${VPS_NX}/src/lib/error-sanitizer/sanitize.ts'" 2>/dev/null; then
    success "error-sanitizer deployed"
    checks_pass=$(( checks_pass + 1 ))
  else
    error "error-sanitizer/sanitize.ts NOT FOUND"
    checks_fail=$(( checks_fail + 1 ))
  fi

  # 7. observability index
  log "Check 7: observability/index.ts..."
  if ssh "$VPS_HOST" "test -f '${VPS_NX}/src/observability/index.ts'" 2>/dev/null; then
    success "observability deployed"
    checks_pass=$(( checks_pass + 1 ))
  else
    error "src/observability/index.ts NOT FOUND"
    checks_fail=$(( checks_fail + 1 ))
  fi

  echo ""
  header "VALIDATION SUMMARY"
  echo "  Passed : ${checks_pass} / $(( checks_pass + checks_fail ))"
  echo "  Failed : ${checks_fail}"
  echo ""

  if (( checks_fail > 0 )); then
    warn "Some checks failed. Review errors above."
    exit 2
  else
    success "All checks passed — Wave I+P deploy verified."
  fi
}

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}nox-mem deploy-wave-i-p.sh${RST}  mode=${MODE}  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Repo  : ${REPO_ROOT}"
echo "  VPS   : ${VPS_HOST}"
echo "  NX    : ${VPS_NX}"
echo ""

case "$MODE" in
  dryrun)
    preflight_checks
    run_dryrun
    ;;
  apply)
    preflight_checks
    run_apply
    run_validate
    ;;
  validate)
    run_validate
    ;;
esac
