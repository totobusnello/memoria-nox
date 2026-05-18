/**
 * G4 — Validator/schema drift patch for /api/answer
 *
 * Gap identified in THREAT-MODEL.md §3.1 (DoS / validator drift):
 *   "top_k schema declares max=20 but validateBody() doesn't enforce it.
 *    User could request top_k=10000 and crash service."
 *
 * This file documents the exact patch to apply to staged-P1/edits/src/api/answer.ts.
 * The validateBody() function must enforce ALL OpenAPI schema constraints at runtime,
 * not just type checks.
 *
 * Ref: THREAT-MODEL.md G4 (medium priority).
 */

/**
 * ValidationError shape for 422 responses:
 *
 *   { error: "Validation failed", details: { field: string, got: unknown, max?: number, min?: number } }
 */
export interface ValidationDetails {
  field: string;
  got: unknown;
  max?: number;
  min?: number;
  reason?: string;
}

export class ValidationError extends Error {
  public readonly status = 422;
  public readonly reason = "validation_failed";
  public readonly details: ValidationDetails;

  constructor(details: ValidationDetails) {
    super(`Validation failed: ${details.field}`);
    this.details = details;
  }
}

/**
 * Schema constraints aligned with OpenAPI JSON schema in answer.ts.
 * Single source of truth — change here only, no duplication.
 */
export const ANSWER_CONSTRAINTS = {
  question: { minLength: 1, maxLength: 2000 },
  top_k: { min: 1, max: 20 },
  max_tokens: { min: 64, max: 8192 },
  temperature: { min: 0, max: 1 },
  trace_id: { maxLength: 64 },
} as const;

/**
 * validateBodyStrict — drop-in replacement for validateBody() in answer.ts.
 *
 * Differences from original:
 *  1. top_k: enforces min=1, max=20 (rejects 10000 → 422)
 *  2. max_tokens: enforces min=64, max=8192
 *  3. temperature: enforces min=0, max=1
 *  4. All violations return 422 with structured ValidationError (not 400 HttpError)
 *
 * Backward compatibility: callers that catch HttpError(400) should also handle
 * ValidationError(422). Existing smoke tests remain green since valid payloads
 * pass all checks.
 */
export function validateAnswerConstraints(
  field: "top_k",
  value: number,
): void;
export function validateAnswerConstraints(
  field: "max_tokens",
  value: number,
): void;
export function validateAnswerConstraints(
  field: "temperature",
  value: number,
): void;
export function validateAnswerConstraints(
  field: keyof typeof ANSWER_CONSTRAINTS,
  value: number,
): void {
  const c = ANSWER_CONSTRAINTS[field] as { min?: number; max?: number };

  if (c.min !== undefined && value < c.min) {
    throw new ValidationError({
      field,
      got: value,
      min: c.min,
      reason: `${field} must be >= ${c.min}`,
    });
  }
  if (c.max !== undefined && value > c.max) {
    throw new ValidationError({
      field,
      got: value,
      max: c.max,
      reason: `${field} must be <= ${c.max}`,
    });
  }
}
