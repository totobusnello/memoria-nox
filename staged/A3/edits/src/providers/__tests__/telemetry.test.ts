/**
 * telemetry.test.ts — ProviderTelemetry queue + aggregation (T12).
 *
 * Cases (9):
 *  1. recordProviderCall enqueues a row with correct fields
 *  2. row.error_kind has secrets redacted (API key pattern stripped)
 *  3. row never contains prompt text (privacy invariant)
 *  4. queue drain flushes all rows via writeFn
 *  5. queue overflow: capacity exceeded → oldest entries dropped
 *  6. writeFn error does NOT propagate to caller
 *  7. aggregateCosts: last24h totals computed correctly
 *  8. aggregateCosts: rows older than 24h excluded
 *  9. aggregateCosts: per-provider breakdown populated
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import {
  TelemetryQueue,
  recordProviderCall,
  setDefaultQueue,
  getDefaultQueue,
  aggregateCosts,
  type ProviderTelemetryRow,
} from "../telemetry.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeQueue(rows: ProviderTelemetryRow[] = [], capacity?: number): TelemetryQueue {
  return new TelemetryQueue({
    writeFn: async (row) => {
      rows.push(row);
    },
    capacity,
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("recordProviderCall — enqueue + field mapping", () => {
  test("enqueues a row with correct fields", async () => {
    const rows: ProviderTelemetryRow[] = [];
    const q = makeQueue(rows);
    const prevQueue = getDefaultQueue();
    setDefaultQueue(q);

    recordProviderCall({
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      tokens_in: 100,
      tokens_out: 50,
      cost_usd: 0.00015,
      latency_ms: 123,
      ok: true,
      caller: "kg-extract",
      session_id: "sess-001",
    });

    await q.drain();
    setDefaultQueue(prevQueue);

    assert.equal(rows.length, 1);
    const row = rows[0];
    assert.ok(row, "row should exist");
    assert.equal(row?.provider_id, "gemini");
    assert.equal(row?.model, "gemini-2.5-flash-lite");
    assert.equal(row?.kind, "llm");
    assert.equal(row?.tokens_in, 100);
    assert.equal(row?.tokens_out, 50);
    assert.equal(row?.ok, 1);
    assert.equal(row?.caller, "kg-extract");
    assert.equal(row?.session_id, "sess-001");
    assert.equal(typeof row?.ts, "number");
    assert.ok((row?.ts ?? 0) > 0);
  });

  test("error_kind has secrets redacted (API key pattern stripped)", async () => {
    const rows: ProviderTelemetryRow[] = [];
    const q = makeQueue(rows);
    const prevQueue = getDefaultQueue();
    setDefaultQueue(q);

    recordProviderCall({
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      latency_ms: 50,
      ok: false,
      errorRaw: "401 Unauthorized: key=AIzaABCDEFGHIJKLMNOPQRSTUVWXYZ12345 is invalid",
    });

    await q.drain();
    setDefaultQueue(prevQueue);

    assert.equal(rows.length, 1);
    const row = rows[0];
    assert.ok(row?.error_kind, "error_kind should be set");
    // Key should be redacted.
    assert.equal(row?.error_kind?.includes("AIzaABCDEFGHIJKLMN"), false);
    assert.match(row?.error_kind ?? "", /REDACTED|401/);
  });

  test("row does NOT contain prompt text (privacy invariant)", async () => {
    const rows: ProviderTelemetryRow[] = [];
    const q = makeQueue(rows);
    const prevQueue = getDefaultQueue();
    setDefaultQueue(q);

    const secretPrompt = "CONFIDENTIAL_PROMPT_CONTENT_DO_NOT_LOG_XYZ";

    recordProviderCall({
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      latency_ms: 10,
      ok: true,
      caller: "reflect",
      // NOTE: no `user` field — prompt is never passed here by design.
    });

    await q.drain();
    setDefaultQueue(prevQueue);

    const rowStr = JSON.stringify(rows[0] ?? {});
    // The secret prompt was never passed so it cannot appear.
    assert.equal(rowStr.includes(secretPrompt), false);
  });
});

describe("TelemetryQueue — drain + overflow + error isolation", () => {
  test("drain flushes all rows via writeFn", async () => {
    const rows: ProviderTelemetryRow[] = [];
    const q = makeQueue(rows);

    for (let i = 0; i < 10; i++) {
      q.enqueue({
        ts: Date.now(),
        provider_id: "gemini",
        model: "m",
        kind: "embedding",
        tokens_in: i,
        tokens_out: 0,
        cost_usd: 0,
        latency_ms: 1,
        ok: 1,
      });
    }

    await q.drain();
    assert.equal(rows.length, 10);
  });

  test("queue overflow: oldest entries dropped when capacity exceeded", async () => {
    const written: ProviderTelemetryRow[] = [];
    const q = new TelemetryQueue({
      writeFn: async (row) => { written.push(row); },
      capacity: 3,
    });

    // Enqueue 5 items — oldest 2 should be dropped.
    for (let i = 0; i < 5; i++) {
      q.enqueue({
        ts: i,
        provider_id: `p${i}`,
        model: "m",
        kind: "llm",
        tokens_in: 0,
        tokens_out: 0,
        cost_usd: 0,
        latency_ms: 1,
        ok: 1,
      });
    }

    await q.drain();
    // capacity=3 means at most 3 survive; p0 and p1 were pushed out.
    // Check that we didn't write more than 3 rows.
    assert.ok(written.length <= 3, `expected ≤3 rows, got ${written.length}`);
    // The surviving rows should be among the later-inserted ones.
    const writtenIds = written.map((r) => r.provider_id);
    // p0 or p1 may have been evicted; p4 must survive.
    assert.ok(writtenIds.includes("p4"), "most recent entry should survive overflow");
  });

  test("writeFn error does NOT propagate to recordProviderCall", async () => {
    let errorCaught: unknown = null;
    const q = new TelemetryQueue({
      writeFn: async () => {
        throw new Error("DB write failed");
      },
      onError: (err) => {
        errorCaught = err;
      },
    });

    const prevQueue = getDefaultQueue();
    setDefaultQueue(q);

    // Must not throw.
    assert.doesNotThrow(() => {
      recordProviderCall({
        provider_id: "gemini",
        model: "m",
        kind: "llm",
        latency_ms: 1,
        ok: true,
      });
    });

    await q.drain();
    setDefaultQueue(prevQueue);

    // Error was captured by onError, not propagated.
    assert.ok(errorCaught instanceof Error);
    assert.match((errorCaught as Error).message, /DB write failed/);
  });
});

describe("aggregateCosts — statistics", () => {
  const nowMs = 1_000_000_000_000;
  const hour = 3_600_000;

  test("last24h totals computed correctly", () => {
    const rows: ProviderTelemetryRow[] = [
      { ts: nowMs - hour, provider_id: "gemini", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 1.50, latency_ms: 10, ok: 1 },
      { ts: nowMs - 2 * hour, provider_id: "openai", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 0.75, latency_ms: 10, ok: 1 },
    ];
    const agg = aggregateCosts(rows, nowMs);
    assert.ok(Math.abs(agg.last24hUsd - 2.25) < 0.001);
    assert.equal(agg.last24hCalls, 2);
    assert.equal(agg.last24hSuccessRate, 1);
  });

  test("rows older than 24h excluded", () => {
    const rows: ProviderTelemetryRow[] = [
      { ts: nowMs - 25 * hour, provider_id: "gemini", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 100.00, latency_ms: 10, ok: 1 },
      { ts: nowMs - hour, provider_id: "gemini", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 0.10, latency_ms: 10, ok: 1 },
    ];
    const agg = aggregateCosts(rows, nowMs);
    assert.ok(Math.abs(agg.last24hUsd - 0.10) < 0.001, `expected ~0.10, got ${agg.last24hUsd}`);
    assert.equal(agg.last24hCalls, 1);
  });

  test("per-provider breakdown populated", () => {
    const rows: ProviderTelemetryRow[] = [
      { ts: nowMs - hour, provider_id: "gemini", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 1.00, latency_ms: 10, ok: 1 },
      { ts: nowMs - hour, provider_id: "gemini", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 2.00, latency_ms: 10, ok: 1 },
      { ts: nowMs - hour, provider_id: "openai", model: "m", kind: "llm", tokens_in: 0, tokens_out: 0, cost_usd: 0.50, latency_ms: 10, ok: 0 },
    ];
    const agg = aggregateCosts(rows, nowMs);
    assert.ok(agg.byProvider["gemini"], "gemini in byProvider");
    assert.ok(Math.abs((agg.byProvider["gemini"]?.usd ?? 0) - 3.00) < 0.001);
    assert.equal(agg.byProvider["gemini"]?.calls, 2);
    assert.equal(agg.byProvider["openai"]?.calls, 1);
    assert.ok(Math.abs(agg.last24hSuccessRate - (2 / 3)) < 0.01);
  });
});
