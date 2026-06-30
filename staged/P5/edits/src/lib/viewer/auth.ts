/**
 * T11 — Optional auth gate
 *
 * Token-based, env-gated. Disabled by default (assumes 127.0.0.1 binding).
 *
 * Behavior:
 *  - If `NOX_VIEWER_AUTH_TOKEN` is unset → allow all (default).
 *  - If set → require either header `Authorization: Bearer <token>` OR
 *    query string `?token=<token>`.
 *  - Constant-time compare so timing leaks are not informative.
 *
 * The `?token=` path exists because the browser EventSource API cannot
 * send custom headers; document this trade-off in VIEWER.md.
 */

import { timingSafeEqual } from "node:crypto";

export interface AuthRequest {
  /** Lower-cased headers map. */
  headers: Record<string, string | string[] | undefined>;
  /** Parsed query string. Values are first-occurrence. */
  query: Record<string, string | undefined>;
}

export interface AuthResult {
  ok: boolean;
  reason?: "no_token_configured" | "matched" | "missing" | "mismatch";
}

function configuredToken(env: NodeJS.ProcessEnv = process.env): string {
  return env.NOX_VIEWER_AUTH_TOKEN ?? "";
}

/** Required-token policy active? */
export function authEnabled(env: NodeJS.ProcessEnv = process.env): boolean {
  return configuredToken(env).length > 0;
}

function extractToken(req: AuthRequest): string | null {
  const authHeader = req.headers.authorization ?? req.headers["Authorization"];
  if (typeof authHeader === "string") {
    const m = /^Bearer\s+(\S+)/i.exec(authHeader);
    if (m) return m[1] ?? null;
  }
  const q = req.query.token;
  if (typeof q === "string" && q.length > 0) return q;
  return null;
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    // Still run a comparison of same-length buffers to neutralize length leak.
    const pad = Buffer.alloc(Math.max(a.length, b.length, 1));
    timingSafeEqual(pad, pad);
    return false;
  }
  return timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

/**
 * Evaluate a request against the configured policy.
 */
export function authorize(
  req: AuthRequest,
  env: NodeJS.ProcessEnv = process.env
): AuthResult {
  const expected = configuredToken(env);
  if (expected.length === 0) {
    return { ok: true, reason: "no_token_configured" };
  }
  const presented = extractToken(req);
  if (!presented) {
    return { ok: false, reason: "missing" };
  }
  if (safeEqual(presented, expected)) {
    return { ok: true, reason: "matched" };
  }
  return { ok: false, reason: "mismatch" };
}

/** Headers + status to send back when authorize() fails. */
export interface DenyResponse {
  status: 401;
  headers: Record<string, string>;
  body: string;
}

export function denyResponse(reason: "missing" | "mismatch"): DenyResponse {
  return {
    status: 401,
    headers: {
      "Content-Type": "application/json",
      "WWW-Authenticate": 'Bearer realm="nox-mem-viewer"',
    },
    body: JSON.stringify({ error: "unauthorized", reason }),
  };
}
