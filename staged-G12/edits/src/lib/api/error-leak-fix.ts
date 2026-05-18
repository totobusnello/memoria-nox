/**
 * G12 — Adoption helpers for safeErrorMessage across staged-* handlers.
 *
 * This file ships drop-in replacements for the leaky `return { status: 500,
 * body: { error: (e as Error).message } }` pattern found in:
 *
 *   - staged-P2/edits/src/api/hooks.ts:99            (G12 root)
 *   - staged-L2/edits/src/api/conflict.ts:181        (resolution_failed message)
 *   - staged-L3/edits/src/api/mark.ts (R-L3-3)       (SQL fragment leak)
 *
 * Use the patch helpers below from each handler. Example (P2 hooks.ts L99):
 *
 *   - return { status: 500, body: { error: (e as Error).message } };
 *   + return { status: 500, body: safeError500(e, { context: "hooks.recent" }) };
 *
 * Logging: caller can pass an `onLog` callback to forward the raw error to
 * stderr / structured logger. The sanitized correlation_id is the link.
 */

import { buildSafeErrorBody, type SanitizeOptions } from "./safe-error-message.js";

export interface SafeError500Options extends SanitizeOptions {
  /** Short context tag for log correlation (e.g. "hooks.recent", "conflict.resolve"). */
  context?: string;
  /** Logger override. Defaults to console.error. */
  onLog?: (info: { correlationId: string; raw: unknown; context?: string }) => void;
}

/**
 * Build a sanitized 5xx response body. Always returns `{ error, correlation_id }`.
 * Side-effect: logs raw error to onLog (or console.error) with the correlation_id.
 */
export function safeError500(e: unknown, opts: SafeError500Options = {}): {
  error: string;
  correlation_id: string;
} {
  const log = opts.onLog
    ? opts.onLog
    : (info: { correlationId: string; raw: unknown; context?: string }) => {
        const ctx = info.context ? `[${info.context}] ` : "";
        // eslint-disable-next-line no-console
        console.error(
          `${ctx}correlation_id=${info.correlationId} error=`,
          info.raw,
        );
      };
  return buildSafeErrorBody(e, {
    ...opts,
    onLog: ({ correlationId, raw }) =>
      log({ correlationId, raw, context: opts.context }),
  });
}

/**
 * Convenience for the L2 conflict resolve path (`409 resolution_failed`).
 * Shape differs slightly — keeps the `error` discriminator for backward
 * compat while still sanitizing the inner message.
 */
export function safeConflict409(e: unknown, opts: SafeError500Options = {}): {
  error: "resolution_failed";
  message: string;
  correlation_id: string;
} {
  const body = safeError500(e, { ...opts, context: opts.context ?? "conflict.resolve" });
  return {
    error: "resolution_failed",
    message: body.error,
    correlation_id: body.correlation_id,
  };
}

/**
 * Convenience for the L3 mark path 500 leak. Same shape as `safeError500`.
 */
export function safeMark500(e: unknown, opts: SafeError500Options = {}): {
  error: string;
  correlation_id: string;
} {
  return safeError500(e, { ...opts, context: opts.context ?? "mark" });
}
