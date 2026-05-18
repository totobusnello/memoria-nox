/**
 * src/lib/confidence/db-shim.ts — minimal Database surface used by the L3
 * implementation. Mirrors better-sqlite3's `Database`, `Statement` so that the
 * staged module compiles without depending on the runtime driver.
 *
 * Production callers pass a real `better-sqlite3` `Database` here; the
 * interface is structurally compatible.
 */

export interface DbStatement {
  run(...params: unknown[]): { changes: number; lastInsertRowid: number | bigint };
  get<T = unknown>(...params: unknown[]): T | undefined;
  all<T = unknown>(...params: unknown[]): T[];
  iterate<T = unknown>(...params: unknown[]): Iterable<T>;
}

export interface Db {
  prepare(sql: string): DbStatement;
  exec(sql: string): void;
  transaction<T extends (...args: unknown[]) => unknown>(fn: T): T;
  pragma(sql: string, opts?: { simple?: boolean }): unknown;
  close?: () => void;
}

/** In-memory mock DB for tests. Implements a tiny subset of behaviour. */
export class MockDb implements Db {
  rows: Map<string, Record<string, unknown>[]> = new Map();
  audit: Record<string, unknown>[] = [];
  private idCounter = 1;

  prepare(sql: string): DbStatement {
    const self = this;
    const sqlNorm = sql.trim();
    return {
      run(...params: unknown[]) {
        if (/^UPDATE chunks/i.test(sqlNorm)) {
          // expect (confidence, provenance_kind, updated_at, id) or (superseded_by, id)
          const id = params[params.length - 1] as number;
          const chunks = self.rows.get("chunks") ?? [];
          const row = chunks.find((r) => r.id === id);
          if (!row) return { changes: 0, lastInsertRowid: 0 };
          if (/SET confidence/i.test(sqlNorm)) {
            row.confidence = params[0];
            row.provenance_kind = params[1];
            row.updated_at = params[2];
          } else if (/SET superseded_by/i.test(sqlNorm)) {
            row.superseded_by = params[0];
            row.provenance_kind = "user-marked";
            row.confidence = 0.05;
            row.updated_at = params[1];
          }
          return { changes: 1, lastInsertRowid: 0 };
        }
        if (/^INSERT INTO ops_audit/i.test(sqlNorm)) {
          const id = self.idCounter++;
          self.audit.push({
            id,
            op: params[0],
            status: params[1],
            details: params[2],
            started_at: params[3],
          });
          return { changes: 1, lastInsertRowid: id };
        }
        if (/^INSERT INTO chunks/i.test(sqlNorm)) {
          const id = self.idCounter++;
          const list = self.rows.get("chunks") ?? [];
          const row: Record<string, unknown> = {
            id,
            content: params[0],
            confidence: params[1],
            provenance_kind: params[2],
            pain: params[3] ?? 0.2,
            created_at: Date.now(),
          };
          list.push(row);
          self.rows.set("chunks", list);
          return { changes: 1, lastInsertRowid: id };
        }
        return { changes: 0, lastInsertRowid: 0 };
      },
      get<T = unknown>(...params: unknown[]): T | undefined {
        if (/FROM chunks WHERE id/i.test(sqlNorm)) {
          const id = params[0];
          const chunks = self.rows.get("chunks") ?? [];
          return chunks.find((r) => r.id === id) as T | undefined;
        }
        if (
          /COUNT\(\*\).*FROM chunks WHERE superseded_by IS NOT NULL/i.test(
            sqlNorm
          )
        ) {
          const chunks = self.rows.get("chunks") ?? [];
          const c = chunks.filter(
            (r) => r.superseded_by !== null && r.superseded_by !== undefined
          ).length;
          return { count: c } as T;
        }
        if (/COUNT\(\*\).*chunks/i.test(sqlNorm)) {
          const chunks = self.rows.get("chunks") ?? [];
          return { count: chunks.length } as T;
        }
        return undefined;
      },
      all<T = unknown>(..._params: unknown[]): T[] {
        if (/GROUP BY provenance_kind/i.test(sqlNorm)) {
          const chunks = self.rows.get("chunks") ?? [];
          const buckets = new Map<string | null, number>();
          for (const c of chunks) {
            const k = (c.provenance_kind as string | null | undefined) ?? null;
            buckets.set(k, (buckets.get(k) ?? 0) + 1);
          }
          const out: { provenance_kind: string | null; count: number }[] = [];
          for (const [k, count] of buckets.entries()) {
            out.push({ provenance_kind: k, count });
          }
          return out as T[];
        }
        if (
          /SELECT confidence FROM chunks WHERE confidence IS NOT NULL/i.test(
            sqlNorm
          )
        ) {
          const chunks = self.rows.get("chunks") ?? [];
          const vals = chunks
            .map((r) => r.confidence)
            .filter(
              (v): v is number =>
                typeof v === "number" && Number.isFinite(v)
            )
            .sort((a, b) => a - b);
          return vals.map((v) => ({ confidence: v })) as T[];
        }
        if (/FROM chunks/i.test(sqlNorm)) {
          return (self.rows.get("chunks") ?? []) as T[];
        }
        if (/FROM ops_audit/i.test(sqlNorm)) {
          return self.audit as T[];
        }
        return [];
      },
      iterate<T = unknown>(..._params: unknown[]): Iterable<T> {
        return [] as T[];
      },
    };
  }

  exec(_sql: string): void {
    /* no-op */
  }

  transaction<T extends (...args: unknown[]) => unknown>(fn: T): T {
    return fn;
  }

  pragma(_sql: string, _opts?: { simple?: boolean }): unknown {
    return 19;
  }

  /** Test helper: seed a chunk row. */
  seedChunk(row: {
    id: number;
    content?: string;
    confidence?: number;
    provenance_kind?: string | null;
    pain?: number;
    superseded_by?: number | null;
  }): void {
    const list = this.rows.get("chunks") ?? [];
    list.push({
      content: "",
      confidence: 0.8,
      provenance_kind: null,
      pain: 0.2,
      superseded_by: null,
      ...row,
    });
    this.rows.set("chunks", list);
  }
}
