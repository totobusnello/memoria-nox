/**
 * S9 — Audit trail integrity (op-audit + conflict_audit + ops_audit).
 *
 * Verifies:
 *   - withOpAudit() writes 'started' → 'success' rows
 *   - Failed op writes 'started' → 'failed' (terminal)
 *   - ops_audit DELETE is blocked by trigger (CWE-693)
 *   - ops_audit UPDATE OF status on terminal rows is blocked
 *   - conflict_audit DELETE is blocked by trigger
 *   - conflict resolution writes status='resolved_pick_one' atomically
 *
 * Bug-class targeted: a regression in op-audit lifecycle where a crash
 * mid-op leaves a row in 'started' forever (silent failure), or where
 * the append-only invariant is broken by some "cleanup" script.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import { withOpAudit } from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);
});
afterEach(() => db.close());

describe("S9 — audit integrity (ops_audit + conflict_audit)", () => {
  it("S9-01 withOpAudit success writes started → success rows", async () => {
    const { auditId } = await withOpAudit(db, "reindex", () => 42);
    const row = db
      .prepare(`SELECT op, status FROM ops_audit WHERE id = ?`)
      .get(auditId) as { op: string; status: string };
    assert.strictEqual(row.op, "reindex");
    assert.strictEqual(row.status, "success");
  });

  it("S9-02 withOpAudit failure writes status='failed' (terminal)", async () => {
    let id = -1;
    await assert.rejects(
      withOpAudit(db, "consolidate", () => {
        throw new Error("simulated failure");
      }),
      /simulated failure/
    );
    // Latest row should be 'failed'.
    const row = db
      .prepare(`SELECT id, op, status FROM ops_audit ORDER BY id DESC LIMIT 1`)
      .get() as { id: number; op: string; status: string };
    id = row.id;
    assert.strictEqual(row.op, "consolidate");
    assert.strictEqual(row.status, "failed");
    void id;
  });

  it("S9-03 DELETE FROM ops_audit is blocked by trigger", async () => {
    await withOpAudit(db, "reindex", () => 1);
    assert.throws(() => db.prepare(`DELETE FROM ops_audit`).run(), /append-only/i);
    assert.throws(
      () => db.prepare(`DELETE FROM ops_audit WHERE id = 1`).run(),
      /append-only/i
    );
  });

  it("S9-04 UPDATE OF status on terminal ops_audit row is blocked", async () => {
    const { auditId } = await withOpAudit(db, "reindex", () => 1);
    // After success, status is 'success' (terminal). Attempt to flip back must fail.
    assert.throws(
      () =>
        db
          .prepare(`UPDATE ops_audit SET status = 'started' WHERE id = ?`)
          .run(auditId),
      /terminal rows are immutable/i
    );
  });

  it("S9-05 ops_audit started → success transition allowed (via wrapper)", async () => {
    // Insert a 'started' row manually (mirrors what withOpAudit does internally).
    const ins = db
      .prepare(
        `INSERT INTO ops_audit (op, status, metadata_json) VALUES ('manual', 'started', '{}')`
      )
      .run();
    const id = Number(ins.lastInsertRowid);
    // Allowed: started → success.
    db.prepare(
      `UPDATE ops_audit SET status = 'success', completed_at = datetime('now') WHERE id = ?`
    ).run(id);
    const row = db.prepare(`SELECT status FROM ops_audit WHERE id = ?`).get(id) as {
      status: string;
    };
    assert.strictEqual(row.status, "success");
  });

  it("S9-06 DELETE FROM conflict_audit is blocked by trigger", () => {
    db.prepare(
      `INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES ('direct', 1, 'p', '[1,2]')`
    ).run();
    assert.throws(() => db.prepare(`DELETE FROM conflict_audit`).run(), /append-only/i);
  });

  it("S9-07 conflict resolution writes terminal status atomically", () => {
    db.prepare(
      `INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids) VALUES ('direct', 1, 'p', '[1,2]')`
    ).run();
    db.prepare(
      `UPDATE conflict_audit SET status = 'resolved_pick_one', resolved_by = ?, resolved_at = ?, resolution_kind = 'pick_one', picked_relation_id = ? WHERE id = 1`
    ).run("toto", Date.now(), 1);
    const row = db
      .prepare(`SELECT status, resolution_kind, picked_relation_id FROM conflict_audit WHERE id = 1`)
      .get() as {
      status: string;
      resolution_kind: string;
      picked_relation_id: number;
    };
    assert.strictEqual(row.status, "resolved_pick_one");
    assert.strictEqual(row.resolution_kind, "pick_one");
    assert.strictEqual(row.picked_relation_id, 1);
  });

  it("S9-08 multiple ops with same name produce distinct audit rows", async () => {
    await withOpAudit(db, "reindex", () => 1);
    await withOpAudit(db, "reindex", () => 2);
    await withOpAudit(db, "reindex", () => 3);
    const rows = db
      .prepare(`SELECT id, status FROM ops_audit WHERE op = 'reindex' ORDER BY id`)
      .all() as Array<{ id: number; status: string }>;
    assert.strictEqual(rows.length, 3);
    for (const r of rows) assert.strictEqual(r.status, "success");
    // ids are monotonic.
    assert.ok(rows[0]!.id < rows[1]!.id);
    assert.ok(rows[1]!.id < rows[2]!.id);
  });
});
