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
}

// ─── Path → source_type mapping (canonical, audit 2026-05-19) ─────────────────
// Order matters: first match wins. Most specific patterns first.

const PATTERNS: Array<[RegExp, string]> = [
  [/\/entities\//, "entity"],
  [/\/cache\/ocr\//, "ocr-cache"],
  [/\/sessions\//, "session"],
  [/\/shared\/imports\/Claude\/skills\//, "skill"],
  [/\/shared\/imports\/Claude\/commands\//, "command"],
  [/\/shared\/lex-biblioteca\//, "legal-template"],
  [/\/Claude\/Projetos\//, "project-doc"],
  [/\/memory\/mac-docs\//, "personal-doc"],
  [/\/memory\/lessons\/|-lessons\.md$/, "lesson"],
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

    const selectStmt = force
      ? db.prepare("SELECT id, source_file FROM chunks ORDER BY id ASC LIMIT ? OFFSET ?")
      : db.prepare(
          "SELECT id, source_file FROM chunks WHERE source_type IS NULL OR source_type = '' ORDER BY id ASC LIMIT ?",
        );
    const updateStmt = db.prepare(
      "UPDATE chunks SET source_type = ?, updated_at = datetime('now') WHERE id = ?",
    );

    while (processed < cap) {
      const remaining = cap - processed;
      const fetchSize = Math.min(batchSize, remaining);
      const batch = (force
        ? selectStmt.all(fetchSize, processed)
        : selectStmt.all(fetchSize)) as Array<{ id: number; source_file: string }>;
      if (batch.length === 0) break;

      const updates: Array<[string, number]> = [];
      for (const { id, source_file } of batch) {
        const stype = classifyPath(source_file);
        byType[stype] = (byType[stype] ?? 0) + 1;
        updates.push([stype, id]);
      }

      if (!dryRun) {
        const tx = db.transaction((items: Array<[string, number]>) => {
          for (const [stype, id] of items) updateStmt.run(stype, id);
        });
        tx(updates);
      }
      processed += batch.length;

      if (processed % 10000 === 0 || processed === cap) {
        const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
        console.error(
          `[backfill-source-type] ${dryRun ? "DRY-RUN " : ""}${processed}/${cap} chunks (${elapsed}s)`,
        );
      }
    }

    return {
      totalChunks,
      processed,
      byType,
      durationMs: Date.now() - t0,
      dryRun,
    };
  };

  // Dry-run skips withOpAudit (no mutation → no snapshot needed).
  if (dryRun) {
    return await exec();
  }

  // Wrap mutation in withOpAudit per CLAUDE.md rule #6.
  return await withOpAudit("backfill-source-type", exec);
}

// ─── CLI entry-point glue (wired by src/index.ts) ─────────────────────────────

export function parseArgs(argv: string[]): BackfillSourceTypeOpts {
  const opts: BackfillSourceTypeOpts = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--force") opts.force = true;
    else if (a === "--limit" && argv[i + 1]) {
      opts.limit = Number.parseInt(argv[++i]!, 10);
    } else if (a === "--batch-size" && argv[i + 1]) {
      opts.batchSize = Number.parseInt(argv[++i]!, 10);
    }
  }
  return opts;
}

export function formatResult(r: BackfillSourceTypeResult): string {
  const lines: string[] = [];
  lines.push(
    `${r.dryRun ? "[DRY-RUN] " : ""}Backfill complete: ${r.processed}/${r.totalChunks} chunks in ${(r.durationMs / 1000).toFixed(1)}s`,
  );
  lines.push("");
  lines.push("Distribution:");
  const entries = Object.entries(r.byType).sort((a, b) => b[1] - a[1]);
  const maxLabel = Math.max(...entries.map(([k]) => k.length));
  for (const [type, count] of entries) {
    const pct = ((count * 100) / r.processed).toFixed(2);
    lines.push(`  ${type.padEnd(maxLabel)}  ${String(count).padStart(7)}  (${pct}%)`);
  }
  return lines.join("\n");
}
