/**
 * src/search.ts — P3 temporal queries patch
 *
 * APPLIES ON TOP OF: staged-1.7a/edits/search.ts (which is the current VPS version)
 *
 * Changes:
 *   1. SearchOptions interface with asOf / changedSince
 *   2. buildTemporalClause() — generates SQL WHERE fragments
 *   3. search() FTS5 + chunks JOIN — pre-filter at SQL level
 *   4. searchSemantic() — post-filter vector candidates by chunk id (SQL IN)
 *   5. searchHybrid() — passes opts through to search() and searchSemantic()
 *   6. logTelemetry() — named-column INSERT covering all schema versions (A2 fix)
 *
 * CONSTRAINT: temporal is a HARD FILTER (WHERE clause), not a boost.
 * Do NOT add to ranking scores. P3 is distinct from E13 temporal boost.
 *
 * KG candidates note: KG entities / relations do not carry created_at/updated_at
 * in the current schema (v18). Temporal filtering applies to CHUNKS only.
 * kg_relations.evidence_chunk_id can be used to reach chunk timestamps but
 * KG-path queries are separate from hybrid search — no BLOCKED condition here.
 *
 * A2 fix (2026-05-19): search_telemetry INSERT uses named columns for all columns
 * added since schema v6 baseline (A0 +4, E05b +2, E13 +2, D01-v1 +6). This prevents
 * silent-fail when the deployed schema has more columns than the original INSERT knew
 * about. Named INSERT is resilient to future additive schema changes.
 */

import { createHash } from "crypto";
import { getDb } from "./db.js";
import { TIER_BOOST } from "./tier-manager.js";
import { expandQuery } from "./search-expansion.js";
import { dedupe } from "./search-dedup.js";
import { toSqliteTs } from "./dates.js";

const BOOST_TYPES = new Set(["decision", "lesson", "person", "project", "pending"]);

const SOURCE_TYPE_BOOST: Record<string, number> = {
  user_statement: 2.0,
  compiled: 1.5,
  timeline: 1.0,
  external: 0.8,
};

// ─── Temporal filter options ──────────────────────────────────────────────────

export interface TemporalFilter {
  /**
   * "What was true on this date?" — only chunks where:
   *   created_at <= asOf AND (deleted_at IS NULL OR deleted_at > asOf)
   * deleted_at column may not exist on all schema versions; guard with COALESCE.
   */
  asOf?: Date;
  /**
   * "What changed since this date?" — only chunks where:
   *   updated_at > changedSince OR created_at > changedSince
   */
  changedSince?: Date;
}

export interface SearchOptions extends TemporalFilter {
  limit?: number;
}

export interface SearchResult {
  id?: number;
  score: number;
  source_file: string;
  chunk_type: string;
  chunk_text: string;
  source_date: string | null;
  tier?: string;
  match_type?: "fts" | "semantic" | "hybrid";
  // P3 additions
  created_at?: string | null;
  updated_at?: string | null;
}

// ─── SQL temporal clause builder ─────────────────────────────────────────────

interface TemporalClause {
  /** AND-ready SQL fragment referencing table alias "c" (chunks) */
  sql: string;
  /** Bound parameters in order */
  params: string[];
}

/**
 * Build a SQL WHERE clause fragment for temporal filtering.
 * Returns { sql: "", params: [] } when no filter is set (no-op).
 *
 * Both filters can be combined (AND logic):
 *   asOf restricts to chunks that existed on that date.
 *   changedSince restricts to chunks created or modified after that date.
 *   Combined: chunks that existed on asOf AND were recently changed — edge case
 *   but valid (e.g. "show me current state as of yesterday, but only things
 *   that changed in the last week").
 */
export function buildTemporalClause(filter: TemporalFilter): TemporalClause {
  const parts: string[] = [];
  const params: string[] = [];

  if (filter.asOf) {
    const ts = toSqliteTs(filter.asOf);
    // created_at <= asOf: chunk existed by that date
    // deleted_at guard: if column doesn't exist, COALESCE to NULL = treat as not deleted
    parts.push(
      `(c.created_at IS NULL OR c.created_at <= ?) ` +
      `AND (COALESCE(c.deleted_at, NULL) IS NULL OR c.deleted_at > ?)`
    );
    params.push(ts, ts);
  }

  if (filter.changedSince) {
    const ts = toSqliteTs(filter.changedSince);
    // Either the chunk was created after OR updated after the cutoff
    parts.push(`(c.created_at > ? OR COALESCE(c.updated_at, c.created_at) > ?)`);
    params.push(ts, ts);
  }

  if (parts.length === 0) return { sql: "", params: [] };
  return { sql: `AND (${parts.join(") AND (")})`, params };
}

// ─── FTS5 search (keyword) ───────────────────────────────────────────────────

export function search(query: string, limit: number = 5, filter: TemporalFilter = {}): SearchResult[] {
  const db = getDb();
  const sanitized = query.replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  if (!sanitized) return [];

  const temporal = buildTemporalClause(filter);

  type RowShape = {
    id: number; source_file: string; chunk_type: string; chunk_text: string;
    source_date: string | null; rank: number; tier: string | null;
    source_type: string | null; created_at: string | null; updated_at: string | null;
  };

  let rows: RowShape[];
  try {
    rows = db.prepare(`
      SELECT c.id, c.source_file, c.chunk_type, c.chunk_text, c.source_date,
             c.tier, c.source_type, c.created_at, c.updated_at,
             bm25(chunks_fts, 1.0, 0.5, 0.5) as rank
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ${temporal.sql}
      ORDER BY rank LIMIT 20
    `).all(sanitized, ...temporal.params) as RowShape[];
  } catch {
    return [];
  }

  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    .toISOString().split("T")[0];

  const scored = rows.map((row) => {
    let score = Math.abs(row.rank);
    if (BOOST_TYPES.has(row.chunk_type)) score *= 2.0;
    if (row.source_date && row.source_date >= sevenDaysAgo) score *= 1.5;
    const tier = (row.tier ?? "peripheral") as keyof typeof TIER_BOOST;
    score *= (TIER_BOOST[tier] ?? 1.0);
    if (row.source_type) score *= SOURCE_TYPE_BOOST[row.source_type] ?? 1.0;
    return {
      id: row.id,
      score: Math.round(score * 100) / 100,
      source_file: row.source_file,
      chunk_type: row.chunk_type,
      chunk_text: row.chunk_text,
      source_date: row.source_date,
      tier: row.tier ?? "peripheral",
      match_type: "fts" as const,
      created_at: row.created_at,
      updated_at: row.updated_at,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  const results = scored.slice(0, limit);

  const ids = results.map((r) => r.id).filter(Boolean);
  if (ids.length > 0) {
    const ts = new Date().toISOString();
    const placeholders = ids.map(() => "?").join(",");
    db.prepare(`UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`).run(ts, ...ids);
  }

  return results;
}

// ─── Semantic search (vector) ────────────────────────────────────────────────

export async function searchSemantic(
  query: string,
  limit: number = 5,
  filter: TemporalFilter = {}
): Promise<SearchResult[]> {
  try {
    const { embedText, semanticSearch, ensureVecTable, countEmbedded } = await import("./embed.js");
    const db = getDb();
    ensureVecTable(db);

    const vecCount = countEmbedded(db);
    if (vecCount === 0) {
      console.error("[WARN] Vector index empty — run 'nox-mem vectorize' first. Falling back to FTS5.");
      return search(query, limit, filter);
    }

    const queryEmbedding = await embedText(query);
    // Fetch more candidates than needed; temporal filter applied after via chunk id lookup
    const rows = semanticSearch(db, queryEmbedding, limit * 3);

    if (rows.length === 0) return [];

    // Apply temporal filter at SQL level using IN (chunk ids from vector results)
    const candidateIds = rows.map((r) => r.chunk_id).filter(Boolean) as number[];
    const temporal = buildTemporalClause(filter);

    let chunkMeta: Array<{
      id: number; tier: string | null; source_type: string | null;
      created_at: string | null; updated_at: string | null;
    }>;

    if (candidateIds.length > 0) {
      const placeholders = candidateIds.map(() => "?").join(",");
      const whereBase = `WHERE c.id IN (${placeholders})`;
      const whereWithTemporal = temporal.sql
        ? `${whereBase} ${temporal.sql}`
        : whereBase;

      chunkMeta = db.prepare(
        `SELECT c.id, c.tier, c.source_type, c.created_at, c.updated_at
         FROM chunks c ${whereWithTemporal}`
      ).all(...candidateIds, ...temporal.params) as typeof chunkMeta;
    } else {
      chunkMeta = [];
    }

    // Build lookup of allowed ids (temporal-filtered)
    const allowedIds = new Set(chunkMeta.map((r) => r.id));
    const metaMap = new Map(chunkMeta.map((r) => [r.id, r]));

    const filteredRows = rows.filter((r) => r.chunk_id != null && allowedIds.has(r.chunk_id!));
    if (filteredRows.length === 0) return [];

    const maxDist = Math.max(...filteredRows.map((r) => r.distance));
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

    const scored = filteredRows.map((row) => {
      let score = maxDist > 0 ? (1 - row.distance / maxDist) * 10 : 10;
      if (BOOST_TYPES.has(row.chunk_type)) score *= 1.5;
      if (row.source_date && row.source_date >= sevenDaysAgo) score *= 1.2;
      const info = row.chunk_id ? metaMap.get(row.chunk_id) : undefined;
      const tier = (info?.tier ?? "peripheral") as keyof typeof TIER_BOOST;
      score *= (TIER_BOOST[tier] ?? 1.0);
      if (info?.source_type) score *= SOURCE_TYPE_BOOST[info.source_type] ?? 1.0;
      return {
        id: row.chunk_id,
        score: Math.round(score * 100) / 100,
        source_file: row.source_file,
        chunk_type: row.chunk_type,
        chunk_text: row.chunk_text,
        source_date: row.source_date,
        tier,
        match_type: "semantic" as const,
        created_at: info?.created_at ?? null,
        updated_at: info?.updated_at ?? null,
      };
    });

    scored.sort((a, b) => b.score - a.score);
    const semResults = scored.slice(0, limit);

    const accessIds = semResults.map((r) => r.id).filter(Boolean);
    if (accessIds.length > 0) {
      const ts = new Date().toISOString();
      const placeholders = accessIds.map(() => "?").join(",");
      db.prepare(`UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`).run(ts, ...accessIds);
    }

    return semResults;
  } catch (err) {
    console.error("[WARN] Semantic search failed, falling back to FTS:", (err as Error).message);
    return search(query, limit, filter);
  }
}

// ─── Hybrid search (FTS5 + semantic, expanded, RRF-fused, deduped) ──────────

function rrfScore(rank: number, k = 60): number {
  return 1 / (k + rank + 1);
}

/**
 * TelemetryExtras carries the optional columns added since the original v6 schema.
 * All fields are undefined by default — callers only set what they know.
 *
 * Column provenance:
 *   A0  (2026-04-25, schema v6+):  query_text, golden_id, top_chunk_ids, top_scores
 *   E05b (2026-05-06, schema v13): reason_boost_applied, reason_relations_used
 *   E13  (2026-05-06, schema v14): was_temporal_query, temporal_boost_mode
 *   D01  (2026-05-07, schema v16): reranker_mode, reranker_top_k_in, reranker_top_k_out,
 *                                  reranker_latency_ms, reranker_position_changes, reranker_lift_score
 */
export interface TelemetryExtras {
  // A0 — opt-in text logging (NOX_SEARCH_LOG_TEXT=1)
  query_text?: string | null;
  golden_id?: string | null;
  top_chunk_ids?: string | null;   // JSON array e.g. "[12,45,3]"
  top_scores?: string | null;      // JSON array of floats

  // E05b — reason-boost telemetry (CUT D38 but columns remain in schema)
  reason_boost_applied?: number | null;
  reason_relations_used?: number | null;

  // E13 — temporal-aware ranking
  was_temporal_query?: number | null;   // 0 or 1
  temporal_boost_mode?: string | null;  // 'off' | 'shadow' | 'active'

  // D01 — cross-encoder reranker (CUT v1+v2, schema v16 columns remain)
  reranker_mode?: string | null;             // 'off' | 'shadow' | 'active'
  reranker_top_k_in?: number | null;
  reranker_top_k_out?: number | null;
  reranker_latency_ms?: number | null;
  reranker_position_changes?: number | null;
  reranker_lift_score?: number | null;
}

/**
 * logTelemetry — write one row to search_telemetry.
 *
 * Uses NAMED columns in the INSERT so the statement is resilient to additive
 * schema migrations. A positional VALUES(...) breaks silently whenever the schema
 * has more columns than the compiled INSERT knows about (A2 bug, PR #139).
 *
 * All extended columns default to NULL when not supplied, which is correct for
 * columns added via ALTER TABLE ... DEFAULT x (SQLite fills the default at
 * the storage level; we still write NULL explicitly to be explicit).
 */
function logTelemetry(
  query: string,
  variantsCount: number,
  resultsCount: number,
  hasSemantic: boolean,
  latencyMs: number,
  skipReason?: string,
  extras: TelemetryExtras = {},
): void {
  try {
    const db = getDb();
    const hash = createHash("sha1").update(query).digest("hex").substring(0, 16);
    const words = query.trim().split(/\s+/).filter(Boolean).length;

    // A0 opt-in: only log raw text when env var is set (privacy default OFF)
    const logText = process.env["NOX_SEARCH_LOG_TEXT"] === "1";
    const queryText = logText ? (extras.query_text ?? query) : null;

    db.prepare(
      `INSERT INTO search_telemetry (
        query_hash, query_words, variants_count, results_count,
        has_semantic, latency_ms, expansion_skipped_reason,
        query_text, golden_id, top_chunk_ids, top_scores,
        reason_boost_applied, reason_relations_used,
        was_temporal_query, temporal_boost_mode,
        reranker_mode, reranker_top_k_in, reranker_top_k_out,
        reranker_latency_ms, reranker_position_changes, reranker_lift_score
      ) VALUES (
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,
        ?, ?,
        ?, ?, ?,
        ?, ?, ?
      )`,
    ).run(
      hash, words, variantsCount, resultsCount,
      hasSemantic ? 1 : 0, latencyMs, skipReason ?? null,
      queryText, extras.golden_id ?? null, extras.top_chunk_ids ?? null, extras.top_scores ?? null,
      extras.reason_boost_applied ?? null, extras.reason_relations_used ?? null,
      extras.was_temporal_query ?? null, extras.temporal_boost_mode ?? null,
      extras.reranker_mode ?? null, extras.reranker_top_k_in ?? null, extras.reranker_top_k_out ?? null,
      extras.reranker_latency_ms ?? null, extras.reranker_position_changes ?? null, extras.reranker_lift_score ?? null,
    );
  } catch {
    // telemetria nunca derruba a search
  }
}

export async function searchHybrid(
  query: string,
  limit: number = 5,
  filter: TemporalFilter = {}
): Promise<SearchResult[]> {
  const t0 = Date.now();
  const perVariantLimit = limit * 2;

  // Fire original-query searches immediately; expansion in parallel.
  const originalFtsPromise = Promise.resolve(search(query.trim(), perVariantLimit, filter));
  const semPromise = searchSemantic(query.trim(), perVariantLimit * 2, filter);
  const expansionPromise = expandQuery(query);

  const expansion = await expansionPromise;
  const variants = expansion.variants;

  // Variant FTS also respects temporal filter
  const extraVariantFtsPromises = variants
    .slice(1)
    .map((v) => Promise.resolve(search(v, perVariantLimit, filter)));

  const allBatches = await Promise.all([
    originalFtsPromise,
    ...extraVariantFtsPromises,
    semPromise,
  ]);

  const scoreMap = new Map<string, SearchResult & { rrfScore: number; saw_semantic: boolean }>();
  const semanticBatchIdx = allBatches.length - 1;

  allBatches.forEach((batch, batchIdx) => {
    const isSemanticBatch = batchIdx === semanticBatchIdx;
    batch.forEach((r, rank) => {
      const key = `${r.source_file}::${r.chunk_text.substring(0, 50)}`;
      const existing = scoreMap.get(key);
      const scoreInc = rrfScore(rank);
      if (existing) {
        existing.rrfScore += scoreInc;
        existing.saw_semantic = existing.saw_semantic || isSemanticBatch;
        if (existing.saw_semantic && (existing.match_type === "fts" || isSemanticBatch)) {
          existing.match_type =
            isSemanticBatch && existing.match_type === "fts" ? "hybrid" : existing.match_type;
        }
      } else {
        scoreMap.set(key, {
          ...r,
          rrfScore: scoreInc,
          saw_semantic: isSemanticBatch,
          match_type: isSemanticBatch ? "semantic" : "fts",
        });
      }
    });
  });

  for (const v of scoreMap.values()) {
    if (v.saw_semantic && v.match_type !== "semantic") v.match_type = "hybrid";
  }

  const preDedup = Array.from(scoreMap.values())
    .sort((a, b) => b.rrfScore - a.rrfScore)
    .slice(0, Math.max(limit * 3, 15))
    .map(({ rrfScore: s, saw_semantic: _, ...r }) => ({ ...r, score: Math.round(s * 1000 * 100) / 100 }));

  const final = dedupe(preDedup, limit);

  const hasSemantic = final.some((r) => r.match_type === "semantic" || r.match_type === "hybrid");
  const isTemporalQuery = (filter.asOf != null || filter.changedSince != null) ? 1 : 0;
  logTelemetry(query, variants.length, final.length, hasSemantic, Date.now() - t0, expansion.reason, {
    was_temporal_query: isTemporalQuery,
    temporal_boost_mode: process.env["NOX_TEMPORAL_BOOST_MODE"] ?? null,
  });

  return final;
}

// ─── Format results ───────────────────────────────────────────────────────────

export function formatResults(results: SearchResult[]): string {
  if (results.length === 0) return "No results found.";
  return results
    .map((r, i) => {
      const preview = r.chunk_text.substring(0, 200).replace(/\n/g, " ");
      const tag = r.match_type ? ` [${r.match_type}]` : "";
      return `#${i + 1} [${r.score}${tag}] ${r.source_file}\n   "${preview}..."`;
    })
    .join("\n\n");
}
