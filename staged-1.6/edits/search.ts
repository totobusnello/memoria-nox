import { createHash } from "crypto";
import { getDb } from "./db.js";
import { TIER_BOOST } from "./tier-manager.js";
import { expandQuery } from "./search-expansion.js";
import { dedupe } from "./search-dedup.js";

const BOOST_TYPES = new Set(["decision", "lesson", "person", "project", "pending"]);

export interface SearchResult {
  id?: number;
  score: number;
  source_file: string;
  chunk_type: string;
  chunk_text: string;
  source_date: string | null;
  tier?: string;
  match_type?: "fts" | "semantic" | "hybrid";
}

// ─── FTS5 search (keyword) ───────────────────────────────────────────────────

export function search(query: string, limit: number = 5): SearchResult[] {
  const db = getDb();
  const sanitized = query.replace(/['"{}()\[\]:*^~&|!]/g, " ").replace(/\s+/g, " ").trim();
  if (!sanitized) return [];

  let rows: Array<{
    id: number; source_file: string; chunk_type: string; chunk_text: string;
    source_date: string | null; rank: number; tier: string | null;
  }>;

  try {
    rows = db.prepare(`
      SELECT c.id, c.source_file, c.chunk_type, c.chunk_text, c.source_date,
             c.tier, bm25(chunks_fts, 1.0, 0.5, 0.5) as rank
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT 20
    `).all(sanitized) as typeof rows;
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
    // Tier boost
    const tier = (row.tier ?? "peripheral") as keyof typeof TIER_BOOST;
    score *= (TIER_BOOST[tier] ?? 1.0);
    return {
      id: row.id,
      score: Math.round(score * 100) / 100,
      source_file: row.source_file,
      chunk_type: row.chunk_type,
      chunk_text: row.chunk_text,
      source_date: row.source_date,
      tier: row.tier ?? "peripheral",
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
    db.prepare(`UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`).run(ts, ...ids);
  }

  return results;
}

// ─── Semantic search (vector) ────────────────────────────────────────────────

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

    // Fetch tier info for these chunk ids
    const chunkIds = rows.map((r) => r.chunk_id).filter(Boolean);
    const tierMap = new Map<number, { tier: string; id: number }>();
    if (chunkIds.length > 0) {
      const placeholders = chunkIds.map(() => "?").join(",");
      const tierRows = db.prepare(`SELECT id, tier FROM chunks WHERE id IN (${placeholders})`).all(...chunkIds) as Array<{ id: number; tier: string | null }>;
      for (const tr of tierRows) tierMap.set(tr.id, { tier: tr.tier ?? "peripheral", id: tr.id });
    }

    const maxDist = Math.max(...rows.map((r) => r.distance));
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

    const scored = rows.map((row) => {
      // Convert distance to score (lower distance = higher similarity)
      let score = maxDist > 0 ? (1 - row.distance / maxDist) * 10 : 10;
      if (BOOST_TYPES.has(row.chunk_type)) score *= 1.5;
      if (row.source_date && row.source_date >= sevenDaysAgo) score *= 1.2;
      // Tier boost
      const tierInfo = row.chunk_id ? tierMap.get(row.chunk_id) : undefined;
      const tier = (tierInfo?.tier ?? "peripheral") as keyof typeof TIER_BOOST;
      score *= (TIER_BOOST[tier] ?? 1.0);
      return {
        id: row.chunk_id,
        score: Math.round(score * 100) / 100,
        source_file: row.source_file,
        chunk_type: row.chunk_type,
        chunk_text: row.chunk_text,
        source_date: row.source_date,
        tier: tier,
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
      db.prepare(`UPDATE chunks SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN (${placeholders})`).run(ts, ...accessIds);
    }

    return semResults;
  } catch (err) {
    // Fallback to FTS if vector index not ready
    console.error("[WARN] Semantic search failed, falling back to FTS:", (err as Error).message);
    return search(query, limit);
  }
}

// ─── Hybrid search (FTS5 + semantic, expanded, RRF-fused, deduped) ──────────

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
  // Total time = max(expansion + variantFTS, originalFTS+semantic) — não bloqueia
  // a busca original atrás de uma chamada Gemini de 500-1500ms.
  const originalFtsPromise = Promise.resolve(search(query.trim(), perVariantLimit));
  const semPromise = searchSemantic(query.trim(), perVariantLimit * 2);
  const expansionPromise = expandQuery(query);

  const expansion = await expansionPromise;
  const variants = expansion.variants;

  // Variantes (excluindo a original, que já está rodando) → FTS apenas.
  const extraVariantFtsPromises = variants.slice(1).map((v) => Promise.resolve(search(v, perVariantLimit)));

  const allBatches = await Promise.all([
    originalFtsPromise,
    ...extraVariantFtsPromises,
    semPromise,
  ]);

  // Fuse via RRF. Rank dentro de CADA batch.
  const scoreMap = new Map<string, SearchResult & { rrfScore: number; saw_semantic: boolean }>();
  const semanticBatchIdx = allBatches.length - 1; // último é o semantic

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
    else if (v.saw_semantic && v.match_type === "semantic") {
      // check if same key also appeared in any fts batch
      // (cheap re-check: at least one fts batch has non-zero matches for this text)
    }
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
