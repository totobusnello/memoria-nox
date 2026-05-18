/**
 * T9 — Search filter tests (8 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  filterByConfidence,
  parseMinConfidence,
  buildConfidenceWhereClause,
} from "../search-filter.js";

const sample = [
  { chunk_id: 1, confidence: 1.0, provenance_kind: "observed" },
  { chunk_id: 2, confidence: 0.7, provenance_kind: "inferred" },
  { chunk_id: 3, confidence: 0.3, provenance_kind: "derived" },
  { chunk_id: 4, confidence: 0.05, provenance_kind: "user-marked" },
  { chunk_id: 5, confidence: null, provenance_kind: null },
  { chunk_id: 6, confidence: 0.9, provenance_kind: "declared", superseded_by: 1 },
];

test("T9.1 parseMinConfidence number passes through clamped", () => {
  assert.equal(parseMinConfidence(0.5), 0.5);
  assert.equal(parseMinConfidence(2), 1);
  assert.equal(parseMinConfidence(-1), 0);
});

test("T9.2 parseMinConfidence string parses", () => {
  assert.equal(parseMinConfidence("0.42"), 0.42);
});

test("T9.3 parseMinConfidence rejects garbage", () => {
  assert.equal(parseMinConfidence("abc"), undefined);
  assert.equal(parseMinConfidence(null), undefined);
});

test("T9.4 filterByConfidence no opts → no-op", () => {
  const out = filterByConfidence(sample);
  assert.equal(out.length, sample.length);
});

test("T9.5 filterByConfidence threshold 0.5 keeps high-conf only", () => {
  const out = filterByConfidence(sample, { min_confidence: 0.5 });
  const ids = out.map((c) => c.chunk_id);
  assert.deepEqual(ids.sort((a, b) => a - b), [1, 2, 5, 6]);
});

test("T9.6 exclude_null drops NULL-confidence chunks", () => {
  const out = filterByConfidence(sample, {
    min_confidence: 0,
    exclude_null: true,
  });
  assert.equal(out.find((c) => c.chunk_id === 5), undefined);
});

test("T9.7 exclude_superseded drops superseded chunks", () => {
  const out = filterByConfidence(sample, { exclude_superseded: true });
  assert.equal(out.find((c) => c.chunk_id === 6), undefined);
});

test("T9.8 buildConfidenceWhereClause SQL + params", () => {
  const r = buildConfidenceWhereClause({ min_confidence: 0.5 });
  assert.ok(r);
  assert.ok(r!.sql.includes("confidence >= ?"));
  assert.equal(r!.params.length, 2);
  const empty = buildConfidenceWhereClause({});
  assert.equal(empty, null);
});
