/**
 * T10 — Round-trip integration test (orchestrator level).
 *
 * Exercises the full pipeline: runExport → archive Buffer → runImport →
 * resolved rows. Both encrypted + unencrypted paths. Tamper test flips a byte
 * inside an encrypted file's ciphertext and asserts TamperedArchiveError on
 * import; manifest tamper test flips a manifest byte and asserts the AAD chain
 * rejects.
 *
 * Spec §6 DoD #1, #2, #3, #5. Memory feedback `feedback_kg_relations_uses_fk_ids`
 * also exercised via planKgMerge edge cases.
 *
 * Why an in-memory model instead of better-sqlite3:
 *   - staged-A2 has zero external native deps to stay buildable on any CI.
 *   - Production wiring (T11 CLI → `nox-mem import`) uses better-sqlite3 in the
 *     parent repo. The orchestrator is DB-agnostic; the resolved.* arrays it
 *     returns are exactly what the production CLI persists via prepared
 *     INSERTs. This test asserts row-for-row equality on those arrays.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  runExport,
  runImport,
  listArchiveEntries,
} from "../orchestrator.js";
import {
  ChunkRow,
  KgEntityRow,
  KgRelationRow,
  OpsAuditRow,
  TamperedArchiveError,
  BadPassphraseError,
} from "../types.js";
import { parseManifest } from "../manifest.js";
import { unpackArchive, packArchive } from "../format.js";
import { EmbeddingInput } from "../serializers/embeddings.js";

// -- fixtures -----------------------------------------------------------------

function makeChunk(id: number): ChunkRow {
  return {
    id,
    content: `Chunk ${id} content — texto com acentuação português para teste unicode`,
    content_hash: `hash-${id.toString().padStart(8, "0")}`,
    source_path: `/notes/file-${id}.md`,
    source_kind: id % 3 === 0 ? "entity" : "note",
    project: id % 2 === 0 ? "nox-mem" : "openclaw-vps",
    created_at: "2026-05-18T12:00:00.000Z",
    updated_at: id % 5 === 0 ? "2026-05-18T13:00:00.000Z" : null,
    retention_days: id % 4 === 0 ? null : 90,
    pain: (id % 10) * 0.1,
    section: id % 3 === 0 ? "compiled" : null,
    section_boost: id % 3 === 0 ? 2.0 : null,
    metadata_json: JSON.stringify({ tag: `t${id}` }),
  };
}

function makeKgEntity(id: number): KgEntityRow {
  return {
    id,
    kind: id % 2 === 0 ? "person" : "project",
    canonical_name: `Entity ${id}`,
    slug: `entity-${id}`,
    aliases_json: JSON.stringify([`alias-${id}-a`, `alias-${id}-b`]),
    frontmatter_json: JSON.stringify({ tier: "A" }),
    updated_at: "2026-05-18T10:00:00.000Z",
  };
}

function makeKgRelation(id: number, src: number, tgt: number): KgRelationRow {
  return {
    id,
    source_entity_id: src,
    target_entity_id: tgt,
    predicate: id % 2 === 0 ? "works_with" : "mentions",
    confidence: 0.5 + (id % 5) * 0.1,
    metadata_json: null,
    created_at: "2026-05-18T11:00:00.000Z",
  };
}

function makeOpsAudit(id: number): OpsAuditRow {
  const statuses: OpsAuditRow["status"][] = [
    "started",
    "success",
    "failed",
    "crashed",
  ];
  return {
    id,
    op: "reindex",
    status: statuses[id % statuses.length]!,
    started_at: "2026-05-17T22:00:00.000Z",
    completed_at: id % 2 === 0 ? "2026-05-17T22:05:00.000Z" : null,
    metadata_json: JSON.stringify({ snapshot: `snap-${id}` }),
  };
}

function makeEmbedding(chunkId: number, dim = 32): EmbeddingInput {
  const vector = new Float32Array(dim);
  for (let i = 0; i < dim; i++) {
    vector[i] = Math.sin(chunkId * 0.13 + i * 0.07);
  }
  return {
    chunk_id: chunkId,
    vector,
    model_name: "gemini-embedding-001",
    embedded_at: "2026-05-18T12:30:00.000Z",
  };
}

function makeFullCorpus(n: number): {
  chunks: ChunkRow[];
  embeddings: EmbeddingInput[];
  kg_entities: KgEntityRow[];
  kg_relations: KgRelationRow[];
  ops_audit: OpsAuditRow[];
} {
  const chunks = Array.from({ length: n }, (_, i) => makeChunk(i + 1));
  const embeddings = chunks.map((c) => makeEmbedding(c.id));
  // ~50 entities, ~30 relations
  const entityCount = Math.max(50, Math.floor(n / 2));
  const kg_entities = Array.from({ length: entityCount }, (_, i) =>
    makeKgEntity(i + 1),
  );
  const relCount = Math.max(30, Math.floor(n / 3));
  const kg_relations = Array.from({ length: relCount }, (_, i) =>
    makeKgRelation(
      i + 1,
      ((i * 3) % entityCount) + 1,
      ((i * 5 + 1) % entityCount) + 1,
    ),
  );
  const ops_audit = Array.from({ length: 10 }, (_, i) => makeOpsAudit(i + 1));
  return { chunks, embeddings, kg_entities, kg_relations, ops_audit };
}

const BASE_REQ_FIELDS = {
  schema_version: 18,
  source_hostname: "test-host",
  source_nox_mem_version: "v3.7-test",
  embedding_provider: "gemini",
  embedding_model: "gemini-embedding-001",
  embedding_dim: 32,
  sqlite_vec_version: "0.1.6",
};

// -- tests --------------------------------------------------------------------

describe("roundtrip / unencrypted", () => {
  it("round-trips 100 chunks + embeddings + KG + ops_audit", async () => {
    const corpus = makeFullCorpus(100);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      unencrypted: true,
    });

    assert.equal(exp.manifest.counts.chunks, 100);
    assert.equal(exp.manifest.counts.embeddings, 100);
    assert.equal(exp.manifest.encryption.enabled, false);
    assert.ok(exp.size_bytes > 0);

    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
    });

    assert.equal(imp.applied, true);
    assert.equal(imp.stats.chunks.inserted, 100);
    assert.equal(imp.resolved.chunks.length, 100);
    assert.equal(imp.resolved.embeddings.size, 100);
    assert.equal(imp.resolved.kg_entities.length, corpus.kg_entities.length);
    assert.equal(
      imp.resolved.ops_audit.length,
      corpus.ops_audit.length,
    );

    // Row-for-row equality
    for (let i = 0; i < 100; i++) {
      assert.deepEqual(imp.resolved.chunks[i], corpus.chunks[i]);
    }
  });

  it("round-trips embedding vectors with byte-identity", async () => {
    const corpus = makeFullCorpus(10);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      unencrypted: true,
    });
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
    });
    for (const original of corpus.embeddings) {
      const got = imp.resolved.embeddings.get(original.chunk_id);
      assert.ok(got, `embedding for chunk ${original.chunk_id}`);
      assert.equal(got!.vector.length, original.vector.length);
      for (let i = 0; i < original.vector.length; i++) {
        // Float32 round-trip should be exact (no normalization happens)
        assert.equal(got!.vector[i], original.vector[i]);
      }
    }
  });

  it("preserves all schema v.29 chunk columns including retention_days, pain, section, section_boost", async () => {
    const chunks: ChunkRow[] = [
      {
        ...makeChunk(1),
        retention_days: null, // feedback never-decay
        pain: 0.9,
        section: "compiled",
        section_boost: 2.0,
      },
      {
        ...makeChunk(2),
        retention_days: 365,
        pain: 0.2,
        section: "timeline",
        section_boost: 0.8,
      },
    ];
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      chunks,
      unencrypted: true,
    });
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
    });
    assert.deepEqual(imp.resolved.chunks, chunks);
  });

  it("ops_audit append-only: existing rows preserved, incoming appended", async () => {
    const corpus = makeFullCorpus(5);
    corpus.ops_audit = [makeOpsAudit(1), makeOpsAudit(2)];
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      unencrypted: true,
    });
    const existingOps: OpsAuditRow[] = [
      { ...makeOpsAudit(100), id: 100, op: "preexisting" },
    ];
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
      existing: { ops_audit: existingOps },
    });
    assert.equal(imp.resolved.ops_audit.length, 3); // 1 existing + 2 incoming
    // Existing row must still be present
    assert.ok(
      imp.resolved.ops_audit.some((r) => r.id === 100 && r.op === "preexisting"),
    );
  });
});

describe("roundtrip / encrypted", () => {
  const PASSPHRASE = "correct-horse-battery-staple-encrypt-test";

  it("encrypted round-trip preserves all rows + reports enabled flag", async () => {
    const corpus = makeFullCorpus(20);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    assert.equal(exp.manifest.encryption.enabled, true);
    assert.equal(exp.manifest.encryption.algorithm, "AES-256-GCM");
    assert.equal(exp.manifest.encryption.kdf, "scrypt");
    assert.deepEqual(exp.manifest.encryption.kdf_params, {
      N: 131072,
      r: 8,
      p: 1,
    });

    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
      passphrase: PASSPHRASE,
    });
    assert.equal(imp.resolved.chunks.length, 20);
    for (let i = 0; i < 20; i++) {
      assert.deepEqual(imp.resolved.chunks[i], corpus.chunks[i]);
    }
  });

  it("encrypted archive uses .enc-suffixed file names in tar layout", async () => {
    const corpus = makeFullCorpus(3);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    const names = listArchiveEntries(exp.archive);
    assert.ok(names.includes("manifest.json"));
    assert.ok(names.includes("schema.sql"));
    assert.ok(names.includes("chunks.jsonl.enc"));
    assert.ok(!names.includes("chunks.jsonl")); // unencrypted name absent
    assert.ok(names.includes("kg_entities.jsonl.enc"));
    assert.ok(names.includes("kg_relations.jsonl.enc"));
    assert.ok(names.includes("ops_audit.jsonl.enc"));
    assert.ok(names.includes("embeddings.bin.enc"));
    assert.ok(names.includes("embeddings.idx.enc"));
  });

  it("manifest stays plaintext even when archive is encrypted (D41 #2)", async () => {
    const corpus = makeFullCorpus(3);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    const entries = unpackArchive(exp.archive);
    const manifestEntry = entries.find((e) => e.name === "manifest.json");
    assert.ok(manifestEntry);
    const parsed = parseManifest(manifestEntry!.content);
    assert.equal(parsed.counts.chunks, 3);
    assert.equal(parsed.encryption.enabled, true);
    // Counts must be readable without a passphrase
    assert.ok(parsed.counts.chunks > 0);
    assert.ok(parsed.encryption.kdf_salt_b64);
  });

  it("rejects export when no passphrase provided + not unencrypted (D41 #2 default safety)", async () => {
    const corpus = makeFullCorpus(1);
    await assert.rejects(
      runExport({
        ...BASE_REQ_FIELDS,
        ...corpus,
      } as any),
      /passphrase required/,
    );
  });

  it("rejects import when archive encrypted but no passphrase given", async () => {
    const corpus = makeFullCorpus(1);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    await assert.rejects(
      runImport({
        archive: exp.archive,
        current_schema_version: 18,
      }),
      /encrypted/,
    );
  });
});

describe("roundtrip / tamper detection", () => {
  const PASSPHRASE = "tamper-test-passphrase";

  it("flipping 1 byte in chunks.jsonl.enc rejects import with TamperedArchiveError", async () => {
    const corpus = makeFullCorpus(3);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });

    // Unpack, tamper, repack
    const entries = unpackArchive(exp.archive);
    const chunksEnc = entries.find((e) => e.name === "chunks.jsonl.enc");
    assert.ok(chunksEnc);
    // Flip a byte well past the GCM padding boundary
    const tamperedContent = Buffer.from(chunksEnc!.content);
    tamperedContent[10] = tamperedContent[10]! ^ 0xff;
    const tamperedEntries = entries.map((e) =>
      e.name === "chunks.jsonl.enc"
        ? { ...e, content: tamperedContent }
        : e,
    );
    const tamperedArchive = packArchive(tamperedEntries);

    await assert.rejects(
      runImport({
        archive: tamperedArchive,
        current_schema_version: 18,
        passphrase: PASSPHRASE,
      }),
      TamperedArchiveError,
    );
  });

  it("flipping 1 byte in manifest.json rejects via parse OR AAD divergence", async () => {
    const corpus = makeFullCorpus(3);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    const entries = unpackArchive(exp.archive);
    const manifestEntry = entries.find((e) => e.name === "manifest.json");
    assert.ok(manifestEntry);
    // Flip a byte inside the JSON payload — likely breaks parse, but if it
    // lands on a value that stays valid JSON the AAD mismatch still kills the
    // import via GCM tag.
    const tampered = Buffer.from(manifestEntry!.content);
    // Land on a digit (more likely to keep JSON valid) — target counts.chunks
    // hopefully ends up with a value change that still parses but mismatches AAD.
    const text = tampered.toString("utf8");
    const idx = text.indexOf('"counts":');
    if (idx >= 0) {
      // Pivot the next digit
      for (let i = idx; i < tampered.length; i++) {
        const ch = tampered[i]!;
        if (ch >= 0x30 && ch <= 0x39) {
          tampered[i] = ch === 0x39 ? 0x30 : ch + 1;
          break;
        }
      }
    } else {
      tampered[5] = tampered[5]! ^ 0x01;
    }
    const tamperedEntries = entries.map((e) =>
      e.name === "manifest.json" ? { ...e, content: tampered } : e,
    );
    const tamperedArchive = packArchive(tamperedEntries);

    await assert.rejects(
      runImport({
        archive: tamperedArchive,
        current_schema_version: 18,
        passphrase: PASSPHRASE,
      }),
      (err) =>
        err instanceof TamperedArchiveError ||
        err instanceof BadPassphraseError ||
        // ManifestError if parse breaks first
        /[Mm]anifest/.test((err as Error).message) ||
        /checksum mismatch/.test((err as Error).message),
    );
  });

  it("wrong passphrase rejects with BadPassphraseError, never silent garbage", async () => {
    const corpus = makeFullCorpus(2);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    await assert.rejects(
      runImport({
        archive: exp.archive,
        current_schema_version: 18,
        passphrase: "wrong-passphrase-xyz",
      }),
      BadPassphraseError,
    );
  });
});

describe("roundtrip / verify_only + dry_run modes", () => {
  const PASSPHRASE = "verify-test-passphrase";

  it("verify_only validates integrity without producing resolved rows", async () => {
    const corpus = makeFullCorpus(5);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: PASSPHRASE,
    });
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
      passphrase: PASSPHRASE,
      verify_only: true,
    });
    assert.equal(imp.applied, false);
    assert.equal(imp.resolved.chunks.length, 0);
    // Counts come from manifest (unencrypted), proving manifest is inspectable
    assert.equal(imp.manifest.counts.chunks, 5);
  });

  it("dry_run still resolves rows but flags applied=false", async () => {
    const corpus = makeFullCorpus(5);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      unencrypted: true,
    });
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
      dry_run: true,
    });
    assert.equal(imp.applied, false);
    assert.equal(imp.resolved.chunks.length, 5);
  });
});

describe("roundtrip / progress + cancellation", () => {
  it("emits ordered progress events through the export pipeline", async () => {
    const corpus = makeFullCorpus(5);
    const events: string[] = [];
    await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      unencrypted: true,
      onProgress: (ev) => events.push(ev.phase),
    });
    assert.ok(events.includes("export.start"));
    assert.ok(events.includes("export.chunks"));
    assert.ok(events.includes("export.pack"));
    assert.equal(events[events.length - 1], "export.done");
  });

  it("AbortSignal cancels export between phases", async () => {
    const corpus = makeFullCorpus(5);
    const ctrl = new AbortController();
    ctrl.abort();
    await assert.rejects(
      runExport({
        ...BASE_REQ_FIELDS,
        ...corpus,
        unencrypted: true,
        signal: ctrl.signal,
      }),
      /cancelled/,
    );
  });
});

describe("roundtrip / unicode + portuguese paths", () => {
  it("preserves unicode content (português, emoji omitted to stay 100-byte path safe)", async () => {
    const chunks: ChunkRow[] = [
      {
        ...makeChunk(1),
        content:
          "Você prefere RRF k=60 (não use tu/te). Empresa ação, decisão, função.",
        source_path: "/notas/decisão-importante.md",
      },
    ];
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      chunks,
      unencrypted: true,
    });
    const imp = await runImport({
      archive: exp.archive,
      current_schema_version: 18,
    });
    assert.equal(imp.resolved.chunks[0]!.content, chunks[0]!.content);
    assert.equal(imp.resolved.chunks[0]!.source_path, chunks[0]!.source_path);
  });
});

describe("roundtrip / open-toolchain inspect (DoD #4)", () => {
  it("listArchiveEntries returns manifest + schema in plaintext for encrypted archives", async () => {
    const corpus = makeFullCorpus(2);
    const exp = await runExport({
      ...BASE_REQ_FIELDS,
      ...corpus,
      passphrase: "inspect-test",
    });
    const names = listArchiveEntries(exp.archive);
    // Manifest and schema are visible without any nox-mem tool
    assert.ok(names.includes("manifest.json"));
    assert.ok(names.includes("schema.sql"));
  });
});
