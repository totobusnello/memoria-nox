#!/bin/bash
# morning-report.sh — Daily 06:30 UTC summary to Discord.
# Runs the 6-step post-Tier-0+1 verification checklist and posts a single
# colored summary. Read-only — never fixes anything automatically.

set -u

LOG="/var/log/nox-morning.log"
DB="/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"

if [ -f /root/.openclaw/.env ]; then
    set -a; . /root/.openclaw/.env; set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# --- gather all signals ---
# Restarts: 1h window reflects CURRENT probe health; 24h contaminates with pre-fix history.
# grep -c returns "0" with exit 1 when no matches — `|| true` to always succeed.
RESTARTS=$( { journalctl -u nox-mem-api --since "1 hour ago" --no-pager 2>/dev/null | grep -c "Started nox-mem-api" || true; } | head -1 )
# Integer guard — if RESTARTS isn't purely numeric, force "?"
case "$RESTARTS" in ''|*[!0-9]*) RESTARTS="?" ;; esac

RATELIMITS=$( { journalctl --since "24 hours ago" --no-pager 2>/dev/null | grep -cE "Resource exhausted" || true; } | head -1 )
case "$RATELIMITS" in ''|*[!0-9]*) RATELIMITS="?" ;; esac

HEALTH=$(curl -sf --max-time 5 "http://127.0.0.1:${NOX_API_PORT}/api/health" 2>/dev/null || echo "{}")
EMBEDDED=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("embedded","?"))' 2>/dev/null || echo "?")
TOTAL=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("total","?"))' 2>/dev/null || echo "?")
ORPHANS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("orphans","?"))' 2>/dev/null || echo "?")
PROCEDURES=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("procedures","?"))' 2>/dev/null || echo "?")
CACHE_HITS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("reflectCache",{}).get("total_hits","?"))' 2>/dev/null || echo "?")

TRIGGER_OK=$(sqlite3 "$DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='trg_chunks_delete_cascade';" 2>/dev/null || echo "?")

# Canary result: read the latest line from the 06:00 run
CANARY_LINE=$(tail -1 /var/log/nox-canary.log 2>/dev/null | sed 's/^\[[^]]*\] //' || echo "no canary log")

# Nightly-maintenance: check log for errors in last run
NIGHTLY_ERRORS=$( { tail -100 /var/log/nox-maintenance.log 2>/dev/null | grep -icE "error|fail|fatal" || true; } | head -1 )
case "$NIGHTLY_ERRORS" in ''|*[!0-9]*) NIGHTLY_ERRORS="?" ;; esac
NIGHTLY_LAST=$(tail -1 /var/log/nox-maintenance.log 2>/dev/null | head -c 200)

# --- classify signals ---
RED=0
YELLOW=0
DETAILS=""

# vectorCoverage classification:
#   Orphans > 0 = RED always (cascade trigger failed)
#   Embedded == Total = green
#   Gap <= 10% = YELLOW (transient; watcher ingested chunks not yet vectorized)
#   Gap > 10% = RED (real drift, vectorize cron not running or failing)
if [ "$ORPHANS" != "0" ] && [ "$ORPHANS" != "?" ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 vectorCoverage: ${ORPHANS} orphans (cascade trigger failed?)"
elif [ "$EMBEDDED" != "$TOTAL" ] && [ "$EMBEDDED" != "?" ] && [ "$TOTAL" != "?" ]; then
    # Compute gap percentage
    GAP_PCT=$(python3 -c "t=$TOTAL; e=$EMBEDDED; print(round((t-e)*100/max(t,1))) if t > 0 else 0" 2>/dev/null || echo "?")
    if [ "$GAP_PCT" = "?" ] || [ "$GAP_PCT" -gt 10 ] 2>/dev/null; then
        RED=$((RED+1))
        DETAILS="${DETAILS}\n🔴 vectorCoverage: ${EMBEDDED}/${TOTAL} embedded (${GAP_PCT}% gap — vectorize not running)"
    else
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 vectorCoverage: ${EMBEDDED}/${TOTAL} embedded (${GAP_PCT}% gap — transient, next vectorize catches up)"
    fi
fi

if [ "$RESTARTS" = "?" ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nox-mem-api restart count unavailable (journalctl failed)"
elif [ "$RESTARTS" -gt 2 ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 nox-mem-api restarted ${RESTARTS}x in last hour (probe likely broken again)"
elif [ "$RESTARTS" -gt 0 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nox-mem-api restarted ${RESTARTS}x in last hour"
fi

if [ "$RATELIMITS" = "?" ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Gemini 429 count unavailable"
elif [ "$RATELIMITS" -gt 100 ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 Gemini 429 count: ${RATELIMITS} in 24h (possible runaway loop)"
elif [ "$RATELIMITS" -gt 20 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Gemini 429 count: ${RATELIMITS} in 24h (elevated)"
fi

if [ "$TRIGGER_OK" != "1" ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 trg_chunks_delete_cascade trigger missing (CASCADE disabled)"
fi

if echo "$CANARY_LINE" | grep -q "^RED\|^FAIL"; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 Canary: ${CANARY_LINE}"
elif ! echo "$CANARY_LINE" | grep -q "^OK"; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Canary: ${CANARY_LINE}"
fi

if [ "$NIGHTLY_ERRORS" != "?" ] && [ "$NIGHTLY_ERRORS" -gt 5 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nightly-maintenance: ${NIGHTLY_ERRORS} errors in log tail"
fi

# --- format summary ---
if [ "$RED" -gt 0 ]; then
    HEADER="🚨 nox-mem morning report: **${RED} RED** / ${YELLOW} yellow"
elif [ "$YELLOW" -gt 0 ]; then
    HEADER="⚠️ nox-mem morning report: ${YELLOW} yellow / all else green"
else
    HEADER="✅ nox-mem morning report: all green"
fi

BODY="${HEADER}\n\`\`\`\nchunks embedded  : ${EMBEDDED}/${TOTAL} (orphans: ${ORPHANS})\nprocedures       : ${PROCEDURES}\nreflect hits     : ${CACHE_HITS}\nrestarts 1h      : ${RESTARTS}\ngemini 429 24h   : ${RATELIMITS}\ntrigger active   : $([ "$TRIGGER_OK" = "1" ] && echo yes || echo NO)\ncanary           : ${CANARY_LINE}\nnightly errors   : ${NIGHTLY_ERRORS}\n\`\`\`"

if [ -n "${DETAILS}" ]; then
    BODY="${BODY}\n**Details:**${DETAILS}"
fi

log "summary: red=${RED} yellow=${YELLOW} embedded=${EMBEDDED}/${TOTAL} restarts=${RESTARTS} rl=${RATELIMITS}"

if [ -n "${DISCORD_WEBHOOK:-}" ]; then
    # Discord max 2000 chars per message — truncate body safely
    CONTENT=$(echo -e "$BODY" | head -c 1900)
    # Build JSON payload via python to escape properly
    PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$CONTENT")
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1
    log "posted to Discord"
fi

# Exit code mirrors severity for external orchestration (0 green, 1 yellow, 2 red)
if [ "$RED" -gt 0 ]; then exit 2
elif [ "$YELLOW" -gt 0 ]; then exit 1
else exit 0
fi
