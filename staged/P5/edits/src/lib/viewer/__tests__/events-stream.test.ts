import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  openSseStream,
  formatSseMessage,
  formatHeartbeat,
  parseLastEventId,
  SSE_HEADERS,
} from "../../../api/events-stream.js";
import { Broadcaster, type BroadcastEnvelope } from "../broadcast.js";
import { nowIso, type ViewerEvent } from "../event-types.js";

function makeEvent(id: number): ViewerEvent {
  return {
    ts: nowIso(),
    type: "ingest",
    source: "ingest-router",
    summary: `chunk ${id}`,
    details: {
      chunk_id: id,
      chunk_kind: "entity",
      length: 100,
      redaction_count: 0,
      section: null,
      retention_days: null,
      pain: 0.2,
    },
  };
}

describe("T3 — SSE handler", () => {
  it("SSE_HEADERS includes required content-type", () => {
    assert.match(SSE_HEADERS["Content-Type"]!, /text\/event-stream/);
    assert.equal(SSE_HEADERS["Cache-Control"], "no-cache, no-transform");
    assert.equal(SSE_HEADERS["X-Accel-Buffering"], "no");
  });

  it("formatSseMessage emits id + event + data per RFC", () => {
    const env: BroadcastEnvelope = { id: 42, ev: makeEvent(1) };
    const msg = formatSseMessage(env);
    assert.match(msg, /^id: 42\n/);
    assert.match(msg, /event: ingest\n/);
    assert.match(msg, /data: \{.*\}\n\n$/);
  });

  it("formatSseMessage uses granular kind for kg events", () => {
    const env: BroadcastEnvelope = {
      id: 1,
      ev: {
        ts: nowIso(),
        type: "kg",
        source: "kg-extract",
        summary: "x",
        details: {
          kg_kind: "entity_created",
          entity_id: 1,
          entity_type: "person",
          name_hash: "h",
          confidence: 1,
        },
      },
    };
    const msg = formatSseMessage(env);
    assert.match(msg, /event: kg\.entity_created\n/);
  });

  it("formatHeartbeat emits comment line", () => {
    const hb = formatHeartbeat(10, 2);
    assert.match(hb, /^: heartbeat .* ring=10 clients=2\n\n$/);
  });

  it("parseLastEventId reads number from headers", () => {
    assert.equal(parseLastEventId({ "Last-Event-ID": "42" }), 42);
    assert.equal(parseLastEventId({ "last-event-id": "0" }), 0);
    assert.equal(parseLastEventId({}), undefined);
    assert.equal(parseLastEventId({ "last-event-id": "bad" }), undefined);
  });

  it("openSseStream yields connected comment first", async () => {
    const b = new Broadcaster();
    const s = openSseStream({ broadcaster: b, clientId: "c1" });
    const it = s.iter[Symbol.asyncIterator]();
    const first = await it.next();
    assert.equal(first.done, false);
    assert.match(first.value!, /^: connected/);
    s.close();
  });

  it("openSseStream forwards events to client", async () => {
    const b = new Broadcaster();
    const s = openSseStream({ broadcaster: b, clientId: "c1" });
    const it = s.iter[Symbol.asyncIterator]();
    await it.next(); // connected line
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    const first = await it.next();
    assert.match(first.value!, /id: 1/);
    const second = await it.next();
    assert.match(second.value!, /id: 2/);
    s.close();
  });

  it("openSseStream replays from lastEventId on reconnect", async () => {
    const b = new Broadcaster();
    b.publish(makeEvent(1));
    b.publish(makeEvent(2));
    b.publish(makeEvent(3));
    const s = openSseStream({ broadcaster: b, clientId: "c1", lastEventId: 1 });
    const it = s.iter[Symbol.asyncIterator]();
    await it.next(); // connected
    const a = await it.next();
    assert.match(a.value!, /id: 2/);
    const c = await it.next();
    assert.match(c.value!, /id: 3/);
    s.close();
  });

  it("close stops the iterator and removes client", async () => {
    const b = new Broadcaster();
    const s = openSseStream({ broadcaster: b, clientId: "c1" });
    const it = s.iter[Symbol.asyncIterator]();
    await it.next();
    s.close();
    const done = await it.next();
    assert.equal(done.done, true);
    assert.equal(b.clientCount(), 0);
  });

  it("onWrite hook fires per event", async () => {
    const b = new Broadcaster();
    let count = 0;
    const s = openSseStream({
      broadcaster: b,
      clientId: "c1",
      onWrite: () => { count += 1; },
    });
    const it = s.iter[Symbol.asyncIterator]();
    await it.next();
    b.publish(makeEvent(1));
    await it.next();
    assert.equal(count, 1);
    s.close();
  });

  it("multiple clients each receive same events", async () => {
    const b = new Broadcaster();
    const s1 = openSseStream({ broadcaster: b, clientId: "c1" });
    const s2 = openSseStream({ broadcaster: b, clientId: "c2" });
    const it1 = s1.iter[Symbol.asyncIterator]();
    const it2 = s2.iter[Symbol.asyncIterator]();
    await it1.next();
    await it2.next();
    b.publish(makeEvent(1));
    const a = await it1.next();
    const b2 = await it2.next();
    assert.match(a.value!, /id: 1/);
    assert.match(b2.value!, /id: 1/);
    s1.close();
    s2.close();
  });

  it("ringSnapshot remains intact across reconnect", () => {
    const b = new Broadcaster({ ringCapacity: 5 });
    for (let i = 0; i < 3; i += 1) b.publish(makeEvent(i));
    assert.equal(b.ringSnapshot().length, 3);
  });

  it("parseLastEventId rejects negative", () => {
    assert.equal(parseLastEventId({ "last-event-id": "-5" }), undefined);
  });
});
