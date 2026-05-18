import { test } from "node:test";
import assert from "node:assert/strict";
import { decideExtraction, mergeRelations } from "../ingest-router-l4.js";

test("router: compiled section + 1 ref → skipGemini=true (regex_only)", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "entity",
    content: "see [[feedback/no_secrets]] always",
  });
  assert.equal(d.skipGemini, true);
  assert.equal(d.telemetry.extraction_method, "regex_only");
  assert.equal(d.regexRelationsCount, 1);
});

test("router: frontmatter section + agent → skipGemini=true", () => {
  const d = decideExtraction({
    section: "frontmatter",
    type: "entity",
    content: "---\nagent: atlas\n---",
  });
  assert.equal(d.skipGemini, true);
  assert.equal(d.regex.frontmatterRelations.length, 1);
});

test("router: timeline section + ref → skipGemini=true", () => {
  const d = decideExtraction({
    section: "timeline",
    type: "entity",
    content: "[[decision/d41]] decided",
  });
  assert.equal(d.skipGemini, true);
});

test("router: prose section → never skip (gemini_only path)", () => {
  // prose ∉ SKIP_ELIGIBLE_SECTIONS, so even with regex hits we fall to gemini_only.
  // regex_primary_gemini_secondary is reserved for section-eligible chunks that
  // still need Gemini for some other gate reason (e.g. mixed structured+prose,
  // not modeled here in v1).
  const d = decideExtraction({
    section: "prose",
    type: "spec",
    content: "see [[feedback/foo]]",
  });
  assert.equal(d.skipGemini, false);
  assert.equal(d.telemetry.extraction_method, "gemini_only");
});

test("router: conversation chunk type forces Gemini even with refs", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "conversation",
    content: "user said [[feedback/foo]]",
  });
  assert.equal(d.skipGemini, false);
});

test("router: daily_log type forces Gemini", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "daily_log",
    content: "today [[decision/d1]]",
  });
  assert.equal(d.skipGemini, false);
});

test("router: zero regex matches → gemini_only_after_regex_zero", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "entity",
    content: "pure prose with no entity refs at all here",
  });
  assert.equal(d.skipGemini, false);
  assert.equal(d.telemetry.extraction_method, "gemini_only_after_regex_zero");
});

test("router: null section → gemini_only (no skip eligibility)", () => {
  const d = decideExtraction({
    section: null,
    type: "other",
    content: "[[feedback/foo]] reference",
  });
  assert.equal(d.skipGemini, false);
  assert.equal(d.telemetry.extraction_method, "gemini_only");
});

test("router: telemetry latency populated", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "entity",
    content: "[[feedback/x]]",
  });
  assert.ok(d.telemetry.latency_ms.regex >= 0);
  assert.equal(d.telemetry.latency_ms.gemini, null);
});

test("router: code refs counted toward regexRelationsCount", () => {
  const d = decideExtraction({
    section: "compiled",
    type: "entity",
    content: "see src/lib/op-audit.ts:42 important",
  });
  assert.equal(d.regex.codeRefs.length, 1);
  assert.equal(d.regexRelationsCount, 1);
  assert.equal(d.skipGemini, true);
});

test("merge: dedupes (source|target|type) across regex+gemini", () => {
  const merged = mergeRelations(
    [
      {
        source: "feedback/a",
        target: "feedback/b",
        relationType: "references",
        extraction_method: "regex",
      },
    ],
    [
      {
        source: "feedback/a",
        target: "feedback/b",
        relationType: "references",
        extraction_method: "gemini",
      },
      {
        source: "feedback/a",
        target: "feedback/c",
        relationType: "references",
        extraction_method: "gemini",
      },
    ],
  );
  assert.equal(merged.length, 2);
  assert.equal(merged[0]?.extraction_method, "regex"); // regex wins (earlier in input)
});

test("merge: case-insensitive dedup", () => {
  const merged = mergeRelations(
    [
      {
        source: "Feedback/A",
        target: "Feedback/B",
        relationType: "References",
        extraction_method: "regex",
      },
    ],
    [
      {
        source: "feedback/a",
        target: "feedback/b",
        relationType: "references",
        extraction_method: "gemini",
      },
    ],
  );
  assert.equal(merged.length, 1);
});
