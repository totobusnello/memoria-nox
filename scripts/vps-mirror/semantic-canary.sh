#!/bin/bash
# semantic-canary.sh — Daily check that the semantic search layer is alive.
# Runs a natural-language query and verifies at least one result has match_type=semantic.
# If not, alert Discord — this catches silent regressions like the Apr 2026 vec_chunk_map
# orphan incident where hybrid search degraded to FTS-only without surfacing any error.

set -u

LOG="/var/log/nox-canary.log"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# Source env so NOX_API_PORT matches the bound port (same convention as health-probe)
if [ -f /root/.openclaw/.env ]; then
    set -a
    . /root/.openclaw/.env
    set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# Natural-language query that BM25 can't fully satisfy — forces semantic contribution
QUERY="how do we handle authentication and session management"

RESP=$(curl -sf --max-time 15 -G "http://127.0.0.1:${NOX_API_PORT}/api/search" \
    --data-urlencode "q=${QUERY}" \
    --data-urlencode "limit=10" 2>/dev/null)

if [ -z "$RESP" ]; then
    log "FAIL: /api/search did not respond on :${NOX_API_PORT}"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
            -d '{"content":"nox-mem canary: /api/search unreachable on port '"${NOX_API_PORT}"'"}' > /dev/null 2>&1
    fi
    exit 1
fi

# Count results and semantic matches via python (always available on this VPS)
SUMMARY=$(echo "$RESP" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if not isinstance(d, list):
        print("FORMAT_ERROR 0 0")
        sys.exit(0)
    total = len(d)
    semantic = sum(1 for r in d if isinstance(r, dict) and r.get("match_type") == "semantic")
    fts = sum(1 for r in d if isinstance(r, dict) and r.get("match_type") == "fts")
    print(f"OK {total} {semantic} {fts}")
except Exception as e:
    print(f"PARSE_ERROR 0 0 0")
' 2>/dev/null)

STATUS=$(echo "$SUMMARY" | awk '{print $1}')
TOTAL=$(echo "$SUMMARY" | awk '{print $2}')
SEMANTIC=$(echo "$SUMMARY" | awk '{print $3}')
FTS=$(echo "$SUMMARY" | awk '{print $4}')

if [ "$STATUS" != "OK" ]; then
    log "FAIL: parse/format error ($STATUS) — response head: $(echo "$RESP" | head -c 200)"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
            -d '{"content":"nox-mem canary: search response parse error — '"${STATUS}"'"}' > /dev/null 2>&1
    fi
    exit 2
fi

if [ "$TOTAL" = "0" ]; then
    log "FAIL: 0 results for canary query (DB empty or FTS broken)"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
            -d '{"content":"nox-mem canary: 0 search results — DB empty or FTS broken"}' > /dev/null 2>&1
    fi
    exit 3
fi

if [ "$SEMANTIC" = "0" ]; then
    log "RED: semantic=0 / total=${TOTAL} / fts=${FTS} — hybrid degraded to FTS-only"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
            -d '{"content":"nox-mem canary RED: semantic layer broken. total='"${TOTAL}"' semantic=0 fts='"${FTS}"'. Check /api/health vectorCoverage + vec_chunk_map orphans."}' > /dev/null 2>&1
    fi
    exit 4
fi

# Also verify /api/health.vectorCoverage hasn't developed orphans
HEALTH=$(curl -sf --max-time 5 "http://127.0.0.1:${NOX_API_PORT}/api/health" 2>/dev/null)
ORPHANS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("orphans",-1))' 2>/dev/null || echo "-1")

if [ "$ORPHANS" != "0" ] && [ "$ORPHANS" != "-1" ]; then
    log "RED: vectorCoverage.orphans=${ORPHANS} (trigger failed?)"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
            -d '{"content":"nox-mem canary RED: vec_chunk_map orphans='"${ORPHANS}"' — cascade trigger likely failed"}' > /dev/null 2>&1
    fi
    exit 5
fi

log "OK: total=${TOTAL} semantic=${SEMANTIC} fts=${FTS} orphans=${ORPHANS}"
exit 0
