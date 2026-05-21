// E-lite-2 backfill CLI subcommand (E14 Wave 1 Fase 1, 2026-05-17)
// Wrapped in withOpAudit for snapshot pre-op + audit trail.
// SHADOW mode: populates chunks.fts_anchor column WITHOUT recreating FTS5
// virtual table. Active mode (Fase 2): drop+recreate chunks_fts indexing
// fts_anchor + update triggers.
//
// Spec: specs/2026-05-10-E14-retrieval-evolution.md Addendum B
//
// Usage:
//   nox-mem backfill-fts-anchor [--dry-run] [--limit N] [--batch-size N]

import { withOpAudit } from "./lib/op-audit.js";
import { getDb, closeDb } from "./db.js";
import { extractAnchors } from "./lib/fts-anchor.js";

export interface BackfillOpts {
  dryRun?: boolean;
  limit?: number;
  batchSize?: number;
  force?: boolean;
}

export interface BackfillResult {
  totalChunks: number;
  processed: number;
  withAnchors: number;
  withoutAnchors: number;
  meanTerms: number;
  durationMs: number;
}

export async function backfillFtsAnchor(opts: BackfillOpts = {}): Promise<BackfillResult> {
  const batchSize = opts.batchSize ?? 2000;
  const dryRun = opts.dryRun ?? false;
  const t0 = Date.now();

  const exec = async (): Promise<BackfillResult> => {
    const db = getDb();
    const totalQ = opts.force ? "SELECT COUNT(*) AS n FROM chunks" : "SELECT COUNT(*) AS n FROM chunks WHERE fts_anchor IS NULL OR fts_anchor = ''";
    const totalRow = db.prepare(totalQ).get() as { n: number };
    const totalChunks = totalRow.n;
    const cap = opts.limit ? Math.min(totalChunks, opts.limit) : totalChunks;

    let processed = 0;
    let withAnchors = 0;
    let withoutAnchors = 0;
    let totalTerms = 0;

    const selectStmt = opts.force
      ? db.prepare("SELECT id, chunk_text FROM chunks ORDER BY id ASC LIMIT ? OFFSET ?")
      : db.prepare("SELECT id, chunk_text FROM chunks WHERE fts_anchor IS NULL OR fts_anchor = '' ORDER BY id ASC LIMIT ?");
    const updateStmt = db.prepare("UPDATE chunks SET fts_anchor = ? WHERE id = ?");

    while (processed < cap) {
      const remaining = cap - processed;
      const fetchSize = Math.min(batchSize, remaining);
      const batch = (opts.force
        ? selectStmt.all(fetchSize, processed)
        : selectStmt.all(fetchSize)) as Array<{ id: number; chunk_text: string }>;
      if (batch.length === 0) break;

      const updates: Array<[string, number]> = [];
      for (const { id, chunk_text } of batch) {
        const anchors = extractAnchors(chunk_text);
        const terms = anchors ? anchors.split(" ").length : 0;
        if (anchors) withAnchors++;
        else withoutAnchors++;
        totalTerms += terms;
        updates.push([anchors, id]);
      }

      if (!dryRun) {
        const tx = db.transaction((items: Array<[string, number]>) => {
          for (const [anchors, id] of items) updateStmt.run(anchors, id);
        });
        tx(updates);
      }
      processed += batch.length;

      if (processed % 5000 === 0 || processed === cap) {
        const pct = ((processed / cap) * 100).toFixed(1);
        console.log(`[backfill-fts-anchor] ${processed}/${cap} (${pct}%) — withAnchors=${withAnchors} mean=${(totalTerms / processed).toFixed(1)}`);
      }
    }

    return {
      totalChunks,
      processed,
      withAnchors,
      withoutAnchors,
      meanTerms: processed > 0 ? totalTerms / processed : 0,
      durationMs: Date.now() - t0,
    };
  };

  if (dryRun) {
    console.log("[backfill-fts-anchor] DRY-RUN mode — no UPDATEs will be executed");
    return await exec();
  }

  // Wrap in withOpAudit for snapshot + audit trail.
  // Issue #3B (2026-05-21): db_source is now explicit — 'main' (prod nox-mem.db).
  const auditResult = await withOpAudit("backfill-fts-anchor-shadow", { db_source: 'main' }, async () => {
    const r = await exec();
    return {
      affected_rows: r.processed,
      notes: `withAnchors=${r.withAnchors} withoutAnchors=${r.withoutAnchors} meanTerms=${r.meanTerms.toFixed(2)} batchSize=${batchSize} limit=${opts.limit ?? "all"}`,
    };
  });

  console.log(`[backfill-fts-anchor] op-audit success — affected=${auditResult.affected_rows} notes=${auditResult.notes}`);
  // exec ran inside withOpAudit but result not exposed; re-query DB for final stats
  const db = getDb();
  const finalRow = db.prepare(
    "SELECT COUNT(*) AS n, COUNT(CASE WHEN fts_anchor != '' THEN 1 END) AS with_a FROM chunks"
  ).get() as { n: number; with_a: number };
  return {
    totalChunks: finalRow.n,
    processed: auditResult.affected_rows ?? 0,
    withAnchors: finalRow.with_a,
    withoutAnchors: finalRow.n - finalRow.with_a,
    meanTerms: 0, // approximate; real value in audit notes
    durationMs: Date.now() - t0,
  };
}
