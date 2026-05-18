/**
 * T3 — Write hooks tests (12 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveConfig } from "../config.js";
import {
  applyConfidence,
  applyConfidenceToRelation,
  defaultsForSource,
} from "../write-hooks.js";

const cfg = resolveConfig({
  default_observed: 0.95,
  default_declared: 0.9,
  default_inferred: 0.65,
  default_derived: 0.75,
  default_graphify: 0.7,
  user_marked_canonical: 1.0,
  user_marked_refuted: 0.05,
  active_floor: 0.3,
  ranking_mode: "disabled",
  decay_halflife_days: -1,
});

test("T3.1 defaultsForSource entity-compiled → declared 0.9", () => {
  const r = defaultsForSource("entity-compiled", cfg);
  assert.equal(r.provenance_kind, "declared");
  assert.equal(r.confidence, 0.9);
});

test("T3.2 defaultsForSource entity-timeline → observed 0.95", () => {
  const r = defaultsForSource("entity-timeline", cfg);
  assert.equal(r.provenance_kind, "observed");
  assert.equal(r.confidence, 0.95);
});

test("T3.3 defaultsForSource markdown → NULL kind, 0.8 confidence", () => {
  const r = defaultsForSource("markdown", cfg);
  assert.equal(r.provenance_kind, null);
  assert.equal(r.confidence, 0.8);
});

test("T3.4 defaultsForSource graphify → derived 0.7", () => {
  const r = defaultsForSource("graphify", cfg);
  assert.equal(r.provenance_kind, "derived");
  assert.equal(r.confidence, 0.7);
});

test("T3.5 defaultsForSource kg-extract → inferred 0.65", () => {
  const r = defaultsForSource("kg-extract", cfg);
  assert.equal(r.provenance_kind, "inferred");
  assert.equal(r.confidence, 0.65);
});

test("T3.6 defaultsForSource consolidate → derived 0.75", () => {
  const r = defaultsForSource("consolidate", cfg);
  assert.equal(r.provenance_kind, "derived");
  assert.equal(r.confidence, 0.75);
});

test("T3.7 applyConfidence does not overwrite explicit values", () => {
  const out = applyConfidence(
    { confidence: 0.42, provenance_kind: "observed" },
    "markdown",
    cfg
  );
  assert.equal(out.confidence, 0.42);
  assert.equal(out.provenance_kind, "observed");
});

test("T3.8 applyConfidence clamps explicit values to [0,1]", () => {
  const out = applyConfidence({ confidence: 1.5 }, "markdown", cfg);
  assert.equal(out.confidence, 1.0);
});

test("T3.9 applyConfidence returns NEW object (immutability)", () => {
  const input = { confidence: 0.5 };
  const out = applyConfidence(input, "entity-compiled", cfg);
  assert.notEqual(out, input);
});

test("T3.10 applyConfidenceToRelation explicit confidence wins", () => {
  const r = applyConfidenceToRelation({ confidence: 0.88 }, cfg);
  assert.equal(r.confidence, 0.88);
});

test("T3.11 applyConfidenceToRelation frontmatter → declared 0.9", () => {
  const r = applyConfidenceToRelation({ source_section: "frontmatter" }, cfg);
  assert.equal(r.confidence, 0.9);
  assert.equal(r.provenance_kind, "declared");
});

test("T3.12 applyConfidenceToRelation regex_only → observed 0.85", () => {
  const r = applyConfidenceToRelation({ extraction_method: "regex_only" }, cfg);
  assert.equal(r.confidence, 0.85);
  assert.equal(r.provenance_kind, "observed");
});
