/**
 * T4 — Redaction / NOX_VIEWER_SHOW_QUERY opt-in
 *
 * Default-deny philosophy: SearchEvent.query, content fields, embeddings, and
 * raw entity names are all redacted by default. Opt-IN via env var only.
 *
 * Env vars handled here:
 *  - NOX_VIEWER_SHOW_QUERY=1     → SearchEvent.query carries raw query text
 *
 * Boot-time WARN must be emitted by `viewerStartupWarnings()` whenever ANY
 * privacy-loosening env is set so operators don't forget it on prod.
 */

import { createHash } from "node:crypto";
import {
  type ViewerEvent,
  type SearchEventDetails,
  isSearchEvent,
} from "./event-types.js";

export const REDACTED = "<redacted>";

/** Stable, non-reversible label for a query string. */
export function queryHash(raw: string): string {
  return createHash("sha256").update(raw).digest("hex").slice(0, 16);
}

/** Stable, non-reversible label for an entity name. */
export function nameHash(raw: string): string {
  return createHash("sha1").update(raw).digest("hex").slice(0, 8);
}

/** Reduce an absolute path to just the basename. */
export function safeBasename(path: string | undefined | null): string | undefined {
  if (!path) return undefined;
  const idx = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return idx >= 0 ? path.slice(idx + 1) : path;
}

/** Truthy env check tolerant of unset/null. */
function envOn(name: string): boolean {
  const v = (typeof process !== "undefined" ? process.env[name] : undefined) ?? "";
  return v === "1" || v.toLowerCase() === "true" || v.toLowerCase() === "yes";
}

export interface RedactionOptions {
  /** Default reads NOX_VIEWER_SHOW_QUERY env. Pass explicit boolean for tests. */
  showQuery?: boolean;
}

function showQueryEnabled(opts: RedactionOptions = {}): boolean {
  if (typeof opts.showQuery === "boolean") return opts.showQuery;
  return envOn("NOX_VIEWER_SHOW_QUERY");
}

/**
 * Apply redaction pass to a ViewerEvent before it leaves the process.
 * Returns a NEW object — input is not mutated.
 *
 * Invariants:
 *  - SearchEvent.details.query MUST be `REDACTED` unless `showQuery` opts say otherwise.
 *  - No `content`, `body`, `text`, `embedding`, or `prompt` fields anywhere.
 *  - Absolute paths anywhere -> basename only.
 */
export function redactEvent(
  raw: ViewerEvent,
  opts: RedactionOptions = {}
): ViewerEvent {
  const showQuery = showQueryEnabled(opts);

  // Deep-clone via structured pass (events are small POJOs).
  const cloned: ViewerEvent = JSON.parse(JSON.stringify(raw));

  if (isSearchEvent(cloned)) {
    const details: SearchEventDetails = cloned.details;
    if (!showQuery) {
      details.query = REDACTED;
    }
  }

  // Strip universally forbidden fields if any sneaked in.
  stripForbiddenFields(cloned as unknown as Record<string, unknown>);
  return cloned;
}

const FORBIDDEN_FIELDS: ReadonlySet<string> = new Set([
  "content",
  "body",
  "text",
  "raw_text",
  "prompt",
  "response",
  "embedding",
  "embedding_vector",
  "vector",
  "password",
  "token",
  "api_key",
  "secret",
]);

/**
 * Recursively strip forbidden field names. Also reduces any string field
 * that looks like an absolute path to its basename via heuristic.
 */
export function stripForbiddenFields(node: unknown): void {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i += 1) {
      const v = node[i];
      if (typeof v === "string" && looksLikeAbsolutePath(v)) {
        node[i] = safeBasename(v);
      } else if (v && typeof v === "object") {
        stripForbiddenFields(v);
      }
    }
    return;
  }
  const obj = node as Record<string, unknown>;
  for (const key of Object.keys(obj)) {
    if (FORBIDDEN_FIELDS.has(key)) {
      delete obj[key];
      continue;
    }
    const val = obj[key];
    if (typeof val === "string" && looksLikeAbsolutePath(val)) {
      obj[key] = safeBasename(val);
    } else if (val && typeof val === "object") {
      stripForbiddenFields(val);
    }
  }
}

function looksLikeAbsolutePath(s: string): boolean {
  // Match Unix absolute or Windows drive letter; require at least one slash
  // and a few chars to dodge false positives on URLs / hashes / general text.
  if (s.length < 4) return false;
  if (s.startsWith("/") && s.includes("/", 1) && !s.startsWith("//")) return true;
  if (/^[A-Za-z]:[\\\/]/.test(s)) return true;
  return false;
}

/**
 * Strings to print at boot when env flags expose more than default.
 * Caller does the `console.warn` so it can route to logger of choice.
 */
export function viewerStartupWarnings(env: NodeJS.ProcessEnv = process.env): string[] {
  const out: string[] = [];
  if (env.NOX_VIEWER_SHOW_QUERY === "1") {
    out.push(
      "[WARN] NOX_VIEWER_SHOW_QUERY=1 — raw queries visible on /api/events/stream. " +
        "Do NOT enable in shared environments."
    );
  }
  if (env.NOX_VIEWER_BIND === "0.0.0.0" && !env.NOX_VIEWER_AUTH_TOKEN) {
    out.push(
      "[WARN] NOX_VIEWER_BIND=0.0.0.0 without NOX_VIEWER_AUTH_TOKEN — viewer reachable from network. " +
        "Set NOX_VIEWER_AUTH_TOKEN or restrict bind."
    );
  }
  return out;
}
