import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isIngestEvent,
  isSearchEvent,
  isKgEvent,
  isCrystallizeEvent,
  isOpAuditEvent,
  isValidViewerEvent,
  eventKindLabel,
  nowIso,
  type ViewerEvent,
} from "../event-types.js";

describe("T1 — event-types", () => {
  it("nowIso returns ISO8601", () => {
    const ts = nowIso();
    assert.match(ts, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });

  it("isIngestEvent narrows correctly", () => {
    const ev: ViewerEvent = {
      ts: nowIso(),
      type: "ingest",
      source: "ingest-router",
      summary: "chunk 1 created",
      details: {
        chunk_id: 1,
        chunk_kind: "entity",
        length: 100,
        redaction_count: 0,
        section: "compiled",
        retention_days: null,
        pain: 0.2,
      },
    };
    assert.ok(isIngestEvent(ev));
    assert.equal(isSearchEvent(ev), false);
    if (isIngestEvent(ev)) {
      assert.equal(ev.details.chunk_id, 1);
    }
  });

  it("isSearchEvent narrows correctly", () => {
    const ev: ViewerEvent = {
      ts: nowIso(),
      type: "search",
      source: "search-hybrid",
      summary: "hybrid search 78ms",
      details: {
        query_hash: "abc123",
        query: "<redacted>",
        latency_ms: 78,
        top_k: 10,
        result_count: 8,
        mode: "hybrid",
        hybrid_breakdown: { bm25: 0.4, vec: 0.5, kg: 0.1 },
      },
    };
    assert.ok(isSearchEvent(ev));
    assert.equal(isKgEvent(ev), false);
  });

  it("isKgEvent narrows for both entity and relation", () => {
    const entityEv: ViewerEvent = {
      ts: nowIso(),
      type: "kg",
      source: "kg-extract",
      summary: "entity created",
      details: {
        kg_kind: "entity_created",
        entity_id: 42,
        entity_type: "person",
        name_hash: "deadbeef",
        confidence: 0.9,
      },
    };
    assert.ok(isKgEvent(entityEv));
    if (isKgEvent(entityEv) && entityEv.details.kg_kind === "entity_created") {
      assert.equal(entityEv.details.entity_id, 42);
    }

    const relEv: ViewerEvent = {
      ts: nowIso(),
      type: "kg",
      source: "kg-extract",
      summary: "relation created",
      details: {
        kg_kind: "relation_created",
        relation_id: 1,
        source_entity_id: 42,
        target_entity_id: 43,
        relation_type: "knows",
        confidence: 0.8,
      },
    };
    assert.ok(isKgEvent(relEv));
  });

  it("isCrystallizeEvent narrows correctly", () => {
    const ev: ViewerEvent = {
      ts: nowIso(),
      type: "crystallize",
      source: "crystallize",
      summary: "crystallize success",
      details: {
        source_chunk_count: 5,
        target_entity_id: 12,
        redaction_count: 0,
        status: "success",
        duration_ms: 250,
      },
    };
    assert.ok(isCrystallizeEvent(ev));
  });

  it("isOpAuditEvent narrows correctly", () => {
    const ev: ViewerEvent = {
      ts: nowIso(),
      type: "op_audit",
      source: "op-audit",
      summary: "reindex started",
      details: {
        op_id: 99,
        op: "reindex",
        status: "started",
        dry_run: false,
      },
    };
    assert.ok(isOpAuditEvent(ev));
  });

  it("isValidViewerEvent accepts good shapes", () => {
    assert.ok(
      isValidViewerEvent({
        ts: nowIso(),
        type: "ingest",
        source: "ingest-router",
        summary: "ok",
        details: { chunk_id: 1 },
      })
    );
  });

  it("isValidViewerEvent rejects bad shapes", () => {
    assert.equal(isValidViewerEvent(null), false);
    assert.equal(isValidViewerEvent({}), false);
    assert.equal(
      isValidViewerEvent({ ts: "", type: "x", source: "y", summary: "z" }),
      false
    );
    assert.equal(
      isValidViewerEvent({
        ts: nowIso(),
        type: "ingest",
        source: "bogus",
        summary: "x",
        details: {},
      }),
      false
    );
  });

  it("eventKindLabel returns granular label for kg events", () => {
    const ev: ViewerEvent = {
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
    };
    assert.equal(eventKindLabel(ev), "kg.entity_created");
  });
});
