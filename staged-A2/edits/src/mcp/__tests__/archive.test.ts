/**
 * T14 — MCP tool tests for archive_export + archive_import.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  archiveExportTool,
  archiveImportTool,
  archiveExportToolSchema,
  archiveImportToolSchema,
} from "../tools/archive.js";
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
    source_hostname: "mcp-test",
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

describe("mcp / archive_export tool", () => {
  it("exposes a name + inputSchema", () => {
    assert.equal(archiveExportToolSchema.name, "archive_export");
    assert.equal(archiveExportToolSchema.inputSchema.type, "object");
  });

  it("returns archive_b64 + manifest summary on success (unencrypted)", async () => {
    const result = await archiveExportTool(
      { unencrypted: true },
      { dbReader: dbReader(2) },
    );
    assert.ok(result.success);
    if (result.success) {
      assert.ok(result.archive_b64.length > 0);
      assert.equal(result.encrypted, false);
      assert.equal(result.manifest.counts.chunks, 2);
    }
  });

  it("resolves passphrase from passphrase_env on server", async () => {
    const result = await archiveExportTool(
      { passphrase_env: "MCP_TEST_PASS" },
      { dbReader: dbReader(1), env: { MCP_TEST_PASS: "secret" } },
    );
    assert.ok(result.success);
    if (result.success) assert.equal(result.encrypted, true);
  });

  it("returns MISSING_ENV when passphrase_env missing", async () => {
    const result = await archiveExportTool(
      { passphrase_env: "NOT_SET" },
      { dbReader: dbReader(1), env: {} },
    );
    assert.equal(result.success, false);
    if (!result.success) assert.equal(result.code, "MISSING_ENV");
  });

  it("returns PASSPHRASE_REQUIRED when no passphrase + not unencrypted", async () => {
    const result = await archiveExportTool(
      {},
      { dbReader: dbReader(1) },
    );
    assert.equal(result.success, false);
    if (!result.success) assert.equal(result.code, "PASSPHRASE_REQUIRED");
  });
});

describe("mcp / archive_import tool", () => {
  it("exposes a name + inputSchema with required archive_b64", () => {
    assert.equal(archiveImportToolSchema.name, "archive_import");
    assert.deepEqual(archiveImportToolSchema.inputSchema.required, [
      "archive_b64",
    ]);
  });

  it("round-trips export → import through MCP tools (encrypted)", async () => {
    const exp = await archiveExportTool(
      { passphrase_env: "PW" },
      { dbReader: dbReader(4), env: { PW: "mcp-test-pw" } },
    );
    assert.ok(exp.success);
    if (!exp.success) return;

    let persisted: number | null = null;
    const imp = await archiveImportTool(
      {
        archive_b64: exp.archive_b64,
        passphrase_env: "PW",
      },
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        env: { PW: "mcp-test-pw" },
        persist: async (r) => {
          persisted = r.chunks.length;
        },
      },
    );
    assert.ok(imp.success);
    if (imp.success) {
      assert.equal(imp.encrypted, true);
      assert.equal(imp.stats.chunks.inserted, 4);
      assert.equal(imp.applied, true);
      assert.equal(persisted, 4);
    }
  });

  it("dry_run does not persist", async () => {
    const exp = await archiveExportTool(
      { unencrypted: true },
      { dbReader: dbReader(2) },
    );
    if (!exp.success) throw new Error("export failed");
    let persisted = false;
    const imp = await archiveImportTool(
      { archive_b64: exp.archive_b64, dry_run: true },
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
    assert.ok(imp.success);
    if (imp.success) assert.equal(imp.applied, false);
    assert.equal(persisted, false);
  });

  it("returns error on bad base64", async () => {
    const result = await archiveImportTool(
      { archive_b64: "not_valid_base64_!!" },
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
    // Base64 of garbage may still decode to bytes; we expect a downstream
    // archive-format error instead.
    assert.equal(result.success, false);
  });
});
