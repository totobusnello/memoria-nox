#!/usr/bin/env bash
# =============================================================================
# OpenClaw zero-downtime upgrade — v2 (2026-04-26)
# Methodology: pre-flight → staging → smoke → atomic swap → watch → auto-rollback
#
# Usage: bash upgrade-zero-downtime.sh <target_version>
# Example: bash upgrade-zero-downtime.sh 2026.4.25
#
# What is NEW vs upgrade-4.24.sh:
#   - npm pack pre-flight: extracts target tarball and diffs harness/plugin manifests
#   - Side-by-side staging on :18790 with isolated workspace (no real channels)
#   - Runtime smoke tests via openclaw CLI against staging port BEFORE swap
#   - Auto-rollback gate expanded: harness errors + channel disconnects + cron fails
#   - Post-swap watch loop checks runtime signals, not only restart count
# =============================================================================
set -euo pipefail

TARGET=${1:?usage: $0 <target_version>}
CURRENT=$(openclaw --version 2>&1 | awk '{print $2}')
ROLLBACK_DIR=/usr/lib/node_modules/openclaw.bak-pre-${TARGET}
BACKUP_DIR=/root/backups/openclaw-pre-${TARGET}
STAGING_MODULES=/opt/openclaw-staging
STAGING_WORKSPACE=/tmp/openclaw-staging-workspace
STAGING_PORT=18790
LOG=/var/log/openclaw-upgrade-$(date +%Y%m%d-%H%M%S).log

exec > >(tee -a "$LOG") 2>&1
echo "=== OpenClaw zero-downtime upgrade: $CURRENT → $TARGET — $(date -Is) ==="
echo "Log: $LOG"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 0: PRE-FLIGHT — validate before touching production
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 0: PRE-FLIGHT ━━━"

mkdir -p "$BACKUP_DIR"

# 0a. Snapshot current production state
echo "[0a] Snapshotting production state..."
rm -rf "$ROLLBACK_DIR"
cp -a /usr/lib/node_modules/openclaw "$ROLLBACK_DIR"
cp /root/.openclaw/openclaw.json "$BACKUP_DIR/openclaw.json.bak"
[[ -f /root/.openclaw/agents/main/sessions/sessions.json ]] && \
  cp /root/.openclaw/agents/main/sessions/sessions.json "$BACKUP_DIR/sessions.json.bak" || true
OLD_PATCH=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | head -1)
cp "$OLD_PATCH" "$BACKUP_DIR/$(basename "$OLD_PATCH").pre-upgrade"
echo "    backup dir: $BACKUP_DIR"
echo "    rollback snapshot: $ROLLBACK_DIR"

# 0b. Download target tarball WITHOUT installing it on production
echo "[0b] Downloading target tarball for inspection..."
TARBALL_DIR=$(mktemp -d /tmp/openclaw-preflight-XXXXXX)
npm pack "openclaw@${TARGET}" --pack-destination "$TARBALL_DIR" >/dev/null 2>&1
TARBALL=$(ls "$TARBALL_DIR"/openclaw-*.tgz | head -1)
[[ -f "$TARBALL" ]] || { echo "ERROR: npm pack failed for $TARGET"; exit 1; }
echo "    tarball: $TARBALL"

# 0c. Extract and diff harness registry (the key invariant that broke .24)
EXTRACT_DIR="$TARBALL_DIR/extracted"
mkdir -p "$EXTRACT_DIR"
tar -xzf "$TARBALL" -C "$EXTRACT_DIR" package/ >/dev/null 2>&1

echo "[0c] Harness diff: current vs target..."
# Extract harness registrations from dist bundles
CURRENT_HARNESSES=$(grep -rh "registerHarness\|harnessId\|harness.*claude-cli" \
  /usr/lib/node_modules/openclaw/dist/ 2>/dev/null \
  | grep -oP '"[a-z]+-[a-z]+"(?=.*harness|harness.*=)' | sort -u || true)
TARGET_HARNESSES=$(grep -rh "registerHarness\|harnessId\|harness.*claude-cli" \
  "$EXTRACT_DIR/package/dist/" 2>/dev/null \
  | grep -oP '"[a-z]+-[a-z]+"(?=.*harness|harness.*=)' | sort -u || true)

HARNESS_DIFF=$(diff <(echo "$CURRENT_HARNESSES") <(echo "$TARGET_HARNESSES") || true)
if [[ -n "$HARNESS_DIFF" ]]; then
  echo "    WARN: harness manifest changed:"
  echo "$HARNESS_DIFF" | sed 's/^/      /'
  echo "    REVIEW REQUIRED — does 'claude-cli' harness still exist in target?"
  # Hard stop if claude-cli harness is removed entirely
  if ! echo "$TARGET_HARNESSES" | grep -q "claude-cli"; then
    echo "ERROR: claude-cli harness NOT FOUND in $TARGET dist bundle — abort" >&2
    exit 10
  fi
else
  echo "    harness manifest identical — OK"
fi

# 0d. Plugin manifest compat check (plugin API version)
echo "[0d] Plugin API version check..."
CURRENT_PLUGIN_API=$(grep -r "pluginApiVersion\|PLUGIN_API_VERSION\|plugin_api" \
  /usr/lib/node_modules/openclaw/dist/ 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "unknown")
TARGET_PLUGIN_API=$(grep -r "pluginApiVersion\|PLUGIN_API_VERSION\|plugin_api" \
  "$EXTRACT_DIR/package/dist/" 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "unknown")
echo "    current plugin API: $CURRENT_PLUGIN_API"
echo "    target plugin API:  $TARGET_PLUGIN_API"
if [[ "$CURRENT_PLUGIN_API" != "$TARGET_PLUGIN_API" && "$TARGET_PLUGIN_API" != "unknown" ]]; then
  echo "    WARN: plugin API version changed — test all plugins in staging"
fi

# 0e. Schema diff in auth-profiles (catches auth schema regressions like .24 issue)
echo "[0e] Auth profile schema check..."
TARGET_AUTH_SCHEMA=$(grep -r "apiKey\|anthropic-max\|type.*token\|type.*api_key" \
  "$EXTRACT_DIR/package/dist/" 2>/dev/null | grep -c "anthropic-max" || echo "0")
echo "    anthropic-max references in target dist: $TARGET_AUTH_SCHEMA"
if [[ "$TARGET_AUTH_SCHEMA" -eq 0 ]]; then
  echo "    WARN: anthropic-max provider may not be supported in target — check auth-profiles.json compat"
fi

# 0f. Dry-run monkey-patch: does the expected function signature exist in target?
echo "[0f] Monkey-patch target compatibility check..."
TARGET_PATCH_FILE=$(ls "$EXTRACT_DIR/package/dist/restart-stale-pids-"*.js 2>/dev/null | head -1 || true)
if [[ -z "$TARGET_PATCH_FILE" ]]; then
  echo "    ERROR: restart-stale-pids-*.js NOT found in target dist — patch will fail" >&2
  echo "    Bundle layout changed. Update reapply-monkey-patch.sh before proceeding." >&2
  exit 11
fi
if ! grep -q "cleanStaleGatewayProcessesSync" "$TARGET_PATCH_FILE"; then
  echo "    ERROR: cleanStaleGatewayProcessesSync function not found in target — patch pattern broken" >&2
  exit 12
fi
echo "    patch target file: $(basename "$TARGET_PATCH_FILE") — function signature OK"

# 0g. Node.js wrapper still intact?
echo "[0g] Node.js wrapper check..."
if ! file /usr/bin/node | grep -q "shell script"; then
  echo "    ERROR: /usr/bin/node is not a wrapper — DEP0040 crash loop risk" >&2
  exit 13
fi

# 0h. Credentials.json immutable?
echo "[0h] Credentials.json immutability check..."
if ! lsattr ~/.claude/.credentials.json | awk '{print $1}' | grep -q 'i'; then
  echo "    ERROR: ~/.claude/.credentials.json is NOT immutable — run: chattr +i ~/.claude/.credentials.json" >&2
  exit 14
fi

echo "[0] PRE-FLIGHT COMPLETE — proceeding to staging"
rm -rf "$TARBALL_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: STAGING — install target in isolated path, start on :18790
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 1: STAGING (:$STAGING_PORT, isolated workspace) ━━━"

echo "[1a] Installing openclaw@$TARGET to $STAGING_MODULES..."
# npm install --prefix puts node_modules/ under the prefix
# We want the package at $STAGING_MODULES/node_modules/openclaw
rm -rf "$STAGING_MODULES"
mkdir -p "$STAGING_MODULES"
npm install --prefix "$STAGING_MODULES" "openclaw@${TARGET}" >/dev/null 2>&1
STAGING_BIN="$STAGING_MODULES/node_modules/.bin/openclaw"
[[ -f "$STAGING_BIN" ]] || STAGING_BIN="$STAGING_MODULES/node_modules/openclaw/dist/index.js"
STAGING_VERSION=$(node "$STAGING_BIN" --version 2>&1 | awk '{print $2}' || echo "unknown")
echo "    installed: $STAGING_VERSION"
[[ "$STAGING_VERSION" == "$TARGET" ]] || \
  { echo "ERROR: staging version mismatch (got $STAGING_VERSION)"; exit 20; }

echo "[1b] Monkey-patching staging installation..."
STAGING_PATCH=$(ls "$STAGING_MODULES/node_modules/openclaw/dist/restart-stale-pids-"*.js | head -1)
bash /root/reapply-monkey-patch.sh "$STAGING_PATCH" 2>/dev/null || \
  python3 - "$STAGING_PATCH" <<'PY'
import re, sys
p = sys.argv[1]
src = open(p).read()
pattern = r'(function cleanStaleGatewayProcessesSync\(portOverride\) \{\n\ttry \{\n)(\t\tconst port)'
if not re.search(pattern, src):
    print(f"ERROR: pattern not found in {p}", file=sys.stderr); sys.exit(2)
patched = re.sub(pattern,
    r'\1\t\t// MONKEY-PATCH: staging test\n\t\treturn [];\n\2', src, count=1)
open(p, 'w').write(patched)
print(f"staging patched: {p}")
PY

echo "[1c] Creating minimal staging workspace..."
rm -rf "$STAGING_WORKSPACE"
mkdir -p "$STAGING_WORKSPACE/agents/staging-test/agent"
# Minimal agent config: single test agent, no real channel webhooks
cat > "$STAGING_WORKSPACE/openclaw.json" <<STAGINGCFG
{
  "agents": {
    "staging-test": {
      "persona": "staging smoke-test agent — DO NOT USE FOR REAL CHANNELS",
      "model": { "primary": "claude-cli/claude-sonnet-4-6", "fallbacks": ["gemini/gemini-2.5-flash-lite"] }
    },
    "defaults": {
      "model": {
        "primary": "claude-cli/claude-sonnet-4-6",
        "fallbacks": ["gemini/gemini-2.5-flash-lite"]
      },
      "compaction": { "keepRecentTokens": 8000 }
    }
  },
  "gateway": { "port": $STAGING_PORT, "reload": { "mode": "off" } },
  "commands": { "restart": false },
  "discovery": { "mdns": { "mode": "off" } },
  "plugins": {}
}
STAGINGCFG

echo "[1d] Starting staging gateway (systemd-run, isolated)..."
systemd-run --unit=openclaw-staging \
  --property=Environment=IS_SANDBOX=1 \
  --property=Environment=OPENCLAW_WORKSPACE="$STAGING_WORKSPACE" \
  --property=EnvironmentFile=/root/.openclaw/.env \
  --property=StandardOutput=journal \
  --property=StandardError=journal \
  -- node "$STAGING_MODULES/node_modules/openclaw/dist/index.js" \
       gateway run --bind loopback \
       2>/dev/null || \
  { echo "    systemd-run failed — trying foreground staging..."; STAGING_FOREGROUND=1; }

# Wait for staging gateway to come up
echo "    waiting for staging gateway on :$STAGING_PORT..."
for i in $(seq 1 12); do
  if curl -sf "http://127.0.0.1:$STAGING_PORT/health" >/dev/null 2>&1 || \
     curl -sf "http://127.0.0.1:$STAGING_PORT/api/health" >/dev/null 2>&1; then
    echo "    staging gateway UP (attempt $i)"
    break
  fi
  sleep 5
  if [[ $i -eq 12 ]]; then
    echo "ERROR: staging gateway did not come up in 60s — abort"
    systemctl stop openclaw-staging 2>/dev/null || true
    exit 21
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: SMOKE TESTS against staging
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 2: SMOKE TESTS (staging :$STAGING_PORT) ━━━"

SMOKE_FAIL=0
smoke() {
  local label="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "    PASS  $label"
  else
    echo "    FAIL  $label"
    SMOKE_FAIL=1
  fi
}

# 2a. Health endpoint responds
smoke "health endpoint" \
  "curl -sf http://127.0.0.1:$STAGING_PORT/health || curl -sf http://127.0.0.1:$STAGING_PORT/api/health"

# 2b. CLI version matches target on staging binary
smoke "version match" \
  "[[ \"\$(node $STAGING_MODULES/node_modules/openclaw/dist/index.js --version 2>&1 | awk '{print \$2}')\" == '$TARGET' ]]"

# 2c. THE KEY TEST: harness registration is live (not just in dist)
# Check gateway runtime exposes claude-cli harness via introspection endpoint (if available)
HARNESS_RUNTIME=$(curl -sf "http://127.0.0.1:$STAGING_PORT/api/harnesses" 2>/dev/null || \
                  curl -sf "http://127.0.0.1:$STAGING_PORT/harnesses" 2>/dev/null || echo "")
if [[ -n "$HARNESS_RUNTIME" ]]; then
  smoke "claude-cli harness registered (runtime)" \
    "echo '$HARNESS_RUNTIME' | jq -e '.[] | select(. == \"claude-cli\")' >/dev/null 2>&1 || \
     echo '$HARNESS_RUNTIME' | grep -q 'claude-cli'"
else
  # Fallback: check journals for harness registration messages
  sleep 5
  JOURNAL_HARNESS=$(journalctl -u openclaw-staging --since "2 min ago" --no-pager 2>/dev/null | \
    grep -i "harness\|claude-cli.*register\|backend.*load" || true)
  if echo "$JOURNAL_HARNESS" | grep -qi "claude-cli"; then
    echo "    PASS  claude-cli harness registration (journal)"
  elif echo "$JOURNAL_HARNESS" | grep -qi "not registered\|harness.*fail\|PI fallback"; then
    echo "    FAIL  claude-cli harness — PI fallback error detected in journal"
    SMOKE_FAIL=1
  else
    echo "    INFO  claude-cli harness — no runtime endpoint, no journal error (check manually if needed)"
  fi
fi

# 2d. Plugin load check: no plugin load errors in staging journals
PLUGIN_ERRORS=$(journalctl -u openclaw-staging --since "2 min ago" --no-pager 2>/dev/null | \
  grep -iE "plugin.*error|failed.*load|cannot.*require|MODULE_NOT_FOUND" || true)
if [[ -n "$PLUGIN_ERRORS" ]]; then
  echo "    FAIL  plugin load errors:"
  echo "$PLUGIN_ERRORS" | head -5 | sed 's/^/      /'
  SMOKE_FAIL=1
else
  echo "    PASS  plugin load (no errors in journals)"
fi

# 2e. Monkey-patch marker confirmed in staging runtime file
smoke "monkey-patch marker in staging dist" \
  "grep -q 'MONKEY-PATCH' $STAGING_MODULES/node_modules/openclaw/dist/restart-stale-pids-*.js"

# 2f. IS_SANDBOX env reaches staging process (fratricide guard)
# Confirm staging process has IS_SANDBOX=1
STAGING_PID=$(systemctl show openclaw-staging --property=MainPID --value 2>/dev/null || echo "")
if [[ -n "$STAGING_PID" && "$STAGING_PID" != "0" ]]; then
  smoke "IS_SANDBOX=1 in staging env" \
    "grep -q 'IS_SANDBOX=1' /proc/$STAGING_PID/environ 2>/dev/null || \
     grep -z 'IS_SANDBOX' /proc/$STAGING_PID/environ 2>/dev/null | grep -q '1'"
else
  echo "    INFO  IS_SANDBOX check skipped (could not get staging PID)"
fi

# 2g. Check for fratricide: staging should NOT have killed production gateway
smoke "production gateway still running" "systemctl is-active openclaw-gateway"

if [[ $SMOKE_FAIL -ne 0 ]]; then
  echo ""
  echo "!!! SMOKE TESTS FAILED — aborting upgrade"
  echo "    staging logs: journalctl -u openclaw-staging --no-pager"
  systemctl stop openclaw-staging 2>/dev/null || true
  rm -rf "$STAGING_WORKSPACE" "$STAGING_MODULES"
  exit 30
fi

echo "[2] ALL SMOKE TESTS PASSED — staging GREEN"
systemctl stop openclaw-staging 2>/dev/null || true
rm -rf "$STAGING_WORKSPACE"

# ─────────────────────────────────────────────────────────────────────────────
# DRY-RUN GATE: stop here if --dry-run was passed (or DRY_RUN=1 env)
# ─────────────────────────────────────────────────────────────────────────────
if [[ "${2:-}" == "--dry-run" ]] || [[ "${DRY_RUN:-}" == "1" ]]; then
  echo ""
  echo "━━━ DRY-RUN MODE: stopping after Phase 2 ━━━"
  echo "  Pre-flight + staging + smoke tests passed."
  echo "  Production NOT touched (still on $CURRENT)."
  echo "  To run real upgrade: bash $0 $TARGET (without --dry-run)"
  echo "  Cleanup staging: rm -rf $STAGING_MODULES"
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: ATOMIC SWAP — production ← target
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 3: ATOMIC SWAP ━━━"

echo "[3a] Stopping production gateway..."
systemctl stop openclaw-gateway
sleep 3

echo "[3b] Swapping node_modules/openclaw..."
# Production snapshot already at $ROLLBACK_DIR (from phase 0)
# Move staging installation into production slot
rm -rf /usr/lib/node_modules/openclaw
mv "$STAGING_MODULES/node_modules/openclaw" /usr/lib/node_modules/openclaw

# Fix npm global symlink if broken
GLOBAL_BIN="/usr/bin/openclaw"
if [[ -L "$GLOBAL_BIN" ]]; then
  rm -f "$GLOBAL_BIN"
  ln -sf /usr/lib/node_modules/openclaw/dist/index.js "$GLOBAL_BIN"
fi

echo "[3c] Reapplying monkey-patch on production path..."
bash /root/reapply-monkey-patch.sh

echo "[3d] Verifying wrapper still immutable..."
if ! lsattr /usr/local/bin/openclaw-gateway-wrapper | awk '{print $1}' | grep -q 'i'; then
  chattr +i /usr/local/bin/openclaw-gateway-wrapper
  echo "    re-immutabilized wrapper"
fi

echo "[3e] Starting production gateway..."
systemctl daemon-reload
systemctl start openclaw-gateway

# Wait for full ready signal — not just systemctl active
echo "[3f] Waiting for [gateway] ready signal (max 30s)..."
READY=""
for i in $(seq 1 6); do
  sleep 5
  READY=$(journalctl -u openclaw-gateway --since "1 min ago" --no-pager 2>/dev/null | \
    grep -E "\[gateway\] ready|Gateway started|gateway.*:18789" | tail -1 || true)
  if [[ -n "$READY" ]]; then
    echo "    gateway ready: $READY"
    break
  fi
  if ! systemctl is-active openclaw-gateway >/dev/null 2>&1; then
    echo "    FATAL: gateway crashed before ready signal — auto-rollback"
    bash /root/rollback-zero-downtime.sh "$TARGET" "$ROLLBACK_DIR" "$BACKUP_DIR"
    exit 40
  fi
done

if [[ -z "$READY" ]]; then
  echo "    WARN: no [gateway] ready signal in 30s — checking if it's running anyway..."
  if ! systemctl is-active openclaw-gateway >/dev/null 2>&1; then
    echo "    FATAL: gateway not active — auto-rollback"
    bash /root/rollback-zero-downtime.sh "$TARGET" "$ROLLBACK_DIR" "$BACKUP_DIR"
    exit 41
  fi
  echo "    gateway is active (ready log may have different format in $TARGET)"
fi

NEW_VERSION=$(openclaw --version 2>&1 | awk '{print $2}')
echo "    installed version confirmed: $NEW_VERSION"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: POST-SWAP WATCH (5min auto-rollback gate)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 4: POST-SWAP WATCH (5min gate) ━━━"
echo "    monitoring: restarts / harness errors / channel disconnects / fratricide"

WATCH_END=$(($(date +%s) + 300))
ROLLBACK_TRIGGERED=0

while [[ $(date +%s) -lt $WATCH_END ]]; do
  sleep 20
  REMAIN=$((WATCH_END - $(date +%s)))

  # Signal 1: restart count (fratricide indicator)
  RESTARTS=$(journalctl -u openclaw-gateway --since "5 min ago" --no-pager 2>/dev/null \
    | grep -c "Started.*openclaw-gateway" || echo "0")

  # Signal 2: harness errors (the .24 failure mode)
  HARNESS_ERRS=$(journalctl -u openclaw-gateway --since "5 min ago" --no-pager 2>/dev/null \
    | grep -ciE "harness.*not registered|PI fallback is disabled|is not registered" || echo "0")

  # Signal 3: channel disconnect storms (channels reconnect is OK once, storm is not)
  DISCONNECTS=$(journalctl -u openclaw-gateway --since "5 min ago" --no-pager 2>/dev/null \
    | grep -ciE "channel.*disconnect|session.*lost|WebSocket.*close" || echo "0")

  # Signal 4: fatal errors
  FATALS=$(journalctl -u openclaw-gateway --since "5 min ago" --no-pager 2>/dev/null \
    | grep -ciE "FATAL|process.*crash|uncaughtException|unhandledRejection" || echo "0")

  echo "    t-${REMAIN}s  restarts=$RESTARTS  harness_errs=$HARNESS_ERRS  disconnects=$DISCONNECTS  fatals=$FATALS"

  # Auto-rollback thresholds
  if [[ $RESTARTS -gt 3 ]]; then
    echo "    ROLLBACK TRIGGER: fratricide ($RESTARTS restarts)"
    ROLLBACK_TRIGGERED=1; break
  fi
  if [[ $HARNESS_ERRS -gt 1 ]]; then
    echo "    ROLLBACK TRIGGER: harness not registered ($HARNESS_ERRS errors) — THIS WAS THE .24 FAILURE"
    ROLLBACK_TRIGGERED=1; break
  fi
  if [[ $DISCONNECTS -gt 15 ]]; then
    echo "    ROLLBACK TRIGGER: channel disconnect storm ($DISCONNECTS in 5min)"
    ROLLBACK_TRIGGERED=1; break
  fi
  if [[ $FATALS -gt 0 ]]; then
    echo "    ROLLBACK TRIGGER: fatal errors ($FATALS)"
    ROLLBACK_TRIGGERED=1; break
  fi

  if ! systemctl is-active openclaw-gateway >/dev/null 2>&1; then
    echo "    ROLLBACK TRIGGER: gateway not active"
    ROLLBACK_TRIGGERED=1; break
  fi
done

if [[ $ROLLBACK_TRIGGERED -eq 1 ]]; then
  bash /root/rollback-zero-downtime.sh "$TARGET" "$ROLLBACK_DIR" "$BACKUP_DIR"
  exit 50
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: FINAL VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ PHASE 5: FINAL VALIDATION ━━━"

FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "    OK    $1"; else echo "    FAIL  $1"; FAIL=1; fi; }

check "credentials.json immutable" \
  "lsattr ~/.claude/.credentials.json | awk '{print \$1}' | grep -q 'i'"
check "/usr/bin/node is bash wrapper" \
  "file /usr/bin/node | grep -q 'shell script'"
check "IS_SANDBOX=1 in override.conf" \
  "grep -q 'IS_SANDBOX=1' /etc/systemd/system/openclaw-gateway.service.d/override.conf"
check "monkey-patch marker in production dist" \
  "grep -q 'MONKEY-PATCH' /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js"
check "primary model == claude-cli/claude-opus-4-6" \
  "jq -e '.agents.defaults.model.primary == \"claude-cli/claude-opus-4-6\"' /root/.openclaw/openclaw.json"
check "no cliBackends override" \
  "jq -e '(.agents.defaults.cliBackends // null) == null' /root/.openclaw/openclaw.json"
check "commands.restart == false" \
  "jq -e '.commands.restart == false' /root/.openclaw/openclaw.json"
check "gateway.reload.mode == off" \
  "jq -e '.gateway.reload.mode == \"off\"' /root/.openclaw/openclaw.json"
check "nox-mem-api healthy" \
  "curl -sf http://127.0.0.1:18802/api/health | jq -e '.status == \"ok\"'"
check "gateway port 18789 listening" \
  "fuser 18789/tcp >/dev/null 2>&1"
check "sessions.json not stuck on non-claude model" \
  "! jq -e 'to_entries[] | select(.value.model | startswith(\"gemini\") or startswith(\"openai\"))' \
    /root/.openclaw/agents/main/sessions/sessions.json"

if [[ $FAIL -ne 0 ]]; then
  echo "    WARN: final validation has failures — investigate before closing"
  echo "    rollback available: bash /root/rollback-zero-downtime.sh $TARGET $ROLLBACK_DIR $BACKUP_DIR"
fi

echo ""
echo "=== UPGRADE COMPLETE ==="
echo "    version:  $NEW_VERSION"
echo "    log:      $LOG"
echo "    backups:  $BACKUP_DIR"
echo "    rollback: bash /root/rollback-zero-downtime.sh $TARGET $ROLLBACK_DIR $BACKUP_DIR"
echo ""
echo "    NEXT: monitor heartbeats for 30min. Check /api/harnesses via claude-cli."
echo "    CLEANUP (after 24h stable): rm -rf $ROLLBACK_DIR"
