/**
 * T5 — HTTP mark API tests (8 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { MockDb } from "../db-shim.js";
import {
  handleMarkRequest,
  handleSupersedeRequest,
} from "../../../api/mark.js";

test("T5.1 mark: 200 on valid canonical request", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.8 });
  const r = handleMarkRequest(db, "1", { kind: "canonical" });
  assert.equal(r.status, 200);
  assert.equal((r.body as { ok: true }).ok, true);
});

test("T5.2 mark: 400 on invalid kind", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.8 });
  const r = handleMarkRequest(db, "1", { kind: "nonsense" });
  assert.equal(r.status, 400);
  assert.equal((r.body as { code: string }).code, "bad_kind");
});

test("T5.3 mark: 400 on invalid chunk id", () => {
  const db = new MockDb();
  const r = handleMarkRequest(db, "abc", { kind: "refuted" });
  assert.equal(r.status, 400);
  assert.equal((r.body as { code: string }).code, "bad_id");
});

test("T5.4 mark: 404 on missing chunk", () => {
  const db = new MockDb();
  const r = handleMarkRequest(db, "9999", { kind: "refuted" });
  assert.equal(r.status, 404);
});

test("T5.5 mark: 400 on missing body", () => {
  const db = new MockDb();
  const r = handleMarkRequest(db, "1", null);
  assert.equal(r.status, 400);
  assert.equal((r.body as { code: string }).code, "bad_body");
});

test("T5.6 supersede: 200 on valid request", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.6 });
  db.seedChunk({ id: 2, confidence: 0.9 });
  const r = handleSupersedeRequest(db, "1", { by_chunk_id: 2 });
  assert.equal(r.status, 200);
});

test("T5.7 supersede: 400 on missing by_chunk_id", () => {
  const db = new MockDb();
  const r = handleSupersedeRequest(db, "1", {});
  assert.equal(r.status, 400);
  assert.equal((r.body as { code: string }).code, "bad_by_id");
});

test("T5.8 supersede: reason normalises to manual_resolution when invalid", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.6 });
  db.seedChunk({ id: 2, confidence: 0.9 });
  const r = handleSupersedeRequest(db, "1", {
    by_chunk_id: 2,
    reason: "garbage",
  });
  assert.equal(r.status, 200);
  // audit row contains the normalised reason
  const audit = db.audit[0] as { details: string };
  const details = JSON.parse(audit.details);
  assert.equal(details.reason, "manual_resolution");
});
