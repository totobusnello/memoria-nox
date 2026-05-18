/**
 * S3 — Provider fallback under stress (A3 + P1).
 *
 * Verifies:
 *   - Primary 429 → fallback succeeds
 *   - 10 concurrent calls all routed correctly
 *   - Telemetry attribution: primary tried, fallback used, both visible per event
 *   - Auth 401 fails fast and does NOT try fallback
 *
 * Bug-class targeted: a regression where concurrent fallback calls share
 * mutable state (cooldown map, lastError) and corrupt telemetry attribution.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  LLMFallbackChain,
  type LLMProvider,
  type CompleteOpts,
  type CompleteResult,
} from "../lib/pillar-shims.js";

class StubProvider implements LLMProvider {
  public callCount = 0;
  constructor(
    public readonly name: string,
    public readonly model: string,
    private readonly behavior:
      | { kind: "ok"; text: string }
      | { kind: "throw"; err: Error }
  ) {}

  async complete(_opts: CompleteOpts): Promise<CompleteResult> {
    this.callCount++;
    if (this.behavior.kind === "throw") throw this.behavior.err;
    return { text: this.behavior.text, tokensIn: 5, tokensOut: 5, latencyMs: 1 };
  }
}

let primary: StubProvider;
let fallback: StubProvider;

beforeEach(() => {
  // Reset per-test so callCount starts at 0.
  primary = new StubProvider("primary", "stub-primary", {
    kind: "throw",
    err: new Error("HTTP 429 rate limited"),
  });
  fallback = new StubProvider("fallback", "stub-fallback", {
    kind: "ok",
    text: "fallback answer",
  });
});

describe("S3 — Provider fallback under stress (A3 + P1)", () => {
  it("S3-01 single call: primary 429 → fallback used, attribution correct", async () => {
    const chain = new LLMFallbackChain(primary, [fallback]);
    const r = await chain.complete({ user: "hi" });
    assert.strictEqual(r.providerId, "fallback");
    assert.strictEqual(r.text, "fallback answer");
    assert.strictEqual(primary.callCount, 1);
    assert.strictEqual(fallback.callCount, 1);
    // Telemetry events: primary_fail_try_next + fallback_ok
    const kinds = chain.events.map((e) => e.kind);
    assert.deepStrictEqual(kinds, ["primary_fail_try_next", "fallback_ok"]);
    assert.strictEqual(chain.events[0]!.errorKind, "rate_limit");
  });

  it("S3-02 10 concurrent calls: every call resolved by fallback", async () => {
    const chain = new LLMFallbackChain(primary, [fallback]);
    const promises = Array.from({ length: 10 }, (_, i) =>
      chain.complete({ user: `q${i}` })
    );
    const results = await Promise.all(promises);
    for (const r of results) {
      assert.strictEqual(r.providerId, "fallback");
      assert.strictEqual(r.text, "fallback answer");
    }
    assert.strictEqual(primary.callCount, 10);
    assert.strictEqual(fallback.callCount, 10);
    // Events: 10 × (primary_fail_try_next + fallback_ok) = 20 events
    assert.strictEqual(chain.events.length, 20);
    const primaryFails = chain.events.filter((e) => e.kind === "primary_fail_try_next");
    const fallbackOks = chain.events.filter((e) => e.kind === "fallback_ok");
    assert.strictEqual(primaryFails.length, 10);
    assert.strictEqual(fallbackOks.length, 10);
  });

  it("S3-03 auth 401 fails fast — fallback NOT tried", async () => {
    const authFail = new StubProvider("primary-auth", "p", {
      kind: "throw",
      err: new Error("HTTP 401 unauthorized"),
    });
    const chain = new LLMFallbackChain(authFail, [fallback]);
    await assert.rejects(chain.complete({ user: "hi" }), /auth failure/i);
    assert.strictEqual(authFail.callCount, 1);
    assert.strictEqual(fallback.callCount, 0); // critical: must not have been tried
    assert.strictEqual(chain.events.at(-1)!.kind, "auth_fail");
  });

  it("S3-04 both providers fail → all_fail event emitted, error rethrown", async () => {
    const a = new StubProvider("a", "ma", { kind: "throw", err: new Error("HTTP 500") });
    const b = new StubProvider("b", "mb", { kind: "throw", err: new Error("HTTP 503") });
    const chain = new LLMFallbackChain(a, [b]);
    await assert.rejects(chain.complete({ user: "x" }));
    assert.strictEqual(a.callCount, 1);
    assert.strictEqual(b.callCount, 1);
    assert.strictEqual(chain.events.at(-1)!.kind, "all_fail");
  });

  it("S3-05 telemetry latency_ms populated for each attempt", async () => {
    const chain = new LLMFallbackChain(primary, [fallback]);
    await chain.complete({ user: "hi" });
    for (const ev of chain.events) {
      assert.ok(ev.latencyMs >= 0, `latencyMs negative: ${ev.latencyMs}`);
      // The last event ('all_fail') has latencyMs=0 by convention; primary/fallback should be reasonable.
      if (ev.kind === "fallback_ok" || ev.kind === "primary_ok") {
        assert.ok(ev.latencyMs < 5000, `latency too high: ${ev.latencyMs}`);
      }
    }
  });
});
