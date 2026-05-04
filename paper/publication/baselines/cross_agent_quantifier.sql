-- =============================================================================
-- cross_agent_quantifier.sql
-- E12 — Cross-Agent Intelligence Quantification
-- nox-mem paper §5 — Diferencial #3: Shared-Canonical Multi-Agent Intelligence
--
-- USAGE: sqlite3 -readonly nox-mem.db < cross_agent_quantifier.sql
--        OR executed via cross_agent_quantifier.py (recommended — formats output)
--
-- ASSUMPTIONS:
--   1. source_file path patterns below cover the agent corpus. Chunks with
--      source_file matching none of the agent patterns fall into 'shared' or
--      'other'. Run Q1 first and inspect 'other' count — if >5% of total,
--      refine patterns before trusting Q2–Q5.
--   2. top_chunk_ids is a JSON TEXT array of INTEGER chunk IDs, e.g. "[12,45,3]".
--      Requires SQLite >= 3.38 (json_each available). Check: SELECT sqlite_version().
--   3. requesting_agent column does NOT exist in search_telemetry as of schema v12.
--      Q2–Q5 require it. Two paths:
--        A) Add migration (see cross_agent_quantifier.py --migrate flag) then
--           re-run searches so telemetry rows get populated.
--        B) If column is absent, Q2–Q5 emit a warning row and skip computation.
--      Threshold: Q2–Q5 are statistically reliable only with >= 100 telemetry
--      rows where both requesting_agent IS NOT NULL AND top_chunk_ids IS NOT NULL.
--      With < 100 rows, treat percentages as directional only.
--   4. golden_id FK references future eval_queries table (W2.1 harness). Q4 only
--      runs when golden_id IS NOT NULL rows exist in search_telemetry.
--   5. This file is split by the sentinel token at the end of each query block.
--      cross_agent_quantifier.py uses these to execute queries individually
--      and label their output.
--
-- RUNTIME ESTIMATE: < 5s on 64K chunks + < 10K telemetry rows (READ-ONLY).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- SHARED CTE: chunk_agent
-- Maps every chunk to its originating agent via source_file path patterns.
-- Used by Q2–Q5 via WITH clauses.
-- ---------------------------------------------------------------------------
-- (Defined inline per-query — SQLite does not support cross-statement CTEs.
--  Each query below is self-contained for sqlite3 CLI compatibility.)

-- ===========================================================================
-- Q1 — Chunk distribution by originating agent
-- Goal: Confirm corpus is genuinely multi-agent and quantify each agent share.
-- Paper target: mean ~10K chunks per agent across 6 agents.
-- ===========================================================================
WITH chunk_agent AS (
  SELECT
    id,
    CASE
      -- Agent-specific memory files (VPS canonical paths)
      WHEN source_file LIKE '%/agents/atlas/%'   OR source_file LIKE 'agents/atlas/%'   THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'   OR source_file LIKE 'agents/boris/%'   THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%'  OR source_file LIKE 'agents/cipher/%'  THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'   OR source_file LIKE 'agents/forge/%'   THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'     OR source_file LIKE 'agents/lex/%'     THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'     OR source_file LIKE 'agents/nox/%'     THEN 'nox'
      -- Entity files injected by each agent (memory/entities/<type>/<slug>)
      WHEN source_file LIKE '%/memory/entities/%' THEN 'shared'
      -- Project docs, specs, decisions — canonical shared knowledge
      WHEN source_file LIKE 'docs/%' OR source_file LIKE '%/docs/%' THEN 'shared'
      WHEN source_file LIKE 'specs/%' OR source_file LIKE '%/specs/%' THEN 'shared'
      -- Catch-all
      ELSE 'other'
    END AS origin_agent
  FROM chunks
),
totals AS (SELECT COUNT(*) AS grand_total FROM chunks)
SELECT
  ca.origin_agent,
  COUNT(*)                                                          AS chunk_count,
  ROUND(100.0 * COUNT(*) / t.grand_total, 2)                       AS pct_of_total,
  -- Counterfactual reference: isolated system would show 0 cross-agent surface
  CASE WHEN ca.origin_agent IN ('atlas','boris','cipher','forge','lex','nox')
       THEN 'agent-owned'
       ELSE 'cross-agent-eligible'
  END AS corpus_type
FROM chunk_agent ca, totals t
GROUP BY ca.origin_agent, t.grand_total
ORDER BY chunk_count DESC;
-- END --

-- ===========================================================================
-- Q2 — Cross-agent hit rate from search_telemetry (stratified by rank)
-- Goal: % of retrieved chunks that belong to a DIFFERENT agent than requester.
-- Requires: requesting_agent column in search_telemetry (schema migration A0+).
--           top_chunk_ids TEXT (JSON array, NOX_SEARCH_LOG_TEXT=1).
-- Stratified at rank 1, ranks 1-3, ranks 1-10.
-- ===========================================================================
WITH
-- Guard: emit warning if column or data missing
schema_check AS (
  SELECT
    (SELECT COUNT(*) FROM pragma_table_info('search_telemetry')
     WHERE name = 'requesting_agent')               AS has_requesting_agent,
    (SELECT COUNT(*) FROM pragma_table_info('search_telemetry')
     WHERE name = 'top_chunk_ids')                  AS has_top_chunk_ids,
    (SELECT COUNT(*) FROM search_telemetry
     WHERE requesting_agent IS NOT NULL
       AND top_chunk_ids IS NOT NULL)                AS eligible_rows
),
chunk_agent AS (
  SELECT
    id,
    CASE
      WHEN source_file LIKE '%/agents/atlas/%'  OR source_file LIKE 'agents/atlas/%'  THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'  OR source_file LIKE 'agents/boris/%'  THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%' OR source_file LIKE 'agents/cipher/%' THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'  OR source_file LIKE 'agents/forge/%'  THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'    OR source_file LIKE 'agents/lex/%'    THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'    OR source_file LIKE 'agents/nox/%'    THEN 'nox'
      WHEN source_file LIKE '%/memory/entities/%'
        OR source_file LIKE 'docs/%' OR source_file LIKE '%/docs/%'
        OR source_file LIKE 'specs/%' OR source_file LIKE '%/specs/%' THEN 'shared'
      ELSE 'other'
    END AS origin_agent
  FROM chunks
),
-- Explode top_chunk_ids JSON array → (query_id, rank_0based, chunk_id)
telemetry_expanded AS (
  SELECT
    st.id            AS query_id,
    st.requesting_agent,
    -- json_each: key is 0-based array index, value is chunk id
    CAST(je.key AS INTEGER) + 1   AS rank_pos,  -- 1-based rank
    CAST(je.value AS INTEGER)     AS chunk_id
  FROM search_telemetry st, json_each(st.top_chunk_ids) je
  WHERE st.requesting_agent IS NOT NULL
    AND st.top_chunk_ids IS NOT NULL
    AND st.top_chunk_ids != '[]'
    AND (SELECT has_requesting_agent FROM schema_check) = 1
),
-- Join with chunk origin
hits_with_origin AS (
  SELECT
    te.query_id,
    te.requesting_agent,
    te.rank_pos,
    te.chunk_id,
    COALESCE(ca.origin_agent, 'other') AS origin_agent,
    CASE
      WHEN COALESCE(ca.origin_agent, 'other') NOT IN ('shared','other')
        AND te.requesting_agent != COALESCE(ca.origin_agent, 'other')
      THEN 1 ELSE 0
    END AS is_cross_agent
  FROM telemetry_expanded te
  LEFT JOIN chunk_agent ca ON ca.id = te.chunk_id
)
SELECT
  sc.eligible_rows                                              AS telemetry_eligible_rows,
  -- Reliability flag: < 100 rows → directional only
  CASE WHEN sc.eligible_rows < 100 THEN 'LOW — directional only (<100 queries)'
       WHEN sc.eligible_rows < 500 THEN 'MEDIUM'
       ELSE 'HIGH'
  END                                                           AS reliability,
  ROUND(100.0 * SUM(CASE WHEN h.rank_pos = 1 THEN h.is_cross_agent END)
                / NULLIF(SUM(CASE WHEN h.rank_pos = 1 THEN 1 END), 0), 2)
                                                                AS cross_agent_pct_rank1,
  ROUND(100.0 * SUM(CASE WHEN h.rank_pos <= 3 THEN h.is_cross_agent END)
                / NULLIF(SUM(CASE WHEN h.rank_pos <= 3 THEN 1 END), 0), 2)
                                                                AS cross_agent_pct_top3,
  ROUND(100.0 * SUM(CASE WHEN h.rank_pos <= 10 THEN h.is_cross_agent END)
                / NULLIF(SUM(CASE WHEN h.rank_pos <= 10 THEN 1 END), 0), 2)
                                                                AS cross_agent_pct_top10,
  -- Counterfactual: isolated system = 0% by definition
  '0.00 (isolated baseline)'                                    AS counterfactual_cross_agent_pct
FROM hits_with_origin h, schema_check sc
GROUP BY sc.eligible_rows;
-- END --

-- ===========================================================================
-- Q3 — Cross-agent retrieval matrix (6×6)
-- Rows = requesting_agent, Cols = origin_agent of top-5 retrieved chunks.
-- Diagonal = self-retrieval; off-diagonal = actual cross-agent intelligence.
-- High off-diagonal values are the empirical evidence for Diferencial #3.
-- ===========================================================================
WITH
chunk_agent AS (
  SELECT
    id,
    CASE
      WHEN source_file LIKE '%/agents/atlas/%'  OR source_file LIKE 'agents/atlas/%'  THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'  OR source_file LIKE 'agents/boris/%'  THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%' OR source_file LIKE 'agents/cipher/%' THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'  OR source_file LIKE 'agents/forge/%'  THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'    OR source_file LIKE 'agents/lex/%'    THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'    OR source_file LIKE 'agents/nox/%'    THEN 'nox'
      ELSE 'shared_other'
    END AS origin_agent
  FROM chunks
),
telemetry_top5 AS (
  SELECT
    st.requesting_agent,
    CAST(je.value AS INTEGER) AS chunk_id
  FROM search_telemetry st, json_each(st.top_chunk_ids) je
  WHERE st.requesting_agent IS NOT NULL
    AND st.top_chunk_ids IS NOT NULL
    AND st.top_chunk_ids != '[]'
    AND (CAST(je.key AS INTEGER) + 1) <= 5   -- top-5 only
),
cell_counts AS (
  SELECT
    t.requesting_agent,
    COALESCE(ca.origin_agent, 'shared_other') AS origin_agent,
    COUNT(*) AS hit_count
  FROM telemetry_top5 t
  LEFT JOIN chunk_agent ca ON ca.id = t.chunk_id
  GROUP BY t.requesting_agent, COALESCE(ca.origin_agent, 'shared_other')
),
row_totals AS (
  SELECT requesting_agent, SUM(hit_count) AS row_total
  FROM cell_counts
  GROUP BY requesting_agent
)
SELECT
  cc.requesting_agent,
  cc.origin_agent,
  cc.hit_count,
  ROUND(100.0 * cc.hit_count / rt.row_total, 2)   AS pct_of_requester_hits,
  CASE WHEN cc.requesting_agent = cc.origin_agent
       THEN 'self-retrieval'
       ELSE 'cross-agent'
  END                                               AS retrieval_type
FROM cell_counts cc
JOIN row_totals rt ON rt.requesting_agent = cc.requesting_agent
-- Exclude shared_other from rows (only named agents as requesters)
WHERE cc.requesting_agent IN ('atlas','boris','cipher','forge','lex','nox')
ORDER BY cc.requesting_agent, cc.pct_of_requester_hits DESC;
-- END --

-- ===========================================================================
-- Q4 — Cross-agent quality parity (nDCG@10 proxy)
-- Goal: Show cross-agent hits do NOT degrade quality vs same-agent hits.
-- Requires: golden_id populated (W2.1 eval harness) + top_chunk_ids.
-- Proxy metric: rank of the golden chunk in top_chunk_ids (lower = better).
-- Real nDCG@10 = 1/log2(rank+1) when golden found, 0 otherwise.
-- If no golden_id rows exist, query returns empty with explanation row.
-- ===========================================================================
WITH
chunk_agent AS (
  SELECT
    id,
    CASE
      WHEN source_file LIKE '%/agents/atlas/%'  OR source_file LIKE 'agents/atlas/%'  THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'  OR source_file LIKE 'agents/boris/%'  THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%' OR source_file LIKE 'agents/cipher/%' THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'  OR source_file LIKE 'agents/forge/%'  THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'    OR source_file LIKE 'agents/lex/%'    THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'    OR source_file LIKE 'agents/nox/%'    THEN 'nox'
      ELSE 'shared_other'
    END AS origin_agent
  FROM chunks
),
-- Golden queries only (golden_id IS NOT NULL means W2.1 harness tagged them)
golden_telemetry AS (
  SELECT
    st.id         AS query_id,
    st.requesting_agent,
    st.golden_id,
    st.top_chunk_ids
  FROM search_telemetry st
  WHERE st.golden_id IS NOT NULL
    AND st.requesting_agent IS NOT NULL
    AND st.top_chunk_ids IS NOT NULL
),
-- For each golden query, find the rank of the golden chunk in top_chunk_ids
-- golden_id is a TEXT FK; cast to INTEGER for chunk id match
golden_ranks AS (
  SELECT
    gt.query_id,
    gt.requesting_agent,
    gt.golden_id,
    CAST(je.key AS INTEGER) + 1           AS rank_of_golden,   -- 1-based
    CAST(je.value AS TEXT)                AS retrieved_chunk_id_text
  FROM golden_telemetry gt, json_each(gt.top_chunk_ids) je
  WHERE CAST(je.value AS TEXT) = gt.golden_id
),
-- Compute nDCG@10 per query (0 if golden not found in top-10)
ndcg_per_query AS (
  SELECT
    gt.query_id,
    gt.requesting_agent,
    gt.golden_id,
    -- nDCG@1 approximation: 1/log2(rank+1) if found within 10, else 0
    CASE
      WHEN gr.rank_of_golden IS NOT NULL AND gr.rank_of_golden <= 10
      THEN 1.0 / (LOG(CAST(gr.rank_of_golden AS REAL) + 1.0) / LOG(2.0))
      ELSE 0.0
    END                                   AS ndcg_at10,
    gr.rank_of_golden,
    -- Is the top-1 hit cross-agent?
    (SELECT CASE
       WHEN COALESCE(ca2.origin_agent, 'shared_other') NOT IN ('shared_other')
         AND gt.requesting_agent != COALESCE(ca2.origin_agent, 'shared_other')
       THEN 'cross-agent'
       ELSE 'same-agent'
     END
     FROM json_each(gt.top_chunk_ids) je2
     LEFT JOIN chunk_agent ca2 ON ca2.id = CAST(je2.value AS INTEGER)
     WHERE CAST(je2.key AS INTEGER) = 0  -- rank 1 = index 0
     LIMIT 1)                            AS top1_type
  FROM golden_telemetry gt
  LEFT JOIN golden_ranks gr ON gr.query_id = gt.query_id
)
SELECT
  nq.top1_type,
  COUNT(*)                               AS query_count,
  ROUND(AVG(nq.ndcg_at10), 4)           AS mean_ndcg_at10,
  ROUND(MIN(nq.ndcg_at10), 4)           AS min_ndcg,
  ROUND(MAX(nq.ndcg_at10), 4)           AS max_ndcg,
  ROUND(AVG(CASE WHEN nq.ndcg_at10 > 0 THEN nq.ndcg_at10 END), 4)
                                         AS mean_ndcg_when_found,
  -- Delta: cross minus same (positive = cross-agent as good or better)
  '(computed by wrapper)'                AS delta_cross_vs_same,
  CASE WHEN COUNT(*) < 20
       THEN 'LOW — <20 golden queries; run W2.1 harness first'
       ELSE 'OK'
  END                                    AS reliability
FROM ndcg_per_query nq
GROUP BY nq.top1_type
ORDER BY nq.top1_type;
-- END --

-- ===========================================================================
-- Q5 — Top cross-agent flows (requester → origin pairs)
-- Goal: Identify dominant dependency patterns between agents.
-- Example interpretation: "forge→boris 31%" = Boris frequently uses Forge's
-- technical memory, revealing an operational dependency.
-- Only counts named agent → named agent flows (excludes shared/other origin).
-- ===========================================================================
WITH
chunk_agent AS (
  SELECT
    id,
    CASE
      WHEN source_file LIKE '%/agents/atlas/%'  OR source_file LIKE 'agents/atlas/%'  THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'  OR source_file LIKE 'agents/boris/%'  THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%' OR source_file LIKE 'agents/cipher/%' THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'  OR source_file LIKE 'agents/forge/%'  THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'    OR source_file LIKE 'agents/lex/%'    THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'    OR source_file LIKE 'agents/nox/%'    THEN 'nox'
      ELSE NULL
    END AS origin_agent
  FROM chunks
),
all_hits AS (
  SELECT
    st.requesting_agent,
    COALESCE(ca.origin_agent, NULL) AS origin_agent,
    COUNT(*) AS pair_hits
  FROM search_telemetry st, json_each(st.top_chunk_ids) je
  LEFT JOIN chunk_agent ca ON ca.id = CAST(je.value AS INTEGER)
  WHERE st.requesting_agent IS NOT NULL
    AND st.top_chunk_ids IS NOT NULL
    AND st.requesting_agent IN ('atlas','boris','cipher','forge','lex','nox')
    AND ca.origin_agent IS NOT NULL
    AND ca.origin_agent != st.requesting_agent   -- cross-agent ONLY
  GROUP BY st.requesting_agent, ca.origin_agent
),
requester_totals AS (
  SELECT requesting_agent, SUM(pair_hits) AS total_cross_hits
  FROM all_hits
  GROUP BY requesting_agent
)
SELECT
  ah.requesting_agent || ' → ' || ah.origin_agent   AS flow,
  ah.requesting_agent,
  ah.origin_agent,
  ah.pair_hits,
  ROUND(100.0 * ah.pair_hits / rt.total_cross_hits, 2)  AS pct_of_requester_cross_hits,
  -- Interpretation hint for paper
  CASE
    WHEN 100.0 * ah.pair_hits / rt.total_cross_hits >= 30
    THEN 'DOMINANT — strong operational dependency'
    WHEN 100.0 * ah.pair_hits / rt.total_cross_hits >= 15
    THEN 'SIGNIFICANT — notable cross-agent usage'
    ELSE 'MINOR'
  END AS interpretation
FROM all_hits ah
JOIN requester_totals rt ON rt.requesting_agent = ah.requesting_agent
ORDER BY ah.pair_hits DESC
LIMIT 10;
-- END --

-- ===========================================================================
-- Q6 — Counterfactual isolation simulation
-- Goal: Compute what recall coverage would look like in an isolated system
-- (each agent can only see its own chunks), vs the shared system.
-- Metric: for each golden query, is the correct chunk even REACHABLE by the
-- requesting agent in isolation? Reachable = golden chunk has same origin_agent.
-- Isolation coverage < 100% proves shared corpus is architecturally necessary.
-- ===========================================================================
WITH
chunk_agent AS (
  SELECT
    id,
    CASE
      WHEN source_file LIKE '%/agents/atlas/%'  OR source_file LIKE 'agents/atlas/%'  THEN 'atlas'
      WHEN source_file LIKE '%/agents/boris/%'  OR source_file LIKE 'agents/boris/%'  THEN 'boris'
      WHEN source_file LIKE '%/agents/cipher/%' OR source_file LIKE 'agents/cipher/%' THEN 'cipher'
      WHEN source_file LIKE '%/agents/forge/%'  OR source_file LIKE 'agents/forge/%'  THEN 'forge'
      WHEN source_file LIKE '%/agents/lex/%'    OR source_file LIKE 'agents/lex/%'    THEN 'lex'
      WHEN source_file LIKE '%/agents/nox/%'    OR source_file LIKE 'agents/nox/%'    THEN 'nox'
      ELSE 'shared_other'
    END AS origin_agent
  FROM chunks
),
golden_queries AS (
  -- golden_id TEXT stores chunk id of the known-correct answer
  SELECT
    st.id                  AS query_id,
    st.requesting_agent,
    CAST(st.golden_id AS INTEGER) AS golden_chunk_id
  FROM search_telemetry st
  WHERE st.golden_id IS NOT NULL
    AND st.requesting_agent IS NOT NULL
    AND st.requesting_agent IN ('atlas','boris','cipher','forge','lex','nox')
),
reachability AS (
  SELECT
    gq.query_id,
    gq.requesting_agent,
    gq.golden_chunk_id,
    COALESCE(ca.origin_agent, 'shared_other')   AS golden_chunk_origin,
    -- Reachable in isolation: same agent OR shared
    CASE
      WHEN COALESCE(ca.origin_agent, 'shared_other') = gq.requesting_agent
        OR COALESCE(ca.origin_agent, 'shared_other') = 'shared_other'
      THEN 1 ELSE 0
    END AS reachable_isolated,
    -- Always reachable in shared system
    1 AS reachable_shared
  FROM golden_queries gq
  LEFT JOIN chunk_agent ca ON ca.id = gq.golden_chunk_id
)
SELECT
  COUNT(*)                                          AS total_golden_queries,
  SUM(reachable_isolated)                           AS reachable_count_isolated,
  SUM(reachable_shared)                             AS reachable_count_shared,
  ROUND(100.0 * SUM(reachable_isolated) / COUNT(*), 2)
                                                    AS recall_coverage_isolated_pct,
  ROUND(100.0 * SUM(reachable_shared) / COUNT(*), 2)
                                                    AS recall_coverage_shared_pct,
  -- Gap is the hard evidence: answers literally unavailable in isolated system
  ROUND(100.0 * (SUM(reachable_shared) - SUM(reachable_isolated)) / COUNT(*), 2)
                                                    AS coverage_gap_pct,
  CASE WHEN COUNT(*) < 20
       THEN 'LOW — <20 golden queries; run W2.1 harness first'
       ELSE 'OK'
  END AS reliability
FROM reachability;
-- END --
