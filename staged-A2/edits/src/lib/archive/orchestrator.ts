/**
 * Orchestrator — T10/T11/T13/T14 backing module.
 *
 * Wires the T1-T9 primitives (format/manifest/serializers/encryption/migration)
 * into two top-level operations: `runExport` and `runImport`. Framework-agnostic
 * — CLI, HTTP and MCP layers all funnel through here.
 *
 * Design constraints (D41 #2 + spec §3 §6):
 *   1. Encrypt-by-default — `unencrypted: true` is opt-out (CLI / HTTP / MCP
 *      surfaces enforce ACK separately).
 *   2. Passphrase never via argv — caller passes a string OR a `getPassphrase`
 *      thunk; this module never inspects `process.argv`.
 *   3. Streaming-friendly outputs — `runExport` returns a Buffer for now
 *      (T10/T11 pivot). The format module already exposes `packArchiveStream`
 *      for callers that need to pipe directly to disk.
 *   4. Progress events — caller passes an optional `onProgress` callback. Tests
 *      assert callback is invoked for each major phase.
 *   5. Cancellation — caller passes an optional `AbortSignal`. We abort
 *      between phases (no partial DB writes possible because we build a single
 *      tarball in memory before writing).
 *   6. ops_audit append-only — see T11 import path; merge/replace never DELETE
 *      audit rows (enforced by `planOpsAuditImport`).
 *   7. Manifest AAD invariant — re-built via `manifestAADHash` after encryption
 *      metadata is filled in, so decrypt side recomputes identically.
 */

import {
  ArchiveEntry,
  BadPassphraseError,
  ChunkRow,
  EncryptionMetadata,
  ImportMode,
  ImportStats,
  KgEntityRow,
  KgRelationRow,
  ManifestCounts,
  ManifestV1,
  OpsAuditRow,
  TamperedArchiveError,
} from "./types.js";
import { listArchive, packArchive, unpackArchive } from "./format.js";
import {
  buildManifest,
  manifestAADHash,
  parseManifest,
  writeManifest,
} from "./manifest.js";
import { serializeChunks, parseChunks, planChunkImport } from "./serializers/chunks.js";
import {
  serializeKgEntities,
  parseKgEntities,
  serializeKgRelations,
  parseKgRelations,
  planKgMerge,
} from "./serializers/kg.js";
import {
  serializeOpsAudit,
  parseOpsAudit,
  planOpsAuditImport,
} from "./serializers/ops_audit.js";
import {
  serializeEmbeddings,
  parseEmbeddings,
  EmbeddingInput,
  EmbeddingsBundle,
} from "./serializers/embeddings.js";
import {
  buildEncryptionMetadata,
  decryptArchiveFile,
  deriveKey,
  encryptBuffer,
} from "./encryption.js";
import { canImport, migrateChunks } from "./migration.js";
import { createHash, randomBytes } from "node:crypto";
import { SALT_LEN } from "./encryption.js";

// -- types --------------------------------------------------------------------

export interface ExportRequest {
  schema_version: number;
  source_hostname: string;
  source_nox_mem_version: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  sqlite_vec_version?: string | null;
  chunks: ChunkRow[];
  embeddings?: EmbeddingInput[];
  kg_entities?: KgEntityRow[];
  kg_relations?: KgRelationRow[];
  ops_audit?: OpsAuditRow[];
  filters?: { project?: string | null; since?: string | null; until?: string | null };
  /** D41 #2: default false (encrypt-by-default). */
  unencrypted?: boolean;
  /** Required if !unencrypted. */
  passphrase?: string;
  /** Cancellation. Aborts between phases. */
  signal?: AbortSignal;
  /** Progress callback. */
  onProgress?: (ev: ProgressEvent) => void;
}

export interface ExportResult {
  archive: Buffer;
  manifest: ManifestV1;
  /** Size of the packed (gzipped) archive in bytes. */
  size_bytes: number;
  /** Wall-clock ms for the full export. */
  duration_ms: number;
}

export interface ImportRequest {
  archive: Buffer;
  /** Required if archive is encrypted. */
  passphrase?: string;
  mode?: ImportMode;
  /** Skip actual writes (T11 --dry-run). */
  dry_run?: boolean;
  /** Skip integrity check + writes (T11 --verify). */
  verify_only?: boolean;
  /** Current DB schema version — used for migration planning. */
  current_schema_version: number;
  /** Existing rows in target DB (empty for clean imports). */
  existing?: {
    chunks?: ChunkRow[];
    kg_entities?: KgEntityRow[];
    kg_relations?: KgRelationRow[];
    ops_audit?: OpsAuditRow[];
  };
  signal?: AbortSignal;
  onProgress?: (ev: ProgressEvent) => void;
}

export interface ImportResult {
  manifest: ManifestV1;
  stats: {
    chunks: ImportStats;
    kg_entities: ImportStats;
    kg_relations: ImportStats;
    ops_audit: ImportStats;
    embeddings: { embedded: number; skipped: number };
  };
  /** Resolved rows ready to be persisted to a DB (caller's responsibility). */
  resolved: {
    chunks: ChunkRow[];
    kg_entities: KgEntityRow[];
    kg_relations: KgRelationRow[];
    ops_audit: OpsAuditRow[];
    embeddings: Map<number, EmbeddingInput>;
  };
  duration_ms: number;
  /** True when caller asked for verify_only or dry_run; no resolved.persist intended. */
  applied: boolean;
}

export type ProgressEvent =
  | { phase: "export.start"; total?: number }
  | { phase: "export.chunks"; emitted: number; total: number }
  | { phase: "export.embeddings"; emitted: number; total: number }
  | { phase: "export.kg"; emitted: number; total: number }
  | { phase: "export.encrypt"; files: number }
  | { phase: "export.pack"; entries: number }
  | { phase: "export.done"; size_bytes: number; duration_ms: number }
  | { phase: "import.start" }
  | { phase: "import.unpack"; entries: number }
  | { phase: "import.decrypt"; files: number }
  | { phase: "import.migrate"; from: number; to: number; steps: number }
  | { phase: "import.chunks"; imported: number; total: number }
  | { phase: "import.embeddings"; imported: number; total: number }
  | { phase: "import.kg"; imported: number; total: number }
  | { phase: "import.done"; duration_ms: number };

// -- export -------------------------------------------------------------------

const FILE_NAMES = {
  schema: "schema.sql",
  chunks: "chunks.jsonl",
  embeddings_bin: "embeddings.bin",
  embeddings_idx: "embeddings.idx",
  kg_entities: "kg_entities.jsonl",
  kg_relations: "kg_relations.jsonl",
  ops_audit: "ops_audit.jsonl",
} as const;

/** Encrypted-suffix variant. */
function encName(name: string): string {
  return `${name}.enc`;
}

export async function runExport(req: ExportRequest): Promise<ExportResult> {
  const started = Date.now();
  const emit = (ev: ProgressEvent): void => req.onProgress?.(ev);
  const checkAbort = (): void => {
    if (req.signal?.aborted) {
      throw new Error("Export cancelled");
    }
  };

  emit({ phase: "export.start", total: req.chunks.length });

  // --- Serialize each table -------------------------------------------------
  checkAbort();
  const chunksBuf = serializeChunks(req.chunks);
  emit({
    phase: "export.chunks",
    emitted: req.chunks.length,
    total: req.chunks.length,
  });

  checkAbort();
  let embeddingsBundle: EmbeddingsBundle | null = null;
  if (req.embeddings && req.embeddings.length > 0) {
    embeddingsBundle = serializeEmbeddings(req.embeddings);
    emit({
      phase: "export.embeddings",
      emitted: req.embeddings.length,
      total: req.embeddings.length,
    });
  }

  checkAbort();
  const kgEntitiesBuf = serializeKgEntities(req.kg_entities ?? []);
  const kgRelationsBuf = serializeKgRelations(req.kg_relations ?? []);
  emit({
    phase: "export.kg",
    emitted: (req.kg_entities?.length ?? 0) + (req.kg_relations?.length ?? 0),
    total: (req.kg_entities?.length ?? 0) + (req.kg_relations?.length ?? 0),
  });

  checkAbort();
  const opsAuditBuf = serializeOpsAudit(req.ops_audit ?? []);

  // --- Build counts + checksums ---------------------------------------------
  const counts: ManifestCounts = {
    chunks: req.chunks.length,
    embeddings: req.embeddings?.length ?? 0,
    kg_entities: req.kg_entities?.length ?? 0,
    kg_relations: req.kg_relations?.length ?? 0,
    ops_audit: req.ops_audit?.length ?? 0,
  };

  const checksums: Record<string, string> = {
    [FILE_NAMES.chunks]: sha256Hex(chunksBuf),
    [FILE_NAMES.kg_entities]: sha256Hex(kgEntitiesBuf),
    [FILE_NAMES.kg_relations]: sha256Hex(kgRelationsBuf),
    [FILE_NAMES.ops_audit]: sha256Hex(opsAuditBuf),
  };
  if (embeddingsBundle) {
    checksums[FILE_NAMES.embeddings_bin] = sha256Hex(embeddingsBundle.bin);
    checksums[FILE_NAMES.embeddings_idx] = sha256Hex(embeddingsBundle.idx);
  }

  const schemaSql = buildSchemaSql(req.schema_version);
  checksums[FILE_NAMES.schema] = sha256Hex(schemaSql);

  // --- Determine includes ---------------------------------------------------
  const includes: ManifestV1["includes"] = ["chunks"];
  if (embeddingsBundle) includes.push("embeddings");
  if ((req.kg_entities?.length ?? 0) + (req.kg_relations?.length ?? 0) > 0) {
    includes.push("kg");
  }
  if ((req.ops_audit?.length ?? 0) > 0) includes.push("audit");

  // --- Build manifest (no encryption yet) -----------------------------------
  let manifest = buildManifest({
    schema_version: req.schema_version,
    source_hostname: req.source_hostname,
    source_nox_mem_version: req.source_nox_mem_version,
    embedding_provider: req.embedding_provider,
    embedding_model: req.embedding_model,
    embedding_dim: req.embedding_dim,
    sqlite_vec_version: req.sqlite_vec_version ?? null,
    includes,
    filters: req.filters,
    counts,
    checksums,
  });

  const unencrypted = req.unencrypted === true;

  // --- Encryption (if requested) --------------------------------------------
  const archiveEntries: ArchiveEntry[] = [];
  // Schema + manifest go in plain — manifest LAST so AAD is stable
  archiveEntries.push({ name: FILE_NAMES.schema, content: schemaSql });

  if (unencrypted) {
    archiveEntries.push({ name: FILE_NAMES.chunks, content: chunksBuf });
    if (embeddingsBundle) {
      archiveEntries.push({
        name: FILE_NAMES.embeddings_bin,
        content: embeddingsBundle.bin,
      });
      archiveEntries.push({
        name: FILE_NAMES.embeddings_idx,
        content: embeddingsBundle.idx,
      });
    }
    archiveEntries.push({ name: FILE_NAMES.kg_entities, content: kgEntitiesBuf });
    archiveEntries.push({
      name: FILE_NAMES.kg_relations,
      content: kgRelationsBuf,
    });
    archiveEntries.push({ name: FILE_NAMES.ops_audit, content: opsAuditBuf });
  } else {
    checkAbort();
    if (typeof req.passphrase !== "string" || req.passphrase.length === 0) {
      throw new Error(
        "runExport: passphrase required (D41 #2 encrypt-by-default). " +
          "Pass `unencrypted: true` to opt out explicitly.",
      );
    }
    // AAD source = canonical manifest plaintext WITHOUT encryption metadata,
    // computed via manifestAADHash (see manifest.ts).
    const aad = manifestAADHash(manifest);
    const salt = randomBytes(SALT_LEN);
    const key = deriveKey(req.passphrase, salt);

    const filesToEncrypt: Array<{ name: string; buf: Buffer }> = [
      { name: FILE_NAMES.chunks, buf: chunksBuf },
      { name: FILE_NAMES.kg_entities, buf: kgEntitiesBuf },
      { name: FILE_NAMES.kg_relations, buf: kgRelationsBuf },
      { name: FILE_NAMES.ops_audit, buf: opsAuditBuf },
    ];
    if (embeddingsBundle) {
      filesToEncrypt.push({
        name: FILE_NAMES.embeddings_bin,
        buf: embeddingsBundle.bin,
      });
      filesToEncrypt.push({
        name: FILE_NAMES.embeddings_idx,
        buf: embeddingsBundle.idx,
      });
    }
    const encResults: Record<string, ReturnType<typeof encryptBuffer>> = {};
    for (const f of filesToEncrypt) {
      checkAbort();
      const res = encryptBuffer(f.buf, key, aad);
      encResults[encName(f.name)] = res;
      archiveEntries.push({ name: encName(f.name), content: res.ciphertext });
    }
    emit({ phase: "export.encrypt", files: filesToEncrypt.length });

    const encryptionMeta: EncryptionMetadata = buildEncryptionMetadata(
      salt.toString("base64"),
      encResults,
    );
    // CRITICAL: preserve created_at from the AAD-source manifest. Re-running
    // buildManifest() with no created_at would default to Date.now(), which
    // would change the AAD bytes between export-time and import-time and
    // break GCM auth tag verification. Memory feedback: AAD stability is the
    // entire reason manifest canonicalization exists (manifest.ts §AAD).
    manifest = buildManifest({
      schema_version: req.schema_version,
      source_hostname: req.source_hostname,
      source_nox_mem_version: req.source_nox_mem_version,
      embedding_provider: req.embedding_provider,
      embedding_model: req.embedding_model,
      embedding_dim: req.embedding_dim,
      sqlite_vec_version: req.sqlite_vec_version ?? null,
      includes,
      filters: req.filters,
      counts,
      checksums,
      encryption: encryptionMeta,
      created_at: manifest.created_at, // freeze
    });
  }

  // Manifest is ALWAYS plaintext (D41 #2)
  const manifestBuf = writeManifest(manifest);
  archiveEntries.push({ name: "manifest.json", content: manifestBuf });

  checkAbort();
  emit({ phase: "export.pack", entries: archiveEntries.length });
  const archive = packArchive(archiveEntries);
  const duration_ms = Date.now() - started;
  emit({ phase: "export.done", size_bytes: archive.length, duration_ms });

  return { archive, manifest, size_bytes: archive.length, duration_ms };
}

// -- import -------------------------------------------------------------------

export async function runImport(req: ImportRequest): Promise<ImportResult> {
  const started = Date.now();
  const emit = (ev: ProgressEvent): void => req.onProgress?.(ev);
  const checkAbort = (): void => {
    if (req.signal?.aborted) {
      throw new Error("Import cancelled");
    }
  };

  emit({ phase: "import.start" });
  const entries = unpackArchive(req.archive);
  emit({ phase: "import.unpack", entries: entries.length });

  const byName = new Map<string, Buffer>();
  for (const e of entries) byName.set(e.name, e.content);

  const manifestBuf = byName.get("manifest.json");
  if (!manifestBuf) {
    throw new Error("Import: manifest.json missing");
  }
  const manifest = parseManifest(manifestBuf);

  // Validate schema compatibility BEFORE any decryption / DB work.
  const importable = canImport(manifest.schema_version, req.current_schema_version);
  if (!importable.ok) {
    throw new Error(importable.reason);
  }

  // Decrypt (or pass through) per-table buffers.
  checkAbort();
  const encrypted = manifest.encryption.enabled === true;
  if (encrypted && (typeof req.passphrase !== "string" || req.passphrase.length === 0)) {
    throw new Error(
      "Import: archive is encrypted; pass passphrase. (See `NOX_IMPORT_PASSPHRASE` env or `--passphrase-env`.)",
    );
  }

  const aad = manifestAADHash(manifest);
  const pickBuf = (plainName: string): Buffer | undefined => {
    if (encrypted) {
      const ct = byName.get(encName(plainName));
      if (!ct) return undefined;
      return decryptArchiveFile({
        ciphertext: ct,
        fileName: encName(plainName),
        encryptionMetadata: manifest.encryption,
        passphrase: req.passphrase!,
        aad,
      });
    }
    return byName.get(plainName);
  };

  let encryptedFiles = 0;
  if (encrypted) {
    encryptedFiles = Object.keys(manifest.encryption.files).length;
    emit({ phase: "import.decrypt", files: encryptedFiles });
  }

  // Pull every table buffer through decrypt + checksum validation.
  const chunksBuf = pickBuf(FILE_NAMES.chunks);
  if (!chunksBuf) throw new Error("Import: chunks payload missing");
  validatePlaintextChecksum(chunksBuf, FILE_NAMES.chunks, manifest, encrypted);

  const kgEntitiesBuf = pickBuf(FILE_NAMES.kg_entities);
  if (kgEntitiesBuf) {
    validatePlaintextChecksum(kgEntitiesBuf, FILE_NAMES.kg_entities, manifest, encrypted);
  }
  const kgRelationsBuf = pickBuf(FILE_NAMES.kg_relations);
  if (kgRelationsBuf) {
    validatePlaintextChecksum(kgRelationsBuf, FILE_NAMES.kg_relations, manifest, encrypted);
  }
  const opsAuditBuf = pickBuf(FILE_NAMES.ops_audit);
  if (opsAuditBuf) {
    validatePlaintextChecksum(opsAuditBuf, FILE_NAMES.ops_audit, manifest, encrypted);
  }
  const embBin = pickBuf(FILE_NAMES.embeddings_bin);
  const embIdx = pickBuf(FILE_NAMES.embeddings_idx);
  if (embBin && embIdx) {
    validatePlaintextChecksum(embBin, FILE_NAMES.embeddings_bin, manifest, encrypted);
    validatePlaintextChecksum(embIdx, FILE_NAMES.embeddings_idx, manifest, encrypted);
  }

  if (req.verify_only) {
    // Stop here: integrity passed, no resolution / writes.
    return assembleVerifyResult(manifest, started);
  }

  // Parse buffers into structured rows.
  let chunks = parseChunks(chunksBuf);
  if (manifest.schema_version !== req.current_schema_version) {
    emit({
      phase: "import.migrate",
      from: manifest.schema_version,
      to: req.current_schema_version,
      steps: req.current_schema_version - manifest.schema_version,
    });
    chunks = migrateChunks(chunks, manifest.schema_version, req.current_schema_version);
  }
  const kgEntities = kgEntitiesBuf ? parseKgEntities(kgEntitiesBuf) : [];
  const kgRelations = kgRelationsBuf ? parseKgRelations(kgRelationsBuf) : [];
  const opsAudit = opsAuditBuf ? parseOpsAudit(opsAuditBuf) : [];
  const embeddings =
    embBin && embIdx ? parseEmbeddings(embBin, embIdx) : new Map<number, EmbeddingInput>();

  // Plan merges.
  const mode: ImportMode = req.mode ?? "merge";
  const existing = req.existing ?? {};
  const chunkPlan = planChunkImport(chunks, existing.chunks ?? [], mode);
  emit({
    phase: "import.chunks",
    imported: chunkPlan.inserted,
    total: chunks.length,
  });

  const kgPlan = planKgMerge(
    kgEntities,
    existing.kg_entities ?? [],
    kgRelations,
    existing.kg_relations ?? [],
  );
  emit({
    phase: "import.kg",
    imported: kgPlan.entities.inserted + kgPlan.relations.inserted,
    total: kgEntities.length + kgRelations.length,
  });

  const opsPlan = planOpsAuditImport(opsAudit, existing.ops_audit ?? []);

  const duration_ms = Date.now() - started;
  emit({ phase: "import.done", duration_ms });

  return {
    manifest,
    stats: {
      chunks: {
        inserted: chunkPlan.inserted,
        skipped: chunkPlan.skipped,
        merged: chunkPlan.merged,
        warnings: chunkPlan.warnings,
      },
      kg_entities: {
        inserted: kgPlan.entities.inserted,
        skipped: kgPlan.entities.skipped,
        merged: kgPlan.entities.merged,
        warnings: kgPlan.entities.warnings,
      },
      kg_relations: {
        inserted: kgPlan.relations.inserted,
        skipped: kgPlan.relations.skipped,
        merged: kgPlan.relations.merged,
        warnings: kgPlan.relations.warnings,
      },
      ops_audit: {
        inserted: opsPlan.inserted,
        skipped: opsPlan.skipped,
        merged: opsPlan.merged,
        warnings: opsPlan.warnings,
      },
      embeddings: { embedded: embeddings.size, skipped: 0 },
    },
    resolved: {
      chunks: chunkPlan.keep,
      kg_entities: kgPlan.entities.keep,
      kg_relations: kgPlan.relations.keep,
      ops_audit: opsPlan.keep,
      embeddings,
    },
    duration_ms,
    applied: req.dry_run !== true,
  };
}

/** Synchronous list of archive entries (open-toolchain DoD #4 hook). */
export function listArchiveEntries(archive: Buffer): string[] {
  return listArchive(archive);
}

// -- internals ---------------------------------------------------------------

function sha256Hex(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("hex");
}

function buildSchemaSql(schemaVersion: number): Buffer {
  // Minimal canonical DDL pointer — full CREATE TABLE text is produced by the
  // caller (T11 import wires it to better-sqlite3 in production). For staged
  // module, we emit a version header so downstream consumers know what to
  // expect.
  const body =
    `-- nox-mem schema version ${schemaVersion}\n` +
    `-- This is a header stub; full DDL is reproduced by the importer side.\n`;
  return Buffer.from(body, "utf8");
}

function validatePlaintextChecksum(
  buf: Buffer,
  name: string,
  manifest: ManifestV1,
  encrypted: boolean,
): void {
  const expected = manifest.checksums[name];
  if (!expected) {
    throw new Error(`Import: manifest missing checksum for ${name}`);
  }
  const got = sha256Hex(buf);
  if (got !== expected) {
    // For encrypted archives, this state is unreachable in practice — GCM
    // tag would have rejected first. But if it does happen, it's tamper.
    if (encrypted) {
      throw new TamperedArchiveError(
        `Plaintext checksum mismatch for ${name} after decrypt — archive tampered`,
      );
    }
    throw new TamperedArchiveError(
      `Plaintext checksum mismatch for ${name}: expected ${expected}, got ${got}`,
    );
  }
}

function assembleVerifyResult(
  manifest: ManifestV1,
  started: number,
): ImportResult {
  return {
    manifest,
    stats: {
      chunks: { inserted: 0, skipped: 0, merged: 0, warnings: [] },
      kg_entities: { inserted: 0, skipped: 0, merged: 0, warnings: [] },
      kg_relations: { inserted: 0, skipped: 0, merged: 0, warnings: [] },
      ops_audit: { inserted: 0, skipped: 0, merged: 0, warnings: [] },
      embeddings: { embedded: 0, skipped: 0 },
    },
    resolved: {
      chunks: [],
      kg_entities: [],
      kg_relations: [],
      ops_audit: [],
      embeddings: new Map(),
    },
    duration_ms: Date.now() - started,
    applied: false,
  };
}

// Re-exported convenience for callers that want the canonical error classes.
export { BadPassphraseError, TamperedArchiveError };
