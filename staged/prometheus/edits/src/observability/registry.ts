/**
 * src/observability/registry.ts — MetricsRegistry singleton (T2).
 *
 * The Registry is the central index of all metrics. It is the only place
 * exposed to the exporter (`/metrics`) and the recording API.
 *
 * INVARIANTS:
 *   - At most ONE metric per name across the whole process.
 *   - Re-registering the SAME object (idempotent) is allowed; re-registering
 *     a DIFFERENT object with the same name throws.
 *   - The registry is in-process (Node.js single-threaded); no external lock
 *     is required.
 *   - `collect()` returns an immutable snapshot — safe to render concurrently.
 *
 * SINGLETON PATTERN:
 *   `getDefaultRegistry()` returns a process-wide instance.
 *   Tests should construct a `new MetricsRegistry()` to stay isolated.
 *
 * THREAD-SAFETY:
 *   Node.js is single-threaded for JS; the only race is yielding between
 *   await points. The registry mutations (register/unregister) are
 *   synchronous so cannot interleave.
 */
import { Counter, Gauge, Histogram, type MetricKind } from "./types.js";

export type AnyMetric = Counter | Gauge | Histogram;

export interface RegistrySnapshot {
  /** Wall-clock ms when snapshot was taken. */
  readonly takenAt: number;
  readonly counters: readonly Counter[];
  readonly gauges: readonly Gauge[];
  readonly histograms: readonly Histogram[];
}

export class MetricsRegistry {
  private readonly byName = new Map<string, AnyMetric>();

  /**
   * Register a metric. Idempotent if the same object is re-registered;
   * throws if a DIFFERENT object claims the same name.
   */
  register<M extends AnyMetric>(metric: M): M {
    const existing = this.byName.get(metric.meta.name);
    if (existing) {
      if (existing === metric) return metric; // idempotent
      throw new Error(
        `metric ${JSON.stringify(metric.meta.name)} already registered with different instance`,
      );
    }
    this.byName.set(metric.meta.name, metric);
    return metric;
  }

  /** Remove a metric by name. Returns true if it existed. */
  unregister(name: string): boolean {
    return this.byName.delete(name);
  }

  /** Look up a metric by name (typed by kind). */
  get<K extends MetricKind>(name: string, kind?: K): AnyMetric | undefined {
    const m = this.byName.get(name);
    if (!m) return undefined;
    if (kind && m.meta.kind !== kind) return undefined;
    return m;
  }

  /** Total number of distinct metric *names* (not series). */
  get size(): number {
    return this.byName.size;
  }

  /** All metric names currently registered. */
  names(): string[] {
    return [...this.byName.keys()].sort();
  }

  /**
   * Take an immutable snapshot of all metrics.
   * Returned arrays are sorted by metric name for stable exposition.
   */
  collect(): RegistrySnapshot {
    const counters: Counter[] = [];
    const gauges: Gauge[] = [];
    const histograms: Histogram[] = [];
    const sortedNames = this.names();
    for (const name of sortedNames) {
      const m = this.byName.get(name);
      if (!m) continue;
      switch (m.meta.kind) {
        case "counter":
          counters.push(m as Counter);
          break;
        case "gauge":
          gauges.push(m as Gauge);
          break;
        case "histogram":
          histograms.push(m as Histogram);
          break;
      }
    }
    return Object.freeze({
      takenAt: Date.now(),
      counters: Object.freeze(counters),
      gauges: Object.freeze(gauges),
      histograms: Object.freeze(histograms),
    });
  }

  /** Test-only — wipe all metrics. */
  clear(): void {
    this.byName.clear();
  }

  /** Total series across all metrics (used for cardinality observability). */
  totalSeries(): number {
    let n = 0;
    for (const m of this.byName.values()) {
      n += m.seriesCount;
    }
    return n;
  }
}

// ─── Process-wide default ────────────────────────────────────────────────────

let _default: MetricsRegistry | undefined;

export function getDefaultRegistry(): MetricsRegistry {
  if (!_default) _default = new MetricsRegistry();
  return _default;
}

/** Reset the default registry — test-only. */
export function resetDefaultRegistry(): void {
  _default = new MetricsRegistry();
}
