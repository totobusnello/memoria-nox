/**
 * gemini.test.ts — Gemini providers mock-based tests (no real API).
 *
 * Cases (10):
 *  - GeminiEmbedding: happy path 1 input → 1 vector of dim 3072
 *  - GeminiEmbedding: batch 3 inputs → 3 vectors in order
 *  - GeminiEmbedding: HTTP 401 → throws with REDACTED key (T14.6 secret hygiene)
 *  - GeminiEmbedding: dim mismatch in response → throws clear error
 *  - GeminiEmbedding: healthCheck happy path → ok=true with latencyMs
 *  - GeminiEmbedding: healthCheck 503 → ok=false, error contains 503
 *  - GeminiLLM: happy path returns text + tokensIn + tokensOut + latencyMs
 *  - GeminiLLM: system+user combined into body correctly
 *  - GeminiLLM: throws when `user` empty
 *  - GeminiLLM: MissingKeyError when GEMINI_API_KEY absent
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import { GeminiEmbeddingProvider, redactSecrets } from "../embedding/gemini.js";
import { GeminiLLMProvider } from "../llm/gemini.js";
import { MissingKeyError } from "../types.js";
import type { FetchLike } from "../embedding/gemini.js";

const FAKE_KEY = "AIzaTESTtestTESTtestTESTtestTESTtest";

/** Build a fake fetchFn that returns the given body or status. */
function makeFetch(opts: {
  body?: unknown;
  status?: number;
  statusText?: string;
  textBody?: string;
}): FetchLike {
  const status = opts.status ?? 200;
  const statusText = opts.statusText ?? "OK";
  return async () => ({
    ok: status >= 200 && status < 300,
    status,
    statusText,
    text: async () => opts.textBody ?? JSON.stringify(opts.body ?? {}),
    json: async () => opts.body ?? {},
  });
}

function vectorOfDim(d: number, fill = 0.1): number[] {
  const a: number[] = [];
  for (let i = 0; i < d; i++) a.push(fill);
  return a;
}

describe("GeminiEmbeddingProvider (mock)", () => {
  test("single embed returns Float32Array of dim 3072", async () => {
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({
        body: { embeddings: [{ values: vectorOfDim(3072) }] },
      }),
    });
    const out = await p.embed(["hello world"]);
    assert.equal(out.length, 1);
    const v0 = out[0];
    assert.ok(v0 instanceof Float32Array);
    assert.equal(v0?.length, 3072);
    // Float32 has 23-bit mantissa: 0.1 round-trips as 0.10000000149011612.
    assert.equal(v0?.[0], Math.fround(0.1));
  });

  test("batch embed: 3 inputs → 3 vectors in order", async () => {
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({
        body: {
          embeddings: [
            { values: vectorOfDim(3072, 0.1) },
            { values: vectorOfDim(3072, 0.2) },
            { values: vectorOfDim(3072, 0.3) },
          ],
        },
      }),
    });
    const out = await p.embed(["a", "b", "c"]);
    assert.equal(out.length, 3);
    assert.equal(out[0]?.[0], Math.fround(0.1));
    assert.equal(out[1]?.[0], Math.fround(0.2));
    assert.equal(out[2]?.[0], Math.fround(0.3));
  });

  test("HTTP 401 surfaces redacted error (no API key in message)", async () => {
    const upstream = `error: API_KEY_INVALID: AIza${"x".repeat(35)}`;
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({ status: 401, statusText: "Unauthorized", textBody: upstream }),
    });
    await assert.rejects(p.embed(["hi"]), (err: Error) => {
      assert.match(err.message, /HTTP 401/);
      // CRITICAL: the redacted message MUST NOT contain the raw key.
      assert.equal(err.message.includes(FAKE_KEY), false);
      assert.match(err.message, /AIza<REDACTED>/);
      return true;
    });
  });

  test("dim mismatch in upstream → throws clear error", async () => {
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({
        body: { embeddings: [{ values: vectorOfDim(1536) }] }, // wrong dim
      }),
    });
    await assert.rejects(p.embed(["hi"]), /dim mismatch/);
  });

  test("healthCheck ok path", async () => {
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({ body: { name: "models/gemini-embedding-001" } }),
    });
    const s = await p.healthCheck();
    assert.equal(s.ok, true);
    assert.equal(typeof s.latencyMs, "number");
    assert.equal(s.error, undefined);
  });

  test("healthCheck 503 → ok=false with HTTP 503 in error", async () => {
    const p = new GeminiEmbeddingProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({ status: 503, statusText: "Service Unavailable" }),
    });
    const s = await p.healthCheck();
    assert.equal(s.ok, false);
    assert.match(s.error ?? "", /503/);
  });
});

describe("GeminiLLMProvider (mock)", () => {
  test("happy path returns text + tokensIn/tokensOut + latencyMs", async () => {
    const p = new GeminiLLMProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({
        body: {
          candidates: [
            { content: { parts: [{ text: "Hello there!" }] } },
          ],
          usageMetadata: { promptTokenCount: 5, candidatesTokenCount: 3 },
        },
      }),
    });
    const out = await p.complete({ user: "Hi" });
    assert.equal(out.text, "Hello there!");
    assert.equal(out.tokensIn, 5);
    assert.equal(out.tokensOut, 3);
    assert.equal(typeof out.latencyMs, "number");
  });

  test("system+user assembled correctly (captured via fetch interceptor)", async () => {
    let capturedBody: string | undefined;
    const interceptor: FetchLike = async (_url, init) => {
      capturedBody = init?.body;
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => "{}",
        json: async () => ({
          candidates: [{ content: { parts: [{ text: "ok" }] } }],
          usageMetadata: { promptTokenCount: 1, candidatesTokenCount: 1 },
        }),
      };
    };
    const p = new GeminiLLMProvider({ apiKey: FAKE_KEY, fetchFn: interceptor });
    await p.complete({ system: "be brief", user: "two plus two?" });
    assert.ok(capturedBody, "fetch body must be captured");
    const parsed = JSON.parse(capturedBody ?? "{}");
    assert.equal(parsed.system_instruction?.parts?.[0]?.text, "be brief");
    assert.equal(parsed.contents?.[0]?.parts?.[0]?.text, "two plus two?");
  });

  test("rejects empty `user` prompt with clear error", async () => {
    const p = new GeminiLLMProvider({
      apiKey: FAKE_KEY,
      fetchFn: makeFetch({ body: {} }),
    });
    await assert.rejects(p.complete({ user: "" }), /`user` is required/);
  });

  test("MissingKeyError when GEMINI_API_KEY absent", () => {
    const origKey = process.env.GEMINI_API_KEY;
    delete process.env.GEMINI_API_KEY;
    try {
      assert.throws(
        () => new GeminiLLMProvider({ fetchFn: makeFetch({ body: {} }) }),
        MissingKeyError,
      );
    } finally {
      if (origKey !== undefined) process.env.GEMINI_API_KEY = origKey;
    }
  });
});

describe("redactSecrets", () => {
  test("redacts gemini AIza..., openai sk-..., Bearer tokens, key= params", () => {
    const inp =
      "AIzaABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi " +
      "sk-AAABBBCCCDDDEEEFFFGGGHHHIII " +
      "Bearer abcdefghijklmnopqrstuvwxyzABCDEF " +
      "key=AAABBBCCCDDDEEEFFFGGGHHHIII";
    const out = redactSecrets(inp);
    assert.equal(out.includes("AIzaABCDEFG"), false);
    assert.equal(out.includes("sk-AAA"), false);
    assert.equal(out.includes("Bearer abcd"), false);
    assert.equal(out.includes("key=AAAB"), false);
    assert.match(out, /AIza<REDACTED>/);
  });
});
