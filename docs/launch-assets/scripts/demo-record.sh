#!/usr/bin/env bash
# =============================================================================
# demo-record.sh — nox-mem launch demo recording script
# =============================================================================
# Usage:
#   ./docs/launch-assets/scripts/demo-record.sh [--dry-run] [--local]
#
# Modes:
#   (default) Uses VPS at http://187.77.234.79:18802 (public demo, read-only)
#   --local   Uses http://localhost:18802 (requires local nox-mem running)
#   --dry-run Echo commands without executing them (sanity check)
#
# Prerequisites (install first — see docs/launch-assets/README.md):
#   brew install asciinema
#   brew install asciinema-agg
#
# Output:
#   docs/launch-assets/cast/demo-v<N>.cast  (auto-increments)
#
# =============================================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CAST_DIR="$REPO_ROOT/docs/launch-assets/cast"
BASE_URL="http://187.77.234.79:18802"
DRY_RUN=false
LOCAL=false

# ── Arg parse ───────────────────────────────────────────────────────────────

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --local)   LOCAL=true; BASE_URL="http://localhost:18802" ;;
    --help|-h)
      sed -n '2,25p' "$0" | sed 's/^# //'
      exit 0
      ;;
  esac
done

# ── Helpers ─────────────────────────────────────────────────────────────────

log()  { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*"; }
err()  { printf '\033[1;31m✖ %s\033[0m\n' "$*" >&2; exit 1; }

run() {
  if $DRY_RUN; then
    printf '\033[0;90m[dry-run] %s\033[0m\n' "$*"
  else
    eval "$*"
  fi
}

# ── Dependency check ─────────────────────────────────────────────────────────

check_deps() {
  local missing=()
  command -v asciinema &>/dev/null || missing+=("asciinema")
  command -v curl       &>/dev/null || missing+=("curl")
  command -v jq         &>/dev/null || missing+=("jq")

  if [[ ${#missing[@]} -gt 0 ]]; then
    err "Missing dependencies: ${missing[*]}. See docs/launch-assets/README.md"
  fi

  # nox-mem CLI (only required for local or if available in PATH)
  if ! command -v nox-mem &>/dev/null; then
    warn "nox-mem not in PATH — CLI steps will use 'node dist/index.js'"
    NOX_CMD="node dist/index.js"
  else
    NOX_CMD="nox-mem"
  fi
}

# ── Pre-flight health check ──────────────────────────────────────────────────

preflight() {
  log "Pre-flight: checking $BASE_URL/api/health ..."
  local health
  health=$(curl -sf "$BASE_URL/api/health" 2>/dev/null) || {
    err "Cannot reach $BASE_URL/api/health. Is nox-mem running?"
  }

  local total coverage salience
  total=$(echo "$health" | jq -r '.total // .totalChunks // "?"')
  coverage=$(echo "$health" | jq -r 'if .vectorCoverage | type == "object" then (.vectorCoverage.percentage // "100") else (.vectorCoverage // "?") end')
  salience=$(echo "$health" | jq -r '.salience.mode // "?"')

  printf '\033[0;32m  ✓ chunks: %s | vec: %s%% | salience: %s\033[0m\n' \
    "$total" "$coverage" "$salience"

  if [[ "$total" != "?" ]] && (( total < 1000 )); then
    warn "Chunk count looks low ($total). Double-check this is the right corpus."
  fi
}

# ── Next cast filename (auto-increment) ─────────────────────────────────────

next_cast_path() {
  local n=1
  while [[ -f "$CAST_DIR/demo-v${n}.cast" ]]; do
    (( n++ ))
  done
  echo "$CAST_DIR/demo-v${n}.cast"
}

# ── The actual demo script (runs inside asciinema) ──────────────────────────
# This function is EXPORTED and called by asciinema via --command

demo_script() {
  # Minimal prompt — looks clean in the recording
  export PS1='nox $ '
  clear

  # ── Intro title card (§5 of narration plan)
  printf '\033[1;36m  nox-mem · pain-weighted hybrid memory · open source\033[0m\n'
  sleep 1.5
  clear

  # ── Step 1: CLI overview (~3s)
  # Shows 26+ subcommands — signals CLI maturity
  log_step 1 "CLI overview"
  sleep 0.5
  $NOX_CMD --help
  sleep 2

  # ── Step 2: Hybrid search (~5s)
  # BM25 + Gemini semantic + RRF, pain-weighted
  log_step 2 "Hybrid search — G10 conditional mutex"
  sleep 0.5
  $NOX_CMD search "G10 conditional mutex"
  sleep 2

  # ── Step 3: Health endpoint (~5s)
  # 69k chunks, 100% vec coverage, salience active
  log_step 3 "API health — corpus state"
  sleep 0.5
  curl -s "$BASE_URL/api/health" | jq '.'
  sleep 2

  # ── Step 4: Answer endpoint (~10s) — flagship P1 feature
  log_step 4 "Flagship — /api/answer with citations"
  sleep 0.5
  curl -s -X POST "$BASE_URL/api/answer" \
    -H 'Content-Type: application/json' \
    -d '{"query":"what is G10d conditional mutex?"}' | jq '.'
  sleep 3

  # ── Step 5: Stats — KG numbers (~5s)
  log_step 5 "Knowledge graph stats"
  sleep 0.5
  $NOX_CMD stats --json | jq '{chunks, entities, relations, coverage}'
  sleep 2

  # ── Outro title card (§5 of narration plan)
  printf '\n\033[1;37m  github.com/totobusnello/memoria-nox · MIT\033[0m\n'
  sleep 2
}

log_step() {
  local n="$1"; shift
  printf '\n\033[0;90m── Step %s: %s ──\033[0m\n' "$n" "$*"
}

export -f demo_script log_step
export NOX_CMD BASE_URL

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  check_deps
  preflight

  local cast_path
  cast_path=$(next_cast_path)
  mkdir -p "$(dirname "$cast_path")"

  log "Recording → $cast_path"
  log "Terminal should be 120×30. Font: JetBrains Mono 14pt (or similar monospace)."
  printf '\033[0;33m  Press ENTER to start recording, Ctrl+D to stop.\033[0m\n'
  read -r

  if $DRY_RUN; then
    warn "DRY RUN — would execute: asciinema rec \"$cast_path\" --idle-time-limit 1 --title 'nox-mem demo' --command 'bash -c demo_script'"
    warn "DRY RUN — commands inside demo:"
    demo_script 2>/dev/null || true
    exit 0
  fi

  asciinema rec "$cast_path" \
    --idle-time-limit 1 \
    --title "nox-mem — pain-weighted hybrid memory" \
    --command "bash -c 'source \"$SCRIPT_DIR/demo-record.sh\" && demo_script'"

  local size
  size=$(du -sh "$cast_path" 2>/dev/null | cut -f1)
  log "Cast saved: $cast_path ($size)"
  printf '\033[0;32m  Next: run ./docs/launch-assets/scripts/cast-to-gif.sh \"%s\"\033[0m\n' "$cast_path"
}

main "$@"
