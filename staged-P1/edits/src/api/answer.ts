/**
 * src/api/answer.ts — P1 T9: POST /api/answer.
 *
 * Framework-agnostic handler. Production `src/api/server.ts` mounts it via
 * a 5-line Fastify (or Express) adapter:
 *
 *     fastify.post('/api/answer', async (req, reply) => {
 *       const out = await handleAnswerRequest({
 *         body: req.body,
 *         headers: req.headers as Record<string, string | undefined>,
 *         answer: realAnswer,
 *         telemetryStore: getTelemetryStore(),
 *       });
 *       reply.code(out.status);
 *       for (const [k, v] of Object.entries(out.headers)) reply.header(k, v);
 *       return out.body;
 *     });
 *
 * Same shape — kickoff §6 status codes:
 *   200 ok / 400 invalid body / 422 hallucination after retry /
 *   502 LLM unreachable / 503 retrieval empty / 504 timeout
 *
 * Response also sets X-Trace-Id, X-Model-Used, X-Retry-Count.
 *
 * Auth: this handler does NOT enforce auth — `src/api/server.ts` chains the
 * existing `requireApiToken()` middleware in front of it (same mechanism
 * as the other 7 routes). Documented as a precondition.
 */

import { randomUUID } from "node:crypto";
import { answer as defaultAnswer, AnswerError } from "../lib/answer/index.js";
import type { AnswerOpts, AnswerResult } from "../lib/answer/index.js";
import {
  recordAnswer,
  type TelemetryStore,
} from "../lib/answer/telemetry.js";

// ─── Request / Response wire types ───────────────────────────────────────

export interface AnswerHttpRequest {
  question: string;
  top_k?: number;
  max_tokens?: number;
  provider?: string;
  model?: string;
  temperature?: number;
  no_citations?: boolean;
  trace_id?: string;
}

export interface AnswerHttpResponseSuccess {
  answer: string;
  citations: AnswerResult["citations"];
  metadata: AnswerResult["metadata"];
  trace_id: string;
}

export interface AnswerHttpResponseError {
  error: true;
  reason: string;
  message: string;
  trace_id: string;
}

export type AnswerHttpResponse = AnswerHttpResponseSuccess | AnswerHttpResponseError;

// ─── Handler I/O contract (framework-agnostic) ────────────────────────────

export interface HandleAnswerArgs {
  /** Parsed JSON body (or raw string we coerce). */
  body: unknown;
  /** Headers (case-insensitive lookups expected by caller). */
  headers?: Record<string, string | string[] | undefined>;
  /** Auth check seam: when present, must return true to allow. Default: allow. */
  authCheck?: (headers: Record<string, string | string[] | undefined>) => boolean;
  /** Test seam — replace answer() under test. */
  answer?: (opts: AnswerOpts) => Promise<AnswerResult>;
  /** Optional telemetry sink. */
  telemetryStore?: TelemetryStore;
  /** Session correlation passthrough (from middleware). */
  sessionId?: string | null;
}

export interface HandlerOutput {
  status: number;
  headers: Record<string, string>;
  body: AnswerHttpResponse;
}

const MARKER_RE = /\s?\[chunk_\d+\]/g;

// ─── Body validation ──────────────────────────────────────────────────────

function getHeader(
  headers: Record<string, string | string[] | undefined> | undefined,
  name: string
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

class HttpError extends Error {
  constructor(public status: number, public reason: string, message: string) {
    super(message);
  }
}

export function validateBody(body: unknown): AnswerHttpRequest {
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    throw new HttpError(400, "invalid_body", "body must be a JSON object");
  }
  const b = body as Record<string, unknown>;
  if (typeof b.question !== "string" || b.question.trim().length === 0) {
    throw new HttpError(400, "invalid_body", "question is required (non-empty string)");
  }
  if (b.question.length > 2000) {
    throw new HttpError(400, "invalid_body", "question exceeds 2000 chars");
  }

  const req: AnswerHttpRequest = { question: b.question };
  if (b.top_k !== undefined) {
    if (typeof b.top_k !== "number" || !Number.isFinite(b.top_k)) {
      throw new HttpError(400, "invalid_body", "top_k must be a number");
    }
    req.top_k = b.top_k;
  }
  if (b.max_tokens !== undefined) {
    if (typeof b.max_tokens !== "number" || !Number.isFinite(b.max_tokens)) {
      throw new HttpError(400, "invalid_body", "max_tokens must be a number");
    }
    req.max_tokens = b.max_tokens;
  }
  if (b.temperature !== undefined) {
    if (typeof b.temperature !== "number" || !Number.isFinite(b.temperature)) {
      throw new HttpError(400, "invalid_body", "temperature must be a number");
    }
    req.temperature = b.temperature;
  }
  if (b.provider !== undefined) {
    if (typeof b.provider !== "string") {
      throw new HttpError(400, "invalid_body", "provider must be a string");
    }
    req.provider = b.provider;
  }
  if (b.model !== undefined) {
    if (typeof b.model !== "string") {
      throw new HttpError(400, "invalid_body", "model must be a string");
    }
    req.model = b.model;
  }
  if (b.no_citations !== undefined) {
    if (typeof b.no_citations !== "boolean") {
      throw new HttpError(400, "invalid_body", "no_citations must be a boolean");
    }
    req.no_citations = b.no_citations;
  }
  if (b.trace_id !== undefined) {
    if (typeof b.trace_id !== "string" || b.trace_id.length > 64) {
      throw new HttpError(400, "invalid_body", "trace_id must be string ≤64 chars");
    }
    req.trace_id = b.trace_id;
  }
  return req;
}

// ─── Status-code mapper ───────────────────────────────────────────────────

export function statusFromReason(reason: string): number {
  switch (reason) {
    case "retrieval_empty":
      return 503;
    case "hallucination_after_retry":
    case "hallucinated_citation":
      return 422;
    case "llm_timeout":
      return 504;
    case "llm_error":
      return 502;
    case "invalid_input":
    case "invalid_body":
      return 400;
    case "unauthorized":
      return 401;
    default:
      return 500;
  }
}

// ─── Handler ──────────────────────────────────────────────────────────────

export async function handleAnswerRequest(args: HandleAnswerArgs): Promise<HandlerOutput> {
  const traceIdHeader = getHeader(args.headers, "x-trace-id");
  const traceId = traceIdHeader ?? randomUUID();
  const baseHeaders: Record<string, string> = { "X-Trace-Id": traceId };

  // Auth (optional; default-allow when no check provided).
  if (args.authCheck && !args.authCheck(args.headers ?? {})) {
    return {
      status: 401,
      headers: baseHeaders,
      body: {
        error: true,
        reason: "unauthorized",
        message: "missing or invalid API token",
        trace_id: traceId,
      },
    };
  }

  // Body validation.
  let req: AnswerHttpRequest;
  try {
    req = validateBody(args.body);
  } catch (err) {
    const httpErr = err as HttpError;
    return {
      status: httpErr.status ?? 400,
      headers: baseHeaders,
      body: {
        error: true,
        reason: httpErr.reason ?? "invalid_body",
        message: httpErr.message,
        trace_id: traceId,
      },
    };
  }

  // Build AnswerOpts.
  const opts: AnswerOpts = { question: req.question };
  if (req.top_k !== undefined) opts.topK = req.top_k;
  if (req.max_tokens !== undefined) opts.maxTokens = req.max_tokens;
  if (req.temperature !== undefined) opts.temperature = req.temperature;
  if (req.provider !== undefined) opts.provider = req.provider;
  if (req.model !== undefined) opts.model = req.model;

  const run = args.answer ?? defaultAnswer;
  try {
    const res = await run(opts);

    if (args.telemetryStore) {
      recordAnswer(args.telemetryStore, {
        question: req.question,
        citationCount: res.citations.length,
        metadata: res.metadata,
        sessionId: args.sessionId ?? null,
      });
    }

    const finalAnswer = req.no_citations
      ? res.answer.replace(MARKER_RE, "")
      : res.answer;

    const headers: Record<string, string> = {
      ...baseHeaders,
      "X-Model-Used": res.metadata.model,
      "X-Retry-Count": String(res.metadata.retry_count ?? 0),
      "Content-Type": "application/json",
    };

    // retrieval_empty is a "success" path (lib returns canonical message)
    // but kickoff §6 maps to 503. Surface accordingly.
    const status = res.metadata.failed_reason === "retrieval_empty" ? 503 : 200;
    return {
      status,
      headers,
      body: {
        answer: finalAnswer,
        citations: res.citations,
        metadata: res.metadata,
        trace_id: traceId,
      },
    };
  } catch (err) {
    if (err instanceof AnswerError) {
      if (args.telemetryStore) {
        recordAnswer(args.telemetryStore, {
          question: req.question,
          citationCount: 0,
          metadata: {
            latency_ms: (err.metadata.latency_ms as number | undefined) ?? 0,
            tokens_in: (err.metadata.tokens_in as number | undefined) ?? 0,
            tokens_out: (err.metadata.tokens_out as number | undefined) ?? 0,
            provider: (err.metadata.provider as string | undefined) ?? "n/a",
            model: (err.metadata.model as string | undefined) ?? "n/a",
            retrieval_count: (err.metadata.retrieval_count as number | undefined) ?? 0,
            fallback_used: (err.metadata.fallback_used as boolean | undefined) ?? false,
            failed_reason: err.reason,
          },
          sessionId: args.sessionId ?? null,
        });
      }
      return {
        status: statusFromReason(err.reason),
        headers: baseHeaders,
        body: {
          error: true,
          reason: err.reason,
          message: err.message,
          trace_id: traceId,
        },
      };
    }
    return {
      status: 500,
      headers: baseHeaders,
      body: {
        error: true,
        reason: "internal_error",
        message: (err as Error).message,
        trace_id: traceId,
      },
    };
  }
}

// ─── JSON Schema (for runtime validators + OpenAPI gen) ───────────────────

export const REQUEST_SCHEMA = {
  $schema: "http://json-schema.org/draft-07/schema#",
  type: "object",
  required: ["question"],
  additionalProperties: false,
  properties: {
    question: { type: "string", minLength: 1, maxLength: 2000 },
    top_k: { type: "integer", minimum: 1, maximum: 20 },
    max_tokens: { type: "integer", minimum: 64, maximum: 8192 },
    provider: { type: "string" },
    model: { type: "string" },
    temperature: { type: "number", minimum: 0, maximum: 1 },
    no_citations: { type: "boolean" },
    trace_id: { type: "string", maxLength: 64 },
  },
} as const;
