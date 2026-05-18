/**
 * collect-competitor-data.ts — per-tool data collection runner.
 *
 * Usage:
 *   npx tsx benchmark/collect-competitor-data.ts \
 *     --competitor <name> \
 *     --dataset <locomo|longmemeval|latency> \
 *     [--output <path>] \
 *     [--dry-run] \
 *     [--n <override>]
 *
 * Modes:
 *   --dry-run (default) : do NOT invoke competitor CLI/API. Emit a deterministic
 *                         stub JSON with synthetic per-question/per-iteration
 *                         records. Useful in local dev (no API keys, no daemons).
 *   (no --dry-run)      : LIVE mode. Refuses to run if competitor's install
 *                         doctor check fails, if required env is missing, or
 *                         if the user is not on a VPS profile (see VPS guard).
 *                         LIVE runs the actual competitor invocations.
 *
 * Output schema (per call, written to --output):
 *   {
 *     "competitor": "<name>",
 *     "dataset": "<locomo|longmemeval|latency>",
 *     "mode": "dry-run" | "live",
 *     "timestamp_iso": "<UTC ISO>",
 *     "harness_sha": "<short SHA>",
 *     "competitor_version": "<vendor-reported>",
 *     "records": [ ... ]    // dataset-specific
 *   }
 *
 * SAFETY:
 *   - Default is --dry-run. Live mode requires explicit --no-dry-run AND
 *     NOX_BENCHMARK_LIVE=1 in the environment.
 *   - We refuse to invoke MOORCHEH-style hosted endpoints unless an explicit
 *     budget env (NOX_BENCHMARK_BUDGET_USD) is set.
 *   - We never write to nox-mem.db production paths.
 */

import { execFile } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const CONFIGS_PATH = resolve(HERE, "competitor-configs.json");

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

type Dataset = "locomo" | "longmemeval" | "latency";
type Mode = "dry-run" | "live";

interface CompetitorConfig {
  name: string;
  type: "self" | "competitor" | "baseline";
  display_name: string;
  install: {
    method: string;
    steps: string[];
    requires_api_key?: string | null;
    requires_daemon?: string;
    saas_only?: boolean;
    prerequisites?: string[];
  };
  invocation: Record<Dataset, {
    ingest?: string;
    retrieve?: string;
    harness?: string;
    mode?: string;
    notes?: string;
  }>;
  self_host_classification: string;
  blockers: string[];
}

interface ConfigsFile {
  version: number;
  competitors: CompetitorConfig[];
  datasets: Dataset[];
}

interface CliArgs {
  competitor: string;
  dataset: Dataset;
  output?: string;
  dryRun: boolean;
  n?: number;
}

interface OutputRecord {
  competitor: string;
  dataset: Dataset;
  mode: Mode;
  timestamp_iso: string;
  harness_sha: string;
  competitor_version: string;
  records: unknown[];
  meta: {
    n: number;
    seed: number;
    notes: string[];
  };
}

// ------------------------------------------------------------------
// CLI parsing
// ------------------------------------------------------------------

function parseArgs(argv: string[]): CliArgs {
  const args: Partial<CliArgs> = { dryRun: true };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case "--competitor": args.competitor = argv[++i]; break;
      case "--dataset": args.dataset = argv[++i] as Dataset; break;
      case "--output": args.output = argv[++i]; break;
      case "--dry-run": args.dryRun = true; break;
      case "--no-dry-run": args.dryRun = false; break;
      case "--n": args.n = Number(argv[++i]); break;
      case "--help":
      case "-h": {
        printHelp();
        process.exit(0);
      }
    }
  }
  if (!args.competitor || !args.dataset) {
    printHelp();
    process.exit(1);
  }
  if (!["locomo", "longmemeval", "latency"].includes(args.dataset)) {
    console.error(`error: dataset must be one of locomo|longmemeval|latency, got: ${args.dataset}`);
    process.exit(1);
  }
  return args as CliArgs;
}

function printHelp(): void {
  console.log(`Usage: collect-competitor-data.ts --competitor <name> --dataset <locomo|longmemeval|latency> [--output path] [--dry-run] [--n N]

Options:
  --competitor <name>   one of: nox-mem | agentmemory | memanto | mem0 | letta | zep | memorymd
  --dataset <name>      locomo | longmemeval | latency
  --output <path>       output JSON path (default: results/<competitor>/<dataset>.json)
  --dry-run             default. Emit stub JSON without invoking competitor.
  --no-dry-run          LIVE mode. Requires NOX_BENCHMARK_LIVE=1.
  --n <N>               sample size override.

Examples:
  # Default dry-run (no API keys, no daemons needed):
  npx tsx benchmark/collect-competitor-data.ts --competitor mem0 --dataset locomo

  # Live (VPS only):
  NOX_BENCHMARK_LIVE=1 npx tsx benchmark/collect-competitor-data.ts \\
    --competitor mem0 --dataset locomo --no-dry-run
`);
}

// ------------------------------------------------------------------
// Config + helpers
// ------------------------------------------------------------------

function loadConfigs(): ConfigsFile {
  const raw = readFileSync(CONFIGS_PATH, "utf-8");
  return JSON.parse(raw) as ConfigsFile;
}

function getCompetitor(name: string): CompetitorConfig {
  const configs = loadConfigs();
  const c = configs.competitors.find(c => c.name === name);
  if (!c) {
    console.error(`error: unknown competitor '${name}'. Known: ${configs.competitors.map(x => x.name).join(", ")}`);
    process.exit(1);
  }
  return c;
}

async function gitShortSha(): Promise<string> {
  return new Promise<string>((resolveP) => {
    execFile("git", ["rev-parse", "--short", "HEAD"], (err, stdout) => {
      if (err) resolveP("UNKNOWN");
      else resolveP(stdout.trim());
    });
  });
}

function defaultOutputPath(competitor: string, dataset: Dataset): string {
  return resolve(HERE, "results", competitor, `${dataset}.json`);
}

function ensureDir(path: string): void {
  const dir = dirname(path);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

// ------------------------------------------------------------------
// Dry-run record generators (deterministic stubs)
// ------------------------------------------------------------------

function dryRunLocomoRecords(competitor: string, n: number): unknown[] {
  const categories = ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"];
  const recs: unknown[] = [];
  for (let i = 0; i < n; i++) {
    const category = categories[i % categories.length];
    recs.push({
      question_id: `dry-${competitor}-${i}`,
      category,
      gold_chunk_ids: [`gold-${i}-a`, `gold-${i}-b`],
      retrieved_chunk_ids: [`stub-${i}-1`, `stub-${i}-2`, `stub-${i}-3`, `stub-${i}-4`, `stub-${i}-5`],
      retrieved_scores: [0.0, 0.0, 0.0, 0.0, 0.0],
      retrieval_ms: -1,
      hit_at_5: null,
      stub: true,
    });
  }
  return recs;
}

function dryRunLongMemEvalRecords(competitor: string, n: number): unknown[] {
  const subtasks = ["single-session", "multi-session", "knowledge-update", "temporal"];
  const recs: unknown[] = [];
  for (let i = 0; i < n; i++) {
    const subtask = subtasks[i % subtasks.length];
    recs.push({
      question_id: `dry-${competitor}-${i}`,
      subtask,
      gold_answer: `(stub gold answer ${i})`,
      composed_answer: `(stub composed answer ${i})`,
      judge_passes: [null, null, null],
      judge_majority: null,
      retrieval_ms: -1,
      composer_ms: -1,
      stub: true,
    });
  }
  return recs;
}

function dryRunLatencyRecords(competitor: string, n: number): unknown[] {
  const workloads = [
    "search.short",
    "search.medium",
    "search.long",
    "search.kg-heavy",
    "ingest.entity-file",
    "ingest.chunk-batch",
  ];
  const recs: unknown[] = [];
  for (const w of workloads) {
    recs.push({
      workload: w,
      n,
      iterations: Array.from({ length: n }, (_, i) => ({
        iteration: i,
        elapsed_ms: null,
        stub: true,
      })),
      stub_summary: {
        p50_ms: null,
        p95_ms: null,
        p99_ms: null,
        stub: true,
      },
    });
  }
  return recs;
}

function buildDryRunRecord(
  competitor: CompetitorConfig,
  dataset: Dataset,
  n: number,
  harnessSha: string,
): OutputRecord {
  let records: unknown[] = [];
  switch (dataset) {
    case "locomo":
      records = dryRunLocomoRecords(competitor.name, n);
      break;
    case "longmemeval":
      records = dryRunLongMemEvalRecords(competitor.name, n);
      break;
    case "latency":
      records = dryRunLatencyRecords(competitor.name, n);
      break;
  }
  const notes: string[] = [
    "DRY-RUN: no competitor invocation occurred.",
    "All numeric fields are null / -1; do not score this output.",
  ];
  if (competitor.blockers.length > 0) {
    notes.push(`blockers: ${competitor.blockers.length} (see competitor-configs.json + BLOCKED.md)`);
  }
  return {
    competitor: competitor.name,
    dataset,
    mode: "dry-run",
    timestamp_iso: new Date().toISOString(),
    harness_sha: harnessSha,
    competitor_version: "(dry-run stub)",
    records,
    meta: {
      n,
      seed: 42,
      notes,
    },
  };
}

// ------------------------------------------------------------------
// Live mode guards (refuse aggressively)
// ------------------------------------------------------------------

function liveModeGuard(competitor: CompetitorConfig): { ok: boolean; reasons: string[] } {
  const reasons: string[] = [];
  if (process.env.NOX_BENCHMARK_LIVE !== "1") {
    reasons.push("NOX_BENCHMARK_LIVE=1 not set (refuse to run live without explicit opt-in).");
  }
  if (competitor.install.requires_api_key) {
    const key = competitor.install.requires_api_key;
    if (!process.env[key]) {
      reasons.push(`required API key env not set: ${key}`);
    }
  }
  if (competitor.install.saas_only && !process.env.NOX_BENCHMARK_BUDGET_USD) {
    reasons.push("SaaS-only competitor requires NOX_BENCHMARK_BUDGET_USD env (explicit budget acknowledgement).");
  }
  if (competitor.install.requires_daemon) {
    reasons.push(`competitor requires proprietary daemon (${competitor.install.requires_daemon}); cannot run on a dev box without VPS provisioning. See BLOCKED.md.`);
  }
  for (const blocker of competitor.blockers) {
    reasons.push(`blocker: ${blocker}`);
  }
  return { ok: reasons.length === 0, reasons };
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const competitor = getCompetitor(args.competitor);
  const harnessSha = await gitShortSha();

  // Default sample sizes if --n not given
  const defaultN: Record<Dataset, number> = {
    locomo: 50,
    longmemeval: 80,
    latency: 100,
  };
  const n = args.n ?? defaultN[args.dataset];
  const outputPath = args.output ?? defaultOutputPath(competitor.name, args.dataset);

  let output: OutputRecord;
  if (args.dryRun) {
    output = buildDryRunRecord(competitor, args.dataset, n, harnessSha);
  } else {
    const guard = liveModeGuard(competitor);
    if (!guard.ok) {
      console.error("LIVE mode refused. Reasons:");
      for (const r of guard.reasons) console.error(`  - ${r}`);
      console.error("\nFall back to --dry-run, or fix the above and re-run.");
      process.exit(2);
    }
    // Live mode implementation would dispatch to per-competitor adapters here.
    // Today: we have no VPS / API access from this dev box. Stub with error.
    console.error("LIVE mode is scaffolded but not yet wired to per-competitor adapters.");
    console.error("Adapters live under benchmark/adapters/<competitor>.ts (TODO).");
    console.error("See BLOCKED.md for the full list of preconditions.");
    process.exit(3);
  }

  ensureDir(outputPath);
  writeFileSync(outputPath, JSON.stringify(output, null, 2) + "\n");
  console.log(`OK  wrote ${outputPath}  (${output.records.length} records, mode=${output.mode})`);
  if (output.meta.notes.length > 0) {
    for (const note of output.meta.notes) console.log(`     note: ${note}`);
  }
}

main().catch((err) => {
  console.error("collect-competitor-data: fatal:", err);
  process.exit(99);
});
