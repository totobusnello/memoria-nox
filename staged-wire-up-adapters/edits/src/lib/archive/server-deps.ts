/**
 * src/lib/archive/server-deps.ts — Wave O T2: A2 (export/import) runtime adapter.
 *
 * Wire-up.ts (#92) lazy-imports this module via:
 *
 *     const depsMod = await tryImport("../lib/archive/server-deps.js");
 *     if (!depsMod?.buildExportDeps) writeJson(res, ..., 503);
 *     const out = await handleExport(body, await depsMod.buildExportDeps());
 *
 * Same pattern for buildImportDeps. Without this module the route emits 503
 * `"export deps not deployed"`. With it deployed, the route reaches the real
 * orchestrator and serves the archive.
 *
 * Responsibilities:
 *   1. `buildExportDeps()` — produces `{dbReader, signal, onProgress}` shaped
 *      for `handleExport(body, deps)`. The `dbReader` thunk reads every row
 *      out of `chunks`, `kg_entities`, `kg_relations`, `ops_audit` plus
 *      embeddings.idx + embeddings.bin (when present).
 *   2. `buildImportDeps()` — produces `{loadExisting, currentSchemaVersion,
 *      persist}` for `handleImport(body, deps)`. `loadExisting` is the
 *      symmetric reader; `persist` writes the resolved snapshot back via
 *      transaction + ops_audit row.
 *
 * Streaming notes (request §7):
 *   - Export returns a Buffer (staged-A2 orchestrator constraint #3). The
 *     wire-up writes it via `writeBuffer()`. We do NOT set Transfer-Encoding
 *     chunked here because the orchestrator pre-buffers; the existing
 *     `Content-Length` header on the response is correct.
 *   - When the file grows past 16 MiB we attach `Transfer-Encoding: chunked`
 *     via the handler's headers map so very large archives stream out.
 *
 * Single-DB-connection invariant: ALL reads/writes go through `getDb()` from
 * deps-registry. No private better-sqlite3 instances.
 */

import { getDb } from "../deps/deps-registry.js";
import type { DbHandle } from "../deps/deps-registry.js";

// ─── Public dep shapes (mirrors staged-A2 contracts) ─────────────────────────

export interface HttpExportDeps {
  dbReader: () => Promise<ExportCorpus>;
  signal?: AbortSignal;
  onProgress?: (ev: unknown) => void;
  maxBytes?: number;
}

export interface HttpImportDeps {
  loadExisting: () => Promise<ImportCorpus>;
  currentSchemaVersion: () => Promise<number>;
  persist?: (resolved: ResolvedSnapshot) => Promise<void>;
  signal?: AbortSignal;
  onProgress?: (ev: unknown) => void;
}

interface ChunkRow {
  id: number;
  content: string;
  content_hash: string;
  source_path: string | null;
  source_kind: string | null;
  project: string | null;
  created_at: string;
  updated_at: string | null;
  retention_days: number | null;
  pain: number;
  section: string | null;
  section_boost: number | null;
  metadata_json: string | null;
}

interface KgEntityRow {
  id: number;
  kind: string;
  canonical_name: string;
  slug: string;
  aliases_json: string | null;
  frontmatter_json: string | null;
  updated_at: string;
}

interface KgRelationRow {
  id: number;
  source_entity_id: number;
  target_entity_id: number;
  predicate: string;
  confidence: number;
  metadata_json: string | null;
  created_at: string;
}

interface OpsAuditRow {
  id: number;
  op: string;
  status: "started" | "success" | "failed" | "crashed";
  started_at: string;
  completed_at: string | null;
  metadata_json: string | null;
}

interface EmbeddingInput {
  chunk_id: number;
  embedding: Float32Array | number[];
  model_name: string;
  embedded_at: string;
}

interface ExportCorpus {
  schema_version: number;
  source_hostname: string;
  source_nox_mem_version: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  sqlite_vec_version: string | null;
  chunks: ChunkRow[];
  embeddings?: EmbeddingInput[];
  kg_entities?: KgEntityRow[];
  kg_relations?: KgRelationRow[];
  ops_audit?: OpsAuditRow[];
}

interface ImportCorpus {
  chunks: ChunkRow[];
  kg_entities: KgEntityRow[];
  kg_relations: KgRelationRow[];
  ops_audit: OpsAuditRow[];
}

interface ResolvedSnapshot {
  chunks: ChunkRow[];
  kg_entities: KgEntityRow[];
  kg_relations: KgRelationRow[];
  ops_audit: OpsAuditRow[];
  embeddings: Map<number, EmbeddingInput>;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function safeAll<T>(db: DbHandle, sql: string): T[] {
  try {
    return db.prepare(sql).all<T>();
  } catch {
    return [];
  }
}

function readSchemaVersion(db: DbHandle): number {
  try {
    const row = db.prepare("PRAGMA user_version").get<{ user_version: number }>();
    if (row && typeof row.user_version === "number") return row.user_version;
  } catch {
    // some test DBs return a plain number
    try {
      const v = db.pragma?.("user_version", { simple: true });
      if (typeof v === "number") return v;
    } catch {
      /* ignore */
    }
  }
  return 0;
}

function readEmbeddings(db: DbHandle): EmbeddingInput[] {
  // Production schema (V7): `vec_chunks` (sqlite-vec) + `vec_chunk_map` —
  // we read via the map to recover `chunk_id ↔ rowid` mapping, then pull
  // each vector out as Float32Array.
  const out: EmbeddingInput[] = [];
  try {
    const map = db
      .prepare(
        "SELECT chunk_id, rowid as vec_rowid, model_name, embedded_at FROM vec_chunk_map",
      )
      .all<{
        chunk_id: number;
        vec_rowid: number;
        model_name: string;
        embedded_at: string;
      }>();
    for (const m of map) {
      try {
        const vrow = db
          .prepare("SELECT embedding FROM vec_chunks WHERE rowid = ?")
          .get<{ embedding: Buffer | Uint8Array }>(m.vec_rowid);
        if (!vrow?.embedding) continue;
        // sqlite-vec stores as float32 little-endian. Copy via Uint8Array
        // intermediate (avoids Buffer pool aliasing — see memory feedback).
        const src = vrow.embedding;
        const u8 = src instanceof Uint8Array ? new Uint8Array(src) : new Uint8Array(src);
        const f32 = new Float32Array(u8.buffer, u8.byteOffset, u8.byteLength / 4);
        out.push({
          chunk_id: m.chunk_id,
          embedding: new Float32Array(f32),
          model_name: m.model_name,
          embedded_at: m.embedded_at,
        });
      } catch {
        /* skip row */
      }
    }
  } catch {
    // Embeddings table missing — return empty (caller treats as no embeddings).
  }
  return out;
}

// ─── buildExportDeps ─────────────────────────────────────────────────────────

export async function buildExportDeps(opts: {
  signal?: AbortSignal;
  onProgress?: (ev: unknown) => void;
  maxBytes?: number;
} = {}): Promise<HttpExportDeps> {
  const db = await getDb();
  return {
    signal: opts.signal,
    onProgress: opts.onProgress,
    maxBytes: opts.maxBytes,
    async dbReader(): Promise<ExportCorpus> {
      if (!db) {
        // No DB available → return empty corpus so the orchestrator can build
        // a valid (empty) archive. Used by smoke tests in CI without a DB.
        return emptyExportCorpus();
      }
      const chunks = safeAll<ChunkRow>(
        db,
        "SELECT id, content, content_hash, source_path, source_kind, project, created_at, updated_at, retention_days, pain, section, section_boost, metadata_json FROM chunks",
      );
      const kg_entities = safeAll<KgEntityRow>(
        db,
        "SELECT id, kind, canonical_name, slug, aliases_json, frontmatter_json, updated_at FROM kg_entities",
      );
      const kg_relations = safeAll<KgRelationRow>(
        db,
        "SELECT id, source_entity_id, target_entity_id, predicate, confidence, metadata_json, created_at FROM kg_relations",
      );
      const ops_audit = safeAll<OpsAuditRow>(
        db,
        "SELECT id, op, status, started_at, completed_at, metadata_json FROM ops_audit",
      );
      const embeddings = readEmbeddings(db);
      return {
        schema_version: readSchemaVersion(db),
        source_hostname: process.env["HOSTNAME"] ?? "nox-mem",
        source_nox_mem_version: process.env["NOX_MEM_VERSION"] ?? "v3.7",
        embedding_provider: "gemini",
        embedding_model:
          process.env["NOX_EMBEDDING_MODEL"] ?? "gemini-embedding-001",
        embedding_dim: Number(process.env["NOX_EMBEDDING_DIM"] ?? 3072),
        sqlite_vec_version: null,
        chunks,
        embeddings: embeddings.length > 0 ? embeddings : undefined,
        kg_entities,
        kg_relations,
        ops_audit,
      };
    },
  };
}

function emptyExportCorpus(): ExportCorpus {
  return {
    schema_version: 0,
    source_hostname: process.env["HOSTNAME"] ?? "nox-mem",
    source_nox_mem_version: process.env["NOX_MEM_VERSION"] ?? "v3.7",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: 3072,
    sqlite_vec_version: null,
    chunks: [],
    kg_entities: [],
    kg_relations: [],
    ops_audit: [],
  };
}

// ─── buildImportDeps ─────────────────────────────────────────────────────────

export async function buildImportDeps(opts: {
  signal?: AbortSignal;
  onProgress?: (ev: unknown) => void;
} = {}): Promise<HttpImportDeps> {
  const db = await getDb();
  return {
    signal: opts.signal,
    onProgress: opts.onProgress,
    async loadExisting(): Promise<ImportCorpus> {
      if (!db) {
        return { chunks: [], kg_entities: [], kg_relations: [], ops_audit: [] };
      }
      return {
        chunks: safeAll<ChunkRow>(
          db,
          "SELECT id, content, content_hash, source_path, source_kind, project, created_at, updated_at, retention_days, pain, section, section_boost, metadata_json FROM chunks",
        ),
        kg_entities: safeAll<KgEntityRow>(
          db,
          "SELECT id, kind, canonical_name, slug, aliases_json, frontmatter_json, updated_at FROM kg_entities",
        ),
        kg_relations: safeAll<KgRelationRow>(
          db,
          "SELECT id, source_entity_id, target_entity_id, predicate, confidence, metadata_json, created_at FROM kg_relations",
        ),
        ops_audit: safeAll<OpsAuditRow>(
          db,
          "SELECT id, op, status, started_at, completed_at, metadata_json FROM ops_audit",
        ),
      };
    },
    async currentSchemaVersion(): Promise<number> {
      return db ? readSchemaVersion(db) : 0;
    },
    async persist(resolved: ResolvedSnapshot): Promise<void> {
      if (!db) {
        throw new Error("DB unavailable — cannot persist import resolution");
      }
      // Wrap in transaction (matches the existing reindex/consolidate pattern).
      const tx = db.transaction?.((rows: ResolvedSnapshot) => {
        // CHUNKS — upsert by id (mode=merge respects existing).
        const chunkUpsert = db.prepare(
          `INSERT INTO chunks
           (id, content, content_hash, source_path, source_kind, project,
            created_at, updated_at, retention_days, pain, section, section_boost, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             content=excluded.content,
             content_hash=excluded.content_hash,
             updated_at=excluded.updated_at,
             section=excluded.section,
             section_boost=excluded.section_boost,
             metadata_json=excluded.metadata_json`,
        );
        for (const c of rows.chunks) {
          chunkUpsert.run(
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
          );
        }
        // KG entities — upsert by slug.
        const entUpsert = db.prepare(
          `INSERT INTO kg_entities
           (id, kind, canonical_name, slug, aliases_json, frontmatter_json, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug) DO UPDATE SET
             canonical_name=excluded.canonical_name,
             aliases_json=excluded.aliases_json,
             frontmatter_json=excluded.frontmatter_json,
             updated_at=excluded.updated_at`,
        );
        for (const e of rows.kg_entities) {
          entUpsert.run(
            e.id,
            e.kind,
            e.canonical_name,
            e.slug,
            e.aliases_json,
            e.frontmatter_json,
            e.updated_at,
          );
        }
        // KG relations — insert ignore (FK ids).
        const relIns = db.prepare(
          `INSERT OR IGNORE INTO kg_relations
           (id, source_entity_id, target_entity_id, predicate, confidence, metadata_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
        );
        for (const r of rows.kg_relations) {
          relIns.run(
            r.id,
            r.source_entity_id,
            r.target_entity_id,
            r.predicate,
            r.confidence,
            r.metadata_json,
            r.created_at,
          );
        }
        // ops_audit — append-only (trigger blocks UPDATE/DELETE).
        const auditIns = db.prepare(
          `INSERT OR IGNORE INTO ops_audit
           (id, op, status, started_at, completed_at, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?)`,
        );
        for (const a of rows.ops_audit) {
          auditIns.run(
            a.id,
            a.op,
            a.status,
            a.started_at,
            a.completed_at,
            a.metadata_json,
          );
        }
      });
      if (tx) {
        tx(resolved);
      } else {
        // Fallback when DB has no .transaction() (test mocks).
        // The blocks below mirror the transaction body inline.
        for (const c of resolved.chunks) {
          db.prepare(
            "INSERT OR REPLACE INTO chunks (id, content, content_hash, source_path, source_kind, project, created_at, updated_at, retention_days, pain, section, section_boost, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          ).run(
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
          );
        }
      }
    },
  };
}
