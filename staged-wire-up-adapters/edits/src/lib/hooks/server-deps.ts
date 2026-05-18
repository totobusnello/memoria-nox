/**
 * src/lib/hooks/server-deps.ts — Wave O T5: P2 (hooks) runtime adapter.
 *
 * Wire-up.ts lazy-imports this module:
 *
 *     const depsMod = await tryImport("../lib/hooks/server-deps.js");
 *     if (!depsMod?.buildHooksDeps) writeJson(res, ..., 503);
 *     const out = await handleHooksRequest(req, await depsMod.buildHooksDeps());
 *
 * The staged-P2 `handleHooksRequest` expects `HooksApiDeps`:
 *
 *   interface HooksApiDeps {
 *     readRecent(limit): Promise<row[]>;
 *     config?: HookConfig;
 *     telemetry?: TelemetrySink;
 *     inspectQueue?(): { queueDepth; rateLimitTokens? };
 *   }
 *
 * `readRecent` queries `agent_events` (schema v11) for the most recent N
 * captured events. Each row is sanitized to METADATA ONLY — no `payload_json`,
 * no raw content (P2 privacy invariant; see staged-P2 source comment).
 */

import { getDb } from "../deps/deps-registry.js";

// ─── Public dep shapes (mirror staged-P2 contracts) ──────────────────────────

export interface HookRecentRow {
  event_uuid: string;
  session_id: string;
  project_slug: string;
  kind: string;
  timestamp: string;
  redaction_count: number;
}

export interface HookTelemetryRow {
  event_uuid: string;
  layer: string;
  reason: string;
  kind: string;
  redaction_count: number;
  payload_json: string;
  ts: string;
}

export interface HooksApiDeps {
  readRecent: (limit: number) => Promise<HookRecentRow[]>;
  /** Optional. When absent, handler defaults to `loadConfig()` from env. */
  config?: unknown;
  /** Sink for dryrun telemetry. No-op default. */
  telemetry?: (row: HookTelemetryRow) => void;
  inspectQueue?: () => { queueDepth: number; rateLimitTokens?: number };
}

// ─── Default implementations ─────────────────────────────────────────────────

async function defaultReadRecent(limit: number): Promise<HookRecentRow[]> {
  const db = await getDb();
  if (!db) return [];
  // Cap limit defensively even though handler already validates.
  const safeLimit = Math.max(1, Math.min(500, Math.floor(limit)));
  try {
    const rows = db
      .prepare(
        `SELECT event_uuid, session_id, project_slug, kind, timestamp, redaction_count
         FROM agent_events
         WHERE captured = 1
         ORDER BY timestamp DESC
         LIMIT ?`,
      )
      .all<HookRecentRow>(safeLimit);
    return rows;
  } catch {
    // Table missing (pre-v11) → return empty.
    return [];
  }
}

function defaultInspectQueue(): { queueDepth: number; rateLimitTokens?: number } {
  // The actual worker singleton lives in `lib/hooks/worker.ts`. We try to
  // probe it dynamically; when unavailable (CLI-only deploy), return zero.
  return { queueDepth: 0 };
}

let _queueProbe: (() => { queueDepth: number; rateLimitTokens?: number }) | null = null;

async function tryLoadWorkerProbe(): Promise<void> {
  if (_queueProbe) return;
  try {
    // String indirection — `./worker.js` is staged-P2's worker module,
    // co-located only after rsync.
    const WORKER_SPEC = "./worker.js";
    const mod: any = await import(WORKER_SPEC);
    if (typeof mod.inspectQueue === "function") {
      _queueProbe = mod.inspectQueue.bind(mod);
    } else if (typeof mod.default?.inspectQueue === "function") {
      _queueProbe = mod.default.inspectQueue.bind(mod.default);
    }
  } catch {
    // Worker module not deployed — silent fallback.
  }
}

// ─── Public builder ──────────────────────────────────────────────────────────

/**
 * Build the HooksApiDeps the staged-P2 `handleHooksRequest` expects.
 * Idempotent — safe to call once per request.
 */
export async function buildHooksDeps(overrides?: Partial<HooksApiDeps>): Promise<HooksApiDeps> {
  await tryLoadWorkerProbe();
  return {
    readRecent: overrides?.readRecent ?? defaultReadRecent,
    config: overrides?.config,
    telemetry: overrides?.telemetry,
    inspectQueue: overrides?.inspectQueue ?? _queueProbe ?? defaultInspectQueue,
  };
}

// ─── Test seam ───────────────────────────────────────────────────────────────

/** Swap the queue probe for tests. */
export function __setQueueProbeForTests(
  probe: (() => { queueDepth: number; rateLimitTokens?: number }) | null,
): void {
  _queueProbe = probe;
}

export function __resetHooksDepsForTests(): void {
  _queueProbe = null;
}
