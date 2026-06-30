/**
 * e2e-real.test.ts — E2E real-providers test (T14, gated).
 *
 * GATED: requires `NOX_E2E_REAL_PROVIDERS=1` + relevant API keys.
 * All tests skip with clear reason if env/keys missing.
 *
 * Cost cap: tiny inputs, MAX_TOKENS=10 to minimize spend.
 *
 * Cases:
 *  - Gemini embedding: real embed call → Float32Array of dim 3072
 *  - Gemini LLM: real complete() call → non-empty text response
 *  - (OpenAI / Anthropic / Voyage: skipped until A3.1 — stubs only)
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import { GeminiEmbeddingProvider } from "../embedding/gemini.js";
import { GeminiLLMProvider } from "../llm/gemini.js";

const E2E_ENABLED = process.env.NOX_E2E_REAL_PROVIDERS === "1";
const GEMINI_KEY = process.env.GEMINI_API_KEY ?? "";

/** Skip helper: returns `true` if the test should run. */
function shouldRun(requiredKey: string, keyName: string): boolean {
  if (!E2E_ENABLED) return false;
  if (!requiredKey) {
    console.log(`[e2e-real] SKIP: ${keyName} not set`);
    return false;
  }
  return true;
}

describe("E2E real providers (gated: NOX_E2E_REAL_PROVIDERS=1)", () => {
  test("Gemini embedding — real embed, dim 3072", { skip: !shouldRun(GEMINI_KEY, "GEMINI_API_KEY") }, async () => {
    const p = new GeminiEmbeddingProvider({ apiKey: GEMINI_KEY });
    const results = await p.embed(["hello world"]);
    assert.equal(results.length, 1);
    const v = results[0];
    assert.ok(v instanceof Float32Array, "should return Float32Array");
    assert.equal(v.length, 3072);
    // Sanity: vector should not be all zeros.
    const nonZero = Array.from(v).some((x) => x !== 0);
    assert.ok(nonZero, "embedding should have non-zero values");
  });

  test("Gemini LLM — real complete(), non-empty response", { skip: !shouldRun(GEMINI_KEY, "GEMINI_API_KEY") }, async () => {
    const p = new GeminiLLMProvider({ apiKey: GEMINI_KEY });
    const result = await p.complete({
      user: "Say 'yes'.",
      maxTokens: 10,
      temperature: 0,
    });
    assert.ok(result.text.length > 0, "should return non-empty text");
    assert.ok(result.tokensIn > 0, "should report input tokens");
    assert.ok(result.tokensOut > 0, "should report output tokens");
    assert.ok(result.latencyMs > 0, "should report latency");
  });

  test("Gemini health check — real network call", { skip: !shouldRun(GEMINI_KEY, "GEMINI_API_KEY") }, async () => {
    const p = new GeminiEmbeddingProvider({ apiKey: GEMINI_KEY });
    const status = await p.healthCheck();
    assert.equal(status.ok, true, `health check should pass, got error: ${status.error}`);
    assert.ok((status.latencyMs ?? 0) > 0, "latency should be > 0 on real call");
  });

  // Stubs: verify they are still stubs (A3.1 guard).
  test("OpenAI stub does NOT hit network even with OPENAI_API_KEY set", async () => {
    // This test always runs — verifies stubs don't accidentally become live.
    const { OpenAIEmbeddingProvider } = await import("../embedding/openai.js");
    const { NotImplementedError } = await import("../types.js");
    const p = new OpenAIEmbeddingProvider({ apiKey: process.env.OPENAI_API_KEY ?? "dummy" });
    await assert.rejects(p.embed(["test"]), NotImplementedError);
  });

  test("Anthropic stub does NOT hit network even with ANTHROPIC_API_KEY set", async () => {
    const { AnthropicLLMProvider } = await import("../llm/anthropic.js");
    const { NotImplementedError } = await import("../types.js");
    const p = new AnthropicLLMProvider({ apiKey: process.env.ANTHROPIC_API_KEY ?? "dummy" });
    await assert.rejects(p.complete({ user: "test" }), NotImplementedError);
  });
});
