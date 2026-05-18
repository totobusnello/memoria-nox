/**
 * Tests for `src/api/server-deps-p1.ts`.
 *
 * Strategy:
 *   - Stub the DB factory in deps-registry to return a Map-backed fake.
 *   - Probe the telemetry insert path with the wrapper directly.
 *   - Exercise sessionId extraction from headers.
 *
 * No real `answer.js` is loaded — `handleAnswerWithDeps` falls back to the
 * 503 path when the staged-P1 handler is absent, which is its own assertion.
 */

import { describe, it, before, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  buildAnswerDeps,
  handleAnswerWithDeps,
  headersFromReq,
} from "../server-deps-p1.js";
import {
  __setDbFactoryForTests,
  resetDepsRegistryForTests,
} from "../../lib/deps/deps-registry.js";

// ─── Fake DB ────────────────────────────────────────────────────────────────

class FakeStatement {
  constructor(private store: any[], private kind: "select-table" | "insert") {}
  run(...params: unknown[]): { changes: number; lastInsertRowid: number | bigint } {
    if (this.kind === "insert") {
      this.store.push(params);
      return { changes: 1, lastInsertRowid: this.store.length };
    }
    return { changes: 0, lastInsertRowid: 0 };
  }
  get<T = unknown>(): T | undefined {
    if (this.kind === "select-table") {
      return { name: "answer_telemetry" } as T;
    }
    return undefined;
  }
  all<T = unknown>(): T[] {
    return [];
  }
}

function makeFakeDb(tableExists: boolean) {
  const inserts: any[][] = [];
  return {
    inserts,
    prepare(sql: string) {
      if (sql.includes("sqlite_master")) {
        return new FakeStatement([], tableExists ? "select-table" : "insert");
      }
      if (sql.includes("INSERT INTO answer_telemetry")) {
        return new FakeStatement(inserts, "insert");
      }
      return new FakeStatement(inserts, "insert");
    },
    exec() {},
  };
}

beforeEach(() => {
  resetDepsRegistryForTests();
});

describe("server-deps-p1", () => {
  it("buildAnswerDeps returns no-op telemetry when DB is unavailable", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildAnswerDeps({ body: {} });
    assert.equal(typeof deps.telemetryStore.insert, "function");
    deps.telemetryStore.insert({
      question_hash: "abc",
      session_id: null,
      timestamp_ms: 1,
      provider: "p",
      model: "m",
      retrieval_count: 0,
      citation_count: 0,
      tokens_in: 0,
      tokens_out: 0,
      latency_ms: 1,
      fallback_used: 0,
      failed_reason: null,
      cost_estimate_usd: 0,
    });
    // No throw = pass
  });

  it("buildAnswerDeps writes to telemetry table when present", async () => {
    const fake = makeFakeDb(true);
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildAnswerDeps({ body: {} });
    deps.telemetryStore.insert({
      question_hash: "deadbeef",
      session_id: "sess-1",
      timestamp_ms: 1234,
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      retrieval_count: 5,
      citation_count: 2,
      tokens_in: 100,
      tokens_out: 80,
      latency_ms: 200,
      fallback_used: 0,
      failed_reason: null,
      cost_estimate_usd: 0.0001,
    });
    assert.equal(fake.inserts.length, 1);
    assert.equal(fake.inserts[0]![0], "deadbeef");
    assert.equal(fake.inserts[0]![1], "sess-1");
  });

  it("extracts sessionId from X-Session-Id header", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildAnswerDeps({
      body: {},
      headers: { "x-session-id": "abc-123" },
    });
    assert.equal(deps.sessionId, "abc-123");
  });

  it("sessionId is null when header absent", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildAnswerDeps({ body: {} });
    assert.equal(deps.sessionId, null);
  });

  it("handleAnswerWithDeps emits 503 when handler module missing", async () => {
    __setDbFactoryForTests(() => null);
    const out = await handleAnswerWithDeps({ body: { question: "hi" } });
    // The dynamic import of "../../../staged-P1/edits/src/api/answer.js" will
    // fail in this isolated test environment, falling back to 503.
    assert.equal(out.status, 503);
    assert.ok(typeof out.body === "object");
    const body = out.body as Record<string, unknown>;
    assert.equal(body["error"], "not_implemented");
  });

  it("headersFromReq returns headers map", () => {
    const fakeReq = {
      headers: { "x-trace-id": "trace-1", "content-type": "application/json" },
    } as any;
    const h = headersFromReq(fakeReq);
    assert.equal(h["x-trace-id"], "trace-1");
  });
});
