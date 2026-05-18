# CLI Scripting Guide

Patterns for using nox-mem in shell scripts, cron jobs, and systemd units.

---

## Environment loading

**Rule #1 (CLAUDE.md):** Always load env before any nox-mem command in a script. Without it, `vectorize`, `kg-build`, `answer`, and `archive export` fail silently with "Done: 0 embedded, N errors".

```bash
#!/usr/bin/env bash
set -euo pipefail

# Load all env vars from .env
set -a
source /root/.openclaw/.env
set +a

# Now safe to call nox-mem
nox-mem vectorize
```

**Local development (non-VPS):**
```bash
set -a; source ~/.nox-mem/.env; set +a
```

---

## Common scripting errors

| Error | Cause | Fix |
|---|---|---|
| "Done: 0 embedded, 0 errors" | `GEMINI_API_KEY` not in env | `set -a; source .env; set +a` before nox-mem |
| "ECONNREFUSED 127.0.0.1:18802" | nox-mem-api not running | `nox-mem serve` or `systemctl start nox-mem-api` |
| Port 18800 conflicts | Chrome squats 18800 | Use `NOX_API_PORT=18802` — never 18800 |
| "sed: invalid command" on .db file | sed on binary SQLite | Never `sed -i` a `.db` file — it corrupts pages |
| Vectorize gap after reindex | reindex called without env | Source env first; then `nox-mem vectorize` to fill gap |

---

## Cron job templates

### Nightly maintenance (recommended pattern from VPS)

```cron
# Run nightly at 23:00 BRT (02:00 UTC next day on VPS in UTC)
0 2 * * * /usr/local/bin/nox-mem-nightly.sh >> /var/log/nox-mem-nightly.log 2>&1
```

`/usr/local/bin/nox-mem-nightly.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
set -a; source /root/.openclaw/.env; set +a

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] nightly start"

# Consolidate (safe — does not wipe section/retention)
nox-mem consolidate

# Vectorize gaps
nox-mem vectorize

# KG build (incremental — only unprocessed chunks)
nox-mem kg-build

# KG prune orphaned nodes
nox-mem kg-prune

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] nightly done"
```

> Do NOT run `nox-mem reindex` in cron without `--dry-run` first. Reindex wipes `section`/`retention` if the ingest router is not applied. Use `consolidate` for nightly maintenance (CLAUDE.md rule #6).

### Schema invariants check (every 15 minutes)

```cron
*/15 * * * * /usr/local/bin/check-schema-invariants.sh >> /var/log/nox-mem-invariants.log 2>&1
```

`/usr/local/bin/check-schema-invariants.sh`:
```bash
#!/usr/bin/env bash
set -a; source /root/.openclaw/.env; set +a

# 4 invariants: section NOT NULL, feedback never_decay, ops_audit terminal, section_boost consistent
RESULT=$(nox-mem check-invariants --json 2>&1)
if echo "$RESULT" | jq -e '.failures | length > 0' > /dev/null 2>&1; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INVARIANT FAILURE: $RESULT"
  # Alert via Discord webhook (configure DISCORD_WEBHOOK_URL in .env)
  curl -s -X POST "$DISCORD_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"nox-mem invariant failure: $RESULT\"}" || true
fi
```

### Health probe (every 5 minutes)

```cron
*/5 * * * * curl -sf http://127.0.0.1:18802/api/health > /dev/null || echo "[$(date)] health probe failed" >> /var/log/nox-mem-health.log
```

### Backup (daily at 02:00 UTC)

```cron
0 2 * * * /usr/local/bin/nox-mem-backup.sh >> /var/log/nox-mem-backup.log 2>&1
```

`/usr/local/bin/nox-mem-backup.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
set -a; source /root/.openclaw/.env; set +a

BACKUP_DIR="/var/backups/nox-mem/daily"
mkdir -p "$BACKUP_DIR"

# VACUUM INTO — creates a clean, defragmented copy
sqlite3 "$NOX_DB_PATH" "VACUUM INTO '$BACKUP_DIR/nox-mem-$(date +%Y%m%d).db'"

# Retain 7 days
find "$BACKUP_DIR" -name "nox-mem-*.db" -mtime +7 -delete

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] backup done: $BACKUP_DIR/nox-mem-$(date +%Y%m%d).db"
```

---

## systemd unit templates

### nox-mem-api.service

`/etc/systemd/system/nox-mem-api.service`:
```ini
[Unit]
Description=nox-mem HTTP API server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/tools/nox-mem
EnvironmentFile=/root/.openclaw/.env
ExecStart=/usr/bin/node dist/index.js serve
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nox-mem-api

# Never hardcode keys in unit — use EnvironmentFile
# Port 18802 — Chrome squats 18800, never use it
Environment=NOX_API_PORT=18802

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable nox-mem-api
systemctl start nox-mem-api
systemctl status nox-mem-api
journalctl -u nox-mem-api -f
```

### nox-mem-watcher.service

`/etc/systemd/system/nox-mem-watcher.service`:
```ini
[Unit]
Description=nox-mem file watcher (inotifywait)
After=nox-mem-api.service
Requires=nox-mem-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/tools/nox-mem
EnvironmentFile=/root/.openclaw/.env
ExecStart=/usr/bin/node dist/index.js watch
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nox-mem-watcher

[Install]
WantedBy=multi-user.target
```

---

## Backup script template (full-featured)

For the pattern used in production (pre-op snapshots via `withOpAudit`):

```bash
#!/usr/bin/env bash
# nox-mem-pre-op-backup.sh — called by withOpAudit() wrapper automatically.
# Do NOT call directly unless NOX_ALLOW_NO_SNAPSHOT=1 emergency is active.

set -euo pipefail
set -a; source /root/.openclaw/.env; set +a

OP_TYPE="${1:-unknown}"
SNAPSHOT_DIR="/var/backups/nox-mem/pre-op"
mkdir -p "$SNAPSHOT_DIR"
chmod 700 "$SNAPSHOT_DIR"

SNAPSHOT_PATH="$SNAPSHOT_DIR/${OP_TYPE}-$(date +%Y%m%d-%H%M%S)-$$-$(uuidgen | tr -d '-').db"

# VACUUM INTO (atomic, clean copy, no WAL artifacts)
sqlite3 "$NOX_DB_PATH" "VACUUM INTO '$SNAPSHOT_PATH'"
chmod 600 "$SNAPSHOT_PATH"

echo "$SNAPSHOT_PATH"
```

> Pre-op snapshots are created automatically by `withOpAudit()` (wraps `reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune`). Only use `NOX_ALLOW_NO_SNAPSHOT=1` if the snapshot fails for a legitimate reason (disk full emergency).

---

## Long-running batch jobs

For batch operations that take more than a few minutes (e.g. full-corpus vectorize on a large store), use `tmux` + a standalone script. Not `nohup` alone — it loses the session on disconnect.

```bash
# Start a named tmux session
tmux new-session -d -s nox-vectorize

# Run the batch inside tmux
tmux send-keys -t nox-vectorize \
  "set -a; source /root/.openclaw/.env; set +a && nox-mem vectorize" Enter

# Monitor progress
tmux attach -t nox-vectorize

# Check on it later without attaching
tmux capture-pane -t nox-vectorize -p | tail -5
```

> Lesson: nohup-only and systemd-run inline fail for interactive-style batch jobs. tmux + standalone script is stable. Reference: `docs/INCIDENTS.md` incident A6.

---

## Serial pipeline with per-step timeouts

Wrap each step with `timeout N` to prevent one hung step from blocking the pipeline:

```bash
#!/usr/bin/env bash
set -a; source /root/.openclaw/.env; set +a

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "vectorize start"
timeout 300 nox-mem vectorize || { log "vectorize timed out or failed — continuing"; }

log "kg-build start"
timeout 600 nox-mem kg-build || { log "kg-build timed out or failed — continuing"; }

log "pipeline done"
```

> Never use `|| true` to mask failures — it hides duration AND exit code. Use `|| { log "..."; }` to log failures while allowing the pipeline to continue.
