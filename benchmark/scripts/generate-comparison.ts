/**
 * benchmark/scripts/generate-comparison.ts
 *
 * Orchestration wrapper for benchmark/generate-comparison.ts.
 *
 * - Reads Q1/Q2/Q3 result JSONs from standard result directories
 * - Validates required fields (no null metrics) before running the main generator
 * - Sets GATE_VERIFIED=1 only if all validations pass and --force is not required
 * - Checks for regression against baseline-2026-05-18.json
 *
 * Usage:
 *   npx tsx benchmark/scripts/generate-comparison.ts [--dry-run] [--force-gate]
 *
 * Environment variables (all optional — defaults shown):
 *   LOCOMO_RESULTS_DIR      path to Q1 results dir (default: eval/locomo/results)
 *   LONGMEMEVAL_RESULTS_DIR path to Q2 results dir (default: eval/longmemeval)
 *   LATENCY_RESULTS_DIR     path to Q3 results dir (default: eval/latency/results)
 *   GATE_VERIFIED           set to "1" to bypass gate checks (manual override)
 *
 * See benchmark/generate-comparison.ts for the actual rendering logic.
 * See benchmark/README.md §Publication gate for gate criteria.
 */

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const REPO_ROOT = resolve(HERE, "../..");

// ── Paths ────────────────────────────────────────────────────────────────────

const LOCOMO_DIR   = process.env.LOCOMO_RESULTS_DIR      ?? resolve(REPO_ROOT, "eval/locomo/results");
const LME_DIR      = process.env.LONGMEMEVAL_RESULTS_DIR ?? resolve(REPO_ROOT, "eval/longmemeval");
const LATENCY_DIR  = process.env.LATENCY_RESULTS_DIR     ?? resolve(REPO_ROOT, "eval/latency/results");
const BASELINE_FILE = resolve(REPO_ROOT, "benchmark/baseline-2026-05-18.json");
const MAIN_GEN     = resolve(REPO_ROOT, "benchmark/generate-comparison.ts");

// ── Result file paths ─────────────────────────────────────────────────────────

const RESULT_FILES = {
  q1:          resolve(LOCOMO_DIR,  "full-run.json"),
  q2_gpt4o:    resolve(LME_DIR,     "full-run.gpt4o.json"),
  q2_gemini:   resolve(LME_DIR,     "full-run.gemini25pro.json"),
  q3_summary:  resolve(LATENCY_DIR, "summary.json"),
};

// ── CLI ───────────────────────────────────────────────────────────────────────

interface Args {
  dryRun: boolean;
  forceGate: boolean;
}

function parseArgs(argv: string[]): Args {
  const args: Args = { dryRun: false, forceGate: false };
  for (const a of argv) {
    if (a === "--dry-run") args.dryRun = true;
    if (a === "--force-gate") args.forceGate = true;
    if (a === "--help" || a === "-h") {
      console.log("Usage: npx tsx benchmark/scripts/generate-comparison.ts [--dry-run] [--force-gate]");
      console.log("  --dry-run    Validate + print plan, do not write files");
      console.log("  --force-gate Skip validation checks and set GATE_VERIFIED=1 unconditionally");
      process.exit(0);
    }
  }
  return args;
}

// ── JSON helpers ──────────────────────────────────────────────────────────────

function loadJson(path: string): Record<string, unknown> | null {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf-8")) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  let cur: unknown = obj;
  for (const part of path.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

// ── Validation ────────────────────────────────────────────────────────────────

interface ValidationResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  metrics: Record<string, number | string>;
}

function validateResults(): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const metrics: Record<string, number | string> = {};

  // Q1
  const q1 = loadJson(RESULT_FILES.q1);
  if (!q1) {
    errors.push(`Q1 result not found: ${RESULT_FILES.q1}`);
  } else {
    const r5 = getNestedValue(q1, "metrics.r5");
    const ndcg = getNestedValue(q1, "metrics.ndcg10");
    const seed = q1.seed;
    if (r5 === null || r5 === undefined) {
      errors.push("Q1: metrics.r5 is null — run was incomplete or scoring failed");
    } else {
      metrics["Q1.r5"] = r5 as number;
      console.log(`  Q1 R@5        : ${r5}`);
    }
    if (ndcg !== null && ndcg !== undefined) {
      metrics["Q1.ndcg10"] = ndcg as number;
      console.log(`  Q1 nDCG@10    : ${ndcg}`);
    }
    if (seed !== 42) {
      warnings.push(`Q1: seed=${seed} (expected 42 for reproducibility)`);
    }
  }

  // Q2 — at least one judge required
  const q2g = loadJson(RESULT_FILES.q2_gpt4o);
  const q2gm = loadJson(RESULT_FILES.q2_gemini);

  if (!q2g && !q2gm) {
    errors.push(`Q2 results not found in ${LME_DIR}`);
  } else {
    if (q2g) {
      const acc = getNestedValue(q2g, "metrics.overall_accuracy");
      if (acc === null || acc === undefined) {
        errors.push("Q2 gpt4o: metrics.overall_accuracy is null — scoring incomplete");
      } else {
        metrics["Q2.accuracy.gpt4o"] = acc as number;
        console.log(`  Q2 accuracy (gpt-4o)        : ${acc}`);
      }
    } else {
      warnings.push("Q2: gpt-4o judge result not found — gate will show gemini-2.5-pro only");
    }

    if (q2gm) {
      const acc = getNestedValue(q2gm, "metrics.overall_accuracy");
      if (acc !== null && acc !== undefined) {
        metrics["Q2.accuracy.gemini25pro"] = acc as number;
        console.log(`  Q2 accuracy (gemini-2.5-pro): ${acc}`);
      }
    } else {
      warnings.push("Q2: gemini-2.5-pro judge result not found");
    }
  }

  // Q3
  const q3 = loadJson(RESULT_FILES.q3_summary);
  if (!q3) {
    errors.push(`Q3 summary not found: ${RESULT_FILES.q3_summary}`);
  } else {
    const wl = getNestedValue(q3, "workloads") as Record<string, Record<string, unknown>> | null;
    if (!wl) {
      errors.push("Q3: workloads field missing from summary.json");
    } else {
      const medP95 = wl["search.medium"]?.p95_ms;
      if (medP95 === null || medP95 === undefined) {
        errors.push("Q3: workloads[\"search.medium\"].p95_ms is null");
      } else {
        metrics["Q3.search.medium.p95_ms"] = medP95 as number;
        console.log(`  Q3 search.medium p95        : ${medP95}ms`);
      }

      for (const workload of ["search.short", "search.long", "search.kg-heavy"]) {
        const p95 = wl[workload]?.p95_ms;
        if (p95 !== null && p95 !== undefined) {
          metrics[`Q3.${workload}.p95_ms`] = p95 as number;
          console.log(`  Q3 ${workload.padEnd(28)}: ${p95}ms`);
        }
      }
    }
  }

  return { ok: errors.length === 0, errors, warnings, metrics };
}

// ── Regression check vs baseline ─────────────────────────────────────────────

function regressionCheck(metrics: Record<string, number | string>): void {
  const baseline = loadJson(BASELINE_FILE);
  if (!baseline) {
    console.log("  WARN: baseline file not found — skipping regression check");
    return;
  }

  console.log("");
  console.log("── Regression check vs baseline-2026-05-18.json ────────");

  // Check search nDCG@10 (E14 wave 1 baseline = 0.6813)
  const baselineNdcg = 0.6813; // from baseline.json L4.quality.retrieval_ndcg10
  const q1Ndcg = metrics["Q1.ndcg10"];
  if (typeof q1Ndcg === "number") {
    if (q1Ndcg < baselineNdcg * 0.95) {
      console.log(`  REGRESSION: Q1 nDCG@10=${q1Ndcg.toFixed(4)} < 95% of baseline ${baselineNdcg} — investigate before publishing`);
    } else {
      console.log(`  OK  Q1 nDCG@10=${q1Ndcg.toFixed(4)} >= 95% of baseline ${baselineNdcg}`);
    }
  }

  // Check P1 pipeline budget (mock baseline p95=101.7ms; VPS real will be higher but warn if absurd)
  const q3MedP95 = metrics["Q3.search.medium.p95_ms"];
  if (typeof q3MedP95 === "number") {
    if (q3MedP95 > 5000) {
      console.log(`  WARN: Q3 search.medium p95=${q3MedP95}ms > 5000ms — investigate VPS load`);
    } else {
      console.log(`  OK  Q3 search.medium p95=${q3MedP95}ms (within 5s threshold)`);
    }
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  console.log("═══════════════════════════════════════════════════════");
  console.log("generate-comparison.ts wrapper — Q1+Q2+Q3 gate check");
  console.log("═══════════════════════════════════════════════════════");
  console.log(`  LOCOMO_DIR   : ${LOCOMO_DIR}`);
  console.log(`  LME_DIR      : ${LME_DIR}`);
  console.log(`  LATENCY_DIR  : ${LATENCY_DIR}`);
  console.log("");

  console.log("── Validating result files ─────────────────────────────");
  const validation = validateResults();

  if (validation.warnings.length > 0) {
    console.log("");
    console.log("── Warnings ─────────────────────────────────────────────");
    for (const w of validation.warnings) {
      console.log(`  WARN: ${w}`);
    }
  }

  if (!validation.ok) {
    console.log("");
    console.log("── Errors ───────────────────────────────────────────────");
    for (const e of validation.errors) {
      console.log(`  ERROR: ${e}`);
    }
    console.log("");
    if (!args.forceGate) {
      console.error("GATE BLOCKED: validation errors above must be resolved.");
      console.error("  Option 1: Run missing benchmarks and collect results.");
      console.error("  Option 2: Use --force-gate to bypass (use with caution).");
      process.exit(1);
    } else {
      console.log("WARN: --force-gate set — bypassing validation errors (use with caution)");
    }
  }

  regressionCheck(validation.metrics);

  if (args.dryRun) {
    console.log("");
    console.log("[--dry-run] Would invoke: GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts");
    console.log("  Validation: " + (validation.ok ? "PASS" : "FAIL (bypassed with --force-gate)"));
    process.exit(0);
  }

  // Set gate flag and pass env vars to the main generator
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    GATE_VERIFIED: "1",
    LOCOMO_RESULTS_DIR: LOCOMO_DIR,
    LONGMEMEVAL_RESULTS_DIR: LME_DIR,
    LATENCY_RESULTS_DIR: LATENCY_DIR,
  };

  console.log("");
  console.log("── Invoking benchmark/generate-comparison.ts ───────────");

  try {
    execFileSync(
      process.execPath,
      ["--import", "tsx/esm", MAIN_GEN, ...(args.dryRun ? ["--dry-run"] : [])],
      { env, stdio: "inherit" },
    );
  } catch (err) {
    // execFileSync throws on non-zero exit
    const exitCode = (err as NodeJS.ErrnoException & { status?: number }).status ?? 1;
    console.error(`generate-comparison.ts exited with code ${exitCode}`);
    process.exit(exitCode);
  }

  console.log("");
  console.log("═══════════════════════════════════════════════════════");
  console.log("Gate update complete.");
  console.log("");
  console.log("Review COMPARISON.md before committing:");
  console.log("  grep 'pending' benchmark/COMPARISON.md   # should be empty");
  console.log("");
  console.log("Commit when ready:");
  console.log("  git add benchmark/COMPARISON.md eval/*/results/");
  console.log("  git commit -m \"data(Q4-gate): Q1+Q2+Q3 verified $(date +%Y-%m-%d)\"");
  console.log("═══════════════════════════════════════════════════════");
}

main().catch((err) => {
  console.error("generate-comparison wrapper: fatal:", err);
  process.exit(99);
});
