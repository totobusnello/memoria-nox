#!/bin/bash
# Health probe — runs every 5 min via cron, checks all critical services.
#
# Circuit breakers: gateway stops restarting after 3 failures; nox-mem-api stops
# after 3 restarts in a rolling hour (2026-08-19 — previously unbounded).
#
# nox-mem-api restart policy (rewritten 2026-08-19 after 4 restarts/h):
#   - "not listening + unit inactive"  → restart immediately (nothing to kill)
#   - "listening but HTTP fails/hangs" → restart only after 2 consecutive probes
#   - "unit activating"                → never restart (boot takes ~30s)
#   - "HTTP 4xx/5xx from a live process" → never restart, alert instead
#   - always: 10-min cooldown + max 3 restarts/hour + evidence written to the ledger
# Rationale in staged/health-probe-restart-loop/README.md.

set -u

# --- paths (overridable for tests) ---
LOG="${NOX_HEALTH_LOG:-/var/log/nox-health.log}"
STATE_DIR="${NOX_STATE_DIR:-/var/lib/nox-health}"
ENV_FILE="${NOX_ENV_FILE:-/root/.openclaw/.env}"
DB="${NOX_DB_PATH:-/root/.openclaw/workspace/tools/nox-mem/nox-mem.db}"
CIRCUIT_FILE="${NOX_GATEWAY_CIRCUIT_FILE:-/tmp/openclaw-circuit-open}"

API_CIRCUIT_FILE="${STATE_DIR}/api-circuit-open"
API_FAIL_COUNTER="${STATE_DIR}/api-consecutive-fails"
API_RESTART_LEDGER="${STATE_DIR}/api-restarts.log"

# --- tunables ---
# 3s was the old timeout and it could not tell "dead" from "busy": /api/health
# does COUNT/JOIN over ~95k chunks plus per-service `systemctl show` calls, and
# p50 query latency in prod is already ~1.5s. morning-report uses 5s, canary 15s.
API_TIMEOUT="${NOX_PROBE_API_TIMEOUT:-8}"
# Consecutive failed probes required before restarting a *listening* API.
# Keep threshold × cron interval in the 10–20 min range (2 at */5, 2 at */10).
FAIL_THRESHOLD="${NOX_PROBE_FAIL_THRESHOLD:-2}"
API_COOLDOWN="${NOX_PROBE_API_COOLDOWN:-600}"          # min seconds between restarts
API_MAX_RESTARTS_HOUR="${NOX_PROBE_API_MAX_RESTARTS:-3}" # circuit opens above this
API_BOOT_WAIT="${NOX_PROBE_API_BOOT_WAIT:-45}"         # readiness wait after restart

DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# Source env so NOX_API_PORT matches the bound port. Hardcoded 18800 caused
# a 5-min restart loop after the service moved to 18802 to dodge a port squatter.
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

mkdir -p "$STATE_DIR" 2>/dev/null || true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

NOW=$(date +%s)
FAILED=0
GATEWAY_OK=1
ALERTS=""

# Defaults so `set -u` holds even on paths that never probe the API.
API_HTTP="000"
API_CURL_RC="0"
PORT_BOUND_DESC="unknown"
UNIT_STATE="unknown"

# 1. Gateway port
if ss -tlnp 2>/dev/null | grep -q ':18789'; then
    log "OK: Gateway port 18789"
else
    log "FAIL: Gateway port 18789 not listening"
    ALERTS="${ALERTS}Gateway DOWN. "
    FAILED=1
    GATEWAY_OK=0

    # Circuit breaker check
    if [ -f "$CIRCUIT_FILE" ]; then
        log "CIRCUIT OPEN: Not restarting gateway. Manual intervention required."
    else
        FAIL_COUNT=$(systemctl show openclaw-gateway -p NRestarts --value 2>/dev/null || echo 0)
        case "$FAIL_COUNT" in ''|*[!0-9]*) FAIL_COUNT=0 ;; esac
        if [ "$FAIL_COUNT" -gt 3 ]; then
            touch "$CIRCUIT_FILE"
            log "CIRCUIT OPENED: Gateway exceeded 3 restarts. Touch $CIRCUIT_FILE removed to re-enable."
            ALERTS="${ALERTS}CIRCUIT BREAKER OPEN. "
        else
            log "Restarting gateway (attempt $FAIL_COUNT)"
            systemctl restart openclaw-gateway
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 2. nox-mem API
#
# A restart is not free: it kills writes mid-flight (see INCIDENTS 2026-04-18,
# 288 restarts/day). So classify first, restart only for states a restart fixes.
# ---------------------------------------------------------------------------

api_port_bound() {
    command -v ss > /dev/null 2>&1 || return 2   # 2 = unknown
    ss -tln 2>/dev/null | grep -q ":${NOX_API_PORT}[[:space:]]"
}

api_unit_state() {
    systemctl is-active nox-mem-api 2>/dev/null || true
}

# Sets API_HTTP / API_CURL_RC. Returns 0 only on HTTP 200.
# --noproxy: `set -a; . .env` exports any http_proxy/ALL_PROXY defined there and
# curl would honour it for 127.0.0.1 unless NO_PROXY happens to cover loopback.
api_probe_once() {
    local timeout="$1" out rc
    out=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' --max-time "$timeout" \
          "http://127.0.0.1:${NOX_API_PORT}/api/health" 2>/dev/null)
    rc=$?
    API_HTTP="${out:-000}"
    API_CURL_RC="$rc"
    [ "$rc" -eq 0 ] && [ "$API_HTTP" = "200" ]
}

api_restarts_last_hour() {
    [ -f "$API_RESTART_LEDGER" ] || { echo 0; return; }
    awk -v cutoff="$((NOW - 3600))" '$1 ~ /^[0-9]+$/ && $1 >= cutoff' "$API_RESTART_LEDGER" \
        | wc -l | tr -d ' '
}

api_last_restart_epoch() {
    [ -f "$API_RESTART_LEDGER" ] || { echo 0; return; }
    awk '$1 ~ /^[0-9]+$/ {last=$1} END {print last+0}' "$API_RESTART_LEDGER"
}

api_read_fails() {
    local v
    v=$(cat "$API_FAIL_COUNTER" 2>/dev/null || echo 0)
    case "$v" in ''|*[!0-9]*) v=0 ;; esac
    echo "$v"
}

# Restart + evidence. The ledger is what morning-report reads to say
# "probe restarted it" instead of guessing "probe likely broken again".
api_restart() {
    local reason="$1"
    printf '%s %s %s http=%s rc=%s\n' \
        "$NOW" "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$reason" "${API_HTTP:-000}" "${API_CURL_RC:-?}" \
        >> "$API_RESTART_LEDGER"

    log "RESTART: nox-mem-api (reason=${reason} http=${API_HTTP:-000} curl_rc=${API_CURL_RC:-?} port_bound=${PORT_BOUND_DESC} unit=${UNIT_STATE})"
    systemctl restart nox-mem-api 2>/dev/null

    # Wait for readiness so the next probe (5 min out) never lands on a booting
    # process — a cold start loads sqlite-vec over 95k×3072d and takes ~30s.
    local waited=0
    while [ "$waited" -lt "$API_BOOT_WAIT" ]; do
        sleep 3
        waited=$((waited + 3))
        if api_probe_once "$API_TIMEOUT"; then
            log "RESTART OK: nox-mem-api healthy after ${waited}s"
            echo 0 > "$API_FAIL_COUNTER"
            return 0
        fi
    done
    log "RESTART FAILED: nox-mem-api still not healthy after ${API_BOOT_WAIT}s (http=${API_HTTP:-000} curl_rc=${API_CURL_RC:-?})"
    ALERTS="${ALERTS}nox-mem-api did not come back after restart. "
    return 1
}

if api_probe_once "$API_TIMEOUT"; then
    log "OK: nox-mem API port ${NOX_API_PORT}"
    echo 0 > "$API_FAIL_COUNTER"
    if [ -f "$API_CIRCUIT_FILE" ]; then
        rm -f "$API_CIRCUIT_FILE"
        log "API circuit breaker cleared — nox-mem-api healthy"
    fi
else
    # One in-run retry absorbs a single slow/transient response before it counts
    # against the consecutive-failure budget.
    sleep 2

    if api_probe_once "$API_TIMEOUT"; then
        log "OK: nox-mem API port ${NOX_API_PORT} (recovered on retry)"
        echo 0 > "$API_FAIL_COUNTER"
    else
        api_port_bound; BOUND_RC=$?
        case "$BOUND_RC" in
            0) PORT_BOUND_DESC="yes" ;;
            1) PORT_BOUND_DESC="no" ;;
            *) PORT_BOUND_DESC="unknown" ;;
        esac
        UNIT_STATE="$(api_unit_state)"

        FAILS=$(( $(api_read_fails) + 1 ))
        echo "$FAILS" > "$API_FAIL_COUNTER"

        # Classify. Only "dead" and "hung" are restartable states.
        if [ "$API_CURL_RC" -eq 0 ]; then
            CLASS="degraded"      # process answered, but not 200
        elif [ "$PORT_BOUND_DESC" = "no" ]; then
            CLASS="dead"
        elif [ "$API_CURL_RC" -eq 28 ]; then
            CLASS="hung"
        else
            CLASS="unreachable"
        fi

        log "WARN: nox-mem API ${CLASS} (http=${API_HTTP} curl_rc=${API_CURL_RC} port_bound=${PORT_BOUND_DESC} unit=${UNIT_STATE} consecutive=${FAILS})"

        LAST_RESTART=$(api_last_restart_epoch)
        SINCE_RESTART=$((NOW - LAST_RESTART))
        RESTARTS_HOUR=$(api_restarts_last_hour)

        if [ "$UNIT_STATE" = "activating" ]; then
            # A cold start in progress. Restarting here is what turns one bad
            # probe into a storm.
            log "SKIP RESTART: unit is activating (boot in progress)"
        elif [ "$CLASS" = "degraded" ]; then
            # HTTP 4xx/5xx from a live process means a subsystem is broken (DB,
            # schema, embeddings). A restart does not fix it and costs writes.
            log "SKIP RESTART: API alive but returning HTTP ${API_HTTP} — restart would not fix it"
            ALERTS="${ALERTS}nox-mem-api HTTP ${API_HTTP}. "
        elif [ -f "$API_CIRCUIT_FILE" ]; then
            log "API CIRCUIT OPEN: not restarting nox-mem-api. Remove ${API_CIRCUIT_FILE} to re-enable."
            ALERTS="${ALERTS}nox-mem-api CIRCUIT OPEN. "
        elif [ "$RESTARTS_HOUR" -ge "$API_MAX_RESTARTS_HOUR" ]; then
            touch "$API_CIRCUIT_FILE"
            log "API CIRCUIT OPENED: ${RESTARTS_HOUR} restarts in the last hour (max ${API_MAX_RESTARTS_HOUR}). Manual intervention required."
            ALERTS="${ALERTS}nox-mem-api CIRCUIT OPEN (${RESTARTS_HOUR} restarts/h). "
        elif [ "$LAST_RESTART" -gt 0 ] && [ "$SINCE_RESTART" -lt "$API_COOLDOWN" ]; then
            log "SKIP RESTART: cooldown (${SINCE_RESTART}s since last restart, need ${API_COOLDOWN}s)"
        elif [ "$CLASS" = "dead" ]; then
            # Nothing is listening: no in-flight writes to kill, recover now.
            api_restart "dead"
        elif [ "$FAILS" -ge "$FAIL_THRESHOLD" ]; then
            api_restart "$CLASS"
        else
            log "SKIP RESTART: ${CLASS} on probe ${FAILS}/${FAIL_THRESHOLD} — waiting for confirmation"
        fi
    fi
fi

# 3. Disk space
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
case "$DISK_PCT" in ''|*[!0-9]*) DISK_PCT=0 ;; esac
if [ "$DISK_PCT" -gt 85 ]; then
    log "WARN: Disk at ${DISK_PCT}%"
    ALERTS="${ALERTS}Disk ${DISK_PCT}%. "
fi

# 4. SQLite readable
if sqlite3 "$DB" "SELECT count(*) FROM chunks LIMIT 1" > /dev/null 2>&1; then
    log "OK: SQLite DB readable"
else
    log "FAIL: SQLite DB unreadable"
    ALERTS="${ALERTS}SQLite FAIL. "
    FAILED=1
fi

# 5. Node.js wrapper integrity
if [ ! -f /usr/bin/node.real ]; then
    log "CRITICAL: node.real missing — wrapper broken"
    ALERTS="${ALERTS}Node wrapper BROKEN. "
    FAILED=1
fi

# 6. Memory check (warn if <1GB free)
FREE_MB=$(free -m | awk '/Mem:/{print $7}')
case "$FREE_MB" in ''|*[!0-9]*) FREE_MB=99999 ;; esac
if [ "$FREE_MB" -lt 1024 ]; then
    log "WARN: Low memory (${FREE_MB}MB available)"
    ALERTS="${ALERTS}Low RAM ${FREE_MB}MB. "
fi

# Alert via Discord if any failures
if [ -n "$ALERTS" ] && [ -n "$DISCORD_WEBHOOK" ]; then
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
        -d "{\"content\": \"🚨 VPS Alert: ${ALERTS}\"}" > /dev/null 2>&1
fi

# Clear the gateway circuit breaker when the *gateway* is healthy. It used to
# key off $FAILED, so an unreadable DB or a missing node wrapper kept the
# gateway breaker latched open even though the gateway was fine.
if [ "$GATEWAY_OK" -eq 1 ] && [ -f "$CIRCUIT_FILE" ]; then
    rm -f "$CIRCUIT_FILE"
    log "Circuit breaker cleared — gateway healthy"
fi

exit 0
