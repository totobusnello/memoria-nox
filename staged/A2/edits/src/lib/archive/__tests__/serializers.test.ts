/**
 * T3-T6 — serializer tests (chunks, embeddings, kg, ops_audit).
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  serializeChunks,
  parseChunks,
  planChunkImport,
} from "../serializers/chunks.js";
import {
  serializeEmbeddings,
  parseEmbeddings,
} from "../serializers/embeddings.js";
import {
  serializeKgEntities,
  parseKgEntities,
  serializeKgRelations,
  parseKgRelations,
  planKgMerge,
} from "../serializers/kg.js";
import {
  serializeOpsAudit,
  parseOpsAudit,
  planOpsAuditImport,
} from "../serializers/ops_audit.js";
import { ChunkRow, KgEntityRow, KgRelationRow, OpsAuditRow } from "../types.js";

function sampleChunk(overrides: Partial<ChunkRow> = {}): ChunkRow {
  return {
    id: 1,
    content: "hello world",
    content_hash: "h".repeat(64),
    source_path: "/tmp/test.md",
    source_kind: "markdown",
    project: "nox-mem",
    created_at: "2026-05-18T12:00:00Z",
    updated_at: null,
    retention_days: 90,
    pain: 0.2,
    section: null,
    section_boost: null,
    metadata_json: null,
    ...overrides,
  };
}

describe("serializers / chunks", () => {
  it("round-trips a single row preserving all schema v.29 columns", () => {
    const row = sampleChunk({
      retention_days: null,
      pain: 0.7,
      section: "compiled",
      section_boost: 2.0,
      metadata_json: '{"project":"nox-mem"}',
    });
    const buf = serializeChunks([row]);
    const [back] = parseChunks(buf);
    assert.deepEqual(back, row);
  });

  it("round-trips 100 rows preserving order", () => {
    const rows: ChunkRow[] = [];
    for (let i = 0; i < 100; i++) {
      rows.push(sampleChunk({ id: i, content_hash: String(i).padStart(64, "0") }));
    }
    const back = parseChunks(serializeChunks(rows));
    assert.equal(back.length, 100);
    for (let i = 0; i < 100; i++) assert.equal(back[i]!.id, i);
  });

  it("planChunkImport merge skips by content_hash", () => {
    const existing = [sampleChunk({ id: 1, content_hash: "a".repeat(64) })];
    const incoming = [
      sampleChunk({ id: 99, content_hash: "a".repeat(64) }), // dup
      sampleChunk({ id: 100, content_hash: "b".repeat(64) }), // new
    ];
    const plan = planChunkImport(incoming, existing, "merge");
    assert.equal(plan.inserted, 1);
    assert.equal(plan.skipped, 1);
    assert.equal(plan.keep.length, 2);
  });

  it("planChunkImport replace wipes existing", () => {
    const existing = [sampleChunk({ id: 1 })];
    const incoming = [sampleChunk({ id: 2 }), sampleChunk({ id: 3 })];
    const plan = planChunkImport(incoming, existing, "replace");
    assert.equal(plan.inserted, 2);
    assert.equal(plan.keep.length, 2);
    assert.ok(plan.keep.every((r) => r.id >= 2));
  });

  it("rejects rows missing a v.29 field", () => {
    const broken = '{"id":1,"content":"x"}';
    assert.throws(() => parseChunks(Buffer.from(broken + "\n")), /missing/);
  });
});

describe("serializers / embeddings", () => {
  it("round-trips a 3072-dim Float32Array byte-identically", () => {
    const dim = 3072;
    const vec = new Float32Array(dim);
    for (let i = 0; i < dim; i++) vec[i] = Math.sin(i * 0.01);
    const bundle = serializeEmbeddings([
      { chunk_id: 42, vector: vec, model_name: "gemini-embedding-001", embedded_at: "2026-05-18T12:00:00Z" },
    ]);
    const map = parseEmbeddings(bundle.bin, bundle.idx);
    const back = map.get(42)!;
    assert.equal(back.vector.length, dim);
    for (let i = 0; i < dim; i++) {
      assert.equal(back.vector[i], vec[i],
        `dim ${i} mismatch: ${back.vector[i]} vs ${vec[i]}`);
    }
  });

  it("round-trips multiple rows", () => {
    const dim = 8;
    const rows = [
      { chunk_id: 1, vector: new Float32Array([1, 2, 3, 4, 5, 6, 7, 8]), model_name: "m", embedded_at: "t" },
      { chunk_id: 2, vector: new Float32Array([-1, -2, -3, -4, -5, -6, -7, -8]), model_name: "m", embedded_at: "t" },
    ];
    const bundle = serializeEmbeddings(rows);
    const map = parseEmbeddings(bundle.bin, bundle.idx);
    assert.equal(map.size, 2);
    assert.equal(map.get(1)!.vector[3], 4);
    assert.equal(map.get(2)!.vector[3], -4);
  });

  it("rejects dim mismatch within batch", () => {
    assert.throws(
      () => serializeEmbeddings([
        { chunk_id: 1, vector: new Float32Array([1, 2, 3]), model_name: "m", embedded_at: "t" },
        { chunk_id: 2, vector: new Float32Array([1, 2]), model_name: "m", embedded_at: "t" },
      ]),
      /dim mismatch/,
    );
  });

  it("rejects bad magic on parse", () => {
    const fake = Buffer.alloc(16);
    fake.write("BADMAGIC", 0);
    assert.throws(() => parseEmbeddings(fake, Buffer.alloc(0)), /bad magic/);
  });

  it("survives a forced GC cycle (Buffer pool aliasing canary)", () => {
    const dim = 16;
    const rows = [];
    for (let i = 0; i < 20; i++) {
      const v = new Float32Array(dim);
      for (let j = 0; j < dim; j++) v[j] = i * 100 + j;
      rows.push({ chunk_id: i, vector: v, model_name: "m", embedded_at: "t" });
    }
    const bundle = serializeEmbeddings(rows);
    // Force allocation churn so the Buffer pool gets reused
    for (let k = 0; k < 200; k++) Buffer.alloc(16384).fill(k & 0xff);
    const map = parseEmbeddings(bundle.bin, bundle.idx);
    for (let i = 0; i < 20; i++) {
      const v = map.get(i)!.vector;
      for (let j = 0; j < dim; j++) {
        assert.equal(v[j], i * 100 + j, `aliasing corruption at chunk ${i} dim ${j}`);
      }
    }
  });
});

describe("serializers / kg", () => {
  const entA: KgEntityRow = {
    id: 1, kind: "person", canonical_name: "Toto", slug: "toto",
    aliases_json: null, frontmatter_json: null, updated_at: "2026-05-18T00:00:00Z",
  };
  const entB: KgEntityRow = {
    id: 2, kind: "project", canonical_name: "nox-mem", slug: "nox-mem",
    aliases_json: null, frontmatter_json: null, updated_at: "2026-05-18T00:00:00Z",
  };
  const rel: KgRelationRow = {
    id: 1, source_entity_id: 1, target_entity_id: 2, predicate: "owns",
    confidence: 0.9, metadata_json: null, created_at: "2026-05-18T00:00:00Z",
  };

  it("round-trips entities + relations", () => {
    const e = parseKgEntities(serializeKgEntities([entA, entB]));
    assert.deepEqual(e, [entA, entB]);
    const r = parseKgRelations(serializeKgRelations([rel]));
    assert.deepEqual(r, [rel]);
  });

  it("merge remaps incoming FK ids via (kind, slug) lookup", () => {
    // Existing DB: entA only with id=10 (not 1)
    const existingEntities = [{ ...entA, id: 10 }];
    // Incoming: entA again (slug match) with id=1 + new entB id=2 + relation 1→2
    const incomingEntities = [entA, entB];
    const incomingRelations = [rel];
    const result = planKgMerge(
      incomingEntities,
      existingEntities,
      incomingRelations,
      [],
    );
    assert.equal(result.entities.inserted, 1); // entB only
    assert.equal(result.entities.merged, 1); // entA matched
    assert.equal(result.relations.inserted, 1);
    // The inserted relation's source_entity_id must point to existing id=10, not 1
    const newRel = result.relations.keep[0]!;
    assert.equal(newRel.source_entity_id, 10);
    // target was newly inserted; should NOT be 2 (which was incoming id)
    assert.ok(newRel.target_entity_id > 10);
  });

  it("skips relations with unresolvable FK endpoints (warning)", () => {
    const incomingRelations = [
      { ...rel, source_entity_id: 999, target_entity_id: 1000 },
    ];
    const result = planKgMerge([entA], [entA], incomingRelations, []);
    assert.equal(result.relations.skipped, 1);
    assert.ok(result.relations.warnings.length > 0);
    assert.match(result.relations.warnings[0]!, /FK endpoint missing/);
  });
});

describe("serializers / ops_audit", () => {
  const row: OpsAuditRow = {
    id: 1, op: "reindex", status: "success",
    started_at: "2026-05-18T12:00:00Z", completed_at: "2026-05-18T12:00:10Z",
    metadata_json: '{"chunks_processed":100}',
  };

  it("round-trips rows preserving status enum", () => {
    const back = parseOpsAudit(serializeOpsAudit([row]));
    assert.deepEqual(back, [row]);
  });

  it("rejects invalid status values on serialize", () => {
    const bad = { ...row, status: "completed" as OpsAuditRow["status"] };
    assert.throws(() => serializeOpsAudit([bad]), /invalid status/);
  });

  it("rejects invalid status on parse", () => {
    const badJson = JSON.stringify({ ...row, status: "rolled_back" });
    assert.throws(() => parseOpsAudit(Buffer.from(badJson + "\n")), /invalid status/);
  });

  it("plan import preserves all existing rows (append-only)", () => {
    const existing = [row, { ...row, id: 2 }];
    const incoming = [{ ...row, id: 3 }];
    const plan = planOpsAuditImport(incoming, existing);
    assert.equal(plan.inserted, 1);
    assert.equal(plan.keep.length, 3);
    assert.deepEqual(plan.keep.map((r) => r.id), [1, 2, 3]);
  });

  it("re-ids on collision (preserves append-only invariant)", () => {
    const existing = [{ ...row, id: 1 }];
    const incoming = [{ ...row, id: 1 }]; // collision
    const plan = planOpsAuditImport(incoming, existing);
    assert.equal(plan.inserted, 1);
    assert.equal(plan.keep.length, 2);
    assert.ok(plan.keep.some((r) => r.id === 1));
    assert.ok(plan.keep.some((r) => r.id === 2));
    assert.match(plan.warnings[0] ?? "", /collision/);
  });
});
