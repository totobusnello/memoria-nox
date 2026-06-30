/**
 * L2 T5 — Audit writer (append-only).
 *
 * - `recordConflict(db, conflict, evidence?)` — INSERT new audit row.
 *   Idempotency: skips when an OPEN row already exists for the same
 *   (subject_entity_id, predicate) — the v21 schema lets us use the partial
 *   index `idx_conflict_audit_open` for a fast existence check.
 *
 * - `updateConflictStatus(db, id, resolution)` — UPDATE status + resolution
 *   columns ONLY. Raw conflict data (kind/subject/predicate/target_relation_ids/
 *   variants/ts) is immutable per the v21 triggers. Status transitions
 *   matching a terminal-row reopen are blocked by trigger
 *   `trg_conflict_audit_no_reopen`.
 *
 * Regra de ouro #2 (v1 NEVER mutates kg_relations) is honored — this module
 * touches conflict_audit only.
 */

import type { DBHandle } from "./db.js";
import type {
  Conflict,
  ConflictAuditRow,
  ConflictEvidence,
  ConflictStatus,
  ResolutionInput,
  VariantRelation,
} from "./types.js";

const INSERT_SQL = `
  INSERT INTO conflict_audit (kind, subject_entity_id, predicate, target_relation_ids, variants, status, shadow_mode)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`.trim();

const UPDATE_SQL = `
  UPDATE conflict_audit
  SET status = ?, resolution_kind = ?, resolved_by = ?, resolved_at = ?, picked_relation_id = ?, merge_target = ?, notes = ?
  WHERE id = ?
`.trim();

const EXISTS_OPEN_SQL = `
  SELECT id FROM conflict_audit
  WHERE subject_entity_id = ? AND predicate = ? AND status = ?
  LIMIT 1
`.trim();

const GET_BY_ID_SQL = `SELECT * FROM conflict_audit WHERE id = ?`;

const LIST_BY_STATUS_SQL = `SELECT * FROM conflict_audit WHERE status = ? LIMIT 500`;

const COUNT_BY_STATUS_SQL = `SELECT status, COUNT(*) AS count FROM conflict_audit GROUP BY status`;

export interface RecordResult {
  /** New row id on insert, existing row id on dedupe. */
  id: number;
  /** True when an existing open row was found and INSERT skipped. */
  deduplicated: boolean;
}

export interface RecordOptions {
  /** Default 1 (shadow). Pass 0 to record an "active" row. */
  shadow_mode?: 0 | 1;
  /** Default 'open'. Use 'reviewed' for batch import workflows that mark seen. */
  initial_status?: Extract<ConflictStatus, "open" | "reviewed">;
  /** When true, skip the dedupe pre-check and always insert. */
  force?: boolean;
}

export function recordConflict(
  db: DBHandle,
  conflict: Conflict,
  evidence: ConflictEvidence | null = null,
  opts: RecordOptions = {},
): RecordResult {
  const shadowMode = opts.shadow_mode ?? 1;
  const status = opts.initial_status ?? "open";

  if (!opts.force) {
    const existing = db
      .prepare(EXISTS_OPEN_SQL)
      .get(conflict.subject_entity_id, conflict.predicate, "open") as
      | { id: number }
      | undefined;
    if (existing) {
      return { id: Number(existing.id), deduplicated: true };
    }
  }

  const targetIds = conflict.variants.map((v) => v.relation_id);
  const variantsJson = JSON.stringify(
    enrichVariantsWithEvidence(conflict.variants, evidence),
  );

  const res = db
    .prepare(INSERT_SQL)
    .run(
      conflict.kind,
      conflict.subject_entity_id,
      conflict.predicate,
      JSON.stringify(targetIds),
      variantsJson,
      status,
      shadowMode,
    );

  return { id: Number(res.lastInsertRowid), deduplicated: false };
}

export function updateConflictStatus(
  db: DBHandle,
  id: number,
  resolution: ResolutionInput,
): void {
  const now = Date.now();
  const picked = resolution.picked_relation_id ?? null;
  const merge = resolution.merge_target ?? null;
  const notes = resolution.notes ?? null;

  // Defensive validation — picked_relation_id required for pick_one.
  if (resolution.resolution_kind === "pick_one" && picked == null) {
    throw new Error(
      "pick_one resolution requires picked_relation_id (got null/undefined)",
    );
  }
  if (resolution.resolution_kind === "merged" && (merge == null || merge === "")) {
    throw new Error("merged resolution requires non-empty merge_target");
  }

  // Trigger trg_conflict_audit_no_reopen will block invalid transitions.
  db.prepare(UPDATE_SQL).run(
    resolution.status,
    resolution.resolution_kind,
    resolution.resolved_by,
    now,
    picked,
    merge,
    notes,
    id,
  );
}

export function getConflictById(
  db: DBHandle,
  id: number,
): ConflictAuditRow | null {
  const row = db.prepare(GET_BY_ID_SQL).get(id) as Record<string, unknown> | undefined;
  if (!row) return null;
  return rowToAudit(row);
}

export function listConflicts(
  db: DBHandle,
  status: ConflictStatus = "open",
  limit = 50,
): ConflictAuditRow[] {
  const safeLimit = Math.max(1, Math.min(500, limit));
  const sql = `SELECT * FROM conflict_audit WHERE status = ? LIMIT ${safeLimit}`;
  const rows = db.prepare(sql).all(status) as Record<string, unknown>[];
  return rows.map(rowToAudit);
}

/** Aggregate counts by status — used by shadow telemetry. */
export function statusCounts(db: DBHandle): Record<ConflictStatus, number> {
  const empty: Record<ConflictStatus, number> = {
    open: 0,
    reviewed: 0,
    resolved_pick_one: 0,
    resolved_both_valid: 0,
    resolved_merged: 0,
    dismissed: 0,
  };
  const rows = db.prepare(COUNT_BY_STATUS_SQL).all() as Array<{
    status: string;
    count: number;
  }>;
  for (const r of rows) {
    if (r.status in empty) {
      empty[r.status as ConflictStatus] = Number(r.count);
    }
  }
  return empty;
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

function enrichVariantsWithEvidence(
  variants: VariantRelation[],
  evidence: ConflictEvidence | null,
): unknown[] {
  if (!evidence) return variants;
  const byId = new Map<number, VariantRelation>();
  for (const v of variants) byId.set(v.relation_id, v);
  return evidence.variants.map((ve) => ({
    ...ve.variant,
    evidence_chunks: ve.chunks,
    weighted_score: ve.weighted_score,
  }));
}

function rowToAudit(row: Record<string, unknown>): ConflictAuditRow {
  const trIds = row.target_relation_ids;
  const variants = row.variants;
  return {
    id: Number(row.id),
    ts: Number(row.ts),
    kind: row.kind as ConflictAuditRow["kind"],
    subject_entity_id: Number(row.subject_entity_id),
    predicate: String(row.predicate),
    target_relation_ids: typeof trIds === "string" ? JSON.parse(trIds) : (trIds as number[]) ?? [],
    variants: typeof variants === "string" ? JSON.parse(variants) : (variants as unknown[]) as VariantRelation[] ?? [],
    status: row.status as ConflictStatus,
    resolved_by: (row.resolved_by as string | null) ?? null,
    resolved_at: row.resolved_at == null ? null : Number(row.resolved_at),
    resolution_kind: (row.resolution_kind as ConflictAuditRow["resolution_kind"]) ?? null,
    picked_relation_id: row.picked_relation_id == null ? null : Number(row.picked_relation_id),
    merge_target: (row.merge_target as string | null) ?? null,
    notes: (row.notes as string | null) ?? null,
    shadow_mode: (Number(row.shadow_mode) === 0 ? 0 : 1) as 0 | 1,
  };
}
