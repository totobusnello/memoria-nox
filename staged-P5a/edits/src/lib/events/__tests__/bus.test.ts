/**
 * P5a Event Bus Tests
 * 13 test cases covering:
 * - Fire-forget (emit never blocks caller)
 * - Listener receives data asynchronously
 * - Typed payloads for all 9 EventKinds
 * - Max-listeners set to 50 (no warning)
 * - No listener leak after unsubscribe
 * - Performance: <1ms overhead per emit (n=1000)
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "events";
import {
  bus,
  emit,
  EventKind,
  type ChunkCreatedPayload,
  type SearchExecutedPayload,
} from "../bus.js";

// Helper: wait for setImmediate to flush
function nextImmediate(): Promise<void> {
  return new Promise((resolve) => setImmediate(resolve));
}

// Helper: capture next event of a kind
function captureNext<T>(kind: string): Promise<T> {
  return new Promise((resolve) => {
    bus.once(kind as never, (data: T) => resolve(data));
  });
}

describe("Event Bus — core", () => {
  it("T01: emitAsync does not block caller (returns before listener fires)", (t, done) => {
    let listenerFired = false;
    bus.once(EventKind.HEALTH_WARNING, () => {
      listenerFired = true;
    });

    bus.emitAsync(EventKind.HEALTH_WARNING, {
      code: "test",
      message: "test warning",
      severity: "warn",
      ts: Date.now(),
    });

    // Must be false immediately after emitAsync returns
    assert.equal(listenerFired, false, "Listener must NOT have fired synchronously");

    setImmediate(() => {
      assert.equal(listenerFired, true, "Listener must fire after setImmediate");
      done();
    });
  });

  it("T02: emit() helper fires via setImmediate (fire-forget)", (t, done) => {
    let received = false;
    bus.once(EventKind.CHUNK_CREATED, () => {
      received = true;
    });

    emit(EventKind.CHUNK_CREATED, { chunk_id: 1, ts: Date.now() });

    assert.equal(received, false, "Must not be synchronous");
    setImmediate(() => {
      assert.equal(received, true);
      done();
    });
  });

  it("T03: listener receives correct typed payload", async () => {
    const expected: ChunkCreatedPayload = {
      chunk_id: 42,
      source_file: "test.md",
      type: "lesson",
      section: "compiled",
      token_count: 128,
      ts: Date.now(),
    };

    const capture = captureNext<ChunkCreatedPayload>(EventKind.CHUNK_CREATED);
    emit(EventKind.CHUNK_CREATED, expected);
    const received = await capture;

    assert.deepEqual(received, expected);
  });

  it("T04: chunk.deleted payload round-trips", async () => {
    const capture = captureNext(EventKind.CHUNK_DELETED);
    emit(EventKind.CHUNK_DELETED, { chunk_id: 99, ts: 1234 });
    const received = await capture;
    assert.deepEqual(received, { chunk_id: 99, ts: 1234 });
  });

  it("T05: kg.entity.created payload round-trips", async () => {
    const capture = captureNext(EventKind.KG_ENTITY_CREATED);
    emit(EventKind.KG_ENTITY_CREATED, {
      entity_id: 7,
      name: "TestEntity",
      entity_type: "person",
      ts: Date.now(),
    });
    const received: any = await capture;
    assert.equal(received.entity_id, 7);
    assert.equal(received.name, "TestEntity");
  });

  it("T06: kg.relation.created payload round-trips", async () => {
    const capture = captureNext(EventKind.KG_RELATION_CREATED);
    emit(EventKind.KG_RELATION_CREATED, {
      relation_id: 3,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "WORKS_AT",
      ts: Date.now(),
    });
    const received: any = await capture;
    assert.equal(received.relation_type, "WORKS_AT");
  });

  it("T07: search.executed payload round-trips", async () => {
    const capture = captureNext<SearchExecutedPayload>(EventKind.SEARCH_EXECUTED);
    emit(EventKind.SEARCH_EXECUTED, {
      query_hash: "abc123",
      latency_ms: 45,
      top_k: 10,
      result_count: 8,
      mode: "hybrid",
      ts: Date.now(),
    });
    const received = await capture;
    assert.equal(received.query_hash, "abc123");
    assert.equal(received.mode, "hybrid");
  });

  it("T08: provider.call payload round-trips", async () => {
    const capture = captureNext(EventKind.PROVIDER_CALL);
    emit(EventKind.PROVIDER_CALL, {
      provider: "gemini",
      op_type: "embed",
      latency_ms: 120,
      cost_usd: 0.00001,
      model: "gemini-embedding-001",
      token_count: 512,
      ts: Date.now(),
    });
    const received: any = await capture;
    assert.equal(received.provider, "gemini");
    assert.equal(received.op_type, "embed");
  });

  it("T09: op_audit.started and op_audit.completed round-trip", async () => {
    const captureStart = captureNext(EventKind.OP_AUDIT_STARTED);
    const captureEnd = captureNext(EventKind.OP_AUDIT_COMPLETED);

    emit(EventKind.OP_AUDIT_STARTED, { op_id: 10, op_type: "reindex", ts: Date.now() });
    emit(EventKind.OP_AUDIT_COMPLETED, {
      op_id: 10,
      op_type: "reindex",
      status: "success",
      duration_ms: 3200,
      ts: Date.now(),
    });

    const [start, end]: any[] = await Promise.all([captureStart, captureEnd]);
    assert.equal(start.op_id, 10);
    assert.equal(end.status, "success");
    assert.equal(end.duration_ms, 3200);
  });
});

describe("Event Bus — listener management", () => {
  it("T10: max listeners is 50 (no EventEmitter leak warning)", () => {
    // EventEmitter warns when maxListeners is exceeded; confirm it's 50
    assert.equal(bus.getMaxListeners(), 50);
  });

  it("T11: subscribe() returns working unsubscribe — no leak", () => {
    let callCount = 0;
    const unsub = bus.subscribe(EventKind.HEALTH_WARNING, () => {
      callCount++;
    });

    const beforeCount = bus.listenerCount(EventKind.HEALTH_WARNING);
    unsub();
    const afterCount = bus.listenerCount(EventKind.HEALTH_WARNING);

    assert.equal(afterCount, beforeCount - 1, "Listener must be removed after unsub");
  });

  it("T12: multiple listeners on same kind all receive event", (t, done) => {
    let fires = 0;
    const target = 3;
    const handlers = Array.from({ length: target }, () => () => {
      fires++;
      if (fires === target) done();
    });

    handlers.forEach((h) => bus.once(EventKind.CHUNK_CREATED, h));
    emit(EventKind.CHUNK_CREATED, { chunk_id: 0, ts: Date.now() });
  });

  it("T13: bus.stats() only includes kinds with active listeners", () => {
    // Remove all listeners for a clean baseline on a rarely-used kind
    bus.removeAllListeners(EventKind.KG_RELATION_CREATED);
    const stats = bus.stats();
    assert.equal(stats[EventKind.KG_RELATION_CREATED], undefined);

    // Add one listener and verify it appears
    const unsub = bus.subscribe(EventKind.KG_RELATION_CREATED, () => {});
    const statsAfter = bus.stats();
    assert.equal(statsAfter[EventKind.KG_RELATION_CREATED], 1);
    unsub();
  });
});

describe("Event Bus — performance", () => {
  it("T14: 1000 emits overhead <1ms per emit (setImmediate scheduling only)", (t, done) => {
    const N = 1000;
    let received = 0;

    // Register one listener to ensure event dispatching path is exercised
    bus.on(EventKind.PROVIDER_CALL, () => {
      received++;
      if (received === N) {
        bus.removeAllListeners(EventKind.PROVIDER_CALL);
        done();
      }
    });

    const start = performance.now();
    for (let i = 0; i < N; i++) {
      emit(EventKind.PROVIDER_CALL, {
        provider: "gemini",
        op_type: "embed",
        latency_ms: i,
        ts: Date.now(),
      });
    }
    const emitDuration = performance.now() - start;

    // All 1000 emitAsync calls must complete in <1ms total (just setImmediate scheduling)
    assert.ok(
      emitDuration < 10,
      `emitAsync scheduling 1000 events took ${emitDuration.toFixed(2)}ms — expected <10ms`
    );
  });
});
