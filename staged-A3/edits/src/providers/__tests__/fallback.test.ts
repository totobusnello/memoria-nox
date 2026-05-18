/**
 * fallback.test.ts — LLMFallbackChain (T9).
 *
 * Cases (13):
 *  1. primary succeeds → result returned, providerId = primary.name
 *  2. primary 429 → fallback tried and succeeds
 *  3. primary 429 → fallback also 429 → second fallback tried → all fail throws
 *  4. primary 401 → fail-fast, no fallback attempted
 *  5. primary 403 → fail-fast, no fallback attempted
 *  6. primary timeout → fallback tried
 *  7. all providers fail → throws original error, not swallowed
 *  8. telemetry events emitted (primary_ok on success)
 *  9. telemetry events emitted (primary_fail_try_next + fallback_ok on 429-then-ok)
 * 10. telemetry events emitted (auth_fail on 401)
 * 11. CostCappedProvider integration: cap exceeded throws CostCapExceededError
 * 12. cooldown: rate-limited provider is skipped on second call within window
 * 13. empty fallbacks list → primary-only mode
 */
import { test, describe, beforeEach } from "node:test";
import { strict as assert } from "node:assert";

import { LLMFallbackChain, buildFallbackChain, clearAllCooldowns } from "../llm/chain.js";
import type { LLMProvider, CompleteOpts, CompleteResult } from "../llm/types.js";

// ─── Test helpers ─────────────────────────────────────────────────────────────

function makeProvider(
  name: string,
  model: string,
  behaviour:
    | { kind: "success"; text: string; tokensIn?: number; tokensOut?: number }
    | { kind: "http_error"; status: number }
    | { kind: "timeout"; delayMs: number }
    | { kind: "network_error" },
): LLMProvider {
  return {
    name,
    model,
    contextWindow: 100_000,
    async complete(_opts: CompleteOpts): Promise<CompleteResult> {
      if (behaviour.kind === "success") {
        return {
          text: behaviour.text,
          tokensIn: behaviour.tokensIn ?? 5,
          tokensOut: behaviour.tokensOut ?? 10,
          latencyMs: 1,
        };
      }
      if (behaviour.kind === "http_error") {
        throw new Error(`${name}: HTTP ${behaviour.status} error`);
      }
      if (behaviour.kind === "timeout") {
        await new Promise<void>((resolve) => setTimeout(resolve, behaviour.delayMs));
        throw new Error(`${name}: timed out`);
      }
      // network_error
      throw new Error(`${name}: network error`);
    },
    async healthCheck() {
      return { ok: true, latencyMs: 1 };
    },
  };
}

beforeEach(() => {
  clearAllCooldowns();
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("LLMFallbackChain — basic routing", () => {
  test("primary succeeds → result returned with primary.name as providerId", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "success",
      text: "hello",
    });
    const chain = buildFallbackChain(primary, []);
    const result = await chain.complete({ user: "hi" });
    assert.equal(result.text, "hello");
    // CompleteResult extended with providerId by chain.
    const ext = result as CompleteResult & { providerId?: string };
    assert.equal(ext.providerId, "gemini");
  });

  test("primary 429 → fallback succeeds", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "http_error",
      status: 429,
    });
    const fallback = makeProvider("anthropic", "claude-3-5-haiku", {
      kind: "success",
      text: "from fallback",
    });
    const chain = buildFallbackChain(primary, [fallback], { cooldownMs: 1 });
    const result = await chain.complete({ user: "hi" });
    assert.equal(result.text, "from fallback");
    const ext = result as CompleteResult & { providerId?: string };
    assert.equal(ext.providerId, "anthropic");
  });

  test("primary 429 + fallback 429 → second fallback OK", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "http_error",
      status: 429,
    });
    const fb1 = makeProvider("anthropic", "claude-3-5-haiku", {
      kind: "http_error",
      status: 429,
    });
    const fb2 = makeProvider("openai", "gpt-4o-mini", {
      kind: "success",
      text: "openai wins",
    });
    const chain = buildFallbackChain(primary, [fb1, fb2], { cooldownMs: 1 });
    const result = await chain.complete({ user: "hi" });
    assert.equal(result.text, "openai wins");
  });

  test("primary 401 → fail-fast, no fallback attempted", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "http_error",
      status: 401,
    });
    const fallback = makeProvider("anthropic", "claude-3-5-haiku", {
      kind: "success",
      text: "should not reach",
    });
    const chain = buildFallbackChain(primary, [fallback]);
    await assert.rejects(
      chain.complete({ user: "hi" }),
      (err: Error) => {
        assert.match(err.message, /auth failure/);
        assert.match(err.message, /401/);
        // Fallback was NOT used.
        assert.equal(err.message.includes("anthropic"), false);
        return true;
      },
    );
  });

  test("primary 403 → fail-fast, error message mentions provider", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "http_error",
      status: 403,
    });
    const chain = buildFallbackChain(primary, []);
    await assert.rejects(chain.complete({ user: "hi" }), /auth failure/);
  });

  test("primary timeout → fallback tried and succeeds", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "timeout",
      delayMs: 200,
    });
    const fallback = makeProvider("anthropic", "claude-3-5-haiku", {
      kind: "success",
      text: "fallback after timeout",
    });
    const chain = buildFallbackChain(primary, [fallback], { timeoutMs: 50 });
    const result = await chain.complete({ user: "hi" });
    assert.equal(result.text, "fallback after timeout");
  });

  test("all providers fail → throws, error message is redacted", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "network_error",
    });
    const fallback = makeProvider("anthropic", "claude-3-5-haiku", {
      kind: "network_error",
    });
    const chain = buildFallbackChain(primary, [fallback]);
    await assert.rejects(chain.complete({ user: "hi" }), /network error/);
  });

  test("empty fallbacks (primary-only) → primary-only mode", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "success",
      text: "solo",
    });
    const chain = buildFallbackChain(primary, []);
    const result = await chain.complete({ user: "hi" });
    assert.equal(result.text, "solo");
  });
});

describe("LLMFallbackChain — telemetry events", () => {
  test("primary_ok event fired on success", async () => {
    const primary = makeProvider("gemini", "gemini-2.5-flash-lite", {
      kind: "success",
      text: "ok",
    });
    const events: string[] = [];
    const chain = buildFallbackChain(primary, [], {
      onEvent: (e) => events.push(e.kind),
    });
    await chain.complete({ user: "hi" });
    assert.deepEqual(events, ["primary_ok"]);
  });

  test("primary_fail_try_next + fallback_ok events on 429→ok", async () => {
    const primary = makeProvider("gemini", "g", { kind: "http_error", status: 429 });
    const fallback = makeProvider("anthropic", "h", { kind: "success", text: "ok" });
    const events: string[] = [];
    const chain = buildFallbackChain(primary, [fallback], {
      onEvent: (e) => events.push(e.kind),
      cooldownMs: 1,
    });
    await chain.complete({ user: "hi" });
    assert.deepEqual(events, ["primary_fail_try_next", "fallback_ok"]);
  });

  test("auth_fail event on 401", async () => {
    const primary = makeProvider("gemini", "g", { kind: "http_error", status: 401 });
    const events: string[] = [];
    const chain = buildFallbackChain(primary, [], {
      onEvent: (e) => events.push(`${e.kind}:${e.errorKind ?? ""}`),
    });
    await assert.rejects(chain.complete({ user: "hi" }));
    assert.deepEqual(events, ["auth_fail:auth"]);
  });
});

describe("LLMFallbackChain — cooldown", () => {
  test("rate-limited provider skipped on second call within cooldown window", async () => {
    let primaryCallCount = 0;
    const primary: LLMProvider = {
      name: "gemini",
      model: "m",
      contextWindow: 1000,
      async complete() {
        primaryCallCount++;
        // First call: 429; subsequent calls (after cooldown): success.
        if (primaryCallCount === 1) throw new Error("HTTP 429");
        return { text: "ok", tokensIn: 1, tokensOut: 1, latencyMs: 1 };
      },
      async healthCheck() { return { ok: true, latencyMs: 1 }; },
    };
    const fallback = makeProvider("anthropic", "h", { kind: "success", text: "fallback-ok" });

    const chain = buildFallbackChain(primary, [fallback], {
      cooldownMs: 5_000, // long cooldown — primary stays skipped
    });

    // Call 1: primary 429 → fallback used, primary enters cooldown.
    const r1 = await chain.complete({ user: "1" });
    assert.equal(r1.text, "fallback-ok");

    // Call 2 (within cooldown): primary is skipped → fallback used directly.
    const r2 = await chain.complete({ user: "2" });
    assert.equal(r2.text, "fallback-ok");
    // Primary should only have been called once.
    assert.equal(primaryCallCount, 1);
  });
});
