/**
 * src/lib/dates.ts — flexible date parsing for temporal search filters (P3)
 *
 * Accepted formats:
 *   ISO 8601 full:   "2026-05-01T00:00:00Z"
 *   ISO 8601 date:   "2026-05-01"
 *   Relative:        "7d" | "1w" | "30d" | "2h" | "15m"
 *
 * NOTE: "1mo" is NOT supported in v1 — use "30d". Document for callers.
 *
 * Throws on unparseable input with a clear message.
 */

const RELATIVE_RE = /^(\d+)(m|h|d|w)$/i;

export function parseFlexibleDate(input: string): Date {
  const trimmed = input.trim();
  if (!trimmed) throw new Error(`temporal: empty date string`);

  // ── Relative durations ─────────────────────────────────────────────────────
  const rel = RELATIVE_RE.exec(trimmed);
  if (rel) {
    const n = parseInt(rel[1], 10);
    const unit = rel[2].toLowerCase();
    const msMap: Record<string, number> = {
      m: 60_000,
      h: 3_600_000,
      d: 86_400_000,
      w: 604_800_000,
    };
    if (!(unit in msMap)) {
      throw new Error(`temporal: unsupported relative unit "${unit}" in "${input}". Use: m, h, d, w`);
    }
    return new Date(Date.now() - n * msMap[unit]);
  }

  // ── ISO 8601 (full or date-only) ───────────────────────────────────────────
  // Date-only: append T00:00:00Z to avoid local-timezone ambiguity
  const normalised =
    /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? `${trimmed}T00:00:00Z` : trimmed;

  const d = new Date(normalised);
  if (isNaN(d.getTime())) {
    throw new Error(
      `temporal: cannot parse date "${input}". ` +
      `Accepted: ISO 8601 ("2026-05-01" or "2026-05-01T00:00:00Z") ` +
      `or relative ("7d", "1w", "2h", "15m"). Note: "1mo" not supported — use "30d".`
    );
  }
  return d;
}

/**
 * Convert a Date to SQLite-compatible ISO string ("YYYY-MM-DDTHH:MM:SS.sssZ").
 * SQLite stores datetimes as text; this format sorts lexicographically correct.
 */
export function toSqliteTs(d: Date): string {
  return d.toISOString();
}
