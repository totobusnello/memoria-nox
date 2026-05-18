import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { loadMigrationSql, applyMigration, type SqlExec } from "../migration.js";

/**
 * Minimal in-memory SQLite shim. We don't depend on better-sqlite3 in tests
 * (would be an extra dep). The shim just stores SQL strings and answers
 * the limited queries `applyMigration` issues.
 */
function makeShim(): SqlExec & {
  executed: string[];
  tables: Set<string>;
  user_version: number;
} {
  const executed: string[] = [];
  const tables = new Set<string>();
  let user_version = 0;

  const shim = {
    executed,
    tables,
    user_version,
    exec(sql: string) {
      executed.push(sql);
      // Detect CREATE TABLE
      const m = /CREATE TABLE IF NOT EXISTS\s+(\w+)/gi;
      let match: RegExpExecArray | null;
      while ((match = m.exec(sql)) !== null) {
        tables.add(match[1]!);
      }
      const versionMatch = /PRAGMA user_version\s*=\s*(\d+)/i.exec(sql);
      if (versionMatch) {
        shim.user_version = Number(versionMatch[1]);
      }
    },
    prepare(sql: string) {
      return {
        all() {
          return [];
        },
        get(..._args: unknown[]) {
          if (sql.includes("PRAGMA user_version")) {
            return { user_version: shim.user_version };
          }
          if (sql.includes("FROM sqlite_master")) {
            return tables.has("viewer_telemetry")
              ? { name: "viewer_telemetry" }
              : undefined;
          }
          return undefined;
        },
      };
    },
  };
  return shim;
}

describe("T5 — migration v20-viewer-telemetry", () => {
  it("SQL file is readable + non-empty", () => {
    const sql = loadMigrationSql();
    assert.ok(sql.length > 0);
    assert.match(sql, /viewer_telemetry/);
  });

  it("SQL contains required columns", () => {
    const sql = loadMigrationSql();
    for (const col of [
      "client_id",
      "ts_start",
      "ts_last_event",
      "ts_end",
      "events_consumed",
      "events_dropped",
    ]) {
      assert.match(sql, new RegExp(col));
    }
  });

  it("Bumps user_version to 20", () => {
    const db = makeShim();
    const r = applyMigration(db);
    assert.equal(r.user_version, 20);
  });

  it("First run creates viewer_telemetry table", () => {
    const db = makeShim();
    applyMigration(db);
    assert.ok(db.tables.has("viewer_telemetry"));
  });

  it("Second run is idempotent (table already present detected)", () => {
    const db = makeShim();
    applyMigration(db);
    const r2 = applyMigration(db);
    assert.equal(r2.idempotent_skip, true);
  });
});
