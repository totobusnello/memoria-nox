/**
 * src/api/cors.ts — Server-side CORS handler for nox-mem API.
 *
 * Scope: Allows browser extensions (Chrome MV3 + Firefox) to call
 * http://127.0.0.1:18802 without CORS blocks. Required by P7 extension
 * (PR #96).
 *
 * Security posture:
 *   - Default allowlist: chrome-extension://* and moz-extension://* only.
 *   - NO `Access-Control-Allow-Origin: *` — reflects only matched origins.
 *   - Extra origins opt-in via NOX_CORS_EXTRA_ORIGINS env var (comma-separated
 *     regex strings). Requires explicit operator action; not enabled by default.
 *   - Regex patterns are anchored and strict (chrome IDs are exactly 32
 *     lowercase alpha chars; Firefox UUIDs are exactly 36-char hex with dashes).
 *   - Must be called BEFORE routing so OPTIONS preflight short-circuits.
 *
 * Usage in api-server.ts:
 *
 *   import { applyCorsHeaders, handlePreflight } from "./api/cors.js";
 *
 *   async function handleRequest(req: IncomingMessage, res: ServerResponse) {
 *     if (handlePreflight(req, res)) return;   // OPTIONS → 204 + headers
 *     applyCorsHeaders(req, res);               // all other methods
 *     // ... existing routing ...
 *   }
 */

import type { IncomingMessage, ServerResponse } from "node:http";

// ─── Default-allow patterns ──────────────────────────────────────────────────
//
// Chrome extension IDs: exactly 32 lowercase a-z characters.
// Firefox extension IDs: UUID format (8-4-4-4-12 hex, lowercase).
// Both patterns are anchored (^ … $) to prevent substring attacks.

const ALLOWED_ORIGINS_DEFAULT: RegExp[] = [
  /^chrome-extension:\/\/[a-z]{32}$/,
  /^moz-extension:\/\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
];

// ─── Env-driven extra origins ────────────────────────────────────────────────
//
// NOX_CORS_EXTRA_ORIGINS=pattern1,pattern2  (comma-separated regex strings)
// Parsed once at module load. Malformed patterns are silently skipped with a
// console.warn so the server doesn't crash on bad env config.

function parseExtraOriginsFromEnv(): RegExp[] {
  const raw = process.env.NOX_CORS_EXTRA_ORIGINS;
  if (!raw || raw.trim() === "") return [];

  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .flatMap((pattern) => {
      try {
        return [new RegExp(pattern)];
      } catch {
        console.warn(
          `[cors] NOX_CORS_EXTRA_ORIGINS: invalid regex "${pattern}" — skipped`
        );
        return [];
      }
    });
}

const ENV_EXTRA_ORIGINS: RegExp[] = parseExtraOriginsFromEnv();

// ─── Core helpers ────────────────────────────────────────────────────────────

/**
 * Checks whether `origin` matches any of the allowed patterns.
 * Returns `true` if matched, `false` otherwise.
 */
export function isOriginAllowed(
  origin: string,
  extraOrigins: RegExp[] = []
): boolean {
  const patterns = [
    ...ALLOWED_ORIGINS_DEFAULT,
    ...ENV_EXTRA_ORIGINS,
    ...extraOrigins,
  ];
  return patterns.some((re) => re.test(origin));
}

export interface CorsOptions {
  /** Additional origin regexes beyond the built-in extension patterns. */
  extraOrigins?: RegExp[];
  /**
   * Set Access-Control-Allow-Credentials: true.
   * Only useful when the caller uses `withCredentials: true` in XHR/fetch.
   * Off by default — extensions don't need it for basic JSON calls.
   */
  allowCredentials?: boolean;
}

/**
 * Applies CORS headers to `res` if `req.headers.origin` is in the allowlist.
 * No-op when:
 *   - Request has no Origin header (same-origin or non-browser request).
 *   - Origin does not match any allowed pattern.
 *
 * Sets:
 *   - `Access-Control-Allow-Origin` — echoes the matched origin (never "*")
 *   - `Vary: Origin` — prevents caching cross-origin mismatch
 *   - `Access-Control-Allow-Methods` — GET, POST, OPTIONS
 *   - `Access-Control-Allow-Headers` — Content-Type, Authorization
 *   - `Access-Control-Max-Age` — 86400 (24 h preflight cache)
 *   - `Access-Control-Allow-Credentials` — only when opts.allowCredentials
 */
export function applyCorsHeaders(
  req: IncomingMessage,
  res: ServerResponse,
  opts?: CorsOptions
): void {
  const origin = req.headers["origin"];
  if (!origin) return;

  if (!isOriginAllowed(origin, opts?.extraOrigins ?? [])) return;

  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization"
  );
  res.setHeader("Access-Control-Max-Age", "86400");

  if (opts?.allowCredentials) {
    res.setHeader("Access-Control-Allow-Credentials", "true");
  }
}

/**
 * Handles an HTTP OPTIONS preflight request.
 *
 * If `req.method === "OPTIONS"`:
 *   - Applies CORS headers (if origin matches)
 *   - Responds 204 No Content
 *   - Returns `true` — caller must stop processing
 *
 * If method is not OPTIONS:
 *   - Returns `false` — caller continues routing normally
 *
 * Pattern:
 *
 *   if (handlePreflight(req, res)) return;
 */
export function handlePreflight(
  req: IncomingMessage,
  res: ServerResponse,
  opts?: CorsOptions
): boolean {
  if (req.method !== "OPTIONS") return false;

  applyCorsHeaders(req, res, opts);
  res.writeHead(204);
  res.end();
  return true;
}
