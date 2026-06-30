/**
 * T1 — Viewer Event Taxonomy
 *
 * Discriminated union of all events the viewer surfaces.
 * Each event has a stable shape: ts, type, source, summary, details.
 *
 * This is the **post-redaction** shape: payloads here are SAFE to send
 * over the wire. Raw chunk content, raw query text, embeddings, and
 * other sensitive fields are stripped upstream by `redaction.ts`.
 *
 * Schema v1 frozen — additive-only post-launch (new kinds OK, no rename/remove).
 */

// ─── Common envelope ─────────────────────────────────────────────────────────

export type ViewerEventKind =
  | "ingest"
  | "search"
  | "kg"
  | "crystallize"
  | "op_audit";

export type ViewerEventSource =
  | "ingest-router"
  | "ingest-watcher"
  | "search-hybrid"
  | "kg-extract"
  | "crystallize"
  | "op-audit"
  | "provider"
  | "health"
  | "unknown";

export interface ViewerEventBase {
  /** ISO 8601 UTC timestamp, monotonic per type. */
  ts: string;
  /** Discriminator — high-level category. */
  type: ViewerEventKind;
  /** Where this event originated (module/subsystem). */
  source: ViewerEventSource;
  /** Short human-readable summary, 1 line, no secrets. */
  summary: string;
}

// ─── Ingest events ───────────────────────────────────────────────────────────

export interface IngestEventDetails {
  /** Chunk id from `chunks` table. */
  chunk_id: number;
  /** Type of chunk (entity/event/code/file/note/...). */
  chunk_kind: string;
  /** Character length of redacted content. */
  length: number;
  /** Count of redactions applied (privacy filter). */
  redaction_count: number;
  /** Section within entity file format (compiled/frontmatter/timeline/null). */
  section: string | null;
  /** Retention horizon (days) or null = never decay. */
  retention_days: number | null;
  /** Pain severity 0.1-1.0. */
  pain: number;
  /** Source file basename only — never full path. */
  source_basename?: string;
}

export interface IngestEvent extends ViewerEventBase {
  type: "ingest";
  details: IngestEventDetails;
}

// ─── Search events ───────────────────────────────────────────────────────────

export interface SearchEventDetails {
  /** sha256(query).slice(0,16) — for correlation without disclosure. */
  query_hash: string;
  /**
   * Raw query text. Present only if `NOX_VIEWER_SHOW_QUERY=1`.
   * Default "<redacted>".
   */
  query: string;
  /** Total wall latency in ms. */
  latency_ms: number;
  /** Requested top-k. */
  top_k: number;
  /** Number of results returned (post-fusion). */
  result_count: number;
  /** Search mode taken. */
  mode: "hybrid" | "fts" | "vector";
  /** Score breakdown by contribution channel (sum ≈ 1.0). */
  hybrid_breakdown: {
    bm25: number;
    vec: number;
    kg: number;
  };
}

export interface SearchEvent extends ViewerEventBase {
  type: "search";
  details: SearchEventDetails;
}

// ─── KG events (entity OR relation) ──────────────────────────────────────────

export interface KgEntityCreatedDetails {
  kg_kind: "entity_created";
  entity_id: number;
  entity_type: string;
  /** sha1(name).slice(0,8) — name never raw on wire. */
  name_hash: string;
  confidence: number;
}

export interface KgRelationCreatedDetails {
  kg_kind: "relation_created";
  relation_id: number;
  source_entity_id: number;
  target_entity_id: number;
  relation_type: string;
  confidence: number;
}

export type KgEventDetails =
  | KgEntityCreatedDetails
  | KgRelationCreatedDetails;

export interface KgEvent extends ViewerEventBase {
  type: "kg";
  details: KgEventDetails;
}

// ─── Crystallize events ──────────────────────────────────────────────────────

export interface CrystallizeEventDetails {
  /** Source chunks counted in the crystallized output. */
  source_chunk_count: number;
  /** Entity id receiving the crystallized output. */
  target_entity_id: number;
  /** Number of redactions applied in the compiled section. */
  redaction_count: number;
  /** Status (started/success/failed). */
  status: "started" | "success" | "failed";
  /** Wall duration in ms (success only). */
  duration_ms?: number;
}

export interface CrystallizeEvent extends ViewerEventBase {
  type: "crystallize";
  details: CrystallizeEventDetails;
}

// ─── OpAudit events ──────────────────────────────────────────────────────────

export type OpAuditOp =
  | "reindex"
  | "consolidate"
  | "compact"
  | "crystallize"
  | "kg-prune"
  | "viewer.connect"
  | "viewer.disconnect"
  | string;

export interface OpAuditEventDetails {
  op_id: number | string;
  op: OpAuditOp;
  status: "started" | "success" | "failed" | "crashed";
  dry_run: boolean;
  duration_ms?: number;
  rows_affected?: number;
}

export interface OpAuditEvent extends ViewerEventBase {
  type: "op_audit";
  details: OpAuditEventDetails;
}

// ─── Discriminated union ─────────────────────────────────────────────────────

export type ViewerEvent =
  | IngestEvent
  | SearchEvent
  | KgEvent
  | CrystallizeEvent
  | OpAuditEvent;

// ─── Type guards (exhaustive, runtime-safe) ──────────────────────────────────

export function isIngestEvent(ev: ViewerEvent): ev is IngestEvent {
  return ev.type === "ingest";
}

export function isSearchEvent(ev: ViewerEvent): ev is SearchEvent {
  return ev.type === "search";
}

export function isKgEvent(ev: ViewerEvent): ev is KgEvent {
  return ev.type === "kg";
}

export function isCrystallizeEvent(
  ev: ViewerEvent
): ev is CrystallizeEvent {
  return ev.type === "crystallize";
}

export function isOpAuditEvent(ev: ViewerEvent): ev is OpAuditEvent {
  return ev.type === "op_audit";
}

// ─── Validators (cheap, no schema lib) ───────────────────────────────────────

const VALID_TYPES: ReadonlySet<string> = new Set([
  "ingest",
  "search",
  "kg",
  "crystallize",
  "op_audit",
]);

const VALID_SOURCES: ReadonlySet<string> = new Set([
  "ingest-router",
  "ingest-watcher",
  "search-hybrid",
  "kg-extract",
  "crystallize",
  "op-audit",
  "provider",
  "health",
  "unknown",
]);

export function isValidViewerEvent(x: unknown): x is ViewerEvent {
  if (!x || typeof x !== "object") return false;
  const ev = x as Record<string, unknown>;
  if (typeof ev.ts !== "string" || !ev.ts) return false;
  if (typeof ev.type !== "string" || !VALID_TYPES.has(ev.type)) return false;
  if (typeof ev.source !== "string" || !VALID_SOURCES.has(ev.source)) {
    return false;
  }
  if (typeof ev.summary !== "string") return false;
  if (!ev.details || typeof ev.details !== "object") return false;
  return true;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function nowIso(): string {
  return new Date().toISOString();
}

export function eventKindLabel(ev: ViewerEvent): string {
  if (isKgEvent(ev)) {
    return `${ev.type}.${ev.details.kg_kind}`;
  }
  return ev.type;
}
