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

// ─── Backwards-compat helpers (used by ingest-entity.ts) ──────────────────────
//
// These helpers existed in the pre-Wave-A salience.ts and are still imported by
// src/ingest-entity.ts. Keeping them here preserves the existing ingest pipeline
// behaviour (chunk_type → importance prior + keyword-based pain inference).
//
// `inferImportance(chunk_type)` is a thin wrapper around `importanceComponent`.
// `inferPain(chunk_type, content)` is keyword-heuristic on incident/outage terms.
//
// Without these exports, src/ingest-entity.ts fails at module-load with
// "Module './salience.js' has no exported member 'inferPain'" — the "import
// mismatch" repair commit (080407f8) in VPS git history.

const PAIN_BY_TYPE: Record<string, number> = {
  feedback: 0.3,
  lesson: 0.4,
  pending: 0.5,
  decision: 0.3,
  project: 0.3,
  daily: 0.2,
  team: 0.2,
  graph_node: 0.2,
  person: 0.2,
};
const FALLBACK_PAIN = 0.2;

// Heuristic: incident/outage/breach/severity keywords elevate pain.
// Conservative pattern — matches PT-BR + EN incident-flavored vocabulary.
const HIGH_PAIN_PATTERN =
  /\b(incident|incidente|outage|breach|critical|cr[íi]tic[ao]|emergency|emerg[êe]ncia|prod[\.\s]?down|sev[\s\-]?[0-2]|p0\b|severity[\s\-]?(high|critical))\b/i;

export function inferPain(chunk_type: string | null | undefined, content: string | null | undefined): number {
  const base: number = chunk_type
    ? (PAIN_BY_TYPE[chunk_type] ?? FALLBACK_PAIN)
    : FALLBACK_PAIN;
  if (content && HIGH_PAIN_PATTERN.test(content)) {
    return clamp01(base + 0.5);
  }
  return base;
}

export function inferImportance(chunk_type: string | null | undefined): number {
  return importanceComponent(chunk_type, null);
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
  /** Binary used/unused signal (introduced 2026-05-19 salience-additive refactor) */
  access_count?: number | null;
}

// ─── Additive weights (evidence-based, audit 2026-05-19) ──────────────────────
//
// Multiplicative formula `recency × pain × importance` concentrated 99.7% chunks
// in the [0.05-0.40] band. Audit (docs/audits/2026-05-19-salience-distribution-audit.md)
// revealed pain (90.67% = default 0.2) and recency (99.76% in [7-30d] post-restore)
// are CONSTANT signals — multiplying by a constant just rescales without
// information gain. Only `importance` (bimodal 74% low / 17% high) is alive
// as a continuous signal; `access_count` (87% zero / 13% accessed) is a strong
// binary signal that the previous formula ignored entirely.
//
// Additive formulation captures live signals proportionally and never
// zero-outs when any single field is NULL/default.
//
// Weights tuned to mirror tier-manager threshold semantics (0.7 / 0.4 / 0.15)
// so `classifySalience` still partitions chunks meaningfully.

// Tunable via env vars (design: CLAUDE.md research/2026-05-20-formula-v2-weights-tuning-design.md):
//   NOX_SALIENCE_W_IMPORTANCE=0.55 (default)
//   NOX_SALIENCE_W_RECENCY=0.15 (default)
//   NOX_SALIENCE_W_PAIN=0.10 (default)
//   NOX_SALIENCE_W_ACCESS=0.20 (default)
//
// Sum must approx 1.0 — warning emitted otherwise (scores can leak >1).
// Use case: grid search via systemd Environment= overrides (no rebuild needed).

function parseWeight(env: string | undefined, fallback: number): number {
  if (env === undefined) return fallback;
  const n = parseFloat(env);
  if (!Number.isFinite(n) || n < 0 || n > 1) return fallback;
  return n;
}

const W_IMPORTANCE = parseWeight(process.env.NOX_SALIENCE_W_IMPORTANCE, 0.55); // PRIMARY live signal
const W_RECENCY = parseWeight(process.env.NOX_SALIENCE_W_RECENCY, 0.15);       // dampened (homogeneous corpus age post-restore)
const W_PAIN = parseWeight(process.env.NOX_SALIENCE_W_PAIN, 0.10);             // dampened (90% default value)
const W_ACCESS = parseWeight(process.env.NOX_SALIENCE_W_ACCESS, 0.20);         // binary used/unused signal

const _totalWeight = W_IMPORTANCE + W_RECENCY + W_PAIN + W_ACCESS;
if (Math.abs(_totalWeight - 1.0) > 0.01) {
  console.warn(`[salience] W_* sum = ${_totalWeight.toFixed(3)} != 1.0 — scores can exceed [0,1] range`);
}

/**
 * Returns the currently active weight values (read-only snapshot).
 * Useful for observability (e.g. /api/health, eval harness introspection).
 */
export function getCurrentWeights(): {
  importance: number;
  recency: number;
  pain: number;
  access: number;
  total: number;
} {
  return {
    importance: W_IMPORTANCE,
    recency: W_RECENCY,
    pain: W_PAIN,
    access: W_ACCESS,
    total: W_IMPORTANCE + W_RECENCY + W_PAIN + W_ACCESS,
  };
}

/**
 * Access-count component. Maps 0 → 0, log-saturating toward 1.0 at ~1000 accesses.
 */
export function accessCountComponent(access_count: number | null | undefined): number {
  if (access_count === null || access_count === undefined || !Number.isFinite(access_count)) {
    return 0;
  }
  if (access_count <= 0) return 0;
  return clamp01(Math.log1p(access_count) / Math.log(1000));
}

/**
 * Pure salience computation. Returns a number in [0, 1].
 * Does NOT consult NOX_SALIENCE_MODE — that gating lives in the caller (search.ts),
 * so this function stays pure and testable.
 *
 * v2 (2026-05-19): additive evidence-weighted formula.
 *   See docs/audits/2026-05-19-salience-distribution-audit.md for rationale.
 *   Previous multiplicative formula is preserved at `calculateSalienceLegacy`
 *   for ablation comparison and shadow-discipline regression detection.
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
  const access = accessCountComponent(chunk.access_count);

  return clamp01(
    W_IMPORTANCE * importance +
      W_RECENCY * recency +
      W_PAIN * pain +
      W_ACCESS * access,
  );
}

/**
 * Legacy multiplicative formula. Retained for ablation comparison only.
 * DO NOT USE in production scoring paths — proven to concentrate 99.7%
 * of chunks in a narrow dead-range (G4 ablation 2026-05-19).
 */
export function calculateSalienceLegacy(chunk: SalienceInput, nowMs: number = Date.now()): number {
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

/**
 * Classify salience score into a tier action (for /api/health.sectionDistribution).
 * Reconstructed from tier-manager.ts usage 2026-05-19 hotfix — pre-A `classifySalience`
 * was not preserved in PR #148 salience.ts rewrite; this restores backwards-compat.
 *   promote: score >= 0.7  (candidate for tier promotion if not core)
 *   retain:  0.4 <= score < 0.7
 *   review:  0.15 <= score < 0.4
 *   archive: score < 0.15
 */
export function classifySalience(score: number): "promote" | "retain" | "review" | "archive" {
  if (score >= 0.7) return "promote";
  if (score >= 0.4) return "retain";
  if (score >= 0.15) return "review";
  return "archive";
}

// ─── Utils ────────────────────────────────────────────────────────────────────

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}
