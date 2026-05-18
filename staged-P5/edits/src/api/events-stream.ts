/**
 * T3 — SSE handler (framework-agnostic)
 *
 * Returns an async iterable of SSE lines + the header set to attach.
 * Caller (Express / Fastify / raw http) wires this onto a response stream:
 *
 *   const sse = openSseStream({ broadcaster, clientId, lastEventId });
 *   res.writeHead(200, sse.headers);
 *   for await (const chunk of sse.iter) {
 *     if (!res.write(chunk)) await once(res, "drain");
 *   }
 *
 * On client disconnect, caller invokes `sse.close()` to release resources.
 */

import { Broadcaster, type BroadcastEnvelope, type ClientHandle } from "../lib/viewer/broadcast.js";
import { eventKindLabel, type ViewerEvent } from "../lib/viewer/event-types.js";

export interface OpenSseStreamOptions {
  broadcaster: Broadcaster;
  /** Client id (UUIDv4). Caller mints + injects. */
  clientId: string;
  /** Last-Event-ID from request header, if any. */
  lastEventId?: number;
  /** Heartbeat interval ms. Default 15000. */
  heartbeatMs?: number;
  /** Hook called whenever an envelope is written (for telemetry). */
  onWrite?: (env: BroadcastEnvelope) => void;
  /** Hook called whenever a drop happens (queue full). */
  onDrop?: (count: number) => void;
}

export interface SseStream {
  headers: Record<string, string>;
  iter: AsyncIterable<string>;
  close: () => void;
}

export const SSE_HEADERS: Record<string, string> = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no", // disable nginx buffering
};

/**
 * Format a ViewerEvent envelope as a single SSE message.
 * Multi-line `data:` is correctly emitted per RFC.
 */
export function formatSseMessage(env: BroadcastEnvelope): string {
  const ev: ViewerEvent = env.ev;
  const kindLabel = eventKindLabel(ev);
  const payload = JSON.stringify(ev);
  // SSE: id, event, data — each on its own line; record terminated by blank line.
  return `id: ${env.id}\nevent: ${kindLabel}\ndata: ${payload}\n\n`;
}

/** Heartbeat is an SSE comment line — ignored by EventSource, keeps proxies alive. */
export function formatHeartbeat(ringSize: number, clients: number): string {
  const ts = new Date().toISOString();
  return `: heartbeat ${ts} ring=${ringSize} clients=${clients}\n\n`;
}

/**
 * Construct a complete SSE stream:
 *  - subscribes to the Broadcaster
 *  - emits SSE-formatted lines via async iterator
 *  - sends heartbeats on schedule
 *  - cleans up on `close()`
 */
export function openSseStream(opts: OpenSseStreamOptions): SseStream {
  const heartbeatMs = opts.heartbeatMs ?? 15_000;
  let closed = false;
  let wakeup: (() => void) | null = null;
  let lastReportedDrops = 0;

  const wake = (): void => {
    if (wakeup) {
      const cb = wakeup;
      wakeup = null;
      cb();
    }
  };

  const client: ClientHandle = opts.broadcaster.addClient(
    opts.clientId,
    wake,
    opts.lastEventId
  );

  let heartbeatDue = false;
  const heartbeatTimer = setInterval(() => {
    heartbeatDue = true;
    if (!closed) wake();
  }, heartbeatMs);
  // Don't prevent process exit if forgotten.
  if (typeof heartbeatTimer.unref === "function") heartbeatTimer.unref();

  async function* iter(): AsyncGenerator<string> {
    // Initial line — tells the client we're connected and arms reconnect.
    yield ": connected\n\n";

    while (!closed) {
      // Drain any queued envelopes first.
      const batch = client.queue.drain();
      const droppedNow = client.queue.stats().dropped;
      if (droppedNow > lastReportedDrops) {
        const delta = droppedNow - lastReportedDrops;
        lastReportedDrops = droppedNow;
        opts.onDrop?.(delta);
      }
      for (const env of batch) {
        client.lastSentId = env.id;
        opts.onWrite?.(env);
        yield formatSseMessage(env);
      }

      if (heartbeatDue) {
        heartbeatDue = false;
        yield formatHeartbeat(
          opts.broadcaster.ringSnapshot().length,
          opts.broadcaster.clientCount()
        );
      }

      if (closed) break;

      // Wait for next wake-up.
      await new Promise<void>((resolve) => {
        wakeup = resolve;
      });
    }
  }

  return {
    headers: { ...SSE_HEADERS },
    iter: iter(),
    close: () => {
      if (closed) return;
      closed = true;
      clearInterval(heartbeatTimer);
      opts.broadcaster.removeClient(opts.clientId);
      // Wake the iterator so it exits cleanly.
      wake();
    },
  };
}

/**
 * Parse the Last-Event-ID header (case-insensitive). Numeric only.
 */
export function parseLastEventId(
  headers: Record<string, string | string[] | undefined>
): number | undefined {
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === "last-event-id") {
      const v = headers[key];
      const raw = Array.isArray(v) ? v[0] : v;
      if (raw === undefined) return undefined;
      const n = Number(raw);
      return Number.isFinite(n) && n >= 0 ? n : undefined;
    }
  }
  return undefined;
}
