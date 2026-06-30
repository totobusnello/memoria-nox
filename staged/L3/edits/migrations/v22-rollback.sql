-- v22-rollback.sql — drops confidence_eval_log table.
-- Schema-additive rollback: safe because no other table FKs into this one.

BEGIN;

DROP TRIGGER IF EXISTS trg_confidence_eval_log_no_delete;
DROP TRIGGER IF EXISTS trg_confidence_eval_log_no_update;
DROP INDEX IF EXISTS idx_confidence_eval_log_run;
DROP INDEX IF EXISTS idx_confidence_eval_log_query;
DROP TABLE IF EXISTS confidence_eval_log;

PRAGMA user_version = 19;  -- rollback to pre-v22 (v19 confidence cols stay)

COMMIT;
