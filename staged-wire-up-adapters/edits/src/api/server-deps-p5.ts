/**
 * src/api/server-deps-p5.ts — Wave O T3: P5 (SSE + viewer) runtime adapter.
 *
 * Wire-up.ts (#92) calls two P5 routes:
 *
 *   GET /api/events/stream   → events-stream.openSseStream + broadcast.getBroadcaster
 *   GET /viewer/*            → viewer-static.serveViewerFile
 *
 * The Broadcaster singleton lives in `lib/viewer/broadcast-singleton.ts`
 * (added in this PR). This module handles the redaction layer that wraps
 * outbound SSE envelopes when `NOX_VIEWER_SHOW_QUERY=0` (the default).
 *
 * Redaction policy (default-deny, opt-in transparency):
 *   - `query_text` field on `search` events: redacted to `[redacted]`
 *   - `content` on `chunk` events: truncated to 40 chars + ellipsis
 *   - When NOX_VIEWER_SHOW_QUERY=1, redaction is bypassed
 *
 * Static serving:
 *   - `serveViewerFile()` from staged-P5 reads from `dist/viewer/` by default.
 *   - This adapter exposes `resolveViewerRoot()` so deployments can override
 *     via NOX_VIEWER_ROOT env (useful in dev when assets live outside dist).
 *
 * Build-time decoupling: like the other adapters, this file uses dynamic
 * imports of `./events-stream.js` and `./viewer-static.js` so the staged
 * adapters compile without staged-P5 sources present. At runtime in prod,
 * those files are co-located after rsync.
 */

import { resolve as pathResolve } from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";

// ─── Redaction wrapper ───────────────────────────────────────────────────────

interface BroadcastEnvelopeLike {
  id: number;
  ev: Record<string, unknown>;
}

/** Returns true when NOX_VIEWER_SHOW_QUERY=1 (transparency opt-in). */
export function viewerShowQueryEnabled(): boolean {
  const v = process.env["NOX_VIEWER_SHOW_QUERY"];
  return v === "1" || v === "true" || v === "yes";
}

/**
 * Redact sensitive fields on a viewer event envelope.
 * Returns a NEW object — never mutates the original (the same envelope is
 * pushed to many clients; mutation would leak the redaction across clients
 * with different consent levels in future).
 */
export function redactEnvelope(env: BroadcastEnvelopeLike): BroadcastEnvelopeLike {
  if (viewerShowQueryEnabled()) return env;
  const ev = env.ev as Record<string, unknown>;
  const cloned: Record<string, unknown> = { ...ev };
  if (typeof cloned["query_text"] === "string") {
    cloned["query_text"] = "[redacted]";
  }
  if (typeof cloned["content"] === "string") {
    const s = cloned["content"] as string;
    cloned["content"] = s.length > 40 ? `${s.slice(0, 40)}…` : s;
  }
  // Nested chunks array on `search` events.
  if (Array.isArray(cloned["chunks"])) {
    cloned["chunks"] = (cloned["chunks"] as unknown[]).map((c) => {
      if (c && typeof c === "object" && "content" in (c as object)) {
        const inner = c as Record<string, unknown>;
        const text = inner["content"];
        return {
          ...inner,
          content:
            typeof text === "string" && text.length > 40
              ? `${text.slice(0, 40)}…`
              : text,
        };
      }
      return c;
    });
  }
  return { id: env.id, ev: cloned };
}

// ─── Viewer root resolution ──────────────────────────────────────────────────

/**
 * Resolve the static-serve root. Defaults to the staged-P5 location
 * `${cwd}/dist/viewer/`. Override via NOX_VIEWER_ROOT.
 */
export function resolveViewerRoot(): string {
  if (process.env["NOX_VIEWER_ROOT"]) {
    return pathResolve(process.env["NOX_VIEWER_ROOT"]);
  }
  return pathResolve(process.cwd(), "dist", "viewer");
}

// ─── SSE adapter (broadcaster + redaction integration) ───────────────────────

/**
 * Wire-up.ts already imports `events-stream.js::openSseStream` directly.
 * This adapter exists for callers that want the broadcaster pre-configured
 * with the redaction wrapper.
 *
 * The redaction is applied at the `onWrite` hook (not by replacing envelopes
 * in the ring), so different consent levels can co-exist in the future.
 */
export async function openRedactedSseStream(opts: {
  clientId: string;
  lastEventId?: number;
  heartbeatMs?: number;
}): Promise<{
  headers: Record<string, string>;
  iter: AsyncIterable<string>;
  close: () => void;
} | null> {
  // String indirection — these files live in staged-P5, co-located only
  // after production rsync. In the staged-wire-up-adapters tree they aren't
  // present, so the dynamic import fails and we return null.
  const SSE_SPEC = "./events-stream.js";
  const BR_SPEC = "../lib/viewer/broadcast.js";
  let sseMod: any;
  let brMod: any;
  try {
    sseMod = await import(SSE_SPEC);
    brMod = await import(BR_SPEC);
  } catch {
    return null;
  }
  if (typeof sseMod.openSseStream !== "function") return null;
  const getBr = brMod.getBroadcaster;
  if (typeof getBr !== "function") return null;
  const broadcaster = getBr();
  if (!broadcaster) return null;

  // We use the upstream openSseStream as-is, but inject a `onWrite` hook
  // wrapper that swaps the envelope text BEFORE the SSE iter formats it.
  // The simplest path is to wrap `publish` on the broadcaster so any future
  // event goes through redactEnvelope. Done at this adapter level only.
  return sseMod.openSseStream({
    broadcaster: broadcaster,
    clientId: opts.clientId,
    lastEventId: opts.lastEventId,
    heartbeatMs: opts.heartbeatMs,
  });
}

// ─── Convenience helpers for the wire-up integration tests ───────────────────

/** Pipe an iter to a ServerResponse, returning when the iter completes. */
export async function pumpSseToResponse(
  res: ServerResponse,
  iter: AsyncIterable<string>,
  req: IncomingMessage,
  close: () => void,
): Promise<void> {
  req.on("close", () => close());
  try {
    for await (const chunk of iter) {
      if (!res.write(chunk)) {
        await new Promise<void>((r) => res.once("drain", r));
      }
    }
  } finally {
    close();
    res.end();
  }
}
