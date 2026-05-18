/**
 * src/observability/adapters/a3-adapter.ts — Provider call instrumentation.
 *
 * Wraps any provider call (LLM or embedding) with:
 *   - nox_provider_calls_total{provider, model, outcome}
 *   - nox_provider_duration_seconds{provider, kind}
 *   - nox_provider_cost_usd_total{provider, model}
 *   - nox_provider_tokens_total{provider, direction}
 *
 * Composes with the existing `provider_telemetry` write path (kept intact).
 * Metrics are *live* per-call; telemetry is durable per-row.
 *
 * Wiring example (in src/providers/llm/chain.ts):
 *
 *   import { instrumentProviderCall } from "../observability/adapters/a3-adapter.js";
 *
 *   const result = await instrumentProviderCall(
 *     { provider: "gemini", model: "gemini-2.5-flash-lite", kind: "llm" },
 *     () => callGeminiAPI(prompt),
 *   );
 *
 * `instrumentProviderCall` returns the inner result + a `metricsCost` field
 * for the caller to inspect.
 */
import { recordProviderCall, startTimer, type ProviderKind, type ProviderOutcome } from "../record.js";

export interface ProviderCallMeta {
  provider: string;
  model: string;
  kind: ProviderKind;
}

export interface ProviderCallResult<T> {
  result: T;
  costUsd?: number;
  tokensIn?: number;
  tokensOut?: number;
}

export type ProviderInner<T> = () => Promise<ProviderCallResult<T>>;

/**
 * Run an inner provider call. Always emits metrics, regardless of success.
 * Errors propagate; the outcome label maps to:
 *   - "rate_limit" if err.status === 429
 *   - "fallback"   if err.code === "FALLBACK"
 *   - "error"      otherwise
 */
export async function instrumentProviderCall<T>(
  meta: ProviderCallMeta,
  inner: ProviderInner<T>,
): Promise<T> {
  const end = startTimer();
  try {
    const { result, costUsd, tokensIn, tokensOut } = await inner();
    recordProviderCall({
      ...meta,
      outcome: "success",
      durationSeconds: end(),
      costUsd,
      tokensIn,
      tokensOut,
    });
    return result;
  } catch (err) {
    const outcome = classifyProviderError(err);
    recordProviderCall({
      ...meta,
      outcome,
      durationSeconds: end(),
    });
    throw err;
  }
}

export function classifyProviderError(err: unknown): ProviderOutcome {
  if (!err || typeof err !== "object") return "error";
  const e = err as { status?: number; code?: string };
  if (e.status === 429) return "rate_limit";
  if (e.code === "FALLBACK" || e.code === "PROVIDER_FALLBACK") return "fallback";
  return "error";
}

/**
 * Example — adding metrics to an existing provider call:
 *
 *   // before:
 *   const out = await callGemini(input);
 *
 *   // after:
 *   const out = await instrumentProviderCall(
 *     { provider: "gemini", model, kind: "llm" },
 *     async () => {
 *       const r = await callGemini(input);
 *       return { result: r, tokensIn: r.usage.in, tokensOut: r.usage.out, costUsd: estimateCost(r) };
 *     },
 *   );
 *
 * Total integration footprint: 1 import + 3-4 LOC at the call site.
 */
