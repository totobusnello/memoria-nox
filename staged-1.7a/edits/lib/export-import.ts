// export-import.ts — A2 Tier 1 + Tier 2: encrypted export/import bundle (AES-256-GCM)
//
// Q/A/P framework — Autonomy pillar. Centerpiece of "data is yours, portable".
//
// Tier 1 scope (original — preserved unchanged):
//   - Single bundle file (JSON envelope w/ base64 ciphertext)
//   - AES-256-GCM with scrypt KDF, random salt + IV per export
//   - AAD = sha256(canonical manifest header) — tamper detects manifest edits
//   - Single ciphertext over JSON of chunks + kg_entities + kg_relations
//   - Two import strategies: 'replace' (truncate then insert) and 'merge' (skip dups)
//   - Dry-run mode (returns counts without mutating target DB)
//
// Tier 2 scope (this file, V2 section):
//   - Per-table encryption — separate ciphertext per table (chunks, kg_entities,
//     kg_relations). Shared scrypt salt; per-table random IV / authTag / AAD.
//   - Selective export (subset of tables in bundle).
//   - Selective import (subset of tables out of bundle).
//   - Per-table tamper detection — flipping one ciphertext in one table fails that
//     table; subset import of the OTHERS still succeeds.
//   - Independent rekey-per-table possible (Tier 3 — formats compatible).
//   - Backward compatibility: importEncryptedAuto() auto-detects v1 vs v2 from
//     the bundle header and routes to the correct handler.
//
// Out of scope (deferred to Tier 3+):
//   - tar.gz container, schema migration, embeddings.bin, streaming, HTTP/MCP,
//     ops_audit serialization, KG predicate-aware merge, source files / provenance,
//     buffer-pool aliasing test for Float32Array (memory `[[buffer-pool-aliasing-in-typed-arrays]]`).
//
// Critical lessons baked in (memoria-nox/MEMORY.md):
//   - [[aad-bug-caught-by-integration-test]]  — chained checksum bugs invisible to unit tests;
//     ALWAYS write 2-instance roundtrip + tamper test
//   - [[no-secrets-in-git]]                   — passphrase must NEVER be in argv or source;
//     accept only via env var name (resolved at runtime)
//   - [[no-hardcoded-secrets]]                — same; CLI rejects bare --passphrase= flag
//
// Authors: A2-T1 implementation 2026-05-21 (Forge swarm)
//          A2-T2 extension     2026-05-21 (per-table encryption + backward compat)

import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes,
  scryptSync,
  timingSafeEqual,
} from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import type Database from "better-sqlite3";

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

/** Public envelope written to disk (JSON). */
export interface ExportBundle {
  /** Format version. Bumped on breaking layout changes. */
  version: 1;
  /** ISO 8601 timestamp of export (informational; AAD-bound). */
  created_at: string;
  /** Row counts of the inner payload (AAD-bound). */
  chunks_count: number;
  entities_count: number;
  relations_count: number;
  /** Always true in Tier 1 — encryption is mandatory (D41 #2). */
  encrypted: boolean;
  /** Cipher identifier (Tier 1 locked to AES-256-GCM). */
  cipher: "aes-256-gcm";
  /** KDF identifier (Tier 1 locked to scrypt). */
  key_derivation: "scrypt";
  /** scrypt parameters (AAD-bound — tamper would break key derivation). */
  kdf_params: { N: number; r: number; p: number; keylen: number };
  /** Random per-export, base64. */
  salt: string;
  /** Random 12 bytes per export, base64. */
  iv: string;
  /** AES-GCM auth tag, base64. */
  authTag: string;
  /** AAD = sha256(canonical(manifest header)), base64. */
  aad: string;
  /** Encrypted JSON payload, base64. */
  ciphertext: string;
}

/** Internal plaintext shape. Layered above DB rows. */
interface PlaintextPayload {
  chunks: Record<string, unknown>[];
  entities: Record<string, unknown>[];
  relations: Record<string, unknown>[];
}

/** What gets returned to the caller of exportEncrypted(). */
export interface ExportResult {
  bundlePath: string;
  chunksExported: number;
  entitiesExported: number;
  relationsExported: number;
  bundleBytes: number;
}

/** What gets returned to the caller of importEncrypted(). */
export interface ImportResult {
  chunksImported: number;
  entitiesImported: number;
  relationsImported: number;
  conflicts: ImportConflict[];
  dryRun: boolean;
}

export interface ImportConflict {
  table: "chunks" | "kg_entities" | "kg_relations";
  reason: "duplicate_content_hash" | "duplicate_unique_key" | "missing_fk";
  /** Stable identifier of the source-side row (e.g. content_hash, canonical_name). */
  key: string;
}

export interface ImportOptions {
  strategy: "replace" | "merge";
  dryRun?: boolean;
}

// ────────────────────────────────────────────────────────────────────────────
// Constants (security parameters — locked)
// ────────────────────────────────────────────────────────────────────────────

const CIPHER = "aes-256-gcm" as const;
const KDF_PARAMS = { N: 1 << 14, r: 8, p: 1, keylen: 32 } as const; // scrypt: ~150ms laptop
const SALT_BYTES = 16;
const IV_BYTES = 12; // GCM standard
const AUTH_TAG_BYTES = 16;
const MIN_PASSPHRASE_LEN = 8; // Tier 1 floor; Tier 2 will raise + entropy check

// ────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────

function canonicalJson(o: unknown): string {
  // Deterministic JSON: sort object keys recursively, no whitespace.
  // AAD stability depends on this — see [[aad-bug-caught-by-integration-test]].
  if (o === null || typeof o !== "object") return JSON.stringify(o);
  if (Array.isArray(o)) return "[" + o.map(canonicalJson).join(",") + "]";
  const obj = o as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalJson(obj[k])).join(",") + "}";
}

function sha256(buf: Buffer): Buffer {
  return createHash("sha256").update(buf).digest();
}

function deriveKey(passphrase: string, salt: Buffer): Buffer {
  if (passphrase.length < MIN_PASSPHRASE_LEN) {
    throw new ExportImportError(
      `Passphrase too short (min ${MIN_PASSPHRASE_LEN} chars). Use a strong passphrase.`,
      "WEAK_PASSPHRASE",
    );
  }
  return scryptSync(passphrase, salt, KDF_PARAMS.keylen, {
    N: KDF_PARAMS.N,
    r: KDF_PARAMS.r,
    p: KDF_PARAMS.p,
  });
}

/** Build the AAD-bound manifest header (everything except ciphertext + authTag). */
function buildAadHeader(args: {
  created_at: string;
  chunks_count: number;
  entities_count: number;
  relations_count: number;
  salt_b64: string;
  iv_b64: string;
}): Buffer {
  const header = {
    version: 1,
    created_at: args.created_at,
    chunks_count: args.chunks_count,
    entities_count: args.entities_count,
    relations_count: args.relations_count,
    encrypted: true,
    cipher: CIPHER,
    key_derivation: "scrypt",
    kdf_params: KDF_PARAMS,
    salt: args.salt_b64,
    iv: args.iv_b64,
  };
  return Buffer.from(canonicalJson(header), "utf8");
}

export class ExportImportError extends Error {
  constructor(
    message: string,
    public readonly code:
      | "WEAK_PASSPHRASE"
      | "TAMPERED_BUNDLE"
      | "BAD_PASSPHRASE"
      | "BAD_BUNDLE_FORMAT"
      | "UNSUPPORTED_VERSION"
      | "AAD_MISMATCH"
      | "BUNDLE_NOT_FOUND"
      // Tier 2 additions
      | "UNKNOWN_TABLE"
      | "TABLE_NOT_IN_BUNDLE",
  ) {
    super(message);
    this.name = "ExportImportError";
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Reads from DB (Tier 1: simple SELECT * — schema-aware columns)
// ────────────────────────────────────────────────────────────────────────────

function readAllChunks(db: Database.Database): Record<string, unknown>[] {
  // Schema v.29 columns preserved verbatim. SELECT * because Tier 1 ships full snapshot.
  // Drivers should ensure FTS5 + vec_chunks rebuild post-import (out of scope T1).
  const rows = db.prepare("SELECT * FROM chunks ORDER BY id").all() as Record<string, unknown>[];
  return rows;
}

function readAllEntities(db: Database.Database): Record<string, unknown>[] {
  const tableExists = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='kg_entities'")
    .get() as { name?: string } | undefined;
  if (!tableExists?.name) return [];
  return db.prepare("SELECT * FROM kg_entities ORDER BY id").all() as Record<string, unknown>[];
}

function readAllRelations(db: Database.Database): Record<string, unknown>[] {
  const tableExists = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='kg_relations'")
    .get() as { name?: string } | undefined;
  if (!tableExists?.name) return [];
  return db.prepare("SELECT * FROM kg_relations ORDER BY id").all() as Record<string, unknown>[];
}

// ────────────────────────────────────────────────────────────────────────────
// Public API: exportEncrypted
// ────────────────────────────────────────────────────────────────────────────

export function exportEncrypted(
  db: Database.Database,
  passphrase: string,
  outputPath: string,
): ExportResult {
  const chunks = readAllChunks(db);
  const entities = readAllEntities(db);
  const relations = readAllRelations(db);

  const payload: PlaintextPayload = { chunks, entities, relations };
  const plaintext = Buffer.from(canonicalJson(payload), "utf8");

  const salt = randomBytes(SALT_BYTES);
  const iv = randomBytes(IV_BYTES);
  const key = deriveKey(passphrase, salt);

  const created_at = new Date().toISOString();
  const aad = sha256(
    buildAadHeader({
      created_at,
      chunks_count: chunks.length,
      entities_count: entities.length,
      relations_count: relations.length,
      salt_b64: salt.toString("base64"),
      iv_b64: iv.toString("base64"),
    }),
  );

  const cipher = createCipheriv(CIPHER, key, iv, { authTagLength: AUTH_TAG_BYTES });
  cipher.setAAD(aad);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag = cipher.getAuthTag();

  const bundle: ExportBundle = {
    version: 1,
    created_at,
    chunks_count: chunks.length,
    entities_count: entities.length,
    relations_count: relations.length,
    encrypted: true,
    cipher: CIPHER,
    key_derivation: "scrypt",
    kdf_params: KDF_PARAMS,
    salt: salt.toString("base64"),
    iv: iv.toString("base64"),
    authTag: authTag.toString("base64"),
    aad: aad.toString("base64"),
    ciphertext: ciphertext.toString("base64"),
  };

  const serialized = JSON.stringify(bundle);
  writeFileSync(outputPath, serialized, { encoding: "utf8", mode: 0o600 });

  // Zero key material (best-effort — Node may keep copies; security note for Tier 2).
  key.fill(0);

  return {
    bundlePath: outputPath,
    chunksExported: chunks.length,
    entitiesExported: entities.length,
    relationsExported: relations.length,
    bundleBytes: Buffer.byteLength(serialized, "utf8"),
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Public API: importEncrypted
// ────────────────────────────────────────────────────────────────────────────

export function importEncrypted(
  db: Database.Database,
  passphrase: string,
  bundlePath: string,
  options: ImportOptions,
): ImportResult {
  let raw: string;
  try {
    raw = readFileSync(bundlePath, "utf8");
  } catch (e) {
    throw new ExportImportError(
      `Bundle not found or unreadable: ${bundlePath} (${(e as Error).message})`,
      "BUNDLE_NOT_FOUND",
    );
  }

  let bundle: ExportBundle;
  try {
    bundle = JSON.parse(raw) as ExportBundle;
  } catch (e) {
    throw new ExportImportError(
      `Bundle is not valid JSON: ${(e as Error).message}`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  if (bundle.version !== 1) {
    throw new ExportImportError(
      `Unsupported bundle version ${String(bundle.version)} (expected 1)`,
      "UNSUPPORTED_VERSION",
    );
  }
  if (bundle.cipher !== CIPHER || bundle.key_derivation !== "scrypt") {
    throw new ExportImportError(
      `Unsupported cipher/KDF combination: ${bundle.cipher}/${bundle.key_derivation}`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  const salt = Buffer.from(bundle.salt, "base64");
  const iv = Buffer.from(bundle.iv, "base64");
  const authTag = Buffer.from(bundle.authTag, "base64");
  const claimedAad = Buffer.from(bundle.aad, "base64");
  const ciphertext = Buffer.from(bundle.ciphertext, "base64");

  if (salt.length !== SALT_BYTES) {
    throw new ExportImportError(
      `Invalid salt length ${salt.length} (expected ${SALT_BYTES})`,
      "BAD_BUNDLE_FORMAT",
    );
  }
  if (iv.length !== IV_BYTES) {
    throw new ExportImportError(
      `Invalid IV length ${iv.length} (expected ${IV_BYTES})`,
      "BAD_BUNDLE_FORMAT",
    );
  }
  if (authTag.length !== AUTH_TAG_BYTES) {
    throw new ExportImportError(
      `Invalid auth tag length ${authTag.length} (expected ${AUTH_TAG_BYTES})`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  // Recompute AAD locally from the header fields. If any header field was tampered
  // (e.g. chunks_count flipped), the recomputed AAD will diverge from the claimed
  // AAD, and we MUST reject before even attempting decryption.
  const recomputedAad = sha256(
    buildAadHeader({
      created_at: bundle.created_at,
      chunks_count: bundle.chunks_count,
      entities_count: bundle.entities_count,
      relations_count: bundle.relations_count,
      salt_b64: bundle.salt,
      iv_b64: bundle.iv,
    }),
  );

  if (
    recomputedAad.length !== claimedAad.length ||
    !timingSafeEqual(recomputedAad, claimedAad)
  ) {
    throw new ExportImportError(
      "Bundle manifest has been tampered with (AAD mismatch). Aborting import.",
      "AAD_MISMATCH",
    );
  }

  const key = deriveKey(passphrase, salt);
  let plaintextBuf: Buffer;
  try {
    const decipher = createDecipheriv(CIPHER, key, iv, { authTagLength: AUTH_TAG_BYTES });
    decipher.setAuthTag(authTag);
    decipher.setAAD(recomputedAad);
    plaintextBuf = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  } catch (e) {
    key.fill(0);
    // Node throws on auth tag mismatch with a generic "Unsupported state or unable
    // to authenticate data" — re-wrap as our explicit error code. Could be a wrong
    // passphrase OR a flipped ciphertext byte; both surface identically (correct —
    // we should not leak which one to an attacker).
    throw new ExportImportError(
      `Decryption failed (bad passphrase or tampered ciphertext): ${(e as Error).message}`,
      "TAMPERED_BUNDLE",
    );
  } finally {
    key.fill(0);
  }

  let payload: PlaintextPayload;
  try {
    payload = JSON.parse(plaintextBuf.toString("utf8")) as PlaintextPayload;
  } catch (e) {
    throw new ExportImportError(
      `Decrypted payload is not valid JSON (likely corrupted): ${(e as Error).message}`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  // Cross-check declared counts vs actual decrypted payload — defense in depth.
  if (
    payload.chunks.length !== bundle.chunks_count ||
    payload.entities.length !== bundle.entities_count ||
    payload.relations.length !== bundle.relations_count
  ) {
    throw new ExportImportError(
      `Decrypted payload counts do not match manifest header ` +
        `(chunks: ${payload.chunks.length}/${bundle.chunks_count}, ` +
        `entities: ${payload.entities.length}/${bundle.entities_count}, ` +
        `relations: ${payload.relations.length}/${bundle.relations_count})`,
      "TAMPERED_BUNDLE",
    );
  }

  return applyImport(db, payload, options);
}

// ────────────────────────────────────────────────────────────────────────────
// Apply (transaction): replace | merge | dry-run
// ────────────────────────────────────────────────────────────────────────────

function applyImport(
  db: Database.Database,
  payload: PlaintextPayload,
  options: ImportOptions,
): ImportResult {
  const conflicts: ImportConflict[] = [];

  // Compute conflicts up front (read-only) — works for dry-run AND for the
  // merge branch below (we reuse the result rather than scanning twice).
  if (options.strategy === "merge") {
    detectMergeConflicts(db, payload, conflicts);
  }

  if (options.dryRun) {
    const chunksWouldImport = options.strategy === "replace"
      ? payload.chunks.length
      : payload.chunks.length - conflicts.filter((c) => c.table === "chunks").length;
    const entitiesWouldImport = options.strategy === "replace"
      ? payload.entities.length
      : payload.entities.length - conflicts.filter((c) => c.table === "kg_entities").length;
    const relationsWouldImport = options.strategy === "replace"
      ? payload.relations.length
      : payload.relations.length - conflicts.filter((c) => c.table === "kg_relations").length;
    return {
      chunksImported: chunksWouldImport,
      entitiesImported: entitiesWouldImport,
      relationsImported: relationsWouldImport,
      conflicts,
      dryRun: true,
    };
  }

  // Wrap mutations in a single transaction — atomicity in case of mid-insert failure.
  const tx = db.transaction(() => {
    if (options.strategy === "replace") {
      // Tier 1: scoped to user-data tables only. ops_audit is preserved (append-only).
      // FTS5 + sqlite-vec indices should be rebuilt by caller post-import.
      db.exec("DELETE FROM kg_relations;");
      db.exec("DELETE FROM kg_entities;");
      db.exec("DELETE FROM chunks;");
    }

    const chunksImported = insertRows(db, "chunks", payload.chunks, options.strategy, conflicts);
    const entitiesImported = insertRows(
      db,
      "kg_entities",
      payload.entities,
      options.strategy,
      conflicts,
    );
    const relationsImported = insertRows(
      db,
      "kg_relations",
      payload.relations,
      options.strategy,
      conflicts,
    );

    return { chunksImported, entitiesImported, relationsImported };
  });

  const result = tx();
  return { ...result, conflicts, dryRun: false };
}

function detectMergeConflicts(
  db: Database.Database,
  payload: PlaintextPayload,
  conflicts: ImportConflict[],
): void {
  // chunks: dedup by content_hash if present; otherwise fall back to id.
  const chunkColumns = getTableColumns(db, "chunks");
  if (chunkColumns.includes("content_hash")) {
    const stmt = db.prepare("SELECT 1 FROM chunks WHERE content_hash = ? LIMIT 1");
    for (const c of payload.chunks) {
      const hash = c.content_hash as string | undefined;
      if (hash && stmt.get(hash)) {
        conflicts.push({ table: "chunks", reason: "duplicate_content_hash", key: hash });
      }
    }
  }

  // kg_entities: dedup by (canonical_name, type) if those columns exist; else id.
  const entityColumns = getTableColumns(db, "kg_entities");
  if (entityColumns.includes("canonical_name") && entityColumns.includes("type")) {
    const stmt = db.prepare(
      "SELECT 1 FROM kg_entities WHERE canonical_name = ? AND type = ? LIMIT 1",
    );
    for (const e of payload.entities) {
      const cn = e.canonical_name as string | undefined;
      const ty = e.type as string | undefined;
      if (cn && ty && stmt.get(cn, ty)) {
        conflicts.push({
          table: "kg_entities",
          reason: "duplicate_unique_key",
          key: `${cn}::${ty}`,
        });
      }
    }
  }

  // kg_relations: dedup by (source_entity_id, predicate, target_entity_id) tuple.
  const relColumns = getTableColumns(db, "kg_relations");
  if (
    relColumns.includes("source_entity_id") &&
    relColumns.includes("target_entity_id") &&
    relColumns.includes("predicate")
  ) {
    const stmt = db.prepare(
      "SELECT 1 FROM kg_relations WHERE source_entity_id = ? AND predicate = ? AND target_entity_id = ? LIMIT 1",
    );
    for (const r of payload.relations) {
      const s = r.source_entity_id;
      const p = r.predicate as string | undefined;
      const t = r.target_entity_id;
      if (s != null && p && t != null && stmt.get(s, p, t)) {
        conflicts.push({
          table: "kg_relations",
          reason: "duplicate_unique_key",
          key: `${String(s)}::${p}::${String(t)}`,
        });
      }
    }
  }
}

function getTableColumns(db: Database.Database, table: string): string[] {
  const rows = db.pragma(`table_info(${table})`) as { name: string }[];
  return rows.map((r) => r.name);
}

function insertRows(
  db: Database.Database,
  table: "chunks" | "kg_entities" | "kg_relations",
  rows: Record<string, unknown>[],
  strategy: "replace" | "merge",
  conflicts: ImportConflict[],
): number {
  if (rows.length === 0) return 0;

  const tableColumns = new Set(getTableColumns(db, table));
  if (tableColumns.size === 0) return 0; // table absent in target (e.g. kg_* not yet built)

  // In merge mode, drop the source-side PK 'id' column so SQLite auto-assigns
  // a fresh id in the target. Carrying source ids causes spurious PK
  // collisions against unrelated rows already in target — the IGNORE would
  // then silently drop them and undercount.
  // In replace mode we truncated the table, so source ids are safe to keep
  // (and preserving them helps FK references inside kg_relations resolve).
  const dropId = strategy === "merge";

  // Conflict keys — used in merge mode to skip dups by semantic unique key.
  const conflictKeys = new Set(
    conflicts.filter((c) => c.table === table).map((c) => c.key),
  );

  let inserted = 0;
  for (const row of rows) {
    if (strategy === "merge") {
      const key = conflictKeyFor(table, row);
      if (key && conflictKeys.has(key)) continue;
    }

    const cols: string[] = [];
    const vals: unknown[] = [];
    for (const k of Object.keys(row)) {
      if (!tableColumns.has(k)) continue; // drop columns absent in target schema
      if (dropId && k === "id") continue; // let SQLite auto-assign
      cols.push(k);
      vals.push(row[k]);
    }
    if (cols.length === 0) continue;

    const placeholders = cols.map(() => "?").join(",");
    const colList = cols.map((c) => `"${c}"`).join(",");

    // OR IGNORE handles the case where INSERT collides on an existing unique
    // index (e.g. another agent inserted the same content_hash mid-import).
    // In strategy='replace' we already truncated, so no collisions expected.
    const sql = `INSERT OR IGNORE INTO ${table} (${colList}) VALUES (${placeholders})`;
    const info = db.prepare(sql).run(...(vals as never[]));
    if (info.changes > 0) inserted++;
  }

  return inserted;
}

function conflictKeyFor(
  table: "chunks" | "kg_entities" | "kg_relations",
  row: Record<string, unknown>,
): string | null {
  if (table === "chunks") {
    const h = row.content_hash;
    return typeof h === "string" ? h : null;
  }
  if (table === "kg_entities") {
    const cn = row.canonical_name;
    const ty = row.type;
    if (typeof cn === "string" && typeof ty === "string") return `${cn}::${ty}`;
    return null;
  }
  // kg_relations
  const s = row.source_entity_id;
  const p = row.predicate;
  const t = row.target_entity_id;
  if (s != null && typeof p === "string" && t != null) {
    return `${String(s)}::${p}::${String(t)}`;
  }
  return null;
}

// ============================================================================
// TIER 2 — Per-table encryption (V2 bundle format)
// ============================================================================
//
// V2 envelope layout:
// {
//   "version": 2,
//   "created_at": "<iso8601>",          // AAD-bound per-table
//   "encrypted": true,
//   "cipher": "aes-256-gcm",
//   "key_derivation": "scrypt",
//   "kdf_params": { N, r, p, keylen },   // shared (single passphrase → single key)
//   "salt": "<b64>",                     // shared salt across tables
//   "tables": {
//     "chunks":       { rows_count, iv, authTag, aad, ciphertext },
//     "kg_entities":  { rows_count, iv, authTag, aad, ciphertext },
//     "kg_relations": { rows_count, iv, authTag, aad, ciphertext }
//   }
// }
//
// Per-table AAD = sha256(canonical({
//   version: 2,
//   created_at,                  // shared timestamp, but locked per table
//   table_name,                  // ← prevents swapping ciphertexts across tables
//   rows_count,                  // ← prevents removing rows then padding
//   kdf_params,                  // ← prevents downgrade attack
//   salt_b64,                    // ← shared salt also AAD-bound
//   iv_b64                       // ← per-table IV
// }))
//
// Key reuse safety: same key + DIFFERENT IV per table = secure (GCM requires
// unique nonce per encryption with a given key — which we have, since IVs are
// freshly randomBytes(12) per table).

const SUPPORTED_TABLES = ["chunks", "kg_entities", "kg_relations"] as const;
type SupportedTable = (typeof SUPPORTED_TABLES)[number];

function isSupportedTable(name: string): name is SupportedTable {
  return (SUPPORTED_TABLES as readonly string[]).includes(name);
}

/** V2 envelope written to disk. */
export interface ExportBundleV2 {
  version: 2;
  created_at: string;
  encrypted: true;
  cipher: "aes-256-gcm";
  key_derivation: "scrypt";
  kdf_params: { N: number; r: number; p: number; keylen: number };
  salt: string; // shared base64
  tables: Record<string, ExportTableEnvelopeV2>;
}

export interface ExportTableEnvelopeV2 {
  rows_count: number;
  iv: string;
  authTag: string;
  aad: string;
  ciphertext: string;
}

export interface ExportV2Options {
  /** Optional subset of tables to export. Default: all of SUPPORTED_TABLES. */
  tables?: readonly string[];
}

export interface ExportV2Result {
  bundlePath: string;
  tablesExported: { name: string; rows: number }[];
  bundleBytes: number;
}

export interface ImportV2Options {
  strategy: "replace" | "merge";
  /** Optional subset to import. Default: all tables present in bundle. */
  tables?: readonly string[];
  dryRun?: boolean;
}

export interface ImportV2Result {
  tablesImported: { name: string; rows: number; conflicts: number }[];
  conflicts: ImportConflict[];
  dryRun: boolean;
}

function readAllOfTable(db: Database.Database, table: SupportedTable): Record<string, unknown>[] {
  if (table === "chunks") return readAllChunks(db);
  if (table === "kg_entities") return readAllEntities(db);
  return readAllRelations(db); // kg_relations
}

/** Build per-table AAD header (V2). */
function buildAadHeaderV2(args: {
  created_at: string;
  table_name: string;
  rows_count: number;
  salt_b64: string;
  iv_b64: string;
}): Buffer {
  const header = {
    version: 2,
    created_at: args.created_at,
    table_name: args.table_name,
    rows_count: args.rows_count,
    cipher: CIPHER,
    key_derivation: "scrypt",
    kdf_params: KDF_PARAMS,
    salt: args.salt_b64,
    iv: args.iv_b64,
  };
  return Buffer.from(canonicalJson(header), "utf8");
}

// ────────────────────────────────────────────────────────────────────────────
// Public API: exportEncryptedV2 (per-table encryption)
// ────────────────────────────────────────────────────────────────────────────

export function exportEncryptedV2(
  db: Database.Database,
  passphrase: string,
  outputPath: string,
  options?: ExportV2Options,
): ExportV2Result {
  // Validate requested table subset.
  const requested = options?.tables ?? SUPPORTED_TABLES;
  for (const t of requested) {
    if (!isSupportedTable(t)) {
      throw new ExportImportError(
        `Unknown table '${t}' for V2 export. Supported: ${SUPPORTED_TABLES.join(", ")}`,
        "UNKNOWN_TABLE",
      );
    }
  }
  // De-dup while preserving order.
  const seen = new Set<string>();
  const tables: SupportedTable[] = [];
  for (const t of requested) {
    if (!seen.has(t)) {
      seen.add(t);
      tables.push(t as SupportedTable);
    }
  }

  // Shared KDF: single passphrase → single key, derived once.
  const salt = randomBytes(SALT_BYTES);
  const key = deriveKey(passphrase, salt);
  const salt_b64 = salt.toString("base64");
  const created_at = new Date().toISOString();

  const envelopes: Record<string, ExportTableEnvelopeV2> = {};
  const tablesExported: { name: string; rows: number }[] = [];

  try {
    for (const table of tables) {
      const rows = readAllOfTable(db, table);
      const plaintext = Buffer.from(canonicalJson(rows), "utf8");

      const iv = randomBytes(IV_BYTES); // unique IV per table — mandatory for GCM
      const iv_b64 = iv.toString("base64");

      const aad = sha256(
        buildAadHeaderV2({
          created_at,
          table_name: table,
          rows_count: rows.length,
          salt_b64,
          iv_b64,
        }),
      );

      const cipher = createCipheriv(CIPHER, key, iv, { authTagLength: AUTH_TAG_BYTES });
      cipher.setAAD(aad);
      const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
      const authTag = cipher.getAuthTag();

      envelopes[table] = {
        rows_count: rows.length,
        iv: iv_b64,
        authTag: authTag.toString("base64"),
        aad: aad.toString("base64"),
        ciphertext: ciphertext.toString("base64"),
      };
      tablesExported.push({ name: table, rows: rows.length });
    }
  } finally {
    key.fill(0);
  }

  const bundle: ExportBundleV2 = {
    version: 2,
    created_at,
    encrypted: true,
    cipher: CIPHER,
    key_derivation: "scrypt",
    kdf_params: KDF_PARAMS,
    salt: salt_b64,
    tables: envelopes,
  };

  const serialized = JSON.stringify(bundle);
  writeFileSync(outputPath, serialized, { encoding: "utf8", mode: 0o600 });

  return {
    bundlePath: outputPath,
    tablesExported,
    bundleBytes: Buffer.byteLength(serialized, "utf8"),
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Public API: importEncryptedV2 (per-table decryption + apply)
// ────────────────────────────────────────────────────────────────────────────

export function importEncryptedV2(
  db: Database.Database,
  passphrase: string,
  bundlePath: string,
  options: ImportV2Options,
): ImportV2Result {
  let raw: string;
  try {
    raw = readFileSync(bundlePath, "utf8");
  } catch (e) {
    throw new ExportImportError(
      `Bundle not found or unreadable: ${bundlePath} (${(e as Error).message})`,
      "BUNDLE_NOT_FOUND",
    );
  }

  let bundle: ExportBundleV2;
  try {
    bundle = JSON.parse(raw) as ExportBundleV2;
  } catch (e) {
    throw new ExportImportError(
      `Bundle is not valid JSON: ${(e as Error).message}`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  if (bundle.version !== 2) {
    throw new ExportImportError(
      `importEncryptedV2 expected version 2, got ${String(bundle.version)}. ` +
        `Use importEncryptedAuto() for backward compat or importEncrypted() for v1.`,
      "UNSUPPORTED_VERSION",
    );
  }
  if (bundle.cipher !== CIPHER || bundle.key_derivation !== "scrypt") {
    throw new ExportImportError(
      `Unsupported cipher/KDF combination: ${bundle.cipher}/${bundle.key_derivation}`,
      "BAD_BUNDLE_FORMAT",
    );
  }
  if (!bundle.tables || typeof bundle.tables !== "object") {
    throw new ExportImportError(
      `V2 bundle missing 'tables' map`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  const salt = Buffer.from(bundle.salt, "base64");
  if (salt.length !== SALT_BYTES) {
    throw new ExportImportError(
      `Invalid salt length ${salt.length} (expected ${SALT_BYTES})`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  // Determine which tables to import.
  const tablesInBundle = Object.keys(bundle.tables);
  const requested = options.tables ?? tablesInBundle;
  for (const t of requested) {
    if (!isSupportedTable(t)) {
      throw new ExportImportError(
        `Unknown table '${t}' requested for V2 import. Supported: ${SUPPORTED_TABLES.join(", ")}`,
        "UNKNOWN_TABLE",
      );
    }
    if (!tablesInBundle.includes(t)) {
      throw new ExportImportError(
        `Table '${t}' not present in bundle (have: ${tablesInBundle.join(", ") || "none"})`,
        "TABLE_NOT_IN_BUNDLE",
      );
    }
  }
  const seen = new Set<string>();
  const targetTables: SupportedTable[] = [];
  for (const t of requested) {
    if (!seen.has(t)) {
      seen.add(t);
      targetTables.push(t as SupportedTable);
    }
  }

  // Decrypt each requested table independently.
  const key = deriveKey(passphrase, salt);
  const decrypted: Partial<Record<SupportedTable, Record<string, unknown>[]>> = {};

  try {
    for (const table of targetTables) {
      const env = bundle.tables[table];
      if (!env) {
        throw new ExportImportError(
          `Table '${table}' missing envelope in bundle (internal error)`,
          "BAD_BUNDLE_FORMAT",
        );
      }

      const iv = Buffer.from(env.iv, "base64");
      const authTag = Buffer.from(env.authTag, "base64");
      const claimedAad = Buffer.from(env.aad, "base64");
      const ciphertext = Buffer.from(env.ciphertext, "base64");

      if (iv.length !== IV_BYTES) {
        throw new ExportImportError(
          `Invalid IV length ${iv.length} for table '${table}' (expected ${IV_BYTES})`,
          "BAD_BUNDLE_FORMAT",
        );
      }
      if (authTag.length !== AUTH_TAG_BYTES) {
        throw new ExportImportError(
          `Invalid auth tag length ${authTag.length} for table '${table}' (expected ${AUTH_TAG_BYTES})`,
          "BAD_BUNDLE_FORMAT",
        );
      }

      // Recompute AAD from the table envelope's claimed counts + table name + shared salt.
      const recomputedAad = sha256(
        buildAadHeaderV2({
          created_at: bundle.created_at,
          table_name: table,
          rows_count: env.rows_count,
          salt_b64: bundle.salt,
          iv_b64: env.iv,
        }),
      );

      if (
        recomputedAad.length !== claimedAad.length ||
        !timingSafeEqual(recomputedAad, claimedAad)
      ) {
        throw new ExportImportError(
          `Bundle table '${table}' has tampered header (AAD mismatch). Aborting import.`,
          "AAD_MISMATCH",
        );
      }

      let plaintextBuf: Buffer;
      try {
        const decipher = createDecipheriv(CIPHER, key, iv, { authTagLength: AUTH_TAG_BYTES });
        decipher.setAuthTag(authTag);
        decipher.setAAD(recomputedAad);
        plaintextBuf = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
      } catch (e) {
        throw new ExportImportError(
          `Decryption failed for table '${table}' (bad passphrase or tampered ciphertext): ${(e as Error).message}`,
          "TAMPERED_BUNDLE",
        );
      }

      let rows: Record<string, unknown>[];
      try {
        rows = JSON.parse(plaintextBuf.toString("utf8")) as Record<string, unknown>[];
      } catch (e) {
        throw new ExportImportError(
          `Decrypted payload for table '${table}' is not valid JSON (likely corrupted): ${(e as Error).message}`,
          "BAD_BUNDLE_FORMAT",
        );
      }

      if (rows.length !== env.rows_count) {
        throw new ExportImportError(
          `Decrypted row count for table '${table}' does not match envelope ` +
            `(${rows.length}/${env.rows_count})`,
          "TAMPERED_BUNDLE",
        );
      }

      decrypted[table] = rows;
    }
  } finally {
    key.fill(0);
  }

  return applyImportV2(db, decrypted, targetTables, options);
}

// ────────────────────────────────────────────────────────────────────────────
// Apply (V2): per-table with subset awareness — no truncate of tables outside subset
// ────────────────────────────────────────────────────────────────────────────

function applyImportV2(
  db: Database.Database,
  decrypted: Partial<Record<SupportedTable, Record<string, unknown>[]>>,
  targetTables: SupportedTable[],
  options: ImportV2Options,
): ImportV2Result {
  const conflicts: ImportConflict[] = [];

  // Compute merge conflicts up front per table (read-only).
  if (options.strategy === "merge") {
    const subsetPayload: PlaintextPayload = {
      chunks: decrypted.chunks ?? [],
      entities: decrypted.kg_entities ?? [],
      relations: decrypted.kg_relations ?? [],
    };
    // Only detect conflicts for tables actually being imported.
    if (targetTables.includes("chunks")) {
      detectMergeConflictsTable(db, "chunks", subsetPayload.chunks, conflicts);
    }
    if (targetTables.includes("kg_entities")) {
      detectMergeConflictsTable(db, "kg_entities", subsetPayload.entities, conflicts);
    }
    if (targetTables.includes("kg_relations")) {
      detectMergeConflictsTable(db, "kg_relations", subsetPayload.relations, conflicts);
    }
  }

  // Dry-run: report what would happen, mutate nothing.
  if (options.dryRun) {
    const tablesImported = targetTables.map((t) => {
      const rows = decrypted[t] ?? [];
      const tableConflicts = conflicts.filter((c) => c.table === t).length;
      const wouldImport = options.strategy === "replace"
        ? rows.length
        : rows.length - tableConflicts;
      return { name: t, rows: wouldImport, conflicts: tableConflicts };
    });
    return { tablesImported, conflicts, dryRun: true };
  }

  // Mutating path — single transaction.
  const tx = db.transaction(() => {
    const out: { name: string; rows: number; conflicts: number }[] = [];

    if (options.strategy === "replace") {
      // Per-table replace: only truncate tables IN the subset.
      // Critical: tables outside the subset are NOT touched (selective restore).
      // Ordering matters for FK: relations → entities → chunks (delete leaves first).
      if (targetTables.includes("kg_relations")) db.exec("DELETE FROM kg_relations;");
      if (targetTables.includes("kg_entities")) db.exec("DELETE FROM kg_entities;");
      if (targetTables.includes("chunks")) db.exec("DELETE FROM chunks;");
    }

    // Insert in dependency order: chunks → kg_entities → kg_relations.
    // Only tables in subset are inserted.
    const insertOrder: SupportedTable[] = ["chunks", "kg_entities", "kg_relations"];
    for (const table of insertOrder) {
      if (!targetTables.includes(table)) continue;
      const rows = decrypted[table] ?? [];
      const inserted = insertRows(db, table, rows, options.strategy, conflicts);
      const tableConflicts = conflicts.filter((c) => c.table === table).length;
      out.push({ name: table, rows: inserted, conflicts: tableConflicts });
    }
    return out;
  });

  const tablesImported = tx();
  return { tablesImported, conflicts, dryRun: false };
}

/** Per-table merge-conflict detection (refactor of detectMergeConflicts split by table). */
function detectMergeConflictsTable(
  db: Database.Database,
  table: SupportedTable,
  rows: Record<string, unknown>[],
  conflicts: ImportConflict[],
): void {
  if (table === "chunks") {
    const cols = getTableColumns(db, "chunks");
    if (!cols.includes("content_hash")) return;
    const stmt = db.prepare("SELECT 1 FROM chunks WHERE content_hash = ? LIMIT 1");
    for (const c of rows) {
      const hash = c.content_hash as string | undefined;
      if (hash && stmt.get(hash)) {
        conflicts.push({ table: "chunks", reason: "duplicate_content_hash", key: hash });
      }
    }
    return;
  }
  if (table === "kg_entities") {
    const cols = getTableColumns(db, "kg_entities");
    if (!(cols.includes("canonical_name") && cols.includes("type"))) return;
    const stmt = db.prepare(
      "SELECT 1 FROM kg_entities WHERE canonical_name = ? AND type = ? LIMIT 1",
    );
    for (const e of rows) {
      const cn = e.canonical_name as string | undefined;
      const ty = e.type as string | undefined;
      if (cn && ty && stmt.get(cn, ty)) {
        conflicts.push({
          table: "kg_entities",
          reason: "duplicate_unique_key",
          key: `${cn}::${ty}`,
        });
      }
    }
    return;
  }
  // kg_relations
  const cols = getTableColumns(db, "kg_relations");
  if (
    !(
      cols.includes("source_entity_id") &&
      cols.includes("target_entity_id") &&
      cols.includes("predicate")
    )
  ) {
    return;
  }
  const stmt = db.prepare(
    "SELECT 1 FROM kg_relations WHERE source_entity_id = ? AND predicate = ? AND target_entity_id = ? LIMIT 1",
  );
  for (const r of rows) {
    const s = r.source_entity_id;
    const p = r.predicate as string | undefined;
    const t = r.target_entity_id;
    if (s != null && p && t != null && stmt.get(s, p, t)) {
      conflicts.push({
        table: "kg_relations",
        reason: "duplicate_unique_key",
        key: `${String(s)}::${p}::${String(t)}`,
      });
    }
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Public API: importEncryptedAuto — auto-detect v1 vs v2 and route
// ────────────────────────────────────────────────────────────────────────────

/**
 * Backward-compatible importer.
 *
 * Reads the bundle header, looks at `version`, and routes to importEncrypted()
 * (v1) or importEncryptedV2() (v2). Useful for callers that don't want to
 * branch on tier — e.g. CLI that accepts both old and new bundles.
 *
 * Note: subset `tables` is only meaningful for v2. If passed against a v1
 * bundle, the option is IGNORED with a documented behavior — v1 imports the
 * whole DB anyway. This is conservative: a user upgrading to T2 can re-export
 * to get table-subset support.
 */
export function importEncryptedAuto(
  db: Database.Database,
  passphrase: string,
  bundlePath: string,
  options: ImportV2Options,
): ImportV2Result {
  let raw: string;
  try {
    raw = readFileSync(bundlePath, "utf8");
  } catch (e) {
    throw new ExportImportError(
      `Bundle not found or unreadable: ${bundlePath} (${(e as Error).message})`,
      "BUNDLE_NOT_FOUND",
    );
  }

  let header: { version?: unknown };
  try {
    header = JSON.parse(raw) as { version?: unknown };
  } catch (e) {
    throw new ExportImportError(
      `Bundle is not valid JSON: ${(e as Error).message}`,
      "BAD_BUNDLE_FORMAT",
    );
  }

  if (header.version === 1) {
    // Route through v1. Subset is meaningless for v1; we ignore it but report
    // back in the v2-shape result so callers don't have to branch.
    const v1Result = importEncrypted(db, passphrase, bundlePath, {
      strategy: options.strategy,
      dryRun: options.dryRun,
    });
    const tablesImported: { name: string; rows: number; conflicts: number }[] = [
      {
        name: "chunks",
        rows: v1Result.chunksImported,
        conflicts: v1Result.conflicts.filter((c) => c.table === "chunks").length,
      },
      {
        name: "kg_entities",
        rows: v1Result.entitiesImported,
        conflicts: v1Result.conflicts.filter((c) => c.table === "kg_entities").length,
      },
      {
        name: "kg_relations",
        rows: v1Result.relationsImported,
        conflicts: v1Result.conflicts.filter((c) => c.table === "kg_relations").length,
      },
    ];
    return {
      tablesImported,
      conflicts: v1Result.conflicts,
      dryRun: v1Result.dryRun,
    };
  }

  if (header.version === 2) {
    return importEncryptedV2(db, passphrase, bundlePath, options);
  }

  throw new ExportImportError(
    `Unsupported bundle version ${String(header.version)} (expected 1 or 2)`,
    "UNSUPPORTED_VERSION",
  );
}
