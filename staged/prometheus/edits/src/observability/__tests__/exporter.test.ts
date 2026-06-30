/**
 * Tests for src/observability/exporter.ts (T5 — 12 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { gunzipSync } from "node:zlib";
import {
  handle,
  render,
  OPENMETRICS_CONTENT_TYPE,
} from "../exporter.ts";
import { MetricsRegistry } from "../registry.ts";
import {
  Counter,
  Gauge,
  Histogram,
  DURATION_BUCKETS_SECONDS,
} from "../types.ts";

function makeReg(): MetricsRegistry {
  const r = new MetricsRegistry();
  const c = new Counter({
    name: "nox_test_total",
    help: "test counter",
    labelKeys: ["method"],
  });
  c.inc({ method: "api" }, 3);
  c.inc({ method: "cli" }, 5);
  r.register(c);

  const g = new Gauge({
    name: "nox_test_inflight",
    help: "test gauge",
    labelKeys: [],
  });
  g.set(7);
  r.register(g);

  const h = new Histogram(
    {
      name: "nox_test_duration_seconds",
      help: "test histogram",
      labelKeys: ["method"],
      unit: "seconds",
    },
    DURATION_BUCKETS_SECONDS,
  );
  h.observe({ method: "api" }, 0.005);
  h.observe({ method: "api" }, 2.0);
  r.register(h);
  return r;
}

test("T5.1 render produces HELP + TYPE + samples", () => {
  const r = makeReg();
  const out = render(r.collect());
  assert.match(out, /# HELP nox_test_total test counter/);
  assert.match(out, /# TYPE nox_test_total counter/);
  assert.match(out, /nox_test_total\{method="api"\} 3/);
  assert.match(out, /nox_test_total\{method="cli"\} 5/);
  assert.match(out, /# HELP nox_test_inflight/);
  assert.match(out, /# TYPE nox_test_inflight gauge/);
  assert.match(out, /nox_test_inflight 7/);
});

test("T5.2 histogram renders _bucket + _sum + _count + +Inf", () => {
  const r = makeReg();
  const out = render(r.collect());
  assert.match(out, /# TYPE nox_test_duration_seconds histogram/);
  assert.match(out, /nox_test_duration_seconds_bucket\{le="0\.01",method="api"\} 1/);
  assert.match(out, /nox_test_duration_seconds_bucket\{le="\+Inf",method="api"\} 2/);
  assert.match(out, /nox_test_duration_seconds_sum\{method="api"\} 2\.005/);
  assert.match(out, /nox_test_duration_seconds_count\{method="api"\} 2/);
});

test("T5.3 render ends with # EOF terminator", () => {
  const r = makeReg();
  const out = render(r.collect());
  assert.match(out, /# EOF\n$/);
});

test("T5.4 handle returns 200 + OpenMetrics content-type by default", () => {
  const r = makeReg();
  const resp = handle({}, { registry: r });
  assert.equal(resp.status, 200);
  assert.equal(resp.headers["content-type"], OPENMETRICS_CONTENT_TYPE);
  assert.equal(resp.headers["cache-control"], "no-store");
});

test("T5.5 handle filters by ?names=…", () => {
  const r = makeReg();
  const params = new URLSearchParams("names=nox_test_inflight");
  const resp = handle({ searchParams: params }, { registry: r });
  const body = resp.body as string;
  assert.match(body, /nox_test_inflight/);
  assert.doesNotMatch(body, /nox_test_total\b/);
});

test("T5.6 handle gzips when Accept-Encoding includes gzip", () => {
  const r = makeReg();
  const resp = handle(
    { headers: { "accept-encoding": "gzip, br" } },
    { registry: r },
  );
  assert.equal(resp.headers["content-encoding"], "gzip");
  assert.ok(Buffer.isBuffer(resp.body));
  const decoded = gunzipSync(resp.body as Buffer).toString("utf8");
  assert.match(decoded, /nox_test_total/);
});

test("T5.7 handle 401 when token required + missing", () => {
  const r = makeReg();
  const resp = handle({}, { registry: r, token: "secret-xyz" });
  assert.equal(resp.status, 401);
  assert.match(resp.headers["www-authenticate"], /Bearer/);
});

test("T5.8 handle 401 when wrong bearer", () => {
  const r = makeReg();
  const resp = handle(
    { headers: { authorization: "Bearer wrong" } },
    { registry: r, token: "secret-xyz" },
  );
  assert.equal(resp.status, 401);
});

test("T5.9 handle 200 with correct bearer", () => {
  const r = makeReg();
  const resp = handle(
    { headers: { authorization: "Bearer secret-xyz" } },
    { registry: r, token: "secret-xyz" },
  );
  assert.equal(resp.status, 200);
});

test("T5.10 labels are sorted + escaped in output", () => {
  const r = new MetricsRegistry();
  const c = new Counter({
    name: "nox_x_total",
    help: 'with "quotes" and\nbreaks',
    labelKeys: ["b", "a"],
  });
  c.inc({ b: 'two"quote', a: "one" });
  r.register(c);
  const out = render(r.collect());
  // sorted keys: a then b
  assert.match(out, /nox_x_total\{a="one",b="two\\"quote"\}/);
  // help escapes newlines + quotes preserved as-is on # HELP line
  assert.match(out, /# HELP nox_x_total with "quotes" and\\nbreaks/);
});

test("T5.11 handle sets snapshot-at header", () => {
  const r = makeReg();
  const resp = handle({}, { registry: r });
  const at = Number(resp.headers["x-metrics-snapshot-at"]);
  assert.ok(at > 0);
  assert.ok(Math.abs(Date.now() - at) < 5_000);
});

test("T5.12 unit annotations rendered as # UNIT", () => {
  const r = makeReg();
  const out = render(r.collect());
  assert.match(out, /# UNIT nox_test_duration_seconds seconds/);
});
