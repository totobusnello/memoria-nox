// backfill-source-type.ts — Populate `source_type` column for legacy chunks
// (Task F, 2026-05-19; companion to PR #150 salience refactor)
//
// Motivation: G4 ablation A5 (source_type_boost only) = 0.4817 = A0 baseline (no boosts)
// → SOURCE_TYPE_BOOST is INERT. Audit 2026-05-19 found 67,949 chunks (98.48%) with
// `source_type IS NULL`. This script derives source_type from `source_file` path
// patterns and backfills in batches.
//
// Wrapped in withOpAudit (CLAUDE.md rule #6) — snapshot pre-op + audit row.
//
// Mapping defined in docs/audits/2026-05-19-source-type-backfill-mapping.md.
//
// Usage:
//   nox-mem backfill-source-type [--dry-run] [--limit N] [--batch-size N] [--force]
//
//   --dry-run      Preview counts per source_type, no mutation
//   --limit N      Process at most N chunks
//   --batch-size N Transaction size (default 2000)
//   --force        Overwrite existing source_type values (NOT just NULL/empty)

import { withOpAudit } from "./lib/op-audit.js";
import { getDb } from "./db.js";

export interface BackfillSourceTypeOpts {
  dryRun?: boolean;
  limit?: number;
  batchSize?: number;
  force?: boolean;
}

export interface BackfillSourceTypeResult {
  totalChunks: number;
  processed: number;
  byType: Record<string, number>;
  durationMs: number;
  dryRun: boolean;
  // OpResult compatibility fields (consumed by withOpAudit<T extends OpResult>):
  affected_rows?: number;
  notes?: string;
}

// ─── Path → source_type mapping (canonical, audit 2026-05-19) ─────────────────
// Order matters: first match wins. Most specific patterns first.
// Each alternative is its own entry to avoid regex operator-precedence
// ambiguity (CodeQL js/regex/missing-regexp-anchor).

// `(?:^|\/)<prefix>\/` matches the prefix at start-of-string OR after any
// path separator. This handles BOTH relative paths (e.g. `sessions/foo.md`)
// AND nested paths (e.g. `memory/sessions/foo.md`). Empirical fix discovered
// during initial dry-run 2026-05-19 22:36 BRT — prior `\/<prefix>\/` only
// matched nested paths, missing 99% of corpus rooted at relative prefixes.
export const PATTERNS: Array<[RegExp, string]> = [
  [/(?:^|\/)entities\//, "entity"],
  [/(?:^|\/)cache\/ocr\//, "ocr-cache"],
  [/(?:^|\/)sessions\//, "session"],
  [/(?:^|\/)shared\/imports\/Claude\/skills\//, "skill"],
  [/(?:^|\/)shared\/imports\/Claude\/commands\//, "command"],
  [/(?:^|\/)shared\/lex-biblioteca\//, "legal-template"],
  [/(?:^|\/)Claude\/Projetos\//, "project-doc"],
  [/(?:^|\/)memory\/mac-docs\//, "personal-doc"],
  [/(?:^|\/)memory\/lessons\//, "lesson"],
  [/-lessons\.md$/, "lesson"],
  [/\.md$/, "note"],
];

const FALLBACK_TYPE = "other";

export function classifyPath(sourceFile: string): string {
  if (!sourceFile) return FALLBACK_TYPE;
  for (const [rx, type] of PATTERNS) {
    if (rx.test(sourceFile)) return type;
  }
  return FALLBACK_TYPE;
}

// ─── Main entry ───────────────────────────────────────────────────────────────

export async function backfillSourceType(
  opts: BackfillSourceTypeOpts = {},
): Promise<BackfillSourceTypeResult> {
  const batchSize = opts.batchSize ?? 2000;
  const dryRun = opts.dryRun ?? false;
  const force = opts.force ?? false;
  const t0 = Date.now();

  const exec = async (): Promise<BackfillSourceTypeResult> => {
    const db = getDb();

    const totalQ = force
      ? "SELECT COUNT(*) AS n FROM chunks"
      : "SELECT COUNT(*) AS n FROM chunks WHERE source_type IS NULL OR source_type = ''";
    const totalRow = db.prepare(totalQ).get() as { n: number };
    const totalChunks = totalRow.n;
    const cap = opts.limit ? Math.min(totalChunks, opts.limit) : totalChunks;

    const byType: Record<string, number> = {};
    let processed = 0;

    // BOTH modes use keyset pagination (WHERE id > :lastId) for two reasons:
    //   1. Avoid OFFSET skew under concurrent ingest watcher (review HIGH #1)
    //   2. dry-run safety: without keyset, non-force dry-run re-queries the
    //      same NULL-filtered batch forever (bug found empirically 2026-05-19 22:42).
    //      In APPLY mode UPDATE removes rows from filter so old approach worked
    //      by accident; in dry-run the filter never shrinks so iteration repeats.
    // `--force`: overwrite ALL non-'external' rows (preserves curated values).
    const selectStmt = force
      ? db.prepare(
          "SELECT id, source_file FROM chunks WHERE id > ? AND (source_type IS NULL OR source_type != 'external') ORDER BY id ASC LIMIT ?",
        )
      : db.prepare(
          "SELECT id, source_file FROM chunks WHERE id > ? AND (source_type IS NULL OR source_type = '') ORDER BY id ASC LIMIT ?",
        );
    // NOTE: do NOT touch updated_at — column-correction migration, not user
    //   activity. Bulk-stamping 67k chunks corrupts recency signal in salience.
    // The `AND (source_type IS NULL OR source_type != 'external')` guard
    //   preserves curated 'external' values even under --force (review MEDIUM #6).
    const updateStmt = db.prepare(
      "UPDATE chunks SET source_type = ? WHERE id = ? AND (source_type IS NULL OR source_type != 'external')",
    );

    // Keyset pagination cursor (both modes).
    let lastId = 0;
    let nextHeartbeat = 10000;

    while (processed < cap) {
      const remaining = cap - processed;
      const fetchSize = Math.min(batchSize, remaining);
      const batch = selectStmt.all(lastId, fetchSize) as Array<{ id: number; source_file: string }>;
      if (batch.length === 0) break;

      const updates: Array<[string, number]> = [];
      for (const { id, source_file } of batch) {
        const stype = classifyPath(source_file);
        byType[stype] = (byType[stype] ?? 0) + 1;
        updates.push([stype, id]);
        if (id > lastId) lastId = id;
      }

      if (!dryRun) {
        const tx = db.transaction((items: Array<[string, number]>) => {
          for (const [stype, id] of items) updateStmt.run(stype, id);
        });
        tx(updates);
      }
      processed += batch.length;

      // Heartbeat every ~10k rows regardless of batchSize (review LOW heartbeat fix).
      if (processed >= nextHeartbeat || processed === cap) {
        const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
        console.error(
          `[backfill-source-type] ${dryRun ? "DRY-RUN " : ""}${processed}/${cap} chunks (${elapsed}s)`,
        );
        nextHeartbeat = Math.ceil((processed + 1) / 10000) * 10000;
      }
    }

    return {
      totalChunks,
      processed,
      byType,
      durationMs: Date.now() - t0,
      dryRun,
      // OpResult fields — populated for audit log clarity:
      affected_rows: dryRun ? 0 : processed,
      notes: `backfill-source-type ${dryRun ? "DRY-RUN" : "applied"} (force=${force}, batch=${batchSize})`,
    };
  };

  // Dry-run skips withOpAudit (no mutation → no snapshot needed).
  if (dryRun) {
    return await exec();
  }

  // Wrap mutation in withOpAudit per CLAUDE.md rule #6.
  return await withOpAudit("backfill-source-type", { db_source: 'main' }, exec);
}

// ─── CLI entry-point glue (wired by src/index.ts) ─────────────────────────────

export function parseArgs(argv: string[]): BackfillSourceTypeOpts {
  const opts: BackfillSourceTypeOpts = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--force") opts.force = true;
    else if (a === "--limit" && argv[i + 1]) {
      const raw = argv[++i]!;
      const n = Number.parseInt(raw, 10);
      if (!Number.isFinite(n) || n <= 0) {
        throw new Error(`--limit requires positive integer, got: '${raw}'`);
      }
      opts.limit = n;
    } else if (a === "--batch-size" && argv[i + 1]) {
      const raw = argv[++i]!;
      const n = Number.parseInt(raw, 10);
      if (!Number.isFinite(n) || n <= 0) {
        throw new Error(`--batch-size requires positive integer, got: '${raw}'`);
      }
      opts.batchSize = n;
    }
  }
  return opts;
}

export function formatResult(r: BackfillSourceTypeResult): string {
  if (r.processed === 0) {
    return `${r.dryRun ? "[DRY-RUN] " : ""}No chunks to process (totalChunks=${r.totalChunks})`;
  }
  const lines: string[] = [];
  lines.push(
    `${r.dryRun ? "[DRY-RUN] " : ""}Backfill complete: ${r.processed}/${r.totalChunks} chunks in ${(r.durationMs / 1000).toFixed(1)}s`,
  );
  lines.push("");
  lines.push("Distribution:");
  const entries = Object.entries(r.byType).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    lines.push("  (empty)");
    return lines.join("\n");
  }
  const maxLabel = Math.max(...entries.map(([k]) => k.length));
  for (const [type, count] of entries) {
    const pct = ((count * 100) / r.processed).toFixed(2);
    lines.push(`  ${type.padEnd(maxLabel)}  ${String(count).padStart(7)}  (${pct}%)`);
  }
  return lines.join("\n");
}
