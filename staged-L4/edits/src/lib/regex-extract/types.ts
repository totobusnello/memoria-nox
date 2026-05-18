/**
 * L4 regex-extract — shared types.
 *
 * Cross-ref: specs/2026-05-18-L4-regex-first-extraction.md §4-§7.
 */

/** Whitelist of recognized entity types (DIR_PATTERN sources). */
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
  "entities", // top-level dir prefix in vault paths
] as const;

export type NoxEntityType = (typeof NOX_ENTITY_TYPES)[number];

/** A single extracted entity reference (markdown link / wikilink / bare). */
export interface EntityRef {
  /** Entity type bucket. */
  entityType: NoxEntityType;
  /** Slug (no extension, no fragment). */
  slug: string;
  /** Canonical key `<entityType>/<slug>` — dedup key. */
  key: string;
  /** Visible display text (markdown alt-text / wikilink pipe). */
  display?: string;
  /** Source pattern that matched. */
  source: "markdown_link" | "wikilink" | "bare_ref";
}

/** Frontmatter-derived typed relation (§5 table). */
export interface FrontmatterRelation {
  relationType:
    | "is_agent_of"
    | "references"
    | "supersedes"
    | "caused_by"
    | "resolves"
    | "decided_by";
  /** Target entity key `<entityType>/<slug>`; may be unqualified — caller resolves stub. */
  target: string;
  /** Raw field value from YAML for audit. */
  raw: string;
}

/** Code-path reference (e.g. `src/lib/op-audit.ts:42`). */
export interface CodeRef {
  /** Top-level dir (src, specs, audits, etc.). */
  root: string;
  /** Full path under root (e.g. `lib/op-audit.ts`). */
  path: string;
  /** Optional 1-based line number. */
  line?: number;
  /** Virtual entity key `codepath/<normalized_path>` for KG storage. */
  key: string;
}

/** Aggregated regex extraction result. */
export interface RegexExtractionResult {
  entityRefs: EntityRef[];
  frontmatterRelations: FrontmatterRelation[];
  codeRefs: CodeRef[];
  /** True when stripCodeBlocks removed at least one fence/inline span. */
  hadCodeFences: boolean;
}
