/**
 * generate-comparison.ts — render benchmark/COMPARISON.md from template + per-tool results.
 *
 * Usage:
 *   GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts [--dry-run] [--out-dir <path>]
 *
 * Inputs:
 *   - benchmark/COMPARISON.md.template
 *   - benchmark/LOCOMO.md.template
 *   - benchmark/LONGMEMEVAL.md.template
 *   - benchmark/LATENCY.md.template
 *   - benchmark/competitor-configs.json
 *   - benchmark/results/<competitor>/{locomo,longmemeval,latency}.json
 *
 * Outputs (only with GATE_VERIFIED=1):
 *   - benchmark/COMPARISON.md
 *   - benchmark/LOCOMO.md
 *   - benchmark/LONGMEMEVAL.md
 *   - benchmark/LATENCY.md
 *
 * Without GATE_VERIFIED=1: prints a gate-status summary and exits 1.
 *
 * The gate is intentionally a human-set env flag, NOT computed automatically.
 * See benchmark/README.md §"Publication gate" for the rationale.
 */

import { execFile } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);

const TEMPLATES = {
  comparison: resolve(HERE, "COMPARISON.md.template"),
  locomo: resolve(HERE, "LOCOMO.md.template"),
  longmemeval: resolve(HERE, "LONGMEMEVAL.md.template"),
  latency: resolve(HERE, "LATENCY.md.template"),
};
const OUTPUTS = {
  comparison: resolve(HERE, "COMPARISON.md"),
  locomo: resolve(HERE, "LOCOMO.md"),
  longmemeval: resolve(HERE, "LONGMEMEVAL.md"),
  latency: resolve(HERE, "LATENCY.md"),
};
const RESULTS_DIR = resolve(HERE, "results");
const CONFIGS_PATH = resolve(HERE, "competitor-configs.json");

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

type Dataset = "locomo" | "longmemeval" | "latency";

interface CompetitorConfig {
  name: string;
  display_name: string;
  type: "self" | "competitor" | "baseline";
  blockers: string[];
}

interface ConfigsFile {
  competitors: CompetitorConfig[];
}

interface ResultsFile {
  competitor: string;
  dataset: Dataset;
  mode: "dry-run" | "live";
  timestamp_iso: string;
  harness_sha: string;
  competitor_version: string;
  records: unknown[];
  meta: { n: number; seed: number; notes: string[] };
}

interface GateInputs {
  competitors: string[];
  haveLocomo: Record<string, boolean>;
  haveLongMemEval: Record<string, boolean>;
  haveLatency: Record<string, boolean>;
  liveResults: Record<string, Record<Dataset, boolean>>;
}

// ------------------------------------------------------------------
// CLI
// ------------------------------------------------------------------

interface Args {
  dryRun: boolean;
  outDir?: string;
}

function parseArgs(argv: string[]): Args {
  const args: Args = { dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case "--dry-run": args.dryRun = true; break;
      case "--out-dir": args.outDir = argv[++i]; break;
      case "--help":
      case "-h":
        console.log("Usage: GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts [--dry-run]");
        process.exit(0);
    }
  }
  return args;
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function loadConfigs(): ConfigsFile {
  return JSON.parse(readFileSync(CONFIGS_PATH, "utf-8")) as ConfigsFile;
}

function tryLoadResults(competitor: string, dataset: Dataset): ResultsFile | null {
  const path = resolve(RESULTS_DIR, competitor, `${dataset}.json`);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf-8")) as ResultsFile;
  } catch (e) {
    console.warn(`warn: failed to parse ${path}: ${(e as Error).message}`);
    return null;
  }
}

async function gitShortSha(): Promise<string> {
  return new Promise<string>((resolveP) => {
    execFile("git", ["rev-parse", "--short", "HEAD"], (err, stdout) => {
      if (err) resolveP("UNKNOWN");
      else resolveP(stdout.trim());
    });
  });
}

function gateStatus(configs: ConfigsFile): GateInputs {
  const competitors = configs.competitors.map(c => c.name);
  const haveLocomo: Record<string, boolean> = {};
  const haveLongMemEval: Record<string, boolean> = {};
  const haveLatency: Record<string, boolean> = {};
  const liveResults: Record<string, Record<Dataset, boolean>> = {};
  for (const name of competitors) {
    const lo = tryLoadResults(name, "locomo");
    const lme = tryLoadResults(name, "longmemeval");
    const lat = tryLoadResults(name, "latency");
    haveLocomo[name] = !!lo;
    haveLongMemEval[name] = !!lme;
    haveLatency[name] = !!lat;
    liveResults[name] = {
      locomo: !!lo && lo.mode === "live",
      longmemeval: !!lme && lme.mode === "live",
      latency: !!lat && lat.mode === "live",
    };
  }
  return { competitors, haveLocomo, haveLongMemEval, haveLatency, liveResults };
}

function printGateStatus(gate: GateInputs): void {
  console.log("Gate status — per competitor / per dataset");
  console.log("──────────────────────────────────────────────────────────────────");
  const header = "competitor".padEnd(20) + "  locomo  longmemeval  latency  (live?)";
  console.log(header);
  console.log("─".repeat(header.length));
  for (const name of gate.competitors) {
    const lo = gate.haveLocomo[name] ? (gate.liveResults[name].locomo ? "LIVE" : "dry ") : "  —  ";
    const lme = gate.haveLongMemEval[name] ? (gate.liveResults[name].longmemeval ? "LIVE" : "dry ") : "  —  ";
    const lat = gate.haveLatency[name] ? (gate.liveResults[name].latency ? "LIVE" : "dry ") : "  —  ";
    console.log(
      `${name.padEnd(20)}  ${lo.padEnd(7)} ${lme.padEnd(12)} ${lat.padEnd(8)}`
    );
  }
  console.log("──────────────────────────────────────────────────────────────────");
  const totalLive = Object.values(gate.liveResults)
    .flatMap(d => Object.values(d))
    .filter(Boolean).length;
  const totalCells = gate.competitors.length * 3;
  console.log(`Live cells: ${totalLive} / ${totalCells}.`);
  if (totalLive === 0) {
    console.log("All results are dry-run stubs. Comparison would be empty.");
  } else if (totalLive < totalCells) {
    console.log("Partial coverage. Missing cells render as '—' in the comparison.");
  } else {
    console.log("Full coverage. Comparison is publishable (subject to numeric gate).");
  }
}

// ------------------------------------------------------------------
// Placeholder expansion
// ------------------------------------------------------------------

function fmtNum(v: number | null | undefined, suffix = ""): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Math.abs(v) < 1) return v.toFixed(3) + suffix;
  if (Math.abs(v) < 100) return v.toFixed(1) + suffix;
  return Math.round(v).toString() + suffix;
}

interface ComputedMetrics {
  locomo?: {
    overall: number | null;
    perCategory: Record<string, number | null>;
    stddev: number | null;
    runs: number;
  };
  longmemeval?: {
    overall: number | null;
    perSubtask: Record<string, number | null>;
    stddev: number | null;
    runs: number;
  };
  latency?: {
    perWorkload: Record<string, { p50: number | null; p95: number | null; p99: number | null; runs: number }>;
  };
}

function computeMetrics(name: string): ComputedMetrics {
  const out: ComputedMetrics = {};
  const lo = tryLoadResults(name, "locomo");
  if (lo) {
    // Real scoring lives in eval/locomo/score.ts; this is a placeholder
    // that returns null for stubs.
    out.locomo = {
      overall: null,
      perCategory: {
        "single-hop": null,
        "multi-hop": null,
        "temporal": null,
        "open-domain": null,
        "adversarial": null,
      },
      stddev: null,
      runs: lo.mode === "live" ? 3 : 0,
    };
  }
  const lme = tryLoadResults(name, "longmemeval");
  if (lme) {
    out.longmemeval = {
      overall: null,
      perSubtask: {
        "single-session": null,
        "multi-session": null,
        "knowledge-update": null,
        "temporal": null,
      },
      stddev: null,
      runs: lme.mode === "live" ? 3 : 0,
    };
  }
  const lat = tryLoadResults(name, "latency");
  if (lat) {
    const workloads = [
      "search.short",
      "search.medium",
      "search.long",
      "search.kg-heavy",
      "ingest.entity-file",
      "ingest.chunk-batch",
    ];
    out.latency = { perWorkload: {} };
    for (const w of workloads) {
      out.latency.perWorkload[w] = { p50: null, p95: null, p99: null, runs: lat.mode === "live" ? 3 : 0 };
    }
  }
  return out;
}

function placeholderMap(
  configs: ConfigsFile,
  metrics: Record<string, ComputedMetrics>,
  harnessSha: string,
): Record<string, string> {
  const runDate = new Date().toISOString().slice(0, 10);
  const map: Record<string, string> = {
    RUN_DATE: runDate,
    HARNESS_SHA: harnessSha,
    HEADLINE_NUMBER: "(headline pending live data)",
    HEADLINE_CAPTION: "(caption pending live data)",
    HERO_PARAGRAPH: "(hero paragraph pending live data — see README §Publication gate)",
    LOCOMO_REVISION: "(pin via eval/locomo)",
    LONGMEMEVAL_REVISION: "(pin via eval/longmemeval)",
    LOCOMO_N_PER_CATEGORY: "n/a",
    LOCOMO_N_TOTAL: "n/a",
    LONGMEMEVAL_N: "n/a",
    LONGMEMEVAL_JUDGE_AGREEMENT: "(pending)",
    LONGMEMEVAL_JUDGE_BUDGET: "(pending)",
    LONGMEMEVAL_HUMAN_SPOT_N: "(pending)",
    LOCOMO_COMMENTARY: "",
    LONGMEMEVAL_COMMENTARY: "",
    LATENCY_COMMENTARY: "",
    LATENCY_HARDWARE: "(VPS hardware specs pending)",
    LATENCY_OS_NODE: "(OS / Node version pending)",
    ZEP_VERSION: "(pending)",
    CAVEATS_EXTRA: "",
  };

  // Per-competitor identifier prefix mapping
  const idMap: Record<string, string> = {
    "nox-mem": "NOXMEM",
    agentmemory: "AGENTMEMORY",
    memanto: "MEMANTO",
    mem0: "MEM0",
    letta: "LETTA",
    zep: "ZEP",
    memorymd: "MEMORYMD",
  };

  for (const c of configs.competitors) {
    const prefix = idMap[c.name];
    if (!prefix) continue;
    const m = metrics[c.name] ?? {};

    // LoCoMo
    const lo = m.locomo;
    map[`${prefix}_LOCOMO_R5`] = fmtNum(lo?.overall ?? null);
    map[`${prefix}_LOCOMO_OVERALL`] = fmtNum(lo?.overall ?? null);
    map[`${prefix}_LOCOMO_STDDEV`] = fmtNum(lo?.stddev ?? null);
    map[`${prefix}_LOCOMO_RUNS`] = String(lo?.runs ?? 0);
    map[`${prefix}_LOCOMO_C1`] = fmtNum(lo?.perCategory["single-hop"] ?? null);
    map[`${prefix}_LOCOMO_C2`] = fmtNum(lo?.perCategory["multi-hop"] ?? null);
    map[`${prefix}_LOCOMO_C3`] = fmtNum(lo?.perCategory["temporal"] ?? null);
    map[`${prefix}_LOCOMO_C4`] = fmtNum(lo?.perCategory["open-domain"] ?? null);
    map[`${prefix}_LOCOMO_C5`] = fmtNum(lo?.perCategory["adversarial"] ?? null);
    map[`${prefix}_LOCOMO_NOTES`] = "(notes pending)";
    map[`${prefix}_LOCOMO_INDEX`] = "(see competitor-configs.json)";
    map[`${prefix}_LOCOMO_RETRIEVE`] = "(see competitor-configs.json)";

    // LongMemEval
    const lme = m.longmemeval;
    map[`${prefix}_LONGMEMEVAL_ACC`] = fmtNum(lme?.overall ?? null);
    map[`${prefix}_LME_OVERALL`] = fmtNum(lme?.overall ?? null);
    map[`${prefix}_LME_STDDEV`] = fmtNum(lme?.stddev ?? null);
    map[`${prefix}_LME_RUNS`] = String(lme?.runs ?? 0);
    map[`${prefix}_LME_S1`] = fmtNum(lme?.perSubtask["single-session"] ?? null);
    map[`${prefix}_LME_S2`] = fmtNum(lme?.perSubtask["multi-session"] ?? null);
    map[`${prefix}_LME_S3`] = fmtNum(lme?.perSubtask["knowledge-update"] ?? null);
    map[`${prefix}_LME_S4`] = fmtNum(lme?.perSubtask["temporal"] ?? null);
    map[`${prefix}_LME_NOTES`] = "(notes pending)";

    // Latency — by-workload
    const lat = m.latency;
    const workloadKey: Record<string, string> = {
      "search.short": "SHORT",
      "search.medium": "MED",
      "search.long": "LONG",
      "search.kg-heavy": "KG",
      "ingest.entity-file": "INGEST",
      "ingest.chunk-batch": "BATCH",
    };
    for (const [wl, suffix] of Object.entries(workloadKey)) {
      const w = lat?.perWorkload[wl];
      map[`${prefix}_LAT_${suffix}_P50`] = fmtNum(w?.p50 ?? null);
      map[`${prefix}_LAT_${suffix}_P95`] = fmtNum(w?.p95 ?? null);
      map[`${prefix}_LAT_${suffix}_P99`] = fmtNum(w?.p99 ?? null);
      map[`${prefix}_LAT_${suffix}_RUNS`] = String(w?.runs ?? 0);
    }
    map[`${prefix}_P95_MS`] = map[`${prefix}_LAT_MED_P95`];

    // Classification / cost
    map[`${prefix}_SELFHOST`] = "(see competitor-configs.json)";
    map[`${prefix}_COST`] = "(pending)";
    map[`${prefix}_API_COST`] = "(pending)";
    map[`${prefix}_SUB`] = "(pending)";
    map[`${prefix}_INFRA_COST`] = "(pending)";
  }

  // Memanto-specific extras used in template
  map["MEMANTO_SUB"] = map["MEMANTO_SUB"] ?? "(pending)";

  return map;
}

function fillTemplate(template: string, map: Record<string, string>): string {
  return template.replace(/\{\{([A-Z0-9_]+)\}\}/g, (m, key) => {
    if (key in map) return map[key];
    return `(MISSING: ${key})`;
  });
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const configs = loadConfigs();
  const gate = gateStatus(configs);
  printGateStatus(gate);

  // -- Gate enforcement --
  if (process.env.GATE_VERIFIED !== "1") {
    console.log("");
    console.log("GATE_VERIFIED is not set to '1'.");
    console.log("This script refuses to write COMPARISON.md without explicit human gate verification.");
    console.log("See benchmark/README.md §'Publication gate' for the criteria.");
    console.log("");
    console.log("To proceed, run:  GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts");
    process.exit(1);
  }

  // Even with GATE_VERIFIED, we want a *Lab finding*-style block if nothing is live.
  const anyLive = Object.values(gate.liveResults).some(d =>
    Object.values(d).some(Boolean));
  if (!anyLive) {
    console.error("");
    console.error("error: GATE_VERIFIED=1 set, but no LIVE results are present in benchmark/results/.");
    console.error("       Publishing a comparison built entirely from dry-run stubs is not allowed.");
    console.error("       Run benchmark/collect-competitor-data.ts with --no-dry-run on a VPS.");
    process.exit(4);
  }

  const harnessSha = await gitShortSha();
  const metrics: Record<string, ComputedMetrics> = {};
  for (const c of configs.competitors) {
    metrics[c.name] = computeMetrics(c.name);
  }
  const map = placeholderMap(configs, metrics, harnessSha);

  const renderTo = (templatePath: string, outPath: string): void => {
    const tpl = readFileSync(templatePath, "utf-8");
    const filled = fillTemplate(tpl, map);
    if (args.dryRun) {
      console.log(`[--dry-run] would write ${outPath} (${filled.length} bytes)`);
      return;
    }
    const dir = dirname(outPath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(outPath, filled);
    console.log(`OK  wrote ${outPath} (${filled.length} bytes)`);
  };

  renderTo(TEMPLATES.comparison, OUTPUTS.comparison);
  renderTo(TEMPLATES.locomo, OUTPUTS.locomo);
  renderTo(TEMPLATES.longmemeval, OUTPUTS.longmemeval);
  renderTo(TEMPLATES.latency, OUTPUTS.latency);
}

main().catch((err) => {
  console.error("generate-comparison: fatal:", err);
  process.exit(99);
});
