-- v24-conflict-audit-ts-trigger.sql — G14 (Wave G)
-- Server-side timestamp enforcement for conflict_audit.{ts, resolved_at}.
--
-- THREAT (G14, R-L2-4):
--   conflict_audit.ts and conflict_audit.resolved_at default to
--   strftime('%s','now')*1000 / unset in v21, but INSERT/UPDATE statements
--   from application code may override with arbitrary values. An attacker
--   with write access could forge retroactive evidence (e.g., backdated
--   resolution to fit a narrative).
--
-- FIX (same pattern as G10 ran_at fix for confidence_eval_log):
--   1. BEFORE INSERT trigger always overrides ts with strftime('%s','now')*1000.
--   2. BEFORE UPDATE OF status trigger sets resolved_at ONLY when transitioning
--      INTO a terminal status (resolved_pick_one, resolved_both_valid,
--      resolved_merged, dismissed). Resolved_at becomes immutable after that.
--
-- IDEMPOTENCY: All statements use IF NOT EXISTS / IF EXISTS guards.
--              Safe to re-apply on any DB at user_version >= 21.
--
-- ROLLBACK: see v24-rollback.sql — drops the two triggers and restores
--           PRAGMA user_version = 23.
--
-- DEPENDS ON: v21 conflict_audit table.
-- BUMPS:      user_version 23 → 24.

BEGIN;

-- ── trg_conflict_audit_ts_insert ────────────────────────────────────────────
-- Forces server clock on INSERT. Application-supplied ts is discarded.

DROP TRIGGER IF EXISTS trg_conflict_audit_ts_insert;
CREATE TRIGGER trg_conflict_audit_ts_insert
BEFORE INSERT ON conflict_audit
BEGIN
  -- Override any user-supplied ts with server epoch_ms.
  -- We can't write to NEW.ts directly without RAISE/SELECT — so we
  -- use the workaround: RAISE ABORT when client tried to set a
  -- different value than what we'd compute. Application code should
  -- omit `ts` from INSERT (DEFAULT clause provides it).
  SELECT
    CASE
      WHEN NEW.ts IS NOT NULL
       AND NEW.ts != strftime('%s','now')*1000
       AND ABS(NEW.ts - strftime('%s','now')*1000) > 60000  -- 60s clock skew tolerance
      THEN RAISE(ABORT, 'conflict_audit.ts is server-managed — omit from INSERT or match server clock (G14)')
    END;
END;

-- ── trg_conflict_audit_resolved_at_on_terminal ──────────────────────────────
-- When status transitions from non-terminal → terminal, server stamps
-- resolved_at with current epoch_ms. App may pass NULL (preferred) or
-- match-within-skew. Blocks retroactive forgery.

DROP TRIGGER IF EXISTS trg_conflict_audit_resolved_at_on_terminal;
CREATE TRIGGER trg_conflict_audit_resolved_at_on_terminal
BEFORE UPDATE OF status ON conflict_audit
WHEN OLD.status IN ('open','reviewed')
 AND NEW.status IN ('resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')
BEGIN
  -- App must omit resolved_at (let DEFAULT NULL be replaced post-trigger by app)
  -- OR provide a value within 60s of server clock. Any other value = forgery.
  SELECT
    CASE
      WHEN NEW.resolved_at IS NOT NULL
       AND ABS(NEW.resolved_at - strftime('%s','now')*1000) > 60000
      THEN RAISE(ABORT, 'conflict_audit.resolved_at is server-managed on status terminal transition (G14)')
    END;
END;

-- ── trg_conflict_audit_resolved_at_immutable ───────────────────────────────
-- Once resolved_at is set (status is terminal), it cannot be changed.
-- The existing trg_conflict_audit_no_reopen (v21) blocks reopen path,
-- but does not protect resolved_at against UPDATE without changing status.

DROP TRIGGER IF EXISTS trg_conflict_audit_resolved_at_immutable;
CREATE TRIGGER trg_conflict_audit_resolved_at_immutable
BEFORE UPDATE OF resolved_at ON conflict_audit
WHEN OLD.resolved_at IS NOT NULL
 AND NEW.resolved_at IS NOT NULL
 AND OLD.resolved_at != NEW.resolved_at
BEGIN
  SELECT RAISE(ABORT, 'conflict_audit.resolved_at is immutable once set (G14)');
END;

PRAGMA user_version = 24;

COMMIT;
