import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  attachInstrumentation,
  makeTestBus,
  mapChunkCreated,
  mapKgEntityCreated,
  mapKgRelationCreated,
  mapSearchExecuted,
  mapOpAuditStarted,
  mapOpAuditCompleted,
  buildCrystallizeEvent,
} from "../instrumentation.js";
import { REDACTED } from "../redaction.js";
import { type ViewerEvent } from "../event-types.js";

describe("T2 — instrumentation", () => {
  it("mapChunkCreated produces ingest event with safe basename", () => {
    const ev = mapChunkCreated({
      chunk_id: 7,
      type: "entity",
      length: 250,
      redaction_count: 1,
      section: "compiled",
      retention_days: null,
      pain: 0.3,
      source_file: "/abs/path/note.md",
      ts: Date.now(),
    });
    assert.equal(ev.type, "ingest");
    assert.equal(ev.details.chunk_id, 7);
    assert.equal(ev.details.source_basename, "note.md");
    assert.equal(ev.details.length, 250);
  });

  it("mapChunkCreated has sane defaults", () => {
    const ev = mapChunkCreated({ chunk_id: 1, ts: Date.now() });
    assert.equal(ev.details.chunk_kind, "unknown");
    assert.equal(ev.details.length, 0);
    assert.equal(ev.details.pain, 0.2);
  });

  it("mapKgEntityCreated hashes the name", () => {
    const ev = mapKgEntityCreated({
      entity_id: 1,
      name: "Atlas",
      entity_type: "person",
      ts: Date.now(),
    });
    assert.equal(ev.type, "kg");
    if (ev.details.kg_kind !== "entity_created") {
      throw new Error("expected entity_created");
    }
    assert.equal(ev.details.name_hash.length, 8);
    assert.notEqual(ev.details.name_hash, "Atlas");
  });

  it("mapKgRelationCreated preserves FK ids", () => {
    const ev = mapKgRelationCreated({
      relation_id: 99,
      source_entity_id: 1,
      target_entity_id: 2,
      relation_type: "knows",
      ts: Date.now(),
    });
    if (ev.details.kg_kind !== "relation_created") {
      throw new Error("expected relation_created");
    }
    assert.equal(ev.details.source_entity_id, 1);
    assert.equal(ev.details.target_entity_id, 2);
  });

  it("mapSearchExecuted derives query_hash from raw query if missing", () => {
    const ev = mapSearchExecuted({
      query: "find me",
      latency_ms: 12,
      top_k: 10,
      result_count: 4,
      ts: Date.now(),
    });
    assert.equal(ev.type, "search");
    assert.equal(ev.details.query_hash.length, 16);
  });

  it("mapOpAuditStarted carries dry_run flag", () => {
    const ev = mapOpAuditStarted({
      op_id: 5,
      op_type: "reindex",
      dry_run: true,
      ts: Date.now(),
    });
    if (ev.type !== "op_audit") throw new Error("type drift");
    assert.equal(ev.details.dry_run, true);
    assert.equal(ev.details.status, "started");
  });

  it("mapOpAuditCompleted carries status + duration", () => {
    const ev = mapOpAuditCompleted({
      op_id: 5,
      op_type: "reindex",
      status: "success",
      duration_ms: 1200,
      rows_affected: 100,
      ts: Date.now(),
    });
    if (ev.type !== "op_audit") throw new Error("type drift");
    assert.equal(ev.details.status, "success");
    assert.equal(ev.details.duration_ms, 1200);
  });

  it("buildCrystallizeEvent emits status correctly", () => {
    const ev = buildCrystallizeEvent("success", 42, 5, 300);
    assert.equal(ev.type, "crystallize");
    assert.equal(ev.details.target_entity_id, 42);
    assert.equal(ev.details.duration_ms, 300);
  });

  it("attachInstrumentation routes bus → ViewerEvent → redacted", async () => {
    const bus = makeTestBus();
    const received: ViewerEvent[] = [];
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => received.push(ev),
      showQuery: false,
    });
    bus.emit("search.executed", {
      query: "secret query text",
      latency_ms: 50,
      top_k: 10,
      result_count: 5,
      ts: Date.now(),
    });
    // Synchronous fire; no async needed.
    assert.equal(received.length, 1);
    const ev = received[0]!;
    if (ev.type !== "search") throw new Error("type drift");
    assert.equal(ev.details.query, REDACTED);
    handle.detach();
  });

  it("attachInstrumentation respects showQuery=true", () => {
    const bus = makeTestBus();
    const received: ViewerEvent[] = [];
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => received.push(ev),
      showQuery: true,
    });
    bus.emit("search.executed", {
      query: "visible query",
      latency_ms: 50,
      top_k: 10,
      result_count: 5,
      ts: Date.now(),
    });
    const ev = received[0]!;
    if (ev.type !== "search") throw new Error("type drift");
    assert.equal(ev.details.query, "visible query");
    handle.detach();
  });

  it("detach stops further events", () => {
    const bus = makeTestBus();
    const received: ViewerEvent[] = [];
    const handle = attachInstrumentation(bus, {
      onEvent: (ev) => received.push(ev),
    });
    bus.emit("chunk.created", { chunk_id: 1, ts: Date.now() });
    handle.detach();
    bus.emit("chunk.created", { chunk_id: 2, ts: Date.now() });
    assert.equal(received.length, 1);
  });
});
