/**
 * Tests for src/observability/registry.ts (T2 — 8 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MetricsRegistry,
  getDefaultRegistry,
  resetDefaultRegistry,
} from "../registry.js";
import { Counter, Gauge, Histogram, DURATION_BUCKETS_SECONDS } from "../types.js";

function newCounter(name = "nox_test_total"): Counter {
  return new Counter({ name, help: "t", labelKeys: [] });
}

test("T2.1 register + get + size", () => {
  const r = new MetricsRegistry();
  const c = newCounter();
  r.register(c);
  assert.equal(r.size, 1);
  assert.equal(r.get("nox_test_total"), c);
  assert.equal(r.get("does_not_exist"), undefined);
});

test("T2.2 register is idempotent (same object)", () => {
  const r = new MetricsRegistry();
  const c = newCounter();
  r.register(c);
  r.register(c);
  r.register(c);
  assert.equal(r.size, 1);
});

test("T2.3 register throws on name collision (different object)", () => {
  const r = new MetricsRegistry();
  r.register(newCounter("x_total"));
  assert.throws(() => r.register(newCounter("x_total")), /already registered/);
});

test("T2.4 unregister + return value", () => {
  const r = new MetricsRegistry();
  r.register(newCounter("a_total"));
  assert.equal(r.unregister("a_total"), true);
  assert.equal(r.unregister("a_total"), false);
  assert.equal(r.size, 0);
});

test("T2.5 collect returns sorted, kinded snapshot", () => {
  const r = new MetricsRegistry();
  r.register(new Gauge({ name: "z_g", help: "x", labelKeys: [] }));
  r.register(newCounter("a_c"));
  r.register(
    new Histogram(
      { name: "m_h", help: "x", labelKeys: [] },
      DURATION_BUCKETS_SECONDS,
    ),
  );
  const snap = r.collect();
  assert.equal(snap.counters.length, 1);
  assert.equal(snap.gauges.length, 1);
  assert.equal(snap.histograms.length, 1);
  // names() sorted alphabetically across all kinds
  assert.deepEqual(r.names(), ["a_c", "m_h", "z_g"]);
  assert.ok(snap.takenAt > 0);
});

test("T2.6 get with kind filter only returns matching kinds", () => {
  const r = new MetricsRegistry();
  const c = newCounter("a_total");
  r.register(c);
  assert.equal(r.get("a_total", "counter"), c);
  assert.equal(r.get("a_total", "gauge"), undefined);
});

test("T2.7 totalSeries sums across metrics", () => {
  const r = new MetricsRegistry();
  const c = new Counter({ name: "c_total", help: "x", labelKeys: ["k"] });
  c.inc({ k: "a" });
  c.inc({ k: "b" });
  c.inc({ k: "c" });
  r.register(c);
  const g = new Gauge({ name: "g", help: "x", labelKeys: [] });
  g.set(1);
  r.register(g);
  assert.equal(r.totalSeries(), 4);
});

test("T2.8 default registry singleton + reset", () => {
  const a = getDefaultRegistry();
  const b = getDefaultRegistry();
  assert.equal(a, b);
  a.register(newCounter("singleton_total"));
  resetDefaultRegistry();
  const c = getDefaultRegistry();
  assert.notEqual(a, c);
  assert.equal(c.size, 0);
});
