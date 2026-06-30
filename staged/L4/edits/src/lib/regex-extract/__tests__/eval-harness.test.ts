/**
 * T8 — Tests for eval harness (eval/regex-vs-llm.ts).
 *
 * Covers: metrics calculation, cost cap, CSV formatting, summary aggregation,
 * file collection, and synthetic corpus correctness.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  computeMetrics,
  runRegexExtraction,
  computeSummary,
  formatCsvRow,
  CSV_HEADER,
  SYNTHETIC_SAMPLES,
  MAX_FILES,
  MAX_TOKENS_PER_FILE,
  COST_PER_TOKEN_USD,
  type FileSampleResult,
  type ExtractedRelation,
} from "../../../../eval/regex-vs-llm.js";

// ---------------------------------------------------------------------------
// computeMetrics
// ---------------------------------------------------------------------------

test("metrics: perfect match → precision=1, recall=1, f1=1", () => {
  const gt: ExtractedRelation[] = [
    { targetSlug: "feedback/foo", relationType: "references" },
    { targetSlug: "decision/d1", relationType: "references" },
  ];
  const regex: ExtractedRelation[] = [
    { targetSlug: "feedback/foo", relationType: "references" },
    { targetSlug: "decision/d1", relationType: "references" },
  ];
  const m = computeMetrics(regex, gt);
  assert.equal(m.precision, 1.0);
  assert.equal(m.recall, 1.0);
  assert.equal(m.f1, 1.0);
});

test("metrics: regex finds nothing, gt is non-empty → recall=0", () => {
  const gt: ExtractedRelation[] = [{ targetSlug: "feedback/foo", relationType: "references" }];
  const m = computeMetrics([], gt);
  assert.equal(m.recall, 0);
  assert.equal(m.truePositives, 0);
  assert.equal(m.falseNegatives, 1);
});

test("metrics: regex has false positives → precision < 1", () => {
  const gt: ExtractedRelation[] = [{ targetSlug: "feedback/foo", relationType: "references" }];
  const regex: ExtractedRelation[] = [
    { targetSlug: "feedback/foo", relationType: "references" },
    { targetSlug: "decision/bogus", relationType: "references" },
  ];
  const m = computeMetrics(regex, gt);
  assert.ok(m.precision < 1.0);
  assert.equal(m.recall, 1.0);
  assert.equal(m.falsePositives, 1);
});

test("metrics: both empty → precision=1, recall=1 (trivially correct)", () => {
  const m = computeMetrics([], []);
  assert.equal(m.precision, 1.0);
  assert.equal(m.recall, 1.0);
  assert.equal(m.f1, 1.0);
});

test("metrics: no gt (gt=[]) with regex hits → precision=0", () => {
  const m = computeMetrics(
    [{ targetSlug: "feedback/fp", relationType: "references" }],
    [],
  );
  assert.equal(m.precision, 0.0);
  assert.equal(m.falsePositives, 1);
});

// ---------------------------------------------------------------------------
// runRegexExtraction
// ---------------------------------------------------------------------------

test("runRegexExtraction: wikilinks extracted correctly", () => {
  const rels = runRegexExtraction("see [[feedback/no_secrets]] and [[decision/d41]]");
  assert.ok(rels.some((r) => r.targetSlug === "feedback/no_secrets"));
  assert.ok(rels.some((r) => r.targetSlug === "decision/d41"));
});

test("runRegexExtraction: frontmatter relations included", () => {
  const content = "---\nreferences: [feedback/a]\nagent: atlas\n---\n";
  const rels = runRegexExtraction(content);
  assert.ok(rels.some((r) => r.targetSlug === "feedback/a" && r.relationType === "references"));
  assert.ok(rels.some((r) => r.relationType === "is_agent_of"));
});

test("runRegexExtraction: deduplicates same slug", () => {
  const rels = runRegexExtraction("[[feedback/x]] and [[feedback/x]]");
  const hits = rels.filter((r) => r.targetSlug === "feedback/x");
  assert.equal(hits.length, 1);
});

// ---------------------------------------------------------------------------
// Cost + cap constants
// ---------------------------------------------------------------------------

test("cost cap: MAX_FILES=200 and MAX_TOKENS_PER_FILE=500", () => {
  assert.equal(MAX_FILES, 200);
  assert.equal(MAX_TOKENS_PER_FILE, 500);
});

test("cost cap: total max cost ≤ $0.01 (200 × 500 × rate)", () => {
  const maxCost = MAX_FILES * MAX_TOKENS_PER_FILE * COST_PER_TOKEN_USD;
  assert.ok(maxCost < 0.01, `Expected <$0.01 but got $${maxCost}`);
});

// ---------------------------------------------------------------------------
// computeSummary
// ---------------------------------------------------------------------------

function makeSampleResult(
  overrides: Partial<FileSampleResult> = {},
): FileSampleResult {
  return {
    fileId: "test-001",
    filePath: "/test/file.md",
    contentLength: 100,
    regexRelations: [],
    llmRelations: null,
    metrics: null,
    latency: { regex: 5, llm: null },
    estimatedLlmCostUsd: null,
    llmSkipped: true,
    ...overrides,
  };
}

test("computeSummary: empty results returns zeros", () => {
  const s = computeSummary([]);
  assert.equal(s.totalFiles, 0);
  assert.equal(s.macroPrecision, 0);
});

test("computeSummary: macro averages computed correctly", () => {
  const results = [
    makeSampleResult({ metrics: { precision: 1.0, recall: 1.0, f1: 1.0, truePositives: 1, falsePositives: 0, falseNegatives: 0 } }),
    makeSampleResult({ metrics: { precision: 0.5, recall: 0.5, f1: 0.5, truePositives: 1, falsePositives: 1, falseNegatives: 1 } }),
  ];
  const s = computeSummary(results);
  assert.equal(s.filesWithLlm, 2);
  assert.ok(Math.abs(s.macroPrecision - 0.75) < 0.001);
  assert.ok(Math.abs(s.macroF1 - 0.75) < 0.001);
});

// ---------------------------------------------------------------------------
// CSV formatting
// ---------------------------------------------------------------------------

test("formatCsvRow: outputs correct number of columns", () => {
  const r = makeSampleResult({ regexRelations: [{ targetSlug: "feedback/x", relationType: "references" }] });
  const row = formatCsvRow(r);
  const cols = row.split(",");
  const headerCols = CSV_HEADER.split(",");
  assert.equal(cols.length, headerCols.length);
});

// ---------------------------------------------------------------------------
// Synthetic corpus
// ---------------------------------------------------------------------------

test("synthetic corpus: has exactly 20 samples", () => {
  assert.equal(SYNTHETIC_SAMPLES.length, 20);
});

test("synthetic corpus: all samples have id, content, groundTruth", () => {
  for (const s of SYNTHETIC_SAMPLES) {
    assert.ok(s.id, "missing id");
    assert.ok(typeof s.content === "string", "content must be string");
    assert.ok(Array.isArray(s.groundTruth), "groundTruth must be array");
  }
});

test("synthetic corpus: syn-004 (pure prose) has empty ground truth", () => {
  const s = SYNTHETIC_SAMPLES.find((x) => x.id === "syn-004");
  assert.ok(s);
  assert.equal(s!.groundTruth.length, 0);
});

test("synthetic corpus: syn-001 regex extraction matches expected slugs", () => {
  const s = SYNTHETIC_SAMPLES.find((x) => x.id === "syn-001");
  assert.ok(s);
  const rels = runRegexExtraction(s!.content);
  const slugs = new Set(rels.map((r) => r.targetSlug));
  // syn-001 has feedback/no_secrets, decision/d41, and agent frontmatter
  assert.ok(slugs.has("feedback/no_secrets"), "expected feedback/no_secrets");
  assert.ok(slugs.has("decision/d41"), "expected decision/d41");
});
