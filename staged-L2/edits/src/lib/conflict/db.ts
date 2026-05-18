/**
 * Minimal DB abstraction for L2 staged code.
 *
 * The production codebase wires better-sqlite3 directly. To keep this staged
 * package zero-dependency for tests (and avoid forcing a `npm install` to run
 * the test suite), we expose a tiny interface that matches the better-sqlite3
 * `Statement`/`Database` shape. Real callers pass `Database.prototype` from
 * better-sqlite3; tests pass a synchronous in-memory fake (see
 * `__tests__/fakes.ts`).
 */

export interface RunResult {
  changes: number;
  lastInsertRowid: number | bigint;
}

export interface PreparedStatement {
  run(...params: unknown[]): RunResult;
  get(...params: unknown[]): unknown;
  all(...params: unknown[]): unknown[];
  iterate?(...params: unknown[]): IterableIterator<unknown>;
}

export interface DBHandle {
  prepare(sql: string): PreparedStatement;
  exec(sql: string): void;
  transaction?<T>(fn: () => T): () => T;
  pragma?(query: string): unknown;
}

// ─── Singleton factory (adapter apply step) ────────────────────────────────
// Wire-up.ts resolves `lib/conflict/db.js::getConflictDb()`. The singleton
// lives in the staged-wire-up-adapters layer; we re-export it here so the
// `tryImport("../lib/conflict/db.js")` call in wire-up.ts finds the symbol.
//
// `ensureConflictDb()` MUST be awaited during API boot to pre-warm the
// async better-sqlite3 open before the first synchronous `getConflictDb()`
// call. Without it, the first request arrives before warmup() resolves and
// getConflictDb() returns null → wire-up emits 503 not_implemented.
export {
  getConflictDb,
  ensureConflictDb,
  resetConflictDbForTests,
  __setConflictDbForTests,
} from "./db-singleton.js";
