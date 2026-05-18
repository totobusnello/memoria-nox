/**
 * embedding-cache-replay.ts — Check 6 of 8 (CI-runnable)
 *
 * Proves that a search for a previously-embedded query returns results
 * without re-invoking the embedding function. This is the cornerstone of
 * the offline-by-default invariant: once a chunk is embedded, you should
 * never need to call Gemini again to find it.
 *
 * Procedure:
 *   1. Seed the fixture DB with 5 chunks + primed embeddings.
 *   2. Run a search against a primed query — must succeed (cache hit).
 *   3. Re-run the same search with NOX_FAIL_IF_EMBED=1. The mock CLI
 *      throws "EMBED_CALLED_UNEXPECTEDLY" if the embedding path is taken.
 *   4. Assert: exit code 0, results returned, no embed call recorded.
 *
 * The real binary on the VPS implements the same NOX_FAIL_IF_EMBED contract
 * (planned for A3 provider abstraction). For now, the mock proves the
 * contract is well-defined and the CI gate enforces it.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EmbeddingCacheReplayReport {
  check: "embedding-cache-replay";
  passed: boolean;
  subChecks: {
    primedCacheHit: SubCheckResult;
    noEmbedOnReplay: SubCheckResult;
    distinctQueryFallback: SubCheckResult;
  };
  mode: "live" | "ci";
  timestamp: string;
}

interface SubCheckResult {
  passed: boolean;
  detail: string;
  metrics?: Record<string, number | string>;
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
  outboundUrls: string[];
}

function runStep(
  bin: string,
  args: string[],
  env: Record<string, string>,
  netLog: string
): RunResult {
  let stdout = "";
  let stderr = "";
  let exitCode: number | null = 0;
  try {
    stdout = execFileSync("node", [bin, ...args], {
      encoding: "utf8",
      timeout: 6000,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, ...env, NOX_NETWORK_REPORT: netLog },
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
  return { exitCode, stdout, stderr, outboundUrls };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export async function runEmbeddingCacheReplayCheck(opts: {
  noxMemDir?: string;
}): Promise<EmbeddingCacheReplayReport> {
  const noxMemDir = opts.noxMemDir ?? process.env.NOX_MEM_DIR ?? "";
  const liveBin = noxMemDir ? findNoxMemBin(noxMemDir) : null;
  const bin = liveBin ?? MOCK_BIN;
  const mode: "live" | "ci" = liveBin ? "live" : "ci";

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "nox-mem-cache-replay-"));
  const fixtureDb = path.join(tmpDir, "fixture-db.json");
  const netLog = path.join(tmpDir, "net.log");

  // Seed fixture with 5 chunks + 4 primed queries.
  try {
    execFileSync("node", [SEED_BIN, fixtureDb], { encoding: "utf8", timeout: 5000, stdio: ["ignore", "ignore", "ignore"] });
  } catch (e: unknown) {
    return {
      check: "embedding-cache-replay",
      passed: false,
      subChecks: {
        primedCacheHit: {
          passed: false,
          detail: `Failed to seed fixture: ${(e as Error).message}`,
        },
        noEmbedOnReplay: { passed: false, detail: "skipped (seed failed)" },
        distinctQueryFallback: { passed: false, detail: "skipped (seed failed)" },
      },
      mode,
      timestamp: new Date().toISOString(),
    };
  }

  const baseEnv = {
    NOX_FIXTURE_DB: fixtureDb,
    NOX_MEM_DIR: noxMemDir,
  };

  // ----- 6a: primed query → cache hit, results returned -----
  const primedQuery = "zero vendor sqlite offline";
  const r1 = runStep(bin, ["search", primedQuery], baseEnv, netLog);

  let r1Results = 0;
  let r1CacheHit = false;
  try {
    const parsed = JSON.parse(r1.stdout.trim().split("\n").pop() || "{}");
    r1Results = Array.isArray(parsed.results) ? parsed.results.length : 0;
    r1CacheHit = !!parsed.cacheHit;
  } catch {
    /* surface in detail below */
  }

  const primedCacheHit: SubCheckResult = {
    passed: r1.exitCode === 0 && r1Results > 0 && r1CacheHit,
    detail:
      r1.exitCode === 0 && r1Results > 0 && r1CacheHit
        ? `Primed query returned ${r1Results} results with cacheHit=true`
        : `FAIL: exit=${r1.exitCode}, results=${r1Results}, cacheHit=${r1CacheHit}`,
    metrics: { results: r1Results, cacheHit: String(r1CacheHit) },
  };

  // ----- 6b: replay with NOX_FAIL_IF_EMBED=1 → must still succeed -----
  const r2 = runStep(
    bin,
    ["search", primedQuery],
    { ...baseEnv, NOX_FAIL_IF_EMBED: "1" },
    netLog
  );

  let r2Results = 0;
  try {
    const parsed = JSON.parse(r2.stdout.trim().split("\n").pop() || "{}");
    r2Results = Array.isArray(parsed.results) ? parsed.results.length : 0;
  } catch {
    /* surface below */
  }

  const embedCalled =
    r2.stdout.includes("EMBED_CALLED_UNEXPECTEDLY") ||
    r2.stderr.includes("EMBED_CALLED_UNEXPECTEDLY") ||
    r2.exitCode !== 0;

  const noEmbedOnReplay: SubCheckResult = {
    passed: !embedCalled && r2Results > 0,
    detail: !embedCalled && r2Results > 0
      ? `Replay returned ${r2Results} results without invoking the embedding function`
      : `FAIL: embed function was called (exit=${r2.exitCode}, results=${r2Results}) — cache replay broken`,
    metrics: { results: r2Results, embedCalled: String(embedCalled) },
  };

  // ----- 6c: distinct (unprimed) query falls back gracefully -----
  // If we ask for something the cache has never seen and tell the system NOT
  // to embed, it must still answer via the FTS path (graceful degradation).
  const distinctQuery = "completely unrelated query mango sunset";
  const r3 = runStep(
    bin,
    ["search", distinctQuery],
    { ...baseEnv, NOX_FAIL_IF_EMBED: "1" },
    netLog
  );

  let r3Exit = r3.exitCode;
  let r3Results = 0;
  try {
    const parsed = JSON.parse(r3.stdout.trim().split("\n").pop() || "{}");
    r3Results = Array.isArray(parsed.results) ? parsed.results.length : 0;
  } catch {
    /* surface below */
  }

  // Acceptable outcomes: process exits 0 (FTS returned 0 or N results, no
  // embedding called). Unacceptable: process crashes with EMBED_CALLED.
  const fellBack =
    r3Exit === 0 &&
    !r3.stdout.includes("EMBED_CALLED_UNEXPECTEDLY") &&
    !r3.stderr.includes("EMBED_CALLED_UNEXPECTEDLY");

  const distinctQueryFallback: SubCheckResult = {
    passed: fellBack,
    detail: fellBack
      ? `Unprimed query fell back to FTS-only without invoking embedder (results=${r3Results})`
      : `FAIL: unprimed query did not degrade gracefully (exit=${r3Exit})`,
    metrics: { results: r3Results, exitCode: String(r3Exit) },
  };

  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* non-fatal */
  }

  const allPassed =
    primedCacheHit.passed && noEmbedOnReplay.passed && distinctQueryFallback.passed;

  return {
    check: "embedding-cache-replay",
    passed: allPassed,
    subChecks: { primedCacheHit, noEmbedOnReplay, distinctQueryFallback },
    mode,
    timestamp: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

if (
  process.argv[1]?.endsWith("embedding-cache-replay.ts") ||
  process.argv[1]?.endsWith("embedding-cache-replay.js")
) {
  const jsonMode = process.argv.includes("--json");
  runEmbeddingCacheReplayCheck({}).then((report) => {
    if (jsonMode) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      const icon = report.passed ? "✓" : "✗";
      console.log(
        `\n[embedding-cache-replay] ${icon} ${report.passed ? "PASS" : "FAIL"} (mode: ${report.mode})`
      );
      for (const [k, sub] of Object.entries(report.subChecks)) {
        const subIcon = sub.passed ? "  ✓" : "  ✗";
        console.log(`${subIcon} ${k}: ${sub.detail}`);
      }
    }
    process.exit(report.passed ? 0 : 1);
  });
}
