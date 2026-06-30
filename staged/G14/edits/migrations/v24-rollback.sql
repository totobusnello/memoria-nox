-- v24-rollback.sql — G14 rollback
-- Removes the three triggers introduced in v24 and restores user_version=23.
-- Safe to apply at user_version=24; no-op at user_version<24 (triggers will
-- silently not exist).

BEGIN;

DROP TRIGGER IF EXISTS trg_conflict_audit_ts_insert;
DROP TRIGGER IF EXISTS trg_conflict_audit_resolved_at_on_terminal;
DROP TRIGGER IF EXISTS trg_conflict_audit_resolved_at_immutable;

PRAGMA user_version = 23;

COMMIT;
