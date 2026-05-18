/**
 * T5 tests — rate-limit.ts (Layer 5)
 *
 * 12 cases covering token bucket + dedup.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  applyRateLimit,
  createState,
  charShingleCosine,
} from "../rate-limit.js";
import type { HookContext, HookEvent } from "../types.js";

function mkCtx(text: string): HookContext {
  const event: HookEvent = {
    event_id: "e",
    source: "openclaw",
    role: "user",
    content: text,
    session_id: "s",
    project_slug: "p",
    ts: "2026-05-18T00:00:00Z",
  };
  return { event, trace: [] };
}

describe("T5 rate-limit + dedup (Layer 5)", () => {
  it("createState: bucket starts full", () => {
    const s = createState(30, () => 0);
    assert.equal(s.tokens, 30);
    assert.equal(s.recent.length, 0);
  });

  it("first capture consumes one token", () => {
    let t = 0;
    const s = createState(5, () => t);
    const dec = applyRateLimit(mkCtx("hello world prose one"), s, {
      capacityPerMin: 5,
      now: () => t,
    });
    assert.equal(dec.capture, true);
    assert.ok(s.tokens < 5);
    assert.equal(s.recent.length, 1);
  });

  it("rate-limited after capacity exhausted", () => {
    let t = 0;
    const s = createState(2, () => t);
    for (let i = 0; i < 2; i++) {
      const dec = applyRateLimit(mkCtx(`uniq prose number ${i} xyz abc`), s, {
        capacityPerMin: 2,
        now: () => t,
      });
      assert.equal(dec.capture, true);
    }
    const dec = applyRateLimit(mkCtx("uniq prose number 99 xyz abc"), s, {
      capacityPerMin: 2,
      now: () => t,
    });
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /rate_limited/);
  });

  it("bucket refills over time", () => {
    let t = 0;
    const s = createState(2, () => t);
    // Exhaust
    applyRateLimit(mkCtx("first prose alpha beta gamma"), s, { capacityPerMin: 2, now: () => t });
    applyRateLimit(mkCtx("second prose alpha beta gamma"), s, { capacityPerMin: 2, now: () => t });
    // Advance 30s — half-refill
    t = 30_000;
    const dec = applyRateLimit(mkCtx("third prose alpha beta gamma"), s, {
      capacityPerMin: 2,
      now: () => t,
    });
    assert.equal(dec.capture, true);
  });

  it("dedup rejects near-identical", () => {
    let t = 0;
    const s = createState(10, () => t);
    applyRateLimit(mkCtx("the user asked about salience formula details"), s, {
      capacityPerMin: 10,
      dedupThreshold: 0.9,
      now: () => t,
    });
    const dec = applyRateLimit(
      mkCtx("the user asked about salience formula details"),
      s,
      { capacityPerMin: 10, dedupThreshold: 0.9, now: () => t },
    );
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /dedup_hit/);
  });

  it("dedup does not consume tokens", () => {
    let t = 0;
    const s = createState(2, () => t);
    applyRateLimit(mkCtx("repeated content alpha beta gamma delta"), s, {
      capacityPerMin: 2,
      dedupThreshold: 0.8,
      now: () => t,
    });
    const tokensBefore = s.tokens;
    applyRateLimit(mkCtx("repeated content alpha beta gamma delta"), s, {
      capacityPerMin: 2,
      dedupThreshold: 0.8,
      now: () => t,
    });
    assert.equal(s.tokens, tokensBefore, "dedup hit should not consume token");
  });

  it("ring buffer caps at ringSize", () => {
    let t = 0;
    const s = createState(10, () => t);
    for (let i = 0; i < 15; i++) {
      applyRateLimit(mkCtx(`unique prose alpha number ${i} text`), s, {
        capacityPerMin: 100,
        ringSize: 5,
        now: () => t,
      });
    }
    assert.ok(s.recent.length <= 5);
  });

  it("charShingleCosine: identical → 1.0", () => {
    assert.equal(charShingleCosine("hello world", "hello world"), 1);
  });

  it("charShingleCosine: empty strings → 0", () => {
    assert.equal(charShingleCosine("", "any"), 0);
    assert.equal(charShingleCosine("any", ""), 0);
  });

  it("charShingleCosine: totally different → low", () => {
    const c = charShingleCosine("abcdef", "xyz123");
    assert.ok(c < 0.5, `got ${c}`);
  });

  it("custom similarity injected respected", () => {
    let t = 0;
    const s = createState(5, () => t);
    applyRateLimit(mkCtx("anything text content here filler"), s, {
      capacityPerMin: 5,
      similarity: () => 1.0, // always match
      now: () => t,
    });
    const dec = applyRateLimit(mkCtx("completely different text now"), s, {
      capacityPerMin: 5,
      similarity: () => 1.0,
      now: () => t,
    });
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /dedup_hit/);
  });

  it("decision carries layer name", () => {
    let t = 0;
    const s = createState(5, () => t);
    const dec = applyRateLimit(mkCtx("plain text here for layer check"), s, {
      capacityPerMin: 5,
      now: () => t,
    });
    assert.equal(dec.layer, "rate-limit");
  });
});
