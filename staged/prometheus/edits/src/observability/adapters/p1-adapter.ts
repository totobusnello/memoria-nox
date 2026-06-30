/**
 * src/observability/adapters/p1-adapter.ts — P1 /api/answer instrumentation.
 *
 * Wraps the answer handler so every call emits:
 *   - nox_answer_requests_total{failure_reason}
 *   - nox_answer_duration_seconds{phase}
 *   - nox_answer_tokens_total{direction}
 *
 * Wiring example (in src/api/answer.ts):
 *
 *   import { withAnswerMetrics } from "../observability/adapters/p1-adapter.js";
 *
 *   export const answerHandler = withAnswerMetrics(async (req, res) => {
 *     // … existing logic
 *     return { outcome: "success", tokensIn, tokensOut, phases };
 *   });
 *
 * The wrapper expects the inner handler to return an `AnswerOutcome` object.
 * That keeps metrics emission *external* to business logic — easy to unit
 * test, easy to remove.
 */
import { recordAnswer, startTimer, type AnswerOutcome, type AnswerTiming } from "../record.js";

export interface AnswerResult {
  outcome: AnswerOutcome;
  tokensIn?: number;
  tokensOut?: number;
  timing?: AnswerTiming;
}

export type AnswerHandler<Args extends unknown[]> = (
  ...args: Args
) => Promise<AnswerResult>;

/**
 * Wrap an answer handler so it emits metrics on every call.
 * The wrapped handler returns the same `AnswerResult` so callers can keep
 * threading metadata to upstream layers.
 *
 * The wrapper never swallows the inner handler's errors — it just emits a
 * "llm_failed" metric and re-throws.
 */
export function withAnswerMetrics<Args extends unknown[]>(
  inner: AnswerHandler<Args>,
): AnswerHandler<Args> {
  return async (...args: Args): Promise<AnswerResult> => {
    const end = startTimer();
    try {
      const result = await inner(...args);
      recordAnswer({
        outcome: result.outcome,
        timing: { ...(result.timing ?? {}), total: result.timing?.total ?? end() },
        tokensIn: result.tokensIn,
        tokensOut: result.tokensOut,
      });
      return result;
    } catch (err) {
      recordAnswer({
        outcome: "llm_failed",
        timing: { total: end() },
      });
      throw err;
    }
  };
}

/**
 * Example — replace the existing /api/answer registration:
 *
 *   // before:
 *   app.get("/api/answer", answerHandler);
 *
 *   // after:
 *   app.get("/api/answer", withAnswerMetrics(answerHandler));
 *
 * Total integration footprint: 1 import + 1 wrapping call.
 */
