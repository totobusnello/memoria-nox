// db.ts — STAGED STUB.
// In production this file is the real DB singleton at /root/.openclaw/workspace/tools/nox-mem/src/db.ts.
// The stub here exists ONLY so that reindex.ts compiles in isolation inside the staged-reindex-emergency
// sandbox. DO NOT deploy this stub. On the VPS, leave the real db.ts in place; only copy reindex.ts +
// reindex-errors.ts + __tests__/reindex.no-wipe.test.ts as the SCP payload (see runbook).
import Database from "better-sqlite3";

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db && _db.open) return _db;
  const path = process.env.NOX_DB_PATH || "/tmp/nox-mem-stub.db";
  _db = new Database(path);
  return _db;
}

export function closeDb(): void {
  if (_db && _db.open) {
    _db.close();
    _db = null;
  }
}
