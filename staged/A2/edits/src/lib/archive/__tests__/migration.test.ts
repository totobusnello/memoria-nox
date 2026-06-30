/**
 * T9 — schema migration tests.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  canImport,
  listMigrations,
  migrateChunks,
  migrationPath,
} from "../migration.js";
import { ChunkRow, SchemaVersionError } from "../types.js";

function sampleChunks(): ChunkRow[] {
  return [
    {
      id: 1,
      content: "x",
      content_hash: "a".repeat(64),
      source_path: null,
      source_kind: null,
      project: null,
      created_at: "2026-05-18T00:00:00Z",
      updated_at: null,
      retention_days: null,
      pain: 0.2,
      section: null,
      section_boost: null,
      metadata_json: null,
    },
  ];
}

describe("migration / canImport", () => {
  it("same-version is a no-op (ok)", () => {
    assert.deepEqual(canImport(18, 18), { ok: true });
  });

  it("forward v18→v19 is allowed (migration registered)", () => {
    assert.deepEqual(canImport(18, 19), { ok: true });
  });

  it("backward v19→v18 fails clearly with actionable message", () => {
    const r = canImport(19, 18);
    assert.equal(r.ok, false);
    if (r.ok === false) {
      assert.match(r.reason, /newer than current/);
      assert.match(r.reason, /Upgrade nox-mem/);
    }
  });

  it("forward with no chain registered fails", () => {
    const r = canImport(18, 25);
    assert.equal(r.ok, false);
    if (r.ok === false) {
      assert.match(r.reason, /No migration registered/);
    }
  });

  it("rejects bogus version numbers", () => {
    assert.equal(canImport(0, 18).ok, false);
    assert.equal(canImport(18, -1).ok, false);
    assert.equal(canImport(1.5, 2).ok, false);
  });
});

describe("migration / migrationPath", () => {
  it("returns [] for same version", () => {
    assert.deepEqual(migrationPath(18, 18), []);
  });

  it("returns ordered list of step ids", () => {
    const path = migrationPath(18, 19);
    assert.equal(path.length, 1);
    assert.match(path[0]!, /v18_to_v19/);
  });

  it("throws SchemaVersionError on backward", () => {
    assert.throws(() => migrationPath(19, 18), SchemaVersionError);
  });
});

describe("migration / migrateChunks chain", () => {
  it("applies v18→v19 transform (identity placeholder, count stable)", () => {
    const before = sampleChunks();
    const after = migrateChunks(before, 18, 19);
    assert.equal(after.length, before.length);
    assert.equal(after[0]!.content_hash, before[0]!.content_hash);
  });

  it("same-version returns input rows unchanged", () => {
    const rows = sampleChunks();
    const out = migrateChunks(rows, 18, 18);
    assert.equal(out.length, rows.length);
  });

  it("backward attempt throws SchemaVersionError", () => {
    assert.throws(
      () => migrateChunks(sampleChunks(), 19, 18),
      SchemaVersionError,
    );
  });
});

describe("migration / registry", () => {
  it("lists at least the v18→v19 placeholder", () => {
    const list = listMigrations();
    assert.ok(list.some((m) => m.from === 18 && m.to === 19));
  });
});
