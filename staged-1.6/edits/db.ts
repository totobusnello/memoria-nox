import Database from "better-sqlite3";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const _ws = process.env.OPENCLAW_WORKSPACE;
export const DB_PATH = _ws ? resolve(_ws, "tools", "nox-mem", "nox-mem.db") : resolve(__dirname, "..", "nox-mem.db");
export const BACKUP_DIR = _ws ? resolve(_ws, "tools", "nox-mem", "backups") : resolve(__dirname, "..", "backups");
const SCHEMA_VERSION = 6;

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db && _db.open) return _db;
  _db = new Database(DB_PATH);
  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");
  // Wait up to 5s on lock contention instead of failing immediately with SQLITE_BUSY.
  // Needed because watcher ingest + api writes + crystallize/reflect share the same DB
  // in WAL mode — writers still serialize, and default busy_timeout=0 causes silent failures.
  _db.pragma("busy_timeout = 5000");
  // Performance: Large cache for 51MB DB + 1,780 chunks
  _db.pragma("cache_size = -64000");     // 64MB cache (was 2MB default)
  _db.pragma("mmap_size = 268435456");   // 256MB memory-mapped I/O (was 0/disabled)
  _db.pragma("synchronous = NORMAL");    // Faster writes (WAL ensures safety)
  ensureSchema(_db);
  return _db;
}

export function closeDb(): void {
  if (_db && _db.open) {
    _db.close();
    _db = null;
  }
}

/**
 * Backup SQLite using the online backup API (safe even during writes).
 * Retains up to `keepDays` daily backups.
 */
export function backupDb(keepDays = 7): string {
  if (!existsSync(DB_PATH)) return "";
  if (!existsSync(BACKUP_DIR)) mkdirSync(BACKUP_DIR, { recursive: true });

  const today = new Date().toISOString().split("T")[0];
  const destPath = resolve(BACKUP_DIR, `nox-mem-${today}.db`);

  // Use SQLite backup API via better-sqlite3
  const src = new Database(DB_PATH, { readonly: true });
  src.backup(destPath).then(() => {
    src.close();
    console.log(`[BACKUP] Saved to ${destPath}`);
    // Prune old backups
    pruneBackups(keepDays);
  }).catch((err: Error) => {
    src.close();
    // Fallback to file copy if backup API fails
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

  db.prepare("INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES ('schema_version', ?, datetime('now'))").run(String(SCHEMA_VERSION));
}

function migrateToV6(db: Database.Database): void {
  // Fase 1.6 — search telemetry + expansion toggle.
  // query_hash is sha1 hex prefix, não armazenamos texto cru da query por privacidade.
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
  // Seed default config (toggle off sem deploy: UPDATE meta SET value='false' WHERE key='expansion_enabled')
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
  // Drop UPDATE trigger (caused FTS5 write amplification in v2)
  db.exec(`DROP TRIGGER IF EXISTS chunks_au;`);
}

function migrateToV4(db: Database.Database): void {
  // Sprint A: Tier system (core/working/peripheral)
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

  // Add noise_filtered column to daily_metrics (if table exists)
  try {
    const metricCols = db.prepare("PRAGMA table_info(daily_metrics)").all() as Array<{ name: string }>;
    const metricColNames = new Set(metricCols.map((c) => c.name));
    if (metricCols.length > 0 && !metricColNames.has("noise_filtered")) {
      db.exec(`ALTER TABLE daily_metrics ADD COLUMN noise_filtered INTEGER DEFAULT 0;`);
    }
  } catch { /* daily_metrics may not exist yet */ }

  // Seed tiers based on existing chunk types
  db.prepare(`
    UPDATE chunks SET tier = 'working', importance = 0.8, updated_at = datetime('now')
    WHERE chunk_type IN ('decision', 'lesson', 'person', 'project')
      AND (tier IS NULL OR tier = 'peripheral')
  `).run();
}

function migrateToV5(db: Database.Database): void {
  // Sprint D: Fix FTS tokenizer — replace Porter (EN stemmer) with unicode61 remove_diacritics=2
  // Porter was incorrectly stemming PT-BR words (e.g. configuracoes ≠ configuracao).
  // unicode61 with remove_diacritics=2 normalizes accents without language-specific stemming,
  // so "decisao" == "decisão", "configuracao" == "configuração", etc.
  //
  // Procedure for content= FTS5 table rebuild:
  //   1. Drop old virtual table + triggers
  //   2. Create new virtual table with updated tokenizer
  //   3. Recreate triggers
  //   4. Rebuild index from chunks table
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

  // Rebuild from chunks table
  db.exec(`INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');`);

  // Recreate triggers
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
  // P2 Fix: Restore UPDATE trigger (correctly, without write amplification)
  // The v2 trigger was buggy because it reinserted without deleting first on content= tables.
  // Correct pattern for content= FTS5: delete old, insert new.
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
  `);

  // P5: Add dedup_log table for tracking suppressed duplicates
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

  // Add memory_type column to chunks for typed retrieval (Sprint 2)
  db.exec(`
    ALTER TABLE chunks ADD COLUMN memory_type TEXT;
  `);
}
