// Type-only stubs for staged-1.7a/edits/search.ts.
//
// search.ts imports from modules that live in the VPS module graph
// (`./db.js`, `./tier-manager.js`, `./search-expansion.js`, `./search-dedup.js`,
// `./embed.js`) and are not part of this staged patch. These shims exist solely
// so we can run `tsc --noEmit` on search.ts in CI without checking out the
// entire VPS src/ tree.
//
// At deploy time the staged file lands inside the VPS src/ dir and resolves
// against the real implementations.

declare module "*/db.js" {
  // Minimal subset of better-sqlite3 we use.
  interface Statement {
    all(...params: unknown[]): unknown[];
    run(...params: unknown[]): unknown;
  }
  interface Database {
    prepare(sql: string): Statement;
    exec(sql: string): void;
  }
  export function getDb(): Database;
  export function closeDb(): void;
  export function checkLargeDbIngestGuard(): void;
}

declare module "*/tier-manager.js" {
  export const TIER_BOOST: Record<string, number>;
  export function getTierStats(): unknown;
  export function evaluateTiers(): unknown;
}

declare module "*/search-expansion.js" {
  export interface ExpansionResult {
    variants: string[];
    reason?: string;
  }
  export function expandQuery(query: string): Promise<ExpansionResult>;
}

declare module "*/search-dedup.js" {
  import type { SearchResult } from "../edits/search.js";
  export function dedupe(results: SearchResult[], limit: number): SearchResult[];
}

declare module "*/embed.js" {
  interface VectorRow {
    chunk_id: number;
    source_file: string;
    chunk_type: string;
    chunk_text: string;
    source_date: string | null;
    distance: number;
  }
  export function embedText(text: string): Promise<number[]>;
  export function semanticSearch(
    db: unknown,
    embedding: number[],
    limit: number,
  ): VectorRow[];
  export function ensureVecTable(db: unknown): void;
  export function countEmbedded(db: unknown): number;
}
