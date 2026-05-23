// staged-A2-T3/edits/src/lib/db.ts
//
// A2 Tier 3 / Phase 1 — db.ts SQLCipher key-open wire-up.
//
// What changed vs staged-1.7a/edits/db.ts:
//   1. Driver swap: `better-sqlite3` → `better-sqlite3-multiple-ciphers`
//      (drop-in API-compatible fork; bundles its own SQLCipher build, no
//      system libsqlcipher required at runtime per RESULTS.md §Build).
//   2. New env-driven crypto open path:
//        NOX_DB_KEY          — secret cipher key (if set: encrypted open)
//        NOX_DB_REQUIRE_KEY  — if "1" and NOX_DB_KEY missing → throw at open
//                              (hard-mode for prod; keeps backward-compat default)
//   3. Encrypted open applies PRAGMAs in canonical order (per spike vec-probe.js
//      Phase 8 + recon §4):
//        PRAGMA cipher = 'sqlcipher';
//        PRAGMA legacy = 4;                  -- alias for cipher_compatibility=4
//        PRAGMA cipher_compatibility = 4;    -- explicit name for newer ciphers
//        PRAGMA key = '<NOX_DB_KEY>';        -- triggers KDF (~70-100ms once)
//      The double-PRAGMA pattern (`legacy=4` + `cipher_compatibility=4`) is
//      defensive: sqlite3mc accepts both spellings, RESULTS.md §Verdict pins
//      "cipher_compatibility=4 (AES-256-CBC HMAC-SHA512)" as the canonical
//      cipher for nox-mem; legacy=4 is included for forward-compat with any
//      sqlite3mc release that prefers it.
//   4. defaultSafeIntegers(true) called post-open. Required for vec0 rowid:
//      better-sqlite3 binds JS Number as REAL (float) by default, but vec0
//      rejects non-integer rowid (F2 in RESULTS.md "Only integers are allows
//      for primary key values"). Safe-integers mode forces all INTEGER columns
//      to be returned/bound as BigInt, which sqlite-vec accepts. This is the
//      same root-cause class as `[[sqlite-text-affinity-coerces-int-back]]`.
//   5. Snapshot/VACUUM INTO compatibility — RESULTS.md Phase 5.e + 8.f confirm
//      that VACUUM INTO from an encrypted source produces an encrypted snapshot
//      using the SAME key. No per-snapshot key wiring required in this file;
//      op-audit's snapshot() reuses the same getDb() singleton, so the key
//      flows through transparently. ATTACH DATABASE with a different key for
//      cross-key operations is NOT supported in this phase (P2 if needed).
//
// What did NOT change:
//   • DB_PATH resolution (NOX_DB_PATH > OPENCLAW_WORKSPACE > __dirname relative)
//   • Large-DB ingest guard (PROD_CHUNK_THRESHOLD)
//   • Performance pragmas (journal_mode WAL, cache_size, mmap_size, etc.)
//   • Schema migrations V1-V7 (all preserved verbatim from staged-1.7a)
//   • backupDb() / pruneBackups() / ensureSchema() public surface
//
// Backward compatibility:
//   • NOX_DB_KEY UNSET + NOX_DB_REQUIRE_KEY UNSET → DB opens plaintext (current
//     behavior; deploy-safe for existing 62.9k-chunk production DB until P2
//     migration script lands).
//   • NOX_DB_KEY UNSET + NOX_DB_REQUIRE_KEY=1 → throw at first getDb() call
//     (operational tripwire for post-migration prod).
//   • NOX_DB_KEY SET on a plaintext DB → sqlite3mc does NOT silently no-op the
//     key PRAGMA. It throws SQLITE_NOTADB on first query ("file is not a
//     database"). Operational implication: rollout MUST sequence "deploy P1
//     code (key infra ready) → run P2 migration (VACUUM INTO encrypted) → set
//     NOX_DB_KEY in env → restart". Never set NOX_DB_KEY against an
//     unmigrated plaintext DB in prod. See db.crypto.test.ts §4 for pinned
//     behavior — that test is the canary against sqlite3mc behavior drift.
//
// References:
//   • Spike RESULTS.md (verdict GO)
//   • Spike vec-probe.js (PRAGMA pattern + defaultSafeIntegers(true))
//   • specs/2026-05-24-A2-tier3-crypto-audit-RECON.md (full design)
//   • docs/DECISIONS.md D54-D58 (resolved defaults)

import Database from "better-sqlite3-multiple-ciphers";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const _ws = process.env.OPENCLAW_WORKSPACE;

// DB path resolution — priority order (postmortem 2026-05-19 fix):
//   1. NOX_DB_PATH env var (explicit override for eval/test isolation)
//   2. OPENCLAW_WORKSPACE-derived canonical path (production default)
//   3. Relative fallback for local dev
export const DB_PATH = (
  process.env.NOX_DB_PATH
    ? resolve(process.env.NOX_DB_PATH)
    : _ws
      ? resolve(_ws, "tools", "nox-mem", "nox-mem.db")
      : resolve(__dirname, "..", "nox-mem.db")
);
export const BACKUP_DIR = _ws ? resolve(_ws, "tools", "nox-mem", "backups") : resolve(__dirname, "..", "backups");
const SCHEMA_VERSION = 18;

// ────────────────────────────────────────────────────────────────────────────
// SQLCipher key-open (A2 Tier 3 / Phase 1)
// ────────────────────────────────────────────────────────────────────────────

/**
 * Whether the singleton was opened with an encryption key in this process.
 * Exposed for /api/health introspection. Reset by closeDb().
 */
let _isEncrypted = false;

export function isDbEncrypted(): boolean {
  return _isEncrypted;
}

/**
 * Apply SQLCipher PRAGMAs to a freshly-opened Database handle. Idempotent and
 * order-sensitive: cipher/legacy/cipher_compatibility BEFORE key, per sqlite3mc
 * docs. The KDF runs synchronously inside the `PRAGMA key` call (~70-100ms
 * one-time per process per RESULTS.md §perf), so callers should not loop this.
 *
 * Throws if the underlying binding rejects any PRAGMA (rare — would indicate
 * a build mismatch between better-sqlite3-multiple-ciphers and the bundled
 * SQLCipher). Wrong-key rejection happens later, on first real query, with
 * the deterministic message "file is not a database (26)" (RESULTS.md 1.b).
 */
function applyCipherPragmas(db: Database.Database, key: string): void {
  // Order: cipher-family declaration first, then compatibility level, then key.
  // The `simple: true` flag tells better-sqlite3 to bypass result parsing
  // (these PRAGMAs return no row; without it the binding warns).
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  // Escape any single-quote inside the key by doubling it (SQL literal rule).
  // Defensive — NOX_DB_KEY in prod is base64 random bytes (no quotes), but if
  // a human types one we don't want a SQL injection at PRAGMA time.
  const escapedKey = key.replace(/'/g, "''");
  db.pragma(`key='${escapedKey}'`, { simple: true });
}

// ────────────────────────────────────────────────────────────────────────────
// Large-DB ingest guard (postmortem 2026-05-19)
// ────────────────────────────────────────────────────────────────────────────
// If the resolved DB has more than PROD_CHUNK_THRESHOLD chunks and the caller
// has not set NOX_ALLOW_PROD_INGEST=1, abort before any write.  This prevents
// eval/test ingests from silently polluting a large production DB.
const PROD_CHUNK_THRESHOLD = 10_000;

export function checkLargeDbIngestGuard(db: Database.Database, operation: string): void {
  if (process.env.NOX_ALLOW_PROD_INGEST === "1") return;

  const row = db.prepare("SELECT COUNT(*) AS n FROM chunks").get() as { n: number } | undefined;
  const chunkCount = row?.n ?? 0;

  if (chunkCount > PROD_CHUNK_THRESHOLD) {
    const msg = [
      `[db] ABORT: Large-DB ingest guard triggered on operation '${operation}'.`,
      `  DB path:     ${DB_PATH}`,
      `  Chunk count: ${chunkCount} (threshold: ${PROD_CHUNK_THRESHOLD})`,
      `  This DB appears to be the production nox-mem.db.`,
      `  If you intend to ingest into production, set:`,
      `    NOX_ALLOW_PROD_INGEST=1 nox-mem ${operation} ...`,
      `  If you are running an eval/ablation, ensure NOX_DB_PATH points to an`,
      `  isolated eval DB (e.g. /tmp/entity-eval.db), NOT the production path.`,
      `  (Root cause of the 2026-05-19 wipe incident — see docs/INCIDENTS.md)`,
    ].join("\n");
    console.error(msg);
    process.exit(1);
  }
}

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db && _db.open) return _db;

  const key = process.env.NOX_DB_KEY;
  const requireKey = process.env.NOX_DB_REQUIRE_KEY === "1";

  if (requireKey && (!key || key.length === 0)) {
    throw new Error(
      "[db] NOX_DB_REQUIRE_KEY=1 but NOX_DB_KEY is unset/empty. " +
      "Either set NOX_DB_KEY to the cipher key for this DB, or unset " +
      "NOX_DB_REQUIRE_KEY to allow plaintext open (backward-compat mode).",
    );
  }

  _db = new Database(DB_PATH);

  // Apply cipher PRAGMAs FIRST if a key is provided — KDF must run before any
  // SQL statement (PRAGMA key on a vanilla DB is a no-op; on encrypted DB it
  // is mandatory). See RESULTS.md §1.a + vec-probe.js order.
  if (key && key.length > 0) {
    applyCipherPragmas(_db, key);
    _isEncrypted = true;
  } else {
    _isEncrypted = false;
  }

  // Required for vec0 rowid (BigInt-strict virtual table).
  // Safe to call on plaintext DBs too — it only changes Number/BigInt
  // marshaling, not on-disk format. See RESULTS.md F2.
  _db.defaultSafeIntegers(true);

  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");
  // Wait up to 5s on lock contention instead of failing immediately with SQLITE_BUSY.
  _db.pragma("busy_timeout = 5000");
  // Performance: Large cache for 51MB DB + 1,780 chunks (current prod).
  _db.pragma("cache_size = -64000");     // 64MB cache (was 2MB default)
  _db.pragma("mmap_size = 268435456");   // 256MB memory-mapped I/O
  _db.pragma("synchronous = NORMAL");    // Faster writes (WAL ensures safety)

  ensureSchema(_db);
  return _db;
}

export function closeDb(): void {
  if (_db && _db.open) {
    _db.close();
    _db = null;
    _isEncrypted = false;
  }
}

/**
 * Backup SQLite using the online backup API (safe even during writes).
 * Retains up to `keepDays` daily backups.
 *
 * NOTE (A2 Tier 3): backup() reads page-by-page in raw form — when the source
 * DB is encrypted, the destination is also encrypted with the SAME key. Reopen
 * with same NOX_DB_KEY to read. This matches RESULTS.md Phase 2 + 5.e behavior.
 */
export function backupDb(keepDays = 7): string {
  if (!existsSync(DB_PATH)) return "";
  if (!existsSync(BACKUP_DIR)) mkdirSync(BACKUP_DIR, { recursive: true });

  const today = new Date().toISOString().split("T")[0];
  const destPath = resolve(BACKUP_DIR, `nox-mem-${today}.db`);

  const key = process.env.NOX_DB_KEY;
  const src = new Database(DB_PATH, { readonly: true });
  if (key && key.length > 0) {
    applyCipherPragmas(src, key);
  }
  src.backup(destPath).then(() => {
    src.close();
    console.log(`[BACKUP] Saved to ${destPath}`);
    pruneBackups(keepDays);
  }).catch((err: Error) => {
    src.close();
    try {
      copyFileSync(DB_PATH, destPath);
      console.log(`[BACKUP] Copied (fallback) to ${destPath}`);
      pruneBackups(keepDays);
    } catch {
      console.error(`[BACKUP] Failed: ${err.message}`);
    }
  });

  return destPath;
}

function pruneBackups(keepDays: number): void {
  try {
    const files = readdirSync(BACKUP_DIR)
      .filter(f => f.match(/^nox-mem-\d{4}-\d{2}-\d{2}\.db$/))
      .sort()
      .reverse();
    for (const f of files.slice(keepDays)) {
      unlinkSync(resolve(BACKUP_DIR, f));
      console.log(`[BACKUP] Pruned old backup: ${f}`);
    }
  } catch { /* non-critical */ }
}

function ensureSchema(db: Database.Database): void {
  db.exec(`CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
  );`);

  const row = db.prepare("SELECT value FROM meta WHERE key = 'schema_version'").get() as { value: string } | undefined;
  const currentVersion = row ? parseInt(row.value, 10) : 0;

  if (currentVersion === SCHEMA_VERSION) return;
  if (currentVersion > SCHEMA_VERSION) {
    throw new Error(`DB schema ${currentVersion} > expected ${SCHEMA_VERSION}`);
  }

  if (currentVersion < 1) migrateToV1(db);
  if (currentVersion < 2) migrateToV2(db);
  if (currentVersion < 3) migrateToV3(db);
  if (currentVersion < 4) migrateToV4(db);
  if (currentVersion < 5) migrateToV5(db);
  if (currentVersion < 6) migrateToV6(db);
  if (currentVersion < 7) migrateToV7(db);

  db.prepare("INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES ('schema_version', ?, datetime('now'))").run(String(SCHEMA_VERSION));
}

function migrateToV7(db: Database.Database): void {
  try { db.exec(`ALTER TABLE kg_entities ADD COLUMN attributes TEXT`); } catch {}
  try { db.exec(`ALTER TABLE chunks ADD COLUMN source_type TEXT`); } catch {}
  try { db.exec(`ALTER TABLE chunks ADD COLUMN is_compiled INTEGER DEFAULT 0`); } catch {}
  db.exec(`CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type);`);
  db.exec(`CREATE INDEX IF NOT EXISTS idx_chunks_is_compiled ON chunks(is_compiled);`);

  db.exec(`
    UPDATE chunks SET is_compiled=1, source_type='compiled'
      WHERE is_consolidated=1 AND source_type IS NULL;
    UPDATE chunks SET source_type='external'
      WHERE source_type IS NULL AND (
        source_file LIKE '%boris%' OR
        source_file LIKE '%atlas/research%' OR
        source_file LIKE '%news%' OR
        source_file LIKE '%noticias%'
      );
    UPDATE chunks SET source_type='user_statement'
      WHERE source_type IS NULL AND (
        source_file LIKE '%whatsapp%' OR
        source_file LIKE '%telegram%' OR
        chunk_text LIKE '%Totó disse%' OR
        chunk_text LIKE '%Toto disse%'
      );
    UPDATE chunks SET source_type='timeline'
      WHERE source_type IS NULL;
  `);
}

function migrateToV6(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS search_telemetry (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL DEFAULT (datetime('now')),
      query_hash TEXT NOT NULL,
      query_words INTEGER NOT NULL,
      variants_count INTEGER NOT NULL DEFAULT 1,
      results_count INTEGER NOT NULL DEFAULT 0,
      has_semantic INTEGER NOT NULL DEFAULT 0,
      latency_ms INTEGER NOT NULL DEFAULT 0,
      expansion_skipped_reason TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_search_telemetry_ts ON search_telemetry(ts DESC);
  `);
  db.prepare("INSERT OR IGNORE INTO meta (key, value, updated_at) VALUES ('expansion_enabled', 'true', datetime('now'))").run();
}

function migrateToV1(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_file TEXT NOT NULL,
      chunk_text TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      source_date TEXT,
      is_consolidated INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      metadata TEXT
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
      chunk_text, source_file, chunk_type,
      content=chunks, content_rowid=id,
      tokenize='porter unicode61'
    );
    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
    END;
    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
    CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_file);
    CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);
    CREATE INDEX IF NOT EXISTS idx_chunks_date ON chunks(source_date);
  `);
}

function migrateToV2(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS consolidated_files (
      source_file TEXT PRIMARY KEY,
      status INTEGER NOT NULL DEFAULT 1,
      processed_at TEXT DEFAULT (datetime('now'))
    );
  `);
  db.exec(`
    INSERT OR IGNORE INTO consolidated_files (source_file, status, processed_at)
    SELECT DISTINCT source_file, 1, datetime('now')
    FROM chunks WHERE is_consolidated = 1;
  `);
  db.exec(`DROP INDEX IF EXISTS idx_chunks_consolidated;`);
  db.exec(`DROP TRIGGER IF EXISTS chunks_au;`);
}

function migrateToV4(db: Database.Database): void {
  const cols = db.prepare("PRAGMA table_info(chunks)").all() as Array<{ name: string }>;
  const colNames = new Set(cols.map((c) => c.name));

  if (!colNames.has("tier")) {
    db.exec(`ALTER TABLE chunks ADD COLUMN tier TEXT DEFAULT 'peripheral';`);
  }
  if (!colNames.has("access_count")) {
    db.exec(`ALTER TABLE chunks ADD COLUMN access_count INTEGER DEFAULT 0;`);
  }
  if (!colNames.has("last_accessed_at")) {
    db.exec(`ALTER TABLE chunks ADD COLUMN last_accessed_at TEXT;`);
  }
  if (!colNames.has("importance")) {
    db.exec(`ALTER TABLE chunks ADD COLUMN importance REAL DEFAULT 0.5;`);
  }

  db.exec(`CREATE INDEX IF NOT EXISTS idx_chunks_tier ON chunks(tier);`);

  try {
    const metricCols = db.prepare("PRAGMA table_info(daily_metrics)").all() as Array<{ name: string }>;
    const metricColNames = new Set(metricCols.map((c) => c.name));
    if (metricCols.length > 0 && !metricColNames.has("noise_filtered")) {
      db.exec(`ALTER TABLE daily_metrics ADD COLUMN noise_filtered INTEGER DEFAULT 0;`);
    }
  } catch { /* daily_metrics may not exist yet */ }

  db.prepare(`
    UPDATE chunks SET tier = 'working', importance = 0.8, updated_at = datetime('now')
    WHERE chunk_type IN ('decision', 'lesson', 'person', 'project')
      AND (tier IS NULL OR tier = 'peripheral')
  `).run();
}

function migrateToV5(db: Database.Database): void {
  db.exec(`
    DROP TRIGGER IF EXISTS chunks_ai;
    DROP TRIGGER IF EXISTS chunks_ad;
    DROP TRIGGER IF EXISTS chunks_au;
    DROP TABLE IF EXISTS chunks_fts;
  `);

  db.exec(`
    CREATE VIRTUAL TABLE chunks_fts USING fts5(
      chunk_text, source_file, chunk_type,
      content=chunks, content_rowid=id,
      tokenize='unicode61 remove_diacritics 2'
    );
  `);

  db.exec(`INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');`);

  db.exec(`
    CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
    CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
    END;
    CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
  `);

  console.log("[MIGRATE V5] FTS tokenizer updated: porter unicode61 → unicode61 remove_diacritics=2");
}

function migrateToV3(db: Database.Database): void {
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS dedup_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      chunk_text_preview TEXT NOT NULL,
      source_file TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      suppressed_at TEXT DEFAULT (datetime('now')),
      reason TEXT
    );
  `);

  db.exec(`
    ALTER TABLE chunks ADD COLUMN memory_type TEXT;
  `);
}
