/**
 * G11 — SSE concurrent connection limit (Wave G)
 *
 * Extends `openSseStream()` (P5 T3) with three connection-control knobs:
 *
 *   1. NOX_VIEWER_MAX_CONNECTIONS (default 50)
 *      Global cap on concurrent SSE clients. New requests above the cap
 *      receive 503 + `Retry-After: 5` and a JSON `{ error: "sse_capacity" }`.
 *
 *   2. NOX_VIEWER_MAX_PER_IP (default 5)
 *      Per-IP cap. Same response as global cap, with `Retry-After: 10`.
 *
 *   3. NOX_VIEWER_DROP_OLDEST=1 (default off)
 *      Instead of rejecting new connections, close the oldest one when the
 *      global cap is exceeded. Useful for ops/admin viewers that prefer
 *      "newest wins" semantics. Per-IP cap still rejects regardless (a single
 *      IP shouldn't be able to evict other tenants).
 *
 * Threat:
 *   - Without a cap, an attacker can open thousands of SSE connections,
 *     pin sockets + memory + ring buffer wake-ups, and starve legitimate
 *     viewers (connection exhaustion DoS — G11 / R-P5-2.1).
 *
 * Backward compat:
 *   - All knobs are env-opt-in. Defaults (50 global, 5 per-IP) are generous
 *     enough that interactive use is unaffected; only abusive bursts hit them.
 *   - Existing `openSseStream()` from P5 T3 is unchanged. This module wraps it.
 *
 * Refs:
 *   - docs/security/THREAT-MODEL.md §7.5 T-P5-2 (DoS / connection exhaustion).
 *   - PR #58 §14 G11.
 */

import type { Broadcaster } from "../lib/viewer/broadcast.js";
import { openSseStream, type OpenSseStreamOptions, type SseStream } from "./events-stream.js";

// ── env config ──────────────────────────────────────────────────────────────

export interface SseLimitConfig {
  /** Global cap on concurrent SSE clients. Default 50. */
  maxConnections: number;
  /** Per-IP cap. Default 5. */
  maxPerIp: number;
  /** If true, drop oldest connection instead of rejecting new ones. */
  dropOldest: boolean;
}

/**
 * Read config from environment. Pure helper — does not mutate process state.
 * Each call re-reads `process.env` so tests can stub it.
 */
export function readSseLimitConfig(env: NodeJS.ProcessEnv = process.env): SseLimitConfig {
  const parsePositiveInt = (raw: string | undefined, fallback: number): number => {
    if (!raw) return fallback;
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) && n > 0 ? n : fallback;
  };
  return {
    maxConnections: parsePositiveInt(env.NOX_VIEWER_MAX_CONNECTIONS, 50),
    maxPerIp: parsePositiveInt(env.NOX_VIEWER_MAX_PER_IP, 5),
    dropOldest: env.NOX_VIEWER_DROP_OLDEST === "1",
  };
}

// ── tracker ─────────────────────────────────────────────────────────────────

interface TrackedClient {
  clientId: string;
  ip: string;
  /** Monotonic open time (ms since epoch). */
  openedAt: number;
  /** Close hook supplied by `openSseStream()`. */
  close: () => void;
}

/**
 * Tracks live SSE clients so we can enforce concurrent-connection limits.
 * One instance per process (singleton via `getSseTracker()` below).
 */
export class SseConnectionTracker {
  private readonly clients = new Map<string, TrackedClient>();
  private readonly byIp = new Map<string, Set<string>>();

  /** Total live clients. */
  size(): number {
    return this.clients.size;
  }

  /** Live clients for a single IP. */
  sizePerIp(ip: string): number {
    return this.byIp.get(ip)?.size ?? 0;
  }

  /** Snapshot for telemetry / tests. Order = insertion order (oldest first). */
  snapshot(): readonly Readonly<TrackedClient>[] {
    return Array.from(this.clients.values());
  }

  /** Register a new client. Caller must invoke `unregister()` on close. */
  register(client: TrackedClient): void {
    this.clients.set(client.clientId, client);
    const ipSet = this.byIp.get(client.ip);
    if (ipSet) ipSet.add(client.clientId);
    else this.byIp.set(client.ip, new Set([client.clientId]));
  }

  unregister(clientId: string): void {
    const c = this.clients.get(clientId);
    if (!c) return;
    this.clients.delete(clientId);
    const ipSet = this.byIp.get(c.ip);
    if (ipSet) {
      ipSet.delete(clientId);
      if (ipSet.size === 0) this.byIp.delete(c.ip);
    }
  }

  /**
   * Close + unregister the oldest tracked client.
   * Returns the closed clientId, or null when tracker is empty.
   */
  dropOldest(): string | null {
    const oldest = this.clients.values().next().value;
    if (!oldest) return null;
    oldest.close();
    this.unregister(oldest.clientId);
    return oldest.clientId;
  }

  /** Test helper — reset between cases. */
  clear(): void {
    for (const c of this.clients.values()) {
      try {
        c.close();
      } catch {
        /* swallow — best effort cleanup */
      }
    }
    this.clients.clear();
    this.byIp.clear();
  }
}

let _trackerSingleton: SseConnectionTracker | null = null;
export function getSseTracker(): SseConnectionTracker {
  if (!_trackerSingleton) _trackerSingleton = new SseConnectionTracker();
  return _trackerSingleton;
}

/** Test helper — fresh tracker, callers should restore via `setSseTracker(prev)`. */
export function setSseTracker(t: SseConnectionTracker | null): SseConnectionTracker | null {
  const prev = _trackerSingleton;
  _trackerSingleton = t;
  return prev;
}

// ── public API ──────────────────────────────────────────────────────────────

/** Reject reason. Includes Retry-After hint for clients. */
export interface SseReject {
  rejected: true;
  status: 503;
  retryAfterSeconds: number;
  reason: "global_cap" | "per_ip_cap";
  body: { error: "sse_capacity"; reason: string; max: number };
}

export interface SseAccept {
  rejected: false;
  stream: SseStream;
  /** Total live clients AFTER this connection was accepted. */
  liveCount: number;
}

export type SseOpenResult = SseAccept | SseReject;

export interface OpenLimitedSseOptions extends OpenSseStreamOptions {
  /** Client IP — derived from `X-Forwarded-For` first hop or socket.remoteAddress. */
  ip: string;
  /** Override config (tests). */
  config?: SseLimitConfig;
  /** Override tracker (tests). */
  tracker?: SseConnectionTracker;
  /** Broadcaster reference — required for `openSseStream`. */
  broadcaster: Broadcaster;
}

/**
 * Open an SSE stream with concurrent-connection limits enforced.
 *
 * Decision tree:
 *   1. If per-IP count >= maxPerIp → reject 503 (per_ip_cap, Retry-After 10s)
 *   2. If global count >= maxConnections:
 *        a. dropOldest=true → close oldest, accept new
 *        b. dropOldest=false → reject 503 (global_cap, Retry-After 5s)
 *   3. Else accept.
 */
export function openLimitedSseStream(opts: OpenLimitedSseOptions): SseOpenResult {
  const config = opts.config ?? readSseLimitConfig();
  const tracker = opts.tracker ?? getSseTracker();

  // 1. Per-IP cap — checked BEFORE global, because a single IP shouldn't be
  //    able to evict legit clients via dropOldest.
  if (tracker.sizePerIp(opts.ip) >= config.maxPerIp) {
    return {
      rejected: true,
      status: 503,
      retryAfterSeconds: 10,
      reason: "per_ip_cap",
      body: {
        error: "sse_capacity",
        reason: "per_ip_cap",
        max: config.maxPerIp,
      },
    };
  }

  // 2. Global cap.
  if (tracker.size() >= config.maxConnections) {
    if (config.dropOldest) {
      tracker.dropOldest();
    } else {
      return {
        rejected: true,
        status: 503,
        retryAfterSeconds: 5,
        reason: "global_cap",
        body: {
          error: "sse_capacity",
          reason: "global_cap",
          max: config.maxConnections,
        },
      };
    }
  }

  // 3. Accept — wrap close to unregister from tracker.
  const stream = openSseStream(opts);
  const wrappedClose = (): void => {
    try {
      stream.close();
    } finally {
      tracker.unregister(opts.clientId);
    }
  };
  tracker.register({
    clientId: opts.clientId,
    ip: opts.ip,
    openedAt: Date.now(),
    close: wrappedClose,
  });

  return {
    rejected: false,
    stream: {
      headers: stream.headers,
      iter: stream.iter,
      close: wrappedClose,
    },
    liveCount: tracker.size(),
  };
}

/**
 * Build the HTTP 503 response payload + headers for caller frameworks
 * (Express / Fastify / raw http). Keeps SSE accept-side and reject-side
 * symmetrical for the host wiring.
 */
export function rejectionToHttp(reject: SseReject): {
  status: 503;
  headers: Record<string, string>;
  body: SseReject["body"];
} {
  return {
    status: 503,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Retry-After": String(reject.retryAfterSeconds),
      "Cache-Control": "no-store",
    },
    body: reject.body,
  };
}
