-- v11.sql — telemetry tables (additive, no breaking changes)
-- Sprints: P1 (answer_telemetry), P2 (agent_events), A3 (provider_telemetry)
-- Depends on: schema v10 (retention_days + pain + section columns on chunks)
-- Apply with: withOpAudit() wrapper per CLAUDE.md rule #6

BEGIN;

PRAGMA foreign_keys = ON;

-- T1: answer_telemetry (P1 — per-query answer quality tracking)
CREATE TABLE IF NOT EXISTS answer_telemetry (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  question_hash       TEXT    NOT NULL,             -- sha256[:16] of question, NEVER raw text
  session_id          TEXT,
  timestamp_ms        INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  provider            TEXT    NOT NULL,             -- 'gemini' | 'openai' | 'anthropic'
  model               TEXT    NOT NULL,             -- 'gemini-2.5-flash-lite' default
  retrieval_count     INTEGER NOT NULL,
  citation_count      INTEGER NOT NULL,
  tokens_in           INTEGER,
  tokens_out          INTEGER,
  latency_ms          INTEGER NOT NULL,
  fallback_used       INTEGER NOT NULL DEFAULT 0,   -- BOOL (0/1)
  failed_reason       TEXT,                         -- 'hallucinated_citation' | 'provider_down' | 'token_budget' | NULL
  cost_estimate_usd   REAL    NOT NULL DEFAULT 0,
  CHECK (fallback_used IN (0, 1)),
  CHECK (failed_reason IN ('hallucinated_citation', 'provider_down', 'token_budget') OR failed_reason IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_answer_telemetry_ts      ON answer_telemetry(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_answer_telemetry_session ON answer_telemetry(session_id, timestamp_ms);

-- T2: agent_events (P2 — hook auto-capture for pre_compact / session lifecycle)
CREATE TABLE IF NOT EXISTS agent_events (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id       TEXT    NOT NULL,
  kind             TEXT    NOT NULL,                -- see CHECK below
  timestamp_ms     INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  payload_json     TEXT,                            -- JSON blob, NULL if fully redacted
  redaction_count  INTEGER NOT NULL DEFAULT 0,
  project          TEXT,
  retention_days   INTEGER NOT NULL DEFAULT 30,
  CHECK (kind IN ('tool_use', 'user_prompt', 'session_start', 'session_end', 'pre_compact'))
);
CREATE INDEX IF NOT EXISTS idx_agent_events_session  ON agent_events(session_id, timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_agent_events_kind_ts  ON agent_events(kind, timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_agent_events_project  ON agent_events(project, timestamp_ms);

-- T3: provider_telemetry (A3 — per-call cost + latency tracking per provider)
CREATE TABLE IF NOT EXISTS provider_telemetry (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp_ms      INTEGER NOT NULL DEFAULT (strftime('%s','now')*1000),
  provider          TEXT    NOT NULL,               -- 'gemini' | 'openai' | 'anthropic'
  model             TEXT    NOT NULL,
  op_type           TEXT    NOT NULL,               -- 'embed' | 'complete' | 'health_check'
  tokens_in         INTEGER,
  tokens_out        INTEGER,
  cost_estimate_usd REAL    NOT NULL DEFAULT 0,
  latency_ms        INTEGER NOT NULL,
  success           INTEGER NOT NULL DEFAULT 1,     -- BOOL (0/1)
  CHECK (op_type IN ('embed', 'complete', 'health_check')),
  CHECK (success IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_provider_telemetry_ts       ON provider_telemetry(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_provider_telemetry_provider ON provider_telemetry(provider, timestamp_ms);

PRAGMA user_version = 11;

COMMIT;
