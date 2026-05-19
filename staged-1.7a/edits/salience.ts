/**
 * staged-1.7a/edits/salience.ts
 *
 * Salience computation helper for nox-mem hybrid search.
 *
 * Implements the canonical formula documented in the paper (§3.2) and CLAUDE.md:
 *
 *     salience = recency × pain × importance
 *
 * Where:
 *   - recency      ∈ [0,1] — half-life decay over `retention_days` window
 *   - pain         ∈ [0,1] — severity field on chunks (0.1 trivial → 1.0 outage)
 *   - importance   ∈ [0,1] — chunk_type / source_type / tier signal (manual mapping)
 *
 * Mode gating (per architectural constraint, paper §4 — "shadow discipline"):
 *
 *   NOX_SALIENCE_MODE=shadow (DEFAULT) — compute but DO NOT apply to retrieval
 *   NOX_SALIENCE_MODE=active            — apply as additive delta in [-0.5, +0.5]
 *   NOX_SALIENCE_MODE=off               — short-circuit to 0 (ablation experiments)
 *
 * The 7-day shadow gate is enforced operationally by /api/health.salience telemetry
 * and `withOpAudit` activation logging — this module just honors whatever value
 * is set in the env at module-load (re-export getter for tests).
 *
 * Mirror module on the VPS lives at `src/lib/salience.ts` (per CLAUDE.md §"Schema v10").
 * This staged copy is the patch shipped via Wave A boost-stack-wiring.
 */

// ─── Mode helpers ─────────────────────────────────────────────────────────────

export type SalienceMode = "shadow" | "active" | "off";

export function getSalienceMode(): SalienceMode {
  const raw = (process.env.NOX_SALIENCE_MODE ?? "shadow").toLowerCase();
  if (raw === "active" || raw === "off") return raw;
  return "shadow";
}

// ─── Recency component ────────────────────────────────────────────────────────
//
// half-life-style decay: a chunk that's `retention_days` old has recency=0.5;
// fresh today = 1.0; ancient (10× retention_days) ≈ 0.001.
// retention_days defaults follow the V8 typed-retention table (see CLAUDE.md).

const DEFAULT_RETENTION_BY_TYPE: Record<string, number> = {
  feedback: 0,          // never-decay (treated as retention=Infinity → recency=1.0)
  person: 0,            // never-decay
  lesson: 180,
  decision: 365,
  project: 365,
  team: 120,
  daily: 90,
  pending: 30,
  graph_node: 60,
};
const FALLBACK_RETENTION = 90;

export function resolveRetentionDays(
  retention_days: number | null | undefined,
  chunk_type: string | null | undefined,
): number {
  if (retention_days !== null && retention_days !== undefined && Number.isFinite(retention_days)) {
    return retention_days;
  }
  if (chunk_type && chunk_type in DEFAULT_RETENTION_BY_TYPE) {
    return DEFAULT_RETENTION_BY_TYPE[chunk_type]!;
  }
  return FALLBACK_RETENTION;
}

export function recencyComponent(
  source_date: string | null | undefined,
  last_accessed_at: string | null | undefined,
  retention_days: number,
  nowMs: number = Date.now(),
): number {
  // never-decay path: retention_days == 0 (per V8 spec, NULL retention === never)
  if (retention_days <= 0) return 1.0;

  const refStr = last_accessed_at ?? source_date;
  if (!refStr) return 0.5; // unknown age → neutral

  const refMs = Date.parse(refStr);
  if (!Number.isFinite(refMs)) return 0.5;

  const ageDays = (nowMs - refMs) / (1000 * 60 * 60 * 24);
  if (ageDays <= 0) return 1.0;

  // half-life decay: at age == retention_days, recency = 0.5
  return Math.pow(2, -ageDays / retention_days);
}

// ─── Importance component ─────────────────────────────────────────────────────
//
// Type-priors. These mirror the section_boost / chunk_type weighting documented
// in the paper and CLAUDE.md. They produce a number in (0, 1].

const IMPORTANCE_BY_TYPE: Record<string, number> = {
  decision: 0.95,
  lesson: 0.90,
  person: 0.85,
  project: 0.80,
  pending: 0.75,
  feedback: 0.70,
  team: 0.60,
  daily: 0.50,
  graph_node: 0.45,
};
const FALLBACK_IMPORTANCE = 0.40;

export function importanceComponent(
  chunk_type: string | null | undefined,
  explicitImportance?: number | null,
): number {
  // explicit column wins if present and finite
  if (
    explicitImportance !== null &&
    explicitImportance !== undefined &&
    Number.isFinite(explicitImportance)
  ) {
    return clamp01(explicitImportance);
  }
  if (chunk_type && chunk_type in IMPORTANCE_BY_TYPE) {
    return IMPORTANCE_BY_TYPE[chunk_type]!;
  }
  return FALLBACK_IMPORTANCE;
}

// ─── Pain component ───────────────────────────────────────────────────────────

export function painComponent(pain: number | null | undefined): number {
  if (pain === null || pain === undefined || !Number.isFinite(pain)) return 0.2; // V9 schema default
  return clamp01(pain);
}

// ─── Main entry: calculateSalience ────────────────────────────────────────────

export interface SalienceInput {
  chunk_type?: string | null;
  source_type?: string | null;
  tier?: string | null;
  pain?: number | null;
  importance?: number | null;
  retention_days?: number | null;
  source_date?: string | null;
  created_at?: string | null;
  last_accessed_at?: string | null;
}

/**
 * Pure salience computation. Returns a number in [0, 1].
 * Does NOT consult NOX_SALIENCE_MODE — that gating lives in the caller (search.ts),
 * so this function stays pure and testable.
 */
export function calculateSalience(chunk: SalienceInput, nowMs: number = Date.now()): number {
  const retention = resolveRetentionDays(chunk.retention_days, chunk.chunk_type);
  const recency = recencyComponent(
    chunk.source_date ?? chunk.created_at,
    chunk.last_accessed_at,
    retention,
    nowMs,
  );
  const pain = painComponent(chunk.pain);
  const importance = importanceComponent(chunk.chunk_type, chunk.importance);
  return clamp01(recency * pain * importance);
}

/**
 * Mirror of `src/lib/salience.ts:computeSalience` on the VPS — kept as an alias
 * so existing call-sites (e.g. /api/health.salience) keep working when the
 * staged patch lands on top of the VPS module graph.
 */
export const computeSalience = calculateSalience;

// ─── Utils ────────────────────────────────────────────────────────────────────

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}
