#!/usr/bin/env bash
# =============================================================================
# OpenClaw 2026.4.29 upgrade — delta-specific checks
# Companion to /root/upgrade-zero-downtime.sh (already parameterized for any version)
#
# Usage:
#   bash upgrade-v29-deltas.sh --pre   # validate target tarball BEFORE atomic swap
#   bash upgrade-v29-deltas.sh --post  # validate behavior AFTER swap
#
# Deltas covered (vs .26 baseline):
#   D1: restart-stale-pids may ship as 2 files in .29 (BIi8yj5G impl + FLUx2q0b wrapper);
#       monkey-patch script must target the impl file, not the wrapper.
#   D2: messages.visibleReplies new global flag — verify default=false (no behavior change).
#   D3: agents.defaults.queueing.mode default changed to "steer" (was 1-at-a-time queue).
#   D4: commitments.enabled new opt-in — verify off by default.
#   D5: bounded subagent orphan recovery (#74864) — telemetry validation post-swap.
#   D6: gateway EADDRINUSE → RestartPreventExitStatus=78 (#75115) — check no restart loop.
#   D7: embedded-runner skip blank prompts (#74137) — verify Telegram lanes don't error.
#
# Exit codes:
#   0  all checks passed
#   10 D1 failed (monkey-patch target unclear)
#   20 D2-D4 failed (config drift)
#   30 D5-D7 failed (post-swap behavior regression)
# =============================================================================

set -euo pipefail

MODE="${1:-}"
TARGET="2026.4.29"
TARBALL_DIR="${TARBALL_DIR:-/tmp/openclaw-v29-tarball}"
EXTRACT_DIR="${EXTRACT_DIR:-${TARBALL_DIR}/extract}"
LOG="/var/log/openclaw-v29-deltas-$(date +%Y%m%d-%H%M%S).log"

exec > >(tee -a "$LOG") 2>&1
echo "=== OpenClaw v${TARGET} delta checks (mode=${MODE}) — $(date -Is) ==="

case "$MODE" in
  --pre)  ;;
  --post) ;;
  *) echo "Usage: $0 --pre | --post" >&2; exit 1 ;;
esac

fail() { echo "    FAIL: $*" >&2; FAILS=$((FAILS+1)); }
pass() { echo "    PASS: $*"; }
warn() { echo "    WARN: $*" >&2; }
FAILS=0

# =============================================================================
# PRE-SWAP CHECKS (run before atomic swap; tarball must exist at $EXTRACT_DIR)
# =============================================================================
if [[ "$MODE" == "--pre" ]]; then
  echo ""
  echo "━━━ PRE-SWAP DELTA VALIDATION ━━━"

  # Stage tarball if not already extracted
  if [[ ! -d "$EXTRACT_DIR/package/dist" ]]; then
    echo "[stage] Pulling openclaw@${TARGET} tarball..."
    rm -rf "$TARBALL_DIR"; mkdir -p "$TARBALL_DIR" "$EXTRACT_DIR"
    cd "$TARBALL_DIR"
    npm pack "openclaw@${TARGET}" >/dev/null 2>&1
    tar xzf "openclaw-${TARGET}.tgz" -C "$EXTRACT_DIR"
    cd - >/dev/null
  fi
  DIST="$EXTRACT_DIR/package/dist"
  [[ -d "$DIST" ]] || { echo "ERROR: $DIST missing"; exit 1; }

  # ─── D1: restart-stale-pids structure ───────────────────────────────────────
  echo ""
  echo "[D1] restart-stale-pids file layout"
  PATCH_FILES=( $(ls "$DIST"/restart-stale-pids-*.js 2>/dev/null) )
  COUNT=${#PATCH_FILES[@]}
  echo "    file count: $COUNT"
  for f in "${PATCH_FILES[@]}"; do
    LINES=$(wc -l < "$f")
    HAS_IMPL=$(grep -c "function cleanStaleGatewayProcessesSync(portOverride)" "$f" || true)
    HAS_REEXPORT=$(grep -cE "^export.*cleanStaleGateway|from ['\"]\\./restart-stale-pids" "$f" || true)
    echo "    $(basename "$f"): lines=$LINES impl=$HAS_IMPL reexport=$HAS_REEXPORT"
  done

  IMPL_FILES=( $(grep -l "function cleanStaleGatewayProcessesSync(portOverride) {" "$DIST"/restart-stale-pids-*.js 2>/dev/null || true) )
  if [[ ${#IMPL_FILES[@]} -eq 0 ]]; then
    fail "D1: NO file contains cleanStaleGatewayProcessesSync impl — patch will FAIL"
    echo "    Bundle layout changed. Inspect manually:" >&2
    echo "    ls $DIST/restart-stale-pids-*.js" >&2
    exit 10
  elif [[ ${#IMPL_FILES[@]} -eq 1 ]]; then
    pass "D1: single impl file: $(basename "${IMPL_FILES[0]}")"
    # Validate the regex pattern matches
    if ! python3 - "${IMPL_FILES[0]}" <<'PY' 2>/dev/null
import re, sys
src = open(sys.argv[1]).read()
pat = r'(function cleanStaleGatewayProcessesSync\(portOverride\) \{\n\ttry \{\n)(\t\tconst port)'
sys.exit(0 if re.search(pat, src) else 1)
PY
    then
      fail "D1: monkey-patch regex pattern does not match — update reapply-monkey-patch.sh"
      exit 10
    fi
    pass "D1: regex pattern matches — existing reapply-monkey-patch.sh compatible"
  else
    warn "D1: multiple impl files (${#IMPL_FILES[@]}) — patch script uses head -1, may need update"
    for f in "${IMPL_FILES[@]}"; do echo "      $(basename "$f")"; done
  fi

  # ─── D2: messages.visibleReplies default ────────────────────────────────────
  echo ""
  echo "[D2] messages.visibleReplies global flag default"
  VR_REFS=$(grep -rl "visibleReplies" "$DIST"/*.js 2>/dev/null | wc -l)
  if [[ "$VR_REFS" -gt 0 ]]; then
    DEFAULT_FALSE=$(grep -hE "visibleReplies['\"]?\\s*[:=]\\s*(false|undefined|null)" "$DIST"/*.js 2>/dev/null | wc -l || true)
    if [[ "$DEFAULT_FALSE" -gt 0 ]]; then
      pass "D2: visibleReplies default appears falsy in $DEFAULT_FALSE definition(s)"
    else
      warn "D2: visibleReplies references found ($VR_REFS files) but no falsy default detected — review schema"
    fi
  else
    pass "D2: no visibleReplies references in dist (feature gated or absent)"
  fi

  # ─── D3: queueing.mode "steer" default ──────────────────────────────────────
  echo ""
  echo "[D3] active-run queueing default mode"
  STEER_REFS=$(grep -rE "queueing\.mode|active.{0,3}run.{0,3}queue" "$DIST"/*.js 2>/dev/null | wc -l || true)
  STEER_DEFAULT=$(grep -hE "['\"]steer['\"]" "$DIST"/*.js 2>/dev/null | head -3 | wc -l || true)
  echo "    queueing references: $STEER_REFS, steer literal: $STEER_DEFAULT"
  if [[ "$STEER_REFS" -gt 0 ]]; then
    warn "D3: new steering default is 'steer' — agents may behave differently with concurrent inputs"
    echo "      If issues: openclaw config set agents.defaults.queueing.mode queue"
  else
    pass "D3: no queueing schema in dist (feature absent)"
  fi

  # ─── D4: commitments default off ────────────────────────────────────────────
  echo ""
  echo "[D4] commitments.enabled default"
  COMMIT_REFS=$(grep -rE "commitments\.(enabled|maxPerDay)" "$DIST"/*.js 2>/dev/null | wc -l || true)
  if [[ "$COMMIT_REFS" -gt 0 ]]; then
    COMMIT_DEFAULT=$(grep -hE "commitments\.enabled[^a-z]*=\\s*false|enabled:\\s*false" "$DIST"/*.js 2>/dev/null | wc -l || true)
    if [[ "$COMMIT_DEFAULT" -gt 0 ]]; then
      pass "D4: commitments.enabled default=false ($COMMIT_DEFAULT references)"
    else
      warn "D4: commitments schema present but default unclear — explicitly set in openclaw.json"
      echo "      openclaw config set agents.defaults.commitments.enabled false"
    fi
  else
    pass "D4: commitments feature absent"
  fi

  # ─── D5/D6/D7 are post-swap only ────────────────────────────────────────────
  echo ""
  echo "[D5-D7] (post-swap behavior — run --post after atomic swap)"

  echo ""
  if [[ "$FAILS" -eq 0 ]]; then
    echo "━━━ PRE-SWAP DELTAS: ALL PASS ━━━"
    echo "Proceed with: bash /root/upgrade-zero-downtime.sh ${TARGET}"
  else
    echo "━━━ PRE-SWAP DELTAS: ${FAILS} FAILURES ━━━"
    exit 20
  fi
fi

# =============================================================================
# POST-SWAP CHECKS (run after atomic swap completes)
# =============================================================================
if [[ "$MODE" == "--post" ]]; then
  echo ""
  echo "━━━ POST-SWAP DELTA VALIDATION ━━━"

  # Confirm version
  VERSION=$(openclaw --version 2>&1 | awk '{print $2}')
  if [[ "$VERSION" != "$TARGET" ]]; then
    fail "version mismatch: expected $TARGET, got $VERSION"
    exit 30
  fi
  pass "running openclaw $VERSION"

  # ─── D5: orphan recovery telemetry (#74864) ─────────────────────────────────
  echo ""
  echo "[D5] subagent orphan recovery telemetry"
  WEDGED=$(journalctl -u openclaw-gateway --since "10min ago" 2>/dev/null | grep -cE "wedged.session|tombstone|orphan.recovery" || true)
  RESTART_LOOP=$(journalctl -u openclaw-gateway --since "10min ago" 2>/dev/null | grep -cE "session.*restart|sessions\.json" || true)
  echo "    wedged/tombstone events (10min): $WEDGED"
  echo "    session restart events (10min):  $RESTART_LOOP"
  if [[ "$RESTART_LOOP" -gt 5 ]]; then
    fail "D5: $RESTART_LOOP session restarts in 10min — possible orphan recovery loop"
  else
    pass "D5: no orphan recovery loop detected"
  fi

  # ─── D6: EADDRINUSE handling (#75115) ───────────────────────────────────────
  echo ""
  echo "[D6] gateway port conflict handling"
  EADDR=$(journalctl -u openclaw-gateway --since "10min ago" 2>/dev/null | grep -c "EADDRINUSE" || true)
  RESTART_PREVENT=$(systemctl show openclaw-gateway -p RestartPreventExitStatus 2>/dev/null | grep -o "78" || echo "")
  echo "    EADDRINUSE events: $EADDR"
  echo "    RestartPreventExitStatus=78 in unit: ${RESTART_PREVENT:-not set}"
  if [[ "$EADDR" -gt 0 && -z "$RESTART_PREVENT" ]]; then
    warn "D6: EADDRINUSE seen but RestartPreventExitStatus=78 not configured — risk of restart loop"
    echo "      Add to /etc/systemd/system/openclaw-gateway.service.d/override.conf:"
    echo "        [Service]"
    echo "        RestartPreventExitStatus=78"
  else
    pass "D6: no port conflict issues"
  fi

  # ─── D7: embedded-runner blank prompt fix (#74137) ──────────────────────────
  echo ""
  echo "[D7] embedded-runner blank prompt handling"
  BLANK_ERRORS=$(journalctl -u openclaw-gateway --since "30min ago" 2>/dev/null | grep -cE "empty.user.input|blank.prompt.error|MessageContentEmpty" || true)
  echo "    empty-input provider errors (30min): $BLANK_ERRORS"
  if [[ "$BLANK_ERRORS" -gt 0 ]]; then
    warn "D7: $BLANK_ERRORS blank-prompt errors — fix may not be reaching Telegram lanes"
  else
    pass "D7: no blank-prompt errors"
  fi

  # ─── Health invariants ──────────────────────────────────────────────────────
  echo ""
  echo "[health] api endpoint + vectorCoverage"
  if HEALTH=$(curl -s --max-time 5 http://127.0.0.1:18802/api/health); then
    EMBEDDED=$(echo "$HEALTH" | jq -r '.vectorCoverage.embedded // 0')
    TOTAL=$(echo "$HEALTH" | jq -r '.chunks.total // 0')
    SAL=$(echo "$HEALTH" | jq -r '.salience.mode // "unknown"')
    echo "    chunks: total=$TOTAL embedded=$EMBEDDED salience=$SAL"
    if [[ "$EMBEDDED" == "$TOTAL" && "$TOTAL" -gt 0 ]]; then
      pass "health: vectorCoverage 100%"
    else
      fail "health: vectorCoverage gap (embedded=$EMBEDDED total=$TOTAL)"
    fi
  else
    fail "health: nox-mem-api :18802 not responding"
  fi

  # ─── Monkey-patch marker ────────────────────────────────────────────────────
  echo ""
  echo "[patch] monkey-patch marker present"
  IMPL_FILE=$(grep -l "function cleanStaleGatewayProcessesSync(portOverride) {" \
              /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js 2>/dev/null | head -1)
  if [[ -n "$IMPL_FILE" ]] && grep -q "MONKEY-PATCH" "$IMPL_FILE"; then
    pass "patch: marker present in $(basename "$IMPL_FILE")"
  else
    fail "patch: monkey-patch marker MISSING — fratricide risk active"
  fi

  # ─── Fratricide indicator (last 5min) ───────────────────────────────────────
  FRAT=$(journalctl -u openclaw-gateway --since "5min ago" 2>/dev/null | \
         grep -cE "Gateway already running locally|cleanStale.*killed|SIGTERM.*own" || true)
  if [[ "$FRAT" -gt 0 ]]; then
    fail "fratricide: $FRAT events in last 5min — patch ineffective"
  else
    pass "fratricide: no events in last 5min"
  fi

  # ─── Anthropic 401 indicator ────────────────────────────────────────────────
  AUTH_401=$(journalctl -u openclaw-gateway --since "10min ago" 2>/dev/null | \
             grep -cE "401.*Anthropic|Invalid authentication credentials" || true)
  if [[ "$AUTH_401" -gt 0 ]]; then
    fail "auth: $AUTH_401 401 events — claude-cli credentials may be desynced"
  else
    pass "auth: no 401 errors"
  fi

  # ─── Discord channel sanity ─────────────────────────────────────────────────
  UNK_CHAN=$(journalctl -u openclaw-gateway --since "10min ago" 2>/dev/null | \
             grep -c "Unknown Channel" || true)
  if [[ "$UNK_CHAN" -gt 5 ]]; then
    fail "channels: $UNK_CHAN 'Unknown Channel' events — run delivery-queue-cleanup.sh"
  else
    pass "channels: no orphan delivery queue issues"
  fi

  # ─── Config drift checks (npm install -g resets defaults to RelayPlane!) ────
  echo ""
  echo "[config-drift] post-upgrade integrity (regra 5 do CLAUDE.md)"
  BASEURL=$(jq -r '.models.providers.anthropic.baseUrl // ""' /root/.openclaw/openclaw.json)
  if [[ "$BASEURL" == "https://api.anthropic.com" ]]; then
    pass "anthropic.baseUrl = api.anthropic.com (not RelayPlane :4100)"
  else
    fail "anthropic.baseUrl = $BASEURL — should be https://api.anthropic.com"
    echo "    Fix: openclaw config set models.providers.anthropic.baseUrl 'https://api.anthropic.com'"
  fi

  if systemctl is-active --quiet relayplane-proxy 2>/dev/null; then
    fail "relayplane-proxy ACTIVE — should be inactive+disabled (redundant)"
    echo "    Fix: systemctl stop relayplane-proxy && systemctl disable relayplane-proxy"
  else
    pass "relayplane-proxy inactive"
  fi

  PRIMARY=$(jq -r '.agents.defaults.model.primary // ""' /root/.openclaw/openclaw.json)
  if [[ "$PRIMARY" =~ ^(anthropic|claude-cli)/claude-(opus|sonnet) ]]; then
    pass "model.primary = $PRIMARY (Max OAuth)"
  else
    fail "model.primary = $PRIMARY — should be anthropic/claude-{opus,sonnet}-*"
  fi

  FALLBACK_LEAK=$(jq -r '.agents.defaults.model.fallbacks // [] | map(select(startswith("anthropic/"))) | length' /root/.openclaw/openclaw.json)
  if [[ "$FALLBACK_LEAK" == "0" ]]; then
    pass "fallbacks: no anthropic/* leak (would mask primary failure)"
  else
    fail "fallbacks contain $FALLBACK_LEAK anthropic/* entry — would mask CLI failure → bill"
  fi

  STUCK=0
  for a in main nox atlas boris cipher forge lex; do
    SF="/root/.openclaw/agents/$a/sessions/sessions.json"
    [[ -f "$SF" ]] || continue
    SC=$(jq -r '[.[] | select(.model | test("^(gemini|openai|gpt-)"))] | length' "$SF" 2>/dev/null || echo 0)
    [[ "$SC" -gt 0 ]] && { STUCK=$((STUCK+SC)); echo "    $a: $SC sessions stuck on fallback"; }
  done
  if [[ "$STUCK" == "0" ]]; then
    pass "sessions: no fallback stickiness"
  else
    warn "sessions: $STUCK total sessions stuck on Gemini/GPT fallback"
    echo "    Fix: reset stuck sessions per agent (regra 11 do CLAUDE.md)"
  fi

  echo ""
  if [[ "$FAILS" -eq 0 ]]; then
    echo "━━━ POST-SWAP DELTAS: ALL PASS ━━━"
    echo ""
    echo "Next steps:"
    echo "  1. Smoke test each persona via Discord (nox/atlas/boris/cipher/forge/lex)"
    echo "  2. Watch /var/log/openclaw-gateway* for 30min"
    echo "  3. Update CLAUDE.md (version + monkey-patch hash)"
    echo "  4. Update docs/HANDOFF.md"
    echo "  5. Save memory observation"
  else
    echo "━━━ POST-SWAP DELTAS: ${FAILS} FAILURES ━━━"
    echo "Consider rollback: bash /root/rollback-zero-downtime.sh ${TARGET} \\"
    echo "  /usr/lib/node_modules/openclaw.bak-pre-${TARGET} \\"
    echo "  /root/backups/openclaw-pre-${TARGET}"
    exit 30
  fi
fi
