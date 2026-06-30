import { test } from "node:test";
import assert from "node:assert/strict";
import {
  recordConflict,
  updateConflictStatus,
  getConflictById,
  listConflicts,
  statusCounts,
} from "../audit-writer.js";
import { FakeDB } from "./fakes.js";
import type { Conflict } from "../types.js";

function fixture(overrides: Partial<Conflict> = {}): Conflict {
  return {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "uses_model",
    variants: [
      { relation_id: 10, target_entity_id: 100, confidence: 0.9, created_at: 1 },
      { relation_id: 11, target_entity_id: 101, confidence: 0.85, created_at: 2 },
    ],
    ...overrides,
  };
}

test("audit-writer: recordConflict inserts a new row when none open", () => {
  const db = new FakeDB();
  const r = recordConflict(db, fixture());
  assert.ok(r.id > 0);
  assert.equal(r.deduplicated, false);
  const row = getConflictById(db, r.id);
  assert.ok(row);
  assert.equal(row!.kind, "direct");
  assert.equal(row!.status, "open");
  assert.equal(row!.shadow_mode, 1);
  assert.deepEqual(row!.target_relation_ids, [10, 11]);
});

test("audit-writer: recordConflict dedupes on (subject, predicate, open)", () => {
  const db = new FakeDB();
  const first = recordConflict(db, fixture());
  const second = recordConflict(db, fixture());
  assert.equal(second.deduplicated, true);
  assert.equal(second.id, first.id);
});

test("audit-writer: recordConflict force=true bypasses dedupe", () => {
  const db = new FakeDB();
  const first = recordConflict(db, fixture());
  const second = recordConflict(db, fixture(), null, { force: true });
  assert.equal(second.deduplicated, false);
  assert.notEqual(second.id, first.id);
});

test("audit-writer: recordConflict shadow_mode=0 writes active row", () => {
  const db = new FakeDB();
  const r = recordConflict(db, fixture(), null, { shadow_mode: 0 });
  const row = getConflictById(db, r.id);
  assert.equal(row!.shadow_mode, 0);
});

test("audit-writer: updateConflictStatus marks resolved_pick_one with timestamp", () => {
  const db = new FakeDB();
  const r = recordConflict(db, fixture());
  updateConflictStatus(db, r.id, {
    status: "resolved_pick_one",
    resolved_by: "toto",
    resolution_kind: "pick_one",
    picked_relation_id: 10,
    notes: "opus is canonical",
  });
  const row = getConflictById(db, r.id);
  assert.equal(row!.status, "resolved_pick_one");
  assert.equal(row!.resolution_kind, "pick_one");
  assert.equal(row!.picked_relation_id, 10);
  assert.equal(row!.resolved_by, "toto");
  assert.ok(row!.resolved_at != null);
  assert.equal(row!.notes, "opus is canonical");
});

test("audit-writer: pick_one without picked_relation_id throws", () => {
  const db = new FakeDB();
  const r = recordConflict(db, fixture());
  assert.throws(
    () =>
      updateConflictStatus(db, r.id, {
        status: "resolved_pick_one",
        resolved_by: "toto",
        resolution_kind: "pick_one",
      }),
    /picked_relation_id/,
  );
});

test("audit-writer: merged without merge_target throws", () => {
  const db = new FakeDB();
  const r = recordConflict(db, fixture());
  assert.throws(
    () =>
      updateConflictStatus(db, r.id, {
        status: "resolved_merged",
        resolved_by: "toto",
        resolution_kind: "merged",
      }),
    /merge_target/,
  );
});

test("audit-writer: DELETE on conflict_audit blocked by trigger semantics", () => {
  const db = new FakeDB();
  db.enableConflictAuditTriggers();
  recordConflict(db, fixture());
  assert.throws(
    () => db.prepare("DELETE FROM conflict_audit WHERE id = 1").run(1),
    /append-only|forbidden/i,
  );
});

test("audit-writer: terminal row cannot be reopened", () => {
  const db = new FakeDB();
  db.enableConflictAuditTriggers();
  const r = recordConflict(db, fixture());
  updateConflictStatus(db, r.id, {
    status: "dismissed",
    resolved_by: "toto",
    resolution_kind: "dismissed",
  });
  assert.throws(
    () =>
      updateConflictStatus(db, r.id, {
        // TS forbids 'open' on ResolutionInput at compile; cast to bypass for runtime trigger test.
        status: "reviewed" as never,
        resolved_by: "toto",
        resolution_kind: "dismissed",
      }),
    /reopened|append-only|forbidden/i,
  );
});

test("audit-writer: statusCounts aggregates correctly", () => {
  const db = new FakeDB();
  recordConflict(db, fixture());
  recordConflict(db, fixture({ subject_entity_id: 2 }));
  const r3 = recordConflict(db, fixture({ subject_entity_id: 3 }));
  updateConflictStatus(db, r3.id, {
    status: "dismissed",
    resolved_by: "system",
    resolution_kind: "dismissed",
  });
  const counts = statusCounts(db);
  assert.equal(counts.open, 2);
  assert.equal(counts.dismissed, 1);
  assert.equal(counts.resolved_pick_one, 0);
});
