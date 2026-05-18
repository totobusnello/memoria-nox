/**
 * Tests for src/observability/types.ts (T1 — 6 tests).
 *
 * Run: node --test --import tsx
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  Counter,
  Gauge,
  Histogram,
  escapeLabelValue,
  labelsKey,
  normalizeLabels,
  validateLabelName,
  DURATION_BUCKETS_SECONDS,
} from "../types.js";

test("T1.1 Counter monotonic + multi-label + reset", () => {
  const c = new Counter({
    name: "nox_test_total",
    help: "test",
    labelKeys: ["method", "status"],
  });
  c.inc({ method: "cli", status: "ok" });
  c.inc({ method: "cli", status: "ok" }, 2);
  c.inc({ method: "api", status: "ok" });
  assert.equal(c.get({ method: "cli", status: "ok" }), 3);
  assert.equal(c.get({ method: "api", status: "ok" }), 1);
  assert.equal(c.get({ method: "mcp", status: "ok" }), 0);
  assert.equal(c.seriesCount, 2);
  assert.throws(() => c.inc({}, -1), /non-negative/);
  c.reset();
  assert.equal(c.seriesCount, 0);
});

test("T1.2 Gauge inc/dec/set + negative ok", () => {
  const g = new Gauge({
    name: "nox_test_inflight",
    help: "test",
    labelKeys: [],
  });
  g.set(5);
  g.inc();
  g.dec({}, 2);
  assert.equal(g.get(), 4);
  g.set({}, -3);
  assert.equal(g.get(), -3);
  assert.throws(() => g.set({}, NaN), /finite/);
});

test("T1.3 Histogram cumulative bucket counts + sum/count", () => {
  const h = new Histogram(
    {
      name: "nox_test_duration_seconds",
      help: "test",
      labelKeys: ["method"],
    },
    DURATION_BUCKETS_SECONDS,
  );
  h.observe({ method: "cli" }, 0.005); // <= 0.01
  h.observe({ method: "cli" }, 0.05); // <= 0.1
  h.observe({ method: "cli" }, 2.0); // <= 5
  h.observe({ method: "cli" }, 10.0); // > all (still counted in `count`)
  const [sample] = h.collect();
  assert.ok(sample, "should have one sample");
  // buckets: [0.001, 0.01, 0.1, 0.5, 1, 5]
  assert.deepEqual(sample.bucketCounts, [0, 1, 2, 2, 2, 3]);
  assert.equal(sample.count, 4);
  assert.equal(sample.sum, 0.005 + 0.05 + 2.0 + 10.0);
});

test("T1.4 Histogram rejects bad bucket configs", () => {
  assert.throws(
    () => new Histogram({ name: "x", help: "x", labelKeys: [] }, []),
    /at least one bucket/,
  );
  assert.throws(
    () =>
      new Histogram(
        { name: "x", help: "x", labelKeys: [] },
        [1, 1, 2],
      ),
    /strictly increasing/,
  );
  assert.throws(
    () =>
      new Histogram(
        { name: "x", help: "x", labelKeys: [] },
        [Number.POSITIVE_INFINITY],
      ),
    /finite/,
  );
});

test("T1.5 label name validation + escape + key canonicalization", () => {
  validateLabelName("ok_name1");
  validateLabelName("_under");
  assert.throws(() => validateLabelName("9bad"), /invalid label/);
  assert.throws(() => validateLabelName("bad-dash"), /invalid label/);
  assert.equal(escapeLabelValue('a"b\\c\nd'), 'a\\"b\\\\c\\nd');
  // labelsKey is sorted + canonical
  const k1 = labelsKey({ b: "2", a: "1" });
  const k2 = labelsKey({ a: "1", b: "2" });
  assert.equal(k1, k2);
  assert.equal(k1, 'a="1",b="2"');
});

test("T1.6 normalizeLabels fills missing with empty + drops unknown", () => {
  const allowed = ["a", "b"];
  const out = normalizeLabels({ b: "x", c: "y" } as Record<string, string>, allowed);
  assert.equal(out.a, "");
  assert.equal(out.b, "x");
  assert.equal((out as Record<string, string>).c, undefined);
});
