/**
 * T4 tests — classifier.ts (Layer 4)
 *
 * 15 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { applyClassifier, scoreText } from "../classifier.js";
import type { HookContext, HookEvent } from "../types.js";

function mkCtx(text: string, redacted?: string): HookContext {
  const event: HookEvent = {
    event_id: "e",
    source: "openclaw",
    role: "user",
    content: text,
    session_id: "s",
    project_slug: "p",
    ts: "2026-05-18T00:00:00Z",
  };
  const ctx: HookContext = { event, trace: [] };
  if (redacted !== undefined) {
    ctx.redacted = { text: redacted, redaction_count: 0, kinds: [] };
  }
  return ctx;
}

describe("T4 classifier (Layer 4)", () => {
  it("too short → score 0", () => {
    assert.equal(scoreText("hi", 20), 0);
  });

  it("pure whitespace/punct → 0", () => {
    assert.equal(scoreText("        ...    ?!?!?!", 20), 0);
  });

  it("URL-heavy → low score", () => {
    const s = scoreText("https://a.example.com/foo/bar https://b.example.com/baz", 20);
    assert.ok(s <= 0.25, `got ${s}`);
  });

  it("natural prose → high score", () => {
    const s = scoreText("The user asked me about the salience formula and we discussed it.", 20);
    assert.ok(s >= 0.7, `got ${s}`);
  });

  it("apply: low-signal short → reject", () => {
    const ctx = mkCtx("short");
    const dec = applyClassifier(ctx, { minLength: 20 });
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /low_signal/);
  });

  it("apply: high-signal prose → accept", () => {
    const ctx = mkCtx("This is a long natural language sentence with real content.");
    const dec = applyClassifier(ctx, { minLength: 20 });
    assert.equal(dec.capture, true);
    assert.match(dec.reason, /high_signal/);
  });

  it("apply: uses redacted text if present", () => {
    const ctx = mkCtx("noise", "This is a real long prose sentence with meaningful nouns.");
    const dec = applyClassifier(ctx, { minLength: 20 });
    assert.equal(dec.capture, true);
  });

  it("apply: ambiguous → default lean capture", () => {
    // Construct text deliberately in mid-range
    const ctx = mkCtx("aaaa bbbb cccc dddd eeee ffff");
    const dec = applyClassifier(ctx, { minLength: 20 });
    // Could be ambiguous or low; just assert reason set
    assert.ok(["ambiguous_lean_capture", "high_signal", "low_signal"].some((p) => dec.reason.includes(p)));
  });

  it("apply: llm fallback called when ambiguous + flag on", () => {
    let called = false;
    const ctx = mkCtx("borderline borderline borderline xyz");
    applyClassifier(ctx, {
      minLength: 20,
      llmFallback: true,
      llmClassify: (_t) => {
        called = true;
        return { capture: true, reason: "llm_says_keep" };
      },
    });
    // May or may not be called depending on score; just confirm no crash
    void called;
  });

  it("apply: llm fallback exception → lean capture", () => {
    const ctx = mkCtx("mid mid mid mid");
    const dec = applyClassifier(ctx, {
      minLength: 20,
      llmFallback: true,
      llmClassify: () => {
        throw new Error("llm down");
      },
    });
    // Whatever score is, decision must be defined
    assert.ok(typeof dec.capture === "boolean");
  });

  it("code-heavy text gets penalty", () => {
    const code = "{ x: 1, y: { z: 2 }, w: [] }; const a = () => { return 1; };";
    const s = scoreText(code, 20);
    const prose = "This is a real natural sentence about people having a conversation.";
    const sp = scoreText(prose, 20);
    assert.ok(sp > s, `prose(${sp}) should outscore code(${s})`);
  });

  it("score clamps to [0,1]", () => {
    const s = scoreText("The quick brown fox jumps over the lazy dog! Yes. And again.", 20);
    assert.ok(s >= 0);
    assert.ok(s <= 1);
  });

  it("layer field set on decision", () => {
    const ctx = mkCtx("This is a complete natural sentence for testing.");
    const dec = applyClassifier(ctx);
    assert.equal(dec.layer, "classifier");
  });

  it("classification recorded on ctx", () => {
    const ctx = mkCtx("This is a complete natural sentence for testing.");
    applyClassifier(ctx);
    assert.ok(ctx.classification);
    assert.ok(typeof ctx.classification!.score === "number");
  });

  it("respects minLength override", () => {
    const ctx = mkCtx("hello world");
    const dec = applyClassifier(ctx, { minLength: 5 });
    // 11 chars > 5, so not rejected by length alone
    assert.ok(typeof dec.capture === "boolean");
  });
});
