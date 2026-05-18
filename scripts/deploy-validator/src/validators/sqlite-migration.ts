/**
 * sqlite-migration.ts — T3c: SQLite migration validator
 *
 * Applies migration SQL files against a temporary in-memory SQLite database
 * using the system `sqlite3` CLI. This avoids native module binding issues
 * with better-sqlite3 and more accurately mirrors the production environment
 * (production also uses the sqlite3 CLI for migrations per DEPLOY-WAVE-B.md).
 *
 * Migration order: v10 baseline → v11 → v19 → v20
 * Verification: PRAGMA user_version after each step.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { spawnSync } from "child_process";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MigrationResult {
  type: "sqlite-migration";
  migrationFile: string;
  expectedVersion: number;
  actualVersion: number;
  passed: boolean;
  errorMessage?: string;
  tablesCreated: string[];
  columnsAdded: string[];
  durationMs: number;
}

export interface MigrationSuiteResult {
  type: "sqlite-migration-suite";
  passed: boolean;
  migrations: MigrationResult[];
  finalVersion: number;
  allTables: string[];
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Baseline schema (v10) — mirrors production schema
// ---------------------------------------------------------------------------

const SCHEMA_V10 = `
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS chunks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file     TEXT    NOT NULL,
  chunk_index     INTEGER NOT NULL,
  chunk_text      TEXT    NOT NULL,
  metadata_json   TEXT,
  created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  updated_at      INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  chunk_hash      TEXT,
  importance      REAL    NOT NULL DEFAULT 0.5,
  retention_days  INTEGER,
  pain            REAL    NOT NULL DEFAULT 0.2,
  section         TEXT,
  section_boost   REAL    NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS kg_entities (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL,
  kind        TEXT    NOT NULL,
  summary     TEXT,
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000)
);

CREATE TABLE IF NOT EXISTS kg_relations (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  source_entity_id    INTEGER NOT NULL REFERENCES kg_entities(id),
  target_entity_id    INTEGER NOT NULL REFERENCES kg_entities(id),
  predicate           TEXT    NOT NULL,
  weight              REAL    NOT NULL DEFAULT 1.0,
  chunk_id            INTEGER REFERENCES chunks(id)
  -- Note: created_at + updated_at are added by v19.sql via ALTER TABLE ADD COLUMN
  -- They are NOT in the v10 baseline because v19 would fail with "duplicate column"
);

CREATE TABLE IF NOT EXISTS ops_audit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  op_name     TEXT    NOT NULL,
  status      TEXT    NOT NULL DEFAULT 'started',
  started_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  finished_at INTEGER,
  snapshot_path TEXT,
  error_message TEXT,
  CHECK (status IN ('started', 'success', 'failed', 'crashed'))
);

PRAGMA user_version = 10;
`;

// ---------------------------------------------------------------------------
// SQLite CLI executor
// ---------------------------------------------------------------------------

function execSql(dbPath: string, sql: string): { ok: boolean; output: string; error: string } {
  const result = spawnSync("sqlite3", [dbPath], {
    input: sql,
    encoding: "utf8",
    timeout: 10000,
  });
  return {
    ok: result.status === 0,
    output: (result.stdout ?? "").trim(),
    error: (result.stderr ?? "").trim(),
  };
}

function execSqlFile(dbPath: string, sqlFile: string): { ok: boolean; output: string; error: string } {
  const sql = fs.readFileSync(sqlFile, "utf8");
  return execSql(dbPath, sql);
}

function getUserVersion(dbPath: string): number {
  const r = execSql(dbPath, "PRAGMA user_version;");
  return parseInt(r.output, 10) || 0;
}

function listTables(dbPath: string): string[] {
  const r = execSql(dbPath, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;");
  if (!r.ok || !r.output) return [];
  return r.output.split("\n").map((l) => l.trim()).filter(Boolean);
}

function listColumnsForTable(dbPath: string, table: string): string[] {
  const r = execSql(dbPath, `PRAGMA table_info(${table});`);
  if (!r.ok || !r.output) return [];
  // PRAGMA table_info returns: cid|name|type|notnull|dflt_value|pk
  return r.output.split("\n").map((l) => l.split("|")[1]?.trim() ?? "").filter(Boolean);
}

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

/**
 * Run the migration chain against a temporary file-based SQLite DB.
 * SQL files are resolved from the provided migrationDir.
 */
export function runMigrationSuite(
  migrationDir: string,
  migrations: Array<{ file: string; expectedVersion: number }>
): MigrationSuiteResult {
  const start = Date.now();

  // Create a temp DB file (not in-memory because sqlite3 CLI doesn't support :memory: easily)
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "deploy-validator-sqlite-"));
  const dbPath = path.join(tmpDir, "test.db");

  try {
    // Apply baseline schema
    const baselineResult = execSql(dbPath, SCHEMA_V10);
    if (!baselineResult.ok) {
      return {
        type: "sqlite-migration-suite",
        passed: false,
        migrations: [
          {
            type: "sqlite-migration",
            migrationFile: "(baseline v10)",
            expectedVersion: 10,
            actualVersion: -1,
            passed: false,
            errorMessage: `Baseline schema failed: ${baselineResult.error}`,
            tablesCreated: [],
            columnsAdded: [],
            durationMs: Date.now() - start,
          },
        ],
        finalVersion: -1,
        allTables: [],
        durationMs: Date.now() - start,
      };
    }

    const results: MigrationResult[] = [];

    for (const { file, expectedVersion } of migrations) {
      const result = applyMigration(dbPath, migrationDir, file, expectedVersion);
      results.push(result);
      if (!result.passed) break;
    }

    const finalVersion = getUserVersion(dbPath);
    const allTables = listTables(dbPath);

    return {
      type: "sqlite-migration-suite",
      passed: results.every((r) => r.passed),
      migrations: results,
      finalVersion,
      allTables,
      durationMs: Date.now() - start,
    };
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

function applyMigration(
  dbPath: string,
  dir: string,
  file: string,
  expectedVersion: number
): MigrationResult {
  const start = Date.now();
  const filePath = path.join(dir, file);
  const tablesBefore = listTables(dbPath);

  try {
    if (!fs.existsSync(filePath)) {
      return {
        type: "sqlite-migration",
        migrationFile: file,
        expectedVersion,
        actualVersion: -1,
        passed: false,
        errorMessage: `Cannot read migration file: ${filePath}`,
        tablesCreated: [],
        columnsAdded: [],
        durationMs: Date.now() - start,
      };
    }

    const r = execSqlFile(dbPath, filePath);
    if (!r.ok) {
      return {
        type: "sqlite-migration",
        migrationFile: file,
        expectedVersion,
        actualVersion: getUserVersion(dbPath),
        passed: false,
        errorMessage: `Migration error: ${r.error}`,
        tablesCreated: [],
        columnsAdded: [],
        durationMs: Date.now() - start,
      };
    }

    const actualVersion = getUserVersion(dbPath);
    const tablesAfter = listTables(dbPath);
    const tablesCreated = tablesAfter.filter((t) => !tablesBefore.includes(t));
    const columnsAdded = detectAddedColumns(dbPath, file);
    const passed = actualVersion === expectedVersion;

    return {
      type: "sqlite-migration",
      migrationFile: file,
      expectedVersion,
      actualVersion,
      passed,
      errorMessage: passed
        ? undefined
        : `Expected user_version=${expectedVersion}, got ${actualVersion}`,
      tablesCreated,
      columnsAdded,
      durationMs: Date.now() - start,
    };
  } catch (e) {
    return {
      type: "sqlite-migration",
      migrationFile: file,
      expectedVersion,
      actualVersion: -1,
      passed: false,
      errorMessage: `Unexpected error: ${(e as Error).message}`,
      tablesCreated: [],
      columnsAdded: [],
      durationMs: Date.now() - start,
    };
  }
}

// ---------------------------------------------------------------------------
// Column detection helpers
// ---------------------------------------------------------------------------

function detectAddedColumns(dbPath: string, migrationFile: string): string[] {
  const added: string[] = [];

  if (migrationFile.includes("v19")) {
    try {
      const chunksCols = listColumnsForTable(dbPath, "chunks");
      if (chunksCols.includes("confidence")) added.push("chunks.confidence");
      if (chunksCols.includes("provenance_kind")) added.push("chunks.provenance_kind");

      const kgCols = listColumnsForTable(dbPath, "kg_relations");
      if (kgCols.includes("confidence")) added.push("kg_relations.confidence");
      if (kgCols.includes("superseded_by_relation_id")) added.push("kg_relations.superseded_by_relation_id");
      if (kgCols.includes("extraction_method")) added.push("kg_relations.extraction_method");
    } catch { /* ignore */ }
  }

  return added;
}

// ---------------------------------------------------------------------------
// Convenience: default migration chain for DEPLOY-WAVE-B
// ---------------------------------------------------------------------------

export const DEFAULT_MIGRATION_CHAIN: Array<{ file: string; expectedVersion: number }> = [
  { file: "v11.sql", expectedVersion: 11 },
  { file: "v19.sql", expectedVersion: 19 },
  { file: "v20-viewer-telemetry.sql", expectedVersion: 20 },
];
