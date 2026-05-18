/**
 * T7 — Stale-link reconciliation on entity file update.
 *
 * When an entity file is renamed or edited, links pointing to the old slug may
 * become stale. This module handles two modes:
 *
 *  - stale-mark (default): sets `confidence` to STALE_CONFIDENCE + adds a
 *    `superseded_by` pointer to the new slug in each affected relation.
 *  - auto-rename (env `NOX_L4_AUTO_RENAME=1`): rewrites old slug → new slug
 *    across all affected kg_relations records.
 *
 * CRITICAL: auto-rename is DESTRUCTIVE — must require explicit env opt-in.
 * Default is stale-mark (append-only philosophy per CLAUDE.md regra 6).
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §8.
 */

import { extractEntityRefsRegex } from "./extractor.js";
import { extractFrontmatterRelations } from "./frontmatter.js";
import { extractCodeRefs } from "./extractor.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Confidence assigned to stale relations (low — known stale). */
export const STALE_CONFIDENCE = 0.3;

/**
 * Reason string written to superseded_reason when stale-marking a relation.
 * Matches the reason used in the stale-link reconciliation flow (spec §8).
 */
export const STALE_REASON = "stale_link_reconciliation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A single KG relation as seen by the reconciler (minimal projection). */
export interface ReconcilerRelation {
  /** Composite key identifying this relation: `<sourceSlug>|<targetSlug>|<relationType>`. */
  key: string;
  /** Source entity slug (e.g. `feedback/no_secrets`). */
  sourceSlug: string;
  /** Target entity slug (e.g. `decision/d41`). */
  targetSlug: string;
  /** Relation type label. */
  relationType: string;
  /** Extraction method tag (only regex-extracted rels are managed by this reconciler). */
  extraction_method: "regex" | "gemini" | string;
  /** Current confidence score (0.0-1.0). */
  confidence: number;
  /** Whether already superseded. */
  superseded?: boolean;
}

/** Discriminated reconciliation action. */
export type ReconcileAction =
  | {
      type: "mark_stale";
      relation: ReconcilerRelation;
      /** New confidence value written (STALE_CONFIDENCE). */
      newConfidence: number;
      /** Reason written to superseded_reason. */
      supersededReason: string;
    }
  | {
      type: "auto_rename";
      relation: ReconcilerRelation;
      /** Old target slug being replaced. */
      oldTargetSlug: string;
      /** New target slug replacing the old one. */
      newTargetSlug: string;
    }
  | {
      type: "add";
      /** New target slug extracted from updated content. */
      targetSlug: string;
      relationType: string;
    }
  | {
      type: "noop";
      targetSlug: string;
    };

/** Full reconciliation result. */
export interface ReconcileResult {
  actions: ReconcileAction[];
  /** Relations newly found (adds). */
  added: string[];
  /** Relations removed from active content (marked stale or auto-renamed). */
  removed: string[];
  /** Relations unchanged. */
  unchanged: string[];
  /** Operating mode used. */
  mode: "stale_mark" | "auto_rename";
}

// ---------------------------------------------------------------------------
// Content → slug set extraction
// ---------------------------------------------------------------------------

/**
 * Derive the full set of target slugs found in `content` via regex extraction
 * (entity refs + frontmatter relations combined). Code refs are excluded from
 * reconciliation — they're not direct KG entity slugs.
 */
export function extractTargetSlugsFromContent(content: string): Set<string> {
  const slugs = new Set<string>();
  for (const ref of extractEntityRefsRegex(content)) {
    slugs.add(ref.key); // already `<entityType>/<slug>`
  }
  for (const rel of extractFrontmatterRelations(content)) {
    const tgt = rel.target.trim();
    if (tgt) slugs.add(tgt);
  }
  return slugs;
}

// ---------------------------------------------------------------------------
// Core reconciliation logic
// ---------------------------------------------------------------------------

export interface ReconcileOptions {
  /**
   * If true, auto-rename is enabled (env `NOX_L4_AUTO_RENAME=1`).
   * Default: false (stale-mark mode).
   *
   * CRITICAL: auto-rename rewrites relations in-place. Never default to true.
   */
  autoRename?: boolean;
  /**
   * When autoRename=true and the old slug has been replaced by a known new
   * slug, pass it here so the auto-rename action can record the mapping.
   * If not provided, stale-mark is used even in auto-rename mode.
   */
  newSlug?: string;
}

/**
 * Reconcile kg_relations for a given entity when its content changes.
 *
 * Algorithm (spec §8):
 *  1. Extract new target slugs from `newContent` via regex.
 *  2. Diff `existingRelations` vs new slug set:
 *     - Added: in new set, not in existing → emit `add` action.
 *     - Removed: in existing (regex_extracted only), not in new set → emit
 *       `mark_stale` or `auto_rename` action.
 *     - Unchanged: present in both → emit `noop`.
 *  3. Gemini relations (extraction_method='gemini') are NEVER touched —
 *     deferred to next Gemini run.
 *  4. Already-superseded relations are skipped.
 *
 * @param sourceSlug     The entity being reconciled (e.g. `feedback/no_secrets`).
 * @param newContent     New markdown content of the entity file.
 * @param existingRelations  Current `kg_relations` rows for this entity.
 * @param opts           Reconcile options.
 */
export function reconcileEntityLinks(
  sourceSlug: string,
  newContent: string,
  existingRelations: ReconcilerRelation[],
  opts: ReconcileOptions = {},
): ReconcileResult {
  const autoRename = opts.autoRename === true;
  const newSlug = opts.newSlug?.trim() ?? "";
  const mode: ReconcileResult["mode"] = autoRename && newSlug
    ? "auto_rename"
    : "stale_mark";

  // Derive new target slug set from updated content.
  const newTargetSlugs = extractTargetSlugsFromContent(newContent);

  // Build lookup of existing REGEX-extracted (active) relations by target slug.
  const existingByTarget = new Map<string, ReconcilerRelation>();
  for (const rel of existingRelations) {
    if (rel.extraction_method !== "regex") continue; // only manage regex rels
    if (rel.superseded) continue; // skip already-superseded
    existingByTarget.set(rel.targetSlug, rel);
  }

  const actions: ReconcileAction[] = [];
  const added: string[] = [];
  const removed: string[] = [];
  const unchanged: string[] = [];

  // Check new slugs: adds vs noops.
  for (const tgtSlug of newTargetSlugs) {
    if (existingByTarget.has(tgtSlug)) {
      actions.push({ type: "noop", targetSlug: tgtSlug });
      unchanged.push(tgtSlug);
    } else {
      actions.push({
        type: "add",
        targetSlug: tgtSlug,
        relationType: "regex_extracted",
      });
      added.push(tgtSlug);
    }
  }

  // Check removed: existing regex rels not in new set.
  for (const [tgtSlug, rel] of existingByTarget) {
    if (newTargetSlugs.has(tgtSlug)) continue; // handled above

    if (mode === "auto_rename" && newSlug) {
      actions.push({
        type: "auto_rename",
        relation: rel,
        oldTargetSlug: tgtSlug,
        newTargetSlug: newSlug,
      });
    } else {
      actions.push({
        type: "mark_stale",
        relation: rel,
        newConfidence: STALE_CONFIDENCE,
        supersededReason: STALE_REASON,
      });
    }
    removed.push(tgtSlug);
  }

  return { actions, added, removed, unchanged, mode };
}

// ---------------------------------------------------------------------------
// Rename detection helper
// ---------------------------------------------------------------------------

/**
 * Detect whether an entity slug has changed between two content snapshots by
 * comparing the `slug` frontmatter field (or the first heading). Returns the
 * detected new slug if different, null if no change detected.
 *
 * This is a lightweight heuristic — the definitive source is the filesystem
 * rename event from the watcher. Use this as a sanity check.
 */
export function detectSlugChange(
  oldContent: string,
  newContent: string,
): { changed: boolean; oldSlug: string | null; newSlug: string | null } {
  const extractSlugHint = (content: string): string | null => {
    // Try frontmatter `slug:` field first.
    const fm = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (fm) {
      const slugMatch = fm[1]?.match(/^slug:\s*([^\r\n]+)/m);
      if (slugMatch) return slugMatch[1]?.trim() ?? null;
    }
    // Fallback: first H1.
    const h1 = content.match(/^#\s+(.+)$/m);
    if (h1) return h1[1]?.trim() ?? null;
    return null;
  };

  const oldSlug = extractSlugHint(oldContent);
  const newSlug = extractSlugHint(newContent);
  const changed =
    oldSlug !== null && newSlug !== null && oldSlug !== newSlug;
  return { changed, oldSlug, newSlug };
}

// ---------------------------------------------------------------------------
// Multi-file reconciliation (rename cascade)
// ---------------------------------------------------------------------------

/**
 * Apply auto-rename across a set of chunk texts that reference `oldSlug`.
 * Rewrites `oldSlug` → `newSlug` in:
 *  - Markdown links `[label](oldSlug)`
 *  - Wikilinks `[[oldSlug]]`
 *  - Bare refs ` oldSlug ` (boundary-sensitive)
 *
 * Returns an array of results: `{ chunkId, original, rewritten, changed }`.
 *
 * CRITICAL: Only call when `NOX_L4_AUTO_RENAME=1`. The caller is responsible
 * for writing the rewritten texts back to the DB.
 */
export interface ChunkRewriteResult {
  chunkId: string;
  original: string;
  rewritten: string;
  changed: boolean;
}

export function rewriteChunksForRename(
  chunks: Array<{ chunkId: string; content: string }>,
  oldSlug: string,
  newSlug: string,
): ChunkRewriteResult[] {
  if (!oldSlug || !newSlug || oldSlug === newSlug) {
    return chunks.map((c) => ({
      chunkId: c.chunkId,
      original: c.content,
      rewritten: c.content,
      changed: false,
    }));
  }

  const escaped = oldSlug.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // Rewrite markdown links: [label](path/to/oldSlug) → [label](path/to/newSlug)
  const mdLinkRe = new RegExp(
    `(\\[[^\\]]*\\]\\()([^)]*?)\\b${escaped}\\b([^)]*)\\)`,
    "g",
  );

  // Rewrite wikilinks: [[oldSlug]] → [[newSlug]] (including anchors and pipes)
  const wikilinkRe = new RegExp(
    `(\\[\\[)${escaped}((?:#[^|\\]\\n]*)?(?:\\|[^\\]\\n]*)?)(\\]\\])`,
    "g",
  );

  // Rewrite bare refs: anchored to word-like boundaries (avoid URLs)
  const bareRefRe = new RegExp(
    `(?<=^|[\\s(,;])${escaped}(?=$|[\\s).,?!;:])`,
    "gm",
  );

  return chunks.map((c) => {
    let rewritten = c.content;
    rewritten = rewritten.replace(mdLinkRe, `$1$2${newSlug}$3)`);
    rewritten = rewritten.replace(wikilinkRe, `$1${newSlug}$2$3`);
    rewritten = rewritten.replace(bareRefRe, newSlug);
    const changed = rewritten !== c.content;
    return { chunkId: c.chunkId, original: c.content, rewritten, changed };
  });
}

// ---------------------------------------------------------------------------
// Circular rename guard
// ---------------------------------------------------------------------------

/**
 * Validate a sequence of renames for circular dependencies.
 * Returns an error string if a cycle is detected, null otherwise.
 *
 * A cycle exists when following rename chain A→B→C→A.
 */
export function detectCircularRename(
  renames: Array<{ from: string; to: string }>,
): string | null {
  const edges = new Map<string, string>();
  for (const r of renames) {
    edges.set(r.from, r.to);
  }

  for (const start of edges.keys()) {
    const visited = new Set<string>();
    let cur: string | undefined = start;
    while (cur !== undefined) {
      if (visited.has(cur)) {
        return `Circular rename detected: ${Array.from(visited).join(" → ")} → ${cur}`;
      }
      visited.add(cur);
      cur = edges.get(cur);
    }
  }
  return null;
}
