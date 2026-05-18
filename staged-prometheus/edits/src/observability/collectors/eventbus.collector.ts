/**
 * src/observability/collectors/eventbus.collector.ts
 *
 * Subscribes to the P5 event bus and translates events into viewer metrics.
 *
 * The event bus interface is intentionally minimal:
 *
 *   interface EventBus {
 *     on(event: string, handler: (payload: { type: string; … }) => void): void;
 *     off(event: string, handler: Function): void;
 *   }
 *
 * Production wiring imports the actual `EventBus` from P5; tests pass a stub.
 */
import {
  recordViewerConnect,
  recordViewerDisconnect,
  recordViewerEvent,
  recordViewerDropped,
} from "../record.js";

export interface EventBusLike {
  on(event: string, handler: (payload: unknown) => void): void;
  off?(event: string, handler: (payload: unknown) => void): void;
}

type Handlers = {
  connect: (payload: unknown) => void;
  disconnect: (payload: unknown) => void;
  event: (payload: unknown) => void;
  drop: (payload: unknown) => void;
};

let handlers: Handlers | undefined;

export function attachEventBusCollector(bus: EventBusLike): void {
  if (handlers) return; // idempotent

  handlers = {
    connect: () => recordViewerConnect(),
    disconnect: () => recordViewerDisconnect(),
    event: (payload: unknown) => {
      const type = isObj(payload) && typeof payload.type === "string" ? payload.type : "other";
      recordViewerEvent(type);
    },
    drop: (payload: unknown) => {
      const reason =
        isObj(payload) && typeof payload.reason === "string"
          ? (payload.reason as "slow_consumer" | "queue_full" | "client_gone")
          : "queue_full";
      recordViewerDropped(reason);
    },
  };

  bus.on("viewer.connect", handlers.connect);
  bus.on("viewer.disconnect", handlers.disconnect);
  bus.on("viewer.event", handlers.event);
  bus.on("viewer.drop", handlers.drop);
}

export function detachEventBusCollector(bus: EventBusLike): void {
  if (!handlers || !bus.off) return;
  bus.off("viewer.connect", handlers.connect);
  bus.off("viewer.disconnect", handlers.disconnect);
  bus.off("viewer.event", handlers.event);
  bus.off("viewer.drop", handlers.drop);
  handlers = undefined;
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}
