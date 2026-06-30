/**
 * T6 — ops_audit serializer.
 *
 * Append-only preservation per CLAUDE.md §regra #6 (W2-1 trigger CWE-693).
 * Importer NEVER deletes or updates existing rows; only appends. If incoming
 * id collides with an existing id, the row is re-assigned a fresh id
 * (preserving its content) to maintain the append-only invariant.
 *
 * Status enum is enforced: 'started' | 'success' | 'failed' | 'crashed'.
 * 'completed' and 'rolled_back' are NOT valid (CLAUDE.md §regra #6).
 */

import { ImportStats, OpsAuditRow } from "../types.js";

const FIELDS: ReadonlyArray<keyof OpsAuditRow> = [
  "id",
  "op",
  "status",
  "started_at",
  "completed_at",
  "metadata_json",
];

const VALID_STATUSES = new Set([
  "started",
  "success",
  "failed",
  "crashed",
]);

export function serializeOpsAudit(rows: Iterable<OpsAuditRow>): Buffer {
  const lines: string[] = [];
  for (const row of rows) {
    if (!VALID_STATUSES.has(row.status)) {
      throw new Error(
        `ops_audit row ${row.id} has invalid status: ${row.status}`,
      );
    }
    const obj: Record<string, unknown> = {};
    for (const k of FIELDS) obj[k] = row[k];
    lines.push(JSON.stringify(obj));
  }
  return Buffer.from(lines.length > 0 ? lines.join("\n") + "\n" : "", "utf8");
}

export function parseOpsAudit(buf: Buffer): OpsAuditRow[] {
  const text = buf.toString("utf8");
  if (text.length === 0) return [];
  const out: OpsAuditRow[] = [];
  for (const line of text.split("\n")) {
    if (line.length === 0) continue;
    const r = JSON.parse(line) as Record<string, unknown>;
    for (const f of FIELDS) {
      if (!(f in r)) {
        throw new Error(`ops_audit row missing field: ${f}`);
      }
    }
    const status = r.status as string;
    if (!VALID_STATUSES.has(status)) {
      throw new Error(`ops_audit row ${r.id} invalid status: ${status}`);
    }
    out.push({
      id: r.id as number,
      op: r.op as string,
      status: status as OpsAuditRow["status"],
      started_at: r.started_at as string,
      completed_at: r.completed_at as string | null,
      metadata_json: r.metadata_json as string | null,
    });
  }
  return out;
}

/**
 * Plan append-only merge. Existing rows preserved verbatim. Incoming rows
 * always appended; ids re-assigned on collision.
 */
export function planOpsAuditImport(
  incoming: OpsAuditRow[],
  existing: OpsAuditRow[],
): ImportStats & { keep: OpsAuditRow[] } {
  const warnings: string[] = [];
  const usedIds = new Set<number>(existing.map((r) => r.id));
  let nextId = 1;
  for (const r of existing) if (r.id >= nextId) nextId = r.id + 1;
  const keep: OpsAuditRow[] = [...existing];
  let inserted = 0;
  for (const row of incoming) {
    let id = row.id;
    if (usedIds.has(id)) {
      id = nextId++;
      warnings.push(`ops_audit id collision: incoming ${row.id} re-assigned ${id}`);
    } else if (id >= nextId) {
      nextId = id + 1;
    }
    keep.push({ ...row, id });
    usedIds.add(id);
    inserted++;
  }
  // Sort by id for deterministic output
  keep.sort((a, b) => a.id - b.id);
  return { inserted, skipped: 0, merged: 0, warnings, keep };
}
