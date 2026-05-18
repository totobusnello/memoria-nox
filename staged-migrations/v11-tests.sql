-- v11-tests.sql — validation queries for v11.sql migration
-- Run AFTER applying v11.sql. All SELECTs should return non-empty / expected values.
-- Usage: sqlite3 /path/to/nox-mem.db < v11-tests.sql

-- ── 1. user_version must be 11 ───────────────────────────────────────────────
SELECT
  CASE WHEN user_version = 11 THEN 'PASS: user_version=11'
       ELSE 'FAIL: user_version=' || user_version END AS test_user_version
FROM pragma_user_version;

-- ── 2. All three tables must exist ──────────────────────────────────────────
SELECT
  CASE WHEN COUNT(*) = 3 THEN 'PASS: all 3 telemetry tables exist'
       ELSE 'FAIL: only ' || COUNT(*) || ' of 3 tables found — missing: ' ||
            GROUP_CONCAT(expected) END AS test_tables_exist
FROM (
  SELECT 'answer_telemetry'  AS expected UNION ALL
  SELECT 'agent_events'                  UNION ALL
  SELECT 'provider_telemetry'
) expected
WHERE expected IN (
  SELECT name FROM sqlite_master WHERE type='table'
);

-- ── 3. answer_telemetry — column presence ───────────────────────────────────
SELECT
  CASE WHEN COUNT(*) = 13 THEN 'PASS: answer_telemetry has 13 columns'
       ELSE 'FAIL: answer_telemetry column count=' || COUNT(*) END AS test_at_cols
FROM pragma_table_info('answer_telemetry');

-- ── 4. agent_events — kind CHECK constraint enforced ────────────────────────
-- Should fail (invalid kind) — catch the error externally or use try/except in harness
-- Uncomment to test manually:
-- INSERT INTO agent_events(session_id, kind) VALUES ('test', 'INVALID_KIND');

-- ── 5. provider_telemetry — op_type CHECK constraint ────────────────────────
-- Should fail (invalid op_type) — test manually:
-- INSERT INTO provider_telemetry(provider, model, op_type, latency_ms)
--   VALUES ('gemini', 'x', 'INVALID', 0);

-- ── 6. Sample insert + select — answer_telemetry ────────────────────────────
INSERT INTO answer_telemetry
  (question_hash, session_id, provider, model, retrieval_count, citation_count, latency_ms, fallback_used)
VALUES
  ('deadbeef1234abcd', 'test-session-v11', 'gemini', 'gemini-2.5-flash-lite', 5, 3, 420, 0);

SELECT
  CASE WHEN question_hash = 'deadbeef1234abcd' AND provider = 'gemini'
       THEN 'PASS: answer_telemetry insert+select OK'
       ELSE 'FAIL: answer_telemetry row mismatch' END AS test_at_insert
FROM answer_telemetry WHERE session_id = 'test-session-v11';

DELETE FROM answer_telemetry WHERE session_id = 'test-session-v11';

-- ── 7. Sample insert + select — agent_events ────────────────────────────────
INSERT INTO agent_events
  (session_id, kind, payload_json, project)
VALUES
  ('test-session-v11', 'session_start', '{"agent":"atlas"}', 'memoria-nox');

SELECT
  CASE WHEN kind = 'session_start' AND project = 'memoria-nox'
       THEN 'PASS: agent_events insert+select OK'
       ELSE 'FAIL: agent_events row mismatch' END AS test_ae_insert
FROM agent_events WHERE session_id = 'test-session-v11';

DELETE FROM agent_events WHERE session_id = 'test-session-v11';

-- ── 8. Sample insert + select — provider_telemetry ──────────────────────────
INSERT INTO provider_telemetry
  (provider, model, op_type, tokens_in, tokens_out, cost_estimate_usd, latency_ms, success)
VALUES
  ('gemini', 'gemini-2.5-flash-lite', 'embed', 512, 0, 0.000024, 230, 1);

SELECT
  CASE WHEN provider = 'gemini' AND op_type = 'embed' AND success = 1
       THEN 'PASS: provider_telemetry insert+select OK'
       ELSE 'FAIL: provider_telemetry row mismatch' END AS test_pt_insert
FROM provider_telemetry WHERE model = 'gemini-2.5-flash-lite' AND op_type = 'embed';

DELETE FROM provider_telemetry WHERE model = 'gemini-2.5-flash-lite' AND op_type = 'embed';

-- ── 9. Indexes present ───────────────────────────────────────────────────────
SELECT
  CASE WHEN COUNT(*) = 7 THEN 'PASS: all 7 v11 indexes present'
       ELSE 'FAIL: only ' || COUNT(*) || ' of 7 indexes found' END AS test_indexes
FROM sqlite_master
WHERE type = 'index'
  AND name IN (
    'idx_answer_telemetry_ts',
    'idx_answer_telemetry_session',
    'idx_agent_events_session',
    'idx_agent_events_kind_ts',
    'idx_agent_events_project',
    'idx_provider_telemetry_ts',
    'idx_provider_telemetry_provider'
  );
