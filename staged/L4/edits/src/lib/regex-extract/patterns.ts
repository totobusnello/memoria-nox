/**
 * T2 — DIR_PATTERN + entity-ref regexes.
 *
 * Adapted from gbrain/src/core/link-extraction.ts (MIT). Adjusted for nox-mem
 * entity-type whitelist (specs/2026-05-18-L4-regex-first-extraction.md §4).
 *
 * IMPORTANT: All consumer regexes carry the global flag (`g`). Always reset
 * `.lastIndex = 0` before reuse or instantiate a fresh RegExp; callers in
 * extractor.ts do so by constructing per call via {@link buildEntityRefRe}.
 */

import { NOX_ENTITY_TYPES } from "./types.js";

/** `(?:feedback|person|...)` literal alternation snippet — non-capturing. */
export const DIR_PATTERN = `(?:${NOX_ENTITY_TYPES.filter((t) => t !== "entities").join("|")})`;

/** Top-level dir prefix `entities/` is optional in wikilinks. */
export const OPTIONAL_TOP = `(?:entities\\/)?`;

/** Slug character class: letters, digits, underscore, dash. NO dots (drops `.md`). */
export const SLUG_CHARS = `[a-z0-9_\\-]+`;

/**
 * Markdown-link form: `[Name](path/to/entityType/slug)`, optional `.md`, optional
 * tooltip `"..."`. Path may have `../` prefix.
 *
 * Groups:
 *  1 — display text
 *  2 — entity type
 *  3 — slug (no .md, no anchor)
 */
export function buildMarkdownLinkRe(): RegExp {
  return new RegExp(
    String.raw`\[([^\]\n]+?)\]\(` +
      String.raw`(?:\.{1,2}\/)*` +
      `(?:entities\\/)?` +
      `(${DIR_PATTERN})\\/` +
      `(${SLUG_CHARS})` +
      String.raw`(?:\.md)?` +
      String.raw`(?:#[^)\s]*)?` +
      String.raw`(?:\s+"[^"]*")?` +
      String.raw`\)`,
    "g",
  );
}

/**
 * Obsidian wikilink form: `[[entityType/slug]]`, optional `entities/` prefix,
 * optional `#anchor`, optional `|display`. Accept ASCII-aware slugs only —
 * Unicode boundary issues handled in extractor via stripping non-slug chars.
 *
 * Groups:
 *  1 — entity type
 *  2 — slug
 *  3 — display (after `|`, optional)
 */
export function buildWikilinkRe(): RegExp {
  return new RegExp(
    String.raw`\[\[` +
      `(?:entities\\/)?` +
      `(${DIR_PATTERN})\\/` +
      `(${SLUG_CHARS})` +
      String.raw`(?:#[^|\]\n]*)?` +
      String.raw`(?:\|([^\]\n]+?))?` +
      String.raw`\]\]`,
    "g",
  );
}

/**
 * Bare slug form: standalone `entityType/slug` token, only when surrounded by
 * whitespace/start/punctuation boundary. Uses lookbehind/lookahead WITHOUT
 * `\b` (MEMORY.md `JS regex \b falha em Unicode`).
 *
 * Tightly anchored to avoid URL false-positives — disallow `/` directly before
 * the token (so `example.com/feedback/foo` does NOT match).
 *
 * Groups:
 *  1 — entity type
 *  2 — slug
 */
export function buildBareRefRe(): RegExp {
  return new RegExp(
    `(?<=^|[\\s(,;:'"\`])` +
      `(${DIR_PATTERN})\\/` +
      `(${SLUG_CHARS})` +
      `(?=$|[\\s).,?!;:'"\`])`,
    "gm",
  );
}

/**
 * Code-path references (`src/lib/op-audit.ts:42`, `specs/foo.md`). Domain dirs
 * are whitelisted to suppress matches against unrelated path-like text.
 *
 * Groups:
 *  1 — top-level dir
 *  2 — path under root (extension included)
 *  3 — extension
 *  4 — line number (optional)
 */
export function buildCodeRefRe(): RegExp {
  return new RegExp(
    `(?<=^|[\\s(,;:'"\`])` +
      `(src|specs|audits|eval|validation|memory|paper|docs|runbooks|scripts|lessons|benchmark)` +
      `\\/` +
      `([a-z0-9_\\-\\/\\.]+\\.(ts|js|md|sh|json|yaml|yml|sql|py))` +
      `(?::(\\d+))?`,
    "gmi",
  );
}
