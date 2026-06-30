-- T5 — viewer_telemetry migration v20
--
-- Records SSE viewer sessions: one row per (client_id, connection).
-- Additive — runs cleanly on existing v19 schemas. No drop / rename.
--
-- Apply idempotently: every CREATE uses IF NOT EXISTS so re-running is safe.

BEGIN;

CREATE TABLE IF NOT EXISTS viewer_telemetry (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id           TEXT    NOT NULL,
  ts_start            TEXT    NOT NULL,
  ts_last_event       TEXT,
  ts_end              TEXT,
  events_consumed     INTEGER NOT NULL DEFAULT 0,
  events_dropped      INTEGER NOT NULL DEFAULT 0,
  remote_label        TEXT,
  -- Optional fields for future analytics (kept nullable).
  user_agent_major    TEXT,
  protocol_version    INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_viewer_telemetry_client_id
  ON viewer_telemetry(client_id);

CREATE INDEX IF NOT EXISTS idx_viewer_telemetry_ts_start
  ON viewer_telemetry(ts_start);

-- For "active sessions" queries (ts_end IS NULL).
CREATE INDEX IF NOT EXISTS idx_viewer_telemetry_active
  ON viewer_telemetry(ts_end)
  WHERE ts_end IS NULL;

-- Bump user_version. NOTE: if not 19, leave alone (caller migration runner
-- checks bounds before running). Conditional assignment via PRAGMA is N/A
-- in pure SQL — runner enforces upgrade ordering.
PRAGMA user_version = 20;

COMMIT;
