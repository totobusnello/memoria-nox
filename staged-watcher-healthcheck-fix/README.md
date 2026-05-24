# staged-watcher-healthcheck-fix

> **Single-line bugfix:** /api/health was reporting `services.nox-mem-watcher: false` because the healthcheck queries the **legacy** systemd unit name. The real running unit is `nox-mem-watch.service`. The legacy `nox-mem-watcher.service` was disabled per the 2026-04-08 audit (duplicata) but the API's `ALLOWED_SERVICES` set and the `services` JSON map still reference the old name.

## Background

| Unit name | Status (2026-05-24) | Notes |
|---|---|---|
| `nox-mem-watch.service` | ✅ active running | Canonical. Modern config (Restart=always, MemoryMax=512M, CPUQuota=50%). ExecStart calls `nox-mem-watch.sh`. |
| `nox-mem-watcher.service` | 💀 inactive dead | Legacy duplicate. Same ExecStart. Disabled per audit-2026-04-08. **Should be removed.** |

The healthcheck `/api/health.services["nox-mem-watcher"]` returns `false` because it queries the dead legacy unit. This caused the persistent yellow alert in the nox-mem-alerts Discord channel.

## Fix (2 lines)

```diff
--- a/src/api-server.ts
+++ b/src/api-server.ts
@@ -59,7 +59,7 @@
 const ALLOWED_SERVICES = new Set([
   "openclaw-gateway",
-  "nox-mem-watcher",
+  "nox-mem-watch",
   "nox-mem-api",
   "ollama",
   "tailscaled",
@@ -174,7 +174,7 @@
         const services = {
           "openclaw-gateway": serviceStatus("openclaw-gateway"),
-          "nox-mem-watcher": serviceStatus("nox-mem-watcher"),
+          "nox-mem-watch": serviceStatus("nox-mem-watch"),
           "ollama": serviceStatus("ollama"),
           "tailscaled": serviceStatus("tailscaled"),
         };
```

## JSON shape impact

**Before** (current prod):
```json
"services": {
  "openclaw-gateway": true,
  "nox-mem-watcher": false,   ← yellow alert source
  "ollama": false,
  "tailscaled": true
}
```

**After:**
```json
"services": {
  "openclaw-gateway": true,
  "nox-mem-watch": true,      ← yellow cleared
  "ollama": false,
  "tailscaled": true
}
```

## Downstream consumers audit

| Consumer | Parses the key? | Action |
|---|---|---|
| `scripts/vps-mirror/morning-report.sh` | No (only chunks/orphans/canary) | None |
| `sdk/python/tests/test_client.py` line 45 | Test fixture only | Updated in this PR |
| `sdk/typescript/src/__tests__/client.test.ts` line 74 | Test fixture only | Updated in this PR |
| Discord nox-mem-alerts cron | Uses morning-report output | None |

## Deploy procedure (parallel session)

```bash
# 1) Pull the corrected source on VPS
cd /root/.openclaw/workspace/tools/nox-mem
git pull origin main  # if repo is git-tracked there, OR pull diff via scp

# 2) Apply patch to live source (if not git-tracked)
sed -i 's/"nox-mem-watcher"/"nox-mem-watch"/g' src/api-server.ts

# 3) Rebuild
npm run build  # tsc -> dist/api-server.js

# 4) Restart API
systemctl restart nox-mem-api
sleep 3

# 5) Verify
curl -sS http://127.0.0.1:18802/api/health | jq '.services'
# Expected: "nox-mem-watch": true (not "nox-mem-watcher")

# 6) Optional cleanup — remove dead legacy unit
systemctl disable nox-mem-watcher.service 2>/dev/null || true
rm -f /etc/systemd/system/nox-mem-watcher.service
systemctl daemon-reload
```

## Verification post-deploy

- `/api/health.services["nox-mem-watch"]` → `true`
- `/api/health.services["nox-mem-watcher"]` → undefined (key removed)
- Discord nox-mem-alerts: yellow flag on `nox-mem-watcher` should clear on next morning report (06:30 BRT)

## References

- `archive/audits/audit-2026-04-08-live-vps.md:106-274` — original duplicate identification
- `archive/audits/hardening-report-2026-04-08.md:84` — disabled per hardening
- `audits/2026-05-21-vps-readiness-pre-Q4.md:56` — yellow flag previously documented as known-issue
- Memory: `[[reference_path_layout_canonical]]`
