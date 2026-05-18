/**
 * T9 — Backpressure ring buffer
 *
 * Bounded queue per SSE client. Producer pushes events; consumer drains.
 * If consumer is slow and buffer hits capacity, OLDEST event is dropped
 * (not the new one) so the recent stream stays current. Producer NEVER
 * blocks — drop counter is incremented and exposed via `stats()`.
 *
 * Design:
 *  - O(1) push + drain via circular buffer (Array-backed deque)
 *  - No locks (single-threaded JS); concurrency safe wrt the event loop
 *  - Stats are read-only snapshots
 */

export interface BackpressureStats {
  /** Items currently buffered. */
  size: number;
  /** Total drop count since construction. */
  dropped: number;
  /** Total enqueued since construction. */
  enqueued: number;
  /** Capacity. */
  capacity: number;
}

export class BackpressureQueue<T> {
  private buf: Array<T | undefined>;
  private head = 0;
  private tail = 0;
  private size_ = 0;
  private dropped_ = 0;
  private enqueued_ = 0;

  constructor(public readonly capacity: number) {
    if (capacity <= 0 || !Number.isFinite(capacity)) {
      throw new Error(`BackpressureQueue capacity must be > 0, got ${capacity}`);
    }
    this.buf = new Array(capacity);
  }

  /**
   * Push an item. Returns:
   *  - "ok" if buffered
   *  - "dropped_oldest" if buffer was full and oldest was evicted to make room
   */
  push(item: T): "ok" | "dropped_oldest" {
    this.enqueued_ += 1;
    if (this.size_ === this.capacity) {
      // Drop oldest by advancing head.
      this.buf[this.head] = undefined;
      this.head = (this.head + 1) % this.capacity;
      this.size_ -= 1;
      this.dropped_ += 1;
      // continue to insert new at tail
    }
    this.buf[this.tail] = item;
    this.tail = (this.tail + 1) % this.capacity;
    this.size_ += 1;
    return this.dropped_ > 0 && this.size_ === this.capacity ? "dropped_oldest" : "ok";
  }

  /** Pop oldest item. Undefined if empty. */
  shift(): T | undefined {
    if (this.size_ === 0) return undefined;
    const out = this.buf[this.head] as T;
    this.buf[this.head] = undefined;
    this.head = (this.head + 1) % this.capacity;
    this.size_ -= 1;
    return out;
  }

  /** Drain up to `max` items into an array. */
  drain(max = Infinity): T[] {
    const out: T[] = [];
    let n = 0;
    while (this.size_ > 0 && n < max) {
      const item = this.shift();
      if (item !== undefined) out.push(item);
      n += 1;
    }
    return out;
  }

  get length(): number {
    return this.size_;
  }

  stats(): BackpressureStats {
    return {
      size: this.size_,
      dropped: this.dropped_,
      enqueued: this.enqueued_,
      capacity: this.capacity,
    };
  }

  /** Reset to empty. Counters preserved unless `hard=true`. */
  clear(hard = false): void {
    this.head = 0;
    this.tail = 0;
    this.size_ = 0;
    this.buf = new Array(this.capacity);
    if (hard) {
      this.dropped_ = 0;
      this.enqueued_ = 0;
    }
  }
}

/**
 * Detect whether write to a Node.js Writable is hitting backpressure.
 * Convenience wrapper for `res.write()` return value semantics.
 */
export interface BackpressureSink {
  /** Buffered amount in bytes (best-effort, may be undefined). */
  writableLength?: number;
  /** High-water mark (bytes). */
  writableHighWaterMark?: number;
  write?(chunk: string): boolean;
}

export function isSinkSaturated(sink: BackpressureSink): boolean {
  const len = sink.writableLength;
  const hwm = sink.writableHighWaterMark;
  if (typeof len !== "number" || typeof hwm !== "number") return false;
  return len >= hwm;
}
