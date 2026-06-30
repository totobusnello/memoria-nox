-- v21-rollback.sql — REVERSES v21-conflict-audit.sql
-- DESTRUCTIVE: drops conflict_audit table + all audit history. Run only with explicit snapshot.

BEGIN;

DROP TRIGGER IF EXISTS trg_conflict_audit_no_delete;
DROP TRIGGER IF EXISTS trg_conflict_audit_immutable_data;
DROP TRIGGER IF EXISTS trg_conflict_audit_no_reopen;

DROP INDEX IF EXISTS idx_conflict_audit_status_ts;
DROP INDEX IF EXISTS idx_conflict_audit_subject_predicate;
DROP INDEX IF EXISTS idx_conflict_audit_open;

DROP TABLE IF EXISTS conflict_audit;

PRAGMA user_version = 19;

COMMIT;
