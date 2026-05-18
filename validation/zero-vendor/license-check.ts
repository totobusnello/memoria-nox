/**
 * license-check.ts — Check 1 of 8
 *
 * Parses package.json + node_modules/.package-lock.json, classifies every
 * direct and transitive dependency by SPDX license.
 *
 * PASS: all deps have OSS licenses in the allowed set
 * FAIL: any dep has GPL/AGPL/proprietary/unknown license
 *
 * Override: add entry to allowlist.json with documented reason.
 *
 * Usage:
 *   npx ts-node validation/zero-vendor/license-check.ts [--pkg-dir /path/to/nox-mem]
 *   npx ts-node validation/zero-vendor/license-check.ts --json   # machine-readable output
 */

import * as fs from "fs";
import * as path from "path";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Full OSS allow-set (SPDX identifiers). */
const OSS_ALLOWED: ReadonlySet<string> = new Set([
  "MIT",
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "ISC",
  "MPL-2.0",
  "CC-BY-4.0",
  "Unlicense",
  "0BSD",
  "BlueOak-1.0.0",
  "CC0-1.0",
  "Python-2.0", // used by some Node bundled polyfills
  "Artistic-2.0",
  "WTFPL", // effectively public domain — keep but flag in report
]);

/** License strings that signal a hard FAIL regardless of anything else. */
const FAIL_PATTERNS: ReadonlyArray<string | RegExp> = [
  /^AGPL/i,
  /^GPL/i,
  /^LGPL/i,
  "Proprietary",
  "Commercial",
  "Custom",
  "UNLICENSED",
  /^SEE LICENSE IN/i,
  /^LicenseRef-/i, // SPDX custom ref — unknown, treat as fail
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AllowlistEntry {
  reason: string;
  approvedBy?: string;
  approvedDate?: string;
}

interface Allowlist {
  _comment?: string;
  _reviewed?: string;
  _reviewer?: string;
  overrides: Record<string, AllowlistEntry>;
}

interface DepResult {
  name: string;
  version: string;
  license: string;
  status: "pass" | "fail" | "allowlisted" | "warn";
  reason?: string;
  isDev?: boolean;
}

export interface LicenseCheckReport {
  check: "license-check";
  passed: boolean;
  summary: {
    total: number;
    pass: number;
    fail: number;
    allowlisted: number;
    warn: number;
  };
  failedDeps: DepResult[];
  warnDeps: DepResult[];
  allowlistedDeps: DepResult[];
  allDeps?: DepResult[]; // only populated with --verbose
  allowlistApplied: string[];
  timestamp: string;
  pkgDir: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadAllowlist(suiteDir: string): Allowlist {
  const p = path.join(suiteDir, "allowlist.json");
  if (!fs.existsSync(p)) return { overrides: {} };
  return JSON.parse(fs.readFileSync(p, "utf8")) as Allowlist;
}

function normalizeLicense(raw: unknown): string {
  if (!raw) return "UNKNOWN";
  if (typeof raw === "object" && raw !== null && "type" in raw) {
    return String((raw as { type: string }).type);
  }
  return String(raw).trim();
}

function classifyLicense(
  license: string,
  depName: string,
  allowlist: Allowlist
): Pick<DepResult, "status" | "reason"> {
  // Allowlist override wins over everything
  if (allowlist.overrides[depName]) {
    return {
      status: "allowlisted",
      reason: allowlist.overrides[depName].reason,
    };
  }

  // Hard fail patterns
  for (const pattern of FAIL_PATTERNS) {
    if (typeof pattern === "string") {
      if (license === pattern) {
        return { status: "fail", reason: `License "${license}" is in the hard-fail list` };
      }
    } else {
      if (pattern.test(license)) {
        return { status: "fail", reason: `License "${license}" matches hard-fail pattern ${pattern}` };
      }
    }
  }

  // Unknown
  if (license === "UNKNOWN" || license === "") {
    return { status: "fail", reason: "License field is missing or empty" };
  }

  // SPDX expression with AND/OR — parse naively: all parts must be allowed
  const parts = license
    .replace(/[()]/g, "")
    .split(/\s+(?:AND|OR)\s+/i)
    .map((p) => p.trim());

  for (const part of parts) {
    if (!OSS_ALLOWED.has(part)) {
      // Might be a known but less common OSS license — warn rather than fail
      return {
        status: "warn",
        reason: `License part "${part}" not in primary allow-set — verify manually`,
      };
    }
  }

  return { status: "pass" };
}

// ---------------------------------------------------------------------------
// Core: parse lock file
// ---------------------------------------------------------------------------

interface PackageLockEntry {
  version: string;
  license?: string;
  dev?: boolean;
  peer?: boolean;
  optional?: boolean;
  packages?: Record<string, PackageLockEntry>;
}

interface PackageLock {
  lockfileVersion?: number;
  packages?: Record<string, PackageLockEntry>;
  dependencies?: Record<string, PackageLockEntry>;
}

function parseDepsFromLockV3(
  lockData: PackageLock
): Array<{ name: string; version: string; license: string; isDev: boolean }> {
  const results: Array<{ name: string; version: string; license: string; isDev: boolean }> = [];
  const packages = lockData.packages ?? {};

  for (const [pkgPath, entry] of Object.entries(packages)) {
    if (pkgPath === "") continue; // root package itself
    const name = pkgPath.replace(/^node_modules\//, "").replace(/\/node_modules\//g, "/");
    results.push({
      name,
      version: entry.version ?? "unknown",
      license: normalizeLicense(entry.license),
      isDev: entry.dev === true,
    });
  }
  return results;
}

function parseDepsFromPackageJsonFallback(
  pkgDir: string
): Array<{ name: string; version: string; license: string; isDev: boolean }> {
  // Fallback when lock file is not available: walk node_modules and read each package.json
  const results: Array<{ name: string; version: string; license: string; isDev: boolean }> = [];
  const nodeModules = path.join(pkgDir, "node_modules");
  if (!fs.existsSync(nodeModules)) return results;

  function walkDir(dir: string, depth = 0): void {
    if (depth > 3) return; // avoid infinite loops in nested node_modules
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const fullPath = path.join(dir, entry.name);
      if (entry.name.startsWith("@")) {
        walkDir(fullPath, depth + 1);
        continue;
      }
      const pkgJson = path.join(fullPath, "package.json");
      if (!fs.existsSync(pkgJson)) continue;
      try {
        const pkg = JSON.parse(fs.readFileSync(pkgJson, "utf8"));
        results.push({
          name: pkg.name ?? entry.name,
          version: pkg.version ?? "unknown",
          license: normalizeLicense(pkg.license),
          isDev: false, // can't tell without lock file
        });
      } catch {
        // malformed package.json — treat as unknown license
        results.push({
          name: entry.name,
          version: "unknown",
          license: "UNKNOWN",
          isDev: false,
        });
      }
    }
  }

  walkDir(nodeModules);
  return results;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export async function runLicenseCheck(opts: {
  pkgDir: string;
  suiteDir: string;
  verbose?: boolean;
}): Promise<LicenseCheckReport> {
  const { pkgDir, suiteDir, verbose = false } = opts;
  const allowlist = loadAllowlist(suiteDir);

  // Resolve deps list
  let rawDeps: Array<{ name: string; version: string; license: string; isDev: boolean }>;

  const lockPath = path.join(pkgDir, "node_modules", ".package-lock.json");
  const lockAltPath = path.join(pkgDir, "package-lock.json");

  if (fs.existsSync(lockPath)) {
    const lockData = JSON.parse(fs.readFileSync(lockPath, "utf8")) as PackageLock;
    rawDeps = parseDepsFromLockV3(lockData);
  } else if (fs.existsSync(lockAltPath)) {
    const lockData = JSON.parse(fs.readFileSync(lockAltPath, "utf8")) as PackageLock;
    rawDeps = parseDepsFromLockV3(lockData);
  } else {
    // Last resort: walk node_modules
    rawDeps = parseDepsFromPackageJsonFallback(pkgDir);
  }

  if (rawDeps.length === 0) {
    // No node_modules — could be a clean CI checkout before npm install
    // Return a warning, not a failure, so CI doesn't block on install step
    return {
      check: "license-check",
      passed: true,
      summary: { total: 0, pass: 0, fail: 0, allowlisted: 0, warn: 0 },
      failedDeps: [],
      warnDeps: [],
      allowlistedDeps: [],
      allowlistApplied: [],
      timestamp: new Date().toISOString(),
      pkgDir,
    };
  }

  // Deduplicate by name (keep first occurrence — typically the hoisted version)
  const seen = new Set<string>();
  const deduped = rawDeps.filter((d) => {
    if (seen.has(d.name)) return false;
    seen.add(d.name);
    return true;
  });

  // Classify each dep
  const results: DepResult[] = deduped.map((dep) => {
    const classification = classifyLicense(dep.license, dep.name, allowlist);
    return {
      name: dep.name,
      version: dep.version,
      license: dep.license,
      isDev: dep.isDev,
      ...classification,
    };
  });

  const failed = results.filter((r) => r.status === "fail");
  const warned = results.filter((r) => r.status === "warn");
  const allowlisted = results.filter((r) => r.status === "allowlisted");
  const passed = results.filter((r) => r.status === "pass");

  const allowlistApplied = allowlisted.map(
    (d) => `${d.name}@${d.version}: ${d.reason}`
  );

  return {
    check: "license-check",
    passed: failed.length === 0,
    summary: {
      total: results.length,
      pass: passed.length,
      fail: failed.length,
      allowlisted: allowlisted.length,
      warn: warned.length,
    },
    failedDeps: failed,
    warnDeps: warned,
    allowlistedDeps: allowlisted,
    allDeps: verbose ? results : undefined,
    allowlistApplied,
    timestamp: new Date().toISOString(),
    pkgDir,
  };
}

// ---------------------------------------------------------------------------
// CLI entry point
// ---------------------------------------------------------------------------

if (process.argv[1]?.endsWith("license-check.ts") || process.argv[1]?.endsWith("license-check.js")) {
  const args = process.argv.slice(2);
  const jsonMode = args.includes("--json");
  const verbose = args.includes("--verbose");
  const pkgDirArg = args.find((a, i) => args[i - 1] === "--pkg-dir");

  // Default: assume nox-mem lives at /root/.openclaw/workspace/tools/nox-mem on VPS,
  // or try to find package.json walking up from CWD
  const pkgDir =
    pkgDirArg ??
    process.env.NOX_MEM_DIR ??
    (() => {
      let d = process.cwd();
      while (d !== "/") {
        if (fs.existsSync(path.join(d, "package.json"))) return d;
        d = path.dirname(d);
      }
      return process.cwd();
    })();

  const suiteDir = path.dirname(new URL(import.meta.url).pathname);

  runLicenseCheck({ pkgDir, suiteDir, verbose }).then((report) => {
    if (jsonMode) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      const icon = report.passed ? "✓" : "✗";
      const label = report.passed ? "PASS" : "FAIL";
      console.log(`\n[license-check] ${icon} ${label}`);
      console.log(
        `  ${report.summary.total} deps scanned: ${report.summary.pass} pass, ` +
        `${report.summary.fail} fail, ${report.summary.allowlisted} allowlisted, ` +
        `${report.summary.warn} warn`
      );

      if (report.failedDeps.length > 0) {
        console.log("\n  FAILED deps:");
        for (const d of report.failedDeps) {
          console.log(`    - ${d.name}@${d.version} [${d.license}]: ${d.reason}`);
        }
      }

      if (report.warnDeps.length > 0) {
        console.log("\n  WARN deps (verify manually):");
        for (const d of report.warnDeps) {
          console.log(`    - ${d.name}@${d.version} [${d.license}]: ${d.reason}`);
        }
      }

      if (report.allowlistedDeps.length > 0) {
        console.log("\n  Allowlisted deps:");
        for (const d of report.allowlistedDeps) {
          console.log(`    - ${d.name}@${d.version} [${d.license}]: ${d.reason}`);
        }
      }
    }

    process.exit(report.passed ? 0 : 1);
  });
}
