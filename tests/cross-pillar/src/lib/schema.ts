/**
 * Canonical cross-pillar test schema.
 *
 * Composes the staged migrations v11 (answer_telemetry + agent_events),
 * v19 (chunks confidence/provenance + kg_relations confidence/supersede/
 * temporal/extraction_method), v20 (viewer_telemetry), v21 (conflict_audit
 * + append-only triggers), v22 (confidence_eval_log) into a single CREATE
 * script. Mirrors the table shapes the real CLAUDE.md schema talks about,
 * but cut down to columns actually exercised by the 12 cross-pillar
 * scenarios.
 *
 * Real DB always — `better-sqlite3` `:memory:`. NO mocks per feedback
 * memory `validate_features_with_db_not_logs`.
 *
 * Why a unified schema (instead of importing each pillar's migration file):
 *   - Staged packages live under `staged-*` and aren't published as npm deps;
 *     cross-pillar tests must compose them without circular imports.
 *   - The cross-pillar surface is a contract test: it pins the shape every
 *     pillar relies on, so future breaking changes show up here loudly.
 */

import type { Database as DatabaseType } from "better-sqlite3";

export const CROSS_PILLAR_SCHEMA = `
-- ── chunks (v3.7 baseline + v10 section + v19 confidence/provenance) ────────
CREATE TABLE IF NOT EXISTS chunks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  content         TEXT    NOT NULL,
  content_hash    TEXT,
  source_path     TEXT,
  source_kind     TEXT,
  project         TEXT,
  created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT,
  retention_days  INTEGER,
  pain            REAL    DEFAULT 0.2,
  section         TEXT,
  section_boost   REAL,
  metadata_json   TEXT,
  -- v19
  confidence      REAL    DEFAULT 0.8 CHECK (confidence IS NULL OR (confidence BETWEEN 0.0 AND 1.0)),
  provenance_kind TEXT    CHECK (provenance_kind IN ('observed','declared','inferred','derived','user-marked') OR provenance_kind IS NULL),
  -- viewer / embed-provider
  embed_provider  TEXT,
  embed_dim       INTEGER,
  embedded_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_confidence
  ON chunks(confidence) WHERE confidence IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_provenance
  ON chunks(provenance_kind) WHERE provenance_kind IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_project_created
  ON chunks(project, created_at);

-- ── kg_entities ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kg_entities (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  kind           TEXT    NOT NULL,
  name           TEXT    NOT NULL,
  slug           TEXT,
  aliases_json   TEXT,
  frontmatter_json TEXT,
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_kg_entities_kind_slug
  ON kg_entities(kind, slug);

-- ── kg_relations (FK ids — per memory feedback) ─────────────────────────────
-- v19 columns inline: confidence + supersede chain + temporal + extraction_method
CREATE TABLE IF NOT EXISTS kg_relations (
  id                          INTEGER PRIMARY KEY AUTOINCREMENT,
  source_entity_id            INTEGER NOT NULL REFERENCES kg_entities(id),
  target_entity_id            INTEGER NOT NULL REFERENCES kg_entities(id),
  predicate                   TEXT    NOT NULL,
  evidence_chunk_id           INTEGER REFERENCES chunks(id),
  user_marked                 INTEGER NOT NULL DEFAULT 0,
  -- v19
  confidence                  REAL    DEFAULT 0.7 CHECK (confidence IS NULL OR (confidence BETWEEN 0.0 AND 1.0)),
  superseded_by_relation_id   INTEGER REFERENCES kg_relations(id) ON DELETE SET NULL,
  superseded_at               INTEGER,
  superseded_reason           TEXT    CHECK (superseded_reason IN ('auto_supersede_temporal','manual_resolution','stale_link_reconciliation','dismiss') OR superseded_reason IS NULL),
  created_at                  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  updated_at                  INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  extraction_method           TEXT    CHECK (extraction_method IN ('regex_only','gemini_only','regex_primary_gemini_secondary','frontmatter','manual') OR extraction_method IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_kg_relations_confidence
  ON kg_relations(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_kg_relations_subject_pred
  ON kg_relations(source_entity_id, predicate);
CREATE INDEX IF NOT EXISTS idx_kg_relations_superseded
  ON kg_relations(superseded_by_relation_id) WHERE superseded_by_relation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kg_relations_created
  ON kg_relations(created_at DESC);

-- ── ops_audit (W2-1 pattern, append-only, terminal-row immutable) ───────────
CREATE TABLE IF NOT EXISTS ops_audit (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  op              TEXT    NOT NULL,
  status          TEXT    NOT NULL DEFAULT 'started' CHECK (status IN ('started','success','failed','crashed')),
  started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  completed_at    TEXT,
  metadata_json   TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_ops_audit_no_delete
BEFORE DELETE ON ops_audit
BEGIN
  SELECT RAISE(ABORT, 'ops_audit is append-only — DELETE forbidden (CLAUDE.md rule #6)');
END;

-- Terminal rows cannot be UPDATEd (status can only transition started → terminal).
CREATE TRIGGER IF NOT EXISTS trg_ops_audit_terminal_immutable
BEFORE UPDATE OF status ON ops_audit
WHEN OLD.status IN ('success','failed','crashed')
BEGIN
  SELECT RAISE(ABORT, 'ops_audit terminal rows are immutable (CLAUDE.md rule #6)');
END;

-- ── v11: answer_telemetry (P1) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS answer_telemetry (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  question_hash       TEXT NOT NULL,
  session_id          TEXT,
  timestamp_ms        INTEGER NOT NULL,
  provider            TEXT NOT NULL,
  model               TEXT NOT NULL,
  retrieval_count     INTEGER NOT NULL,
  citation_count      INTEGER NOT NULL,
  tokens_in           INTEGER,
  tokens_out          INTEGER,
  latency_ms          INTEGER NOT NULL,
  fallback_used       INTEGER NOT NULL DEFAULT 0,
  failed_reason       TEXT,
  cost_estimate_usd   REAL NOT NULL DEFAULT 0,
  CHECK (failed_reason IS NULL OR failed_reason IN
         ('hallucinated_citation','provider_down','token_budget'))
);

-- ── v11: agent_events (P2 hooks telemetry) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uuid        TEXT    NOT NULL,
  session_id        TEXT    NOT NULL,
  project_slug      TEXT,
  kind              TEXT    NOT NULL,
  timestamp         TEXT    NOT NULL DEFAULT (datetime('now')),
  payload_json      TEXT    NOT NULL,
  redaction_count   INTEGER NOT NULL DEFAULT 0,
  retention_days    INTEGER NOT NULL DEFAULT 90,
  -- Privacy: explicit empty-content sentinel; pipeline NEVER writes raw content.
  content           TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_agent_events_session ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_kind ON agent_events(kind);

-- ── v20: viewer_telemetry (P5) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS viewer_telemetry (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id           TEXT    NOT NULL,
  ts_start            TEXT    NOT NULL,
  ts_last_event       TEXT,
  ts_end              TEXT,
  events_consumed     INTEGER NOT NULL DEFAULT 0,
  events_dropped      INTEGER NOT NULL DEFAULT 0,
  remote_label        TEXT,
  user_agent_major    TEXT,
  protocol_version    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_viewer_telemetry_client_id
  ON viewer_telemetry(client_id);

-- ── v21: conflict_audit (L2) ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conflict_audit (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                   INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  kind                 TEXT    NOT NULL CHECK (kind IN ('direct','temporal_supersede','value_drift','multi_target')),
  subject_entity_id    INTEGER NOT NULL,
  predicate            TEXT    NOT NULL,
  target_relation_ids  TEXT    NOT NULL,
  variants             TEXT,
  status               TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewed','resolved_pick_one','resolved_both_valid','resolved_merged','dismissed')),
  resolved_by          TEXT,
  resolved_at          INTEGER,
  resolution_kind      TEXT    CHECK (resolution_kind IN ('pick_one','both_valid','merged','dismissed') OR resolution_kind IS NULL),
  picked_relation_id   INTEGER,
  merge_target         TEXT,
  notes                TEXT,
  shadow_mode          INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_conflict_audit_open
  ON conflict_audit(status) WHERE status = 'open';

CREATE TRIGGER IF NOT EXISTS trg_conflict_audit_no_delete
BEFORE DELETE ON conflict_audit
BEGIN
  SELECT RAISE(ABORT, 'conflict_audit is append-only — DELETE forbidden');
END;

-- ── v22: confidence_eval_log (L3) ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS confidence_eval_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  query_id          TEXT    NOT NULL,
  variant           TEXT    NOT NULL CHECK (variant IN ('A','B','C','D')),
  ndcg_at_10        REAL    NOT NULL,
  delta_vs_baseline REAL    NOT NULL,
  ran_at            TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_confidence_eval_query
  ON confidence_eval_log(query_id);
`;

/**
 * Apply the full cross-pillar schema to a fresh better-sqlite3 Database.
 * Throws clearly on any CREATE failure so test failures point at the schema,
 * not at the test under test.
 */
export function applySchema(db: DatabaseType): void {
  try {
    db.exec(CROSS_PILLAR_SCHEMA);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(
      `cross-pillar schema apply failed: ${msg}\n` +
        `If a real staged migration changed, update tests/cross-pillar/src/lib/schema.ts.`
    );
  }
}
