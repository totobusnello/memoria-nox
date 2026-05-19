import { createHash } from "crypto";
import { getDb } from "./db.js";
import { TIER_BOOST } from "./tier-manager.js";
import { expandQuery } from "./search-expansion.js";
import { dedupe } from "./search-dedup.js";
import { calculateSalience, getSalienceMode } from "./salience.js";

// ─── Boost configuration (Fase 1.7a + A-boost-stack-wiring 2026-05-19) ────────
//
// G3 ablation (PR #146, 2026-05-19) proved every boost below was INERT in the
// deployed search.ts: section_boost / pain / source_type maps never matched
// the live corpus keys, and salience was observability-only. This module wires
// them up correctly for the first time.
//
// ## ADDITIVE pattern (CLAUDE.md rule #5)
//
// All boosts contribute a delta `(factor − 1)` into a single `boostSum`, then
// collapse via `score = baseScore * (1 + boostSum)`. Multiplicative stacking
// is forbidden — it amplifies tails super-linearly and caused incident v3.4.
//
// ## Env toggles (default: ALL boosts ACTIVE)
//
//   NOX_DISABLE_TYPE_BOOST=1         — disable BOOST_TYPES (chunk_type)
//   NOX_DISABLE_TIER_BOOST=1         — disable TIER_BOOST (tier column)
//   NOX_DISABLE_SOURCE_TYPE_BOOST=1  — disable SOURCE_TYPE_BOOST (source_type)
//   NOX_DISABLE_SECTION_BOOST=1      — disable SECTION_BOOST (section / section_boost)
//   NOX_DISABLE_RECENCY_BOOST=1      — disable 7-day recency window boost
//   NOX_SALIENCE_MODE=active         — apply salience delta (shadow=DEFAULT, off=ablation)
//
// Defaults preserve backwards-compat: if no env vars are set, the multiplicative
// path is replaced by the equivalent additive path. The `NOX_SALIENCE_MODE`
// default stays `shadow` per architectural shadow-discipline (paper §4).

const BOOST_TYPES = new Set(["decision", "lesson", "person", "project", "pending"]);

// Legacy multiplicative factors → additive deltas (factor − 1):
const TYPE_BOOST_DELTA_FTS = 1.0;        // was *2.0
const TYPE_BOOST_DELTA_SEMANTIC = 0.5;   // was *1.5
const RECENCY_BOOST_DELTA_FTS = 0.5;     // was *1.5
const RECENCY_BOOST_DELTA_SEMANTIC = 0.2; // was *1.2

// ── Source-attribution boost ──────────────────────────────────────────────────
//
// G3 audit (2026-05-19, n=68,995 chunks in prod):
//   NULL:     67,949 (98.5%)
//   external: 1,046 (1.5%)
//
// The legacy keys `user_statement` / `compiled` / `timeline` from staged-1.7a do
// NOT exist in the live corpus — they came from a planning doc that never landed
// in the ingest pipeline (caused SOURCE_TYPE_BOOST to resolve to 1.0 in 100% of
// lookups). We keep them for forward-compat (they activate automatically when
// the ingest path lands) and add the live key `external` with a small penalty.
const SOURCE_TYPE_BOOST: Record<string, number> = {
  user_statement: 2.0, // forward-compat: dead-by-corpus today
  compiled: 1.5,        // forward-compat: dead-by-corpus today
  timeline: 1.0,        // forward-compat: neutral
  external: 0.8,        // ACTIVE: web/external content slight penalty
};

// ── Section boost (V10 schema, populated by ingestEntityFile) ─────────────────
//
// Audited 2026-05-19 (per WIP stash inspection):
//   NULL:        68,246 (legacy non-entity chunks)
//   timeline:    383
//   frontmatter: 183
//   compiled:    183
const SECTION_BOOST: Record<string, number> = {
  compiled: 2.0,    // truth section of an entity file (high signal)
  frontmatter: 1.5, // YAML metadata (medium signal)
  timeline: 0.8,    // event log (lower signal per token)
};

// Module-load env flag snapshot (avoids per-chunk process.env read).
const DISABLE_TYPE_BOOST = process.env.NOX_DISABLE_TYPE_BOOST === "1";
const DISABLE_TIER_BOOST = process.env.NOX_DISABLE_TIER_BOOST === "1";
const DISABLE_SOURCE_TYPE_BOOST = process.env.NOX_DISABLE_SOURCE_TYPE_BOOST === "1";
const DISABLE_SECTION_BOOST = process.env.NOX_DISABLE_SECTION_BOOST === "1";
const DISABLE_RECENCY_BOOST = process.env.NOX_DISABLE_RECENCY_BOOST === "1";

// ─── Per-boost delta helpers ──────────────────────────────────────────────────

function tierDelta(tier: string | null | undefined): number {
  if (DISABLE_TIER_BOOST) return 0;
  const t = (tier ?? "peripheral") as keyof typeof TIER_BOOST;
  const f = TIER_BOOST[t] ?? 1.0;
  return f - 1.0;
}

function sourceTypeDelta(sourceType: string | null | undefined): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;
  const f = SOURCE_TYPE_BOOST[sourceType] ?? 1.0;
  return f - 1.0;
}

function sectionDelta(
  section: string | null | undefined,
  sectionBoostCol: number | null | undefined,
): number {
  if (DISABLE_SECTION_BOOST) return 0;
  // Canonical: map by section name (forward-stable across new schemas).
  if (section && SECTION_BOOST[section] !== undefined) {
    return SECTION_BOOST[section]! - 1.0;
  }
  // Fallback: trust the section_boost column the ingester wrote
  // (lets forward-compat fields work without touching this map).
  if (
    sectionBoostCol !== null &&
    sectionBoostCol !== undefined &&
    Number.isFinite(sectionBoostCol)
  ) {
    return sectionBoostCol - 1.0;
  }
  return 0;
}

interface SalienceChunkInput {
  chunk_type?: string | null;
  source_type?: string | null;
  tier?: string | null;
  pain?: number | null;
  importance?: number | null;
  retention_days?: number | null;
  source_date?: string | null;
  created_at?: string | null;
  last_accessed_at?: string | null;
}

function salienceDelta(chunk: SalienceChunkInput): number {
  // Shadow mode and off mode both contribute 0 to ranking (shadow can still
  // be logged elsewhere; that observability path is not in scope here).
  if (getSalienceMode() !== "active") return 0;
  const s = calculateSalience(chunk);
  // Neutral baseline 0.5: salience=0.5 → no net effect; salience=1.0 → +0.5;
  // salience=0 → −0.5. Bounded delta keeps multi-stack stacking sane.
  return s - 0.5;
}

// ─── Public result shape (extended with boost-stack diagnostics) ──────────────

export interface SearchResult {
  id?: number;
  score: number;
  source_file: string;
  chunk_type: string;
  chunk_text: string;
  source_date: string | null;
  tier?: string;
  section?: string | null;
  pain?: number | null;
  importance?: number | null;
  source_type?: string | null;
  match_type?: "fts" | "semantic" | "hybrid";
}

// ─── FTS5 search (keyword) ────────────────────────────────────────────────────

interface FtsRow {
  id: number;
  source_file: string;
  chunk_type: string;
  chunk_text: string;
  source_date: string | null;
  rank: number;
  tier: string | null;
  source_type: string | null;
  section: string | null;
  section_boost: number | null;
  pain: number | null;
  importance: number | null;
  retention_days: number | null;
  created_at: string | null;
  last_accessed_at: string | null;
}

export function search(query: string, limit: number = 5): SearchResult[] {
  const db = getDb();
  const sanitized = query.replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  if (!sanitized) return [];

  let rows: FtsRow[];
  try {
    rows = db.prepare(`
      SELECT c.id, c.source_file, c.chunk_type, c.chunk_text, c.source_date,
             c.tier, c.source_type, c.section, c.section_boost,
             c.pain, c.importance, c.retention_days, c.created_at, c.last_accessed_at,
             bm25(chunks_fts, 1.0, 0.5, 0.5) as rank
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT 20
    `).all(sanitized) as FtsRow[];
  } catch {
    return [];
  }

  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    .toISOString().split("T")[0]!;

  const scored = rows.map((row) => {
    const baseScore = Math.abs(row.rank);
    let boostSum = 0;

    if (!DISABLE_TYPE_BOOST && BOOST_TYPES.has(row.chunk_type)) {
      boostSum += TYPE_BOOST_DELTA_FTS;
    }
    if (!DISABLE_RECENCY_BOOST && row.source_date && row.source_date >= sevenDaysAgo) {
      boostSum += RECENCY_BOOST_DELTA_FTS;
    }
    boostSum += tierDelta(row.tier);
    boostSum += sourceTypeDelta(row.source_type);
    boostSum += sectionDelta(row.section, row.section_boost);
    boostSum += salienceDelta(row);

    const score = baseScore * (1 + boostSum);

    return {
      id: row.id,
      score: Math.round(score * 100) / 100,
      source_file: row.source_file,
      chunk_type: row.chunk_type,
      chunk_text: row.chunk_text,
      source_date: row.source_date,
      tier: row.tier ?? "peripheral",
      section: row.section,
      pain: row.pain,
      importance: row.importance,
      source_type: row.source_type,
      match_type: "fts" as const,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  const results = scored.slice(0, limit);

  // Track access
  const ids = results.map((r) => r.id).filter(Boolean);
  if (ids.length > 0) {
    const ts = new Date().toISOString();
    const placeholders = ids.map(() => "?").join(",");
    db.prepare(
      `UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`,
    ).run(ts, ...ids);
  }

  return results;
}

// ─── Semantic search (vector) ─────────────────────────────────────────────────

interface BoostRow {
  id: number;
  tier: string | null;
  source_type: string | null;
  section: string | null;
  section_boost: number | null;
  pain: number | null;
  importance: number | null;
  retention_days: number | null;
  created_at: string | null;
  last_accessed_at: string | null;
  chunk_type: string;
}

export async function searchSemantic(query: string, limit: number = 5): Promise<SearchResult[]> {
  try {
    const { embedText, semanticSearch, ensureVecTable, countEmbedded } = await import("./embed.js");
    const db = getDb();
    ensureVecTable(db);

    // Check if index has any embeddings
    const vecCount = countEmbedded(db);
    if (vecCount === 0) {
      console.error("[WARN] Vector index empty — run 'nox-mem vectorize' first. Falling back to FTS5.");
      return search(query, limit);
    }

    const queryEmbedding = await embedText(query);
    const rows = semanticSearch(db, queryEmbedding, limit * 2);

    if (rows.length === 0) return [];

    // Fetch boost-stack columns in one shot.
    const chunkIds = rows.map((r) => r.chunk_id).filter(Boolean);
    const boostMap = new Map<number, BoostRow>();
    if (chunkIds.length > 0) {
      const placeholders = chunkIds.map(() => "?").join(",");
      const boostRows = db.prepare(`
        SELECT id, tier, source_type, section, section_boost,
               pain, importance, retention_days, created_at, last_accessed_at,
               chunk_type
        FROM chunks WHERE id IN (${placeholders})
      `).all(...chunkIds) as BoostRow[];
      for (const br of boostRows) boostMap.set(br.id, br);
    }

    const maxDist = Math.max(...rows.map((r) => r.distance));
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      .toISOString().split("T")[0]!;

    const scored = rows.map((row) => {
      const baseScore = maxDist > 0 ? (1 - row.distance / maxDist) * 10 : 10;
      const info = row.chunk_id ? boostMap.get(row.chunk_id) : undefined;
      let boostSum = 0;

      if (!DISABLE_TYPE_BOOST && BOOST_TYPES.has(row.chunk_type)) {
        boostSum += TYPE_BOOST_DELTA_SEMANTIC;
      }
      if (!DISABLE_RECENCY_BOOST && row.source_date && row.source_date >= sevenDaysAgo) {
        boostSum += RECENCY_BOOST_DELTA_SEMANTIC;
      }
      boostSum += tierDelta(info?.tier);
      boostSum += sourceTypeDelta(info?.source_type);
      boostSum += sectionDelta(info?.section, info?.section_boost);
      if (info) {
        boostSum += salienceDelta({
          chunk_type: info.chunk_type,
          source_type: info.source_type,
          tier: info.tier,
          pain: info.pain,
          importance: info.importance,
          retention_days: info.retention_days,
          created_at: info.created_at,
          last_accessed_at: info.last_accessed_at,
          source_date: row.source_date,
        });
      }

      const score = baseScore * (1 + boostSum);
      const tier = (info?.tier ?? "peripheral") as keyof typeof TIER_BOOST;

      return {
        id: row.chunk_id,
        score: Math.round(score * 100) / 100,
        source_file: row.source_file,
        chunk_type: row.chunk_type,
        chunk_text: row.chunk_text,
        source_date: row.source_date,
        tier: tier,
        section: info?.section ?? null,
        pain: info?.pain ?? null,
        importance: info?.importance ?? null,
        source_type: info?.source_type ?? null,
        match_type: "semantic" as const,
      };
    });

    scored.sort((a, b) => b.score - a.score);
    const semResults = scored.slice(0, limit);

    // Track access
    const accessIds = semResults.map((r) => r.id).filter(Boolean);
    if (accessIds.length > 0) {
      const ts = new Date().toISOString();
      const placeholders = accessIds.map(() => "?").join(",");
      db.prepare(
        `UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`,
      ).run(ts, ...accessIds);
    }

    return semResults;
  } catch (err) {
    // Fallback to FTS if vector index not ready
    console.error("[WARN] Semantic search failed, falling back to FTS:", (err as Error).message);
    return search(query, limit);
  }
}

// ─── Hybrid search (FTS5 + semantic, expanded, RRF-fused, deduped) ───────────

function rrfScore(rank: number, k = 60): number {
  return 1 / (k + rank + 1);
}

function logTelemetry(
  query: string,
  variantsCount: number,
  resultsCount: number,
  hasSemantic: boolean,
  latencyMs: number,
  skipReason?: string,
): void {
  try {
    const db = getDb();
    const hash = createHash("sha1").update(query).digest("hex").substring(0, 16);
    const words = query.trim().split(/\s+/).filter(Boolean).length;
    db.prepare(
      `INSERT INTO search_telemetry (query_hash, query_words, variants_count, results_count, has_semantic, latency_ms, expansion_skipped_reason)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ).run(hash, words, variantsCount, resultsCount, hasSemantic ? 1 : 0, latencyMs, skipReason || null);
  } catch {
    // telemetria nunca derruba a search
  }
}

export async function searchHybrid(query: string, limit: number = 5): Promise<SearchResult[]> {
  const t0 = Date.now();
  const perVariantLimit = limit * 2;

  // Kick off original-query searches IMMEDIATELY and expansion in parallel.
  // Total time = max(expansion + variantFTS, originalFTS+semantic) — does not block
  // the original search behind a 500-1500ms Gemini call.
  const originalFtsPromise = Promise.resolve(search(query.trim(), perVariantLimit));
  const semPromise = searchSemantic(query.trim(), perVariantLimit * 2);
  const expansionPromise = expandQuery(query);

  const expansion = await expansionPromise;
  const variants = expansion.variants;

  // Variants (excluding the original, which is already running) → FTS only.
  const extraVariantFtsPromises = variants.slice(1).map((v) => Promise.resolve(search(v, perVariantLimit)));

  const allBatches = await Promise.all([
    originalFtsPromise,
    ...extraVariantFtsPromises,
    semPromise,
  ]);

  // Fuse via RRF. Rank within EACH batch.
  const scoreMap = new Map<string, SearchResult & { rrfScore: number; saw_semantic: boolean }>();
  const semanticBatchIdx = allBatches.length - 1; // last is the semantic batch

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
          existing.match_type = isSemanticBatch && existing.match_type === "fts" ? "hybrid" : existing.match_type;
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

  // Promote to hybrid any result touched by both fts and semantic batches
  for (const v of scoreMap.values()) {
    if (v.saw_semantic && v.match_type !== "semantic") v.match_type = "hybrid";
  }

  const preDedup = Array.from(scoreMap.values())
    .sort((a, b) => b.rrfScore - a.rrfScore)
    .slice(0, Math.max(limit * 3, 15))
    .map(({ rrfScore: s, saw_semantic: _, ...r }) => ({ ...r, score: Math.round(s * 1000 * 100) / 100 }));

  const final = dedupe(preDedup, limit);

  const hasSemantic = final.some((r) => r.match_type === "semantic" || r.match_type === "hybrid");
  logTelemetry(query, variants.length, final.length, hasSemantic, Date.now() - t0, expansion.reason);

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

// ─── Test-only exports (named with _ prefix to signal "do not use externally") ─

export const _internals = {
  SOURCE_TYPE_BOOST,
  SECTION_BOOST,
  BOOST_TYPES,
  TYPE_BOOST_DELTA_FTS,
  TYPE_BOOST_DELTA_SEMANTIC,
  RECENCY_BOOST_DELTA_FTS,
  RECENCY_BOOST_DELTA_SEMANTIC,
  tierDelta,
  sourceTypeDelta,
  sectionDelta,
  salienceDelta,
};
