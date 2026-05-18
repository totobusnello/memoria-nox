/**
 * In-memory fake DB — emulates the subset of better-sqlite3 behavior that the
 * conflict-detection modules exercise. NOT a general SQLite — only the queries
 * present in this package. New SQL added to detector/evidence/audit-writer
 * must add a matching branch here.
 *
 * The fake stores tables as Map<id, Row> and parses SQL by simple pattern
 * matching. Sufficient for unit tests; full integration uses a real DB.
 */

import type { DBHandle, PreparedStatement, RunResult } from "../db.js";

type Row = Record<string, unknown>;

interface FakeTable {
  rows: Row[];
  nextId: number;
  /** Optional immutability function returning a violation message or null. */
  beforeUpdate?: (oldRow: Row, newRow: Row) => string | null;
  beforeDelete?: (row: Row) => string | null;
}

export class FakeDB implements DBHandle {
  public tables: Record<string, FakeTable> = {
    kg_entities: { rows: [], nextId: 1 },
    kg_relations: { rows: [], nextId: 1 },
    chunks: { rows: [], nextId: 1 },
    conflict_audit: { rows: [], nextId: 1 },
  };

  /** PRAGMA user_version simulator. */
  public userVersion = 19;

  /** Apply the v21 trigger semantics on this fake instance. */
  enableConflictAuditTriggers(): void {
    const tbl = this.table("conflict_audit");
    tbl.beforeDelete = () =>
      "conflict_audit is append-only — DELETE forbidden (CLAUDE.md rule #6)";
    tbl.beforeUpdate = (oldRow, newRow) => {
      const immutable = [
        "kind",
        "subject_entity_id",
        "predicate",
        "target_relation_ids",
        "variants",
        "ts",
      ];
      for (const col of immutable) {
        if (oldRow[col] !== newRow[col]) {
          return "conflict_audit raw conflict data is immutable (CLAUDE.md rule #6)";
        }
      }
      const terminal = [
        "resolved_pick_one",
        "resolved_both_valid",
        "resolved_merged",
        "dismissed",
      ];
      if (
        terminal.includes(String(oldRow.status)) &&
        !terminal.includes(String(newRow.status))
      ) {
        return "conflict_audit terminal rows cannot be reopened — create a new audit row instead";
      }
      return null;
    };
  }

  /** Lazy table getter that creates an empty table on first reference. */
  table(name: string): FakeTable {
    let tbl = this.tables[name];
    if (!tbl) {
      tbl = { rows: [], nextId: 1 };
      this.tables[name] = tbl;
    }
    return tbl;
  }

  prepare(sql: string): PreparedStatement {
    return new FakeStatement(this, sql);
  }

  exec(_sql: string): void {
    // No-op — schema is implicit in the fake.
  }

  pragma(query: string): unknown {
    if (query.trim().toLowerCase().startsWith("user_version")) {
      return [{ user_version: this.userVersion }];
    }
    return [];
  }

  transaction<T>(fn: () => T): () => T {
    return () => fn();
  }
}

class FakeStatement implements PreparedStatement {
  constructor(private db: FakeDB, private sql: string) {}

  run(...params: unknown[]): RunResult {
    return runOn(this.db, this.sql, params);
  }

  get(...params: unknown[]): unknown {
    const rows = allOn(this.db, this.sql, params);
    return rows[0];
  }

  all(...params: unknown[]): unknown[] {
    return allOn(this.db, this.sql, params);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// SQL dispatcher — pattern-matches on canonical query shapes used in this pkg.
// Anything not matched falls through with an explicit "unsupported" error to
// catch new queries early.
// ─────────────────────────────────────────────────────────────────────────────

function normalize(sql: string): string {
  return sql.replace(/\s+/g, " ").trim().toLowerCase();
}

function runOn(db: FakeDB, sql: string, params: unknown[]): RunResult {
  const q = normalize(sql);

  // INSERT INTO conflict_audit
  if (
    q.startsWith(
      "insert into conflict_audit",
    )
  ) {
    const tbl = db.table("conflict_audit");
    const [
      kind,
      subject_entity_id,
      predicate,
      target_relation_ids,
      variants,
      status,
      shadow_mode,
    ] = params;
    const row: Row = {
      id: tbl.nextId++,
      ts: Date.now(),
      kind,
      subject_entity_id,
      predicate,
      target_relation_ids,
      variants,
      status: status ?? "open",
      resolved_by: null,
      resolved_at: null,
      resolution_kind: null,
      picked_relation_id: null,
      merge_target: null,
      notes: null,
      shadow_mode: shadow_mode ?? 1,
    };
    tbl.rows.push(row);
    return { changes: 1, lastInsertRowid: Number(row.id) };
  }

  // UPDATE conflict_audit SET status=?, resolution_kind=?, resolved_by=?, resolved_at=?, picked_relation_id=?, merge_target=?, notes=? WHERE id=?
  if (q.startsWith("update conflict_audit set")) {
    const tbl = db.table("conflict_audit");
    const [
      status,
      resolution_kind,
      resolved_by,
      resolved_at,
      picked_relation_id,
      merge_target,
      notes,
      id,
    ] = params;
    const idx = tbl.rows.findIndex((r) => Number(r.id) === Number(id));
    if (idx === -1) return { changes: 0, lastInsertRowid: 0 };
    const oldRow = tbl.rows[idx]!;
    const newRow: Row = {
      ...oldRow,
      status: status ?? oldRow.status,
      resolution_kind: resolution_kind ?? oldRow.resolution_kind,
      resolved_by: resolved_by ?? oldRow.resolved_by,
      resolved_at: resolved_at ?? oldRow.resolved_at,
      picked_relation_id: picked_relation_id ?? oldRow.picked_relation_id,
      merge_target: merge_target ?? oldRow.merge_target,
      notes: notes ?? oldRow.notes,
    };
    if (tbl.beforeUpdate) {
      const err = tbl.beforeUpdate(oldRow, newRow);
      if (err) throw new Error(err);
    }
    tbl.rows[idx] = newRow;
    return { changes: 1, lastInsertRowid: 0 };
  }

  // DELETE FROM conflict_audit — must raise via trigger
  if (q.startsWith("delete from conflict_audit")) {
    const tbl = db.table("conflict_audit");
    if (tbl.beforeDelete && tbl.rows.length > 0) {
      const err = tbl.beforeDelete(tbl.rows[0]!);
      if (err) throw new Error(err);
    }
    return { changes: 0, lastInsertRowid: 0 };
  }

  throw new Error(`FakeDB: unsupported run() query: ${sql}`);
}

function allOn(db: FakeDB, sql: string, params: unknown[]): Row[] {
  const q = normalize(sql);

  // detector query — see detector-direct.ts
  if (
    q.startsWith("select source_entity_id") &&
    q.includes("from kg_relations") &&
    q.includes("group by source_entity_id, predicate") &&
    q.includes("having count(distinct target_entity_id) > 1")
  ) {
    const min_conf = (params[0] as number) ?? 0.5;
    const tbl = db.table("kg_relations");
    const groups = new Map<
      string,
      {
        source_entity_id: number;
        predicate: string;
        relation_ids: number[];
        targets: Set<number>;
      }
    >();
    for (const r of tbl.rows) {
      const conf = (r.confidence as number) ?? 0.7;
      const superseded = r.superseded_by_relation_id;
      if (conf < min_conf) continue;
      if (superseded != null) continue;
      const key = `${r.source_entity_id}::${r.predicate}`;
      let g = groups.get(key);
      if (!g) {
        g = {
          source_entity_id: r.source_entity_id as number,
          predicate: r.predicate as string,
          relation_ids: [],
          targets: new Set(),
        };
        groups.set(key, g);
      }
      g.relation_ids.push(r.id as number);
      g.targets.add(r.target_entity_id as number);
    }
    const out: Row[] = [];
    for (const g of groups.values()) {
      if (g.targets.size > 1) {
        out.push({
          source_entity_id: g.source_entity_id,
          predicate: g.predicate,
          distinct_targets: g.targets.size,
          relation_ids_csv: g.relation_ids.join(","),
        });
      }
    }
    return out;
  }

  // hydrate variants for a (subject, predicate) — used by detector follow-up
  if (
    q.startsWith("select id, target_entity_id") &&
    q.includes("from kg_relations") &&
    q.includes("where source_entity_id = ? and predicate = ?")
  ) {
    const [subject, predicate, min_conf] = params as [number, string, number];
    const tbl = db.table("kg_relations");
    return tbl.rows
      .filter(
        (r) =>
          Number(r.source_entity_id) === Number(subject) &&
          r.predicate === predicate &&
          (Number(r.confidence ?? 0.7) >= Number(min_conf ?? 0.5)) &&
          r.superseded_by_relation_id == null,
      )
      .map((r) => ({
        id: r.id,
        target_entity_id: r.target_entity_id,
        confidence: r.confidence ?? 0.7,
        extraction_method: r.extraction_method ?? null,
        evidence_chunk_id: r.evidence_chunk_id ?? null,
        created_at: r.created_at ?? 0,
        user_marked: r.user_marked ?? 0,
      }));
  }

  // SELECT * FROM kg_entities WHERE id = ?
  if (q.startsWith("select") && q.includes("from kg_entities") && q.includes("where id =")) {
    const id = params[0] as number;
    return db.table("kg_entities").rows.filter((r) => Number(r.id) === Number(id));
  }

  // evidence query — SELECT c.* FROM chunks c WHERE c.id IN (...)
  if (q.startsWith("select") && q.includes("from chunks") && q.includes("where")) {
    const ids = params as number[];
    return db
      .table("chunks")
      .rows.filter((r) => ids.some((i) => Number(i) === Number(r.id)));
  }

  // SELECT * FROM conflict_audit list / filters
  if (q.startsWith("select") && q.includes("from conflict_audit")) {
    const tbl = db.table("conflict_audit");
    let rows = [...tbl.rows];
    // Combined subject + predicate + status filter (EXISTS_OPEN_SQL dedupe check)
    if (
      q.includes("subject_entity_id = ?") &&
      q.includes("predicate = ?") &&
      q.includes("status = ?")
    ) {
      const [s, p, status] = params as [number, string, string];
      rows = rows.filter(
        (r) =>
          Number(r.subject_entity_id) === Number(s) &&
          r.predicate === p &&
          r.status === status,
      );
    } else if (q.includes("subject_entity_id = ?") && q.includes("predicate = ?")) {
      const [s, p] = params as [number, string];
      rows = rows.filter(
        (r) => Number(r.subject_entity_id) === Number(s) && r.predicate === p,
      );
    } else if (/where\s+status\s*=\s*\?/.exec(q)) {
      const status = params[0] as string;
      rows = rows.filter((r) => r.status === status);
    } else if (q.includes("id = ?")) {
      const id = params[0] as number;
      rows = rows.filter((r) => Number(r.id) === Number(id));
    }
    // status counts aggregate (used by shadow telemetry)
    if (q.includes("count(*)") && q.includes("group by status")) {
      const counts = new Map<string, number>();
      for (const r of tbl.rows) {
        counts.set(String(r.status), (counts.get(String(r.status)) ?? 0) + 1);
      }
      return Array.from(counts.entries()).map(([status, count]) => ({
        status,
        count,
      }));
    }
    // limit
    const limitMatch = /limit\s+(\d+)/.exec(q);
    if (limitMatch) {
      rows = rows.slice(0, Number(limitMatch[1]));
    }
    return rows;
  }

  throw new Error(`FakeDB: unsupported all() query: ${sql}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers to seed the fake DB from tests.
// ─────────────────────────────────────────────────────────────────────────────

export function seedEntity(
  db: FakeDB,
  id: number,
  name: string,
  type = "person",
): void {
  db.table("kg_entities").rows.push({ id, name, type });
}

export function seedRelation(
  db: FakeDB,
  rel: {
    id: number;
    source_entity_id: number;
    predicate: string;
    target_entity_id: number;
    confidence?: number;
    extraction_method?: string | null;
    evidence_chunk_id?: number | null;
    created_at?: number;
    superseded_by_relation_id?: number | null;
    user_marked?: 0 | 1;
  },
): void {
  db.table("kg_relations").rows.push({
    id: rel.id,
    source_entity_id: rel.source_entity_id,
    predicate: rel.predicate,
    target_entity_id: rel.target_entity_id,
    confidence: rel.confidence ?? 0.7,
    extraction_method: rel.extraction_method ?? null,
    evidence_chunk_id: rel.evidence_chunk_id ?? null,
    created_at: rel.created_at ?? Date.now(),
    superseded_by_relation_id: rel.superseded_by_relation_id ?? null,
    user_marked: rel.user_marked ?? 0,
  });
}

export function seedChunk(
  db: FakeDB,
  chunk: {
    id: number;
    content: string;
    ts?: number;
    source_session_id?: string | null;
    confidence?: number | null;
    provenance_kind?: string | null;
  },
): void {
  db.table("chunks").rows.push({
    id: chunk.id,
    content: chunk.content,
    ts: chunk.ts ?? Date.now(),
    source_session_id: chunk.source_session_id ?? null,
    confidence: chunk.confidence ?? 0.8,
    provenance_kind: chunk.provenance_kind ?? null,
  });
}
