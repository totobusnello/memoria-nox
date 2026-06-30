import { test } from "node:test";
import assert from "node:assert/strict";
import {
  resolveMode,
  runConflictPass,
  annotateRelations,
  getShadowTelemetry,
  getConflictsForRelations,
  _resetLastScanForTests,
} from "../shadow.js";
import { FakeDB, seedEntity, seedRelation } from "./fakes.js";

function seedConflict(db: FakeDB): void {
  seedEntity(db, 1, "toto");
  seedEntity(db, 100, "opus");
  seedEntity(db, 101, "sonnet");
  seedRelation(db, { id: 10, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 11, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
}

test("shadow: resolveMode default is 'disabled'", () => {
  delete process.env.NOX_CONFLICT_MODE;
  assert.equal(resolveMode(), "disabled");
});

test("shadow: resolveMode reads env", () => {
  process.env.NOX_CONFLICT_MODE = "shadow";
  assert.equal(resolveMode(), "shadow");
  process.env.NOX_CONFLICT_MODE = "active";
  assert.equal(resolveMode(), "active");
  delete process.env.NOX_CONFLICT_MODE;
});

test("shadow: unknown env value falls back to 'disabled' (safe default)", () => {
  process.env.NOX_CONFLICT_MODE = "yolo";
  assert.equal(resolveMode(), "disabled");
  delete process.env.NOX_CONFLICT_MODE;
});

test("shadow: 'disabled' mode performs no writes", () => {
  const db = new FakeDB();
  seedConflict(db);
  _resetLastScanForTests();
  const result = runConflictPass(db, {}, "disabled");
  assert.equal(result.detected, 0);
  assert.equal(result.recorded, 0);
  assert.equal(db.table("conflict_audit").rows.length, 0);
});

test("shadow: 'shadow' mode records rows with shadow_mode=1", () => {
  const db = new FakeDB();
  seedConflict(db);
  const result = runConflictPass(db, {}, "shadow");
  assert.equal(result.mode, "shadow");
  assert.equal(result.detected, 1);
  assert.equal(result.recorded, 1);
  assert.equal(db.table("conflict_audit").rows.length, 1);
  assert.equal(db.table("conflict_audit").rows[0]!.shadow_mode, 1);
});

test("shadow: 'active' mode records rows with shadow_mode=0", () => {
  const db = new FakeDB();
  seedConflict(db);
  const result = runConflictPass(db, {}, "active");
  assert.equal(result.mode, "active");
  assert.equal(db.table("conflict_audit").rows[0]!.shadow_mode, 0);
});

test("shadow: dedupe — second pass produces deduplicated counter", () => {
  const db = new FakeDB();
  seedConflict(db);
  const r1 = runConflictPass(db, {}, "shadow");
  const r2 = runConflictPass(db, {}, "shadow");
  assert.equal(r1.recorded, 1);
  assert.equal(r2.recorded, 0);
  assert.equal(r2.deduplicated, 1);
});

test("shadow: annotateRelations returns empty Set in shadow mode", () => {
  const db = new FakeDB();
  seedConflict(db);
  runConflictPass(db, {}, "shadow");
  const flagged = annotateRelations(db, [10, 11, 99], "shadow");
  assert.equal(flagged.size, 0);
});

test("shadow: annotateRelations flags ids on open conflicts in active mode", () => {
  const db = new FakeDB();
  seedConflict(db);
  runConflictPass(db, {}, "active");
  const flagged = annotateRelations(db, [10, 11, 99], "active");
  assert.ok(flagged.has(10));
  assert.ok(flagged.has(11));
  assert.ok(!flagged.has(99));
});

test("shadow: telemetry surface includes mode + counts + scan ts", () => {
  const db = new FakeDB();
  seedConflict(db);
  runConflictPass(db, {}, "shadow");
  const t = getShadowTelemetry(db, "shadow");
  assert.equal(t.mode, "shadow");
  assert.equal(t.counts.open, 1);
  assert.ok(t.last_scan_at != null);
});

test("shadow: getConflictsForRelations returns rich payload", () => {
  const db = new FakeDB();
  seedConflict(db);
  runConflictPass(db, {}, "shadow");
  const matched = getConflictsForRelations(db, [10]);
  assert.equal(matched.length, 1);
  assert.equal(matched[0]!.predicate, "uses_model");
  assert.equal(matched[0]!.variants.length, 2);
});
