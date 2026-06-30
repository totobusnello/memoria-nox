/**
 * src/observability/collectors/process.collector.ts — Node runtime metrics.
 *
 * Periodically samples Node.js process stats into the corresponding gauges
 * and counters. Intended to be wired by the API server bootstrap:
 *
 *   import { startProcessCollector } from "./observability/collectors/process.collector.js";
 *   startProcessCollector();
 *
 * Sampling cadence is conservative (10s) to minimise CPU overhead.
 */
import { performance, monitorEventLoopDelay } from "node:perf_hooks";
import {
  processCpuUserSecondsTotal,
  processCpuSystemSecondsTotal,
  processResidentMemoryBytes,
  processOpenFds,
  nodejsEventloopLagSeconds,
} from "../metrics.js";

let intervalHandle: NodeJS.Timeout | undefined;
let lastCpu: NodeJS.CpuUsage | undefined;
let elMonitor: ReturnType<typeof monitorEventLoopDelay> | undefined;

export interface ProcessCollectorOpts {
  /** Sampling interval ms. Default 10_000. */
  intervalMs?: number;
}

export function startProcessCollector(opts: ProcessCollectorOpts = {}): void {
  if (intervalHandle) return; // idempotent
  const interval = opts.intervalMs ?? 10_000;

  elMonitor = monitorEventLoopDelay({ resolution: 50 });
  elMonitor.enable();

  lastCpu = process.cpuUsage();

  intervalHandle = setInterval(() => {
    try {
      collectOnce();
    } catch {
      // Never throw from a metrics sampler.
    }
  }, interval);
  // Allow process to exit cleanly.
  intervalHandle.unref?.();
  // Take one immediate sample for fresh /metrics.
  collectOnce();
}

export function stopProcessCollector(): void {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = undefined;
  }
  if (elMonitor) {
    elMonitor.disable();
    elMonitor = undefined;
  }
  lastCpu = undefined;
}

export function collectOnce(): void {
  // CPU — delta since last sample. Counter is monotonic, so we accumulate.
  const cur = process.cpuUsage();
  if (lastCpu) {
    const userDeltaMicros = cur.user - lastCpu.user;
    const sysDeltaMicros = cur.system - lastCpu.system;
    if (userDeltaMicros > 0) {
      processCpuUserSecondsTotal.inc({}, userDeltaMicros / 1e6);
    }
    if (sysDeltaMicros > 0) {
      processCpuSystemSecondsTotal.inc({}, sysDeltaMicros / 1e6);
    }
  }
  lastCpu = cur;

  // Memory
  const mem = process.memoryUsage();
  processResidentMemoryBytes.set(mem.rss);

  // Open FDs (POSIX-only best effort).
  const fdCount = bestEffortFdCount();
  if (fdCount >= 0) processOpenFds.set(fdCount);

  // Event loop lag — use mean since last sample then reset.
  if (elMonitor) {
    const meanNs = elMonitor.mean;
    elMonitor.reset();
    if (Number.isFinite(meanNs)) {
      nodejsEventloopLagSeconds.set(meanNs / 1e9);
    }
  }

  // Touch performance.now() so V8 doesn't dead-code-elim.
  void performance.now();
}

function bestEffortFdCount(): number {
  try {
    // /proc/self/fd is Linux-specific.
    if (process.platform !== "linux") return -1;
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const fs = require("node:fs") as typeof import("node:fs");
    const list = fs.readdirSync("/proc/self/fd");
    return list.length;
  } catch {
    return -1;
  }
}
