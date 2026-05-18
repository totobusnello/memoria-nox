/**
 * aggregator.ts — Compute p50/p95/p99/p99.9/min/max/stddev from runner output.
 *
 * Input:  JSON array of WorkloadRun (output of runner.ts)
 * Output: JSON array of WorkloadSummary
 *
 * Outlier policy: NO trimming. All samples included. GC pauses inflate
 * p99/p99.9 intentionally — tail behavior is what we're measuring.
 *
 * Usage:
 *   node dist/aggregator.js --input results/run.json --output results/summary.json
 *   node dist/aggregator.js --input results/run.json  # prints to stdout
 */

import { readFileSync, writeFileSync } from "node:fs";
import type { WorkloadRun } from "./runner.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkloadSummary {
  workload: string;
  n: number;
  warmup_n: number;
  cold: boolean;
  p50_ms: number | null;
  p75_ms: number | null;
  p90_ms: number | null;
  p95_ms: number | null;
  p99_ms: number | null;
  "p99.9_ms": number | null;
  min_ms: number | null;
  max_ms: number | null;
  mean_ms: number | null;
  stddev_ms: number | null;
  errors: number;
  timestamp_iso: string;
  note?: string;
}

// ---------------------------------------------------------------------------
// Stats utilities
// ---------------------------------------------------------------------------

/** Sort samples ascending and return the value at percentile p (0–100). */
function percentile(sorted: number[], p: number): number | null {
  if (sorted.length === 0) return null;
  if (p <= 0) return sorted[0];
  if (p >= 100) return sorted[sorted.length - 1];

  // Nearest-rank method
  const rank = Math.ceil((p / 100) * sorted.length);
  return sorted[rank - 1];
}

function mean(samples: number[]): number | null {
  if (samples.length === 0) return null;
  return samples.reduce((a, b) => a + b, 0) / samples.length;
}

function stddev(samples: number[], avg: number): number | null {
  if (samples.length < 2) return null;
  const variance =
    samples.reduce((acc, v) => acc + (v - avg) ** 2, 0) / (samples.length - 1);
  return Math.sqrt(variance);
}

function round2(v: number | null): number | null {
  if (v === null) return null;
  return Math.round(v * 100) / 100;
}

// ---------------------------------------------------------------------------
// Core aggregation
// ---------------------------------------------------------------------------

export function aggregateRun(run: WorkloadRun): WorkloadSummary {
  const sorted = [...run.samples_ms].sort((a, b) => a - b);
  const avg = mean(sorted);

  if (sorted.length === 0) {
    return {
      workload: run.workload_id,
      n: run.n_measured,
      warmup_n: run.warmup_n,
      cold: run.cold,
      p50_ms: null,
      p75_ms: null,
      p90_ms: null,
      p95_ms: null,
      p99_ms: null,
      "p99.9_ms": null,
      min_ms: null,
      max_ms: null,
      mean_ms: null,
      stddev_ms: null,
      errors: run.errors,
      timestamp_iso: run.timestamp_iso,
      note: run.workload_id.endsWith("placeholder")
        ? "NOT_YET — placeholder workload"
        : `No samples collected (errors: ${run.errors})`,
    };
  }

  return {
    workload: run.workload_id,
    n: sorted.length,
    warmup_n: run.warmup_n,
    cold: run.cold,
    p50_ms: round2(percentile(sorted, 50)),
    p75_ms: round2(percentile(sorted, 75)),
    p90_ms: round2(percentile(sorted, 90)),
    p95_ms: round2(percentile(sorted, 95)),
    p99_ms: round2(percentile(sorted, 99)),
    "p99.9_ms": round2(percentile(sorted, 99.9)),
    min_ms: round2(sorted[0]),
    max_ms: round2(sorted[sorted.length - 1]),
    mean_ms: round2(avg),
    stddev_ms: round2(avg !== null ? stddev(sorted, avg) : null),
    errors: run.errors,
    timestamp_iso: run.timestamp_iso,
  };
}

export function aggregateAll(runs: WorkloadRun[]): WorkloadSummary[] {
  return runs.map(aggregateRun);
}

// ---------------------------------------------------------------------------
// CLI entrypoint
// ---------------------------------------------------------------------------

function main() {
  const args = process.argv.slice(2);

  const inputPath =
    args.includes("--input")
      ? args[args.indexOf("--input") + 1]
      : null;
  const outputPath =
    args.includes("--output")
      ? args[args.indexOf("--output") + 1]
      : null;

  if (!inputPath) {
    console.error("[aggregator] --input <path> is required");
    process.exit(1);
  }

  const raw = JSON.parse(readFileSync(inputPath, "utf8")) as WorkloadRun[];
  const summaries = aggregateAll(raw);

  const out = JSON.stringify(summaries, null, 2);
  if (outputPath) {
    writeFileSync(outputPath, out, "utf8");
    console.log(`[aggregator] Wrote ${summaries.length} summary(ies) to ${outputPath}`);
  } else {
    console.log(out);
  }
}

// Only run CLI when invoked directly (not when imported as a module)
const isMain =
  process.argv[1] &&
  (process.argv[1].endsWith("aggregator.js") ||
    process.argv[1].endsWith("aggregator.ts"));
if (isMain) {
  main();
}
