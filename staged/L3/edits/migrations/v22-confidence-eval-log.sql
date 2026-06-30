-- v22-confidence-eval-log.sql — adds confidence_eval_log table for L3 ablation runs.
-- Sprint: L3 (this is companion to schema v19 confidence + provenance columns).
-- Depends on: v19+ (confidence column on chunks).
-- Apply with: withOpAudit() wrapper per CLAUDE.md rule #6.
-- Schema-additive, idempotent (IF NOT EXISTS); safe to rerun.

BEGIN;

CREATE TABLE IF NOT EXISTS confidence_eval_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id            TEXT NOT NULL,                  -- arbitrary tag for grouping runs (e.g. '2026-05-25-ablation-1')
  query_id          TEXT NOT NULL,                  -- golden set id (e.g. 'Q-042')
  variant           TEXT NOT NULL
                    CHECK (variant IN ('A', 'B', 'C', 'D')),
  ndcg_at_10        REAL NOT NULL
                    CHECK (ndcg_at_10 >= 0),
  delta_vs_baseline REAL NOT NULL,                  -- nDCG@10 - baseline (variant A)
  ran_at            TEXT NOT NULL,                  -- ISO 8601
  notes             TEXT,                           -- optional free-text
  created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000)
);

CREATE INDEX IF NOT EXISTS idx_confidence_eval_log_run
  ON confidence_eval_log(run_id, variant);

CREATE INDEX IF NOT EXISTS idx_confidence_eval_log_query
  ON confidence_eval_log(query_id);

-- Append-only guard (mirrors ops_audit pattern from CLAUDE.md regra #6).
CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_no_delete
  BEFORE DELETE ON confidence_eval_log
  BEGIN
    SELECT RAISE(ABORT, 'confidence_eval_log is append-only');
  END;

CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_no_update
  BEFORE UPDATE ON confidence_eval_log
  BEGIN
    SELECT RAISE(ABORT, 'confidence_eval_log is append-only');
  END;

PRAGMA user_version = 22;

COMMIT;
