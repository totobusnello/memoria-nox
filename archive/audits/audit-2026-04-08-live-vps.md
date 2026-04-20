# Live VPS Audit Report -- 2026-04-08 10:43 BRT

**Auditor:** SRE Agent (Claude Opus 4.6)
**Target:** srv1465941 (root@100.87.8.44 via Tailscale)
**Method:** Live SSH inspection. Documentation compared against actual state.

---

## 1. System Resources

| Metric | Value | Status |
|--------|-------|--------|
| RAM | 1.9 GB used / 16 GB total (14 GB available) | OK |
| Swap | 4 GB configured, 0 used | OK |
| Disk | 41 GB used / 193 GB (22%) | OK |
| CPU | 4 cores, load avg 0.07/0.11/0.32 | OK |
| Swappiness | 10 | OK (tuned) |
| Uptime | 1 day, 1 hour | Recent reboot (Apr 7 ~09:38) |

**No resource concerns.** System is lightly loaded.

---

## 2. Critical Findings (Fix Immediately)

### CRITICAL-1: OAuth Tokens Exposed in Process Arguments

Three orphaned `claude` processes from Apr 7 have **OAuth tokens visible in plaintext** via `ps aux`:

```
PID 65572: bash -c ... echo 'sk-ant-oat01-IlluB97L...' | claude setup-token
PID 65949: bash -c echo 'sk-ant-oat01-4S1jClmz...' | claude setup-token
```

**Impact:** Any user who can run `ps aux` on this machine can read your Anthropic OAuth tokens. These processes have been running for 17+ hours doing nothing.

**Fix:**
```bash
kill 65452 65453 65572 65590 65949 65951
# Then rotate the exposed tokens via: claude auth login
```

### CRITICAL-2: Credentials File World-Readable

`/root/.claude-max/credentials.json` has permissions `644` (world-readable). Contains OAuth refresh tokens.

**Fix:**
```bash
chmod 600 /root/.claude-max/credentials.json
```

### CRITICAL-3: Google Client Secret World-Readable

`/root/.openclaw/workspace/google_client_secret.json` has permissions `644`.

**Fix:**
```bash
chmod 600 /root/.openclaw/workspace/google_client_secret.json
```

### CRITICAL-4: Gateway Binding on 0.0.0.0 Despite Loopback Wrapper

The gateway wrapper script passes `--bind loopback` but the config has `gateway.bind: lan`. The actual binding is `0.0.0.0:18789` -- meaning the gateway listens on ALL interfaces, not just loopback.

The `--bind loopback` flag in the wrapper is being overridden by the config file's `"bind": "lan"`. UFW restricts 18789 to Tailscale (100.64.0.0/10), but if UFW ever fails or is reset, the gateway becomes publicly accessible.

**Fix (choose one):**
```bash
# Option A: Fix the config to match the wrapper intent
python3 -c "
import json
d=json.load(open('/root/.openclaw/openclaw.json'))
d['gateway']['bind']='loopback'
json.dump(d,open('/root/.openclaw/openclaw.json','w'),indent=2)
"
systemctl restart openclaw-gateway

# Option B: Or if LAN access IS needed, remove --bind loopback from wrapper
# and rely solely on UFW
```

---

## 3. High-Priority Findings

### HIGH-1: Gateway Service Type Mismatch (Type=oneshot for Long-Running Process)

The systemd service is `Type=oneshot` with `RemainAfterExit=yes` and `KillMode=none`. The gateway process forks/daemonizes itself, so systemd loses tracking of the actual child process.

**Evidence:** systemd shows `active (exited)` while the actual gateway PID 150775 is running at 8% CPU and 608 MB RSS. The `SuccessExitStatus=KILL` line proves the wrapper process gets killed (signal 9) by the gateway's own daemonization, and systemd considers that "success."

**Consequences:**
- `systemctl stop openclaw-gateway` will NOT stop the actual gateway (KillMode=none)
- systemd cannot detect if the gateway crashes
- No automatic restart on failure
- Health check cron is the only thing detecting failures, adding 15-min MTTR

**Docs say:** `Type=simple, Restart=always, StartLimitBurst=5, StartLimitIntervalSec=120` -- NONE of these are present in the actual service file.

**55 start attempts today** (10:00-10:43) with multiple crash loops, confirming the service configuration is unstable.

### HIGH-2: Duplicate File Watcher Services

Two services both running the SAME script (`nox-mem-watch.sh`):
- `nox-mem-watch.service` (enabled, running, PID 144351)
- `nox-mem-watcher.service` (enabled, running, PID 144352)

Both are active, consuming double the inotify watches and potentially processing the same file events twice, leading to duplicate ingestions.

**Fix:**
```bash
systemctl stop nox-mem-watcher.service
systemctl disable nox-mem-watcher.service
# Keep nox-mem-watch.service (the one with resource limits)
```

### HIGH-3: Model Fallbacks Completely Empty

All 7 agents have `"fallbacks": []`. The docs claim a cascade: `Sonnet -> Haiku -> DeepSeek R1 -> Qwen3 -> Llama 70B`. **This cascade does not exist at the OpenClaw level.** If the Anthropic API is down, all agents fail immediately with no fallback.

RelayPlane cascade is configured but only works if the gateway sends requests through RelayPlane. The `ANTHROPIC_BASE_URL` is no longer set in the env file (only 5 env vars found: `ANTHROPIC_API_KEY`, `ANTHROPIC_MAX_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `NOTION_TOKEN`, `SLACK_TOKEN`). No `GROQ_API_KEY` or `GEMINI_API_KEY` in the env file either.

**Fix:** Either restore fallbacks in `openclaw.json` agents.defaults.model, or ensure `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` is in the env file so requests route through RelayPlane.

### HIGH-4: Ollama Service Disabled and Dead

Docs say Ollama is one of the "6 active services." In reality:
```
ollama.service: disabled, inactive (dead)
```

This means:
- Knowledge Graph extraction (uses `llama3.2:3b`) will fail silently
- `kg-build` cron (Sunday 21:35) will fail
- No local LLM fallback available

**Fix:**
```bash
systemctl enable ollama.service
systemctl start ollama.service
```

### HIGH-5: Billing Proxy Running as Orphan Process

PID 144370 (`/root/openclaw-billing-proxy/proxy.js`) is running on port 18801, spawned by `systemd --user` (not managed by any service unit). If it dies, nothing restarts it. No logs are captured by journald.

The proxy's purpose (injecting Claude Code billing headers) may or may not still be needed after the auth fix on Apr 7. If it IS needed, it should have a systemd service. If not, it should be killed.

### HIGH-6: WAL Checkpoint Script Targets Wrong Database

`wal-checkpoint.sh` runs against:
```
/root/.openclaw/workspace/memory/nox-mem.db  (40 KB, stale since Mar 31, only vec tables)
```

The actual production database is:
```
/root/.openclaw/workspace/tools/nox-mem/nox-mem.db  (87 MB, 1826 chunks)
```

The checkpoint has been silently doing nothing useful since the DB was moved. The stale DB at `/workspace/memory/` only has vector tables and should be cleaned up.

**Fix:**
```bash
# Fix the script
sed -i 's|workspace/memory/nox-mem.db|workspace/tools/nox-mem/nox-mem.db|' /root/.openclaw/scripts/wal-checkpoint.sh
```

---

## 4. Medium-Priority Findings

### MED-1: OpenClaw Version Mismatch in Docs

**Docs say:** v2026.3.31
**Actual:** v2026.4.5

This is not just cosmetic -- the docs warn "never add root keys not recognized by v2026.3.31." The actual version is v2026.4.5 which likely supports additional keys. The doc's safety guidance is based on stale version info.

### MED-2: 90 Sanitized Config Backups Not Cleaned Up

`/root/.openclaw/workspace/backups/` contains 90 `openclaw_SANITIZED-*.json` files from April 5. These appear to be leftovers from an automated sanitization loop that ran ~90 times in rapid succession (timestamps increment by 5 seconds).

**Fix:**
```bash
# These are all identical, keep one for reference
cp /root/.openclaw/workspace/backups/openclaw_SANITIZED-1775040207.json \
   /root/.openclaw/workspace/backups/openclaw_SANITIZED-SAMPLE.json
rm /root/.openclaw/workspace/backups/openclaw_SANITIZED-17750*.json
```

### MED-3: Older Config Backups World-Readable

Backups before Apr 6 have `644` permissions, while newer ones correctly have `600`. Old backups may contain API keys.

**Fix:**
```bash
chmod 600 /root/.openclaw/workspace/backups/openclaw_*.json
```

### MED-4: marker-env Python Venv Using 7.5 GB

`/root/.openclaw/tools/marker-env/` is a Python virtual environment consuming 7.5 GB of disk. This is the single largest directory on the system (18% of used disk). If marker (PDF extraction tool) is not actively used, this can be reclaimed.

### MED-5: Two Different Node Binaries (node.bin vs node.real)

```
/usr/bin/node      -> bash wrapper calling node.real --no-warnings
/usr/bin/node.bin  -> 16 KB ELF binary (different from node.real)
/usr/bin/node.real -> 119 MB ELF binary (actual Node.js 22)
```

The wrapper calls `node.real`, not `node.bin`. `node.bin` appears to be the original binary from before the wrapper was created (per the CLAUDE.md instructions: "renomear novo binary para node.bin"). But the wrapper points to `node.real` instead. `node.bin` (16 KB) seems too small to be a real Node.js binary -- it may be a stub or shim from a package manager.

### MED-6: Yesterday's Log Had 4,856 Errors

`/tmp/openclaw/openclaw-2026-04-07.log` (21 MB) contained 4,856 lines matching error patterns. Today so far: 249 errors in 4,190 lines. The error rate has improved but yesterday's high count correlates with the gateway crash loops visible in journald.

### MED-7: Nox Workspace Agent Path Inconsistency in Crontab

The crontab has an inconsistent path for the `nox` agent:
```
OPENCLAW_WORKSPACE=/root/.openclaw/workspace/agents/nox  (crontab line for reindex)
```

Other agents use:
```
OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas  (no /workspace/ prefix)
```

The nox agent directory exists at both paths. Verify which is canonical.

### MED-8: No Groq/Gemini API Keys in .env

The env file only has 5 variables. No `GROQ_API_KEY` or `GEMINI_API_KEY` visible. RelayPlane config references these providers but may not have keys available, which would make the cascade fallback non-functional.

---

## 5. Documentation vs Reality Discrepancies

| Item | Docs Say | Reality |
|------|----------|---------|
| OpenClaw version | v2026.3.31 | **v2026.4.5** |
| Ollama status | Active service | **Disabled, dead** |
| Systemd services | 6 active | 5 active + 1 disabled (ollama) + 1 duplicate (watcher) |
| Gateway service Type | Type=simple, Restart=always | **Type=oneshot, RemainAfterExit=yes, no restart** |
| StartLimitBurst | 5 | **Not present in service file** |
| StartLimitIntervalSec | 120 | **Not present in service file** |
| Chunks count | 1,880 | **1,826** |
| Consolidated files | 18 done | **43 done** |
| DB size | 51 MB | **87 MB** |
| Agent fallbacks | Sonnet->Haiku->DeepSeek->Qwen->Llama | **Empty array []** |
| Crontab entries | 29 | **30** |
| Node wrapper | calls node.bin | **Calls node.real** |
| Env vars | Many including GROQ, GEMINI | **Only 5: ANTHROPIC x2, CLAUDE_CODE_OAUTH, NOTION, SLACK** |
| WAL checkpoint | Runs on production DB | **Targets wrong/stale DB** |
| Health check interval | */15 min | ***/15 min (matches)** |
| General health check | */30 min | ***/30 min (matches)** |
| Billing proxy | Removed per Apr 7 fix | **Still running on port 18801** |

---

## 6. Process Inventory

### Running Processes (what IS there)

| Process | PID | RSS | Port | Managed By |
|---------|-----|-----|------|------------|
| openclaw-gateway | 150775 | 608 MB | 18789, 18791, 43125 | systemd (oneshot) |
| relayplane-proxy | 148200 | 79 MB | 4100 | systemd (simple) |
| nox-mem-api | 1027 | 64 MB | 18800 | systemd (simple) |
| billing-proxy | 144370 | 50 MB | 18801 | **ORPHAN** (systemd --user) |
| nox-mem-watch | 144351 | 1 MB | -- | systemd (simple) |
| nox-mem-watcher | 144352 | 1 MB | -- | systemd (simple) **DUPLICATE** |
| claude (orphan 1) | 65453 | 208 MB | 33373 | **ORPHAN** (17h old) |
| claude (orphan 2) | 65590 | 208 MB | 43087 | **ORPHAN** (17h old) |
| claude (orphan 3) | 65951 | 208 MB | 37439 | **ORPHAN** (17h old) |
| tailscaled | 1048 | 44 MB | 34764, 54996 | systemd |
| fail2ban | 1021 | 50 MB | -- | systemd |

**Total orphaned memory:** ~674 MB (3 claude + 1 billing proxy)

### What is NOT running (should be)

| Process | Expected | Status |
|---------|----------|--------|
| ollama | Active per docs | **Disabled, dead** |

---

## 7. Network Ports

| Port | Process | Binding | UFW Rule | Status |
|------|---------|---------|----------|--------|
| 22 | sshd | 0.0.0.0 | ALLOW Anywhere | OK |
| 4100 | relayplane | 0.0.0.0 | Tailscale only | CONCERN: bound to all interfaces |
| 18789 | gateway | 0.0.0.0 | Tailscale only | CONCERN: wrapper says loopback |
| 18791 | gateway | 127.0.0.1 | None needed | OK (internal) |
| 18800 | nox-mem-api | 0.0.0.0 | Tailscale only | OK |
| 18801 | billing-proxy | 127.0.0.1 | None | OK (loopback only) |
| 43125 | gateway | 127.0.0.1 | None needed | OK (internal) |

---

## 8. Security Assessment

| Check | Status | Notes |
|-------|--------|-------|
| UFW active | PASS | Default deny, SSH + Tailscale rules |
| fail2ban active | PASS | 1 jail (sshd) |
| .env permissions | PASS | 600 (root only) |
| credentials.json perms | **FAIL** | 644 -- world-readable |
| google_client_secret | **FAIL** | 644 -- world-readable |
| Tokens in ps output | **FAIL** | OAuth tokens visible in process args |
| Old backup perms | **FAIL** | Some 644 (contain API keys) |
| Gateway binding | **WARN** | 0.0.0.0 despite --bind loopback intent |
| RelayPlane binding | **WARN** | 0.0.0.0 (relies solely on UFW) |

---

## 9. Crontab Assessment

30 active entries. Key observations:

- **Config drift monitor** (new, not in docs): runs every 30 min, good addition
- **Token refresh** (new, not in docs): runs every 4 hours, refreshes Claude MAX OAuth
- **Forge CC token check** (new): runs Monday 09:00
- **Sync verify** (not in docs): runs daily 06:00
- **Compact** (not in docs): runs Sunday 01:00

No conflicting schedules detected. Sunday is the busiest day: compact (01:00), vectorize (04:00), session-distill (05:00), pull-shared (06:05), kg-build (21:35), pull-shared (23:55).

---

## 10. Prioritized Remediation Plan

### Immediate (do now)

```bash
# 1. Kill orphaned processes leaking tokens
kill 65452 65453 65572 65590 65949 65951

# 2. Fix credential permissions
chmod 600 /root/.claude-max/credentials.json
chmod 600 /root/.openclaw/workspace/google_client_secret.json
chmod 600 /root/.openclaw/workspace/backups/openclaw_*.json

# 3. Rotate exposed tokens (tokens were visible in ps output)
claude auth login  # generates new tokens
```

### Today

```bash
# 4. Disable duplicate watcher
systemctl stop nox-mem-watcher.service
systemctl disable nox-mem-watcher.service

# 5. Enable Ollama
systemctl enable ollama.service
systemctl start ollama.service

# 6. Fix WAL checkpoint path
sed -i 's|workspace/memory/nox-mem.db|workspace/tools/nox-mem/nox-mem.db|' \
  /root/.openclaw/scripts/wal-checkpoint.sh

# 7. Clean up sanitized backup spam
cd /root/.openclaw/workspace/backups/
ls openclaw_SANITIZED-*.json | tail -n+2 | xargs rm
```

### This Week

```bash
# 8. Decide on billing proxy: kill or create a systemd service
kill 144370  # if no longer needed
# OR
# Create /etc/systemd/system/openclaw-billing-proxy.service

# 9. Fix gateway bind conflict
# Either change config to "bind": "loopback"
# Or remove --bind loopback from wrapper

# 10. Assess if marker-env (7.5 GB) is still needed
du -sh /root/.openclaw/tools/marker-env/

# 11. Verify GROQ_API_KEY and GEMINI_API_KEY are available to RelayPlane
# If not in .env, the cascade fallback is non-functional

# 12. Consider restructuring gateway service to Type=simple or Type=forking
# to get proper process tracking and automatic restart
```

### Documentation Updates Needed

- OpenClaw version: v2026.3.31 -> v2026.4.5
- Ollama status: active -> disabled
- Gateway service Type: simple -> oneshot
- Chunks: 1880 -> 1826
- Consolidated: 18 -> 43
- DB size: 51 MB -> 87 MB
- Agent fallbacks: cascade list -> empty array
- Node wrapper: node.bin -> node.real
- Add billing proxy to service inventory
- Add config-drift-monitor and token-refresh-max to cron docs
- Remove "nox-mem-watcher" from docs (duplicate of nox-mem-watch)

---

## 11. Overall Health Score

| Category | Score | Notes |
|----------|-------|-------|
| System Resources | 9/10 | Plenty of headroom |
| Service Health | 4/10 | Wrong service type, duplicates, orphans, disabled Ollama |
| Security | 5/10 | Tokens leaked in ps, world-readable creds |
| Configuration | 4/10 | Empty fallbacks, wrong WAL path, bind conflict |
| Documentation Accuracy | 3/10 | 15+ discrepancies found |
| Monitoring | 6/10 | Health checks exist but rely on cron, not systemd |
| Backup | 6/10 | Config backups work, DB backup targets wrong path |
| Reliability | 5/10 | 55 restart attempts today, no auto-restart |

**Overall: 5.3/10 -- Needs significant remediation.**

The system is running but held together by cron-based health checks compensating for broken systemd configuration. The gateway has no proper process supervision, model fallbacks are non-functional, and there are active security issues with exposed credentials. The documentation is significantly out of date with 15+ factual discrepancies.

---

*Audit completed 2026-04-08 10:50 BRT by SRE Agent.*
