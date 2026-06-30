// op-audit.ts — Snapshot pré-op atômico + audit log para operações destrutivas
// Lição do incident 2026-04-25 (reindex zerou metadata de 183 entities sem rede de proteção).
// CLAUDE.md regra #15: 'ops destrutivas só com --dry-run ou snapshot atômico'.
//
// Pós-audit 2026-04-25 (5 CRITICAL/HIGH fixados):
// - Filename collision-resistant (pid + uuid)
// - Fail-closed: snapshot falha → throw (override via NOX_ALLOW_NO_SNAPSHOT=1)
// - Path validation contra traversal
// - VACUUM INTO atômico via .tmp + integrity_check + rename
// - safeRestore() helper exportado pra recovery sem WAL/SHM stale + schema check
//
// Fix 2026-05-19 (BUG CRITICAL — audit rows silently swallowed):
// - trg_ops_audit_started_at_server_side comparava TEXT datetime('now') default vs INTEGER
//   epoch-ms: TEXT string é sempre > qualquer inteiro no SQLite → RAISE(IGNORE) em TODO INSERT
// - Fix: INSERT passa started_at como epoch ms explícito (strftime('%s','now')*1000)
// - Fix: INSERT falha ruidosamente se changes=0 (detecta RAISE(IGNORE) silencioso futuro)
// - Fix: remove triggers trg_ops_audit_started_at_server_side e trg_ops_audit_force_started_at
//        (design falho — tipo errado na comparação; substituídos por started_at epoch ms no INSERT)
// - Veja: docs/INCIDENTS.md#2026-05-19, memory/feedback_withopaudit_trigger_raise_ignore_swallows_insert.md
//
// Uso:
//   await withOpAudit('reindex', { db_source: 'main' }, async () => {
//     // ...código que muta DB...
//     return { affected_rows: 9540 };
//   });
//
// Recovery:
//   import { safeRestore } from './lib/op-audit.js';
//   safeRestore('/var/backups/nox-mem/pre-op/reindex-20260425143012-12345-abc123.db');

import { existsSync, mkdirSync, renameSync, statSync, unlinkSync, chmodSync, realpathSync, statfsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import Database from 'better-sqlite3';
import { getDb } from '../db.js';

const ALLOWED_PREFIXES = ['/var/backups/', '/root/.openclaw/'];
const DEFAULT_SNAPSHOT_DIR = '/var/backups/nox-mem/pre-op';
const DB_PATH = process.env.NOX_DB_PATH || '/root/.openclaw/workspace/tools/nox-mem/nox-mem.db';

// W2-2 (audit cleanup 04-26): validate DB_PATH at module load — symetric trust w/ snapshot dir.
// Prevents attacker setting NOX_DB_PATH to /tmp/foo and having safeRestore install snapshot there.
{
  const resolvedDb = resolve(DB_PATH);
  const allowed = ALLOWED_PREFIXES.some((p) => resolvedDb.startsWith(p));
  if (!allowed) {
    throw new Error(`[op-audit] NOX_DB_PATH '${resolvedDb}' must be inside ${ALLOWED_PREFIXES.join(' or ')}`);
  }
}

function getValidatedSnapshotDir(): string {
  const raw = process.env.NOX_PRE_OP_SNAPSHOT_DIR || DEFAULT_SNAPSHOT_DIR;
  const resolved = resolve(raw);
  // Fix CRIT-3: path traversal protection (lexical)
  const allowed = ALLOWED_PREFIXES.some((p) => resolved.startsWith(p));
  if (!allowed) {
    throw new Error(`[op-audit] snapshot dir '${resolved}' must be inside ${ALLOWED_PREFIXES.join(' or ')}`);
  }
  // Fix SEC HIGH #2 (audit 04-26): symlink protection — resolve real path and re-validate.
  // Lexical resolve() doesn't follow symlinks; attacker with dir write could ln -s /etc nox-mem-link
  // and bypass prefix check. realpathSync.native traverses links.
  if (existsSync(resolved)) {
    const realPath = realpathSync.native(resolved);
    const realAllowed = ALLOWED_PREFIXES.some((p) => realPath.startsWith(p));
    if (!realAllowed || realPath !== resolved) {
      throw new Error(`[op-audit] snapshot dir '${resolved}' resolves via symlink to '${realPath}' — refusing`);
    }
  }
  return resolved;
}

const VALID_OPNAME = /^[a-z0-9-]{1,32}$/;

// Fase 1 / Gap B (2026-05-15): derive dbSource for snapshot filename qualifier.
// Primary: NOX_DB_SOURCE env (set by orchestrator, e.g. nightly-maintenance.sh).
// Fallback: parse known path patterns (agents/<name>/ → name; tools/nox-mem/ → main).
// Final fallback: 'unknown' (operationally visible, never breaks).
// Sanitized to filename-safe chars; max 32 chars.
function deriveDbSource(): string {
  const explicit = process.env.NOX_DB_SOURCE;
  if (explicit) {
    return explicit.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 32);
  }
  const path = DB_PATH;
  const agentMatch = path.match(/\/agents\/([a-zA-Z0-9_-]+)\//);
  if (agentMatch) return agentMatch[1].substring(0, 32);
  if (path.includes('/workspace/tools/nox-mem/')) return 'main';
  return 'unknown';
}

export interface OpResult {
  affected_rows?: number;
  notes?: string;
}

/**
 * Valid db_source values for withOpAudit().
 *
 * Issue #3B (2026-05-21): db_source is now a REQUIRED explicit parameter.
 * Rationale: the previous implicit deriveDbSource() fallback allowed callers
 * to silently land in the 'unknown' bucket whenever NOX_DB_SOURCE was unset
 * and the path heuristic didn't match. Requiring it at compile-time eliminates
 * the entire class of 'unknown' pollution at the call site rather than just
 * filtering it at reporting time (the #3A approach).
 *
 * Values:
 *  'main'     — production nox-mem.db (standard CLI ops: reindex, consolidate, compact, kg-merge)
 *  'shadow'   — shadow/evaluation DB (eval harness, G-series ablation runs)
 *  'isolated' — temp-isolated copy (backfill migrations running against a clone)
 *  'test'     — test suite ops (will be filtered out of /api/health.opsAudit metrics)
 */
export type DbSource = 'main' | 'shadow' | 'isolated' | 'test';

/**
 * Options for withOpAudit(). db_source is REQUIRED — no implicit fallback.
 */
export interface WithOpAuditOptions {
  /** Explicit DB source classification. Required — prevents silent 'unknown' bucket. */
  db_source: DbSource;
}

function ensureSnapshotDir(dir: string): void {
  // Fix SEC HIGH #1 (audit 04-26): chmod even when dir already exists (drift correction).
  // Pre-existing dir may have permissive mode (was 0o755 in prod, snapshots leaked world-readable).
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true, mode: 0o700 });
  } else {
    try { chmodSync(dir, 0o700); } catch (err) {
      throw new Error(`[op-audit] cannot enforce 0o700 on snapshot dir '${dir}': ${(err as Error).message}`);
    }
  }
}

/**
 * Atomic snapshot via VACUUM INTO to .tmp + integrity_check + rename.
 * Returns final path on success, throws on failure.
 * Filename has pid + uuid to avoid collisions in concurrent runs.
 */
// Issue #3B (2026-05-21): snapshot() now receives dbSource from caller (explicit, not derived).
// deriveDbSource() kept for backward compat with any external direct callers but is no longer
// used by withOpAudit itself.
function snapshot(opName: string, dbSource: string): string {
  if (!VALID_OPNAME.test(opName)) {
    throw new Error(`[op-audit] invalid opName '${opName}': must match ${VALID_OPNAME}`);
  }
  const dir = getValidatedSnapshotDir();
  ensureSnapshotDir(dir);

  // W2-3 (audit cleanup 04-26): refuse snapshot if free space < 2x current DB size (DoS prevention).
  // Multiple parallel reindex (e.g. 6 agents in nightly Phase 2) could otherwise fill /var/backups.
  try {
    const dbSize = existsSync(DB_PATH) ? statSync(DB_PATH).size : 0;
    if (dbSize > 0) {
      const stats = statfsSync(dir);
      const freeBytes = Number(stats.bavail) * Number(stats.bsize);
      const required = dbSize * 2;
      if (freeBytes < required) {
        throw new Error(`[op-audit] insufficient free space in '${dir}': ${freeBytes} < ${required} (2x DB size). Refusing snapshot.`);
      }
    }
  } catch (err) {
    // Re-throw if it's our own error; swallow statfs failures (cross-FS, container quirks) silently.
    if ((err as Error).message.startsWith('[op-audit] insufficient')) throw err;
  }

  // Fix CRIT-1/H1 + SEC HIGH #3 (audit 04-26): use full uuid (128-bit) for ts collision resistance
  // and to make the .tmp filename unpredictable enough to defeat racing between integrity_check and rename.
  const ts = new Date().toISOString().replace(/[-:T.]/g, '').substring(0, 14);
  const uid = randomUUID().replace(/-/g, '');
  // Fase 1 / Gap B (2026-05-15): qualify filename with dbSource for operational visibility.
  // Pattern: <opName>-<dbSource>-<ts>-<pid>-<uid>.db
  // E.g. reindex-main-..., compact-main-..., ocr-batch-cloud-main-...
  const finalPath = join(dir, `${opName}-${dbSource}-${ts}-${process.pid}-${uid}.db`);
  const tmpPath = `${finalPath}.tmp`;

  const db = getDb();
  try {
    // Fix H2: write to .tmp first
    db.prepare('VACUUM INTO ?').run(tmpPath);
  } catch (err) {
    try { if (existsSync(tmpPath)) unlinkSync(tmpPath); } catch {}
    throw new Error(`[op-audit] VACUUM INTO failed: ${(err as Error).message}`);
  }

  // Fix H2 + SEC HIGH #3 (audit 04-26): validate integrity AND size stability before rename.
  // Capture size pre-integrity, re-stat post, refuse if changed (TOCTOU swap detection).
  let integrityOk = false;
  // Fix SEC HIGH #3: capture size before integrity_check; re-verify after to detect mid-check swap.
  let preIntegritySize = 0;
  try { preIntegritySize = statSync(tmpPath).size; } catch (err) {
    throw new Error(`[op-audit] cannot stat tmp snapshot: ${(err as Error).message}`);
  }
  try {
    const verify = new Database(tmpPath, { readonly: true });
    try {
      const row = verify.prepare('PRAGMA integrity_check').get() as { integrity_check: string };
      integrityOk = row?.integrity_check === 'ok';
    } finally {
      verify.close();
    }
  } catch (err) {
    try { unlinkSync(tmpPath); } catch {}
    throw new Error(`[op-audit] integrity_check failed on snapshot: ${(err as Error).message}`);
  }

  if (!integrityOk) {
    try { unlinkSync(tmpPath); } catch {}
    throw new Error('[op-audit] snapshot integrity_check did not return ok');
  }

  // Fix SEC HIGH #3 (audit 04-26): re-stat post-integrity; refuse if size changed (mid-window swap).
  let postIntegritySize = 0;
  try { postIntegritySize = statSync(tmpPath).size; } catch (err) {
    throw new Error(`[op-audit] cannot re-stat tmp after integrity check: ${(err as Error).message}`);
  }
  if (postIntegritySize !== preIntegritySize) {
    try { unlinkSync(tmpPath); } catch {}
    throw new Error(`[op-audit] tmp size changed during integrity check (${preIntegritySize}→${postIntegritySize}) — refusing rename`);
  }

  // Atomic rename (same FS) — guaranteed valid file at finalPath or none
  renameSync(tmpPath, finalPath);
  try { chmodSync(finalPath, 0o600); } catch (err) {
    // Fix SEC HIGH #1 (audit 04-26): chmod failure on snapshot is security-critical (leak window).
    // throw to fail-closed; cross-FS users should set perms via dir mode + umask instead.
    throw new Error(`[op-audit] cannot enforce 0o600 on snapshot ${finalPath}: ${(err as Error).message}`);
  }
  return finalPath;
}

function ensureAuditTable(): void {
  const db = getDb();
  db.exec(`
    CREATE TABLE IF NOT EXISTS ops_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      op_name TEXT NOT NULL,
      started_at INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
      finished_at TEXT,
      duration_ms INTEGER,
      status TEXT NOT NULL DEFAULT 'running',
      affected_rows INTEGER,
      snapshot_path TEXT,
      snapshot_bytes INTEGER,
      schema_user_version INTEGER,
      pid INTEGER,
      error_message TEXT,
      notes TEXT,
      db_source TEXT NOT NULL DEFAULT 'unknown',
      db_path TEXT NOT NULL DEFAULT 'unknown',
      last_heartbeat_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_ops_audit_started ON ops_audit(started_at DESC);
    CREATE INDEX IF NOT EXISTS idx_ops_audit_status ON ops_audit(status, started_at DESC);
  `);
  // W2-1 (audit cleanup 04-26): append-only enforcement (CWE-693).
  // Allow INSERT (always) and UPDATE only when row is in 'running' state (final transition only).
  // DELETE blocked entirely. Compromised CLI cannot erase its trail.
  // NOTE: cron prune-pre-op-snapshots.sh deletes snapshot files but should NOT delete audit rows;
  // if rotation needed in future, use a status='pruned_from_disk' update path instead.
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS trg_ops_audit_no_delete
      BEFORE DELETE ON ops_audit
      BEGIN SELECT RAISE(ABORT, 'ops_audit is append-only (CWE-693 protection)'); END;
    CREATE TRIGGER IF NOT EXISTS trg_ops_audit_terminal_immutable
      BEFORE UPDATE ON ops_audit
      WHEN OLD.status IN ('success', 'failed', 'crashed')
      BEGIN SELECT RAISE(ABORT, 'ops_audit row in terminal state is immutable'); END;
  `);
  // Fix 2026-05-19: drop the broken started_at anti-backdating triggers.
  // Root cause: trg_ops_audit_started_at_server_side compared TEXT datetime('now') (column DEFAULT)
  // against INTEGER epoch-ms — SQLite TEXT > INTEGER always → RAISE(IGNORE) fired on EVERY INSERT,
  // silently swallowing all audit rows. trg_ops_audit_force_started_at had same type-mismatch flaw.
  // Replacement: INSERT now passes started_at as epoch ms explicitly; no trigger needed.
  db.exec(`
    DROP TRIGGER IF EXISTS trg_ops_audit_started_at_server_side;
    DROP TRIGGER IF EXISTS trg_ops_audit_force_started_at;
  `);
  // Fix 2026-05-21 (Issue #1C): enforce started_at is INTEGER on INSERT/UPDATE.
  // Prevents regression to TEXT formats (ISO datetime or float-as-text) which broke
  // /api/health.opsAudit.total_24h lexicographic comparisons. Uses RAISE(ABORT) — fail
  // loudly because TEXT values silently distort 24h window metrics. NULL allowed only on
  // UPDATE to support nullable finished_at-style patterns (not applicable here, but defensive).
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS trg_ops_audit_started_at_must_be_int
      BEFORE INSERT ON ops_audit
      FOR EACH ROW WHEN NEW.started_at IS NOT NULL AND typeof(NEW.started_at) != 'integer'
      BEGIN SELECT RAISE(ABORT, 'ops_audit.started_at must be INTEGER epoch ms — got non-integer value'); END;
    CREATE TRIGGER IF NOT EXISTS trg_ops_audit_started_at_must_be_int_upd
      BEFORE UPDATE OF started_at ON ops_audit
      FOR EACH ROW WHEN NEW.started_at IS NOT NULL AND typeof(NEW.started_at) != 'integer'
      BEGIN SELECT RAISE(ABORT, 'ops_audit.started_at must be INTEGER epoch ms — got non-integer value'); END;
  `);
}

/**
 * Heartbeat: update last_heartbeat_at em uma op em execução.
 * Fase 3 / Gap D (2026-05-15) — necessário pra watchdog detectar ops zombies
 * (>20min sem heartbeat = considered stale, candidata pra reap pelo ocr-watchdog).
 *
 * Usage no caller:
 *   const hbInterval = setInterval(() => recordHeartbeat('ocr-batch-cloud'), 5*60*1000);
 *   try { ... } finally { clearInterval(hbInterval); }
 *
 * Idempotent: UPDATE com WHERE filtro de op_name + pid + status='running' garante que
 * só toca a row da operação em curso (não interfere em outras ops paralelas).
 * Trigger trg_ops_audit_terminal_immutable permite UPDATE pq status atual é 'running'.
 */
export function recordHeartbeat(opName: string, pid: number = process.pid): void {
  const db = getDb();
  db.prepare(
    "UPDATE ops_audit SET last_heartbeat_at = datetime('now') WHERE op_name = ? AND status = 'running' AND pid = ?",
  ).run(opName, pid);
}

/**
 * Reaper: zombie 'running' rows from crashes (SIGKILL, OOM).
 * Run on startup of any caller importing this module via reapZombies().
 * Fix CRIT-4.
 */
export function reapZombies(): number {
  ensureAuditTable();
  const db = getDb();
  // Fix CODE HIGH #3 (audit 04-26): bump threshold from 1h to 6h (reindex on large DBs may legit
  // run >1h due to Gemini API latency) AND add JS-level PID liveness check via process.kill(pid, 0)
  // — only mark crashed if the recorded pid is no longer alive. Prevents reaping legit in-flight ops.
  // Note: started_at is now epoch ms (INTEGER) — compare against epoch ms threshold.
  const thresholdMs = Date.now() - 6 * 60 * 60 * 1000;
  // Fix 2026-05-21 (Issue #1B): defensive CAST for legacy TEXT rows. Same rationale as
  // getOpAuditStats() — historical rows with TEXT started_at would otherwise lexicographic-
  // compare to thresholdMs (INTEGER) and produce false positives in zombie reap.
  const candidates = db
    .prepare("SELECT id, pid FROM ops_audit WHERE status='running' AND CAST(started_at AS INTEGER) < ?")
    .all(thresholdMs) as Array<{ id: number; pid: number | null }>;
  let reaped = 0;
  const update = db.prepare(
    "UPDATE ops_audit SET status='crashed', finished_at=datetime('now'), error_message=COALESCE(error_message,'reaped: process died before completing (>6h, pid not alive)') WHERE id = ? AND status='running'",
  );
  for (const row of candidates) {
    let alive = false;
    if (row.pid && row.pid > 0) {
      try { process.kill(row.pid, 0); alive = true; } catch { alive = false; }
    }
    if (!alive) {
      const r = update.run(row.id);
      if (r.changes > 0) reaped++;
    }
  }
  return reaped;
}

/**
 * Fix SEC HIGH #5 (audit 04-26): redact secrets in error_message before persisting to ops_audit.
 * Audit table is exposed via /api/health.opsAudit; raw stack traces leak Gemini API keys
 * (AIza...), Anthropic OAuth tokens (sk-ant-oat-..., oat_...), and absolute paths.
 */
export function scrubSecrets(s: string): string {
  return s
    .replace(/AIza[A-Za-z0-9_-]{35}/g, 'AIza[REDACTED]')
    .replace(/sk-ant-(oat|api)[A-Za-z0-9_-]+/gi, 'sk-ant-$1[REDACTED]')
    .replace(/sk-[A-Za-z0-9_-]{20,}/g, 'sk-[REDACTED]')
    .replace(/oat_[A-Za-z0-9_-]{20,}/g, 'oat_[REDACTED]')
    .replace(/Bearer\s+[A-Za-z0-9_.-]+/gi, 'Bearer [REDACTED]')
    .replace(/\/root\/\.openclaw\/[^\s'"`)]+\.env/g, '/root/.openclaw/[REDACTED-PATH].env')
    .replace(/\/home\/[^/\s'"`)]+\/\.[^\s'"`)]+/g, '/home/[USER]/[REDACTED-DOTFILE]');
}

/**
 * Wraps a destructive DB operation with:
 *  1. Atomic VACUUM INTO snapshot (fail-closed by default)
 *  2. ops_audit row lifecycle: started → success | failed
 *  3. Secret-scrubbed error messages in audit rows
 *
 * Fix 2026-05-21 (Issue #3B): `options.db_source` is NOW REQUIRED.
 * Passing it explicitly prevents silent fallback to 'unknown' in byDbSource metrics.
 *
 * @example
 *   return withOpAudit('reindex', { db_source: 'main' }, async () => {
 *     const result = await _reindexImpl();
 *     return { affected_rows: result.chunks };
 *   });
 */
export async function withOpAudit<T extends OpResult>(
  opName: string,
  options: WithOpAuditOptions,
  fn: () => Promise<T>,
): Promise<T> {
  ensureAuditTable();
  const db = getDb();
  const t0 = Date.now();

  // Issue #3B (2026-05-21): use caller-provided db_source (REQUIRED).
  // db_path still derived from DB_PATH env for complete audit trail.
  const opDbSource = options.db_source;
  const opDbPath = DB_PATH;

  // Fix CRIT-2: fail-closed if snapshot fails (override only via explicit env var).
  // Pass opDbSource to snapshot() so the filename reflects the explicit db_source value
  // (not the legacy env-derived fallback). E.g. reindex-main-..., ocr-batch-cloud-main-...
  let snapshotPath: string;
  let snapshotBytes = 0;
  try {
    snapshotPath = snapshot(opName, opDbSource);
    try { snapshotBytes = statSync(snapshotPath).size; } catch {}
  } catch (err) {
    if (process.env.NOX_ALLOW_NO_SNAPSHOT === '1') {
      console.error(`[op-audit] WARN: snapshot failed but NOX_ALLOW_NO_SNAPSHOT=1, proceeding: ${(err as Error).message}`);
      snapshotPath = '';
    } else {
      throw new Error(`[op-audit] aborting ${opName}: ${(err as Error).message}. Set NOX_ALLOW_NO_SNAPSHOT=1 to override.`);
    }
  }

  const userVersion = (db.prepare('PRAGMA user_version').get() as { user_version: number })?.user_version ?? 0;

  // Fix 2026-05-19: pass started_at as explicit epoch ms INTEGER to avoid type-mismatch with
  // the (now-dropped) trigger that compared TEXT datetime vs INTEGER epoch-ms.
  // Also: check r.changes immediately — if 0, a future trigger swallowed the INSERT; fail loudly.
  //
  // Fix 2026-05-21 (Issue #1A): better-sqlite3 binds JS `number` as REAL (float), not INTEGER,
  // even when Number.isSafeInteger(n) === true. The historical `"1779242511707.0"` rows in
  // prod are literal proof: stored as REAL because Date.now() was bound as REAL. Wrap the
  // parameter in CAST(? AS INTEGER) so the trigger trg_ops_audit_started_at_must_be_int
  // (typeof='integer' check) accepts the value AND the on-disk storage is INTEGER.
  const insertResult = db
    .prepare(
      "INSERT INTO ops_audit (op_name, started_at, snapshot_path, snapshot_bytes, schema_user_version, pid, status, db_source, db_path) VALUES (?, CAST(? AS INTEGER), ?, ?, ?, ?, 'running', ?, ?)",
    )
    .run(opName, t0, snapshotPath || null, snapshotBytes || null, userVersion, process.pid, opDbSource, opDbPath);

  if (insertResult.changes === 0) {
    // A trigger (present or future) silently swallowed the INSERT via RAISE(IGNORE).
    // Fail loudly rather than proceed with a phantom auditId.
    throw new Error(`[op-audit] INSERT into ops_audit returned changes=0 for op '${opName}' — trigger may have blocked it. Aborting.`);
  }

  const auditId = Number(insertResult.lastInsertRowid);
  console.log(`[op-audit] ${opName} started (snapshot: ${snapshotPath || 'NONE'}, audit_id=${auditId})`);

  try {
    const result = await fn();
    // W2-11 (audit cleanup 04-26): validate fn() returned an object before accessing fields.
    // Prevents row-stuck-running if a caller mistakenly passes a sync fn returning undefined,
    // or fn returns a primitive that crashes `.affected_rows` access.
    if (!result || typeof result !== 'object') {
      throw new Error(`[op-audit] opFn must return OpResult object, got ${typeof result}`);
    }
    const duration = Date.now() - t0;
    db.prepare(
      "UPDATE ops_audit SET finished_at = datetime('now'), duration_ms = ?, status = 'success', affected_rows = ?, notes = ? WHERE id = ?",
    ).run(duration, result.affected_rows ?? null, result.notes ?? null, auditId);
    console.log(`[op-audit] ${opName} success in ${duration}ms (affected=${result.affected_rows ?? 'n/a'})`);
    return result;
  } catch (err) {
    const duration = Date.now() - t0;
    // Fix SEC HIGH #5: scrub secrets BEFORE truncate, then truncate.
    const rawMsg = err instanceof Error ? (err.stack || err.message) : String(err);
    const scrubbed = scrubSecrets(rawMsg);
    const msg = scrubbed.length > 2000 ? scrubbed.substring(0, 1980) + '…[truncated]' : scrubbed;
    db.prepare(
      "UPDATE ops_audit SET finished_at = datetime('now'), duration_ms = ?, status = 'failed', error_message = ? WHERE id = ?",
    ).run(duration, msg, auditId);
    console.error(`[op-audit] ${opName} FAILED in ${duration}ms — snapshot preserved: ${snapshotPath || 'NONE'}`);
    throw err;
  }
}

/**
 * Stats helper for /api/health (Fix L2: single transaction for consistent reads).
 */
export interface OpsAuditStats {
  total_24h: number;
  success_24h: number;
  failed_24h: number;
  crashed_24h: number;
  last_op: { op_name: string; status: string; finished_at: string } | null;
  // Fase 5 / Gap C-visibility (2026-05-15): breakdown por DB de origem.
  // Mapa db_source → contadores por status (24h window).
  byDbSource: Record<string, { total: number; success: number; failed: number; crashed: number; running: number }>;
}

export function getOpAuditStats(): OpsAuditStats {
  ensureAuditTable();
  const db = getDb();
  // Note: started_at is now epoch ms INTEGER. 24h window = now - 86400000 ms.
  const since24h = Date.now() - 86400 * 1000;
  // Fix 2026-05-21 (Issue #1B): defensive CAST(started_at AS INTEGER) — historical rows have
  // mixed TEXT formats (ISO datetime + epoch-ms-as-text) because the prod ops_audit table
  // was created BEFORE the INTEGER schema change in ensureAuditTable (CREATE TABLE IF NOT EXISTS
  // doesn't migrate existing tables). Without CAST, SQLite lexicographic compare retains old rows
  // as "24h" forever. Migration script normalizes per-cell values to INTEGER; CAST is
  // belt-and-suspenders against any future TEXT regression.
  //
  // Fix 2026-05-21 (Issue #3A): filter out test ops (op_name LIKE 'test-%') from health metrics.
  // Test fixtures populate ops_audit without isolation; rows pollute byDbSource=unknown bucket.
  // This is a reporting-layer filter; no DB mutation.
  const txn = db.transaction(() => {
    const total = db.prepare("SELECT COUNT(*) AS c FROM ops_audit WHERE CAST(started_at AS INTEGER) >= ? AND op_name NOT LIKE 'test-%'").get(since24h) as { c: number };
    const success = db.prepare("SELECT COUNT(*) AS c FROM ops_audit WHERE CAST(started_at AS INTEGER) >= ? AND status = 'success' AND op_name NOT LIKE 'test-%'").get(since24h) as { c: number };
    const failed = db.prepare("SELECT COUNT(*) AS c FROM ops_audit WHERE CAST(started_at AS INTEGER) >= ? AND status = 'failed' AND op_name NOT LIKE 'test-%'").get(since24h) as { c: number };
    const crashed = db.prepare("SELECT COUNT(*) AS c FROM ops_audit WHERE CAST(started_at AS INTEGER) >= ? AND status = 'crashed' AND op_name NOT LIKE 'test-%'").get(since24h) as { c: number };
    const lastOp = db.prepare("SELECT op_name, status, finished_at FROM ops_audit WHERE finished_at IS NOT NULL AND op_name NOT LIKE 'test-%' ORDER BY id DESC LIMIT 1").get() as { op_name: string; status: string; finished_at: string } | undefined;

    // Fase 5 / Gap C-visibility: agregar por (db_source, status) em uma única query.
    // COALESCE pra rows legacy com db_source NULL (não devem existir pós-v.17 migration, mas defesa).
    const breakdown = db
      .prepare(
        `SELECT COALESCE(db_source, 'unknown') AS db_source, status, COUNT(*) AS c
         FROM ops_audit
         WHERE CAST(started_at AS INTEGER) >= ?
           AND op_name NOT LIKE 'test-%'
         GROUP BY db_source, status`,
      )
      .all(since24h) as Array<{ db_source: string; status: string; c: number }>;

    const byDbSource: OpsAuditStats['byDbSource'] = {};
    for (const row of breakdown) {
      const src = row.db_source || 'unknown';
      if (!byDbSource[src]) byDbSource[src] = { total: 0, success: 0, failed: 0, crashed: 0, running: 0 };
      byDbSource[src].total += row.c;
      if (row.status === 'success') byDbSource[src].success += row.c;
      else if (row.status === 'failed') byDbSource[src].failed += row.c;
      else if (row.status === 'crashed') byDbSource[src].crashed += row.c;
      else if (row.status === 'running') byDbSource[src].running += row.c;
    }

    return {
      total_24h: total.c,
      success_24h: success.c,
      failed_24h: failed.c,
      crashed_24h: crashed.c,
      last_op: lastOp ?? null,
      byDbSource,
    };
  });
  return txn();
}

/**
 * safeRestore — recovery helper que faz restore seguro removendo WAL/SHM órfãos
 * e validando schema_user_version. Fix H3 (WAL/SHM órfãos) + H7 (schema mismatch).
 *
 * Caller deve PARAR serviços que escrevem no DB ANTES de chamar:
 *   systemctl stop nox-mem-api nox-mem-watch openclaw-gateway
 *   node -e "import('./dist/lib/op-audit.js').then(m => m.safeRestore('/var/backups/nox-mem/pre-op/reindex-XXX.db'))"
 *   systemctl start nox-mem-api nox-mem-watch openclaw-gateway
 */
export function safeRestore(snapshotPath: string, opts: { force?: boolean } = {}): { ok: boolean; warnings: string[] } {
  const warnings: string[] = [];

  // Fix SEC HIGH #4 (audit 04-26): validate snapshotPath against ALLOWED_PREFIXES to prevent
  // attacker-controlled DB injection. Same guard as withOpAudit's snapshot dir, applied to argument.
  const resolvedSnap = resolve(snapshotPath);
  const snapAllowed = ALLOWED_PREFIXES.some((p) => resolvedSnap.startsWith(p));
  if (!snapAllowed) {
    throw new Error(`[op-audit] safeRestore refuses snapshot '${resolvedSnap}': must be inside ${ALLOWED_PREFIXES.join(' or ')}`);
  }

  // Also validate DB_PATH (env-overridable via NOX_DB_PATH) against same allowlist.
  const resolvedDb = resolve(DB_PATH);
  const dbAllowed = ALLOWED_PREFIXES.some((p) => resolvedDb.startsWith(p));
  if (!dbAllowed) {
    throw new Error(`[op-audit] safeRestore refuses target DB_PATH '${resolvedDb}': must be inside ${ALLOWED_PREFIXES.join(' or ')}`);
  }

  if (!existsSync(snapshotPath)) throw new Error(`snapshot not found: ${snapshotPath}`);

  // Validate snapshot integrity first
  const verify = new Database(snapshotPath, { readonly: true });
  let snapshotVersion = 0;
  try {
    const integrity = verify.prepare('PRAGMA integrity_check').get() as { integrity_check: string };
    if (integrity?.integrity_check !== 'ok') {
      throw new Error(`snapshot integrity_check failed: ${integrity?.integrity_check}`);
    }
    snapshotVersion = (verify.prepare('PRAGMA user_version').get() as { user_version: number })?.user_version ?? 0;
  } finally {
    verify.close();
  }

  // Schema version check
  if (existsSync(DB_PATH)) {
    const current = new Database(DB_PATH, { readonly: true });
    try {
      const currentVersion = (current.prepare('PRAGMA user_version').get() as { user_version: number })?.user_version ?? 0;
      if (currentVersion !== snapshotVersion) {
        const msg = `schema mismatch: current user_version=${currentVersion}, snapshot=${snapshotVersion}`;
        if (!opts.force) throw new Error(`${msg}. Pass { force: true } to restore anyway.`);
        warnings.push(msg);
      }
    } finally {
      current.close();
    }
  }

  // W2-4 (audit cleanup 04-26): order matters — restore main DB FIRST, then unlink WAL/SHM.
  // Old order (WAL/SHM unlink before rename) left DB inconsistent if process died mid-restore:
  // main file = old, WAL/SHM = gone. New order ensures main file is always consistent with WAL state.

  // Step 1: VACUUM INTO tmp + atomic rename to DB_PATH
  const tmpDest = `${DB_PATH}.restore-tmp`;
  try {
    const srcDb = new Database(snapshotPath, { readonly: true });
    try {
      srcDb.prepare('VACUUM INTO ?').run(tmpDest);
    } finally {
      srcDb.close();
    }
    renameSync(tmpDest, DB_PATH);
  } catch (err) {
    try { if (existsSync(tmpDest)) unlinkSync(tmpDest); } catch {}
    throw err;
  }

  // Step 2: only NOW unlink WAL/SHM (atomic — main DB already consistent)
  for (const suffix of ['-wal', '-shm']) {
    const sidecar = `${DB_PATH}${suffix}`;
    if (existsSync(sidecar)) {
      try { unlinkSync(sidecar); warnings.push(`removed stale ${suffix} file`); } catch (err) { warnings.push(`failed to remove ${suffix}: ${(err as Error).message}`); }
    }
  }

  return { ok: true, warnings };
}
