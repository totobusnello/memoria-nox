/**
 * smoke-runner.ts — T4: Post-validation smoke test harness
 *
 * Attempts to run curl commands from DEPLOY-WAVE-B.md against a
 * locally running nox-mem instance (if available). VPS-only tests
 * are marked accordingly and skipped in CI.
 */

import { spawnSync } from "child_process";
import type { CategorizedCommand } from "./categorize.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SmokeStatus = "pass" | "fail" | "vps-only" | "skipped" | "no-local-api";

export interface SmokeResult {
  type: "smoke";
  label: string;
  url: string;
  status: SmokeStatus;
  httpStatus?: number;
  responseSnippet?: string;
  errorMessage?: string;
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const LOCAL_API_BASE = "http://127.0.0.1:18802";
const TIMEOUT_MS = 5000;

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

/**
 * Run smoke tests against local API for all curl commands.
 * VPS-only commands (ssh-wrapped, or auth-requiring) are flagged and skipped.
 */
export async function runSmokeTests(
  cmds: CategorizedCommand[],
  opts: { skipLocalCheck?: boolean } = {}
): Promise<SmokeResult[]> {
  const results: SmokeResult[] = [];

  // Check if local API is reachable
  const apiReachable = opts.skipLocalCheck ? false : isLocalApiReachable();

  for (const cmd of cmds) {
    const curlCommands = cmd.commands.filter((c) => c.type === "curl");
    for (const curl of curlCommands) {
      const url = curl.meta.curlUrl;
      if (!url) continue;

      const result = await runSmoke(url, cmd, apiReachable);
      results.push(result);
    }
  }

  return results;
}

async function runSmoke(
  rawUrl: string,
  cmd: CategorizedCommand,
  apiReachable: boolean
): Promise<SmokeResult> {
  const start = Date.now();

  // Determine if this is a localhost URL
  const isLocalhost =
    rawUrl.includes("127.0.0.1") || rawUrl.includes("localhost");

  // Check if URL references env vars that we can't resolve (VPS-only)
  const hasUnresolvableVars =
    /\$\{?(?:NOX_VIEWER_TOKEN|NOX_EXPORT_PASSPHRASE)\}?/.test(rawUrl);

  // Is this inside an SSH block? (remote execution)
  const isRemote = cmd.isRemoteOnly;

  if (isRemote || (!isLocalhost && !rawUrl.startsWith("http://127.0.0.1"))) {
    return {
      type: "smoke",
      label: `VPS curl: ${rawUrl.slice(0, 60)}`,
      url: rawUrl,
      status: "vps-only",
      durationMs: Date.now() - start,
    };
  }

  if (hasUnresolvableVars) {
    return {
      type: "smoke",
      label: `Auth-required curl: ${rawUrl.slice(0, 60)}`,
      url: rawUrl,
      status: "vps-only",
      durationMs: Date.now() - start,
    };
  }

  if (!apiReachable) {
    return {
      type: "smoke",
      label: `Local curl: ${rawUrl.slice(0, 60)}`,
      url: rawUrl,
      status: "no-local-api",
      durationMs: Date.now() - start,
    };
  }

  // Resolve env vars with test values for localhost calls
  const resolvedUrl = rawUrl
    .replace(/\$\{?NM\}?/g, "/root/.openclaw/workspace/tools/nox-mem")
    .replace(/\$\{?[A-Z_][A-Z0-9_]*\}?/g, "test-placeholder");

  try {
    const curlResult = spawnSync(
      "curl",
      ["-sf", "--max-time", String(TIMEOUT_MS / 1000), resolvedUrl],
      {
        encoding: "utf8",
        timeout: TIMEOUT_MS + 1000,
      }
    );

    const responseSnippet = (curlResult.stdout ?? "").slice(0, 200);
    const passed = curlResult.status === 0;

    return {
      type: "smoke",
      label: `curl ${resolvedUrl.slice(0, 60)}`,
      url: rawUrl,
      status: passed ? "pass" : "fail",
      httpStatus: curlResult.status ?? undefined,
      responseSnippet,
      durationMs: Date.now() - start,
    };
  } catch (e) {
    return {
      type: "smoke",
      label: `curl ${rawUrl.slice(0, 60)}`,
      url: rawUrl,
      status: "fail",
      errorMessage: (e as Error).message,
      durationMs: Date.now() - start,
    };
  }
}

// ---------------------------------------------------------------------------
// Probe local API
// ---------------------------------------------------------------------------

function isLocalApiReachable(): boolean {
  try {
    const result = spawnSync(
      "curl",
      ["-sf", "--max-time", "2", `${LOCAL_API_BASE}/api/health`],
      { encoding: "utf8", timeout: 3000 }
    );
    return result.status === 0;
  } catch {
    return false;
  }
}
