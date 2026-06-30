/**
 * T11 — Migration v22 tests (4 tests).
 * Validates SQL string contents — actual SQL execution requires sqlite runtime.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
// from dist/edits/src/lib/confidence/__tests__/ → ../../../../../../edits/migrations
const migrationDir = resolve(here, "../../../../../../edits/migrations");
const v22Path = resolve(migrationDir, "v22-confidence-eval-log.sql");
const rollbackPath = resolve(migrationDir, "v22-rollback.sql");

const v22Sql = readFileSync(v22Path, "utf8");
const rollbackSql = readFileSync(rollbackPath, "utf8");

test("T11.1 v22 creates confidence_eval_log table", () => {
  assert.ok(/CREATE TABLE IF NOT EXISTS confidence_eval_log/i.test(v22Sql));
});

test("T11.2 v22 declares CHECK constraint on variant column", () => {
  assert.ok(/variant IN \('A', 'B', 'C', 'D'\)/i.test(v22Sql));
});

test("T11.3 v22 installs append-only triggers (regra #6)", () => {
  assert.ok(/trg_confidence_eval_log_no_delete/i.test(v22Sql));
  assert.ok(/trg_confidence_eval_log_no_update/i.test(v22Sql));
});

test("T11.4 rollback drops everything", () => {
  assert.ok(/DROP TABLE IF EXISTS confidence_eval_log/i.test(rollbackSql));
  assert.ok(/DROP TRIGGER IF EXISTS trg_confidence_eval_log_no_delete/i.test(rollbackSql));
  assert.ok(/DROP INDEX IF EXISTS idx_confidence_eval_log_run/i.test(rollbackSql));
});
