#!/bin/bash
# Health probe — runs every 5 min, checks all critical services
# Circuit breaker: stops restarting after 3 failures
LOG="/var/log/nox-health.log"
CIRCUIT_FILE="/tmp/openclaw-circuit-open"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# Source env so NOX_API_PORT matches the bound port. Hardcoded 18800 caused
# a 5-min restart loop after the service moved to 18802 to dodge a port squatter.
if [ -f /root/.openclaw/.env ]; then
    set -a
    . /root/.openclaw/.env
    set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

FAILED=0
ALERTS=""

# 1. Gateway port
if ss -tlnp | grep -q ':18789'; then
    log "OK: Gateway port 18789"
else
    log "FAIL: Gateway port 18789 not listening"
    ALERTS="${ALERTS}Gateway DOWN. "
    FAILED=1

    # Circuit breaker check
    if [ -f "$CIRCUIT_FILE" ]; then
        log "CIRCUIT OPEN: Not restarting gateway. Manual intervention required."
    else
        FAIL_COUNT=$(systemctl show openclaw-gateway -p NRestarts --value 2>/dev/null || echo 0)
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

# 2. nox-mem API
if curl -sf --max-time 3 "http://127.0.0.1:${NOX_API_PORT}/api/health" > /dev/null 2>&1; then
    log "OK: nox-mem API port ${NOX_API_PORT}"
else
    log "WARN: nox-mem API not responding on ${NOX_API_PORT}, restarting"
    systemctl restart nox-mem-api 2>/dev/null
fi

# 3. Disk space
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 85 ]; then
    log "WARN: Disk at ${DISK_PCT}%"
    ALERTS="${ALERTS}Disk ${DISK_PCT}%. "
fi

# 4. SQLite readable
DB=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
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
if [ "$FREE_MB" -lt 1024 ]; then
    log "WARN: Low memory (${FREE_MB}MB available)"
    ALERTS="${ALERTS}Low RAM ${FREE_MB}MB. "
fi

# Alert via Discord if any failures
if [ -n "$ALERTS" ] && [ -n "$DISCORD_WEBHOOK" ]; then
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
        -d "{\"content\": \"🚨 VPS Alert: ${ALERTS}\"}" > /dev/null 2>&1
fi

# Clear circuit breaker if gateway is healthy
if [ $FAILED -eq 0 ] && [ -f "$CIRCUIT_FILE" ]; then
    rm -f "$CIRCUIT_FILE"
    log "Circuit breaker cleared — gateway healthy"
fi
