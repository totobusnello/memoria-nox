/**
 * G17 — Constant-time response shape for /api/hooks/status (Wave G)
 *
 * BACKGROUND
 *   `GET /api/hooks/status` currently returns `rateLimitTokens` from
 *   `inspectQueue().rateLimitTokens`. An attacker monitoring this value
 *   can:
 *     - Detect when capture is busy (tokens trend down → user is active).
 *     - Time their own probes to land between legitimate captures.
 *     - Inferring capture cadence reveals user activity patterns, an
 *       indirect side-channel even when the actual payloads are private.
 *
 * THREAT (G17, R-P2-3)
 *   `rateLimitTokens` oracle reveals capture activity to anyone with
 *   access to `/api/hooks/status` (which is itself a low-effort read
 *   endpoint).
 *
 * FIX
 *   - Omit (zero-out, not delete) `rateLimitTokens` by default.
 *   - Always return the same response shape — `rateLimitTokens: null`.
 *     "Constant-time" here = constant *shape* (no field absence/presence
 *     toggle), so introspection can't fingerprint the env config.
 *   - Operators can opt back in via `NOX_HOOK_EXPOSE_TOKENS=1` for ops
 *     debugging (with a boot WARN logged).
 *
 * Backward compat:
 *   - Field still present (null) — clients reading `body.rateLimitTokens`
 *     don't crash; they just see null.
 *   - Opt-in env restores legacy behavior.
 */

export interface SanitizeStatusInput {
  /** Raw token count from inspectQueue() — may be number or null/undefined. */
  rateLimitTokens?: number | null;
}

export interface SanitizeStatusResult {
  rateLimitTokens: number | null;
  /** True when env opt-in was honored; useful for telemetry. */
  exposed: boolean;
}

export function readExposeTokensFlag(
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  return env.NOX_HOOK_EXPOSE_TOKENS === "1";
}

/**
 * Take the raw `rateLimitTokens` value and return what should be exposed
 * in the response body. Default: always null. Opt-in: pass through.
 */
export function sanitizeRateLimitTokens(
  input: SanitizeStatusInput,
  env: NodeJS.ProcessEnv = process.env,
): SanitizeStatusResult {
  const expose = readExposeTokensFlag(env);
  if (expose) {
    return {
      rateLimitTokens:
        typeof input.rateLimitTokens === "number" ? input.rateLimitTokens : null,
      exposed: true,
    };
  }
  return { rateLimitTokens: null, exposed: false };
}

/**
 * Boot-time WARN helper. Caller invokes once on startup if hooks API
 * is mounted.
 */
export function checkExposeTokensAtBoot(
  logger: { warn: (msg: string) => void } = console,
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  if (readExposeTokensFlag(env)) {
    logger.warn(
      "[security] NOX_HOOK_EXPOSE_TOKENS=1 — /api/hooks/status will leak " +
        "rateLimitTokens. Disables G17 mitigation. Use only for ops debugging.",
    );
    return true;
  }
  return false;
}

// ── Drop-in transformer for hooks.ts /status branch ────────────────────────
//
// Replace the current `rateLimitTokens: inspect.rateLimitTokens ?? null`
// with `rateLimitTokens: sanitizeRateLimitTokens({ rateLimitTokens: inspect.rateLimitTokens }).rateLimitTokens`.
//
// Or, use the helper below for a one-liner:

export function statusBodyWithSanitizedTokens<B extends Record<string, unknown>>(
  body: B & { rateLimitTokens?: number | null },
  env: NodeJS.ProcessEnv = process.env,
): B & { rateLimitTokens: number | null } {
  const sanitized = sanitizeRateLimitTokens({ rateLimitTokens: body.rateLimitTokens }, env);
  return { ...body, rateLimitTokens: sanitized.rateLimitTokens };
}
