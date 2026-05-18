/**
 * Public API for the A2 archive primitives.
 *
 * Importers should reach into specific modules for serializer-level types;
 * this barrel re-exports the most common surface used by the CLI/HTTP layers
 * that will land in T10-T13.
 */

export * from "./types.js";
export {
  packArchive,
  unpackArchive,
  listArchive,
  packArchiveStream,
} from "./format.js";
export {
  buildManifest,
  defaultEncryptionDisabled,
  canonicalize,
  writeManifest,
  parseManifest,
  manifestAADSource,
  manifestAADHash,
} from "./manifest.js";
export type { ManifestSeed } from "./manifest.js";
export {
  serializeChunks,
  parseChunks,
  serializeChunkRow,
  parseChunkRow,
  planChunkImport,
} from "./serializers/chunks.js";
export {
  serializeEmbeddings,
  parseEmbeddings,
} from "./serializers/embeddings.js";
export type { EmbeddingInput, EmbeddingsBundle } from "./serializers/embeddings.js";
export {
  serializeKgEntities,
  parseKgEntities,
  serializeKgRelations,
  parseKgRelations,
  planKgMerge,
} from "./serializers/kg.js";
export type { KgMergeResult } from "./serializers/kg.js";
export {
  serializeOpsAudit,
  parseOpsAudit,
  planOpsAuditImport,
} from "./serializers/ops_audit.js";
export {
  deriveKey,
  encryptBuffer,
  decryptBuffer,
  decryptArchiveFile,
  verifyCiphertextSha256,
  getPassphrase,
  buildEncryptionMetadata,
  SCRYPT_N,
  SCRYPT_R,
  SCRYPT_P,
  KEY_LEN,
  SALT_LEN,
  NONCE_LEN,
  TAG_LEN,
} from "./encryption.js";
export type { EncryptResult } from "./encryption.js";
export {
  canImport,
  migrationPath,
  migrateChunks,
  listMigrations,
} from "./migration.js";
export type { ImportabilityResult } from "./migration.js";
export {
  runExport,
  runImport,
  listArchiveEntries,
} from "./orchestrator.js";
export type {
  ExportRequest,
  ExportResult,
  ImportRequest,
  ImportResult,
  ProgressEvent,
} from "./orchestrator.js";
