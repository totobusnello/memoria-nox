/**
 * observability.test.ts — F10 Phase A unit tests
 *
 * Covers:
 *   - vectorHealth / canaryHealth / recentOpsHealth threshold logic
 *   - snapshotPair caching + delta calculation
 *   - handleObsHealth response shape + indicators
 *   - handleObsRecentOps filter (status IN failed,crashed) + ordering
 *   - parseCanaryLine timestamp + ok/fail heuristic
 *   - handleObsCanaryTail tail size + missing-file graceful handling
 *
 * Cross-link: staged-1.7a/edits/observability.ts
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §"Critérios de aceitação"
 */

import { test, describe, before, after } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import { writeFileSync, mkdtempSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

import {
  vectorHealth,
  canaryHealth,
  recentOpsHealth,
  snapshotPair,
  _resetSnapshotCache,
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
  parseCanaryLine,
} from "../observability.js";

// ── Fixture DB ────────────────────────────────────────────────────────────────

function makeFixtureDb(): Database.Database {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_text TEXT);
    CREATE TABLE kg_entities (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
    CREATE TABLE kg_relations (id INTEGER PRIMARY KEY AUTOINCREMENT, src INTEGER, tgt INTEGER);
    CREATE TABLE ops_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      op_name TEXT NOT NULL,
      started_at INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'started',
      duration_ms INTEGER,
      db_source TEXT NOT NULL DEFAULT 'unknown',
      error_message TEXT
    );
  `);
  return db;
}

function seedChunks(db: Database.Database, n: number): void {
  const stmt = db.prepare("INSERT INTO chunks (chunk_text) VALUES (?)");
  const tx = db.transaction((count: number) => {
    for (let i = 0; i < count; i++) stmt.run(`chunk ${i}`);
  });
  tx(n);
}

// ── Threshold logic ───────────────────────────────────────────────────────────

describe("vectorHealth", () => {
  test("green when embedded == total and orphans == 0", () => {
    assert.equal(vectorHealth(100, 100, 0), "green");
  });
  test("yellow when small gap or few orphans", () => {
    assert.equal(vectorHealth(98, 100, 0), "yellow");
    assert.equal(vectorHealth(100, 100, 3), "yellow");
  });
  test("red when significant gap or many orphans", () => {
    assert.equal(vectorHealth(80, 100, 0), "red");
    assert.equal(vectorHealth(100, 100, 50), "red");
  });
});

describe("canaryHealth", () => {
  test("green when recent (<20min)", () => {
    assert.equal(canaryHealth(5 * 60_000), "green");
  });
  test("yellow when 20-60 min", () => {
    assert.equal(canaryHealth(30 * 60_000), "yellow");
  });
  test("red when 60+ min or missing", () => {
    assert.equal(canaryHealth(90 * 60_000), "red");
    assert.equal(canaryHealth(null), "red");
  });
});

describe("recentOpsHealth", () => {
  test("green at 0", () => assert.equal(recentOpsHealth(0), "green"));
  test("yellow at 1-3", () => {
    assert.equal(recentOpsHealth(1), "yellow");
    assert.equal(recentOpsHealth(3), "yellow");
  });
  test("red at 4+", () => assert.equal(recentOpsHealth(4), "red"));
});

// ── snapshotPair caching ──────────────────────────────────────────────────────

describe("snapshotPair", () => {
  test("first call has no historical (cache empty)", () => {
    _resetSnapshotCache();
    const db = makeFixtureDb();
    seedChunks(db, 100);
    const { current, historical } = snapshotPair(db);
    assert.equal(current.chunks_total, 100);
    assert.equal(historical, null);
  });

  test("second call within TTL still no historical", () => {
    _resetSnapshotCache();
    const db = makeFixtureDb();
    seedChunks(db, 100);
    snapshotPair(db); // primes cache
    seedChunks(db, 5);
    const { current, historical } = snapshotPair(db, 1_000_000);
    assert.equal(current.chunks_total, 105);
    assert.equal(historical, null, "TTL not crossed → no historical yet");
  });

  test("after TTL crossed historical is the prior snapshot", () => {
    _resetSnapshotCache();
    const db = makeFixtureDb();
    seedChunks(db, 100);
    snapshotPair(db, 0); // cache primed with 100
    seedChunks(db, 50);
    // ttl=0 forces every subsequent call to surface the cached snapshot
    const { current, historical } = snapshotPair(db, 0);
    assert.equal(current.chunks_total, 150);
    assert.ok(historical);
    assert.equal(historical!.chunks_total, 100);
  });
});

// ── handleObsHealth ───────────────────────────────────────────────────────────

describe("handleObsHealth", () => {
  test("returns shape with indicators and delta_24h fields", () => {
    _resetSnapshotCache();
    const db = makeFixtureDb();
    seedChunks(db, 42);
    const r = handleObsHealth(db, { canaryLogPath: "/nonexistent/path.log", lastFailedOps24h: 0 });
    assert.equal(r.current.chunks_total, 42);
    assert.ok(r.indicators.vector);
    assert.ok(r.indicators.canary);
    assert.ok(r.indicators.recentOps);
    assert.equal(r.indicators.canary, "red", "missing canary log → red");
    assert.equal(r.indicators.recentOps, "green", "zero failed ops → green");
    assert.ok("chunks" in r.delta_24h);
    assert.equal(r.delta_24h.chunks, null, "no historical → null delta");
  });

  test("counts failed/crashed ops from DB when lastFailedOps24h not provided", () => {
    _resetSnapshotCache();
    const db = makeFixtureDb();
    seedChunks(db, 10);
    const now = Date.now();
    const insert = db.prepare(
      "INSERT INTO ops_audit (op_name, started_at, status, db_source) VALUES (?, ?, ?, ?)",
    );
    insert.run("reindex", now - 60_000, "failed", "main");
    insert.run("vectorize", now - 120_000, "crashed", "main");
    insert.run("backfill", now - 180_000, "success", "main"); // excluded
    const r = handleObsHealth(db, { canaryLogPath: "/nonexistent" });
    assert.equal(r.indicators.recentOps, "yellow", "2 failed → yellow");
  });
});

// ── handleObsRecentOps ────────────────────────────────────────────────────────

describe("handleObsRecentOps", () => {
  test("filters status IN failed/crashed only, DESC order", () => {
    const db = makeFixtureDb();
    const insert = db.prepare(
      "INSERT INTO ops_audit (op_name, started_at, status, db_source, duration_ms, error_message) VALUES (?, ?, ?, ?, ?, ?)",
    );
    const now = Date.now();
    insert.run("a", now - 3000, "success", "main", 100, null);
    insert.run("b", now - 2000, "failed", "main", 200, "boom");
    insert.run("c", now - 1000, "crashed", "entity-eval", 300, "kaboom");
    insert.run("d", now,         "started", "main", null, null);
    const rows = handleObsRecentOps(db, 10);
    assert.equal(rows.length, 2);
    assert.equal(rows[0]!.op_name, "c", "crashed before failed by recency");
    assert.equal(rows[1]!.op_name, "b");
    assert.equal(rows[0]!.db_source, "entity-eval");
  });

  test("clamps n to [1, 50]", () => {
    const db = makeFixtureDb();
    const insert = db.prepare(
      "INSERT INTO ops_audit (op_name, started_at, status) VALUES (?, ?, ?)",
    );
    for (let i = 0; i < 60; i++) insert.run(`op${i}`, Date.now() - i * 1000, "failed");
    assert.equal(handleObsRecentOps(db, 999).length, 50, "upper clamp");
    assert.equal(handleObsRecentOps(db, 0).length, 1, "lower clamp");
  });

  test("returns [] when ops_audit table missing", () => {
    const db = new Database(":memory:");
    assert.deepEqual(handleObsRecentOps(db, 5), []);
  });
});

// ── parseCanaryLine + handleObsCanaryTail ─────────────────────────────────────

describe("parseCanaryLine", () => {
  test("extracts ISO timestamp from bracketed prefix", () => {
    const r = parseCanaryLine("[2026-05-21T14:45:00Z] all 4 invariants OK");
    assert.equal(r.timestamp, "2026-05-21T14:45:00Z");
    assert.equal(r.ok, true);
  });
  test("detects FAIL", () => {
    const r = parseCanaryLine("[2026-05-21T14:45:00Z] FAIL: chunk_count drift detected");
    assert.equal(r.ok, false);
  });
  test("missing timestamp returns null", () => {
    const r = parseCanaryLine("garbage line without timestamp");
    assert.equal(r.timestamp, null);
  });
});

describe("handleObsCanaryTail", () => {
  let tmpDir: string;
  let logPath: string;

  before(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "f10-canary-"));
    logPath = join(tmpDir, "canary.log");
    const lines = [
      "[2026-05-21T13:00:00Z] all 4 invariants OK",
      "[2026-05-21T13:15:00Z] all 4 invariants OK",
      "[2026-05-21T13:30:00Z] all 4 invariants OK",
      "[2026-05-21T13:45:00Z] FAIL: chunk_count drift",
      "[2026-05-21T14:00:00Z] all 4 invariants OK",
    ];
    writeFileSync(logPath, lines.join("\n") + "\n");
  });

  after(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("returns last N lines parsed", () => {
    const r = handleObsCanaryTail(3, { canaryLogPath: logPath });
    assert.equal(r.length, 3);
    assert.equal(r[2]!.timestamp, "2026-05-21T14:00:00Z");
    assert.equal(r[1]!.ok, false, "second-to-last is FAIL");
  });

  test("returns [] on missing file", () => {
    const r = handleObsCanaryTail(3, { canaryLogPath: "/nonexistent/path.log" });
    assert.deepEqual(r, []);
  });

  test("clamps n to [1, 20]", () => {
    const big = handleObsCanaryTail(999, { canaryLogPath: logPath });
    assert.equal(big.length, 5, "only 5 lines in file");
    const zero = handleObsCanaryTail(0, { canaryLogPath: logPath });
    assert.equal(zero.length, 1, "lower clamp = 1");
  });
});
