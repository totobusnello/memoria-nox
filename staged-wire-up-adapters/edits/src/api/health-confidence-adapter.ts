/**
 * src/api/health-confidence-adapter.ts — Wave O T4 (L3 health piece).
 *
 * Wire-up.ts (#92, line 446) does:
 *
 *     const mod = await tryImport("./health-confidence.js");
 *     if (!mod?.handleHealthConfidence) writeJson(res, ..., 503);
 *     const out = await mod.handleHealthConfidence();
 *
 * staged-L3 ships `computeConfidenceHealth(db, rankingMode?)` — not the
 * arg-free `handleHealthConfidence()` the wire-up needs. This adapter wraps
 * the upstream function with deps-registry's DB singleton.
 *
 * Apply step appends to staged-L3's `health-confidence.ts`:
 *
 *   export { handleHealthConfidence } from "./health-confidence-adapter.js";
 *
 * The adapter returns `{status, body}` per the wire-up contract.
 */

import { getDb } from "../lib/deps/deps-registry.js";

interface ConfidenceHealthResponse {
  status: number;
  body: unknown;
}

/**
 * Wire-up-shaped handler. No args — pulls DB from registry; returns 503 when
 * the L3 health module or the DB is unavailable.
 */
export async function handleHealthConfidence(): Promise<ConfidenceHealthResponse> {
  const db = await getDb();
  if (!db) {
    return {
      status: 503,
      body: { error: "not_implemented", reason: "DB unavailable" },
    };
  }
  // String indirection — `./health-confidence.js` is co-located only after
  // staged-L3 is rsynced; here in the staged-wire-up-adapters tree the file
  // isn't present, so we let the dynamic import fail and return 503.
  const HC_SPEC = "./health-confidence.js";
  let mod: any;
  try {
    mod = await import(HC_SPEC);
  } catch {
    return {
      status: 503,
      body: {
        error: "not_implemented",
        reason: "L3 health-confidence module not deployed",
      },
    };
  }
  const compute = mod.computeConfidenceHealth ?? mod.default?.computeConfidenceHealth;
  if (typeof compute !== "function") {
    return {
      status: 503,
      body: {
        error: "not_implemented",
        reason: "computeConfidenceHealth export missing",
      },
    };
  }
  try {
    const slice = compute(db);
    return { status: 200, body: { confidence: slice } };
  } catch (err) {
    return {
      status: 500,
      body: {
        error: "internal_error",
        message: (err as Error).message ?? "compute failed",
      },
    };
  }
}
