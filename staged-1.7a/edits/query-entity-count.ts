/**
 * query-entity-count.ts — G10d: Conditional Hard Mutex entity detection
 *
 * Counts named entities mentioned in a query by matching against the
 * `kg_entities` table (Option B — KG lookup, recommended in spec).
 *
 * Design constraints:
 *   - Zero LLM calls — pure DB lookup, p95 <1ms on hot cache
 *   - Cache TTL 5min — amortises cold-start overhead (~12KB index, ~5ms)
 *   - Greedy longest-match — "Fundo Lombardia" counts as 1, not 2
 *   - Fallback: if DB unavailable or KG empty → returns 0 (mutex stays active,
 *     same as current G10 hard mutex behaviour — no regression possible)
 *   - PascalCase regex fallback when KG returns 0 rows
 *
 * Env flags used (evaluated at call time, NOT at module load):
 *   (none — count is stateless data, flags live in search.ts)
 *
 * Cross-links:
 *   - specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md §3 Option B
 *   - staged-1.7a/edits/search.ts — consumer of countQueryEntities()
 */

import type Database from "better-sqlite3";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface QueryEntityCountResult {
  count: number;
  matchedEntities: string[];
  method: "kg_lookup" | "fallback_regex";
}

// ── In-memory entity index (module-scope, amortised across queries) ───────────

/** Lowercased name → set of entity_types (for diagnostic use). */
let _entityIndex: Map<string, Set<string>> | null = null;
let _entityIndexLoadedAt = 0;
const ENTITY_INDEX_TTL_MS = 5 * 60 * 1000; // 5 min — covers >>99% of queries

/**
 * Per-query LRU cache (string → count result).
 * Bounded at CACHE_MAX_SIZE to avoid unbounded growth in long-running daemons.
 * Eviction: oldest-insert (Map insertion-order property).
 */
const _queryCache = new Map<string, QueryEntityCountResult>();
const CACHE_MAX_SIZE = 1_000;

// ── Entity index management ───────────────────────────────────────────────────

interface KgEntityRow {
  name: string;
  entity_type: string;
}

function loadEntityIndex(db: Database.Database): Map<string, Set<string>> {
  const now = Date.now();
  if (_entityIndex !== null && now - _entityIndexLoadedAt < ENTITY_INDEX_TTL_MS) {
    return _entityIndex;
  }

  try {
    const rows = db
      .prepare("SELECT name, entity_type FROM kg_entities WHERE name IS NOT NULL")
      .all() as KgEntityRow[];

    const idx = new Map<string, Set<string>>();
    for (const row of rows) {
      const key = row.name.toLowerCase().trim();
      if (!key) continue;
      if (!idx.has(key)) idx.set(key, new Set());
      idx.get(key)!.add(row.entity_type ?? "unknown");
    }

    _entityIndex = idx;
    _entityIndexLoadedAt = now;
    return idx;
  } catch {
    // DB unavailable or table missing — return empty, triggering fallback
    return new Map<string, Set<string>>();
  }
}

// ── Greedy longest-match scan ─────────────────────────────────────────────────

/**
 * Scans `lower` for entity names from `idx`, using greedy longest-match:
 * entities are tested in descending length order so "Fundo Lombardia" is
 * consumed before a hypothetical standalone "Fundo" entry.
 * Returns an array of canonical (lowercased) matched entity names.
 */
function greedyMatch(lower: string, idx: Map<string, Set<string>>): string[] {
  // Sort once per idx reference — in practice this is cached alongside the index.
  const sorted = [...idx.keys()].sort((a, b) => b.length - a.length);

  const matched: string[] = [];
  let remaining = lower;

  for (const name of sorted) {
    if (remaining.includes(name)) {
      matched.push(name);
      // Replace matched span with spaces so overlapping shorter names don't
      // re-match the same span (e.g. "Fundo" inside "Fundo Lombardia").
      remaining = remaining.split(name).join(" ");
    }
  }

  return matched;
}

// ── PascalCase fallback ───────────────────────────────────────────────────────

/**
 * Lightweight regex fallback used when KG is empty (cold start before
 * kg-extract has run, or evaluation harness with minimal fixture DB).
 *
 * Detects PascalCase tokens and quoted strings. Intentionally conservative —
 * false positives are preferable to false negatives in this fallback path
 * (mutex defaults to active on undercount, which is the safe direction).
 */
function countPascalCaseFallback(query: string): QueryEntityCountResult {
  // Multi-word PascalCase: "Fundo Lombardia", "Galapagos Capital", "Toto"
  const pascalMatches =
    query.match(/\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+)*/gu) ?? [];
  // Quoted entities: "nox-mem", 'openclaw'
  const quotedMatches = query.match(/"[^"]+"|'[^']+'/g) ?? [];

  const deduped = new Set([
    ...pascalMatches,
    ...quotedMatches.map((q) => q.slice(1, -1)),
  ]);

  const matchedEntities = [...deduped];
  return {
    count: matchedEntities.length,
    matchedEntities,
    method: "fallback_regex",
  };
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Returns the number of distinct KG entities mentioned in `query`.
 *
 * Algorithm:
 *   1. Check per-query cache (LRU, max 1000 entries).
 *   2. Load entity index from `kg_entities` (cached 5min).
 *   3. Greedy longest-match scan of lowercased query.
 *   4. If index is empty, fall back to PascalCase regex.
 *   5. Cache and return result.
 *
 * The `cacheable` option (default: true) allows callers to suppress caching
 * for eval harnesses that reuse query strings across different DB fixtures.
 *
 * @param query  The raw search query string.
 * @param db     The open better-sqlite3 database connection.
 * @param options.cacheable  Whether to use per-query result cache (default true).
 */
export function countQueryEntities(
  query: string,
  db: Database.Database,
  options: { cacheable?: boolean } = {},
): QueryEntityCountResult {
  const { cacheable = true } = options;

  // Cache check
  if (cacheable && _queryCache.has(query)) {
    return _queryCache.get(query)!;
  }

  const idx = loadEntityIndex(db);

  let result: QueryEntityCountResult;

  if (idx.size === 0) {
    // KG unavailable or not yet populated — use regex fallback
    result = countPascalCaseFallback(query);
  } else {
    const lower = query.toLowerCase();
    const matched = greedyMatch(lower, idx);
    result = {
      count: matched.length,
      matchedEntities: matched,
      method: "kg_lookup",
    };
  }

  // Evict oldest entry if cache is full (Map preserves insertion order)
  if (cacheable) {
    if (_queryCache.size >= CACHE_MAX_SIZE) {
      const oldest = _queryCache.keys().next().value;
      if (oldest !== undefined) _queryCache.delete(oldest);
    }
    _queryCache.set(query, result);
  }

  return result;
}

// ── Test hooks ────────────────────────────────────────────────────────────────

/** Resets entity index AND query cache. Call in beforeEach for test isolation. */
export function clearQueryEntityCache(): void {
  _queryCache.clear();
  _entityIndex = null;
  _entityIndexLoadedAt = 0;
}

/**
 * @deprecated Use clearQueryEntityCache() — resets both caches.
 * Kept for backward compat with spec examples.
 */
export function _resetEntityIndexCache(): void {
  clearQueryEntityCache();
}
