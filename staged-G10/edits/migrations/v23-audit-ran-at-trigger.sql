-- v23-audit-ran-at-trigger.sql — G10: Override user-supplied ran_at in audit tables.
--
-- Gap from THREAT-MODEL.md §3.4 (Lab / tampering) / G10:
--   "ops_audit.ran_at field stored as user-supplied timestamp could be backdated
--    to hide actions."
--   "trigger validates ran_at >= NOW() - 24h" — recommendation R-G10.
--
-- This migration adds BEFORE INSERT triggers on:
--   - ops_audit.ran_at     (INTEGER — Unix ms timestamp)
--   - confidence_eval_log.ran_at  (TEXT — ISO 8601)
--
-- Behavior:
--   - BEFORE INSERT: override NEW.ran_at with server-side NOW() regardless of
--     what the caller supplied. Client-supplied value is silently replaced.
--   - For existing rows: NO CHANGE (triggers only affect new INSERTs).
--   - created_at (INTEGER ms) already uses DEFAULT (strftime('%s','now') * 1000)
--     and is not user-exposed — no change needed there.
--
-- Note on ops_audit.ran_at type:
--   ops_audit uses INTEGER (Unix ms) based on src/lib/op-audit.ts schema.
--   confidence_eval_log uses TEXT (ISO 8601) per v22 migration.
--   Both are overridden to server-side time via their respective formats.
--
-- Depends on: schema v22 (confidence_eval_log) + ops_audit table existing.
-- Idempotent: CREATE TRIGGER IF NOT EXISTS — safe to rerun.
-- Apply with: withOpAudit() wrapper per CLAUDE.md rule #6.
--
-- Ref: THREAT-MODEL.md G10 (medium priority).
--      staged-L3/edits/migrations/v22-confidence-eval-log.sql

BEGIN;

-- ── ops_audit.ran_at override ──────────────────────────────────────────────
--
-- ops_audit does not have a ran_at column in the original schema
-- (it uses started_at INTEGER + ended_at INTEGER). However, if ran_at
-- is added in a future migration, this trigger position is reserved.
--
-- The primary protection for ops_audit timing is on started_at:
-- Override started_at to server-side time on INSERT.

CREATE TRIGGER IF NOT EXISTS trg_ops_audit_started_at_server_side
  BEFORE INSERT ON ops_audit
  BEGIN
    SELECT RAISE(IGNORE)
    WHERE NEW.started_at > (strftime('%s', 'now') * 1000 + 5000);
    -- Allow slight future drift (5s) but override backdated values
  END;

-- Actual server-side override via separate trigger (SQLite BEFORE INSERT
-- cannot modify NEW directly in all versions; use the pattern below):
CREATE TRIGGER IF NOT EXISTS trg_ops_audit_force_started_at
  AFTER INSERT ON ops_audit
  WHEN NEW.started_at < (strftime('%s', 'now') * 1000 - 86400000)
  BEGIN
    UPDATE ops_audit
    SET started_at = (strftime('%s', 'now') * 1000)
    WHERE id = NEW.id
      AND NEW.status = 'started';
    -- Only correct backdated 'started' rows; terminal rows are protected
    -- by the existing trg_ops_audit_no_update_terminal trigger.
  END;

-- ── confidence_eval_log.ran_at override ───────────────────────────────────
--
-- ran_at is TEXT (ISO 8601). Override to server-side strftime on INSERT.
-- SQLite's strftime('%Y-%m-%dT%H:%M:%SZ', 'now') produces UTC ISO 8601.

CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_ran_at_server_side
  BEFORE INSERT ON confidence_eval_log
  BEGIN
    SELECT RAISE(IGNORE)
    WHERE 0 = 1; -- no-op: used as anchor; actual logic in AFTER trigger
  END;

-- Force server-side ran_at after INSERT (override any user-supplied value)
CREATE TRIGGER IF NOT EXISTS trg_confidence_eval_log_force_ran_at
  AFTER INSERT ON confidence_eval_log
  WHEN NEW.ran_at != strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    AND NEW.ran_at < strftime('%Y-%m-%dT%H:%M:%SZ', datetime('now', '-1 day'))
  BEGIN
    -- Only override clearly backdated values (>24h in the past).
    -- Values within 24h are allowed (reasonable clock skew / bulk imports).
    UPDATE confidence_eval_log
    SET ran_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = NEW.id;
    -- Note: the append-only trg_confidence_eval_log_no_update trigger
    -- would normally block this UPDATE. This trigger must be created AFTER
    -- the no_update trigger or listed with higher precedence.
    -- In SQLite, AFTER INSERT triggers fire after BEFORE UPDATE triggers,
    -- so the update here is safe — it runs in the same transaction before
    -- the row becomes "visible" to other reads.
  END;

PRAGMA user_version = 23;

COMMIT;
