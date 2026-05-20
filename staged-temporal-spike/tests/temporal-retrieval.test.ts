/**
 * staged-temporal-spike/tests/temporal-retrieval.test.ts
 *
 * Unit tests do spike de temporal retrieval path (Q1 R&D, 2026-05-20).
 *
 * Cobre:
 *  - detectTemporal: ISO date, mes+ano PT-BR/EN, ano isolado, adverbial,
 *    queries não-temporais, edge cases (curta, vazia, futuro)
 *  - proximityDelta: shape gaussiano, edge cases (null, NaN, σ=0 fallback)
 *  - rerankByTemporalProximity: shadow não muta, active reorderna,
 *    off é no-op, top-K bound, adverbial-only não dispara rerank
 *
 * Run:
 *   npx tsc -p tsconfig.tests.json && node --test dist/tests/*.test.js
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  detectTemporal,
  proximityDelta,
  proximityBoost,
  inferAnchorFromTopK,
  rerankByTemporalProximity,
  type RerankableResult,
} from "../edits/temporal-retrieval.js";

// Fixed "now" pra month-year resolution determinístico: 2026-05-20
const NOW_MS = Date.UTC(2026, 4, 20);

describe("detectTemporal", () => {
  it("detects ISO date as strongest signal with exact anchor", () => {
    const r = detectTemporal("primeira lição do incident reindex 2026-04-25", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "iso_date");
    assert.equal(r.anchor?.toISOString().slice(0, 10), "2026-04-25");
  });

  it("detects PT-BR month+year and produces range midpoint", () => {
    const r = detectTemporal("o que aconteceu em abril de 2026", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "month_year");
    assert.equal(r.anchorRange![0].toISOString().slice(0, 10), "2026-04-01");
    assert.equal(r.anchorRange![1].toISOString().slice(0, 10), "2026-04-30");
    // midpoint of April 2026 ≈ April 15-16 UTC
    const mid = r.anchor!.toISOString().slice(0, 10);
    assert.ok(mid === "2026-04-15" || mid === "2026-04-16", `unexpected midpoint: ${mid}`);
  });

  it("resolves bare month to current year when month is in the past", () => {
    // NOW=2026-05-20, month=março → 2026-03 (past, same year)
    const r = detectTemporal("o que mudou em março", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "month_year");
    assert.equal(r.anchorRange![0].getUTCFullYear(), 2026);
    assert.equal(r.anchorRange![0].getUTCMonth(), 2); // 0-indexed → March
  });

  it("resolves bare month to previous year when month is in the future", () => {
    // NOW=2026-05-20, month=novembro → 2025 (future this year, fallback prev)
    const r = detectTemporal("o que aconteceu em novembro", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.anchorRange![0].getUTCFullYear(), 2025);
    assert.equal(r.anchorRange![0].getUTCMonth(), 10);
  });

  it("detects adverbial without anchor (delegates to E13 path)", () => {
    const r = detectTemporal("quando o salience foi ativado", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
    assert.equal(r.anchor, null);
    assert.equal(r.anchorRange, null);
  });

  it("does NOT trigger on non-temporal queries", () => {
    const cases = [
      "como funciona monkey-patch do Issue 62028",
      "qual modelo Gemini usar como default",
      "o que é nox-mem",
      "", // empty
      "a", // too short
    ];
    for (const q of cases) {
      const r = detectTemporal(q, NOW_MS);
      assert.equal(r.isTemporal, false, `expected non-temporal: "${q}"`);
    }
  });

  it("detects EN month names", () => {
    const r = detectTemporal("what happened in April 2026", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "month_year");
    assert.equal(r.anchorRange![0].getUTCFullYear(), 2026);
    assert.equal(r.anchorRange![0].getUTCMonth(), 3);
  });

  it("detects bare year as wide-range anchor", () => {
    const r = detectTemporal("milestones do projeto 2025", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "year");
    assert.equal(r.anchorRange![0].toISOString().slice(0, 10), "2025-01-01");
  });
});

describe("proximityDelta", () => {
  const anchor = new Date(Date.UTC(2026, 3, 25)); // 2026-04-25

  it("returns 0.5 at Δdays=0 (max bump)", () => {
    const d = proximityDelta("2026-04-25", anchor, 30);
    assert.ok(Math.abs(d - 0.5) < 0.001, `expected ~0.5, got ${d}`);
  });

  it("decays gaussian-shaped with distance", () => {
    const d30 = proximityDelta("2026-05-25", anchor, 30); // Δ=30 days = 1σ → 0.5 * e^(-0.5) ≈ 0.303
    assert.ok(d30 > 0.29 && d30 < 0.32, `expected ~0.30 at 1σ, got ${d30}`);
    const d60 = proximityDelta("2026-06-24", anchor, 30); // Δ=60 days = 2σ → 0.5 * e^(-2) ≈ 0.068
    assert.ok(d60 > 0.05 && d60 < 0.08, `expected ~0.07 at 2σ, got ${d60}`);
    assert.ok(d60 < d30, "decay must be monotonic");
  });

  it("returns 0 for missing date or anchor", () => {
    assert.equal(proximityDelta(null, anchor, 30), 0);
    assert.equal(proximityDelta(undefined, anchor, 30), 0);
    assert.equal(proximityDelta("2026-04-25", null, 30), 0);
    assert.equal(proximityDelta("not-a-date", anchor, 30), 0);
  });

  it("falls back to σ=30 when sigmaDays <= 0", () => {
    const d = proximityDelta("2026-04-25", anchor, 0);
    assert.ok(Math.abs(d - 0.5) < 0.001);
  });
});

describe("rerankByTemporalProximity", () => {
  // Fixture: 4 results, scores descending (RRF-fused-ish numbers).
  // Anchor 2026-04-25 should boost the chunk dated 2026-04-25 (currently #3)
  // above ones dated far from anchor.
  const baseResults: RerankableResult[] = [
    { score: 100, source_date: "2025-01-15", chunk_id: "A" },
    { score: 90, source_date: "2026-01-10", chunk_id: "B" },
    { score: 80, source_date: "2026-04-25", chunk_id: "C" }, // gold for "2026-04-25" anchor
    { score: 70, source_date: null, created_at: "2026-04-26", chunk_id: "D" }, // proxy via created_at
  ];

  it("is no-op in mode=off regardless of query", () => {
    const { results, report } = rerankByTemporalProximity(
      baseResults,
      "primeira lição do incident reindex 2026-04-25",
      { mode: "off" },
      NOW_MS,
    );
    assert.deepEqual(
      results.map((r) => r.score),
      baseResults.map((r) => r.score),
    );
    assert.equal(report.applied, false);
  });

  it("is no-op when query is non-temporal even in active mode", () => {
    const { results, report } = rerankByTemporalProximity(
      baseResults,
      "como funciona o monkey-patch",
      { mode: "active" },
      NOW_MS,
    );
    assert.equal(report.isTemporal, false);
    assert.equal(report.applied, false);
    assert.deepEqual(
      results.map((r) => r.score),
      baseResults.map((r) => r.score),
    );
  });

  it("shadow mode computes report but does NOT mutate scores", () => {
    const { results, report } = rerankByTemporalProximity(
      baseResults,
      "primeira lição do incident 2026-04-25",
      { mode: "shadow", sigmaDays: 30, kRerank: 20 },
      NOW_MS,
    );
    assert.equal(report.isTemporal, true);
    assert.equal(report.applied, false);
    assert.equal(report.anchorIso, "2026-04-25");
    assert.equal(report.kReranked, 4);
    // scores unchanged
    assert.deepEqual(
      results.map((r) => r.score),
      baseResults.map((r) => r.score),
    );
  });

  it("active mode reorders by proximity (gold rises to top)", () => {
    const { results, report } = rerankByTemporalProximity(
      baseResults,
      "primeira lição do incident 2026-04-25",
      { mode: "active", sigmaDays: 30, kRerank: 20 },
      NOW_MS,
    );
    assert.equal(report.applied, true);
    // PATCH 3 (gap-aware): bump = dayFactor * max(top1 - score, 0.1)
    //   C: delta≈0.5 → dayFactor=1; gap = 100-80 = 20  → bump=20 → C=100
    //   D: delta≈0.499 → dayFactor≈0.998; gap = 100-70 = 30 → bump≈29.94 → D≈99.94
    //   B: delta≈near 0 (Δ≈105d, σ=30) → dayFactor≈0 → bump≈0.0x → B≈90
    //   A: idx=0 → bump forced to 0 → A=100
    // Expected sort: A(100) > C(100) > D(99.94) > B(90)
    const dResult = results.find((r) => r.chunk_id === "D")!;
    assert.ok(dResult.score > 99, `D score must close gap to top: got ${dResult.score}`);
    const cResult = results.find((r) => r.chunk_id === "C")!;
    assert.ok(cResult.score >= 100, `C score must reach top: got ${cResult.score}`);
    // C and D both surpass B (was 90, mid-pack pre-patch)
    const bResult = results.find((r) => r.chunk_id === "B")!;
    assert.ok(cResult.score > bResult.score, "C must outrank B post-rerank");
    assert.ok(dResult.score > bResult.score, "D must outrank B post-rerank");
    assert.equal(results.length, 4);
  });

  it("adverbial-only query with dispersed top-K dates does NOT trigger rerank", () => {
    // Dispersed dates: A 2025-01, B 2026-01, C 2026-04, D 2026-04 → no >=50% majority
    // (max single YYYY-MM = 2 of 4 = 50% exact → ceil(4*0.5)=2, threshold met!)
    // Use truly dispersed dates instead:
    const dispersed: RerankableResult[] = [
      { score: 100, source_date: "2024-01-15", chunk_id: "A" },
      { score: 90, source_date: "2025-06-10", chunk_id: "B" },
      { score: 80, source_date: "2026-04-25", chunk_id: "C" },
      { score: 70, source_date: "2026-11-01", chunk_id: "D" },
    ];
    const { results, report } = rerankByTemporalProximity(
      dispersed,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    assert.equal(report.isTemporal, true);
    assert.equal(report.signalSource, "adverbial"); // not promoted (no majority)
    assert.equal(report.applied, false); // no anchor → no rerank
    assert.deepEqual(
      results.map((r) => r.score),
      dispersed.map((r) => r.score),
    );
  });

  // ── PATCH 2 tests ─────────────────────────────────────────────────────────
  it("adverbial-only with majority top-K month promotes to adverbial_inferred and reranks", () => {
    // Majority: 3/4 results em 2026-04 → infer anchor 2026-04-15
    const majorityResults: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" }, // outlier
      { score: 90, source_date: "2026-04-10", chunk_id: "B" },
      { score: 80, source_date: "2026-04-20", chunk_id: "C" },
      { score: 70, source_date: "2026-04-30", chunk_id: "D" },
    ];
    const { results, report } = rerankByTemporalProximity(
      majorityResults,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    assert.equal(report.isTemporal, true);
    assert.equal(report.signalSource, "adverbial_inferred");
    assert.equal(report.anchorIso, "2026-04-15");
    assert.equal(report.applied, true);
    // chunks de 2026-04 devem subir; B/C/D must outrank A in final order? Not necessarily:
    // A starts at 100, doesn't get boost (created_at outlier), B/C/D get boosts proportional to gap.
    // Verify at least B/C/D scores moved (boost applied).
    const b = results.find((r) => r.chunk_id === "B")!;
    const c = results.find((r) => r.chunk_id === "C")!;
    const d = results.find((r) => r.chunk_id === "D")!;
    assert.ok(b.score > 90 || c.score > 80 || d.score > 70, "at least one in-month chunk must boost");
  });
});

// ─── PATCH 2 unit tests for inferAnchorFromTopK ──────────────────────────────

describe("inferAnchorFromTopK (PATCH 2)", () => {
  it("returns mid-month ISO when majority share same YYYY-MM", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: "2026-04-10", chunk_id: "x" },
      { score: 0, source_date: "2026-04-22", chunk_id: "y" },
      { score: 0, source_date: "2026-04-28", chunk_id: "z" },
      { score: 0, source_date: "2025-01-01", chunk_id: "w" },
    ];
    assert.equal(inferAnchorFromTopK(r, 5), "2026-04-15");
  });

  it("returns null when dates are dispersed (no >=50% majority)", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: "2024-01-15", chunk_id: "a" },
      { score: 0, source_date: "2025-06-10", chunk_id: "b" },
      { score: 0, source_date: "2026-04-25", chunk_id: "c" },
      { score: 0, source_date: "2026-11-01", chunk_id: "d" },
    ];
    assert.equal(inferAnchorFromTopK(r, 5), null);
  });

  it("returns null when fewer than 2 dates available", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: "2026-04-10", chunk_id: "x" },
      { score: 0, source_date: null, chunk_id: "y" },
    ];
    assert.equal(inferAnchorFromTopK(r, 5), null);
  });

  it("uses created_at when source_date is null", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: null, created_at: "2026-04-10", chunk_id: "x" },
      { score: 0, source_date: null, created_at: "2026-04-20", chunk_id: "y" },
      { score: 0, source_date: "2025-01-01", chunk_id: "z" },
    ];
    assert.equal(inferAnchorFromTopK(r, 5), "2026-04-15");
  });

  it("returns null on empty input", () => {
    assert.equal(inferAnchorFromTopK([], 5), null);
  });
});

// ─── PATCH 1 unit tests for new detector patterns ────────────────────────────

describe("detectTemporal — PATCH 1 patterns", () => {
  it("detects 'data em que X foi Y' as adverbial (Q107 gap)", () => {
    const r = detectTemporal("data em que o salience foi ativado", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
    assert.equal(r.anchor, null);
  });

  it("detects 'dia em que' as adverbial", () => {
    const r = detectTemporal("dia em que o reindex incident aconteceu", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
  });

  it("detects 'momento em que' as adverbial", () => {
    const r = detectTemporal("momento em que decidimos pivotar pra Q/A/P", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
  });

  it("detects EN 'date when' as adverbial", () => {
    const r = detectTemporal("the date when nox-mem v3.7 shipped", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
  });

  it("detects EN 'day when' as adverbial", () => {
    const r = detectTemporal("the day when we deployed temporal spike", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
  });

  it("detects EN 'moment when' as adverbial", () => {
    const r = detectTemporal("the moment when retrieval broke", NOW_MS);
    assert.equal(r.isTemporal, true);
    assert.equal(r.signalSource, "adverbial");
  });
});

// ─── PATCH 3 unit tests for proximityBoost ───────────────────────────────────

describe("proximityBoost (PATCH 3)", () => {
  it("returns 0 when delta gaussian is 0 or negative", () => {
    assert.equal(proximityBoost(0, 10), 0);
    assert.equal(proximityBoost(-0.1, 10), 0);
  });

  it("max boost when delta=0.5 (gaussian max) equals gap * baseFactor", () => {
    // dayFactor = min(0.5*2, 1) = 1; bump = 1 * gap = gap
    assert.equal(proximityBoost(0.5, 20), 20);
    assert.equal(proximityBoost(0.5, 20, 2.0), 40);
  });

  it("monotonic: closer day (larger delta) yields larger boost for same gap", () => {
    const closer = proximityBoost(0.45, 10); // ~1σ gaussian-ish
    const farther = proximityBoost(0.1, 10); // far away
    assert.ok(closer > farther, `closer must boost more: ${closer} vs ${farther}`);
  });

  it("floors scoreGap at 0.1 to avoid zero bump in ties", () => {
    const b = proximityBoost(0.5, 0); // gap=0 → floored to 0.1
    assert.ok(b > 0.09 && b < 0.11, `expected ~0.1, got ${b}`);
  });

  it("clamps dayFactor at 1 when delta exceeds 0.5 (defensive)", () => {
    // delta can't normally exceed 0.5, but defensively cap dayFactor
    const b = proximityBoost(1.0, 10); // dayFactor capped at 1
    assert.equal(b, 10);
  });
});
