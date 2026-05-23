/**
 * shadow-tracker.ts — F10 Phase D shadow tracker
 *
 * Records side-by-side comparisons between a baseline ranker and a shadow
 * (candidate) ranker for the same query. Used to validate ranking changes
 * BEFORE flipping the active path (per memory [[shadow-mode-for-ranking-changes]]).
 *
 * Data flow:
 *   1. `recordShadowComparison(feature, query, baseline, shadow, metrics)` is
 *      called from the search hot-path (post-result, before response write).
 *   2. The collector computes a delta_pct from the supplied scalar metric
 *      (or, when result-sets are passed without scalar metrics, from a
 *      rank-difference fallback).
 *   3. The event is stored in BOTH:
 *        a) an in-memory 24h × 1h ring buffer keyed by feature, used by the
 *           dashboard endpoint for fast aggregation.
 *        b) the `shadow_runs` SQLite table for long-tail audit (append-only).
 *
 * Design principles:
 *   - Pattern mirrors `telemetry-collector.ts` from Phase C: synchronous, no
 *     external deps, ring-buffer eviction lazy on record().
 *   - Persistence is best-effort: a DB write failure logs to stderr but does
 *     NOT throw, so the search hot-path is never broken by observability.
 *   - SQLite handle is injected (not import-time singleton), so tests use
 *     in-memory DBs and prod uses the shared connection from db.ts.
 *
 * Spec: docs/ROADMAP.md F10 Phase D
 * Cross-link: src/lib/shadow-tracker-schema.sql, api-server.shadow-wire-up.md
 */

import { createHash } from "node:crypto";

// ── Types ─────────────────────────────────────────────────────────────────────

/** A single ranking result row. Shape is intentionally loose — the tracker only
 *  uses `id` (for rank-diff) and ignores the rest. */
export interface ResultRow {
  id: string | number;
  score?: number;
  [k: string]: unknown;
}

export type ResultSet = ResultRow[];

export interface ShadowComparison {
  /** Epoch ms when the comparison was recorded */
  ts: number;
  /** Feature name (e.g. "temporal-spike-v2", "salience-v2") */
  feature: string;
  /** Privacy-preserving hash of the query text */
  query_hash: string;
  /** Scalar metric for baseline (nullable: caller may only supply IDs) */
  baseline_value: number | null;
  /** Scalar metric for shadow */
  shadow_value: number | null;
  /** (shadow - baseline) / baseline * 100; null if baseline is 0 or null */
  delta_pct: number | null;
  /** Arbitrary per-feature payload (parsed JSON or raw object) */
  metadata: Record<string, unknown>;
}

export interface ShadowFeatureBucket {
  /** Start of this 1h bucket (epoch ms, floored to the hour) */
  hour_ts: number;
  label: string;
  count: number;
  sum_delta_pct: number;
  sum_delta_sq: number;   // For std-dev computation
  win_count: number;      // delta_pct > 0
  regression_count: number; // delta_pct < 0
  neutral_count: number;  // delta_pct == 0 or null
}

export interface ShadowAggregate {
  feature: string;
  count: number;
  win_count: number;
  regression_count: number;
  neutral_count: number;
  mean_delta_pct: number | null;
  std_dev: number | null;
  buckets: ShadowFeatureBucket[];
}

export interface ShadowResponse {
  window: {
    hours: number;
    bucket_size_hours: number;
    from_ts: number;
    to_ts: number;
  };
  /** When ?feature=<name> was passed, this is a single-element array. */
  features: ShadowAggregate[];
  /** Latest N comparisons for drill-down (only when ?feature=<name> is set) */
  latest_runs: ShadowComparison[];
  generated_at_ms: number;
}

/** Minimal SQLite handle shape (better-sqlite3-compatible). Kept loose for testability. */
export interface ShadowDB {
  prepare(sql: string): {
    run(...params: unknown[]): { lastInsertRowid?: number | bigint };
    all(...params: unknown[]): unknown[];
    get(...params: unknown[]): unknown;
  };
  exec(sql: string): void;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const BUCKET_SIZE_MS = 60 * 60 * 1000; // 1h
const MAX_BUCKETS = 24;
/** Latest N rows kept per feature in memory for drill-down. */
const MAX_LATEST_PER_FEATURE = 10;

// ── Hashing ───────────────────────────────────────────────────────────────────

/** Stable SHA-256 (truncated) of the query string. Privacy-preserving (no
 *  way to recover the query text from the hash). */
export function hashQuery(query: string): string {
  return createHash("sha256").update(query).digest("hex").slice(0, 16);
}

// ── Delta helpers ─────────────────────────────────────────────────────────────

function hourFloor(ts: number): number {
  return Math.floor(ts / BUCKET_SIZE_MS) * BUCKET_SIZE_MS;
}

function hourLabel(ts: number): string {
  return new Date(ts).toISOString().slice(0, 13) + ":00Z";
}

function emptyBucket(hour_ts: number): ShadowFeatureBucket {
  return {
    hour_ts,
    label: hourLabel(hour_ts),
    count: 0,
    sum_delta_pct: 0,
    sum_delta_sq: 0,
    win_count: 0,
    regression_count: 0,
    neutral_count: 0,
  };
}

/** Compute (shadow - baseline) / baseline * 100. Returns null when baseline is
 *  zero, null, or undefined. */
export function computeDeltaPct(
  baseline: number | null | undefined,
  shadow: number | null | undefined,
): number | null {
  if (baseline === null || baseline === undefined) return null;
  if (shadow === null || shadow === undefined) return null;
  if (baseline === 0) return null;
  return ((shadow - baseline) / baseline) * 100;
}

/** Fallback delta when the caller did not supply a scalar metric: compute
 *  Kendall-style rank-difference normalised to [-100, +100] where positive
 *  means shadow promoted more of the baseline's top results. */
export function rankDifferenceDelta(
  baseline: ResultSet,
  shadow: ResultSet,
): number {
  if (baseline.length === 0 && shadow.length === 0) return 0;
  if (baseline.length === 0) return 100; // any result is an improvement over nothing
  if (shadow.length === 0) return -100;

  const baselineIds = baseline.map((r) => String(r.id));
  const shadowIds = shadow.map((r) => String(r.id));
  const baselineRank = new Map<string, number>();
  baselineIds.forEach((id, i) => baselineRank.set(id, i));

  // For each item in the shadow's top-K, find how much it moved up vs baseline
  let totalDelta = 0;
  let counted = 0;
  const K = Math.min(baselineIds.length, shadowIds.length, 10);
  for (let i = 0; i < K; i++) {
    const id = shadowIds[i];
    if (id === undefined) continue;
    const baselineIdx = baselineRank.get(id);
    if (baselineIdx === undefined) {
      // New item — count as a positive move (capped at +K)
      totalDelta += K;
    } else {
      totalDelta += baselineIdx - i; // baseline at pos 5, shadow at pos 0 → +5
    }
    counted++;
  }
  if (counted === 0) return 0;
  // Normalise: max possible per-item delta is K (item went from worst to best).
  return Math.max(-100, Math.min(100, (totalDelta / (counted * K)) * 100));
}

// ── ShadowTracker class ───────────────────────────────────────────────────────

export class ShadowTracker {
  /** Ring buffer: Map<feature, Map<hour_ts, ShadowFeatureBucket>> */
  private buckets: Map<string, Map<number, ShadowFeatureBucket>> = new Map();
  /** Per-feature ring of latest comparisons for drill-down. */
  private latest: Map<string, ShadowComparison[]> = new Map();
  /** Optional DB handle for append-only persistence. */
  private db: ShadowDB | null = null;
  /** Cumulative count of skipped DB writes (failure or no-handle). Exposed for ops visibility. */
  private skippedPersist = 0;

  constructor(db?: ShadowDB | null) {
    this.db = db ?? null;
  }

  /** Inject or replace the DB handle (used by tests + lazy wire-up). */
  setDB(db: ShadowDB | null): void {
    this.db = db;
  }

  /**
   * Record a shadow comparison.
   *
   * @param feature  Feature name. Required, non-empty.
   * @param query    Query text (will be hashed, not stored verbatim).
   * @param baseline Baseline result-set (used for rank-diff fallback).
   * @param shadow   Shadow result-set (used for rank-diff fallback).
   * @param metrics  Optional scalar metrics. If `metric_name` is set, the
   *                 corresponding `baseline`/`shadow` keys drive delta_pct.
   *                 Otherwise delta_pct falls back to rank-difference.
   * @param nowMs    Override of `Date.now()` for tests.
   */
  recordShadowComparison(
    feature: string,
    query: string,
    baseline: ResultSet,
    shadow: ResultSet,
    metrics: Record<string, number | string> = {},
    nowMs?: number,
  ): ShadowComparison {
    if (!feature || feature.length === 0) {
      throw new Error("shadow-tracker: feature must be a non-empty string");
    }
    const ts = nowMs ?? Date.now();
    const query_hash = hashQuery(query);

    let baseline_value: number | null = null;
    let shadow_value: number | null = null;
    let delta_pct: number | null = null;

    const baselineMetric = metrics["baseline"];
    const shadowMetric = metrics["shadow"];
    if (
      typeof baselineMetric === "number" &&
      typeof shadowMetric === "number" &&
      Number.isFinite(baselineMetric) &&
      Number.isFinite(shadowMetric)
    ) {
      baseline_value = baselineMetric;
      shadow_value = shadowMetric;
      delta_pct = computeDeltaPct(baseline_value, shadow_value);
    } else {
      // Fallback: use rank-difference scaled to delta_pct semantics.
      delta_pct = rankDifferenceDelta(baseline, shadow);
    }

    const metadata: Record<string, unknown> = {
      ...metrics,
      baseline_size: baseline.length,
      shadow_size: shadow.length,
      baseline_top_ids: baseline.slice(0, 5).map((r) => r.id),
      shadow_top_ids: shadow.slice(0, 5).map((r) => r.id),
    };

    const comparison: ShadowComparison = {
      ts,
      feature,
      query_hash,
      baseline_value,
      shadow_value,
      delta_pct,
      metadata,
    };

    this._updateRingBuffer(comparison);
    this._updateLatestRing(comparison);
    this._persist(comparison);

    return comparison;
  }

  /** Update the per-feature ring buffer + roll old buckets. */
  private _updateRingBuffer(c: ShadowComparison): void {
    const hour_ts = hourFloor(c.ts);
    let featureMap = this.buckets.get(c.feature);
    if (!featureMap) {
      featureMap = new Map<number, ShadowFeatureBucket>();
      this.buckets.set(c.feature, featureMap);
    }
    this._evict(featureMap, hour_ts);

    let bucket = featureMap.get(hour_ts);
    if (!bucket) {
      bucket = emptyBucket(hour_ts);
      featureMap.set(hour_ts, bucket);
    }
    bucket.count++;
    const d = c.delta_pct;
    if (d === null) {
      bucket.neutral_count++;
    } else {
      bucket.sum_delta_pct += d;
      bucket.sum_delta_sq += d * d;
      if (d > 0) bucket.win_count++;
      else if (d < 0) bucket.regression_count++;
      else bucket.neutral_count++;
    }
  }

  private _updateLatestRing(c: ShadowComparison): void {
    let ring = this.latest.get(c.feature);
    if (!ring) {
      ring = [];
      this.latest.set(c.feature, ring);
    }
    ring.push(c);
    while (ring.length > MAX_LATEST_PER_FEATURE) ring.shift();
  }

  private _evict(featureMap: Map<number, ShadowFeatureBucket>, currentHour: number): void {
    const oldestKept = currentHour - (MAX_BUCKETS - 1) * BUCKET_SIZE_MS;
    for (const [ts] of featureMap) {
      if (ts < oldestKept) featureMap.delete(ts);
    }
  }

  /** Best-effort SQLite persistence. Never throws — failures bump skippedPersist. */
  private _persist(c: ShadowComparison): void {
    if (!this.db) {
      this.skippedPersist++;
      return;
    }
    try {
      const stmt = this.db.prepare(
        `INSERT INTO shadow_runs (ts, feature, query_hash, baseline_value, shadow_value, delta_pct, metadata)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      );
      stmt.run(
        c.ts,
        c.feature,
        c.query_hash,
        c.baseline_value,
        c.shadow_value,
        c.delta_pct,
        JSON.stringify(c.metadata),
      );
    } catch (err) {
      this.skippedPersist++;
      // Mirror telemetry-collector silence policy: stderr only, do not throw.
      process.stderr.write(
        `[shadow-tracker] persist failed for feature=${c.feature}: ${(err as Error).message}\n`,
      );
    }
  }

  /**
   * Aggregate shadow stats for the dashboard endpoint.
   *
   * @param featureFilter When set, returns only that feature (+ latest_runs).
   * @param windowHours   1..24
   * @param nowMs         Override "now" for tests.
   */
  query(
    featureFilter: string | null = null,
    windowHours = 24,
    nowMs?: number,
  ): ShadowResponse {
    const now = nowMs ?? Date.now();
    const window_hours = Math.max(1, Math.min(MAX_BUCKETS, Math.floor(windowHours)));
    const to_ts = hourFloor(now) + BUCKET_SIZE_MS;
    const from_ts = to_ts - window_hours * BUCKET_SIZE_MS;

    const features: ShadowAggregate[] = [];
    const featureNames = featureFilter
      ? [featureFilter]
      : Array.from(this.buckets.keys()).sort();

    for (const featureName of featureNames) {
      const featureMap = this.buckets.get(featureName);
      const buckets: ShadowFeatureBucket[] = [];
      let count = 0;
      let win = 0;
      let regression = 0;
      let neutral = 0;
      let sumDelta = 0;
      let sumDeltaSq = 0;

      for (let ts = from_ts; ts < to_ts; ts += BUCKET_SIZE_MS) {
        const bucket = featureMap?.get(ts) ?? emptyBucket(ts);
        buckets.push(bucket);
        count += bucket.count;
        win += bucket.win_count;
        regression += bucket.regression_count;
        neutral += bucket.neutral_count;
        sumDelta += bucket.sum_delta_pct;
        sumDeltaSq += bucket.sum_delta_sq;
      }

      const measured = count - neutral;
      const mean_delta_pct = measured > 0 ? sumDelta / measured : null;
      // Sample standard deviation requires ≥2 measured points.
      let std_dev: number | null = null;
      if (measured >= 2 && mean_delta_pct !== null) {
        const variance = sumDeltaSq / measured - mean_delta_pct * mean_delta_pct;
        std_dev = variance > 0 ? Math.sqrt(variance) : 0;
      }

      features.push({
        feature: featureName,
        count,
        win_count: win,
        regression_count: regression,
        neutral_count: neutral,
        mean_delta_pct,
        std_dev,
        buckets,
      });
    }

    // Drill-down: latest N runs for the filtered feature only.
    let latest_runs: ShadowComparison[] = [];
    if (featureFilter) {
      const ring = this.latest.get(featureFilter) ?? [];
      latest_runs = ring
        .filter((c) => c.ts >= from_ts)
        .slice(-MAX_LATEST_PER_FEATURE)
        .reverse(); // newest first
    }

    return {
      window: {
        hours: window_hours,
        bucket_size_hours: 1,
        from_ts,
        to_ts,
      },
      features,
      latest_runs,
      generated_at_ms: now,
    };
  }

  /** Exposed for tests. */
  _reset(): void {
    this.buckets.clear();
    this.latest.clear();
    this.skippedPersist = 0;
  }

  /** Exposed for ops visibility. */
  getSkippedPersistCount(): number {
    return this.skippedPersist;
  }

  /** Exposed for tests — number of features currently held. */
  _featureCount(): number {
    return this.buckets.size;
  }
}

// ── Singleton + wire-up helpers ───────────────────────────────────────────────

/** Module-scope singleton consumed by api-server.ts wire-up. Tests use
 *  fresh instances or call `_reset()` between cases. */
export const tracker = new ShadowTracker();

/**
 * Hot-path API: record one shadow comparison. Mirrors `recordRequest` shape
 * from the Phase C telemetry collector.
 *
 * @param feature Feature name (required).
 * @param query   Query text (will be hashed).
 * @param baseline Baseline result-set.
 * @param shadow   Shadow result-set.
 * @param metrics  Optional scalar metrics: pass `{ baseline, shadow }` to use
 *                 scalar delta; omit to fall back to rank-diff.
 */
export function recordShadowComparison(
  feature: string,
  query: string,
  baseline: ResultSet,
  shadow: ResultSet,
  metrics: Record<string, number | string> = {},
): ShadowComparison {
  return tracker.recordShadowComparison(feature, query, baseline, shadow, metrics);
}

/**
 * Handler for GET /api/observability/shadow.
 * Query params:
 *   feature   (optional)  Filter to a single feature name.
 *   window    (default 24h) Hours to include (1..24).
 *   bucket    (default 1h)  Reserved for future sub-hour buckets.
 */
export function handleObsShadow(params: Record<string, string>): ShadowResponse {
  const feature = params["feature"]?.trim() || null;
  const windowHours = parseWindowParam(params["window"] ?? "24h");
  return tracker.query(feature, windowHours);
}

/** Parse "24h"/"6h"/"12" → integer hours clamped to [1, 24]. */
export function parseWindowParam(raw: string): number {
  const m = /^(\d+)h?$/i.exec(raw.trim());
  if (!m || !m[1]) return 24;
  const n = parseInt(m[1], 10);
  if (!Number.isFinite(n) || n < 1) return 24;
  return Math.min(MAX_BUCKETS, n);
}

// ── Internals for tests ───────────────────────────────────────────────────────

export const _internals = {
  BUCKET_SIZE_MS,
  MAX_BUCKETS,
  MAX_LATEST_PER_FEATURE,
  hourFloor,
  hourLabel,
  emptyBucket,
};
