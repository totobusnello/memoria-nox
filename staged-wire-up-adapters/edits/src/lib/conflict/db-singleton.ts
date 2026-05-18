/**
 * src/lib/conflict/db-singleton.ts — Wave O T4 (L2 piece).
 *
 * Wire-up.ts expects `lib/conflict/db.js::getConflictDb(): DBHandle`.
 * staged-L2 ships only the `DBHandle` interface — no factory. This adapter
 * adds the factory.
 *
 * Apply step appends one line to staged-L2's `db.ts`:
 *
 *   export { getConflictDb, resetConflictDbForTests } from "./db-singleton.js";
 *
 * Resolution path: `getConflictDb()` delegates to `deps-registry.getDb()`,
 * sharing the same nox-mem.db connection used by every other pillar.
 *
 * Schema dep: L2 reads/writes `conflict_audit` (created by L2 migration v18).
 * When the table is missing the upstream `dispatchConflictApi` returns 500;
 * the wire-up's G5 sanitizer catches it and returns a redacted 500.
 *
 * Build-time: ESM TLA loads deps-registry at module init.
 */

import { getDb } from "../deps/deps-registry.js";

type DBHandle = unknown; // structural — defined by staged-L2's db.ts

let _override: DBHandle | null = null;

/**
 * Sync accessor — wire-up calls `dbMod.getConflictDb()` synchronously.
 * We warm up the singleton in deps-registry at first call.
 *
 * Returns `null` when no DB is available; wire-up's null-check then emits
 * 503 not_implemented.
 */
let _cached: DBHandle | null | undefined;

export function getConflictDb(): DBHandle | null {
  if (_override !== null) return _override;
  if (_cached !== undefined) return _cached ?? null;
  // Kick off the async resolve; the first call may return null until the
  // warmup completes. Production startup invokes `await ensureConflictDb()`
  // in the API boot sequence.
  void warmup();
  return _cached ?? null;
}

async function warmup(): Promise<void> {
  if (_cached !== undefined) return;
  const db = await getDb();
  _cached = db;
}

/** Warm up the singleton at boot. Returns the handle once ready. */
export async function ensureConflictDb(): Promise<DBHandle | null> {
  await warmup();
  return _cached ?? null;
}

// ─── Test seam ───────────────────────────────────────────────────────────────

/** Inject a fake DB for tests. Pass null to clear. */
export function __setConflictDbForTests(db: DBHandle | null): void {
  _override = db;
}

export function resetConflictDbForTests(): void {
  _override = null;
  _cached = undefined;
}
