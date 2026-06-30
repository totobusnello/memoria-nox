/**
 * Shared TypeScript types for the A2 archive primitives.
 *
 * Spec: specs/2026-05-17-A2-export-import.md
 * Kickoff: specs/2026-05-18-A2-implementation-kickoff.md
 */

export const MANIFEST_FORMAT_VERSION = "1.0" as const;
export const ENCRYPTION_FORMAT_VERSION = 1 as const;

/** Files that can appear in an archive (excluding manifest itself). */
export type ArchiveEntryName =
  | "schema.sql"
  | "chunks.jsonl"
  | "chunks.jsonl.enc"
  | "embeddings.bin"
  | "embeddings.bin.enc"
  | "embeddings.idx"
  | "embeddings.idx.enc"
  | "kg_entities.jsonl"
  | "kg_entities.jsonl.enc"
  | "kg_relations.jsonl"
  | "kg_relations.jsonl.enc"
  | "ops_audit.jsonl"
  | "ops_audit.jsonl.enc"
  | string; // provenance/** paths, etc

export interface ArchiveEntry {
  /** Path inside the tarball. Use forward slashes regardless of OS. */
  name: string;
  /** Raw content. Buffer for binary, Uint8Array also accepted via Buffer.from. */
  content: Buffer;
  /** Optional Unix mtime (seconds). Defaults to now. */
  mtime?: number;
  /** Optional Unix mode. Defaults to 0o644 (file) or 0o755 (dir). */
  mode?: number;
}

export interface FileEncryptionMetadata {
  /** base64 12-byte GCM nonce */
  nonce_b64: string;
  /** base64 16-byte GCM auth tag */
  tag_b64: string;
  /** sha256 hex of the ciphertext (NOT plaintext) */
  ciphertext_sha256: string;
}

export interface EncryptionMetadata {
  enabled: boolean;
  /** Always "AES-256-GCM" when enabled, null when disabled */
  algorithm: "AES-256-GCM" | null;
  /** Always "scrypt" when enabled */
  kdf: "scrypt" | null;
  /** scrypt parameters — locked per D41 */
  kdf_params: { N: number; r: number; p: number } | null;
  /** base64 16-byte scrypt salt */
  kdf_salt_b64: string | null;
  /** Per-file encryption metadata; key is the file name inside the tar */
  files: Record<string, FileEncryptionMetadata>;
  /** Always "sha256(manifest_pre_encryption_bytes)" — documentation field */
  aad_source: "sha256(manifest_pre_encryption_bytes)" | null;
  /** Forward-compat: post-quantum cipher bump in v2 */
  format_version: typeof ENCRYPTION_FORMAT_VERSION;
}

export interface ManifestCounts {
  chunks: number;
  embeddings: number;
  kg_entities: number;
  kg_relations: number;
  ops_audit: number;
}

export interface ManifestFilters {
  project: string | null;
  since: string | null;
  until: string | null;
}

export interface ManifestV1 {
  format_version: typeof MANIFEST_FORMAT_VERSION;
  schema_version: number;
  created_at: string;
  source_hostname: string;
  source_nox_mem_version: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  sqlite_vec_version: string | null;
  includes: ("chunks" | "embeddings" | "kg" | "audit")[];
  filters: ManifestFilters;
  counts: ManifestCounts;
  /** sha256 hex of each file's PLAINTEXT (pre-encryption) contents. */
  checksums: Record<string, string>;
  encryption: EncryptionMetadata;
  /** Reserved for partial export warnings (KG dangling refs, etc). */
  integrity_warnings: string[];
}

/** Per-row chunk record. Matches schema v.29 (D41 baseline). */
export interface ChunkRow {
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

/** Per-row embedding entry in embeddings.idx (JSONL). */
export interface EmbeddingIndexEntry {
  chunk_id: number;
  offset: number;
  length: number;
  model_name: string;
  embedded_at: string;
}

/** KG entity row. */
export interface KgEntityRow {
  id: number;
  kind: string;
  canonical_name: string;
  slug: string;
  aliases_json: string | null;
  frontmatter_json: string | null;
  updated_at: string;
}

/** KG relation row. FK ids per memory feedback `kg_relations_uses_fk_ids`. */
export interface KgRelationRow {
  id: number;
  source_entity_id: number;
  target_entity_id: number;
  predicate: string;
  confidence: number;
  metadata_json: string | null;
  created_at: string;
}

/** ops_audit row (append-only). */
export interface OpsAuditRow {
  id: number;
  op: string;
  status: "started" | "success" | "failed" | "crashed";
  started_at: string;
  completed_at: string | null;
  metadata_json: string | null;
}

export type ImportMode = "merge" | "replace";

export interface ImportStats {
  inserted: number;
  skipped: number;
  merged: number;
  warnings: string[];
}

/** Sentinel errors. */
export class BadPassphraseError extends Error {
  constructor(message = "Bad passphrase or wrong key") {
    super(message);
    this.name = "BadPassphraseError";
  }
}

export class TamperedArchiveError extends Error {
  constructor(message = "Archive tampered — GCM tag mismatch") {
    super(message);
    this.name = "TamperedArchiveError";
  }
}

export class MissingAADError extends Error {
  constructor(message = "Missing or invalid AAD (manifest plaintext required)") {
    super(message);
    this.name = "MissingAADError";
  }
}

export class SchemaVersionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SchemaVersionError";
  }
}

export class ManifestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ManifestError";
  }
}

export class ArchiveFormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ArchiveFormatError";
  }
}
