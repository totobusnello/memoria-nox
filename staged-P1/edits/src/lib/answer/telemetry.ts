/**
 * src/lib/answer/telemetry.ts — P1 T7 scope: persist per-call answer metadata.
 *
 * Writes one row to `answer_telemetry` (schema v11) per answer() invocation,
 * INCLUDING failures (LLM error, hallucination_after_retry, retrieval_empty).
 *
 * Privacy rule (kickoff §critical decision):
 *   - NEVER log raw question or answer text.
 *   - Store `question_hash = sha256(question)[:16]` instead.
 *
 * Storage abstraction:
 *   - `TelemetryStore` interface decouples lib from better-sqlite3.
 *   - `InMemoryTelemetryStore` for tests (push to array, query helpers).
 *   - VPS apply step binds a `Sqlite3TelemetryStore` that targets
 *     `nox-mem.db` opened by the rest of the codebase. We avoid hard-
 *     coding `better-sqlite3` here to keep the staged dir installable
 *     with zero runtime deps (tests use the in-memory store).
 *
 * Cost estimation:
 *   - We accept `cost_estimate_usd` as input from caller (provider knows the
 *     per-model unit price). When absent we derive a 0-USD estimate so the
 *     column stays NOT NULL per v11 schema.
 *
 * Failure-reason mapping:
 *   The v11 schema CHECK constrains `failed_reason IN ('hallucinated_citation',
 *   'provider_down', 'token_budget')` OR NULL. The lib's AnswerFailureReason
 *   enum is broader (includes 'hallucination_after_retry', 'llm_timeout',
 *   'retrieval_empty', 'llm_error', 'invalid_input'). We map to the schema
 *   alphabet in `mapFailureReason()` so the INSERT never violates CHECK.
 */

import { createHash } from "node:crypto";
import type { AnswerFailureReason, AnswerMetadata } from "./types.js";

// ─── Public types ─────────────────────────────────────────────────────────

/** Subset of v11 schema column names — keeps the lib decoupled from SQL. */
export interface AnswerTelemetryRow {
  question_hash: string;
  session_id: string | null;
  timestamp_ms: number;
  provider: string;
  model: string;
  retrieval_count: number;
  citation_count: number;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number;
  fallback_used: 0 | 1;
  failed_reason: SchemaFailureReason | null;
  cost_estimate_usd: number;
}

/** Subset allowed by the v11 schema CHECK. */
export type SchemaFailureReason =
  | "hallucinated_citation"
  | "provider_down"
  | "token_budget";

/** Storage seam: prod implementation wraps better-sqlite3 prepared insert. */
export interface TelemetryStore {
  insert(row: AnswerTelemetryRow): void;
}

/** In-memory store for tests + dev. Keeps every row in `rows`. */
export class InMemoryTelemetryStore implements TelemetryStore {
  public readonly rows: AnswerTelemetryRow[] = [];
  public insert(row: AnswerTelemetryRow): void {
    this.rows.push(row);
  }
  /** Convenience: filter by `failed_reason` (or NULL for success rows). */
  public byFailure(reason: SchemaFailureReason | null): AnswerTelemetryRow[] {
    return this.rows.filter((r) => r.failed_reason === reason);
  }
}

// ─── Privacy helpers ──────────────────────────────────────────────────────

/** sha256(question)[:16] — never store raw question text. */
export function hashQuestion(question: string): string {
  return createHash("sha256").update(question, "utf8").digest("hex").slice(0, 16);
}

// ─── Failure-reason mapping ───────────────────────────────────────────────

/**
 * Map the lib's broader AnswerFailureReason → the narrow v11 schema alphabet.
 * Returns NULL for happy-path success (no failure reason on metadata).
 *
 * Mapping:
 *   hallucinated_citation       → hallucinated_citation
 *   hallucination_after_retry   → hallucinated_citation (root cause is same)
 *   llm_error                   → provider_down
 *   llm_timeout                 → provider_down
 *   retrieval_empty             → NULL (not a failure — surfaces via citations.length=0)
 *   invalid_input               → NULL (caller bug; we still record the row but no SQL-side failure tag)
 */
export function mapFailureReason(
  reason: AnswerFailureReason | undefined
): SchemaFailureReason | null {
  switch (reason) {
    case "hallucinated_citation":
    case "hallucination_after_retry":
      return "hallucinated_citation";
    case "llm_error":
    case "llm_timeout":
      return "provider_down";
    case "retrieval_empty":
    case "invalid_input":
    case undefined:
      return null;
    default:
      return null;
  }
}

// ─── Cost estimation ──────────────────────────────────────────────────────

/**
 * Conservative USD cost estimator. Numbers from D41 #1 baseline; revise via
 * spec, not silently. Returns 0 for unknown models so we never overstate
 * spend in dashboards.
 *
 * Prices in USD per 1M tokens (input / output):
 *   gemini-2.5-flash-lite  → 0.10 / 0.40
 *   gemini-2.5-flash       → 0.30 / 2.50
 *   mock                   → 0     (test)
 */
const PRICE_TABLE: Record<string, { in: number; out: number }> = {
  "gemini-2.5-flash-lite": { in: 0.1, out: 0.4 },
  "gemini-2.5-flash": { in: 0.3, out: 2.5 },
};

export function estimateCost(
  model: string,
  tokensIn: number,
  tokensOut: number
): number {
  const price = PRICE_TABLE[model];
  if (!price) return 0;
  const usd = (tokensIn * price.in + tokensOut * price.out) / 1_000_000;
  // round to 6 decimals — single call almost always sub-cent
  return Math.round(usd * 1_000_000) / 1_000_000;
}

// ─── Public API ───────────────────────────────────────────────────────────

export interface RecordAnswerInput {
  question: string;
  citationCount: number;
  metadata: AnswerMetadata;
  /** Optional session correlation; pass-through from caller (CLI/HTTP/MCP). */
  sessionId?: string | null;
  /** Optional override; if absent we estimate from model + tokens. */
  costEstimateUsd?: number;
  /** Override clock — test seam; defaults to Date.now(). */
  now?: () => number;
}

/**
 * Persist one telemetry row. Returns the row written (useful in tests).
 * Never throws — telemetry failures must NOT break the user-facing answer call.
 * Errors are swallowed and surfaced via process.stderr in non-test mode.
 */
export function recordAnswer(
  store: TelemetryStore,
  input: RecordAnswerInput
): AnswerTelemetryRow {
  const m = input.metadata;
  const tokensIn = m.tokens_in ?? 0;
  const tokensOut = m.tokens_out ?? 0;
  const cost =
    input.costEstimateUsd !== undefined
      ? input.costEstimateUsd
      : estimateCost(m.model, tokensIn, tokensOut);

  const row: AnswerTelemetryRow = {
    question_hash: hashQuestion(input.question),
    session_id: input.sessionId ?? null,
    timestamp_ms: (input.now ?? Date.now)(),
    provider: m.provider,
    model: m.model,
    retrieval_count: m.retrieval_count,
    citation_count: input.citationCount,
    tokens_in: m.tokens_in ?? null,
    tokens_out: m.tokens_out ?? null,
    latency_ms: m.latency_ms,
    fallback_used: m.fallback_used ? 1 : 0,
    failed_reason: mapFailureReason(m.failed_reason),
    cost_estimate_usd: cost,
  };

  try {
    store.insert(row);
  } catch (err) {
    // Telemetry MUST NOT break the call. Log to stderr (best-effort) and
    // swallow so the caller still receives the answer.
    if (process.env.NODE_ENV !== "test") {
      process.stderr.write(
        `[answer/telemetry] insert failed: ${(err as Error).message}\n`
      );
    }
  }

  return row;
}

// ─── SQL hints (for VPS-side adapter, kept here as a runbook) ─────────────

/**
 * Prepared INSERT string the VPS adapter should use. Exported so the apply
 * step can `const STMT = db.prepare(INSERT_SQL)` without re-deriving column
 * order from scratch.
 */
export const INSERT_SQL = `
INSERT INTO answer_telemetry (
  question_hash, session_id, timestamp_ms, provider, model,
  retrieval_count, citation_count, tokens_in, tokens_out,
  latency_ms, fallback_used, failed_reason, cost_estimate_usd
) VALUES (
  @question_hash, @session_id, @timestamp_ms, @provider, @model,
  @retrieval_count, @citation_count, @tokens_in, @tokens_out,
  @latency_ms, @fallback_used, @failed_reason, @cost_estimate_usd
)`.trim();
