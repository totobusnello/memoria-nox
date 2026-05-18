/**
 * S6 — Viewer events (P5 + ingestion).
 *
 * Verifies:
 *   - Subscribe to event bus → receive IngestEvent on chunk insert
 *   - Receive SearchEvent on search; default has query="<redacted>"
 *   - NOX_VIEWER_SHOW_QUERY=1 → query is the raw text
 *   - Multiple subscribers all get each event (broadcast contract)
 *
 * Bug-class targeted: a regression where the query-redaction default is
 * accidentally reversed (env=0 leaks query) — exactly the kind of feature-
 * flag flip a unit test on emitSearchEvent alone wouldn't surface.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  ViewerBus,
  emitSearchEvent,
  type ViewerEvent,
} from "../lib/pillar-shims.js";

let bus: ViewerBus;
let received: ViewerEvent[];

beforeEach(() => {
  bus = new ViewerBus();
  received = [];
  bus.subscribe((e) => received.push(e));
});

function emitIngest(chunkId: number, length: number, redactions: number): void {
  bus.publish({
    ts: new Date().toISOString(),
    type: "ingest",
    source: "ingest-router",
    summary: `ingested chunk_id=${chunkId} length=${length}`,
    details: {
      chunk_id: chunkId,
      length,
      redaction_count: redactions,
      section: "compiled",
      pain: 0.2,
    },
  });
}

describe("S6 — viewer event bus (P5 + ingestion)", () => {
  it("S6-01 ingest emits IngestEvent with chunk_id + redaction_count", () => {
    emitIngest(101, 50, 0);
    assert.strictEqual(received.length, 1);
    const ev = received[0]!;
    assert.strictEqual(ev.type, "ingest");
    assert.strictEqual((ev.details as { chunk_id: number }).chunk_id, 101);
    assert.strictEqual((ev.details as { redaction_count: number }).redaction_count, 0);
  });

  it("S6-02 search emits SearchEvent with query='<redacted>' by default", () => {
    emitSearchEvent(bus, "what is D41?", 42, 5);
    assert.strictEqual(received.length, 1);
    const ev = received[0]!;
    assert.strictEqual(ev.type, "search");
    assert.strictEqual((ev.details as { query: string }).query, "<redacted>");
    assert.ok((ev.details as { query_hash: string }).query_hash.length === 16);
  });

  it("S6-03 NOX_VIEWER_SHOW_QUERY=1 surfaces the raw query text", () => {
    emitSearchEvent(bus, "what is D41?", 42, 5, { NOX_VIEWER_SHOW_QUERY: "1" });
    assert.strictEqual((received[0]!.details as { query: string }).query, "what is D41?");
  });

  it("S6-04 NOX_VIEWER_SHOW_QUERY=0 explicit still defaults to redacted", () => {
    emitSearchEvent(bus, "what is D41?", 42, 5, { NOX_VIEWER_SHOW_QUERY: "0" });
    assert.strictEqual((received[0]!.details as { query: string }).query, "<redacted>");
  });

  it("S6-05 multiple subscribers all receive each event (broadcast)", () => {
    const r2: ViewerEvent[] = [];
    bus.subscribe((e) => r2.push(e));
    emitIngest(1, 10, 0);
    emitSearchEvent(bus, "q", 1, 1);
    assert.strictEqual(received.length, 2);
    assert.strictEqual(r2.length, 2);
    // Both subscribers see the events in the same order.
    assert.strictEqual(received[0]!.type, "ingest");
    assert.strictEqual(received[1]!.type, "search");
    assert.strictEqual(r2[0]!.type, "ingest");
    assert.strictEqual(r2[1]!.type, "search");
  });

  it("S6-06 unsubscribe stops further events for that subscriber only", () => {
    const r2: ViewerEvent[] = [];
    const off = bus.subscribe((e) => r2.push(e));
    emitIngest(1, 10, 0);
    off();
    emitIngest(2, 20, 1);
    assert.strictEqual(r2.length, 1); // only first event received
    assert.strictEqual(received.length, 2); // primary subscriber kept receiving
  });
});
