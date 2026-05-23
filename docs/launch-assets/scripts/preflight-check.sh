#!/usr/bin/env bash
# =============================================================================
# preflight-check.sh — validate recording environment before demo day
# =============================================================================
# Run this on Sat 2026-05-30 BEFORE starting asciinema.
# Checks every item in §6 checklist of launch-demo-plan.md
#
# Usage: ./docs/launch-assets/scripts/preflight-check.sh [--local]
# =============================================================================

set -euo pipefail

BASE_URL="http://187.77.234.79:18802"
PASS=0
FAIL=0
WARN=0

for arg in "$@"; do
  case "$arg" in
    --local) BASE_URL="http://localhost:18802" ;;
  esac
done

# ── Helpers ─────────────────────────────────────────────────────────────────

ok()   { printf '\033[0;32m  ✓ %s\033[0m\n' "$*"; (( PASS++ )); }
fail() { printf '\033[1;31m  ✗ %s\033[0m\n' "$*"; (( FAIL++ )); }
note() { printf '\033[1;33m  ⚠ %s\033[0m\n' "$*"; (( WARN++ )); }
hdr()  { printf '\n\033[1;37m%s\033[0m\n' "$*"; }

# ── Checks ───────────────────────────────────────────────────────────────────

hdr "1. Recording tools"

command -v asciinema &>/dev/null \
  && ok "asciinema: $(asciinema --version 2>&1 | head -1)" \
  || fail "asciinema NOT found — install: brew install asciinema"

command -v agg &>/dev/null \
  && ok "agg (asciinema-agg): found" \
  || fail "agg NOT found — install: brew install asciinema-agg"

command -v svg-term &>/dev/null \
  && ok "svg-term: found (SVG fallback available)" \
  || note "svg-term not installed — fallback unavailable if GIF >2MB (npm install -g svg-term-cli)"

command -v gifski &>/dev/null \
  && ok "gifski: found (dashboard GIF available)" \
  || note "gifski not installed — needed for F10 dashboard GIF (brew install gifski)"

command -v ffmpeg &>/dev/null \
  && ok "ffmpeg: found" \
  || note "ffmpeg not installed — needed if converting .mov for dashboard GIF (brew install ffmpeg)"

hdr "2. nox-mem CLI"

if command -v nox-mem &>/dev/null; then
  ok "nox-mem in PATH: $(nox-mem --version 2>&1 | head -1)"
elif [[ -f "dist/index.js" ]]; then
  ok "dist/index.js found (use: node dist/index.js ...)"
else
  fail "nox-mem not available — build first: npm install && npm run build"
fi

hdr "3. VPS / local endpoint ($BASE_URL)"

HEALTH=$(curl -sf --max-time 10 "$BASE_URL/api/health" 2>/dev/null) || {
  fail "Cannot reach $BASE_URL/api/health"
  HEALTH=""
}

if [[ -n "$HEALTH" ]]; then
  TOTAL=$(echo "$HEALTH" | jq -r '.total // .totalChunks // 0')
  COVERAGE=$(echo "$HEALTH" | jq -r '.vectorCoverage.percentage // .vectorCoverage // 0')
  SALIENCE=$(echo "$HEALTH" | jq -r '.salience.mode // "unknown"')

  [[ "$TOTAL" -ge 68000 ]] \
    && ok "chunk count: $TOTAL (≥68000)" \
    || fail "chunk count: $TOTAL (expected ≥68000) — corpus may be wrong DB"

  [[ "$COVERAGE" == "100" ]] || [[ "$COVERAGE" == "100.00" ]] \
    && ok "vector coverage: $COVERAGE%" \
    || note "vector coverage: $COVERAGE% (expected 100)"

  [[ "$SALIENCE" == "active" ]] \
    && ok "salience mode: active" \
    || note "salience mode: $SALIENCE (expected active)"
fi

hdr "4. Answer endpoint (flagship /api/answer)"

ANSWER=$(curl -sf --max-time 20 -X POST "$BASE_URL/api/answer" \
  -H 'Content-Type: application/json' \
  -d '{"query":"what is G10d?"}' 2>/dev/null) || {
  fail "/api/answer request failed"
  ANSWER=""
}

if [[ -n "$ANSWER" ]]; then
  HAS_ANS=$(echo "$ANSWER" | jq -r 'has("answer") or has("response") or has("result")' 2>/dev/null || echo "false")
  [[ "$HAS_ANS" == "true" ]] \
    && ok "/api/answer: returned answer field" \
    || note "/api/answer: response shape unexpected — check jq output"
fi

hdr "5. Search smoke test"

SEARCH=$(curl -sf --max-time 10 "$BASE_URL/api/search?q=conditional+mutex&limit=3" 2>/dev/null) || {
  fail "/api/search request failed"
  SEARCH=""
}

if [[ -n "$SEARCH" ]]; then
  COUNT=$(echo "$SEARCH" | jq -r '.results | length' 2>/dev/null || echo 0)
  [[ "$COUNT" -gt 0 ]] \
    && ok "/api/search: returned $COUNT results" \
    || fail "/api/search: 0 results for 'conditional mutex'"
fi

hdr "6. Terminal size"

COLS=$(tput cols 2>/dev/null || echo 0)
ROWS=$(tput lines 2>/dev/null || echo 0)

[[ "$COLS" -ge 120 ]] \
  && ok "terminal width: $COLS cols (≥120)" \
  || note "terminal width: $COLS cols — resize to ≥120 before recording (stty cols 120)"

[[ "$ROWS" -ge 30 ]] \
  && ok "terminal height: $ROWS rows (≥30)" \
  || note "terminal height: $ROWS rows — resize to ≥30 before recording (stty rows 30)"

# ── Summary ──────────────────────────────────────────────────────────────────

printf '\n\033[1;37m══ Preflight summary ══\033[0m\n'
printf '\033[0;32m  PASS: %d\033[0m\n' "$PASS"
printf '\033[1;33m  WARN: %d\033[0m\n' "$WARN"
printf '\033[1;31m  FAIL: %d\033[0m\n' "$FAIL"

if [[ "$FAIL" -gt 0 ]]; then
  printf '\n\033[1;31mFix FAIL items before recording.\033[0m\n'
  exit 1
elif [[ "$WARN" -gt 0 ]]; then
  printf '\n\033[1;33mAll FAIL checks pass. Review WARN items — they are optional but recommended.\033[0m\n'
  exit 0
else
  printf '\n\033[0;32mAll checks passed. You are ready to record.\033[0m\n'
  printf '\033[0;36m  Run: ./docs/launch-assets/scripts/demo-record.sh\033[0m\n'
  exit 0
fi
