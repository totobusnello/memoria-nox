#!/usr/bin/env bash
# A2 Tier 3 — P0 SQLCipher compat spike
# Time-boxed: 4h
# Goal: determine if SQLCipher + sqlite-vec + better-sqlite3 stack is viable
# Verdict: GO (proceed P1) / NO-GO (pivot LUKS-only D-A2T3-1 fallback)
#
# Usage:
#   ./spike-runner.sh           # full spike
#   ./spike-runner.sh --quick   # skip sqlite-vec compile (Tier-1 vanilla only)
#   ./spike-runner.sh --clean   # wipe work/ and exit
#
# Outputs: work/*.log, work/*.db, RESULTS.md
# Exit codes: 0=GO, 1=NO-GO, 2=PARTIAL (LUKS-only viable but SQLCipher path failed)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work"
LOG="${WORK_DIR}/spike-runner.log"
QUICK=false
CLEAN=false

for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=true ;;
    --clean) CLEAN=true ;;
    -h|--help)
      grep '^#' "${BASH_SOURCE[0]}" | head -20
      exit 0
      ;;
  esac
done

if $CLEAN; then
  echo "Cleaning ${WORK_DIR}/"
  rm -rf "${WORK_DIR}"
  mkdir -p "${WORK_DIR}"
  echo "Done."
  exit 0
fi

mkdir -p "${WORK_DIR}"
echo "=== A2 Tier 3 SQLCipher spike — $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "${LOG}"

# ============================================================
# Phase 0 — environment probe
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 0 — Environment probe" | tee -a "${LOG}"

phase0_pass=true

if ! command -v sqlcipher >/dev/null 2>&1; then
  echo "FAIL: sqlcipher not installed. Run: brew install sqlcipher (macOS) or apt install sqlcipher (Linux)" | tee -a "${LOG}"
  phase0_pass=false
else
  ver=$(sqlcipher --version 2>&1)
  echo "PASS: sqlcipher present — ${ver}" | tee -a "${LOG}"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "FAIL: node not present" | tee -a "${LOG}"
  phase0_pass=false
else
  echo "PASS: node $(node --version)" | tee -a "${LOG}"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "FAIL: npm not present" | tee -a "${LOG}"
  phase0_pass=false
else
  echo "PASS: npm $(npm --version)" | tee -a "${LOG}"
fi

if ! $phase0_pass; then
  echo "Phase 0 failed — aborting." | tee -a "${LOG}"
  exit 1
fi

# ============================================================
# Phase 1 — vanilla sqlcipher CLI smoke
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 1 — sqlcipher CLI smoke (key/insert/select/wrong-key)" | tee -a "${LOG}"

DB1="${WORK_DIR}/cli-smoke.db"
rm -f "${DB1}"

sqlcipher "${DB1}" <<'SQL' 2>&1 | tee -a "${LOG}"
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT, src TEXT);
INSERT INTO chunks (content, src) VALUES
  ('memoria-nox chunk one', 'spike'),
  ('memoria-nox chunk two', 'spike'),
  ('memoria-nox chunk three', 'spike');
SELECT count(*) AS n FROM chunks;
SQL

phase1_basic=$?

# attempt wrong-key open
echo "--- wrong-key probe ---" | tee -a "${LOG}"
wrong_out=$(sqlcipher "${DB1}" <<'SQL' 2>&1
PRAGMA key = 'wrong-pass';
PRAGMA cipher_compatibility = 4;
SELECT count(*) FROM chunks;
SQL
)
echo "$wrong_out" | tee -a "${LOG}"

if echo "$wrong_out" | grep -qE "(file is not a database|not a database|HMAC)"; then
  phase1_wrong_key=0
  echo "PASS: wrong key rejected cleanly" | tee -a "${LOG}"
else
  phase1_wrong_key=1
  echo "FAIL: wrong key did NOT fail predictably — got: ${wrong_out}" | tee -a "${LOG}"
fi

# WAL plaintext probe — write under WAL then inspect .wal raw bytes
DB_WAL="${WORK_DIR}/wal-probe.db"
rm -f "${DB_WAL}" "${DB_WAL}-wal" "${DB_WAL}-shm"
sqlcipher "${DB_WAL}" <<'SQL' 2>&1 >> "${LOG}"
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
PRAGMA journal_mode=WAL;
CREATE TABLE secrets (id INTEGER PRIMARY KEY, payload TEXT);
INSERT INTO secrets (payload) VALUES ('UNIQUE_PLAINTEXT_MARKER_42_BANANA');
.headers on
SELECT * FROM secrets;
SQL

if [ -f "${DB_WAL}-wal" ]; then
  if strings "${DB_WAL}-wal" 2>/dev/null | grep -q "UNIQUE_PLAINTEXT_MARKER_42_BANANA"; then
    phase1_wal=1
    echo "FAIL: WAL leaked plaintext marker" | tee -a "${LOG}"
  else
    phase1_wal=0
    echo "PASS: WAL did not leak plaintext marker" | tee -a "${LOG}"
  fi
else
  phase1_wal=0
  echo "PASS: WAL file not created (checkpoint absorbed) — no leak path" | tee -a "${LOG}"
fi

# also probe main DB has no plaintext
if strings "${DB_WAL}" 2>/dev/null | grep -q "UNIQUE_PLAINTEXT_MARKER_42_BANANA"; then
  phase1_main_leak=1
  echo "FAIL: main DB file leaked plaintext marker" | tee -a "${LOG}"
else
  phase1_main_leak=0
  echo "PASS: main DB file is ciphertext (no marker visible via strings)" | tee -a "${LOG}"
fi

# ============================================================
# Phase 2 — VACUUM INTO (snapshot via op-audit pattern)
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 2 — VACUUM INTO snapshot compat (op-audit pattern)" | tee -a "${LOG}"

DB_VAC_SRC="${WORK_DIR}/vacuum-src.db"
DB_VAC_DST="${WORK_DIR}/vacuum-dst.db"
rm -f "${DB_VAC_SRC}" "${DB_VAC_DST}"

sqlcipher "${DB_VAC_SRC}" <<'SQL' 2>&1 | tee -a "${LOG}"
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT);
INSERT INTO chunks (content) VALUES ('chunk-a'), ('chunk-b'), ('chunk-c');
ATTACH DATABASE '/tmp/vacuum-dst-attached.db' AS dst KEY 'spike-pass-1';
SELECT sqlcipher_export('dst');
DETACH dst;
SQL

# move attached file to expected output (sqlcipher_export needs attach pattern)
if [ -f /tmp/vacuum-dst-attached.db ]; then
  mv /tmp/vacuum-dst-attached.db "${DB_VAC_DST}"
fi

# Try VACUUM INTO ? on encrypted DB (this is op-audit's actual pattern)
sqlcipher "${DB_VAC_SRC}" <<SQL 2>&1 | tee -a "${LOG}"
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
VACUUM INTO '${WORK_DIR}/vacuum-via-into.db';
SQL

if [ -f "${WORK_DIR}/vacuum-via-into.db" ]; then
  # validate — note PRAGMA key emits "ok" on stdout; grep the LAST numeric line only
  count=$(sqlcipher "${WORK_DIR}/vacuum-via-into.db" <<SQL 2>/dev/null
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
SELECT count(*) FROM chunks;
SQL
)
  count_trim=$(echo "$count" | grep -E '^[0-9]+$' | tail -1)
  if [ "$count_trim" = "3" ]; then
    phase2_vacuum_into=0
    echo "PASS: VACUUM INTO produced encrypted snapshot, 3 rows preserved" | tee -a "${LOG}"
  else
    phase2_vacuum_into=1
    echo "FAIL: VACUUM INTO snapshot wrong count or unreadable (got: ${count_trim})" | tee -a "${LOG}"
  fi
else
  phase2_vacuum_into=1
  echo "FAIL: VACUUM INTO did not produce file" | tee -a "${LOG}"
fi

# ============================================================
# Phase 3 — FTS5 + standard CRUD round-trip
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 3 — FTS5 + CRUD on encrypted DB" | tee -a "${LOG}"

DB_FTS="${WORK_DIR}/fts5.db"
rm -f "${DB_FTS}"

fts_out=$(sqlcipher "${DB_FTS}" <<'SQL' 2>&1
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
CREATE VIRTUAL TABLE chunks_fts USING fts5(content);
INSERT INTO chunks_fts (content) VALUES ('memoria nox encrypted memory'),
                                         ('SQLCipher with FTS5 works'),
                                         ('quick brown fox jumps'),
                                         ('memory of nox memory');
SELECT rowid, content FROM chunks_fts WHERE chunks_fts MATCH 'memory' ORDER BY rank;
INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild');
SELECT count(*) FROM chunks_fts;
SQL
)
echo "$fts_out" | tee -a "${LOG}"

if echo "$fts_out" | grep -qE "memory.*nox.*memory|memoria nox encrypted memory" && \
   ! echo "$fts_out" | grep -qiE "no such (module|table)"; then
  phase3_fts5=0
  echo "PASS: FTS5 MATCH + rebuild work on encrypted DB" | tee -a "${LOG}"
else
  phase3_fts5=1
  echo "FAIL: FTS5 broken on encrypted DB" | tee -a "${LOG}"
fi

# ============================================================
# Phase 4 — loadable extension policy (sqlite-vec probe)
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 4 — loadable extension policy (sqlite-vec init probe)" | tee -a "${LOG}"

# SQLCipher CLI in 4.x defaults to load_extension DISABLED; must enable
# at compile-time OR via PRAGMA. CLI does not expose PRAGMA route.
# What we CAN test: (a) Does the binary even support .load? (b) Can we PRAGMA-enable?
ext_out=$(sqlcipher "${WORK_DIR}/ext-probe.db" <<'SQL' 2>&1
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
SELECT sqlite_compileoption_used('SQLITE_OMIT_LOAD_EXTENSION') AS omit_flag;
SELECT sqlite_compileoption_used('SQLITE_ALLOW_LOAD_EXTENSION') AS allow_flag;
SELECT sqlite_compileoption_used('SQLITE_ENABLE_LOAD_EXTENSION') AS enable_flag;
SQL
)
echo "$ext_out" | tee -a "${LOG}"

if echo "$ext_out" | grep -E "omit_flag.*=.*1" >/dev/null 2>&1; then
  phase4_loadable=1
  echo "WARN: SQLCipher CLI compiled with SQLITE_OMIT_LOAD_EXTENSION — extensions unavailable in CLI" | tee -a "${LOG}"
  echo "      Node binding (better-sqlite3-multiple-ciphers / @journeyapps/sqlcipher) may differ — must test in Phase 5" | tee -a "${LOG}"
else
  phase4_loadable=0
  echo "PASS: SQLCipher CLI does not omit load_extension (Node binding will inherit)" | tee -a "${LOG}"
fi

# ============================================================
# Phase 5 — Node bindings (better-sqlite3 fork)
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 5 — Node binding (better-sqlite3-multiple-ciphers OR @journeyapps/sqlcipher)" | tee -a "${LOG}"

if $QUICK; then
  echo "SKIP: --quick set — skipping Node binding install + tests" | tee -a "${LOG}"
  phase5_node=2
  phase5_vec=2
else
  cd "${WORK_DIR}"
  if [ ! -f package.json ]; then
    cat > package.json <<'PKG'
{
  "name": "sqlcipher-spike-work",
  "version": "0.0.0",
  "private": true,
  "type": "commonjs"
}
PKG
  fi

  echo "Attempting install of better-sqlite3-multiple-ciphers (recommended primary)..." | tee -a "${LOG}"
  install_log="${WORK_DIR}/npm-install.log"
  if npm install --no-fund --no-audit --loglevel=error better-sqlite3-multiple-ciphers 2> "${install_log}" 1>> "${LOG}"; then
    echo "PASS: better-sqlite3-multiple-ciphers installed" | tee -a "${LOG}"
    binding="multiple-ciphers"
  else
    tail -20 "${install_log}" | tee -a "${LOG}"
    echo "FAIL on primary binding — trying fallback @journeyapps/sqlcipher..." | tee -a "${LOG}"
    if npm install --no-fund --no-audit --loglevel=error @journeyapps/sqlcipher 2> "${install_log}" 1>> "${LOG}"; then
      echo "PASS: @journeyapps/sqlcipher installed (fallback)" | tee -a "${LOG}"
      binding="journeyapps"
    else
      tail -20 "${install_log}" | tee -a "${LOG}"
      echo "FAIL: both Node bindings failed to install" | tee -a "${LOG}"
      binding="none"
    fi
  fi

  if [ "$binding" != "none" ]; then
    # write probe script based on binding
    cat > probe.js <<JS
const BINDING = process.env.BINDING || '${binding}';
let Database;
if (BINDING === 'multiple-ciphers') {
  Database = require('better-sqlite3-multiple-ciphers');
} else {
  // @journeyapps/sqlcipher has an async-callback API; use sync-ish via promise wrap.
  // We attempt the simpler sqlite3-style first, falling back to noting incompat.
  try {
    Database = require('@journeyapps/sqlcipher').verbose().Database;
  } catch (e) {
    console.error('JOURNEYAPPS_LOAD_FAIL', e.message);
    process.exit(2);
  }
}

const path = require('path');
const dbPath = path.join(__dirname, 'node-probe.db');
require('fs').existsSync(dbPath) && require('fs').unlinkSync(dbPath);

function runMultipleCiphers() {
  const db = new Database(dbPath);
  db.pragma("cipher='sqlcipher'");
  db.pragma("legacy=4");
  db.pragma("key='spike-pass-1'");

  // basic CRUD
  db.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT)");
  const ins = db.prepare("INSERT INTO chunks (content) VALUES (?)");
  for (let i = 0; i < 100; i++) ins.run('chunk ' + i);
  const n = db.prepare("SELECT count(*) AS n FROM chunks").get().n;
  console.log('PROBE_BASIC_COUNT=' + n);

  // FTS5
  db.exec("CREATE VIRTUAL TABLE chunks_fts USING fts5(content)");
  db.prepare("INSERT INTO chunks_fts (content) SELECT content FROM chunks").run();
  const fts = db.prepare("SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'chunk'").get().n;
  console.log('PROBE_FTS_MATCH=' + fts);

  // load_extension capability probe
  let extOk = false;
  let extErr = '';
  try {
    if (typeof db.loadExtension === 'function') {
      // probe path — sqlite-vec dylib may not exist on this machine; expect "no such file"
      // we accept that error as "API works, extension just missing" = capability YES
      try {
        db.loadExtension('/nonexistent/path/sqlite-vec.dylib');
      } catch (e) {
        if (/no such file|cannot find|image not found/i.test(e.message)) {
          extOk = true;
          extErr = 'API present; dylib missing (expected on dev box)';
        } else if (/not authorized|disabled|omit/i.test(e.message)) {
          extOk = false;
          extErr = e.message;
        } else {
          // Unknown error — note it
          extOk = false;
          extErr = e.message;
        }
      }
    } else {
      extErr = 'loadExtension API not present on binding';
    }
  } catch (e) {
    extErr = e.message;
  }
  console.log('PROBE_LOAD_EXT_API=' + extOk);
  console.log('PROBE_LOAD_EXT_NOTE=' + extErr);

  // VACUUM INTO
  const snapPath = path.join(__dirname, 'node-snap.db');
  require('fs').existsSync(snapPath) && require('fs').unlinkSync(snapPath);
  try {
    db.exec("VACUUM INTO '" + snapPath.replace(/'/g, "''") + "'");
    console.log('PROBE_VACUUM_INTO=ok');
  } catch (e) {
    console.log('PROBE_VACUUM_INTO_ERR=' + e.message);
  }

  // re-open snap with same key, count
  try {
    const db2 = new Database(snapPath);
    db2.pragma("cipher='sqlcipher'");
    db2.pragma("legacy=4");
    db2.pragma("key='spike-pass-1'");
    const n2 = db2.prepare("SELECT count(*) AS n FROM chunks").get().n;
    console.log('PROBE_SNAP_COUNT=' + n2);
    db2.close();
  } catch (e) {
    console.log('PROBE_SNAP_REOPEN_ERR=' + e.message);
  }

  // benchmark: 1000 selects on indexed col
  db.exec("CREATE INDEX idx_content ON chunks(content)");
  const sel = db.prepare("SELECT id FROM chunks WHERE content = ?");
  const N = 1000;
  const t0 = process.hrtime.bigint();
  for (let i = 0; i < N; i++) sel.get('chunk ' + (i % 100));
  const t1 = process.hrtime.bigint();
  const elapsedMs = Number(t1 - t0) / 1e6;
  console.log('PROBE_BENCH_SELECTS=' + N);
  console.log('PROBE_BENCH_TOTAL_MS=' + elapsedMs.toFixed(2));
  console.log('PROBE_BENCH_PER_OP_US=' + (elapsedMs * 1000 / N).toFixed(2));

  db.close();
}

function runJourneyApps() {
  // journeyapps API is async/sqlite3-style
  const db = new Database(dbPath);
  db.serialize(() => {
    db.run("PRAGMA cipher_compatibility = 4");
    db.run("PRAGMA key = 'spike-pass-1'");
    db.run("CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT)");
    db.run("INSERT INTO chunks (content) VALUES ('one'), ('two'), ('three')");
    db.get("SELECT count(*) AS n FROM chunks", (err, row) => {
      if (err) {
        console.log('PROBE_JOURNEY_ERR=' + err.message);
      } else {
        console.log('PROBE_BASIC_COUNT=' + row.n);
      }
    });
  });
  db.close();
}

try {
  if (BINDING === 'multiple-ciphers') runMultipleCiphers();
  else runJourneyApps();
} catch (e) {
  console.error('PROBE_FATAL=' + e.message);
  console.error(e.stack);
  process.exit(2);
}
JS

    echo "Running probe.js with BINDING=${binding}..." | tee -a "${LOG}"
    if BINDING="${binding}" node probe.js 2>&1 | tee -a "${LOG}"; then
      phase5_node=0
      if grep -qE "PROBE_LOAD_EXT_API=true" "${LOG}" && \
         grep -qE "PROBE_BASIC_COUNT=100" "${LOG}" && \
         grep -qE "PROBE_FTS_MATCH=100" "${LOG}" && \
         grep -qE "PROBE_SNAP_COUNT=100" "${LOG}"; then
        phase5_vec=0
        echo "PASS: Node binding (${binding}) — CRUD + FTS5 + snapshot + load_extension API all green" | tee -a "${LOG}"
      else
        phase5_vec=1
        echo "WARN: Node binding (${binding}) installed but some probes failed — see log" | tee -a "${LOG}"
      fi
    else
      phase5_node=1
      phase5_vec=1
      echo "FAIL: probe.js exited non-zero" | tee -a "${LOG}"
    fi
  else
    phase5_node=1
    phase5_vec=1
  fi
  cd "${SCRIPT_DIR}"
fi

# ============================================================
# Phase 6 — Performance overhead (vanilla vs cipher)
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 6 — Performance overhead vanilla vs SQLCipher (rough)" | tee -a "${LOG}"

# vanilla baseline via system sqlite3
if command -v sqlite3 >/dev/null 2>&1; then
  DB_VAN="${WORK_DIR}/vanilla-bench.db"
  rm -f "${DB_VAN}"
  start=$(date +%s%N)
  sqlite3 "${DB_VAN}" <<'SQL' >/dev/null 2>&1
CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT);
WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<5000)
INSERT INTO chunks (content) SELECT 'chunk ' || x FROM c;
CREATE INDEX idx ON chunks(content);
SELECT count(*) FROM chunks WHERE content LIKE 'chunk 1%';
SQL
  end=$(date +%s%N)
  vanilla_ms=$(( (end - start) / 1000000 ))
  echo "vanilla sqlite3 5k-insert+index+like: ${vanilla_ms}ms" | tee -a "${LOG}"

  DB_CIP="${WORK_DIR}/cipher-bench.db"
  rm -f "${DB_CIP}"
  start=$(date +%s%N)
  sqlcipher "${DB_CIP}" <<'SQL' >/dev/null 2>&1
PRAGMA key = 'spike-pass-1';
PRAGMA cipher_compatibility = 4;
CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT);
WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<5000)
INSERT INTO chunks (content) SELECT 'chunk ' || x FROM c;
CREATE INDEX idx ON chunks(content);
SELECT count(*) FROM chunks WHERE content LIKE 'chunk 1%';
SQL
  end=$(date +%s%N)
  cipher_ms=$(( (end - start) / 1000000 ))
  echo "sqlcipher 5k-insert+index+like: ${cipher_ms}ms" | tee -a "${LOG}"

  if [ "$vanilla_ms" -gt 0 ]; then
    overhead_pct=$(( (cipher_ms - vanilla_ms) * 100 / vanilla_ms ))
    echo "Overhead: ${overhead_pct}% (cipher vs vanilla)" | tee -a "${LOG}"
  fi
else
  echo "vanilla sqlite3 not available — skipping perf comparison" | tee -a "${LOG}"
fi

# ============================================================
# Phase 7 — Realistic per-op benchmark (Node binding)
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 7 — Realistic per-op benchmark (vanilla vs cipher)" | tee -a "${LOG}"

if $QUICK || [ "$phase5_node" -ne 0 ]; then
  echo "SKIP: --quick or Phase 5 fail" | tee -a "${LOG}"
  phase7_bench=2
else
  cp "${SCRIPT_DIR}/bench-realistic.js" "${WORK_DIR}/bench-realistic.js" 2>/dev/null || true
  cd "${WORK_DIR}"
  if node bench-realistic.js > "${WORK_DIR}/bench-realistic.json" 2>> "${LOG}"; then
    cat "${WORK_DIR}/bench-realistic.json" | tee -a "${LOG}"
    phase7_bench=0
    echo "PASS: realistic benchmark captured to bench-realistic.json" | tee -a "${LOG}"
  else
    phase7_bench=1
    echo "FAIL: bench-realistic.js errored" | tee -a "${LOG}"
  fi
  cd "${SCRIPT_DIR}"
fi

# ============================================================
# Phase 8 — sqlite-vec extension load + vec0 query on encrypted DB
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Phase 8 — sqlite-vec on SQLCipher (vec0 virtual table + query + snapshot)" | tee -a "${LOG}"

if $QUICK || [ "$phase5_node" -ne 0 ]; then
  echo "SKIP: --quick or Phase 5 fail" | tee -a "${LOG}"
  phase8_vec=2
else
  cd "${WORK_DIR}"
  if ! [ -d node_modules/sqlite-vec ]; then
    echo "Installing sqlite-vec npm package..." | tee -a "${LOG}"
    npm install --no-fund --no-audit --loglevel=error sqlite-vec 2>> "${LOG}" 1>> "${LOG}" || true
  fi
  cp "${SCRIPT_DIR}/vec-probe.js" "${WORK_DIR}/vec-probe.js" 2>/dev/null || true
  if node vec-probe.js 2>&1 | tee -a "${LOG}" | grep -q "ALL_VEC_PROBES_PASSED"; then
    phase8_vec=0
    echo "PASS: sqlite-vec loads + vec0 query + snapshot all green on encrypted DB" | tee -a "${LOG}"
  else
    phase8_vec=1
    echo "FAIL: sqlite-vec probe did not complete cleanly" | tee -a "${LOG}"
  fi
  cd "${SCRIPT_DIR}"
fi

# ============================================================
# Verdict
# ============================================================
echo "" | tee -a "${LOG}"
echo "## Verdict computation" | tee -a "${LOG}"

# Critical gates:
#  - Phase 1 basic CRUD ok (sqlcipher CLI works)
#  - Phase 1 wrong-key rejects cleanly
#  - Phase 2 VACUUM INTO preserves data (op-audit compat)
#  - Phase 3 FTS5 works on encrypted DB
#  - Phase 5 Node binding present + LOAD_EXT API exposed (for sqlite-vec)
#
# Verdict matrix:
#   ALL critical PASS → GO
#   FTS5 fail OR Node binding fail (extension API absent) → NO-GO (pivot LUKS-only)
#   Snapshot fail → NO-GO (op-audit pattern broken — non-starter)
#   Wrong-key fail → NO-GO (cipher integrity not guaranteed)

go=true
nogo_reasons=()

[ "$phase1_basic"     -eq 0 ] || { go=false; nogo_reasons+=("phase1_basic_crud"); }
[ "$phase1_wrong_key" -eq 0 ] || { go=false; nogo_reasons+=("phase1_wrong_key"); }
[ "$phase1_main_leak" -eq 0 ] || { go=false; nogo_reasons+=("phase1_main_db_leak"); }
[ "$phase2_vacuum_into" -eq 0 ] || { go=false; nogo_reasons+=("phase2_vacuum_into"); }
[ "$phase3_fts5"      -eq 0 ] || { go=false; nogo_reasons+=("phase3_fts5"); }

# Phase 5/7/8 only blocking if not in --quick
if ! $QUICK; then
  [ "$phase5_node"    -eq 0 ] || { go=false; nogo_reasons+=("phase5_node_binding"); }
  [ "$phase5_vec"     -eq 0 ] || { go=false; nogo_reasons+=("phase5_extension_api"); }
  [ "$phase8_vec"     -eq 0 ] || { go=false; nogo_reasons+=("phase8_sqlite_vec"); }
fi

if $go; then
  echo "VERDICT: GO ✔" | tee -a "${LOG}"
  echo "VERDICT=GO" > "${WORK_DIR}/verdict.txt"
  exit 0
else
  echo "VERDICT: NO-GO ✗" | tee -a "${LOG}"
  echo "Reasons: ${nogo_reasons[*]}" | tee -a "${LOG}"
  echo "VERDICT=NO-GO" > "${WORK_DIR}/verdict.txt"
  echo "REASONS=${nogo_reasons[*]}" >> "${WORK_DIR}/verdict.txt"
  exit 1
fi
