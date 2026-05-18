/**
 * offline-mode-check.ts — Check 3 of 8 (CI-runnable)
 *
 * Starts the nox-mem mock (or the real binary on the VPS) with
 * NOX_OFFLINE_MODE=1 + a pre-seeded fixture DB, runs a full ingest + search
 * workload, and asserts:
 *
 *   3a. Ingest of a sample entity file completes offline.
 *   3b. Search returns ≥ 1 result via the FTS/cache path.
 *   3c. Zero outbound socket attempts to any non-loopback destination.
 *
 * Network blocking: in addition to the mock's own offline-mode guard, this
 * check pre-loads a Socket.prototype.connect patch via NODE_OPTIONS so that
 * any rogue native code attempting a TCP connect to a non-loopback peer is
 * rejected at the OS-binding boundary.
 *
 * Usage:
 *   npx ts-node validation/zero-vendor/offline-mode-check.ts
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OfflineModeReport {
  check: "offline-mode-check";
  passed: boolean;
  subChecks: {
    ingestOffline: SubCheckResult;
    searchOffline: SubCheckResult;
    zeroNetworkCalls: SubCheckResult;
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
// Config
// ---------------------------------------------------------------------------

const SUITE_DIR = path.dirname(fileURLToPath(import.meta.url));
const MOCK_BIN = path.join(SUITE_DIR, "fixtures", "mock-nox-mem.cjs");
const SEED_BIN = path.join(SUITE_DIR, "fixtures", "seed-fixture-db.cjs");
const SOCKET_GUARD = path.join(SUITE_DIR, "fixtures", "socket-guard.cjs");

const SAMPLE_ENTITY = `---
type: concept
slug: zero-vendor-offline-fixture
title: "Zero Vendor Offline Fixture"
importance: 0.8
pain: 0.1
retention_days: 30
created: 2026-05-17
---

# Compiled

nox-mem is offline-capable by design. FTS5 indexing requires no network.
Hybrid search degrades gracefully to BM25-only when no cached embeddings.

# Timeline

- 2026-05-17 created as offline test fixture for the zero-vendor suite.
`;

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
// Process runner — captures both the mock-recorded outbound URLs AND any
// socket attempts intercepted by the socket-guard preload.
// ---------------------------------------------------------------------------

interface RunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  outboundUrls: string[];
  socketAttempts: string[];
}

function runStep(
  bin: string,
  args: string[],
  env: Record<string, string>,
  netLog: string,
  socketLog: string
): RunResult {
  let stdout = "";
  let stderr = "";
  let exitCode: number | null = 0;

  // NODE_OPTIONS lets us preload the guard into BOTH the mock and a future
  // real binary without modifying their source.
  const nodeOptions = `--require ${SOCKET_GUARD}`;

  try {
    stdout = execFileSync("node", [bin, ...args], {
      encoding: "utf8",
      timeout: 8000,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        ...env,
        NOX_NETWORK_REPORT: netLog,
        NOX_SOCKET_LOG: socketLog,
        NODE_OPTIONS: nodeOptions,
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
  const socketAttempts = fs.existsSync(socketLog)
    ? fs.readFileSync(socketLog, "utf8").split("\n").filter(Boolean)
    : [];

  return { exitCode, stdout, stderr, outboundUrls, socketAttempts };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export async function runOfflineModeCheck(opts: {
  noxMemDir?: string;
}): Promise<OfflineModeReport> {
  const noxMemDir = opts.noxMemDir ?? process.env.NOX_MEM_DIR ?? "";
  const liveBin = noxMemDir ? findNoxMemBin(noxMemDir) : null;
  const bin = liveBin ?? MOCK_BIN;
  const mode: "live" | "ci" = liveBin ? "live" : "ci";

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "nox-mem-offline-"));
  const entityFile = path.join(tmpDir, "test-entity.md");
  const fixtureDb = path.join(tmpDir, "fixture-db.json");
  const netLog = path.join(tmpDir, "net.log");
  const socketLog = path.join(tmpDir, "socket.log");

  fs.writeFileSync(entityFile, SAMPLE_ENTITY, "utf8");

  // Seed the fixture DB with primed embeddings BEFORE entering offline mode.
  // This simulates the real-world "warm cache" scenario.
  try {
    execFileSync("node", [SEED_BIN, fixtureDb], { encoding: "utf8", timeout: 5000, stdio: ["ignore", "ignore", "ignore"] });
  } catch {
    /* mock degrades gracefully */
  }

  const baseEnv = {
    NOX_OFFLINE_MODE: "1",
    NOX_FIXTURE_DB: fixtureDb,
    NOX_MEM_DIR: noxMemDir,
  };

  // ----- 3a: ingest offline -----
  const ingest = runStep(bin, ["ingest-entity", entityFile], baseEnv, netLog, socketLog);
  let ingestOk = false;
  try {
    const parsed = JSON.parse(ingest.stdout.trim().split("\n").pop() || "{}");
    ingestOk = !!parsed.success && (parsed.ingested ?? 0) > 0;
  } catch {
    ingestOk = false;
  }
  const ingestOffline: SubCheckResult = {
    passed: ingestOk && ingest.exitCode === 0,
    detail: ingestOk
      ? "Entity ingested successfully with NOX_OFFLINE_MODE=1 (FTS path, no embedding network call)"
      : `Ingest failed (exit=${ingest.exitCode}): ${ingest.stderr.slice(0, 200) || ingest.stdout.slice(0, 200)}`,
  };

  // ----- 3b: search offline against the pre-seeded fixture -----
  const search = runStep(
    bin,
    ["search", "zero vendor sqlite offline"],
    baseEnv,
    netLog,
    socketLog
  );
  let hasResults = false;
  let cacheHit = false;
  try {
    const parsed = JSON.parse(search.stdout.trim().split("\n").pop() || "{}");
    hasResults = Array.isArray(parsed.results) && parsed.results.length > 0;
    cacheHit = !!parsed.cacheHit;
  } catch {
    hasResults = false;
  }
  const searchOffline: SubCheckResult = {
    passed: hasResults && search.exitCode === 0,
    detail: hasResults
      ? `Search returned results offline (cacheHit=${cacheHit})`
      : `Search returned no results (exit=${search.exitCode}): ${search.stdout.slice(0, 200)}`,
    metrics: { cacheHit: String(cacheHit) },
  };

  // ----- 3c: zero outbound network calls across both ops -----
  const allUrls = [...ingest.outboundUrls, ...search.outboundUrls];
  const allSockets = [...ingest.socketAttempts, ...search.socketAttempts];

  // Subtract known-safe loopback targets from socket attempts.
  const unexpectedSockets = allSockets.filter(
    (s) => !s.includes("127.0.0.1") && !s.includes("localhost") && !s.includes("::1")
  );

  // In offline mode the mock refuses to record outbound HTTP attempts that
  // would have gone out — but does record blocked attempts. Anything that
  // resulted in an actual socket.connect is the smoking gun.
  const zeroNetworkCalls: SubCheckResult = {
    passed: unexpectedSockets.length === 0,
    detail:
      unexpectedSockets.length === 0
        ? `Zero non-loopback socket attempts across ingest + search (urls=${allUrls.length}, all blocked at offline guard)`
        : `FAIL: ${unexpectedSockets.length} non-loopback socket attempt(s): ${unexpectedSockets.slice(0, 5).join(", ")}`,
    metrics: {
      blockedHttpAttempts: allUrls.length,
      socketConnects: allSockets.length,
      unexpectedSockets: unexpectedSockets.length,
    },
  };

  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* non-fatal */
  }

  const allPassed =
    ingestOffline.passed && searchOffline.passed && zeroNetworkCalls.passed;

  return {
    check: "offline-mode-check",
    passed: allPassed,
    subChecks: { ingestOffline, searchOffline, zeroNetworkCalls },
    mode,
    timestamp: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

if (
  process.argv[1]?.endsWith("offline-mode-check.ts") ||
  process.argv[1]?.endsWith("offline-mode-check.js")
) {
  const jsonMode = process.argv.includes("--json");
  runOfflineModeCheck({}).then((report) => {
    if (jsonMode) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      const icon = report.passed ? "✓" : "✗";
      console.log(
        `\n[offline-mode-check] ${icon} ${report.passed ? "PASS" : "FAIL"} (mode: ${report.mode})`
      );
      for (const [k, sub] of Object.entries(report.subChecks)) {
        const subIcon = sub.passed ? "  ✓" : "  ✗";
        console.log(`${subIcon} ${k}: ${sub.detail}`);
        if (sub.metrics) {
          for (const [mk, mv] of Object.entries(sub.metrics)) {
            console.log(`      ${mk}: ${mv}`);
          }
        }
      }
    }
    process.exit(report.passed ? 0 : 1);
  });
}
