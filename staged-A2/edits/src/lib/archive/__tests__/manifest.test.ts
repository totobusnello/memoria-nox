/**
 * T2 — manifest.ts tests.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  buildManifest,
  canonicalize,
  manifestAADHash,
  manifestAADSource,
  parseManifest,
  writeManifest,
} from "../manifest.js";
import { ManifestError } from "../types.js";

function seed() {
  return {
    schema_version: 18,
    source_hostname: "test-host",
    source_nox_mem_version: "3.7.2",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: 3072,
    includes: ["chunks", "kg"] as ("chunks" | "kg")[],
    counts: { chunks: 5, embeddings: 5, kg_entities: 2, kg_relations: 1, ops_audit: 0 },
    checksums: {
      "chunks.jsonl": "a".repeat(64),
      "kg_entities.jsonl": "b".repeat(64),
    },
    created_at: "2026-05-18T12:00:00.000Z",
  };
}

describe("manifest / canonicalize", () => {
  it("sorts object keys recursively", () => {
    const out = canonicalize({ b: 1, a: 2, c: { y: 1, x: 2 } });
    assert.equal(out, '{"a":2,"b":1,"c":{"x":2,"y":1}}');
  });

  it("rejects NaN and Infinity", () => {
    assert.throws(() => canonicalize(NaN), /non-finite/);
    assert.throws(() => canonicalize(Infinity), /non-finite/);
  });

  it("is byte-stable across multiple calls (AAD property)", () => {
    const obj = { z: [3, 1, 2], a: { b: "x", a: "y" } };
    assert.equal(canonicalize(obj), canonicalize(obj));
  });
});

describe("manifest / build + write + parse round-trip", () => {
  it("round-trips a basic manifest", () => {
    const m = buildManifest(seed());
    const buf = writeManifest(m);
    const back = parseManifest(buf);
    assert.equal(back.schema_version, 18);
    assert.equal(back.source_hostname, "test-host");
    assert.equal(back.counts.chunks, 5);
  });

  it("rejects bad sha256 checksum hex on write", () => {
    const m = buildManifest(seed());
    m.checksums["chunks.jsonl"] = "not-a-hash";
    assert.throws(() => writeManifest(m), ManifestError);
  });

  it("rejects unsupported format_version on parse", () => {
    const m = buildManifest(seed());
    const obj = JSON.parse(writeManifest(m).toString("utf8"));
    obj.format_version = "999.0";
    const corrupted = Buffer.from(JSON.stringify(obj));
    assert.throws(() => parseManifest(corrupted), /format_version/);
  });
});

describe("manifest / AAD source", () => {
  it("AAD excludes per-file encryption metadata", () => {
    const m = buildManifest(seed());
    const aadBefore = manifestAADHash(m);
    // Now add fake encryption per-file metadata
    m.encryption = {
      enabled: true,
      algorithm: "AES-256-GCM",
      kdf: "scrypt",
      kdf_params: { N: 131072, r: 8, p: 1 },
      kdf_salt_b64: Buffer.alloc(16).toString("base64"),
      files: {
        "chunks.jsonl.enc": {
          nonce_b64: Buffer.alloc(12).toString("base64"),
          tag_b64: Buffer.alloc(16).toString("base64"),
          ciphertext_sha256: "c".repeat(64),
        },
      },
      aad_source: "sha256(manifest_pre_encryption_bytes)",
      format_version: 1,
    };
    const aadAfter = manifestAADHash(m);
    assert.ok(Buffer.compare(aadBefore, aadAfter) === 0,
      "AAD must be stable against per-file encryption metadata additions");
  });

  it("AAD changes when manifest counts change (tamper signal)", () => {
    const m = buildManifest(seed());
    const aadBefore = manifestAADHash(m);
    m.counts.chunks = 9999;
    const aadAfter = manifestAADHash(m);
    assert.notEqual(aadBefore.toString("hex"), aadAfter.toString("hex"));
  });

  it("AAD equals sha256 of canonical manifest (zeroed files)", () => {
    const m = buildManifest(seed());
    const expected = createHash("sha256").update(manifestAADSource(m)).digest();
    assert.equal(manifestAADHash(m).toString("hex"), expected.toString("hex"));
  });
});
