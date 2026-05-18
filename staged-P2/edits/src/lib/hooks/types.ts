/**
 * src/lib/hooks/types.ts — T1: Hook contract types.
 *
 * Public interfaces consumed by the 5-layer pipeline (T6) and all callers
 * (plugin T8, CLI T11, HTTP T12, MCP T13).
 *
 * Schema dependency: `agent_events` table (v11) already exists per spec §6.1
 * and is used by telemetry (T6 emits one row per rejection/capture).
 *
 * Privacy invariant: HookEvent.content is RAW until it leaves Layer 3.
 * After Layer 3, content has been passed through staged-A1 redact().
 * Telemetry rows NEVER include raw content — only layer name + reason + ts.
 */

/**
 * Roles we recognize from the source agent's turn.
 * Layer 2 (source allowlist) constrains which roles get processed.
 */
export type HookRole = "user" | "assistant" | "system" | "tool" | "unknown";

/**
 * Origin channel of the event. Determines source allowlist (Layer 2).
 *  - openclaw : afterTurn hook from the OpenClaw gateway
 *  - cli      : explicit `nox-mem hooks ingest` (manual or scripted)
 *  - manual   : in-process API client (tests, REPL, ad-hoc)
 *  - mcp      : MCP tool call
 *  - api      : HTTP endpoint
 *  - unknown  : default; ALWAYS rejected by Layer 2 unless explicitly allowed
 */
export type HookSource =
  | "openclaw"
  | "cli"
  | "manual"
  | "mcp"
  | "api"
  | "unknown";

/**
 * Five-layer rejection reasons (one per layer + ok).
 * Stored in `agent_events.kind`-like telemetry column.
 */
export type RejectionReason =
  | "env_disabled"           // Layer 1
  | "source_not_allowed"     // Layer 2
  | "pii_detected_skip"      // Layer 3 (when policy says drop on PII; default = redact+continue)
  | "classifier_low_signal"  // Layer 4
  | "rate_limited"           // Layer 5
  | "dedup_hit"              // Layer 5
  | "queue_full"             // Worker overflow (T9)
  | "explicit_skip"          // @nox:skip decorator (T10)
  | "dry_run"                // NOX_HOOK_DRY_RUN gate
  | "invalid_input";         // Schema validation in T8/T12

/** A capture decision returned by any layer. */
export interface CaptureDecision {
  /** True → forward to next layer (or persist if last). */
  capture: boolean;
  /** Human-readable reason. Stored in telemetry. NEVER includes raw content. */
  reason: string;
  /** Optional layer-name; pipeline fills this if missing. */
  layer?: string;
  /** Optional score in [0,1] when classifier returned ambiguous. */
  score?: number;
}

/**
 * A normalized event before any layer touches it.
 * Source must populate role + content; rest is metadata.
 */
export interface HookEvent {
  /** ULID assigned by caller or pipeline; used for dedup key + telemetry. */
  event_id: string;
  /** Where this event came from. */
  source: HookSource;
  /** Speaker. Layer 2 may filter by allowed roles. */
  role: HookRole;
  /** Raw text content (potentially containing PII). */
  content: string;
  /** Optional session_id (groups events from same convo). */
  session_id?: string;
  /** Optional project slug (cwd → slug mapping in plugin). */
  project_slug?: string;
  /** ISO 8601 timestamp. */
  ts: string;
  /** Optional decorator hints (T10 parses these). */
  decorators?: ReadonlyArray<"capture" | "skip">;
  /** Free-form metadata (model name, tool name, etc). NEVER content. */
  meta?: Readonly<Record<string, string | number | boolean>>;
}

/**
 * Mutable per-event state threaded through the pipeline.
 * Lets each layer attach side-data without mutating the original HookEvent.
 */
export interface HookContext {
  event: HookEvent;
  /** Redacted text + redaction count after Layer 3. */
  redacted?: { text: string; redaction_count: number; kinds: string[] };
  /** Classifier output after Layer 4. */
  classification?: { score: number; reason: string };
  /** Per-layer trace (debug + dryrun). */
  trace: Array<{ layer: string; decision: CaptureDecision; t_ms: number }>;
  /** Set once when pipeline short-circuits or persists. */
  outcome?: HookResult;
}

/** Final pipeline result. */
export interface HookResult {
  captured: boolean;
  /** Reason for rejection, or "ok" when captured. */
  reason: RejectionReason | "ok";
  /** Layer that fired the rejection, or "persisted" on success. */
  layer: string;
  /** chunk_id when captured (set by ingestText). */
  chunk_id?: number;
  /** Total wall-clock time. */
  duration_ms: number;
  /** Whether dry-run mode was on (no persistence even if captured=true). */
  dry_run: boolean;
}

/**
 * Telemetry row written by pipeline for EVERY event (captured or rejected).
 * Maps onto `agent_events` columns; payload_json is a sanitized stub
 * (NEVER raw content).
 */
export interface HookTelemetryRow {
  event_uuid: string;
  session_id: string;
  project_slug: string;
  kind: "tool_use" | "user_prompt" | "session_start" | "session_end" | "pre_compact";
  timestamp: string;
  payload_json: string; // JSON.stringify({ layer, reason, score?, redaction_count? })
  redaction_count: number;
  retention_days: number;
}

/** Standard error class for hook pipeline failures. */
export class HookError extends Error {
  public readonly code: RejectionReason | "internal";
  public readonly layer?: string;
  constructor(code: RejectionReason | "internal", message: string, layer?: string) {
    super(message);
    this.name = "HookError";
    this.code = code;
    this.layer = layer;
  }
}
