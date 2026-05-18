/**
 * rsync.ts — T3b: rsync dry-run validator
 *
 * Replaces remote destinations (root@vps:/path) with local tmp dirs,
 * then runs rsync --dry-run --verbose to verify the command is valid.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { spawnSync } from "child_process";
import type { CategorizedCommand } from "../categorize.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RsyncResult {
  type: "rsync";
  /** Original command line */
  originalLine: string;
  /** Rewritten command with local paths */
  rewrittenLine: string;
  passed: boolean;
  /** Files that would be transferred (from dry-run output) */
  fileList: string[];
  /** Any errors */
  errorOutput: string;
  durationMs: number;
  /** True if this was a --dry-run rewrite (always true in validator) */
  isDryRun: boolean;
  /** Warnings found (e.g., double slashes in paths) */
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

const REPO_ROOT = new URL("../../../..", import.meta.url).pathname;

/**
 * Validate all rsync commands in a CategorizedCommand block.
 * Creates tmp src dirs, rewrites remote destinations to tmp, runs --dry-run.
 */
export async function validateRsync(cmd: CategorizedCommand): Promise<RsyncResult[]> {
  const results: RsyncResult[] = [];

  for (const detected of cmd.commands.filter((c) => c.type === "rsync")) {
    const result = await runRsyncDryRun(detected.line);
    results.push(result);
  }

  return results;
}

async function runRsyncDryRun(rawLine: string): Promise<RsyncResult> {
  const start = Date.now();
  const warnings: string[] = [];

  // Join line continuations (\ at end of line) before processing
  const line = rawLine.replace(/\\\n\s*/g, " ").trim();

  // Create tmp dirs
  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), "deploy-validator-rsync-"));
  const tmpSrc = path.join(tmpBase, "src");
  const tmpDest = path.join(tmpBase, "dest");
  fs.mkdirSync(tmpSrc, { recursive: true });
  fs.mkdirSync(tmpDest, { recursive: true });

  // Create placeholder source files so rsync has something to check
  fs.writeFileSync(path.join(tmpSrc, "placeholder.ts"), "// placeholder\n");

  try {
    // Rewrite the command: replace remote and local staged- paths
    const { rewritten, detectedWarnings } = rewriteRsyncLine(line, tmpSrc, tmpDest);
    warnings.push(...detectedWarnings);

    // Parse rewritten command into args
    const args = parseRsyncArgs(rewritten);

    // Ensure --dry-run is present
    if (!args.includes("--dry-run")) {
      args.splice(1, 0, "--dry-run");
    }
    if (!args.includes("--verbose") && !args.includes("-v")) {
      args.splice(1, 0, "--verbose");
    }

    const result = spawnSync("rsync", args, {
      encoding: "utf8",
      timeout: 15000,
    });

    const stdout = result.stdout ?? "";
    const stderr = result.stderr ?? "";
    const fileList = stdout
      .split("\n")
      .filter((l) => l && !l.startsWith("sending") && !l.startsWith("sent") && !l.startsWith("total") && !l.startsWith("./"))
      .map((l) => l.trim())
      .filter(Boolean);

    // Check for path issues
    if (rewritten.includes("//")) {
      warnings.push("double slash detected in path");
    }

    return {
      type: "rsync",
      originalLine: line,
      rewrittenLine: rewritten,
      passed: result.status === 0,
      fileList,
      errorOutput: stderr.trim(),
      durationMs: Date.now() - start,
      isDryRun: true,
      warnings,
    };
  } finally {
    fs.rmSync(tmpBase, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// Path rewriter
// ---------------------------------------------------------------------------

function rewriteRsyncLine(
  line: string,
  tmpSrc: string,
  tmpDest: string
): { rewritten: string; detectedWarnings: string[] } {
  const warnings: string[] = [];
  let rewritten = line;

  // Replace remote destinations: root@<host>:/path → tmpDest
  rewritten = rewritten.replace(/(?:root|ubuntu|admin|[\w-]+)@[\w.-]+:[\w/\\.${}-]*/g, tmpDest + "/");

  // Replace $VPS_HOST:/path patterns
  rewritten = rewritten.replace(/\$\{?VPS_HOST\}?:[\w/\\.${}-]*/g, tmpDest + "/");

  // Replace worktree-absolute paths to local staged-* dirs with tmpSrc
  // e.g., /Users/lab/Claude/.../staged-P5/edits/src/
  rewritten = rewritten.replace(/\/[^\s]+\/staged-[\w-]+\/[^\s]*/g, tmpSrc + "/");

  // Replace relative staged-* paths (source side) with tmpSrc
  rewritten = rewritten.replace(/\bstaged-[\w.-]+\/[^\s]*/g, tmpSrc + "/");

  // Detect double slashes (path construction bug)
  if (/[^:]{2}\/\//.test(rewritten)) {
    warnings.push(`double slash in: ${rewritten}`);
  }

  return { rewritten, detectedWarnings: warnings };
}

// ---------------------------------------------------------------------------
// Simple arg parser (handles quoted strings and continuation lines)
// ---------------------------------------------------------------------------

function parseRsyncArgs(line: string): string[] {
  // Remove rsync prefix
  const rest = line.replace(/^\s*rsync\s+/, "");
  // Naive split on whitespace (handles most cases in deploy guide)
  const args: string[] = [];
  const tokenRe = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = tokenRe.exec(rest)) !== null) {
    args.push(m[1].replace(/^["']|["']$/g, ""));
  }
  return args;
}
