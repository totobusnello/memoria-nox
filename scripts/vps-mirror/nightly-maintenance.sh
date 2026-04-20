#!/bin/bash
# nightly-maintenance.sh — Sequential nox-mem maintenance
# Replaces 20+ staggered cron entries with one orchestrated script
# Runs daily at 23:00, day-of-week logic inside

set -a
source /root/.openclaw/.env 2>/dev/null
set +a

LOCKFILE=/tmp/nox-maintenance.lock
LOG=/var/log/nox-maintenance.log
DOW=$(date +%u)  # 1=Mon ... 7=Sun
DOM=$(date +%d)  # day of month
DB=/root/.openclaw/workspace/nox-mem.db

exec 200>"$LOCKFILE"
flock -n 200 || { echo "[$(date)] Already running, skipping" >> "$LOG"; exit 0; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; echo "$1"; }

log "=== Nightly maintenance started (DOW=$DOW, DOM=$DOM) ==="

# Phase 1: Update session state (daily)
log "Phase 1: update-session"
cd /root/.openclaw/workspace && /usr/local/bin/nox-mem update-session >> "$LOG" 2>&1 || true

# Phase 2: Agent reindex + consolidate (every 2 days, odd DOM)
if [ $((DOM % 2)) -eq 1 ]; then
    # Check if there are new chunks worth consolidating
    NEW_CHUNKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM chunks WHERE created_at > datetime('now', '-2 days');" 2>/dev/null || echo "0")
    if [ "$NEW_CHUNKS" -gt 0 ]; then
        log "Phase 2: Agent reindex (odd day, $NEW_CHUNKS new chunks)"
        for agent in atlas boris cipher forge lex; do
            log "  Reindexing $agent"
            OPENCLAW_WORKSPACE=/root/.openclaw/agents/$agent /usr/local/bin/nox-mem reindex >> "$LOG" 2>&1 || true
            sleep 10
        done
        # Nox agent (different path)
        log "  Reindexing nox"
        OPENCLAW_WORKSPACE=/root/.openclaw/workspace/agents/nox /usr/local/bin/nox-mem reindex >> "$LOG" 2>&1 || true
        sleep 10

        # Workspace consolidate
        log "  Consolidating workspace"
        cd /root/.openclaw/workspace && /usr/local/bin/nox-mem consolidate >> "$LOG" 2>&1 || true
    else
        log "Phase 2: Skipped (odd day but 0 new chunks in last 2 days)"
    fi
else
    log "Phase 2: Skipped (even day)"
fi

# Phase 3: Session wrap-ups (Wed=3, Sat=6)
if [ "$DOW" -eq 3 ] || [ "$DOW" -eq 6 ]; then
    log "Phase 3: Session wrap-ups"
    for agent in atlas boris cipher lex; do
        log "  Wrap-up $agent"
        AGENT_NAME=$agent OPENCLAW_WORKSPACE=/root/.openclaw/agents/$agent \
            bash /root/.openclaw/workspace/tools/session-wrap-up.sh --agent $agent --fix >> "$LOG" 2>&1 || true
        sleep 5
    done
else
    log "Phase 3: Skipped (not Wed/Sat)"
fi

# Phase 4: Sunday tasks
if [ "$DOW" -eq 7 ]; then
    log "Phase 4: Sunday — compact"
    cd /root/.openclaw/workspace && /usr/local/bin/nox-mem compact >> "$LOG" 2>&1 || true

    # Order matters: session-distill creates new chunks that must be embedded
    # by vectorize. Previously the order was inverted, leaving distilled chunks
    # without embeddings until the next Sunday — monitoring flagged this gap.
    log "Phase 4: Sunday — session-distill"
    /usr/local/bin/nox-mem session-distill >> "$LOG" 2>&1 || true

    log "Phase 4: Sunday — vectorize (Gemini)"
    /usr/local/bin/nox-mem vectorize >> "$LOG" 2>&1 || true

    log "Phase 4: Sunday — pull-shared (forge + nox)"
    cd /root/.openclaw/workspace/tools/nox-mem
    AGENT_NAME=forge node dist/index.js pull-shared >> "$LOG" 2>&1 || true
    AGENT_NAME=nox node dist/index.js pull-shared --agent nox >> "$LOG" 2>&1 || true

    log "Phase 4: Sunday — kg-build + kg-merge"
    node dist/index.js kg-build --limit 1000 >> "$LOG" 2>&1 || true
    node dist/index.js kg-merge >> "$LOG" 2>&1 || true

    # Generate KG summary for agent boot context
    log "Phase 4: Sunday — KG-SUMMARY.md for boot"
    node dist/index.js kg-stats > /root/.openclaw/workspace/memory/KG-SUMMARY.md 2>&1 || true
else
    log "Phase 4: Skipped (not Sunday)"
fi

# Phase 5: Monday tasks
if [ "$DOW" -eq 1 ]; then
    log "Phase 5: Monday — kg-prune"
    cd /root/.openclaw/workspace/tools/nox-mem && node dist/index.js kg-prune >> "$LOG" 2>&1 || true

    log "Phase 5: Monday — tiers evaluate"
    /usr/local/bin/nox-mem tiers evaluate >> "$LOG" 2>&1 || true
else
    log "Phase 5: Skipped (not Monday)"
fi

log "=== Nightly maintenance complete ==="
