/**
 * src/providers/telemetry.ts — Provider telemetry recording (T12 / spec T11).
 *
 * Records each provider call: provider_id, model, kind, latency, tokens, cost, success.
 * Schema v11 `provider_telemetry` table (see spec §5).
 *
 * PRIVACY INVARIANTS (non-negotiable):
 *   - NO prompts logged.
 *   - NO response text logged.
 *   - Caller name + token count + cost + latency ONLY.
 *   - API keys are NEVER stored — `redactSecrets()` applied to any error_kind string.
 *
 * This module is intentionally DB-agnostic:
 *   - Production callers inject `writeFn` pointing to SQLite `provider_telemetry`.
 *   - Tests inject a no-op or array collector.
 *   - The `ProviderTelemetryRow` type mirrors schema v11 exactly.
 *
 * Write-behind queue:
 *   - `recordProviderCall()` enqueues the row and resolves immediately.
 *   - Flush happens in background via `flushQueue()`.
 *   - Queue is bounded (default 500 rows). Oldest entries dropped on overflow.
 *   - `drain()` flushes synchronously for tests and graceful shutdown.
 */
import { redactSecrets } from "./embedding/gemini.js";

// ─── Row type (mirrors schema v11) ───────────────────────────────────────────

export interface ProviderTelemetryRow {
  /** Unix ms timestamp. */
  ts: number;
  /** Provider id: 'gemini' | 'openai' | 'anthropic' | 'voyage'. */
  provider_id: string;
  /** Model id: e.g. 'gemini-2.5-flash-lite'. */
  model: string;
  /** 'embedding' | 'llm'. */
  kind: "embedding" | "llm";
  /** Input tokens billed (0 for embedding calls that don't report tokens). */
  tokens_in: number;
  /** Output tokens billed (0 for embedding calls). */
  tokens_out: number;
  /** Estimated cost in USD. */
  cost_usd: number;
  /** Wall-clock latency ms. */
  latency_ms: number;
  /** 1 = success, 0 = error. */
  ok: 0 | 1;
  /** Which caller produced this call: 'vectorize' | 'kg-extract' | 'reflect' | etc. */
  caller?: string;
  /** Session id for correlation (optional). */
  session_id?: string;
  /** Redacted error kind if ok=0. NEVER contains prompt text or keys. */
  error_kind?: string;
}

// ─── Write function type ──────────────────────────────────────────────────────

export type TelemetryWriteFn = (row: ProviderTelemetryRow) => Promise<void>;

// ─── In-process write-behind queue ───────────────────────────────────────────

const DEFAULT_QUEUE_CAPACITY = 500;

export interface TelemetryQueueOpts {
  writeFn?: TelemetryWriteFn;
  capacity?: number;
  /** Called on write error (default: console.error). Never throws. */
  onError?: (err: unknown) => void;
}

export class TelemetryQueue {
  private readonly queue: ProviderTelemetryRow[] = [];
  private readonly capacity: number;
  private readonly writeFn: TelemetryWriteFn;
  private readonly onError: (err: unknown) => void;
  private flushing = false;

  constructor(opts: TelemetryQueueOpts = {}) {
    this.capacity = opts.capacity ?? DEFAULT_QUEUE_CAPACITY;
    this.writeFn = opts.writeFn ?? noopWrite;
    this.onError = opts.onError ?? defaultOnError;
  }

  /** Enqueue a row. Returns immediately. Drops oldest on overflow. */
  enqueue(row: ProviderTelemetryRow): void {
    if (this.queue.length >= this.capacity) {
      // Drop oldest entry (ring-buffer behaviour).
      this.queue.shift();
    }
    this.queue.push(row);
    // Kick off background flush (non-blocking).
    this.scheduleFlush();
  }

  private scheduleFlush(): void {
    if (this.flushing) return;
    this.flushing = true;
    // Use setImmediate if available (Node.js), else microtask fallback.
    const schedFn =
      typeof setImmediate === "function"
        ? (fn: () => void) => setImmediate(fn)
        : (fn: () => void) => Promise.resolve().then(fn);
    schedFn(() => {
      this.flushSync().catch(this.onError).finally(() => {
        this.flushing = false;
      });
    });
  }

  private async flushSync(): Promise<void> {
    while (this.queue.length > 0) {
      const row = this.queue.shift();
      if (!row) break;
      try {
        await this.writeFn(row);
      } catch (err) {
        this.onError(err);
      }
    }
  }

  /** Drain all queued rows synchronously. Use for graceful shutdown + tests. */
  async drain(): Promise<void> {
    await this.flushSync();
  }

  /** Peek at current queue length (for monitoring). */
  get pending(): number {
    return this.queue.length;
  }
}

async function noopWrite(_row: ProviderTelemetryRow): Promise<void> {
  // Default no-op: safe to use when no DB is available.
}

function defaultOnError(err: unknown): void {
  const msg = err instanceof Error ? err.message : String(err);
  // Use console.error but never throw — telemetry must not affect caller.
  console.error(`[provider-telemetry] write error: ${msg}`);
}

// ─── Global default queue (can be replaced via setDefaultQueue) ───────────────

let _defaultQueue: TelemetryQueue = new TelemetryQueue();

export function setDefaultQueue(q: TelemetryQueue): void {
  _defaultQueue = q;
}

export function getDefaultQueue(): TelemetryQueue {
  return _defaultQueue;
}

// ─── Recording helpers ────────────────────────────────────────────────────────

export interface RecordCallOpts {
  provider_id: string;
  model: string;
  kind: "embedding" | "llm";
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number;
  latency_ms: number;
  ok: boolean;
  caller?: string;
  session_id?: string;
  /** Raw error message — will be redacted before logging. */
  errorRaw?: string;
  queue?: TelemetryQueue;
}

/** Record a provider call into the telemetry queue. Never throws. */
export function recordProviderCall(opts: RecordCallOpts): void {
  try {
    const row: ProviderTelemetryRow = {
      ts: Date.now(),
      provider_id: opts.provider_id,
      model: opts.model,
      kind: opts.kind,
      tokens_in: opts.tokens_in ?? 0,
      tokens_out: opts.tokens_out ?? 0,
      cost_usd: opts.cost_usd ?? 0,
      latency_ms: Math.round(opts.latency_ms),
      ok: opts.ok ? 1 : 0,
      caller: opts.caller,
      session_id: opts.session_id,
      // Redact error to prevent key leakage in stored rows.
      error_kind: opts.errorRaw ? redactSecrets(opts.errorRaw).slice(0, 200) : undefined,
    };
    const q = opts.queue ?? _defaultQueue;
    q.enqueue(row);
  } catch {
    // Never propagate telemetry errors to caller.
  }
}

// ─── Aggregated stats (for /api/health.cost) ─────────────────────────────────

export interface CostAggregate {
  /** USD spent in last 24h. */
  last24hUsd: number;
  /** Total calls in last 24h. */
  last24hCalls: number;
  /** Success rate 0-1 in last 24h. */
  last24hSuccessRate: number;
  /** Per-provider breakdown. */
  byProvider: Record<string, { usd: number; calls: number }>;
}

/**
 * Compute aggregates from an array of rows.
 * In production, the API layer queries `provider_telemetry` directly via SQL.
 * This function is provided for in-memory tests.
 */
export function aggregateCosts(
  rows: ProviderTelemetryRow[],
  nowMs = Date.now(),
): CostAggregate {
  const windowMs = 24 * 60 * 60 * 1000;
  const cutoff = nowMs - windowMs;
  const recent = rows.filter((r) => r.ts >= cutoff);

  let totalUsd = 0;
  let successCount = 0;
  const byProvider: Record<string, { usd: number; calls: number }> = {};

  for (const row of recent) {
    totalUsd += row.cost_usd;
    if (row.ok === 1) successCount++;
    const p = byProvider[row.provider_id];
    if (p) {
      p.usd += row.cost_usd;
      p.calls += 1;
    } else {
      byProvider[row.provider_id] = { usd: row.cost_usd, calls: 1 };
    }
  }

  return {
    last24hUsd: totalUsd,
    last24hCalls: recent.length,
    last24hSuccessRate: recent.length > 0 ? successCount / recent.length : 1,
    byProvider,
  };
}
