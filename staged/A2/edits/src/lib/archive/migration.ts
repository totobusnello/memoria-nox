/**
 * T9 — Schema migration logic.
 *
 * Forward-only auto-migration. Backward attempts fail clearly with an
 * actionable message (per spec §6). Migrations live in `migrations/v<N>_to_v<N+1>.ts`
 * as pure data transforms (no DB side effects).
 *
 * Public API:
 *   - canImport(archive, current)  → { ok, reason? }
 *   - migrationPath(archive, current) → ordered list of step ids
 *   - migrateChunks(rows, from, to) → applies the chain to a chunk row set
 *
 * The actual import pipeline (T11) wires this to its serializers; here we
 * keep the planning + chunk-migration logic pure so it's trivially testable.
 */

import { ChunkRow, SchemaVersionError } from "./types.js";
import * as v18_to_v19 from "./migrations/v18_to_v19.js";

interface MigrationStep {
  id: string;
  from: number;
  to: number;
  migrateChunks: (rows: ChunkRow[]) => ChunkRow[];
}

const STEPS: MigrationStep[] = [
  {
    id: v18_to_v19.MIGRATION_ID,
    from: v18_to_v19.FROM_VERSION,
    to: v18_to_v19.TO_VERSION,
    migrateChunks: v18_to_v19.migrateChunks,
  },
];

const STEP_BY_FROM = new Map<number, MigrationStep>(
  STEPS.map((s) => [s.from, s]),
);

export type ImportabilityResult =
  | { ok: true }
  | { ok: false, reason: string };

export function canImport(
  archiveVersion: number,
  currentVersion: number,
): ImportabilityResult {
  if (!Number.isInteger(archiveVersion) || archiveVersion < 1) {
    return { ok: false, reason: `Invalid archive schema version: ${archiveVersion}` };
  }
  if (!Number.isInteger(currentVersion) || currentVersion < 1) {
    return { ok: false, reason: `Invalid current schema version: ${currentVersion}` };
  }
  if (archiveVersion === currentVersion) {
    return { ok: true };
  }
  if (archiveVersion > currentVersion) {
    return {
      ok: false,
      reason:
        `Archive schema version ${archiveVersion} is newer than current nox-mem schema version ${currentVersion}. ` +
        `Upgrade nox-mem before importing: \`npm install -g openclaw-nox-mem@latest\`.`,
    };
  }
  // archive < current — verify a chain exists
  let v = archiveVersion;
  while (v < currentVersion) {
    const step = STEP_BY_FROM.get(v);
    if (!step) {
      return {
        ok: false,
        reason:
          `No migration registered from v${v} to v${v + 1}. ` +
          `Chain v${archiveVersion} → v${currentVersion} cannot complete.`,
      };
    }
    v = step.to;
  }
  return { ok: true };
}

export function migrationPath(
  archiveVersion: number,
  currentVersion: number,
): string[] {
  const verdict = canImport(archiveVersion, currentVersion);
  if (!verdict.ok) throw new SchemaVersionError(verdict.reason);
  if (archiveVersion === currentVersion) return [];
  const path: string[] = [];
  let v = archiveVersion;
  while (v < currentVersion) {
    const step = STEP_BY_FROM.get(v)!;
    path.push(step.id);
    v = step.to;
  }
  return path;
}

/**
 * Apply the migration chain to a set of chunk rows. Each step is a pure
 * transform; if any step throws, the whole chain aborts and the error
 * propagates (T11 wraps in a transaction with rollback).
 */
export function migrateChunks(
  rows: ChunkRow[],
  archiveVersion: number,
  currentVersion: number,
): ChunkRow[] {
  const verdict = canImport(archiveVersion, currentVersion);
  if (!verdict.ok) throw new SchemaVersionError(verdict.reason);
  let current = rows;
  let v = archiveVersion;
  while (v < currentVersion) {
    const step = STEP_BY_FROM.get(v)!;
    try {
      current = step.migrateChunks(current);
    } catch (err) {
      throw new SchemaVersionError(
        `Migration ${step.id} failed at v${v}→v${step.to}: ${(err as Error).message}`,
      );
    }
    v = step.to;
  }
  return current;
}

/** Exposed for tests — list registered migrations. */
export function listMigrations(): ReadonlyArray<{
  id: string;
  from: number;
  to: number;
}> {
  return STEPS.map(({ id, from, to }) => ({ id, from, to }));
}
