/**
 * integration.test.ts — node:test integration suite for the zero-vendor
 * validation checks. Confirms each of the 4 newly-runnable checks passes
 * against fresh fixture data AND that the existing 4 checks remain green.
 *
 * Run via:
 *   node --test --test-reporter=spec --import tsx validation/zero-vendor/__tests__/integration.test.ts
 *
 * The suite re-uses the exported `run*Check` functions from each check
 * module so failures surface with full subCheck context.
 */

import { test, describe, before } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { runRuntimeDepsCheck } from "../runtime-deps-check.js";
import { runOfflineModeCheck } from "../offline-mode-check.js";
import { runEmbeddingCacheReplayCheck } from "../embedding-cache-replay.js";
import { runProviderSubstitutionCheck } from "../provider-substitution-dry-run.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SUITE_DIR = path.dirname(HERE);
const MOCK_BIN = path.join(SUITE_DIR, "fixtures", "mock-nox-mem.cjs");
const SEED_BIN = path.join(SUITE_DIR, "fixtures", "seed-fixture-db.cjs");

let scratchDir: string;

before(() => {
  scratchDir = fs.mkdtempSync(path.join(os.tmpdir(), "zero-vendor-itest-"));
  // Force CI mode by clearing any inherited NOX_MEM_DIR.
  delete process.env.NOX_MEM_DIR;
});

// ---------------------------------------------------------------------------
// Fixture sanity — the mock CLI must accept the contract env vars.
// ---------------------------------------------------------------------------

describe("fixture/mock-nox-mem.cjs contract", () => {
  test("stats command returns valid JSON", () => {
    const fixtureDb = path.join(scratchDir, "stats-fixture.json");
    execFileSync("node", [SEED_BIN, fixtureDb], { stdio: "ignore" });

    const out = execFileSync("node", [MOCK_BIN, "stats"], {
      encoding: "utf8",
      env: { ...process.env, NOX_FIXTURE_DB: fixtureDb },
      stdio: ["ignore", "pipe", "pipe"],
    });
    const parsed = JSON.parse(out);
    assert.equal(parsed.status, "ok");
    assert.equal(parsed.totalChunks, 5);
    assert.equal(parsed.vectorCoverage, 1);
  });

  test("search returns results in offline mode using primed cache", () => {
    const fixtureDb = path.join(scratchDir, "search-fixture.json");
    execFileSync("node", [SEED_BIN, fixtureDb], { stdio: "ignore" });

    const out = execFileSync(
      "node",
      [MOCK_BIN, "search", "zero vendor sqlite offline"],
      {
        encoding: "utf8",
        env: {
          ...process.env,
          NOX_FIXTURE_DB: fixtureDb,
          NOX_OFFLINE_MODE: "1",
        },
        stdio: ["ignore", "pipe", "pipe"],
      }
    );
    const parsed = JSON.parse(out);
    assert.ok(Array.isArray(parsed.results), "results is an array");
    assert.ok(parsed.results.length > 0, "at least one result");
    assert.equal(parsed.cacheHit, true);
  });

  test("answer with anthropic + invalid key emits structured PROVIDER_AUTH_FAILED", () => {
    let stderr = "";
    let exitCode = 0;
    try {
      execFileSync("node", [MOCK_BIN, "answer", "test"], {
        encoding: "utf8",
        env: {
          ...process.env,
          NOX_LLM_PROVIDER: "anthropic",
          ANTHROPIC_API_KEY: "invalid-key-xxxxxx",
        },
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (e: unknown) {
      const err = e as { status?: number; stderr?: Buffer | string };
      exitCode = err.status ?? 1;
      stderr = err.stderr ? err.stderr.toString() : "";
    }
    assert.notEqual(exitCode, 0, "process must fail");
    const parsed = JSON.parse(stderr.trim());
    assert.equal(parsed.ok, false);
    assert.match(parsed.error, /PROVIDER_AUTH/);
    assert.equal(parsed.provider, "anthropic");
    assert.match(parsed.hint, /ANTHROPIC_API_KEY/);
  });
});

// ---------------------------------------------------------------------------
// 4 newly-runnable checks
// ---------------------------------------------------------------------------

describe("runtime-deps-check (CI mock)", () => {
  test("passes with no unexpected egress in offline mode", async () => {
    const report = await runRuntimeDepsCheck({});
    assert.equal(report.mode, "ci");
    assert.equal(report.passed, true, JSON.stringify(report.subChecks, null, 2));
    assert.equal(report.subChecks.offlineEgress.passed, true);
    assert.equal(report.subChecks.geminiOnlyEgress.passed, true);
  });
});

describe("offline-mode-check (CI mock + socket-guard)", () => {
  test("passes ingest + search with zero non-loopback connects", async () => {
    const report = await runOfflineModeCheck({});
    assert.equal(report.mode, "ci");
    assert.equal(report.passed, true, JSON.stringify(report.subChecks, null, 2));
    assert.equal(report.subChecks.ingestOffline.passed, true);
    assert.equal(report.subChecks.searchOffline.passed, true);
    assert.equal(report.subChecks.zeroNetworkCalls.passed, true);
  });
});

describe("embedding-cache-replay (CI mock + NOX_FAIL_IF_EMBED)", () => {
  test("primed query is a cache hit; replay does not invoke embedder", async () => {
    const report = await runEmbeddingCacheReplayCheck({});
    assert.equal(report.mode, "ci");
    assert.equal(report.passed, true, JSON.stringify(report.subChecks, null, 2));
    assert.equal(report.subChecks.primedCacheHit.passed, true);
    assert.equal(report.subChecks.noEmbedOnReplay.passed, true);
    assert.equal(report.subChecks.distinctQueryFallback.passed, true);
  });
});

describe("provider-substitution-dry-run (CI mock contract)", () => {
  test("invalid / missing / unknown all produce structured errors; no silent fallback", async () => {
    const report = await runProviderSubstitutionCheck({});
    assert.equal(report.mode, "ci");
    assert.equal(report.passed, true, JSON.stringify(report.subChecks, null, 2));
    assert.equal(report.subChecks.invalidKeyFailsClearly.passed, true);
    assert.equal(report.subChecks.missingKeyFailsClearly.passed, true);
    assert.equal(report.subChecks.unknownProviderFailsClearly.passed, true);
    assert.equal(report.subChecks.noSilentFallback.passed, true);
  });
});

// ---------------------------------------------------------------------------
// Regression — the existing 4 working checks must remain green.
// ---------------------------------------------------------------------------

describe("regression — existing CI checks remain green", () => {
  test("sqlite-portable-check.sh exits 0 against CI fixture", () => {
    const out = execFileSync(
      "bash",
      [path.join(SUITE_DIR, "sqlite-portable-check.sh")],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    assert.match(out, /CI fixture mode|chunks/i);
  });

  test("no-daemon-check.sh exits 0 against CI fixture", () => {
    const out = execFileSync(
      "bash",
      [path.join(SUITE_DIR, "no-daemon-check.sh")],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    assert.match(out, /CI fixture mode|queries|daemon/i);
  });
});

// ---------------------------------------------------------------------------
// Full-suite smoke test: the runner must report passed=true.
// ---------------------------------------------------------------------------

describe("runner end-to-end", () => {
  test("runner.ts emits a report with all 8 checks passing", () => {
    const reportPath = path.join(scratchDir, "suite-report.json");
    execFileSync(
      "npx",
      ["--yes", "tsx", path.join(SUITE_DIR, "runner.ts"), "--report", reportPath],
      {
        encoding: "utf8",
        timeout: 60_000,
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, NOX_MEM_DIR: "" },
      }
    );
    const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
    assert.equal(report.passed, true, JSON.stringify(report.summary));
    assert.equal(report.summary.total, 8);
    assert.equal(report.summary.fail, 0);
    assert.equal(report.summary.pass, 8);
  });
});
