import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const MIGRATION_PATH = resolve(__dirname, "../../../../../edits/migrations/v21-conflict-audit.sql");
const ROLLBACK_PATH = resolve(__dirname, "../../../../../edits/migrations/v21-rollback.sql");

test("migration: v21 file exists in expected location", () => {
  assert.ok(existsSync(MIGRATION_PATH), `Expected migration at ${MIGRATION_PATH}`);
});

test("migration: v21 bumps user_version to 21 (and ONLY 21)", () => {
  const sql = readFileSync(MIGRATION_PATH, "utf8");
  const matches = sql.match(/PRAGMA\s+user_version\s*=\s*(\d+)/gi) ?? [];
  assert.equal(matches.length, 1, "must set user_version exactly once");
  assert.match(matches[0]!, /=\s*21\b/, "must target version 21");
});

test("migration: v21 idempotent — CREATE TABLE/INDEX/TRIGGER guarded by IF NOT EXISTS", () => {
  const sql = readFileSync(MIGRATION_PATH, "utf8");
  // Every CREATE statement must use IF NOT EXISTS so re-application is safe.
  const creates = sql.match(/CREATE\s+(TABLE|INDEX|TRIGGER)\s+(IF NOT EXISTS\s+)?\w+/gi) ?? [];
  assert.ok(creates.length >= 6, `expected ≥6 CREATE statements (1 table + 3 indexes + 3 triggers), got ${creates.length}`);
  for (const c of creates) {
    assert.match(c, /IF NOT EXISTS/i, `non-idempotent CREATE detected: ${c}`);
  }
});

test("migration: conflict_audit append-only via DELETE/UPDATE triggers", () => {
  const sql = readFileSync(MIGRATION_PATH, "utf8");
  assert.match(sql, /trg_conflict_audit_no_delete/, "DELETE trigger missing");
  assert.match(sql, /trg_conflict_audit_immutable_data/, "immutability trigger missing");
  assert.match(sql, /trg_conflict_audit_no_reopen/, "no-reopen trigger missing");
  assert.match(sql, /BEFORE DELETE ON conflict_audit/i);
  assert.match(sql, /BEFORE UPDATE OF kind, subject_entity_id, predicate, target_relation_ids, variants, ts/i);
});

test("migration: rollback reverts user_version to 19 and drops all v21 objects", () => {
  assert.ok(existsSync(ROLLBACK_PATH), `Expected rollback at ${ROLLBACK_PATH}`);
  const sql = readFileSync(ROLLBACK_PATH, "utf8");
  assert.match(sql, /DROP TABLE IF EXISTS conflict_audit/);
  assert.match(sql, /DROP TRIGGER IF EXISTS trg_conflict_audit_no_delete/);
  assert.match(sql, /DROP TRIGGER IF EXISTS trg_conflict_audit_immutable_data/);
  assert.match(sql, /DROP TRIGGER IF EXISTS trg_conflict_audit_no_reopen/);
  assert.match(sql, /PRAGMA\s+user_version\s*=\s*19/);
});
