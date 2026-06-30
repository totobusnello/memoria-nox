/**
 * G6 — Localhost-only middleware factory + auth model enforcement.
 *
 * Gap from THREAT-MODEL.md §3.3 / G6:
 *   "Some endpoints assume localhost-only but no enforcement. If exposed
 *    publicly via reverse proxy, all endpoints become world-readable."
 *
 * This module provides:
 *   1. requireLocalhost(req) — rejects 403 if request is not from 127.0.0.1 / ::1
 *      AND has no valid Bearer token.
 *   2. NOX_API_BIND_HOST env var doc (default '127.0.0.1') — explicit binding.
 *   3. requireApiToken(req, token) — constant-time Bearer comparison.
 *   4. Composable: requireLocalhost + requireApiToken as layered middleware.
 *
 * Policy: localhost-default. Remote access requires explicit Bearer token.
 *   - If NOX_API_BEARER_TOKEN is not set → only localhost requests allowed.
 *   - If NOX_API_BEARER_TOKEN is set → localhost OR valid Bearer allowed.
 *
 * Ref: THREAT-MODEL.md G6 (medium priority).
 *      THREAT-MODEL.md §7 "HTTP endpoint threat model".
 */

import { timingSafeEqual, createHash } from "node:crypto";
import { IncomingMessage, ServerResponse } from "node:http";

// ─── Config ──────────────────────────────────────────────────────────────────

/**
 * NOX_API_BIND_HOST — env var controlling which address nox-mem-api binds to.
 *
 * Default: '127.0.0.1' (localhost-only).
 * Set to '0.0.0.0' to expose publicly (requires NOX_API_BEARER_TOKEN to be set,
 * or explicitly set NOX_API_ALLOW_PUBLIC=1 to acknowledge the risk).
 *
 * This constant documents the intent; actual binding is in the HTTP server
 * startup code (src/api/server.ts). NEVER bind to 0.0.0.0 without review.
 */
export const NOX_API_BIND_HOST_DEFAULT = "127.0.0.1";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AuthContext {
  /** Whether request originates from localhost (127.0.0.1 or ::1). */
  isLocalhost: boolean;
  /** Whether a valid Bearer token was presented. */
  hasBearerToken: boolean;
  /** Resolved client IP (after X-Forwarded-For stripping for localhost only). */
  clientIp: string;
}

export interface AuthError {
  status: 403;
  reason: "forbidden";
  message: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const LOCALHOST_IPS = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

/**
 * Extract client IP from IncomingMessage.
 *
 * For localhost-only binding, X-Forwarded-For is intentionally NOT trusted —
 * a reverse proxy on 0.0.0.0 that forwards requests could spoof the IP.
 * We read the raw socket address instead.
 */
export function extractClientIp(req: IncomingMessage): string {
  // Raw socket — this is the only source that cannot be spoofed by the client.
  const addr = req.socket?.remoteAddress ?? "";
  // Normalize IPv6 localhost
  if (addr === "::1" || addr === "::ffff:127.0.0.1") return "::1";
  return addr;
}

/**
 * Check whether an IP is localhost.
 */
export function isLocalhostIp(ip: string): boolean {
  return LOCALHOST_IPS.has(ip);
}

/**
 * Constant-time string comparison to prevent timing attacks on Bearer tokens.
 * Returns false if lengths differ (also constant-time via padding).
 */
export function constantTimeEqual(a: string, b: string): boolean {
  // Normalize both to same-length Buffer via sha256 to avoid length leak
  const hashA = createHash("sha256").update(a).digest();
  const hashB = createHash("sha256").update(b).digest();
  return timingSafeEqual(hashA, hashB);
}

/**
 * Extract Bearer token from Authorization header.
 * Returns null if header is missing or malformed.
 */
export function extractBearerToken(req: IncomingMessage): string | null {
  const auth = req.headers["authorization"];
  if (typeof auth !== "string") return null;
  const match = /^Bearer\s+(.+)$/i.exec(auth.trim());
  if (!match || !match[1]) return null;
  return match[1];
}

// ─── Core guard ──────────────────────────────────────────────────────────────

/**
 * buildAuthContext — inspects request and returns AuthContext.
 * Does NOT throw; caller decides policy.
 */
export function buildAuthContext(
  req: IncomingMessage,
  configuredToken?: string,
): AuthContext {
  const clientIp = extractClientIp(req);
  const isLocalhost = isLocalhostIp(clientIp);

  let hasBearerToken = false;
  if (configuredToken) {
    const presented = extractBearerToken(req);
    if (presented) {
      hasBearerToken = constantTimeEqual(presented, configuredToken);
    }
  }

  return { isLocalhost, hasBearerToken, clientIp };
}

/**
 * requireLocalhost — middleware factory.
 *
 * Rejects with 403 if:
 *   - Request is NOT from localhost (127.0.0.1 / ::1)
 *   - AND no valid Bearer token is presented (when NOX_API_BEARER_TOKEN is set)
 *
 * Usage in handler:
 *   const guard = makeLocalhostGuard();
 *   const denied = guard(req, res);
 *   if (denied) return; // response already sent
 *
 * @param opts.token - expected Bearer token (from NOX_API_BEARER_TOKEN env).
 *                     If undefined, only localhost is accepted.
 */
export function makeLocalhostGuard(opts?: { token?: string }) {
  const token = opts?.token ?? process.env.NOX_API_BEARER_TOKEN;

  return function requireLocalhostMiddleware(
    req: IncomingMessage,
    res: ServerResponse,
  ): boolean {
    const ctx = buildAuthContext(req, token);

    // Allow if localhost
    if (ctx.isLocalhost) return false;

    // Allow if valid Bearer presented
    if (ctx.hasBearerToken) return false;

    // Deny
    const body = JSON.stringify({
      error: "forbidden",
      message: token
        ? "Remote access requires a valid Bearer token"
        : "API is restricted to localhost (127.0.0.1). Set NOX_API_BEARER_TOKEN to allow remote access.",
    });
    res.writeHead(403, {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
    });
    res.end(body);
    return true; // request handled, caller should return
  };
}

/**
 * Default guard singleton — reads NOX_API_BEARER_TOKEN from env at call time.
 *
 * Usage:
 *   import { defaultLocalhostGuard } from "./localhost-guard.js";
 *   if (defaultLocalhostGuard(req, res)) return;
 */
export function defaultLocalhostGuard(
  req: IncomingMessage,
  res: ServerResponse,
): boolean {
  const guard = makeLocalhostGuard();
  return guard(req, res);
}

// ─── Startup warning ─────────────────────────────────────────────────────────

/**
 * warnIfPubliclyExposed — logs a warning if the server binds to 0.0.0.0
 * without a Bearer token configured.
 *
 * Call this during server startup before listen().
 */
export function warnIfPubliclyExposed(bindHost: string): void {
  const isPublic = bindHost !== "127.0.0.1" && bindHost !== "localhost";
  const hasToken = Boolean(process.env.NOX_API_BEARER_TOKEN);

  if (isPublic && !hasToken) {
    console.error(
      "[nox-mem-api] WARNING: Server is binding to",
      bindHost,
      "without NOX_API_BEARER_TOKEN set. " +
        "All endpoints are world-readable. " +
        "Set NOX_API_BEARER_TOKEN or bind to 127.0.0.1.",
    );
  }
}
