import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  recentEvents,
  validateInput,
  VIEWER_MCP_DESCRIPTOR,
} from "../../../mcp/tools/viewer.js";
import { Broadcaster } from "../broadcast.js";
import { nowIso, type ViewerEvent } from "../event-types.js";

function makeIngest(id: number): ViewerEvent {
  return {
    ts: nowIso(),
    type: "ingest",
    source: "ingest-router",
    summary: `c${id}`,
    details: {
      chunk_id: id,
      chunk_kind: "entity",
      length: 0,
      redaction_count: 0,
      section: null,
      retention_days: null,
      pain: 0.2,
    },
  };
}

function makeSearch(): ViewerEvent {
  return {
    ts: nowIso(),
    type: "search",
    source: "search-hybrid",
    summary: "s",
    details: {
      query_hash: "h",
      query: "<redacted>",
      latency_ms: 10,
      top_k: 5,
      result_count: 3,
      mode: "hybrid",
      hybrid_breakdown: { bm25: 0.3, vec: 0.6, kg: 0.1 },
    },
  };
}

describe("T13 — MCP viewer_recent_events", () => {
  it("validateInput defaults", () => {
    const v = validateInput({});
    assert.equal(v.limit, 50);
    assert.equal(v.filter, "all");
  });

  it("validateInput clamps to max 200", () => {
    const v = validateInput({ limit: 1000 });
    assert.equal(v.limit, 200);
  });

  it("validateInput rejects invalid limit", () => {
    const v = validateInput({ limit: -1 });
    assert.equal(v.limit, 50);
  });

  it("recentEvents returns last N items", () => {
    const b = new Broadcaster();
    for (let i = 1; i <= 10; i += 1) b.publish(makeIngest(i));
    const out = recentEvents(b, { limit: 3 });
    assert.equal(out.count, 3);
    assert.equal(out.items[0]!.id, 8);
    assert.equal(out.items[2]!.id, 10);
  });

  it("recentEvents filters by type", () => {
    const b = new Broadcaster();
    b.publish(makeIngest(1));
    b.publish(makeSearch());
    b.publish(makeIngest(2));
    const out = recentEvents(b, { type_filter: "search" });
    assert.equal(out.count, 1);
    assert.equal(out.items[0]!.ev.type, "search");
  });

  it("recentEvents default all", () => {
    const b = new Broadcaster();
    b.publish(makeIngest(1));
    b.publish(makeSearch());
    const out = recentEvents(b);
    assert.equal(out.count, 2);
    assert.equal(out.filter, "all");
  });

  it("VIEWER_MCP_DESCRIPTOR schema includes enum filter", () => {
    const enums =
      VIEWER_MCP_DESCRIPTOR.inputSchema.properties.type_filter.enum;
    assert.ok(enums.includes("ingest"));
    assert.ok(enums.includes("all"));
  });
});
