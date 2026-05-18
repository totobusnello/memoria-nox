/**
 * T7 — Ranking integration tests (12 tests).
 * GATED feature; default mode is "disabled" so all live behavior is no-op.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveConfig } from "../config.js";
import {
  applyConfidenceRanking,
  computeRankedSalience,
  CLAMP_MIN,
  CLAMP_MAX,
  SUPERSEDED_MULTIPLIER,
} from "../ranking.js";

const baseCfg = resolveConfig({
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

const sampleChunks = [
  { chunk_id: 1, salience: 0.9, confidence: 1.0, provenance_kind: "observed" },
  { chunk_id: 2, salience: 0.85, confidence: 0.65, provenance_kind: "inferred" },
  { chunk_id: 3, salience: 0.5, confidence: 0.05, provenance_kind: "user-marked" },
  { chunk_id: 4, salience: 0.8, confidence: 0.9, provenance_kind: "declared", superseded_by: 99 },
];

test("T7.1 disabled mode returns chunks unchanged", () => {
  const r = applyConfidenceRanking(sampleChunks, baseCfg);
  assert.equal(r.mode, "disabled");
  assert.equal(r.chunks.length, sampleChunks.length);
  for (let i = 0; i < sampleChunks.length; i++) {
    assert.equal(r.chunks[i]!.ranked_salience, sampleChunks[i]!.salience);
  }
});

test("T7.2 shadow mode returns original salience but records shadow_delta", () => {
  const r = applyConfidenceRanking(sampleChunks, {
    ...baseCfg,
    ranking_mode: "shadow",
  });
  assert.equal(r.mode, "shadow");
  for (let i = 0; i < sampleChunks.length; i++) {
    // Output salience equals input — shadow does not apply
    assert.equal(r.chunks[i]!.ranked_salience, sampleChunks[i]!.salience);
    // But shadow_delta is populated
    assert.equal(typeof r.chunks[i]!.shadow_delta, "number");
  }
});

test("T7.3 active mode multiplies confidence into salience", () => {
  const r = applyConfidenceRanking(
    [{ chunk_id: 1, salience: 0.9, confidence: 0.5, provenance_kind: "inferred" }],
    { ...baseCfg, ranking_mode: "active" }
  );
  // 0.9 * 0.5 = 0.45 (above floor 0.3, below cap 1.5)
  assert.equal(r.chunks[0]!.ranked_salience, 0.45);
});

test("T7.4 active mode skips chunks with confidence below active_floor", () => {
  const r = applyConfidenceRanking(sampleChunks, {
    ...baseCfg,
    ranking_mode: "active",
  });
  // chunk 3 has confidence 0.05 < 0.3 floor → skipped
  const ids = r.chunks.map((c) => c.chunk_id);
  assert.equal(ids.includes(3), false);
  assert.equal(r.stats.skipped, 1);
});

test("T7.5 active mode de-prioritizes superseded chunks (does NOT skip)", () => {
  const r = applyConfidenceRanking(
    [{ chunk_id: 4, salience: 0.8, confidence: 0.9, provenance_kind: "declared", superseded_by: 99 }],
    { ...baseCfg, ranking_mode: "active" }
  );
  // 0.8 * 0.9 * 0.5 = 0.36 (floating-point: 0.36000000000000004)
  assert.equal(r.chunks.length, 1);
  assert.ok(Math.abs(r.chunks[0]!.ranked_salience - 0.36) < 1e-9);
  assert.equal(r.stats.superseded_deprioritized, 1);
});

test("T7.6 active mode clamps salience to [0.3, 1.5]", () => {
  const r = applyConfidenceRanking(
    [
      { chunk_id: 1, salience: 1.4, confidence: 1.0, provenance_kind: "observed" },
      { chunk_id: 2, salience: 0.4, confidence: 0.4, provenance_kind: "inferred" },
    ],
    { ...baseCfg, ranking_mode: "active" }
  );
  // 1.4 * 1.0 = 1.4 (no clamp)
  assert.equal(r.chunks[0]!.ranked_salience, 1.4);
  // 0.4 * 0.4 = 0.16 → clamp to 0.3
  assert.equal(r.chunks[1]!.ranked_salience, 0.3);
});

test("T7.7 computeRankedSalience pure helper", () => {
  assert.ok(Math.abs(computeRankedSalience(0.9, 0.5, false) - 0.45) < 1e-9);
  assert.ok(Math.abs(computeRankedSalience(0.8, 0.9, true) - 0.36) < 1e-9);
});

test("T7.8 missing confidence defaults to 0.8", () => {
  const r = applyConfidenceRanking(
    [{ chunk_id: 1, salience: 0.5 }],
    { ...baseCfg, ranking_mode: "active" }
  );
  // 0.5 * 0.8 = 0.4
  assert.equal(r.chunks[0]!.ranked_salience, 0.4);
});

test("T7.9 corpus-wide confidence=1.0 → active equals disabled (no-op proof)", () => {
  const chunks = [
    { chunk_id: 1, salience: 0.9, confidence: 1.0 },
    { chunk_id: 2, salience: 0.8, confidence: 1.0 },
    { chunk_id: 3, salience: 0.5, confidence: 1.0 },
  ];
  const active = applyConfidenceRanking(chunks, { ...baseCfg, ranking_mode: "active" });
  const disabled = applyConfidenceRanking(chunks, baseCfg);
  for (let i = 0; i < chunks.length; i++) {
    assert.equal(active.chunks[i]!.ranked_salience, disabled.chunks[i]!.ranked_salience);
  }
});

test("T7.10 ranking constants exported for downstream calibration", () => {
  assert.equal(CLAMP_MIN, 0.3);
  assert.equal(CLAMP_MAX, 1.5);
  assert.equal(SUPERSEDED_MULTIPLIER, 0.5);
});

test("T7.11 stats.mean_delta computed across all chunks (disabled mode)", () => {
  const r = applyConfidenceRanking(sampleChunks, baseCfg);
  // mean_delta computed even when not applied; useful for shadow stats
  assert.ok(Number.isFinite(r.stats.mean_delta));
});

test("T7.12 active mode skip preserves stats.input_count != output_count", () => {
  const r = applyConfidenceRanking(sampleChunks, {
    ...baseCfg,
    ranking_mode: "active",
  });
  assert.equal(r.stats.input_count, 4);
  assert.ok(r.stats.output_count < r.stats.input_count);
  assert.equal(r.stats.input_count, r.stats.output_count + r.stats.skipped);
});
