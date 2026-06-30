/**
 * T13 — HTTP handler tests for /api/export + /api/import.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { handleExport } from "../export.js";
import { handleImport } from "../import.js";
import { ChunkRow } from "../../lib/archive/types.js";

function makeChunk(id: number): ChunkRow {
  return {
    id,
    content: `c-${id}`,
    content_hash: `h-${id}`,
    source_path: null,
    source_kind: null,
    project: "test",
    created_at: "2026-05-18T00:00:00.000Z",
    updated_at: null,
    retention_days: 90,
    pain: 0.2,
    section: null,
    section_boost: null,
    metadata_json: null,
  };
}

function dbReader(n: number) {
  return async () => ({
    schema_version: 18,
    source_hostname: "http-test",
    source_nox_mem_version: "v3.7",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: 32,
    sqlite_vec_version: null,
    chunks: Array.from({ length: n }, (_, i) => makeChunk(i + 1)),
    embeddings: [],
    kg_entities: [],
    kg_relations: [],
    ops_audit: [],
  });
}

describe("api / handleExport", () => {
  it("returns 400 when no passphrase + not unencrypted", async () => {
    const res = await handleExport({}, { dbReader: dbReader(1) });
    assert.equal(res.status, 400);
  });

  it("returns 200 + gzip body when --unencrypted", async () => {
    const res = await handleExport(
      { unencrypted: true },
      { dbReader: dbReader(2) },
    );
    assert.equal(res.status, 200);
    assert.equal(res.headers["Content-Type"], "application/gzip");
    assert.ok(res.body instanceof Buffer);
    assert.equal(res.headers["X-Archive-Encrypted"], "false");
    assert.equal(res.headers["X-Archive-Chunks"], "2");
  });

  it("returns 200 with encryption header when passphrase given", async () => {
    const res = await handleExport(
      { passphrase: "test-pass" },
      { dbReader: dbReader(1) },
    );
    assert.equal(res.status, 200);
    assert.equal(res.headers["X-Archive-Encrypted"], "true");
  });

  it("returns 413 when archive exceeds maxBytes", async () => {
    const res = await handleExport(
      { unencrypted: true },
      { dbReader: dbReader(5), maxBytes: 10 },
    );
    assert.equal(res.status, 413);
  });

  it("returns 499 when signal already aborted", async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    const res = await handleExport(
      { unencrypted: true },
      { dbReader: dbReader(2), signal: ctrl.signal },
    );
    assert.equal(res.status, 499);
  });
});

describe("api / handleImport", () => {
  it("returns 400 when archive_b64 missing", async () => {
    const res = await handleImport(
      {},
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
      },
    );
    assert.equal(res.status, 400);
  });

  it("round-trips through handleExport → handleImport (unencrypted)", async () => {
    const exp = await handleExport(
      { unencrypted: true },
      { dbReader: dbReader(3) },
    );
    assert.equal(exp.status, 200);
    const archive = exp.body as Buffer;
    const imp = await handleImport(
      { archive_b64: archive.toString("base64") },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
      },
    );
    assert.equal(imp.status, 200);
    const summary = JSON.parse(imp.body as string);
    assert.equal(summary.stats.chunks.inserted, 3);
    assert.equal(summary.encrypted, false);
  });

  it("round-trips encrypted with correct passphrase", async () => {
    const exp = await handleExport(
      { passphrase: "http-pass" },
      { dbReader: dbReader(2) },
    );
    const archive = exp.body as Buffer;
    const imp = await handleImport(
      {
        archive_b64: archive.toString("base64"),
        passphrase: "http-pass",
      },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
      },
    );
    assert.equal(imp.status, 200);
  });

  it("returns 401 on bad passphrase", async () => {
    const exp = await handleExport(
      { passphrase: "right-pass" },
      { dbReader: dbReader(1) },
    );
    const archive = exp.body as Buffer;
    const imp = await handleImport(
      {
        archive_b64: archive.toString("base64"),
        passphrase: "wrong-pass",
      },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
      },
    );
    assert.equal(imp.status, 401);
  });

  it("returns 401 when encrypted but no passphrase given", async () => {
    const exp = await handleExport(
      { passphrase: "x" },
      { dbReader: dbReader(1) },
    );
    const archive = exp.body as Buffer;
    const imp = await handleImport(
      { archive_b64: archive.toString("base64") },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
      },
    );
    assert.equal(imp.status, 401);
  });

  it("dry_run does not call persist", async () => {
    let persisted = false;
    const exp = await handleExport(
      { unencrypted: true },
      { dbReader: dbReader(1) },
    );
    await handleImport(
      {
        archive_b64: (exp.body as Buffer).toString("base64"),
        dry_run: true,
      },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        persist: async () => {
          persisted = true;
        },
      },
    );
    assert.equal(persisted, false);
  });
});
