/**
 * T4 — extractFrontmatterRelations.
 *
 * Parses a small, well-known subset of YAML frontmatter (scalars + flow/block
 * arrays of scalars) — enough to support the 6 rules in spec §5 without an
 * external dep. If consumers need full YAML they can preprocess and pass the
 * already-parsed object via {@link extractFrontmatterRelationsFromObject}.
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §5.
 */

import { FrontmatterRelation } from "./types.js";

/** Match a leading `---\n...\n---` block. */
const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

const FIELD_TO_RELATION: Record<string, FrontmatterRelation["relationType"]> = {
  agent: "is_agent_of",
  references: "references",
  supersedes: "supersedes",
  caused_by: "caused_by",
  resolves: "resolves",
  decided_by: "decided_by",
};

/** Strip surrounding quotes (single or double). */
function unquote(s: string): string {
  const t = s.trim();
  if (t.length >= 2) {
    const first = t[0];
    const last = t[t.length - 1];
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return t.slice(1, -1);
    }
  }
  return t;
}

/** Pull the `---`-delimited block from the head of a markdown doc. */
export function extractFrontmatterBlock(content: string): string | null {
  const m = content.match(FRONTMATTER_RE);
  return m ? (m[1] ?? null) : null;
}

interface ParsedField {
  key: string;
  /** Single scalar value (no array). */
  scalar?: string;
  /** Array values (collected from flow `[a, b]` or block `- a\n- b`). */
  array?: string[];
}

/**
 * Minimal YAML scalar/array parser for top-level fields. NOT a full YAML
 * implementation — handles:
 *  - `key: value`
 *  - `key: "quoted value"`
 *  - `key: [a, b, c]`  (flow array)
 *  - block array:
 *      key:
 *        - a
 *        - b
 */
export function parseFrontmatterFields(block: string): ParsedField[] {
  const lines = block.split(/\r?\n/);
  const out: ParsedField[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i] ?? "";
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      i++;
      continue;
    }
    const colonIdx = trimmed.indexOf(":");
    if (colonIdx <= 0) {
      i++;
      continue;
    }
    const key = trimmed.slice(0, colonIdx).trim();
    const rest = trimmed.slice(colonIdx + 1).trim();
    if (!rest) {
      // Possible block array — peek subsequent indented `- ` lines.
      const items: string[] = [];
      let j = i + 1;
      while (j < lines.length) {
        const peek = lines[j] ?? "";
        const peekTrim = peek.trim();
        if (peekTrim.startsWith("- ")) {
          items.push(unquote(peekTrim.slice(2)));
          j++;
          continue;
        }
        if (peekTrim === "") {
          j++;
          continue;
        }
        break;
      }
      if (items.length > 0) {
        out.push({ key, array: items });
        i = j;
        continue;
      }
      out.push({ key, scalar: "" });
      i++;
      continue;
    }
    if (rest.startsWith("[") && rest.endsWith("]")) {
      const inner = rest.slice(1, -1).trim();
      const items = inner ? inner.split(",").map((p) => unquote(p)) : [];
      out.push({ key, array: items.filter(Boolean) });
      i++;
      continue;
    }
    out.push({ key, scalar: unquote(rest) });
    i++;
  }
  return out;
}

function relationFrom(
  field: string,
  raw: string,
): FrontmatterRelation | null {
  const rel = FIELD_TO_RELATION[field];
  if (!rel) return null;
  const target = raw.trim();
  if (!target) return null;
  return { relationType: rel, target, raw };
}

/**
 * Parse frontmatter block + emit typed relations per spec §5 table.
 *
 * Returns [] when the doc has no frontmatter.
 */
export function extractFrontmatterRelations(
  content: string,
): FrontmatterRelation[] {
  const block = extractFrontmatterBlock(content);
  if (!block) return [];
  const fields = parseFrontmatterFields(block);
  const out: FrontmatterRelation[] = [];
  for (const f of fields) {
    if (!(f.key in FIELD_TO_RELATION)) continue;
    if (f.array) {
      for (const v of f.array) {
        const rel = relationFrom(f.key, v);
        if (rel) out.push(rel);
      }
    } else if (f.scalar !== undefined && f.scalar !== "") {
      const rel = relationFrom(f.key, f.scalar);
      if (rel) out.push(rel);
    }
  }
  return out;
}

/**
 * Variant for callers that already parsed YAML (e.g. via gray-matter elsewhere
 * in the pipeline). Object values may be string | string[].
 */
export function extractFrontmatterRelationsFromObject(
  data: Record<string, unknown>,
): FrontmatterRelation[] {
  const out: FrontmatterRelation[] = [];
  for (const [k, v] of Object.entries(data)) {
    if (!(k in FIELD_TO_RELATION)) continue;
    if (Array.isArray(v)) {
      for (const item of v) {
        if (typeof item !== "string") continue;
        const rel = relationFrom(k, item);
        if (rel) out.push(rel);
      }
    } else if (typeof v === "string") {
      const rel = relationFrom(k, v);
      if (rel) out.push(rel);
    }
  }
  return out;
}
