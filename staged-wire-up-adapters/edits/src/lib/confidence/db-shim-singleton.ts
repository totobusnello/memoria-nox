/**
 * src/lib/confidence/db-shim-singleton.ts — Wave O T4 (L3 piece).
 *
 * Wire-up.ts expects `lib/confidence/db-shim.js::getConfidenceDb(): Db`.
 * staged-L3 ships only the `Db` interface + `MockDb` for tests — no
 * factory. This adapter adds the factory.
 *
 * Apply step appends one line to staged-L3's `db-shim.ts`:
 *
 *   export { getConfidenceDb, resetConfidenceDbForTests } from "./db-shim-singleton.js";
 *
 * Identical lifecycle pattern to `lib/conflict/db-singleton.ts`. Shares the
 * deps-registry singleton.
 */

import { getDb } from "../deps/deps-registry.js";

type Db = unknown;

let _override: Db | null = null;
let _cached: Db | null | undefined;

export function getConfidenceDb(): Db | null {
  if (_override !== null) return _override;
  if (_cached !== undefined) return _cached ?? null;
  void warmup();
  return _cached ?? null;
}

async function warmup(): Promise<void> {
  if (_cached !== undefined) return;
  _cached = await getDb();
}

export async function ensureConfidenceDb(): Promise<Db | null> {
  await warmup();
  return _cached ?? null;
}

export function __setConfidenceDbForTests(db: Db | null): void {
  _override = db;
}

export function resetConfidenceDbForTests(): void {
  _override = null;
  _cached = undefined;
}
