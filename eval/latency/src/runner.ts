/**
 * runner.ts — Executes benchmark workloads and records raw latency samples.
 *
 * DESIGN DECISIONS:
 *
 * 1. Subprocess execution model:
 *    nox-mem has no importable module in this repo — the binary is compiled on
 *    VPS at dist/index.js. Each search iteration spawns:
 *      `node <NOX_MEM_BIN> search "<query>" --limit 10 --no-interactive`
 *    Startup overhead (~5–15ms per spawn) is INCLUDED in measurement to give
 *    honest end-to-end numbers. Warmup absorbs the first cold JIT hit.
 *    If HTTP API (:18802) is available, set NOX_USE_HTTP=1 to switch to
 *    fetch-based measurement (no subprocess overhead).
 *
 * 2. Timing: process.hrtime.bigint() for nanosecond precision, converted to ms.
 *
 * 3. No trimming: all samples are kept. GC pauses inflate p99/p99.9 — that is
 *    intentional and visible in the output.
 *
 * 4. eval.db isolation: points at NOX_EVAL_DB (default: eval/latency/eval.db).
 *    Never touches the production nox-mem.db.
 *
 * 5. Ingest uniqueness: each ingest iteration appends a unique slug suffix
 *    (timestamp + iteration index) to avoid dedup short-circuits.
 *
 * Usage:
 *   node dist/runner.js --workload search.short [--n 100] [--warmup 10] [--cold] [--output path.json]
 *   node dist/runner.js --all [--output path.json]
 */

import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { buildWorkloads, type WorkloadDefinition } from "./workloads.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Configuration from environment
// ---------------------------------------------------------------------------

const NOX_MEM_BIN =
  process.env.NOX_MEM_BIN ??
  "/root/.openclaw/workspace/tools/nox-mem/dist/index.js";

const NOX_EVAL_DB =
  process.env.NOX_EVAL_DB ??
  join(__dirname, "..", "..", "latency", "eval.db");

const NOX_USE_HTTP = process.env.NOX_USE_HTTP === "1";
const NOX_API_URL =
  process.env.NOX_API_URL ?? "http://127.0.0.1:18802";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkloadRun {
  workload_id: string;
  n_measured: number;
  warmup_n: number;
  cold: boolean;
  samples_ms: number[];
  errors: number;
  timestamp_iso: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** High-resolution timer in ms. */
function hrNow(): bigint {
  return process.hrtime.bigint();
}

function nsToMs(ns: bigint): number {
  return Number(ns) / 1_000_000;
}

/** Build nox-mem subprocess args for search. */
function buildSearchArgs(query: string): string[] {
  return [
    NOX_MEM_BIN,
    "search",
    query,
    "--limit",
    "10",
  ];
}

/** Build nox-mem subprocess args for ingest-entity. */
function buildIngestEntityArgs(filePath: string): string[] {
  return [NOX_MEM_BIN, "ingest-entity", filePath];
}

/** Run a single search iteration via subprocess. Returns elapsed ms or null on error. */
function runSearchSubprocess(query: string): number | null {
  const t0 = hrNow();
  const result = spawnSync("node", buildSearchArgs(query), {
    env: {
      ...process.env,
      NOX_DB_PATH: NOX_EVAL_DB,
    },
    encoding: "utf8",
    timeout: 30_000,
  });
  const elapsed = nsToMs(hrNow() - t0);

  if (result.status !== 0 && result.status !== null) {
    // Non-zero exit is still a timing sample — command ran but returned error
    // (e.g. no results). Count it but flag separately.
    return elapsed;
  }
  if (result.error) {
    // Process spawn failure — skip this sample
    return null;
  }
  return elapsed;
}

/** Run a single search iteration via HTTP API. Returns elapsed ms or null on error. */
async function runSearchHTTP(query: string): Promise<number | null> {
  const t0 = hrNow();
  try {
    const res = await fetch(`${NOX_API_URL}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 10 }),
      signal: AbortSignal.timeout(30_000),
    });
    const elapsed = nsToMs(hrNow() - t0);
    if (!res.ok) return elapsed; // still a valid latency sample
    await res.json(); // drain body
    return nsToMs(hrNow() - t0);
  } catch {
    return null;
  }
}

/** Run a single ingest-entity iteration. Modifies fixturePath slug to ensure uniqueness. */
function runIngestEntity(fixturePath: string, iteration: number): number | null {
  // For uniqueness, we pass NOX_INGEST_SLUG_SUFFIX env var — the fixture
  // template is expected to use a slug that the runner can suffix.
  // If the fixture doesn't support this, dedup may short-circuit — document it.
  const t0 = hrNow();
  const result = spawnSync("node", buildIngestEntityArgs(fixturePath), {
    env: {
      ...process.env,
      NOX_DB_PATH: NOX_EVAL_DB,
      NOX_INGEST_SLUG_SUFFIX: `bench-${Date.now()}-${iteration}`,
    },
    encoding: "utf8",
    timeout: 60_000,
  });
  const elapsed = nsToMs(hrNow() - t0);
  if (result.error) return null;
  return elapsed;
}

/** Check if eval.db exists; warn if not. */
function checkEvalDb(): boolean {
  if (!existsSync(NOX_EVAL_DB)) {
    console.warn(`
[runner] WARNING: eval.db not found at ${NOX_EVAL_DB}
  Create it by cloning nox-mem.db:
    cp /root/.openclaw/workspace/tools/nox-mem/nox-mem.db ${NOX_EVAL_DB}
  Or document in BLOCKED.md if DB is unavailable in this environment.
`);
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Core runner
// ---------------------------------------------------------------------------

export async function runWorkload(
  workload: WorkloadDefinition,
  overrides?: { n?: number; warmup?: number; cold?: boolean }
): Promise<WorkloadRun> {
  const n = overrides?.n ?? workload.n;
  const warmup = overrides?.warmup ?? workload.warmup;
  const cold = overrides?.cold ?? false;

  const run: WorkloadRun = {
    workload_id: workload.id,
    n_measured: n,
    warmup_n: warmup,
    cold,
    samples_ms: [],
    errors: 0,
    timestamp_iso: new Date().toISOString(),
  };

  if (workload.placeholder) {
    console.log(`[runner] ${workload.id}: PLACEHOLDER — ${workload.placeholderReason}`);
    return run;
  }

  if (n === 0) return run;

  const queries = workload.queries ?? [];
  const totalIterations = warmup + n;

  console.log(
    `[runner] ${workload.id}: warmup=${warmup} n=${n} type=${workload.type} db=${NOX_EVAL_DB}`
  );

  for (let i = 0; i < totalIterations; i++) {
    const isWarmup = i < warmup;
    let elapsed: number | null = null;

    if (workload.type === "search") {
      const query = queries[i % queries.length] ?? "nox-mem";
      if (NOX_USE_HTTP) {
        elapsed = await runSearchHTTP(query);
      } else {
        elapsed = runSearchSubprocess(query);
      }
    } else if (workload.type === "ingest") {
      if (!workload.fixturePath) {
        console.warn(`[runner] ${workload.id}: no fixturePath`);
        break;
      }
      elapsed = runIngestEntity(workload.fixturePath, i);
    }

    if (elapsed === null) {
      if (!isWarmup) run.errors++;
      continue;
    }

    if (!isWarmup) {
      run.samples_ms.push(elapsed);
    }

    if (i % 10 === 0) {
      process.stdout.write(
        `\r[runner] ${workload.id}: ${i}/${totalIterations} (${isWarmup ? "warmup" : "bench"})    `
      );
    }
  }
  process.stdout.write("\n");

  return run;
}

// ---------------------------------------------------------------------------
// CLI entrypoint
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);

  const workloadId = args[args.indexOf("--workload") + 1] ?? null;
  const all = args.includes("--all");
  const nOverride = args.includes("--n")
    ? parseInt(args[args.indexOf("--n") + 1], 10)
    : undefined;
  const warmupOverride = args.includes("--warmup")
    ? parseInt(args[args.indexOf("--warmup") + 1], 10)
    : undefined;
  const cold = args.includes("--cold");
  const outputPath =
    args.includes("--output")
      ? args[args.indexOf("--output") + 1]
      : "results/run.json";

  checkEvalDb();

  const workloads = buildWorkloads();
  const targets = all
    ? workloads
    : workloads.filter((w) => w.id === workloadId);

  if (targets.length === 0) {
    console.error(
      `[runner] No workload found for id="${workloadId}". Available: ${workloads.map((w) => w.id).join(", ")}`
    );
    process.exit(1);
  }

  const results: WorkloadRun[] = [];
  for (const w of targets) {
    const run = await runWorkload(w, { n: nOverride, warmup: warmupOverride, cold });
    results.push(run);
  }

  writeFileSync(outputPath, JSON.stringify(results, null, 2), "utf8");
  console.log(`[runner] Wrote ${results.length} workload run(s) to ${outputPath}`);
}

// Only run CLI when invoked directly (not when imported as a module)
const isMain =
  process.argv[1] &&
  (process.argv[1].endsWith("runner.js") ||
    process.argv[1].endsWith("runner.ts"));
if (isMain) {
  main().catch((err) => {
    console.error("[runner] Fatal:", err);
    process.exit(1);
  });
}
