/**
 * src/observability/types.ts — Prometheus / OpenMetrics metric primitives (T1).
 *
 * Provides three core types — Counter, Gauge, Histogram — implementing the
 * OpenMetrics text exposition format used by Prometheus, VictoriaMetrics and
 * Grafana Agent.
 *
 * DESIGN PROPERTIES (non-negotiable):
 *   - Labels are multi-dimensional but bounded: cardinality is enforced by the
 *     CardinalityGuard (see ./cardinality.ts). This module does NOT enforce
 *     limits — that is the responsibility of the Registry.
 *   - All recording APIs are synchronous and side-effect-free (no I/O).
 *   - Counter is monotonic: a `reset()` is provided only for tests.
 *   - Gauge supports `inc/dec/set`.
 *   - Histogram is bucketed with `le` semantics (less-or-equal upper bound)
 *     and accumulates `+Inf` bucket implicitly via `count`.
 *
 * The metric *name* is what is exported. Label *names* must match `[a-zA-Z_]
 * [a-zA-Z0-9_]*` and label *values* are UTF-8 strings (escaped on render).
 *
 * Refs:
 *   - https://prometheus.io/docs/instrumenting/exposition_formats/
 *   - https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md
 */

// ─── Public types ────────────────────────────────────────────────────────────

export type MetricKind = "counter" | "gauge" | "histogram";

export type Labels = Readonly<Record<string, string>>;

export interface MetricMeta {
  /** Metric name (snake_case, prom convention). */
  readonly name: string;
  /** Help text shown on /metrics output (`# HELP` line). */
  readonly help: string;
  /** Type marker (`# TYPE` line). */
  readonly kind: MetricKind;
  /** Allowed label keys. If empty, the metric has no labels. */
  readonly labelKeys: readonly string[];
  /** Optional unit suffix per OpenMetrics (e.g. "seconds", "bytes"). */
  readonly unit?: string;
}

export interface CounterSample {
  labels: Labels;
  value: number;
}

export interface GaugeSample {
  labels: Labels;
  value: number;
}

export interface HistogramSample {
  labels: Labels;
  /** Bucket boundaries (sorted ascending), excluding +Inf. */
  buckets: readonly number[];
  /** Cumulative counts per bucket (parallel to `buckets`). */
  bucketCounts: number[];
  /** Total observations (== count of +Inf bucket). */
  count: number;
  /** Sum of observed values. */
  sum: number;
}

// ─── Label helpers ───────────────────────────────────────────────────────────

const LABEL_NAME_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

export function validateLabelName(name: string): void {
  if (!LABEL_NAME_RE.test(name)) {
    throw new Error(`invalid label name: ${JSON.stringify(name)}`);
  }
}

/** Stable string key for a label set (canonical form). */
export function labelsKey(labels: Labels): string {
  const keys = Object.keys(labels).sort();
  if (keys.length === 0) return "";
  const parts: string[] = [];
  for (const k of keys) {
    parts.push(`${k}="${escapeLabelValue(labels[k] ?? "")}"`);
  }
  return parts.join(",");
}

/** Escape a label value per OpenMetrics spec (backslash, double-quote, newline). */
export function escapeLabelValue(v: string): string {
  return v.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/"/g, '\\"');
}

/** Filter a labels object to only the allowed keys; missing keys default to "". */
export function normalizeLabels(labels: Labels, allowed: readonly string[]): Labels {
  const out: Record<string, string> = {};
  for (const k of allowed) {
    const v = labels[k];
    out[k] = typeof v === "string" ? v : "";
  }
  return Object.freeze(out);
}

// ─── Counter ─────────────────────────────────────────────────────────────────

/**
 * Monotonic counter. Use for events that only go up (requests, errors, bytes).
 */
export class Counter {
  readonly meta: MetricMeta;
  private readonly values = new Map<string, { labels: Labels; value: number }>();

  constructor(meta: Omit<MetricMeta, "kind">) {
    for (const k of meta.labelKeys) validateLabelName(k);
    this.meta = { ...meta, kind: "counter" };
  }

  inc(labels: Labels = {}, delta = 1): void {
    if (delta < 0 || !Number.isFinite(delta)) {
      throw new Error(`counter increment must be a non-negative finite number, got ${delta}`);
    }
    const norm = normalizeLabels(labels, this.meta.labelKeys);
    const key = labelsKey(norm);
    const entry = this.values.get(key);
    if (entry) {
      entry.value += delta;
    } else {
      this.values.set(key, { labels: norm, value: delta });
    }
  }

  /** Get the current value for a specific label set (0 if absent). */
  get(labels: Labels = {}): number {
    const norm = normalizeLabels(labels, this.meta.labelKeys);
    const key = labelsKey(norm);
    return this.values.get(key)?.value ?? 0;
  }

  /** Test-only: clear all observations. */
  reset(): void {
    this.values.clear();
  }

  /** Snapshot — used by the exporter. */
  collect(): CounterSample[] {
    const out: CounterSample[] = [];
    for (const e of this.values.values()) {
      out.push({ labels: e.labels, value: e.value });
    }
    return out;
  }

  /** Number of distinct label series tracked. */
  get seriesCount(): number {
    return this.values.size;
  }
}

// ─── Gauge ───────────────────────────────────────────────────────────────────

/**
 * Gauge — value that goes up and down (queue length, memory, in-flight count).
 */
export class Gauge {
  readonly meta: MetricMeta;
  private readonly values = new Map<string, { labels: Labels; value: number }>();

  constructor(meta: Omit<MetricMeta, "kind">) {
    for (const k of meta.labelKeys) validateLabelName(k);
    this.meta = { ...meta, kind: "gauge" };
  }

  set(labels: Labels, value: number): void;
  set(value: number): void;
  set(labelsOrValue: Labels | number, maybeValue?: number): void {
    const { labels, value } =
      typeof labelsOrValue === "number"
        ? { labels: {} as Labels, value: labelsOrValue }
        : { labels: labelsOrValue, value: maybeValue! };
    if (!Number.isFinite(value)) {
      throw new Error(`gauge value must be finite, got ${value}`);
    }
    const norm = normalizeLabels(labels, this.meta.labelKeys);
    const key = labelsKey(norm);
    this.values.set(key, { labels: norm, value });
  }

  inc(labels: Labels = {}, delta = 1): void {
    const cur = this.get(labels);
    this.set(labels, cur + delta);
  }

  dec(labels: Labels = {}, delta = 1): void {
    const cur = this.get(labels);
    this.set(labels, cur - delta);
  }

  get(labels: Labels = {}): number {
    const norm = normalizeLabels(labels, this.meta.labelKeys);
    return this.values.get(labelsKey(norm))?.value ?? 0;
  }

  reset(): void {
    this.values.clear();
  }

  collect(): GaugeSample[] {
    const out: GaugeSample[] = [];
    for (const e of this.values.values()) {
      out.push({ labels: e.labels, value: e.value });
    }
    return out;
  }

  get seriesCount(): number {
    return this.values.size;
  }
}

// ─── Histogram ───────────────────────────────────────────────────────────────

/**
 * Histogram — observations bucketed by upper bound. Used for latencies and
 * sizes. Follows Prometheus `_bucket{le="..."}` conventions.
 */
export class Histogram {
  readonly meta: MetricMeta;
  readonly buckets: readonly number[];
  private readonly entries = new Map<
    string,
    { labels: Labels; bucketCounts: number[]; count: number; sum: number }
  >();

  constructor(meta: Omit<MetricMeta, "kind">, buckets: readonly number[]) {
    for (const k of meta.labelKeys) validateLabelName(k);
    if (buckets.length === 0) {
      throw new Error("histogram requires at least one bucket boundary");
    }
    // Buckets must be strictly increasing and finite.
    for (let i = 0; i < buckets.length; i++) {
      const b = buckets[i];
      if (!Number.isFinite(b)) {
        throw new Error(`bucket ${i} must be finite, got ${b}`);
      }
      if (i > 0 && b <= buckets[i - 1]) {
        throw new Error(`buckets must be strictly increasing (idx=${i})`);
      }
    }
    this.buckets = Object.freeze([...buckets]);
    this.meta = { ...meta, kind: "histogram" };
  }

  observe(labels: Labels, value: number): void;
  observe(value: number): void;
  observe(labelsOrValue: Labels | number, maybeValue?: number): void {
    const { labels, value } =
      typeof labelsOrValue === "number"
        ? { labels: {} as Labels, value: labelsOrValue }
        : { labels: labelsOrValue, value: maybeValue! };
    if (!Number.isFinite(value)) {
      return; // silently ignore NaN/Inf — never block hot path
    }
    const norm = normalizeLabels(labels, this.meta.labelKeys);
    const key = labelsKey(norm);
    let entry = this.entries.get(key);
    if (!entry) {
      entry = {
        labels: norm,
        bucketCounts: new Array<number>(this.buckets.length).fill(0),
        count: 0,
        sum: 0,
      };
      this.entries.set(key, entry);
    }
    entry.count += 1;
    entry.sum += value;
    for (let i = 0; i < this.buckets.length; i++) {
      if (value <= this.buckets[i]) entry.bucketCounts[i] += 1;
    }
  }

  reset(): void {
    this.entries.clear();
  }

  collect(): HistogramSample[] {
    const out: HistogramSample[] = [];
    for (const e of this.entries.values()) {
      out.push({
        labels: e.labels,
        buckets: this.buckets,
        bucketCounts: [...e.bucketCounts],
        count: e.count,
        sum: e.sum,
      });
    }
    return out;
  }

  get seriesCount(): number {
    return this.entries.size;
  }
}

// ─── Common bucket presets ───────────────────────────────────────────────────

export const DURATION_BUCKETS_SECONDS = Object.freeze([
  0.001, 0.01, 0.1, 0.5, 1, 5,
]);

export const RESULT_COUNT_BUCKETS = Object.freeze([1, 5, 10, 20, 50, 100]);

export const SIZE_BUCKETS_BYTES = Object.freeze([
  256, 1024, 4096, 16384, 65536, 262144, 1048576,
]);
