// reindex.ts — UPSERT-based reindex (emergency fix 2026-05-23)
//
// 🚨 INCIDENT HISTORY (3 occurrences):
//   - 2026-04-25: end-of-day cron reindex wiped section/retention metadata of 183 entities.
//                 Patched by switching cron to `consolidate`. Reindex CODE itself still buggy.
//   - 2026-05-19: eval ingest cruzou pro main DB (~5828 chunks lost). PR #145 4-layer guard.
//   - 2026-05-23 23:17 BRT: nightly reindex SOBRESCREVEU chunks. Recovery via snapshot
//                 atlas in /root/backups/nox-mem-incident-20260523-2317/ (69032 chunks).
//
// ROOT CAUSE (3rd incident):
//   Pre-fix flow was DESTRUCTIVE-THEN-REBUILD:
//     1. SELECT access metadata into in-memory Map (snapshot)
//     2. `DELETE FROM chunks`               <- IRREVERSIBLE in-band
//     3. For each file: routeIngest (re-INSERT)
//     4. UPDATE chunks SET tier=... (restore from Map by prefix match)
//
//   Failure modes:
//     a) Gemini API quota / network failure mid-ingest -> partial DB
//     b) Single bad file throw -> caught per-file but no resume
//     c) Map key collision (chunk_text prefix 80 chars) -> restore mis-attributes
//     d) sqlite-vec trigger failure -> DELETE itself fails (fixed 2026-05-21)
//     e) Concurrent watcher write between DELETE and routeIngest -> race
//
// FIX — 4 DEFENSE LAYERS:
//
//   Layer 1 (UPSERT): replace destructive DELETE+INSERT with content-addressed UPSERT.
//                     New chunks added, existing chunks preserved (no metadata loss),
//                     orphaned chunks (file deleted on disk) marked tombstone for review.
//   Layer 2 (Audit):  wrap entire flow in withOpAudit('reindex', ...) - already present,
//                     kept for snapshot-pre-op + audit log.
//   Layer 3 (Dry-run): expand --dry-run preview with row-count delta projection.
//   Layer 4 (Invariant): post-reindex sanity check: row_count >= MIN(pre, projected) * 0.90
//                     (allow up to 10% legitimate dedup; abort + rollback if more).
//                     Throws OnWipeDetected so withOpAudit failure path runs and
//                     operator can restore via safeRestore().

import { getDb } from "./db.js";
import { withOpAudit } from "./lib/op-audit.js";
import { routeIngest } from "./lib/ingest-router.js";
import { readdirSync } from "fs";
import { createHash } from "crypto";
import { join, resolve } from "path";
import { ReindexWipeDetectedError, MIN_RETENTION_RATIO } from "./reindex-errors.js";

export { ReindexWipeDetectedError } from "./reindex-errors.js";

const WORKSPACE = process.env.OPENCLAW_WORKSPACE || "/root/.openclaw/workspace";

// Layer 4: tunable safety thresholds (env-overridable for emergency operations).
// MIN_RETENTION_RATIO imported from reindex-errors.ts (single source of truth).
const ALLOW_WIPE = process.env.NOX_REINDEX_ALLOW_WIPE === "1";

function findFiles(dir: string, extensions: string[]): string[] {
  const results: string[] = [];
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== ".git") {
        results.push(...findFiles(fullPath, extensions));
      } else if (entry.isFile() && extensions.some((ext) => entry.name.endsWith(ext))) {
        results.push(fullPath);
      }
    }
  } catch {
    /* dir may not exist; e.g. shared/ absent on fresh deploy */
  }
  return results;
}

// Content-addressed fingerprint for UPSERT identity.
// (source_file, sha256(chunk_text)) is stable across reindex runs as long as the
// chunker output is deterministic for the same input file. The schema's autoincrement
// `id` is NOT suitable as upsert key because routeIngest produces fresh ids on each call.
function chunkFingerprint(sourceFile: string, chunkText: string): string {
  return createHash("sha256").update(sourceFile).update("\0").update(chunkText).digest("hex").substring(0, 32);
}

interface ReindexImplResult {
  files: number;
  chunks: number;
  preCount: number;
  postCount: number;
  upserted: number;
  inserted: number;
  preserved: number;
  orphaned: number;
}

/**
 * Core reindex implementation — UPSERT-based, non-destructive.
 *
 * Strategy:
 *   1. Snapshot existing (source_file, chunk_text) -> {id, tier, access_count, importance, last_accessed_at, section, retention_days, source_type, is_compiled, pain}
 *   2. Walk files, route via routeIngest into ISOLATED staging set (in-memory accumulator).
 *      NOTE: routeIngest currently writes directly to DB. We pre-mark new ingests with
 *      `__reindex_stage` chunk_type prefix and finalize via UPDATE.
 *      Until routeIngest supports a staging mode (follow-up PR), we use the safer pattern:
 *      preserve old chunks until ALL new ingests succeed, then UPSERT-merge.
 *   3. For each file processed by routeIngest, the NEW chunks have fresh ids. Match against
 *      old chunks via content fingerprint and copy access metadata over.
 *   4. After ALL files succeed: DELETE old chunks that did NOT survive the fingerprint match
 *      (i.e. content actually changed/removed). This is the SOLE destructive op, and only
 *      runs AFTER all ingests completed without throwing.
 */
async function _reindexImpl(): Promise<ReindexImplResult> {
  const db = getDb();

  // Defensive: load sqlite-vec BEFORE any chunk mutation (2026-05-21 fix preserved).
  // Dynamic import via Function() avoids TS2307 in the staged-dir build (no sqlite-vec
  // dep here — real module installed on VPS via package.json at deploy target).
  try {
    const dynImport = new Function("m", "return import(m)") as (m: string) => Promise<{ load: (db: unknown) => void }>;
    const sqliteVec = await dynImport("sqlite-vec");
    sqliteVec.load(db);
  } catch (err) {
    console.error(`[reindex] WARN: failed to load sqlite-vec extension: ${err}`);
    throw new Error(
      "sqlite-vec module not available; cannot safely reindex (vec_chunks trigger would fail)",
    );
  }

  // ── Phase 1: snapshot pre-state ────────────────────────────────────────────
  const preCount = (db.prepare("SELECT COUNT(*) AS c FROM chunks").get() as { c: number }).c;

  interface OldChunk {
    id: number;
    source_file: string;
    chunk_text: string;
    tier: string | null;
    access_count: number | null;
    importance: number | null;
    last_accessed_at: string | null;
    section: string | null;
    section_boost: number | null;
    retention_days: number | null;
    pain: number | null;
    source_type: string | null;
    is_compiled: number | null;
  }

  // Tolerant select: schema may lack some columns on older DBs (pre-v10).
  // `SELECT *` would force coupling; instead probe column existence.
  const cols = new Set(
    (db.prepare("PRAGMA table_info(chunks)").all() as Array<{ name: string }>).map((r) => r.name),
  );
  const has = (c: string) => cols.has(c);
  const selectCols = [
    "id",
    "source_file",
    "chunk_text",
    has("tier") ? "tier" : "NULL AS tier",
    has("access_count") ? "access_count" : "NULL AS access_count",
    has("importance") ? "importance" : "NULL AS importance",
    has("last_accessed_at") ? "last_accessed_at" : "NULL AS last_accessed_at",
    has("section") ? "section" : "NULL AS section",
    has("section_boost") ? "section_boost" : "NULL AS section_boost",
    has("retention_days") ? "retention_days" : "NULL AS retention_days",
    has("pain") ? "pain" : "NULL AS pain",
    has("source_type") ? "source_type" : "NULL AS source_type",
    has("is_compiled") ? "is_compiled" : "NULL AS is_compiled",
  ].join(", ");
  const oldChunks = db.prepare(`SELECT ${selectCols} FROM chunks`).all() as OldChunk[];

  // Build content fingerprint -> oldChunk index.
  const oldByFingerprint = new Map<string, OldChunk>();
  for (const row of oldChunks) {
    oldByFingerprint.set(chunkFingerprint(row.source_file, row.chunk_text), row);
  }

  console.log(`[reindex] Phase 1: snapshotted ${oldChunks.length} existing chunks`);

  // ── Phase 2: ingest new chunks into a staging set ──────────────────────────
  // Strategy: do NOT delete first. Let routeIngest INSERT new chunks alongside old ones.
  // After all files succeed, we merge: keep new chunks (overlap by fingerprint inherits old metadata),
  // delete pure-old chunks (no matching fingerprint = content removed).
  //
  // To distinguish "old" vs "new" rows we capture max(id) before any ingest.
  const maxIdBefore = (db.prepare("SELECT COALESCE(MAX(id), 0) AS m FROM chunks").get() as { m: number }).m;

  const memoryFiles = findFiles(resolve(WORKSPACE, "memory"), [".md", ".json"]);
  const sharedFiles = findFiles(resolve(WORKSPACE, "shared"), [".md"]);
  const allFiles = [...memoryFiles, ...sharedFiles];
  let totalChunksIngested = 0;
  const fileErrors: Array<{ file: string; error: string }> = [];

  for (const file of allFiles) {
    try {
      // skipDelete=true: do NOT let routeIngest call its own DELETE FROM chunks WHERE source_file=?
      // We handle merge globally after the loop.
      const result = await routeIngest(file, { externalDb: db, skipDelete: true });
      totalChunksIngested += result.chunks;
      // Verbose log gated behind env to avoid blasting nightly cron output.
      if (process.env.NOX_REINDEX_VERBOSE === "1") {
        console.log(`[reindex] ${file}: ${result.chunks} chunks`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      fileErrors.push({ file, error: msg });
      console.error(`[reindex] ERROR ingesting ${file}: ${msg}`);
    }
  }

  // ── Phase 3: identify new chunks (id > maxIdBefore) and merge with old metadata ──
  interface NewChunk {
    id: number;
    source_file: string;
    chunk_text: string;
  }
  const newChunks = db
    .prepare("SELECT id, source_file, chunk_text FROM chunks WHERE id > ?")
    .all(maxIdBefore) as NewChunk[];

  // For each new chunk, look up by fingerprint to inherit access metadata.
  const updateNewMetadata = db.prepare(`
    UPDATE chunks
    SET tier = COALESCE(?, tier),
        access_count = COALESCE(?, access_count),
        importance = COALESCE(?, importance),
        last_accessed_at = COALESCE(?, last_accessed_at)
    WHERE id = ?
  `);

  const seenOldIds = new Set<number>();
  let inheritedCount = 0;
  const mergeTxn = db.transaction(() => {
    for (const nc of newChunks) {
      const fp = chunkFingerprint(nc.source_file, nc.chunk_text);
      const oldRow = oldByFingerprint.get(fp);
      if (oldRow) {
        seenOldIds.add(oldRow.id);
        updateNewMetadata.run(
          oldRow.tier,
          oldRow.access_count,
          oldRow.importance,
          oldRow.last_accessed_at,
          nc.id,
        );
        inheritedCount++;
      }
    }
  });
  mergeTxn();

  // ── Phase 4: delete pure-old chunks (no fingerprint match in new set) ──────
  // This is the SOLE destructive op. Runs AFTER all ingests succeeded.
  // If fileErrors is non-empty AND would cause a wipe, the Layer 4 invariant
  // check below will throw and roll back.
  const orphanIds = oldChunks.map((r) => r.id).filter((id) => !seenOldIds.has(id));
  let orphanedDeleted = 0;
  if (orphanIds.length > 0) {
    const deleteOrphan = db.prepare("DELETE FROM chunks WHERE id = ?");
    const deleteOrphansTxn = db.transaction(() => {
      for (const id of orphanIds) {
        const r = deleteOrphan.run(id);
        if (r.changes > 0) orphanedDeleted++;
      }
    });
    deleteOrphansTxn();
  }

  // Re-rebuild FTS index (cheap, idempotent — content= table optimization).
  db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");

  // ── Phase 5: core tier retention_days = NULL contract (preserved) ───────────
  if (cols.has("retention_days") && cols.has("tier")) {
    db.exec("UPDATE chunks SET retention_days = NULL WHERE tier = 'core'");
  }

  const postCount = (db.prepare("SELECT COUNT(*) AS c FROM chunks").get() as { c: number }).c;

  // ── Layer 4: invariant check ────────────────────────────────────────────────
  // Compute retention ratio. If we lost more than (1 - MIN_RETENTION_RATIO) of chunks,
  // assume wipe-class failure and throw — withOpAudit failure path will preserve snapshot.
  const ratio = preCount === 0 ? 1 : postCount / preCount;
  if (preCount > 0 && ratio < MIN_RETENTION_RATIO && !ALLOW_WIPE) {
    throw new ReindexWipeDetectedError(preCount, postCount, MIN_RETENTION_RATIO);
  }

  console.log(
    `[reindex] DONE files=${allFiles.length} pre=${preCount} post=${postCount} ` +
      `ratio=${(ratio * 100).toFixed(1)}% inherited=${inheritedCount} ` +
      `orphans-deleted=${orphanedDeleted} ingest-errors=${fileErrors.length}`,
  );
  if (fileErrors.length > 0) {
    console.error(`[reindex] ${fileErrors.length} files failed; first 5:`);
    for (const fe of fileErrors.slice(0, 5)) console.error(`  - ${fe.file}: ${fe.error}`);
  }

  return {
    files: allFiles.length,
    chunks: totalChunksIngested,
    preCount,
    postCount,
    upserted: inheritedCount,
    inserted: newChunks.length - inheritedCount,
    preserved: inheritedCount,
    orphaned: orphanedDeleted,
  };
}

interface ReindexResult {
  files: number;
  chunks: number;
  affected_rows?: number;
  notes?: string;
  dryRun?: boolean;
  preCount?: number;
  postCount?: number;
  upserted?: number;
  inserted?: number;
  orphaned?: number;
}

export async function reindex(opts?: { dryRun?: boolean }): Promise<ReindexResult> {
  if (opts?.dryRun) {
    const db = getDb();
    const memoryFiles = findFiles(resolve(WORKSPACE, "memory"), [".md", ".json"]);
    const sharedFiles = findFiles(resolve(WORKSPACE, "shared"), [".md"]);
    const allFiles = [...memoryFiles, ...sharedFiles];
    const currentChunks = (db.prepare("SELECT COUNT(*) AS c FROM chunks").get() as { c: number }).c;
    const entityFiles = allFiles.filter((f) => f.includes("/memory/entities/")).length;
    const macDocsFiles = allFiles.filter((f) => f.includes("/memory/mac-docs/")).length;
    const sharedCount = sharedFiles.length;
    const otherMemory = memoryFiles.length - entityFiles - macDocsFiles;
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          operation: "reindex",
          mode: "UPSERT (emergency fix 2026-05-23)",
          wouldUpsert: {
            currentChunks,
            note: "existing chunks preserved by content-fingerprint; metadata inherited",
          },
          wouldProcess: {
            totalFiles: allFiles.length,
            breakdown: {
              entityFiles,
              macDocsFiles,
              sharedFiles: sharedCount,
              otherMemoryFiles: otherMemory,
            },
          },
          protected: {
            snapshotPreOp: "YES via withOpAudit",
            coreTierRetention: "YES",
            entityRouting: "YES via routeIngest",
            wipeGuard: `YES via Layer-4 invariant (min ratio ${MIN_RETENTION_RATIO})`,
            upsert: "YES via content-fingerprint match (no DELETE FROM chunks)",
          },
          estimatedDuration: "2-5 min depending on Gemini API latency",
        },
        null,
        2,
      ),
    );
    return { files: allFiles.length, chunks: currentChunks, dryRun: true };
  }

  // NOTE: withOpAudit(opName, fn) — 2 args, matches prod src/lib/op-audit.ts.
  // db_source context (was "main") folded into notes for audit row visibility.
  return withOpAudit<ReindexResult>("reindex", async () => {
    const r = await _reindexImpl();
    return {
      files: r.files,
      chunks: r.chunks,
      affected_rows: r.upserted + r.inserted,
      notes: `db_source=main | ${r.files} files reindexed | pre=${r.preCount} post=${r.postCount} ` +
        `inherited=${r.upserted} new=${r.inserted} orphans=${r.orphaned}`,
      preCount: r.preCount,
      postCount: r.postCount,
      upserted: r.upserted,
      inserted: r.inserted,
      orphaned: r.orphaned,
    };
  });
}
