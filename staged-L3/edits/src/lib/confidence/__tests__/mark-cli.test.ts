/**
 * T4 — CLI mark tests (10 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { MockDb } from "../db-shim.js";
import {
  parseMarkArgs,
  runMark,
  markCommand,
  CliError,
} from "../../../cli/mark.js";

test("T4.1 parse --canonical", () => {
  const parsed = parseMarkArgs(["42", "--canonical"]);
  assert.equal(parsed.chunk_id, 42);
  assert.equal(parsed.kind, "canonical");
});

test("T4.2 parse --refuted with --notes", () => {
  const parsed = parseMarkArgs(["7", "--refuted", "--notes", "stale info"]);
  assert.equal(parsed.kind, "refuted");
  assert.equal(parsed.notes, "stale info");
});

test("T4.3 parse --stale", () => {
  const parsed = parseMarkArgs(["3", "--stale"]);
  assert.equal(parsed.kind, "stale");
});

test("T4.4 parse --supersede-by", () => {
  const parsed = parseMarkArgs(["1", "--supersede-by", "99"]);
  assert.equal(parsed.supersede_by, 99);
});

test("T4.5 parse rejects invalid chunk_id", () => {
  assert.throws(() => parseMarkArgs(["abc", "--canonical"]), CliError);
});

test("T4.6 parse rejects empty argv", () => {
  assert.throws(() => parseMarkArgs([]), CliError);
});

test("T4.7 parse rejects when no kind nor supersede given", () => {
  assert.throws(() => parseMarkArgs(["42"]), CliError);
});

test("T4.8 runMark canonical updates DB + emits audit row", () => {
  const db = new MockDb();
  db.seedChunk({ id: 5, confidence: 0.8, provenance_kind: null });
  const result = runMark(db, { chunk_id: 5, kind: "canonical" });
  assert.equal(result.applied.confidence, 1.0);
  assert.equal(result.applied.provenance_kind, "user-marked");
  assert.equal(db.audit.length, 1);
  assert.equal(db.audit[0]?.op, "confidence-mark-canonical");
  assert.equal(db.audit[0]?.status, "success");
});

test("T4.9 runMark missing chunk emits failed audit + throws", () => {
  const db = new MockDb();
  assert.throws(() =>
    runMark(db, { chunk_id: 9999, kind: "refuted" })
  );
  assert.equal(db.audit.length, 1);
  assert.equal(db.audit[0]?.status, "failed");
});

test("T4.10 markCommand returns JSON, supports supersede + canonical combo", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.6 });
  db.seedChunk({ id: 2, confidence: 0.9 });
  const out = markCommand(db, ["1", "--canonical", "--supersede-by", "2"]);
  const parsed = JSON.parse(out);
  assert.equal(parsed.ok, true);
  // canonical applied after supersede
  assert.equal(parsed.applied.confidence, 1.0);
});
