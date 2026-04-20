#!/bin/bash
# check-nox-mem.sh — Local one-shot health summary of the nox-mem system on the VPS.
# Runs all 6 post-Tier-0+1 verification checks via SSH and prints a colored summary.
# Safe to run any time — read-only on the VPS.

set -u

VPS="root@100.87.8.44"

GREEN='\033[32m'; RED='\033[31m'; YELLOW='\033[33m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET} $1"; }
bad()  { echo -e "${RED}✗${RESET} $1"; }

echo -e "${BOLD}nox-mem health check${RESET} — $(date '+%Y-%m-%d %H:%M')"
echo ""

# --- single SSH round-trip gathers everything ---
DATA=$(ssh -o ConnectTimeout=5 "$VPS" 'bash -s' <<'REMOTE'
set -u
source /root/.openclaw/.env 2>/dev/null || true
PORT="${NOX_API_PORT:-18800}"

HEALTH=$(curl -sf --max-time 5 "http://127.0.0.1:${PORT}/api/health" 2>/dev/null || echo "{}")
echo "HEALTH_JSON=${HEALTH}"
echo "RESTARTS_1H=$( journalctl -u nox-mem-api --since '1 hour ago' --no-pager 2>/dev/null | grep -c 'Started nox-mem-api' || echo 0 )"
echo "RESTARTS_24H=$( journalctl -u nox-mem-api --since '24 hours ago' --no-pager 2>/dev/null | grep -c 'Started nox-mem-api' || echo 0 )"
echo "RATELIMITS_24H=$( journalctl --since '24 hours ago' --no-pager 2>/dev/null | grep -cE 'Resource exhausted' || echo 0 )"
echo "TRIGGER_OK=$( sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='trg_chunks_delete_cascade';" 2>/dev/null || echo '?' )"
echo "CANARY_LAST=$( tail -1 /var/log/nox-canary.log 2>/dev/null | sed 's/^\[[^]]*\] //' )"
echo "MORNING_LAST=$( tail -1 /var/log/nox-morning.log 2>/dev/null | sed 's/^\[[^]]*\] //' )"
echo "NIGHTLY_LAST=$( tail -1 /var/log/nox-maintenance.log 2>/dev/null | head -c 200 )"
REMOTE
)

if [ -z "$DATA" ]; then
    bad "SSH to $VPS failed — can't reach VPS"
    exit 1
fi

# --- parse output ---
HEALTH_JSON=$(echo "$DATA" | grep '^HEALTH_JSON=' | cut -d= -f2-)
RESTARTS_1H=$(echo "$DATA" | grep '^RESTARTS_1H=' | cut -d= -f2)
RESTARTS_24H=$(echo "$DATA" | grep '^RESTARTS_24H=' | cut -d= -f2)
RATELIMITS=$(echo "$DATA" | grep '^RATELIMITS_24H=' | cut -d= -f2)
TRIGGER_OK=$(echo "$DATA" | grep '^TRIGGER_OK=' | cut -d= -f2)
CANARY_LAST=$(echo "$DATA" | grep '^CANARY_LAST=' | cut -d= -f2-)
MORNING_LAST=$(echo "$DATA" | grep '^MORNING_LAST=' | cut -d= -f2-)
NIGHTLY_LAST=$(echo "$DATA" | grep '^NIGHTLY_LAST=' | cut -d= -f2-)

if [ -z "$HEALTH_JSON" ] || [ "$HEALTH_JSON" = "{}" ]; then
    bad "/api/health unreachable on VPS — nox-mem-api down?"
    echo "  raw: $HEALTH_JSON"
    exit 2
fi

# --- extract JSON fields with python ---
read -r EMBEDDED TOTAL ORPHANS PROCEDURES HITS ENTRIES GW_OK <<< "$(echo "$HEALTH_JSON" | python3 -c '
import sys, json
d = json.load(sys.stdin)
vc = d.get("vectorCoverage", {})
rc = d.get("reflectCache", {})
svc = d.get("services", {})
print(
    vc.get("embedded", "?"),
    vc.get("total", "?"),
    vc.get("orphans", "?"),
    d.get("procedures", "?"),
    rc.get("total_hits", "?"),
    rc.get("entries", "?"),
    svc.get("openclaw-gateway", "?"),
)
')"

# --- print report ---
echo -e "${BOLD}Memory layer${RESET}"
if [ "$EMBEDDED" = "$TOTAL" ] && [ "$ORPHANS" = "0" ]; then
    ok "embeddings ${EMBEDDED}/${TOTAL} (0 orphans)"
else
    bad "embeddings ${EMBEDDED}/${TOTAL}, orphans=${ORPHANS}"
fi

if [ "$TRIGGER_OK" = "1" ]; then
    ok "CASCADE trigger active"
else
    bad "CASCADE trigger MISSING (reinstall required)"
fi

echo ""
echo -e "${BOLD}Reflect cache${RESET}"
ok "${ENTRIES} entries, ${HITS} hits"

echo ""
echo -e "${BOLD}Reliability (last 1h / 24h)${RESET}"
if [ "$RESTARTS_1H" -le 2 ] 2>/dev/null; then
    ok "restarts 1h: ${RESTARTS_1H}, 24h: ${RESTARTS_24H}"
else
    bad "restarts 1h: ${RESTARTS_1H} (>2 suggests probe broken)"
fi

if [ "$RATELIMITS" -le 20 ] 2>/dev/null; then
    ok "Gemini 429 count 24h: ${RATELIMITS}"
else
    warn "Gemini 429 count 24h: ${RATELIMITS} (elevated)"
fi

echo ""
echo -e "${BOLD}Automation logs${RESET}"
case "$CANARY_LAST" in
    OK:*) ok "canary (06:00): $CANARY_LAST" ;;
    "")   warn "canary (06:00): no log yet (may not have run today)" ;;
    *)    bad "canary (06:00): $CANARY_LAST" ;;
esac

if [ -n "$MORNING_LAST" ]; then
    echo "  morning report: $MORNING_LAST"
else
    warn "morning report (06:30): no log yet"
fi

if [ -n "$NIGHTLY_LAST" ]; then
    echo "  nightly (23:00): $NIGHTLY_LAST"
fi

echo ""
echo -e "${BOLD}Services${RESET}"
if [ "$GW_OK" = "True" ]; then
    ok "openclaw-gateway: active"
else
    bad "openclaw-gateway: $GW_OK"
fi

echo ""
echo -e "${BOLD}Next step${RESET}"
if [ "$EMBEDDED" = "$TOTAL" ] && [ "$ORPHANS" = "0" ] && [ "$TRIGGER_OK" = "1" ] && [ "${RESTARTS_1H:-99}" -le 2 ] 2>/dev/null; then
    echo -e "  ${GREEN}All green — safe to proceed to Tier 3 (observability)${RESET}"
else
    echo -e "  ${RED}Red flags present — investigate before proceeding${RESET}"
    echo "  see: plans/2026-04-18-tier0-tier1-session-log.md section 'Se algo vermelho'"
fi
