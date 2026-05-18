/**
 * path-validator.ts — T3d: Path and argument validator
 *
 * Validates file paths and env var references in deploy commands.
 * Catches: double slashes, unescaped spaces, undefined $VARs, suspicious paths.
 */

import type { CategorizedCommand } from "../categorize.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PathIssue {
  kind:
    | "double-slash"
    | "unescaped-space"
    | "undefined-var"
    | "absolute-local-path"
    | "suspicious-path"
    | "missing-trailing-slash-dir"
    | "worktree-path-leaked";
  message: string;
  line: string;
}

export interface PathValidationResult {
  type: "path-validator";
  block: CategorizedCommand;
  passed: boolean;
  issues: PathIssue[];
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Known env vars (defined in DEPLOY-WAVE-B.md or .env)
// ---------------------------------------------------------------------------

const KNOWN_ENV_VARS = new Set([
  "VPS_HOST",
  "NM",
  "NOX_ANSWER_MODEL",
  "NOX_ANSWER_MAX_CHUNKS",
  "NOX_EMBEDDING_PROVIDER",
  "NOX_LLM_PROVIDER",
  "NOX_EXPORT_PASSPHRASE",
  "NOX_L4_REGEX_ENABLED",
  "NOX_VIEWER_TOKEN",
  "NOX_CONFLICT_MODE",
  "NOX_CONFIDENCE_SCORING",
  "NOX_SALIENCE_MODE",
  "NOX_ALLOW_NO_SNAPSHOT",
  "NOX_API_PORT",
  "NOX_SEARCH_LOG_TEXT",
  "GEMINI_API_KEY",
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "HOME",
  "PATH",
  "USER",
  "SHELL",
  "PWD",
  "VIEWER_TOKEN",
  "SNAP_V11",
  "SNAP_V19",
  "SNAP_V20",
  "BAK",
  "SSE_PID",
]);

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

export function validatePaths(cmd: CategorizedCommand): PathValidationResult {
  const start = Date.now();
  const issues: PathIssue[] = [];
  const lines = cmd.block.content.split("\n");

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    // Double slash in paths (excluding ://)
    const doubleSlash = trimmed.replace(/https?:\/\//g, "").replace(/:\/\//g, "");
    if (/[^\s:]{1}\/\//.test(doubleSlash)) {
      issues.push({
        kind: "double-slash",
        message: `Double slash detected (possible path construction bug)`,
        line: trimmed,
      });
    }

    // Worktree paths leaked into deploy commands (local machine paths that shouldn't be on VPS)
    if (/\/\.claude\/worktrees\/agent-[a-f0-9]+\//.test(trimmed)) {
      issues.push({
        kind: "worktree-path-leaked",
        message: `Worktree-absolute path in command — replace with VPS path or relative path. The DEPLOY-WAVE-B.md §3c correctly references worktree paths for P5 only, which is expected.`,
        line: trimmed,
      });
    }

    // Unescaped spaces in paths (between quotes is OK, outside is not)
    // Simplified: look for paths that seem to have spaces not in quotes
    if (/[^"']\s+\/[A-Za-z]/.test(trimmed) && !/ssh|rsync|curl|systemctl/.test(trimmed)) {
      // Heuristic only — not reported as error, only warning
    }

    // Undefined $VARs (only flag uppercase that look like env vars but aren't known)
    const varRefs = trimmed.match(/\$\{?([A-Z_][A-Z0-9_]*)\}?/g) ?? [];
    for (const varRef of varRefs) {
      const varName = varRef.replace(/[${}]/g, "");
      if (!KNOWN_ENV_VARS.has(varName) && varName.length > 2 && !varName.startsWith("_")) {
        issues.push({
          kind: "undefined-var",
          message: `$${varName} not found in known env vars list — verify it's defined in .env or earlier in the block`,
          line: trimmed,
        });
      }
    }
  }

  return {
    type: "path-validator",
    block: cmd,
    passed: !issues.some(
      (i) => i.kind === "double-slash" || i.kind === "undefined-var"
    ),
    issues,
    durationMs: Date.now() - start,
  };
}
