-- v11-rollback.sql — reverses v11.sql (telemetry tables)
-- Safe to run: telemetry tables have NO FK references from other tables
-- After rollback: user_version returns to 10

BEGIN;

DROP TABLE IF EXISTS provider_telemetry;
DROP TABLE IF EXISTS agent_events;
DROP TABLE IF EXISTS answer_telemetry;

PRAGMA user_version = 10;

COMMIT;
