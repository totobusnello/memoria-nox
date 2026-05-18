/**
 * src/lib/confidence/search-filter.ts — opt-in `--min-confidence` filter.
 *
 * Wired into search via CLI flag `--min-confidence 0.5`, HTTP query param
 * `min_confidence=0.5`, MCP arg `min_confidence: 0.5`.
 *
 * Default: undefined (no filter). When set, chunks with confidence < threshold
 * are removed from the search result set BEFORE ranking. This is purely
 * additive and DOES NOT depend on NOX_RANKING_CONFIDENCE mode — caller-side
 * choice, useful for "show me only high-trust facts" client UX.
 *
 * Threshold range: [0.0, 1.0]. Out-of-range values are clamped (loose
 * validation; we never want to drop entire results due to typo).
 */

export interface SearchResultWithConfidence {
  chunk_id: number;
  confidence?: number | null;
  [key: string]: unknown;
}

export interface SearchFilterOpts {
  /** Minimum confidence to include. undefined = no filter. */
  min_confidence?: number | null;
  /** If true, also exclude chunks with NULL confidence (default false — NULL passes). */
  exclude_null?: boolean;
  /** If true, exclude superseded chunks (default false). */
  exclude_superseded?: boolean;
  /** If true, exclude refuted (provenance=user-marked + low conf) chunks (default false). */
  exclude_refuted?: boolean;
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.min(1, Math.max(0, v));
}

/** Validates + normalises the threshold. Returns undefined to skip filtering. */
export function parseMinConfidence(
  raw: number | string | undefined | null
): number | undefined {
  if (raw === undefined || raw === null) return undefined;
  let n: number;
  if (typeof raw === "number") n = raw;
  else {
    const parsed = parseFloat(raw);
    if (!Number.isFinite(parsed)) return undefined;
    n = parsed;
  }
  return clamp01(n);
}

/** Apply filter to a result set. Returns new array — does not mutate input. */
export function filterByConfidence<T extends SearchResultWithConfidence>(
  results: T[],
  opts: SearchFilterOpts = {}
): T[] {
  const threshold = opts.min_confidence ?? undefined;
  const excludeNull = opts.exclude_null === true;
  const excludeSuperseded = opts.exclude_superseded === true;
  const excludeRefuted = opts.exclude_refuted === true;

  if (
    threshold === undefined &&
    !excludeNull &&
    !excludeSuperseded &&
    !excludeRefuted
  ) {
    return results; // no-op
  }

  return results.filter((r) => {
    const conf = r.confidence;
    const confIsNull = conf === null || conf === undefined;

    if (excludeNull && confIsNull) return false;

    if (threshold !== undefined) {
      if (confIsNull) {
        // NULL counts as 0.8 baseline (DB default before v19); allow through
        // unless excludeNull also requested.
        if (0.8 < threshold) return false;
      } else if ((conf as number) < threshold) {
        return false;
      }
    }

    if (excludeSuperseded) {
      const sb = (r as { superseded_by?: number | null }).superseded_by;
      if (sb !== null && sb !== undefined) return false;
    }

    if (excludeRefuted) {
      const kind = (r as { provenance_kind?: string | null }).provenance_kind;
      const c = confIsNull ? 0.8 : (conf as number);
      if (kind === "user-marked" && c < 0.3) return false;
    }

    return true;
  });
}

/**
 * Convenience: build the SQL WHERE clause fragment for direct DB-level
 * filtering (more efficient than client-side). Returns null if no filter.
 *
 * Example output:
 *   { sql: "AND chunks.confidence >= ?", params: [0.5] }
 */
export function buildConfidenceWhereClause(
  opts: SearchFilterOpts
): { sql: string; params: unknown[] } | null {
  const fragments: string[] = [];
  const params: unknown[] = [];

  if (opts.min_confidence !== undefined && opts.min_confidence !== null) {
    fragments.push(
      "(chunks.confidence >= ? OR (chunks.confidence IS NULL AND 0.8 >= ?))"
    );
    params.push(opts.min_confidence, opts.min_confidence);
  }

  if (opts.exclude_null) {
    fragments.push("chunks.confidence IS NOT NULL");
  }

  if (opts.exclude_superseded) {
    fragments.push("chunks.superseded_by IS NULL");
  }

  if (opts.exclude_refuted) {
    fragments.push(
      "NOT (chunks.provenance_kind = 'user-marked' AND chunks.confidence < 0.3)"
    );
  }

  if (fragments.length === 0) return null;
  return { sql: " AND " + fragments.join(" AND "), params };
}
