/**
 * G12 — Safe error message helper (Wave G)
 *
 * Sanitize `(e as Error).message` before exposing it in 5xx responses across
 * `/api/hooks/recent` (P2), `/api/conflict/:id/resolve` (L2), `/api/mark` (L3),
 * and any future endpoint that may surface backend errors to clients.
 *
 * Complements G5 (Wave F) which strips `error.stack`. Even with stack gone,
 * `error.message` itself often contains:
 *   - Absolute file paths (`/Users/.../db.ts:42:15`, `/root/.openclaw/...`)
 *   - SQLite connection strings (`SQLITE_ERROR: ... /var/lib/nox-mem.db ...`)
 *   - Env var values dumped by stricter ORMs (`ENV NOX_API_TOKEN=xyz ...`)
 *   - Stack frame fragments embedded in long `Error.toString()` outputs
 *
 * Strategy:
 *   1. Walk through a small set of regex strippers (paths, DB strings, env).
 *   2. Generate a stable correlation ID (UUID-v4) to map sanitized error
 *      → original (logged server-side via `onLog`).
 *   3. Return generic message + correlationId. Caller logs full error.
 *
 * Threats addressed (refs PR #58 §14):
 *   - G12 (High) — `/api/hooks/recent` 500 leaks DB path.
 *   - R-L3-3 — `/mark` 500 leaks SQL fragments.
 *   - Cross-cutting hardening across staged-* edit dirs.
 *
 * Backward compat:
 *   - Pure function. No deps on Express / Fastify / http. Caller wires it
 *     into existing handlers.
 *   - Env-opt-in for full passthrough during local dev:
 *       NOX_ERROR_PASSTHROUGH=1 → returns raw message (NEVER set in prod).
 *       A boot-time WARN should be emitted by the caller when active.
 */

import { randomUUID } from "node:crypto";

// ── strippers ───────────────────────────────────────────────────────────────

/**
 * Each stripper takes a string and returns a (possibly redacted) string.
 * Order matters — paths first, then DB strings, then env values, then
 * generic stack-line patterns.
 */
const STRIPPERS: ReadonlyArray<{ name: string; re: RegExp; replacement: string }> = [
  // Absolute POSIX paths with optional :line:col suffix (mac dev + linux prod).
  { name: "users-path", re: /\/Users\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  { name: "root-path", re: /\/root\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  { name: "var-path", re: /\/var\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  { name: "opt-path", re: /\/opt\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  { name: "tmp-path", re: /\/tmp\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  { name: "home-path", re: /\/home\/[^\s'"`)]+(?::\d+(?::\d+)?)?/g, replacement: "<path>" },
  // SQLite errors often embed the DB file path. We catch the path with the
  // earlier rules; this catches the connection-string-style fragment.
  { name: "sqlite-conn", re: /(?:sqlite:|file:)[^\s'"`)]+/gi, replacement: "<dburl>" },
  // ENV=value patterns (e.g. NOX_API_TOKEN=abc123).
  { name: "env-assign", re: /\b([A-Z][A-Z0-9_]{2,})=([A-Za-z0-9_\-\.+/=]{4,})/g, replacement: "$1=<redacted>" },
  // Bearer tokens / API keys embedded inline.
  { name: "bearer", re: /\bBearer\s+[A-Za-z0-9_\-\.]+/gi, replacement: "Bearer <redacted>" },
  // Long opaque tokens (32+ chars). Avoid greedy match on natural language.
  { name: "long-token", re: /\b[A-Za-z0-9_\-]{32,}\b/g, replacement: "<token>" },
  // Stack frame fragments that survive `Error.toString()` flattening.
  { name: "stack-frame", re: /\bat\s+[^\s()]+\s+\([^\s)]+\)/g, replacement: "<frame>" },
];

export interface SanitizeOptions {
  /** Cap on returned message length. Default 200. */
  maxLength?: number;
  /** Generic fallback when stripping leaves empty/garbage. Default 'internal_error'. */
  fallback?: string;
  /** Allow raw passthrough (DEV ONLY). Default false. */
  passthrough?: boolean;
}

export interface SafeErrorResult {
  /** Sanitized, length-capped message safe to expose in 5xx responses. */
  message: string;
  /** UUID-v4 correlation ID. Log server-side with the raw error for triage. */
  correlationId: string;
}

/**
 * Sanitize an arbitrary error/string for client exposure.
 */
export function safeErrorMessage(
  e: unknown,
  opts: SanitizeOptions = {},
): SafeErrorResult {
  const correlationId = randomUUID();
  const passthrough =
    opts.passthrough ?? process.env.NOX_ERROR_PASSTHROUGH === "1";

  const raw = extractMessage(e);

  if (passthrough) {
    return { message: raw, correlationId };
  }

  let cleaned = raw;
  for (const s of STRIPPERS) {
    cleaned = cleaned.replace(s.re, s.replacement);
  }

  // Collapse whitespace; remove repeated <path>/<frame>/<token> placeholders.
  cleaned = cleaned
    .replace(/\s+/g, " ")
    .replace(/(<path>(?:\s+<path>)+)/g, "<path>")
    .replace(/(<frame>(?:\s+<frame>)+)/g, "<frame>")
    .replace(/(<token>(?:\s+<token>)+)/g, "<token>")
    .trim();

  if (!cleaned || cleaned === "<path>" || cleaned === "<frame>") {
    cleaned = opts.fallback ?? "internal_error";
  }

  const maxLength = opts.maxLength ?? 200;
  if (cleaned.length > maxLength) {
    cleaned = cleaned.slice(0, maxLength - 3) + "...";
  }

  return { message: cleaned, correlationId };
}

function extractMessage(e: unknown): string {
  if (typeof e === "string") return e;
  if (e instanceof Error) return e.message ?? String(e);
  if (e && typeof e === "object" && "message" in e) {
    const m = (e as { message: unknown }).message;
    return typeof m === "string" ? m : String(m);
  }
  return String(e);
}

// ── helpers for caller-side adoption ────────────────────────────────────────

/**
 * Build a complete `{ error, correlation_id }` body for HTTP 500 responses.
 * Optionally invoke a logging hook with the full original error.
 */
export function buildSafeErrorBody(
  e: unknown,
  opts: SanitizeOptions & {
    onLog?: (info: { correlationId: string; raw: unknown }) => void;
  } = {},
): { error: string; correlation_id: string } {
  const { message, correlationId } = safeErrorMessage(e, opts);
  opts.onLog?.({ correlationId, raw: e });
  return { error: message, correlation_id: correlationId };
}

/**
 * Boot-time check — caller should invoke once on startup to emit a WARN
 * when passthrough is enabled.
 */
export function checkErrorPassthroughAtBoot(
  logger: { warn: (msg: string) => void } = console,
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  if (env.NOX_ERROR_PASSTHROUGH === "1") {
    logger.warn(
      "[security] NOX_ERROR_PASSTHROUGH=1 — 5xx responses will leak raw error messages. " +
        "DISABLE in production.",
    );
    return true;
  }
  return false;
}
