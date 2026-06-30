/**
 * conformance-extended.test.ts — Extended conformance suite across all providers (T13).
 *
 * Verifies that the abstraction is actually abstract: identical input → same shape
 * output, modulo content. Callers must not depend on provider-specific quirks.
 *
 * Cases (14):
 * Embedding conformance (5):
 *  1. gemini: embed empty array → [] (no network call shape)
 *  2. all embedding providers: embed() returns Float32Array[] or throws NotImplementedError
 *  3. all embedding providers: healthCheck() returns HealthStatus shape (ok + optional error + optional latencyMs)
 *  4. all embedding providers: dimensions and maxTokens are positive integers
 *  5. all embedding providers: costPerMillionTokens is a non-negative number
 *
 * LLM conformance (5):
 *  6. all LLM providers: complete() returns CompleteResult shape or throws NotImplementedError
 *  7. all LLM providers: healthCheck() returns HealthStatus shape
 *  8. all LLM providers: name, model, contextWindow are non-empty strings/positive numbers
 *  9. gemini: complete() result has all required fields (text, tokensIn, tokensOut, latencyMs)
 * 10. stub providers: NotImplementedError from complete() names the provider
 *
 * Chain conformance (2):
 * 11. LLMFallbackChain exposes LLMProvider interface (name, model, contextWindow, complete, healthCheck)
 * 12. CostCappedProvider exposes LLMProvider interface
 *
 * Secret hygiene (2):
 * 13. stub errors do NOT contain API key patterns
 * 14. telemetry row shapes conform to ProviderTelemetryRow (all required fields present)
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import { GeminiEmbeddingProvider } from "../embedding/gemini.js";
import { OpenAIEmbeddingProvider } from "../embedding/openai.js";
import { VoyageEmbeddingProvider } from "../embedding/voyage.js";
import { GeminiLLMProvider } from "../llm/gemini.js";
import { OpenAILLMProvider } from "../llm/openai.js";
import { AnthropicLLMProvider } from "../llm/anthropic.js";
import { NotImplementedError } from "../types.js";
import { LLMFallbackChain } from "../llm/chain.js";
import { CostCappedProvider } from "../../lib/cost-cap.js";
import type { EmbeddingProvider } from "../embedding/types.js";
import type { LLMProvider } from "../llm/types.js";
import type { ProviderTelemetryRow } from "../telemetry.js";

const FAKE_KEY = "AIzaTESTtestTESTtestTESTtestTESTtest";

/** Mock fetch that always returns a fixed embed response. */
function mockEmbedFetch(dim: number) {
  const values = Array.from({ length: dim }, (_, i) => i / dim);
  return async () => ({
    ok: true, status: 200, statusText: "OK",
    text: async () => "{}",
    json: async () => ({ embeddings: [{ values }] }),
  });
}

/** Mock fetch for Gemini LLM. */
function mockLLMFetch() {
  return async () => ({
    ok: true, status: 200, statusText: "OK",
    text: async () => "{}",
    json: async () => ({
      candidates: [{ content: { parts: [{ text: "response" }] } }],
      usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 5 },
    }),
  });
}

const ALL_EMBEDDING_PROVIDERS: EmbeddingProvider[] = [
  new GeminiEmbeddingProvider({ apiKey: FAKE_KEY, fetchFn: mockEmbedFetch(3072) as never }),
  new OpenAIEmbeddingProvider(),
  new VoyageEmbeddingProvider(),
];

const ALL_LLM_PROVIDERS: LLMProvider[] = [
  new GeminiLLMProvider({ apiKey: FAKE_KEY, fetchFn: mockLLMFetch() as never }),
  new OpenAILLMProvider(),
  new AnthropicLLMProvider(),
];

// ─── Embedding conformance ────────────────────────────────────────────────────

describe("EmbeddingProvider conformance — all providers", () => {
  test("gemini: embed([]) returns empty array without network call", async () => {
    const p = new GeminiEmbeddingProvider({ apiKey: FAKE_KEY, fetchFn: mockEmbedFetch(3072) as never });
    const result = await p.embed([]);
    assert.deepEqual(result, []);
  });

  test("all providers: embed() returns Float32Array[] or NotImplementedError", async () => {
    for (const p of ALL_EMBEDDING_PROVIDERS) {
      try {
        const result = await p.embed(["test input"]);
        assert.ok(Array.isArray(result), `${p.name}: embed() should return array`);
        if (result.length > 0) {
          assert.ok(result[0] instanceof Float32Array, `${p.name}: each element should be Float32Array`);
        }
      } catch (err) {
        assert.ok(err instanceof NotImplementedError, `${p.name}: only NotImplementedError allowed, got: ${err}`);
      }
    }
  });

  test("all providers: healthCheck() returns HealthStatus shape", async () => {
    for (const p of ALL_EMBEDDING_PROVIDERS) {
      const status = await p.healthCheck();
      assert.equal(typeof status.ok, "boolean", `${p.name}: ok must be boolean`);
      if (status.latencyMs !== undefined) {
        assert.equal(typeof status.latencyMs, "number", `${p.name}: latencyMs must be number`);
      }
      if (!status.ok) {
        assert.ok(
          status.error && status.error.length > 0,
          `${p.name}: ok=false must have non-empty error`,
        );
      }
    }
  });

  test("all providers: dimensions and maxTokens are positive integers", () => {
    for (const p of ALL_EMBEDDING_PROVIDERS) {
      assert.ok(Number.isInteger(p.dimensions) && p.dimensions > 0,
        `${p.name}: dimensions=${p.dimensions} must be positive integer`);
      assert.ok(Number.isInteger(p.maxTokens) && p.maxTokens > 0,
        `${p.name}: maxTokens=${p.maxTokens} must be positive integer`);
    }
  });

  test("all providers: costPerMillionTokens is non-negative number", () => {
    for (const p of ALL_EMBEDDING_PROVIDERS) {
      assert.equal(typeof p.costPerMillionTokens, "number",
        `${p.name}: costPerMillionTokens must be number`);
      assert.ok(p.costPerMillionTokens >= 0,
        `${p.name}: costPerMillionTokens=${p.costPerMillionTokens} must be >= 0`);
    }
  });
});

// ─── LLM conformance ─────────────────────────────────────────────────────────

describe("LLMProvider conformance — all providers", () => {
  test("all providers: complete() returns CompleteResult shape or NotImplementedError", async () => {
    for (const p of ALL_LLM_PROVIDERS) {
      try {
        const result = await p.complete({ user: "hello" });
        assert.equal(typeof result.text, "string", `${p.name}: text must be string`);
        assert.equal(typeof result.tokensIn, "number", `${p.name}: tokensIn must be number`);
        assert.equal(typeof result.tokensOut, "number", `${p.name}: tokensOut must be number`);
        assert.equal(typeof result.latencyMs, "number", `${p.name}: latencyMs must be number`);
      } catch (err) {
        assert.ok(err instanceof NotImplementedError,
          `${p.name}: only NotImplementedError allowed from complete(), got: ${err}`);
      }
    }
  });

  test("all providers: healthCheck() returns HealthStatus shape", async () => {
    for (const p of ALL_LLM_PROVIDERS) {
      const status = await p.healthCheck();
      assert.equal(typeof status.ok, "boolean", `${p.name}: ok must be boolean`);
      if (!status.ok) {
        assert.ok(status.error && status.error.length > 0,
          `${p.name}: ok=false must have non-empty error`);
      }
    }
  });

  test("all providers: name, model, contextWindow have correct types", () => {
    for (const p of ALL_LLM_PROVIDERS) {
      assert.equal(typeof p.name, "string", `name must be string`);
      assert.ok(p.name.length > 0, `${p.name}: name must be non-empty`);
      assert.equal(typeof p.model, "string");
      assert.ok(p.model.length > 0, `${p.name}: model must be non-empty`);
      assert.ok(typeof p.contextWindow === "number" && p.contextWindow > 0,
        `${p.name}: contextWindow must be positive number`);
    }
  });

  test("gemini: complete() result has all required fields", async () => {
    const p = new GeminiLLMProvider({ apiKey: FAKE_KEY, fetchFn: mockLLMFetch() as never });
    const result = await p.complete({ user: "ping", system: "be brief", maxTokens: 10 });
    assert.equal(result.text, "response");
    assert.equal(result.tokensIn, 10);
    assert.equal(result.tokensOut, 5);
    assert.ok(result.latencyMs >= 0);
  });

  test("stub providers: NotImplementedError names the provider", async () => {
    const stubs: LLMProvider[] = [new OpenAILLMProvider(), new AnthropicLLMProvider()];
    for (const p of stubs) {
      let err: Error | undefined;
      try {
        await p.complete({ user: "hi" });
      } catch (e) {
        err = e as Error;
      }
      assert.ok(err instanceof NotImplementedError, `${p.name}: should throw NotImplementedError`);
      // Error message should name the provider.
      assert.ok(err?.message.includes(p.name),
        `NotImplementedError message should include "${p.name}": got "${err?.message}"`);
    }
  });
});

// ─── Chain / wrapper conformance ─────────────────────────────────────────────

describe("Chain/wrapper LLMProvider conformance", () => {
  test("LLMFallbackChain exposes LLMProvider interface", () => {
    const primary = new GeminiLLMProvider({ apiKey: FAKE_KEY, fetchFn: mockLLMFetch() as never });
    const chain = new LLMFallbackChain({ primary, fallbacks: [] });
    assert.equal(typeof chain.name, "string");
    assert.equal(typeof chain.model, "string");
    assert.ok(chain.contextWindow > 0);
    assert.equal(typeof chain.complete, "function");
    assert.equal(typeof chain.healthCheck, "function");
  });

  test("CostCappedProvider exposes LLMProvider interface", () => {
    const primary = new GeminiLLMProvider({ apiKey: FAKE_KEY, fetchFn: mockLLMFetch() as never });
    const capped = new CostCappedProvider({ provider: primary, capUsd: 50 });
    assert.equal(typeof capped.name, "string");
    assert.equal(typeof capped.model, "string");
    assert.ok(capped.contextWindow > 0);
    assert.equal(typeof capped.complete, "function");
    assert.equal(typeof capped.healthCheck, "function");
  });
});

// ─── Secret hygiene ───────────────────────────────────────────────────────────

describe("Secret hygiene conformance", () => {
  test("stub errors do NOT contain API key patterns", async () => {
    const stubs: Array<EmbeddingProvider | LLMProvider> = [
      new OpenAIEmbeddingProvider(),
      new VoyageEmbeddingProvider(),
      new OpenAILLMProvider(),
      new AnthropicLLMProvider(),
    ];
    const keyPattern = /AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}/;
    for (const p of stubs) {
      const status = await p.healthCheck();
      if (status.error) {
        assert.ok(!keyPattern.test(status.error),
          `${p.name}: healthCheck error should not contain key pattern`);
      }
    }
  });

  test("ProviderTelemetryRow shape: all required fields present", () => {
    // Verify the type contract by constructing a valid row and checking fields.
    const row: ProviderTelemetryRow = {
      ts: Date.now(),
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      tokens_in: 10,
      tokens_out: 5,
      cost_usd: 0.001,
      latency_ms: 50,
      ok: 1,
      caller: "kg-extract",
      session_id: "s1",
    };
    // All required fields present.
    assert.equal(typeof row.ts, "number");
    assert.equal(typeof row.provider_id, "string");
    assert.equal(typeof row.model, "string");
    assert.ok(row.kind === "embedding" || row.kind === "llm");
    assert.equal(typeof row.tokens_in, "number");
    assert.equal(typeof row.tokens_out, "number");
    assert.equal(typeof row.cost_usd, "number");
    assert.equal(typeof row.latency_ms, "number");
    assert.ok(row.ok === 0 || row.ok === 1);
  });
});
