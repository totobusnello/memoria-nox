// staged-A2-T3/edits/src/lib/audit-checkpoints.ts
//
// A2 Tier 3 / Phase 4 — Ed25519 signed audit checkpoints.
//
// Decisions resolved (docs/DECISIONS.md):
//   D56 (D-A2T3-3) — Ed25519 manual signing. Public key published in
//                    docs/AUDIT-PUBKEY.md. Private key off-box (Toto laptop +
//                    paper backup). Auditor verifies offline; doesn't need to
//                    trust nox-mem host.
//
// What this module provides:
//   - generateKeyPair() → Ed25519 keypair (base64-encoded raw 32-byte halves)
//   - createCheckpoint(scope, privateKey) → SHA-256 of audit rows since last
//     checkpoint, signed with private key, persisted in audit_checkpoints
//   - verifyCheckpoint(id, publicKey) → re-compute hash + verify Ed25519 sig
//   - verifyChain(scope, publicKey) → iterate all checkpoints in a scope,
//     return aggregate verified/broken counts + the IDs of broken rows
//
// Design contract — what an offline auditor needs:
//   1. The signed `audit_checkpoints` table (export as JSON / CSV / SQLite)
//   2. The published public key (base64 raw 32 bytes — Ed25519 spec)
//   3. The audit table being verified (ops_audit OR reads_audit) — note the
//      checkpoint covers a RANGE of rows; if the range still exists in the
//      audit table at verify-time, re-hashing gives the same result.
//
// Tamper detection lifecycle:
//   - Adversary deletes row N in ops_audit  → its range checkpoint fails
//     (re-computed hash differs from sha256_hex).
//   - Adversary inserts retroactive row    → re-computed hash differs.
//   - Adversary mutates audit_checkpoints  → triggers RAISE(ABORT).
//   - Adversary signs forged checkpoint    → fails Ed25519 verify against
//     the published public key.
//
// References:
//   - audit-checkpoints-schema.sql (DDL source-of-truth)
//   - specs/2026-05-24-A2-tier3-crypto-audit-RECON.md §4.3 F2 (signed checkpoints)
//   - src/lib/op-audit.ts (parent pattern; ops_audit producer)
//   - staged-A2-T3/edits/src/lib/reads-audit.ts (reads_audit producer)
//   - docs/DECISIONS.md D56
//   - docs/A2-TIER3-CHECKPOINTS-GUIDE.md (operator runbook)

import {
  createHash,
  generateKeyPairSync,
  sign as edSign,
  verify as edVerify,
  createPrivateKey,
  createPublicKey,
  type KeyObject,
} from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import DatabaseConstructor from 'better-sqlite3-multiple-ciphers';
import type Database from 'better-sqlite3-multiple-ciphers';

const __filename = fileURLToPath(import.meta.url);
const __thisDir = dirname(__filename);
const SCHEMA_PATH = resolve(__thisDir, 'audit-checkpoints-schema.sql');

// ────────────────────────────────────────────────────────────────────────────
// Public types
// ────────────────────────────────────────────────────────────────────────────

/** Scopes supported by this module. Mirrors the SQL trigger allowlist. */
export type CheckpointScope = 'ops' | 'reads';
export const KNOWN_SCOPES: readonly CheckpointScope[] = ['ops', 'reads'] as const;

/** Result of generateKeyPair(). Raw 32-byte halves base64-encoded. */
export interface KeyPair {
  /** base64 of the 32-byte raw Ed25519 private key */
  privateKey: string;
  /** base64 of the 32-byte raw Ed25519 public key */
  publicKey: string;
  /** SHA-256(publicKeyRaw32) — 16-char hex prefix; for cross-ref in docs */
  publicKeyFingerprint: string;
}

/** Successful checkpoint creation. */
export interface CheckpointResult {
  id: number;
  ts: number;
  scope: CheckpointScope;
  last_id: number;
  prev_last_id: number | null;
  row_count: number;
  sha256_hex: string;
  signature_b64: string;
  public_key_b64: string;
  public_key_fingerprint: string;
}

/** Result of verifyCheckpoint(). */
export interface VerifyResult {
  valid: boolean;
  /** Set when invalid; populated with first-failure reason. */
  error?: string;
  /** Set on success; the recomputed hash. Useful for debugging. */
  recomputed_sha256_hex?: string;
}

/** Result of verifyChain(). */
export interface ChainResult {
  scope: CheckpointScope;
  verified: number;
  broken: number;
  /** IDs of checkpoint rows that failed verification (in id-order). */
  breaks: number[];
  /** First-failure details per broken checkpoint (id → error). */
  errors: Record<number, string>;
  /** Total checkpoints inspected. */
  total: number;
}

// ────────────────────────────────────────────────────────────────────────────
// Key generation / encoding
// ────────────────────────────────────────────────────────────────────────────

/**
 * Generate a fresh Ed25519 keypair.
 *
 * The returned base64 strings encode the RAW 32-byte halves (Ed25519 spec) —
 * NOT PKCS8 / SPKI DER. This keeps the published `docs/AUDIT-PUBKEY.md`
 * compact + cross-tool compatible (sodium, libsodium-wrappers, age, ssh-keygen
 * -t ed25519 with manual raw extraction, etc).
 *
 * The fingerprint is sha256(raw32)[:16] hex — short enough for human
 * cross-check but long enough to detect substitution (16 hex = 64 bits).
 */
export function generateKeyPair(): KeyPair {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  // Export raw 32-byte halves
  const privRaw = exportRawPrivateKey(privateKey);
  const pubRaw = exportRawPublicKey(publicKey);
  const fpFull = createHash('sha256').update(pubRaw).digest('hex');
  return {
    privateKey: privRaw.toString('base64'),
    publicKey: pubRaw.toString('base64'),
    publicKeyFingerprint: fpFull.slice(0, 16),
  };
}

/**
 * Extract the raw 32-byte Ed25519 private key from a Node KeyObject.
 *
 * Node's `generateKeyPairSync('ed25519')` returns a KeyObject; PKCS8 export is
 * the standard wire format. We strip the PKCS8 wrapper to get the raw seed.
 * The PKCS8 v1 OctetString wrapper for Ed25519 is fixed at byte offset 16
 * (header bytes 0..15) per RFC 8410 §7 — the last 32 bytes are always the
 * raw private seed.
 */
function exportRawPrivateKey(key: KeyObject): Buffer {
  const der = key.export({ format: 'der', type: 'pkcs8' });
  // PKCS8 wrapper for Ed25519 is exactly 48 bytes total: 16-byte header +
  // 32-byte raw seed. RFC 8410 §7.
  if (der.length !== 48) {
    throw new Error(
      `[audit-checkpoints] unexpected PKCS8 Ed25519 length ${der.length} (want 48). ` +
      'Node binding may have changed encoding.',
    );
  }
  return der.subarray(16);
}

/**
 * Extract the raw 32-byte Ed25519 public key from a Node KeyObject. SPKI
 * wrapper for Ed25519 is exactly 44 bytes total: 12-byte header + 32-byte raw
 * public key. RFC 8410 §4.
 */
function exportRawPublicKey(key: KeyObject): Buffer {
  const der = key.export({ format: 'der', type: 'spki' });
  if (der.length !== 44) {
    throw new Error(
      `[audit-checkpoints] unexpected SPKI Ed25519 length ${der.length} (want 44). ` +
      'Node binding may have changed encoding.',
    );
  }
  return der.subarray(12);
}

/**
 * Reverse of exportRawPrivateKey: rebuild a KeyObject from base64 raw 32-byte
 * private seed by prepending the canonical PKCS8 v1 Ed25519 header.
 *
 * Header bytes (16): 30 2e 02 01 00 30 05 06 03 2b 65 70 04 22 04 20
 * Source: RFC 8410 §7 + section A.1 (asn.1 encoding of the AlgorithmIdentifier
 * for id-Ed25519 and the wrapping OctetString).
 */
function rawPrivateKeyToKeyObject(rawB64: string): KeyObject {
  const raw = Buffer.from(rawB64, 'base64');
  if (raw.length !== 32) {
    throw new Error(
      `[audit-checkpoints] invalid private key length ${raw.length} (want 32 raw bytes). ` +
      'Pass base64 of the 32-byte Ed25519 seed exactly as produced by generateKeyPair().',
    );
  }
  const header = Buffer.from('302e020100300506032b657004220420', 'hex');
  const pkcs8 = Buffer.concat([header, raw]);
  return createPrivateKey({ key: pkcs8, format: 'der', type: 'pkcs8' });
}

/**
 * Reverse of exportRawPublicKey: rebuild a KeyObject from base64 raw 32-byte
 * public key by prepending the canonical SPKI Ed25519 header.
 *
 * Header bytes (12): 30 2a 30 05 06 03 2b 65 70 03 21 00
 * Source: RFC 8410 §4.
 */
function rawPublicKeyToKeyObject(rawB64: string): KeyObject {
  const raw = Buffer.from(rawB64, 'base64');
  if (raw.length !== 32) {
    throw new Error(
      `[audit-checkpoints] invalid public key length ${raw.length} (want 32 raw bytes). ` +
      'Pass base64 of the 32-byte Ed25519 public key exactly as produced by generateKeyPair().',
    );
  }
  const header = Buffer.from('302a300506032b6570032100', 'hex');
  const spki = Buffer.concat([header, raw]);
  return createPublicKey({ key: spki, format: 'der', type: 'spki' });
}

/** sha256 of a raw 32-byte public key, hex-encoded, first 16 chars. */
function fingerprintOfPublicKey(pubB64: string): string {
  const raw = Buffer.from(pubB64, 'base64');
  return createHash('sha256').update(raw).digest('hex').slice(0, 16);
}

// ────────────────────────────────────────────────────────────────────────────
// Canonical serialization
// ────────────────────────────────────────────────────────────────────────────
//
// The HASHED bytestring must be REPRODUCIBLE by an offline auditor who has:
//   - access to ops_audit / reads_audit (the same DB the producer used)
//   - the algorithm spec (this file or its doc-mirror)
//
// Reproducibility hazards we have to neutralize:
//   1. JavaScript object key order — JSON.stringify is non-canonical by default
//   2. BigInt — better-sqlite3 in safe-integers mode returns INTEGER columns
//      as BigInt; JSON.stringify(BigInt) throws.
//   3. Null vs undefined for nullable columns — must encode as JSON null
//   4. UTF-8 strings — Node default; auditor must hash UTF-8 bytes, NOT UTF-16
//
// Resolution: canonicalRowJson serializes each row as a JSON object with
// keys SORTED ALPHABETICALLY, BigInt → decimal-string, null → null. Each row
// gets its own JSON object on its own line; the final hashed bytestring is
// the line-by-line concatenation with '\n' separator + trailing '\n' on the
// last line.

function canonicalRowJson(row: Record<string, unknown>): string {
  const keys = Object.keys(row).sort();
  const parts: string[] = [];
  for (const k of keys) {
    parts.push(JSON.stringify(k) + ':' + canonicalValue(row[k]));
  }
  return '{' + parts.join(',') + '}';
}

function canonicalValue(v: unknown): string {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'bigint') return JSON.stringify(v.toString());
  if (typeof v === 'string') return JSON.stringify(v);
  if (typeof v === 'number') {
    // Must be finite — non-finite floats are not valid JSON and break verify.
    if (!Number.isFinite(v)) {
      throw new Error('[audit-checkpoints] non-finite number in audit row — cannot canonicalize');
    }
    return JSON.stringify(v);
  }
  if (typeof v === 'boolean') return JSON.stringify(v);
  // Catch-all: arrays / nested objects (none currently in ops_audit / reads_audit,
  // but defensive against future schema additions). Sort keys recursively.
  if (Array.isArray(v)) {
    return '[' + v.map((x) => canonicalValue(x)).join(',') + ']';
  }
  if (typeof v === 'object') {
    return canonicalRowJson(v as Record<string, unknown>);
  }
  if (v instanceof Uint8Array) {
    // Bytes encoded as base64. Defensive for future BLOB columns.
    return JSON.stringify(Buffer.from(v).toString('base64'));
  }
  throw new Error(`[audit-checkpoints] unsupported value type ${typeof v} in audit row`);
}

function rowsToCanonicalBytes(rows: Array<Record<string, unknown>>): Buffer {
  if (rows.length === 0) {
    // Empty range is valid (idempotent re-checkpoint with no new rows). Hash
    // an explicit empty marker so the digest is not "all rows produce same
    // hash". The marker is the literal byte sequence "<empty>\n".
    return Buffer.from('<empty>\n', 'utf8');
  }
  return Buffer.from(rows.map((r) => canonicalRowJson(r)).join('\n') + '\n', 'utf8');
}

/**
 * The bytes ACTUALLY signed by Ed25519. This includes:
 *   - scope, ts, last_id, sha256_hex  → bind hash to metadata
 *   - prev_last_id                    → bind the range to the previous
 *                                       checkpoint (anti-replay)
 * The id is NOT included because it's assigned by SQLite after INSERT.
 */
function signaturePayload(args: {
  scope: string;
  ts: number;
  last_id: number;
  prev_last_id: number | null;
  sha256_hex: string;
}): Buffer {
  const canonical = canonicalRowJson({
    scope: args.scope,
    ts: args.ts,
    last_id: args.last_id,
    prev_last_id: args.prev_last_id,
    sha256_hex: args.sha256_hex,
  });
  return Buffer.from(canonical, 'utf8');
}

// ────────────────────────────────────────────────────────────────────────────
// DB connection (self-contained — same lazy pattern as reads-audit.ts)
// ────────────────────────────────────────────────────────────────────────────

function resolveDbPathLazy(): string {
  if (process.env.NOX_DB_PATH) return resolve(process.env.NOX_DB_PATH);
  const ws = process.env.OPENCLAW_WORKSPACE;
  if (ws) return resolve(ws, 'tools', 'nox-mem', 'nox-mem.db');
  return resolve(__thisDir, '..', 'nox-mem.db');
}

function applyCipherPragmas(db: Database.Database, key: string): void {
  // Lock-step with db.ts:applyCipherPragmas / reads-audit.ts.
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const escapedKey = key.replace(/'/g, "''");
  db.pragma(`key='${escapedKey}'`, { simple: true });
}

let _conn: Database.Database | null = null;
let _connPath: string | null = null;
let _connKey: string | null = null;
let _schemaApplied = false;
let _schemaSql: string | null = null;

function getConn(): Database.Database {
  const path = resolveDbPathLazy();
  const key = process.env.NOX_DB_KEY ?? null;
  if (_conn && _conn.open && _connPath === path && _connKey === key) {
    return _conn;
  }
  if (_conn && _conn.open) {
    try { _conn.close(); } catch { /* best-effort */ }
  }
  _conn = new DatabaseConstructor(path);
  _connPath = path;
  _connKey = key;
  if (key && key.length > 0) applyCipherPragmas(_conn, key);
  _conn.defaultSafeIntegers(true);
  _conn.pragma('busy_timeout = 5000');
  _schemaApplied = false;
  return _conn;
}

function ensureSchema(db: Database.Database): void {
  if (_schemaApplied) return;
  if (_schemaSql == null) {
    try {
      _schemaSql = readFileSync(SCHEMA_PATH, 'utf8');
    } catch (err) {
      throw new Error(
        `[audit-checkpoints] cannot load schema from ${SCHEMA_PATH}: ${(err as Error).message}. ` +
        'Verify the staged-A2-T3 build copied audit-checkpoints-schema.sql alongside audit-checkpoints.js.',
      );
    }
  }
  db.exec(_schemaSql);
  _schemaApplied = true;
}

/**
 * Reset module-local caches AND close the audit connection. Test-only helper.
 */
export function _resetForTest(): void {
  _schemaApplied = false;
  if (_conn && _conn.open) {
    try { _conn.close(); } catch { /* best-effort */ }
  }
  _conn = null;
  _connPath = null;
  _connKey = null;
}

// ────────────────────────────────────────────────────────────────────────────
// Scope helpers
// ────────────────────────────────────────────────────────────────────────────

function assertScope(s: string): asserts s is CheckpointScope {
  if (s !== 'ops' && s !== 'reads') {
    throw new Error(`[audit-checkpoints] invalid scope '${s}' — expected 'ops' or 'reads'`);
  }
}

/** Audit table name for a given scope. The convention is `<scope>_audit`. */
function tableForScope(scope: CheckpointScope): string {
  return scope === 'ops' ? 'ops_audit' : 'reads_audit';
}

/**
 * Fetch the latest checkpoint row in a given scope (highest id). Returns
 * undefined if no checkpoint exists yet for this scope (genesis case).
 */
function getLatestCheckpointForScope(
  db: Database.Database,
  scope: CheckpointScope,
): { id: bigint; last_id: bigint; sha256_hex: string } | undefined {
  return db
    .prepare(
      'SELECT id, last_id, sha256_hex FROM audit_checkpoints ' +
      'WHERE scope = ? ORDER BY id DESC LIMIT 1',
    )
    .get(scope) as { id: bigint; last_id: bigint; sha256_hex: string } | undefined;
}

/**
 * Fetch audit rows in range (prevLastId, lastId] for the given scope.
 *
 * Returns rows as plain objects with their column names. The row order is
 * by `id ASC` — STABLE and deterministic. Any auditor reading the same DB
 * gets identical results.
 *
 * NOTE: when prevLastId is null (genesis), the range is (-∞, lastId].
 */
function fetchScopeRows(
  db: Database.Database,
  scope: CheckpointScope,
  prevLastId: bigint | null,
  lastId: bigint,
): Array<Record<string, unknown>> {
  const tbl = tableForScope(scope);
  // Use the columns directly — different scopes have different shapes. We
  // SELECT * so the canonical-JSON includes every column (any new column
  // breaks past hashes — intentional: schema upgrade demands new checkpoint
  // baseline, see migration runbook).
  const sql = prevLastId == null
    ? `SELECT * FROM ${tbl} WHERE id <= ? ORDER BY id ASC`
    : `SELECT * FROM ${tbl} WHERE id > ? AND id <= ? ORDER BY id ASC`;
  const params = prevLastId == null ? [lastId] : [prevLastId, lastId];
  // better-sqlite3 with safe-integers will return BigInts for INTEGER columns.
  // canonicalValue() coerces BigInt → decimal-string, so reproducibility is
  // preserved.
  return db.prepare(sql).all(...params) as Array<Record<string, unknown>>;
}

/** Read the MAX(id) from the audit table for a scope. Returns 0 if empty. */
function maxAuditId(db: Database.Database, scope: CheckpointScope): bigint {
  const tbl = tableForScope(scope);
  const row = db.prepare(`SELECT COALESCE(MAX(id), 0) AS m FROM ${tbl}`).get() as { m: bigint };
  return row.m;
}

// ────────────────────────────────────────────────────────────────────────────
// Schema-version helper (best-effort; nox-mem db stores it in meta.schema_version)
// ────────────────────────────────────────────────────────────────────────────

function readSchemaVersion(db: Database.Database): number {
  try {
    const row = db
      .prepare("SELECT value FROM meta WHERE key = 'schema_version'")
      .get() as { value: string } | undefined;
    return row ? parseInt(row.value, 10) : 0;
  } catch {
    // Table doesn't exist in eval/test DBs; that's fine.
    return 0;
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Public API — create / verify / chain
// ────────────────────────────────────────────────────────────────────────────

/**
 * Create a signed checkpoint for the rows added to <scope>_audit since the
 * previous checkpoint (or since the beginning of time for the first one).
 *
 * The returned object describes the persisted row. The signature is computed
 * BEFORE INSERT and stored INLINE — there is no pending state in this path.
 * (The pending-then-sign batch flow is reserved for P4.1 and uses the
 * schema's UPDATE allowance for NULL → non-NULL signature.)
 *
 * If the audit table is empty for this scope, the function returns
 * undefined (caller should treat as "nothing to checkpoint"). This is the
 * idempotent guard for cron — no rows since last checkpoint → no-op.
 */
export function createCheckpoint(
  scope: CheckpointScope,
  privateKeyB64: string,
): CheckpointResult | undefined {
  assertScope(scope);
  const db = getConn();
  ensureSchema(db);

  const lastIdNow = maxAuditId(db, scope);
  const previous = getLatestCheckpointForScope(db, scope);
  const prevLastId: bigint | null = previous ? previous.last_id : null;

  if (previous && lastIdNow <= previous.last_id) {
    // No new rows since last checkpoint. Caller's policy decides what to do;
    // here we return undefined (idempotent guard).
    return undefined;
  }
  if (!previous && lastIdNow === 0n) {
    // Genesis case with empty audit table — nothing to checkpoint at all.
    return undefined;
  }

  const rows = fetchScopeRows(db, scope, prevLastId, lastIdNow);
  const canonicalBytes = rowsToCanonicalBytes(rows);
  const sha256_hex = createHash('sha256').update(canonicalBytes).digest('hex');

  const ts = Date.now();

  // Derive public key from private (so caller doesn't have to pass both;
  // matches the "single source of truth" intent of D56).
  const privKeyObj = rawPrivateKeyToKeyObject(privateKeyB64);
  // Node's KeyObject.asymmetricKeyType === 'ed25519'; we can derive the
  // public via createPublicKey({ key: privKeyObj }).
  const pubKeyObj = createPublicKey(privKeyObj);
  const pubRaw = exportRawPublicKey(pubKeyObj);
  const publicKeyB64 = pubRaw.toString('base64');

  const payload = signaturePayload({
    scope,
    ts,
    last_id: Number(lastIdNow),
    prev_last_id: prevLastId === null ? null : Number(prevLastId),
    sha256_hex,
  });
  const sigBuf = edSign(null, payload, privKeyObj);
  const signature_b64 = sigBuf.toString('base64');

  const metadata = JSON.stringify({
    prev_last_id: prevLastId === null ? null : Number(prevLastId),
    row_count: rows.length,
    schema_version: readSchemaVersion(db),
    ts_iso: new Date(ts).toISOString(),
  });

  const insertResult = db.prepare(
    'INSERT INTO audit_checkpoints ' +
    '(ts, scope, last_id, sha256_hex, signature_b64, public_key_b64, metadata) ' +
    'VALUES (CAST(? AS INTEGER), ?, CAST(? AS INTEGER), ?, ?, ?, ?)',
  ).run(ts, scope, Number(lastIdNow), sha256_hex, signature_b64, publicKeyB64, metadata);

  return {
    id: Number(insertResult.lastInsertRowid),
    ts,
    scope,
    last_id: Number(lastIdNow),
    prev_last_id: prevLastId === null ? null : Number(prevLastId),
    row_count: rows.length,
    sha256_hex,
    signature_b64,
    public_key_b64: publicKeyB64,
    public_key_fingerprint: fingerprintOfPublicKey(publicKeyB64),
  };
}

/**
 * Verify a single checkpoint row by id.
 *
 * Returns { valid: true } iff:
 *   1. The Ed25519 signature in signature_b64 verifies against the supplied
 *      publicKeyB64 over the canonical payload.
 *   2. Re-hashing the actual audit rows (range from previous checkpoint to
 *      this one) produces the same sha256_hex stored in the row.
 *
 * `error` field is populated with the first-failure reason. Subsequent
 * problems (if any) are masked — call verifyChain() for a global view.
 *
 * NOTE: the supplied publicKeyB64 is COMPARED against the row's stored
 * `public_key_b64` first. If they differ, verification fails immediately —
 * the auditor's expected key is the source-of-truth, and a row with a
 * mismatched stored key is treated as tampered.
 */
export function verifyCheckpoint(
  id: number,
  publicKeyB64: string,
): VerifyResult {
  const db = getConn();
  ensureSchema(db);

  const row = db.prepare(
    'SELECT id, ts, scope, last_id, sha256_hex, signature_b64, public_key_b64, metadata ' +
    'FROM audit_checkpoints WHERE id = ?',
  ).get(id) as {
    id: bigint;
    ts: bigint;
    scope: string;
    last_id: bigint;
    sha256_hex: string;
    signature_b64: string | null;
    public_key_b64: string | null;
    metadata: string;
  } | undefined;

  if (!row) return { valid: false, error: `checkpoint id=${id} not found` };
  if (row.signature_b64 == null) {
    return { valid: false, error: `checkpoint id=${id} is pending (signature_b64 NULL)` };
  }
  if (row.public_key_b64 == null) {
    return { valid: false, error: `checkpoint id=${id} missing stored public_key_b64` };
  }

  // Key match: expected vs stored.
  if (row.public_key_b64 !== publicKeyB64) {
    return {
      valid: false,
      error:
        `checkpoint id=${id} public key mismatch — ` +
        `stored fingerprint=${fingerprintOfPublicKey(row.public_key_b64)}, ` +
        `expected fingerprint=${fingerprintOfPublicKey(publicKeyB64)}`,
    };
  }

  // Reconstruct prev_last_id from metadata (single source — schema's metadata
  // column). Auditor parses, doesn't re-walk the chain (which would be O(N)).
  let metadata: { prev_last_id: number | null };
  try {
    metadata = JSON.parse(row.metadata) as { prev_last_id: number | null };
  } catch (err) {
    return { valid: false, error: `checkpoint id=${id} metadata not valid JSON: ${(err as Error).message}` };
  }

  // Verify Ed25519 signature over the canonical payload.
  const payload = signaturePayload({
    scope: row.scope,
    ts: Number(row.ts),
    last_id: Number(row.last_id),
    prev_last_id: metadata.prev_last_id,
    sha256_hex: row.sha256_hex,
  });
  let pubKeyObj: KeyObject;
  try {
    pubKeyObj = rawPublicKeyToKeyObject(publicKeyB64);
  } catch (err) {
    return { valid: false, error: `checkpoint id=${id} public key decode failed: ${(err as Error).message}` };
  }
  const sigBuf = Buffer.from(row.signature_b64, 'base64');
  const sigOk = edVerify(null, payload, pubKeyObj, sigBuf);
  if (!sigOk) {
    return { valid: false, error: `checkpoint id=${id} signature does NOT verify against supplied public key` };
  }

  // Re-hash the actual audit rows and compare.
  if (!['ops', 'reads'].includes(row.scope)) {
    return { valid: false, error: `checkpoint id=${id} has unknown scope '${row.scope}'` };
  }
  const scope = row.scope as CheckpointScope;
  const prevLastId: bigint | null =
    metadata.prev_last_id == null ? null : BigInt(metadata.prev_last_id);
  const rows = fetchScopeRows(db, scope, prevLastId, row.last_id);
  const canonicalBytes = rowsToCanonicalBytes(rows);
  const recomputed = createHash('sha256').update(canonicalBytes).digest('hex');

  if (recomputed !== row.sha256_hex) {
    return {
      valid: false,
      error:
        `checkpoint id=${id} hash mismatch — stored=${row.sha256_hex} ` +
        `recomputed=${recomputed} (range prev_last_id=${prevLastId} → last_id=${row.last_id}, ` +
        `${rows.length} rows). Chain broken — audit table mutated since signing.`,
      recomputed_sha256_hex: recomputed,
    };
  }

  return { valid: true, recomputed_sha256_hex: recomputed };
}

/**
 * Verify the full chain of checkpoints for a given scope. Iterates id ASC,
 * accumulates verified / broken counts. Returns the IDs of broken rows so the
 * operator can investigate.
 *
 * This function loads each checkpoint independently — no cross-checkpoint
 * chaining beyond what's encoded in (prev_last_id, last_id]. A break at
 * checkpoint N does NOT poison subsequent checkpoints (their range may still
 * verify against the unmodified rows). Each break is an INDEPENDENT signal.
 */
export function verifyChain(
  scope: CheckpointScope,
  publicKeyB64: string,
): ChainResult {
  assertScope(scope);
  const db = getConn();
  ensureSchema(db);

  const ids = db.prepare(
    'SELECT id FROM audit_checkpoints WHERE scope = ? ORDER BY id ASC',
  ).all(scope) as Array<{ id: bigint }>;

  const result: ChainResult = {
    scope,
    verified: 0,
    broken: 0,
    breaks: [],
    errors: {},
    total: ids.length,
  };

  for (const { id } of ids) {
    const idNum = Number(id);
    const v = verifyCheckpoint(idNum, publicKeyB64);
    if (v.valid) {
      result.verified += 1;
    } else {
      result.broken += 1;
      result.breaks.push(idNum);
      result.errors[idNum] = v.error ?? 'unknown';
    }
  }
  return result;
}

// ────────────────────────────────────────────────────────────────────────────
// Internal helpers exposed for testing / advanced operators
// ────────────────────────────────────────────────────────────────────────────

/** Expose canonical row JSON for test reproducibility checks. */
export const _internals = {
  canonicalRowJson,
  rowsToCanonicalBytes,
  signaturePayload,
  fingerprintOfPublicKey,
  rawPrivateKeyToKeyObject,
  rawPublicKeyToKeyObject,
};
