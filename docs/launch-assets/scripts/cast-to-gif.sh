#!/usr/bin/env bash
# =============================================================================
# cast-to-gif.sh — asciinema .cast → GIF pipeline
# =============================================================================
# Usage:
#   ./docs/launch-assets/scripts/cast-to-gif.sh <input.cast> [output.gif]
#
# If output is omitted, writes to docs/launch-assets/gif/<basename>.gif
#
# Pipeline:
#   1. agg (primary) — asciinema-agg, dracula theme, font-size 14, 120×30
#   2. svg-term (fallback) — if agg not available or GIF >2MB
#
# Size targets (per launch-demo-plan.md §4):
#   demo-cli.gif: < 2MB (fps-cap 20, fallback fps-cap 15)
#   Any GIF >2MB: auto-retry with --fps-cap 15
#   If still >2MB: generate SVG fallback via svg-term
#
# Prerequisites:
#   brew install asciinema-agg        # primary
#   npm install -g svg-term-cli       # fallback
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
GIF_DIR="$REPO_ROOT/docs/launch-assets/gif"

# ── Config ──────────────────────────────────────────────────────────────────

THEME="dracula"
FONT_SIZE=14
COLS=120
ROWS=30
FPS_CAP_PRIMARY=20
FPS_CAP_FALLBACK=15
MAX_GIF_MB=2

# ── Helpers ─────────────────────────────────────────────────────────────────

log()  { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*"; }
err()  { printf '\033[1;31m✖ %s\033[0m\n' "$*" >&2; exit 1; }

file_mb() {
  local f="$1"
  local bytes
  bytes=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
  echo "scale=2; $bytes / 1048576" | bc
}

mb_exceeds() {
  local f="$1"
  local limit="$2"
  local mb
  mb=$(file_mb "$f")
  (( $(echo "$mb > $limit" | bc -l) ))
}

# ── Dependency check ─────────────────────────────────────────────────────────

HAS_AGG=false
HAS_SVGTERM=false

command -v agg      &>/dev/null && HAS_AGG=true
command -v svg-term &>/dev/null && HAS_SVGTERM=true

if ! $HAS_AGG && ! $HAS_SVGTERM; then
  err "Neither 'agg' nor 'svg-term' found. Install: brew install asciinema-agg (or npm install -g svg-term-cli)"
fi

# ── Args ────────────────────────────────────────────────────────────────────

INPUT="${1:-}"
if [[ -z "$INPUT" ]]; then
  err "Usage: $0 <input.cast> [output.gif]"
fi

[[ -f "$INPUT" ]] || err "Cast file not found: $INPUT"

BASENAME=$(basename "$INPUT" .cast)

if [[ -n "${2:-}" ]]; then
  OUTPUT_GIF="$2"
else
  mkdir -p "$GIF_DIR"
  OUTPUT_GIF="$GIF_DIR/${BASENAME}.gif"
fi

OUTPUT_SVG="${OUTPUT_GIF%.gif}.svg"

# ── agg pipeline ─────────────────────────────────────────────────────────────

agg_convert() {
  local fps="$1"
  log "agg: converting '$INPUT' → '$OUTPUT_GIF' (fps-cap $fps, theme $THEME) ..."
  agg "$INPUT" "$OUTPUT_GIF" \
    --theme "$THEME" \
    --font-size "$FONT_SIZE" \
    --cols "$COLS" \
    --rows "$ROWS" \
    --fps-cap "$fps"
}

# ── svg-term fallback ────────────────────────────────────────────────────────

svgterm_convert() {
  log "svg-term: converting '$INPUT' → '$OUTPUT_SVG' ..."
  cat "$INPUT" | svg-term --out "$OUTPUT_SVG" \
    --window \
    --width "$COLS" \
    --height "$ROWS"
  local mb
  mb=$(file_mb "$OUTPUT_SVG")
  log "SVG fallback created: $OUTPUT_SVG (${mb}MB)"
  warn "Verify rendering on github.com before committing SVG — not all Markdown renderers animate SVG"
}

# ── Size report ─────────────────────────────────────────────────────────────

report() {
  local f="$1"
  local mb
  mb=$(file_mb "$f")
  if (( $(echo "$mb <= $MAX_GIF_MB" | bc -l) )); then
    printf '\033[0;32m  ✓ %s (%.2fMB) — within %sMB limit\033[0m\n' "$f" "$mb" "$MAX_GIF_MB"
  else
    printf '\033[1;31m  ✗ %s (%.2fMB) — EXCEEDS %sMB limit\033[0m\n' "$f" "$mb" "$MAX_GIF_MB"
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  log "Input: $INPUT"

  if $HAS_AGG; then
    # Try primary fps-cap
    agg_convert "$FPS_CAP_PRIMARY"

    if [[ -f "$OUTPUT_GIF" ]] && mb_exceeds "$OUTPUT_GIF" "$MAX_GIF_MB"; then
      warn "GIF exceeds ${MAX_GIF_MB}MB — retrying with fps-cap $FPS_CAP_FALLBACK ..."
      agg_convert "$FPS_CAP_FALLBACK"
    fi

    if [[ -f "$OUTPUT_GIF" ]]; then
      report "$OUTPUT_GIF"

      # If still over limit, offer SVG fallback
      if mb_exceeds "$OUTPUT_GIF" "$MAX_GIF_MB" && $HAS_SVGTERM; then
        warn "GIF still exceeds ${MAX_GIF_MB}MB — generating SVG fallback ..."
        svgterm_convert
      elif mb_exceeds "$OUTPUT_GIF" "$MAX_GIF_MB"; then
        warn "GIF exceeds ${MAX_GIF_MB}MB. Install svg-term-cli for a smaller fallback:"
        warn "  npm install -g svg-term-cli"
        warn "  Then re-run this script."
      fi
    fi
  elif $HAS_SVGTERM; then
    warn "agg not available — using svg-term (SVG output only)"
    svgterm_convert
  fi

  # Final instructions
  printf '\n\033[0;36mNext steps:\033[0m\n'
  printf '  1. Inspect output in browser/VS Code preview\n'
  printf '  2. Test GitHub rendering: push to a branch and check github.com preview\n'
  printf '  3. README embed target: docs/assets/demo-cli.gif\n'
  printf '     Run: cp "%s" "%s/docs/assets/demo-cli.gif"\n' "$OUTPUT_GIF" "$REPO_ROOT"
}

main "$@"
