/**
 * tests/search-telemetry-schema.test.ts
 *
 * Regression guard for A2 anomaly: search_telemetry INSERT must not silently
 * fail when the deployed schema has more columns than the original 7-column
 * baseline (schema v6). Bug confirmed by Agent F (PR #139): 0 rows in
 * search_telemetry after 700 queries because dist/search.js used positional
 * binding against a schema that now has 21 columns.
 *
 * Test structure:
 *   A. Build full schema (all ALTER TABLE ADD COLUMN layers)
 *   B. Named-column INSERT succeeds and row is retrievable
 *   C. Named-column INSERT is resilient: adding another column afterwards
 *      does NOT break subsequent INSERTs (future-proof guard)
 *   D. Adversarial: old-style positional INSERT fails loudly (documents the bug)
 *   E. NOX_SEARCH_LOG_TEXT opt-in: query_text is NULL when env not set,
 *      and equals the query string when env is set
 *
 * Run: node --test dist/tests/search-telemetry-schema.test.js
 *
 * NOTE: This file is self-contained (no imports from src/) so it can run
 * on any machine with better-sqlite3 available. The INSERT pattern mirrors
 * logTelemetry() in staged-P3/edits/search.ts.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import Database from "better-sqlite3";

// ── Schema builder ────────────────────────────────────────────────────────────
// Mirrors the full sequence of DDL that has been applied on the VPS since v6.
// Order matters: each ALTER TABLE must come after CREATE TABLE.

function buildFullSchema(db: InstanceType<typeof Database>): void {
  // v6 baseline (staged-1.6/edits/db.ts migrateToV6)
  db.exec(`
    CREATE TABLE IF NOT EXISTS search_telemetry (
      id                        INTEGER PRIMARY KEY AUTOINCREMENT,
      ts                        TEXT    NOT NULL DEFAULT (datetime('now')),
      query_hash                TEXT    NOT NULL,
      query_words               INTEGER NOT NULL,
      variants_count            INTEGER NOT NULL DEFAULT 1,
      results_count             INTEGER NOT NULL DEFAULT 0,
      has_semantic              INTEGER NOT NULL DEFAULT 0,
      latency_ms                INTEGER NOT NULL DEFAULT 0,
      expansion_skipped_reason  TEXT
    );
  `);

  // A0 (2026-04-25) — query logging extension, opt-in via NOX_SEARCH_LOG_TEXT=1
  db.exec(`
    ALTER TABLE search_telemetry ADD COLUMN query_text   TEXT    DEFAULT NULL;
    ALTER TABLE search_telemetry ADD COLUMN golden_id    TEXT    DEFAULT NULL;
    ALTER TABLE search_telemetry ADD COLUMN top_chunk_ids TEXT   DEFAULT NULL;
    ALTER TABLE search_telemetry ADD COLUMN top_scores   TEXT    DEFAULT NULL;
  `);

  // E05b (2026-05-06, schema v13) — reason-boost telemetry (CUT D38 but cols remain)
  db.exec(`
    ALTER TABLE search_telemetry ADD COLUMN reason_boost_applied   REAL    DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN reason_relations_used  INTEGER DEFAULT 0;
  `);

  // E13 (2026-05-06, schema v14) — temporal-aware ranking
  db.exec(`
    ALTER TABLE search_telemetry ADD COLUMN was_temporal_query  INTEGER DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN temporal_boost_mode TEXT    DEFAULT 'off';
  `);

  // D01 (2026-05-07, schema v16) — cross-encoder reranker (CUT v1+v2, cols remain)
  db.exec(`
    ALTER TABLE search_telemetry ADD COLUMN reranker_mode              TEXT    DEFAULT 'off';
    ALTER TABLE search_telemetry ADD COLUMN reranker_top_k_in          INTEGER DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN reranker_top_k_out         INTEGER DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN reranker_latency_ms        INTEGER DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN reranker_position_changes  INTEGER DEFAULT 0;
    ALTER TABLE search_telemetry ADD COLUMN reranker_lift_score        REAL    DEFAULT 0;
  `);
}

// ── logTelemetry — mirror of staged-P3/edits/search.ts ───────────────────────
// Reproduced inline to keep the test self-contained. Must stay in sync with
// the source. If this test starts failing, check staged-P3/edits/search.ts.

interface TelemetryExtras {
  query_text?: string | null;
  golden_id?: string | null;
  top_chunk_ids?: string | null;
  top_scores?: string | null;
  reason_boost_applied?: number | null;
  reason_relations_used?: number | null;
  was_temporal_query?: number | null;
  temporal_boost_mode?: string | null;
  reranker_mode?: string | null;
  reranker_top_k_in?: number | null;
  reranker_top_k_out?: number | null;
  reranker_latency_ms?: number | null;
  reranker_position_changes?: number | null;
  reranker_lift_score?: number | null;
}

function logTelemetryInto(
  db: InstanceType<typeof Database>,
  query: string,
  variantsCount: number,
  resultsCount: number,
  hasSemantic: boolean,
  latencyMs: number,
  skipReason?: string,
  extras: TelemetryExtras = {},
  logText = false,
): void {
  const hash = createHash("sha1").update(query).digest("hex").substring(0, 16);
  const words = query.trim().split(/\s+/).filter(Boolean).length;
  const queryText = logText ? (extras.query_text ?? query) : null;

  db.prepare(
    `INSERT INTO search_telemetry (
      query_hash, query_words, variants_count, results_count,
      has_semantic, latency_ms, expansion_skipped_reason,
      query_text, golden_id, top_chunk_ids, top_scores,
      reason_boost_applied, reason_relations_used,
      was_temporal_query, temporal_boost_mode,
      reranker_mode, reranker_top_k_in, reranker_top_k_out,
      reranker_latency_ms, reranker_position_changes, reranker_lift_score
    ) VALUES (
      ?, ?, ?, ?,
      ?, ?, ?,
      ?, ?, ?, ?,
      ?, ?,
      ?, ?,
      ?, ?, ?,
      ?, ?, ?
    )`,
  ).run(
    hash, words, variantsCount, resultsCount,
    hasSemantic ? 1 : 0, latencyMs, skipReason ?? null,
    queryText, extras.golden_id ?? null, extras.top_chunk_ids ?? null, extras.top_scores ?? null,
    extras.reason_boost_applied ?? null, extras.reason_relations_used ?? null,
    extras.was_temporal_query ?? null, extras.temporal_boost_mode ?? null,
    extras.reranker_mode ?? null, extras.reranker_top_k_in ?? null, extras.reranker_top_k_out ?? null,
    extras.reranker_latency_ms ?? null, extras.reranker_position_changes ?? null, extras.reranker_lift_score ?? null,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("search_telemetry schema A2 regression", () => {
  let db: InstanceType<typeof Database>;

  before(() => {
    db = new Database(":memory:");
    buildFullSchema(db);
  });

  after(() => {
    db.close();
  });

  // ── A. Schema inspection ────────────────────────────────────────────────────

  it("A1: schema has exactly 21 columns (7 baseline + 14 added)", () => {
    const cols = db.pragma("table_info(search_telemetry)") as { name: string }[];
    assert.strictEqual(
      cols.length,
      21,
      `expected 21 columns, got ${cols.length}: ${cols.map((c) => c.name).join(", ")}`,
    );
  });

  it("A2: all A0+E05b+E13+D01 columns exist by name", () => {
    const cols = db.pragma("table_info(search_telemetry)") as { name: string }[];
    const names = new Set(cols.map((c) => c.name));

    const expected = [
      // baseline
      "id", "ts", "query_hash", "query_words", "variants_count",
      "results_count", "has_semantic", "latency_ms", "expansion_skipped_reason",
      // A0
      "query_text", "golden_id", "top_chunk_ids", "top_scores",
      // E05b
      "reason_boost_applied", "reason_relations_used",
      // E13
      "was_temporal_query", "temporal_boost_mode",
      // D01
      "reranker_mode", "reranker_top_k_in", "reranker_top_k_out",
      "reranker_latency_ms", "reranker_position_changes", "reranker_lift_score",
    ];

    for (const col of expected) {
      assert.ok(names.has(col), `missing column: ${col}`);
    }
  });

  // ── B. Named-column INSERT succeeds ────────────────────────────────────────

  it("B1: logTelemetry INSERT succeeds on full schema — row appears in SELECT", () => {
    logTelemetryInto(db, "when was schema v12 deployed", 1, 5, true, 940);
    const row = db.prepare("SELECT * FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.ok(row, "no row found after INSERT");
    assert.strictEqual(row["results_count"], 5);
    assert.strictEqual(row["has_semantic"], 1);
    assert.strictEqual(row["latency_ms"], 940);
    assert.strictEqual(row["query_text"], null, "query_text must be NULL when logText=false");
  });

  it("B2: logTelemetry writes was_temporal_query and temporal_boost_mode correctly", () => {
    logTelemetryInto(db, "o que mudou nos últimos 7 dias", 2, 3, true, 1100, undefined, {
      was_temporal_query: 1,
      temporal_boost_mode: "active",
    });
    const row = db.prepare("SELECT * FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["was_temporal_query"], 1);
    assert.strictEqual(row["temporal_boost_mode"], "active");
  });

  it("B3: logTelemetry writes reranker columns as NULL when not supplied", () => {
    logTelemetryInto(db, "dor produção ontem", 1, 8, true, 1240);
    const row = db.prepare("SELECT * FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["reranker_mode"], null);
    assert.strictEqual(row["reranker_top_k_in"], null);
    assert.strictEqual(row["reranker_lift_score"], null);
  });

  it("B4: logTelemetry writes all D01 reranker fields when supplied", () => {
    logTelemetryInto(db, "latência de embedding", 1, 10, true, 384, undefined, {
      reranker_mode: "shadow",
      reranker_top_k_in: 50,
      reranker_top_k_out: 10,
      reranker_latency_ms: 204,
      reranker_position_changes: 3,
      reranker_lift_score: 0.341,
    });
    const row = db.prepare("SELECT * FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["reranker_mode"], "shadow");
    assert.strictEqual(row["reranker_top_k_in"], 50);
    assert.strictEqual(row["reranker_top_k_out"], 10);
    assert.strictEqual(row["reranker_position_changes"], 3);
    assert.ok(Math.abs((row["reranker_lift_score"] as number) - 0.341) < 1e-6, "lift_score mismatch");
  });

  // ── C. Named INSERT is resilient to future additive schema changes ──────────

  it("C1: named INSERT still works after adding a future column to the schema", () => {
    // Simulate a future migration adding a new column
    db.exec(`ALTER TABLE search_telemetry ADD COLUMN future_experiment_score REAL DEFAULT NULL`);

    // The existing logTelemetry INSERT must NOT fail — it doesn't reference the new col
    assert.doesNotThrow(() => {
      logTelemetryInto(db, "query after schema expansion", 1, 4, false, 500);
    });

    const row = db.prepare("SELECT * FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.ok(row, "row must exist");
    assert.strictEqual(row["results_count"], 4);
    // New column should be NULL (SQLite default)
    assert.strictEqual(row["future_experiment_score"], null);
  });

  // ── D. Adversarial: document the old positional INSERT bug ─────────────────

  it("D1: old positional INSERT fails loudly when column count mismatches", () => {
    // The old INSERT (v6 era, 7 columns, positional VALUES):
    //   INSERT INTO search_telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    // With 22 columns in the table (after C1 added future_experiment_score),
    // better-sqlite3 raises "expected 22 bound values, got 8"
    const colCount = (db.pragma("table_info(search_telemetry)") as { name: string }[]).length;
    const positionalPlaceholders = "?, ".repeat(8).slice(0, -2); // 8 = original VALUES cols

    assert.throws(() => {
      db.prepare(`INSERT INTO search_telemetry VALUES (${positionalPlaceholders})`).run(
        null, "now", "aabbccddee001122", 2, 1, 3, 0, 350,
      );
    }, /expected \d+ bound values|column count/i,
      `expected positional INSERT to throw with ${colCount} columns in schema`);
  });

  // ── E. NOX_SEARCH_LOG_TEXT opt-in ─────────────────────────────────────────

  it("E1: query_text is NULL when logText=false (privacy default OFF)", () => {
    logTelemetryInto(db, "salience formula v3", 1, 2, true, 800, undefined, {}, false);
    const row = db.prepare("SELECT query_text FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["query_text"], null);
  });

  it("E2: query_text captures raw query when logText=true (NOX_SEARCH_LOG_TEXT=1)", () => {
    const query = "quais foram os incidents de produção em abril";
    logTelemetryInto(db, query, 1, 3, true, 1020, undefined, {}, true);
    const row = db.prepare("SELECT query_text FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["query_text"], query);
  });

  it("E3: query_text can be overridden via extras.query_text when logText=true", () => {
    // Caller may sanitize the query before storing
    logTelemetryInto(db, "raw query with PII", 1, 1, false, 200, undefined, {
      query_text: "redacted_query_hash_only",
    }, true);
    const row = db.prepare("SELECT query_text FROM search_telemetry ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;
    assert.strictEqual(row["query_text"], "redacted_query_hash_only");
  });

  // ── F. Row count sanity ───────────────────────────────────────────────────

  it("F1: all test INSERTs accumulated — at least 8 rows in table", () => {
    const count = (db.prepare("SELECT COUNT(*) AS n FROM search_telemetry").get() as { n: number }).n;
    assert.ok(count >= 8, `expected at least 8 rows, got ${count}`);
  });
});
