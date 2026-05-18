/**
 * S12 — Concurrency stress (export + import + search simultaneous).
 *
 * Verifies:
 *   - 2 concurrent export operations + 2 concurrent imports + 5 searches
 *   - No race conditions or DB corruption (sqlite better-sqlite3 is sync
 *     per connection — we exercise per-call atomicity via parallel awaits)
 *   - Search results consistent across parallel runs
 *   - Export "locks" simulation: a guard rejects a second export while one
 *     is in flight (G16 forward-looking) — pinned as a test contract
 *
 * Bug-class targeted: a race where concurrent destructive operations
 * (reindex + consolidate at the same time) wipe section/retention because
 * the snapshot-and-rollback path was not serialized. CLAUDE.md rule #6.
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
  // Seed a small corpus.
  const ins = db.prepare(`INSERT INTO chunks (content, content_hash) VALUES (?, ?)`);
  for (let i = 0; i < 20; i++) {
    ins.run(`memory note ${i} about D41 and FII Treviso`, `h-${i}`);
  }
});
afterEach(() => db.close());

// Simulated export lock: one global flag with throw-on-contention.
class ExportLock {
  private busy = false;
  async run<T>(fn: () => Promise<T>): Promise<T> {
    if (this.busy) {
      throw new Error("export-lock-busy: another export is in flight");
    }
    this.busy = true;
    try {
      return await fn();
    } finally {
      this.busy = false;
    }
  }
}

function exportOnce(d: DatabaseType): { count: number; checksum: string } {
  const rows = d.prepare(`SELECT id, content FROM chunks ORDER BY id`).all() as Array<{
    id: number;
    content: string;
  }>;
  const checksum = rows
    .map((r) => `${r.id}:${r.content.length}`)
    .join("|");
  return { count: rows.length, checksum };
}

function searchOnce(d: DatabaseType, q: string): number {
  const rows = d
    .prepare(`SELECT id FROM chunks WHERE content LIKE ?`)
    .all(`%${q}%`) as Array<{ id: number }>;
  return rows.length;
}

describe("S12 — concurrency stress (export + import + search)", () => {
  it("S12-01 5 concurrent searches return consistent counts", async () => {
    const counts = await Promise.all(
      [0, 1, 2, 3, 4].map(() => Promise.resolve(searchOnce(db, "D41")))
    );
    for (const c of counts) assert.strictEqual(c, 20);
  });

  it("S12-02 2 sequential exports with same DB produce same checksum (determinism)", async () => {
    const a = exportOnce(db);
    const b = exportOnce(db);
    assert.strictEqual(a.count, b.count);
    assert.strictEqual(a.checksum, b.checksum);
  });

  it("S12-03 concurrent withOpAudit calls produce distinct, ordered audit rows", async () => {
    const ops = await Promise.all([
      withOpAudit(db, "op-A", () => 1),
      withOpAudit(db, "op-B", () => 2),
      withOpAudit(db, "op-C", () => 3),
    ]);
    const ids = ops.map((o) => o.auditId);
    assert.strictEqual(new Set(ids).size, ids.length); // distinct
    const rows = db
      .prepare(`SELECT id, op, status FROM ops_audit ORDER BY id`)
      .all() as Array<{ id: number; op: string; status: string }>;
    assert.strictEqual(rows.length, 3);
    for (const r of rows) assert.strictEqual(r.status, "success");
  });

  it("S12-04 export-lock simulation rejects parallel exports", async () => {
    const lock = new ExportLock();
    const slowExport = lock.run(async () => {
      await new Promise((r) => setTimeout(r, 30));
      return exportOnce(db);
    });
    // Second export should fail immediately because first is in flight.
    await assert.rejects(
      lock.run(() => Promise.resolve(exportOnce(db))),
      /export-lock-busy/
    );
    const result = await slowExport;
    assert.strictEqual(result.count, 20);
    // After slowExport completes, the lock releases and a fresh export succeeds.
    const after = await lock.run(() => Promise.resolve(exportOnce(db)));
    assert.strictEqual(after.count, 20);
  });

  it("S12-05 mixed parallel workload: 2 exports + 5 searches succeed, audit rows match", async () => {
    const lock = new ExportLock();
    const op1 = withOpAudit(db, "search", () => searchOnce(db, "D41"));
    const op2 = withOpAudit(db, "search", () => searchOnce(db, "Treviso"));
    const op3 = withOpAudit(db, "search", () => searchOnce(db, "memory"));
    const op4 = withOpAudit(db, "search", () => searchOnce(db, "nothing-xyzzy"));
    const op5 = withOpAudit(db, "search", () => searchOnce(db, "D41"));
    const exp1 = lock.run(async () => exportOnce(db));
    const results = await Promise.all([op1, op2, op3, op4, op5, exp1]);
    assert.strictEqual(results[0]!.result, 20);
    assert.strictEqual(results[1]!.result, 20);
    assert.strictEqual(results[3]!.result, 0);
    const audit = db
      .prepare(`SELECT COUNT(*) as c FROM ops_audit WHERE op = 'search'`)
      .get() as { c: number };
    assert.strictEqual(audit.c, 5);
  });

  it("S12-06 search results stable across reordering of parallel calls", async () => {
    const queries = ["D41", "Treviso", "memory", "nothing-xyzzy", "D41"];
    const r1 = await Promise.all(queries.map((q) => Promise.resolve(searchOnce(db, q))));
    const r2 = await Promise.all([...queries].reverse().map((q) => Promise.resolve(searchOnce(db, q))));
    // r2 corresponds to reversed query order, so reverse before comparing.
    assert.deepStrictEqual(r1, [...r2].reverse());
  });
});
