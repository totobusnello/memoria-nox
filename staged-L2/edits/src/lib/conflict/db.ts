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
