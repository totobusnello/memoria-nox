#!/bin/bash
# semantic-canary.sh — Daily check that the semantic search layer is alive.
# Runs a natural-language query and verifies at least one result has match_type=semantic.
# If not, attempts self-heal via `nox-mem vectorize` before alerting Discord.
# This catches silent regressions like:
#   - Apr 2026 vec_chunk_map orphan incident (hybrid degraded to FTS-only, total>0/semantic=0)
#   - Apr 21 2026 reindex-wipe incident (DELETE FROM chunks cascaded, total=0)

set -u

LOG="/var/log/nox-canary.log"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# Source env so NOX_API_PORT matches the bound port (same convention as health-probe)
# AND so GEMINI_API_KEY is available if we need to self-heal via vectorize.
if [ -f /root/.openclaw/.env ]; then
    set -a
    . /root/.openclaw/.env
    set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

discord() {
    local msg="$1"
    [ -n "$DISCORD_WEBHOOK" ] || return 0
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
        -d "{\"content\":\"${msg}\"}" > /dev/null 2>&1 || true
}

# Natural-language query em PT-BR (corpus majoritariamente em português).
# Keywords existem no corpus ("memória", "knowledge graph") mas frase não bate
# literalmente com nenhum chunk, forçando semantic a contribuir.
# 2026-04-19: query anterior era em inglês ("authentication and session management"),
# gerando falso-positivo quando corpus cresceu e falso-negativo quando semantic degradou.
QUERY="como funciona a memória persistente e o knowledge graph do sistema"

run_query() {
    curl -sf --max-time 15 -G "http://127.0.0.1:${NOX_API_PORT}/api/search" \
        --data-urlencode "q=${QUERY}" \
        --data-urlencode "limit=10" \
        --data-urlencode "track=false" 2>/dev/null
}

parse_summary() {
    echo "$1" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if not isinstance(d, list):
        print("FORMAT_ERROR 0 0 0")
        sys.exit(0)
    total = len(d)
    semantic = sum(1 for r in d if isinstance(r, dict) and r.get("match_type") == "semantic")
    fts = sum(1 for r in d if isinstance(r, dict) and r.get("match_type") == "fts")
    print(f"OK {total} {semantic} {fts}")
except Exception:
    print("PARSE_ERROR 0 0 0")
' 2>/dev/null
}

# Self-heal: try to re-vectorize and re-query. Returns 0 if heal succeeded,
# 1 otherwise. Output goes to the canary log for post-mortem.
# Safeguards:
#   - Requires GEMINI_API_KEY to be set (already sourced from .env above).
#   - 5-minute timeout on vectorize so it can't hang the cron.
#   - Uses a /tmp lockfile to prevent concurrent heal attempts if canary runs
#     faster than vectorize (shouldn't happen — cron is hourly at most — but cheap insurance).
self_heal() {
    local reason="$1"
    local heal_lock=/tmp/nox-canary-heal.lock

    if [ -z "${GEMINI_API_KEY:-}" ]; then
        log "SELF-HEAL: skipped — GEMINI_API_KEY not set (check /root/.openclaw/.env)"
        return 1
    fi

    exec 201>"$heal_lock"
    if ! flock -n 201; then
        log "SELF-HEAL: skipped — another heal already running"
        return 1
    fi

    log "SELF-HEAL: starting vectorize (trigger=${reason})"
    local heal_out
    heal_out=$(cd /root/.openclaw/workspace/tools/nox-mem && \
        timeout 300 /usr/local/bin/nox-mem vectorize 2>&1 | tail -3)
    local heal_rc=$?
    log "SELF-HEAL: vectorize rc=${heal_rc} out=${heal_out}"

    if [ $heal_rc -ne 0 ]; then
        return 1
    fi

    # Re-run the canary query now that embeddings should be back
    local retry_resp retry_summary retry_status retry_total retry_semantic
    retry_resp=$(run_query)
    if [ -z "$retry_resp" ]; then
        log "SELF-HEAL: post-heal /api/search did not respond"
        return 1
    fi
    retry_summary=$(parse_summary "$retry_resp")
    retry_status=$(echo "$retry_summary" | awk '{print $1}')
    retry_total=$(echo "$retry_summary" | awk '{print $2}')
    retry_semantic=$(echo "$retry_summary" | awk '{print $3}')

    if [ "$retry_status" = "OK" ] && [ "$retry_total" != "0" ] && [ "$retry_semantic" != "0" ]; then
        log "SELF-HEAL: SUCCESS — total=${retry_total} semantic=${retry_semantic}"
        return 0
    fi

    log "SELF-HEAL: FAILED — post-heal total=${retry_total} semantic=${retry_semantic}"
    return 1
}

# Debounce: só alerta se 2 checagens consecutivas falharem (evita falso-positivo
# por restart transitório do processo Node, ~30s de boot).
# Usa lockfile com timestamp. Se falhar 1x, grava o timestamp e sai silenciosamente.
# Se falhar novamente dentro de 90min (3 janelas de 30min), aí sim alerta.
FAIL_STAMP=/tmp/nox-canary-fail.stamp
DEBOUNCE_WINDOW=5400  # 90 minutos em segundos

debounce_fail() {
    local reason="$1"
    local now
    now=$(date +%s)

    if [ -f "$FAIL_STAMP" ]; then
        local prev_time prev_reason
        prev_time=$(cut -d'|' -f1 "$FAIL_STAMP" 2>/dev/null || echo 0)
        prev_reason=$(cut -d'|' -f2- "$FAIL_STAMP" 2>/dev/null || echo "")
        local age=$(( now - prev_time ))
        if [ $age -le $DEBOUNCE_WINDOW ]; then
            log "FAIL(2): ${reason} (prev=${prev_reason} age=${age}s) — alertando Discord"
            rm -f "$FAIL_STAMP"
            return 0  # alerta real
        fi
    fi

    # Primeira falha ou stamp expirado — registra silenciosamente
    echo "${now}|${reason}" > "$FAIL_STAMP"
    log "FAIL(1): ${reason} — aguardando confirmação (debounce ${DEBOUNCE_WINDOW}s)"
    return 1  # não alerta ainda
}

RESP=$(run_query)

if [ -z "$RESP" ]; then
    if debounce_fail "unreachable:${NOX_API_PORT}"; then
        discord "nox-mem canary: /api/search unreachable on port ${NOX_API_PORT} (2x consecutivo)"
    fi
    exit 1
fi

# Serviço respondeu — limpa stamp de falha anterior (se houver)
rm -f "$FAIL_STAMP"

SUMMARY=$(parse_summary "$RESP")
STATUS=$(echo "$SUMMARY" | awk '{print $1}')
TOTAL=$(echo "$SUMMARY" | awk '{print $2}')
SEMANTIC=$(echo "$SUMMARY" | awk '{print $3}')
FTS=$(echo "$SUMMARY" | awk '{print $4}')

if [ "$STATUS" != "OK" ]; then
    log "FAIL: parse/format error ($STATUS) — response head: $(echo "$RESP" | head -c 200)"
    if debounce_fail "parse_error:${STATUS}"; then
        discord "nox-mem canary: search response parse error — ${STATUS} (2x consecutivo)"
    fi
    exit 2
fi

if [ "$TOTAL" = "0" ]; then
    # Most likely cause: chunks were deleted (reindex/consolidate) and cascade wiped
    # vec_chunks, leaving the PT-BR natural-language canary query with zero matches
    # (FTS can't match the phrase literally, semantic layer is empty).
    # Try self-heal before alerting.
    log "FAIL: 0 results for canary query (DB empty or FTS broken) — attempting self-heal"
    if self_heal "total=0"; then
        discord "nox-mem canary: **auto-healed** — vector layer was empty (likely reindex wipe), re-vectorized and recovered. Root cause should be investigated but service is back."
        exit 0
    fi
    discord "nox-mem canary: 0 search results AND self-heal FAILED — manual intervention needed. Check /health vectorCoverage and GEMINI_API_KEY."
    exit 3
fi

if [ "$SEMANTIC" = "0" ]; then
    # Same failure class as total=0, but with FTS still contributing (so TOTAL>0).
    # Canonical Apr 2026 vec_chunk_map orphan symptom.
    log "RED: semantic=0 / total=${TOTAL} / fts=${FTS} — hybrid degraded to FTS-only — attempting self-heal"
    if self_heal "semantic=0"; then
        discord "nox-mem canary: **auto-healed** — semantic layer was down (total=${TOTAL} semantic=0 fts=${FTS}), re-vectorized and recovered."
        exit 0
    fi
    discord "nox-mem canary RED: semantic layer broken AND self-heal FAILED. total=${TOTAL} semantic=0 fts=${FTS}. Check /health vectorCoverage + vec_chunk_map orphans."
    exit 4
fi

# Also verify /health.vectorCoverage hasn't developed orphans
HEALTH=$(curl -sf --max-time 5 "http://127.0.0.1:${NOX_API_PORT:-18802}/api/health" 2>/dev/null)
ORPHANS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("orphans",-1))' 2>/dev/null || echo "-1")

if [ "$ORPHANS" != "0" ] && [ "$ORPHANS" != "-1" ] && [ "${ORPHANS}" -gt 3 ] 2>/dev/null; then
    log "RED: vectorCoverage.orphans=${ORPHANS} (>3 threshold) — attempting self-heal"
    if self_heal "orphans=${ORPHANS}"; then
        log "SELF-HEAL: orphans resolved — no alert sent"
    else
        discord "nox-mem canary RED: vec_chunk_map orphans=${ORPHANS} (>3) AND self-heal FAILED — cascade trigger likely broken"
        exit 5
    fi
elif [ "$ORPHANS" != "0" ] && [ "$ORPHANS" != "-1" ]; then
    log "INFO: vectorCoverage.orphans=${ORPHANS} (<=3, within tolerance — watcher race condition)"
fi

log "OK: total=${TOTAL} semantic=${SEMANTIC} fts=${FTS} orphans=${ORPHANS}"
exit 0
