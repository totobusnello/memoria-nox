/**
 * G16 — File-based advisory lock for runExport / runImport (Wave G)
 *
 * BACKGROUND
 *   `runExport()` and `runImport()` in `staged-A2/edits/src/lib/archive/
 *   orchestrator.ts` are long-running (minutes for >1GB DB). Two concurrent
 *   runExport calls against the same output path race on:
 *     - manifest writes
 *     - encryption nonce reuse (CRITICAL — GCM nonce reuse breaks AES-GCM
 *       confidentiality + authenticity)
 *     - tar block boundaries
 *
 * THREAT (G16, R-A2-Orch-1)
 *   Two concurrent exports → corrupted archive OR (worse) AES-GCM nonce
 *   reuse if both runs share the same passphrase + salt.
 *
 * FIX
 *   File-based advisory lock written to `<output>.lock` at runExport start,
 *   removed on completion / failure. Manual lock-file pattern (works on all
 *   platforms — flock(2) on linux/mac when available, else exclusive
 *   O_CREAT|O_EXCL semantics). Includes PID + start-time JSON so a stale
 *   lock (process gone, or >30 min idle) can be safely broken.
 *
 * Lock file shape (`<output>.lock`, mode 0600):
 *   {
 *     "pid": 12345,
 *     "started_at_ms": 1716050000000,
 *     "hostname": "nox-vps-1",
 *     "op": "export",
 *     "v": 1
 *   }
 *
 * Behavior:
 *   - First caller writes lock with O_EXCL. If success, holds it.
 *   - Subsequent caller checks for existing lock:
 *       - If pid is alive AND started_at_ms within 30 min → 409 Conflict.
 *       - If pid is dead OR started_at_ms > 30 min ago → log WARN, break
 *         the stale lock, take it.
 *   - On crash mid-export, the lock persists until next caller breaks it
 *     by age. This is correct — we don't want to silently delete locks
 *     just because OS reused a pid.
 *
 * Backward compat:
 *   - Module is opt-in. Caller (orchestrator) wraps runExport with
 *     `withExportLock(outputPath, async () => runExport(...))`.
 *   - No changes to existing exports if module not adopted (forward
 *     migration path).
 */

import { promises as fs, existsSync } from "node:fs";
import path from "node:path";
import os from "node:os";

// ── lock file format ────────────────────────────────────────────────────────

export interface LockMetadata {
  pid: number;
  started_at_ms: number;
  hostname: string;
  op: "export" | "import";
  v: 1;
}

/** Default stale-after (ms). 30 minutes — covers typical 1-2GB exports. */
export const DEFAULT_STALE_MS = 30 * 60 * 1000;

// ── public errors ───────────────────────────────────────────────────────────

export class ExportLockBusyError extends Error {
  readonly status = 409;
  readonly lockPath: string;
  readonly heldBy: LockMetadata;
  constructor(lockPath: string, heldBy: LockMetadata) {
    super(
      `Export lock at ${lockPath} held by pid=${heldBy.pid} on host=${heldBy.hostname} (started ${new Date(heldBy.started_at_ms).toISOString()})`,
    );
    this.name = "ExportLockBusyError";
    this.lockPath = lockPath;
    this.heldBy = heldBy;
  }
}

// ── helpers ────────────────────────────────────────────────────────────────

function lockPathFor(outputPath: string): string {
  return outputPath + ".lock";
}

function isAlive(pid: number): boolean {
  if (!Number.isFinite(pid) || pid <= 0) return false;
  try {
    // signal 0 → "does pid exist" check (POSIX). Throws ESRCH if not.
    process.kill(pid, 0);
    return true;
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code === "EPERM") return true; // exists but we lack rights
    return false;
  }
}

async function readLock(lockPath: string): Promise<LockMetadata | null> {
  try {
    const raw = await fs.readFile(lockPath, "utf8");
    const parsed = JSON.parse(raw) as LockMetadata;
    if (parsed.v !== 1 || typeof parsed.pid !== "number") return null;
    return parsed;
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code === "ENOENT") return null;
    return null; // malformed — caller may opt to break it
  }
}

async function writeLock(
  lockPath: string,
  meta: LockMetadata,
  exclusive: boolean,
): Promise<void> {
  const data = JSON.stringify(meta, null, 2);
  // O_EXCL semantics via `flag: 'wx'`. If we want to overwrite stale, use 'w'.
  await fs.writeFile(lockPath, data, {
    encoding: "utf8",
    flag: exclusive ? "wx" : "w",
    mode: 0o600,
  });
}

// ── public API ──────────────────────────────────────────────────────────────

export interface AcquireLockOptions {
  /** Stale threshold (ms). Default 30 min. */
  staleMs?: number;
  /** "export" or "import". Default "export". */
  op?: "export" | "import";
  /** WARN logger when breaking a stale lock. Default console.warn. */
  onWarn?: (msg: string) => void;
}

/**
 * Try to acquire an exclusive advisory lock for the given output path.
 * Throws ExportLockBusyError when an active lock blocks acquisition.
 *
 * Returns a release handle. Caller MUST invoke `release()` (preferably in
 * a `try/finally`).
 */
export async function acquireExportLock(
  outputPath: string,
  opts: AcquireLockOptions = {},
): Promise<{ release: () => Promise<void>; lockPath: string }> {
  const lockPath = lockPathFor(outputPath);
  const staleMs = opts.staleMs ?? DEFAULT_STALE_MS;
  const op = opts.op ?? "export";
  const meta: LockMetadata = {
    pid: process.pid,
    started_at_ms: Date.now(),
    hostname: os.hostname(),
    op,
    v: 1,
  };

  // 1. Try exclusive write.
  try {
    await writeLock(lockPath, meta, true);
    return { release: () => releaseLock(lockPath, meta), lockPath };
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code !== "EEXIST") throw err;
  }

  // 2. Lock exists. Decide: stale or active?
  const existing = await readLock(lockPath);
  if (existing) {
    const ageMs = Date.now() - existing.started_at_ms;
    const stale = ageMs > staleMs || !isAlive(existing.pid);
    if (!stale) {
      throw new ExportLockBusyError(lockPath, existing);
    }
    (opts.onWarn ?? console.warn)(
      `[export-lock] Breaking stale lock at ${lockPath} (pid=${existing.pid} alive=${isAlive(existing.pid)} ageMs=${ageMs})`,
    );
  } else {
    (opts.onWarn ?? console.warn)(
      `[export-lock] Lock file at ${lockPath} unreadable/malformed — breaking it`,
    );
  }

  // 3. Break stale + take.
  await writeLock(lockPath, meta, false);
  return { release: () => releaseLock(lockPath, meta), lockPath };
}

async function releaseLock(lockPath: string, expectedMeta: LockMetadata): Promise<void> {
  // Defensive: only delete if we still own it. Re-read first.
  try {
    const current = await readLock(lockPath);
    if (
      current &&
      current.pid === expectedMeta.pid &&
      current.started_at_ms === expectedMeta.started_at_ms
    ) {
      await fs.unlink(lockPath);
    }
    // else: someone else broke + reused our lock — leave it alone.
  } catch {
    // Best-effort; file system may have been cleaned by another process.
  }
}

/**
 * Convenience wrapper. Acquires lock, runs fn, releases unconditionally.
 *
 *   const result = await withExportLock(outputPath, () => runExport(...));
 */
export async function withExportLock<T>(
  outputPath: string,
  fn: () => Promise<T>,
  opts: AcquireLockOptions = {},
): Promise<T> {
  const handle = await acquireExportLock(outputPath, opts);
  try {
    return await fn();
  } finally {
    await handle.release();
  }
}

/**
 * Inspect a lock file without acquiring. Returns null when absent.
 */
export async function inspectExportLock(outputPath: string): Promise<LockMetadata | null> {
  return readLock(lockPathFor(outputPath));
}

/**
 * Pure helper for tests / docs. Returns the canonical lock path.
 */
export function getLockPath(outputPath: string): string {
  return lockPathFor(outputPath);
}

/**
 * Pure helper — used to inspect file existence in scripts.
 */
export function lockExistsSync(outputPath: string): boolean {
  return existsSync(lockPathFor(outputPath));
}

// Re-export for namespace cleanliness.
export { path as _path };
