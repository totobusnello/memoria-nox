/**
 * S8 — Confidence ranking shadow vs active (L3 + P1).
 *
 * Verifies:
 *   - 10 chunks with confidence ∈ [0.3, 1.0]
 *   - mode='disabled' (baseline): ranking unchanged, shadow_modulated_score=0
 *   - mode='shadow': ranking still baseline; shadow_modulated_score visible
 *   - mode='active': low-confidence chunks (< floor 0.4) excluded; ranking
 *     uses base * confidence
 *
 * Bug-class targeted: a regression where 'shadow' mode accidentally modifies
 * the answer (defeats the whole point of shadow). Per CLAUDE.md rule #5,
 * ranking changes ship in shadow first — this test pins the contract.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  applyConfidenceRanking,
  ACTIVE_FLOOR_DEFAULT,
} from "../lib/pillar-shims.js";

const corpus = [
  { id: 1, base_score: 1.0, confidence: 1.0 },
  { id: 2, base_score: 0.9, confidence: 0.9 },
  { id: 3, base_score: 0.85, confidence: 0.8 },
  { id: 4, base_score: 0.8, confidence: 0.7 },
  { id: 5, base_score: 0.75, confidence: 0.6 },
  { id: 6, base_score: 0.7, confidence: 0.5 },
  { id: 7, base_score: 0.65, confidence: 0.45 },
  { id: 8, base_score: 0.6, confidence: 0.4 },
  { id: 9, base_score: 0.55, confidence: 0.35 },
  { id: 10, base_score: 0.5, confidence: 0.3 },
];

describe("S8 — confidence shadow vs active ranking (L3 + P1)", () => {
  it("S8-01 mode='disabled' returns rows in base_score order, shadow_modulated_score=0", () => {
    const out = applyConfidenceRanking(corpus, "disabled");
    assert.strictEqual(out.length, 10);
    // Should be sorted by base_score (which equals modulated_score in disabled mode).
    for (let i = 1; i < out.length; i++) {
      assert.ok(out[i - 1]!.modulated_score >= out[i]!.modulated_score);
    }
    for (const r of out) assert.strictEqual(r.shadow_modulated_score, 0);
  });

  it("S8-02 mode='shadow' ranking IDENTICAL to baseline (the iron law)", () => {
    const disabled = applyConfidenceRanking(corpus, "disabled");
    const shadow = applyConfidenceRanking(corpus, "shadow");
    assert.strictEqual(disabled.length, shadow.length);
    for (let i = 0; i < disabled.length; i++) {
      assert.strictEqual(disabled[i]!.id, shadow[i]!.id);
      assert.strictEqual(disabled[i]!.modulated_score, shadow[i]!.modulated_score);
    }
  });

  it("S8-03 mode='shadow' populates shadow_modulated_score = base * confidence", () => {
    const out = applyConfidenceRanking(corpus, "shadow");
    for (const r of out) {
      const expected = r.base_score * r.confidence;
      assert.ok(Math.abs(r.shadow_modulated_score - expected) < 1e-9);
    }
  });

  it("S8-04 mode='active' drops rows with confidence < floor (0.4 default)", () => {
    const out = applyConfidenceRanking(corpus, "active");
    assert.ok(out.length < corpus.length);
    for (const r of out) {
      assert.ok(r.confidence >= ACTIVE_FLOOR_DEFAULT);
    }
    // ids 9 (0.35) and 10 (0.3) should be gone.
    const ids = out.map((r) => r.id);
    assert.ok(!ids.includes(9));
    assert.ok(!ids.includes(10));
    // ids 7 (0.45) and 8 (0.4) survive.
    assert.ok(ids.includes(7));
    assert.ok(ids.includes(8));
  });

  it("S8-05 mode='active' ranks by base * confidence, so high-confidence wins ties", () => {
    // Synthetic case: two chunks with same base_score, different confidence.
    const tied = [
      { id: 100, base_score: 0.9, confidence: 0.5 },
      { id: 101, base_score: 0.9, confidence: 0.95 },
    ];
    const out = applyConfidenceRanking(tied, "active");
    // 0.9*0.95 = 0.855 > 0.9*0.5 = 0.45 — id 101 must be first.
    assert.strictEqual(out[0]!.id, 101);
    assert.strictEqual(out[1]!.id, 100);
  });

  it("S8-06 active floor configurable via param (defense-in-depth knob)", () => {
    const strictFloor = applyConfidenceRanking(corpus, "active", 0.7);
    for (const r of strictFloor) assert.ok(r.confidence >= 0.7);
    // ids 1 (1.0), 2 (0.9), 3 (0.8), 4 (0.7) survive.
    const ids = strictFloor.map((r) => r.id).sort();
    assert.deepStrictEqual(ids, [1, 2, 3, 4]);
  });
});
