/**
 * T9 — Integration tests for production wire-up (production-wire.ts).
 *
 * 11 tests covering:
 *  - Confidence scoring per relation type
 *  - Fast-path skip decision (threshold=0.8)
 *  - Bare-ref falls through to LLM (confidence=0.75 < 0.8)
 *  - Frontmatter typed links skip LLM (confidence=0.95 ≥ 0.8)
 *  - Wikilink/md-link skip LLM (confidence=0.90 ≥ 0.8)
 *  - Dedup merge: regex wins over LLM for same triple
 *  - filterHighConfidence filters below threshold
 *  - Env flags isRegexEnabled / isSkipGeminiEnabled
 *  - Telemetry extraction_method propagated correctly
 */

import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  runProductionFastPath,
  filterHighConfidence,
  mergeWithLlmRelations,
  relationDedupKey,
  isRegexEnabled,
  isSkipGeminiEnabled,
  CONFIDENCE_THRESHOLD,
  CONFIDENCE_FRONTMATTER,
  CONFIDENCE_EXPLICIT_LINK,
  CONFIDENCE_BARE_REF,
  scoreEntityRef,
  scoreFrontmatterRelation,
} from "../production-wire.js";
import type { EntityRef, FrontmatterRelation } from "../types.js";

// ---------------------------------------------------------------------------
// scoreEntityRef / scoreFrontmatterRelation
// ---------------------------------------------------------------------------

test("score: wikilink → CONFIDENCE_EXPLICIT_LINK (0.90)", () => {
  const ref: EntityRef = {
    entityType: "feedback",
    slug: "no_secrets",
    key: "feedback/no_secrets",
    source: "wikilink",
  };
  assert.equal(scoreEntityRef(ref), CONFIDENCE_EXPLICIT_LINK);
  assert.ok(CONFIDENCE_EXPLICIT_LINK >= CONFIDENCE_THRESHOLD);
});

test("score: markdown_link → CONFIDENCE_EXPLICIT_LINK (0.90)", () => {
  const ref: EntityRef = {
    entityType: "decision",
    slug: "d41",
    key: "decision/d41",
    source: "markdown_link",
  };
  assert.equal(scoreEntityRef(ref), CONFIDENCE_EXPLICIT_LINK);
});

test("score: bare_ref → CONFIDENCE_BARE_REF (0.75) — below gate threshold", () => {
  const ref: EntityRef = {
    entityType: "feedback",
    slug: "bare_slug",
    key: "feedback/bare_slug",
    source: "bare_ref",
  };
  assert.equal(scoreEntityRef(ref), CONFIDENCE_BARE_REF);
  assert.ok(CONFIDENCE_BARE_REF < CONFIDENCE_THRESHOLD);
});

test("score: frontmatter relation → CONFIDENCE_FRONTMATTER (0.95)", () => {
  const rel: FrontmatterRelation = {
    relationType: "is_agent_of",
    target: "agent/atlas",
    raw: "atlas",
  };
  assert.equal(scoreFrontmatterRelation(rel), CONFIDENCE_FRONTMATTER);
  assert.ok(CONFIDENCE_FRONTMATTER >= CONFIDENCE_THRESHOLD);
});

// ---------------------------------------------------------------------------
// runProductionFastPath — skip logic
// ---------------------------------------------------------------------------

test("fast-path: wikilink in compiled section → skipLlm=true", () => {
  const result = runProductionFastPath(
    {
      section: "compiled",
      type: "entity",
      content: "see [[feedback/no_secrets]] always",
    },
    "decision/d41",
  );
  assert.equal(result.skipLlm, true);
  assert.ok(result.maxConfidence >= CONFIDENCE_THRESHOLD);
  assert.equal(result.regexRelations.length, 1);
  assert.equal(result.regexRelations[0]?.targetSlug, "feedback/no_secrets");
});

test("fast-path: frontmatter typed link in frontmatter section → skipLlm=true", () => {
  const result = runProductionFastPath(
    {
      section: "frontmatter",
      type: "entity",
      content: "---\nagent: atlas\n---",
    },
    "feedback/src",
  );
  assert.equal(result.skipLlm, true);
  assert.ok(result.maxConfidence >= CONFIDENCE_THRESHOLD);
  const rel = result.regexRelations[0];
  assert.equal(rel?.relationType, "is_agent_of");
  assert.equal(rel?.relation_reason, "regex_extracted");
});

test("fast-path: bare_ref only → skipLlm=false (confidence 0.75 < threshold 0.8)", () => {
  // Bare refs have confidence 0.75. But the section gate also matters:
  // in compiled section with ≥1 ref, decideExtraction says skipGemini=true.
  // However our confidence gate overrides: maxConfidence must also be ≥ 0.8.
  // Bare refs produce 0.75 → combined gate fails → skipLlm=false.
  const result = runProductionFastPath(
    {
      section: "compiled",
      type: "entity",
      content: "see feedback/no_secrets here", // bare_ref only
    },
    "decision/src",
  );
  // Max confidence = 0.75 (bare_ref) < 0.80 threshold → skipLlm=false.
  assert.equal(result.skipLlm, false);
  assert.equal(result.maxConfidence, CONFIDENCE_BARE_REF);
});

test("fast-path: prose section forces LLM even with explicit links", () => {
  const result = runProductionFastPath(
    {
      section: "prose",
      type: "spec",
      content: "[[feedback/foo]] explicit link",
    },
    "decision/src",
  );
  // prose section is not eligible for skip (decideExtraction returns skipGemini=false).
  assert.equal(result.skipLlm, false);
});

test("fast-path: no relations at all → skipLlm=false, maxConfidence=0", () => {
  const result = runProductionFastPath(
    {
      section: "compiled",
      type: "entity",
      content: "pure prose with no entity links whatsoever",
    },
    "feedback/src",
  );
  assert.equal(result.skipLlm, false);
  assert.equal(result.maxConfidence, 0);
  assert.equal(result.regexRelations.length, 0);
});

test("fast-path: telemetry extraction_method set correctly when skipLlm=true", () => {
  const result = runProductionFastPath(
    {
      section: "compiled",
      type: "entity",
      content: "[[decision/d1]]",
    },
    "feedback/src",
  );
  assert.equal(result.telemetry.extraction_method, "regex_only");
  assert.equal(result.telemetry.gemini_call_skipped, true);
});

// ---------------------------------------------------------------------------
// filterHighConfidence + mergeWithLlmRelations
// ---------------------------------------------------------------------------

test("filterHighConfidence: removes below-threshold, keeps above", () => {
  const rels = [
    { sourceSlug: "s", targetSlug: "t1", relationType: "r", confidence: 0.95, extraction_method: "regex" as const, relation_reason: "regex_extracted" as const },
    { sourceSlug: "s", targetSlug: "t2", relationType: "r", confidence: 0.75, extraction_method: "regex" as const, relation_reason: "regex_extracted" as const },
  ];
  const filtered = filterHighConfidence(rels);
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0]?.targetSlug, "t1");
});

test("mergeWithLlmRelations: regex wins dedup for same triple", () => {
  const regexRels = [
    { sourceSlug: "s", targetSlug: "t1", relationType: "references", confidence: 0.9, extraction_method: "regex" as const, relation_reason: "regex_extracted" as const },
  ];
  const llmRels = [
    { sourceSlug: "s", targetSlug: "t1", relationType: "references" },
    { sourceSlug: "s", targetSlug: "t2", relationType: "references" },
  ];
  const merged = mergeWithLlmRelations(regexRels, llmRels);
  // t1 deduped → regex wins, t2 added from LLM
  assert.equal(merged.length, 2);
  const t1 = merged.find((r) => r.targetSlug === "t1");
  assert.equal(t1?.extraction_method, "regex");
  const t2 = merged.find((r) => r.targetSlug === "t2");
  assert.equal(t2?.extraction_method, "llm");
  assert.equal(t2?.relation_reason, "gemini_extracted");
});

// ---------------------------------------------------------------------------
// Env flags
// ---------------------------------------------------------------------------

test("env flags: isRegexEnabled reads NOX_L4_REGEX_ENABLED", () => {
  const originalEnv = process.env["NOX_L4_REGEX_ENABLED"];
  try {
    process.env["NOX_L4_REGEX_ENABLED"] = "1";
    assert.equal(isRegexEnabled(), true);
    process.env["NOX_L4_REGEX_ENABLED"] = "0";
    assert.equal(isRegexEnabled(), false);
    delete process.env["NOX_L4_REGEX_ENABLED"];
    assert.equal(isRegexEnabled(), false);
  } finally {
    if (originalEnv === undefined) {
      delete process.env["NOX_L4_REGEX_ENABLED"];
    } else {
      process.env["NOX_L4_REGEX_ENABLED"] = originalEnv;
    }
  }
});
