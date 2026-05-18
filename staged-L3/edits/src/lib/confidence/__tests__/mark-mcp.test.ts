/**
 * T6 — MCP mark tools tests (5 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { MockDb } from "../db-shim.js";
import {
  listMarkTools,
  callChunkMark,
  callChunkSupersede,
} from "../../../mcp/tools/mark.js";

test("T6.1 listMarkTools exposes 2 tools", () => {
  const tools = listMarkTools();
  assert.equal(tools.length, 2);
  const names = tools.map((t) => t.name).sort();
  assert.deepEqual(names, ["chunk_mark", "chunk_supersede"]);
});

test("T6.2 chunk_mark inputSchema requires id + kind", () => {
  const tool = listMarkTools().find((t) => t.name === "chunk_mark");
  assert.ok(tool);
  assert.deepEqual(tool!.inputSchema.required.sort(), ["id", "kind"]);
});

test("T6.3 chunk_supersede inputSchema requires id + by_id", () => {
  const tool = listMarkTools().find((t) => t.name === "chunk_supersede");
  assert.ok(tool);
  assert.deepEqual(tool!.inputSchema.required.sort(), ["by_id", "id"]);
});

test("T6.4 callChunkMark with refuted returns refuted confidence", () => {
  const db = new MockDb();
  db.seedChunk({ id: 11, confidence: 0.8 });
  const r = callChunkMark(db, { id: 11, kind: "refuted" });
  assert.equal(r.applied.confidence, 0.05);
  assert.equal(r.applied.provenance_kind, "user-marked");
});

test("T6.5 callChunkSupersede sets superseded_by", () => {
  const db = new MockDb();
  db.seedChunk({ id: 1, confidence: 0.5 });
  db.seedChunk({ id: 2, confidence: 0.9 });
  const r = callChunkSupersede(db, { id: 1, by_id: 2 });
  assert.equal(r.applied.superseded_by, 2);
});
