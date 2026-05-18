/**
 * T2 — Event source instrumentation
 *
 * Adapter layer: subscribes to the P5a internal bus (`bus` singleton from
 * `lib/events/bus.ts`) and converts each raw payload into a redacted
 * `ViewerEvent` ready for the SSE feed.
 *
 * Design:
 *  - Single subscriber per kind — fan-out happens downstream (broadcast.ts).
 *  - Pure conversion: no I/O, no DB calls, no async — keep emit→adapter <1ms.
 *  - Output goes through `redactEvent()` so default-deny is enforced once.
 *
 * The bus dependency is injected as `BusLike` for tests so we can swap a
 * mock EventEmitter without touching globals.
 */

import { EventEmitter } from "node:events";
import {
  type ViewerEvent,
  type IngestEvent,
  type SearchEvent,
  type KgEvent,
  type CrystallizeEvent,
  type OpAuditEvent,
  nowIso,
} from "./event-types.js";
import { redactEvent, queryHash, nameHash, safeBasename } from "./redaction.js";

// ─── Bus interface (subset we depend on) ────────────────────────────────────

export interface BusLike {
  on(event: string, listener: (...args: unknown[]) => void): this;
  off(event: string, listener: (...args: unknown[]) => void): this;
}

// Event kind strings from P5a bus (must match `EventKind` in bus.ts).
const BUS_KINDS = {
  CHUNK_CREATED: "chunk.created",
  CHUNK_DELETED: "chunk.deleted",
  KG_ENTITY_CREATED: "kg.entity.created",
  KG_RELATION_CREATED: "kg.relation.created",
  SEARCH_EXECUTED: "search.executed",
  PROVIDER_CALL: "provider.call",
  OP_AUDIT_STARTED: "op_audit.started",
  OP_AUDIT_COMPLETED: "op_audit.completed",
  HEALTH_WARNING: "health.warning",
} as const;

// ─── Payload shapes from bus (subset, defensive) ────────────────────────────

interface BusChunkCreated {
  chunk_id: number;
  source_file?: string;
  type?: string;
  section?: string;
  token_count?: number;
  length?: number;
  redaction_count?: number;
  retention_days?: number | null;
  pain?: number;
  ts: number;
}

interface BusChunkDeleted {
  chunk_id: number;
  ts: number;
}

interface BusKgEntityCreated {
  entity_id: number;
  name: string;
  entity_type: string;
  confidence?: number;
  ts: number;
}

interface BusKgRelationCreated {
  relation_id: number;
  source_entity_id: number;
  target_entity_id: number;
  relation_type: string;
  confidence?: number;
  ts: number;
}

interface BusSearchExecuted {
  query?: string;
  query_hash?: string;
  latency_ms: number;
  top_k: number;
  result_count: number;
  mode?: "hybrid" | "fts" | "vector";
  bm25_score?: number;
  vec_score?: number;
  kg_score?: number;
  ts: number;
}

interface BusOpAuditStarted {
  op_id: number;
  op_type: string;
  dry_run?: boolean;
  ts: number;
}

interface BusOpAuditCompleted {
  op_id: number;
  op_type: string;
  status: "success" | "failed" | "crashed";
  duration_ms: number;
  rows_affected?: number;
  ts: number;
}

// ─── Mappers (pure functions) ───────────────────────────────────────────────

export function mapChunkCreated(p: BusChunkCreated): IngestEvent {
  return {
    ts: nowIso(),
    type: "ingest",
    source: "ingest-router",
    summary: `chunk ${p.chunk_id} created (${p.type ?? "unknown"})`,
    details: {
      chunk_id: p.chunk_id,
      chunk_kind: p.type ?? "unknown",
      length: p.length ?? p.token_count ?? 0,
      redaction_count: p.redaction_count ?? 0,
      section: p.section ?? null,
      retention_days: p.retention_days ?? null,
      pain: p.pain ?? 0.2,
      source_basename: safeBasename(p.source_file),
    },
  };
}

export function mapChunkDeleted(p: BusChunkDeleted): IngestEvent {
  return {
    ts: nowIso(),
    type: "ingest",
    source: "ingest-router",
    summary: `chunk ${p.chunk_id} deleted`,
    details: {
      chunk_id: p.chunk_id,
      chunk_kind: "deleted",
      length: 0,
      redaction_count: 0,
      section: null,
      retention_days: null,
      pain: 0,
    },
  };
}

export function mapKgEntityCreated(p: BusKgEntityCreated): KgEvent {
  return {
    ts: nowIso(),
    type: "kg",
    source: "kg-extract",
    summary: `KG entity ${p.entity_type} created`,
    details: {
      kg_kind: "entity_created",
      entity_id: p.entity_id,
      entity_type: p.entity_type,
      name_hash: nameHash(p.name),
      confidence: p.confidence ?? 1,
    },
  };
}

export function mapKgRelationCreated(p: BusKgRelationCreated): KgEvent {
  return {
    ts: nowIso(),
    type: "kg",
    source: "kg-extract",
    summary: `KG relation ${p.relation_type} created`,
    details: {
      kg_kind: "relation_created",
      relation_id: p.relation_id,
      source_entity_id: p.source_entity_id,
      target_entity_id: p.target_entity_id,
      relation_type: p.relation_type,
      confidence: p.confidence ?? 1,
    },
  };
}

export function mapSearchExecuted(p: BusSearchExecuted): SearchEvent {
  const raw = p.query ?? "";
  return {
    ts: nowIso(),
    type: "search",
    source: "search-hybrid",
    summary: `search ${p.mode ?? "hybrid"} ${p.latency_ms}ms`,
    details: {
      query_hash: p.query_hash ?? (raw ? queryHash(raw) : ""),
      query: raw, // will be redacted unless NOX_VIEWER_SHOW_QUERY=1
      latency_ms: p.latency_ms,
      top_k: p.top_k,
      result_count: p.result_count,
      mode: p.mode ?? "hybrid",
      hybrid_breakdown: {
        bm25: p.bm25_score ?? 0,
        vec: p.vec_score ?? 0,
        kg: p.kg_score ?? 0,
      },
    },
  };
}

export function mapOpAuditStarted(p: BusOpAuditStarted): OpAuditEvent {
  return {
    ts: nowIso(),
    type: "op_audit",
    source: "op-audit",
    summary: `${p.op_type} started`,
    details: {
      op_id: p.op_id,
      op: p.op_type,
      status: "started",
      dry_run: p.dry_run ?? false,
    },
  };
}

export function mapOpAuditCompleted(p: BusOpAuditCompleted): OpAuditEvent {
  return {
    ts: nowIso(),
    type: "op_audit",
    source: "op-audit",
    summary: `${p.op_type} ${p.status} in ${p.duration_ms}ms`,
    details: {
      op_id: p.op_id,
      op: p.op_type,
      status: p.status,
      dry_run: false,
      duration_ms: p.duration_ms,
      rows_affected: p.rows_affected,
    },
  };
}

// ─── Crystallize emit helper (called directly by crystallize.ts) ─────────────

export function buildCrystallizeEvent(
  status: "started" | "success" | "failed",
  target_entity_id: number,
  source_chunk_count: number,
  duration_ms?: number,
  redaction_count = 0
): CrystallizeEvent {
  const out: CrystallizeEvent = {
    ts: nowIso(),
    type: "crystallize",
    source: "crystallize",
    summary: `crystallize entity ${target_entity_id} ${status}`,
    details: {
      source_chunk_count,
      target_entity_id,
      redaction_count,
      status,
    },
  };
  if (typeof duration_ms === "number") out.details.duration_ms = duration_ms;
  return out;
}

// ─── Subscriber wiring ──────────────────────────────────────────────────────

export interface InstrumentationOptions {
  /** Callback invoked with each ready-to-ship ViewerEvent (post-redaction). */
  onEvent: (ev: ViewerEvent) => void;
  /** Optional override for environment flag (defaults to env). */
  showQuery?: boolean;
}

export interface InstrumentationHandle {
  /** Unsubscribe all listeners and detach from bus. */
  detach: () => void;
  /** Count of events emitted since attach. */
  emitted: () => number;
}

/**
 * Attach to the P5a bus. Every relevant bus event is mapped and forwarded
 * through `redactEvent()` to the consumer.
 */
export function attachInstrumentation(
  bus: BusLike,
  opts: InstrumentationOptions
): InstrumentationHandle {
  let count = 0;
  const emit = (ev: ViewerEvent): void => {
    const safe = redactEvent(ev, { showQuery: opts.showQuery });
    count += 1;
    opts.onEvent(safe);
  };

  const handlers: Array<[string, (...args: unknown[]) => void]> = [
    [
      BUS_KINDS.CHUNK_CREATED,
      (p) => emit(mapChunkCreated(p as BusChunkCreated)),
    ],
    [
      BUS_KINDS.CHUNK_DELETED,
      (p) => emit(mapChunkDeleted(p as BusChunkDeleted)),
    ],
    [
      BUS_KINDS.KG_ENTITY_CREATED,
      (p) => emit(mapKgEntityCreated(p as BusKgEntityCreated)),
    ],
    [
      BUS_KINDS.KG_RELATION_CREATED,
      (p) => emit(mapKgRelationCreated(p as BusKgRelationCreated)),
    ],
    [
      BUS_KINDS.SEARCH_EXECUTED,
      (p) => emit(mapSearchExecuted(p as BusSearchExecuted)),
    ],
    [
      BUS_KINDS.OP_AUDIT_STARTED,
      (p) => emit(mapOpAuditStarted(p as BusOpAuditStarted)),
    ],
    [
      BUS_KINDS.OP_AUDIT_COMPLETED,
      (p) => emit(mapOpAuditCompleted(p as BusOpAuditCompleted)),
    ],
  ];

  for (const [kind, fn] of handlers) {
    bus.on(kind, fn);
  }

  return {
    detach: () => {
      for (const [kind, fn] of handlers) {
        bus.off(kind, fn);
      }
    },
    emitted: () => count,
  };
}

/** Convenience: create a fresh isolated EventEmitter for tests. */
export function makeTestBus(): EventEmitter {
  return new EventEmitter();
}
