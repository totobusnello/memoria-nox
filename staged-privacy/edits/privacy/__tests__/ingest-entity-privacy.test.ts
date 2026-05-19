/**
 * privacy/__tests__/ingest-entity-privacy.test.ts
 *
 * Integration-style tests for the privacy redaction hook applied in
 * src/ingest-entity.ts (follow-up Wave Q).
 *
 * These tests verify that when ingestEntityFile() processes each entity
 * section (frontmatter, compiled, timeline), the redact() pipeline fires
 * correctly on each section text before it would reach INSERT INTO chunks.
 *
 * Strategy: we do NOT need a real SQLite DB. We simulate the three-section
 * data flow that ingest-entity.ts produces and assert redact() behaviour
 * on each, matching exactly how the hook is wired (per ingest-entity.patch.md).
 *
 * All secret values are SYNTHETIC TEST FIXTURES — no real credentials present.
 * gitleaks:allow — test fixtures only
 *
 * Runner: node:test (node --test dist/privacy/__tests__/ingest-entity-privacy.test.js)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { redact } from "../filter.js";

// ─── Shared fake key fixture ──────────────────────────────────────────────────
// This is a syntactically-valid but entirely fake Anthropic key token.
// It must be ≥20 chars after "sk-ant-" to match the pattern.
const FAKE_ANT_KEY = "sk-ant-oat-FAKEKEY00000000000000000000000000000000"; // gitleaks:allow

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Simulate what ingest-entity.ts does for each section:
 * apply redact() and return { text, redacted: boolean }.
 * The hook is: const _r = redact(sectionText); sectionText = _r.text;
 */
function applyPrivacyHook(sectionText: string): {
  text: string;
  redactionCount: number;
  kinds: string[];
} {
  return redact(sectionText);
}

// ─── Section: compiled (body — highest risk) ──────────────────────────────────

describe("ingest-entity compiled section — privacy hook", () => {
  it("redacts Anthropic API key in compiled body", () => {
    const compiled = [
      "## Credentials rotated",
      `Old key was: ${FAKE_ANT_KEY}`,
      "Replaced with new key on 2026-05-18.",
    ].join("\n");

    const result = applyPrivacyHook(compiled);

    assert.ok(result.redactionCount > 0, "Expected at least one redaction in compiled body");
    assert.ok(
      result.kinds.includes("anthropic-key") || result.kinds.includes("env-secret"),
      `Expected anthropic-key or env-secret kind, got: [${result.kinds.join(", ")}]`
    );
    assert.ok(
      !result.text.includes(FAKE_ANT_KEY),
      "Raw fake key must NOT appear in redacted text"
    );
    assert.ok(
      result.text.includes("[REDACTED:anthropic-key]") ||
        result.text.includes("[REDACTED:env-secret]"),
      "Output must contain [REDACTED:...] placeholder"
    );
  });

  it("redacts ANTHROPIC_API_KEY=... env-style assignment in compiled", () => {
    // gitleaks:allow — synthetic test fixture
    const compiled = `ANTHROPIC_API_KEY=${FAKE_ANT_KEY}\nOPENAI_API_KEY=sk-EXAMPLEKEY1234567890abcdef`;

    const result = applyPrivacyHook(compiled);

    assert.ok(result.redactionCount >= 2, `Expected ≥2 redactions, got ${result.redactionCount}`);
    assert.ok(!result.text.includes(FAKE_ANT_KEY), "Anthropic key must be redacted");
    assert.ok(!result.text.includes("sk-EXAMPLEKEY1234567890abcdef"), "OpenAI key must be redacted");
  });

  it("clean compiled body passes through unchanged", () => {
    const compiled = [
      "## Team member",
      "Name: Alice",
      "Role: Staff Engineer",
      "Joined: 2025-01-10",
    ].join("\n");

    const result = applyPrivacyHook(compiled);

    assert.strictEqual(result.redactionCount, 0, "Clean body must produce zero redactions");
    assert.strictEqual(result.text, compiled, "Text must be returned unchanged when clean");
  });
});

// ─── Section: frontmatter ─────────────────────────────────────────────────────

describe("ingest-entity frontmatter section — privacy hook", () => {
  it("redacts leaked token in frontmatter YAML value", () => {
    // Frontmatter rarely has secrets but we must handle it defensively.
    const frontmatter = [
      "---",
      "type: credential-rotation",
      `api_key: ${FAKE_ANT_KEY}`, // gitleaks:allow
      "date: 2026-05-18",
      "---",
    ].join("\n");

    const result = applyPrivacyHook(frontmatter);

    assert.ok(result.redactionCount > 0, "Leaked token in frontmatter must be redacted");
    assert.ok(
      !result.text.includes(FAKE_ANT_KEY),
      "Raw fake key must NOT appear in redacted frontmatter"
    );
  });

  it("clean frontmatter with metadata-only fields is not affected", () => {
    const frontmatter = [
      "---",
      "type: person",
      "slug: alice-smith",
      "tags: [engineering, backend]",
      "updated: 2026-05-18",
      "---",
    ].join("\n");

    const result = applyPrivacyHook(frontmatter);

    assert.strictEqual(result.redactionCount, 0, "Clean frontmatter must not be touched");
    assert.strictEqual(result.text, frontmatter);
  });
});

// ─── Section: timeline ────────────────────────────────────────────────────────

describe("ingest-entity timeline section — privacy hook", () => {
  it("redacts key accidentally logged in timeline event", () => {
    const timeline = [
      "## Timeline",
      "### 2026-05-18",
      "- Rotated credentials.",
      `- Previous: ${FAKE_ANT_KEY}`, // gitleaks:allow
      "- New key provisioned.",
    ].join("\n");

    const result = applyPrivacyHook(timeline);

    assert.ok(result.redactionCount > 0, "Timeline event with key must trigger redaction");
    assert.ok(!result.text.includes(FAKE_ANT_KEY), "Key must be removed from timeline text");
  });

  it("clean timeline with dates and notes is not affected", () => {
    const timeline = [
      "## Timeline",
      "### 2026-04-01",
      "- Initial entity created.",
      "### 2026-05-18",
      "- Updated compiled section.",
    ].join("\n");

    const result = applyPrivacyHook(timeline);

    assert.strictEqual(result.redactionCount, 0, "Clean timeline must not be touched");
    assert.strictEqual(result.text, timeline);
  });
});

// ─── Cross-section: all 3 sections processed independently ───────────────────

describe("all 3 sections processed independently (as ingest-entity.ts does)", () => {
  it("redacts in compiled only — frontmatter and timeline untouched", () => {
    const sections = {
      frontmatter: "---\ntype: person\nslug: alice\n---",
      compiled: `Key: ${FAKE_ANT_KEY}`, // gitleaks:allow
      timeline: "## Timeline\n### 2026-05-18\n- Created.",
    };

    const results = {
      frontmatter: applyPrivacyHook(sections.frontmatter),
      compiled: applyPrivacyHook(sections.compiled),
      timeline: applyPrivacyHook(sections.timeline),
    };

    // Only compiled triggered redaction
    assert.strictEqual(results.frontmatter.redactionCount, 0, "frontmatter must be clean");
    assert.ok(results.compiled.redactionCount > 0, "compiled must have redaction");
    assert.strictEqual(results.timeline.redactionCount, 0, "timeline must be clean");

    // The key is gone from compiled
    assert.ok(!results.compiled.text.includes(FAKE_ANT_KEY));
    // The other sections are verbatim
    assert.strictEqual(results.frontmatter.text, sections.frontmatter);
    assert.strictEqual(results.timeline.text, sections.timeline);
  });

  it("multiple secrets across all 3 sections are each redacted", () => {
    // gitleaks:allow — all synthetic
    const sections = {
      frontmatter: `---\ntoken: ${FAKE_ANT_KEY}\n---`,
      compiled: "GITHUB_TOKEN=ghp_EXAMPLETOKEN1234567890abcdefghij",
      timeline: "## Timeline\n- Rotated: AIzaSyEXAMPLEKEY1234567890abcdefghij123", // gitleaks:allow
    };

    const rFrontmatter = applyPrivacyHook(sections.frontmatter);
    const rCompiled = applyPrivacyHook(sections.compiled);
    const rTimeline = applyPrivacyHook(sections.timeline);

    assert.ok(rFrontmatter.redactionCount > 0, "frontmatter key redacted");
    assert.ok(rCompiled.redactionCount > 0, "compiled GitHub token redacted");
    assert.ok(rTimeline.redactionCount > 0, "timeline Gemini key redacted");

    assert.ok(!rFrontmatter.text.includes(FAKE_ANT_KEY));
    assert.ok(!rCompiled.text.includes("ghp_EXAMPLETOKEN1234567890abcdefghij"));
    assert.ok(!rTimeline.text.includes("AIzaSyEXAMPLEKEY1234567890abcdefghij123")); // gitleaks:allow
  });
});

// ─── <private> tag in entity file ────────────────────────────────────────────

describe("<private> tag in entity file sections", () => {
  it("strips <private> block inside compiled section", () => {
    const compiled = [
      "## Notes",
      "Public info: Alice is Staff Engineer.",
      "<private>Personal detail: born 1990, SSN redacted.</private>",
      "End of section.",
    ].join("\n");

    const result = applyPrivacyHook(compiled);

    assert.ok(result.redactionCount > 0, "private tag must trigger redaction");
    assert.ok(result.kinds.includes("user-marked"), "kind must be user-marked");
    assert.ok(!result.text.includes("Personal detail"), "private content must be removed");
    assert.ok(result.text.includes("Public info"), "public content must survive");
  });
});

// ─── Warn telemetry shape ─────────────────────────────────────────────────────

describe("redaction telemetry used for console.warn in hook", () => {
  it("returns redactionCount and kinds needed for the warn log", () => {
    // The hook does:
    //   if (_r.redactionCount > 0) console.warn(`[privacy-filter] redacted ${_r.redactionCount} secret(s)...`)
    const text = `Leaked: ${FAKE_ANT_KEY}`; // gitleaks:allow
    const _r = applyPrivacyHook(text);

    // Verify the fields the warn log needs exist
    assert.ok(typeof _r.redactionCount === "number", "redactionCount must be a number");
    assert.ok(Array.isArray(_r.kinds), "kinds must be an array");
    assert.ok(_r.redactionCount > 0, "must detect secret for warn path");
    assert.ok(_r.kinds.length > 0, "kinds must be non-empty when count > 0");
  });
});
