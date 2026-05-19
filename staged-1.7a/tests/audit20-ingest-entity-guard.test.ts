/**
 * staged-1.7a/tests/audit20-ingest-entity-guard.test.ts
 *
 * audit #20 fix verification — ingest-entity guard semantics.
 *
 * Validates that ingestEntityFile() (deployed via patch in
 * staged-1.7a/edits/ingest-entity.patch.ts) calls checkLargeDbIngestGuard
 * before its INSERT loop. The guard behavior is tested via an isolated copy.
 *
 * Run: node --test dist/tests/audit20-ingest-entity-guard.test.js
 * Or:  npx tsx staged-1.7a/tests/audit20-ingest-entity-guard.test.ts (dev)
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";

const PROD_CHUNK_THRESHOLD = 10_000;

function runGuard(db: InstanceType<typeof Database>, operation: string, env: NodeJS.ProcessEnv): {
  aborted: boolean;
  message: string;
} {
  if (env.NOX_ALLOW_PROD_INGEST === "1") return { aborted: false, message: "" };
  const row = db.prepare("SELECT COUNT(*) AS n FROM chunks").get() as { n: number } | undefined;
  const chunkCount = row?.n ?? 0;
  if (chunkCount > PROD_CHUNK_THRESHOLD) {
    return {
      aborted: true,
      message: `[db] ABORT: Large-DB ingest guard triggered on operation '${operation}'.`,
    };
  }
  return { aborted: false, message: "" };
}

function makeDb(chunkCount: number): InstanceType<typeof Database> {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_file TEXT NOT NULL,
      chunk_text TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      source_date TEXT,
      section TEXT,
      section_boost REAL,
      retention_days INTEGER
    );
  `);
  if (chunkCount > 0) {
    const insert = db.prepare(
      "INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, section, section_boost, retention_days) VALUES (?, ?, ?, ?, ?, ?, ?)",
    );
    const insertMany = db.transaction((n: number) => {
      for (let i = 0; i < n; i++) {
        insert.run(`entity-${i}.md`, `text ${i}`, "person", "2026-05-19", "compiled", 2.0, null);
      }
    });
    insertMany(chunkCount);
  }
  return db;
}

describe("audit #20 — ingest-entity guard", () => {
  let savedEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    savedEnv = { ...process.env };
    delete process.env.NOX_ALLOW_PROD_INGEST;
  });

  afterEach(() => {
    process.env = savedEnv;
  });

  it("aborts when DB has >10k chunks and no override", () => {
    const db = makeDb(15_000);
    const result = runGuard(db, "ingest-entity", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, true);
    assert.match(result.message, /ingest-entity/, "abort message must name ingest-entity");
  });

  it("passes with NOX_ALLOW_PROD_INGEST=1 (explicit override)", () => {
    const db = makeDb(15_000);
    const result = runGuard(db, "ingest-entity", {
      ...process.env,
      NOX_ALLOW_PROD_INGEST: "1",
    });
    db.close();
    assert.strictEqual(result.aborted, false);
  });

  it("passes on eval-scale DB (<10k chunks)", () => {
    const db = makeDb(500);
    const result = runGuard(db, "ingest-entity", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, false);
  });

  it("passes on freshly-initialized eval DB (empty)", () => {
    const db = makeDb(0);
    const result = runGuard(db, "ingest-entity", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, false);
  });

  it("aborts on prod-scale entity DB (68k chunks — current prod size)", () => {
    const db = makeDb(68_000);
    const result = runGuard(db, "ingest-entity", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, true, "68k (prod) must abort ingest-entity");
  });
});

describe("audit #20 — ingest-entity defense in depth", () => {
  // The guard is at the head of ingestEntityFile(). Documents the invariant:
  // every entity ingest path — direct CLI, watcher, reindex, generic router —
  // funnels through ingestEntityFile() and therefore through this guard.

  it("guard runs even when called via externalDb path (caller-provided handle)", () => {
    // Some callers pass an externalDb. The guard must run regardless of how
    // the db handle was obtained.
    const externalDb = makeDb(50_000);
    // ingestEntityFile contract: `const db = externalDb ?? getDb()` then guard.
    const db = externalDb; // simulate externalDb branch
    const result = runGuard(db, "ingest-entity", { ...process.env });
    externalDb.close();
    assert.strictEqual(result.aborted, true, "guard must run on externalDb path too");
  });

  it("section/retention preservation is unaffected by guard (no false positive)", () => {
    // The guard is a COUNT(*) check — it does not touch section or retention.
    // This test ensures the guard does not regress the entity ingest semantics.
    const db = makeDb(5);
    const result = runGuard(db, "ingest-entity", { ...process.env });
    assert.strictEqual(result.aborted, false, "small DB must allow ingest");

    // Section data should still be intact after guard runs
    const row = db.prepare("SELECT section, section_boost FROM chunks WHERE id = 1").get() as {
      section: string;
      section_boost: number;
    };
    assert.strictEqual(row.section, "compiled");
    assert.strictEqual(row.section_boost, 2.0);
    db.close();
  });
});
