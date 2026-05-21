import { getDb } from "./db.js";
import { withOpAudit } from "./lib/op-audit.js";
import { routeIngest } from "./lib/ingest-router.js";
import { readdirSync } from "fs";
import { join, resolve } from "path";

const WORKSPACE = process.env.OPENCLAW_WORKSPACE || "/root/.openclaw/workspace";

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
  } catch {}
  return results;
}

async function _reindexImpl(): Promise<{ files: number; chunks: number }> {
  const db = getDb();

  // Load sqlite-vec extension BEFORE any DELETE/INSERT on chunks (2026-05-21 fix).
  // Root cause: trg_chunks_delete_cascade trigger references vec_chunks (sqlite-vec
  // virtual table). Without vec0 module loaded, `db.exec("DELETE FROM chunks")`
  // fails with `SqliteError: no such module: vec0`.
  // api-server.js loads sqlite-vec at startup; CLI (index.js) does not, so this
  // function would fail when invoked via `nox-mem reindex`. Fix is to load
  // extension defensively here — idempotent if already loaded.
  // Audit ref: audits/2026-05-21-opsAudit-investigation.md (issue #2)
  try {
    const sqliteVec = await import("sqlite-vec");
    sqliteVec.load(db);
  } catch (err) {
    console.error(`[reindex] WARN: failed to load sqlite-vec extension: ${err}`);
    console.error(`[reindex] Aborting — DELETE FROM chunks would cascade fail on vec_chunks trigger.`);
    throw new Error("sqlite-vec module not available; cannot safely reindex (vec_chunks trigger would fail)");
  }

  // Snapshot access metadata BEFORE clearing chunks so we can restore after reindex.
  // Key: source_file + chunk_text prefix (first 80 chars) for fuzzy matching.
  // This preserves tier promotions and access_count earned through actual usage.
  interface AccessSnapshot {
    chunk_text_prefix: string;
    tier: string;
    access_count: number;
    importance: number;
    last_accessed_at: string | null;
  }
  const accessSnapshot = new Map<string, AccessSnapshot>();
  const existingChunks = db
    .prepare("SELECT source_file, chunk_text, tier, access_count, importance, last_accessed_at FROM chunks WHERE access_count > 0 OR tier != 'peripheral'")
    .all() as Array<{ source_file: string; chunk_text: string; tier: string; access_count: number; importance: number; last_accessed_at: string | null }>;

  for (const row of existingChunks) {
    const key = `${row.source_file}::${row.chunk_text.substring(0, 80)}`;
    accessSnapshot.set(key, {
      chunk_text_prefix: row.chunk_text.substring(0, 80),
      tier: row.tier,
      access_count: row.access_count,
      importance: row.importance,
      last_accessed_at: row.last_accessed_at,
    });
  }
  console.log(`[reindex] Snapshot: ${accessSnapshot.size} chunks with access data preserved`);

  // Clear chunks but PRESERVE consolidated_files table
  db.exec("DELETE FROM chunks");
  db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");

  const memoryFiles = findFiles(resolve(WORKSPACE, "memory"), [".md", ".json"]);
  const sharedFiles = findFiles(resolve(WORKSPACE, "shared"), [".md"]);
  const allFiles = [...memoryFiles, ...sharedFiles];
  let totalChunks = 0;

  for (const file of allFiles) {
    try {
      // skipDelete=true since table is already cleared
      const result = await routeIngest(file, { externalDb: db, skipDelete: true });
      totalChunks += result.chunks;
      console.log(`[INFO] ${file}: ${result.chunks} chunks`);
    } catch (err) {
      console.error(`[ERROR] ${file}: ${err}`);
    }
  }

  // Restore access metadata for chunks that match the snapshot
  if (accessSnapshot.size > 0) {
    const restore = db.prepare(`
      UPDATE chunks
      SET tier = ?, access_count = ?, importance = ?, last_accessed_at = ?
      WHERE source_file = ? AND substr(chunk_text, 1, 80) = ?
    `);
    const restoreAll = db.transaction(() => {
      let restored = 0;
      for (const [key, snap] of accessSnapshot) {
        const [sourceFile] = key.split("::");
        const result = restore.run(
          snap.tier,
          snap.access_count,
          snap.importance,
          snap.last_accessed_at,
          sourceFile,
          snap.chunk_text_prefix,
        );
        if (result.changes > 0) restored++;
      }
      return restored;
    });
    const restored = restoreAll();
    console.log(`[reindex] Restored access metadata for ${restored}/${accessSnapshot.size} chunks`);
  }

  // 1.7b-c-core-preserve: core tier chunks are never_decay by contract.
  // Re-INSERT via ingestFile assigns retention_days from RETENTION_BY_TYPE,
  // so we must re-clear it after snapshot restore to honor the contract.
  // Fix B2 (2026-04-26): closeDb() removed from here — it invalidated the singleton mid-op,
  // causing withOpAudit final UPDATE to fail silently → 6 zombie rows in agent DBs 04-26.
  // CLI handler in index.ts owns lifecycle and closes after subcommand returns.
  db.exec("UPDATE chunks SET retention_days = NULL WHERE tier = 'core'");

  return { files: allFiles.length, chunks: totalChunks };
}

// A1 (2026-04-25): wrap with snapshot pré-op + audit log (CLAUDE.md regra #15)
// A5 (2026-04-25): dry-run mode preview do escopo sem mutar DB
// CODE HIGH #2 (audit 04-26): typed result avoids `as unknown as Promise<>` cast that hid drift.
interface ReindexResult { files: number; chunks: number; affected_rows?: number; notes?: string; dryRun?: boolean }
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
    console.log(JSON.stringify({
      dryRun: true,
      operation: "reindex",
      wouldDelete: { chunks: currentChunks, note: "all chunks, vec_chunks cascade-deleted via trigger" },
      wouldProcess: {
        totalFiles: allFiles.length,
        breakdown: { entityFiles, macDocsFiles, sharedFiles: sharedCount, otherMemoryFiles: otherMemory },
      },
      protected: { snapshotPreOp: "YES via withOpAudit", coreTierRetention: "YES", entityRouting: "YES via routeIngest" },
      estimatedDuration: "2-5 min depending on Gemini API latency",
    }, null, 2));
    return { files: allFiles.length, chunks: currentChunks, dryRun: true };
  }
  // Issue #3B (2026-05-21): db_source is now explicit — 'main' (prod nox-mem.db).
  return withOpAudit<ReindexResult>("reindex", { db_source: 'main' }, async () => {
    const result = await _reindexImpl();
    return { files: result.files, chunks: result.chunks, affected_rows: result.chunks, notes: `${result.files} files reindexed` };
  });
}
