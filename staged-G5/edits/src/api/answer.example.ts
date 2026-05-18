/**
 * G5 T3 — Integration EXAMPLE: P1 `/api/answer` handler refactored to use
 * the sanitizer.
 *
 * Diff vs `staged-P1/edits/src/api/answer.ts` (only the parts that change):
 *
 *   - The 500/internal_error catch branch is replaced by `errorToResponse(err)`.
 *   - The 400/422/etc. AnswerError branch ALSO routes through the sanitizer so
 *     prod stack-trace leak is impossible by construction.
 *   - X-Request-ID propagation is preserved (was X-Trace-Id; both are valid).
 *
 * This file is INTENTIONALLY a side-by-side example — NOT a drop-in replacement.
 * Wave G will copy the relevant lines into staged-P1 once we're past Wave F PR
 * review. Until then this serves as the migration pattern doc.
 *
 * Lines that DID NOT change are elided with `// … (unchanged)`.
 */

import { randomUUID } from "node:crypto";
import { errorToResponse } from "../lib/error-sanitizer/middleware.js";

// NOTE: imports below are placeholders for the example; the real refactor
// reuses the staged-P1 modules verbatim.
type AnswerOpts = { question: string; [k: string]: unknown };
type AnswerResult = {
  answer: string;
  citations: unknown[];
  metadata: { failed_reason?: string; model: string; retry_count?: number };
};
class AnswerError extends Error {
  reason!: string;
  metadata!: Record<string, unknown>;
}

interface HandleAnswerArgs {
  body: unknown;
  headers?: Record<string, string | string[] | undefined>;
  answer?: (opts: AnswerOpts) => Promise<AnswerResult>;
}

interface HandlerOutput {
  status: number;
  headers: Record<string, string>;
  body: unknown;
}

export async function handleAnswerRequest(
  args: HandleAnswerArgs,
): Promise<HandlerOutput> {
  // Pull or generate the correlation id ONCE — it threads through both the
  // happy and error paths so logs join up.
  const requestId = getHeader(args.headers, "x-request-id") ?? randomUUID();
  const baseHeaders: Record<string, string> = {
    "X-Request-ID": requestId,
    "Content-Type": "application/json",
  };

  // — Body validation (unchanged) — …

  try {
    // — Resolve provider + call answer() — …
    const run = args.answer!;
    const res = await run({ question: "placeholder" });
    return {
      status: 200,
      headers: { ...baseHeaders, "X-Model-Used": res.metadata.model },
      body: { answer: res.answer, citations: res.citations, requestId },
    };
  } catch (err) {
    // Single shared error path — sanitizer handles class → status mapping +
    // stack stripping + path scrubbing in one call.
    return errorToResponse(err, { requestId });
    // Note: AnswerError already has `name = "AnswerError"` in production; you'd
    // add it to ERROR_STATUS_MAP if you want a specific status code.
  }
}

function getHeader(
  headers: Record<string, string | string[] | undefined> | undefined,
  name: string,
): string | undefined {
  if (!headers) return undefined;
  const lower = name.toLowerCase();
  for (const k of Object.keys(headers)) {
    if (k.toLowerCase() === lower) {
      const v = headers[k];
      if (Array.isArray(v)) return v[0];
      return v;
    }
  }
  return undefined;
}
