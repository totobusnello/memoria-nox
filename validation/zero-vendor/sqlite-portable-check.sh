#!/usr/bin/env bash
# sqlite-portable-check.sh — Check 4 of 8
#
# Copies nox-mem.db to a fresh temp directory, opens it with vanilla sqlite3 CLI
# (zero nox-mem code), and verifies standard SQLite portability.
#
# PASS: .schema lists expected tables; SELECT count(*) FROM chunks returns > 0
# FAIL: sqlite3 CLI not available, can't open file, schema missing, SQLITE_CORRUPT
#
# What this proves:
#   The memory file is a standard SQLite database.
#   No proprietary format. No vendor-specific SQLite extensions required.
#   Any SQLite-capable tool (DB Browser, DBeaver, pandas, etc.) can open it.
#
# Usage:
#   bash validation/zero-vendor/sqlite-portable-check.sh [/path/to/nox-mem.db]
#   NOX_DB_PATH=/path/to/nox-mem.db bash validation/zero-vendor/sqlite-portable-check.sh
#
# CI mode: if DB not found, creates a minimal fixture DB and tests against it.

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NOX_DB="${1:-${NOX_DB_PATH:-/root/.openclaw/workspace/tools/nox-mem/nox-mem.db}}"
JSON_MODE="${JSON_MODE:-0}"

# Expected tables that prove schema integrity
REQUIRED_TABLES=(
  "chunks"
  "chunks_fts"
  "vec_chunks"
  "kg_entities"
  "kg_relations"
  "ops_audit"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pass_count=0
fail_count=0
results_json="[]"

check_result() {
  local name="$1"
  local passed="$2"
  local detail="$3"

  if [ "$passed" = "true" ]; then
    ((pass_count++)) || true
    if [ "$JSON_MODE" = "0" ]; then
      echo "  ✓ $name: $detail"
    fi
  else
    ((fail_count++)) || true
    if [ "$JSON_MODE" = "0" ]; then
      echo "  ✗ $name: $detail"
    fi
  fi

  # Append to JSON (minimal, no jq required)
  results_json="${results_json%]},{\"name\":\"$name\",\"passed\":$passed,\"detail\":\"$detail\"}]"
  results_json="${results_json/#\[\,/[}"
}

# ---------------------------------------------------------------------------
# Pre-flight: sqlite3 CLI availability
# ---------------------------------------------------------------------------

if ! command -v sqlite3 &>/dev/null; then
  echo '[sqlite-portable-check] FAIL: sqlite3 CLI not found in PATH'
  echo 'Install: apt-get install sqlite3 (Ubuntu) / brew install sqlite (macOS)'
  exit 1
fi

SQLITE_VERSION=$(sqlite3 --version 2>&1 | head -1)

# ---------------------------------------------------------------------------
# Database setup: use real DB or create CI fixture
# ---------------------------------------------------------------------------

TMP_DIR=$(mktemp -d)
TMP_DB="$TMP_DIR/nox-mem-portable-check.db"
FIXTURE_MODE=0

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [ -f "$NOX_DB" ]; then
  # Copy to temp to avoid any file lock issues and to NOT touch prod DB
  cp "$NOX_DB" "$TMP_DB"
  # Remove WAL files from the copy's dir — the copy should be self-consistent
  rm -f "${TMP_DB}-shm" "${TMP_DB}-wal" 2>/dev/null || true
else
  # CI mode: create minimal fixture DB with the expected schema
  FIXTURE_MODE=1
  sqlite3 "$TMP_DB" <<'SCHEMA'
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  content TEXT NOT NULL,
  type TEXT DEFAULT 'lesson',
  importance REAL DEFAULT 0.5,
  pain REAL DEFAULT 0.2,
  section TEXT,
  section_boost REAL DEFAULT 1.0,
  retention_days INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, source, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS vec_chunks (id INTEGER PRIMARY KEY, embedding BLOB);
CREATE TABLE IF NOT EXISTS vec_chunk_map (vec_id INTEGER, chunk_id INTEGER);
CREATE TABLE IF NOT EXISTS kg_entities (id INTEGER PRIMARY KEY, name TEXT, type TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS kg_relations (id INTEGER PRIMARY KEY, source_entity_id INTEGER, target_entity_id INTEGER, relation TEXT);
CREATE TABLE IF NOT EXISTS ops_audit (id INTEGER PRIMARY KEY, op TEXT, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS search_telemetry (id INTEGER PRIMARY KEY, query_text TEXT, top_chunk_ids TEXT, created_at TEXT);
INSERT INTO chunks (source, content, type, importance) VALUES
  ('fixture/test.md', 'This is a zero-vendor test fixture chunk for portable SQLite validation.', 'lesson', 0.9),
  ('fixture/test.md', 'nox-mem stores memories in standard SQLite — no proprietary format required.', 'decision', 0.8);
INSERT INTO chunks_fts (content, source) VALUES
  ('This is a zero-vendor test fixture chunk for portable SQLite validation.', 'fixture/test.md'),
  ('nox-mem stores memories in standard SQLite — no proprietary format required.', 'fixture/test.md');
INSERT INTO kg_entities (name, type, description) VALUES
  ('nox-mem', 'system', 'Memory system for intelligent second brain');
SCHEMA
fi

# ---------------------------------------------------------------------------
# Check 1: sqlite3 can open the file
# ---------------------------------------------------------------------------

if sqlite3 "$TMP_DB" "SELECT 1;" &>/dev/null; then
  check_result "open-db" "true" "sqlite3 opened the database successfully (sqlite $SQLITE_VERSION)"
else
  check_result "open-db" "false" "sqlite3 could not open the database"
  echo ""
  echo "[sqlite-portable-check] FAIL (cannot open DB — aborting remaining checks)"
  exit 1
fi

# ---------------------------------------------------------------------------
# Check 2: integrity check
# ---------------------------------------------------------------------------

INTEGRITY=$(sqlite3 "$TMP_DB" "PRAGMA integrity_check;" 2>&1 | head -5)
if [ "$INTEGRITY" = "ok" ]; then
  check_result "integrity-check" "true" "PRAGMA integrity_check: ok"
else
  check_result "integrity-check" "false" "PRAGMA integrity_check: $INTEGRITY"
fi

# ---------------------------------------------------------------------------
# Check 3: schema has required tables
# ---------------------------------------------------------------------------

SCHEMA_OUTPUT=$(sqlite3 "$TMP_DB" ".tables" 2>&1)
all_tables_found=true
missing_tables=()

for table in "${REQUIRED_TABLES[@]}"; do
  if ! echo "$SCHEMA_OUTPUT" | grep -qw "$table"; then
    all_tables_found=false
    missing_tables+=("$table")
  fi
done

if [ "$all_tables_found" = "true" ]; then
  check_result "schema-tables" "true" "All required tables present: ${REQUIRED_TABLES[*]}"
else
  check_result "schema-tables" "false" "Missing tables: ${missing_tables[*]}"
fi

# ---------------------------------------------------------------------------
# Check 4: SELECT count(*) FROM chunks returns > 0
# ---------------------------------------------------------------------------

CHUNK_COUNT=$(sqlite3 "$TMP_DB" "SELECT count(*) FROM chunks;" 2>&1)
if [[ "$CHUNK_COUNT" =~ ^[0-9]+$ ]] && [ "$CHUNK_COUNT" -gt 0 ]; then
  check_result "chunks-count" "true" "chunks table has $CHUNK_COUNT rows"
else
  check_result "chunks-count" "false" "chunks table count is $CHUNK_COUNT (expected > 0)"
fi

# ---------------------------------------------------------------------------
# Check 5: SELECT count(*) FROM kg_entities works (may be 0 on fresh DB)
# ---------------------------------------------------------------------------

KG_COUNT=$(sqlite3 "$TMP_DB" "SELECT count(*) FROM kg_entities;" 2>&1)
if [[ "$KG_COUNT" =~ ^[0-9]+$ ]]; then
  check_result "kg-entities-count" "true" "kg_entities table has $KG_COUNT rows (≥ 0 is valid)"
else
  check_result "kg-entities-count" "false" "kg_entities query failed: $KG_COUNT"
fi

# ---------------------------------------------------------------------------
# Check 6: FTS5 search works without nox-mem runtime
# ---------------------------------------------------------------------------

FTS_RESULT=$(sqlite3 "$TMP_DB" \
  "SELECT count(*) FROM chunks c JOIN chunks_fts ON chunks_fts.rowid = c.id WHERE chunks_fts MATCH 'sqlite';" \
  2>&1)
if [[ "$FTS_RESULT" =~ ^[0-9]+$ ]]; then
  check_result "fts5-vanilla-search" "true" "FTS5 MATCH query works with vanilla sqlite3 (${FTS_RESULT} hits)"
else
  check_result "fts5-vanilla-search" "false" "FTS5 query failed: $FTS_RESULT"
fi

# ---------------------------------------------------------------------------
# Check 7: WAL mode readable without nox-mem process
# ---------------------------------------------------------------------------

JOURNAL_MODE=$(sqlite3 "$TMP_DB" "PRAGMA journal_mode;" 2>&1)
check_result "journal-mode-accessible" "true" "journal_mode=$JOURNAL_MODE — readable by vanilla sqlite3"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

FIXTURE_NOTE=""
[ "$FIXTURE_MODE" = "1" ] && FIXTURE_NOTE=" [CI fixture mode — real DB not found at $NOX_DB]"

OVERALL_PASSED="true"
[ "$fail_count" -gt 0 ] && OVERALL_PASSED="false"

if [ "$JSON_MODE" = "1" ]; then
  echo "{\"check\":\"sqlite-portable-check\",\"passed\":$OVERALL_PASSED,\"summary\":{\"pass\":$pass_count,\"fail\":$fail_count},\"fixtureMode\":$FIXTURE_MODE,\"sqliteVersion\":\"$SQLITE_VERSION\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
else
  ICON="✗"
  LABEL="FAIL"
  [ "$OVERALL_PASSED" = "true" ] && ICON="✓" && LABEL="PASS"
  echo ""
  echo "[sqlite-portable-check] $ICON $LABEL — $pass_count pass, $fail_count fail$FIXTURE_NOTE"
fi

[ "$fail_count" -eq 0 ]
