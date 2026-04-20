# Deep Stability Audit: OpenClaw VPS Infrastructure
## 2026-04-08 | Architect Agent (Opus)

---

## Executive Summary

This infrastructure has suffered **5+ major incidents in 8 days** (Mar 31 - Apr 8), all sharing a common pattern: **cascading failures amplified by architectural fragility**. The root cause is not any single bug — it is a system designed for feature richness that lacks the defensive boundaries needed for production reliability.

The system is a **single-point-of-failure monolith disguised as a distributed architecture**. Six agents, three messaging channels, a proxy, a memory system, a knowledge graph, and 29 cron jobs all share one VPS with no process isolation, no configuration validation, no circuit breakers, and agents that have root SSH access to rewrite systemd service files.

---

## Risk Matrix

| # | Fragility | Severity | Likelihood | Last Triggered |
|---|-----------|----------|------------|----------------|
| 1 | Agents can rewrite systemd service files | **Critical** | High | Apr 8 |
| 2 | OpenClaw fork-then-die vs systemd | **Critical** | High | Apr 8 |
| 3 | RelayPlane death goes undetected | **Critical** | High | Apr 8 |
| 4 | Node.js wrapper overwritten by apt upgrade | **Critical** | Medium | Apr 1 |
| 5 | openclaw.json unrecognized keys cause crash | **Critical** | High | Apr 1, Mar 31 |
| 6 | Fallback cascade amplifies failures | **Critical** | High | Mar 31, Apr 1 |
| 7 | .env with `export` prefix ignored by systemd | **High** | Medium | Apr 8 |
| 8 | auth-profiles.json corrupted by sed | **High** | Medium | Mar 31 |
| 9 | 29 cron jobs competing for resources | **High** | Medium | Ongoing |
| 10 | KillMode=none (deprecated) in gateway | **Medium** | High | Apr 8 |
| 11 | SQLite WAL under concurrent access | **Medium** | Low | Not yet |
| 12 | Single VPS, no failover | **High** | Low | Not yet |

---

## Phase 1: Stop the Bleeding (Day 1, ~2 hours)

### 1.1 Fix File Permissions
```bash
chmod 644 /etc/systemd/system/openclaw-gateway.service
chmod 644 /root/.openclaw/openclaw.json
chown root:root /root/.openclaw/scripts/*
```

### 1.2 Fix Health Check — Add RelayPlane Probe
```bash
#!/bin/bash
# /root/.openclaw/scripts/health-probe.sh
FAILED=0

# Gateway port
if ! ss -tlnp | grep -q ':18789'; then
    echo "CRITICAL: Gateway port 18789 not listening"
    FAILED=1
fi

# RelayPlane port
if ! curl -sf --max-time 3 http://127.0.0.1:4100/health > /dev/null 2>&1; then
    echo "CRITICAL: RelayPlane port 4100 not responding"
    systemctl restart relayplane-proxy
    FAILED=1
fi

# nox-mem API port
if ! curl -sf --max-time 3 http://127.0.0.1:18800/api/health > /dev/null 2>&1; then
    echo "WARN: nox-mem API port 18800 not responding"
    systemctl restart nox-mem-api
fi

# Disk space
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
    echo "WARN: Disk usage at ${DISK_PCT}%"
fi

# SQLite integrity
DB=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
if ! sqlite3 "$DB" "SELECT count(*) FROM chunks LIMIT 1" > /dev/null 2>&1; then
    echo "CRITICAL: SQLite database unreadable"
    FAILED=1
fi

if [ $FAILED -eq 1 ]; then
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' \
        -d "{\"content\": \"ALERT: VPS health check failed at $(date)\"}" > /dev/null 2>&1
fi
```

### 1.3 Remove Dead Providers
Remove OpenAI from ALL configs (no credits). Never use `sed` on JSON — use Python:
```python
# /root/.openclaw/scripts/json-edit.py
import json, sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: data = json.load(f)
keys = key.split('.')
obj = data
for k in keys[:-1]: obj = obj[k]
obj[keys[-1]] = json.loads(value)
with open(path, 'w') as f: json.dump(data, f, indent=2)
```

### 1.4 Add JSON Validation to Gateway Startup
```ini
ExecStartPre=/usr/bin/python3 -c "import json; json.load(open('/root/.openclaw/openclaw.json'))"
```

---

## Phase 2: Stabilize Systemd (Day 2, ~3 hours)

### 2.1 Fix Service Type
Replace `KillMode=none` hack with proper wrapper:
```bash
#!/bin/bash
# /root/.openclaw/scripts/gateway-wrapper.sh
/usr/local/bin/openclaw gateway run --bind loopback &
GATEWAY_PID=$!
echo $GATEWAY_PID > /run/openclaw-gateway.pid
trap "kill $GATEWAY_PID 2>/dev/null; exit" SIGTERM SIGINT
wait $GATEWAY_PID
```

```ini
[Unit]
Description=OpenClaw Gateway
After=network.target relayplane-proxy.service
Requires=relayplane-proxy.service

[Service]
Type=simple
User=root
EnvironmentFile=/root/.openclaw/.env
ExecStartPre=-/usr/bin/fuser -k 18789/tcp
ExecStartPre=/usr/bin/python3 -c "import json; json.load(open('/root/.openclaw/openclaw.json'))"
ExecStart=/root/.openclaw/scripts/gateway-wrapper.sh
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitIntervalSec=600

[Install]
WantedBy=multi-user.target
```

### 2.2 Circuit Breaker
After 3 failures in 10 min, systemd stops. Health check should NOT restart blindly:
```bash
# In health-probe.sh
if systemctl is-failed openclaw-gateway 2>/dev/null; then
    FAIL_COUNT=$(systemctl show openclaw-gateway -p NRestarts --value 2>/dev/null)
    if [ "$FAIL_COUNT" -gt 3 ]; then
        echo "CIRCUIT OPEN: Gateway exceeded restart limit. Manual intervention required."
        # Alert Discord but do NOT restart
        exit 1
    fi
fi
```

---

## Phase 3: Simplify Crons (Day 3, ~2 hours)

Replace **29 cron entries** with **3**:

```bash
#!/bin/bash
# /root/.openclaw/scripts/nightly-maintenance.sh
set -e
LOCKFILE=/tmp/nox-maintenance.lock
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Already running"; exit 1; }

log() { echo "[$(date '+%H:%M:%S')] $1"; }
log "Starting nightly maintenance"

# Phase 1: Reindex + consolidate (sequential)
for agent in workspace nox atlas boris cipher forge lex; do
    log "Consolidating $agent"
    if [ "$agent" = "workspace" ]; then
        WS=/root/.openclaw/workspace
    else
        WS=/root/.openclaw/agents/$agent
    fi
    set -a && source /root/.openclaw/.env 2>/dev/null && set +a
    OPENCLAW_WORKSPACE=$WS nox-mem reindex 2>&1 || true
    OPENCLAW_WORKSPACE=$WS nox-mem consolidate 2>&1 || true
    sleep 10
done

# Phase 2: Session update
log "Updating session state"
nox-mem update-session 2>&1 || true

# Phase 3: Sunday — KG + vectorize
if [ "$(date +%u)" -eq 7 ]; then
    log "Building knowledge graph"
    nox-mem kg-build 2>&1 || true
    nox-mem kg-merge 2>&1 || true
    log "Vectorizing"
    nox-mem vectorize 2>&1 || true
fi

# Phase 4: Monday — prune + tiers
if [ "$(date +%u)" -eq 1 ]; then
    log "Pruning KG and evaluating tiers"
    nox-mem kg-prune 2>&1 || true
    nox-mem tiers evaluate 2>&1 || true
fi

log "Maintenance complete"
```

**New crontab (3 entries):**
```
0 23 * * *   /root/.openclaw/scripts/nightly-maintenance.sh >> /var/log/nox-maintenance.log 2>&1
*/5 * * * *  /root/.openclaw/scripts/health-probe.sh >> /var/log/nox-health.log 2>&1
0 2 * * *    /root/.openclaw/scripts/backup-all.sh >> /var/log/nox-backup.log 2>&1
```

---

## Phase 4: Agent Isolation (Week 1, ~4 hours)

1. Create `openclaw` system user
2. Migrate workspace ownership
3. Update systemd units to `User=openclaw`
4. Create sudoers allowlist
5. Agents can read `openclaw.json` but NOT write

---

## Phase 5: Node.js Wrapper Hardening (Week 1, ~1 hour)

1. Move wrapper to `/root/.openclaw/scripts/node-wrapper.sh`
2. Update systemd units to use wrapper explicitly
3. Add apt hook to detect nodejs upgrades
4. Add wrapper validation to health check

---

## What to Remove

| Remove | Reason |
|--------|--------|
| 26 of 29 cron entries | Replace with 3 orchestrated scripts |
| `claude-telegram.service` unit file | Already disabled. Delete entirely |
| `claude-tg-watchdog.sh` | Already removed. Delete script |
| OpenAI from all configs | No credits. Wasted cascade step |
| `anthropic-overload-monitor` cron | Disabled/broken. Delete |
| `session-context.json` | Deprecated since Apr 1 |
| `active-tasks.md` | Deprecated since Apr 1 |
| `KillMode=none` in gateway unit | Replace with proper wrapper |
| RelayPlane (if going Anthropic-only) | Removes a dependency and failure point |

---

## Why Crashes Cascade

```
Trigger (single failure)
    → Amplification (gateway restarts, kills 7 agents)
        → Exhaustion (boot tasks burn API quotas)
            → Feedback (health check restarts again)
                → Collateral (agents "fix" things, make it worse)
```

**Break the cascade at every junction:**
- RelayPlane failing → dependency ordering, probe
- Gateway restarting → startup throttle, circuit breaker
- Failed providers → remove dead ones, empty fallbacks
- Health checks → don't restart blindly after 3 failures
- Agents → can't modify infrastructure (permissions)

---

## Final Assessment

The memory system (nox-mem, hybrid search, KG v2) is genuinely impressive and solid. The instability is entirely in the infrastructure plumbing. Phases 1-2 would have prevented **every single incident** in the log. The system doesn't need more features — it needs fewer moving parts, harder boundaries, and the assumption that things will fail.
