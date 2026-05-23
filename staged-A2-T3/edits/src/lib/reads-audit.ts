// staged-A2-T3/edits/src/lib/reads-audit.ts
//
// A2 Tier 3 / Phase 3 — opt-in read-path audit wrapper.
//
// Decisions resolved (docs/DECISIONS.md):
//   D55 (D-A2T3-2) — default OFF, opt-in via NOX_READS_AUDIT=1
//   D58 (D-A2T3-5) — retention env-driven default 90d, archive policy
//
// Design (mirrors src/lib/op-audit.ts):
//   - When NOX_READS_AUDIT !== '1' → zero overhead (early return inside the
//     wrapper, BEFORE any DB handle is obtained). Cold-path bypass.
//   - When enabled → wrap fn(), record duration, INSERT one row into
//     reads_audit. Single prepared statement is reused (cached on the db
//     handle per-process).
//   - Sanitization happens in JS before bind: query is coerced to string,
//     stripped of NUL bytes + control chars, truncated to ≤200 chars (per
//     task brief §2). If NOX_READS_AUDIT_HASH_QUERIES=1, the query is
//     replaced with sha256-hex BEFORE truncation (defense for regulated
//     tier; aligns with recon §4.3 F1 "NEVER plaintext query" intent).
//   - user_id is NEVER stored raw. If a caller passes user_id, the env
//     NOX_READS_AUDIT_USER_HASH MUST also be set (acts as salt + opt-in flag);
//     otherwise we REFUSE the bind and throw — fail-closed against accidental
//     PII leakage.
//   - INSERT uses CAST(? AS INTEGER) for ts/k/n_results/latency_ms (lesson
//     [[sqlite-text-affinity-coerces-int-back]] + ops_audit Issue #1A).
//   - All errors inside the audit path are swallowed and logged to console.warn
//     — audit MUST NOT break the search hot path. (op-audit throws because a
//     destructive op without audit is a deployment bug; a search without audit
//     is acceptable degradation.)
//
// Usage:
//   import { withReadAudit } from './lib/reads-audit.js';
//   const results = await withReadAudit(
//     { op_name: 'search', query: 'foo bar', k: 10, source_app: 'http' },
//     async () => doSearch('foo bar', 10),
//   );
//   // Audit row inserted iff NOX_READS_AUDIT=1; otherwise zero overhead.
//
// References:
//   - reads-audit-schema.sql (DDL source-of-truth)
//   - src/lib/op-audit.ts (parent pattern — withOpAudit)
//   - specs/2026-05-24-A2-tier3-crypto-audit-RECON.md §4.3 F1
//   - docs/DECISIONS.md D55 + D58
//   - docs/A2-TIER3-READS-AUDIT-GUIDE.md (operator runbook)

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import DatabaseConstructor from 'better-sqlite3-multiple-ciphers';
import type Database from 'better-sqlite3-multiple-ciphers';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Resolve schema SQL relative to THIS module — works whether running from
// dist/ (production) or via dynamic import in tests. Read at first-enable;
// cached for subsequent calls.
const SCHEMA_PATH = resolve(__dirname, 'reads-audit-schema.sql');

/** Max characters of the `query` column. Task brief §2 pins ≤200. */
export const QUERY_MAX_LEN = 200;

/** Free-form source_app, but we validate against this allowlist for the
 *  common cases — caller can pass arbitrary string but consider matching one. */
export const KNOWN_SOURCE_APPS = ['cli', 'http', 'mcp', 'cron', 'test'] as const;
export type KnownSourceApp = (typeof KNOWN_SOURCE_APPS)[number];

/**
 * Options for a single audited read. All fields optional except op_name.
 *
 *  - op_name: required. Free-form. Conventional values: 'search', 'answer',
 *             'kg-path', 'mcp:<tool_name>', 'health-read'.
 *  - query:   the raw query text (will be sanitized + truncated; or hashed if
 *             NOX_READS_AUDIT_HASH_QUERIES=1).
 *  - k:       top-k parameter of the search call (if applicable).
 *  - source_app: 'cli' | 'http' | 'mcp' | 'cron' | <custom>.
 *  - user_id: optional. ONLY accepted if NOX_READS_AUDIT_USER_HASH is set;
 *             hashed-with-salt before bind. Pass {} or omit for anonymous.
 */
export interface ReadAuditOptions {
  op_name: string;
  query?: string;
  k?: number;
  source_app?: string;
  user_id?: string;
}

/**
 * Result returned by the wrapped fn. The wrapper uses .length / .n_results /
 * the array length as a heuristic — if you return something else, pass
 * n_results explicitly via the @ result.n_results field of an object response.
 *
 * Default heuristics:
 *   - Array  → n_results = arr.length
 *   - Object with .n_results → use it
 *   - Object with .results.length → use it
 *   - Otherwise → n_results = null (recorded as NULL in DB)
 */
function deriveNResults(result: unknown): number | null {
  if (result == null) return null;
  if (Array.isArray(result)) return result.length;
  if (typeof result === 'object') {
    const r = result as { n_results?: unknown; results?: unknown };
    if (typeof r.n_results === 'number' && Number.isFinite(r.n_results)) {
      return Math.trunc(r.n_results);
    }
    if (Array.isArray(r.results)) return r.results.length;
  }
  return null;
}

/** Strip NUL bytes + ASCII control chars (except newline + tab) which would
 *  break SQLite TEXT round-trip or downstream JSON tooling. */
function sanitizeQueryText(raw: string): string {
  // eslint-disable-next-line no-control-regex
  return raw.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
}

/** sha256(value) → hex string (lowercase). */
function sha256Hex(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

/**
 * Apply the configured query transform:
 *   - If NOX_READS_AUDIT_HASH_QUERIES=1 → return sha256-hex(sanitized).
 *     (sha256-hex is 64 chars, well under QUERY_MAX_LEN.)
 *   - Else → sanitize + truncate to QUERY_MAX_LEN.
 *   - Empty/undefined → null.
 */
function transformQuery(query: string | undefined): string | null {
  if (query == null) return null;
  const sanitized = sanitizeQueryText(String(query));
  if (sanitized.length === 0) return null;
  if (process.env.NOX_READS_AUDIT_HASH_QUERIES === '1') {
    return sha256Hex(sanitized);
  }
  // Truncate; do NOT add ellipsis — keeps the column predictable byte-cap
  // and avoids accidental "1234567890…" prefix-collision in hash mode.
  return sanitized.length > QUERY_MAX_LEN ? sanitized.substring(0, QUERY_MAX_LEN) : sanitized;
}

/**
 * Transform user_id per the env policy:
 *   - If user_id is null/undefined → return null (no PII bound).
 *   - If NOX_READS_AUDIT_USER_HASH is unset → THROW (fail-closed). Caller
 *     must opt-in to user-id auditing explicitly.
 *   - Else → sha256(salt + user_id) — salt is the env value itself, so
 *     operators rotating the salt invalidate the linkability of historical
 *     rows. (Acceptable trade-off: salt rotation is rare; auditor still has
 *     the per-period stable identifier.)
 */
function transformUserId(userId: string | undefined): string | null {
  if (userId == null || userId === '') return null;
  const salt = process.env.NOX_READS_AUDIT_USER_HASH;
  if (!salt || salt.length === 0) {
    throw new Error(
      '[reads-audit] caller passed user_id but NOX_READS_AUDIT_USER_HASH env is unset. ' +
      'Set NOX_READS_AUDIT_USER_HASH=<salt> to opt-in to user-id auditing (stored as ' +
      'sha256(salt + user_id), NEVER raw). Refusing to bind raw user_id.',
    );
  }
  return sha256Hex(salt + ':' + userId);
}

// ────────────────────────────────────────────────────────────────────────────
// Connection management (self-contained — separate from db.ts singleton)
// ────────────────────────────────────────────────────────────────────────────
//
// IMPORTANT design choice: this module opens its OWN better-sqlite3 connection
// rather than reusing the db.ts getDb() singleton. Rationale:
//
//   1. db.ts captures DB_PATH at module-load time as a `const` (ESM static
//      const). The memory `[[no-getdb-in-eval-scripts]]` documents this trap:
//      "singleton ignores late env overrides + ESM hoisting captures env at
//      load". Eval scripts and test harnesses that mutate NOX_DB_PATH between
//      operations would hit the wrong file.
//   2. The op-audit pattern (parent of this module) runs ONCE per process and
//      doesn't have the issue. reads-audit, by contrast, may run in test
//      contexts that switch DBs.
//   3. Opening a second connection to the same file is supported by SQLite
//      WAL mode (concurrent readers + one writer). The cipher key flows
//      through via env (NOX_DB_KEY) so the second connection inherits crypto
//      state correctly.
//
// Resolution of DB_PATH at safeRecord() time:
//   1. NOX_DB_PATH env var (explicit; test-friendly)
//   2. OPENCLAW_WORKSPACE-derived canonical path (prod)
//   3. Relative fallback (local dev)
//
// Same precedence order as db.ts:DB_PATH — so production behavior is
// identical to "reuse the same handle". The difference is purely about
// re-reading the env on each enable cycle.

const __filename = fileURLToPath(import.meta.url);
const __thisDir = dirname(__filename);

function resolveDbPathLazy(): string {
  if (process.env.NOX_DB_PATH) return resolve(process.env.NOX_DB_PATH);
  const ws = process.env.OPENCLAW_WORKSPACE;
  if (ws) return resolve(ws, 'tools', 'nox-mem', 'nox-mem.db');
  // Fallback: relative to this file (same as db.ts default).
  return resolve(__thisDir, '..', 'nox-mem.db');
}

function applyCipherPragmas(db: Database.Database, key: string): void {
  // Lock-step with db.ts:applyCipherPragmas — keep both in sync. Order matters:
  // cipher/legacy/cipher_compatibility BEFORE key.
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
let _insertStmt: Database.Statement | null = null;

/**
 * Get-or-open the audit-side connection. Reads NOX_DB_PATH + NOX_DB_KEY at
 * call time so test harnesses can swap DBs between runs.
 *
 * Closes-and-reopens if the resolved path OR key changed since last call —
 * defensive against env mutation mid-process.
 */
function getAuditConn(): Database.Database {
  const path = resolveDbPathLazy();
  const key = process.env.NOX_DB_KEY ?? null;
  if (_conn && _conn.open && _connPath === path && _connKey === key) {
    return _conn;
  }
  // Close any stale connection
  if (_conn && _conn.open) {
    try { _conn.close(); } catch { /* best-effort */ }
  }
  _conn = new DatabaseConstructor(path);
  _connPath = path;
  _connKey = key;
  if (key && key.length > 0) applyCipherPragmas(_conn, key);
  _conn.defaultSafeIntegers(true);
  // Defensive perf pragmas (mirror db.ts but only those that affect this
  // connection's behavior — busy_timeout matters for write contention with
  // the main app handle).
  _conn.pragma('busy_timeout = 5000');
  // Reset the schema-applied flag whenever we rebind to a new file, so the
  // next safeRecord() re-bootstraps the schema.
  _schemaApplied = false;
  // Drop any prepared statement bound to the prior connection.
  _insertStmt = null;
  return _conn;
}

/**
 * Read the schema SQL file from disk (once per process) and exec it.
 * Idempotent: CREATE ... IF NOT EXISTS guards all DDL.
 *
 * Failures here are logged + re-thrown — schema bootstrap is opt-in (only
 * called when NOX_READS_AUDIT=1) so a failure means the operator explicitly
 * asked for audit and we couldn't deliver it. Better to throw at enable time
 * than to silently swallow at every search.
 */
function ensureReadsAuditSchema(db: Database.Database): void {
  if (_schemaApplied) return;
  if (_schemaSql == null) {
    try {
      _schemaSql = readFileSync(SCHEMA_PATH, 'utf8');
    } catch (err) {
      throw new Error(
        `[reads-audit] cannot load schema from ${SCHEMA_PATH}: ${(err as Error).message}. ` +
        'Verify the staged-A2-T3 build copied reads-audit-schema.sql alongside reads-audit.js.',
      );
    }
  }
  db.exec(_schemaSql);
  _schemaApplied = true;
}

/**
 * Prepare (and cache) the INSERT statement. Uses CAST(? AS INTEGER) on
 * numeric columns to defeat better-sqlite3's REAL binding (lesson from
 * ops_audit 2026-05-21 Issue #1A).
 *
 * The cache is per-connection. getAuditConn() clears it on rebind.
 */
function getInsertStmt(db: Database.Database): Database.Statement {
  if (_insertStmt) return _insertStmt;
  _insertStmt = db.prepare(
    'INSERT INTO reads_audit ' +
    '(ts, query, k, n_results, latency_ms, user_id, source_app) ' +
    'VALUES (CAST(? AS INTEGER), ?, CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER), ?, ?)',
  );
  return _insertStmt;
}

/**
 * Reset all module-local caches AND close the audit connection. Test-only
 * helper — production code should rely on the process-lifecycle reset (cache
 * dies with process).
 *
 * Call this between tests that swap NOX_DB_PATH or NOX_DB_KEY. The next
 * audit operation will re-open with the current env values.
 *
 * NOT exported as part of the public surface; available for the __tests__/
 * suite via direct import (Node ESM convention — underscore prefix signals
 * internal-use).
 */
export function _resetForTest(): void {
  _schemaApplied = false;
  _insertStmt = null;
  if (_conn && _conn.open) {
    try { _conn.close(); } catch { /* best-effort */ }
  }
  _conn = null;
  _connPath = null;
  _connKey = null;
  // Intentionally do NOT clear _schemaSql — the file content is immutable on
  // disk; re-reading would only add I/O without changing behavior.
}

/**
 * True if read-audit is enabled in this process (NOX_READS_AUDIT === '1').
 * Cheap — single env lookup. Safe to call on the hot path.
 */
export function isReadsAuditEnabled(): boolean {
  return process.env.NOX_READS_AUDIT === '1';
}

/**
 * The opt-in flag for query hashing. Exposed for /api/health introspection
 * and for the operator runbook.
 */
export function isQueryHashingEnabled(): boolean {
  return process.env.NOX_READS_AUDIT_HASH_QUERIES === '1';
}

// ────────────────────────────────────────────────────────────────────────────
// Public wrapper
// ────────────────────────────────────────────────────────────────────────────

/**
 * Wrap an async read operation with optional reads_audit recording.
 *
 * When NOX_READS_AUDIT !== '1' (default): pure pass-through, zero overhead
 * (single env lookup + direct fn() return — no DB touch, no statement
 * preparation, no schema check).
 *
 * When NOX_READS_AUDIT='1': records a single reads_audit row with ts +
 * sanitized query + k + n_results (derived from result) + latency_ms +
 * user_id (hashed) + source_app. Audit failures are logged + swallowed —
 * the caller's fn() result is always returned.
 *
 * IMPORTANT: this function is intentionally PERMISSIVE on the result type
 * (uses `unknown` internally via deriveNResults). It does not enforce that
 * fn() returns an array or any specific shape — search functions return
 * various shapes (objects with .results, arrays, single objects). The
 * heuristic in deriveNResults() covers the common cases.
 *
 * @typeParam T - inferred from fn(); returned unchanged.
 */
export async function withReadAudit<T>(
  options: ReadAuditOptions,
  fn: () => Promise<T>,
): Promise<T> {
  // FAST PATH: not enabled → call fn() directly. The env lookup is the
  // total cost of audit being "off" in this process. No DB handle obtained.
  if (process.env.NOX_READS_AUDIT !== '1') {
    return fn();
  }

  // Refuse user_id without hash salt EARLY (before fn() runs) so caller learns
  // about the misconfiguration on the first audited read, not after a successful
  // search has already returned.
  let userIdHashed: string | null;
  try {
    userIdHashed = transformUserId(options.user_id);
  } catch (err) {
    // Fail-closed: refuse the operation entirely. Caller MUST either remove
    // user_id from the call or set NOX_READS_AUDIT_USER_HASH.
    throw err;
  }

  const t0 = Date.now();
  let result: T;
  let errClass: string | null = null;
  try {
    result = await fn();
  } catch (err) {
    errClass = err instanceof Error ? err.constructor.name : 'unknown';
    // Record the failed attempt too (n_results=0, latency=elapsed) before
    // re-throwing — auditor wants to see failures, not just successes.
    safeRecord({
      ts: t0,
      query: transformQuery(options.query),
      k: options.k ?? null,
      n_results: 0,
      latency_ms: Date.now() - t0,
      user_id: userIdHashed,
      source_app: options.source_app ?? null,
      _errClass: errClass,
      _opName: options.op_name,
    });
    throw err;
  }
  // Success path
  safeRecord({
    ts: t0,
    query: transformQuery(options.query),
    k: options.k ?? null,
    n_results: deriveNResults(result),
    latency_ms: Date.now() - t0,
    user_id: userIdHashed,
    source_app: options.source_app ?? null,
    _errClass: null,
    _opName: options.op_name,
  });
  return result;
}

/**
 * Best-effort INSERT into reads_audit. Catches and logs all errors — audit
 * MUST NOT break the read path. (Contrast: op-audit throws because missing
 * audit for a destructive op is a deploy bug.)
 *
 * Note: `_errClass` and `_opName` are currently unused (schema doesn't
 * include error_class or op_name per the task brief column list). Captured
 * here for the future P4 extension where audit_checkpoints rollup might
 * partition by op_name.
 */
function safeRecord(row: {
  ts: number;
  query: string | null;
  k: number | null;
  n_results: number | null;
  latency_ms: number | null;
  user_id: string | null;
  source_app: string | null;
  _errClass: string | null;
  _opName: string;
}): void {
  try {
    const db = getAuditConn();
    ensureReadsAuditSchema(db);
    const stmt = getInsertStmt(db);
    stmt.run(
      row.ts,
      row.query,
      row.k,
      row.n_results,
      row.latency_ms,
      row.user_id,
      row.source_app,
    );
  } catch (err) {
    // Log + swallow. Use console.warn (not error) — audit failures aren't
    // service-impacting. Include op_name for grep-ability.
    console.warn(
      `[reads-audit] safeRecord failed for op '${row._opName}': ${(err as Error).message}`,
    );
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Operator helpers (read-side queries)
// ────────────────────────────────────────────────────────────────────────────

export interface ReadsAuditStats {
  /** Total rows in the local reads_audit table (NOT counting archive). */
  total_rows: bigint;
  /** Rows in the trailing 24h window. */
  rows_24h: bigint;
  /** Earliest ts in the table (epoch ms), or null if empty. */
  oldest_ts: bigint | null;
  /** Latest ts in the table (epoch ms), or null if empty. */
  newest_ts: bigint | null;
}

/**
 * Read-side stats helper for /api/health or operator inspection. Always
 * safe to call — schema is bootstrapped on demand. Returns zeros on a
 * fresh DB or when audit has never been enabled.
 *
 * NOTE: returns bigint (safe-integers mode is on at the DB layer per
 * staged-A2-T3 db.ts). Caller should coerce to number only when known
 * < Number.MAX_SAFE_INTEGER.
 */
export function getReadsAuditStats(): ReadsAuditStats {
  const db = getAuditConn();
  ensureReadsAuditSchema(db);
  const since = Date.now() - 86_400_000;
  const total = db
    .prepare('SELECT COUNT(*) AS c FROM reads_audit')
    .get() as { c: bigint };
  const recent = db
    .prepare('SELECT COUNT(*) AS c FROM reads_audit WHERE CAST(ts AS INTEGER) >= ?')
    .get(since) as { c: bigint };
  const bounds = db
    .prepare('SELECT MIN(ts) AS lo, MAX(ts) AS hi FROM reads_audit')
    .get() as { lo: bigint | null; hi: bigint | null };
  return {
    total_rows: total.c,
    rows_24h: recent.c,
    oldest_ts: bounds.lo,
    newest_ts: bounds.hi,
  };
}
