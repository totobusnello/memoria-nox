/**
 * src/api/server-deps-l2-l3.ts — Wave O T4: L2 + L3 combined runtime adapter.
 *
 * Closes the 503 gap for:
 *
 *   L2: GET  /api/conflict
 *   L2: GET  /api/conflict/:id
 *   L2: POST /api/conflict/:id/resolve
 *   L3: POST /api/chunk/:id/mark
 *   L3: POST /api/chunk/:id/supersede
 *   L3: GET  /api/health/confidence
 *
 * Wire-up.ts already lazy-imports each pillar separately:
 *
 *   const dbMod   = await tryImport("../lib/conflict/db.js");
 *   const shimMod = await tryImport("../lib/confidence/db-shim.js");
 *   const healthMod = await tryImport("./health-confidence.js");
 *
 * The work in this adapter:
 *   - Re-export the singletons (`getConflictDb`, `getConfidenceDb`,
 *     `handleHealthConfidence`) under a single import path so callers /
 *     deploy scripts can validate "L2+L3 deps present" with one require.
 *   - Validate that `conflict_audit` + `chunks.confidence`/`chunks.provenance_kind`
 *     columns exist before exposing the DB. When schema v18/v19 hasn't
 *     migrated, return `null` so wire-up surfaces 503 not_implemented.
 *
 * The two pillars share `nox-mem.db` (singleton from deps-registry) — there
 * is exactly ONE DB connection across L2 + L3.
 */

import { getDb } from "../lib/deps/deps-registry.js";

export {
  getConflictDb,
  ensureConflictDb,
  resetConflictDbForTests,
  __setConflictDbForTests,
} from "../lib/conflict/db-singleton.js";

export {
  getConfidenceDb,
  ensureConfidenceDb,
  resetConfidenceDbForTests,
  __setConfidenceDbForTests,
} from "../lib/confidence/db-shim-singleton.js";

export { handleHealthConfidence } from "./health-confidence-adapter.js";

// ─── Boot-time warm-up ────────────────────────────────────────────────────────

/**
 * Await this during API server boot (before the first request) to pre-warm the
 * L2 singleton. Mirrors the `buildP1Deps()` pattern used by /api/answer.
 *
 * What it does:
 *   1. Opens the better-sqlite3 connection via deps-registry (shared handle).
 *   2. Runs a schema readiness probe — warns to console if conflict_audit is
 *      missing (migration v18 hasn't run) so the operator sees it in logs.
 *   3. Returns { db, l2Ready } so api-server.ts can decide whether to mount
 *      the /api/conflict routes or skip them with a startup log line.
 *
 * If the boot call is skipped, getConflictDb() returns null on the first
 * synchronous call (warmup() is async, fires but hasn't settled yet) and
 * wire-up emits 503 not_implemented. Calling buildConflictDeps() once at
 * boot ensures the singleton is ready before any request arrives.
 */
export async function buildConflictDeps(): Promise<{
  db: unknown | null;
  l2Ready: boolean;
}> {
  const { ensureConflictDb } = await import("../lib/conflict/db-singleton.js");
  const db = await ensureConflictDb();
  if (!db) {
    return { db: null, l2Ready: false };
  }
  const readiness = await probeSchemaReadiness();
  if (!readiness.l2_ready) {
    console.warn(
      "[nox-mem] /api/conflict: conflict_audit table not found " +
        "(schema v18 migration pending). Endpoints will return 503 until migrated.",
    );
  }
  return { db, l2Ready: readiness.l2_ready };
}

// ─── Schema readiness probe ──────────────────────────────────────────────────

export interface SchemaReadiness {
  l2_ready: boolean;
  l3_ready: boolean;
  details: {
    has_conflict_audit: boolean;
    has_confidence_col: boolean;
    has_provenance_col: boolean;
    has_superseded_by_col: boolean;
    schema_version: number;
  };
}

/**
 * Check whether L2 + L3 tables/columns are present in the live DB.
 * Used by `/api/health` extension + deploy validation.
 */
export async function probeSchemaReadiness(): Promise<SchemaReadiness> {
  const db = await getDb();
  if (!db) {
    return {
      l2_ready: false,
      l3_ready: false,
      details: {
        has_conflict_audit: false,
        has_confidence_col: false,
        has_provenance_col: false,
        has_superseded_by_col: false,
        schema_version: 0,
      },
    };
  }
  let conflictAudit = false;
  try {
    const row = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conflict_audit'",
      )
      .get<{ name: string }>();
    conflictAudit = !!row;
  } catch {
    /* ignore */
  }
  let chunkCols: Array<{ name: string }> = [];
  try {
    chunkCols = db.prepare("PRAGMA table_info(chunks)").all<{ name: string }>();
  } catch {
    /* ignore */
  }
  const hasConf = chunkCols.some((c) => c.name === "confidence");
  const hasProv = chunkCols.some((c) => c.name === "provenance_kind");
  const hasSup = chunkCols.some((c) => c.name === "superseded_by");
  let schemaVer = 0;
  try {
    const r = db.prepare("PRAGMA user_version").get<{ user_version: number }>();
    if (r && typeof r.user_version === "number") schemaVer = r.user_version;
  } catch {
    /* ignore */
  }
  return {
    l2_ready: conflictAudit,
    l3_ready: hasConf && hasProv && hasSup,
    details: {
      has_conflict_audit: conflictAudit,
      has_confidence_col: hasConf,
      has_provenance_col: hasProv,
      has_superseded_by_col: hasSup,
      schema_version: schemaVer,
    },
  };
}
