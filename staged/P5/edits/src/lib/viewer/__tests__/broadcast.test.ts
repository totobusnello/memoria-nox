import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Broadcaster } from "../broadcast.js";
import { type ViewerEvent, nowIso } from "../event-types.js";

function makeEvent(chunk_id: number): ViewerEvent {
  return {
    ts: nowIso(),
    type: "ingest",
    source: "ingest-router",
    summary: `chunk ${chunk_id}`,
    details: {
      chunk_id,
      chunk_kind: "entity",
      length: 100,
      redaction_count: 0,
      section: null,
      retention_days: null,
      pain: 0.2,
    },
  };
}

describe("T10 — broadcast", () => {
  it("publish increments id monotonically", () => {
    const b = new Broadcaster();
    const a = b.publish(makeEvent(1));
    const c = b.publish(makeEvent(2));
    assert.equal(a.id, 1);
    assert.equal(c.id, 2);
  });

  it("ring buffer holds last N envelopes", () => {
    const b = new Broadcaster({ ringCapacity: 3 });
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    b.publish(makeEvent(3));
    b.publish(makeEvent(4));
    const snap = b.ringSnapshot();
    assert.equal(snap.length, 3);
    assert.equal(snap[0]!.id, 2);
    assert.equal(snap[2]!.id, 4);
  });

  it("addClient with no lastEventId starts empty", () => {
    const b = new Broadcaster();
    b.publish(makeEvent(1));
    const c = b.addClient("c1", () => {});
    assert.equal(c.queue.length, 0);
  });

  it("addClient with lastEventId pre-seeds gap from ring", () => {
    const b = new Broadcaster();
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    b.publish(makeEvent(3));
    const c = b.addClient("c1", () => {}, 1);
    // Should have envelopes id=2 and id=3
    assert.equal(c.queue.length, 2);
    const items = c.queue.drain();
    assert.equal(items[0]!.id, 2);
    assert.equal(items[1]!.id, 3);
  });

  it("publish fans out to all connected clients", () => {
    const b = new Broadcaster();
    let n1 = 0;
    let n2 = 0;
    const c1 = b.addClient("c1", () => { n1 += 1; });
    const c2 = b.addClient("c2", () => { n2 += 1; });
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    assert.equal(c1.queue.length, 2);
    assert.equal(c2.queue.length, 2);
    assert.equal(n1, 2);
    assert.equal(n2, 2);
  });

  it("slow client does not stall fast client", () => {
    const b = new Broadcaster({ clientCapacity: 5 });
    const slow = b.addClient("slow", () => {});
    const fast = b.addClient("fast", () => {});
    for (let i = 0; i < 20; i += 1) b.publish(makeEvent(i));
    // Both queues capped at 5
    assert.equal(slow.queue.length, 5);
    assert.equal(fast.queue.length, 5);
    // But fast drains, slow does not — only slow accrues drops next round
    fast.queue.drain();
    for (let i = 0; i < 3; i += 1) b.publish(makeEvent(100 + i));
    assert.equal(fast.queue.length, 3);
    assert.equal(slow.queue.stats().dropped > 0, true);
  });

  it("removeClient detaches", () => {
    const b = new Broadcaster();
    b.addClient("c1", () => {});
    b.removeClient("c1");
    b.publish(makeEvent(1));
    assert.equal(b.clientCount(), 0);
  });

  it("clientStats returns per-client snapshot", () => {
    const b = new Broadcaster();
    b.addClient("c1", () => {});
    b.publish(makeEvent(1));
    const stats = b.clientStats();
    assert.equal(stats.length, 1);
    assert.equal(stats[0]!.id, "c1");
    assert.equal(stats[0]!.queueSize, 1);
  });

  it("trimRingTo drops oldest globally", () => {
    const b = new Broadcaster({ ringCapacity: 10 });
    for (let i = 0; i < 8; i += 1) b.publish(makeEvent(i));
    const dropped = b.trimRingTo(3);
    assert.equal(dropped, 5);
    const snap = b.ringSnapshot();
    assert.equal(snap.length, 3);
  });

  it("notify hook is called per publish", () => {
    const b = new Broadcaster();
    let called = 0;
    b.addClient("c1", () => { called += 1; });
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    b.publish(makeEvent(3));
    assert.equal(called, 3);
  });
});
