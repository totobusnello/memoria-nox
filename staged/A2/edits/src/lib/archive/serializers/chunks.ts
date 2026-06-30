/**
 * T3 — Chunks serializer.
 *
 * JSONL one row per line. Preserves all schema v.29 columns:
 *   id, content, content_hash, source_path, source_kind, project,
 *   created_at, updated_at, retention_days, pain, section, section_boost,
 *   metadata_json
 *
 * Schema v.29 columns retention_days/pain/section/section_boost are MANDATORY
 * (CLAUDE.md §regra #6 — A2 reindex incident). Missing any of them = test fail.
 */

import { ChunkRow, ImportMode, ImportStats } from "../types.js";

const SCHEMA_FIELDS: ReadonlyArray<keyof ChunkRow> = [
  "id",
  "content",
  "content_hash",
  "source_path",
  "source_kind",
  "project",
  "created_at",
  "updated_at",
  "retention_days",
  "pain",
  "section",
  "section_boost",
  "metadata_json",
];

/** Serialize rows to a JSONL Buffer. */
export function serializeChunks(rows: Iterable<ChunkRow>): Buffer {
  const lines: string[] = [];
  for (const row of rows) {
    lines.push(serializeChunkRow(row));
  }
  return Buffer.from(lines.length > 0 ? lines.join("\n") + "\n" : "", "utf8");
}

/** Parse a JSONL Buffer back into rows. */
export function parseChunks(buf: Buffer): ChunkRow[] {
  const text = buf.toString("utf8");
  if (text.length === 0) return [];
  const rows: ChunkRow[] = [];
  for (const line of text.split("\n")) {
    if (line.length === 0) continue;
    rows.push(parseChunkRow(line));
  }
  return rows;
}

/** Single-row serializer. Stable key order matches SCHEMA_FIELDS. */
export function serializeChunkRow(row: ChunkRow): string {
  const obj: Record<string, unknown> = {};
  for (const k of SCHEMA_FIELDS) obj[k] = row[k];
  return JSON.stringify(obj);
}

export function parseChunkRow(line: string): ChunkRow {
  const raw = JSON.parse(line) as Record<string, unknown>;
  for (const field of SCHEMA_FIELDS) {
    if (!(field in raw)) {
      throw new Error(`chunks.jsonl row missing required field: ${field}`);
    }
  }
  return {
    id: raw.id as number,
    content: raw.content as string,
    content_hash: raw.content_hash as string,
    source_path: raw.source_path as string | null,
    source_kind: raw.source_kind as string | null,
    project: raw.project as string | null,
    created_at: raw.created_at as string,
    updated_at: raw.updated_at as string | null,
    retention_days: raw.retention_days as number | null,
    pain: raw.pain as number,
    section: raw.section as string | null,
    section_boost: raw.section_boost as number | null,
    metadata_json: raw.metadata_json as string | null,
  };
}

/**
 * In-memory import simulation. Used by tests + future DB-bound importer to
 * compute stats deterministically before hitting the DB.
 *
 * @param incoming new rows from archive
 * @param existing rows already in the DB (or empty for replace mode)
 * @param mode    merge dedups by content_hash; replace wipes existing first
 */
export function planChunkImport(
  incoming: ChunkRow[],
  existing: ChunkRow[],
  mode: ImportMode,
): ImportStats & { keep: ChunkRow[] } {
  const warnings: string[] = [];
  if (mode === "replace") {
    return {
      inserted: incoming.length,
      skipped: 0,
      merged: 0,
      warnings,
      keep: [...incoming],
    };
  }
  const existingByHash = new Map<string, ChunkRow>();
  for (const r of existing) existingByHash.set(r.content_hash, r);
  let inserted = 0;
  let skipped = 0;
  const keep: ChunkRow[] = [...existing];
  for (const row of incoming) {
    if (existingByHash.has(row.content_hash)) {
      skipped++;
      continue;
    }
    keep.push(row);
    existingByHash.set(row.content_hash, row);
    inserted++;
  }
  return { inserted, skipped, merged: 0, warnings, keep };
}
