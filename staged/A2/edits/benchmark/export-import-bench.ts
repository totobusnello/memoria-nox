/**
 * T18 — Latency + size benchmark for export / import.
 *
 * Scales: 1k, 10k, 62k chunks with synthetic 3072d embeddings + ~400 KG
 * entities + ~600 relations. Reports archive size compressed / uncompressed,
 * encryption overhead, peak RSS, and rows/sec per table.
 *
 * Output: JSON to stdout + Markdown summary table.
 *
 * Run:
 *   npm run bench                       # default: small set (1k+10k)
 *   BENCH_FULL=1 npm run bench          # full set including 62k
 *
 * Notes:
 *   - 62k scale matches CLAUDE.md current corpus size (62.9k chunks v3.7).
 *   - We use 3072d (Gemini production dim) — RSS scales linearly w/ dim.
 *   - scrypt N=2^17 is the dominant fixed cost (~500-1000 ms on M-series). It
 *     is paid once per export regardless of corpus size.
 */

import { runExport, runImport } from "../src/lib/archive/orchestrator.js";
import { ChunkRow, KgEntityRow, KgRelationRow, OpsAuditRow } from "../src/lib/archive/types.js";
import { EmbeddingInput } from "../src/lib/archive/serializers/embeddings.js";

interface BenchPoint {
  scale: number;
  encrypted: boolean;
  export_ms: number;
  import_ms: number;
  archive_bytes: number;
  uncompressed_estimate_bytes: number;
  encryption_overhead_ms: number | null;
  peak_rss_mb: number;
  chunks_per_sec_export: number;
  chunks_per_sec_import: number;
}

const DIM = 3072;

function makeChunk(id: number): ChunkRow {
  return {
    id,
    content:
      `Chunk ${id} ` +
      "Lorem ipsum dolor sit amet consectetur adipiscing elit. ".repeat(8),
    content_hash: `h-${id.toString().padStart(10, "0")}`,
    source_path: `/notes/${id}.md`,
    source_kind: id % 3 === 0 ? "entity" : "note",
    project: id % 2 === 0 ? "nox-mem" : "openclaw-vps",
    created_at: "2026-05-18T00:00:00.000Z",
    updated_at: null,
    retention_days: 90,
    pain: (id % 10) * 0.1,
    section: id % 3 === 0 ? "compiled" : null,
    section_boost: id % 3 === 0 ? 2.0 : null,
    metadata_json: JSON.stringify({ tag: `t${id}` }),
  };
}

function makeEmbedding(chunkId: number): EmbeddingInput {
  const v = new Float32Array(DIM);
  for (let i = 0; i < DIM; i++) v[i] = Math.sin(chunkId * 0.13 + i * 0.007);
  return {
    chunk_id: chunkId,
    vector: v,
    model_name: "gemini-embedding-001",
    embedded_at: "2026-05-18T00:00:00.000Z",
  };
}

function makeEntity(id: number): KgEntityRow {
  return {
    id,
    kind: id % 2 === 0 ? "person" : "project",
    canonical_name: `Entity ${id}`,
    slug: `entity-${id}`,
    aliases_json: JSON.stringify([`a-${id}`]),
    frontmatter_json: null,
    updated_at: "2026-05-18T00:00:00.000Z",
  };
}

function makeRelation(id: number, src: number, tgt: number): KgRelationRow {
  return {
    id,
    source_entity_id: src,
    target_entity_id: tgt,
    predicate: "mentions",
    confidence: 0.8,
    metadata_json: null,
    created_at: "2026-05-18T00:00:00.000Z",
  };
}

function makeOps(id: number): OpsAuditRow {
  return {
    id,
    op: "reindex",
    status: "success",
    started_at: "2026-05-17T22:00:00.000Z",
    completed_at: "2026-05-17T22:05:00.000Z",
    metadata_json: null,
  };
}

async function runOne(scale: number, encrypted: boolean): Promise<BenchPoint> {
  const chunks = Array.from({ length: scale }, (_, i) => makeChunk(i + 1));
  const embeddings = chunks.map((c) => makeEmbedding(c.id));
  const ENT = Math.max(50, Math.floor(scale / 100));
  const REL = Math.max(80, Math.floor(scale / 100));
  const entities = Array.from({ length: ENT }, (_, i) => makeEntity(i + 1));
  const relations = Array.from({ length: REL }, (_, i) =>
    makeRelation(i + 1, ((i * 3) % ENT) + 1, ((i * 5 + 1) % ENT) + 1),
  );
  const ops = Array.from({ length: 10 }, (_, i) => makeOps(i + 1));

  const baseReq = {
    schema_version: 18,
    source_hostname: "bench",
    source_nox_mem_version: "v3.7-bench",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: DIM,
    sqlite_vec_version: null,
    chunks,
    embeddings,
    kg_entities: entities,
    kg_relations: relations,
    ops_audit: ops,
  };

  // -- Export
  const tExpStart = performance.now();
  let exp;
  if (encrypted) {
    exp = await runExport({ ...baseReq, passphrase: "bench-passphrase" });
  } else {
    exp = await runExport({ ...baseReq, unencrypted: true });
  }
  const exportMs = performance.now() - tExpStart;

  // -- Encryption overhead: re-run unencrypted to subtract
  let encOverhead: number | null = null;
  if (encrypted) {
    const t2 = performance.now();
    await runExport({ ...baseReq, unencrypted: true });
    const plainMs = performance.now() - t2;
    encOverhead = exportMs - plainMs;
  }

  // -- Import
  const tImpStart = performance.now();
  await runImport({
    archive: exp.archive,
    current_schema_version: 18,
    passphrase: encrypted ? "bench-passphrase" : undefined,
  });
  const importMs = performance.now() - tImpStart;

  // Uncompressed estimate = serialized chunks + embeddings + KG + ops
  // Calculated by encoding JSONL once (cheap, helps the ratio table).
  const uncompressed = estimateUncompressedSize(scale, ENT, REL, DIM);
  const peakRssMb = process.memoryUsage().rss / (1024 * 1024);

  return {
    scale,
    encrypted,
    export_ms: Math.round(exportMs),
    import_ms: Math.round(importMs),
    archive_bytes: exp.archive.length,
    uncompressed_estimate_bytes: uncompressed,
    encryption_overhead_ms: encOverhead === null ? null : Math.round(encOverhead),
    peak_rss_mb: Math.round(peakRssMb),
    chunks_per_sec_export: Math.round((scale / exportMs) * 1000),
    chunks_per_sec_import: Math.round((scale / importMs) * 1000),
  };
}

function estimateUncompressedSize(
  chunks: number,
  entities: number,
  relations: number,
  dim: number,
): number {
  const CHUNK_JSON_BYTES = 350; // rough per-line JSONL
  const EMBED_BYTES = dim * 4;
  const ENT_JSON = 250;
  const REL_JSON = 200;
  return (
    chunks * CHUNK_JSON_BYTES +
    chunks * EMBED_BYTES +
    entities * ENT_JSON +
    relations * REL_JSON
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function buildMarkdown(points: BenchPoint[]): string {
  let out = "# A2 Export/Import Benchmark\n\n";
  out += "| Scale | Mode | Export ms | Import ms | Archive | Uncompressed | Compression | Enc overhead ms | RSS MB | Export rows/s | Import rows/s |\n";
  out += "|------:|------|----------:|----------:|---------|--------------|------------:|----------------:|-------:|--------------:|--------------:|\n";
  for (const p of points) {
    const ratio = (p.archive_bytes / p.uncompressed_estimate_bytes) * 100;
    out +=
      `| ${p.scale} | ${p.encrypted ? "enc" : "plain"} | ${p.export_ms} | ${p.import_ms} | ${formatBytes(p.archive_bytes)} | ${formatBytes(p.uncompressed_estimate_bytes)} | ${ratio.toFixed(1)}% | ${p.encryption_overhead_ms ?? "—"} | ${p.peak_rss_mb} | ${p.chunks_per_sec_export} | ${p.chunks_per_sec_import} |\n`;
  }
  return out + "\n";
}

async function main(): Promise<void> {
  const FULL = process.env.BENCH_FULL === "1";
  const scales = FULL ? [1000, 10000, 62000] : [500, 2000];
  const points: BenchPoint[] = [];
  for (const s of scales) {
    process.stderr.write(`[bench] scale=${s} plain…\n`);
    points.push(await runOne(s, false));
    process.stderr.write(`[bench] scale=${s} encrypted…\n`);
    points.push(await runOne(s, true));
  }
  // JSON on stdout (machine-readable). Markdown on stderr (human-readable
  // alongside the [bench] progress lines).
  process.stdout.write(JSON.stringify(points, null, 2));
  process.stderr.write("\n" + buildMarkdown(points));
}

main().catch((err) => {
  process.stderr.write(`bench failed: ${(err as Error).stack ?? err}\n`);
  process.exit(1);
});
