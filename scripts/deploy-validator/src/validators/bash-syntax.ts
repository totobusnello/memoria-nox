/**
 * bash-syntax.ts — T3a: bash -n syntax checker
 *
 * Runs `bash -n` on each bash code block to catch syntax errors
 * (missing quotes, unmatched brackets, bad heredocs) WITHOUT executing.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { spawnSync } from "child_process";
import type { CategorizedCommand } from "../categorize.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BashSyntaxResult {
  type: "bash-syntax";
  block: CategorizedCommand;
  passed: boolean;
  /** bash -n exit code (0 = ok) */
  exitCode: number;
  /** Any stderr output from bash -n */
  errorOutput: string;
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

/**
 * Run `bash -n` syntax check on a block of bash.
 * Skips non-bash blocks and diagram/text-only blocks.
 */
export function checkBashSyntax(cmd: CategorizedCommand): BashSyntaxResult {
  const start = Date.now();
  const { block } = cmd;

  // Skip empty-language blocks — they are likely diagrams or plain text, not shell
  if (block.language === "") {
    return {
      type: "bash-syntax",
      block: cmd,
      passed: true,
      exitCode: 0,
      errorOutput: "(skipped: empty language tag — not shell)",
      durationMs: Date.now() - start,
    };
  }

  // Pre-process: replace VPS-specific env vars with safe placeholders
  const content = sanitizeForBashCheck(block.content);

  // Write to tmp file
  const tmpFile = path.join(os.tmpdir(), `deploy-validator-bash-${Date.now()}-${Math.random().toString(36).slice(2)}.sh`);
  try {
    fs.writeFileSync(tmpFile, `#!/usr/bin/env bash\n${content}\n`, "utf8");

    const result = spawnSync("bash", ["-n", tmpFile], {
      encoding: "utf8",
      timeout: 5000,
    });

    return {
      type: "bash-syntax",
      block: cmd,
      passed: result.status === 0,
      exitCode: result.status ?? 1,
      errorOutput: (result.stderr ?? "").trim(),
      durationMs: Date.now() - start,
    };
  } finally {
    try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
  }
}

// ---------------------------------------------------------------------------
// Sanitizer — replaces env vars / VPS paths so bash -n doesn't error
// on undefined variables but can still check syntax
// ---------------------------------------------------------------------------

function sanitizeForBashCheck(content: string): string {
  let result = content;

  // Join line continuations (\ at end of line) — multi-line shell commands
  result = result.replace(/\\\n\s*/g, " ");

  return result
    // Replace <placeholder> template tokens (e.g., root@<vps>, <timestamp>)
    .replace(/<[a-z][\w-]*>/g, "placeholder")
    // Replace $VAR_NAME patterns with safe placeholder strings
    .replace(/\$\{([A-Z_][A-Z0-9_]*)\}/g, '"placeholder_$1"')
    .replace(/\$([A-Z_][A-Z0-9_]*)/g, '"placeholder_$1"')
    // Remove set -e / set -euo pipefail (would cause failures on unset vars)
    .replace(/set\s+-[a-zA-Z]*e[a-zA-Z]*/g, "# set -e (removed for syntax check)")
    // Remove trap statements that reference vars
    .replace(/^trap\s+.*/gm, "# trap (removed for syntax check)")
    // Replace bare text DAG diagram lines (not valid shell) that appear in deploy guides
    // e.g. "Step 1  ── Schema v11" or "Pre-flight → v11 migration"
    .replace(/^(Step\s+\d|Pre-flight|Final\s+build|staged-).*$/gm, "# [diagram line removed]");
}
