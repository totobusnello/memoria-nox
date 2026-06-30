/**
 * T8 — Health telemetry tests (8 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { MockDb } from "../db-shim.js";
import {
  computeConfidenceHealth,
  percentile,
  meanStddev,
} from "../../../api/health-confidence.js";

test("T8.1 empty DB returns zeroed slice", () => {
  const db = new MockDb();
  const slice = computeConfidenceHealth(db);
  assert.equal(slice.provenance.observed, 0);
  assert.equal(slice.confidence_distribution.mean, 0);
  assert.equal(slice.superseded_count, 0);
});

test("T8.2 provenance histogram counts each kind", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, provenance_kind: "observed", confidence: 1.0 });
  db.seedChunk({ id: 2, provenance_kind: "observed", confidence: 0.9 });
  db.seedChunk({ id: 3, provenance_kind: "inferred", confidence: 0.65 });
  db.seedChunk({ id: 4, provenance_kind: null, confidence: 0.8 });
  const slice = computeConfidenceHealth(db);
  assert.equal(slice.provenance.observed, 2);
  assert.equal(slice.provenance.inferred, 1);
  assert.equal(slice.provenance.null, 1);
});

test("T8.3 confidence_distribution mean computed correctly", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 1.0 });
  db.seedChunk({ id: 2, confidence: 0.5 });
  db.seedChunk({ id: 3, confidence: 0.0 });
  const slice = computeConfidenceHealth(db);
  assert.ok(Math.abs(slice.confidence_distribution.mean - 0.5) < 0.001);
});

test("T8.4 superseded_count counts non-null superseded_by", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.5 });
  db.seedChunk({ id: 2, confidence: 0.5, superseded_by: 1 });
  db.seedChunk({ id: 3, confidence: 0.5, superseded_by: 1 });
  const slice = computeConfidenceHealth(db);
  assert.equal(slice.superseded_count, 2);
});

test("T8.5 ranking_mode reflected from explicit arg", () => {
  const db = new MockDb();
  const slice = computeConfidenceHealth(db, "shadow");
  assert.equal(slice.ranking_mode, "shadow");
});

test("T8.6 percentile helper computes correctly", () => {
  const sorted = [0.1, 0.3, 0.5, 0.7, 0.9];
  assert.equal(percentile(sorted, 0.0), 0.1);
  assert.equal(percentile(sorted, 0.5), 0.5);
  assert.equal(percentile(sorted, 1.0), 0.9);
});

test("T8.7 meanStddev helper", () => {
  const r = meanStddev([1, 2, 3, 4, 5]);
  assert.equal(r.mean, 3);
  // population stddev sqrt(2)
  assert.ok(Math.abs(r.stddev - Math.sqrt(2)) < 0.001);
});

test("T8.8 percentile interpolates between values", () => {
  const sorted = [0.0, 1.0];
  assert.equal(percentile(sorted, 0.5), 0.5);
});
