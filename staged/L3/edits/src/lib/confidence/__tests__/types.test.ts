/**
 * T1 — Types tests (6 tests).
 * Validates type shapes via constructor coercion (TS structural).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import type {
  ProvenanceKind,
  MarkKind,
  RankingMode,
  ConfidenceConfig,
  IngestSource,
  ConfidenceHealthSlice,
} from "../types.js";

test("T1.1 ProvenanceKind enum accepts all 5 DB-level values", () => {
  const valid: ProvenanceKind[] = [
    "observed",
    "declared",
    "inferred",
    "derived",
    "user-marked",
  ];
  assert.equal(valid.length, 5);
});

test("T1.2 MarkKind accepts canonical / refuted / stale", () => {
  const valid: MarkKind[] = ["canonical", "refuted", "stale"];
  assert.equal(valid.length, 3);
});

test("T1.3 RankingMode accepts disabled / shadow / active", () => {
  const valid: RankingMode[] = ["disabled", "shadow", "active"];
  assert.equal(valid.length, 3);
});

test("T1.4 IngestSource enum covers all spec §4a routing kinds", () => {
  const valid: IngestSource[] = [
    "entity-compiled",
    "entity-frontmatter",
    "entity-timeline",
    "markdown",
    "graphify",
    "kg-extract",
    "consolidate",
    "crystallize",
    "cli-explicit",
  ];
  assert.equal(valid.length, 9);
});

test("T1.5 ConfidenceConfig has all 10 required numeric fields + ranking_mode", () => {
  const cfg: ConfidenceConfig = {
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
  };
  assert.equal(typeof cfg.default_observed, "number");
  assert.equal(cfg.ranking_mode, "disabled");
});

test("T1.6 ConfidenceHealthSlice shape complete", () => {
  const slice: ConfidenceHealthSlice = {
    provenance: {
      observed: 100,
      declared: 200,
      inferred: 300,
      derived: 50,
      "user-marked": 5,
      null: 1000,
    },
    confidence_distribution: {
      mean: 0.8,
      p25: 0.7,
      p50: 0.8,
      p75: 0.9,
      p95: 0.95,
      stddev: 0.1,
    },
    superseded_count: 10,
    ranking_mode: "shadow",
  };
  assert.equal(slice.ranking_mode, "shadow");
  assert.equal(slice.provenance.observed, 100);
});
