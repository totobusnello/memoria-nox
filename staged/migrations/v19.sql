-- v19.sql — confidence + provenance columns (additive, no breaking changes)
-- Sprints: L3 (chunks.confidence + provenance_kind), L2 (kg_relations confidence + supersession + temporal), L4 (extraction_method)
-- Depends on: schema v11+ (telemetry tables must exist)
-- Apply with: withOpAudit() wrapper per CLAUDE.md rule #6
-- NOTE: user_version jumps 11→19; versions 12-18 are reserved for other overnight sprints

BEGIN;

-- L3: chunks — confidence score + provenance_kind
-- confidence: 0.8 default (calibrated baseline for existing chunks)
-- provenance_kind: NULL default (legacy chunks have no provenance metadata)
ALTER TABLE chunks ADD COLUMN confidence      REAL DEFAULT 0.8 CHECK (confidence IS NULL OR (confidence BETWEEN 0.0 AND 1.0));
ALTER TABLE chunks ADD COLUMN provenance_kind TEXT             CHECK (provenance_kind IN ('observed', 'declared', 'inferred', 'derived', 'user-marked') OR provenance_kind IS NULL);

-- L2: kg_relations — confidence + supersession chain + temporal tracking
-- confidence: 0.7 default (slightly lower baseline than chunks — relations are harder to verify)
ALTER TABLE kg_relations ADD COLUMN confidence              REAL    DEFAULT 0.7 CHECK (confidence IS NULL OR (confidence BETWEEN 0.0 AND 1.0));
ALTER TABLE kg_relations ADD COLUMN superseded_by_relation_id INTEGER REFERENCES kg_relations(id) ON DELETE SET NULL;
ALTER TABLE kg_relations ADD COLUMN superseded_at           INTEGER;  -- epoch_ms, NULL = not superseded
ALTER TABLE kg_relations ADD COLUMN superseded_reason       TEXT      CHECK (superseded_reason IN ('auto_supersede_temporal', 'manual_resolution', 'stale_link_reconciliation', 'dismiss') OR superseded_reason IS NULL);

-- Temporal tracking (all existing rows get current time as default)
ALTER TABLE kg_relations ADD COLUMN created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000);
ALTER TABLE kg_relations ADD COLUMN updated_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000);

-- L4: extraction_method — regex-first pipeline tracking
ALTER TABLE kg_relations ADD COLUMN extraction_method TEXT CHECK (extraction_method IN ('regex_only', 'gemini_only', 'regex_primary_gemini_secondary', 'frontmatter', 'manual') OR extraction_method IS NULL);

-- Indexes for new kg_relations columns
CREATE INDEX IF NOT EXISTS idx_kg_relations_confidence  ON kg_relations(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_kg_relations_superseded  ON kg_relations(superseded_by_relation_id) WHERE superseded_by_relation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kg_relations_created     ON kg_relations(created_at DESC);

PRAGMA user_version = 19;

COMMIT;
