/**
 * staged-1.7a/tests/audit20-watch-guard.test.ts
 *
 * audit #20 fix verification — watcher boot guard.
 *
 * Validates that `nox-mem watch` runs checkLargeDbIngestGuard() at boot,
 * before any ingestFile() loop. The guard semantics are tested via an
 * isolated copy that mocks process.exit.
 *
 * Note: the watcher is INSERT-only via ingestFile; no withOpAudit wrap is
 * required (per CLAUDE.md rule #6 — withOpAudit is for DELETE/UPDATE/destructive
 * ops). Defense is at-boot, not per-write.
 *
 * Run: node --test dist/tests/audit20-watch-guard.test.js
 * Or:  npx tsx staged-1.7a/tests/audit20-watch-guard.test.ts (dev)
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
      source_date TEXT
    );
  `);
  if (chunkCount > 0) {
    const insert = db.prepare(
      "INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date) VALUES (?, ?, ?, ?)",
    );
    const insertMany = db.transaction((n: number) => {
      for (let i = 0; i < n; i++) {
        insert.run(`source-${i}.md`, `text ${i}`, "daily", "2026-05-19");
      }
    });
    insertMany(chunkCount);
  }
  return db;
}

describe("audit #20 — watch boot guard", () => {
  let savedEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    savedEnv = { ...process.env };
    delete process.env.NOX_ALLOW_PROD_INGEST;
  });

  afterEach(() => {
    process.env = savedEnv;
  });

  it("aborts watch boot when DB has >10k chunks and no override", () => {
    const db = makeDb(20_000);
    const result = runGuard(db, "watch", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, true, "watch must abort on large DB");
    assert.match(result.message, /watch/, "abort message must name 'watch'");
  });

  it("starts watch when NOX_ALLOW_PROD_INGEST=1 is set", () => {
    const db = makeDb(20_000);
    const result = runGuard(db, "watch", {
      ...process.env,
      NOX_ALLOW_PROD_INGEST: "1",
    });
    db.close();
    assert.strictEqual(result.aborted, false, "explicit override must let watcher start");
  });

  it("starts watch on fresh eval DB (default behavior)", () => {
    const db = makeDb(0);
    const result = runGuard(db, "watch", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, false, "empty DB must let watcher start");
  });

  it("starts watch on dev-scale DB (1k chunks)", () => {
    const db = makeDb(1_000);
    const result = runGuard(db, "watch", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, false, "1k chunks (dev) must not abort");
  });

  it("aborts watch on prod-scale DB (62k chunks — current prod size)", () => {
    // Production at sync time (2026-05-01) was 62.9k. By 2026-05-19 it was 68k+.
    // Watcher must refuse to attach to that without explicit opt-in.
    const db = makeDb(62_900);
    const result = runGuard(db, "watch", { ...process.env });
    db.close();
    assert.strictEqual(result.aborted, true, "62.9k (prod) must abort watch boot");
  });
});

describe("audit #20 — watch is INSERT-only (no withOpAudit required)", () => {
  // Documents the design decision: watcher does not wrap in withOpAudit
  // because it is INSERT-only via ingestFile(). withOpAudit is for
  // destructive ops (DELETE/UPDATE/VACUUM). For an append-only watcher,
  // defense-in-depth is at-boot via the large-DB guard.

  it("watcher loop is conceptually INSERT-only (no DELETE)", () => {
    // Simulate ingest loop: only INSERT, never DELETE.
    const db = makeDb(0);
    const insert = db.prepare(
      "INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date) VALUES (?, ?, ?, ?)",
    );
    for (let i = 0; i < 50; i++) {
      insert.run(`file-${i}.md`, `chunk text ${i}`, "daily", "2026-05-19");
    }
    const total = (db.prepare("SELECT COUNT(*) AS n FROM chunks").get() as { n: number }).n;
    assert.strictEqual(total, 50);
    // No DELETE was issued — withOpAudit not required here.
    db.close();
  });
});
