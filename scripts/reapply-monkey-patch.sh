#!/usr/bin/env bash
# Reapplies Issue #62028 fratricide fix to restart-stale-pids-*.js
# Idempotent — safe to run multiple times.
#
# IMPORTANT (since v2026.4.27): bundle ships restart-stale-pids in 2 files —
# one impl (~500 lines) + one re-export wrapper (2 lines). `ls | head -1` would
# pick the wrapper alphabetically (BxD39Nsb < DNoLLjzi in v.29), so we filter
# via grep to only target the file containing the actual function definition.
set -euo pipefail

DIST_DIR="${DIST_DIR:-/usr/lib/node_modules/openclaw/dist}"

# Select impl file (contains function body, not the re-export wrapper)
PATCH_FILE=$(grep -l "function cleanStaleGatewayProcessesSync(portOverride) {" \
             "$DIST_DIR"/restart-stale-pids-*.js 2>/dev/null | head -1)

if [[ -z "$PATCH_FILE" ]]; then
  # Fallback: any file matching just the symbol name (in case v.30+ changes)
  PATCH_FILE=$(grep -l "cleanStaleGatewayProcessesSync" \
               "$DIST_DIR"/restart-stale-pids-*.js 2>/dev/null | \
               xargs -I{} sh -c 'wc -l < {} | { read n; [[ $n -gt 50 ]] && echo {}; }' 2>/dev/null | head -1)
fi

[[ -n "$PATCH_FILE" ]] || { echo "ERROR: no impl file with cleanStaleGatewayProcessesSync found in $DIST_DIR" >&2; exit 1; }

if grep -q "MONKEY-PATCH" "$PATCH_FILE"; then
  echo "already patched: $PATCH_FILE"
  exit 0
fi

python3 - "$PATCH_FILE" <<'PY'
import re, sys
p = sys.argv[1]
src = open(p).read()
pattern = r'(function cleanStaleGatewayProcessesSync\(portOverride\) \{\n\ttry \{\n)(\t\tconst port)'
if not re.search(pattern, src):
    print("ERROR: expected pattern not found — bundle layout changed, patch manually", file=sys.stderr)
    sys.exit(2)
replacement = r'\1\t\t// MONKEY-PATCH: Issue #62028 fratricide fix (reapplied on upgrade)\n\t\treturn [];\n\2'
patched = re.sub(pattern, replacement, src, count=1)
open(p, 'w').write(patched)
print(f"patched: {p}")
PY

# Verify marker is present
if ! grep -q "MONKEY-PATCH" "$PATCH_FILE"; then
  echo "ERROR: patch did not take" >&2
  exit 3
fi
echo "verified: $(grep -c 'MONKEY-PATCH' "$PATCH_FILE") marker(s) present in $(basename "$PATCH_FILE")"
