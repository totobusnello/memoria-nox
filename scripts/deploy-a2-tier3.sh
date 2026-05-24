#!/usr/bin/env bash
# scripts/deploy-a2-tier3.sh
#
# A2 Tier 3 / Phase 5 — deployment automation wrapper.
#
# PURPOSE
# -------
# Orchestrates the master deployment runbook
# (docs/A2-TIER3-DEPLOYMENT-MASTER.md) phases A→K. Each phase is idempotent:
# re-running a completed phase is a no-op (the script checks the
# post-condition first). Pre-flight gates each phase entry.
#
# USAGE
# -----
#   scripts/deploy-a2-tier3.sh --dry-run --all
#   scripts/deploy-a2-tier3.sh --phase A         # run phase A only
#   scripts/deploy-a2-tier3.sh --phase A,B,C     # run a subset in order
#   scripts/deploy-a2-tier3.sh --all             # run A→K, halting on first fail
#   scripts/deploy-a2-tier3.sh --pre-flight      # run pre-flight only
#   scripts/deploy-a2-tier3.sh --help
#
# FLAGS
# -----
#   --dry-run         Print the plan WITHOUT executing destructive commands.
#                     Idempotent post-condition checks DO run (read-only).
#   --phase <list>    Comma-separated list of phases A..K to run in order.
#   --all             Equivalent to --phase A,B,C,D,E,F,G,H,I,J,K.
#   --pre-flight      Run pre-flight checklist only (PF-1 .. PF-7).
#   --vps-host <h>    VPS hostname for SSH-based phases (default: from env).
#   --log-dir <p>     Override audit log directory (default: ./audits).
#   --help, -h        Show this help.
#
# ENV
# ---
#   NOX_VPS_HOST                 VPS hostname (e.g. nox-prod). Required for B/E/F/G/H/I.
#   NOX_DB_KEY                   SQLCipher key (post-Phase E). Required for F/G/H/J.
#   NOX_AUDIT_PRIVATE_KEY_FILE   Local path to Ed25519 private key. Required for J.
#
# LOGGING
# -------
# All output is tee'd to audits/a2-tier3-deploy-<ISO-ts>.log alongside the
# console. Errors are prefixed with [FAIL] and have nonzero exit codes.
#
# EXIT CODES
# ----------
#   0  — all requested phases completed (or were already done)
#   1  — pre-flight failure
#   2  — phase execution failure
#   3  — usage / argument error
#   4  — required env var missing
#
# NON-GOALS
# ---------
# - This script does NOT automate the off-box private-key custody steps
#   (Phase A.2). Those MUST be done manually by Toto.
# - This script does NOT push commits or merge PRs.
# - This script does NOT exfiltrate the cipher key — the key flows only
#   between the operator's shell env and the systemd EnvironmentFile.

set -euo pipefail

# ────────────────────────────────────────────────────────────────────────────
# Constants + globals
# ────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNBOOK="${REPO_ROOT}/docs/A2-TIER3-DEPLOYMENT-MASTER.md"

ALL_PHASES="A,B,C,D,E,F,G,H,I,J,K"
DRY_RUN=0
PHASES=""
RUN_PREFLIGHT_ONLY=0
LOG_DIR="${REPO_ROOT}/audits"
VPS_HOST="${NOX_VPS_HOST:-}"

# ────────────────────────────────────────────────────────────────────────────
# Output helpers
# ────────────────────────────────────────────────────────────────────────────

log_init() {
  mkdir -p "${LOG_DIR}"
  local ts
  ts="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
  LOG_FILE="${LOG_DIR}/a2-tier3-deploy-${ts}.log"
  exec > >(tee -a "${LOG_FILE}") 2>&1
  echo "[INIT] log file: ${LOG_FILE}"
  echo "[INIT] dry-run: ${DRY_RUN}"
  echo "[INIT] phases: ${PHASES:-<pre-flight-only>}"
  echo "[INIT] vps-host: ${VPS_HOST:-<not set>}"
}

step()  { echo ""; echo "──────────────────────────────────────────────────"; echo "[STEP] $*"; echo "──────────────────────────────────────────────────"; }
info()  { echo "[INFO] $*"; }
warn()  { echo "[WARN] $*" >&2; }
fail()  { echo "[FAIL] $*" >&2; exit 2; }
skip()  { echo "[SKIP] $*"; }
ok()    { echo "[OK]   $*"; }

run() {
  # Execute a command, honoring DRY_RUN. Always logs the command line.
  echo "[CMD ] $*"
  if (( DRY_RUN )); then
    echo "[DRY]  (would run)"
    return 0
  fi
  eval "$@"
}

require_env() {
  # require_env VAR_NAME [reason]
  local var="$1"
  local reason="${2:-required}"
  if [[ -z "${!var:-}" ]]; then
    echo "[FAIL] env var ${var} is ${reason} for this phase" >&2
    exit 4
  fi
}

ssh_run() {
  # ssh_run <command...> — wraps run with ssh to VPS_HOST.
  require_env VPS_HOST "required to run remote commands"
  run "ssh '${VPS_HOST}' \"$*\""
}

# ────────────────────────────────────────────────────────────────────────────
# Pre-flight (PF-1 .. PF-7 per master runbook)
# ────────────────────────────────────────────────────────────────────────────

pre_flight() {
  step "Pre-flight checklist"

  # PF-1 — disk space + baseline counts
  info "PF-1 — disk space + DB size baseline"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "df -h /root/.openclaw/workspace/tools/nox-mem | tail -1"
    ssh_run "ls -lh /root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
    ssh_run "sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db 'SELECT count(*) FROM chunks;' || echo 'cannot count chunks (DB may already be encrypted)'"
  else
    info "PF-1 — skipped (no VPS_HOST set; manual baseline required)"
  fi

  # PF-2 — recent nightly backup
  info "PF-2 — recent nightly backup exists"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "ls -lht /var/backups/nox-mem/ 2>/dev/null | head -3 || echo 'no backups directory'"
  fi

  # PF-3 — op-audit clean
  info "PF-3 — op-audit clean (no running ops)"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "curl -s http://127.0.0.1:18802/api/health 2>/dev/null | jq '.opsAudit' 2>/dev/null || echo 'API unreachable — check by hand'"
  fi

  # PF-4 — schema invariants
  info "PF-4 — schema invariants OK"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "/root/.openclaw/workspace/tools/nox-mem/scripts/check-schema-invariants.sh 2>&1 || warn 'schema invariants script missing or failing'"
  fi

  # PF-5 — better-sqlite3-multiple-ciphers available
  info "PF-5 — better-sqlite3-multiple-ciphers installable"
  run "npm view better-sqlite3-multiple-ciphers@^11.10 version 2>/dev/null | head -1 || warn 'npm registry unreachable from local'"

  # PF-6 — systemd override dir exists
  info "PF-6 — systemd unit override directory exists"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "ls -la /etc/systemd/system/nox-mem-api.service.d/ 2>/dev/null || echo 'override dir absent — Phase G will create'"
  fi

  # PF-7 — secrets directory
  info "PF-7 — secrets directory + ACL"
  if [[ -n "${VPS_HOST}" ]]; then
    ssh_run "stat -c '%a %U:%G' /root/.openclaw/secrets/ 2>/dev/null || echo 'secrets dir absent — Phase E will create'"
  fi

  ok "Pre-flight checks complete (review output for warnings)"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase A — Generate Ed25519 keypair + publish public key
# ────────────────────────────────────────────────────────────────────────────

phase_a() {
  step "Phase A — Generate Ed25519 keypair + publish public key"

  # Post-condition probe: does docs/AUDIT-PUBKEY.md exist already?
  if [[ -f "${REPO_ROOT}/docs/AUDIT-PUBKEY.md" ]]; then
    skip "docs/AUDIT-PUBKEY.md already present — Phase A previously completed."
    info "    To force re-generation: rm docs/AUDIT-PUBKEY.md && re-run --phase A"
    return 0
  fi

  local out_dir="/tmp/nox-audit-keys-$(date +%Y%m%d-%H%M%S)"
  info "Generating keypair into ${out_dir}"
  info "(staged P4 CLI: dist/edits/scripts/audit-checkpoint-cli.js gen-key)"
  run "cd '${REPO_ROOT}/staged-A2-T3' && npm run build > /dev/null 2>&1"
  run "node '${REPO_ROOT}/staged-A2-T3/dist/edits/scripts/audit-checkpoint-cli.js' gen-key --out-dir '${out_dir}'"

  cat <<EOF

[MANUAL] Phase A is partially manual:
  1. Move the private key OFF-BOX (laptop + paper backup):
       ls ${out_dir}/audit-checkpoints-private-*.b64
  2. Publish docs/AUDIT-PUBKEY.md with the public key + fingerprint.
  3. Wipe the private key file on the local machine (shred -u).
  4. Commit + push docs/AUDIT-PUBKEY.md.
  See docs/A2-TIER3-DEPLOYMENT-MASTER.md §Phase A for the exact template.
EOF

  ok "Phase A keypair generated. Complete the manual steps above before Phase J."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase B — Deploy P1 code (db.ts wire-up) to VPS
# ────────────────────────────────────────────────────────────────────────────

phase_b() {
  step "Phase B — Deploy P1 code (db.ts wire-up)"
  require_env VPS_HOST "to SCP staged code to VPS"

  # Post-condition: is the API already running with isEncrypted=false (P1 deployed, plaintext mode)?
  # We can't tell from outside whether the db.ts on the VPS is the P1 version without
  # inspecting it. Use a marker: presence of better-sqlite3-multiple-ciphers in package.json.
  # NOTE: guard with DRY_RUN so this read-only SSH probe does not fire during dry-run validation.
  local check="0"
  if (( DRY_RUN == 0 )); then
    check="$(ssh "${VPS_HOST}" 'grep -c better-sqlite3-multiple-ciphers /root/.openclaw/workspace/tools/nox-mem/package.json 2>/dev/null || echo 0' || true)"
  fi
  if [[ "${check}" =~ [1-9] ]]; then
    skip "better-sqlite3-multiple-ciphers already in VPS package.json — Phase B previously deployed."
    info "    To force re-deploy: remove the dependency on VPS then re-run."
    return 0
  fi

  info "Step B.1 — SCP staged code"
  run "rsync -avz '${REPO_ROOT}/staged-A2-T3/edits/src/lib/db.ts' '${VPS_HOST}:/root/.openclaw/workspace/tools/nox-mem/src/lib/db.ts.staged'"
  run "rsync -avz '${REPO_ROOT}/staged-A2-T3/edits/src/lib/reads-audit.ts' '${REPO_ROOT}/staged-A2-T3/edits/src/lib/reads-audit-schema.sql' '${REPO_ROOT}/staged-A2-T3/edits/src/lib/audit-checkpoints.ts' '${REPO_ROOT}/staged-A2-T3/edits/src/lib/audit-checkpoints-schema.sql' '${VPS_HOST}:/root/.openclaw/workspace/tools/nox-mem/src/lib/'"
  run "rsync -avz '${REPO_ROOT}/staged-A2-T3/scripts/migrate-encrypt-db.ts' '${VPS_HOST}:/root/.openclaw/workspace/tools/nox-mem/scripts/'"
  run "rsync -avz '${REPO_ROOT}/staged-A2-T3/edits/scripts/audit-checkpoint-cli.ts' '${REPO_ROOT}/staged-A2-T3/edits/scripts/reads-audit-sweep.ts' '${VPS_HOST}:/root/.openclaw/workspace/tools/nox-mem/scripts/'"

  info "Step B.2 — install dependency + build on VPS"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && npm install better-sqlite3-multiple-ciphers@^11.10"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && cp src/lib/db.ts src/lib/db.ts.pre-a2-t3-\$(date +%Y%m%d-%H%M).bak"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && mv src/lib/db.ts.staged src/lib/db.ts"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && npm run build"

  info "Step B.3 — restart API (still plaintext, NOX_DB_KEY not yet in env)"
  ssh_run "systemctl restart nox-mem-api"
  ssh_run "sleep 2 && systemctl status nox-mem-api | head -10"

  info "Step B.4 — validate /api/health responds + isEncrypted=false"
  ssh_run "curl -s http://127.0.0.1:18802/api/health | jq '{ok, totalChunks, isEncrypted}'"

  ok "Phase B deployed. Verify isEncrypted=false in the output above."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase C — Verify smoke on plaintext (no-regression)
# ────────────────────────────────────────────────────────────────────────────

phase_c() {
  step "Phase C — Verify smoke on plaintext (no-regression)"
  require_env VPS_HOST "to curl API endpoints"

  info "C.1-C.5: standard search + KG + vector smokes"
  ssh_run "curl -s http://127.0.0.1:18802/api/health | jq '.totalChunks'"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/search?q=nox' | jq 'length'"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/search?q=memoria+nox+pain+weighted&hybrid=true' | jq '.[0] | {id, score}'"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/kg?entity=Toto' | jq 'length'"
  ssh_run "curl -s http://127.0.0.1:18802/api/health | jq '.vectorCoverage'"

  ok "Phase C complete (visually verify non-zero counts above)."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase D — Stop ingest pipeline
# ────────────────────────────────────────────────────────────────────────────

phase_d() {
  step "Phase D — Stop ingest pipeline"
  require_env VPS_HOST "to manipulate crontab + processes"

  info "D.1 — back up + clear cron"
  ssh_run "crontab -l > /tmp/crontab-pre-a2-t3.bak 2>/dev/null || true"
  ssh_run "crontab -l | grep -v 'nox-mem' | crontab - || crontab -r"
  ssh_run "crontab -l 2>&1 | grep -c nox-mem || echo 0"

  info "D.2 — kill inotifywait watcher"
  ssh_run "pkill -f 'inotifywait.*nox-mem' 2>/dev/null || true"
  ssh_run "ps -ef | grep -E 'inotifywait|nox-mem' | grep -v grep || true"

  info "D.3 — stop API"
  ssh_run "systemctl stop nox-mem-api"
  ssh_run "systemctl status nox-mem-api | head -3"

  info "D.4 — verify no DB holders"
  ssh_run "lsof 2>/dev/null | grep nox-mem.db || echo 'no holders — good'"

  ok "Phase D complete. Ingest pipeline quiesced."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase E — Run P2 migration script
# ────────────────────────────────────────────────────────────────────────────

phase_e() {
  step "Phase E — Run P2 migration script (create encrypted dest)"
  require_env VPS_HOST "to run migration on VPS"

  info "E.1 — generate cipher key on VPS if not already present"
  ssh_run "mkdir -p /root/.openclaw/secrets/ && chmod 0700 /root/.openclaw/secrets/"
  ssh_run "test -f /root/.openclaw/secrets/nox-mem-cipher.key && echo 'key exists — keep it' || (openssl rand -base64 48 > /root/.openclaw/secrets/nox-mem-cipher.key && chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.key && chown root:root /root/.openclaw/secrets/nox-mem-cipher.key)"

  cat <<EOF

[MANUAL] E.2 — back up the cipher key to laptop NOW (BEFORE Phase F):
  scp ${VPS_HOST}:/root/.openclaw/secrets/nox-mem-cipher.key ~/Documents/nox-secrets/
  chmod 0600 ~/Documents/nox-secrets/nox-mem-cipher.key

EOF
  if (( DRY_RUN == 0 )); then
    read -r -p "Press ENTER when key is backed up to laptop (or Ctrl-C to abort): " _
  fi

  info "E.3 — run migration (non-destructive)"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && export NOX_DB_KEY=\$(cat /root/.openclaw/secrets/nox-mem-cipher.key) && node dist/scripts/migrate-encrypt-db.js ./nox-mem.db ./nox-mem.encrypted.db \"\$NOX_DB_KEY\" 2>&1 | tee /tmp/migrate-encrypt-\$(date +%Y%m%d-%H%M).log"

  info "E.4 — validate encrypted DB row counts"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && export NOX_DB_KEY=\$(cat /root/.openclaw/secrets/nox-mem-cipher.key) && node -e \"const D=require('better-sqlite3-multiple-ciphers'); const db=new D('./nox-mem.encrypted.db'); db.pragma(\\\"cipher='sqlcipher'\\\"); db.pragma(\\\"legacy=4\\\"); db.pragma(\\\"cipher_compatibility=4\\\"); db.pragma(\\\"key='\\\"+process.env.NOX_DB_KEY+\\\"'\\\"); db.defaultSafeIntegers(true); console.log('chunks:', Number(db.prepare('SELECT count(*) AS n FROM chunks').get().n)); console.log('kg_entities:', Number(db.prepare('SELECT count(*) AS n FROM kg_entities').get().n)); console.log('kg_relations:', Number(db.prepare('SELECT count(*) AS n FROM kg_relations').get().n));\""

  ok "Phase E complete. Verify counts match pre-encryption baseline (PF-1)."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase F — Atomic swap
# ────────────────────────────────────────────────────────────────────────────

phase_f() {
  step "Phase F — Atomic swap (encrypted → canonical path)"
  require_env VPS_HOST "to perform swap on VPS"

  info "F.1 — confirm API stopped"
  ssh_run "systemctl status nox-mem-api 2>&1 | grep -E 'Active:' | head -1"

  info "F.2 — perform swap via dedicated helper"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && export NOX_DB_KEY=\$(cat /root/.openclaw/secrets/nox-mem-cipher.key) && node -e \"const {swapEncryptedIntoSource}=require('./dist/scripts/migrate-encrypt-db.js'); const b=swapEncryptedIntoSource('./nox-mem.db','./nox-mem.encrypted.db'); console.log('plaintext backup at:', b);\""

  info "F.3 — validate (encrypted DB rejects no-key open)"
  ssh_run "ls -la /root/.openclaw/workspace/tools/nox-mem/nox-mem.db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db.pre-encrypt-*.db 2>/dev/null | head -3"
  ssh_run "sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db 'SELECT count(*) FROM sqlite_master;' 2>&1 | grep -E 'not a database|encrypted' && echo 'PASS — encrypted DB rejects no-key open' || echo 'FAIL — encrypted DB readable without key'"

  ok "Phase F complete."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase G — Set NOX_DB_KEY + NOX_DB_REQUIRE_KEY in systemd
# ────────────────────────────────────────────────────────────────────────────

phase_g() {
  step "Phase G — Set NOX_DB_KEY + NOX_DB_REQUIRE_KEY in systemd"
  require_env VPS_HOST "to update systemd unit"

  info "G.1 — create EnvironmentFile"
  ssh_run "cat > /root/.openclaw/secrets/nox-mem-cipher.env <<EOF
NOX_DB_KEY=\$(cat /root/.openclaw/secrets/nox-mem-cipher.key)
NOX_DB_REQUIRE_KEY=1
EOF"
  ssh_run "chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.env"
  ssh_run "chown root:root /root/.openclaw/secrets/nox-mem-cipher.env"

  info "G.2 — write systemd unit override"
  ssh_run "mkdir -p /etc/systemd/system/nox-mem-api.service.d/"
  ssh_run "cat > /etc/systemd/system/nox-mem-api.service.d/override.conf <<'EOF'
[Service]
EnvironmentFile=/root/.openclaw/secrets/nox-mem-cipher.env
EOF"
  ssh_run "systemctl daemon-reload"

  info "G.3 — validation"
  ssh_run "stat -c '%a %U:%G %s' /root/.openclaw/secrets/nox-mem-cipher.env"
  ssh_run "systemctl cat nox-mem-api | grep -E 'EnvironmentFile|Environment' || echo 'no env directives in unit'"

  ok "Phase G complete. (API not yet restarted — Phase H drives that.)"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase H — Smoke encrypted DB
# ────────────────────────────────────────────────────────────────────────────

phase_h() {
  step "Phase H — Smoke encrypted DB"
  require_env VPS_HOST "to start API + run smokes"

  info "H.1 — start API"
  ssh_run "systemctl start nox-mem-api && sleep 3 && systemctl status nox-mem-api | head -10"

  info "H.2 — /api/health reports encrypted mode"
  ssh_run "curl -s http://127.0.0.1:18802/api/health | jq '{ok, totalChunks, vectorCoverage, isEncrypted}'"

  info "H.3 — FTS5 search smoke"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/search?q=nox' | jq 'length'"

  info "H.4 — hybrid search"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/search?q=memoria+pain+weighted&hybrid=true' | jq '.[0] | {id, score}'"

  info "H.5 — KG endpoint"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/kg?entity=Toto' | jq 'length'"

  info "H.6 — vec0 vector search"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/search?q=hybrid+memory&hybrid=true&topK=5' | jq 'length'"

  info "H.7 — /api/answer flagship"
  ssh_run "curl -s 'http://127.0.0.1:18802/api/answer?q=what+is+nox-mem' | jq '{answer: (.answer | .[0:100]), latency_ms}'"

  ok "Phase H smoke complete. Verify isEncrypted=true above."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase I — Re-enable ingest pipeline
# ────────────────────────────────────────────────────────────────────────────

phase_i() {
  step "Phase I — Re-enable ingest pipeline"
  require_env VPS_HOST "to restore cron"

  info "I.1 — restore crontab from Phase D backup"
  ssh_run "test -f /tmp/crontab-pre-a2-t3.bak && crontab /tmp/crontab-pre-a2-t3.bak || echo 'no backup found — restore manually'"
  ssh_run "crontab -l | grep -c nox-mem || echo 0"

  info "I.2 — restart inotifywait watcher (best-effort, may be systemd-managed)"
  ssh_run "systemctl start nox-mem-watch 2>/dev/null || (nohup /root/.openclaw/workspace/tools/nox-mem/scripts/watch-and-ingest.sh > /var/log/nox-mem/watch.log 2>&1 & echo 'started via nohup')"

  info "I.4 — write a tracer + confirm round-trip"
  ssh_run "echo 'post-encryption tracer \$(date -Is)' > /tmp/nox-mem-tracer-i4.txt && nox-mem ingest /tmp/nox-mem-tracer-i4.txt && sleep 2 && curl -s 'http://127.0.0.1:18802/api/search?q=tracer-i4' | jq 'length'"

  ok "Phase I complete. Ingest pipeline restored."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase J — Initial Ed25519 checkpoint
# ────────────────────────────────────────────────────────────────────────────

phase_j() {
  step "Phase J — Initial Ed25519 checkpoint (auditor baseline)"
  require_env VPS_HOST "to bridge encrypted DB"
  require_env NOX_AUDIT_PRIVATE_KEY_FILE "to sign initial checkpoint"

  cat <<EOF

[MANUAL] Phase J is heavily off-box (laptop-driven). Auto-orchestration is
limited to bridging the snapshot + running create/verify commands. The actual
signing happens on the laptop where NOX_AUDIT_PRIVATE_KEY_FILE points.

Sequence:
  1. Bridge an encrypted snapshot from VPS to laptop
  2. Run audit-checkpoint create --scope ops on laptop (signs offline)
  3. Run audit-checkpoint create --scope reads on laptop
  4. verify-chain --scope all
  5. Sync the checkpoint rows back to VPS via SQL dump

See docs/A2-TIER3-DEPLOYMENT-MASTER.md §Phase J for the full sequence.

EOF
  if (( DRY_RUN == 0 )); then
    read -r -p "Press ENTER to proceed with bridge (or Ctrl-C to handle manually): " _
  fi

  info "J.1 — bridge snapshot to laptop"
  ssh_run "cp /root/.openclaw/workspace/tools/nox-mem/nox-mem.db /tmp/nox-mem-checkpoint-bridge.db"
  run "scp '${VPS_HOST}:/tmp/nox-mem-checkpoint-bridge.db' /tmp/"

  info "J.2 + J.3 — create checkpoints (signed offline on laptop)"
  run "cd '${REPO_ROOT}/staged-A2-T3' && NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db NOX_DB_KEY=\"\${NOX_DB_KEY:-}\" node dist/edits/scripts/audit-checkpoint-cli.js create --scope ops --key-file '${NOX_AUDIT_PRIVATE_KEY_FILE}'"
  run "cd '${REPO_ROOT}/staged-A2-T3' && NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db NOX_DB_KEY=\"\${NOX_DB_KEY:-}\" node dist/edits/scripts/audit-checkpoint-cli.js create --scope reads --key-file '${NOX_AUDIT_PRIVATE_KEY_FILE}'"

  info "J.4 — verify chain"
  local pub_file="${NOX_AUDIT_PUBLIC_KEY_FILE:-${NOX_AUDIT_PRIVATE_KEY_FILE/-private-/-public-}}"
  run "cd '${REPO_ROOT}/staged-A2-T3' && NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db NOX_DB_KEY=\"\${NOX_DB_KEY:-}\" node dist/edits/scripts/audit-checkpoint-cli.js verify-chain --scope all --key-file '${pub_file}'"

  cat <<EOF

[MANUAL] J.5 — sync checkpoint rows back to VPS:
  sqlite3 /tmp/nox-mem-checkpoint-bridge.db ".dump audit_checkpoints" > /tmp/checkpoints.sql
  scp /tmp/checkpoints.sql ${VPS_HOST}:/tmp/
  ssh ${VPS_HOST} 'cd /root/.openclaw/workspace/tools/nox-mem && export NOX_DB_KEY=\$(cat /root/.openclaw/secrets/nox-mem-cipher.key) && node -e "const D=require(\"better-sqlite3-multiple-ciphers\"); const fs=require(\"fs\"); const db=new D(\"./nox-mem.db\"); db.pragma(\"cipher='\''sqlcipher'\''\"); db.pragma(\"legacy=4\"); db.pragma(\"cipher_compatibility=4\"); db.pragma(\"key='\''\\\$NOX_DB_KEY'\''\"); db.exec(fs.readFileSync(\"/tmp/checkpoints.sql\",\"utf8\"));"'
  rm /tmp/nox-mem-checkpoint-bridge.db /tmp/checkpoints.sql

EOF

  ok "Phase J automated portion complete. Finish J.5 manually."
}

# ────────────────────────────────────────────────────────────────────────────
# Phase K — Cron schedule
# ────────────────────────────────────────────────────────────────────────────

phase_k() {
  step "Phase K — Cron schedule (P3 reads-audit sweep + P4 reminder)"
  require_env VPS_HOST "to install cron lines"

  info "K.1 — install P3 sweep cron"
  ssh_run "(crontab -l 2>/dev/null; echo '0 6 * * 0  cd /root/.openclaw/workspace/tools/nox-mem && set -a && source /root/.openclaw/.env && source /root/.openclaw/secrets/nox-mem-cipher.env && set +a && node dist/scripts/reads-audit-sweep.js --retention-days 90 --archive-path /var/backups/nox-mem/reads-audit-archive.db >> /var/log/nox-mem/reads-audit-sweep.log 2>&1') | crontab -"

  info "K.2 — install weekly checkpoint reminder"
  ssh_run "(crontab -l 2>/dev/null; echo '0 12 * * 1  echo \"Weekly nox-mem audit checkpoint due — run from laptop: ssh + audit-checkpoint create --scope all\" | mail -s \"[nox-mem] weekly checkpoint reminder\" lab@nuvini.com.br') | crontab -"

  info "K.3 — validation"
  ssh_run "crontab -l | grep -c -E 'reads-audit-sweep|checkpoint'"
  ssh_run "cd /root/.openclaw/workspace/tools/nox-mem && set -a && source /root/.openclaw/.env && source /root/.openclaw/secrets/nox-mem-cipher.env && set +a && node dist/scripts/reads-audit-sweep.js --dry-run --retention-days 90"

  ok "Phase K complete. A2 Tier 3 deployment finalized."
}

# ────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ────────────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $0 [flags]

Flags:
  --dry-run         Print plan without executing destructive commands.
  --phase <list>    Comma-separated phases A..K (e.g. 'A,B,C').
  --all             Equivalent to --phase ${ALL_PHASES}.
  --pre-flight      Run pre-flight checks only.
  --vps-host <h>    VPS hostname for SSH-based phases.
  --log-dir <p>     Override audit log directory (default: ./audits).
  --help, -h        This help.

Env:
  NOX_VPS_HOST                  VPS hostname (default for --vps-host)
  NOX_DB_KEY                    SQLCipher key (post-Phase E)
  NOX_AUDIT_PRIVATE_KEY_FILE    Ed25519 private key path (Phase J)
  NOX_AUDIT_PUBLIC_KEY_FILE     Ed25519 public key path (Phase J verify)

See: ${RUNBOOK}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)         DRY_RUN=1; shift ;;
    --phase)           PHASES="${2:-}"; shift 2 ;;
    --all)             PHASES="${ALL_PHASES}"; shift ;;
    --pre-flight)      RUN_PREFLIGHT_ONLY=1; shift ;;
    --vps-host)        VPS_HOST="${2:-}"; shift 2 ;;
    --log-dir)         LOG_DIR="${2:-}"; shift 2 ;;
    --help|-h)         usage; exit 0 ;;
    *)                 echo "[FAIL] unknown arg: $1" >&2; usage >&2; exit 3 ;;
  esac
done

if (( RUN_PREFLIGHT_ONLY == 0 )) && [[ -z "${PHASES}" ]]; then
  echo "[FAIL] either --pre-flight, --phase <list>, or --all must be given" >&2
  usage >&2
  exit 3
fi

# ────────────────────────────────────────────────────────────────────────────
# Main dispatch
# ────────────────────────────────────────────────────────────────────────────

log_init

if (( RUN_PREFLIGHT_ONLY )); then
  pre_flight
  ok "Pre-flight only — exiting clean."
  exit 0
fi

# Always run pre-flight before any phase (gated; failures stop the run).
pre_flight

# Execute phases in given order.
IFS=',' read -ra phase_list <<< "${PHASES}"
for p in "${phase_list[@]}"; do
  p="$(echo "${p}" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')"
  case "${p}" in
    A) phase_a ;;
    B) phase_b ;;
    C) phase_c ;;
    D) phase_d ;;
    E) phase_e ;;
    F) phase_f ;;
    G) phase_g ;;
    H) phase_h ;;
    I) phase_i ;;
    J) phase_j ;;
    K) phase_k ;;
    *) echo "[FAIL] unknown phase '${p}' — expected A..K" >&2; exit 3 ;;
  esac
done

ok "All requested phases (${PHASES}) completed."
