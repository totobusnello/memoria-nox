/**
 * T12 — End-to-end integration tests (12 tests).
 *
 * Scenarios:
 *   1. Ingest chunks with various provenance kinds
 *   2. Mark some canonical, some refuted, some stale
 *   3. Run search with min_confidence filter
 *   4. Verify ranking integration (gated)
 *   5. Verify telemetry slice reflects state
 *   6. Verify audit trail
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { MockDb } from "../db-shim.js";
import { resolveConfig } from "../config.js";
import { applyConfidence } from "../write-hooks.js";
import { markChunk, supersedeChunk } from "../mark.js";
import { applyConfidenceRanking } from "../ranking.js";
import { filterByConfidence } from "../search-filter.js";
import { computeConfidenceHealth } from "../../../api/health-confidence.js";

function setupCorpus(): MockDb {
  const db = new MockDb();
  // Mix of provenance kinds
  const seeds: {
    id: number;
    confidence: number;
    provenance_kind: string | null;
    pain?: number;
  }[] = [
    { id: 1, confidence: 0.95, provenance_kind: "observed", pain: 0.5 },
    { id: 2, confidence: 0.9, provenance_kind: "declared", pain: 0.3 },
    { id: 3, confidence: 0.65, provenance_kind: "inferred", pain: 0.2 },
    { id: 4, confidence: 0.75, provenance_kind: "derived", pain: 0.2 },
    { id: 5, confidence: 0.8, provenance_kind: null, pain: 0.2 },
    { id: 6, confidence: 0.5, provenance_kind: "inferred", pain: 1.0 }, // prod outage
    { id: 7, confidence: 0.2, provenance_kind: "derived", pain: 0.1 }, // weak
  ];
  for (const s of seeds) db.seedChunk(s);
  return db;
}

test("T12.1 ingest with write-hooks sets correct defaults per source", () => {
  const cfg = resolveConfig();
  const observed = applyConfidence({}, "entity-timeline", cfg);
  const inferred = applyConfidence({}, "kg-extract", cfg);
  const derived = applyConfidence({}, "consolidate", cfg);
  assert.equal(observed.provenance_kind, "observed");
  assert.equal(inferred.provenance_kind, "inferred");
  assert.equal(derived.provenance_kind, "derived");
});

test("T12.2 mark chunk canonical updates DB + audit row", () => {
  const db = setupCorpus();
  const r = markChunk({ db, chunk_id: 3, kind: "canonical" });
  assert.equal(r.applied.confidence, 1.0);
  const row = db
    .prepare("SELECT id, confidence, provenance_kind FROM chunks WHERE id = ?")
    .get<{ confidence: number; provenance_kind: string }>(3);
  assert.equal(row?.confidence, 1.0);
  assert.equal(row?.provenance_kind, "user-marked");
  assert.equal(db.audit.length, 1);
});

test("T12.3 mark chunk refuted sets confidence to 0.05", () => {
  const db = setupCorpus();
  markChunk({ db, chunk_id: 1, kind: "refuted" });
  const row = db
    .prepare("SELECT id, confidence FROM chunks WHERE id = ?")
    .get<{ confidence: number }>(1);
  assert.equal(row?.confidence, 0.05);
});

test("T12.4 supersede sets FK", () => {
  const db = setupCorpus();
  supersedeChunk({ db, chunk_id: 3, by_chunk_id: 2 });
  const row = db
    .prepare("SELECT id, superseded_by, provenance_kind FROM chunks WHERE id = ?")
    .get<{ superseded_by: number; provenance_kind: string }>(3);
  assert.equal(row?.superseded_by, 2);
});

test("T12.5 search filter min_confidence=0.7 keeps high-trust only", () => {
  const db = setupCorpus();
  const all = db.prepare("SELECT * FROM chunks").all<{ chunk_id: number; confidence: number; id: number }>();
  // Add chunk_id alias for the filter
  const results = all.map((r) => ({ ...r, chunk_id: r.id }));
  const filtered = filterByConfidence(results, { min_confidence: 0.7 });
  // Should include 1 (0.95), 2 (0.9), 4 (0.75), 5 (0.8); exclude 3 (0.65), 6 (0.5), 7 (0.2)
  assert.equal(filtered.length, 4);
});

test("T12.6 ranking integration default disabled is no-op", () => {
  const db = setupCorpus();
  const chunks = db.prepare("SELECT * FROM chunks").all<{ id: number; confidence: number; provenance_kind: string | null; pain: number }>();
  const rankable = chunks.map((c) => ({
    chunk_id: c.id,
    salience: 0.8,
    confidence: c.confidence,
    provenance_kind: c.provenance_kind,
  }));
  const r = applyConfidenceRanking(rankable, resolveConfig());
  assert.equal(r.mode, "disabled");
  // No skips, no rewrites
  assert.equal(r.chunks.length, rankable.length);
  for (let i = 0; i < rankable.length; i++) {
    assert.equal(r.chunks[i]!.ranked_salience, 0.8);
  }
});

test("T12.7 ranking active mode reorders + skips low confidence", () => {
  const db = setupCorpus();
  const chunks = db.prepare("SELECT * FROM chunks").all<{ id: number; confidence: number; provenance_kind: string | null }>();
  const rankable = chunks.map((c) => ({
    chunk_id: c.id,
    salience: 0.8,
    confidence: c.confidence,
    provenance_kind: c.provenance_kind,
  }));
  const r = applyConfidenceRanking(rankable, {
    ...resolveConfig(),
    ranking_mode: "active",
  });
  assert.equal(r.mode, "active");
  // chunk 7 (conf 0.2) < floor 0.3 → skipped
  assert.equal(r.chunks.find((c) => c.chunk_id === 7), undefined);
  assert.equal(r.stats.skipped, 1);
});

test("T12.8 health slice reflects corpus distribution", () => {
  const db = setupCorpus();
  const slice = computeConfidenceHealth(db);
  assert.equal(slice.provenance.observed, 1);
  assert.equal(slice.provenance.declared, 1);
  assert.equal(slice.provenance.inferred, 2);
  assert.equal(slice.provenance.derived, 2);
  assert.equal(slice.provenance.null, 1);
});

test("T12.9 after mark, telemetry reflects user-marked count", () => {
  const db = setupCorpus();
  markChunk({ db, chunk_id: 3, kind: "canonical" });
  markChunk({ db, chunk_id: 6, kind: "refuted" });
  const slice = computeConfidenceHealth(db);
  assert.equal(slice.provenance["user-marked"], 2);
  // Inferred dropped from 2 to 0 (both became user-marked)
  assert.equal(slice.provenance.inferred, 0);
});

test("T12.10 audit trail accumulates across operations", () => {
  const db = setupCorpus();
  markChunk({ db, chunk_id: 1, kind: "canonical" });
  markChunk({ db, chunk_id: 2, kind: "refuted" });
  supersedeChunk({ db, chunk_id: 3, by_chunk_id: 1 });
  assert.equal(db.audit.length, 3);
  // All status=success
  for (const row of db.audit) {
    assert.equal(row.status, "success");
  }
});

test("T12.11 supersede self → throws + audit failed", () => {
  const db = setupCorpus();
  assert.throws(() => supersedeChunk({ db, chunk_id: 3, by_chunk_id: 3 }));
  assert.equal(db.audit.length, 1);
  assert.equal(db.audit[0]?.status, "failed");
});

test("T12.12 end-to-end: mark refuted + active ranking → chunk excluded", () => {
  const db = setupCorpus();
  markChunk({ db, chunk_id: 1, kind: "refuted" });
  // chunk 1 now confidence=0.05, provenance=user-marked
  const chunks = db.prepare("SELECT * FROM chunks").all<{ id: number; confidence: number; provenance_kind: string }>();
  const rankable = chunks.map((c) => ({
    chunk_id: c.id,
    salience: 0.8,
    confidence: c.confidence,
    provenance_kind: c.provenance_kind,
  }));
  const r = applyConfidenceRanking(rankable, {
    ...resolveConfig(),
    ranking_mode: "active",
  });
  // chunk 1 must be excluded (confidence 0.05 < 0.3 floor)
  assert.equal(r.chunks.find((c) => c.chunk_id === 1), undefined);
});
