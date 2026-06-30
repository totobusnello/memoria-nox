/**
 * src/lib/hooks/worker.ts — T9: Async worker queue.
 *
 * Backpressure-aware bounded queue:
 *   - enqueue() returns synchronously (non-blocking for callers like
 *     OpenClaw afterTurn hook). Returns {accepted, reason}.
 *   - When full, oldest event is dropped + telemetry "queue_full" row
 *     emitted. New event takes its slot (most-recent-wins).
 *   - A drain loop runs every `tickMs` ms, processing batches of up to
 *     `batchSize` events through the pipeline.
 *
 * The worker is the bridge between the synchronous hook trigger (an
 * OpenClaw turn ended) and the async pipeline (which may call out to
 * embed/ingest).
 *
 * Lifecycle:
 *   const w = createWorker({ pipeline, ...opts });
 *   w.start();
 *   w.enqueue(event);
 *   ...
 *   await w.stop();  // drains remaining + shuts down
 */

import type { PipelineHandle } from "./pipeline.js";
import type { HookEvent, HookResult, HookTelemetryRow } from "./types.js";

export interface WorkerOpts {
  pipeline: PipelineHandle;
  /** Max events held in queue. Default 10_000 (matches spec ring buffer). */
  maxSize?: number;
  /** Drain tick interval. Default 250ms (matches spec §3 T3). */
  tickMs?: number;
  /** Max events processed per tick. Default 100. */
  batchSize?: number;
  /** Optional sink for queue-overflow telemetry. */
  telemetry?: (row: HookTelemetryRow) => void | Promise<void>;
}

export interface WorkerStats {
  enqueued: number;
  processed: number;
  rejected: number;
  captured: number;
  dropped: number;
  errors: number;
  queueDepth: number;
}

export interface WorkerHandle {
  enqueue(event: HookEvent): { accepted: boolean; reason: string; depth: number };
  start(): void;
  stop(): Promise<void>;
  drain(): Promise<HookResult[]>;
  stats(): WorkerStats;
}

export function createWorker(opts: WorkerOpts): WorkerHandle {
  const pipeline = opts.pipeline;
  const maxSize = opts.maxSize ?? 10_000;
  const tickMs = opts.tickMs ?? 250;
  const batchSize = opts.batchSize ?? 100;
  const telemetry = opts.telemetry;

  const queue: HookEvent[] = [];
  let timer: ReturnType<typeof setInterval> | null = null;
  let running = false;
  let inFlight: Promise<void> | null = null;

  const counters: WorkerStats = {
    enqueued: 0,
    processed: 0,
    rejected: 0,
    captured: 0,
    dropped: 0,
    errors: 0,
    queueDepth: 0,
  };

  function refreshDepth(): void {
    counters.queueDepth = queue.length;
  }

  function emitOverflow(droppedEvent: HookEvent): void {
    if (!telemetry) return;
    try {
      void telemetry({
        event_uuid: droppedEvent.event_id,
        session_id: droppedEvent.session_id ?? "unknown",
        project_slug: droppedEvent.project_slug ?? "unknown",
        kind: "tool_use",
        timestamp: droppedEvent.ts,
        payload_json: JSON.stringify({ layer: "worker", reason: "queue_full_dropped_oldest" }),
        redaction_count: 0,
        retention_days: 30,
      });
    } catch {
      /* ignore */
    }
  }

  async function tick(force = false): Promise<void> {
    if ((!running && !force) || queue.length === 0) return;
    const batch: HookEvent[] = queue.splice(0, batchSize);
    refreshDepth();
    for (const ev of batch) {
      try {
        const result = await pipeline.run(ev);
        counters.processed += 1;
        if (result.captured) counters.captured += 1;
        else counters.rejected += 1;
      } catch {
        counters.errors += 1;
      }
    }
  }

  function scheduleTick(): void {
    inFlight = tick().finally(() => {
      inFlight = null;
    });
  }

  return {
    enqueue(event: HookEvent): { accepted: boolean; reason: string; depth: number } {
      counters.enqueued += 1;
      if (queue.length >= maxSize) {
        // Drop oldest, append new
        const dropped = queue.shift();
        if (dropped) {
          counters.dropped += 1;
          emitOverflow(dropped);
        }
        queue.push(event);
        refreshDepth();
        return { accepted: true, reason: "queue_full_dropped_oldest", depth: queue.length };
      }
      queue.push(event);
      refreshDepth();
      return { accepted: true, reason: "enqueued", depth: queue.length };
    },

    start(): void {
      if (running) return;
      running = true;
      timer = setInterval(scheduleTick, tickMs);
    },

    async stop(): Promise<void> {
      running = false;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
      // Drain remaining (force=true to bypass running check)
      if (inFlight) await inFlight;
      while (queue.length > 0) {
        await tick(true);
      }
    },

    async drain(): Promise<HookResult[]> {
      const out: HookResult[] = [];
      while (queue.length > 0) {
        const ev = queue.shift()!;
        refreshDepth();
        try {
          const r = await pipeline.run(ev);
          counters.processed += 1;
          if (r.captured) counters.captured += 1;
          else counters.rejected += 1;
          out.push(r);
        } catch {
          counters.errors += 1;
        }
      }
      return out;
    },

    stats(): WorkerStats {
      refreshDepth();
      return { ...counters };
    },
  };
}
