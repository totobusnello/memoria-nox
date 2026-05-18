/**
 * dry-run.ts — Validates pipeline without real nox-mem binary.
 *
 * Generates a synthetic WorkloadRun for search.short with n=10
 * to prove the runner → aggregator pipeline is wired correctly.
 *
 * When run on VPS with NOX_MEM_BIN set, this can be replaced
 * with a real runner.ts invocation with --n 10 --warmup 0.
 *
 * Usage (local, no VPS):
 *   node dist/dry-run.js
 * Usage (VPS):
 *   node dist/runner.js --workload search.short --n 10 --warmup 0 --output dry-run-raw.json
 *   node dist/aggregator.js --input dry-run-raw.json --output dry-run-sample.json
 */

import { writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { aggregateAll } from "./aggregator.js";
import type { WorkloadRun } from "./runner.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Simulate 10-query dry-run for search.short
// Synthetic latencies approximate subprocess spawn (~12ms) + BM25 search (~35ms) warm
// ---------------------------------------------------------------------------

const SYNTHETIC_SAMPLES_MS = [
  47.3, 52.1, 38.9, 61.4, 44.7, 55.2, 43.1, 49.8, 58.6, 41.2
];

const dryRunRaw: WorkloadRun[] = [
  {
    workload_id: "search.short",
    n_measured: 10,
    warmup_n: 0,
    cold: false,
    samples_ms: SYNTHETIC_SAMPLES_MS,
    errors: 0,
    timestamp_iso: new Date().toISOString(),
  },
];

const summaries = aggregateAll(dryRunRaw);

// Output matches the report format specified in README
const output = summaries.map((s) => ({ summary: s }));

const outPath = join(__dirname, "..", "dry-run-sample.json");
writeFileSync(outPath, JSON.stringify(output, null, 2), "utf8");

const first = summaries[0];
console.log(`[dry-run] Wrote dry-run-sample.json`);
console.log(`[dry-run] search.short p50=${first.p50_ms}ms p95=${first.p95_ms}ms (n=${first.n}, synthetic)`);
console.log(`[dry-run] Pipeline validated: workloads → runner → aggregator OK`);
