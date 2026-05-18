import { test } from "node:test";
import assert from "node:assert/strict";
import { dispatchConflictApi } from "../conflict.js";
import { FakeDB } from "../../lib/conflict/__tests__/fakes.js";
import { recordConflict } from "../../lib/conflict/audit-writer.js";
import type { Conflict } from "../../lib/conflict/types.js";

function fixture(overrides: Partial<Conflict> = {}): Conflict {
  return {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "p",
    variants: [
      { relation_id: 10, target_entity_id: 100, confidence: 0.9, created_at: 1 },
      { relation_id: 11, target_entity_id: 101, confidence: 0.85, created_at: 2 },
    ],
    ...overrides,
  };
}

test("api: unknown path returns 404", () => {
  const db = new FakeDB();
  const r = dispatchConflictApi(db, { method: "GET", path: "/api/unrelated" });
  assert.equal(r.status, 404);
});

test("api: GET /api/conflict returns count + rows", () => {
  const db = new FakeDB();
  recordConflict(db, fixture());
  const r = dispatchConflictApi(db, {
    method: "GET",
    path: "/api/conflict",
    query: { status: "open" },
  });
  assert.equal(r.status, 200);
  const body = r.body as { count: number; rows: unknown[] };
  assert.equal(body.count, 1);
  assert.equal(body.rows.length, 1);
});

test("api: GET /api/conflict invalid status → 400", () => {
  const db = new FakeDB();
  const r = dispatchConflictApi(db, {
    method: "GET",
    path: "/api/conflict",
    query: { status: "weird" },
  });
  assert.equal(r.status, 400);
});

test("api: GET /api/conflict invalid limit → 400", () => {
  const db = new FakeDB();
  const r = dispatchConflictApi(db, {
    method: "GET",
    path: "/api/conflict",
    query: { limit: "-1" },
  });
  assert.equal(r.status, 400);
});

test("api: GET /api/conflict/:id returns row + evidence", () => {
  const db = new FakeDB();
  const ins = recordConflict(db, fixture());
  const r = dispatchConflictApi(db, {
    method: "GET",
    path: `/api/conflict/${ins.id}`,
  });
  assert.equal(r.status, 200);
  const body = r.body as { row: { id: number }; evidence: unknown };
  assert.equal(body.row.id, ins.id);
  assert.ok(body.evidence);
});

test("api: GET /api/conflict/:id nonexistent → 404", () => {
  const db = new FakeDB();
  const r = dispatchConflictApi(db, {
    method: "GET",
    path: "/api/conflict/999",
  });
  assert.equal(r.status, 404);
});

test("api: POST resolve pick_one without picked_relation_id → 400", () => {
  const db = new FakeDB();
  const ins = recordConflict(db, fixture());
  const r = dispatchConflictApi(db, {
    method: "POST",
    path: `/api/conflict/${ins.id}/resolve`,
    body: { kind: "pick_one" },
  });
  assert.equal(r.status, 400);
});

test("api: POST resolve happy-path returns updated row", () => {
  const db = new FakeDB();
  const ins = recordConflict(db, fixture());
  const r = dispatchConflictApi(db, {
    method: "POST",
    path: `/api/conflict/${ins.id}/resolve`,
    body: { kind: "pick_one", picked_relation_id: 10, notes: "opus canonical" },
    actor: "toto",
  });
  assert.equal(r.status, 200);
  const body = r.body as { row: { status: string; resolved_by: string } };
  assert.equal(body.row.status, "resolved_pick_one");
  assert.equal(body.row.resolved_by, "toto");
});
