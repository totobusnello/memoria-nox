/**
 * telemetry-collector.test.ts — F10 Phase C Phase 1 unit tests
 *
 * Covers:
 *   1. Empty collector: query returns zeroed aggregate, all buckets empty
 *   2. Bucket boundary: events in different hours land in correct buckets
 *   3. Ring rollover: buckets older than 24h are evicted on next record()
 *   4. Concurrent writes simulation: multiple records in same bucket accumulate correctly
 *   5. Query window filter: ?window=6h only returns last 6 buckets
 *   6. Percentile computation: p50/p95/p99 accuracy on known data set
 *   7. parseWindowParam: valid + invalid + edge cases
 *   8. handleObsTelemetry: integration smoke
 *   9. by_path and by_path_used aggregation
 *   10. semantic_ratio calculation
 *
 * Cross-link: staged-1.7c/edits/lib/telemetry-collector.ts
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §P2 Phase C Phase 1
 */

import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  TelemetryCollector,
  collector,
  handleObsTelemetry,
  parseWindowParam,
  _internals,
} from "../lib/telemetry-collector.js";

const { BUCKET_SIZE_MS, MAX_BUCKETS, hourFloor, percentile } = _internals;

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Create a fresh isolated collector (avoids singleton state pollution) */
function fresh(): TelemetryCollector {
  return new TelemetryCollector();
}

/** Build a minimal TelemetryEvent */
function ev(
  ts: number,
  latency_ms: number,
  opts: Partial<{
    path: "search" | "answer";
    result_count: number;
    path_used: string;
    semantic_used: boolean;
  }> = {},
) {
  return {
    ts,
    path: opts.path ?? ("search" as const),
    latency_ms,
    result_count: opts.result_count ?? 5,
    path_used: opts.path_used ?? "hybrid",
    semantic_used: opts.semantic_used ?? false,
  };
}

// ── 1. Empty collector ─────────────────────────────────────────────────────────

describe("empty collector", () => {
  test("query returns zeroed aggregate when no events recorded", () => {
    const c = fresh();
    const now = Date.now();
    const res = c.query(24, 1, now);

    assert.equal(res.aggregate.count, 0);
    assert.equal(res.aggregate.avg_latency_ms, null);
    assert.equal(res.aggregate.p50_ms, null);
    assert.equal(res.aggregate.p95_ms, null);
    assert.equal(res.aggregate.p99_ms, null);
    assert.equal(res.aggregate.semantic_ratio, null);
    assert.equal(res.aggregate.by_path.search, 0);
    assert.equal(res.aggregate.by_path.answer, 0);
  });

  test("query returns exactly window_hours empty buckets", () => {
    const c = fresh();
    const now = Date.now();
    const res = c.query(24, 1, now);

    assert.equal(res.buckets.length, 24);
    for (const bucket of res.buckets) {
      assert.equal(bucket.count, 0);
      assert.equal(bucket.p50_ms, null);
    }
  });

  test("window param is included in response", () => {
    const c = fresh();
    const now = Date.now();
    const res = c.query(6, 1, now);

    assert.equal(res.window.hours, 6);
    assert.equal(res.window.bucket_size_hours, 1);
    assert.equal(res.buckets.length, 6);
  });
});

// ── 2. Bucket boundary ─────────────────────────────────────────────────────────

describe("bucket boundary", () => {
  test("events in same hour land in same bucket", () => {
    const c = fresh();
    const base = hourFloor(Date.now()); // start of current hour

    c.record(ev(base + 1000, 100));
    c.record(ev(base + 2000, 200));
    c.record(ev(base + 3599_000, 300)); // still same hour

    const res = c.query(24, 1, base + 3600_000);
    const lastBucket = res.buckets[res.buckets.length - 1];
    assert.ok(lastBucket);
    // The last bucket covers [base, base+3600s) — all 3 events land here
    // NOTE: query window includes partial current hour, so events at base+1000..3599000
    // are in the bucket at `base`
    const populated = res.buckets.filter((b) => b.count > 0);
    assert.equal(populated.length, 1);
    assert.equal(populated[0]!.count, 3);
  });

  test("events in adjacent hours land in different buckets", () => {
    const c = fresh();
    const hour1 = hourFloor(Date.now()) - BUCKET_SIZE_MS; // previous hour
    const hour2 = hour1 + BUCKET_SIZE_MS; // current hour

    c.record(ev(hour1 + 500, 100)); // previous hour
    c.record(ev(hour2 + 500, 200)); // current hour

    const now = hour2 + BUCKET_SIZE_MS - 1; // end of current hour
    const res = c.query(24, 1, now);

    const populated = res.buckets.filter((b) => b.count > 0);
    assert.equal(populated.length, 2, "two separate buckets should be populated");
    // verify buckets have correct hour_ts
    const ts_set = new Set(populated.map((b) => b.hour_ts));
    assert.ok(ts_set.has(hour1));
    assert.ok(ts_set.has(hour2));
  });

  test("hourFloor is idempotent", () => {
    const ts = 1_716_300_000_000; // some epoch ms
    const floor = hourFloor(ts);
    assert.equal(hourFloor(floor), floor);
    assert.ok(floor <= ts);
    assert.ok(ts - floor < BUCKET_SIZE_MS);
  });
});

// ── 3. Ring buffer rollover ────────────────────────────────────────────────────

describe("ring buffer rollover", () => {
  test("buckets older than 24h are evicted on next record", () => {
    const c = fresh();
    const now = Date.now();
    const baseHour = hourFloor(now);

    // Record events in MAX_BUCKETS+2 distinct hours: from baseHour down to baseHour - (MAX_BUCKETS+1)*BUCKET
    // Each record() triggers _evict(currentHour) based on the event's hour
    // After recording all, the oldest buckets should be gone
    for (let i = 0; i <= MAX_BUCKETS + 1; i++) {
      const ts = baseHour - i * BUCKET_SIZE_MS + 500;
      c.record(ev(ts, 100));
    }

    // Record at baseHour to trigger final eviction with baseHour as currentHour
    c.record(ev(baseHour + 500, 100));

    assert.ok(
      c._bucketCount() <= MAX_BUCKETS,
      `bucket count ${c._bucketCount()} should be <= MAX_BUCKETS ${MAX_BUCKETS}`,
    );
  });

  test("query only returns MAX_BUCKETS even when clamp asked for more", () => {
    const c = fresh();
    const res = c.query(100, 1, Date.now()); // ask for 100h but max is 24
    assert.equal(res.window.hours, 24);
    assert.equal(res.buckets.length, 24);
  });

  test("window=1h returns only 1 bucket", () => {
    const c = fresh();
    const now = Date.now();
    c.record(ev(now - 500, 100));
    const res = c.query(1, 1, now);
    assert.equal(res.buckets.length, 1);
    assert.equal(res.aggregate.count, 1);
  });
});

// ── 4. Concurrent writes simulation ───────────────────────────────────────────

describe("concurrent writes (sequential simulation)", () => {
  test("many records in same bucket accumulate correctly", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());

    // Simulate 50 requests in the same hour
    for (let i = 0; i < 50; i++) {
      c.record(ev(baseHour + i * 1000, 100 + i, { result_count: i % 3 + 1 }));
    }

    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    assert.equal(res.aggregate.count, 50);
    assert.ok(res.aggregate.avg_latency_ms !== null);
    // avg of 100..149 = 124.5
    assert.ok(
      Math.abs((res.aggregate.avg_latency_ms ?? 0) - 124) <= 1,
      `avg latency should be ~124, got ${res.aggregate.avg_latency_ms}`,
    );
  });

  test("by_path counts accumulate correctly across mixed paths", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());

    for (let i = 0; i < 30; i++) {
      c.record(ev(baseHour + i * 100, 100, { path: "search" }));
    }
    for (let i = 0; i < 10; i++) {
      c.record(ev(baseHour + (i + 30) * 100, 200, { path: "answer" }));
    }

    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    assert.equal(res.aggregate.by_path.search, 30);
    assert.equal(res.aggregate.by_path.answer, 10);
    assert.equal(res.aggregate.count, 40);
  });

  test("by_path_used breakdown is populated", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());

    c.record(ev(baseHour + 100, 100, { path_used: "hybrid" }));
    c.record(ev(baseHour + 200, 100, { path_used: "fts-only" }));
    c.record(ev(baseHour + 300, 100, { path_used: "hybrid" }));

    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    const bucket = res.buckets.find((b) => b.count > 0);
    assert.ok(bucket);
    assert.equal(bucket.by_path_used["hybrid"], 2);
    assert.equal(bucket.by_path_used["fts-only"], 1);
  });
});

// ── 5. Query window filter ─────────────────────────────────────────────────────

describe("query window filter", () => {
  test("window=6h excludes events older than 6h", () => {
    const c = fresh();
    const now = Date.now();
    const baseHour = hourFloor(now);

    // Event 7h ago — should be excluded by window=6h
    c.record(ev(baseHour - 7 * BUCKET_SIZE_MS + 100, 999));
    // Event 2h ago — should be included
    c.record(ev(baseHour - 2 * BUCKET_SIZE_MS + 100, 100));

    const res = c.query(6, 1, now);
    assert.equal(res.aggregate.count, 1, "only the 2h-ago event should be in window=6h");
    assert.ok(
      res.aggregate.avg_latency_ms !== null &&
        Math.abs(res.aggregate.avg_latency_ms - 100) < 5,
      "avg should reflect only the 2h-ago event",
    );
  });

  test("window=24h includes all events in last 24h", () => {
    const c = fresh();
    const now = Date.now();
    const baseHour = hourFloor(now);

    // Spread 10 events across the last 24h window
    for (let h = 0; h < 10; h++) {
      c.record(ev(baseHour - h * BUCKET_SIZE_MS + 500, 100));
    }

    const res = c.query(24, 1, now);
    assert.equal(res.aggregate.count, 10);
  });

  test("window clamps at 1h minimum", () => {
    const c = fresh();
    const res = c.query(0, 1, Date.now());
    assert.equal(res.window.hours, 1);
    assert.equal(res.buckets.length, 1);
  });
});

// ── 6. Percentile computation ──────────────────────────────────────────────────

describe("percentile computation", () => {
  test("percentile returns null for empty array", () => {
    assert.equal(percentile([], 50), null);
    assert.equal(percentile([], 95), null);
    assert.equal(percentile([], 99), null);
  });

  test("single element returns it for all percentiles", () => {
    assert.equal(percentile([42], 50), 42);
    assert.equal(percentile([42], 95), 42);
    assert.equal(percentile([42], 99), 42);
  });

  test("p50 of [1,2,3,4,5] is ~3 (median)", () => {
    const sorted = [1, 2, 3, 4, 5];
    const p = percentile(sorted, 50);
    // ceil(2.5) - 1 = 2 → index 2 → value 3
    assert.equal(p, 3);
  });

  test("p95/p99 on 100-element array are accurate", () => {
    const sorted = Array.from({ length: 100 }, (_, i) => i + 1); // 1..100
    assert.equal(percentile(sorted, 95), 95);
    assert.equal(percentile(sorted, 99), 99);
    assert.equal(percentile(sorted, 50), 50);
  });

  test("bucket percentiles reflect recorded latencies", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());

    // Record 100 events with latencies 1..100
    for (let i = 1; i <= 100; i++) {
      c.record(ev(baseHour + i * 1000, i));
    }

    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    const bucket = res.buckets.find((b) => b.count > 0);
    assert.ok(bucket);
    // p50 should be around 50
    assert.ok(bucket.p50_ms !== null && bucket.p50_ms >= 49 && bucket.p50_ms <= 52, `p50=${bucket.p50_ms}`);
    // p95 should be around 95
    assert.ok(bucket.p95_ms !== null && bucket.p95_ms >= 93 && bucket.p95_ms <= 97, `p95=${bucket.p95_ms}`);
  });
});

// ── 7. parseWindowParam ────────────────────────────────────────────────────────

describe("parseWindowParam", () => {
  test("parses standard forms correctly", () => {
    assert.equal(parseWindowParam("24h"), 24);
    assert.equal(parseWindowParam("6h"), 6);
    assert.equal(parseWindowParam("1h"), 1);
    assert.equal(parseWindowParam("12"), 12); // no 'h' suffix
  });

  test("clamps to 24 maximum", () => {
    assert.equal(parseWindowParam("100h"), 24);
    assert.equal(parseWindowParam("999"), 24);
  });

  test("falls back to 24 on invalid input", () => {
    assert.equal(parseWindowParam(""), 24);
    assert.equal(parseWindowParam("abc"), 24);
    assert.equal(parseWindowParam("0h"), 24); // below 1 → fallback
    assert.equal(parseWindowParam("-5h"), 24);
  });

  test("case insensitive suffix", () => {
    assert.equal(parseWindowParam("6H"), 6);
  });
});

// ── 8. handleObsTelemetry integration smoke ────────────────────────────────────

describe("handleObsTelemetry", () => {
  beforeEach(() => {
    // Reset the module-scope singleton between tests
    collector._reset();
  });

  test("returns valid response shape with empty params", () => {
    const res = handleObsTelemetry({});
    assert.ok("window" in res);
    assert.ok("buckets" in res);
    assert.ok("aggregate" in res);
    assert.ok("generated_at_ms" in res);
    assert.equal(res.window.hours, 24);
    assert.equal(res.buckets.length, 24);
  });

  test("respects window param", () => {
    const res = handleObsTelemetry({ window: "6h" });
    assert.equal(res.window.hours, 6);
    assert.equal(res.buckets.length, 6);
  });

  test("reflects recorded events via singleton", () => {
    const now = Date.now();
    collector.record({
      ts: now,
      path: "search",
      latency_ms: 500,
      result_count: 10,
      path_used: "hybrid",
      semantic_used: true,
    });
    const res = handleObsTelemetry({ window: "1h" });
    assert.equal(res.aggregate.count, 1);
    assert.equal(res.aggregate.semantic_ratio, 1.0);
  });
});

// ── 9. semantic_ratio calculation ──────────────────────────────────────────────

describe("semantic_ratio", () => {
  test("is null when no events recorded", () => {
    const c = fresh();
    const res = c.query(24, 1, Date.now());
    assert.equal(res.aggregate.semantic_ratio, null);
  });

  test("is 1.0 when all events used semantic", () => {
    const c = fresh();
    const now = Date.now();
    c.record(ev(now - 1000, 100, { semantic_used: true }));
    c.record(ev(now - 500, 100, { semantic_used: true }));
    // Query with nowMs=now so events at now-X are inside the current hour bucket
    const res = c.query(24, 1, now);
    assert.equal(res.aggregate.semantic_ratio, 1.0);
  });

  test("is 0.0 when no events used semantic", () => {
    const c = fresh();
    const now = Date.now();
    c.record(ev(now - 500, 100, { semantic_used: false }));
    const res = c.query(24, 1, now);
    assert.equal(res.aggregate.semantic_ratio, 0.0);
  });

  test("computes correct ratio for mixed events", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());
    // 3 semantic, 1 non-semantic → 0.75
    c.record(ev(baseHour + 100, 100, { semantic_used: true }));
    c.record(ev(baseHour + 200, 100, { semantic_used: true }));
    c.record(ev(baseHour + 300, 100, { semantic_used: true }));
    c.record(ev(baseHour + 400, 100, { semantic_used: false }));
    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    assert.equal(res.aggregate.semantic_ratio, 0.75);
  });
});

// ── 10. result_count_sum ───────────────────────────────────────────────────────

describe("result_count_sum", () => {
  test("accumulates result counts across events in bucket", () => {
    const c = fresh();
    const baseHour = hourFloor(Date.now());
    c.record(ev(baseHour + 100, 100, { result_count: 5 }));
    c.record(ev(baseHour + 200, 100, { result_count: 10 }));
    c.record(ev(baseHour + 300, 100, { result_count: 3 }));

    const res = c.query(1, 1, baseHour + BUCKET_SIZE_MS - 1);
    const bucket = res.buckets.find((b) => b.count > 0);
    assert.ok(bucket);
    assert.equal(bucket.result_count_sum, 18);
  });
});
