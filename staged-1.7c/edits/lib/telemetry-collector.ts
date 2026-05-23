/**
 * telemetry-collector.ts — F10 Phase C Phase 1: in-process telemetry collector
 *
 * Collects per-request metrics for /api/search and /api/answer.
 * Stores data in a ring buffer (last 24h, 1h buckets).
 * No external dependencies — pure in-memory with atomic writes.
 *
 * Design principles:
 *   - Ring buffer of 24 fixed 1h buckets; oldest bucket rolls when the hour
 *     changes. Rollover is done lazily on record() — no background timer needed.
 *   - All writes are synchronous (single-process Node.js event loop is naturally
 *     sequential); no mutex needed.
 *   - Exported as a singleton (module-scope instance) with _reset() for tests.
 *
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §P2 (Phase C, Phase 1)
 * Status: Phase C Phase 1 implementation
 *
 * Endpoint served by api-server.ts wire-up:
 *   GET /api/observability/telemetry?window=24h&bucket=1h
 */

// ── Types ──────────────────────────────────────────────────────────────────────

export type TelemetryPath = "search" | "answer";

export interface TelemetryEvent {
  /** Epoch ms when the request completed */
  ts: number;
  /** Which API path triggered this record */
  path: TelemetryPath;
  /** Total request latency in ms */
  latency_ms: number;
  /** Number of results returned (chunks for search, 1 for answer) */
  result_count: number;
  /** Which internal path was used (e.g. "hybrid", "fts-only", "semantic", "answer-pipeline") */
  path_used: string;
  /** Whether semantic (vector) search was invoked */
  semantic_used: boolean;
  /** Optional: HTTP status code */
  status_code?: number;
}

export interface TelemetryBucket {
  /** Epoch ms of the start of this 1h bucket (floored to hour) */
  hour_ts: number;
  /** Human-readable label "YYYY-MM-DDTHH:00Z" */
  label: string;
  /** Total requests in this bucket */
  count: number;
  /** Sum of latencies (for computing avg) */
  latency_sum_ms: number;
  /** p50 latency estimate (median of sampled values, ms) */
  p50_ms: number | null;
  /** p95 latency estimate (95th percentile of sampled values, ms) */
  p95_ms: number | null;
  /** p99 latency estimate (99th percentile of sampled values, ms) */
  p99_ms: number | null;
  /** Per-path breakdown */
  by_path: Record<TelemetryPath, number>;
  /** Per path_used breakdown */
  by_path_used: Record<string, number>;
  /** Count of requests with semantic search */
  semantic_count: number;
  /** Total result_count across all requests */
  result_count_sum: number;
  /** Sorted latency samples (kept for percentile calc, capped at MAX_SAMPLES) */
  _samples: number[];
}

export interface TelemetryResponse {
  /** Window covered by the response */
  window: {
    hours: number;
    bucket_size_hours: number;
    from_ts: number;
    to_ts: number;
  };
  /** Buckets ordered oldest → newest; empty buckets included */
  buckets: Array<Omit<TelemetryBucket, "_samples">>;
  /** Aggregate across the entire window */
  aggregate: {
    count: number;
    avg_latency_ms: number | null;
    p50_ms: number | null;
    p95_ms: number | null;
    p99_ms: number | null;
    by_path: Record<TelemetryPath, number>;
    semantic_ratio: number | null;
  };
  generated_at_ms: number;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const BUCKET_SIZE_MS = 60 * 60 * 1000; // 1 hour
const MAX_BUCKETS = 24; // 24h ring buffer
/** Cap samples per bucket to avoid unbounded memory (≥1000 req/h = still accurate) */
const MAX_SAMPLES_PER_BUCKET = 1000;

// ── Bucket helpers ─────────────────────────────────────────────────────────────

function hourFloor(ts: number): number {
  return Math.floor(ts / BUCKET_SIZE_MS) * BUCKET_SIZE_MS;
}

function hourLabel(ts: number): string {
  return new Date(ts).toISOString().slice(0, 13) + ":00Z";
}

function emptyBucket(hour_ts: number): TelemetryBucket {
  return {
    hour_ts,
    label: hourLabel(hour_ts),
    count: 0,
    latency_sum_ms: 0,
    p50_ms: null,
    p95_ms: null,
    p99_ms: null,
    by_path: { search: 0, answer: 0 },
    by_path_used: {},
    semantic_count: 0,
    result_count_sum: 0,
    _samples: [],
  };
}

/** Compute percentile from a sorted array. Returns null if empty. */
function percentile(sorted: number[], p: number): number | null {
  if (sorted.length === 0) return null;
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  const clamped = Math.max(0, Math.min(sorted.length - 1, idx));
  return sorted[clamped] ?? null;
}

function recomputePercentiles(bucket: TelemetryBucket): void {
  const sorted = [...bucket._samples].sort((a, b) => a - b);
  bucket.p50_ms = percentile(sorted, 50);
  bucket.p95_ms = percentile(sorted, 95);
  bucket.p99_ms = percentile(sorted, 99);
}

function stripSamples(bucket: TelemetryBucket): Omit<TelemetryBucket, "_samples"> {
  const { _samples: _s, ...rest } = bucket;
  void _s; // suppress unused var
  return rest;
}

// ── TelemetryCollector class ───────────────────────────────────────────────────

export class TelemetryCollector {
  /**
   * Ring buffer: Map<hour_ts, TelemetryBucket>.
   * We keep at most MAX_BUCKETS entries; evict oldest when rolling.
   */
  private buckets: Map<number, TelemetryBucket> = new Map();

  constructor() {}

  /**
   * Record a single telemetry event.
   * Thread-safe within Node.js single-thread model (no async gap between read/write).
   */
  record(event: TelemetryEvent): void {
    const hour_ts = hourFloor(event.ts);
    this._evict(hour_ts);

    let bucket = this.buckets.get(hour_ts);
    if (!bucket) {
      bucket = emptyBucket(hour_ts);
      this.buckets.set(hour_ts, bucket);
    }

    bucket.count++;
    bucket.latency_sum_ms += event.latency_ms;

    // Reservoir: only keep MAX_SAMPLES_PER_BUCKET samples
    if (bucket._samples.length < MAX_SAMPLES_PER_BUCKET) {
      bucket._samples.push(event.latency_ms);
    } else {
      // Replace a random existing sample (reservoir sampling step)
      const replaceIdx = Math.floor(Math.random() * MAX_SAMPLES_PER_BUCKET);
      bucket._samples[replaceIdx] = event.latency_ms;
    }

    recomputePercentiles(bucket);

    bucket.by_path[event.path]++;

    const prevCount = bucket.by_path_used[event.path_used] ?? 0;
    bucket.by_path_used[event.path_used] = prevCount + 1;

    if (event.semantic_used) bucket.semantic_count++;
    bucket.result_count_sum += event.result_count;
  }

  /**
   * Evict buckets older than MAX_BUCKETS hours relative to the current hour.
   * Called on every record() so no background timer is needed.
   */
  private _evict(currentHour: number): void {
    // Keep only the most recent MAX_BUCKETS hours.
    // cutoff is the oldest hour we want to KEEP, so anything strictly older is evicted.
    // currentHour is the most recent hour slot; oldest kept = currentHour - (MAX_BUCKETS-1)*BUCKET_SIZE_MS
    const oldestKept = currentHour - (MAX_BUCKETS - 1) * BUCKET_SIZE_MS;
    for (const [ts] of this.buckets) {
      if (ts < oldestKept) {
        this.buckets.delete(ts);
      }
    }
  }

  /**
   * Query telemetry data.
   * @param windowHours How many hours to include (1–24, default 24)
   * @param bucketHours Bucket granularity (must be 1 for now)
   * @param nowMs Override "now" for testing
   */
  query(windowHours: number = 24, bucketHours: number = 1, nowMs?: number): TelemetryResponse {
    const now = nowMs ?? Date.now();
    const window_hours = Math.max(1, Math.min(MAX_BUCKETS, Math.floor(windowHours)));
    void bucketHours; // reserved for future sub-hour buckets

    const to_ts = hourFloor(now) + BUCKET_SIZE_MS; // inclusive of current partial hour
    const from_ts = to_ts - window_hours * BUCKET_SIZE_MS;

    // Build ordered bucket list (oldest → newest), filling gaps with empty buckets
    const resultBuckets: Array<Omit<TelemetryBucket, "_samples">> = [];
    let agg_count = 0;
    let agg_latency_sum = 0;
    let agg_semantic = 0;
    const agg_by_path: Record<TelemetryPath, number> = { search: 0, answer: 0 };
    const allSamples: number[] = [];

    for (let ts = from_ts; ts < to_ts; ts += BUCKET_SIZE_MS) {
      const bucket = this.buckets.get(ts);
      if (bucket) {
        resultBuckets.push(stripSamples(bucket));
        agg_count += bucket.count;
        agg_latency_sum += bucket.latency_sum_ms;
        agg_semantic += bucket.semantic_count;
        agg_by_path.search += bucket.by_path.search;
        agg_by_path.answer += bucket.by_path.answer;
        allSamples.push(...bucket._samples);
      } else {
        resultBuckets.push(stripSamples(emptyBucket(ts)));
      }
    }

    // Aggregate percentiles from all samples
    const sortedAll = [...allSamples].sort((a, b) => a - b);

    return {
      window: {
        hours: window_hours,
        bucket_size_hours: 1,
        from_ts,
        to_ts,
      },
      buckets: resultBuckets,
      aggregate: {
        count: agg_count,
        avg_latency_ms: agg_count > 0 ? Math.round(agg_latency_sum / agg_count) : null,
        p50_ms: percentile(sortedAll, 50),
        p95_ms: percentile(sortedAll, 95),
        p99_ms: percentile(sortedAll, 99),
        by_path: agg_by_path,
        semantic_ratio: agg_count > 0 ? Math.round((agg_semantic / agg_count) * 1000) / 1000 : null,
      },
      generated_at_ms: now,
    };
  }

  /** Exposed for tests — reset all collected data. */
  _reset(): void {
    this.buckets.clear();
  }

  /** Exposed for tests — inspect raw bucket map size. */
  _bucketCount(): number {
    return this.buckets.size;
  }
}

// ── Singleton ──────────────────────────────────────────────────────────────────

/**
 * Module-scope singleton used by api-server.ts hooks.
 * Tests import this and call _reset() in before()/beforeEach().
 */
export const collector = new TelemetryCollector();

// ── Wire-up helpers (called from api-server.ts) ────────────────────────────────

/**
 * Middleware-style wrapper: records telemetry for a completed request.
 * Call AFTER response has been computed, before writing to the client.
 *
 * @param path Which API path
 * @param startMs Performance.now()-based start time in epoch ms (Date.now() at request start)
 * @param endMs Date.now() at response ready (before write)
 * @param resultCount Number of results in response
 * @param pathUsed Which internal search path was invoked
 * @param semanticUsed Whether semantic (vector) embedding was called
 * @param statusCode HTTP response status
 */
export function recordRequest(
  path: TelemetryPath,
  startMs: number,
  endMs: number,
  resultCount: number,
  pathUsed: string,
  semanticUsed: boolean,
  statusCode = 200,
): void {
  collector.record({
    ts: endMs,
    path,
    latency_ms: Math.max(0, endMs - startMs),
    result_count: resultCount,
    path_used: pathUsed,
    semantic_used: semanticUsed,
    status_code: statusCode,
  });
}

/**
 * Handler for GET /api/observability/telemetry endpoint.
 * Parses ?window=Nh&bucket=1h query params (defaults: window=24h, bucket=1h).
 * Returns TelemetryResponse JSON.
 */
export function handleObsTelemetry(params: Record<string, string>): TelemetryResponse {
  const windowParam = params["window"] ?? "24h";
  const windowHours = parseWindowParam(windowParam);
  return collector.query(windowHours, 1);
}

/**
 * Parse window param: "24h" → 24, "6h" → 6, "1h" → 1.
 * Clamps to [1, 24]. Falls back to 24 on invalid input.
 */
export function parseWindowParam(raw: string): number {
  const m = /^(\d+)h?$/i.exec(raw.trim());
  if (!m || !m[1]) return 24;
  const n = parseInt(m[1], 10);
  if (!Number.isFinite(n) || n < 1) return 24;
  return Math.min(24, n);
}

// ── Internals for tests ────────────────────────────────────────────────────────

export const _internals = {
  BUCKET_SIZE_MS,
  MAX_BUCKETS,
  MAX_SAMPLES_PER_BUCKET,
  hourFloor,
  hourLabel,
  emptyBucket,
  percentile,
};
