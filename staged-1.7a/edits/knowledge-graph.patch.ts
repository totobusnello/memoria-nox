/**
 * staged-1.7a/edits/knowledge-graph.patch.ts
 *
 * audit #20 fix — Adds `previewMergeEntities()` to knowledge-graph.ts (VPS:
 * /root/.openclaw/workspace/tools/nox-mem/src/knowledge-graph.ts). This is a
 * **patch file** documenting the new export — apply by appending the function
 * below to the existing knowledge-graph.ts, and ensure the `mergeEntities`
 * function shares the same canonicalization logic.
 *
 * Deploy steps in staged-1.7a/DEPLOY-AUDIT20-FIXES.md.
 *
 * Why a patch file (not full replacement):
 *   The knowledge-graph.ts on VPS has ~1500 LOC of graph build, query, prune,
 *   decision-versioning logic. This audit #20 fix only adds a preview helper.
 *   Replacing the full file risks drift.
 *
 * Expected callsite (already wired in staged-1.7a/edits/index.ts kg-merge):
 *   if (opts.dryRun) {
 *     const { previewMergeEntities } = await import("./knowledge-graph.js");
 *     const preview = previewMergeEntities();
 *     ...
 *   }
 */

import { getDb } from "./db.js";

/** Normalize entity name for grouping — same logic as mergeEntities(). */
function canonicalize(name: string): string {
  return name.toLowerCase().trim().replace(/\s+/g, " ");
}

export interface MergePreview {
  wouldMerge: number;
  groups: Array<{
    canonical: string;
    entity_type: string;
    survivor_id: number;
    duplicates: number;
    member_names: string[];
  }>;
}

/**
 * Preview kg-merge without mutating. Returns groups that WOULD be merged.
 * Used by `nox-mem kg-merge --dry-run`.
 */
export function previewMergeEntities(): MergePreview {
  const db = getDb();
  const entities = db.prepare(
    "SELECT id, name, entity_type FROM kg_entities ORDER BY id ASC",
  ).all() as Array<{ id: number; name: string; entity_type: string }>;

  // Group by (canonical, entity_type). Survivor = lowest id in group.
  const groups = new Map<string, {
    canonical: string;
    entity_type: string;
    survivor_id: number;
    members: Array<{ id: number; name: string }>;
  }>();

  for (const e of entities) {
    const canon = canonicalize(e.name);
    const key = `${canon}::${e.entity_type}`;
    const existing = groups.get(key);
    if (existing) {
      existing.members.push({ id: e.id, name: e.name });
      if (e.id < existing.survivor_id) existing.survivor_id = e.id;
    } else {
      groups.set(key, {
        canonical: canon,
        entity_type: e.entity_type,
        survivor_id: e.id,
        members: [{ id: e.id, name: e.name }],
      });
    }
  }

  const merge_groups = Array.from(groups.values())
    .filter((g) => g.members.length > 1)
    .map((g) => ({
      canonical: g.canonical,
      entity_type: g.entity_type,
      survivor_id: g.survivor_id,
      duplicates: g.members.length - 1,
      member_names: g.members.map((m) => m.name),
    }));

  return {
    wouldMerge: merge_groups.reduce((acc, g) => acc + g.duplicates, 0),
    groups: merge_groups,
  };
}
