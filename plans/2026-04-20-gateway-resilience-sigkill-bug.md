# Gateway Resilience Plan — SIGKILL Self-Parent Bug (2026.4.14)

**Date:** 2026-04-20
**Author:** sre-engineer
**Status:** Proposal — awaiting Toto approval before execution

---

## Context Summary

- OpenClaw binary `2026.4.14` (installed 2026-04-01 via npm global, replacing documented `2026.3.31`) self-SIGKILLs parent process ~6–7s after boot.
- **Child survives** under `systemd --user` (PID 472430, PPID=1) and continues listening on `127.0.0.1:18789`. All 14 plugins loaded, all 6 agents functional via orphan.
- Systemd *system* service (`openclaw-gateway.service`) shows `failed` because it watches the parent PID, which was killed.
- `health-probe.sh` (patched 2026-04-20 12:00) explicitly detects "port up + systemd=failed" as an orphan condition and *kills + restarts*, causing:
  - Downtime every 5 min (fuser -k kills the working child)
  - CPU/memory churn (~11s × 825MB per restart = ~9.5 GB·s)
  - Log spam (5 journal restarts + Discord alerts)
- Previous attempts (mDNS off, config restore, queue clean, StartLimitBurst=100) failed — bug is in binary, not config.

---

## Option Evaluation

### Option A — Move gateway off systemd (tmux/pm2/supervisord)
- **Viability:** High. `tmux 3.5a` already installed. Binary behavior is unchanged, but:
  - `systemd --user` is ALREADY our de facto process manager (that's why orphan survives). Running under tmux would make the child's new parent `tmux server`, which doesn't reap either, so the same orphan pattern persists.
  - pm2 / supervisord would re-introduce the same "parent died → manager restarts" loop, because they track PID of the *wrapper* and the bug kills the wrapper.
- **Esforço:** Médio (rewrite wrapper, migrate logs to tmux pipe-pane or file, new health-check contract).
- **Riscos:** Doesn't fix the restart loop — moves it to a different supervisor. Adds a new failure surface (tmux crash = gateway dies silently). **Rejected as standalone.**

### Option B — Rollback to 2026.3.31
- **Viability:** Possible. `2026.3.31` is in npm registry (`npm view openclaw versions` confirms). No local archive, but `npm install -g openclaw@2026.3.31` works.
- **Esforço:** Baixo-Médio (30 min: stop service, npm downgrade, smoke test, restart, monitor 1h).
- **Riscos principais:**
  1. **Config drift.** `openclaw.json` has been edited under 2026.4.14 conventions. CLAUDE.md convention ("Nunca adicionar chaves root novas sem verificar versão") exists precisely because of crash loop risk. Need to diff current config against backup `openclaw_2026-04-17_02-00.json` or earlier.
  2. **Active-memory, graph-memory, hooks:loader are new subsystems** — may not exist in 2026.3.31 or may have incompatible DB schemas. `graph-memory.db` was created by 2026.4.x; downgrade could corrupt or refuse it.
  3. Pip/node_modules for 2026.3.31 may pull older peer deps incompatible with current `relayplane` v1.8.37 and Node 22.22.2 wrapper.
- **Also:** We don't yet know if 2026.3.31 had the bug — we only know the symptom appeared *after* an upgrade. Worth validating first via `npm view openclaw@2026.3.31` changelog or just trying 2026.4.10 (one minor step back).

### Option C — Accept orphan, redesign monitoring
- **Viability:** Alta. Already works today — child has been running since 13:16, stable. Real problem is our health-probe actively breaks it.
- **Esforço:** Baixo (20 min: mask systemd unit, revert probe patch, add port-only health-check).
- **Riscos:** 
  - Orphan has no auto-restart if child crashes (systemd --user reaps but doesn't restart). Need an independent supervisor: a bash while-loop under `systemd` (simple Type=oneshot + Timer, or Type=forking with PIDFile).
  - Lost journal integration — need explicit log redirection (`/tmp/openclaw/openclaw-YYYY-MM-DD.log` already exists and the binary writes there).
  - If binary is fixed upstream, we must remember to re-enable systemd. Keep a flag file documenting the state.

---

## Recommendation: **Hybrid C → B**

**Phase 1 (today, low-risk):** Adopt Option C — stop fighting the orphan. Disable broken systemd unit, rewrite `health-probe.sh` to monitor **port** + **HTTP /__openclaw__** endpoint independently, add a separate `openclaw-gateway-supervisor.service` that re-launches the binary if port dies for >60s.

**Phase 2 (tomorrow, validation):** Attempt Option B rollback to `2026.4.10` (smaller blast radius than going back to 2026.3.31) in a dry-run: `npm install -g openclaw@2026.4.10 --dry-run`, review deps, snapshot config + DBs, swap, validate 1h, decide.

**Why this order:**
- Phase 1 is fully reversible and stops the 5-min downtime *today*.
- Phase 2 is the real fix but needs config/DB compatibility work that's risky without a calm baseline.
- Option A adds a supervisor we don't need — systemd --user already supervises and tmux doesn't solve the root cause.

---

## Execution Plan — Phase 1 (Accept Orphan)

### Pre-flight backups
```bash
ssh root@100.87.8.44 '
mkdir -p /root/backups/2026-04-20-gateway-fix
cp /etc/systemd/system/openclaw-gateway.service /root/backups/2026-04-20-gateway-fix/
cp /usr/local/bin/openclaw-gateway-wrapper /root/backups/2026-04-20-gateway-fix/
cp /root/.openclaw/scripts/health-probe.sh /root/backups/2026-04-20-gateway-fix/
cp /root/.openclaw/openclaw.json /root/backups/2026-04-20-gateway-fix/
crontab -l > /root/backups/2026-04-20-gateway-fix/crontab.txt
'
```

### Step 1: Stop the restart loop (mask service, keep config)
```bash
ssh root@100.87.8.44 '
systemctl stop openclaw-gateway
# child survives under systemd --user; verify:
ss -tlnp | grep 18789
# if gone, launch via user-systemd exec-path below BEFORE masking
systemctl mask openclaw-gateway
systemctl daemon-reload
rm -f /tmp/openclaw-circuit-open
'
```
**Decision point:** If port 18789 empty after stop, the orphan had already been killed. In that case, launch manually FIRST using Step 2, THEN mask.

### Step 2: Launch gateway as detached process (idempotent)
Create `/root/.openclaw/scripts/gateway-launch.sh`:
```bash
#!/bin/bash
set -e
unset INVOCATION_ID JOURNAL_STREAM NOTIFY_SOCKET LISTEN_FDS LISTEN_PID MANAGERPID
set -a; source /root/.openclaw/.env; set +a
LOG=/var/log/openclaw-gateway.log
nohup /usr/local/bin/openclaw gateway run --bind loopback >> "$LOG" 2>&1 &
disown
```
Run it once. Verify child survives parent death via `ps -ef | grep openclaw-gateway`.

### Step 3: New supervisor service (watchdog, not restart-loop)
Create `/etc/systemd/system/openclaw-gateway-watchdog.service`:
```
[Unit]
Description=OpenClaw Gateway Watchdog (port-based)
After=network.target

[Service]
Type=oneshot
ExecStart=/root/.openclaw/scripts/gateway-watchdog.sh
```
And `.timer`:
```
[Unit]
Description=Run gateway watchdog every 2 min

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
Unit=openclaw-gateway-watchdog.service

[Install]
WantedBy=timers.target
```
Watchdog script:
```bash
#!/bin/bash
# Only launches if port 18789 is dead for 60s. Never kills existing listener.
GRACE=60
if ss -tlnp | grep -q ':18789'; then exit 0; fi
sleep "$GRACE"
if ss -tlnp | grep -q ':18789'; then exit 0; fi
logger -t openclaw-watchdog "port 18789 absent for ${GRACE}s — relaunching"
/root/.openclaw/scripts/gateway-launch.sh
```
Enable: `systemctl enable --now openclaw-gateway-watchdog.timer`.

### Step 4: Rewrite `health-probe.sh` — no more orphan-killing
Patch section 1 to:
```bash
# 1. Gateway reachability (port + /__openclaw__ canvas endpoint)
if ss -tlnp | grep -q ':18789' && \
   curl -sf --max-time 3 'http://127.0.0.1:18789/__openclaw__/canvas/' > /dev/null 2>&1; then
    log "OK: Gateway serving on 18789"
else
    log "FAIL: Gateway unreachable"
    ALERTS="${ALERTS}Gateway DOWN. "
    FAILED=1
    # Do NOT kill or restart — let openclaw-gateway-watchdog.timer handle it
fi
```
Keep circuit breaker for Discord alerts only.

### Step 5: Document state
Create `/root/.openclaw/OPERATIONAL-STATE.md` noting: binary 2026.4.14 has self-kill parent bug; running in "orphan-accepted" mode; watchdog timer supervises; revert plan below.

---

## Rollback Plan (revert to systemd-managed)

```bash
ssh root@100.87.8.44 '
systemctl stop openclaw-gateway-watchdog.timer
systemctl disable openclaw-gateway-watchdog.timer
systemctl unmask openclaw-gateway
cp /root/backups/2026-04-20-gateway-fix/health-probe.sh /root/.openclaw/scripts/health-probe.sh
systemctl daemon-reload
# kill any orphan child
fuser -k 18789/tcp
systemctl start openclaw-gateway
'
```

---

## Success Metrics (validate after 1h and 24h)

| Metric | Target | How to measure |
|---|---|---|
| Port 18789 uptime | >99% over 24h | `journalctl -u openclaw-gateway-watchdog` relaunches ≤ 2 |
| Agent response latency | ≤ pre-patch baseline | spot-test `nox` via Telegram, expect <5s first reply |
| Zero `fuser -k 18789` from health-probe | 0 kills in 24h | `grep 'ORPHAN' /var/log/nox-health.log` empty |
| systemd `openclaw-gateway.service` | `masked` (not failed, not active) | `systemctl is-enabled openclaw-gateway` returns `masked` |
| Memory churn | <1 restart/24h | `/var/log/openclaw-gateway.log` rotation entries ≤ 1 |

Canary: Send a test message via Telegram to each of the 6 agents and confirm reply within 30s. Run at T+1h, T+6h, T+24h.

---

## Phase 2 Plan (rollback to 2026.4.10) — deferred

See section at bottom of this doc. Requires:
1. Snapshot `graph-memory.db` + `openclaw.json` + `active-memory.db` (any 2026.4-era DB).
2. Diff current config vs `/root/.openclaw/workspace/backups/openclaw_2026-04-01_02-00.json`.
3. `npm install -g openclaw@2026.4.10`, restart, 1h canary.
4. If 2026.4.10 also self-kills → try 2026.4.7 → 2026.4.5 → 2026.3.31 (binary-search).

Do not execute Phase 2 until Phase 1 has been stable for 24h.
