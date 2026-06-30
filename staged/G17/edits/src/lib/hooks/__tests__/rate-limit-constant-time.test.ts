/**
 * G17 — rateLimitTokens oracle fix tests.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  sanitizeRateLimitTokens,
  readExposeTokensFlag,
  checkExposeTokensAtBoot,
  statusBodyWithSanitizedTokens,
} from "../rate-limit-constant-time.js";

describe("readExposeTokensFlag", () => {
  it("returns false when env unset", () => {
    assert.equal(readExposeTokensFlag({}), false);
  });

  it("returns true only on exact '1'", () => {
    assert.equal(readExposeTokensFlag({ NOX_HOOK_EXPOSE_TOKENS: "1" }), true);
    assert.equal(readExposeTokensFlag({ NOX_HOOK_EXPOSE_TOKENS: "true" }), false);
    assert.equal(readExposeTokensFlag({ NOX_HOOK_EXPOSE_TOKENS: "yes" }), false);
    assert.equal(readExposeTokensFlag({ NOX_HOOK_EXPOSE_TOKENS: "0" }), false);
  });
});

describe("sanitizeRateLimitTokens", () => {
  it("default: always returns null + exposed=false", () => {
    const r = sanitizeRateLimitTokens({ rateLimitTokens: 42 }, {});
    assert.equal(r.rateLimitTokens, null);
    assert.equal(r.exposed, false);
  });

  it("default: even with null/undefined input, returns null", () => {
    assert.equal(
      sanitizeRateLimitTokens({ rateLimitTokens: null }, {}).rateLimitTokens,
      null,
    );
    assert.equal(
      sanitizeRateLimitTokens({}, {}).rateLimitTokens,
      null,
    );
  });

  it("opt-in: returns the actual number", () => {
    const r = sanitizeRateLimitTokens(
      { rateLimitTokens: 42 },
      { NOX_HOOK_EXPOSE_TOKENS: "1" },
    );
    assert.equal(r.rateLimitTokens, 42);
    assert.equal(r.exposed, true);
  });

  it("opt-in with non-number input → null (shape preserved)", () => {
    const r = sanitizeRateLimitTokens({}, { NOX_HOOK_EXPOSE_TOKENS: "1" });
    assert.equal(r.rateLimitTokens, null);
    assert.equal(r.exposed, true);
  });
});

describe("checkExposeTokensAtBoot", () => {
  it("warns + returns true when env=1", () => {
    let warned = false;
    const r = checkExposeTokensAtBoot(
      { warn: () => { warned = true; } },
      { NOX_HOOK_EXPOSE_TOKENS: "1" },
    );
    assert.equal(r, true);
    assert.equal(warned, true);
  });

  it("silent + returns false when unset", () => {
    let warned = false;
    const r = checkExposeTokensAtBoot(
      { warn: () => { warned = true; } },
      {},
    );
    assert.equal(r, false);
    assert.equal(warned, false);
  });
});

describe("statusBodyWithSanitizedTokens", () => {
  it("zero-outs token field while preserving shape (constant-time guarantee)", () => {
    const original = {
      config: { enabled: true },
      queueDepth: 3,
      rateLimitTokens: 17,
    };
    const sanitized = statusBodyWithSanitizedTokens(original, {});
    assert.equal(sanitized.rateLimitTokens, null);
    // Field is still present — shape preserved.
    assert.equal("rateLimitTokens" in sanitized, true);
    // Other fields untouched.
    assert.equal(sanitized.queueDepth, 3);
    assert.deepEqual(sanitized.config, { enabled: true });
  });

  it("opt-in honors original value", () => {
    const sanitized = statusBodyWithSanitizedTokens(
      { queueDepth: 0, rateLimitTokens: 5 },
      { NOX_HOOK_EXPOSE_TOKENS: "1" },
    );
    assert.equal(sanitized.rateLimitTokens, 5);
  });
});
