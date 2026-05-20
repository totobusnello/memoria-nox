/**
 * staged-1.7a/tests/salience.test.ts
 *
 * Unit tests for v2 salience formula (additive, evidence-weighted).
 *
 * Companion to PR #150. Validates:
 *  - accessCountComponent edge cases (null/NaN/0/saturation)
 *  - calculateSalience never returns NaN/Infinity for any nullable-field combo
 *  - calculateSalience weights sum to 1.0 when all components saturate
 *  - calculateSalience vs calculateSalienceLegacy fingerprint (5 fixtures)
 *  - classifySalience boundary tests at 0.15 / 0.4 / 0.7
 *
 * Run: node --test dist/tests/salience.test.js
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  accessCountComponent,
  calculateSalience,
  calculateSalienceLegacy,
  classifySalience,
  inferImportance,
  inferPain,
  type SalienceInput,
} from "../edits/salience.js";

// Helper: approximate equality
function approx(actual: number, expected: number, eps = 0.01): boolean {
  return Math.abs(actual - expected) < eps;
}

describe("accessCountComponent", () => {
  it("returns 0 for null", () => {
    assert.equal(accessCountComponent(null), 0);
  });
  it("returns 0 for undefined", () => {
    assert.equal(accessCountComponent(undefined), 0);
  });
  it("returns 0 for NaN", () => {
    assert.equal(accessCountComponent(NaN), 0);
  });
  it("returns 0 for 0", () => {
    assert.equal(accessCountComponent(0), 0);
  });
  it("returns 0 for negative", () => {
    assert.equal(accessCountComponent(-1), 0);
    assert.equal(accessCountComponent(-100), 0);
  });
  it("returns ~0.10 for access_count=1", () => {
    assert.ok(approx(accessCountComponent(1), 0.10, 0.005));
  });
  it("returns ~0.35 for access_count=10", () => {
    assert.ok(approx(accessCountComponent(10), 0.347, 0.01));
  });
  it("returns ~0.67 for access_count=100", () => {
    assert.ok(approx(accessCountComponent(100), 0.667, 0.01));
  });
  it("returns 1.0 for access_count=1000 (saturates)", () => {
    assert.ok(approx(accessCountComponent(1000), 1.0, 0.001));
  });
  it("clamps to 1.0 for access_count >> 1000", () => {
    assert.equal(accessCountComponent(10000), 1.0);
    assert.equal(accessCountComponent(1_000_000), 1.0);
  });
});

describe("calculateSalience v2 (additive)", () => {
  it("never returns NaN/Infinity for fully-null chunk", () => {
    const chunk: SalienceInput = {};
    const s = calculateSalience(chunk);
    assert.ok(Number.isFinite(s));
    assert.ok(s >= 0 && s <= 1);
  });

  it("never returns NaN for any nullable-field combo", () => {
    const nullableCombos: SalienceInput[] = [
      { chunk_type: null, pain: null, importance: null },
      { chunk_type: "decision", pain: 0.5, importance: null },
      { chunk_type: undefined, pain: undefined, importance: 0.8 },
      { access_count: null },
      { access_count: undefined },
      { access_count: NaN as unknown as number },
      { source_date: null, created_at: null, last_accessed_at: null },
      { source_date: "INVALID-DATE", created_at: null },
      { retention_days: null, chunk_type: "feedback" },
      { retention_days: 0, chunk_type: null },
    ];
    for (const c of nullableCombos) {
      const s = calculateSalience(c, Date.now());
      assert.ok(Number.isFinite(s), `NaN/Infinity for ${JSON.stringify(c)}`);
      assert.ok(s >= 0 && s <= 1, `out-of-range for ${JSON.stringify(c)}: ${s}`);
    }
  });

  it("returns 1.0 when all 4 components saturate to 1.0", () => {
    // All saturate:
    //   - importance=1.0 via explicit override
    //   - recency=1.0 via never-decay retention (feedback type)
    //   - pain=1.0 explicit
    //   - access=1.0 via large access_count
    const chunk: SalienceInput = {
      chunk_type: "feedback", // retention=0 → recency=1.0
      importance: 1.0,
      pain: 1.0,
      access_count: 10000, // saturates accessCountComponent to 1.0
    };
    const s = calculateSalience(chunk);
    // Weights: 0.55 + 0.15 + 0.10 + 0.20 = 1.00
    assert.ok(approx(s, 1.0, 0.001), `expected ~1.0, got ${s}`);
  });

  it("returns 0.0 when all 4 components bottom out", () => {
    // All zero:
    //   - importance=0
    //   - pain=0
    //   - recency≈0 via very old source_date
    //   - access_count=0
    const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString();
    const chunk: SalienceInput = {
      chunk_type: "pending", // retention=30d → after 1y, recency ≈ 2^-12 ≈ 0.0002
      importance: 0,
      pain: 0,
      access_count: 0,
      source_date: oneYearAgo,
    };
    const s = calculateSalience(chunk);
    assert.ok(s < 0.05, `expected near-zero, got ${s}`);
  });

  it("importance dominates as primary signal (W=0.55)", () => {
    // Compare two chunks identical except importance
    const lowImp: SalienceInput = { chunk_type: "daily", importance: 0.0, access_count: 0 };
    const highImp: SalienceInput = { chunk_type: "daily", importance: 1.0, access_count: 0 };
    const sLow = calculateSalience(lowImp);
    const sHigh = calculateSalience(highImp);
    assert.ok(sHigh - sLow >= 0.5, `importance delta should be ≥0.5, got ${sHigh - sLow}`);
  });

  it("access_count contributes ~0.20 swing as secondary signal", () => {
    const lowAcc: SalienceInput = { chunk_type: "daily", importance: 0.5, access_count: 0 };
    const highAcc: SalienceInput = { chunk_type: "daily", importance: 0.5, access_count: 1000 };
    const sLow = calculateSalience(lowAcc);
    const sHigh = calculateSalience(highAcc);
    assert.ok(approx(sHigh - sLow, 0.20, 0.02), `access delta should be ~0.20, got ${sHigh - sLow}`);
  });
});

describe("calculateSalienceLegacy (multiplicative, for ablation)", () => {
  it("returns 0 when any component is 0 (multiplicative collapse)", () => {
    const chunk: SalienceInput = {
      chunk_type: "feedback",
      importance: 0,
      pain: 0.5,
    };
    const s = calculateSalienceLegacy(chunk);
    assert.equal(s, 0);
  });

  it("legacy and v2 produce different rankings for evidence-based corpus", () => {
    // Fixture mimicking real prod chunk: importance=0.40 (74% bucket),
    // pain=0.2 (default), access_count=0, recent
    const corpusTypical: SalienceInput = {
      chunk_type: "daily",
      importance: 0.40,
      pain: 0.2,
      access_count: 0,
      source_date: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    };
    const sLegacy = calculateSalienceLegacy(corpusTypical);
    const sV2 = calculateSalience(corpusTypical);
    // Legacy: ~0.9 * 0.2 * 0.40 ≈ 0.072 (dead band [0.05-0.15])
    // V2: 0.55*0.40 + 0.15*~0.9 + 0.10*0.2 + 0.20*0 ≈ 0.22 + 0.135 + 0.02 + 0 = 0.375
    assert.ok(sLegacy < 0.15, `legacy expected <0.15 (dead band), got ${sLegacy}`);
    assert.ok(sV2 > 0.30, `v2 expected >0.30 (alive band), got ${sV2}`);
    assert.ok(sV2 > sLegacy, "v2 should rank typical corpus chunks higher than legacy dead band");
  });

  it("legacy v2 5-fixture fingerprint for shadow comparison", () => {
    // Anchored fixtures: capture both formulas on representative chunks.
    // Any future refactor must explain shifts in these values.
    const fixtures: Array<[string, SalienceInput, number, number]> = [
      // [label, chunk, expected_legacy, expected_v2]
      ["typical-dead-band-chunk", {
        chunk_type: "daily", importance: 0.40, pain: 0.2,
        source_date: new Date(Date.now() - 14*864e5).toISOString(),
      }, 0.072, 0.375],
      ["high-importance-zero-access", {
        chunk_type: "decision", importance: 0.9, pain: 0.2, access_count: 0,
        source_date: new Date(Date.now() - 14*864e5).toISOString(),
      }, 0.16, 0.66],
      ["heavily-accessed", {
        chunk_type: "lesson", importance: 0.5, pain: 0.2, access_count: 1000,
        source_date: new Date(Date.now() - 14*864e5).toISOString(),
      }, 0.09, 0.62],
      ["high-pain", {
        chunk_type: "lesson", importance: 0.4, pain: 1.0, access_count: 5,
        source_date: new Date(Date.now() - 14*864e5).toISOString(),
      }, 0.36, 0.45],
      ["null-everything", {}, 0.08, 0.27],
    ];
    for (const [label, chunk, expectedLegacy, expectedV2] of fixtures) {
      const sLegacy = calculateSalienceLegacy(chunk);
      const sV2 = calculateSalience(chunk);
      assert.ok(approx(sLegacy, expectedLegacy, 0.06), `legacy[${label}] expected ~${expectedLegacy}, got ${sLegacy.toFixed(3)}`);
      assert.ok(approx(sV2, expectedV2, 0.06), `v2[${label}] expected ~${expectedV2}, got ${sV2.toFixed(3)}`);
    }
  });
});

describe("classifySalience boundary tests", () => {
  it("classifies score=0.7 exactly as promote", () => {
    assert.equal(classifySalience(0.7), "promote");
  });
  it("classifies score=0.6999 as retain (just below promote)", () => {
    assert.equal(classifySalience(0.6999), "retain");
  });
  it("classifies score=0.4 exactly as retain", () => {
    assert.equal(classifySalience(0.4), "retain");
  });
  it("classifies score=0.3999 as review (just below retain)", () => {
    assert.equal(classifySalience(0.3999), "review");
  });
  it("classifies score=0.15 exactly as review", () => {
    assert.equal(classifySalience(0.15), "review");
  });
  it("classifies score=0.1499 as archive (just below review)", () => {
    assert.equal(classifySalience(0.1499), "archive");
  });
  it("classifies score=0 as archive", () => {
    assert.equal(classifySalience(0), "archive");
  });
  it("classifies score=1 as promote", () => {
    assert.equal(classifySalience(1), "promote");
  });
});

// ── Backwards-compat helpers (used by src/ingest-entity.ts) ───────────────────

describe("inferImportance (backwards-compat)", () => {
  it("returns mapped value for known chunk_type", () => {
    assert.ok(approx(inferImportance("decision"), 0.95, 0.001));
    assert.ok(approx(inferImportance("lesson"), 0.90, 0.001));
    assert.ok(approx(inferImportance("daily"), 0.50, 0.001));
  });
  it("returns fallback for unknown chunk_type", () => {
    assert.ok(approx(inferImportance("foo-unknown"), 0.40, 0.001));
  });
  it("returns fallback for null/undefined", () => {
    assert.ok(approx(inferImportance(null), 0.40, 0.001));
    assert.ok(approx(inferImportance(undefined), 0.40, 0.001));
  });
});

describe("inferPain (backwards-compat)", () => {
  it("returns base pain by chunk_type for non-incident content", () => {
    assert.ok(approx(inferPain("feedback", "regular feedback note"), 0.3, 0.001));
    assert.ok(approx(inferPain("lesson", "lesson about caching"), 0.4, 0.001));
    assert.ok(approx(inferPain("pending", "todo item"), 0.5, 0.001));
    assert.ok(approx(inferPain("daily", "morning notes"), 0.2, 0.001));
  });
  it("returns fallback pain for unknown chunk_type", () => {
    assert.ok(approx(inferPain("foo-unknown", "regular content"), 0.2, 0.001));
  });
  it("elevates pain on incident/outage/severity keywords (EN)", () => {
    assert.ok(inferPain("daily", "incident in prod-down at 14:00") > 0.5);
    assert.ok(inferPain("daily", "outage P0 severity high") > 0.5);
    assert.ok(inferPain("daily", "data breach detected") > 0.5);
    assert.ok(inferPain("daily", "emergency response sev-1") > 0.5);
  });
  it("elevates pain on PT-BR incident keywords", () => {
    assert.ok(inferPain("daily", "incidente crítico em produção") > 0.5);
    assert.ok(inferPain("daily", "emergência grave") > 0.5);
  });
  it("caps pain at 1.0 (clamp)", () => {
    // base + 0.5 = 1.5, but clamp to 1.0
    const result = inferPain("pending", "P0 incident outage emergency");
    assert.ok(result <= 1.0);
    assert.ok(result > 0.9);
  });
  it("handles null/undefined safely", () => {
    assert.ok(approx(inferPain(null, null), 0.2, 0.001));
    assert.ok(approx(inferPain(undefined, undefined), 0.2, 0.001));
    assert.ok(approx(inferPain("daily", null), 0.2, 0.001));
    assert.ok(approx(inferPain(null, "incident"), 0.7, 0.001));
  });
});
