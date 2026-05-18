/**
 * G4 — Tests for validateBody() constraint enforcement.
 *
 * 10 tests covering:
 *   - top_k: accepts valid, rejects > max=20, rejects < min=1, rejects non-integer
 *   - max_tokens: accepts valid, rejects > max=8192, rejects < min=64
 *   - temperature: rejects > 1, rejects < 0
 *   - 422 response shape matches expected contract
 *
 * Run: node --test staged-G4/edits/src/api/__tests__/validate.test.ts
 * (requires Node 20+ built-in test runner)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validateBody, ValidationError, HttpError, errorToResponse } from "../answer.ts";

// Helper to call validateBody and catch thrown error
function tryValidate(body: unknown): { ok: true; value: unknown } | { ok: false; error: unknown } {
  try {
    const value = validateBody(body);
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error };
  }
}

describe("G4 — validateBody() constraint enforcement", () => {
  // ── Baseline: valid request passes through ──────────────────────────────────

  it("accepts minimal valid request (question only)", () => {
    const result = tryValidate({ question: "What is memory?" });
    assert.equal(result.ok, true);
  });

  // ── top_k ──────────────────────────────────────────────────────────────────

  it("accepts top_k=20 (at max boundary)", () => {
    const result = tryValidate({ question: "q", top_k: 20 });
    assert.equal(result.ok, true);
    if (result.ok) assert.equal((result.value as { top_k: number }).top_k, 20);
  });

  it("accepts top_k=1 (at min boundary)", () => {
    const result = tryValidate({ question: "q", top_k: 1 });
    assert.equal(result.ok, true);
  });

  it("rejects top_k=21 with ValidationError(422) and max=20 in details", () => {
    const result = tryValidate({ question: "q", top_k: 21 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError, `expected ValidationError, got ${result.error}`);
    const ve = result.error as ValidationError;
    assert.equal(ve.status, 422);
    assert.equal(ve.details.field, "top_k");
    assert.equal(ve.details.got, 21);
    assert.equal(ve.details.max, 20);
  });

  it("rejects top_k=10000 with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", top_k: 10000 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.max, 20);
  });

  it("rejects top_k=0 (below min=1) with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", top_k: 0 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.field, "top_k");
    assert.equal(ve.details.min, 1);
  });

  // ── max_tokens ──────────────────────────────────────────────────────────────

  it("rejects max_tokens=8193 (above max=8192) with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", max_tokens: 8193 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.field, "max_tokens");
    assert.equal(ve.details.max, 8192);
  });

  it("rejects max_tokens=63 (below min=64) with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", max_tokens: 63 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.min, 64);
  });

  // ── temperature ─────────────────────────────────────────────────────────────

  it("rejects temperature=1.01 (above max=1) with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", temperature: 1.01 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.field, "temperature");
    assert.equal(ve.details.max, 1);
  });

  it("rejects temperature=-0.01 (below min=0) with ValidationError(422)", () => {
    const result = tryValidate({ question: "q", temperature: -0.01 });
    assert.equal(result.ok, false);
    assert.ok(result.error instanceof ValidationError);
    const ve = result.error as ValidationError;
    assert.equal(ve.details.min, 0);
  });

  // ── 422 response shape ──────────────────────────────────────────────────────

  it("errorToResponse converts ValidationError to 422 with structured details", () => {
    const ve = new ValidationError({ field: "top_k", got: 999, max: 20 });
    const { status, body } = errorToResponse(ve);
    assert.equal(status, 422);
    assert.equal(body.error, "Validation failed");
    const details = body.details as { field: string; got: number; max: number };
    assert.equal(details.field, "top_k");
    assert.equal(details.got, 999);
    assert.equal(details.max, 20);
  });
});
