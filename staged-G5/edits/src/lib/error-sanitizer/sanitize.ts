/**
 * G5 T1 — Central error sanitizer for HTTP responses.
 *
 * Threat-model ref: docs/security/THREAT-MODEL.md §6.2 T-A3-1 + Appendix Gap G5.
 *
 * Problem: Wave B HTTP handlers (P1 answer, A2 export, L3 mark, P5 viewer
 * SSE, L2 conflict, P2 hooks) each implement their own catch-block. Several
 * leak `error.stack` or internal paths (`/Users/lab/...`, `/root/...`) via
 * `JSON.stringify(err)` or `err.message` containing fs paths.
 *
 * Solution: one function. All handlers pipe their errors through
 * `sanitizeErrorForHttp()` to produce a fixed shape:
 *
 *   { error: string, code: string, requestId: string, details?: unknown }
 *
 * Always emits requestId so users can quote one to support. Never emits stack
 * (unless `exposeStack: true` AND NODE_ENV=development AND the dev flag is
 * explicitly opted into via the caller).
 *
 * Status-code policy: maps a small allowlist of known error classes. Unknown
 * → 500 + generic message. The status code is the only signal the client
 * needs to differentiate "your input was bad" from "we crashed".
 *
 * Code values are CAPITAL_SNAKE per HTTP-convention; matches both the error's
 * `.name` and a stable string per error class.
 */

import { randomUUID } from "node:crypto";

// ─── Wire types ──────────────────────────────────────────────────────────

export interface SanitizedErrorBody {
  /** User-safe message (≤200 chars). NO paths, NO env, NO stack. */
  error: string;
  /** Stable code: error class name OR known status code label. */
  code: string;
  /** Request correlation ID — present even when caller didn't supply one. */
  requestId: string;
  /**
   * Optional safe details. Caller MUST pre-vet — sanitizer will pass through
   * unchanged but drops the field entirely if it contains a stack trace or
   * a recognised internal-path pattern.
   */
  details?: unknown;
  /**
   * Stack trace — present ONLY when `exposeStack: true` AND `NODE_ENV !== 'production'`.
   * Always omitted in production builds. Tested.
   */
  stack?: string;
}

export interface SanitizeOptions {
  /**
   * Request correlation ID. If empty/missing, generated via crypto.randomUUID().
   * MUST be propagated by the caller (middleware seam).
   */
  requestId?: string;
  /**
   * Expose stack in the response body. Default `false`.
   * GATED additionally on `nodeEnv !== 'production'` — production never leaks.
   */
  exposeStack?: boolean;
  /**
   * NODE_ENV override (defaults to process.env.NODE_ENV).
   * Tests pass this explicitly to validate the prod-guard branch.
   */
  nodeEnv?: string;
  /** Optional log sink for the redacted line (caller-injectable). */
  log?: (line: string) => void;
}

export interface SanitizedResult {
  status: number;
  body: SanitizedErrorBody;
}

// ─── Known error → status mapping ────────────────────────────────────────
//
// Add entries here (and to the tests) when a new throwable becomes part of
// the public HTTP surface. Anything not listed → 500.

const ERROR_STATUS_MAP: ReadonlyMap<string, { status: number; code: string; safeMsg?: string }> =
  new Map([
    // Validation / client input — 4xx
    ["ValidationError", { status: 400, code: "VALIDATION_ERROR" }],
    ["InvalidBodyError", { status: 400, code: "INVALID_BODY" }],
    ["BadRequestError", { status: 400, code: "BAD_REQUEST" }],
    ["WeakPassphraseError", { status: 400, code: "WEAK_PASSPHRASE" }],
    ["UnauthorizedError", { status: 401, code: "UNAUTHORIZED", safeMsg: "missing or invalid auth token" }],
    ["ForbiddenError", { status: 403, code: "FORBIDDEN", safeMsg: "forbidden" }],
    ["NotFoundError", { status: 404, code: "NOT_FOUND", safeMsg: "resource not found" }],
    ["ConflictError", { status: 409, code: "CONFLICT" }],
    ["PayloadTooLargeError", { status: 413, code: "PAYLOAD_TOO_LARGE" }],

    // Archive / encryption — 422 (semantically processable but failed)
    ["BadPassphraseError", { status: 422, code: "BAD_PASSPHRASE", safeMsg: "bad passphrase or wrong key" }],
    ["TamperedArchiveError", { status: 422, code: "TAMPERED_ARCHIVE", safeMsg: "archive integrity check failed" }],
    ["MissingAADError", { status: 422, code: "MISSING_AAD" }],
    ["SchemaVersionError", { status: 422, code: "SCHEMA_VERSION_MISMATCH" }],
    ["ManifestError", { status: 422, code: "MANIFEST_ERROR" }],
    ["ArchiveFormatError", { status: 422, code: "ARCHIVE_FORMAT_ERROR" }],

    // Rate limit / overload — 429
    ["RateLimitError", { status: 429, code: "RATE_LIMITED", safeMsg: "rate limit exceeded" }],
    ["CostCapExceededError", { status: 429, code: "COST_CAP_EXCEEDED" }],

    // Server-side — 5xx
    ["LLMTimeoutError", { status: 504, code: "LLM_TIMEOUT", safeMsg: "upstream LLM timed out" }],
    ["LLMUnreachableError", { status: 502, code: "LLM_UNREACHABLE", safeMsg: "upstream LLM unreachable" }],
    ["RetrievalEmptyError", { status: 503, code: "RETRIEVAL_EMPTY" }],
    ["HallucinationError", { status: 422, code: "HALLUCINATION_AFTER_RETRY" }],
  ]);

// ─── Internal-path patterns (drop on sight) ──────────────────────────────

/**
 * Patterns that indicate an internal filesystem path or runtime detail leaked
 * into the message. If detected, the message is replaced with a generic
 * "internal_error: <code>" string.
 */
const INTERNAL_PATH_PATTERNS: ReadonlyArray<RegExp> = [
  /\/Users\/[^\s'"`]+/, // macOS dev path
  /\/home\/[^\s'"`]+/,  // linux user homedir
  /\/root\/[^\s'"`]+/,  // root path (very common in VPS)
  /\/var\/[^\s'"`]+/,
  /\/etc\/[^\s'"`]+/,
  /\/tmp\/[^\s'"`]+/,
  /\/opt\/[^\s'"`]+/,
  /C:\\[^\s'"`]+/i,     // windows paths just in case
  /\(node:\d+\)/,       // node debug line markers leak pid
  /[A-Za-z]:\\Users\\[^\s'"`]+/, // windows user homedir variants
];

/** Token-shaped secrets — never appear in body */
const SECRET_PATTERNS: ReadonlyArray<RegExp> = [
  /AIza[0-9A-Za-z_-]{20,}/g, // Google API keys
  /sk-[A-Za-z0-9]{20,}/g,    // OpenAI / Stripe-style
  /Bearer\s+[A-Za-z0-9._-]{20,}/gi,
  /eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g, // JWTs
  /xox[bps]-[A-Za-z0-9-]{20,}/g, // Slack
  /ghp_[A-Za-z0-9]{20,}/g,       // GitHub PAT
  /key=[A-Za-z0-9_-]{16,}/g,
  /token=[A-Za-z0-9_-]{16,}/g,
  /password=[^\s&]+/gi,
  /passphrase=[^\s&]+/gi,
];

/** Env-shaped indicators — never appear in body */
const ENV_PATTERNS: ReadonlyArray<RegExp> = [
  /\bNOX_[A-Z_]+=[^\s]+/g,
  /\bGEMINI_API_KEY=[^\s]+/gi,
  /\bANTHROPIC_API_KEY=[^\s]+/gi,
  /\bAWS_[A-Z_]+=[^\s]+/g,
];

const MAX_MSG_LEN = 200;

// ─── Core ────────────────────────────────────────────────────────────────

export function sanitizeErrorForHttp(
  err: unknown,
  opts: SanitizeOptions = {},
): SanitizedResult {
  const requestId =
    typeof opts.requestId === "string" && opts.requestId.length > 0
      ? opts.requestId
      : randomUUID();

  const nodeEnv = opts.nodeEnv ?? process.env.NODE_ENV ?? "production";
  const isProd = nodeEnv === "production";

  // Coerce to Error.
  const errObj: Error =
    err instanceof Error
      ? err
      : new Error(typeof err === "string" ? err : "unknown error");

  const name = errObj.name || "Error";
  const known = ERROR_STATUS_MAP.get(name);
  const status = known?.status ?? 500;
  const code = known?.code ?? "INTERNAL_ERROR";

  // Build a safe message.
  let safeMsg: string;
  if (known?.safeMsg) {
    safeMsg = known.safeMsg;
  } else if (status >= 500) {
    // Server-side: NEVER echo the raw message (might contain SQL fragments,
    // stack lines, internal paths). Use a fixed phrase.
    safeMsg = "internal error";
  } else {
    safeMsg = scrubMessage(errObj.message ?? "");
  }

  // Optional details — sanitizer drops it if it smells like a leak.
  const details = sanitizeDetails((errObj as { details?: unknown }).details);

  const body: SanitizedErrorBody = {
    error: safeMsg,
    code,
    requestId,
  };
  if (details !== undefined) {
    body.details = details;
  }

  // Stack: dev-only AND opt-in. Production NEVER leaks.
  if (opts.exposeStack === true && !isProd && typeof errObj.stack === "string") {
    body.stack = errObj.stack;
  }

  // Log a redacted line for observability (caller can wire to pino/winston).
  if (opts.log) {
    opts.log(
      `[error-sanitizer] requestId=${requestId} status=${status} code=${code} name=${name}`,
    );
  }

  return { status, body };
}

/** Strip secrets/paths/env from a message; trim to MAX_MSG_LEN. */
function scrubMessage(raw: string): string {
  if (typeof raw !== "string" || raw.length === 0) return "request failed";
  let s = raw;
  for (const re of SECRET_PATTERNS) s = s.replace(re, "[REDACTED]");
  for (const re of ENV_PATTERNS) s = s.replace(re, "[REDACTED]");
  // If any internal path remains, replace the whole message — too risky to partially redact.
  for (const re of INTERNAL_PATH_PATTERNS) {
    if (re.test(s)) return "request failed (details redacted)";
  }
  // Drop newlines (stack-like content).
  s = s.replace(/[\r\n]+/g, " ");
  if (s.length > MAX_MSG_LEN) s = s.slice(0, MAX_MSG_LEN) + "…";
  return s;
}

/** Best-effort scrub for an arbitrary `details` payload. */
function sanitizeDetails(d: unknown): unknown {
  if (d == null) return undefined;
  if (typeof d === "string") {
    const cleaned = scrubMessage(d);
    return cleaned === "request failed (details redacted)" ? undefined : cleaned;
  }
  if (typeof d === "number" || typeof d === "boolean") return d;
  if (Array.isArray(d)) {
    const arr = d.map(sanitizeDetails).filter((v) => v !== undefined);
    return arr.length > 0 ? arr : undefined;
  }
  if (typeof d === "object") {
    const out: Record<string, unknown> = {};
    let kept = 0;
    for (const [k, v] of Object.entries(d as Record<string, unknown>)) {
      // Drop top-level forbidden keys
      if (/^(stack|cause|env|process|__proto__)$/i.test(k)) continue;
      const cv = sanitizeDetails(v);
      if (cv !== undefined) {
        out[k] = cv;
        kept++;
      }
    }
    return kept > 0 ? out : undefined;
  }
  return undefined;
}

/** Convenience: generate a fresh requestId (callable from middleware). */
export function newRequestId(): string {
  return randomUUID();
}

/** Re-export so callers can `import { sanitizeErrorForHttp, ... }`. */
export { ERROR_STATUS_MAP };
