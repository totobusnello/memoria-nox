/**
 * Placeholder migration v18 → v19.
 *
 * Real v19 schema lands later. This shim demonstrates the contract:
 *   - takes rows in v18 shape
 *   - returns rows in v19 shape
 *   - idempotent (re-run = no-op)
 *
 * Until v19 ships, this is a literal identity transform so the migration
 * chain can be wired and tested end-to-end with synthetic version numbers.
 */

import { ChunkRow } from "../types.js";

export const MIGRATION_ID = "v18_to_v19_placeholder";
export const FROM_VERSION = 18;
export const TO_VERSION = 19;

export function migrateChunks(rows: ChunkRow[]): ChunkRow[] {
  // Identity. Real migration logic will go here.
  return rows.map((r) => ({ ...r }));
}
