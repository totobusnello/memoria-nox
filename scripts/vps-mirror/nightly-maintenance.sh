#!/bin/bash
# nightly-maintenance.sh — Sequential nox-mem maintenance
# Replaces 20+ staggered cron entries with one orchestrated script
# Runs daily at 23:00, day-of-week logic inside

set -a

# Notify helper (added 2026-05-31 Frente C2)
source /root/.openclaw/scripts/notify-discord.sh

# Track start time (Frente C2 2026-05-31)
date +%s > /tmp/nox-maintenance-start
trap "MAINTENANCE_EXIT=\$?" EXIT

source /root/.openclaw/.env 2>/dev/null
set +a

LOCKFILE=/tmp/nox-maintenance.lock
LOG=/var/log/nox-maintenance.log
DOW=$(date +%u)  # 1=Mon ... 7=Sun
DOM=$(date +%d)  # day of month
DB=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db

exec 200>"$LOCKFILE"
flock -n 200 || { echo "[$(date)] Already running, skipping" >> "$LOG"; exit 0; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; echo "$1"; }

log "=== Nightly maintenance started (DOW=$DOW, DOM=$DOM) ==="

# Phase 1: Update session state (daily)
log "Phase 1: update-session"
cd /root/.openclaw/workspace && NOX_DB_SOURCE=main /usr/local/bin/nox-mem update-session >> "$LOG" 2>&1 || true

# Phase 2: Agent reindex + consolidate (every 2 days, odd DOM)
# NOX_DB_SOURCE set explicitly per op (Fase 1 / Gap B, 2026-05-15) — qualifies pre-op snapshot filename.
if [ ! -f /root/.openclaw/DISABLE_AGENT_REINDEX ] && [ $((DOM % 2)) -eq 1 ]; then
    # Check if there are new chunks worth consolidating
    NEW_CHUNKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM chunks WHERE created_at > datetime('now', '-2 days');" 2>/dev/null || echo "0")
    if [ "$NEW_CHUNKS" -gt 0 ]; then
        log "Phase 2: Agent reindex (odd day, $NEW_CHUNKS new chunks)"
        for agent in atlas boris cipher forge lex; do
            log "  Reindexing $agent"
            NOX_DB_SOURCE=$agent OPENCLAW_WORKSPACE=/root/.openclaw/agents/$agent NOX_DB_PATH=/root/.openclaw/agents/$agent/tools/nox-mem/nox-mem.db /usr/local/bin/nox-mem reindex >> "$LOG" 2>&1 || true
            sleep 10
        done
        # Nox agent (different path)
        log "  Reindexing nox"
        NOX_DB_SOURCE=nox OPENCLAW_WORKSPACE=/root/.openclaw/workspace/agents/nox NOX_DB_PATH=/root/.openclaw/workspace/agents/nox/tools/nox-mem/nox-mem.db /usr/local/bin/nox-mem reindex >> "$LOG" 2>&1 || true
        sleep 10

        # Workspace consolidate
        log "  Consolidating workspace"
        cd /root/.openclaw/workspace && NOX_DB_SOURCE=main /usr/local/bin/nox-mem consolidate >> "$LOG" 2>&1 || true
    else
        log "Phase 2: Skipped (odd day but 0 new chunks in last 2 days)"
    fi
else
    log "Phase 2: Skipped (even day)"
fi

# Phase 3: Session wrap-ups — neutralized 2026-06-21.
# Canonical Kaizen weekly wrap-up now runs as BLOCO 0 inside
# `cipher-weekly-full` (Sunday 09:00 BRT) to avoid duplicate agent writes.
log "Phase 3: Skipped (canonical wrap-up is cipher-weekly-full BLOCO 0)"

# Phase 4: Sunday tasks
if [ "$DOW" -eq 7 ]; then
    log "Phase 4: Sunday — compact"
    cd /root/.openclaw/workspace && NOX_DB_SOURCE=main /usr/local/bin/nox-mem compact >> "$LOG" 2>&1 || true

    # Order matters: session-distill creates new chunks that must be embedded
    # by vectorize. Previously the order was inverted, leaving distilled chunks
    # without embeddings until the next Sunday — monitoring flagged this gap.
    log "Phase 4: Sunday — session-distill"
    timeout 1800 /usr/local/bin/nox-mem session-distill >> "$LOG" 2>&1 || log "  session-distill TIMEOUT/ERROR (rc=$?) — continuing"

    log "Phase 4: Sunday — pull-shared (forge + nox)"
    cd /root/.openclaw/workspace/tools/nox-mem
    AGENT_NAME=forge node dist/index.js pull-shared >> "$LOG" 2>&1 || true
    AGENT_NAME=nox node dist/index.js pull-shared --agent nox >> "$LOG" 2>&1 || true

    log "Phase 4: Sunday — kg-build + kg-merge"
    if ! node dist/index.js kg-build --limit 50000 >> "$LOG" 2>&1; then
        log "Phase 4: kg-build FALHOU — backlog do grafo nao avancou esta semana"
    fi
    if ! node dist/index.js kg-merge >> "$LOG" 2>&1; then
        log "Phase 4: kg-merge FALHOU"
    fi

    # Generate KG summary for agent boot context
    log "Phase 4: Sunday — KG-SUMMARY.md for boot"
    node dist/index.js kg-stats > /root/.openclaw/workspace/memory/KG-SUMMARY.md 2>&1 || true
else
    log "Phase 4: Skipped (not Sunday)"
fi

# Phase 4b: kg-confirm DIARIO — renova relacao cujo evidence_chunk_id ainda
# existe no corpus. Sem LLM: e um JOIN, ~7s sobre o grafo inteiro. Por isso
# diario, e nao semanal como o kg-build (que precisa de LLM e e amostrado).
#
# Roda ANTES da Phase 5 de proposito: na segunda, confirmar o que tem suporte
# antes de podar o que nao tem. Sem isto, o kg-prune apaga relacao valida so
# porque o kg-build nao chegou nela — foi assim que o grafo caiu de 21.518
# para 554 relacoes entre maio e julho de 2026.
#
# SEM `|| true`: o silenciamento por `|| true` nos outros comandos kg e o
# motivo de a extracao ter morrido sem ninguem notar. Falha aqui vai pro log.
log "Phase 4b: Daily kg-confirm (por evidencia, sem LLM)"
cd /root/.openclaw/workspace/tools/nox-mem || exit 1
if ! node dist/index.js kg-confirm >> "$LOG" 2>&1; then
    log "Phase 4b: kg-confirm FALHOU — grafo pode perder relacao valida na proxima poda"
fi

# Phase 5: Monday tasks
if [ "$DOW" -eq 1 ]; then
    log "Phase 5: Monday — kg-prune"
    cd /root/.openclaw/workspace/tools/nox-mem || exit 1
    if ! node dist/index.js kg-prune >> "$LOG" 2>&1; then
        log "Phase 5: kg-prune FALHOU"
    fi

    log "Phase 5: Monday — tiers evaluate"
    /usr/local/bin/nox-mem tiers evaluate >> "$LOG" 2>&1 || true
else
    log "Phase 5: Skipped (not Monday)"
fi

# Phase 6: Daily vectorize — keep vector layer in sync with chunks (idempotent).
# Any DELETE on chunks cascades into vec_chunks/vec_chunk_map via
# trg_chunks_delete_cascade. Without this daily catch-up, vectors stay gone
# until the next Sunday run — which was the Apr 21 2026 incident
# (reindex at 01:09 UTC wiped all embeddings, no recovery until canary caught it).
# Idempotent: skips already-embedded chunks in ~2s; full re-embed of ~2000 chunks
# takes ~110s when needed. Runs AFTER all phases so it picks up any new/recreated chunks.
log "Phase 6: Daily vectorize (idempotent)"
cd /root/.openclaw/workspace/tools/nox-mem && /usr/local/bin/nox-mem vectorize >> "$LOG" 2>&1 || true


log "Phase 7: WAL checkpoint (TRUNCATE) — keep DB file compact"
sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);" >> "$LOG" 2>&1 || true

# F8 (added 2026-05-01): Monthly VACUUM (1st Sunday of month)
DAY_OF_MONTH=$(date +%-d)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" = "7" ] && [ "$DAY_OF_MONTH" -le 7 ]; then
  log "Phase 8: Monthly VACUUM"
  sqlite3 "$DB" "VACUUM;" >> "$LOG" 2>&1 && log "VACUUM ok" || log "VACUUM failed"
fi

log "=== Nightly maintenance complete ==="

# Notify on completion (Frente C2 2026-05-31)
END_TS=$(date +%s)
START_TS_FILE=/tmp/nox-maintenance-start
START_TS=$(cat "$START_TS_FILE" 2>/dev/null || echo "$END_TS")
DUR_MIN=$(( (END_TS - START_TS) / 60 ))
rm -f "$START_TS_FILE" 2>/dev/null
if [ "${MAINTENANCE_EXIT:-0}" -ne 0 ]; then
    notify_discord critical nightly-maintenance "Maintenance FAILED (exit=${MAINTENANCE_EXIT}, ${DUR_MIN}min) — check /var/log/nox-maintenance.log"
fi
