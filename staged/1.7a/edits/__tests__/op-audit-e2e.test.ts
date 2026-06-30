// E2E test (W2-extra 2026-04-26): _reindexImpl + withOpAudit integration.
// Lição: bug B2 (closeDb mid-function) escapou do audit duplo porque smoke só cobriu
// happy-path standalone. Este test exercita a integração que levou ao bug:
// withOpAudit wrappa fn() que muta DB usando o MESMO singleton — qualquer closeDb
// mid-op invalida o handle de UPDATE final → row stuck running.
//
// Run: cd /root/.openclaw/workspace/tools/nox-mem && npx tsc &&
//      node --test dist/__tests__/op-audit-e2e.test.js
//
// IMPORTANT: este test usa NOX_DB_PATH temp em /var/backups/nox-mem-test/ (allowlist OK).
// Snapshot dir override via NOX_PRE_OP_SNAPSHOT_DIR também em /var/backups/nox-mem-test/.
//
// Issue #3B (2026-05-21): updated to use new 3-argument withOpAudit signature.
// db_source: 'test' for all test ops (filtered from /api/health.opsAudit metrics).

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Database from "better-sqlite3";

const TMP_ROOT = mkdtempSync("/var/backups/nox-mem-test-");
const TEST_DB = join(TMP_ROOT, "test.db");
const TEST_SNAP_DIR = join(TMP_ROOT, "snapshots");

// Set env BEFORE importing op-audit (module-load validation reads NOX_DB_PATH).
process.env.NOX_DB_PATH = TEST_DB;
process.env.NOX_PRE_OP_SNAPSHOT_DIR = TEST_SNAP_DIR;

// Fix 2026-05-01: setupDb não pode pré-criar tabela chunks com schema v1 minimal porque
// conflita com migrations cumulativas (source_date, pain, section, etc adicionados em v3+).
// Em vez disso, deixar ensureSchema (em db.ts.getDb) construir schema v10 completo via NOX_DB_PATH override.
const setupDb = async () => {
  const { getDb, closeDb } = await import("../db.js");
  const db = getDb();
  db.exec(`
    INSERT INTO chunks (source_file, chunk_text, chunk_type, tier, access_count, importance)
    VALUES
      ('memory/test.md', 'sample chunk text 1', 'daily', 'core', 5, 0.8),
      ('memory/test.md', 'sample chunk text 2', 'daily', 'peripheral', 0, 0.5);
  `);
  closeDb();
};

before(async () => {
  await setupDb();
});

after(() => {
  // Cleanup: rmSync recursive remove temp dir + snapshots
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

test("E2E: withOpAudit success path — INSERT row, fn runs, UPDATE final fires", async () => {
  // Reset singleton (db.ts) and lib state via dynamic import after env set
  const opAudit = await import("../lib/op-audit.js");
  const { getDb, closeDb } = await import("../db.js");

  // Issue #3B: explicit db_source: 'test' (op name starts with 'test-' so it's
  // filtered from /api/health.opsAudit; db_source confirms intent at code level).
  const result = await opAudit.withOpAudit("test-success", { db_source: 'test' }, async () => {
    const db = getDb();
    const inserted = db.prepare("INSERT INTO chunks (source_file, chunk_text, chunk_type) VALUES (?, ?, ?)").run("e2e/added.md", "added by e2e", "test");
    return { affected_rows: Number(inserted.changes), notes: "e2e success path" };
  });

  assert.equal(result.affected_rows, 1);

  // Verify ops_audit row was INSERTED then UPDATED to status='success'
  const db = getDb();
  const row = db.prepare("SELECT op_name, status, affected_rows, snapshot_path, snapshot_bytes, schema_user_version, pid, error_message FROM ops_audit WHERE op_name = ?").get("test-success") as Record<string, unknown> | undefined;
  assert.ok(row, "ops_audit row exists");
  assert.equal(row.status, "success", "status should be success");
  assert.equal(row.affected_rows, 1);
  assert.ok(row.snapshot_path && typeof row.snapshot_path === "string" && (row.snapshot_path as string).length > 0, "snapshot_path populated");
  assert.ok(typeof row.snapshot_bytes === "number" && (row.snapshot_bytes as number) > 0, "snapshot_bytes populated");
  assert.equal(row.error_message, null, "no error on success path");

  // Verify snapshot file actually exists on disk
  assert.ok(existsSync(row.snapshot_path as string), "snapshot file on disk");

  closeDb();
});

test("E2E: withOpAudit failure path — row marked failed, snapshot preserved", async () => {
  const opAudit = await import("../lib/op-audit.js");
  const { getDb, closeDb } = await import("../db.js");

  await assert.rejects(
    opAudit.withOpAudit("test-failure", { db_source: 'test' }, async () => {
      throw new Error("intentional e2e failure");
    }),
    /intentional e2e failure/,
    "withOpAudit propagates fn error"
  );

  const db = getDb();
  const row = db.prepare("SELECT status, error_message, snapshot_path FROM ops_audit WHERE op_name = ?").get("test-failure") as Record<string, unknown> | undefined;
  assert.ok(row, "failure row exists");
  assert.equal(row.status, "failed");
  assert.match(row.error_message as string, /intentional e2e failure/);
  assert.ok(existsSync(row.snapshot_path as string), "snapshot preserved on failure (recovery path)");

  closeDb();
});

test("E2E REGRESSION GUARD (B2): closeDb mid-op throws, fail-loud not silent", async () => {
  // This test catches the B2 bug class: if anyone adds closeDb() inside an op wrapped by
  // withOpAudit, the final UPDATE on ops_audit must FAIL LOUD (throw), not silently leave
  // the row stuck in 'running' state. Fix B2 (2026-04-26) removed mid-op closeDb from
  // _reindexImpl; this test ensures the wrapper itself reacts correctly if a future caller
  // re-introduces the anti-pattern.
  const opAudit = await import("../lib/op-audit.js");
  const { getDb, closeDb } = await import("../db.js");

  // Simulate the B2 anti-pattern: fn() calls closeDb() mid-op. The expected behavior is
  // that withOpAudit's UPDATE final throws (DB closed) — propagating loudly.
  await assert.rejects(
    opAudit.withOpAudit("test-b2-regression", { db_source: 'test' }, async () => {
      const db = getDb();
      db.prepare("INSERT INTO chunks (source_file, chunk_text, chunk_type) VALUES (?, ?, ?)").run("b2/test.md", "before close", "test");
      closeDb();  // anti-pattern
      return { affected_rows: 1, notes: "b2 anti-pattern" };
    }),
    /database connection is not open|closed/i,
    "withOpAudit must surface the closed-DB error, not silently leave row in 'running'"
  );

  closeDb();
});

test("E2E: opFn returning undefined throws (W2-11 validation)", async () => {
  const opAudit = await import("../lib/op-audit.js");
  const { closeDb } = await import("../db.js");

  await assert.rejects(
    // @ts-expect-error testing runtime check intentionally
    opAudit.withOpAudit("test-bad-fn", { db_source: 'test' }, async () => undefined),
    /opFn must return OpResult object/,
    "type validation throws"
  );
  closeDb();
});
