import { createHash } from "crypto";
import { getDb } from "./db.js";
import { TIER_BOOST } from "./tier-manager.js";
import { expandQuery } from "./search-expansion.js";
import { dedupe } from "./search-dedup.js";
import { calculateSalience, calculateSalienceLegacy, getSalienceMode } from "./salience.js";
import { rerankByTemporalProximity, logTemporalProbe } from "./temporal-retrieval.js";
import { countQueryEntities } from "./query-entity-count.js";

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
// G3 audit (2026-05-19, n=68,995 chunks in prod): 98.48% NULL, 1.52% external.
// G5 V3 ablation A5 (2026-05-19) confirmed SOURCE_TYPE_BOOST inert because the
// only live key was `external` (1.5%) — A10 (full minus source_type) tied A8
// canonical at 0.6237, proving the map contributed 0%.
//
// G9 ablation (2026-05-20, g5.db prod n=69,495 chunks, n=100 queries) cravou
// que a calibração POST-backfill mantém o boost vivo PORÉM redundante com
// SECTION_BOOST em entity files (compiled/frontmatter/timeline):
//   A0 (no boosts)              = 0.4108
//   A5 (source_type only)       = 0.4693  → +14.2% vs A0 (boost LIVE)
//   A8 (full canonical)         = 0.5387
//   A10 (full minus source_type) = 0.5530 → +2.6% vs A8 (REDUNDÂNCIA)
//
// Resolution (PR #180 Option 1): Hard Mutex — `sourceTypeDelta` retorna 0
// quando o chunk já tem `section` populado (sinal mais granular ganha). Spec:
// `specs/2026-05-20-mutual-exclusion-section-source-type.md`. Rollback rápido
// via env `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` (reverte ao pré-mutex).
//
// Post-backfill state (2026-05-19, audit_id=118, via PR #151):
//   note          ~31000  (~46%) — generic .md catch-all
//   personal-doc  ~23000  (~34%) — faturamento, contratos, planilhas
//   ocr-cache     ~11000  (~16%) — scan artifacts, low signal
//   entity            749  (1.10%) — curated entity files (compiled/frontmatter/timeline)
//   project-doc       560  (0.82%) — project planning docs
//   session          small         — Cipher/Atlas/Boris/etc session checkpoints
//   skill            small         — Claude Code skill defs
//   command          small         — slash command defs
//   lesson           small         — retrospective lessons learned
//   legal-template   small         — disputes/contracts templates
//   external         1046  (1.52%) — preserved (web/external content)
//   other            residual      — unclassified fallback
//
// Calibration rationale (signal-to-noise × curation):
//   2.0    entity        — highest curation, hand-authored truth
//   1.8    lesson        — distilled retrospective, dense signal/token
//   1.5    skill         — Claude Code skill definitions (curated)
//   1.4    project-doc   — project planning (curated, scoped)
//   1.4    command       — slash command defs (curated)
//   1.3    legal-template — legal templates (curated, low-volume)
//   1.2    personal-doc  — faturamento/contratos (relevant, heterogeneous)
//   1.0    session       — checkpoints (mixed signal)
//   1.0    note          — generic .md baseline
//   0.8    external      — web/external slight penalty (preserved)
//   0.7    other         — unclassified fallback penalty
//   0.7    ocr-cache     — scan artifacts, low signal-per-token (conservative)
//
// `ocr-cache` deliberately set to 0.7 (NOT 0.5 as a first instinct would
// suggest) per PR #154 code-review MEDIUM: ocr-cache is 16% of corpus and we
// have NO empirical evidence (pre-deploy) that −0.5 is safe in the live mix —
// a deeper penalty risks demoting golden hits backed by faturamento PDFs that
// fell through to OCR. Treat 0.7 as the conservative landing; a G6 ablation
// (post next eval cycle) can tighten to 0.5 if it proves net-positive on
// goldens. Same defensive posture as tier_boost default-off (PR #150).
//
// Forward-compat: `user_statement` retained — legitimate ingest path that
// hasn't landed yet (planning doc lineage). `compiled` / `timeline` removed
// from this map (2026-05-20, code-review LOW #2) — those are V10 `section`
// column values, NOT source_type values; keeping them here was confusing
// and they're already covered by SECTION_BOOST below.
const SOURCE_TYPE_BOOST: Record<string, number> = {
  // Active keys (post-backfill 2026-05-19)
  entity: 2.0,
  lesson: 1.8,
  skill: 1.5,
  "project-doc": 1.4,
  command: 1.4,
  "legal-template": 1.3,
  "personal-doc": 1.2,
  session: 1.0,
  note: 1.0,
  external: 0.8,
  other: 0.7,
  "ocr-cache": 0.7,
  // Forward-compat (ingest path planned but not landed):
  user_statement: 2.0,
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
// tier_boost DEFAULT DISABLED per G4 ablation (2026-05-19):
//   A6 (tier only) = 0.4616 nDCG@10 < A0 (no boosts) = 0.4817.
// Core chunks (3.96% of corpus, memory-system internals) over-promote and push
// golden hits down. Opt-in via NOX_ENABLE_TIER_BOOST=1; legacy
// NOX_DISABLE_TIER_BOOST=1 honored as redundant (preserves back-compat).
// See docs/audits/2026-05-19-salience-distribution-audit.md.
const DISABLE_TIER_BOOST =
  process.env.NOX_DISABLE_TIER_BOOST === "1" ||
  process.env.NOX_ENABLE_TIER_BOOST !== "1";
const DISABLE_SOURCE_TYPE_BOOST = process.env.NOX_DISABLE_SOURCE_TYPE_BOOST === "1";
const DISABLE_SECTION_BOOST = process.env.NOX_DISABLE_SECTION_BOOST === "1";
const DISABLE_RECENCY_BOOST = process.env.NOX_DISABLE_RECENCY_BOOST === "1";
// G9 mutex: default ON. Set `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` to revert
// to pre-mutex behaviour (both `sectionDelta` and `sourceTypeDelta` accumulate
// on entity-compiled/frontmatter/timeline chunks — known redundant per G9).
const DISABLE_MUTEX_SECTION_SOURCE_TYPE =
  process.env.NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE === "1";

// G10d conditional mutex: mutex is gated on query entity count.
//
// Evidence (G10b/G10c audits 2026-05-21):
//   single-hop:  +8.22% nDCG (mutex helps — removes double-boost on gold)
//   multi-hop:   −3.95% nDCG (mutex hurts — removes chain-traversal signal)
//   style-agnostic (NL −3.91%, keyword −3.99%)
//
// Conditional logic:
//   queryEntityCount ≤ MUTEX_QUERY_ENTITY_THRESHOLD (default 1) → mutex active
//   queryEntityCount >  threshold                               → mutex disabled
//
// Rollback:
//   Tier 1 — NOX_DISABLE_CONDITIONAL_MUTEX=1 → hard mutex always-on (G10)
//   Tier 2 — NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1 → no mutex at all (pre-G9)
//
// Spec: specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md

/** Mutex threshold: entity count AT OR BELOW this value → mutex active. Default 1. */
const MUTEX_QUERY_ENTITY_THRESHOLD = Number.parseInt(
  process.env.NOX_MUTEX_QUERY_ENTITY_THRESHOLD ?? "1",
  10,
);

/** When true, reverts to hard mutex always-on (G10 behaviour, ignores entity count). */
const DISABLE_CONDITIONAL_MUTEX =
  process.env.NOX_DISABLE_CONDITIONAL_MUTEX === "1";

// ─── Per-boost delta helpers ──────────────────────────────────────────────────

function tierDelta(tier: string | null | undefined): number {
  if (DISABLE_TIER_BOOST) return 0;
  const t = (tier ?? "peripheral") as keyof typeof TIER_BOOST;
  const f = TIER_BOOST[t] ?? 1.0;
  return f - 1.0;
}

function sourceTypeDelta(
  sourceType: string | null | undefined,
  section: string | null | undefined,
  queryEntityCount: number = 0, // G10d: default 0 preserves pre-G10d call sites
): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;

  // HARD MUTEX (G9 evidence — spec PR #180 Option 1):
  // Se o chunk já tem section_boost ativo (sinal mais granular), pula
  // source_type_boost pra evitar double-boost em entity files.
  //
  // G10d CONDITIONAL LAYER: mutex applies only when queryEntityCount ≤ threshold.
  // Multi-entity queries (≥2 entities) disable mutex to preserve chain traversal.
  //   - DISABLE_CONDITIONAL_MUTEX=true → ignores entity count, hard mutex always-on
  //   - queryEntityCount > MUTEX_QUERY_ENTITY_THRESHOLD → mutex bypassed
  //   - queryEntityCount ≤ MUTEX_QUERY_ENTITY_THRESHOLD → mutex active (current G10)
  //
  // Rollback: NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1 bypasses the entire mutex.
  // Spec: specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md §4 Step 2.
  const mutexShouldApply =
    !DISABLE_MUTEX_SECTION_SOURCE_TYPE &&
    !DISABLE_SECTION_BOOST &&
    section != null &&
    SECTION_BOOST[section] !== undefined;

  if (mutexShouldApply) {
    // G10d conditional: skip mutex when multi-entity query (unless conditional disabled)
    const conditionalAllowsPass =
      !DISABLE_CONDITIONAL_MUTEX && queryEntityCount > MUTEX_QUERY_ENTITY_THRESHOLD;

    if (!conditionalAllowsPass) {
      return 0; // mutex active
    }
    // else: fall through — multi-entity query, mutex disabled
  }

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
  access_count?: number | null;
}

// ─── Salience observability probes (MEDIUM #4 + #5, PR #150 review) ───────────
//
// Two opt-in env-gated probes that log salience telemetry WITHOUT affecting
// ranking. Both write JSON lines to stderr; downstream telemetry collector
// (per /api/health pipeline, CLAUDE.md §5) is expected to ingest these.
//
//   NOX_SALIENCE_SHADOW_LOG=1   — log v2 salience computed in shadow mode
//   NOX_SALIENCE_AB_SHADOW=1    — log (v2, legacy, delta) per chunk for
//                                 A/B comparison without flipping to active
//
// These never throw — observability must not derail search.

function shadowProbeSalience(s: number, chunkId: number | undefined): void {
  if (process.env.NOX_SALIENCE_SHADOW_LOG !== "1") return;
  try {
    process.stderr.write(
      JSON.stringify({ type: "shadow_salience", chunk_id: chunkId, salience: s, ts: Date.now() }) + "\n",
    );
  } catch {
    /* observability must not throw */
  }
}

function abShadowProbe(sV2: number, sLegacy: number, chunkId: number | undefined): void {
  if (process.env.NOX_SALIENCE_AB_SHADOW !== "1") return;
  try {
    process.stderr.write(
      JSON.stringify({
        type: "ab_salience",
        chunk_id: chunkId,
        v2: sV2,
        legacy: sLegacy,
        delta: sV2 - sLegacy,
        ts: Date.now(),
      }) + "\n",
    );
  } catch {
    /* observability must not throw */
  }
}

function salienceDelta(chunk: SalienceChunkInput, chunkId?: number): number {
  const mode = getSalienceMode();

  // Shadow probe: compute v2 even in shadow mode for telemetry,
  // but return 0 (no ranking effect).
  if (mode === "shadow") {
    try {
      shadowProbeSalience(calculateSalience(chunk), chunkId);
    } catch {
      /* probe must not throw */
    }
  }

  // A/B sentinel: opt-in dual-formula logging regardless of mode.
  // Cheap (2 pure-fn calls); skipped entirely when env flag absent.
  if (process.env.NOX_SALIENCE_AB_SHADOW === "1") {
    try {
      const sV2 = calculateSalience(chunk);
      const sLegacy = calculateSalienceLegacy(chunk);
      abShadowProbe(sV2, sLegacy, chunkId);
    } catch {
      /* probe must not throw */
    }
  }

  if (mode !== "active") return 0;
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
  access_count: number | null;
}

export function search(query: string, limit: number = 5): SearchResult[] {
  const db = getDb();
  const sanitized = query.replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  if (!sanitized) return [];

  // G10d: compute entity count once per query (amortised via cache, <1ms hot path).
  const { count: queryEntityCount } = countQueryEntities(query, db);

  let rows: FtsRow[];
  try {
    rows = db.prepare(`
      SELECT c.id, c.source_file, c.chunk_type, c.chunk_text, c.source_date,
             c.tier, c.source_type, c.section, c.section_boost,
             c.pain, c.importance, c.retention_days, c.created_at, c.last_accessed_at,
             c.access_count,
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
    boostSum += sourceTypeDelta(row.source_type, row.section, queryEntityCount);
    boostSum += sectionDelta(row.section, row.section_boost);
    boostSum += salienceDelta(row, row.id);

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
  access_count: number | null;
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

    // G10d: compute entity count once per query (shared cache with FTS path).
    const { count: queryEntityCount } = countQueryEntities(query, db);

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
               access_count, chunk_type
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
      boostSum += sourceTypeDelta(info?.source_type, info?.section, queryEntityCount);
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
          access_count: info.access_count,
          source_date: row.source_date,
        }, info.id);
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

  // D49 Phase 1 — temporal proximity rerank, shadow-mode opt-in.
  // Only activates if NOX_TEMPORAL_PATH=shadow|active. In shadow mode the
  // module computes the would-be rerank report but does NOT mutate `final`;
  // it emits one stderr JSON line (type=temporal_path) for telemetry.
  // Ranking semantics remain identical when env is unset or =off.
  if (process.env.NOX_TEMPORAL_PATH && process.env.NOX_TEMPORAL_PATH !== "off") {
    try {
      const { report } = rerankByTemporalProximity(final as unknown as Parameters<typeof rerankByTemporalProximity>[0], query);
      if (report.isTemporal) {
        const queryHash = createHash("sha1").update(query).digest("hex").slice(0, 12);
        logTemporalProbe(report, queryHash);
      }
    } catch (e) {
      // observability must never break ranking
      process.stderr.write(JSON.stringify({ type: "temporal_path_error", err: String(e) }) + "\n");
    }
  }

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
  DISABLE_MUTEX_SECTION_SOURCE_TYPE,
  // G10d conditional mutex
  MUTEX_QUERY_ENTITY_THRESHOLD,
  DISABLE_CONDITIONAL_MUTEX,
  tierDelta,
  sourceTypeDelta,
  sectionDelta,
  salienceDelta,
};
