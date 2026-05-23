-- shadow-tracker-schema.sql — F10 Phase D shadow tracker
--
-- Append-only persistence layer for shadow-mode comparisons.
-- Each row is one comparison between a baseline result-set and a shadow result-set
-- for a given feature (e.g. "temporal-spike-v2", "salience-v2", "tier-boost").
--
-- Design principles:
--   - Append-only: DELETE and UPDATE are blocked by triggers (parallel to ops_audit
--     append-only design in A1 op-audit module).
--   - Storage is the source of truth for long-tail aggregation; the in-process
--     ring buffer is a 24h fast cache for the dashboard endpoint.
--   - JSON `metadata` lets callers stash arbitrary per-feature payload (e.g. rank
--     diffs, top-k ids) without schema churn.
--
-- Spec: docs/ROADMAP.md F10 Phase D + memory [[shadow-mode-for-ranking-changes]].
-- Cross-link: src/lib/shadow-tracker.ts (writes), api-server.shadow-wire-up.md (reads).

CREATE TABLE IF NOT EXISTS shadow_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,                  -- Epoch ms when the comparison was recorded
  feature TEXT NOT NULL,                -- Feature name (e.g. "temporal-spike-v2")
  query_hash TEXT NOT NULL,             -- Stable hash of the query text (privacy-preserving)
  baseline_value REAL,                  -- Scalar metric for baseline (e.g. nDCG@10)
  shadow_value REAL,                    -- Scalar metric for shadow
  delta_pct REAL,                       -- (shadow - baseline) / baseline * 100; null if baseline=0
  metadata TEXT,                        -- JSON: { metric_name, baseline_ids, shadow_ids, ranking_diff, ... }
  CHECK (ts >= 0),
  CHECK (length(feature) > 0),
  CHECK (length(query_hash) > 0)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
-- Time-window scans for the /api/observability/shadow endpoint.
CREATE INDEX IF NOT EXISTS idx_shadow_runs_ts
  ON shadow_runs (ts);

-- Per-feature time-window scans (most common dashboard query: pick a feature, last 24h).
CREATE INDEX IF NOT EXISTS idx_shadow_runs_feature_ts
  ON shadow_runs (feature, ts);

-- ── Append-only triggers ──────────────────────────────────────────────────────
-- Mirrors ops_audit pattern (W2-1 trigger CWE-693) — DELETE/UPDATE are aborted.
-- Rationale: shadow comparisons are research evidence; rewriting them post-hoc
-- would invalidate any rollout decision derived from the audit trail.

CREATE TRIGGER IF NOT EXISTS trg_shadow_runs_block_delete
BEFORE DELETE ON shadow_runs
BEGIN
  SELECT RAISE(ABORT, 'shadow_runs is append-only: DELETE blocked');
END;

CREATE TRIGGER IF NOT EXISTS trg_shadow_runs_block_update
BEFORE UPDATE ON shadow_runs
BEGIN
  SELECT RAISE(ABORT, 'shadow_runs is append-only: UPDATE blocked');
END;
