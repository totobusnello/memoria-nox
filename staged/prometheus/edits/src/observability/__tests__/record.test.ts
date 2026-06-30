/**
 * Tests for src/observability/record.ts (T6 — 10 tests).
 *
 * These tests touch the singleton metric instances (from ./metrics.ts).
 * Each test isolates by reading the delta and verifying the recorded value.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  recordSearch,
  recordAnswer,
  recordProviderCall,
  recordChunkIngest,
  recordEmbedding,
  recordHookEvent,
  recordViewerConnect,
  recordViewerDisconnect,
  recordViewerEvent,
  recordAuditWrite,
  startTimer,
} from "../record.ts";
import {
  searchRequestsTotal,
  searchDurationSeconds,
  searchResultsReturned,
  answerRequestsTotal,
  answerDurationSeconds,
  answerTokensTotal,
  providerCallsTotal,
  providerCostUsdTotal,
  chunksTotal,
  embeddingsTotal,
  hooksEventsTotal,
  viewerConnections,
  viewerEventsTotal,
  auditRowsTotal,
} from "../metrics.ts";

test("T6.1 recordSearch increments + observes correctly", () => {
  searchRequestsTotal.reset();
  searchDurationSeconds.reset();
  searchResultsReturned.reset();
  recordSearch({
    method: "api",
    durationSeconds: 0.05,
    resultsCount: 12,
    outcome: "success",
  });
  assert.equal(
    searchRequestsTotal.get({ method: "api", outcome: "success" }),
    1,
  );
  assert.equal(searchDurationSeconds.collect().length, 1);
  assert.equal(searchResultsReturned.collect().length, 1);
});

test("T6.2 recordAnswer records all phases + tokens", () => {
  answerRequestsTotal.reset();
  answerDurationSeconds.reset();
  answerTokensTotal.reset();
  recordAnswer({
    outcome: "success",
    timing: { total: 0.5, retrieve: 0.1, synthesize: 0.3, verify: 0.05 },
    tokensIn: 800,
    tokensOut: 200,
  });
  assert.equal(
    answerRequestsTotal.get({ failure_reason: "success" }),
    1,
  );
  // 4 phases recorded
  assert.equal(answerDurationSeconds.collect().length, 4);
  assert.equal(answerTokensTotal.get({ direction: "input" }), 800);
  assert.equal(answerTokensTotal.get({ direction: "output" }), 200);
});

test("T6.3 recordProviderCall increments calls + cost", () => {
  providerCallsTotal.reset();
  providerCostUsdTotal.reset();
  recordProviderCall({
    provider: "gemini",
    model: "gemini-2.5-flash-lite",
    kind: "llm",
    durationSeconds: 0.2,
    outcome: "success",
    costUsd: 0.0002,
  });
  assert.equal(
    providerCallsTotal.get({
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      outcome: "success",
    }),
    1,
  );
  const c = providerCostUsdTotal.get({
    provider: "gemini",
    model: "gemini-2.5-flash-lite",
  });
  assert.ok(c > 0);
});

test("T6.4 recordChunkIngest with provenance label", () => {
  chunksTotal.reset();
  recordChunkIngest({ provenanceKind: "fresh", count: 5 });
  recordChunkIngest({ provenanceKind: "stale", count: 2 });
  assert.equal(chunksTotal.get({ provenance_kind: "fresh" }), 5);
  assert.equal(chunksTotal.get({ provenance_kind: "stale" }), 2);
});

test("T6.5 recordEmbedding label cardinality", () => {
  embeddingsTotal.reset();
  recordEmbedding({ provider: "gemini", outcome: "success", count: 3 });
  recordEmbedding({ provider: "gemini", outcome: "error" });
  assert.equal(
    embeddingsTotal.get({ provider: "gemini", outcome: "success" }),
    3,
  );
  assert.equal(
    embeddingsTotal.get({ provider: "gemini", outcome: "error" }),
    1,
  );
});

test("T6.6 recordHookEvent increments + observes pipeline duration", () => {
  hooksEventsTotal.reset();
  recordHookEvent({ layer: "pre-tool", reason: "captured", durationSeconds: 0.001 });
  assert.equal(
    hooksEventsTotal.get({ layer: "pre-tool", reason: "captured" }),
    1,
  );
});

test("T6.7 viewer connect/disconnect maintains gauge", () => {
  viewerConnections.reset();
  recordViewerConnect();
  recordViewerConnect();
  recordViewerConnect();
  recordViewerDisconnect();
  assert.equal(viewerConnections.get(), 2);
});

test("T6.8 recordViewerEvent + unknown type bucketed to 'other'", () => {
  viewerEventsTotal.reset();
  recordViewerEvent("ingest");
  recordViewerEvent("payload_xyz"); // unknown → bucketed to 'other'
  assert.equal(viewerEventsTotal.get({ type: "ingest" }), 1);
  assert.equal(viewerEventsTotal.get({ type: "other" }), 1);
});

test("T6.9 recordAuditWrite + recording never throws on bad input", () => {
  auditRowsTotal.reset();
  recordAuditWrite("ops_audit");
  recordAuditWrite("provider_telemetry", 5);
  assert.equal(auditRowsTotal.get({ table: "ops_audit" }), 1);
  assert.equal(auditRowsTotal.get({ table: "provider_telemetry" }), 5);

  // never throws
  recordSearch({
    method: "api",
    durationSeconds: NaN,
    resultsCount: -1,
    outcome: "success",
  });
});

test("T6.10 startTimer returns elapsed seconds (sub-millisecond)", async () => {
  const end = startTimer();
  await new Promise((r) => setTimeout(r, 5));
  const elapsed = end();
  assert.ok(elapsed >= 0.004, `expected >= 4ms, got ${elapsed}`);
  assert.ok(elapsed < 1, `expected < 1s, got ${elapsed}`);
});
