/**
 * G5 T2 — Middleware factories.
 *
 * Two flavours:
 *   - `expressErrorMiddleware(opts)` — drop-in `(err, req, res, next)` for
 *     Express / Fastify-adapter routes.
 *   - `sanitizerWrap(handler, opts)` — framework-agnostic. Wraps an async
 *     handler `(input) => Promise<{ status, headers, body }>` so any thrown
 *     error is converted into a sanitized response shape consistent with
 *     P1/A2/L2/L3/P2/P5.
 *
 * Both seed requestId via `X-Request-ID` header (case-insensitive) when
 * present, else generate a fresh UUID.
 */

import {
  sanitizeErrorForHttp,
  SanitizeOptions,
  SanitizedResult,
} from "./sanitize.js";

// ─── Express middleware ──────────────────────────────────────────────────

type ExpressLike = {
  status: (n: number) => ExpressLike;
  setHeader: (name: string, value: string) => void;
  json: (body: unknown) => void;
};

type ExpressReqLike = {
  headers?: Record<string, string | string[] | undefined>;
};

type NextFn = (err?: unknown) => void;

export interface ExpressMiddlewareOptions
  extends Omit<SanitizeOptions, "requestId"> {
  /** Header name from which to pull existing request IDs. Default `x-request-id`. */
  requestIdHeader?: string;
}

export function expressErrorMiddleware(opts: ExpressMiddlewareOptions = {}) {
  const headerName = (opts.requestIdHeader ?? "x-request-id").toLowerCase();
  return function (
    err: unknown,
    req: ExpressReqLike,
    res: ExpressLike,
    _next: NextFn,
  ): void {
    const requestId = pickHeader(req.headers, headerName);
    const { status, body } = sanitizeErrorForHttp(err, {
      exposeStack: opts.exposeStack,
      nodeEnv: opts.nodeEnv,
      log: opts.log,
      requestId,
    });
    res.status(status);
    res.setHeader("Content-Type", "application/json");
    res.setHeader("X-Request-ID", body.requestId);
    res.json(body);
  };
}

function pickHeader(
  headers: Record<string, string | string[] | undefined> | undefined,
  lowerName: string,
): string | undefined {
  if (!headers) return undefined;
  for (const k of Object.keys(headers)) {
    if (k.toLowerCase() === lowerName) {
      const v = headers[k];
      if (Array.isArray(v)) return v[0];
      return v;
    }
  }
  return undefined;
}

// ─── Framework-agnostic wrapper ──────────────────────────────────────────
//
// The nox-mem HTTP handlers (P1/A2/L2/L3/P5/P2) return a `{ status, headers,
// body }` triple instead of using Express directly (see `staged-P1/edits/src/
// api/answer.ts` for the canonical shape). `sanitizerWrap` lets each handler
// keep its happy-path logic and route any throw through the sanitizer.

export interface HandlerInput {
  headers?: Record<string, string | string[] | undefined>;
  // Anything else the inner handler needs.
  [k: string]: unknown;
}

export interface HandlerOutput {
  status: number;
  headers?: Record<string, string>;
  body: unknown;
}

export function sanitizerWrap<I extends HandlerInput>(
  handler: (input: I) => Promise<HandlerOutput>,
  opts: ExpressMiddlewareOptions = {},
): (input: I) => Promise<HandlerOutput> {
  const headerName = (opts.requestIdHeader ?? "x-request-id").toLowerCase();
  return async (input: I): Promise<HandlerOutput> => {
    const requestId = pickHeader(input.headers, headerName);
    try {
      const out = await handler(input);
      // Always propagate X-Request-ID on success too, so clients can correlate.
      const finalHeaders = {
        ...(out.headers ?? {}),
        "X-Request-ID": requestId ?? "",
      };
      if (finalHeaders["X-Request-ID"].length === 0) {
        // Generate one on success path too so logs always have a key.
        finalHeaders["X-Request-ID"] = sanitizeErrorForHttp(new Error("noop"), {
          requestId: undefined,
        }).body.requestId;
        // Note: we don't actually throw here — generator above is the cheap
        // randomUUID fallback path; the noop error result is discarded.
      }
      return { ...out, headers: finalHeaders };
    } catch (err) {
      const sanitized: SanitizedResult = sanitizeErrorForHttp(err, {
        exposeStack: opts.exposeStack,
        nodeEnv: opts.nodeEnv,
        log: opts.log,
        requestId,
      });
      return {
        status: sanitized.status,
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": sanitized.body.requestId,
        },
        body: sanitized.body,
      };
    }
  };
}

// ─── Light-touch helper for already-implemented catch-blocks ────────────
//
// Most existing handlers have a per-error `try { ... } catch (err) { return
// jsonResponse(500, ...) }` pattern. Migration step 1 is to swap that for
// `return errorToResponse(err, opts)` — minimal blast radius, zero behaviour
// change on the happy path.

export function errorToResponse(
  err: unknown,
  opts: Omit<SanitizeOptions, "requestId"> & {
    requestId?: string;
  } = {},
): HandlerOutput {
  const { status, body } = sanitizeErrorForHttp(err, opts);
  return {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": body.requestId,
    },
    body,
  };
}
