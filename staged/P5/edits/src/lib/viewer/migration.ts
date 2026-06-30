/**
 * T5 — Migration runner helper
 *
 * Reads `migrations/v20-viewer-telemetry.sql` and applies it to a
 * better-sqlite3-compatible Database. Pure helper so tests can run with
 * an in-memory shim and prod uses the real driver.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

export interface SqlExec {
  exec(sql: string): void;
  prepare(sql: string): { all(...args: unknown[]): unknown[]; get(...args: unknown[]): unknown };
}

export interface MigrationResult {
  applied: boolean;
  /** user_version after migration. */
  user_version: number;
  /** True if tables / indexes were already present (idempotent run). */
  idempotent_skip: boolean;
}

export function loadMigrationSql(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  // Try multiple candidate locations:
  //  - source layout: edits/src/lib/viewer -> ../../../migrations/...
  //  - compiled layout (no edits in path): dist/src/lib/viewer -> ../../../../edits/migrations/...
  const candidates = [
    join(here, "..", "..", "..", "..", "migrations", "v20-viewer-telemetry.sql"),
    join(here, "..", "..", "..", "..", "edits", "migrations", "v20-viewer-telemetry.sql"),
    join(here, "..", "..", "..", "migrations", "v20-viewer-telemetry.sql"),
    // Fallback: walk up looking for `migrations/v20-...` next to a package.json
    findUpwards(here, "migrations/v20-viewer-telemetry.sql"),
  ].filter(Boolean) as string[];
  for (const p of candidates) {
    if (existsSync(p)) return readFileSync(p, "utf8");
  }
  throw new Error(
    `v20-viewer-telemetry.sql not found; searched: ${candidates.join(", ")}`
  );
}

function findUpwards(start: string, rel: string): string | null {
  let cur = resolve(start);
  for (let i = 0; i < 8; i += 1) {
    const candidate = join(cur, rel);
    if (existsSync(candidate)) return candidate;
    const editsCandidate = join(cur, "edits", rel);
    if (existsSync(editsCandidate)) return editsCandidate;
    const next = dirname(cur);
    if (next === cur) break;
    cur = next;
  }
  return null;
}

export function applyMigration(db: SqlExec): MigrationResult {
  const sql = loadMigrationSql();
  // Detect if already applied by querying sqlite_master.
  const present = (db.prepare(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='viewer_telemetry'"
  ).get() as { name?: string } | undefined)?.name;
  db.exec(sql);
  const versionRow = db.prepare("PRAGMA user_version").get() as
    | { user_version?: number }
    | undefined;
  return {
    applied: true,
    user_version: versionRow?.user_version ?? 0,
    idempotent_skip: Boolean(present),
  };
}
