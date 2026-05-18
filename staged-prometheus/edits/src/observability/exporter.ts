/**
 * src/observability/exporter.ts — `/metrics` exporter (T5).
 *
 * Serializes the registry snapshot to OpenMetrics text format (Prometheus
 * 0.0.4+ compatible).
 *
 * RESPONSIBILITIES:
 *   1. Render Counter / Gauge / Histogram in canonical order.
 *   2. Filter by `?names=metric1,metric2` (CSV).
 *   3. Optional Bearer-token auth (`NOX_METRICS_TOKEN` env).
 *   4. Gzip the body when Accept-Encoding lists gzip.
 *
 * NEVER expose:
 *   - Stack traces
 *   - Caller identity
 *   - Anything beyond the registered metrics
 *
 * The exporter is designed to be transport-agnostic. The `handle()` function
 * accepts a Request-like input and returns a Response-like output, so it can
 * plug into the existing nox-mem HTTP API (port 18802) or any Node http
 * server.
 */
import { gzipSync } from "node:zlib";
import { getDefaultRegistry, type MetricsRegistry, type RegistrySnapshot } from "./registry.js";
import {
  type Counter,
  type Gauge,
  type Histogram,
  escapeLabelValue,
} from "./types.js";

// ─── Content-type & version ─────────────────────────────────────────────────

export const OPENMETRICS_CONTENT_TYPE =
  "application/openmetrics-text; version=1.0.0; charset=utf-8";

export const PROMETHEUS_CONTENT_TYPE =
  "text/plain; version=0.0.4; charset=utf-8";

// ─── Rendering ───────────────────────────────────────────────────────────────

/**
 * Render a full snapshot to text. Stable line order:
 *   - Sorted by metric name.
 *   - For each metric: `# HELP`, `# TYPE`, optional `# UNIT`, samples.
 *   - Samples within a metric: sorted by stringified labels.
 */
export function render(snapshot: RegistrySnapshot): string {
  const lines: string[] = [];

  // Render counters
  for (const c of snapshot.counters) {
    renderCounter(c, lines);
  }
  // Render gauges
  for (const g of snapshot.gauges) {
    renderGauge(g, lines);
  }
  // Render histograms
  for (const h of snapshot.histograms) {
    renderHistogram(h, lines);
  }
  // OpenMetrics EOF terminator (optional in Prometheus mode; safe in both).
  lines.push("# EOF");
  return lines.join("\n") + "\n";
}

function renderHeader(meta: { name: string; help: string; kind: string; unit?: string }, lines: string[]): void {
  lines.push(`# HELP ${meta.name} ${escapeHelp(meta.help)}`);
  lines.push(`# TYPE ${meta.name} ${meta.kind}`);
  if (meta.unit) lines.push(`# UNIT ${meta.name} ${meta.unit}`);
}

function escapeHelp(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/\n/g, "\\n");
}

function labelsToString(labels: Record<string, string>): string {
  const keys = Object.keys(labels).sort();
  if (keys.length === 0) return "";
  const parts: string[] = [];
  for (const k of keys) {
    const v = labels[k];
    if (typeof v !== "string") continue;
    parts.push(`${k}="${escapeLabelValue(v)}"`);
  }
  if (parts.length === 0) return "";
  return `{${parts.join(",")}}`;
}

function renderCounter(c: Counter, lines: string[]): void {
  renderHeader(c.meta, lines);
  const samples = sortSamples(
    c.collect().map((s) => ({ labels: s.labels, value: s.value })),
  );
  for (const s of samples) {
    lines.push(`${c.meta.name}${labelsToString(s.labels)} ${formatValue(s.value)}`);
  }
}

function renderGauge(g: Gauge, lines: string[]): void {
  renderHeader(g.meta, lines);
  const samples = sortSamples(
    g.collect().map((s) => ({ labels: s.labels, value: s.value })),
  );
  for (const s of samples) {
    lines.push(`${g.meta.name}${labelsToString(s.labels)} ${formatValue(s.value)}`);
  }
}

function renderHistogram(h: Histogram, lines: string[]): void {
  renderHeader(h.meta, lines);
  for (const s of h.collect()) {
    const base: Record<string, string> = { ...(s.labels as Record<string, string>) };
    for (let i = 0; i < s.buckets.length; i++) {
      const lbl = { ...base, le: formatLe(s.buckets[i]) };
      lines.push(
        `${h.meta.name}_bucket${labelsToString(lbl)} ${formatValue(s.bucketCounts[i])}`,
      );
    }
    // +Inf bucket
    const inf = { ...base, le: "+Inf" };
    lines.push(`${h.meta.name}_bucket${labelsToString(inf)} ${formatValue(s.count)}`);
    lines.push(`${h.meta.name}_sum${labelsToString(base)} ${formatValue(s.sum)}`);
    lines.push(`${h.meta.name}_count${labelsToString(base)} ${formatValue(s.count)}`);
  }
}

function sortSamples<T extends { labels: Record<string, string> }>(samples: T[]): T[] {
  return [...samples].sort((a, b) =>
    labelsToString(a.labels).localeCompare(labelsToString(b.labels)),
  );
}

function formatValue(v: number): string {
  if (Number.isInteger(v)) return String(v);
  return v.toString();
}

function formatLe(v: number): string {
  // Use plain number; Prometheus accepts both "1" and "1.0".
  return v.toString();
}

// ─── HTTP handler shape ──────────────────────────────────────────────────────

export interface MetricsRequest {
  /** Lower-cased URL search params for filtering, e.g. ?names=a,b */
  searchParams?: URLSearchParams | Record<string, string>;
  /** Standard HTTP headers as a Record (lower-case keys). */
  headers?: Record<string, string | string[] | undefined>;
}

export interface MetricsResponse {
  status: number;
  headers: Record<string, string>;
  /** Body — string or Buffer (when gzipped). */
  body: string | Buffer;
}

export interface ExporterOpts {
  registry?: MetricsRegistry;
  /** If set, require `Authorization: Bearer <token>`. */
  token?: string;
  /** Content type — defaults to OpenMetrics. */
  contentType?: string;
}

export function handle(req: MetricsRequest, opts: ExporterOpts = {}): MetricsResponse {
  const token = opts.token ?? process.env.NOX_METRICS_TOKEN;
  if (token) {
    const auth = headerString(req.headers, "authorization");
    if (!auth || !auth.startsWith("Bearer ") || auth.slice(7) !== token) {
      return {
        status: 401,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "www-authenticate": 'Bearer realm="nox-metrics"',
        },
        body: "unauthorized\n",
      };
    }
  }

  const reg = opts.registry ?? getDefaultRegistry();
  const snap = reg.collect();
  const names = parseNames(req.searchParams);

  const filtered = names.size === 0 ? snap : filterSnapshot(snap, names);
  const text = render(filtered);

  const acceptEnc = headerString(req.headers, "accept-encoding") ?? "";
  const wantsGzip = /\bgzip\b/i.test(acceptEnc);

  const headers: Record<string, string> = {
    "content-type": opts.contentType ?? OPENMETRICS_CONTENT_TYPE,
    "cache-control": "no-store",
    "x-metrics-snapshot-at": String(snap.takenAt),
  };

  if (wantsGzip) {
    const body = gzipSync(Buffer.from(text, "utf8"));
    headers["content-encoding"] = "gzip";
    headers["content-length"] = String(body.length);
    return { status: 200, headers, body };
  }
  return { status: 200, headers, body: text };
}

function headerString(
  headers: Record<string, string | string[] | undefined> | undefined,
  name: string,
): string | undefined {
  if (!headers) return undefined;
  const v = headers[name] ?? headers[name.toLowerCase()];
  if (Array.isArray(v)) return v[0];
  return v;
}

function parseNames(params: MetricsRequest["searchParams"]): Set<string> {
  if (!params) return new Set();
  const raw =
    params instanceof URLSearchParams
      ? params.get("names")
      : (params as Record<string, string>)["names"];
  if (!raw) return new Set();
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0),
  );
}

function filterSnapshot(snap: RegistrySnapshot, names: Set<string>): RegistrySnapshot {
  return Object.freeze({
    takenAt: snap.takenAt,
    counters: snap.counters.filter((c) => names.has(c.meta.name)),
    gauges: snap.gauges.filter((g) => names.has(g.meta.name)),
    histograms: snap.histograms.filter((h) => names.has(h.meta.name)),
  });
}
