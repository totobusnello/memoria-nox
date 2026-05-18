/**
 * src/observability/collectors/search-telemetry.collector.ts
 *
 * Polls `search_telemetry` (post-A0 column set) and translates rows into
 * `nox_search_*` metric increments. Rows are read in batches keyed by an
 * incrementing cursor so we don't double-count.
 *
 * Schema dependency:
 *   search_telemetry(id INTEGER PK, ts INTEGER, method TEXT, duration_ms INTEGER,
 *                    results_count INTEGER, outcome TEXT, …)
 *
 * IMPORTANT: This collector does NOT read query_text — it only consumes the
 * categorical fields. Privacy invariant.
 */
import {
  searchRequestsTotal,
  searchDurationSeconds,
  searchResultsReturned,
} from "../metrics.js";
import { guardLabels } from "../privacy-guard.js";

export type DbQueryFn = (
  sql: string,
  params?: ReadonlyArray<string | number>,
) => Array<Record<string, unknown>>;

export interface SearchTelemetryCollectorOpts {
  query: DbQueryFn;
  intervalMs?: number;
  /** Initial cursor (id watermark). Default 0. */
  startId?: number;
}

let intervalHandle: NodeJS.Timeout | undefined;
let cursor = 0;

export function startSearchTelemetryCollector(
  opts: SearchTelemetryCollectorOpts,
): void {
  if (intervalHandle) return;
  cursor = opts.startId ?? 0;
  const interval = opts.intervalMs ?? 5_000;
  const runOnce = () => {
    try {
      drain(opts.query);
    } catch {
      // never crash
    }
  };
  runOnce();
  intervalHandle = setInterval(runOnce, interval);
  intervalHandle.unref?.();
}

export function stopSearchTelemetryCollector(): void {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = undefined;
  }
}

export function drain(query: DbQueryFn): number {
  const rows = query(
    `SELECT id, method, duration_ms, results_count, outcome
       FROM search_telemetry
      WHERE id > ?
      ORDER BY id ASC
      LIMIT 1000`,
    [cursor],
  );
  for (const r of rows) {
    const id = Number(r.id);
    const method = String(r.method ?? "other");
    const durMs = Number(r.duration_ms ?? 0);
    const count = Number(r.results_count ?? 0);
    const outcome = String(r.outcome ?? "success");

    const reqL = guardLabels("nox_search_requests_total", {
      method,
      outcome,
    }).labels;
    if (reqL) searchRequestsTotal.inc(reqL);
    const durL = guardLabels("nox_search_duration_seconds", { method }).labels;
    if (durL) searchDurationSeconds.observe(durL, durMs / 1000);
    const resL = guardLabels("nox_search_results_returned", { method }).labels;
    if (resL) searchResultsReturned.observe(resL, count);

    if (id > cursor) cursor = id;
  }
  return rows.length;
}

export function getCursor(): number {
  return cursor;
}

export function resetCursor(): void {
  cursor = 0;
}
