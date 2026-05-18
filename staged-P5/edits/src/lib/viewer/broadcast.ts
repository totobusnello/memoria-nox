/**
 * T10 — Multi-client broadcast
 *
 * Single source (instrumentation) → fan-out to N SSE clients.
 * Each client gets its own BackpressureQueue so a slow one cannot
 * stall fast ones (no head-of-line blocking).
 *
 * In addition to per-client queues, a SHARED ring buffer keeps the last
 * N events so reconnecting clients can resume via Last-Event-ID.
 */

import { BackpressureQueue } from "./backpressure.js";
import { type ViewerEvent } from "./event-types.js";

export interface BroadcastEnvelope {
  /** Monotonic numeric id used in SSE `id:` line. */
  id: number;
  ev: ViewerEvent;
}

export interface ClientHandle {
  /** Globally unique id. */
  id: string;
  /** Per-client queue. */
  queue: BackpressureQueue<BroadcastEnvelope>;
  /** Last id sent to this client (for Last-Event-ID resume). */
  lastSentId: number;
  /** Notify hook — called when push happens (so consumer wakes up). */
  notify: () => void;
}

export interface BroadcasterOptions {
  /** Ring buffer (replay) capacity. Default 1000. */
  ringCapacity?: number;
  /** Per-client queue capacity. Default 100. */
  clientCapacity?: number;
}

export class Broadcaster {
  private readonly ring: BroadcastEnvelope[] = [];
  private readonly clients = new Map<string, ClientHandle>();
  private nextId = 1;
  public readonly ringCapacity: number;
  public readonly clientCapacity: number;

  constructor(opts: BroadcasterOptions = {}) {
    this.ringCapacity = opts.ringCapacity ?? 1000;
    this.clientCapacity = opts.clientCapacity ?? 100;
  }

  /**
   * Publish an event. Updates ring buffer and pushes to all connected clients.
   * Each client backpressure is independent; producer never blocks.
   */
  publish(ev: ViewerEvent): BroadcastEnvelope {
    const envelope: BroadcastEnvelope = { id: this.nextId, ev };
    this.nextId += 1;

    this.ring.push(envelope);
    if (this.ring.length > this.ringCapacity) {
      this.ring.shift();
    }

    for (const client of this.clients.values()) {
      client.queue.push(envelope);
      try {
        client.notify();
      } catch {
        // Notification failure must never stop broadcast.
      }
    }
    return envelope;
  }

  /**
   * Register a new SSE client. Returns the client handle for read access.
   * If `lastEventId` provided and within ring, the queue is pre-seeded with
   * the gap so client can resume.
   */
  addClient(
    id: string,
    notify: () => void,
    lastEventId?: number
  ): ClientHandle {
    const queue = new BackpressureQueue<BroadcastEnvelope>(this.clientCapacity);
    const client: ClientHandle = {
      id,
      queue,
      lastSentId: lastEventId ?? 0,
      notify,
    };
    this.clients.set(id, client);

    if (lastEventId !== undefined) {
      for (const env of this.ring) {
        if (env.id > lastEventId) {
          queue.push(env);
        }
      }
    }

    return client;
  }

  removeClient(id: string): void {
    this.clients.delete(id);
  }

  /** Read current ring buffer snapshot (shallow copy). */
  ringSnapshot(): readonly BroadcastEnvelope[] {
    return this.ring.slice();
  }

  /** Number of active clients. */
  clientCount(): number {
    return this.clients.size;
  }

  /** Per-client stats. */
  clientStats(): Array<{
    id: string;
    queueSize: number;
    dropped: number;
    lastSentId: number;
  }> {
    return Array.from(this.clients.values()).map((c) => ({
      id: c.id,
      queueSize: c.queue.length,
      dropped: c.queue.stats().dropped,
      lastSentId: c.lastSentId,
    }));
  }

  /** Force-drop oldest envelopes globally (e.g. memory pressure). */
  trimRingTo(size: number): number {
    let dropped = 0;
    while (this.ring.length > size) {
      this.ring.shift();
      dropped += 1;
    }
    return dropped;
  }
}
