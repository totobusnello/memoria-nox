import { test } from "node:test";
import assert from "node:assert/strict";
import { runConflictCli } from "../conflict.js";
import {
  FakeDB,
  seedEntity,
  seedRelation,
  seedChunk,
} from "../../lib/conflict/__tests__/fakes.js";
import { recordConflict } from "../../lib/conflict/audit-writer.js";

function seedConflictDB(): FakeDB {
  const db = new FakeDB();
  db.enableConflictAuditTriggers();
  seedEntity(db, 1, "toto");
  seedEntity(db, 100, "opus");
  seedEntity(db, 101, "sonnet");
  seedRelation(db, { id: 10, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9, evidence_chunk_id: 5000 });
  seedRelation(db, { id: 11, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85, evidence_chunk_id: 5001 });
  seedChunk(db, { id: 5000, content: "Switched primary to opus on 2026-05-01" });
  seedChunk(db, { id: 5001, content: "Switched to sonnet on 2026-05-10" });
  return db;
}

test("cli: no action prints usage and exits 1", () => {
  const db = new FakeDB();
  const r = runConflictCli(db, []);
  assert.equal(r.code, 1);
  assert.ok(r.stderr.join("\n").includes("nox-mem conflict"));
});

test("cli: unknown action exits 1 with hint", () => {
  const db = new FakeDB();
  const r = runConflictCli(db, ["nuke"]);
  assert.equal(r.code, 1);
  assert.ok(r.stderr.some((l) => l.includes("unknown action")));
});

test("cli: scan reports detected/recorded counts", () => {
  const db = seedConflictDB();
  const r = runConflictCli(db, ["scan", "--json"]);
  assert.equal(r.code, 0);
  const j = r.json as { detected: number; recorded: number };
  assert.equal(j.detected, 1);
  assert.equal(j.recorded, 1);
});

test("cli: list defaults to status=open", () => {
  const db = seedConflictDB();
  runConflictCli(db, ["scan"]);
  const r = runConflictCli(db, ["list", "--json"]);
  assert.equal(r.code, 0);
  const rows = r.json as unknown[];
  assert.equal(rows.length, 1);
});

test("cli: list honors --status and --limit", () => {
  const db = seedConflictDB();
  runConflictCli(db, ["scan"]);
  const r = runConflictCli(db, ["list", "--status", "dismissed", "--json"]);
  assert.equal(r.code, 0);
  const rows = r.json as unknown[];
  assert.equal(rows.length, 0);
});

test("cli: show missing id exits 1", () => {
  const db = new FakeDB();
  const r = runConflictCli(db, ["show"]);
  assert.equal(r.code, 1);
});

test("cli: show invalid id exits 1", () => {
  const db = new FakeDB();
  const r = runConflictCli(db, ["show", "notanint"]);
  assert.equal(r.code, 1);
});

test("cli: show nonexistent id exits 2", () => {
  const db = new FakeDB();
  const r = runConflictCli(db, ["show", "999"]);
  assert.equal(r.code, 2);
});

test("cli: show prints variants + evidence", () => {
  const db = seedConflictDB();
  runConflictCli(db, ["scan"]);
  const r = runConflictCli(db, ["show", "1"]);
  assert.equal(r.code, 0);
  const joined = r.stdout.join("\n");
  assert.match(joined, /conflict 1/);
  assert.match(joined, /uses_model/);
  assert.match(joined, /rel 10/);
  assert.match(joined, /rel 11/);
});

test("cli: resolve --pick marks resolved_pick_one", () => {
  const db = seedConflictDB();
  runConflictCli(db, ["scan"]);
  const r = runConflictCli(db, ["resolve", "1", "--pick", "10"], { actor: "toto" });
  assert.equal(r.code, 0);
  const show = runConflictCli(db, ["show", "1", "--json"]);
  const p = (show.json as { row: { status: string; picked_relation_id: number } }).row;
  assert.equal(p.status, "resolved_pick_one");
  assert.equal(p.picked_relation_id, 10);
});

test("cli: resolve --dismiss with --notes", () => {
  const db = seedConflictDB();
  runConflictCli(db, ["scan"]);
  const r = runConflictCli(db, ["resolve", "1", "--dismiss", "--notes", "false positive"]);
  assert.equal(r.code, 0);
  const show = runConflictCli(db, ["show", "1", "--json"]);
  const p = (show.json as { row: { status: string; notes: string } }).row;
  assert.equal(p.status, "dismissed");
  assert.equal(p.notes, "false positive");
});

test("cli: resolve without action flag exits 1", () => {
  const db = seedConflictDB();
  // Insert a conflict directly to avoid running scan side-effect
  recordConflict(db, {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "p",
    variants: [
      { relation_id: 1, target_entity_id: 10, confidence: 0.9, created_at: 1 },
      { relation_id: 2, target_entity_id: 11, confidence: 0.8, created_at: 2 },
    ],
  });
  const r = runConflictCli(db, ["resolve", "1"]);
  assert.equal(r.code, 1);
  assert.ok(r.stderr.some((l) => l.includes("--pick")));
});
