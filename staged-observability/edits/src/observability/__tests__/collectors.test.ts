/**
 * Tests for the collectors (T4).
 *
 * Process collector is exercised indirectly (it touches real process state).
 * DB + telemetry collectors are driven by stub query functions.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  chunksActive,
  chunksStale,
  dbSizeBytes,
  searchRequestsTotal,
  searchDurationSeconds,
  providerCallsTotal,
  providerCostUsdTotal,
  viewerEventsTotal,
} from "../metrics.js";
import { collectDbStats } from "../collectors/db-stats.collector.js";
import {
  drain as drainSearch,
  resetCursor as resetSearchCursor,
} from "../collectors/search-telemetry.collector.js";
import {
  drain as drainProvider,
  resetCursor as resetProviderCursor,
} from "../collectors/provider-telemetry.collector.js";
import {
  attachEventBusCollector,
  detachEventBusCollector,
  type EventBusLike,
} from "../collectors/eventbus.collector.js";

test("Collector.DbStats — chunk bucket counts", () => {
  chunksActive.reset();
  chunksStale.reset();
  dbSizeBytes.reset();
  const fakeQuery = () => [
    { provenance_kind: "fresh", n: 100 },
    { provenance_kind: "compiled", n: 25 },
    { provenance_kind: "stale", n: 13 },
  ];
  collectDbStats({ dbPath: "/nonexistent/db.sqlite", query: fakeQuery });
  assert.equal(chunksActive.get(), 125);
  assert.equal(chunksStale.get(), 13);
  // sizes default to 0 when files missing
  assert.equal(dbSizeBytes.get({ component: "main" }), 0);
});

test("Collector.SearchTelemetry — drain & advance cursor", () => {
  searchRequestsTotal.reset();
  searchDurationSeconds.reset();
  resetSearchCursor();
  const rows = [
    { id: 1, method: "api", duration_ms: 50, results_count: 12, outcome: "success" },
    { id: 2, method: "cli", duration_ms: 30, results_count: 0, outcome: "empty" },
  ];
  let called = 0;
  const query = () => {
    called++;
    return called === 1 ? rows : []; // second pass: empty
  };
  const n1 = drainSearch(query);
  const n2 = drainSearch(query);
  assert.equal(n1, 2);
  assert.equal(n2, 0);
  assert.equal(
    searchRequestsTotal.get({ method: "api", outcome: "success" }),
    1,
  );
  assert.equal(
    searchRequestsTotal.get({ method: "cli", outcome: "empty" }),
    1,
  );
});

test("Collector.ProviderTelemetry — translates rows + emits cost", () => {
  providerCallsTotal.reset();
  providerCostUsdTotal.reset();
  resetProviderCursor();
  const rows = [
    {
      id: 1,
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      tokens_in: 100,
      tokens_out: 50,
      cost_usd: 0.0003,
      latency_ms: 200,
      ok: 1,
    },
    {
      id: 2,
      provider_id: "gemini",
      model: "gemini-2.5-flash-lite",
      kind: "llm",
      tokens_in: 0,
      tokens_out: 0,
      cost_usd: 0,
      latency_ms: 1000,
      ok: 0,
    },
  ];
  drainProvider(() => rows);
  assert.equal(
    providerCallsTotal.get({
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      outcome: "success",
    }),
    1,
  );
  assert.equal(
    providerCallsTotal.get({
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      outcome: "error",
    }),
    1,
  );
  assert.ok(
    providerCostUsdTotal.get({
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
    }) > 0,
  );
});

test("Collector.EventBus — translates fired events to viewer metrics", () => {
  viewerEventsTotal.reset();
  const subs = new Map<string, (p: unknown) => void>();
  const bus: EventBusLike = {
    on(e, h) {
      subs.set(e, h);
    },
    off(e) {
      subs.delete(e);
    },
  };
  attachEventBusCollector(bus);
  subs.get("viewer.event")?.({ type: "ingest" });
  subs.get("viewer.event")?.({ type: "search" });
  subs.get("viewer.event")?.({ type: "anything_outside_allowlist" });
  assert.equal(viewerEventsTotal.get({ type: "ingest" }), 1);
  assert.equal(viewerEventsTotal.get({ type: "search" }), 1);
  // unknown → bucketed to 'other' by privacy/cardinality guard chain
  assert.equal(viewerEventsTotal.get({ type: "other" }), 1);
  detachEventBusCollector(bus);
});
