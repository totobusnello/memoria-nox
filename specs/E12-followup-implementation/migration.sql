-- E12-followup migration: requesting_agent column for cross-agent retrieval quantification
-- Idempotent: SQLite ignores the ALTER if column already exists (try/catch in shell script)
-- Zero-downtime: ALTER TABLE ADD COLUMN acquires no write lock beyond the schema change itself
-- Schema user_version intentionally unchanged (no retrieval/scoring change per spec §3.3)

ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;

-- Backfill: historical rows carry NULL after migration.
-- 'unknown' simplifies Q2-Q6 GROUP BY aggregations in cross_agent_quantifier.py.
-- Single UPDATE on tens-of-thousands of rows completes in <1s — no chunking needed.
UPDATE search_telemetry SET requesting_agent = 'unknown' WHERE requesting_agent IS NULL;

-- Validation — expected: all rows now have requesting_agent NOT NULL
SELECT
  COUNT(*) AS total_rows,
  COUNT(requesting_agent) AS rows_with_agent,
  COUNT(*) - COUNT(requesting_agent) AS still_null
FROM search_telemetry;
