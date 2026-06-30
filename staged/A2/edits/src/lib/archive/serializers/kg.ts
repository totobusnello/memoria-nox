/**
 * T5 — KG serializer (entities + relations).
 *
 * Memory feedback `feedback_kg_relations_uses_fk_ids_not_inline_strings`:
 * relations use INTEGER FK ids referencing kg_entities.id. On merge, ids
 * collide between source and target DB; we therefore remap via (kind, slug)
 * which is the natural unique key. Relations whose endpoints can't be mapped
 * after merge are skipped with a warning (matches partial-export risk #16).
 */

import {
  ImportStats,
  KgEntityRow,
  KgRelationRow,
} from "../types.js";

const ENTITY_FIELDS: ReadonlyArray<keyof KgEntityRow> = [
  "id",
  "kind",
  "canonical_name",
  "slug",
  "aliases_json",
  "frontmatter_json",
  "updated_at",
];

const RELATION_FIELDS: ReadonlyArray<keyof KgRelationRow> = [
  "id",
  "source_entity_id",
  "target_entity_id",
  "predicate",
  "confidence",
  "metadata_json",
  "created_at",
];

export function serializeKgEntities(rows: Iterable<KgEntityRow>): Buffer {
  const lines: string[] = [];
  for (const row of rows) {
    const obj: Record<string, unknown> = {};
    for (const k of ENTITY_FIELDS) obj[k] = row[k];
    lines.push(JSON.stringify(obj));
  }
  return Buffer.from(lines.length > 0 ? lines.join("\n") + "\n" : "", "utf8");
}

export function parseKgEntities(buf: Buffer): KgEntityRow[] {
  const text = buf.toString("utf8");
  if (text.length === 0) return [];
  const out: KgEntityRow[] = [];
  for (const line of text.split("\n")) {
    if (line.length === 0) continue;
    const r = JSON.parse(line) as Record<string, unknown>;
    for (const field of ENTITY_FIELDS) {
      if (!(field in r)) {
        throw new Error(`kg_entities.jsonl missing field: ${field}`);
      }
    }
    out.push({
      id: r.id as number,
      kind: r.kind as string,
      canonical_name: r.canonical_name as string,
      slug: r.slug as string,
      aliases_json: r.aliases_json as string | null,
      frontmatter_json: r.frontmatter_json as string | null,
      updated_at: r.updated_at as string,
    });
  }
  return out;
}

export function serializeKgRelations(rows: Iterable<KgRelationRow>): Buffer {
  const lines: string[] = [];
  for (const row of rows) {
    const obj: Record<string, unknown> = {};
    for (const k of RELATION_FIELDS) obj[k] = row[k];
    lines.push(JSON.stringify(obj));
  }
  return Buffer.from(lines.length > 0 ? lines.join("\n") + "\n" : "", "utf8");
}

export function parseKgRelations(buf: Buffer): KgRelationRow[] {
  const text = buf.toString("utf8");
  if (text.length === 0) return [];
  const out: KgRelationRow[] = [];
  for (const line of text.split("\n")) {
    if (line.length === 0) continue;
    const r = JSON.parse(line) as Record<string, unknown>;
    for (const field of RELATION_FIELDS) {
      if (!(field in r)) {
        throw new Error(`kg_relations.jsonl missing field: ${field}`);
      }
    }
    out.push({
      id: r.id as number,
      source_entity_id: r.source_entity_id as number,
      target_entity_id: r.target_entity_id as number,
      predicate: r.predicate as string,
      confidence: r.confidence as number,
      metadata_json: r.metadata_json as string | null,
      created_at: r.created_at as string,
    });
  }
  return out;
}

export interface KgMergeResult {
  entities: ImportStats & { keep: KgEntityRow[] };
  relations: ImportStats & { keep: KgRelationRow[] };
}

/**
 * Plan KG merge: remap incoming entity ids via (kind, slug). For relations,
 * resolve FK ids from incoming → final via the entity remap. Relations whose
 * endpoints don't resolve are skipped + warned.
 */
export function planKgMerge(
  incomingEntities: KgEntityRow[],
  existingEntities: KgEntityRow[],
  incomingRelations: KgRelationRow[],
  existingRelations: KgRelationRow[],
): KgMergeResult {
  const entityWarnings: string[] = [];
  const relWarnings: string[] = [];

  // Index existing by (kind, slug) → id
  const existingKey = new Map<string, number>();
  for (const e of existingEntities) existingKey.set(`${e.kind}::${e.slug}`, e.id);

  // Allocate new ids for entities that aren't already present.
  let nextId = 1;
  for (const e of existingEntities) if (e.id >= nextId) nextId = e.id + 1;

  const remap = new Map<number, number>(); // incoming id → final id
  const finalEntities: KgEntityRow[] = [...existingEntities];
  let entInserted = 0;
  let entSkipped = 0;
  let entMerged = 0;
  for (const incoming of incomingEntities) {
    const key = `${incoming.kind}::${incoming.slug}`;
    const existingId = existingKey.get(key);
    if (existingId !== undefined) {
      remap.set(incoming.id, existingId);
      entMerged++;
      continue;
    }
    const newId = nextId++;
    remap.set(incoming.id, newId);
    finalEntities.push({ ...incoming, id: newId });
    existingKey.set(key, newId);
    entInserted++;
  }
  void entSkipped; // currently always 0; reserved for future conflict modes

  // Relations: existing kept as-is; incoming remapped.
  const finalRelations: KgRelationRow[] = [...existingRelations];
  const seenTuple = new Set<string>(
    existingRelations.map(
      (r) => `${r.source_entity_id}|${r.predicate}|${r.target_entity_id}`,
    ),
  );
  let nextRelId = 1;
  for (const r of existingRelations) if (r.id >= nextRelId) nextRelId = r.id + 1;
  let relInserted = 0;
  let relSkipped = 0;
  for (const r of incomingRelations) {
    const newSrc = remap.get(r.source_entity_id);
    const newTgt = remap.get(r.target_entity_id);
    if (newSrc === undefined || newTgt === undefined) {
      relWarnings.push(
        `Relation ${r.id} skipped: FK endpoint missing (src=${r.source_entity_id}, tgt=${r.target_entity_id})`,
      );
      relSkipped++;
      continue;
    }
    const tupleKey = `${newSrc}|${r.predicate}|${newTgt}`;
    if (seenTuple.has(tupleKey)) {
      relSkipped++;
      continue;
    }
    seenTuple.add(tupleKey);
    finalRelations.push({
      ...r,
      id: nextRelId++,
      source_entity_id: newSrc,
      target_entity_id: newTgt,
    });
    relInserted++;
  }

  return {
    entities: {
      inserted: entInserted,
      skipped: 0,
      merged: entMerged,
      warnings: entityWarnings,
      keep: finalEntities,
    },
    relations: {
      inserted: relInserted,
      skipped: relSkipped,
      merged: 0,
      warnings: relWarnings,
      keep: finalRelations,
    },
  };
}
