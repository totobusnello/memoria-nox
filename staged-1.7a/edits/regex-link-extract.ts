/**
 * regex-link-extract.ts — L4 typed-link extraction (gbrain-inspired port)
 *
 * Adapted from gbrain/src/core/link-extraction.ts (MIT, Garry Tan, 16.6k★).
 *
 * Scope: this file covers the FOUNDATIONAL extraction primitives (T1+T2+T3
 * of spec §11). T4 frontmatter rules + T5 code refs + T6 ingest integration
 * are out of scope for this sprint and ship in follow-ups.
 *
 * # T0 reality check (2026-05-21)
 *
 * Spec §4 proposed 16 entity types (feedback, person, lesson, decision,
 * project, team, daily, pending, graph_node, agent, incident, spec, audit,
 * skill, persona, reference). Live VPS `/root/.openclaw/workspace/memory/
 * entities/` exposes only FIVE plural dirs:
 *
 *   agents/ decisions/ lessons/ projects/ systems/
 *
 * `kg_entities.entity_type` distribution is broader (concept 4848, person
 * 3178, document 2857, metric, organization, tool, agent 249, decision 110,
 * ...) — but those are Gemini-extracted abstractions without a filesystem
 * canonical home. Regex extraction only makes sense against filesystem-
 * resolvable refs, so we anchor DIR_PATTERN to the live dirs.
 *
 * Deviation from spec: 5 plural dirs instead of 16 singular. Documented in
 * the PR description; spec §4 should be updated in a follow-up commit.
 *
 * # Public API
 *
 *   stripCodeBlocks(text)         — remove fenced + inline code, preserve offsets
 *   extractEntityRefsRegex(text)  — extract entity refs (markdown / wikilink / bare)
 *
 * # Internals exposed for tests via _internals
 *
 *   NOX_ENTITY_DIRS, DIR_PATTERN, MARKDOWN_LINK_RE, WIKILINK_RE, BARE_REF_RE
 *
 * # Cross-refs
 *
 *   - Spec: specs/2026-05-18-L4-regex-first-extraction.md
 *   - CLAUDE.md regra #5 (shadow-mode mandatory)
 *   - MEMORY.md `[[js-regex-unicode-word-boundary-fails]]` — Unicode handling
 *   - MEMORY.md `[[unicode-aware-sanitize-for-fts5]]` — `\p{L}\p{N}` patterns
 */

/**
 * Live entity-file directories on `memory/entities/` (T0 verified
 * 2026-05-21 against VPS `/root/.openclaw/workspace/memory/entities/`).
 *
 * Plural — matches filesystem layout. Singular variants (e.g. "lesson",
 * "decision") are NOT accepted as path components; they only appear as
 * `kg_entities.entity_type` values, which is a separate concern.
 */
export const NOX_ENTITY_DIRS = [
  "agents",
  "decisions",
  "lessons",
  "projects",
  "systems",
] as const;

export type NoxEntityDir = (typeof NOX_ENTITY_DIRS)[number];

/**
 * Non-capturing alternation matching any of the live entity dirs.
 * Kept as a literal so we can inline it into the source-static patterns
 * below (regex literals can't interpolate from runtime).
 */
const DIR_PATTERN = `(?:agents|decisions|lessons|projects|systems)`;

/**
 * Markdown link to an entity file:
 *   [Display text](agents/nox)
 *   [Display text](decisions/2026-03-09-brave-search.md)
 *   [Display text](memory/entities/lessons/foo.md)
 *
 * Capture groups:
 *   1: display text
 *   2: full path string (must contain DIR_PATTERN as a path component)
 *
 * We post-filter the path string in `extractEntityRefsRegex` to pull out
 * the (dir, slug) pair and reject URLs.
 */
const MARKDOWN_LINK_RE = /\[([^\]]+)\]\(\s*([^)\s]+?)\s*(?:\s+"[^"]*")?\s*\)/g;

/**
 * Obsidian-style wikilink to an entity:
 *   [[agents/nox]]            (legacy bare form)
 *   [[entities/agents/nox]]   (preferred fully-qualified form)
 *
 * Capture groups:
 *   1: optional "entities" prefix (kept only as a sanity guard)
 *   2: entity dir (DIR_PATTERN)
 *   3: slug (lowercase + digits + dash + underscore)
 */
const WIKILINK_RE = new RegExp(
  `\\[\\[(?:(entities)\\/)?(${DIR_PATTERN})\\/([a-z0-9_\\-]+)\\]\\]`,
  "g",
);

/**
 * Bare reference appearing inline in prose:
 *   "see decisions/brave-search"
 *   "ref agents/nox"
 *
 * Lookbehind requires start-of-string OR whitespace OR opening paren —
 * avoids matching `https://example.com/lessons/foo` (the slash before
 * `lessons` is path, not whitespace).
 *
 * Lookahead allows EOL, whitespace, or sentence punctuation.
 *
 * Capture groups:
 *   1: entity dir
 *   2: slug
 */
const BARE_REF_RE = new RegExp(
  `(?<=^|[\\s\\(])(${DIR_PATTERN})\\/([a-z0-9_\\-]+)(?=$|[\\s\\.,;:!?\\)])`,
  "g",
);

// ── stripCodeBlocks ───────────────────────────────────────────────────────────

/**
 * Replace fenced code blocks (```…```) and inline code (`…`) with
 * length-equivalent whitespace runs so that regex matches over the
 * resulting string still align with offsets in the original.
 *
 * This is the FIRST step of any extraction — prevents wikilinks /
 * markdown-style links inside code examples from being treated as
 * real entity refs.
 *
 * # Notes
 *
 * - Fenced blocks are matched in a single non-greedy run including the
 *   surrounding triple-backtick fences themselves. Nested fences are
 *   not supported (CommonMark forbids them); the regex stops at the
 *   first closing fence at any indent.
 * - Inline backticks are stripped pair-wise. Mismatched single backticks
 *   pass through (rare in prose; harmless if a stray ref hides nearby —
 *   the consumer dedups anyway).
 * - We deliberately preserve newlines inside fenced blocks so that line
 *   numbers in callers' error messages stay sane. Other content becomes
 *   plain ASCII space.
 */
export function stripCodeBlocks(text: string): string {
  // Pass 1 — fenced blocks. Pattern handles ``` and ```lang fences.
  let out = text.replace(/```[\s\S]*?```/g, (m) => {
    // Replace non-newline chars with spaces; keep \n intact for line preservation.
    return m.replace(/[^\n]/g, " ");
  });
  // Pass 2 — inline backticks. Non-greedy, single-line.
  out = out.replace(/`[^`\n]*?`/g, (m) => " ".repeat(m.length));
  return out;
}

// ── extractEntityRefsRegex ────────────────────────────────────────────────────

export interface ExtractedRef {
  /** Entity directory (NOX_ENTITY_DIRS member). */
  dir: NoxEntityDir;
  /** Slug (filename without extension). */
  slug: string;
  /**
   * Canonical key `<dir>/<slug>` — used for dedup and as a stable handle
   * for downstream KG resolution.
   */
  key: string;
  /** Where the match was extracted from (telemetry / debug). */
  source: "markdown" | "wikilink" | "bare";
}

/**
 * Strip a `.md` / `.markdown` suffix from a path component if present.
 * Slugs in `kg_entities` are stored extension-free; markdown links may
 * include the extension. Normalise here so dedup catches both forms.
 */
function stripMdExt(s: string): string {
  return s.replace(/\.(md|markdown)$/i, "");
}

/**
 * Parse a markdown link target like `memory/entities/agents/nox.md`,
 * `entities/agents/nox`, or `agents/nox.md` into `{ dir, slug }`.
 *
 * Returns `null` if:
 *   - the URL has a scheme (http:, mailto:, ...) — external, not an entity ref
 *   - no path component matches `DIR_PATTERN`
 *   - the slug after that dir is empty
 *   - the slug after dir contains a slash (sub-path; out of scope)
 */
function parseMarkdownTarget(target: string): { dir: NoxEntityDir; slug: string } | null {
  // Reject URLs / external links.
  if (/^[a-z][a-z0-9+\-.]*:/i.test(target)) return null;
  // Strip fragment / query.
  const cleaned = target.split("#")[0]!.split("?")[0]!;
  const parts = cleaned.split("/").filter((p) => p.length > 0);
  // The entity ref form is exactly `<...>/<dir>/<slug>` — the dir MUST be the
  // second-to-last segment so the slug is the final segment. Sub-paths under
  // entity dirs (e.g. `agents/nox/notes.md`) are NOT first-class entities and
  // must be rejected — the file `agents/nox/notes.md` is "notes inside nox",
  // not the nox entity.
  if (parts.length < 2) return null;
  const dir = parts[parts.length - 2];
  const slugRaw = parts[parts.length - 1];
  if (!dir || !slugRaw) return null;
  if (!(NOX_ENTITY_DIRS as readonly string[]).includes(dir)) return null;
  const slug = stripMdExt(slugRaw);
  if (slug.length === 0) return null;
  // Reject slugs that don't look like valid entity slugs (alpha-numeric +
  // underscore + dash only). Anything with whitespace, dots, slashes, or
  // Unicode is filtered out here — live VPS slugs are ASCII.
  if (!/^[a-z0-9_\-]+$/i.test(slug)) return null;
  return { dir: dir as NoxEntityDir, slug: slug.toLowerCase() };
}

/**
 * Extract entity refs from a chunk of text. Call `stripCodeBlocks` first
 * (or pass already-stripped text) — this function does NOT strip code
 * itself, to let callers reuse the stripped buffer across multiple
 * extractors (frontmatter, code refs, etc).
 *
 * Refs are deduped by `key` (`<dir>/<slug>`). The first occurrence wins
 * for `source` attribution.
 *
 * # Order of extractors
 *
 * 1. Wikilinks  — most explicit, lowest false-positive rate
 * 2. Markdown   — explicit text + path
 * 3. Bare refs  — highest false-positive risk; runs last so it can
 *                 only contribute keys NOT already captured.
 */
export function extractEntityRefsRegex(text: string): ExtractedRef[] {
  const seen = new Map<string, ExtractedRef>();

  // 1) Wikilinks
  for (const m of text.matchAll(WIKILINK_RE)) {
    const dir = m[2] as NoxEntityDir | undefined;
    const slug = m[3];
    if (!dir || !slug) continue;
    const key = `${dir}/${slug.toLowerCase()}`;
    if (!seen.has(key)) {
      seen.set(key, { dir, slug: slug.toLowerCase(), key, source: "wikilink" });
    }
  }

  // 2) Markdown links
  for (const m of text.matchAll(MARKDOWN_LINK_RE)) {
    const target = m[2];
    if (!target) continue;
    const parsed = parseMarkdownTarget(target);
    if (!parsed) continue;
    const key = `${parsed.dir}/${parsed.slug}`;
    if (!seen.has(key)) {
      seen.set(key, { ...parsed, key, source: "markdown" });
    }
  }

  // 3) Bare refs (last — least confident)
  for (const m of text.matchAll(BARE_REF_RE)) {
    const dir = m[1] as NoxEntityDir | undefined;
    const slug = m[2];
    if (!dir || !slug) continue;
    const key = `${dir}/${slug.toLowerCase()}`;
    if (!seen.has(key)) {
      seen.set(key, { dir, slug: slug.toLowerCase(), key, source: "bare" });
    }
  }

  return Array.from(seen.values());
}

// ── _internals (for tests) ────────────────────────────────────────────────────

export const _internals = {
  NOX_ENTITY_DIRS,
  DIR_PATTERN,
  MARKDOWN_LINK_RE,
  WIKILINK_RE,
  BARE_REF_RE,
  parseMarkdownTarget,
  stripMdExt,
};
