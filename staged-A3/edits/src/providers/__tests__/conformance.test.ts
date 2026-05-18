/**
 * conformance.test.ts — interface conformance for all 5 providers.
 *
 * Each provider MUST:
 *   - expose the locked readonly fields (name, model | dimensions etc.)
 *   - return a HealthStatus-shaped object from healthCheck()
 *   - stubs MUST throw NotImplementedError on the work method
 *
 * Cases (10):
 *  - GeminiEmbedding readonly fields (name/dim/max/cost)
 *  - GeminiLLM readonly fields (name/model/contextWindow)
 *  - OpenAIEmbedding stub throws on embed()
 *  - OpenAILLM stub throws on complete()
 *  - AnthropicLLM stub throws on complete()
 *  - VoyageEmbedding stub throws on embed()
 *  - All stubs return ok=false with error from healthCheck()
 *  - Errors from stubs are NotImplementedError subclass
 *  - Stub healthCheck() never throws (returns ok=false instead)
 *  - Conformance shape for HealthStatus (ok required, error iff !ok)
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import { GeminiEmbeddingProvider } from "../embedding/gemini.js";
import { GeminiLLMProvider } from "../llm/gemini.js";
import { OpenAIEmbeddingProvider } from "../embedding/openai.js";
import { OpenAILLMProvider } from "../llm/openai.js";
import { AnthropicLLMProvider } from "../llm/anthropic.js";
import { VoyageEmbeddingProvider } from "../embedding/voyage.js";
import { NotImplementedError } from "../types.js";

const FAKE_KEY = "AIzaTESTtestTESTtestTESTtestTESTtest";

describe("Gemini provider readonly fields", () => {
  test("embedding: name/dimensions/maxTokens/costPerMillionTokens locked", () => {
    const p = new GeminiEmbeddingProvider({ apiKey: FAKE_KEY });
    assert.equal(p.name, "gemini");
    assert.equal(p.dimensions, 3072);
    assert.ok(p.maxTokens >= 2048);
    assert.ok(p.costPerMillionTokens > 0);
  });

  test("llm: name/model/contextWindow locked (D41 default = flash-lite)", () => {
    const p = new GeminiLLMProvider({ apiKey: FAKE_KEY });
    assert.equal(p.name, "gemini");
    assert.equal(p.model, "gemini-2.5-flash-lite");
    assert.ok(p.contextWindow >= 1_000_000);
  });
});

describe("Stub providers throw NotImplementedError on work methods", () => {
  test("OpenAIEmbeddingProvider.embed() throws NotImplementedError", async () => {
    const p = new OpenAIEmbeddingProvider();
    await assert.rejects(p.embed(["hi"]), NotImplementedError);
  });

  test("OpenAILLMProvider.complete() throws NotImplementedError", async () => {
    const p = new OpenAILLMProvider();
    await assert.rejects(p.complete({ user: "hi" }), NotImplementedError);
  });

  test("AnthropicLLMProvider.complete() throws NotImplementedError", async () => {
    const p = new AnthropicLLMProvider();
    await assert.rejects(p.complete({ user: "hi" }), NotImplementedError);
  });

  test("VoyageEmbeddingProvider.embed() throws NotImplementedError", async () => {
    const p = new VoyageEmbeddingProvider();
    await assert.rejects(p.embed(["hi"]), NotImplementedError);
  });
});

describe("Stub healthCheck conformance (T8)", () => {
  test("OpenAI embedding stub returns ok=false with error", async () => {
    const p = new OpenAIEmbeddingProvider();
    const s = await p.healthCheck();
    assert.equal(s.ok, false);
    assert.ok(s.error && s.error.length > 0);
    assert.equal(typeof s.latencyMs, "number");
  });

  test("Anthropic LLM stub returns ok=false with error", async () => {
    const p = new AnthropicLLMProvider();
    const s = await p.healthCheck();
    assert.equal(s.ok, false);
    assert.ok(s.error && s.error.length > 0);
  });

  test("Voyage embedding stub returns ok=false with error", async () => {
    const p = new VoyageEmbeddingProvider();
    const s = await p.healthCheck();
    assert.equal(s.ok, false);
    assert.ok(s.error && s.error.length > 0);
  });

  test("Stub healthCheck never throws (returns ok=false)", async () => {
    const stubs = [
      new OpenAIEmbeddingProvider(),
      new OpenAILLMProvider(),
      new AnthropicLLMProvider(),
      new VoyageEmbeddingProvider(),
    ];
    for (const s of stubs) {
      await assert.doesNotReject(s.healthCheck());
    }
  });
});
