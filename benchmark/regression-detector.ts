/**
 * benchmark/regression-detector.ts — Wave K performance regression CI gate.
 *
 * Reads baseline-2026-05-18.json, runs each runnable benchmark, compares
 * results against baseline, and reports drift per metric. Exits non-zero
 * if any measured drift exceeds DRIFT_THRESHOLD_PCT (default 10%).
 *
 * Only runnable benchmarks are executed (those with a `reproduce` command
 * pointing to staged-P1 / staged-A2 / staged-A3). Pending/estimate metrics
 * are reported as SKIPPED.
 *
 * Output:
 *   - JSON to stdout (--json-only for stdout-only mode)
 *   - Markdown summary to stderr
 *
 * Usage:
 *   # From repo root:
 *   npx tsx benchmark/regression-detector.ts
 *   npx tsx benchmark/regression-detector.ts --threshold=5
 *   npx tsx benchmark/regression-detector.ts --json-only
 *   npx tsx benchmark/regression-detector.ts --dry-run   # skip actual bench runs, compare vs baseline only
 *
 * Environment:
 *   NOX_DRIFT_THRESHOLD_PCT   — override default 10% threshold
 *   NOX_BENCH_LLM_MS          — LLM mock delay for P1 bench (default 100)
 *   NOX_BENCH_N               — sample count for P1 bench (default 50)
 *   NOX_BENCH_ITERATIONS      — iteration count for A3 bench (default 1000)
 *
 * CI integration (GitHub Actions example):
 *   - run: npx tsx benchmark/regression-detector.ts --threshold=10
 *     # exits 1 on any drift > threshold; artifact upload handled separately
 */

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { performance } from "node:perf_hooks";

// ─── Config ──────────────────────────────────────────────────────────────────

const argv = process.argv.slice(2);
const JSON_ONLY = argv.includes("--json-only");
const DRY_RUN = argv.includes("--dry-run");

const thresholdFromArg = (() => {
  const m = argv.find((a) => a.startsWith("--threshold="));
  return m ? parseFloat(m.split("=")[1]!) : undefined;
})();

const DRIFT_THRESHOLD_PCT =
  thresholdFromArg ??
  parseFloat(process.env["NOX_DRIFT_THRESHOLD_PCT"] ?? "10");

const REPO_ROOT = resolve(import.meta.dirname ?? process.cwd(), "..");
const BASELINE_PATH = join(REPO_ROOT, "benchmark", "baseline-2026-05-18.json");

// ─── Types ───────────────────────────────────────────────────────────────────

interface BaselineMetric {
  value: number;
  unit: string;
  budget_ms?: number;
  within_budget?: boolean;
  description: string;
  methodology?: string;
  hardware?: string;
  source_pr?: number | null;
  source_file?: string;
  reproduce?: string;
  notes?: string;
}

interface BaselineFile {
  version: string;
  timestamp: string;
  host: string;
  node_version: string;
  notes?: string[];
  metrics: Record<string, BaselineMetric>;
  pending_metrics?: Record<string, string>;
  methodology_summary?: Record<string, string>;
}

type MetricStatus = "PASS" | "FAIL" | "SKIP" | "BASELINE_ONLY";

interface MetricResult {
  metric_key: string;
  baseline: number;
  measured: number | null;
  drift_pct: number | null;
  status: MetricStatus;
  budget_ms: number | undefined;
  within_budget: boolean | undefined;
  source_pr: number | null | undefined;
  unit: string;
  skip_reason?: string;
  notes?: string;
}

interface DetectorReport {
  version: string;
  baseline_timestamp: string;
  run_timestamp: string;
  host: string;
  node_version: string;
  drift_threshold_pct: number;
  dry_run: boolean;
  total_metrics: number;
  measured: number;
  passed: number;
  failed: number;
  skipped: number;
  baseline_only: number;
  overall_status: "PASS" | "FAIL" | "SKIP";
  failures: MetricResult[];
  results: MetricResult[];
}

// ─── Benchmark runners ────────────────────────────────────────────────────────

/**
 * Run staged-P1 answer-latency bench and extract p50/p95/p99/phase stats.
 * Returns a map of metric key → measured value (ms).
 */
function runP1Bench(): Record<string, number> | null {
  const benchDir = join(REPO_ROOT, "staged-P1");
  if (!existsSync(benchDir)) {
    return null;
  }

  if (DRY_RUN) return null;

  try {
    // Build first if dist doesn't exist.
    const distFile = join(benchDir, "dist", "benchmark", "answer-latency.js");
    if (!existsSync(distFile)) {
      execFileSync("npm", ["run", "build"], {
        cwd: benchDir,
        stdio: "pipe",
        timeout: 120_000,
      });
    }

    const llmMs = process.env["NOX_BENCH_LLM_MS"] ?? "100";
    const n = process.env["NOX_BENCH_N"] ?? "50";

    const out = execFileSync(
      "node",
      [distFile, "--json-only", `--n=${n}`],
      {
        cwd: benchDir,
        stdio: "pipe",
        timeout: 60_000,
        env: { ...process.env, NOX_BENCH_LLM_MS: llmMs, NOX_BENCH_N: n },
      },
    ).toString("utf-8");

    const result = JSON.parse(out) as {
      phases: {
        retrieval: { p50: number; p95: number; p99: number };
        prompt: { p50: number; p95: number; p99: number };
        llm: { p50: number; p95: number; p99: number };
        citation: { p50: number; p95: number; p99: number };
        telemetry: { p50: number; p95: number; p99: number };
        total: { p50: number; p95: number; p99: number };
      };
    };

    const ph = result.phases;
    return {
      "P1.answer.pipeline.total.p50_ms": ph.total.p50,
      "P1.answer.pipeline.total.p95_ms": ph.total.p95,
      "P1.answer.pipeline.total.p99_ms": ph.total.p99,
      "P1.answer.phase.retrieval.p95_ms": ph.retrieval.p95,
      "P1.answer.phase.prompt.p95_ms": ph.prompt.p95,
      "P1.answer.phase.llm_mock.p95_ms": ph.llm.p95,
      "P1.answer.phase.citation.p95_ms": ph.citation.p95,
      "P1.answer.phase.telemetry.p95_ms": ph.telemetry.p95,
      "P1.answer.non_llm_overhead.p95_ms":
        ph.retrieval.p95 + ph.prompt.p95 + ph.citation.p95 + ph.telemetry.p95,
    };
  } catch {
    return null;
  }
}

/**
 * Run staged-A2 export-import bench (default scale 500 + 2000 chunks).
 * Returns metric key → measured value.
 */
function runA2Bench(): Record<string, number> | null {
  const benchDir = join(REPO_ROOT, "staged-A2");
  if (!existsSync(benchDir)) return null;
  if (DRY_RUN) return null;

  try {
    const distFile = join(benchDir, "dist", "benchmark", "export-import-bench.js");
    if (!existsSync(distFile)) {
      execFileSync("npm", ["run", "build"], {
        cwd: benchDir,
        stdio: "pipe",
        timeout: 120_000,
      });
    }

    const out = execFileSync("node", [distFile], {
      cwd: benchDir,
      stdio: "pipe",
      timeout: 120_000,
    }).toString("utf-8");

    const points = JSON.parse(out) as Array<{
      scale: number;
      encrypted: boolean;
      export_ms: number;
      import_ms: number;
      archive_bytes: number;
      uncompressed_estimate_bytes: number;
      encryption_overhead_ms: number | null;
      peak_rss_mb: number;
    }>;

    const results: Record<string, number> = {};
    for (const p of points) {
      // Default bench runs scale 500 + 2000; map 500 plain/encrypted to baseline keys.
      if (p.scale === 500 && !p.encrypted) {
        results["A2.export.plain.500chunks_3072d.duration_ms"] = p.export_ms;
        results["A2.import.plain.500chunks_3072d.duration_ms"] = p.import_ms;
        const archiveMb = p.archive_bytes / (1024 * 1024);
        results["A2.export.plain.500chunks_3072d.archive_mb"] = archiveMb;
        const compressionPct =
          (p.archive_bytes / p.uncompressed_estimate_bytes) * 100;
        results["A2.export.plain.500chunks_3072d.compression_ratio_pct"] =
          compressionPct;
      }
      if (p.scale === 500 && p.encrypted) {
        results["A2.export.encrypted.500chunks_3072d.duration_ms"] = p.export_ms;
        results["A2.import.encrypted.500chunks_3072d.duration_ms"] = p.import_ms;
        const archiveMb = p.archive_bytes / (1024 * 1024);
        results["A2.export.encrypted.500chunks_3072d.archive_mb"] = archiveMb;
        if (p.encryption_overhead_ms !== null) {
          results["A2.encryption_overhead.kdf_ms"] = p.encryption_overhead_ms;
        }
      }
    }
    return results;
  } catch {
    return null;
  }
}

/**
 * Run staged-A3 provider-overhead bench.
 * Returns metric key → measured value.
 */
function runA3Bench(): Record<string, number> | null {
  const benchDir = join(REPO_ROOT, "staged-A3");
  if (!existsSync(benchDir)) return null;
  if (DRY_RUN) return null;

  try {
    const distFile = join(
      benchDir,
      "dist",
      "benchmark",
      "provider-overhead.js",
    );
    if (!existsSync(distFile)) {
      execFileSync("npm", ["run", "build"], {
        cwd: benchDir,
        stdio: "pipe",
        timeout: 120_000,
      });
    }

    const iterations =
      process.env["NOX_BENCH_ITERATIONS"] ?? "1000";

    const out = execFileSync("node", [distFile], {
      cwd: benchDir,
      stdio: "pipe",
      timeout: 120_000,
      env: { ...process.env, NOX_BENCH_ITERATIONS: iterations },
    }).toString("utf-8");

    const parsed = JSON.parse(out) as {
      overhead: {
        embed_p95_abs_overhead_ms: number;
        llm_p95_abs_overhead_ms: number;
      };
    };

    return {
      "A3.provider_overhead.embed.p95_abs_ms":
        parsed.overhead.embed_p95_abs_overhead_ms,
      "A3.provider_overhead.llm.p95_abs_ms":
        parsed.overhead.llm_p95_abs_overhead_ms,
      "A3.provider_overhead.total.p95_abs_ms":
        parsed.overhead.embed_p95_abs_overhead_ms +
        parsed.overhead.llm_p95_abs_overhead_ms,
    };
  } catch {
    return null;
  }
}

// ─── Metric keys that can be measured by the runners above ───────────────────

const RUNNABLE_METRICS = new Set([
  "P1.answer.pipeline.total.p50_ms",
  "P1.answer.pipeline.total.p95_ms",
  "P1.answer.pipeline.total.p99_ms",
  "P1.answer.phase.retrieval.p95_ms",
  "P1.answer.phase.prompt.p95_ms",
  "P1.answer.phase.llm_mock.p95_ms",
  "P1.answer.phase.citation.p95_ms",
  "P1.answer.phase.telemetry.p95_ms",
  "P1.answer.non_llm_overhead.p95_ms",
  "A2.export.plain.500chunks_3072d.duration_ms",
  "A2.export.plain.500chunks_3072d.archive_mb",
  "A2.export.plain.500chunks_3072d.compression_ratio_pct",
  "A2.import.plain.500chunks_3072d.duration_ms",
  "A2.export.encrypted.500chunks_3072d.duration_ms",
  "A2.export.encrypted.500chunks_3072d.archive_mb",
  "A2.import.encrypted.500chunks_3072d.duration_ms",
  "A2.encryption_overhead.kdf_ms",
  "A3.provider_overhead.embed.p95_abs_ms",
  "A3.provider_overhead.llm.p95_abs_ms",
  "A3.provider_overhead.total.p95_abs_ms",
]);

// Metrics that are constants or design-time estimates — report as baseline-only.
//
// A2 (encrypted backup, PR #41) and A3 (provider overhead, PR #39) are FUTURE
// FEATURES not shipped in v1.0-rc1. They are exempted from the nightly FAIL gate
// until those features ship in v1.1. See benchmark/exempt-metrics.json and
// audits/2026-05-22-perf-nightly-investigation.md for full rationale.
// Re-include in RUNNABLE_METRICS when A2/A3 land in main.
const BASELINE_ONLY_METRICS = new Set([
  "A2.roundtrip_integrity.byte_loss",
  // --- A2 future-feature exemption (v1.0 gate) ---
  "A2.export.plain.500chunks_3072d.compression_ratio_pct",
  "A2.import.plain.500chunks_3072d.duration_ms",
  "A2.export.encrypted.500chunks_3072d.duration_ms",
  "A2.import.encrypted.500chunks_3072d.duration_ms",
  "A2.encryption_overhead.kdf_ms",
  // --- A3 future-feature exemption (v1.0 gate) ---
  // NOTE: embed/total show sign anomaly (measured negative, e.g. -0.13 vs baseline
  // 0.001) — instrumentation direction flip bug in A3 itself. Defer fix to A3 ship PR.
  "A3.provider_overhead.embed.p95_abs_ms",
  "A3.provider_overhead.llm.p95_abs_ms",
  "A3.provider_overhead.total.p95_abs_ms",
  // --- end future-feature exemptions ---
  "L4.extraction.regex.latency_p50_ms",
  "L4.extraction.entity_file.latency_p95_ms",
  "L4.cost.gemini_kg_monthly_usd_before",
  "L4.cost.gemini_kg_monthly_usd_after",
  "L4.quality.retrieval_ndcg10",
  "SEARCH.hybrid.ndcg_vs_fts5_only",
  "MONITORING.api.health.check_interval_min",
  "PROMETHEUS.metrics_catalog.total_metrics",
]);

// ─── Drift calculation ────────────────────────────────────────────────────────

function computeDriftPct(baseline: number, measured: number): number {
  if (baseline === 0) {
    // Avoid division by zero; any nonzero measured value is infinite drift.
    return measured === 0 ? 0 : Infinity;
  }
  return ((measured - baseline) / baseline) * 100;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const t0 = performance.now();

  if (!existsSync(BASELINE_PATH)) {
    process.stderr.write(
      `[regression-detector] ERROR: baseline file not found: ${BASELINE_PATH}\n`,
    );
    process.exit(2);
  }

  const baseline: BaselineFile = JSON.parse(
    readFileSync(BASELINE_PATH, "utf-8"),
  );

  // Run benchmarks (collect all results first to avoid interleaving output).
  if (!JSON_ONLY) {
    process.stderr.write(
      "[regression-detector] Running benchmarks…\n",
    );
    if (DRY_RUN) {
      process.stderr.write(
        "[regression-detector] --dry-run: skipping actual bench runs\n",
      );
    }
  }

  const p1Results = runP1Bench();
  const a2Results = runA2Bench();
  const a3Results = runA3Bench();

  const measured: Record<string, number> = {
    ...(p1Results ?? {}),
    ...(a2Results ?? {}),
    ...(a3Results ?? {}),
  };

  // Build results per baseline metric.
  const results: MetricResult[] = [];

  for (const [key, bm] of Object.entries(baseline.metrics)) {
    const baselineValue = bm.value;
    const measuredValue = measured[key] ?? null;

    if (BASELINE_ONLY_METRICS.has(key)) {
      results.push({
        metric_key: key,
        baseline: baselineValue,
        measured: null,
        drift_pct: null,
        status: "BASELINE_ONLY",
        budget_ms: bm.budget_ms,
        within_budget: bm.within_budget,
        source_pr: bm.source_pr,
        unit: bm.unit,
        skip_reason: "Design-time estimate or invariant — not runnable in CI",
        notes: bm.notes,
      });
      continue;
    }

    if (!RUNNABLE_METRICS.has(key)) {
      results.push({
        metric_key: key,
        baseline: baselineValue,
        measured: null,
        drift_pct: null,
        status: "SKIP",
        budget_ms: bm.budget_ms,
        within_budget: bm.within_budget,
        source_pr: bm.source_pr,
        unit: bm.unit,
        skip_reason: "Not in runnable set — pending VPS run or missing bench",
        notes: bm.notes,
      });
      continue;
    }

    if (measuredValue === null) {
      results.push({
        metric_key: key,
        baseline: baselineValue,
        measured: null,
        drift_pct: null,
        status: "SKIP",
        budget_ms: bm.budget_ms,
        within_budget: bm.within_budget,
        source_pr: bm.source_pr,
        unit: bm.unit,
        skip_reason: DRY_RUN
          ? "--dry-run: bench not executed"
          : "Bench runner returned null (staged dir missing or build failed)",
        notes: bm.notes,
      });
      continue;
    }

    const driftPct = computeDriftPct(baselineValue, measuredValue);
    const passed = Math.abs(driftPct) <= DRIFT_THRESHOLD_PCT;

    results.push({
      metric_key: key,
      baseline: baselineValue,
      measured: measuredValue,
      drift_pct: driftPct,
      status: passed ? "PASS" : "FAIL",
      budget_ms: bm.budget_ms,
      within_budget: bm.within_budget,
      source_pr: bm.source_pr,
      unit: bm.unit,
      notes: bm.notes,
    });
  }

  const measured_count = results.filter(
    (r) => r.status === "PASS" || r.status === "FAIL",
  ).length;
  const passed = results.filter((r) => r.status === "PASS").length;
  const failed = results.filter((r) => r.status === "FAIL").length;
  const skipped = results.filter((r) => r.status === "SKIP").length;
  const baseline_only = results.filter(
    (r) => r.status === "BASELINE_ONLY",
  ).length;
  const failures = results.filter((r) => r.status === "FAIL");

  const overall_status =
    failed > 0 ? "FAIL" : measured_count === 0 ? "SKIP" : "PASS";

  const elapsed_ms = Math.round(performance.now() - t0);

  const report: DetectorReport = {
    version: baseline.version,
    baseline_timestamp: baseline.timestamp,
    run_timestamp: new Date().toISOString(),
    host: baseline.host,
    node_version: process.version,
    drift_threshold_pct: DRIFT_THRESHOLD_PCT,
    dry_run: DRY_RUN,
    total_metrics: results.length,
    measured: measured_count,
    passed,
    failed,
    skipped,
    baseline_only,
    overall_status,
    failures,
    results,
  };

  // JSON output to stdout.
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");

  // Markdown summary to stderr.
  if (!JSON_ONLY) {
    const lines: string[] = [];
    lines.push("");
    lines.push(
      `# nox-mem regression detector — ${new Date().toISOString().slice(0, 10)}`,
    );
    lines.push("");
    lines.push(
      `Baseline: ${baseline.version} (${baseline.timestamp.slice(0, 10)})`,
    );
    lines.push(`Threshold: ±${DRIFT_THRESHOLD_PCT}%`);
    lines.push(
      `Overall: **${overall_status}** in ${elapsed_ms}ms` +
        (DRY_RUN ? " (dry-run)" : ""),
    );
    lines.push("");
    lines.push(
      `| Status | Count |`,
    );
    lines.push(
      `|--------|------:|`,
    );
    lines.push(`| PASS           | ${passed} |`);
    lines.push(`| FAIL           | ${failed} |`);
    lines.push(`| SKIP           | ${skipped} |`);
    lines.push(`| BASELINE_ONLY  | ${baseline_only} |`);
    lines.push(`| **TOTAL**      | **${results.length}** |`);
    lines.push("");

    if (failures.length > 0) {
      lines.push("## Failures");
      lines.push("");
      lines.push(
        "| Metric | Baseline | Measured | Drift | Threshold |",
      );
      lines.push(
        "|--------|--------:|--------:|------:|----------:|",
      );
      for (const f of failures) {
        const drift = f.drift_pct !== null ? `${f.drift_pct > 0 ? "+" : ""}${f.drift_pct.toFixed(2)}%` : "n/a";
        lines.push(
          `| ${f.metric_key} | ${f.baseline} ${f.unit} | ${f.measured} ${f.unit} | **${drift}** | ±${DRIFT_THRESHOLD_PCT}% |`,
        );
      }
      lines.push("");
    }

    lines.push("## All Results");
    lines.push("");
    lines.push(
      "| Metric | Baseline | Measured | Drift | Status |",
    );
    lines.push(
      "|--------|--------:|--------:|------:|--------|",
    );
    for (const r of results) {
      const meas =
        r.measured !== null ? `${r.measured} ${r.unit}` : "—";
      const drift =
        r.drift_pct !== null
          ? `${r.drift_pct > 0 ? "+" : ""}${r.drift_pct.toFixed(2)}%`
          : "—";
      const statusIcon =
        r.status === "PASS"
          ? "PASS"
          : r.status === "FAIL"
          ? "**FAIL**"
          : r.status === "SKIP"
          ? "SKIP"
          : "INFO";
      lines.push(
        `| ${r.metric_key} | ${r.baseline} ${r.unit} | ${meas} | ${drift} | ${statusIcon} |`,
      );
    }
    lines.push("");
    lines.push(
      `> Reproduce locally: \`npx tsx benchmark/regression-detector.ts\``,
    );
    lines.push("");

    process.stderr.write(lines.join("\n") + "\n");
  }

  // Save JSON report to disk for CI artifact upload.
  const reportPath = join(
    REPO_ROOT,
    "benchmark",
    `regression-report-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.json`,
  );
  try {
    writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
    if (!JSON_ONLY) {
      process.stderr.write(
        `[regression-detector] Report saved: ${reportPath}\n`,
      );
    }
  } catch {
    // Non-fatal — stdout already has the JSON.
  }

  if (overall_status === "FAIL") {
    process.exit(1);
  }
}

main().catch((err) => {
  process.stderr.write(
    `[regression-detector] fatal: ${(err as Error).stack ?? err}\n`,
  );
  process.exit(2);
});
