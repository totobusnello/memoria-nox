/**
 * S4 — Export → import round-trip with KG (A2 + L4 + L2 + L3).
 *
 * Verifies:
 *   - Build a full DB with chunks + KG (regex-extracted relations + LLM relations
 *     + frontmatter relations) + conflicts + canonical marks
 *   - Pack archive with passphrase (AES-256-GCM, scrypt KDF)
 *   - Unpack to a fresh DB and verify byte-equality across all tables
 *   - Verify L2 conflict detection produces same results on the imported DB
 *   - Tampered ciphertext fails with TamperedArchiveError-class
 *   - Wrong passphrase fails with BadPassphraseError-class
 *   - AAD mismatch (manifest tampering) fails to decrypt
 *
 * Bug-class targeted: the AAD bug caught in Wave B+C — packing used `manifest_v1`
 * but unpacking computed AAD from `manifest_v2` (different `created_at`), so
 * the GCM tag refused to verify on a freshly-packed-then-unpacked archive.
 * This scenario asserts AAD is deterministic across pack/unpack of the same
 * manifest, AND that mutating the manifest after pack invalidates the AAD.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";
import { createHash } from "node:crypto";

import { applySchema } from "../lib/schema.js";
import {
  packArchive,
  unpackArchive,
  detectDirectConflicts,
  markRelationCanonical,
  BadPassphraseError,
  manifestAADHash,
  canonicalize,
  type ArchiveManifest,
} from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);

  // Build a representative corpus.
  const insEnt = db.prepare(`INSERT INTO kg_entities (kind, name, slug) VALUES (?,?,?)`);
  const e1 = Number(insEnt.run("project", "FII Treviso", "fii-treviso").lastInsertRowid);
  const e2 = Number(insEnt.run("person", "Toto", "toto").lastInsertRowid);
  const e3 = Number(insEnt.run("person", "Boris", "boris").lastInsertRowid);
  const e4 = Number(insEnt.run("decision", "D41", "d41").lastInsertRowid);

  const insCh = db.prepare(
    `INSERT INTO chunks (content, content_hash, confidence, provenance_kind, section) VALUES (?,?,?,?,?)`
  );
  insCh.run("D41 decided default model is gemini-2.5-flash-lite", "h1", 0.9, "declared", "compiled");
  insCh.run("Toto leads FII Treviso", "h2", 0.85, "observed", "compiled");
  insCh.run("Boris also leads FII Treviso (regex-extracted, disputed)", "h3", 0.6, "inferred", "timeline");

  const insRel = db.prepare(
    `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method) VALUES (?,?,?,?,?)`
  );
  insRel.run(e1, e2, "led_by", 0.85, "regex_only");
  const r2 = insRel.run(e1, e3, "led_by", 0.7, "gemini_only");
  insRel.run(e4, e2, "decided_by", 0.95, "frontmatter");

  // Mark one variant canonical (L3 contract).
  markRelationCanonical(db, Number(r2.lastInsertRowid), "toto");

  // Record a conflict (L2).
  const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
  if (conflicts.length > 0) {
    const cins = db.prepare(
      `INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids, variants, shadow_mode)
       VALUES (?, ?, ?, ?, ?, 1)`
    );
    cins.run(
      conflicts[0]!.kind,
      conflicts[0]!.subject_entity_id,
      conflicts[0]!.predicate,
      JSON.stringify(conflicts[0]!.variants.map((v) => v.relation_id)),
      JSON.stringify(conflicts[0]!.variants)
    );
  }
});
afterEach(() => db.close());

interface ExportPayload {
  chunks: Array<Record<string, unknown>>;
  kg_entities: Array<Record<string, unknown>>;
  kg_relations: Array<Record<string, unknown>>;
  conflict_audit: Array<Record<string, unknown>>;
}

function serializeDb(d: DatabaseType): { manifest: ArchiveManifest; payload: Buffer } {
  const chunks = d.prepare(`SELECT * FROM chunks ORDER BY id`).all() as Array<
    Record<string, unknown>
  >;
  const ents = d.prepare(`SELECT * FROM kg_entities ORDER BY id`).all() as Array<
    Record<string, unknown>
  >;
  const rels = d.prepare(`SELECT * FROM kg_relations ORDER BY id`).all() as Array<
    Record<string, unknown>
  >;
  const conflicts = d
    .prepare(`SELECT * FROM conflict_audit ORDER BY id`)
    .all() as Array<Record<string, unknown>>;

  const payload: ExportPayload = {
    chunks,
    kg_entities: ents,
    kg_relations: rels,
    conflict_audit: conflicts,
  };
  const payloadBuf = Buffer.from(canonicalize(payload), "utf-8");
  const manifest: ArchiveManifest = {
    format_version: "1.0",
    schema_version: 22,
    created_at: "2026-05-18T00:00:00Z",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: 3072,
    counts: {
      chunks: chunks.length,
      kg_entities: ents.length,
      kg_relations: rels.length,
    },
    checksums: {
      payload_sha256: createHash("sha256").update(payloadBuf).digest("hex"),
    },
  };
  return { manifest, payload: payloadBuf };
}

function applyToFreshDb(payload: ExportPayload): DatabaseType {
  const d = new Database(":memory:");
  applySchema(d);

  const insEnt = d.prepare(
    `INSERT INTO kg_entities (id, kind, name, slug, aliases_json, frontmatter_json, updated_at) VALUES (?,?,?,?,?,?,?)`
  );
  for (const e of payload.kg_entities) {
    insEnt.run(
      e.id,
      e.kind,
      e.name,
      e.slug,
      e.aliases_json,
      e.frontmatter_json,
      e.updated_at
    );
  }

  const insCh = d.prepare(
    `INSERT INTO chunks (id, content, content_hash, source_path, source_kind, project, created_at, updated_at, retention_days, pain, section, section_boost, metadata_json, confidence, provenance_kind, embed_provider, embed_dim, embedded_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
  );
  for (const c of payload.chunks) {
    insCh.run(
      c.id,
      c.content,
      c.content_hash,
      c.source_path,
      c.source_kind,
      c.project,
      c.created_at,
      c.updated_at,
      c.retention_days,
      c.pain,
      c.section,
      c.section_boost,
      c.metadata_json,
      c.confidence,
      c.provenance_kind,
      c.embed_provider,
      c.embed_dim,
      c.embedded_at
    );
  }

  const insRel = d.prepare(
    `INSERT INTO kg_relations (id, source_entity_id, target_entity_id, predicate, evidence_chunk_id, user_marked, confidence, superseded_by_relation_id, superseded_at, superseded_reason, created_at, updated_at, extraction_method)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`
  );
  for (const r of payload.kg_relations) {
    insRel.run(
      r.id,
      r.source_entity_id,
      r.target_entity_id,
      r.predicate,
      r.evidence_chunk_id,
      r.user_marked,
      r.confidence,
      r.superseded_by_relation_id,
      r.superseded_at,
      r.superseded_reason,
      r.created_at,
      r.updated_at,
      r.extraction_method
    );
  }

  // conflict_audit (status defaults to 'open'; we replay raw rows for byte-equality).
  const insConf = d.prepare(
    `INSERT INTO conflict_audit (id, ts, kind, subject_entity_id, predicate, target_relation_ids, variants, status, resolved_by, resolved_at, resolution_kind, picked_relation_id, merge_target, notes, shadow_mode)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
  );
  for (const c of payload.conflict_audit) {
    insConf.run(
      c.id,
      c.ts,
      c.kind,
      c.subject_entity_id,
      c.predicate,
      c.target_relation_ids,
      c.variants,
      c.status,
      c.resolved_by,
      c.resolved_at,
      c.resolution_kind,
      c.picked_relation_id,
      c.merge_target,
      c.notes,
      c.shadow_mode
    );
  }
  return d;
}

function dumpTables(d: DatabaseType) {
  return {
    chunks: d.prepare(`SELECT * FROM chunks ORDER BY id`).all(),
    kg_entities: d.prepare(`SELECT * FROM kg_entities ORDER BY id`).all(),
    kg_relations: d.prepare(`SELECT * FROM kg_relations ORDER BY id`).all(),
    conflict_audit: d.prepare(`SELECT * FROM conflict_audit ORDER BY id`).all(),
  };
}

describe("S4 — Export → import round-trip with KG (A2 + L4 + L2 + L3)", () => {
  it("S4-01 round-trip preserves chunks byte-for-byte", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const plaintext = unpackArchive("test-passphrase", blob);
    const recovered = JSON.parse(plaintext.toString("utf-8")) as ExportPayload;
    const d2 = applyToFreshDb(recovered);
    assert.deepStrictEqual(dumpTables(d2).chunks, dumpTables(db).chunks);
    d2.close();
  });

  it("S4-02 round-trip preserves kg_entities byte-for-byte", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const recovered = JSON.parse(
      unpackArchive("test-passphrase", blob).toString("utf-8")
    ) as ExportPayload;
    const d2 = applyToFreshDb(recovered);
    assert.deepStrictEqual(dumpTables(d2).kg_entities, dumpTables(db).kg_entities);
    d2.close();
  });

  it("S4-03 round-trip preserves kg_relations including confidence + user_marked", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const recovered = JSON.parse(
      unpackArchive("test-passphrase", blob).toString("utf-8")
    ) as ExportPayload;
    const d2 = applyToFreshDb(recovered);
    assert.deepStrictEqual(dumpTables(d2).kg_relations, dumpTables(db).kg_relations);
    // L3 invariant survives round-trip.
    const marked = (dumpTables(d2).kg_relations as Array<{ user_marked: number; confidence: number }>)
      .filter((r) => r.user_marked === 1);
    assert.ok(marked.length >= 1);
    for (const m of marked) assert.strictEqual(m.confidence, 1.0);
    d2.close();
  });

  it("S4-04 round-trip preserves conflict_audit byte-for-byte", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const recovered = JSON.parse(
      unpackArchive("test-passphrase", blob).toString("utf-8")
    ) as ExportPayload;
    const d2 = applyToFreshDb(recovered);
    assert.deepStrictEqual(dumpTables(d2).conflict_audit, dumpTables(db).conflict_audit);
    d2.close();
  });

  it("S4-05 L2 conflict detection on imported DB matches source DB", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const recovered = JSON.parse(
      unpackArchive("test-passphrase", blob).toString("utf-8")
    ) as ExportPayload;
    const d2 = applyToFreshDb(recovered);

    const c1 = detectDirectConflicts(db, { min_confidence: 0.5 });
    const c2 = detectDirectConflicts(d2, { min_confidence: 0.5 });
    assert.strictEqual(c1.length, c2.length);
    if (c1.length > 0) {
      assert.strictEqual(c1[0]!.kind, c2[0]!.kind);
      assert.strictEqual(c1[0]!.predicate, c2[0]!.predicate);
      assert.strictEqual(c1[0]!.variants.length, c2[0]!.variants.length);
    }
    d2.close();
  });

  it("S4-06 wrong passphrase rejects archive with BadPassphraseError-class", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("right-passphrase", manifest, payload);
    assert.throws(() => unpackArchive("wrong-passphrase", blob), BadPassphraseError);
  });

  it("S4-07 tampered ciphertext rejects archive", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    // Flip one byte of ciphertext.
    blob.ciphertext[10] = blob.ciphertext[10]! ^ 0xff;
    assert.throws(() => unpackArchive("test-passphrase", blob), BadPassphraseError);
  });

  it("S4-08 AAD bug regression: mutating manifest after pack invalidates GCM tag", () => {
    // This is the EXACT AAD bug class that the round-trip test caught in Wave B+C.
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    // Mutate the manifest reference held in blob — recomputed AAD on unpack differs.
    const mutated = { ...blob, manifest: { ...blob.manifest, created_at: "2099-01-01T00:00:00Z" } };
    assert.throws(() => unpackArchive("test-passphrase", mutated as typeof blob), BadPassphraseError);
  });

  it("S4-09 AAD is deterministic: same manifest object → same AAD hash on every call", () => {
    const { manifest } = serializeDb(db);
    const h1 = manifestAADHash(manifest);
    const h2 = manifestAADHash(manifest);
    assert.deepStrictEqual(h1, h2);
  });

  it("S4-10 round-trip preserves chunk-level confidence + provenance fields", () => {
    const { manifest, payload } = serializeDb(db);
    const blob = packArchive("test-passphrase", manifest, payload);
    const recovered = JSON.parse(
      unpackArchive("test-passphrase", blob).toString("utf-8")
    ) as ExportPayload;
    const d2 = applyToFreshDb(recovered);
    const orig = db.prepare(`SELECT confidence, provenance_kind FROM chunks ORDER BY id`).all();
    const back = d2.prepare(`SELECT confidence, provenance_kind FROM chunks ORDER BY id`).all();
    assert.deepStrictEqual(back, orig);
    d2.close();
  });
});
