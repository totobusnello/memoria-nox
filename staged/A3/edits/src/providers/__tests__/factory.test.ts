/**
 * factory.test.ts — T2 selectEmbeddingProvider / selectLLMProvider.
 *
 * Cases (8):
 *  1. Default env → gemini embedding provider
 *  2. Default env → gemini llm provider (default model = flash-lite, D41)
 *  3. NOX_EMBEDDING_PROVIDER=openai → OpenAIEmbeddingProvider (stub)
 *  4. NOX_LLM_PROVIDER=anthropic → AnthropicLLMProvider (stub)
 *  5. NOX_LLM_PROVIDER=voyage → UnknownProviderError (voyage is embedding only)
 *  6. Unknown provider → UnknownProviderError
 *  7. NOX_LLM_MODEL=gemini-2.5-flash → flash full applied (regra #3, explicit)
 *  8. NOX_EMBEDDING_MODEL=text-embedding-3-large applied to openai stub
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import {
  selectEmbeddingProvider,
  selectLLMProvider,
  UnknownProviderError,
} from "../index.js";
import { GeminiEmbeddingProvider } from "../embedding/gemini.js";
import { GeminiLLMProvider } from "../llm/gemini.js";
import { OpenAIEmbeddingProvider } from "../embedding/openai.js";
import { AnthropicLLMProvider } from "../llm/anthropic.js";

const FAKE_KEY = "AIzaTESTtestTESTtestTESTtestTESTtest";

describe("selectEmbeddingProvider (T2)", () => {
  test("defaults to gemini with GEMINI_API_KEY set", () => {
    const p = selectEmbeddingProvider(undefined, { GEMINI_API_KEY: FAKE_KEY });
    assert.equal(p.name, "gemini");
    assert.equal(p.dimensions, 3072);
    assert.ok(p instanceof GeminiEmbeddingProvider);
  });

  test("honours NOX_EMBEDDING_PROVIDER=openai (stub)", () => {
    const p = selectEmbeddingProvider(undefined, { NOX_EMBEDDING_PROVIDER: "openai" });
    assert.equal(p.name, "openai");
    assert.ok(p instanceof OpenAIEmbeddingProvider);
  });

  test("honours NOX_EMBEDDING_MODEL on stub provider", () => {
    const p = selectEmbeddingProvider(undefined, {
      NOX_EMBEDDING_PROVIDER: "openai",
      NOX_EMBEDDING_MODEL: "text-embedding-3-large",
    });
    // `model` is implementation-level (not on the locked EmbeddingProvider
    // interface — see embedding/types.ts comment). All concrete classes expose
    // it; cast through the known shape to assert.
    assert.equal((p as unknown as { model: string }).model, "text-embedding-3-large");
  });

  test("unknown name throws UnknownProviderError", () => {
    assert.throws(
      () => selectEmbeddingProvider("cohere", { GEMINI_API_KEY: FAKE_KEY }),
      UnknownProviderError,
    );
  });
});

describe("selectLLMProvider (T2)", () => {
  test("defaults to gemini flash-lite (D41)", () => {
    const p = selectLLMProvider(undefined, { GEMINI_API_KEY: FAKE_KEY });
    assert.equal(p.name, "gemini");
    assert.equal(p.model, "gemini-2.5-flash-lite");
    assert.ok(p instanceof GeminiLLMProvider);
  });

  test("NOX_LLM_PROVIDER=anthropic returns Anthropic stub", () => {
    const p = selectLLMProvider(undefined, { NOX_LLM_PROVIDER: "anthropic" });
    assert.equal(p.name, "anthropic");
    assert.ok(p instanceof AnthropicLLMProvider);
  });

  test("NOX_LLM_PROVIDER=voyage rejected (voyage is embedding-only)", () => {
    assert.throws(
      () => selectLLMProvider(undefined, { NOX_LLM_PROVIDER: "voyage" }),
      UnknownProviderError,
    );
  });

  test("NOX_LLM_MODEL=gemini-2.5-flash applied explicitly (regra #3)", () => {
    const p = selectLLMProvider(undefined, {
      GEMINI_API_KEY: FAKE_KEY,
      NOX_LLM_MODEL: "gemini-2.5-flash",
    });
    assert.equal(p.model, "gemini-2.5-flash");
  });
});

// Sanity-check sentinel to keep the "explicit name beats env" path covered.
describe("explicit arg precedence", () => {
  test("explicit name arg overrides env", () => {
    const p = selectLLMProvider("anthropic", {
      GEMINI_API_KEY: FAKE_KEY,
      NOX_LLM_PROVIDER: "gemini",
    });
    assert.equal(p.name, "anthropic");
  });
});
