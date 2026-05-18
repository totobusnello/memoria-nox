/**
 * src/lib/cost-cap.ts — Daily cost cap mechanism (T10 / spec T12).
 *
 * `CostCappedProvider` wraps any LLMProvider with a daily/hourly budget cap.
 * Tracks tokens × $/token from `PRICE_TABLE_USD_PER_1M` (or custom table).
 *
 * Configuration:
 *   NOX_PROVIDER_DAILY_USD_CAP=50.00      (default)
 *   NOX_PROVIDER_DAILY_USD_CAP_BYPASS=1   (explicit bypass — writes audit row)
 *
 * Cap check pre-call: if today's SUM(cost_usd) >= cap → throw CostCapExceededError.
 * Reset interval: daily at UTC midnight (rolling window configurable).
 *
 * INVARIANTS:
 *   - CostCapExceededError MUST NOT contain prompt content — only counts.
 *   - Bypass MUST write an audit record (never silent).
 *   - Cap check must complete within 200ms of window start crossing.
 *   - This module has NO SQLite dependency — it uses in-memory state.
 *     Production callers inject an `accumulatedCostFn` that queries provider_telemetry.
 */
import type { LLMProvider, CompleteOpts, CompleteResult } from "../providers/llm/types.js";
import type { HealthStatus } from "../providers/types.js";

// ─── Error type ──────────────────────────────────────────────────────────────

/** Thrown when the daily spend cap is exceeded. MUST NOT contain prompt content. */
export class CostCapExceededError extends Error {
  public readonly capUsd: number;
  public readonly spentUsd: number;
  public readonly resetAtUtc: string; // ISO date string

  constructor(capUsd: number, spentUsd: number, resetAtUtc: string) {
    // CRITICAL: no prompt content here — only numbers.
    super(
      `CostCapExceededError: daily spend cap of $${capUsd.toFixed(4)} USD exceeded ` +
        `(accumulated: $${spentUsd.toFixed(4)} USD). ` +
        `Cap resets at ${resetAtUtc} UTC. ` +
        `Set NOX_PROVIDER_DAILY_USD_CAP_BYPASS=1 to override (logged to ops_audit).`,
    );
    this.name = "CostCapExceededError";
    this.capUsd = capUsd;
    this.spentUsd = spentUsd;
    this.resetAtUtc = resetAtUtc;
  }
}

// ─── Price table ─────────────────────────────────────────────────────────────

/**
 * Price table: USD per 1M tokens (input).
 * Sources: public pricing pages as of 2026-05.
 * These are used for real-time cost estimation — reconcile vs invoice monthly.
 */
export const PRICE_TABLE_USD_PER_1M_INPUT: Record<string, number> = {
  "gemini-2.5-flash-lite": 0.10,
  "gemini-2.5-flash": 0.30,
  "gemini-2.5-pro": 1.25,
  "gpt-4o-mini": 0.15,
  "gpt-4o": 2.50,
  "claude-3-5-haiku": 0.80,
  "claude-3-5-sonnet": 3.00,
};

export const PRICE_TABLE_USD_PER_1M_OUTPUT: Record<string, number> = {
  "gemini-2.5-flash-lite": 0.40,
  "gemini-2.5-flash": 2.50,
  "gemini-2.5-pro": 10.00,
  "gpt-4o-mini": 0.60,
  "gpt-4o": 10.00,
  "claude-3-5-haiku": 4.00,
  "claude-3-5-sonnet": 15.00,
};

/** Estimate cost in USD from token counts + model name. Returns 0 if model unknown. */
export function estimateCostUsd(
  model: string,
  tokensIn: number,
  tokensOut: number,
): number {
  const inPrice = PRICE_TABLE_USD_PER_1M_INPUT[model] ?? 0;
  const outPrice = PRICE_TABLE_USD_PER_1M_OUTPUT[model] ?? 0;
  return (tokensIn / 1_000_000) * inPrice + (tokensOut / 1_000_000) * outPrice;
}

// ─── Audit record ─────────────────────────────────────────────────────────────

export interface BypassAuditRecord {
  ts: number;          // Date.now() ms
  capUsd: number;
  spentUsd: number;
  model: string;
  providerId: string;
}

// ─── CostCappedProvider ───────────────────────────────────────────────────────

export interface CostCapOpts {
  /** Provider to wrap. */
  provider: LLMProvider;
  /**
   * Daily cap in USD. Default: 50.00.
   * Overridden by `NOX_PROVIDER_DAILY_USD_CAP` env at construction time.
   */
  capUsd?: number;
  /**
   * Async function that returns total USD spent today (since midnight UTC).
   * In production this queries `SUM(cost_usd)` from `provider_telemetry`.
   * Default: in-memory accumulator (resets on process restart).
   */
  accumulatedCostFn?: () => Promise<number>;
  /**
   * Whether the bypass env var is active. Default: reads `NOX_PROVIDER_DAILY_USD_CAP_BYPASS`.
   * Pass env seam for testing.
   */
  bypassFn?: () => boolean;
  /**
   * Callback to record bypass events (replaces ops_audit write in isolated module).
   * In production the API layer wires this to `withOpAudit()`.
   */
  onBypass?: (record: BypassAuditRecord) => void;
  /**
   * Callback to accumulate cost after a successful call.
   * Production: inserts row into provider_telemetry.
   * Default: updates in-memory accumulator.
   */
  onCost?: (costUsd: number, model: string, providerId: string) => void;
  /** Env override for tests. */
  env?: NodeJS.ProcessEnv;
}

/** In-memory fallback accumulator (single-day rolling window). */
let inMemorySpentUsd = 0;
let inMemoryWindowStart = startOfDayUtcMs();

function startOfDayUtcMs(): number {
  const now = new Date();
  return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
}

/** Reset the in-memory accumulator (test utility). */
export function resetInMemoryAccumulator(): void {
  inMemorySpentUsd = 0;
  inMemoryWindowStart = startOfDayUtcMs();
}

function defaultAccumulatedCostFn(): Promise<number> {
  // Rotate window at midnight UTC.
  const dayStart = startOfDayUtcMs();
  if (dayStart > inMemoryWindowStart) {
    inMemorySpentUsd = 0;
    inMemoryWindowStart = dayStart;
  }
  return Promise.resolve(inMemorySpentUsd);
}

function defaultOnCost(costUsd: number): void {
  // Rotate window first.
  const dayStart = startOfDayUtcMs();
  if (dayStart > inMemoryWindowStart) {
    inMemorySpentUsd = 0;
    inMemoryWindowStart = dayStart;
  }
  inMemorySpentUsd += costUsd;
}

export class CostCappedProvider implements LLMProvider {
  public readonly name: string;
  public readonly model: string;
  public readonly contextWindow: number;

  private readonly provider: LLMProvider;
  private readonly capUsd: number;
  private readonly accumulatedCostFn: () => Promise<number>;
  private readonly bypassFn: () => boolean;
  private readonly onBypass?: (record: BypassAuditRecord) => void;
  private readonly onCost: (costUsd: number, model: string, providerId: string) => void;

  constructor(opts: CostCapOpts) {
    this.provider = opts.provider;
    this.name = opts.provider.name;
    this.model = opts.provider.model;
    this.contextWindow = opts.provider.contextWindow;

    const env = opts.env ?? process.env;
    const capFromEnv = parseFloat(env.NOX_PROVIDER_DAILY_USD_CAP ?? "50.00");
    this.capUsd = opts.capUsd ?? (isFinite(capFromEnv) ? capFromEnv : 50.00);

    this.accumulatedCostFn = opts.accumulatedCostFn ?? defaultAccumulatedCostFn;
    this.bypassFn =
      opts.bypassFn ?? (() => (opts.env ?? process.env).NOX_PROVIDER_DAILY_USD_CAP_BYPASS === "1");
    this.onBypass = opts.onBypass;
    this.onCost = opts.onCost ?? defaultOnCost;
  }

  public async complete(opts: CompleteOpts): Promise<CompleteResult> {
    const spent = await this.accumulatedCostFn();
    const bypass = this.bypassFn();

    if (spent >= this.capUsd) {
      if (!bypass) {
        const resetAt = new Date(startOfDayUtcMs() + 86_400_000).toISOString().slice(0, 10);
        throw new CostCapExceededError(this.capUsd, spent, resetAt);
      }
      // Bypass active → audit log + proceed.
      this.onBypass?.({
        ts: Date.now(),
        capUsd: this.capUsd,
        spentUsd: spent,
        model: this.model,
        providerId: this.name,
      });
    }

    const result = await this.provider.complete(opts);

    // Track cost after successful call.
    const costUsd = estimateCostUsd(this.model, result.tokensIn, result.tokensOut);
    this.onCost(costUsd, this.model, this.name);

    return result;
  }

  public async healthCheck(): Promise<HealthStatus> {
    return this.provider.healthCheck();
  }
}
