/**
 * src/observability/adapters/p5-adapter.ts — Viewer (P5) instrumentation.
 *
 * Two entry points:
 *   1. `wrapBroadcast(broadcast)`  — instruments the broadcast pipeline so
 *      every event emitted is counted by type.
 *   2. `trackConnection(socket)`   — increments/decrements the open
 *      connection gauge for the lifetime of the SSE/WS socket.
 *
 * Wiring example (in src/lib/viewer/broadcast.ts):
 *
 *   import { wrapBroadcast, trackConnection } from "../../observability/adapters/p5-adapter.js";
 *
 *   const safeBroadcast = wrapBroadcast(rawBroadcast);
 *   server.on("connection", (sock) => trackConnection(sock));
 *
 * The wiring is ~5 LOC at the integration site.
 */
import {
  recordViewerConnect,
  recordViewerDisconnect,
  recordViewerEvent,
  recordViewerDropped,
} from "../record.js";

export interface BroadcastEvent {
  type: string;
  [k: string]: unknown;
}

export type BroadcastFn = (event: BroadcastEvent) => void | Promise<void>;

/**
 * Wrap a broadcast function so every emitted event is counted.
 * If the inner broadcast throws, the event is counted as dropped/error and
 * the error re-thrown.
 */
export function wrapBroadcast(inner: BroadcastFn): BroadcastFn {
  return async (event: BroadcastEvent) => {
    try {
      await inner(event);
      recordViewerEvent(event.type);
    } catch (err) {
      recordViewerDropped("queue_full");
      throw err;
    }
  };
}

export interface SocketLike {
  on(event: "close" | "error" | string, listener: () => void): unknown;
}

/**
 * Track a viewer SSE/WS connection lifecycle. Increments the gauge on entry
 * and decrements when the socket closes (or errors).
 */
export function trackConnection(socket: SocketLike): void {
  recordViewerConnect();
  let decremented = false;
  const onClose = () => {
    if (decremented) return;
    decremented = true;
    recordViewerDisconnect();
  };
  socket.on("close", onClose);
  socket.on("error", onClose);
}

/**
 * Manual backpressure reporting helper for upstream code paths that drop
 * events without going through `wrapBroadcast`.
 */
export function reportBackpressureDrop(reason: "slow_consumer" | "queue_full" | "client_gone"): void {
  recordViewerDropped(reason);
}

/**
 * Example — minimal wiring inside an existing SSE server:
 *
 *   import { trackConnection, wrapBroadcast } from "./observability/adapters/p5-adapter.js";
 *
 *   const broadcast = wrapBroadcast(rawBroadcast);
 *
 *   sseRouter.get("/events", (req, res) => {
 *     trackConnection(res);
 *     subscribe((evt) => broadcast(evt));
 *   });
 */
