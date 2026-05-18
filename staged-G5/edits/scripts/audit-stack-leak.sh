#!/usr/bin/env bash
#
# G5 — audit:stack-leak
#
# Greps for patterns that historically leak stack traces / internal paths /
# raw error messages into HTTP responses. Non-zero exit when matches found.
#
# Usage:
#   scripts/audit-stack-leak.sh [path]
#
# Default path: repository root (cwd).
#
# Patterns scanned:
#   1) JSON.stringify(err)               — Error JSON quirks leak stack on some node versions
#   2) err.stack    in api/* / handler files
#   3) (err as Error).message in 500 / jsonResponse / errorBody path
#   4) `error: msg` where msg = raw err.message (heuristic; manual review needed)
#
# Excludes:
#   - dist/ build output
#   - node_modules/
#   - **/__tests__/**
#   - **/*.md docs
#   - the sanitizer module itself

set -uo pipefail

ROOT="${1:-.}"
EXIT_CODE=0
LEAK_COUNT=0

cyan()  { printf '\033[36m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }

cyan "[audit] scanning ${ROOT} for stack-leak patterns…"

# Collect source files (POSIX-portable, no mapfile dep).
TMP_LIST="$(mktemp)"
find "${ROOT}" \
  \( -path '*/dist' -o -path '*/node_modules' -o -path '*/__tests__' \) -prune -o \
  -type f \( -name '*.ts' -o -name '*.js' -o -name '*.mjs' \) -not -path '*/error-sanitizer/*' -print \
  > "${TMP_LIST}"

scan_pattern() {
  pattern="$1"
  label="$2"
  while IFS= read -r f; do
    [ -z "${f}" ] && continue
    if grep -nE "${pattern}" "${f}" >/dev/null 2>&1; then
      grep -nE "${pattern}" "${f}" | while IFS= read -r line; do
        red "[audit] LEAK  ${f}: ${line}   (${label})"
      done
      LEAK_COUNT=$((LEAK_COUNT + 1))
      EXIT_CODE=1
    fi
  done < "${TMP_LIST}"
}

scan_pattern 'JSON\.stringify\(\s*err' \
  "JSON.stringify(err) — Error serialization may include enumerable stack on some Node versions"

scan_pattern '\berr\.stack\b' \
  "err.stack referenced in src — verify it doesn't reach a response body"

scan_pattern 'res\.(json|send|write)\([^)]*err\.message' \
  "res.*(err.message) — raw err.message in response body"

scan_pattern 'message:\s*\(err as Error\)\.message' \
  "message: (err as Error).message — raw message echoed"

scan_pattern 'error:\s*\(err as Error\)\.message' \
  "error: (err as Error).message — raw message echoed"

scan_pattern 'jsonResponse\(\s*5\d\d\s*,\s*\{[^}]*err\.message' \
  "jsonResponse(5xx, { ...err.message }) — server-error raw message echoed"

rm -f "${TMP_LIST}"

if [ "${EXIT_CODE}" -eq 0 ]; then
  green "[audit] PASS — no obvious stack-leak patterns found"
else
  red "[audit] FAIL — ${LEAK_COUNT} leak source(s) detected"
  yellow "      see staged-G5/edits/docs/ERROR-SANITIZER.md for the migration pattern"
  yellow "      replace catch-blocks with: return errorToResponse(err, { requestId });"
fi

exit "${EXIT_CODE}"
