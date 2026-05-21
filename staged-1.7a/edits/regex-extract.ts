/**
 * regex-extract.ts — Tier 1 regex-first typed-link extraction for KG pipeline.
 *
 * L4 implementation: regex-first pass before LLM, shadow-mode default.
 * Adapted from gbrain/src/core/link-extraction.ts (MIT, Garry Tan, 16.6k★).
 * See: specs/2026-05-18-L4-regex-first-extraction.md
 *
 * CRITICAL: Shadow-mode DEFAULT. NOX_KG_EXTRACT_MODE=hybrid_shadow until
 * 7-day shadow validation passes. Do NOT promote to active without evidence.
 *
 * Design:
 *  - Pure functions: no IO, no DB, no network.
 *  - Returns shape compatible with existing LLM extraction (entities[], relations[]).
 *  - DIR_PATTERN whitelist (16 nox entity types) prevents false-positives.
 *  - Unicode-safe boundary anchors — NO `\b` (MEMORY.md: JS regex \b fails on PT-BR).
 */

// ─── Entity type whitelist (DIR_PATTERN) ─────────────────────────────────────

/**
 * Canonical nox-mem entity types (SINGULAR form). Mirrors `kg_entities.entity_type`
 * column values stored in the DB. This is the form that downstream consumers
 * (KG lookups, FK joins) expect.
 *
 * T0 validation 2026-05-21: live VPS filesystem `memory/entities/` exposes
 * PLURAL dirs (agents/decisions/lessons/projects/systems/). To bridge the two
 * conventions in a single pass, the regex accepts BOTH singular and plural
 * forms (see DIR_PATTERN), and `asEntityType()` normalises plural → singular
 * before storing the ref. `system` was added in this round to canonicalise
 * the `systems/` filesystem dir (previous list had 16 types; this list has 17).
 */
export const NOX_ENTITY_TYPES = [
  "feedback",
  "person",
  "lesson",
  "decision",
  "project",
  "team",
  "daily",
  "pending",
  "graph_node",
  "agent",
  "incident",
  "spec",
  "audit",
  "skill",
  "persona",
  "reference",
  "system",
] as const;

export type NoxEntityType = (typeof NOX_ENTITY_TYPES)[number];

/**
 * Plural-form filesystem dir names that resolve to a canonical singular
 * entity type. Captures the gap that PR #210 cleanup surfaced.
 *
 * Keep in sync with the live filesystem layout (`memory/entities/`):
 *   agents/, decisions/, lessons/, projects/, systems/.
 *
 * Maps to singular forms in NOX_ENTITY_TYPES via PLURAL_TO_SINGULAR below.
 * Only the 5 plurals that exist on disk today are accepted — adding new
 * filesystem dirs requires extending BOTH this list and PLURAL_TO_SINGULAR.
 */
export const NOX_ENTITY_DIRS_PLURAL = [
  "agents",
  "decisions",
  "lessons",
  "projects",
  "systems",
] as const;

export type NoxEntityDirPlural = (typeof NOX_ENTITY_DIRS_PLURAL)[number];

/** Plural → singular canonical map. */
const PLURAL_TO_SINGULAR: Record<NoxEntityDirPlural, NoxEntityType> = {
  agents: "agent",
  decisions: "decision",
  lessons: "lesson",
  projects: "project",
  systems: "system",
};

/**
 * Alternation snippet: `(?:feedback|person|...|agents|decisions|...)`.
 * Accepts BOTH singular (canonical) and plural (filesystem) forms.
 * Normalisation to singular happens in `asEntityType()`.
 */
const DIR_PATTERN = `(?:${[...NOX_ENTITY_TYPES, ...NOX_ENTITY_DIRS_PLURAL].join("|")})`;

/** Slug character class: lowercase letters, digits, underscore, dash. */
const SLUG_CHARS = `[a-z0-9_\\-]+`;

// ─── Types ────────────────────────────────────────────────────────────────────

/** A single extracted entity reference. */
export interface EntityRef {
  entityType: NoxEntityType;
  slug: string;
  /** Canonical dedup key `<entityType>/<slug>`. */
  key: string;
  display?: string;
  source: "markdown_link" | "wikilink" | "bare_ref";
}

/** Frontmatter-derived typed relation (spec §5). */
export interface FrontmatterRelation {
  relationType:
    | "is_agent_of"
    | "references"
    | "supersedes"
    | "caused_by"
    | "resolves"
    | "decided_by";
  target: string;
  raw: string;
}

/** Code-path reference (`src/lib/op-audit.ts:42`). */
export interface CodeRef {
  root: string;
  path: string;
  line?: number;
  key: string; // `codepath/<normalized_path>`
}

/** Full regex extraction result — shape compatible with LLM extraction output. */
export interface RegexExtractionResult {
  /** Entity references extracted (entity_type + slug). */
  entityRefs: EntityRef[];
  /** Frontmatter-typed relations per spec §5 table. */
  frontmatterRelations: FrontmatterRelation[];
  /** Code-path refs (`src/*.ts`, `specs/*.md`, etc.). */
  codeRefs: CodeRef[];
  /** Total count of all extracted items (entityRefs + frontmatterRelations + codeRefs). */
  totalCount: number;
  /** Whether input had code fences stripped. */
  hadCodeFences: boolean;
}

// ─── T1: stripCodeBlocks ─────────────────────────────────────────────────────

/** Fenced code block (``` with optional info-string). */
const FENCE_RE = /```[^\n]*\n[\s\S]*?```/g;
/** Inline code (single, double, or triple backticks on one line). */
const INLINE_CODE_RE = /(`{1,3})([^\n`]|`(?!`))+?\1/g;
/** Indented 4-space code blocks. */
const INDENTED_BLOCK_RE = /(^|\n)((?:    [^\n]*(?:\n|$))+)/g;

/**
 * Replace code spans with whitespace of equal length, preserving newlines.
 * Length-preserving so any downstream offset math over the stripped buffer
 * maps 1:1 to original positions.
 */
function blankPreserveNewlines(s: string): string {
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    out += ch === "\n" || ch === "\r" ? ch : " ";
  }
  return out;
}

function stripCodeBlocks(text: string): { stripped: string; hadFences: boolean } {
  let hadFences = false;
  let out = text.replace(FENCE_RE, (m) => { hadFences = true; return blankPreserveNewlines(m); });
  out = out.replace(INDENTED_BLOCK_RE, (_full, prefix: string, body: string) => {
    hadFences = true;
    return prefix + blankPreserveNewlines(body);
  });
  out = out.replace(INLINE_CODE_RE, (m) => { hadFences = true; return blankPreserveNewlines(m); });
  return { stripped: out, hadFences };
}

// ─── T2: regex constructors ───────────────────────────────────────────────────

/**
 * Markdown link: `[Name](path/to/entityType/slug)`.
 * Groups: 1=display, 2=entityType, 3=slug.
 */
function buildMarkdownLinkRe(): RegExp {
  return new RegExp(
    String.raw`\[([^\]\n]+?)\]\(` +
    String.raw`(?:\.{1,2}\/)*` +
    `(?:entities\\/)?` +
    `(${DIR_PATTERN})\\/` +
    `(${SLUG_CHARS})` +
    String.raw`(?:\.md)?(?:#[^)\s]*)?(?:\s+"[^"]*")?\)`,
    "g",
  );
}

/**
 * Obsidian wikilink: `[[entityType/slug]]`, optional `entities/` prefix,
 * optional `#anchor`, optional `|display`.
 * Groups: 1=entityType, 2=slug, 3=display.
 */
function buildWikilinkRe(): RegExp {
  return new RegExp(
    String.raw`\[\[` +
    `(?:entities\\/)?` +
    `(${DIR_PATTERN})\\/` +
    `(${SLUG_CHARS})` +
    String.raw`(?:#[^|\]\n]*)?(?:\|([^\]\n]+?))?` +
    String.raw`\]\]`,
    "g",
  );
}

/**
 * Bare slug: standalone `entityType/slug` token at word boundary.
 * Uses lookbehind/lookahead WITHOUT `\b` (MEMORY.md: \b fails on Unicode PT-BR chars).
 * Disallows `/` before the token (prevents URL matches like example.com/feedback/foo).
 * Groups: 1=entityType, 2=slug.
 */
function buildBareRefRe(): RegExp {
  return new RegExp(
    `(?<=^|[\\s(,;:'"\`])` +
    `(${DIR_PATTERN})\\/` +
    `(${SLUG_CHARS})` +
    `(?=$|[\\s).,?!;:'"\`])`,
    "gm",
  );
}

/**
 * Code-path references: `src/lib/op-audit.ts:42`, `specs/foo.md`.
 * Domain dirs whitelisted to suppress false matches in unrelated path-like text.
 * Groups: 1=root-dir, 2=path, 3=extension, 4=line-number (optional).
 */
function buildCodeRefRe(): RegExp {
  return new RegExp(
    `(?<=^|[\\s(,;:'"\`])` +
    `(src|specs|audits|eval|validation|memory|paper|docs|runbooks|scripts|lessons|benchmark)` +
    `\\/` +
    `([a-z0-9_\\-\\/\\.]+\\.(ts|js|md|sh|json|yaml|yml|sql|py))` +
    `(?::(\\d+))?`,
    "gmi",
  );
}

// ─── T3: entity-ref extractor ─────────────────────────────────────────────────

const ENTITY_TYPE_SET: ReadonlySet<string> = new Set(NOX_ENTITY_TYPES);
const PLURAL_DIR_SET: ReadonlySet<string> = new Set(NOX_ENTITY_DIRS_PLURAL);

/**
 * Resolve a captured directory token to its canonical singular entity type.
 * Accepts either form:
 *   - singular form already in NOX_ENTITY_TYPES → returned as-is
 *   - plural filesystem form in NOX_ENTITY_DIRS_PLURAL → mapped via
 *     PLURAL_TO_SINGULAR (`agents` → `agent`, etc.)
 *   - anything else → null (filtered out before pushRef)
 */
function asEntityType(v: string): NoxEntityType | null {
  if (ENTITY_TYPE_SET.has(v)) return v as NoxEntityType;
  if (PLURAL_DIR_SET.has(v)) return PLURAL_TO_SINGULAR[v as NoxEntityDirPlural];
  return null;
}

function pushRef(
  bucket: Map<string, EntityRef>,
  rawType: string,
  rawSlug: string,
  source: EntityRef["source"],
  display?: string,
): void {
  const entityType = asEntityType(rawType);
  if (!entityType) return;
  const slug = rawSlug.toLowerCase();
  if (!slug) return;
  const key = `${entityType}/${slug}`;
  const existing = bucket.get(key);
  if (existing) {
    if (!existing.display && display) existing.display = display;
    return;
  }
  bucket.set(key, { entityType, slug, key, source, display });
}

/**
 * Extract all entity refs from text via 3 regex passes (markdown link,
 * wikilink, bare ref), deduped by canonical key.
 */
export function extractEntityRefsRegex(content: string): EntityRef[] {
  if (!content) return [];
  const { stripped } = stripCodeBlocks(content);
  const refs = new Map<string, EntityRef>();

  for (const m of stripped.matchAll(buildMarkdownLinkRe())) {
    pushRef(refs, m[2] ?? "", m[3] ?? "", "markdown_link", m[1]?.trim());
  }
  for (const m of stripped.matchAll(buildWikilinkRe())) {
    pushRef(refs, m[1] ?? "", m[2] ?? "", "wikilink", m[3]?.trim());
  }
  for (const m of stripped.matchAll(buildBareRefRe())) {
    pushRef(refs, m[1] ?? "", m[2] ?? "", "bare_ref");
  }

  return Array.from(refs.values());
}

// ─── T4: frontmatter relation extractor ──────────────────────────────────────

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

const FIELD_TO_RELATION: Record<string, FrontmatterRelation["relationType"]> = {
  agent: "is_agent_of",
  references: "references",
  supersedes: "supersedes",
  caused_by: "caused_by",
  resolves: "resolves",
  decided_by: "decided_by",
};

function unquote(s: string): string {
  const t = s.trim();
  if (t.length >= 2) {
    const [first, last] = [t[0], t[t.length - 1]];
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return t.slice(1, -1);
    }
  }
  return t;
}

interface ParsedField {
  key: string;
  scalar?: string;
  array?: string[];
}

/**
 * Minimal YAML scalar/array parser for the 6 typed-relation frontmatter fields.
 * Handles: `key: value`, `key: "quoted"`, `key: [a, b]` (flow), block `- item`.
 * NOT a full YAML parser — sufficient for spec §5 requirements.
 */
function parseFrontmatterFields(block: string): ParsedField[] {
  const lines = block.split(/\r?\n/);
  const out: ParsedField[] = [];
  let i = 0;
  while (i < lines.length) {
    const trimmed = (lines[i] ?? "").trim();
    if (!trimmed || trimmed.startsWith("#")) { i++; continue; }
    const colonIdx = trimmed.indexOf(":");
    if (colonIdx <= 0) { i++; continue; }
    const key = trimmed.slice(0, colonIdx).trim();
    const rest = trimmed.slice(colonIdx + 1).trim();
    if (!rest) {
      // Possible block array.
      const items: string[] = [];
      let j = i + 1;
      while (j < lines.length) {
        const peek = (lines[j] ?? "").trim();
        if (peek.startsWith("- ")) { items.push(unquote(peek.slice(2))); j++; continue; }
        if (peek === "") { j++; continue; }
        break;
      }
      if (items.length > 0) { out.push({ key, array: items }); i = j; continue; }
      out.push({ key, scalar: "" }); i++; continue;
    }
    if (rest.startsWith("[") && rest.endsWith("]")) {
      const items = rest.slice(1, -1).trim()
        ? rest.slice(1, -1).split(",").map(unquote).filter(Boolean)
        : [];
      out.push({ key, array: items }); i++; continue;
    }
    out.push({ key, scalar: unquote(rest) }); i++;
  }
  return out;
}

/**
 * Extract typed frontmatter relations per spec §5 table.
 * Returns [] when document has no frontmatter.
 */
export function extractFrontmatterRelations(content: string): FrontmatterRelation[] {
  const m = content.match(FRONTMATTER_RE);
  if (!m) return [];
  const fields = parseFrontmatterFields(m[1] ?? "");
  const out: FrontmatterRelation[] = [];
  for (const f of fields) {
    if (!(f.key in FIELD_TO_RELATION)) continue;
    const relationType = FIELD_TO_RELATION[f.key]!;
    if (f.array) {
      for (const v of f.array) {
        if (v.trim()) out.push({ relationType, target: v.trim(), raw: v });
      }
    } else if (f.scalar) {
      out.push({ relationType, target: f.scalar.trim(), raw: f.scalar });
    }
  }
  return out;
}

// ─── T5: code-ref extractor ───────────────────────────────────────────────────

/**
 * Extract code-path references like `src/lib/op-audit.ts:42` or `specs/E14.md`.
 * Returns virtual entity keys `codepath/<path>` for KG stub creation.
 */
export function extractCodeRefs(content: string): CodeRef[] {
  if (!content) return [];
  const { stripped } = stripCodeBlocks(content);
  const seen = new Map<string, CodeRef>();
  for (const m of stripped.matchAll(buildCodeRefRe())) {
    const root = (m[1] ?? "").toLowerCase();
    const path = m[2] ?? "";
    if (!root || !path) continue;
    const line = m[4] ? Number.parseInt(m[4], 10) : undefined;
    const normalized = `${root}/${path}`.toLowerCase();
    const key = `codepath/${normalized}${line ? `:${line}` : ""}`;
    if (!seen.has(key)) seen.set(key, { root, path, line, key });
  }
  return Array.from(seen.values());
}

// ─── Public extraction entry point ────────────────────────────────────────────

/**
 * Run all 3 regex tiers over a chunk and return the aggregated result.
 *
 * This is the function called by kg-llm.ts hybrid orchestration when
 * `NOX_KG_EXTRACT_MODE !== 'gemini_only'`.
 */
export function regexExtract(content: string): RegexExtractionResult {
  if (!content) {
    return { entityRefs: [], frontmatterRelations: [], codeRefs: [], totalCount: 0, hadCodeFences: false };
  }
  const { hadFences } = stripCodeBlocks(content);
  const entityRefs = extractEntityRefsRegex(content);
  const frontmatterRelations = extractFrontmatterRelations(content);
  const codeRefs = extractCodeRefs(content);
  return {
    entityRefs,
    frontmatterRelations,
    codeRefs,
    totalCount: entityRefs.length + frontmatterRelations.length + codeRefs.length,
    hadCodeFences: hadFences,
  };
}

// ─── Ambiguity detection (for Gemini fallback signal) ────────────────────────

/**
 * Returns true when regex result is likely incomplete and Gemini fallback
 * would add meaningful signal.
 *
 * Ambiguous markers (any one triggers fallback in hybrid_active mode):
 *  - totalCount === 0 (nothing captured)
 *  - content has prose sentences (non-entity text > 200 chars)
 *  - content type hints at conversation/daily log
 */
export function isAmbiguous(
  content: string,
  result: RegexExtractionResult,
  chunkType?: string,
): boolean {
  // Explicit force-Gemini types.
  if (chunkType === "conversation" || chunkType === "daily_log" || chunkType === "freeform") {
    return true;
  }
  // Nothing found — may be prose-only.
  if (result.totalCount === 0 && content.length > 50) return true;
  // Rich prose (long sentences without structured links).
  if (result.entityRefs.length === 0 && content.length > 200) return true;
  return false;
}
