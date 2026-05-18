/**
 * L2 T6 — Shadow-mode wrapper.
 *
 * Honors CLAUDE.md regra crítica #5 (ranking changes need ≥7d shadow baseline)
 * + spec regra de ouro #1 (shadow-first; default disabled).
 *
 * Mode selector lives in env `NOX_CONFLICT_MODE`:
 *   - 'disabled' (default) — no detection runs, no rows inserted, no telemetry.
 *     `runConflictPass` returns synthetic { mode:'disabled' } with zero counts.
 *   - 'shadow' — detection runs, conflict_audit rows inserted with
 *     shadow_mode=1, NO surface annotations on retrieved relations.
 *   - 'active' — detection runs, conflict_audit rows inserted with
 *     shadow_mode=0, surface annotations available via `annotateRelations`
 *     for callers (e.g. P1 answer pipeline) to display "⚠ conflicting info".
 *
 * Telemetry: `getShadowTelemetry(db)` exposes status counts + last scan ts +
 * mode. Plug into `/api/health.conflictDetection`.
 */

import { detectDirectConflicts } from "./detector-direct.js";
import { collectEvidence } from "./evidence.js";
import { recordConflict, statusCounts } from "./audit-writer.js";
import type { DBHandle } from "./db.js";
import type {
  Conflict,
  ConflictMode,
  ConflictStatus,
  DetectorOptions,
  VariantRelation,
} from "./types.js";
import { DEFAULT_CONFLICT_MODE } from "./types.js";

export interface PassResult {
  mode: ConflictMode;
  scanned_at: number;
  detected: number;
  recorded: number;
  deduplicated: number;
  /** New audit row ids (excludes dedupe hits). */
  audit_ids: number[];
}

export interface ShadowTelemetry {
  mode: ConflictMode;
  last_scan_at: number | null;
  counts: Record<ConflictStatus, number>;
  /** True when an `active` row exists — informational only. */
  has_active_rows: boolean;
}

/**
 * Resolve mode from env (with explicit override option). Default: 'disabled'.
 */
export function resolveMode(envOverride?: string): ConflictMode {
  const raw = (envOverride ?? process.env.NOX_CONFLICT_MODE ?? "").toLowerCase().trim();
  if (raw === "shadow") return "shadow";
  if (raw === "active") return "active";
  if (raw === "disabled" || raw === "") return DEFAULT_CONFLICT_MODE;
  // Unknown value → safe default 'disabled' (avoid surprise activation).
  return "disabled";
}

let _lastScanAt: number | null = null;

/**
 * Run a single conflict-detection pass under the current mode.
 *
 * - 'disabled' → no DB writes, returns empty result
 * - 'shadow' / 'active' → detect + record + (active only) annotate
 */
export function runConflictPass(
  db: DBHandle,
  opts: DetectorOptions = {},
  modeOverride?: ConflictMode,
): PassResult {
  const mode = modeOverride ?? resolveMode();
  const now = Date.now();

  if (mode === "disabled") {
    return {
      mode,
      scanned_at: now,
      detected: 0,
      recorded: 0,
      deduplicated: 0,
      audit_ids: [],
    };
  }

  const conflicts = detectDirectConflicts(db, { ...opts, scan_ts: now });
  const shadow = mode === "shadow" ? 1 : 0;
  const auditIds: number[] = [];
  let recorded = 0;
  let dedup = 0;
  for (const c of conflicts) {
    const ev = collectEvidence(db, c);
    const r = recordConflict(db, c, ev, { shadow_mode: shadow });
    if (r.deduplicated) {
      dedup++;
    } else {
      recorded++;
      auditIds.push(r.id);
    }
  }
  _lastScanAt = now;
  return {
    mode,
    scanned_at: now,
    detected: conflicts.length,
    recorded,
    deduplicated: dedup,
    audit_ids: auditIds,
  };
}

/**
 * Annotate a set of relation ids with conflict flags. In shadow mode this is
 * a no-op (returns empty Set). In active mode, returns the subset of input
 * relation ids that appear in any OPEN conflict_audit row.
 *
 * Callers (e.g. P1 answer composer) pass the candidate set; only flagged ids
 * are surfaced as "⚠ conflicting info" in the response payload.
 */
export function annotateRelations(
  db: DBHandle,
  relationIds: readonly number[],
  modeOverride?: ConflictMode,
): Set<number> {
  const mode = modeOverride ?? resolveMode();
  if (mode !== "active") return new Set();
  if (relationIds.length === 0) return new Set();

  // Pull all OPEN audit rows once — typical scale is dozens to low hundreds.
  // For large scans we'd push into SQL; v1 keeps the API simple.
  const rows = db
    .prepare(
      `SELECT target_relation_ids FROM conflict_audit WHERE status = ? LIMIT 500`,
    )
    .all("open") as Array<{ target_relation_ids: string | number[] }>;

  const flagged = new Set<number>();
  for (const r of rows) {
    const ids =
      typeof r.target_relation_ids === "string"
        ? (JSON.parse(r.target_relation_ids) as number[])
        : r.target_relation_ids;
    for (const id of ids) {
      if (relationIds.includes(id)) flagged.add(id);
    }
  }
  return flagged;
}

/**
 * Telemetry surface — drop into /api/health.conflictDetection.
 */
export function getShadowTelemetry(
  db: DBHandle,
  modeOverride?: ConflictMode,
): ShadowTelemetry {
  const mode = modeOverride ?? resolveMode();
  const counts = statusCounts(db);
  const hasActiveRows = mode === "active";
  return {
    mode,
    last_scan_at: _lastScanAt,
    counts,
    has_active_rows: hasActiveRows,
  };
}

/** Test-only: reset module-level scan timestamp. */
export function _resetLastScanForTests(): void {
  _lastScanAt = null;
}

/** Surface conflicting variants for a relation id list — returns the variants
 *  bundled with their conflict id. Useful for richer UI than a simple Set. */
export function getConflictsForRelations(
  db: DBHandle,
  relationIds: readonly number[],
): Array<{ conflict_id: number; predicate: string; variants: VariantRelation[] }> {
  if (relationIds.length === 0) return [];
  const rows = db
    .prepare(
      `SELECT * FROM conflict_audit WHERE status = ? LIMIT 500`,
    )
    .all("open") as Array<Record<string, unknown>>;
  const out: Array<{ conflict_id: number; predicate: string; variants: VariantRelation[] }> = [];
  for (const r of rows) {
    const trIds: number[] =
      typeof r.target_relation_ids === "string"
        ? JSON.parse(r.target_relation_ids as string)
        : (r.target_relation_ids as number[]);
    const overlap = trIds.some((id) => relationIds.includes(id));
    if (!overlap) continue;
    const variants: VariantRelation[] =
      typeof r.variants === "string"
        ? JSON.parse(r.variants as string)
        : (r.variants as VariantRelation[]);
    out.push({
      conflict_id: Number(r.id),
      predicate: String(r.predicate),
      variants,
    });
  }
  return out;
}

/** Build an instance to share state across modules — pattern used by API. */
export interface ConflictContext {
  mode: ConflictMode;
  db: DBHandle;
}

export function makeConflictContext(db: DBHandle): ConflictContext {
  return { db, mode: resolveMode() };
}
