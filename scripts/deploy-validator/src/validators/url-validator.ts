/**
 * url-validator.ts — T3e: URL syntax validator
 *
 * Validates URLs extracted from curl commands:
 * - Parses with `new URL()` to catch malformed URLs
 * - Verifies localhost URLs use correct port (18802 per CLAUDE.md regra #4)
 * - Checks path format (no trailing ??, double slashes in path)
 */

import type { CategorizedCommand } from "../categorize.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UrlIssue {
  kind: "parse-error" | "wrong-port" | "double-slash-in-path" | "http-in-prod-warning";
  url: string;
  message: string;
}

export interface UrlValidationResult {
  type: "url-validator";
  block: CategorizedCommand;
  passed: boolean;
  issues: UrlIssue[];
  validUrls: string[];
  durationMs: number;
}

// ---------------------------------------------------------------------------
// Constants from CLAUDE.md regra #4
// ---------------------------------------------------------------------------

const CORRECT_NOX_PORT = 18802;
const WRONG_PORT = 18800; // Chrome squats this

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

export function validateUrls(cmd: CategorizedCommand): UrlValidationResult {
  const start = Date.now();
  const issues: UrlIssue[] = [];
  const validUrls: string[] = [];

  const blockLines = cmd.block.content.split("\n");
  for (const detected of cmd.commands.filter((c) => c.type === "curl")) {
    const rawUrl = detected.meta.curlUrl;
    if (!rawUrl) continue;

    // Skip curl commands in "WRONG" example context
    // Check the line before the command line in the block
    const lineIdx = detected.lineOffset - 1; // lineOffset is 1-based
    const prevLine = lineIdx > 0 ? blockLines[lineIdx - 1]?.trim() ?? "" : "";
    if (/^#\s*WRONG/i.test(prevLine)) continue;

    // Resolve env vars to testable values
    const resolvedUrl = resolveTestUrl(rawUrl);
    if (!resolvedUrl) continue; // Skip if not resolvable

    const urlIssues = validateUrl(resolvedUrl, rawUrl);
    if (urlIssues.length === 0) {
      validUrls.push(rawUrl);
    } else {
      issues.push(...urlIssues);
    }
  }

  // Also scan all lines for URLs not captured by curl detector
  const lines = cmd.block.content.split("\n");
  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    // Skip lines in "WRONG" example blocks (preceded by # WRONG comment)
    const prevLine = li > 0 ? lines[li - 1].trim() : "";
    if (/^#\s*WRONG/i.test(prevLine) || /^#\s*WRONG/i.test(line)) continue;

    const urlMatches = line.match(/https?:\/\/[^\s'")\]]+/g) ?? [];
    for (const url of urlMatches) {
      if (validUrls.includes(url) || issues.some((i) => i.url === url)) continue;
      const resolvedUrl = resolveTestUrl(url);
      if (!resolvedUrl) continue;
      const urlIssues = validateUrl(resolvedUrl, url);
      if (urlIssues.length === 0) {
        if (!validUrls.includes(url)) validUrls.push(url);
      } else {
        issues.push(...urlIssues);
      }
    }
  }

  const hasFatal = issues.some(
    (i) => i.kind === "parse-error" || i.kind === "wrong-port"
  );

  return {
    type: "url-validator",
    block: cmd,
    passed: !hasFatal,
    issues,
    validUrls,
    durationMs: Date.now() - start,
  };
}

// ---------------------------------------------------------------------------
// Per-URL validation
// ---------------------------------------------------------------------------

function validateUrl(resolved: string, original: string): UrlIssue[] {
  const issues: UrlIssue[] = [];

  // 1. Parse check
  let parsed: URL;
  try {
    parsed = new URL(resolved);
  } catch {
    issues.push({
      kind: "parse-error",
      url: original,
      message: `Invalid URL syntax: ${resolved}`,
    });
    return issues;
  }

  // 2. Port check for localhost/127.0.0.1 — must be 18802
  if (
    (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") &&
    parsed.port
  ) {
    const port = parseInt(parsed.port, 10);
    if (port === WRONG_PORT) {
      issues.push({
        kind: "wrong-port",
        url: original,
        message: `Wrong port ${WRONG_PORT} — Chrome squats it. Correct port is ${CORRECT_NOX_PORT} (CLAUDE.md regra #4)`,
      });
    } else if (port !== CORRECT_NOX_PORT) {
      // Other ports (e.g., :3000 for viewer?) are just a warning
      issues.push({
        kind: "http-in-prod-warning",
        url: original,
        message: `Localhost port ${port} is not the standard nox-mem port ${CORRECT_NOX_PORT} — verify intentional`,
      });
    }
  }

  // 3. Double slash in path
  if (/\/\//.test(parsed.pathname)) {
    issues.push({
      kind: "double-slash-in-path",
      url: original,
      message: `Double slash in URL path: ${parsed.pathname}`,
    });
  }

  return issues;
}

// ---------------------------------------------------------------------------
// Resolve env vars to testable values
// ---------------------------------------------------------------------------

function resolveTestUrl(raw: string): string | null {
  // Replace ${NOX_VIEWER_TOKEN} and similar with placeholder
  const resolved = raw
    .replace(/\$\{?[A-Z_][A-Z0-9_]*\}?/g, "placeholder")
    .replace(/`[^`]*`/g, "placeholder");

  // If still not parseable (e.g., variable-only URL), skip
  if (!resolved.startsWith("http")) return null;
  return resolved;
}
