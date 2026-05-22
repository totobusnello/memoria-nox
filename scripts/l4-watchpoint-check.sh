#!/usr/bin/env bash
# L4 watchpoint check — run Mon 2026-05-25 morning BRT after Sun cron fire
# Validates that PR #214 plural-normalisation cron fired and populated
# kg_relations.extraction_method (was 100% NULL pre-cron per audit below).
#
# Cross-ref: audits/2026-05-21-l4-extraction-method-null-finding.md, PR #214
# Expected cron window: Sun 2026-05-24 23:00 UTC = 20:00 BRT
#
# Usage:
#   ./scripts/l4-watchpoint-check.sh
#   NOX_DB_PATH=/path/to/nox-mem.db ./scripts/l4-watchpoint-check.sh
#   L4_NON_NULL_THRESHOLD=10 ./scripts/l4-watchpoint-check.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH="${NOX_DB_PATH:-/root/.openclaw/workspace/tools/nox-mem/nox-mem.db}"
THRESHOLD="${L4_NON_NULL_THRESHOLD:-1}"  # minimum non-NULL rows to PASS

# ---------------------------------------------------------------------------
# Preflight: check dependencies
# ---------------------------------------------------------------------------
if ! command -v sqlite3 &>/dev/null; then
  echo "ERROR: sqlite3 binary not found in PATH" >&2
  echo "  Install: apt-get install sqlite3  (Debian/Ubuntu)" >&2
  echo "  Or:      brew install sqlite3     (macOS)" >&2
  exit 2
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "ERROR: DB not found at: $DB_PATH" >&2
  echo "  Set NOX_DB_PATH env var to the correct path." >&2
  exit 2
fi

if [[ ! -r "$DB_PATH" ]]; then
  echo "ERROR: DB not readable: $DB_PATH" >&2
  echo "  Check file permissions (expected 0600, owner root)." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Query: extraction_method distribution in kg_relations
# ---------------------------------------------------------------------------
DIST_SQL="
SELECT
  COALESCE(extraction_method, 'NULL') AS extraction_method,
  COUNT(*)                             AS count
FROM kg_relations
GROUP BY extraction_method
ORDER BY count DESC;
"

TOTAL_SQL="SELECT COUNT(*) FROM kg_relations;"
NON_NULL_SQL="SELECT COUNT(*) FROM kg_relations WHERE extraction_method IS NOT NULL;"

echo "================================================================"
echo "  L4 watchpoint check — kg_relations.extraction_method"
echo "  DB: $DB_PATH"
echo "  Date: $(date '+%Y-%m-%d %H:%M %Z')"
echo "================================================================"
echo ""

TOTAL=$(sqlite3 "$DB_PATH" "$TOTAL_SQL" 2>/dev/null)
NON_NULL=$(sqlite3 "$DB_PATH" "$NON_NULL_SQL" 2>/dev/null)

echo "  Total relations:    $TOTAL"
echo "  Non-NULL method:    $NON_NULL"
echo "  NULL threshold req: >= $THRESHOLD non-NULL to PASS"
echo ""
echo "  Distribution:"
echo "  -------------------------"

# Pretty-print via column -t (align columns)
sqlite3 -separator $'\t' "$DB_PATH" "$DIST_SQL" 2>/dev/null \
  | awk -F'\t' 'BEGIN{print "  extraction_method\tcount"} {print "  "$0}' \
  | column -t -s $'\t'

echo ""

# ---------------------------------------------------------------------------
# Evaluate result
# ---------------------------------------------------------------------------
if [[ "$NON_NULL" -ge "$THRESHOLD" ]]; then
  echo "RESULT: PASS"
  echo "  L4 cron fired correctly — $NON_NULL relations have extraction_method set."
  echo "  Pre-cron baseline was 0 non-NULL (audit 2026-05-21). Delta confirms PR #214 active."
  exit 0
else
  echo "RESULT: ALERT"
  echo "  extraction_method still all-NULL ($NON_NULL non-NULL, need >= $THRESHOLD)."
  echo ""
  echo "  Possible causes:"
  echo "    1. Cron did not fire — check Sun 2026-05-24 23:00 UTC window"
  echo "    2. nightly-maintenance.service failed silently"
  echo "    3. NOX_ENTITY_DIRS_PLURAL not set in env (PR #214 dep)"
  echo "    4. DB path mismatch — script hit wrong DB"
  echo ""
  echo "  Debug commands (run on VPS):"
  echo "    journalctl -u nightly-maintenance.service --since '2026-05-24 22:50' --until '2026-05-25 01:00' -n 200"
  echo "    systemctl status nightly-maintenance.service"
  echo "    grep extraction_method /root/.openclaw/workspace/tools/nox-mem/dist/lib/*.js | head -5"
  echo "    sqlite3 $DB_PATH 'SELECT extraction_method, COUNT(*) FROM kg_relations GROUP BY 1;'"
  echo "    cat /root/.openclaw/.env | grep -E 'NOX_ENTITY|NOX_DB|OPENCLAW_WORKSPACE'"
  exit 1
fi
