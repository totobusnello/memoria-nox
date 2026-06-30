/**
 * T14 — Integration test
 *
 * End-to-end through the in-memory stack:
 *   bus → instrumentation → redaction → broadcaster → SSE handler → client
 *
 * No HTTP server is started — we exercise the async generator directly.
 * This catches the load-bearing wiring: redaction guards, ordering, fan-out,
 * Last-Event-ID resume, and disconnect cleanup.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";

import { attachInstrumentation } from "../instrumentation.js";
import { Broadcaster, type BroadcastEnvelope } from "../broadcast.js";
import { openSseStream } from "../../../api/events-stream.js";
import { recentEvents } from "../../../mcp/tools/viewer.js";
import { REDACTED } from "../redaction.js";
import {
  InMemorySessionStore,
  openSession,
  recordEvent,
  closeSession,
  mintClientId,
} from "../session.js";

interface MiniClient {
  events: string[];
  drain: () => Promise<void>;
  stop: () => void;
}

async function collect(
  iter: AsyncIterable<string>,
  count: number,
  timeoutMs = 2000
): Promise<string[]> {
  const out: string[] = [];
  const it = iter[Symbol.asyncIterator]();
  const deadline = Date.now() + timeoutMs;
  while (out.length < count) {
    if (Date.now() > deadline) {
      throw new Error(
        `timeout waiting for ${count} messages; got ${out.length}`
      );
    }
    const r = await it.next();
    if (r.done) break;
    out.push(r.value);
  }
  return out;
}

describe("T14 — integration", () => {
  it("bus -> instrumentation -> broadcast -> SSE redacts query", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
      showQuery: false,
    });
    const sse = openSseStream({ broadcaster, clientId: "c1" });

    bus.emit("search.executed", {
      query: "very-secret-query",
      latency_ms: 12,
      top_k: 10,
      result_count: 5,
      ts: Date.now(),
    });
    bus.emit("chunk.created", {
      chunk_id: 1,
      type: "entity",
      length: 100,
      ts: Date.now(),
    });
    bus.emit("kg.entity.created", {
      entity_id: 7,
      name: "Atlas",
      entity_type: "person",
      ts: Date.now(),
    });

    const lines = await collect(sse.iter, 4);
    // First line = ": connected"
    assert.match(lines[0]!, /^: connected/);
    const joined = lines.join("\n");
    assert.equal(
      joined.includes("very-secret-query"),
      false,
      "raw query must not appear in stream"
    );
    assert.equal(joined.includes("Atlas"), false, "raw entity name leaked");
    assert.match(joined, new RegExp(REDACTED));

    sse.close();
    handle.detach();
  });

  it("multi-client fan-out: both clients receive same events", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    const s1 = openSseStream({ broadcaster, clientId: "c1" });
    const s2 = openSseStream({ broadcaster, clientId: "c2" });

    bus.emit("chunk.created", { chunk_id: 1, ts: Date.now() });
    bus.emit("chunk.created", { chunk_id: 2, ts: Date.now() });

    const l1 = await collect(s1.iter, 3);
    const l2 = await collect(s2.iter, 3);
    // Verify both got 2 chunk.created events in order
    const c1Ids = l1.filter((m) => m.includes("data:")).map(
      (m) => /id: (\d+)/.exec(m)?.[1]
    );
    const c2Ids = l2.filter((m) => m.includes("data:")).map(
      (m) => /id: (\d+)/.exec(m)?.[1]
    );
    assert.deepEqual(c1Ids, c2Ids);
    assert.equal(c1Ids.length, 2);
    s1.close();
    s2.close();
    handle.detach();
  });

  it("Last-Event-ID resume seeds gap from ring", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster({ ringCapacity: 10 });
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    for (let i = 1; i <= 5; i += 1) {
      bus.emit("chunk.created", { chunk_id: i, ts: Date.now() });
    }
    // Reconnect from lastEventId=2 — should get ids 3,4,5
    const sse = openSseStream({
      broadcaster,
      clientId: "c1",
      lastEventId: 2,
    });
    const lines = await collect(sse.iter, 4);
    const idLines = lines.filter((l) => /^id: \d+/.test(l));
    const ids = idLines.map((l) => /^id: (\d+)/.exec(l)![1]);
    assert.deepEqual(ids, ["3", "4", "5"]);
    sse.close();
    handle.detach();
  });

  it("ordering preserved across mixed event types", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    const sse = openSseStream({ broadcaster, clientId: "c1" });

    bus.emit("chunk.created", { chunk_id: 1, ts: Date.now() });
    bus.emit("search.executed", {
      latency_ms: 1,
      top_k: 1,
      result_count: 0,
      ts: Date.now(),
    });
    bus.emit("kg.entity.created", {
      entity_id: 1,
      name: "x",
      entity_type: "y",
      ts: Date.now(),
    });
    bus.emit("op_audit.started", { op_id: 1, op_type: "reindex", ts: Date.now() });
    bus.emit("op_audit.completed", {
      op_id: 1,
      op_type: "reindex",
      status: "success",
      duration_ms: 10,
      ts: Date.now(),
    });

    const lines = await collect(sse.iter, 6);
    const idLines = lines.filter((l) => /^id: \d+/.test(l));
    const ids = idLines.map((l) => Number(/^id: (\d+)/.exec(l)![1]));
    for (let i = 1; i < ids.length; i += 1) {
      assert.ok(ids[i]! > ids[i - 1]!, "ids monotonic");
    }
    sse.close();
    handle.detach();
  });

  it("session lifecycle integrates with SSE stream", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const store = new InMemorySessionStore();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    const cid = mintClientId();
    const ctx = await openSession(store, cid, "127.0.0.1");
    const sse = openSseStream({
      broadcaster,
      clientId: cid,
      onWrite: () => {
        // Fire-and-forget for test.
        void recordEvent(store, ctx);
      },
    });
    bus.emit("chunk.created", { chunk_id: 1, ts: Date.now() });
    bus.emit("chunk.created", { chunk_id: 2, ts: Date.now() });
    await collect(sse.iter, 3);
    sse.close();
    await closeSession(store, ctx);
    const rows = await store.list();
    assert.equal(rows[0]!.events_consumed >= 1, true);
    assert.notEqual(rows[0]!.ts_end, null);
    handle.detach();
  });

  it("MCP recent_events returns post-redaction items", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
      showQuery: false,
    });
    bus.emit("search.executed", {
      query: "hidden-text",
      latency_ms: 8,
      top_k: 3,
      result_count: 1,
      ts: Date.now(),
    });
    const out = recentEvents(broadcaster, { type_filter: "search" });
    assert.equal(out.count, 1);
    const ev = out.items[0]!.ev;
    if (ev.type !== "search") throw new Error("type drift");
    assert.equal(ev.details.query, REDACTED);
    handle.detach();
  });

  it("disconnect cleans up client from broadcaster", async () => {
    const broadcaster = new Broadcaster();
    const sse = openSseStream({ broadcaster, clientId: "c1" });
    assert.equal(broadcaster.clientCount(), 1);
    sse.close();
    assert.equal(broadcaster.clientCount(), 0);
  });

  it("backpressure: slow client drops oldest without affecting fast client", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster({ clientCapacity: 5 });
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    const slow = broadcaster.addClient("slow", () => {});
    const fast = broadcaster.addClient("fast", () => {});
    for (let i = 0; i < 20; i += 1) {
      bus.emit("chunk.created", { chunk_id: i, ts: Date.now() });
    }
    fast.queue.drain();
    bus.emit("chunk.created", { chunk_id: 100, ts: Date.now() });
    assert.equal(fast.queue.length, 1);
    assert.ok(slow.queue.stats().dropped > 0);
    handle.detach();
  });

  it("redaction strips forbidden field names that sneak in", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    // Simulate a malformed payload where someone added `content`.
    bus.emit("chunk.created", {
      chunk_id: 1,
      type: "entity",
      ts: Date.now(),
      content: "this should never leak",
    } as unknown as Record<string, unknown>);
    const ring = broadcaster.ringSnapshot();
    assert.equal(JSON.stringify(ring).includes("this should never leak"), false);
    handle.detach();
  });

  it("event count from instrumentation handle matches publishes", () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    for (let i = 0; i < 7; i += 1) {
      bus.emit("chunk.created", { chunk_id: i, ts: Date.now() });
    }
    assert.equal(handle.emitted(), 7);
    handle.detach();
  });

  it("ring buffer eviction does not break new clients", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster({ ringCapacity: 3 });
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    for (let i = 0; i < 10; i += 1) {
      bus.emit("chunk.created", { chunk_id: i, ts: Date.now() });
    }
    const sse = openSseStream({
      broadcaster,
      clientId: "fresh",
      lastEventId: 0,
    });
    const lines = await collect(sse.iter, 4);
    const ids = lines
      .filter((l) => /^id: /.test(l))
      .map((l) => Number(/^id: (\d+)/.exec(l)![1]));
    assert.equal(ids.length, 3);
    sse.close();
    handle.detach();
  });

  it("multiple kg event types both surface through stream", async () => {
    const bus = new EventEmitter();
    const broadcaster = new Broadcaster();
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => broadcaster.publish(ev),
    });
    const sse = openSseStream({ broadcaster, clientId: "c1" });
    bus.emit("kg.entity.created", {
      entity_id: 1,
      name: "n",
      entity_type: "person",
      ts: Date.now(),
    });
    bus.emit("kg.relation.created", {
      relation_id: 1,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "knows",
      ts: Date.now(),
    });
    const lines = await collect(sse.iter, 3);
    const joined = lines.join("\n");
    assert.match(joined, /event: kg\.entity_created/);
    assert.match(joined, /event: kg\.relation_created/);
    sse.close();
    handle.detach();
  });
});

// Mark the helper as referenced for unused-import lint hygiene
void (null as unknown as MiniClient);
void (null as unknown as BroadcastEnvelope);
