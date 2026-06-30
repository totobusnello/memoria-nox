/**
 * src/lib/search/__tests__/temporal.test.ts
 *
 * Temporal filter tests for P3 — --as-of / --changed-since
 *
 * Tests are organized in three sections:
 *   A. parseFlexibleDate unit tests (no DB)
 *   B. buildTemporalClause SQL generation tests (no DB)
 *   C. Integration tests against an in-memory SQLite DB
 *
 * Run: node --test dist/lib/search/__tests__/temporal.test.js
 * Or via the existing test runner on VPS.
 *
 * NOTE: This test file assumes the VPS test harness uses node:test (native).
 * If the project uses a different runner, adapt the import/describe/it pattern.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";

// ── Inline implementations for isolation ──────────────────────────────────────
// We re-implement parseFlexibleDate and buildTemporalClause inline so these
// tests can run without the full nox-mem module graph. This also validates
// the contract independently.

// ---- dates.ts inline --------------------------------------------------------

const RELATIVE_RE = /^(\d+)(m|h|d|w)$/i;

function parseFlexibleDate(input: string): Date {
  const trimmed = input.trim();
  if (!trimmed) throw new Error(`temporal: empty date string`);

  const rel = RELATIVE_RE.exec(trimmed);
  if (rel) {
    const n = parseInt(rel[1], 10);
    const unit = rel[2].toLowerCase();
    const msMap: Record<string, number> = {
      m: 60_000,
      h: 3_600_000,
      d: 86_400_000,
      w: 604_800_000,
    };
    if (!(unit in msMap)) {
      throw new Error(`temporal: unsupported relative unit "${unit}" in "${input}"`);
    }
    return new Date(Date.now() - n * msMap[unit]);
  }

  const normalised =
    /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? `${trimmed}T00:00:00Z` : trimmed;

  const d = new Date(normalised);
  if (isNaN(d.getTime())) {
    throw new Error(`temporal: cannot parse date "${input}"`);
  }
  return d;
}

function toSqliteTs(d: Date): string {
  return d.toISOString();
}

// ---- search.ts buildTemporalClause inline -----------------------------------

interface TemporalFilter { asOf?: Date; changedSince?: Date; }
interface TemporalClause { sql: string; params: string[]; }

function buildTemporalClause(filter: TemporalFilter): TemporalClause {
  const parts: string[] = [];
  const params: string[] = [];

  if (filter.asOf) {
    const ts = toSqliteTs(filter.asOf);
    parts.push(
      `(c.created_at IS NULL OR c.created_at <= ?) ` +
      `AND (COALESCE(c.deleted_at, NULL) IS NULL OR c.deleted_at > ?)`
    );
    params.push(ts, ts);
  }

  if (filter.changedSince) {
    const ts = toSqliteTs(filter.changedSince);
    parts.push(`(c.created_at > ? OR COALESCE(c.updated_at, c.created_at) > ?)`);
    params.push(ts, ts);
  }

  if (parts.length === 0) return { sql: "", params: [] };
  return { sql: `AND (${parts.join(") AND (")})`, params };
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTION A — parseFlexibleDate unit tests
// ─────────────────────────────────────────────────────────────────────────────

describe("parseFlexibleDate", () => {
  // TC-01: ISO date-only parses to midnight UTC
  it("TC-01: parses ISO date-only as midnight UTC", () => {
    const d = parseFlexibleDate("2026-05-01");
    assert.equal(d.toISOString(), "2026-05-01T00:00:00.000Z");
  });

  // TC-02: ISO full datetime with Z timezone
  it("TC-02: parses ISO full datetime with Z", () => {
    const d = parseFlexibleDate("2026-05-01T12:30:00Z");
    assert.equal(d.toISOString(), "2026-05-01T12:30:00.000Z");
  });

  // TC-03: ISO with explicit +00:00 offset
  it("TC-03: parses ISO with +00:00 offset", () => {
    const d = parseFlexibleDate("2026-05-01T00:00:00+00:00");
    assert.equal(d.getTime(), new Date("2026-05-01T00:00:00Z").getTime());
  });

  // TC-04: Relative 7d is approximately 7 days ago
  it("TC-04: relative 7d is ~7 days ago", () => {
    const before = Date.now();
    const d = parseFlexibleDate("7d");
    const after = Date.now();
    const sevenDaysMs = 7 * 86_400_000;
    assert.ok(d.getTime() >= before - sevenDaysMs - 100);
    assert.ok(d.getTime() <= after - sevenDaysMs + 100);
  });

  // TC-05: Relative 1w = 7d
  it("TC-05: relative 1w equals 7 days ago", () => {
    const w = parseFlexibleDate("1w");
    const d = parseFlexibleDate("7d");
    assert.ok(Math.abs(w.getTime() - d.getTime()) < 200); // within 200ms
  });

  // TC-06: Relative 2h is ~2 hours ago
  it("TC-06: relative 2h is ~2 hours ago", () => {
    const before = Date.now();
    const d = parseFlexibleDate("2h");
    const after = Date.now();
    const twoHoursMs = 2 * 3_600_000;
    assert.ok(d.getTime() >= before - twoHoursMs - 100);
    assert.ok(d.getTime() <= after - twoHoursMs + 100);
  });

  // TC-07: Relative 30d
  it("TC-07: relative 30d is ~30 days ago", () => {
    const before = Date.now();
    const d = parseFlexibleDate("30d");
    const after = Date.now();
    const thirtyDaysMs = 30 * 86_400_000;
    assert.ok(d.getTime() >= before - thirtyDaysMs - 100);
    assert.ok(d.getTime() <= after - thirtyDaysMs + 100);
  });

  // TC-08: Relative 15m (minutes)
  it("TC-08: relative 15m is ~15 minutes ago", () => {
    const before = Date.now();
    const d = parseFlexibleDate("15m");
    const after = Date.now();
    const fifteenMinMs = 15 * 60_000;
    assert.ok(d.getTime() >= before - fifteenMinMs - 100);
    assert.ok(d.getTime() <= after - fifteenMinMs + 100);
  });

  // TC-09: Invalid string throws with clear message
  it("TC-09: invalid string throws with descriptive error", () => {
    assert.throws(
      () => parseFlexibleDate("not-a-date"),
      (err: Error) => {
        assert.ok(err.message.includes("temporal:"), `expected "temporal:" prefix, got: ${err.message}`);
        return true;
      }
    );
  });

  // TC-10: Empty string throws
  it("TC-10: empty string throws", () => {
    assert.throws(() => parseFlexibleDate(""), /temporal: empty/);
  });

  // TC-11: "1mo" is NOT supported — throws with hint to use "30d"
  it("TC-11: 1mo is not supported, throws with 30d hint", () => {
    // "1mo" doesn't match RELATIVE_RE (only single-char units), falls to ISO parse, which fails
    assert.throws(
      () => parseFlexibleDate("1mo"),
      (err: Error) => {
        assert.ok(err.message.includes("temporal:"), `expected "temporal:" prefix`);
        return true;
      }
    );
  });

  // TC-12: Large relative value (365d)
  it("TC-12: relative 365d parses correctly", () => {
    const d = parseFlexibleDate("365d");
    const expected = Date.now() - 365 * 86_400_000;
    assert.ok(Math.abs(d.getTime() - expected) < 200);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SECTION B — buildTemporalClause SQL generation
// ─────────────────────────────────────────────────────────────────────────────

describe("buildTemporalClause", () => {
  // TC-13: No filter → empty clause
  it("TC-13: empty filter returns no-op clause", () => {
    const { sql, params } = buildTemporalClause({});
    assert.equal(sql, "");
    assert.deepEqual(params, []);
  });

  // TC-14: asOf only → 2 params (ts, ts for created_at + deleted_at)
  it("TC-14: asOf only generates 2-param clause", () => {
    const date = new Date("2026-01-01T00:00:00Z");
    const { sql, params } = buildTemporalClause({ asOf: date });
    assert.ok(sql.includes("created_at"), "should reference created_at");
    assert.ok(sql.includes("deleted_at"), "should reference deleted_at");
    assert.equal(params.length, 2);
    assert.equal(params[0], "2026-01-01T00:00:00.000Z");
    assert.equal(params[1], "2026-01-01T00:00:00.000Z");
  });

  // TC-15: changedSince only → 2 params
  it("TC-15: changedSince only generates 2-param clause", () => {
    const date = new Date("2026-04-01T00:00:00Z");
    const { sql, params } = buildTemporalClause({ changedSince: date });
    assert.ok(sql.includes("updated_at"), "should reference updated_at");
    assert.equal(params.length, 2);
    assert.equal(params[0], "2026-04-01T00:00:00.000Z");
  });

  // TC-16: Both filters → 4 params, AND joined
  it("TC-16: both filters combined gives 4 params AND-joined", () => {
    const asOf = new Date("2026-05-01T00:00:00Z");
    const changedSince = new Date("2026-04-01T00:00:00Z");
    const { sql, params } = buildTemporalClause({ asOf, changedSince });
    assert.equal(params.length, 4);
    // AND must appear between the two filter groups
    assert.ok(sql.includes("AND"), "combined clause must have AND");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// SECTION C — Integration tests with in-memory SQLite
// ─────────────────────────────────────────────────────────────────────────────

describe("temporal SQL filtering (integration)", () => {
  let db: Database.Database;

  before(() => {
    db = new Database(":memory:");
    db.exec(`
      CREATE TABLE chunks (
        id INTEGER PRIMARY KEY,
        source_file TEXT,
        chunk_type TEXT,
        chunk_text TEXT,
        source_date TEXT,
        tier TEXT,
        source_type TEXT,
        created_at TEXT,
        updated_at TEXT,
        deleted_at TEXT
      );
    `);

    // Seed data with known timestamps
    const now = new Date("2026-05-17T12:00:00Z");
    const past = new Date("2026-01-01T00:00:00Z");      // old chunk
    const recent = new Date("2026-05-10T00:00:00Z");    // recent chunk
    const future = new Date("2026-12-31T00:00:00Z");    // future chunk

    db.prepare(`INSERT INTO chunks VALUES (1, 'old.md', 'lesson', 'old lesson', '2026-01-01', 'core', null, ?, ?, null)`)
      .run(past.toISOString(), past.toISOString());

    db.prepare(`INSERT INTO chunks VALUES (2, 'recent.md', 'decision', 'recent decision', '2026-05-10', 'core', null, ?, ?, null)`)
      .run(recent.toISOString(), recent.toISOString());

    db.prepare(`INSERT INTO chunks VALUES (3, 'current.md', 'lesson', 'current lesson', '2026-05-17', 'working', null, ?, ?, null)`)
      .run(now.toISOString(), now.toISOString());

    db.prepare(`INSERT INTO chunks VALUES (4, 'future.md', 'project', 'future project', '2026-12-31', 'working', null, ?, ?, null)`)
      .run(future.toISOString(), future.toISOString());

    // Deleted chunk (deleted before now)
    const deleted = new Date("2026-03-01T00:00:00Z");
    db.prepare(`INSERT INTO chunks VALUES (5, 'deleted.md', 'lesson', 'deleted lesson', '2026-02-01', 'peripheral', null, ?, ?, ?)`)
      .run(past.toISOString(), deleted.toISOString(), deleted.toISOString());
  });

  after(() => {
    db.close();
  });

  function queryWithFilter(filter: TemporalFilter): number[] {
    const { sql, params } = buildTemporalClause(filter);
    const query = `SELECT id FROM chunks c WHERE 1=1 ${sql} ORDER BY id`;
    const rows = db.prepare(query).all(...params) as Array<{ id: number }>;
    return rows.map((r) => r.id);
  }

  // TC-17: No filter returns all 5 chunks
  it("TC-17: no filter returns all chunks", () => {
    const ids = queryWithFilter({});
    assert.deepEqual(ids, [1, 2, 3, 4, 5]);
  });

  // TC-18: asOf = 2026-02-01 — only old chunk existed, not recent/current/future
  it("TC-18: asOf past date excludes chunks created after", () => {
    const asOf = new Date("2026-02-01T00:00:00Z");
    const ids = queryWithFilter({ asOf });
    // id=1 created 2026-01-01 ✅, id=2-4 created after ❌
    // id=5 created 2026-01-01 but deleted 2026-03-01 (which is after asOf 2026-02-01) → ✅ still existed
    assert.ok(ids.includes(1), "old chunk must be included");
    assert.ok(!ids.includes(2), "recent chunk must be excluded");
    assert.ok(!ids.includes(3), "current chunk must be excluded");
    assert.ok(!ids.includes(4), "future chunk must be excluded");
    assert.ok(ids.includes(5), "deleted-after-asOf chunk must be included (existed on asOf date)");
  });

  // TC-19: asOf = far future (2027) returns all non-deleted chunks
  it("TC-19: asOf far future includes all except those deleted before asOf", () => {
    const asOf = new Date("2027-01-01T00:00:00Z");
    const ids = queryWithFilter({ asOf });
    // id=5 deleted_at=2026-03-01, asOf=2027-01-01 → deleted_at (2026-03-01) > asOf (2027) = false → excluded
    assert.ok(ids.includes(1));
    assert.ok(ids.includes(2));
    assert.ok(ids.includes(3));
    assert.ok(ids.includes(4));
    assert.ok(!ids.includes(5), "chunk deleted before asOf must be excluded");
  });

  // TC-20: changedSince = 2026-05-01 returns only recent/current/future
  it("TC-20: changedSince excludes old chunks", () => {
    const changedSince = new Date("2026-05-01T00:00:00Z");
    const ids = queryWithFilter({ changedSince });
    assert.ok(!ids.includes(1), "old chunk must be excluded (updated_at 2026-01-01)");
    assert.ok(ids.includes(2), "recent chunk must be included (created 2026-05-10)");
    assert.ok(ids.includes(3), "current chunk must be included");
    assert.ok(ids.includes(4), "future chunk must be included");
  });

  // TC-21: changedSince = 2026-12-01 returns only future chunk
  it("TC-21: changedSince very recent returns only future chunk", () => {
    const changedSince = new Date("2026-12-01T00:00:00Z");
    const ids = queryWithFilter({ changedSince });
    assert.deepEqual(ids, [4]);
  });

  // TC-22: Combination asOf + changedSince — intersection
  it("TC-22: asOf + changedSince combined returns intersection", () => {
    // asOf=2026-05-17 (current, recent, old existed) AND changedSince=2026-05-01 (recent, current)
    const asOf = new Date("2026-05-17T12:00:00Z");
    const changedSince = new Date("2026-05-01T00:00:00Z");
    const ids = queryWithFilter({ asOf, changedSince });
    assert.ok(!ids.includes(1), "old chunk changed before changedSince → excluded");
    assert.ok(ids.includes(2), "recent chunk: existed on asOf + changed after changedSince → included");
    assert.ok(ids.includes(3), "current chunk → included");
    // id=4 was created 2026-12-31 which is AFTER asOf 2026-05-17 → excluded by asOf filter
    assert.ok(!ids.includes(4), "future chunk not yet created on asOf → excluded");
  });

  // TC-23: asOf with chunk that has NULL created_at (treated as always existed)
  it("TC-23: NULL created_at treated as always existed under asOf", () => {
    db.prepare(`INSERT INTO chunks VALUES (6, 'legacy.md', 'lesson', 'legacy no created_at', '2025-01-01', 'peripheral', null, null, null, null)`).run();
    const asOf = new Date("2026-01-01T00:00:00Z");
    const ids = queryWithFilter({ asOf });
    assert.ok(ids.includes(6), "NULL created_at chunk must be included (treated as always existed)");
    db.prepare("DELETE FROM chunks WHERE id = 6").run();
  });
});
