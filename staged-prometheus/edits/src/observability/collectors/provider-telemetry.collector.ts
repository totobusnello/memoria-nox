/**
 * src/observability/collectors/provider-telemetry.collector.ts
 *
 * Reads `provider_telemetry` (schema v11, A3) and translates rows into
 * `nox_provider_*` metric increments.
 *
 * Columns (per A3 telemetry spec):
 *   ts, provider_id, model, kind ('embedding'|'llm'),
 *   tokens_in, tokens_out, cost_usd, latency_ms, ok (0|1),
 *   caller, session_id, error_kind
 *
 * Privacy: `error_kind` is already redacted at write time (see
 * src/providers/telemetry.ts). We do NOT export caller or session_id.
 */
import {
  providerCallsTotal,
  providerDurationSeconds,
  providerCostUsdTotal,
  providerTokensTotal,
  auditRowsTotal,
} from "../metrics.js";
import { guardLabels } from "../privacy-guard.js";

export type DbQueryFn = (
  sql: string,
  params?: ReadonlyArray<string | number>,
) => Array<Record<string, unknown>>;

export interface ProviderTelemetryCollectorOpts {
  query: DbQueryFn;
  intervalMs?: number;
  startId?: number;
}

let intervalHandle: NodeJS.Timeout | undefined;
let cursor = 0;

export function startProviderTelemetryCollector(
  opts: ProviderTelemetryCollectorOpts,
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

export function stopProviderTelemetryCollector(): void {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = undefined;
  }
}

export function drain(query: DbQueryFn): number {
  const rows = query(
    `SELECT id, provider_id, model, kind, tokens_in, tokens_out,
            cost_usd, latency_ms, ok
       FROM provider_telemetry
      WHERE id > ?
      ORDER BY id ASC
      LIMIT 1000`,
    [cursor],
  );
  for (const r of rows) {
    const id = Number(r.id);
    const provider = String(r.provider_id ?? "other");
    const model = String(r.model ?? "unknown");
    const kind = String(r.kind ?? "llm");
    const tokensIn = Number(r.tokens_in ?? 0);
    const tokensOut = Number(r.tokens_out ?? 0);
    const cost = Number(r.cost_usd ?? 0);
    const latMs = Number(r.latency_ms ?? 0);
    const ok = Number(r.ok ?? 0) === 1;

    const outcome = ok ? "success" : "error";
    const callL = guardLabels("nox_provider_calls_total", {
      provider,
      model,
      outcome,
    }).labels;
    if (callL) providerCallsTotal.inc(callL);

    const durL = guardLabels("nox_provider_duration_seconds", {
      provider,
      kind,
    }).labels;
    if (durL) providerDurationSeconds.observe(durL, latMs / 1000);

    if (cost > 0) {
      const costL = guardLabels("nox_provider_cost_usd_total", {
        provider,
        model,
      }).labels;
      if (costL) providerCostUsdTotal.inc(costL, cost);
    }
    if (tokensIn > 0) {
      const lbl = guardLabels("nox_provider_tokens_total", {
        provider,
        direction: "input",
      }).labels;
      if (lbl) providerTokensTotal.inc(lbl, tokensIn);
    }
    if (tokensOut > 0) {
      const lbl = guardLabels("nox_provider_tokens_total", {
        provider,
        direction: "output",
      }).labels;
      if (lbl) providerTokensTotal.inc(lbl, tokensOut);
    }

    const auditL = guardLabels("nox_audit_rows_total", {
      table: "provider_telemetry",
    }).labels;
    if (auditL) auditRowsTotal.inc(auditL);

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
