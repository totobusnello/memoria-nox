/**
 * P5a — Internal Event Bus
 * Singleton EventEmitter for nox-mem-api internal observability.
 * Used as SSE feed prerequisite for P5 viewer.
 *
 * Design constraints:
 * - Never blocks caller — all emits are fire-forget via setImmediate
 * - No external dependencies — Node native events.EventEmitter only
 * - Max listeners: 50 (SSE clients + internal subscribers)
 * - Sub-millisecond overhead per emit (benchmarked in tests)
 */

import { EventEmitter } from "events";

// ─── Event Kinds ─────────────────────────────────────────────────────────────

export const EventKind = {
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

export type EventKindValue = (typeof EventKind)[keyof typeof EventKind];

// ─── Event Payloads ──────────────────────────────────────────────────────────

export interface ChunkCreatedPayload {
  chunk_id: number;
  source_file?: string;
  type?: string;
  section?: string;
  token_count?: number;
  ts: number;
}

export interface ChunkDeletedPayload {
  chunk_id: number;
  ts: number;
}

export interface KgEntityCreatedPayload {
  entity_id: number;
  name: string;
  entity_type: string;
  ts: number;
}

export interface KgRelationCreatedPayload {
  relation_id: number;
  source_entity_id: number;
  target_entity_id: number;
  relation_type: string;
  ts: number;
}

export interface SearchExecutedPayload {
  query_hash: string;
  latency_ms: number;
  top_k: number;
  result_count: number;
  mode?: "hybrid" | "fts" | "vector";
  ts: number;
}

export interface ProviderCallPayload {
  provider: string;
  op_type: "embed" | "complete" | "extract";
  latency_ms: number;
  cost_usd?: number;
  model?: string;
  token_count?: number;
  ts: number;
}

export interface OpAuditStartedPayload {
  op_id: number;
  op_type: string;
  ts: number;
}

export interface OpAuditCompletedPayload {
  op_id: number;
  op_type: string;
  status: "success" | "failed" | "crashed";
  duration_ms: number;
  ts: number;
}

export interface HealthWarningPayload {
  code: string;
  message: string;
  severity: "warn" | "critical";
  context?: Record<string, unknown>;
  ts: number;
}

export type EventPayloadMap = {
  [EventKind.CHUNK_CREATED]: ChunkCreatedPayload;
  [EventKind.CHUNK_DELETED]: ChunkDeletedPayload;
  [EventKind.KG_ENTITY_CREATED]: KgEntityCreatedPayload;
  [EventKind.KG_RELATION_CREATED]: KgRelationCreatedPayload;
  [EventKind.SEARCH_EXECUTED]: SearchExecutedPayload;
  [EventKind.PROVIDER_CALL]: ProviderCallPayload;
  [EventKind.OP_AUDIT_STARTED]: OpAuditStartedPayload;
  [EventKind.OP_AUDIT_COMPLETED]: OpAuditCompletedPayload;
  [EventKind.HEALTH_WARNING]: HealthWarningPayload;
};

// ─── Bus Singleton ───────────────────────────────────────────────────────────

const MAX_LISTENERS = 50;

class NoxEventBus extends EventEmitter {
  constructor() {
    super();
    // High limit for SSE clients + internal subscribers
    this.setMaxListeners(MAX_LISTENERS);
  }

  /**
   * Fire-forget emit — schedules listener dispatch via setImmediate.
   * NEVER blocks caller. Caller returns before any listener runs.
   * Overhead: <1ms per call (just setImmediate scheduling).
   */
  emitAsync<K extends EventKindValue>(
    kind: K,
    data: EventPayloadMap[K]
  ): void {
    setImmediate(() => {
      this.emit(kind, data);
    });
  }

  /**
   * Subscribe to a typed event kind.
   * Returns unsubscribe function for clean teardown.
   */
  on<K extends EventKindValue>(
    kind: K,
    listener: (data: EventPayloadMap[K]) => void
  ): this {
    return super.on(kind, listener as (...args: unknown[]) => void);
  }

  once<K extends EventKindValue>(
    kind: K,
    listener: (data: EventPayloadMap[K]) => void
  ): this {
    return super.once(kind, listener as (...args: unknown[]) => void);
  }

  off<K extends EventKindValue>(
    kind: K,
    listener: (data: EventPayloadMap[K]) => void
  ): this {
    return super.off(kind, listener as (...args: unknown[]) => void);
  }

  /**
   * Subscribe and return explicit unsubscribe. Preferred for SSE/cleanup paths.
   */
  subscribe<K extends EventKindValue>(
    kind: K,
    listener: (data: EventPayloadMap[K]) => void
  ): () => void {
    this.on(kind, listener);
    return () => this.off(kind, listener);
  }

  /**
   * Current listener count per kind — for health checks and leak detection.
   */
  listenerCount(kind: EventKindValue): number {
    return super.listenerCount(kind);
  }

  /**
   * Stats for /api/health.eventBus endpoint.
   */
  stats(): Record<string, number> {
    const result: Record<string, number> = {};
    for (const kind of Object.values(EventKind)) {
      const count = super.listenerCount(kind);
      if (count > 0) result[kind] = count;
    }
    return result;
  }
}

// Export singleton
export const bus = new NoxEventBus();

// ─── Top-level emit helper ───────────────────────────────────────────────────

/**
 * Convenience wrapper. Prefer `bus.emitAsync()` for explicit intent.
 * This alias exists so integration sites can import just `emit`.
 *
 * Usage:
 *   import { emit, EventKind } from '../lib/events/bus';
 *   emit(EventKind.CHUNK_CREATED, { chunk_id: 42, ts: Date.now() });
 */
export function emit<K extends EventKindValue>(
  kind: K,
  data: EventPayloadMap[K]
): void {
  bus.emitAsync(kind, data);
}
