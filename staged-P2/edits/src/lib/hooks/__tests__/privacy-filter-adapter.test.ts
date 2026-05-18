/**
 * T3 tests — privacy-filter-adapter.ts (Layer 3)
 *
 * 10 cases covering:
 *  - identity redact: no PII → capture=true, redaction_count=0
 *  - mock redact with PII: ctx.redacted populated, capture=true (redact policy)
 *  - drop policy: redaction_count>0 → capture=false
 *  - drop policy with no PII: capture=true
 *  - kinds dedup (set semantics)
 *  - exception in redact() → capture=false (fail closed)
 *  - empty content
 *  - very long content (no truncation by adapter)
 *  - ctx.redacted shape stability
 *  - reason string contains layer name
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { applyPrivacyFilter, identityRedact, type RedactFn } from "../privacy-filter-adapter.js";
import type { HookContext, HookEvent } from "../types.js";

function mkCtx(content: string): HookContext {
  const event: HookEvent = {
    event_id: "e",
    source: "openclaw",
    role: "user",
    content,
    session_id: "s",
    project_slug: "p",
    ts: "2026-05-18T00:00:00Z",
  };
  return { event, trace: [] };
}

const mockRedact: RedactFn = (s) => {
  let count = 0;
  const kinds = new Set<string>();
  let text = s;
  if (text.includes("sk-")) {
    text = text.replace(/sk-[a-zA-Z0-9_-]+/g, "<private>");
    count++;
    kinds.add("openai-key");
  }
  if (text.includes("AKIA")) {
    text = text.replace(/AKIA[A-Z0-9]+/g, "<private>");
    count++;
    kinds.add("aws-key");
  }
  return { text, redactionCount: count, kinds: Array.from(kinds) };
};

describe("T3 privacy-filter-adapter (Layer 3)", () => {
  it("identity redact: clean text passes through", () => {
    const ctx = mkCtx("hello world this is fine");
    const dec = applyPrivacyFilter(ctx, { redact: identityRedact });
    assert.equal(dec.capture, true);
    assert.equal(ctx.redacted?.redaction_count, 0);
    assert.equal(ctx.redacted?.text, "hello world this is fine");
  });

  it("mock redact with PII under redact policy: capture continues", () => {
    const ctx = mkCtx("here is sk-test-12345 secret");
    const dec = applyPrivacyFilter(ctx, { redact: mockRedact });
    assert.equal(dec.capture, true);
    assert.equal(ctx.redacted?.redaction_count, 1);
    assert.ok(ctx.redacted?.text.includes("<private>"));
    assert.ok(!ctx.redacted?.text.includes("sk-test-12345"));
  });

  it("drop policy: redaction_count>0 → capture=false", () => {
    const ctx = mkCtx("token: sk-real-deadbeef");
    const dec = applyPrivacyFilter(ctx, { redact: mockRedact, dropOnDetect: true });
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /pii_detected/);
  });

  it("drop policy + no PII → capture=true", () => {
    const ctx = mkCtx("normal sentence with words");
    const dec = applyPrivacyFilter(ctx, { redact: mockRedact, dropOnDetect: true });
    assert.equal(dec.capture, true);
  });

  it("multiple PII kinds → kinds dedupe to set", () => {
    const ctx = mkCtx("two keys: sk-aaaa and AKIABBBB also sk-cccc");
    const dec = applyPrivacyFilter(ctx, { redact: mockRedact });
    assert.equal(dec.capture, true);
    assert.equal(ctx.redacted?.kinds.length, 2);
    assert.ok(ctx.redacted?.kinds.includes("openai-key"));
    assert.ok(ctx.redacted?.kinds.includes("aws-key"));
  });

  it("redact throws → capture=false (fail closed)", () => {
    const ctx = mkCtx("any");
    const throwingRedact: RedactFn = () => {
      throw new Error("boom");
    };
    const dec = applyPrivacyFilter(ctx, { redact: throwingRedact });
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /threw/);
  });

  it("empty content: no PII, no error", () => {
    const ctx = mkCtx("");
    const dec = applyPrivacyFilter(ctx, { redact: identityRedact });
    assert.equal(dec.capture, true);
    assert.equal(ctx.redacted?.redaction_count, 0);
  });

  it("very long content does not get truncated by adapter", () => {
    const big = "abc ".repeat(10_000);
    const ctx = mkCtx(big);
    const dec = applyPrivacyFilter(ctx, { redact: identityRedact });
    assert.equal(dec.capture, true);
    assert.equal(ctx.redacted?.text.length, big.length);
  });

  it("ctx.redacted shape stable", () => {
    const ctx = mkCtx("hello");
    applyPrivacyFilter(ctx, { redact: identityRedact });
    assert.ok("text" in (ctx.redacted ?? {}));
    assert.ok("redaction_count" in (ctx.redacted ?? {}));
    assert.ok("kinds" in (ctx.redacted ?? {}));
  });

  it("reason string mentions privacy-filter layer", () => {
    const ctx = mkCtx("text");
    const dec = applyPrivacyFilter(ctx, { redact: identityRedact });
    assert.equal(dec.layer, "privacy-filter");
  });
});
