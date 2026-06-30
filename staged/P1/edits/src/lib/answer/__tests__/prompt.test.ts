/**
 * src/lib/answer/__tests__/prompt.test.ts
 *
 * Focused tests for prompt assembly (T3). 10+ cases covering:
 *   - system prompt content (anti-hallucination clause, citation rule)
 *   - chunk marker preservation in user prompt
 *   - empty context → fallback indicator
 *   - long context → truncation honours char budget
 *   - chunk ordering in rendered prompt = marker_id ascending
 *   - retry prompt uses STRICT MODE language
 *   - deterministic snapshot (same inputs → same outputs)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { buildPrompt, buildRetryPrompt } from "../prompt.js";
import type { RetrievedChunk } from "../types.js";

function mkChunk(i: number, content: string, score: number): RetrievedChunk {
  return {
    chunk_id: i * 100,
    marker_id: `chunk_${i}`,
    file_path: `f${i}.md`,
    content,
    score,
  };
}

describe("buildPrompt — system prompt", () => {
  it("anti-hallucination guard present", () => {
    const { system } = buildPrompt("q", [mkChunk(1, "x", 1)]);
    assert.ok(system.includes("Answer ONLY"));
    assert.ok(system.includes("no memory matches"));
  });

  it("explicit citation rule present", () => {
    const { system } = buildPrompt("q", [mkChunk(1, "x", 1)]);
    assert.ok(system.includes("Cite EVERY"));
    assert.ok(system.includes("[chunk_N]"));
    assert.ok(system.includes("Never invent"));
  });
});

describe("buildPrompt — user prompt", () => {
  it("preserves chunk markers verbatim", () => {
    const chunks = [
      mkChunk(1, "alpha content", 0.9),
      mkChunk(2, "beta content", 0.7),
      mkChunk(3, "gamma content", 0.5),
    ];
    const { user } = buildPrompt("test question", chunks);
    assert.ok(user.includes("[chunk_1] alpha content"));
    assert.ok(user.includes("[chunk_2] beta content"));
    assert.ok(user.includes("[chunk_3] gamma content"));
  });

  it("includes the question verbatim", () => {
    const { user } = buildPrompt("Why is salience recency × pain × importance?", [
      mkChunk(1, "x", 1),
    ]);
    assert.ok(user.includes("Why is salience recency × pain × importance?"));
  });

  it("empty chunks produces fallback indicator", () => {
    const { user } = buildPrompt("q", []);
    assert.ok(user.includes("(No context retrieved.)"));
  });

  it("renders chunks in marker_id ascending order even if input score-sorted", () => {
    const chunks = [
      mkChunk(3, "third", 0.9), // highest score
      mkChunk(1, "first", 0.5),
      mkChunk(2, "second", 0.7),
    ];
    const { user } = buildPrompt("q", chunks);
    const i1 = user.indexOf("[chunk_1]");
    const i2 = user.indexOf("[chunk_2]");
    const i3 = user.indexOf("[chunk_3]");
    assert.ok(i1 < i2);
    assert.ok(i2 < i3);
  });

  it("truncates lowest-score chunks first when over budget", () => {
    // Very small token budget — forces truncation.
    const big = "x".repeat(2000);
    const chunks = [
      mkChunk(1, big, 0.95), // high score — keep
      mkChunk(2, big, 0.05), // low score — drop
      mkChunk(3, big, 0.5),
    ];
    const { user } = buildPrompt("q", chunks, /*maxTokens*/ 900);
    assert.ok(user.includes("[chunk_1]"), "highest score kept");
    assert.ok(!user.includes("[chunk_2]"), "lowest score dropped");
  });

  it("keeps at least one chunk even when budget < single-chunk size", () => {
    const enormous = "x".repeat(50_000);
    const chunks = [mkChunk(1, enormous, 0.95)];
    const { user } = buildPrompt("q", chunks, /*maxTokens*/ 100);
    assert.ok(user.includes("[chunk_1]"), "must keep ≥1 chunk");
  });

  it("deterministic: same input → same output", () => {
    const chunks = [mkChunk(1, "alpha", 0.9), mkChunk(2, "beta", 0.7)];
    const a = buildPrompt("q", chunks);
    const b = buildPrompt("q", chunks);
    assert.strictEqual(a.system, b.system);
    assert.strictEqual(a.user, b.user);
  });
});

describe("buildRetryPrompt", () => {
  it("uses STRICT MODE language", () => {
    const { system } = buildRetryPrompt("q", [mkChunk(1, "x", 1)]);
    assert.ok(system.includes("STRICT MODE"));
  });

  it("same user-prompt layout as buildPrompt", () => {
    const chunks = [mkChunk(1, "alpha", 0.9), mkChunk(2, "beta", 0.7)];
    const a = buildPrompt("q", chunks);
    const b = buildRetryPrompt("q", chunks);
    // System differs by design; user prompt content is identical.
    assert.strictEqual(a.user, b.user);
    assert.notStrictEqual(a.system, b.system);
  });

  it("reaffirms zero-hallucination contract", () => {
    const { system } = buildRetryPrompt("q", [mkChunk(1, "x", 1)]);
    assert.ok(system.includes("only cite markers literally listed"));
    assert.ok(system.includes("Do NOT speculate"));
  });
});
