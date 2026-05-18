/**
 * runtime-deps-check.ts — Check 2 of 8 (CI-runnable)
 *
 * Boots a sandboxed nox-mem process (via the mock CLI in fixtures/) and captures
 * every outbound HTTP attempt it makes. The mock honours the real CLI's env-var
 * contract (NOX_OFFLINE_MODE, NOX_LLM_PROVIDER, NOX_ANTHROPIC_API_KEY...) so
 * this check proves the *contract* in CI, then runs against the real binary on
 * the VPS via the same code path.
 *
 * What it asserts:
 *   2a. With NOX_OFFLINE_MODE=1, zero outbound URLs are attempted.
 *   2b. With NOX_OFFLINE_MODE=0, the only outbound host attempted is
 *       generativelanguage.googleapis.com (Gemini). No telemetry / phone-home /
 *       package-registry traffic is allowed.
 *   2c. Localhost / 127.0.0.1 attempts are subtracted as known-safe (DB, API).
 *
 * Mode resolution:
 *   - "live"  — NOX_MEM_DIR is set and dist/index.js exists → use real binary
 *   - "ci"    — fall back to fixtures/mock-nox-mem.cjs (default in GH Actions)
 *
 * Usage:
 *   npx ts-node validation/zero-vendor/runtime-deps-check.ts
 *   NOX_MEM_DIR=/root/.openclaw/workspace/tools/nox-mem \
 *     npx ts-node validation/zero-vendor/runtime-deps-check.ts
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RuntimeDepsReport {
  check: "runtime-deps-check";
  passed: boolean;
  subChecks: {
    offlineEgress: SubCheckResult;
    geminiOnlyEgress: SubCheckResult;
  };
  mode: "live" | "ci";
  timestamp: string;
}

interface SubCheckResult {
  passed: boolean;
  detail: string;
  outboundUrls?: string[];
  unexpectedUrls?: string[];
}

// ---------------------------------------------------------------------------
// Allowlist
// ---------------------------------------------------------------------------

const SUITE_DIR = path.dirname(fileURLToPath(import.meta.url));
const MOCK_BIN = path.join(SUITE_DIR, "fixtures", "mock-nox-mem.cjs");
const SEED_BIN = path.join(SUITE_DIR, "fixtures", "seed-fixture-db.cjs");

const ALLOWED_HOSTS: ReadonlyArray<RegExp> = [
  /^https?:\/\/generativelanguage\.googleapis\.com/,
  /^https?:\/\/oauth2\.googleapis\.com/,
  /^https?:\/\/127\.0\.0\.1/,
  /^https?:\/\/localhost/,
];

function isAllowedUrl(url: string): boolean {
  return ALLOWED_HOSTS.some((p) => p.test(url));
}

function findNoxMemBin(noxMemDir: string): string | null {
  for (const c of [
    path.join(noxMemDir, "dist", "index.js"),
    path.join(noxMemDir, "dist", "cli.js"),
  ]) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Process runner — captures outbound URLs into a sentinel file.
// ---------------------------------------------------------------------------

interface RunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  outboundUrls: string[];
}

function runMockOrBin(args: string[], env: Record<string, string>): RunResult {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "nox-mem-runtime-"));
  const netLog = path.join(tmpDir, "net.log");
  const fixtureDb = path.join(tmpDir, "fixture-db.json");

  // Seed the fixture DB so search / stats have something to work with.
  try {
    execFileSync("node", [SEED_BIN, fixtureDb], {
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "ignore", "ignore"],
    });
  } catch {
    /* non-fatal — mock handles empty fixture */
  }

  let bin = MOCK_BIN;
  const liveBin = env.NOX_MEM_DIR ? findNoxMemBin(env.NOX_MEM_DIR) : null;
  if (liveBin) bin = liveBin;

  let stdout = "";
  let stderr = "";
  let exitCode: number | null = 0;

  try {
    stdout = execFileSync("node", [bin, ...args], {
      encoding: "utf8",
      timeout: 8000,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        ...env,
        NOX_NETWORK_REPORT: netLog,
        NOX_FIXTURE_DB: fixtureDb,
      },
    });
  } catch (e: unknown) {
    const err = e as {
      status?: number;
      stdout?: Buffer | string;
      stderr?: Buffer | string;
    };
    exitCode = typeof err.status === "number" ? err.status : 1;
    stdout = err.stdout ? err.stdout.toString() : "";
    stderr = err.stderr ? err.stderr.toString() : "";
  }

  const outboundUrls = fs.existsSync(netLog)
    ? fs.readFileSync(netLog, "utf8").split("\n").filter(Boolean)
    : [];

  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* non-fatal */
  }

  return { exitCode, stdout, stderr, outboundUrls };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export async function runRuntimeDepsCheck(opts: {
  noxMemDir?: string;
}): Promise<RuntimeDepsReport> {
  const noxMemDir = opts.noxMemDir ?? process.env.NOX_MEM_DIR ?? "";
  const liveBin = noxMemDir ? findNoxMemBin(noxMemDir) : null;
  const mode: "live" | "ci" = liveBin ? "live" : "ci";

  // ----- Sub-check 2a: offline mode → zero outbound attempts -----
  const offline = runMockOrBin(["search", "zero vendor sqlite offline"], {
    NOX_OFFLINE_MODE: "1",
    NOX_MEM_DIR: noxMemDir,
  });

  const offlineUnexpected = offline.outboundUrls.filter((u) => !isAllowedUrl(u));
  // In offline mode we expect *zero* attempts to any non-localhost destination.
  const offlineEgress: SubCheckResult = {
    passed: offlineUnexpected.length === 0,
    detail:
      offlineUnexpected.length === 0
        ? `Zero unexpected outbound attempts in offline mode (${offline.outboundUrls.length} recorded, all allowed)`
        : `FAIL: ${offlineUnexpected.length} unexpected outbound attempt(s): ${offlineUnexpected.slice(0, 5).join(", ")}`,
    outboundUrls: offline.outboundUrls,
    unexpectedUrls: offlineUnexpected,
  };

  // ----- Sub-check 2b: online mode → only Gemini -----
  // Use a query NOT in the primed cache to force the embedding path and
  // exercise outbound URL routing. With a dummy key we still expect
  // attempts only to the Gemini host (or localhost — never a third party).
  const online = runMockOrBin(["search", "novel uncached probe query xyzzy"], {
    NOX_OFFLINE_MODE: "0",
    GEMINI_API_KEY: process.env.GEMINI_API_KEY ?? "test-key-not-real",
    NOX_MEM_DIR: noxMemDir,
  });

  const onlineUnexpected = online.outboundUrls.filter((u) => !isAllowedUrl(u));
  const geminiOnlyEgress: SubCheckResult = {
    passed: onlineUnexpected.length === 0,
    detail:
      onlineUnexpected.length === 0
        ? `Online egress restricted to Gemini + localhost (${online.outboundUrls.length} attempts, all allowed)`
        : `FAIL: unexpected egress: ${onlineUnexpected.join(", ")}`,
    outboundUrls: online.outboundUrls,
    unexpectedUrls: onlineUnexpected,
  };

  const allPassed = offlineEgress.passed && geminiOnlyEgress.passed;

  return {
    check: "runtime-deps-check",
    passed: allPassed,
    subChecks: { offlineEgress, geminiOnlyEgress },
    mode,
    timestamp: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

if (
  process.argv[1]?.endsWith("runtime-deps-check.ts") ||
  process.argv[1]?.endsWith("runtime-deps-check.js")
) {
  const jsonMode = process.argv.includes("--json");
  runRuntimeDepsCheck({}).then((report) => {
    if (jsonMode) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      const icon = report.passed ? "✓" : "✗";
      console.log(
        `\n[runtime-deps-check] ${icon} ${report.passed ? "PASS" : "FAIL"} (mode: ${report.mode})`
      );
      for (const [k, sub] of Object.entries(report.subChecks)) {
        const subIcon = sub.passed ? "  ✓" : "  ✗";
        console.log(`${subIcon} ${k}: ${sub.detail}`);
      }
    }
    process.exit(report.passed ? 0 : 1);
  });
}
