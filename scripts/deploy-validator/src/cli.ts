/**
 * cli.ts — T6: Deploy validator CLI entry point
 *
 * Usage:
 *   npm run validate-deploy
 *   npm run validate-deploy -- --guide docs/DEPLOY-WAVE-B.md
 *   npm run validate-deploy -- --category rsync,sqlite3
 *   npm run validate-deploy -- --quick          # skip slow checks
 *   npm run validate-deploy -- --json           # JSON output only
 *   npm run validate-deploy -- --no-smoke       # skip smoke tests
 *
 * Exit codes: 0 = all pass, 1 = any fail
 */

import * as path from "path";
import { fileURLToPath } from "url";
import * as fs from "fs";
import { parseMarkdown } from "./parser.js";
import { categorizeBlocks } from "./categorize.js";
import { checkBashSyntax } from "./validators/bash-syntax.js";
import { validateRsync } from "./validators/rsync.js";
import {
  runMigrationSuite,
  DEFAULT_MIGRATION_CHAIN,
} from "./validators/sqlite-migration.js";
import { validatePaths } from "./validators/path-validator.js";
import { validateUrls } from "./validators/url-validator.js";
import { runSmokeTests } from "./smoke-runner.js";
import { buildReport, writeReport, formatMarkdown } from "./reporter.js";
import type { AnyResult } from "./reporter.js";
import type { CommandType } from "./categorize.js";

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const VALIDATOR_ROOT = path.resolve(SCRIPT_DIR, "..");
const REPO_ROOT = path.resolve(VALIDATOR_ROOT, "../..");
const DEFAULT_GUIDE = path.join(REPO_ROOT, "docs", "DEPLOY-WAVE-B.md");
const FIXTURES_DIR = path.join(VALIDATOR_ROOT, "fixtures");
const OUTPUT_DIR = path.join(REPO_ROOT, "validation");

// ---------------------------------------------------------------------------
// Arg parser
// ---------------------------------------------------------------------------

interface CliOptions {
  guide: string;
  categories: CommandType[] | null; // null = all
  quick: boolean;
  jsonMode: boolean;
  noSmoke: boolean;
  outputDir: string;
}

function getArgValue(args: string[], flag: string): string | undefined {
  const idx = args.indexOf(flag);
  return idx >= 0 ? args[idx + 1] : undefined;
}

function parseArgs(argv: string[]): CliOptions {
  const args = argv.slice(2);

  return {
    guide: getArgValue(args, "--guide") ?? process.env.DEPLOY_GUIDE ?? DEFAULT_GUIDE,
    categories: (() => {
      const v = getArgValue(args, "--category");
      return v ? (v.split(",") as CommandType[]) : null;
    })(),
    quick: args.includes("--quick"),
    jsonMode: args.includes("--json"),
    noSmoke: args.includes("--no-smoke"),
    outputDir: getArgValue(args, "--output") ?? OUTPUT_DIR,
  };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const opts = parseArgs(process.argv);

  if (!opts.jsonMode) {
    console.log("\n  deploy-validator — DEPLOY-WAVE-B.md local dry-run check");
    console.log("  ──────────────────────────────────────────────────────");
    console.log(`  Guide: ${opts.guide}`);
    console.log(`  Mode: ${opts.quick ? "quick" : "full"}${opts.noSmoke ? " (no smoke)" : ""}\n`);
  }

  // Verify guide exists
  if (!fs.existsSync(opts.guide)) {
    console.error(`ERROR: Guide file not found: ${opts.guide}`);
    process.exit(1);
  }

  // T1: Parse markdown
  if (!opts.jsonMode) process.stdout.write("[T1] Parsing markdown ... ");
  const blocks = parseMarkdown(opts.guide);
  const bashBlocks = blocks.filter((b) => b.language === "bash" || b.language === "sh" || b.language === "");
  const sqlBlocks = blocks.filter((b) => b.language === "sql");
  if (!opts.jsonMode)
    console.log(`done. ${blocks.length} total blocks, ${bashBlocks.length} bash, ${sqlBlocks.length} sql`);

  // T2: Categorize
  if (!opts.jsonMode) process.stdout.write("[T2] Categorizing commands ... ");
  const categorized = categorizeBlocks(blocks);
  const destructiveCount = categorized.filter((c) => c.hasDestructive).length;
  if (!opts.jsonMode)
    console.log(`done. ${categorized.length} blocks, ${destructiveCount} destructive (manual review only)`);

  const allResults: AnyResult[] = [];

  // T3a: Bash syntax
  if (!opts.quick && (!opts.categories || opts.categories.includes("other"))) {
    if (!opts.jsonMode) process.stdout.write("[T3a] bash -n syntax check ... ");
    let pass = 0, fail = 0;
    for (const cmd of categorized) {
      if (cmd.hasDestructive) continue; // skip destructive blocks entirely
      const r = checkBashSyntax(cmd);
      allResults.push(r);
      if (r.passed) pass++; else fail++;
    }
    if (!opts.jsonMode) console.log(`done. ${pass} pass, ${fail} fail`);
  }

  // T3b: rsync
  if (!opts.categories || opts.categories.includes("rsync")) {
    if (!opts.jsonMode) process.stdout.write("[T3b] rsync dry-run ... ");
    const rsyncCmds = categorized.filter((c) => c.types.includes("rsync"));
    let pass = 0, fail = 0;
    for (const cmd of rsyncCmds) {
      const results = await validateRsync(cmd);
      allResults.push(...results);
      pass += results.filter((r) => r.passed).length;
      fail += results.filter((r) => !r.passed).length;
    }
    if (!opts.jsonMode) console.log(`done. ${pass} pass, ${fail} fail`);
  }

  // T3c: SQLite migrations
  if (!opts.categories || opts.categories.includes("sqlite3")) {
    if (!opts.jsonMode) process.stdout.write("[T3c] SQLite migration suite ... ");
    const migResult = runMigrationSuite(FIXTURES_DIR, DEFAULT_MIGRATION_CHAIN);
    allResults.push(migResult);
    if (!opts.jsonMode)
      console.log(
        `done. final version=${migResult.finalVersion} (${migResult.passed ? "PASS" : "FAIL"})`
      );
  }

  // T3d: Path validator
  if (!opts.categories || opts.categories.includes("rsync") || !opts.categories) {
    if (!opts.jsonMode) process.stdout.write("[T3d] Path/arg validator ... ");
    let warn = 0, fail = 0;
    for (const cmd of categorized) {
      const r = validatePaths(cmd);
      allResults.push(r);
      if (!r.passed) fail++;
      else if (r.issues.length > 0) warn++;
    }
    if (!opts.jsonMode) console.log(`done. ${fail} fail, ${warn} warnings`);
  }

  // T3e: URL validator
  if (!opts.categories || opts.categories.includes("curl") || !opts.categories) {
    if (!opts.jsonMode) process.stdout.write("[T3e] URL validator ... ");
    const curlCmds = categorized.filter((c) => c.types.includes("curl"));
    let pass = 0, fail = 0;
    for (const cmd of curlCmds) {
      const r = validateUrls(cmd);
      allResults.push(r);
      if (r.passed) pass++; else fail++;
    }
    if (!opts.jsonMode) console.log(`done. ${pass} pass, ${fail} fail`);
  }

  // T4: Smoke tests
  if (!opts.noSmoke && !opts.quick) {
    if (!opts.jsonMode) process.stdout.write("[T4] Smoke tests ... ");
    const smokeResults = await runSmokeTests(categorized, {
      skipLocalCheck: process.env.CI === "true",
    });
    allResults.push(...smokeResults);
    const vpsOnly = smokeResults.filter((r) => r.status === "vps-only" || r.status === "no-local-api").length;
    const pass = smokeResults.filter((r) => r.status === "pass").length;
    const fail = smokeResults.filter((r) => r.status === "fail").length;
    if (!opts.jsonMode) console.log(`done. ${pass} pass, ${fail} fail, ${vpsOnly} vps-only`);
  }

  // T5: Report
  const report = buildReport(opts.guide, allResults);

  if (opts.jsonMode) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    // Print summary
    const { summary } = report;
    console.log("\n  ── Summary ──────────────────────────────────────────");
    console.log(`  ${report.overallPassed ? "PASSED" : "FAILED"}`);
    console.log(
      `  pass: ${summary.pass}  fail: ${summary.fail}  warn: ${summary.warning}  ` +
      `vps-only: ${summary.vpsOnly}  skip: ${summary.skip}`
    );

    if (summary.fail > 0) {
      console.log("\n  Failures:");
      for (const e of report.entries.filter((e) => e.status === "fail")) {
        console.log(`    FAIL [${e.category}] ${e.label}: ${e.detail.slice(0, 100)}`);
      }
    }

    if (summary.vpsOnly > 0) {
      console.log(`\n  NOTE: ${summary.vpsOnly} check(s) are VPS-only — run on production to validate.`);
    }

    // Write report files
    try {
      const { mdPath, jsonPath } = writeReport(report, opts.outputDir);
      console.log(`\n  Report: ${mdPath}`);
      console.log(`  JSON:   ${jsonPath}\n`);
    } catch (e) {
      console.log(`\n  (Could not write report files: ${(e as Error).message})\n`);
    }
  }

  process.exit(report.overallPassed ? 0 : 1);
}

main().catch((e) => {
  console.error("Fatal error:", e);
  process.exit(1);
});
