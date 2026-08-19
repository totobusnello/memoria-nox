#!/usr/bin/env bash
# health-probe.test.sh — Restart-policy tests for the nox-mem-api block of
# health-probe.sh.
#
# Every external command the probe touches (curl, ss, systemctl, sqlite3, df,
# free, sleep) is stubbed on PATH, so the suite is hermetic: no network, no
# systemd, no DB, no real waiting.
#
# Usage:
#   ./health-probe.test.sh [--verbose]
#
# Requires: bash 4+, awk. Does NOT require the VPS or a running nox-mem.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE="${SCRIPT_DIR}/health-probe.sh"
VERBOSE=0
[[ "${1:-}" == "--verbose" ]] && VERBOSE=1

PASS=0; FAIL=0
SUITE_TMP="$(mktemp -d)"
trap 'rm -rf "$SUITE_TMP"' EXIT

ok()   { echo -e "\033[0;32m  PASS\033[0m $1"; PASS=$((PASS+1)); }
fail() { echo -e "\033[0;31m  FAIL\033[0m $1: $2"; FAIL=$((FAIL+1)); }

# --------------------------------------------------------------------------
# Stub environment
# --------------------------------------------------------------------------
STUB_BIN="${SUITE_TMP}/bin"
mkdir -p "$STUB_BIN"

cat > "${STUB_BIN}/curl" <<'STUB'
#!/usr/bin/env bash
# Health probes read a behavior from $STUB_STATE/curl_seq (one per call, last
# line repeats once exhausted). Anything that is not /api/health (the Discord
# webhook POST) just succeeds.
for arg in "$@"; do
  case "$arg" in *api/health*) HEALTH=1 ;; esac
done
[ "${HEALTH:-0}" = "1" ] || exit 0

SEQ="${STUB_STATE}/curl_seq"
behavior="ok"
if [ -s "$SEQ" ]; then
  behavior=$(head -1 "$SEQ")
  if [ "$(wc -l < "$SEQ")" -gt 1 ]; then
    tail -n +2 "$SEQ" > "${SEQ}.tmp" && mv "${SEQ}.tmp" "$SEQ"
  fi
fi
echo "$behavior" >> "${STUB_STATE}/curl_calls"
case "$behavior" in
  ok)      printf '200'; exit 0 ;;
  http500) printf '500'; exit 0 ;;
  http503) printf '503'; exit 0 ;;
  timeout) printf '000'; exit 28 ;;
  refused) printf '000'; exit 7 ;;
  *)       printf '000'; exit 7 ;;
esac
STUB

cat > "${STUB_BIN}/ss" <<'STUB'
#!/usr/bin/env bash
# Gateway port is always up; the API port follows $STUB_STATE/port_bound.
echo "LISTEN 0 511 127.0.0.1:18789 0.0.0.0:* users:((\"node\",pid=1,fd=1))"
if [ "$(cat "${STUB_STATE}/port_bound" 2>/dev/null || echo 1)" = "1" ]; then
  echo "LISTEN 0 511 127.0.0.1:${NOX_API_PORT:-18802} 0.0.0.0:* users:((\"node\",pid=2,fd=2))"
fi
STUB

cat > "${STUB_BIN}/systemctl" <<'STUB'
#!/usr/bin/env bash
case "${1:-}" in
  is-active)
    cat "${STUB_STATE}/unit_state" 2>/dev/null || echo active ;;
  show)
    echo 0 ;;
  restart)
    echo "$2" >> "${STUB_STATE}/systemctl_restarts"
    # Let a scenario decide what the service does after being restarted.
    if [ -s "${STUB_STATE}/curl_after_restart" ]; then
      cp "${STUB_STATE}/curl_after_restart" "${STUB_STATE}/curl_seq"
    fi
    ;;
esac
exit 0
STUB

cat > "${STUB_BIN}/sqlite3" <<'STUB'
#!/usr/bin/env bash
echo 94900
STUB

cat > "${STUB_BIN}/df" <<'STUB'
#!/usr/bin/env bash
echo "Filesystem 1K-blocks Used Available Use% Mounted on"
echo "/dev/vda1  100000000 58000000 42000000 58% /"
STUB

cat > "${STUB_BIN}/free" <<'STUB'
#!/usr/bin/env bash
echo "               total        used        free      shared  buff/cache   available"
echo "Mem:            7976        2100        1200         100        4600        5300"
STUB

# The probe sleeps between the retry and each readiness poll — not in tests.
cat > "${STUB_BIN}/sleep" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB

chmod +x "${STUB_BIN}"/*

# --------------------------------------------------------------------------
# Scenario runner
# --------------------------------------------------------------------------
# run_probe <name> <curl_seq lines...> — state persists per scenario dir so a
# test can run the probe several times in a row (that is the whole point of a
# consecutive-failure policy).
new_scenario() {
  SCENARIO="$1"
  STUB_STATE="${SUITE_TMP}/${SCENARIO}"
  mkdir -p "$STUB_STATE"
  : > "${STUB_STATE}/curl_calls"
  : > "${STUB_STATE}/systemctl_restarts"
  : > "${STUB_STATE}/curl_after_restart"
  echo 1 > "${STUB_STATE}/port_bound"
  echo active > "${STUB_STATE}/unit_state"
  PROBE_LOG="${STUB_STATE}/nox-health.log"
  : > "$PROBE_LOG"
  STATE_DIR="${STUB_STATE}/state"
  mkdir -p "$STATE_DIR"
}

run_probe() {
  printf '%s\n' "$@" > "${STUB_STATE}/curl_seq"
  PATH="${STUB_BIN}:${PATH}" \
  STUB_STATE="$STUB_STATE" \
  NOX_API_PORT=18802 \
  NOX_ENV_FILE="${SUITE_TMP}/nonexistent.env" \
  NOX_HEALTH_LOG="$PROBE_LOG" \
  NOX_STATE_DIR="$STATE_DIR" \
  NOX_DB_PATH="${SUITE_TMP}/fake.db" \
  NOX_GATEWAY_CIRCUIT_FILE="${STUB_STATE}/gateway-circuit" \
  NOX_PROBE_API_BOOT_WAIT=6 \
  DISCORD_WEBHOOK="" \
    bash "$PROBE" > "${STUB_STATE}/stdout" 2>&1
  [[ "$VERBOSE" -eq 1 ]] && { echo "--- ${SCENARIO} log ---"; cat "$PROBE_LOG"; }
  return 0
}

restart_count() { wc -l < "${STUB_STATE}/systemctl_restarts" | tr -d ' '; }
log_has()       { grep -q "$1" "$PROBE_LOG"; }

assert_restarts() {
  local label="$1" want="$2" got
  got="$(restart_count)"
  [ "$got" = "$want" ] && ok "$label" || fail "$label" "expected ${want} restart(s), got ${got}"
}
assert_log() {
  local label="$1" needle="$2"
  log_has "$needle" && ok "$label" || fail "$label" "'${needle}' not in probe log"
}
assert_no_log() {
  local label="$1" needle="$2"
  log_has "$needle" && fail "$label" "unexpected '${needle}' in probe log" || ok "$label"
}

echo "health-probe.sh — nox-mem-api restart policy"

# 1. Healthy API — never touched.
new_scenario healthy
run_probe ok
assert_restarts "healthy: no restart" 0
assert_log      "healthy: logged OK" "OK: nox-mem API port 18802"

# 2. One slow probe that recovers on the in-run retry — no restart.
new_scenario retry_recovers
run_probe timeout ok
assert_restarts "transient: no restart" 0
assert_log      "transient: logged recovery" "recovered on retry"

# 3. First hung probe — counted, not acted on (this is the 4-restarts/h fix).
new_scenario hung_first
run_probe timeout timeout
assert_restarts "hung 1st probe: no restart" 0
assert_log      "hung 1st probe: waits for confirmation" "SKIP RESTART: hung on probe 1/2"

# 4. Second consecutive hung probe — restart, then confirm it came back.
new_scenario hung_second
run_probe timeout timeout
echo "ok" > "${STUB_STATE}/curl_after_restart"
run_probe timeout timeout
assert_restarts "hung 2nd probe: restarted once" 1
assert_log      "hung 2nd probe: reason recorded" "RESTART: nox-mem-api (reason=hung"
assert_log      "hung 2nd probe: readiness confirmed" "RESTART OK: nox-mem-api healthy"
[ -s "${STATE_DIR}/api-restarts.log" ] \
  && ok "hung 2nd probe: ledger written" \
  || fail "hung 2nd probe: ledger written" "api-restarts.log is empty"

# 5. Cooldown — a restart 0s ago blocks the next one.
new_scenario cooldown
echo "$(date +%s) $(date '+%Y-%m-%dT%H:%M:%S%z') hung http=000 rc=28" > "${STATE_DIR}/api-restarts.log"
run_probe timeout timeout
run_probe timeout timeout
assert_restarts "cooldown: no restart within 600s" 0
assert_log      "cooldown: logged" "SKIP RESTART: cooldown"

# 6. Dead process (nothing listening, unit inactive) — restart on the first probe.
new_scenario dead
echo 0 > "${STUB_STATE}/port_bound"
echo inactive > "${STUB_STATE}/unit_state"
echo "ok" > "${STUB_STATE}/curl_after_restart"
run_probe refused refused
assert_restarts "dead: immediate restart" 1
assert_log      "dead: reason recorded" "reason=dead"

# 7. Boot in progress — never restart a unit that is activating.
new_scenario activating
echo 0 > "${STUB_STATE}/port_bound"
echo activating > "${STUB_STATE}/unit_state"
run_probe refused refused
run_probe refused refused
assert_restarts "activating: no restart" 0
assert_log      "activating: logged" "SKIP RESTART: unit is activating"

# 8. Live process answering 5xx — a restart cannot fix it, so alert instead.
new_scenario degraded
run_probe http500 http500
run_probe http500 http500
assert_restarts "degraded: no restart" 0
assert_log      "degraded: logged" "SKIP RESTART: API alive but returning HTTP 500"

# 9. Circuit breaker — 3 restarts inside the hour stops the loop.
new_scenario circuit
NOW=$(date +%s)
{
  echo "$((NOW - 2400)) x hung http=000 rc=28"
  echo "$((NOW - 1800)) x hung http=000 rc=28"
  echo "$((NOW - 1200)) x hung http=000 rc=28"
} > "${STATE_DIR}/api-restarts.log"
run_probe timeout timeout
run_probe timeout timeout
assert_restarts "circuit: no restart above 3/h" 0
assert_log      "circuit: opened" "API CIRCUIT OPENED"
[ -f "${STATE_DIR}/api-circuit-open" ] \
  && ok "circuit: breaker file created" \
  || fail "circuit: breaker file created" "api-circuit-open missing"
run_probe timeout timeout
assert_log      "circuit: stays open" "API CIRCUIT OPEN: not restarting"

# 10. A healthy probe clears the breaker and the consecutive counter.
run_probe ok
[ ! -f "${STATE_DIR}/api-circuit-open" ] \
  && ok "circuit: cleared when healthy" \
  || fail "circuit: cleared when healthy" "api-circuit-open still present"
[ "$(cat "${STATE_DIR}/api-consecutive-fails")" = "0" ] \
  && ok "circuit: fail counter reset" \
  || fail "circuit: fail counter reset" "counter = $(cat "${STATE_DIR}/api-consecutive-fails")"

# 11. Old restarts age out of the rolling hour.
new_scenario ledger_window
NOW=$(date +%s)
{
  echo "$((NOW - 7200)) x hung http=000 rc=28"
  echo "$((NOW - 5400)) x hung http=000 rc=28"
  echo "$((NOW - 4000)) x hung http=000 rc=28"
} > "${STATE_DIR}/api-restarts.log"
echo "ok" > "${STUB_STATE}/curl_after_restart"
run_probe timeout timeout
run_probe timeout timeout
assert_restarts "ledger: >1h old restarts do not count" 1
assert_no_log   "ledger: circuit stayed closed" "API CIRCUIT OPENED"

# 12. The gateway breaker no longer latches on unrelated failures.
new_scenario gateway_circuit
touch "${STUB_STATE}/gateway-circuit"
run_probe ok
[ ! -f "${STUB_STATE}/gateway-circuit" ] \
  && ok "gateway: breaker cleared when gateway healthy" \
  || fail "gateway: breaker cleared when gateway healthy" "circuit file still present"

echo
echo "  ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] || exit 1
