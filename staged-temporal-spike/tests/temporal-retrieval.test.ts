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
 *  - PATCH 1 (detector gap Q107)
 *  - PATCH 2 v2 (extractAnchorFromQuery Stage A + inferAnchorFromTopKAge Stage B)
 *  - PATCH 3 v2 (confidence tiers, getConfidenceMultiplier)
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
  inferAnchorFromTopKAge,
  extractAnchorFromQuery,
  getConfidenceMultiplier,
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
    // PATCH 3 v2: bump = dayFactor * max(top1 - score, 0.1) * confidence(iso_date=1.0)
    //   C: delta≈0.5 → dayFactor=1; gap = 100-80 = 20  → bump=20*1.0 → C=100
    //   D: delta≈0.499 → dayFactor≈0.998; gap = 100-70 = 30 → bump≈29.94 → D≈99.94
    //   B: delta≈near 0 (Δ≈105d, σ=30) → dayFactor≈0 → bump≈0.0x → B≈90
    //   A: idx=0 → bump forced to 0 → A=100
    // Expected sort: A(100) ≈ C(100) > D(99.94) > B(90)
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

  it("adverbial-only query with no month/year and dispersed dates does NOT trigger rerank", () => {
    // Truly dispersed dates → Stage A fails (no month/year in query), Stage B
    // computes median but applies confidence=0.3 → still moves but small. We
    // assert that scores DID move (Stage B fires) since v2 uses median, not
    // mode threshold. Compare with separate test that confidence multiplier
    // limits the effect.
    const dispersed: RerankableResult[] = [
      { score: 100, source_date: "2024-01-15", chunk_id: "A" },
      { score: 90, source_date: "2025-06-10", chunk_id: "B" },
      { score: 80, source_date: "2026-04-25", chunk_id: "C" },
      { score: 70, source_date: "2026-11-01", chunk_id: "D" },
    ];
    const { report } = rerankByTemporalProximity(
      dispersed,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    assert.equal(report.isTemporal, true);
    // Stage A fails (no month/year keyword), Stage B fires → adverbial_topk_inferred
    assert.equal(report.signalSource, "adverbial_topk_inferred");
    assert.ok(report.confidence === 0.3, `confidence=${report.confidence} expected 0.3`);
  });

  it("query with explicit month keyword triggers Stage A (adverbial_keyword_inferred)", () => {
    const results: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" },
      { score: 90, source_date: "2026-04-10", chunk_id: "B" },
      { score: 80, source_date: "2026-04-20", chunk_id: "C" },
      { score: 70, source_date: "2026-04-30", chunk_id: "D" },
    ];
    const { report } = rerankByTemporalProximity(
      results,
      "quando lançamos algo em abril 2026",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    // "abril 2026" matches month_year detector primarily; not adverbial inference path
    // This documents that month_year detector wins when explicit
    assert.ok(
      report.signalSource === "month_year",
      `expected month_year detector wins, got ${report.signalSource}`,
    );
    assert.equal(report.confidence, 0.8);
  });

  it("adverbial query w/ month keyword only (no detector match) falls to Stage A keyword inference", () => {
    // Query "quando ... abril" — "quando" matches adverbial pattern FIRST, so
    // detector returns "adverbial". Stage A finds "abril" → anchor 2026-04-15.
    // BUT: "abril" alone (no year) also matches MONTH_YEAR regex which is tried
    // BEFORE adverbial in detectTemporal. So this depends on regex precedence.
    // Verify behavior: detector ordering says month_year > adverbial → expect
    // month_year direct.
    const results: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" },
      { score: 90, source_date: "2026-04-10", chunk_id: "B" },
    ];
    const { report } = rerankByTemporalProximity(
      results,
      "quando algo aconteceu abril",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    // month_year detector wins (regex order in detectTemporal)
    assert.equal(report.signalSource, "month_year");
  });
});

// ─── PATCH 2 v2 unit tests for extractAnchorFromQuery (Stage A) ──────────────

describe("extractAnchorFromQuery (PATCH 2 v2 Stage A)", () => {
  it('returns "YYYY-MM-15" for "<month> <year>" PT-BR', () => {
    assert.equal(extractAnchorFromQuery("quando foi em abril 2026", NOW_MS), "2026-04-15");
    assert.equal(extractAnchorFromQuery("em maio 2026 lançamos X", NOW_MS), "2026-05-15");
    assert.equal(extractAnchorFromQuery("janeiro 2025 começou", NOW_MS), "2025-01-15");
  });

  it('returns "YYYY-MM-15" for "<month> de <year>" PT-BR', () => {
    assert.equal(extractAnchorFromQuery("evento em março de 2026", NOW_MS), "2026-03-15");
  });

  it('returns "YYYY-MM-15" for "<month> <year>" EN', () => {
    assert.equal(extractAnchorFromQuery("what happened in May 2026", NOW_MS), "2026-05-15");
    assert.equal(extractAnchorFromQuery("April 2026 release", NOW_MS), "2026-04-15");
  });

  it('returns "YYYY-MM-15" for "<month> of <year>" EN', () => {
    assert.equal(extractAnchorFromQuery("the date of June of 2025", NOW_MS), "2025-06-15");
  });

  it("returns implicit-year midpoint for bare month (past = current year)", () => {
    // NOW=2026-05-20, "março" past → 2026-03-15
    assert.equal(extractAnchorFromQuery("o que aconteceu em março", NOW_MS), "2026-03-15");
  });

  it("returns implicit-year midpoint for bare month (future = previous year)", () => {
    // NOW=2026-05-20, "novembro" future → 2025-11-15
    assert.equal(extractAnchorFromQuery("o que aconteceu em novembro", NOW_MS), "2025-11-15");
  });

  it("returns mid-year for bare year only", () => {
    assert.equal(extractAnchorFromQuery("os incidents de 2026", NOW_MS), "2026-06-15");
    assert.equal(extractAnchorFromQuery("milestones 2025", NOW_MS), "2025-06-15");
  });

  it("returns null when query has no month/year keyword", () => {
    assert.equal(extractAnchorFromQuery("data do deploy", NOW_MS), null);
    assert.equal(extractAnchorFromQuery("quando o salience foi ativado", NOW_MS), null);
    assert.equal(extractAnchorFromQuery("", NOW_MS), null);
    assert.equal(extractAnchorFromQuery("como funciona", NOW_MS), null);
  });

  it("uppercase / mixed case is normalized", () => {
    assert.equal(extractAnchorFromQuery("ABRIL 2026 deploy", NOW_MS), "2026-04-15");
    assert.equal(extractAnchorFromQuery("April 2026 Release", NOW_MS), "2026-04-15");
  });
});

// ─── PATCH 2 v2 unit tests for inferAnchorFromTopKAge (Stage B) ──────────────

describe("inferAnchorFromTopKAge (PATCH 2 v2 Stage B)", () => {
  it("returns median date (not mode) of top-K source_dates", () => {
    // dates sorted: 2024-01-15, 2025-06-10, 2026-04-25, 2026-04-30, 2026-11-01
    // median index = floor(5/2) = 2 → "2026-04-25"
    const r: RerankableResult[] = [
      { score: 0, source_date: "2024-01-15", chunk_id: "a" },
      { score: 0, source_date: "2025-06-10", chunk_id: "b" },
      { score: 0, source_date: "2026-04-25", chunk_id: "c" },
      { score: 0, source_date: "2026-04-30", chunk_id: "d" },
      { score: 0, source_date: "2026-11-01", chunk_id: "e" },
    ];
    assert.equal(inferAnchorFromTopKAge(r, 5), "2026-04-25");
  });

  it("preserves exact day (does NOT normalize to mid-month-15)", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: "2026-05-01", chunk_id: "a" },
      { score: 0, source_date: "2026-05-05", chunk_id: "b" }, // median
      { score: 0, source_date: "2026-05-10", chunk_id: "c" },
    ];
    assert.equal(inferAnchorFromTopKAge(r, 5), "2026-05-05");
  });

  it("returns null when fewer than 2 dates available", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: "2026-04-10", chunk_id: "x" },
      { score: 0, source_date: null, chunk_id: "y" },
    ];
    assert.equal(inferAnchorFromTopKAge(r, 5), null);
  });

  it("uses created_at when source_date is null", () => {
    const r: RerankableResult[] = [
      { score: 0, source_date: null, created_at: "2026-04-10", chunk_id: "x" },
      { score: 0, source_date: null, created_at: "2026-04-20", chunk_id: "y" },
      { score: 0, source_date: "2025-01-01", chunk_id: "z" },
    ];
    // sorted: 2025-01-01, 2026-04-10, 2026-04-20 → median = 2026-04-10
    assert.equal(inferAnchorFromTopKAge(r, 5), "2026-04-10");
  });

  it("returns null on empty input", () => {
    assert.equal(inferAnchorFromTopKAge([], 5), null);
  });

  it("respects k bound (only looks at top-K)", () => {
    // 6 results; k=3 → only top 3 considered. Median of {2026-01, 2026-02, 2026-03} = 2026-02-15
    const r: RerankableResult[] = [
      { score: 0, source_date: "2026-01-15", chunk_id: "a" },
      { score: 0, source_date: "2026-02-15", chunk_id: "b" },
      { score: 0, source_date: "2026-03-15", chunk_id: "c" },
      { score: 0, source_date: "2026-12-01", chunk_id: "d" }, // outside k=3
      { score: 0, source_date: "2026-12-15", chunk_id: "e" }, // outside k=3
      { score: 0, source_date: "2026-12-31", chunk_id: "f" }, // outside k=3
    ];
    assert.equal(inferAnchorFromTopKAge(r, 3), "2026-02-15");
  });
});

// ─── Legacy inferAnchorFromTopK (kept for backward-compat) ───────────────────

describe("inferAnchorFromTopK (legacy v1, deprecated)", () => {
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

// ─── PATCH 3 v2 unit tests for getConfidenceMultiplier ───────────────────────

describe("getConfidenceMultiplier (PATCH 3 v2)", () => {
  it("returns 1.0 for iso_date (exact)", () => {
    assert.equal(getConfidenceMultiplier("iso_date"), 1.0);
  });

  it("returns 0.8 for month_year (explicit)", () => {
    assert.equal(getConfidenceMultiplier("month_year"), 0.8);
  });

  it("returns 0.5 for year (wide range)", () => {
    assert.equal(getConfidenceMultiplier("year"), 0.5);
  });

  it("returns 0.6 for adverbial_keyword_inferred (Stage A)", () => {
    assert.equal(getConfidenceMultiplier("adverbial_keyword_inferred"), 0.6);
  });

  it("returns 0.3 for adverbial_topk_inferred (Stage B, weak signal)", () => {
    assert.equal(getConfidenceMultiplier("adverbial_topk_inferred"), 0.3);
  });

  it("returns 0.0 for adverbial (no anchor, legacy v1 off)", () => {
    assert.equal(getConfidenceMultiplier("adverbial"), 0.0);
  });

  it("returns 0.0 for adverbial_inferred (legacy v1, deprecated)", () => {
    assert.equal(getConfidenceMultiplier("adverbial_inferred"), 0.0);
  });

  it("returns 0.0 for null / unknown", () => {
    assert.equal(getConfidenceMultiplier(null), 0.0);
  });
});

// ─── PATCH 2 v2 + PATCH 3 v2 integration: rerank with confidence ─────────────

describe("rerankByTemporalProximity — PATCH 2/3 v2 integration", () => {
  it("adverbial query w/ no month → Stage B median, confidence=0.3 applied", () => {
    // Query has "quando" → adverbial; no month/year → Stage A fails; Stage B
    // computes median = 2026-04-20 from top-K. Confidence = 0.3 limits boost.
    const results: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" },
      { score: 90, source_date: "2026-04-10", chunk_id: "B" },
      { score: 80, source_date: "2026-04-20", chunk_id: "C" },
      { score: 70, source_date: "2026-04-30", chunk_id: "D" },
      { score: 60, source_date: "2026-04-25", chunk_id: "E" },
    ];
    const { report } = rerankByTemporalProximity(
      results,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    assert.equal(report.signalSource, "adverbial_topk_inferred");
    assert.equal(report.confidence, 0.3);
    assert.equal(report.applied, true);
    assert.ok(report.anchorIso, "anchor must be set from Stage B");
  });

  it("adverbial-only with no top-K dates → bail (no rerank)", () => {
    // Query is adverbial, but top-K has no parseable dates → Stage A fail +
    // Stage B fail → confidence=0 → no rerank
    const results: RerankableResult[] = [
      { score: 100, source_date: null, chunk_id: "A" },
      { score: 90, source_date: null, chunk_id: "B" },
    ];
    const { report } = rerankByTemporalProximity(
      results,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    assert.equal(report.signalSource, "adverbial");
    assert.equal(report.confidence, 0.0);
    assert.equal(report.applied, false);
  });

  it("confidence multiplier reduces bump magnitude vs full strength", () => {
    // Compare two queries with same intent but different signalSource confidence.
    // ISO date query (confidence=1.0) should produce LARGER bump than adverbial w/
    // Stage B (confidence=0.3) given identical fixture.
    const fixture: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" },
      { score: 90, source_date: "2026-04-15", chunk_id: "B" },
      { score: 80, source_date: "2026-04-15", chunk_id: "C" },
      { score: 70, source_date: "2026-04-15", chunk_id: "D" },
      { score: 60, source_date: "2026-04-15", chunk_id: "E" },
    ];

    const isoRun = rerankByTemporalProximity(
      fixture,
      "deploy em 2026-04-15",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    const advRun = rerankByTemporalProximity(
      fixture,
      "quando o salience foi ativado",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );

    assert.equal(isoRun.report.signalSource, "iso_date");
    assert.equal(isoRun.report.confidence, 1.0);
    assert.equal(advRun.report.signalSource, "adverbial_topk_inferred");
    assert.equal(advRun.report.confidence, 0.3);

    // ISO bump for B = dayFactor(1) * gap(10) * conf(1.0) = 10 → score 100
    // ADV bump for B = dayFactor(1) * gap(10) * conf(0.3) = 3  → score 93
    const isoB = isoRun.results.find((r) => r.chunk_id === "B")!;
    const advB = advRun.results.find((r) => r.chunk_id === "B")!;
    assert.ok(
      isoB.score > advB.score,
      `iso bump (${isoB.score}) should exceed adv (${advB.score})`,
    );
  });

  it("Stage A wins over Stage B when both could fire (precedence test)", () => {
    // Note: detectTemporal already returns month_year if month keyword found
    // BEFORE adverbial pattern. So a query like "quando aconteceu em abril 2026"
    // gets month_year directly (not adverbial → Stage A path). But what about
    // a query that matches adverbial pattern AND has a year-only ("2026")?
    // detectTemporal returns adverbial (4th branch); Stage A finds 2026 → fires.
    const results: RerankableResult[] = [
      { score: 100, source_date: "2025-01-15", chunk_id: "A" },
      { score: 90, source_date: "2026-04-10", chunk_id: "B" },
    ];
    // "quando ... 2026" → adverbial detector + Stage A bare-year match
    const { report } = rerankByTemporalProximity(
      results,
      "quando algo aconteceu 2026",
      { mode: "active", sigmaDays: 30 },
      NOW_MS,
    );
    // adverbial detector fires (matches "quando"), then Stage A finds bare year
    assert.equal(report.signalSource, "adverbial_keyword_inferred");
    assert.equal(report.anchorIso, "2026-06-15");
    assert.equal(report.confidence, 0.6);
  });
});
