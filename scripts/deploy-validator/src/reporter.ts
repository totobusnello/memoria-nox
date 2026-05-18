/**
 * reporter.ts — T5: Validation results reporter
 *
 * Formats results as markdown table + JSON.
 * Writes to validation/deploy-report-YYYY-MM-DD.{md,json}
 */

import * as fs from "fs";
import * as path from "path";
import type { BashSyntaxResult } from "./validators/bash-syntax.js";
import type { RsyncResult } from "./validators/rsync.js";
import type { MigrationSuiteResult } from "./validators/sqlite-migration.js";
import type { PathValidationResult } from "./validators/path-validator.js";
import type { UrlValidationResult } from "./validators/url-validator.js";
import type { SmokeResult } from "./smoke-runner.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AnyResult =
  | BashSyntaxResult
  | RsyncResult
  | MigrationSuiteResult
  | PathValidationResult
  | UrlValidationResult
  | SmokeResult;

export interface ReportEntry {
  category: string;
  label: string;
  status: "ok" | "warning" | "fail" | "vps-only" | "skip";
  detail: string;
  durationMs: number;
}

export interface ValidationReport {
  generatedAt: string;
  guideFile: string;
  summary: {
    total: number;
    pass: number;
    fail: number;
    warning: number;
    vpsOnly: number;
    skip: number;
  };
  overallPassed: boolean;
  entries: ReportEntry[];
  rawResults: unknown[];
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildReport(
  guideFile: string,
  results: AnyResult[]
): ValidationReport {
  const entries: ReportEntry[] = [];

  for (const r of results) {
    entries.push(...resultToEntries(r));
  }

  const summary = {
    total: entries.length,
    pass: entries.filter((e) => e.status === "ok").length,
    fail: entries.filter((e) => e.status === "fail").length,
    warning: entries.filter((e) => e.status === "warning").length,
    vpsOnly: entries.filter((e) => e.status === "vps-only").length,
    skip: entries.filter((e) => e.status === "skip").length,
  };

  return {
    generatedAt: new Date().toISOString(),
    guideFile,
    summary,
    overallPassed: summary.fail === 0,
    entries,
    rawResults: results,
  };
}

function resultToEntries(r: AnyResult): ReportEntry[] {
  switch (r.type) {
    case "bash-syntax":
      return [
        {
          category: "bash-syntax",
          label: `L${r.block.block.lineNumber}: ${r.block.block.contextHeading.slice(0, 50)}`,
          status: r.passed ? "ok" : "fail",
          detail: r.passed
            ? "Syntax OK"
            : `bash -n failed: ${r.errorOutput.slice(0, 200)}`,
          durationMs: r.durationMs,
        },
      ];

    case "rsync":
      return [
        {
          category: "rsync",
          label: r.originalLine.slice(0, 60),
          status: r.passed ? "ok" : "fail",
          detail: r.passed
            ? `dry-run OK${r.warnings.length > 0 ? ` (warnings: ${r.warnings.join(", ")})` : ""}`
            : `rsync failed: ${r.errorOutput.slice(0, 200)}`,
          durationMs: r.durationMs,
        },
      ];

    case "sqlite-migration-suite":
      return r.migrations.map((m) => ({
        category: "sqlite-migration",
        label: m.migrationFile,
        status: m.passed ? "ok" : "fail",
        detail: m.passed
          ? `user_version=${m.actualVersion}, tables created: ${m.tablesCreated.join(", ") || "none"}`
          : m.errorMessage ?? "unknown error",
        durationMs: m.durationMs,
      }));

    case "path-validator": {
      const criticalIssues = r.issues.filter(
        (i) => i.kind === "double-slash" || i.kind === "undefined-var"
      );
      const warnIssues = r.issues.filter(
        (i) => i.kind === "worktree-path-leaked"
      );
      const status =
        criticalIssues.length > 0
          ? "fail"
          : warnIssues.length > 0
          ? "warning"
          : "ok";
      return [
        {
          category: "path-validator",
          label: `L${r.block.block.lineNumber}: ${r.block.block.contextHeading.slice(0, 40)}`,
          status,
          detail:
            r.issues.length === 0
              ? "No path issues"
              : r.issues
                  .map((i) => `[${i.kind}] ${i.message.slice(0, 100)}`)
                  .join("; "),
          durationMs: r.durationMs,
        },
      ];
    }

    case "url-validator": {
      const fatalIssues = r.issues.filter(
        (i) => i.kind === "parse-error" || i.kind === "wrong-port"
      );
      const warnIssues = r.issues.filter((i) => i.kind !== "parse-error" && i.kind !== "wrong-port");
      const status = fatalIssues.length > 0 ? "fail" : warnIssues.length > 0 ? "warning" : "ok";
      return [
        {
          category: "url-validator",
          label: `L${r.block.block.lineNumber}: ${r.validUrls[0]?.slice(0, 50) ?? "no urls"}`,
          status,
          detail:
            r.issues.length === 0
              ? `${r.validUrls.length} URL(s) valid`
              : r.issues.map((i) => `[${i.kind}] ${i.message.slice(0, 100)}`).join("; "),
          durationMs: r.durationMs,
        },
      ];
    }

    case "smoke":
      return [
        {
          category: "smoke",
          label: r.label.slice(0, 60),
          status:
            r.status === "pass"
              ? "ok"
              : r.status === "fail"
              ? "fail"
              : r.status === "vps-only" || r.status === "no-local-api"
              ? "vps-only"
              : "skip",
          detail:
            r.status === "vps-only"
              ? "VPS-only — skipped in local/CI"
              : r.status === "no-local-api"
              ? "Local nox-mem API not running — skipped"
              : r.status === "pass"
              ? `HTTP OK: ${r.responseSnippet?.slice(0, 80) ?? ""}`
              : `FAIL: ${r.errorMessage ?? "curl non-zero exit"}`,
          durationMs: r.durationMs,
        },
      ];

    default: {
      const _exhaustive: never = r;
      return [];
    }
  }
}

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

const STATUS_ICONS: Record<string, string> = {
  ok: "ok",
  fail: "FAIL",
  warning: "WARN",
  "vps-only": "vps-only",
  skip: "skip",
};

export function formatMarkdown(report: ValidationReport): string {
  const lines: string[] = [
    `# Deploy Validator Report — ${report.generatedAt.slice(0, 10)}`,
    "",
    `**Guide:** \`${report.guideFile}\``,
    `**Generated:** ${report.generatedAt}`,
    `**Overall:** ${report.overallPassed ? "PASSED" : "FAILED"}`,
    "",
    "## Summary",
    "",
    `| Metric | Count |`,
    `|--------|-------|`,
    `| Total checks | ${report.summary.total} |`,
    `| Pass | ${report.summary.pass} |`,
    `| Fail | ${report.summary.fail} |`,
    `| Warning | ${report.summary.warning} |`,
    `| VPS-only (skipped) | ${report.summary.vpsOnly} |`,
    `| Skip | ${report.summary.skip} |`,
    "",
    "## Results",
    "",
    "| Status | Category | Label | Detail |",
    "|--------|----------|-------|--------|",
  ];

  for (const e of report.entries) {
    const icon = STATUS_ICONS[e.status] ?? e.status;
    const label = e.label.replace(/\|/g, "\\|");
    const detail = e.detail.replace(/\|/g, "\\|").slice(0, 120);
    lines.push(`| ${icon} | ${e.category} | ${label} | ${detail} |`);
  }

  if (report.summary.fail > 0) {
    lines.push("", "## Failures", "");
    for (const e of report.entries.filter((e) => e.status === "fail")) {
      lines.push(`### ${e.category} — ${e.label}`);
      lines.push("", `> ${e.detail}`, "");
    }
  }

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// File writer
// ---------------------------------------------------------------------------

export function writeReport(
  report: ValidationReport,
  outputDir: string
): { mdPath: string; jsonPath: string } {
  const date = report.generatedAt.slice(0, 10);
  const mdPath = path.join(outputDir, `deploy-report-${date}.md`);
  const jsonPath = path.join(outputDir, `deploy-report-${date}.json`);

  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(mdPath, formatMarkdown(report), "utf8");
  fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2), "utf8");

  return { mdPath, jsonPath };
}
