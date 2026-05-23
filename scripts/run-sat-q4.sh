#!/usr/bin/env bash
set -euo pipefail
# Sat full Q4 run — 6 systems × locomo+longmemeval × 100 queries
# Estimated time: ~75-90min (agentmemory ingest dominates)
# Estimated cost: ~$0.60 (mem0 OpenAI embeddings)
#
# Usage:
#   ./scripts/run-sat-q4.sh                            # full run
#   ./scripts/run-sat-q4.sh --dry-run                  # estimate cost+time only
#   ./scripts/run-sat-q4.sh --skip-preflight           # skip ALL pre-flight checks (debug)
#   ./scripts/run-sat-q4.sh --quiet                    # suppress verbose echo statements
#   ./scripts/run-sat-q4.sh --cost-limit 2.00          # abort if >$2
#   ./scripts/run-sat-q4.sh --skip-systems zep,letta   # skip specific systems
#   ./scripts/run-sat-q4.sh --systems nox_mem,mem0     # run only listed systems
#   ./scripts/run-sat-q4.sh --limit 10                 # shorter dev run
#
# Scheduled: Sun 2026-05-25 09h00 BRT (UTC-3 = 12:00 UTC)
# Wall-clock breakdown:
#   nox_mem      ~2min  ($0.00)  — HTTP on :18802, no ingest needed
#   mem0         ~12min ($0.60)  — OpenAI embed ingest + 100 queries
#   zep          ~5min  ($0.00)  — FastEmbed local, Docker required
#   letta        ~5min  ($0.00)  — SQLite backend, Docker or bare letta server
#   agentmemory  ~54min ($0.00)  — iii-engine full corpus ingest (REST :3111)
#   evermind     SKIP   ($0.00)  — repo 404, adapter.validate() returns ok=False
#   aggregate    ~1min  ($0.00)  — offline nDCG/MRR/latency computation
#
# Pre-flight timeout behavior:
#   All blocking operations (curl, docker info, agentmemory --version) are
#   wrapped with `timeout N` to prevent indefinite hangs. Network checks use
#   `--max-time 5` on curl and `ping -c 1 -W 2`. Docker daemon check uses
#   `timeout 5 docker info`. If any check times out it is treated as WARN
#   (non-fatal) not ABORT unless it's a required file (venv, datasets, runner.py).
#
# --skip-preflight flag:
#   Bypasses ALL pre-flight checks. Use when you know the environment is
#   correct and just want to validate dry-run output speed, or to debug a
#   hang caused by a stuck check. Systems remain at the defaults/--systems
#   value; daemon health waits in Stage 3 still fire.
#
# Sat run sequence (with these flags in mind):
#   1. Debug unknown hang:  ./scripts/run-sat-q4.sh --dry-run --skip-preflight
#   2. Validate adapters:   ./scripts/run-sat-q4.sh --dry-run
#   3. Full run:            ./scripts/run-sat-q4.sh

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
Q4_DIR="${REPO_ROOT}/eval/q4-comparison"
OUTPUT_DIR="${Q4_DIR}/output"
COMPOSE_FILE="${Q4_DIR}/compose/docker-compose.yml"
# .venv lives in the main worktree (not in agent worktrees under /tmp).
# Q4_VENV_PYTHON can be overridden when running from a worktree.
VENV_PYTHON="${Q4_VENV_PYTHON:-${Q4_DIR}/.venv/bin/python}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${OUTPUT_DIR}/sat-q4-run-${TIMESTAMP}.log"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DRY_RUN=0
SKIP_PREFLIGHT=0
QUIET=0
COST_LIMIT="5.00"
SKIP_SYSTEMS=""
SYSTEMS="nox_mem,mem0,zep,letta,agentmemory"  # evermind always skipped (repo 404)
LIMIT=100
DOCKER_PROFILES="zep"   # postgres is implied; add 'letta' if desired

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------

usage() {
  grep '^#' "${BASH_SOURCE[0]}" | grep -v '^#!/' | sed 's/^# \?//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)         DRY_RUN=1;          shift ;;
    --skip-preflight)  SKIP_PREFLIGHT=1;   shift ;;
    --quiet)           QUIET=1;            shift ;;
    --cost-limit)      COST_LIMIT="$2";    shift 2 ;;
    --skip-systems)    SKIP_SYSTEMS="$2";  shift 2 ;;
    --systems)         SYSTEMS="$2";       shift 2 ;;
    --limit)           LIMIT="$2";         shift 2 ;;
    --with-letta)      DOCKER_PROFILES="zep,letta"; shift ;;
    -h|--help)         usage ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Apply skip list
if [[ -n "$SKIP_SYSTEMS" ]]; then
  for skip in ${SKIP_SYSTEMS//,/ }; do
    SYSTEMS="${SYSTEMS//$skip/}"
  done
  # Clean up doubled commas
  SYSTEMS="${SYSTEMS//,,/,}"
  SYSTEMS="${SYSTEMS#,}"
  SYSTEMS="${SYSTEMS%,}"
fi

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

mkdir -p "${OUTPUT_DIR}"

log() {
  local ts
  ts="$(date -u +%H:%M:%SZ)"
  if [[ "${QUIET}" == "1" ]]; then
    echo "[${ts}] $*" >> "${LOG_FILE}"
  else
    echo "[${ts}] $*" | tee -a "${LOG_FILE}"
  fi
}

log_section() {
  if [[ "${QUIET}" == "1" ]]; then
    {
      echo ""
      echo "================================================================"
      echo "[$(date -u +%H:%M:%SZ)] STAGE: $*"
      echo "================================================================"
    } >> "${LOG_FILE}"
  else
    echo "" | tee -a "${LOG_FILE}"
    echo "================================================================" | tee -a "${LOG_FILE}"
    log "STAGE: $*"
    echo "================================================================" | tee -a "${LOG_FILE}"
  fi
}

# Redirect all output to log as well (but only when not quiet — quiet mode
# writes to log directly in log() above to avoid the tee subprocess overhead).
if [[ "${QUIET}" == "0" ]]; then
  exec > >(tee -a "${LOG_FILE}") 2>&1
fi

log "Run started — log: ${LOG_FILE}"
log "Systems: ${SYSTEMS}"
log "Limit: ${LIMIT} queries/dataset | Cost limit: \$${COST_LIMIT}"
log "Dry-run: ${DRY_RUN} | Skip-preflight: ${SKIP_PREFLIGHT} | Quiet: ${QUIET}"

# ---------------------------------------------------------------------------
# Cost guard helpers
# ---------------------------------------------------------------------------

# mem0 cost estimate: ~$0.60 per full 100q run (OpenAI text-embedding-3-small)
# Letta default is also OpenAI but shares ingest with mem0 roughly
ESTIMATED_COST_USD="0.00"

cost_add() {
  ESTIMATED_COST_USD="$(LC_NUMERIC=C awk "BEGIN{printf \"%.2f\", ${ESTIMATED_COST_USD} + $1}")"
}

cost_check() {
  local exceeds
  exceeds="$(LC_NUMERIC=C awk "BEGIN{print (${ESTIMATED_COST_USD} > ${COST_LIMIT}) ? 1 : 0}")"
  if [[ "${exceeds}" == "1" ]]; then
    log "ABORT: estimated cost \$${ESTIMATED_COST_USD} exceeds --cost-limit \$${COST_LIMIT}"
    exit 2
  fi
}

system_enabled() {
  local sys="$1"
  [[ ",${SYSTEMS}," == *",${sys},"* ]]
}

# ---------------------------------------------------------------------------
# STAGE 1: Pre-flight checks
# ---------------------------------------------------------------------------

log_section "PRE-FLIGHT"

if [[ "${SKIP_PREFLIGHT}" == "1" ]]; then
  log "SKIP_PREFLIGHT set — bypassing all pre-flight checks"
  log "Systems will proceed as-is: ${SYSTEMS}"
else

PREFLIGHT_OK=1

# 1a. Python venv
if [[ ! -f "${VENV_PYTHON}" ]]; then
  log "ERROR: venv not found at ${VENV_PYTHON}"
  log "  Fix: cd ${Q4_DIR} && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  PREFLIGHT_OK=0
else
  log "OK  venv: ${VENV_PYTHON}"
fi

# 1b. OPENAI_API_KEY (required for mem0 + letta defaults)
if system_enabled "mem0" || system_enabled "letta"; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    log "WARN: OPENAI_API_KEY not set — mem0/letta will fail during setup()"
    log "  Fix: export OPENAI_API_KEY=sk-..."
    # Not fatal — adapter.validate() will surface this cleanly
  else
    log "OK  OPENAI_API_KEY set (${#OPENAI_API_KEY} chars)"
    # mem0: ~$0.60 per 100q run (ada embeddings for ingest corpus)
    if system_enabled "mem0"; then
      cost_add "0.60"
    fi
    # letta: ~$0.10 per 100q run (smaller corpus ingest)
    if system_enabled "letta"; then
      cost_add "0.10"
    fi
  fi
fi

cost_check

# 1c. GEMINI_API_KEY (nox-mem)
if system_enabled "nox_mem"; then
  if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    log "WARN: GEMINI_API_KEY not set — nox_mem semantic search may degrade"
  else
    log "OK  GEMINI_API_KEY set"
  fi
fi

# 1d. nox-mem API reachable
if system_enabled "nox_mem"; then
  NOX_API_BASE="${NOX_API_BASE:-http://127.0.0.1:18802}"
  if timeout 5 curl -sf --max-time 5 "${NOX_API_BASE}/api/health" > /dev/null 2>&1; then
    log "OK  nox-mem API: ${NOX_API_BASE}/api/health"
  else
    log "WARN: nox-mem API not reachable at ${NOX_API_BASE} — adapter may fail"
    log "  Fix: node dist/index.js api   (in ${REPO_ROOT})"
    log "  Or:  NOX_API_BASE=http://<vps>:18802 ./scripts/run-sat-q4.sh ..."
  fi
fi

# 1e. agentmemory CLI installed
if system_enabled "agentmemory"; then
  if command -v agentmemory > /dev/null 2>&1; then
    AM_VERSION="$(timeout 5 agentmemory --version 2>/dev/null || echo 'unknown')"
    log "OK  agentmemory CLI: ${AM_VERSION}"
  else
    log "WARN: agentmemory CLI not found in PATH"
    log "  Fix: npm install -g @agentmemory/agentmemory"
  fi
fi

# 1f. Docker / OrbStack
# IMPORTANT: `docker info` can hang indefinitely if Docker Desktop is in a
# crashed/starting state. Always wrap with `timeout`.
DOCKER_UP=0
if command -v docker > /dev/null 2>&1 && timeout 5 docker info > /dev/null 2>&1; then
  DOCKER_UP=1
  log "OK  Docker daemon: up"
else
  log "INFO: Docker not available or not responding — zep/letta will be skipped unless already running"
  # Remove Docker-dependent systems from run list if Docker is down
  for dock_sys in zep letta; do
    if system_enabled "${dock_sys}"; then
      if ! timeout 3 curl -sf --max-time 2 "http://127.0.0.1:8000/healthz" > /dev/null 2>&1 \
         && ! timeout 3 curl -sf --max-time 2 "http://127.0.0.1:8283/v1/health" > /dev/null 2>&1; then
        log "INFO: removing ${dock_sys} from run (Docker down + no existing daemon)"
        SYSTEMS="${SYSTEMS//${dock_sys}/}"
        SYSTEMS="${SYSTEMS//,,/,}"
        SYSTEMS="${SYSTEMS#,}"
        SYSTEMS="${SYSTEMS%,}"
      fi
    fi
  done
fi

# 1g. Dataset files present
for ds in locomo longmemeval; do
  DS_FILE="${REPO_ROOT}/eval/${ds}/dry-run-sample.json"
  if [[ -f "${DS_FILE}" ]]; then
    log "OK  dataset: eval/${ds}/dry-run-sample.json"
  else
    log "ERROR: dataset file missing: ${DS_FILE}"
    PREFLIGHT_OK=0
  fi
done

# 1h. runner.py + aggregate.py present
for pyfile in runner.py aggregate.py; do
  if [[ -f "${Q4_DIR}/${pyfile}" ]]; then
    log "OK  ${pyfile}"
  else
    log "ERROR: ${Q4_DIR}/${pyfile} not found"
    PREFLIGHT_OK=0
  fi
done

if [[ "${PREFLIGHT_OK}" == "0" ]]; then
  log "ABORT: pre-flight checks failed (see above)"
  exit 1
fi

fi  # end SKIP_PREFLIGHT block

log ""
log "Systems enabled: ${SYSTEMS}"
log "Estimated cost:  \$${ESTIMATED_COST_USD} (limit: \$${COST_LIMIT})"

if [[ "${DRY_RUN}" == "1" ]]; then
  log_section "DRY-RUN MODE — printing plan only"
  log "Wall-clock estimate:"
  system_enabled "nox_mem"      && log "  nox_mem:     ~2min   \$0.00  — HTTP on :18802"
  system_enabled "mem0"         && log "  mem0:        ~12min  \$0.60  — OpenAI embed ingest"
  system_enabled "zep"          && log "  zep:         ~5min   \$0.00  — FastEmbed local"
  system_enabled "letta"        && log "  letta:       ~5min   \$0.10  — OpenAI embed (smaller corpus)"
  system_enabled "agentmemory"  && log "  agentmemory: ~54min  \$0.00  — iii-engine REST ingest"
  log "  evermind:    SKIP   — repo 404"
  log "  aggregate:   ~1min  \$0.00"
  log ""
  log "Running runner.py --dry-run to validate adapters..."
  "${VENV_PYTHON}" "${Q4_DIR}/runner.py" \
    --systems "${SYSTEMS}" \
    --datasets locomo,longmemeval \
    --limit "${LIMIT}" \
    --dry-run
  log ""
  log "DRY-RUN complete. Re-run without --dry-run to execute."
  exit 0
fi

# ---------------------------------------------------------------------------
# STAGE 2: Daemon management
# ---------------------------------------------------------------------------

log_section "DAEMON MANAGEMENT"

# Track PIDs we started so we can tear down at exit
AGENTMEMORY_PID=""
DOCKER_STARTED=0

cleanup() {
  log_section "TEARDOWN"
  if [[ -n "${AGENTMEMORY_PID}" ]]; then
    log "Stopping agentmemory (PID ${AGENTMEMORY_PID})..."
    kill "${AGENTMEMORY_PID}" 2>/dev/null || true
    sleep 2
    # iii-engine child may linger — kill by port
    lsof -ti :3111 2>/dev/null | xargs kill -9 2>/dev/null || true
    log "agentmemory stopped"
  fi
  if [[ "${DOCKER_STARTED}" == "1" ]]; then
    log "Running docker compose down..."
    docker compose -f "${COMPOSE_FILE}" down 2>/dev/null || true
    log "docker compose down complete"
  fi
  log "Cleanup done."
}

trap cleanup EXIT INT TERM

# 2a. agentmemory
if system_enabled "agentmemory"; then
  if timeout 3 curl -sf --max-time 2 http://localhost:3111/agentmemory/livez > /dev/null 2>&1; then
    log "agentmemory: already running on :3111 — reusing"
  else
    if command -v agentmemory > /dev/null 2>&1; then
      log "agentmemory: starting daemon (iii-engine auto-installs on first run)..."
      log "  NOTE: first-ever run may take 60-120s for iii-engine download"
      agentmemory > "${OUTPUT_DIR}/agentmemory-daemon.log" 2>&1 &
      AGENTMEMORY_PID=$!
      log "agentmemory PID: ${AGENTMEMORY_PID}"
    else
      log "WARN: agentmemory not installed — removing from run"
      SYSTEMS="${SYSTEMS//agentmemory/}"
      SYSTEMS="${SYSTEMS//,,/,}"
      SYSTEMS="${SYSTEMS#,}"
      SYSTEMS="${SYSTEMS%,}"
    fi
  fi
fi

# 2b. Docker (Zep + optional Letta)
NEED_DOCKER=0
for dock_sys in zep letta; do
  system_enabled "${dock_sys}" && NEED_DOCKER=1
done

if [[ "${NEED_DOCKER}" == "1" && "${DOCKER_UP}" == "1" ]]; then
  # Build profile args
  PROFILE_ARGS=""
  for profile in ${DOCKER_PROFILES//,/ }; do
    PROFILE_ARGS="${PROFILE_ARGS} --profile ${profile}"
  done

  # Check if already running
  ZEP_ALREADY_UP=0
  if timeout 3 curl -sf --max-time 2 http://localhost:8000/healthz > /dev/null 2>&1; then
    ZEP_ALREADY_UP=1
    log "Zep: already running on :8000 — reusing"
  fi

  if [[ "${ZEP_ALREADY_UP}" == "0" ]]; then
    log "docker compose: starting (profiles: ${DOCKER_PROFILES})..."
    # shellcheck disable=SC2086
    docker compose -f "${COMPOSE_FILE}" ${PROFILE_ARGS} up -d 2>&1 | tail -5
    DOCKER_STARTED=1
    log "docker compose: services started"
  fi
fi

# ---------------------------------------------------------------------------
# STAGE 3: Wait for health
# ---------------------------------------------------------------------------

log_section "HEALTH CHECKS"

wait_for() {
  local name="$1"
  local url="$2"
  local timeout_sec="${3:-120}"
  local interval=5
  local elapsed=0

  log "Waiting for ${name} at ${url} (timeout: ${timeout_sec}s)..."
  while ! timeout 5 curl -sf --max-time 3 "${url}" > /dev/null 2>&1; do
    if [[ "${elapsed}" -ge "${timeout_sec}" ]]; then
      log "TIMEOUT: ${name} not healthy after ${timeout_sec}s — skipping"
      return 1
    fi
    sleep "${interval}"
    elapsed=$((elapsed + interval))
  done
  log "OK  ${name} healthy (${elapsed}s)"
  return 0
}

# agentmemory health
if system_enabled "agentmemory"; then
  if ! wait_for "agentmemory" "http://localhost:3111/agentmemory/livez" 300; then
    log "WARN: agentmemory not healthy — removing from run"
    SYSTEMS="${SYSTEMS//agentmemory/}"
    SYSTEMS="${SYSTEMS//,,/,}"
    SYSTEMS="${SYSTEMS#,}"
    SYSTEMS="${SYSTEMS%,}"
  fi
fi

# Zep health
if system_enabled "zep"; then
  if ! wait_for "zep" "http://localhost:8000/healthz" 120; then
    log "WARN: Zep not healthy — removing from run"
    SYSTEMS="${SYSTEMS//zep/}"
    SYSTEMS="${SYSTEMS//,,/,}"
    SYSTEMS="${SYSTEMS#,}"
    SYSTEMS="${SYSTEMS%,}"
  fi
fi

# Letta health (optional)
if system_enabled "letta"; then
  if ! wait_for "letta" "http://localhost:8283/v1/health" 120; then
    log "WARN: Letta not healthy — removing from run"
    SYSTEMS="${SYSTEMS//letta/}"
    SYSTEMS="${SYSTEMS//,,/,}"
    SYSTEMS="${SYSTEMS#,}"
    SYSTEMS="${SYSTEMS%,}"
  fi
fi

log ""
log "Systems ready for run: ${SYSTEMS}"

# ---------------------------------------------------------------------------
# STAGE 4: Run runner.py — one system at a time (cheapest first)
# ---------------------------------------------------------------------------

log_section "Q4 RUN — ${SYSTEMS} × locomo,longmemeval × ${LIMIT} queries"

ORDERED_SYSTEMS=()
for sys in nox_mem mem0 zep letta agentmemory; do
  system_enabled "${sys}" && ORDERED_SYSTEMS+=("${sys}")
done

log "Execution order: ${ORDERED_SYSTEMS[*]:-none}"
log ""

RUN_START_EPOCH="$(date +%s)"

for sys in "${ORDERED_SYSTEMS[@]}"; do
  log_section "Running system: ${sys}"
  SYS_START="$(date +%s)"

  # Per-system wall-clock timeout (setup=300s + 60s/query × 2 datasets × limit)
  SETUP_TIMEOUT=300
  QUERY_TIMEOUT=$(( 60 * LIMIT * 2 ))
  SYSTEM_TIMEOUT=$(( SETUP_TIMEOUT + QUERY_TIMEOUT ))

  log "Timeout: ${SYSTEM_TIMEOUT}s (setup 300s + 60s × ${LIMIT}q × 2 datasets)"

  if timeout "${SYSTEM_TIMEOUT}" \
      "${VENV_PYTHON}" "${Q4_DIR}/runner.py" \
        --systems "${sys}" \
        --datasets locomo,longmemeval \
        --limit "${LIMIT}" \
        --output "${OUTPUT_DIR}"; then
    SYS_ELAPSED=$(( $(date +%s) - SYS_START ))
    log "[${sys}] DONE in ${SYS_ELAPSED}s"
  else
    SYS_ELAPSED=$(( $(date +%s) - SYS_START ))
    log "[${sys}] FAILED or TIMED OUT after ${SYS_ELAPSED}s — continuing to next system"
  fi

  # Check output file landed
  if [[ -f "${OUTPUT_DIR}/${sys}.json" ]]; then
    QUERY_COUNT="$(python3 -c "import json; d=json.load(open('${OUTPUT_DIR}/${sys}.json')); print(len(d.get('queries',[])))" 2>/dev/null || echo '?')"
    log "[${sys}] output/${sys}.json — ${QUERY_COUNT} query records"
  else
    log "[${sys}] WARNING: output/${sys}.json not found"
  fi

  echo "" | tee -a "${LOG_FILE}"
done

RUN_ELAPSED=$(( $(date +%s) - RUN_START_EPOCH ))
log "All systems done in $((RUN_ELAPSED / 60))min $((RUN_ELAPSED % 60))s"

# ---------------------------------------------------------------------------
# STAGE 5: Aggregate → COMPARISON.md
# ---------------------------------------------------------------------------

log_section "AGGREGATE"

COMPARISON_DEST="${REPO_ROOT}/docs/COMPARISON.md"

if "${VENV_PYTHON}" "${Q4_DIR}/aggregate.py" --output "${OUTPUT_DIR}"; then
  log "aggregate.py complete"
  if [[ -f "${OUTPUT_DIR}/_aggregate.md" ]]; then
    cp "${OUTPUT_DIR}/_aggregate.md" "${COMPARISON_DEST}"
    log "COMPARISON.md updated: ${COMPARISON_DEST}"
  else
    log "WARN: _aggregate.md not produced — check aggregate.py output"
  fi
else
  log "WARN: aggregate.py exited non-zero — manual review needed"
fi

# ---------------------------------------------------------------------------
# STAGE 6: Summary
# ---------------------------------------------------------------------------

log_section "SUMMARY"

TOTAL_ELAPSED=$(( $(date +%s) - RUN_START_EPOCH ))
log "Wall-clock total: $((TOTAL_ELAPSED / 60))min $((TOTAL_ELAPSED % 60))s"
log "Estimated cost:   \$${ESTIMATED_COST_USD}"
log ""
log "Output files:"
ls -lh "${OUTPUT_DIR}"/*.json 2>/dev/null | awk '{print "  " $5 "\t" $NF}' || log "  (none)"
log ""
log "Log: ${LOG_FILE}"
log ""
log "Next: review ${COMPARISON_DEST}"
log "      git add docs/COMPARISON.md eval/q4-comparison/output/"
log "      git commit -m 'feat(q4): Sat Q4 run results $(date -u +%Y-%m-%d)'"

# cleanup trap fires on EXIT
