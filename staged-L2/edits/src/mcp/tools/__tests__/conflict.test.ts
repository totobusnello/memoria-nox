import { test } from "node:test";
import assert from "node:assert/strict";
import { conflict_scan, conflict_list, conflict_resolve } from "../conflict.js";
import { FakeDB, seedEntity, seedRelation } from "../../../lib/conflict/__tests__/fakes.js";
import { recordConflict } from "../../../lib/conflict/audit-writer.js";

function seedDB(): FakeDB {
  const db = new FakeDB();
  seedEntity(db, 1, "toto");
  seedEntity(db, 100, "opus");
  seedEntity(db, 101, "sonnet");
  seedRelation(db, { id: 10, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 11, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  return db;
}

test("mcp: conflict_scan runs detection and records (shadow override)", () => {
  const db = seedDB();
  const r = conflict_scan(db, { mode_override: "shadow" });
  assert.equal(r.ok, true);
  const d = r.data as { detected: number; recorded: number };
  assert.equal(d.detected, 1);
  assert.equal(d.recorded, 1);
});

test("mcp: conflict_list invalid status returns error", () => {
  const db = new FakeDB();
  const r = conflict_list(db, { status: "weird" as never });
  assert.equal(r.ok, false);
  assert.equal(r.error, "invalid_status");
});

test("mcp: conflict_list happy path returns rows", () => {
  const db = seedDB();
  conflict_scan(db, { mode_override: "shadow" });
  const r = conflict_list(db, { status: "open" });
  assert.equal(r.ok, true);
  const d = r.data as { count: number };
  assert.equal(d.count, 1);
});

test("mcp: conflict_resolve refuses without NOX_MCP_ALLOW_WRITES", () => {
  const db = new FakeDB();
  recordConflict(db, {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "p",
    variants: [
      { relation_id: 1, target_entity_id: 10, confidence: 0.9, created_at: 1 },
      { relation_id: 2, target_entity_id: 11, confidence: 0.85, created_at: 2 },
    ],
  });
  const r = conflict_resolve(db, { id: 1, kind: "dismissed" }, {}); // no env
  assert.equal(r.ok, false);
  assert.equal(r.error, "mcp_write_disabled");
});

test("mcp: conflict_resolve happy path under MCP writes", () => {
  const db = new FakeDB();
  recordConflict(db, {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "p",
    variants: [
      { relation_id: 1, target_entity_id: 10, confidence: 0.9, created_at: 1 },
      { relation_id: 2, target_entity_id: 11, confidence: 0.85, created_at: 2 },
    ],
  });
  const r = conflict_resolve(
    db,
    { id: 1, kind: "pick_one", picked_relation_id: 1, actor: "mcp-toto" },
    { NOX_MCP_ALLOW_WRITES: "1" },
  );
  assert.equal(r.ok, true);
  const d = r.data as { row: { status: string; resolved_by: string } };
  assert.equal(d.row.status, "resolved_pick_one");
  assert.equal(d.row.resolved_by, "mcp-toto");
});

test("mcp: conflict_resolve pick_one without picked_relation_id errors", () => {
  const db = new FakeDB();
  recordConflict(db, {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "p",
    variants: [
      { relation_id: 1, target_entity_id: 10, confidence: 0.9, created_at: 1 },
      { relation_id: 2, target_entity_id: 11, confidence: 0.85, created_at: 2 },
    ],
  });
  const r = conflict_resolve(
    db,
    { id: 1, kind: "pick_one" },
    { NOX_MCP_ALLOW_WRITES: "1" },
  );
  assert.equal(r.ok, false);
  assert.equal(r.error, "picked_relation_id_required");
});
