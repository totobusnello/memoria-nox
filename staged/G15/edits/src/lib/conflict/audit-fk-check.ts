/**
 * G15 — conflict_audit FK validation (Wave G)
 *
 * BACKGROUND
 *   `conflict_audit.target_relation_ids` is a JSON array of `kg_relations.id`
 *   values (string-encoded). The v21 schema explicitly chose to skip a hard
 *   foreign-key for cheap migration cost — but means INSERT accepts any
 *   integer, including non-existent FK ids ("dangling" audit rows).
 *
 *   Same risk applies to:
 *     - `picked_relation_id` (resolution: pick_one)
 *     - `subject_entity_id` (FK kg_entities.id)
 *
 * THREAT (G15, R-L2-2.1)
 *   Attacker (or buggy writer) inserts a row referencing a deleted/never-
 *   existed relation. Downstream `evidence.ts` then yields empty
 *   evidence — confusing analysts and breaking the audit chain.
 *
 * FIX
 *   1. Validation function `validateConflictAuditFK(db, conflict)` — runs the
 *      check ahead of any INSERT/UPDATE; returns the list of missing ids
 *      (empty = pass). Caller (audit-writer.ts) decides to reject or warn.
 *   2. Plus a CHECK constraint addendum SQL (v25 migration) that enforces
 *      JSON shape — array of positive integers. Existence check must remain
 *      in code (SQLite CHECK can't reach across tables in pre-3.x SQLite
 *      and is brittle even with FK pragma).
 *
 * Backward compat:
 *   - Function is opt-in — caller can wrap audit-writer.ts INSERT_SQL with
 *     a pre-flight call.
 *   - JSON shape CHECK is additive; rolls back via v25-rollback.sql.
 */

export interface ConflictAuditFKInput {
  subject_entity_id: number;
  target_relation_ids: number[];
  /** Optional. Only validated when present (resolution path). */
  picked_relation_id?: number | null;
}

export interface FKValidationResult {
  valid: boolean;
  /** subject_entity_id missing in kg_entities? */
  missingSubject: boolean;
  /** Subset of target_relation_ids not found in kg_relations. */
  missingRelationIds: number[];
  /** True if picked_relation_id was supplied and not found. */
  missingPicked: boolean;
}

export interface DBHandleMinimal {
  prepare: (sql: string) => {
    all: (...params: unknown[]) => Array<{ id: number }>;
    get: (...params: unknown[]) => unknown;
  };
}

/**
 * Run all FK existence checks for a conflict_audit row. Pure read-only.
 *
 * Performance: O(1) prepared statements; single query per category.
 * No `IN (?, ?, ...)` placeholder explosion — uses `json_each` instead.
 */
export function validateConflictAuditFK(
  db: DBHandleMinimal,
  input: ConflictAuditFKInput,
): FKValidationResult {
  // 1. subject_entity_id check.
  const subjectRow = db
    .prepare("SELECT id FROM kg_entities WHERE id = ?")
    .get(input.subject_entity_id);
  const missingSubject = !subjectRow;

  // 2. target_relation_ids — bulk existence query.
  const targets = input.target_relation_ids ?? [];
  let missingRelationIds: number[] = [];
  if (targets.length > 0) {
    const idsJson = JSON.stringify(targets);
    const existing = db
      .prepare(
        "SELECT kr.id AS id FROM kg_relations kr WHERE kr.id IN (SELECT value FROM json_each(?))",
      )
      .all(idsJson) as Array<{ id: number }>;
    const existingSet = new Set(existing.map((r) => r.id));
    missingRelationIds = targets.filter((id) => !existingSet.has(id));
  }

  // 3. picked_relation_id (resolution path).
  let missingPicked = false;
  if (
    input.picked_relation_id !== undefined &&
    input.picked_relation_id !== null
  ) {
    const row = db
      .prepare("SELECT id FROM kg_relations WHERE id = ?")
      .get(input.picked_relation_id);
    missingPicked = !row;
  }

  return {
    valid: !missingSubject && missingRelationIds.length === 0 && !missingPicked,
    missingSubject,
    missingRelationIds,
    missingPicked,
  };
}

/**
 * Drop-in helper for audit-writer.ts. Throws a structured Error on FK
 * miss so the caller can `try/catch` and map to a 4xx.
 */
export class ConflictAuditFKError extends Error {
  readonly result: FKValidationResult;
  constructor(result: FKValidationResult) {
    super(
      `conflict_audit FK validation failed: ${JSON.stringify({
        missingSubject: result.missingSubject,
        missingRelationIds: result.missingRelationIds,
        missingPicked: result.missingPicked,
      })}`,
    );
    this.name = "ConflictAuditFKError";
    this.result = result;
  }
}

export function assertConflictAuditFK(
  db: DBHandleMinimal,
  input: ConflictAuditFKInput,
): void {
  const r = validateConflictAuditFK(db, input);
  if (!r.valid) throw new ConflictAuditFKError(r);
}

// ── SQL addendum: JSON shape CHECK (optional v25 migration) ────────────────
//
// SQLite CHECK constraint can verify that `target_relation_ids` parses as a
// JSON array of positive integers. Existence checks remain code-side.
//
// This SQL is exported as a string so callers can compose it into a future
// v25 migration if desired. Not auto-applied here (additive, opt-in).

export const JSON_SHAPE_CHECK_SQL = `
-- v25-conflict-audit-json-shape.sql (G15 addendum)
-- Adds a CHECK constraint to conflict_audit.target_relation_ids guaranteeing
-- the column is a non-empty JSON array of positive integers.
--
-- SQLite limitation: ALTER TABLE ADD CONSTRAINT is unsupported, so this
-- ships as a trigger instead (BEFORE INSERT/UPDATE OF target_relation_ids).

BEGIN;

DROP TRIGGER IF EXISTS trg_conflict_audit_target_relation_ids_shape;
CREATE TRIGGER trg_conflict_audit_target_relation_ids_shape
BEFORE INSERT ON conflict_audit
BEGIN
  SELECT
    CASE
      WHEN json_valid(NEW.target_relation_ids) = 0
       OR json_type(NEW.target_relation_ids) != 'array'
       OR (
            SELECT COUNT(*)
              FROM json_each(NEW.target_relation_ids)
             WHERE typeof(value) != 'integer' OR value <= 0
          ) > 0
       OR (SELECT COUNT(*) FROM json_each(NEW.target_relation_ids)) = 0
      THEN RAISE(ABORT, 'conflict_audit.target_relation_ids must be a non-empty JSON array of positive integers (G15)')
    END;
END;

PRAGMA user_version = 25;

COMMIT;
`;
