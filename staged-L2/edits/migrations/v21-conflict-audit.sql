-- v21-conflict-audit.sql — L2 conflict detection audit table (additive, append-only)
-- Sprint: L2 (Wave C) — KG conflict / contradiction detection (memanto Gap #5 differentiator)
-- Depends on: schema v19+ (kg_relations confidence + supersession columns present)
-- Apply with: withOpAudit() wrapper per CLAUDE.md rule #6
-- NOTE: user_version jumps 19→20→21
--   - v20 is reserved (intentionally vacant; staged-migrations placeholder slot)
--   - v21 introduces conflict_audit + triggers
-- IDEMPOTENCY: All statements use IF NOT EXISTS / IF EXISTS guards. Safe to re-apply.

BEGIN;

-- ── conflict_audit: append-only ledger of detected KG contradictions ──────────
-- Mirrors ops_audit shape (CLAUDE.md rule #6) — terminal-row immutability
-- enforced via triggers (see below).
CREATE TABLE IF NOT EXISTS conflict_audit (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                   INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),  -- epoch_ms
  kind                 TEXT    NOT NULL CHECK (kind IN ('direct','temporal_supersede','value_drift','multi_target')),
  subject_entity_id    INTEGER NOT NULL,                                       -- FK kg_entities.id (no hard FK to keep migration cheap)
  predicate            TEXT    NOT NULL,
  target_relation_ids  TEXT    NOT NULL,                                       -- JSON array of kg_relations.id involved
  variants             TEXT,                                                   -- JSON array of {relation_id, target_entity_id, confidence, extraction_method, evidence_chunk_id, created_at}
  status               TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewed','resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')),
  resolved_by          TEXT,                                                   -- user id or 'system' or 'auto' (v1 never auto-resolves)
  resolved_at          INTEGER,                                                -- epoch_ms when status flipped terminal
  resolution_kind      TEXT    CHECK (resolution_kind IN ('pick_one','both_valid','merged','dismissed') OR resolution_kind IS NULL),
  picked_relation_id   INTEGER,                                                -- when resolution_kind='pick_one'
  merge_target         TEXT,                                                   -- when resolution_kind='merged' (new canonical target value)
  notes                TEXT,                                                   -- free-form analyst note
  shadow_mode          INTEGER NOT NULL DEFAULT 1                              -- 1=shadow (no ranking effect), 0=active
);

CREATE INDEX IF NOT EXISTS idx_conflict_audit_status_ts        ON conflict_audit(status, ts DESC);
CREATE INDEX IF NOT EXISTS idx_conflict_audit_subject_predicate ON conflict_audit(subject_entity_id, predicate);
CREATE INDEX IF NOT EXISTS idx_conflict_audit_open             ON conflict_audit(status) WHERE status = 'open';

-- ── Triggers: append-only enforcement (mirror ops_audit W2-1 pattern) ────────
-- CWE-693 mitigation: prevent tampering with the audit log.
-- DELETE is unconditionally blocked. UPDATE is restricted:
--   - allowed on (status, notes, resolved_by, resolved_at, resolution_kind,
--                 picked_relation_id, merge_target, shadow_mode)
--   - blocked on raw conflict data (kind, subject_entity_id, predicate,
--                                   target_relation_ids, variants, ts)
-- Additionally, terminal rows (resolved_*/dismissed) cannot have status
-- changed back to 'open' or 'reviewed'.

CREATE TRIGGER IF NOT EXISTS trg_conflict_audit_no_delete
BEFORE DELETE ON conflict_audit
BEGIN
  SELECT RAISE(ABORT, 'conflict_audit is append-only — DELETE forbidden (CLAUDE.md rule #6)');
END;

CREATE TRIGGER IF NOT EXISTS trg_conflict_audit_immutable_data
BEFORE UPDATE OF kind, subject_entity_id, predicate, target_relation_ids, variants, ts ON conflict_audit
BEGIN
  SELECT RAISE(ABORT, 'conflict_audit raw conflict data is immutable (CLAUDE.md rule #6)');
END;

CREATE TRIGGER IF NOT EXISTS trg_conflict_audit_no_reopen
BEFORE UPDATE OF status ON conflict_audit
WHEN OLD.status IN ('resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')
 AND NEW.status NOT IN ('resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')
BEGIN
  SELECT RAISE(ABORT, 'conflict_audit terminal rows cannot be reopened — create a new audit row instead');
END;

PRAGMA user_version = 21;

COMMIT;
