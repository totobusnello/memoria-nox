/**
 * src/observability/collectors/db-stats.collector.ts
 *
 * Periodically samples DB state into gauges (db size, chunk counts).
 *
 * Schema dependencies (nox-mem v3.7):
 *   - chunks(id, provenance_kind)
 *   - kg_entities, kg_relations (counted via the dedicated collectors)
 *
 * The collector is DB-driver agnostic: callers inject `queryFn`. Production
 * wiring uses better-sqlite3; tests use an in-memory stub.
 */
import { statSync } from "node:fs";
import { dirname, join } from "node:path";
import { chunksActive, chunksStale, dbSizeBytes } from "../metrics.js";

export type DbQueryFn = (sql: string) => Array<Record<string, unknown>>;

export interface DbStatsCollectorOpts {
  dbPath: string;
  query: DbQueryFn;
  intervalMs?: number;
}

let intervalHandle: NodeJS.Timeout | undefined;

export function startDbStatsCollector(opts: DbStatsCollectorOpts): void {
  if (intervalHandle) return;
  const interval = opts.intervalMs ?? 30_000;
  const runOnce = () => {
    try {
      collectDbStats(opts);
    } catch {
      // never crash
    }
  };
  runOnce();
  intervalHandle = setInterval(runOnce, interval);
  intervalHandle.unref?.();
}

export function stopDbStatsCollector(): void {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = undefined;
  }
}

export function collectDbStats(opts: DbStatsCollectorOpts): void {
  // 1. DB file sizes (main + WAL + SHM).
  const sizes = readDbSizes(opts.dbPath);
  dbSizeBytes.set({ component: "main" }, sizes.main);
  dbSizeBytes.set({ component: "wal" }, sizes.wal);
  dbSizeBytes.set({ component: "shm" }, sizes.shm);

  // 2. Chunk counts. Provenance enum is small (~5 values) — bucket
  //    everything not 'stale' as "active".
  let active = 0;
  let stale = 0;
  try {
    const rows = opts.query(
      `SELECT provenance_kind, COUNT(*) AS n FROM chunks GROUP BY provenance_kind`,
    );
    for (const r of rows) {
      const kind = String((r as { provenance_kind: unknown }).provenance_kind ?? "");
      const n = Number((r as { n: unknown }).n ?? 0);
      if (kind === "stale") stale += n;
      else active += n;
    }
  } catch {
    // Schema may not exist yet — keep gauges at last value.
    return;
  }
  chunksActive.set(active);
  chunksStale.set(stale);
}

function readDbSizes(dbPath: string): { main: number; wal: number; shm: number } {
  const base = dbPath;
  const dir = dirname(base);
  // WAL / SHM are sibling files
  return {
    main: safeSize(base),
    wal: safeSize(join(dir, `${baseName(base)}-wal`)),
    shm: safeSize(join(dir, `${baseName(base)}-shm`)),
  };
}

function baseName(p: string): string {
  const idx = p.lastIndexOf("/");
  return idx >= 0 ? p.slice(idx + 1) : p;
}

function safeSize(p: string): number {
  try {
    return statSync(p).size;
  } catch {
    return 0;
  }
}
