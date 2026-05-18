/**
 * G4 — Patched answer.ts validateBody() with full schema constraint enforcement.
 *
 * This is a complete replacement for staged-P1/edits/src/api/answer.ts validateBody().
 * All other code in that file is unchanged. Only validateBody() and the error
 * handling in handleAnswerRequest (status 422 path) are modified.
 *
 * CHANGES vs staged-P1 original:
 *   - top_k: now enforces min=1, max=20 (was type-only check)
 *   - max_tokens: now enforces min=64, max=8192 (was type-only check)
 *   - temperature: now enforces min=0.0, max=1.0 (was type-only check)
 *   - top_k and max_tokens must be integer (Number.isInteger guard added)
 *   - All bound violations return 422 with structured JSON body
 *
 * Ref: THREAT-MODEL.md §3.1 "DoS via prompt longo / top_k not enforced" (G4).
 */

// ---------- Types (same as staged-P1) ----------------------------------------

export interface AnswerHttpRequest {
  question: string;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
  provider?: string;
  model?: string;
  no_citations?: boolean;
  trace_id?: string;
}

// ---------- Error classes -------------------------------------------------------

export class HttpError extends Error {
  constructor(
    public status: number,
    public reason: string,
    message: string,
  ) {
    super(message);
  }
}

export class ValidationError extends Error {
  public readonly status = 422;
  public readonly reason = "validation_failed";

  constructor(
    public readonly details: {
      field: string;
      got: unknown;
      max?: number;
      min?: number;
    },
  ) {
    super(`Validation failed: ${details.field}`);
  }
}

// ---------- Schema constraints (single source of truth) -------------------------

const CONSTRAINTS = {
  question: { minLength: 1, maxLength: 2000 },
  top_k: { min: 1, max: 20, integer: true },
  max_tokens: { min: 64, max: 8192, integer: true },
  temperature: { min: 0, max: 1 },
  trace_id: { maxLength: 64 },
} as const;

// ---------- validateBody (patched) -----------------------------------------------

/**
 * validateBody — parses and validates the raw HTTP request body.
 *
 * All field constraints are enforced here; downstream code can trust
 * that values are within schema bounds.
 *
 * On invalid input:
 *   - Missing/wrong type → HttpError(400, "invalid_body", ...)
 *   - Out-of-range bound → ValidationError(422) with { field, got, min?, max? }
 */
export function validateBody(body: unknown): AnswerHttpRequest {
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    throw new HttpError(400, "invalid_body", "body must be a JSON object");
  }
  const b = body as Record<string, unknown>;

  // question — required, non-empty, max length
  if (typeof b.question !== "string" || b.question.trim().length === 0) {
    throw new HttpError(400, "invalid_body", "question is required (non-empty string)");
  }
  if (b.question.length > CONSTRAINTS.question.maxLength) {
    throw new HttpError(400, "invalid_body", `question exceeds ${CONSTRAINTS.question.maxLength} chars`);
  }

  const req: AnswerHttpRequest = { question: b.question };

  // top_k — optional, integer, min=1, max=20
  if (b.top_k !== undefined) {
    if (typeof b.top_k !== "number" || !Number.isFinite(b.top_k)) {
      throw new HttpError(400, "invalid_body", "top_k must be a number");
    }
    if (!Number.isInteger(b.top_k)) {
      throw new ValidationError({ field: "top_k", got: b.top_k, reason: "top_k must be an integer" } as never);
    }
    if (b.top_k < CONSTRAINTS.top_k.min) {
      throw new ValidationError({ field: "top_k", got: b.top_k, min: CONSTRAINTS.top_k.min });
    }
    if (b.top_k > CONSTRAINTS.top_k.max) {
      throw new ValidationError({ field: "top_k", got: b.top_k, max: CONSTRAINTS.top_k.max });
    }
    req.top_k = b.top_k;
  }

  // max_tokens — optional, integer, min=64, max=8192
  if (b.max_tokens !== undefined) {
    if (typeof b.max_tokens !== "number" || !Number.isFinite(b.max_tokens)) {
      throw new HttpError(400, "invalid_body", "max_tokens must be a number");
    }
    if (!Number.isInteger(b.max_tokens)) {
      throw new ValidationError({ field: "max_tokens", got: b.max_tokens, reason: "max_tokens must be an integer" } as never);
    }
    if (b.max_tokens < CONSTRAINTS.max_tokens.min) {
      throw new ValidationError({ field: "max_tokens", got: b.max_tokens, min: CONSTRAINTS.max_tokens.min });
    }
    if (b.max_tokens > CONSTRAINTS.max_tokens.max) {
      throw new ValidationError({ field: "max_tokens", got: b.max_tokens, max: CONSTRAINTS.max_tokens.max });
    }
    req.max_tokens = b.max_tokens;
  }

  // temperature — optional, float, min=0, max=1
  if (b.temperature !== undefined) {
    if (typeof b.temperature !== "number" || !Number.isFinite(b.temperature)) {
      throw new HttpError(400, "invalid_body", "temperature must be a number");
    }
    if (b.temperature < CONSTRAINTS.temperature.min) {
      throw new ValidationError({ field: "temperature", got: b.temperature, min: CONSTRAINTS.temperature.min });
    }
    if (b.temperature > CONSTRAINTS.temperature.max) {
      throw new ValidationError({ field: "temperature", got: b.temperature, max: CONSTRAINTS.temperature.max });
    }
    req.temperature = b.temperature;
  }

  // provider — optional string
  if (b.provider !== undefined) {
    if (typeof b.provider !== "string") {
      throw new HttpError(400, "invalid_body", "provider must be a string");
    }
    req.provider = b.provider;
  }

  // model — optional string
  if (b.model !== undefined) {
    if (typeof b.model !== "string") {
      throw new HttpError(400, "invalid_body", "model must be a string");
    }
    req.model = b.model;
  }

  // no_citations — optional boolean
  if (b.no_citations !== undefined) {
    if (typeof b.no_citations !== "boolean") {
      throw new HttpError(400, "invalid_body", "no_citations must be a boolean");
    }
    req.no_citations = b.no_citations;
  }

  // trace_id — optional string, maxLength=64
  if (b.trace_id !== undefined) {
    if (typeof b.trace_id !== "string") {
      throw new HttpError(400, "invalid_body", "trace_id must be a string");
    }
    if (b.trace_id.length > CONSTRAINTS.trace_id.maxLength) {
      throw new HttpError(400, "invalid_body", `trace_id must be string <= ${CONSTRAINTS.trace_id.maxLength} chars`);
    }
    req.trace_id = b.trace_id;
  }

  return req;
}

/**
 * errorToResponse — converts HttpError or ValidationError to HTTP response shape.
 *
 * ValidationError (422):
 *   { error: "Validation failed", details: { field, got, max?, min? } }
 *
 * HttpError (4xx):
 *   { error: <reason>, message: <message> }
 */
export function errorToResponse(err: unknown): { status: number; body: Record<string, unknown> } {
  if (err instanceof ValidationError) {
    return {
      status: 422,
      body: {
        error: "Validation failed",
        details: err.details,
      },
    };
  }
  if (err instanceof HttpError) {
    return {
      status: err.status,
      body: { error: err.reason, message: err.message },
    };
  }
  return {
    status: 500,
    body: { error: "internal_error" },
  };
}
