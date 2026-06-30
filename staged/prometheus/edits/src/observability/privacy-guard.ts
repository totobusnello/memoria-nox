/**
 * src/observability/privacy-guard.ts — PII / sensitive-text stripper (T9).
 *
 * RULES (non-negotiable):
 *   1. No raw query text in label values — replace with "<redacted-query>".
 *   2. No paths, file names, IPs, emails, phone numbers, BR personal IDs
 *      (CPF/CNPJ/CEP/RG), Pix keys, API keys / bearer tokens.
 *   3. Anything not on a strict allowlist of "shapes" → "<redacted>".
 *
 * This module composes with `cardinality.ts` — privacy strips PII *contents*,
 * cardinality enforces *shape* (allowlists) and *budget*.
 *
 * Patterns mirror A1 (privacy filter) and A1.1 (BR PII). Kept self-contained
 * to avoid coupling — the observability layer must function even if the
 * privacy package is later refactored.
 */

// ─── PII / secret patterns ───────────────────────────────────────────────────

const PATTERNS: ReadonlyArray<{ re: RegExp; label: string }> = [
  // Emails
  { re: /[\w.+-]+@[\w-]+\.[\w.-]+/gi, label: "<redacted-email>" },
  // Bearer tokens / Bearer + JWT-ish
  { re: /Bearer\s+[A-Za-z0-9._-]{16,}/gi, label: "<redacted-bearer>" },
  // OpenAI / Anthropic / Gemini-ish API keys
  { re: /sk-[A-Za-z0-9_-]{20,}/g, label: "<redacted-key>" },
  { re: /AIza[0-9A-Za-z_-]{20,}/g, label: "<redacted-key>" },
  { re: /\bgsk_[A-Za-z0-9]{20,}/g, label: "<redacted-key>" },
  // Generic high-entropy hex/uuid in the wild (32+ chars hex)
  { re: /\b[A-Fa-f0-9]{32,}\b/g, label: "<redacted-hex>" },
  // UUID
  {
    re: /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi,
    label: "<redacted-uuid>",
  },
  // IPv4
  { re: /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, label: "<redacted-ip>" },
  // CPF (Brazilian personal ID) — 000.000.000-00 or 11 digits
  { re: /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g, label: "<redacted-cpf>" },
  // CNPJ — 00.000.000/0000-00
  {
    re: /\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b/g,
    label: "<redacted-cnpj>",
  },
  // CEP — 00000-000
  { re: /\b\d{5}-\d{3}\b/g, label: "<redacted-cep>" },
  // Phone — generic E.164 + BR
  { re: /\+?\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{4,5}[\s-]?\d{4}/g, label: "<redacted-phone>" },
  // Absolute path (Unix or Windows)
  { re: /(?:[A-Za-z]:)?(?:\/[\w.\-+@]+){2,}/g, label: "<redacted-path>" },
  // URL
  { re: /https?:\/\/[\w.\-/?&=%#:]+/gi, label: "<redacted-url>" },
];

/** Strip PII from a string. Returns the sanitized string. */
export function sanitizeString(s: string): string {
  if (!s) return s;
  let out = s;
  for (const { re, label } of PATTERNS) {
    out = out.replace(re, label);
  }
  return out;
}

/**
 * Validate a label value: it must be either a known short shape (alphanum,
 * snake_case, enum-style), or it gets coerced to "<redacted>".
 *
 * The intent is that *label values* are categorical (small set of low-entropy
 * strings). Anything longer than 64 chars or containing PII patterns is
 * automatically dropped.
 */
const SAFE_VALUE_RE = /^[A-Za-z0-9_:\-.+]{1,64}$/;

const FORBIDDEN_NAME_HINTS = [
  "query",
  "prompt",
  "response",
  "user",
  "email",
  "ip",
  "path",
  "file",
];

export function sanitizeLabelValue(name: string, value: string): string {
  // First, hard-strip PII patterns.
  const stripped = sanitizeString(value);

  // If the name itself looks like it carries content (query, prompt, …),
  // collapse the value to a constant.
  if (FORBIDDEN_NAME_HINTS.some((h) => name.toLowerCase().includes(h))) {
    return "<redacted>";
  }

  // If after stripping it doesn't match safe shape, redact.
  if (!SAFE_VALUE_RE.test(stripped)) {
    return "<redacted>";
  }
  return stripped;
}

/** Sanitize an entire labels object — drop forbidden keys, coerce values. */
export function sanitizeLabels(
  labels: Record<string, string>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(labels)) {
    if (typeof v !== "string") continue;
    out[k] = sanitizeLabelValue(k, v);
  }
  return out;
}

// ─── Composable guard: privacy → cardinality ────────────────────────────────

import { CardinalityGuard, getDefaultGuard } from "./cardinality.js";

export interface GuardChainResult {
  /** Sanitized + cardinality-checked labels, or null if dropped. */
  labels: Record<string, string> | null;
}

/**
 * One-call guard for any metric: privacy first, then cardinality.
 *
 * This is the function the recording API uses. Caller should `null`-check.
 */
export function guardLabels(
  metricName: string,
  rawLabels: Record<string, string> = {},
  guard: CardinalityGuard = getDefaultGuard(),
): GuardChainResult {
  const sanitized = sanitizeLabels(rawLabels);
  const checked = guard.guard(metricName, sanitized);
  return { labels: checked };
}
