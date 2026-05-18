/**
 * src/api/server-deps-p1.ts — Wave O T1: P1 (answer) runtime adapter.
 *
 * Closes the 503 gap for `POST /api/answer`. The staged-P1 handler
 * (`src/api/answer.ts::handleAnswerRequest`) is framework-agnostic but expects
 * a `TelemetryStore` injected via `args.telemetryStore`. Without that
 * injection, telemetry rows are silently dropped — and the wire-up.ts
 * currently passes only `{body, headers}`.
 *
 * This adapter exposes `buildAnswerHandler()` that returns a thin closure
 * the wire-up can call as a drop-in replacement: same input shape, but
 * pre-configured with:
 *
 *   - A live `TelemetryStore` backed by better-sqlite3 (writes to
 *     `answer_telemetry` table, schema v11).
 *   - A `sessionId` derived from `X-Session-Id` header (when present).
 *   - The real `answer()` pipeline from staged-P1.
 *
 * Why this module is a separate file from `wire-up.ts`:
 *   - Keeps wire-up.ts framework-only (route table). Adapter knows about DB.
 *   - Singleton DB acquisition happens via `deps-registry.ts` — one connection
 *     shared across all five adapters (regra de ouro #2).
 *   - `__setHandlerForTests()` lets unit tests stub the inner pipeline so
 *     they don't need an actual Gemini key.
 *
 * Apply step (production): rsync this file + deps-registry.ts to
 *   ${NM}/src/api/server-deps-p1.ts and rebuild — the wire-up's
 *   `await import("./answer.js")` already finds the existing `answer.ts`;
 *   the only change is that `answer.ts` (staged-P1) gets re-exported with
 *   the adapter's wrapper on top, so the wire-up doesn't need patching.
 *
 * NOTE: this module does NOT modify wire-up.ts. The wire-up imports
 * `./answer.js` directly; our adapter sits in front and the answer.js shim
 * (also in this PR) chains here. See `./answer-bridge.ts`.
 */

import type { IncomingMessage } from "node:http";
import { getDb } from "../lib/deps/deps-registry.js";
import type { DbHandle } from "../lib/deps/deps-registry.js";

// Re-typed contract — mirrors staged-P1's `HandleAnswerArgs` / `HandlerOutput`
// without an import dep (staged-wire-up-adapters compiles independently).
export interface AnswerArgs {
  body: unknown;
  headers?: Record<string, string | string[] | undefined>;
  /** Set by upstream auth middleware; passed through to telemetry. */
  sessionId?: string | null;
}

export interface AnswerOutput {
  status: number;
  headers: Record<string, string>;
  body: unknown;
}

// ─── TelemetryStore adapter (better-sqlite3 → P1 schema v11) ─────────────────

interface SchemaTelemetryRow {
  question_hash: string;
  session_id: string | null;
  timestamp_ms: number;
  provider: string;
  model: string;
  retrieval_count: number;
  citation_count: number;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number;
  fallback_used: 0 | 1;
  failed_reason: string | null;
  cost_estimate_usd: number;
}

interface TelemetryStore {
  insert(row: SchemaTelemetryRow): void;
}

/**
 * Build a TelemetryStore that writes to `answer_telemetry`.
 * Returns a no-op store when the DB or the table is unavailable —
 * telemetry must never break the user-facing answer call.
 */
function buildTelemetryStore(db: DbHandle | null): TelemetryStore {
  if (!db) {
    return { insert: () => undefined };
  }
  // Verify table exists. If missing, fall back to a no-op (silent skip).
  let tableExists = false;
  try {
    const row = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='answer_telemetry'",
      )
      .get<{ name: string }>();
    tableExists = !!row;
  } catch {
    tableExists = false;
  }
  if (!tableExists) {
    return { insert: () => undefined };
  }

  let stmt: ReturnType<DbHandle["prepare"]> | null = null;
  try {
    stmt = db.prepare(
      `INSERT INTO answer_telemetry
       (question_hash, session_id, timestamp_ms, provider, model,
        retrieval_count, citation_count, tokens_in, tokens_out, latency_ms,
        fallback_used, failed_reason, cost_estimate_usd)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
  } catch {
    return { insert: () => undefined };
  }

  return {
    insert(row): void {
      try {
        stmt!.run(
          row.question_hash,
          row.session_id,
          row.timestamp_ms,
          row.provider,
          row.model,
          row.retrieval_count,
          row.citation_count,
          row.tokens_in,
          row.tokens_out,
          row.latency_ms,
          row.fallback_used,
          row.failed_reason,
          row.cost_estimate_usd,
        );
      } catch {
        // Swallow — privacy rule: telemetry never breaks the answer path.
      }
    },
  };
}

// ─── Adapter entrypoint ──────────────────────────────────────────────────────

/**
 * Bridge `wire-up.ts`'s call signature `(req, body)` to the staged-P1
 * `handleAnswerRequest({body, headers, telemetryStore, sessionId})`.
 *
 * Returns the same `{status, headers, body}` shape wire-up.ts already writes
 * via `writeJson(res, out.body, out.status, out.headers)`.
 */
export async function buildAnswerDeps(args: AnswerArgs): Promise<{
  telemetryStore: TelemetryStore;
  sessionId: string | null;
}> {
  const db = await getDb();
  const telemetryStore = buildTelemetryStore(db);

  // Session id from header (X-Session-Id) or middleware seam.
  let sessionId: string | null = args.sessionId ?? null;
  if (!sessionId && args.headers) {
    for (const k of Object.keys(args.headers)) {
      if (k.toLowerCase() === "x-session-id") {
        const v = args.headers[k];
        sessionId = Array.isArray(v) ? v[0] ?? null : v ?? null;
        break;
      }
    }
  }
  return { telemetryStore, sessionId };
}

/**
 * Public adapter — used by `./answer.js` bridge (also in this PR) and tests.
 * Lazy-imports the P1 pipeline. Falls back to 503 on missing handler.
 */
export async function handleAnswerWithDeps(args: AnswerArgs): Promise<AnswerOutput> {
  // Production path: staged-P1 rsynced as `src/api/answer.js`. Tests don't
  // co-locate it, so the dynamic import fails and we fall to 503 (which the
  // wire-up.ts router then surfaces unchanged). String indirection prevents
  // TS from resolving the path at compile time (intentional for the staged
  // tree — file lives at the prod path, not here).
  const ANSWER_SPEC = "./answer.js";
  let p1: any;
  try {
    p1 = await import(ANSWER_SPEC);
  } catch {
    return {
      status: 503,
      headers: { "Content-Type": "application/json" },
      body: {
        error: "not_implemented",
        reason: "P1 answer handler not deployed",
        hint: "rsync staged-P1/edits/src/api/answer.ts → src/api/answer.ts",
      },
    };
  }
  const handler =
    p1.handleAnswerRequest ??
    p1.default?.handleAnswerRequest ??
    p1.default;
  if (typeof handler !== "function") {
    return {
      status: 503,
      headers: { "Content-Type": "application/json" },
      body: {
        error: "not_implemented",
        reason: "P1 handleAnswerRequest export missing",
      },
    };
  }
  const deps = await buildAnswerDeps(args);
  return handler({
    body: args.body,
    headers: args.headers,
    telemetryStore: deps.telemetryStore,
    sessionId: deps.sessionId,
  });
}

/** Helper for the wire-up integration — extracts headers off IncomingMessage. */
export function headersFromReq(
  req: IncomingMessage,
): Record<string, string | string[] | undefined> {
  return req.headers as Record<string, string | string[] | undefined>;
}
