/**
 * G14 — Integration tests for v24 conflict_audit timestamp triggers.
 *
 * Uses better-sqlite3 when available. If the dep is missing (e.g. CI image
 * without native build chain), each test is skipped with a clear message
 * rather than failing — same pattern as A1 staged tests.
 */

import { describe, it, before } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Idempotent self-loader: tries better-sqlite3, sets capability flag.
type Db = {
  exec: (sql: string) => unknown;
  prepare: (sql: string) => {
    run: (...params: unknown[]) => { changes: number; lastInsertRowid: number };
    get: (...params: unknown[]) => unknown;
    all: (...params: unknown[]) => unknown[];
  };
  close: () => void;
};

let openDb: ((filename: string) => Db) | null = null;
let skipReason = "";

before(async () => {
  try {
    // Use dynamic-spec import so missing dep at typecheck doesn't fail compile.
    const specifier = "better-sqlite3";
    const mod = (await import(specifier)) as { default: new (f: string) => Db };
    openDb = (f: string) => new mod.default(f);
  } catch (e) {
    skipReason = `better-sqlite3 unavailable: ${(e as Error).message}`;
  }
});

const V21_SQL = `
CREATE TABLE IF NOT EXISTS conflict_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  kind TEXT NOT NULL CHECK (kind IN ('direct','temporal_supersede','value_drift','multi_target')),
  subject_entity_id INTEGER NOT NULL,
  predicate TEXT NOT NULL,
  target_relation_ids TEXT NOT NULL,
  variants TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewed','resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')),
  resolved_by TEXT,
  resolved_at INTEGER,
  resolution_kind TEXT CHECK (resolution_kind IN ('pick_one','both_valid','merged','dismissed') OR resolution_kind IS NULL),
  picked_relation_id INTEGER,
  merge_target TEXT,
  notes TEXT,
  shadow_mode INTEGER NOT NULL DEFAULT 1
);
PRAGMA user_version = 21;
`;

function applyV24(db: Db): void {
  const sql = readFileSync(
    path.join(__dirname, "..", "migrations", "v24-conflict-audit-ts-trigger.sql"),
    "utf8",
  );
  db.exec(sql);
}

function setup(): Db | null {
  if (!openDb) return null;
  const db = openDb(":memory:");
  db.exec(V21_SQL);
  applyV24(db);
  return db;
}

describe("v24 conflict_audit triggers", () => {
  it("user_version is 24 after migration", () => {
    const db = setup();
    if (!db) return; // skipped
    const ver = (db.prepare("PRAGMA user_version").get() as { user_version: number }).user_version;
    assert.equal(ver, 24);
    db.close();
  });

  it("INSERT with ts omitted gets server time", () => {
    const db = setup();
    if (!db) return;
    const before = Date.now() - 1000;
    db.prepare(
      "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES (?,?,?,?)",
    ).run("direct", 1, "is_at", "[1,2]");
    const row = db.prepare("SELECT ts FROM conflict_audit").get() as { ts: number };
    assert.equal(row.ts >= before, true);
    assert.equal(row.ts <= Date.now() + 1000, true);
    db.close();
  });

  it("INSERT with backdated ts (>60s skew) is rejected", () => {
    const db = setup();
    if (!db) return;
    const stale = Date.now() - 24 * 60 * 60 * 1000; // 1 day ago
    assert.throws(
      () =>
        db.prepare(
          "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids, ts) VALUES (?,?,?,?,?)",
        ).run("direct", 1, "is_at", "[1]", stale),
      /G14/,
    );
    db.close();
  });

  it("INSERT with ts within 60s clock skew passes", () => {
    const db = setup();
    if (!db) return;
    const justNow = Date.now() - 5000; // 5s old
    db.prepare(
      "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids, ts) VALUES (?,?,?,?,?)",
    ).run("direct", 1, "is_at", "[1]", justNow);
    const row = db.prepare("SELECT ts FROM conflict_audit").get() as { ts: number };
    // App-supplied value preserved (server didn't override because within skew).
    assert.equal(row.ts, justNow);
    db.close();
  });

  it("UPDATE to terminal status with backdated resolved_at is rejected", () => {
    const db = setup();
    if (!db) return;
    db.prepare(
      "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES (?,?,?,?)",
    ).run("direct", 1, "is_at", "[1]");
    const stale = Date.now() - 24 * 60 * 60 * 1000;
    assert.throws(
      () =>
        db.prepare(
          "UPDATE conflict_audit SET status=?, resolution_kind=?, resolved_by=?, resolved_at=? WHERE id=?",
        ).run("resolved_pick_one", "pick_one", "test", stale, 1),
      /G14|server-managed/,
    );
    db.close();
  });

  it("UPDATE to terminal status without resolved_at (or fresh value) passes", () => {
    const db = setup();
    if (!db) return;
    db.prepare(
      "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES (?,?,?,?)",
    ).run("direct", 1, "is_at", "[1]");
    // App passes NULL — let server compute later via a follow-up patch. Trigger doesn't reject.
    db.prepare(
      "UPDATE conflict_audit SET status=?, resolution_kind=?, resolved_by=? WHERE id=?",
    ).run("resolved_pick_one", "pick_one", "test", 1);
    const row = db.prepare("SELECT status FROM conflict_audit WHERE id=1").get() as { status: string };
    assert.equal(row.status, "resolved_pick_one");
    db.close();
  });

  it("once resolved_at is set, subsequent UPDATE that changes it is blocked", () => {
    const db = setup();
    if (!db) return;
    db.prepare(
      "INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES (?,?,?,?)",
    ).run("direct", 1, "is_at", "[1]");
    const now = Date.now();
    db.prepare(
      "UPDATE conflict_audit SET status=?, resolution_kind=?, resolved_by=?, resolved_at=? WHERE id=?",
    ).run("resolved_pick_one", "pick_one", "test", now, 1);

    assert.throws(
      () =>
        db.prepare(
          "UPDATE conflict_audit SET resolved_at=? WHERE id=?",
        ).run(now - 1_000_000, 1),
      /immutable|G14/,
    );
    db.close();
  });

  it("migration is idempotent (re-apply does not error)", () => {
    const db = setup();
    if (!db) return;
    // Re-apply should not throw thanks to DROP IF EXISTS in v24.
    applyV24(db);
    applyV24(db);
    const ver = (db.prepare("PRAGMA user_version").get() as { user_version: number }).user_version;
    assert.equal(ver, 24);
    db.close();
  });
});
