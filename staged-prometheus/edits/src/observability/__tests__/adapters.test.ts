/**
 * Tests for the integration adapters (T7).
 *
 * Focus: composing recorders with the inner handlers, error paths, gauge
 * lifecycle.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  answerRequestsTotal,
  providerCallsTotal,
  viewerConnections,
  viewerEventsTotal,
  viewerDroppedTotal,
} from "../metrics.ts";
import { withAnswerMetrics } from "../adapters/p1-adapter.ts";
import {
  instrumentProviderCall,
  classifyProviderError,
} from "../adapters/a3-adapter.ts";
import {
  wrapBroadcast,
  trackConnection,
  reportBackpressureDrop,
} from "../adapters/p5-adapter.ts";

test("Adapter.P1 — wraps success", async () => {
  answerRequestsTotal.reset();
  const handler = withAnswerMetrics(async () => ({
    outcome: "success" as const,
    tokensIn: 10,
    tokensOut: 4,
    timing: { total: 0.05 },
  }));
  const out = await handler();
  assert.equal(out.outcome, "success");
  assert.equal(
    answerRequestsTotal.get({ failure_reason: "success" }),
    1,
  );
});

test("Adapter.P1 — wraps thrown error → llm_failed", async () => {
  answerRequestsTotal.reset();
  const handler = withAnswerMetrics(async () => {
    throw new Error("boom");
  });
  await assert.rejects(() => handler(), /boom/);
  assert.equal(
    answerRequestsTotal.get({ failure_reason: "llm_failed" }),
    1,
  );
});

test("Adapter.A3 — instrumentProviderCall success path", async () => {
  providerCallsTotal.reset();
  const out = await instrumentProviderCall(
    { provider: "gemini", model: "gemini-2.5-flash-lite", kind: "llm" },
    async () => ({ result: 42, tokensIn: 100, tokensOut: 50, costUsd: 0.0001 }),
  );
  assert.equal(out, 42);
  assert.equal(
    providerCallsTotal.get({
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      outcome: "success",
    }),
    1,
  );
});

test("Adapter.A3 — classifies rate_limit / fallback / error", () => {
  assert.equal(classifyProviderError({ status: 429 }), "rate_limit");
  assert.equal(classifyProviderError({ code: "FALLBACK" }), "fallback");
  assert.equal(classifyProviderError({ code: "PROVIDER_FALLBACK" }), "fallback");
  assert.equal(classifyProviderError(new Error("x")), "error");
  assert.equal(classifyProviderError(null), "error");
});

test("Adapter.A3 — rethrows + emits rate_limit metric", async () => {
  providerCallsTotal.reset();
  await assert.rejects(
    () =>
      instrumentProviderCall(
        { provider: "openai", model: "gpt-4o", kind: "llm" },
        async () => {
          const e = new Error("429");
          (e as Error & { status?: number }).status = 429;
          throw e;
        },
      ),
    /429/,
  );
  assert.equal(
    providerCallsTotal.get({
      provider: "openai",
      model: "gpt-4o",
      outcome: "rate_limit",
    }),
    1,
  );
});

test("Adapter.P5 — trackConnection inc/dec gauge on close", () => {
  viewerConnections.reset();
  const listeners: Record<string, Array<() => void>> = {};
  const fakeSock = {
    on(event: string, cb: () => void) {
      (listeners[event] ??= []).push(cb);
    },
  };
  trackConnection(fakeSock);
  assert.equal(viewerConnections.get(), 1);
  // close → decrement once
  listeners["close"][0]();
  assert.equal(viewerConnections.get(), 0);
  // second close should be no-op (decremented flag)
  listeners["close"][0]();
  assert.equal(viewerConnections.get(), 0);
});

test("Adapter.P5 — wrapBroadcast counts emitted + dropped", async () => {
  viewerEventsTotal.reset();
  viewerDroppedTotal.reset();
  const broadcast = wrapBroadcast(async (evt) => {
    if (evt.type === "boom") throw new Error("dead");
  });
  await broadcast({ type: "ingest" });
  await assert.rejects(
    async () => {
      await broadcast({ type: "boom" });
    },
    /dead/,
  );
  assert.equal(viewerEventsTotal.get({ type: "ingest" }), 1);
  assert.equal(viewerDroppedTotal.get({ reason: "queue_full" }), 1);
  reportBackpressureDrop("slow_consumer");
  assert.equal(viewerDroppedTotal.get({ reason: "slow_consumer" }), 1);
});
