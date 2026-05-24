// ingest-router.ts — STAGED STUB.
// Real implementation lives at src/lib/ingest-router.ts on the VPS — DO NOT replace.
// This stub exists only so reindex.ts compiles in isolation inside this staged dir.
import type Database from "better-sqlite3";

export interface RouteIngestOpts {
  externalDb?: Database.Database;
  skipDelete?: boolean;
}

export interface RouteIngestResult {
  chunks: number;
}

export async function routeIngest(
  _filePath: string,
  _opts?: RouteIngestOpts,
): Promise<RouteIngestResult> {
  // Stub: no-op.
  return { chunks: 0 };
}
