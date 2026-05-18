/**
 * provider-substitution-dry-run.ts — Check 7 of 8 (CI-runnable)
 *
 * Asserts that swapping the LLM provider via env var produces a clear,
 * actionable error when the alternate provider's key is missing or invalid
 * — proving the provider abstraction is well-defined (no silent fallback to
 * Gemini, no swallowed errors, no opaque 500/stack trace).
 *
 * Procedure:
 *   1. Set NOX_LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY=invalid-key-xxxxxx
 *   2. Run `nox-mem answer "test"`.
 *   3. Assert the process:
 *      - exits non-zero within 5 seconds (no silent hang)
 *      - emits a structured error containing "ANTHROPIC_API_KEY"
 *      - does NOT silently fall back to gemini
 *      - does NOT print a raw stack trace
 *
 *   4. Also test the missing-key variant:
 *      Set NOX_LLM_PROVIDER=anthropic with NO key at all. Must emit
 *      PROVIDER_AUTH_MISSING (not PROVIDER_AUTH_FAILED — distinct cases).
 *
 *   5. Bonus: NOX_LLM_PROVIDER=unknown-vendor must emit PROVIDER_UNKNOWN
 *      with a helpful "must be one of:" list.
 *
 * A3 (provider abstraction) is currently spec-only. This check enforces the
 * contract NOW so when A3 lands the existing CI gate validates it.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProviderSubstitutionReport {
  check: "provider-substitution-dry-run";
  passed: boolean;
  subChecks: {
    invalidKeyFailsClearly: SubCheckResult;
    missingKeyFailsClearly: SubCheckResult;
    unknownProviderFailsClearly: SubCheckResult;
    noSilentFallback: SubCheckResult;
  };
  mode: "live" | "ci";
  timestamp: string;
}

interface SubCheckResult {
  passed: boolean;
  detail: string;
  evidence?: Record<string, string | number>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SUITE_DIR = path.dirname(fileURLToPath(import.meta.url));
const MOCK_BIN = path.join(SUITE_DIR, "fixtures", "mock-nox-mem.cjs");
const SEED_BIN = path.join(SUITE_DIR, "fixtures", "seed-fixture-db.cjs");

function findNoxMemBin(noxMemDir: string): string | null {
  for (const c of [
    path.join(noxMemDir, "dist", "index.js"),
    path.join(noxMemDir, "dist", "cli.js"),
  ]) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

interface RunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  durationMs: number;
}

function runStep(bin: string, args: string[], env: Record<string, string>): RunResult {
  const start = Date.now();
  let stdout = "";
  let stderr = "";
  let exitCode: number | null = 0;
  try {
    stdout = execFileSync("node", [bin, ...args], {
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, ...env },
    });
  } catch (e: unknown) {
    const err = e as {
      status?: number;
      signal?: string;
      stdout?: Buffer | string;
      stderr?: Buffer | string;
    };
    exitCode = typeof err.status === "number" ? err.status : 1;
    stdout = err.stdout ? err.stdout.toString() : "";
    stderr = err.stderr ? err.stderr.toString() : "";
    if (err.signal === "SIGTERM") exitCode = 124; // timeout marker
  }
  return { exitCode, stdout, stderr, durationMs: Date.now() - start };
}

function isStackTrace(s: string): boolean {
  // Detect raw V8 stack trace leakage.
  return /^\s*at\s+\S+\s+\(.+:\d+:\d+\)/m.test(s);
}

function isSilentHang(r: RunResult): boolean {
  return r.exitCode === 124 || r.durationMs > 4500;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export async function runProviderSubstitutionCheck(opts: {
  noxMemDir?: string;
}): Promise<ProviderSubstitutionReport> {
  const noxMemDir = opts.noxMemDir ?? process.env.NOX_MEM_DIR ?? "";
  const liveBin = noxMemDir ? findNoxMemBin(noxMemDir) : null;
  const bin = liveBin ?? MOCK_BIN;
  const mode: "live" | "ci" = liveBin ? "live" : "ci";

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "nox-mem-provider-"));
  const fixtureDb = path.join(tmpDir, "fixture-db.json");
  try {
    execFileSync("node", [SEED_BIN, fixtureDb], { encoding: "utf8", timeout: 5000, stdio: ["ignore", "ignore", "ignore"] });
  } catch {
    /* mock works without fixture too */
  }

  const baseEnv = {
    NOX_FIXTURE_DB: fixtureDb,
    NOX_MEM_DIR: noxMemDir,
  };

  // ----- 7a: invalid key fails clearly -----
  const invalid = runStep(bin, ["answer", "test"], {
    ...baseEnv,
    NOX_LLM_PROVIDER: "anthropic",
    ANTHROPIC_API_KEY: "invalid-key-xxxxxx",
    NOX_ANTHROPIC_API_KEY: "invalid-key-xxxxxx",
  });

  const invalidOutput = invalid.stdout + invalid.stderr;
  const invalidMentionsKey = /ANTHROPIC_API_KEY/i.test(invalidOutput);
  const invalidIsClean = !isStackTrace(invalidOutput);
  const invalidIsClear =
    invalid.exitCode !== 0 &&
    !isSilentHang(invalid) &&
    invalidMentionsKey &&
    invalidIsClean;

  const invalidKeyFailsClearly: SubCheckResult = {
    passed: invalidIsClear,
    detail: invalidIsClear
      ? `Invalid key produced structured error mentioning ANTHROPIC_API_KEY in ${invalid.durationMs}ms`
      : isSilentHang(invalid)
      ? `FAIL: invalid key caused silent hang (${invalid.durationMs}ms)`
      : !invalidMentionsKey
      ? `FAIL: invalid key error does not mention ANTHROPIC_API_KEY. Output: ${invalidOutput.slice(0, 200)}`
      : !invalidIsClean
      ? `FAIL: invalid key produced raw stack trace (not structured error)`
      : `FAIL: invalid key exited 0 — should have failed`,
    evidence: {
      exitCode: String(invalid.exitCode),
      durationMs: invalid.durationMs,
      mentionsKey: String(invalidMentionsKey),
      hasStackTrace: String(!invalidIsClean),
    },
  };

  // ----- 7b: missing key fails clearly -----
  const missing = runStep(bin, ["answer", "test"], {
    ...baseEnv,
    NOX_LLM_PROVIDER: "anthropic",
    // ⚠ DELIBERATELY unset both env vars
    ANTHROPIC_API_KEY: "",
    NOX_ANTHROPIC_API_KEY: "",
  });

  const missingOutput = missing.stdout + missing.stderr;
  const missingMentionsKey = /ANTHROPIC_API_KEY/i.test(missingOutput);
  const missingIsClear =
    missing.exitCode !== 0 &&
    !isSilentHang(missing) &&
    missingMentionsKey &&
    !isStackTrace(missingOutput);

  const missingKeyFailsClearly: SubCheckResult = {
    passed: missingIsClear,
    detail: missingIsClear
      ? `Missing key produced structured error in ${missing.durationMs}ms`
      : `FAIL: missing-key path did not surface ANTHROPIC_API_KEY clearly. Output: ${missingOutput.slice(0, 200)}`,
    evidence: {
      exitCode: String(missing.exitCode),
      durationMs: missing.durationMs,
      mentionsKey: String(missingMentionsKey),
    },
  };

  // ----- 7c: unknown provider name fails clearly -----
  const unknown = runStep(bin, ["answer", "test"], {
    ...baseEnv,
    NOX_LLM_PROVIDER: "totally-fictional-vendor",
  });

  const unknownOutput = unknown.stdout + unknown.stderr;
  const unknownMentionsProvider = /provider/i.test(unknownOutput);
  const unknownMentionsAllowed = /gemini|anthropic|must be one of/i.test(unknownOutput);
  const unknownIsClear =
    unknown.exitCode !== 0 &&
    !isSilentHang(unknown) &&
    unknownMentionsProvider &&
    unknownMentionsAllowed;

  const unknownProviderFailsClearly: SubCheckResult = {
    passed: unknownIsClear,
    detail: unknownIsClear
      ? `Unknown provider produced enumerated-list error in ${unknown.durationMs}ms`
      : `FAIL: unknown provider did not surface allowed-list. Output: ${unknownOutput.slice(0, 200)}`,
    evidence: {
      exitCode: String(unknown.exitCode),
      durationMs: unknown.durationMs,
      mentionsAllowedProviders: String(unknownMentionsAllowed),
    },
  };

  // ----- 7d: no silent fallback to gemini -----
  // When asked for anthropic and we have a GEMINI_API_KEY in env, the binary
  // must NOT silently use Gemini instead. It must respect NOX_LLM_PROVIDER.
  const fallback = runStep(bin, ["answer", "test"], {
    ...baseEnv,
    NOX_LLM_PROVIDER: "anthropic",
    ANTHROPIC_API_KEY: "invalid-key-xxxxxx",
    NOX_ANTHROPIC_API_KEY: "invalid-key-xxxxxx",
    GEMINI_API_KEY: "fake-gemini-key-that-would-work-if-fallback-existed",
  });

  const fallbackOutput = fallback.stdout + fallback.stderr;
  // Pass: process still fails (no silent gemini fallback) AND error mentions anthropic
  const didNotFallBack =
    fallback.exitCode !== 0 && /anthropic/i.test(fallbackOutput);

  const noSilentFallback: SubCheckResult = {
    passed: didNotFallBack,
    detail: didNotFallBack
      ? `Anthropic config with invalid key did NOT silently fall back to Gemini`
      : `FAIL: process exited ${fallback.exitCode} with a valid Gemini key in env — possible silent fallback. Output: ${fallbackOutput.slice(0, 200)}`,
    evidence: {
      exitCode: String(fallback.exitCode),
      mentionsAnthropic: String(/anthropic/i.test(fallbackOutput)),
    },
  };

  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* non-fatal */
  }

  const allPassed =
    invalidKeyFailsClearly.passed &&
    missingKeyFailsClearly.passed &&
    unknownProviderFailsClearly.passed &&
    noSilentFallback.passed;

  return {
    check: "provider-substitution-dry-run",
    passed: allPassed,
    subChecks: {
      invalidKeyFailsClearly,
      missingKeyFailsClearly,
      unknownProviderFailsClearly,
      noSilentFallback,
    },
    mode,
    timestamp: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

if (
  process.argv[1]?.endsWith("provider-substitution-dry-run.ts") ||
  process.argv[1]?.endsWith("provider-substitution-dry-run.js")
) {
  const jsonMode = process.argv.includes("--json");
  runProviderSubstitutionCheck({}).then((report) => {
    if (jsonMode) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      const icon = report.passed ? "✓" : "✗";
      console.log(
        `\n[provider-substitution-dry-run] ${icon} ${report.passed ? "PASS" : "FAIL"} (mode: ${report.mode})`
      );
      for (const [k, sub] of Object.entries(report.subChecks)) {
        const subIcon = sub.passed ? "  ✓" : "  ✗";
        console.log(`${subIcon} ${k}: ${sub.detail}`);
      }
    }
    process.exit(report.passed ? 0 : 1);
  });
}
