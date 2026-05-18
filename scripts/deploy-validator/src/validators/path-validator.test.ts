/**
 * path-validator.test.ts — T3d tests (8 tests)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validatePaths } from "./path-validator.js";
import { categorizeBlock } from "../categorize.js";
import type { CodeBlock } from "../parser.js";

function makeCmd(content: string) {
  const block: CodeBlock = {
    lineNumber: 1,
    language: "bash",
    content,
    contextHeading: "Test",
    sectionPath: "Test",
  };
  return categorizeBlock(block);
}

describe("T3d — path-validator", () => {
  it("passes for clean rsync command", () => {
    const cmd = makeCmd("rsync -avz staged-A3/edits/src/providers/ $VPS_HOST:/opt/nox-mem/src/providers/");
    const r = validatePaths(cmd);
    // VPS_HOST is a known var
    const realIssues = r.issues.filter((i) => i.kind !== "worktree-path-leaked");
    assert.ok(realIssues.length === 0 || r.passed, `unexpected issues: ${JSON.stringify(realIssues)}`);
  });

  it("detects double slash in path", () => {
    const cmd = makeCmd("rsync -avz staged-A3//edits/src/ $VPS_HOST:/opt/nox-mem/src/");
    const r = validatePaths(cmd);
    const hasDoubleSlash = r.issues.some((i) => i.kind === "double-slash");
    assert.ok(hasDoubleSlash, "Expected double-slash issue");
    assert.equal(r.passed, false);
  });

  it("flags worktree-leaked path", () => {
    const cmd = makeCmd(
      "rsync -avz /Users/lab/.claude/worktrees/agent-abc123/staged-P5/edits/src/ $VPS_HOST:/opt/src/"
    );
    const r = validatePaths(cmd);
    const hasWorktree = r.issues.some((i) => i.kind === "worktree-path-leaked");
    assert.ok(hasWorktree, "Expected worktree-path-leaked issue");
  });

  it("passes for known env vars (VPS_HOST, NM)", () => {
    const cmd = makeCmd('ssh $VPS_HOST "cd ${NM} && npm run build"');
    const r = validatePaths(cmd);
    const unknownVars = r.issues.filter((i) => i.kind === "undefined-var");
    assert.equal(unknownVars.length, 0, `Unexpected undefined-var issues: ${JSON.stringify(unknownVars)}`);
  });

  it("flags unknown uppercase var", () => {
    const cmd = makeCmd("rsync -avz staged-P1/ $UNKNOWN_HOST:/opt/nox-mem/");
    const r = validatePaths(cmd);
    const unknownVars = r.issues.filter((i) => i.kind === "undefined-var");
    assert.ok(unknownVars.length > 0, "Expected undefined-var for UNKNOWN_HOST");
    assert.ok(unknownVars[0].message.includes("UNKNOWN_HOST"));
  });

  it("passes for sqlite3 with known NM path var", () => {
    const cmd = makeCmd("sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'");
    const r = validatePaths(cmd);
    const criticalIssues = r.issues.filter(
      (i) => i.kind === "double-slash" || i.kind === "undefined-var"
    );
    assert.equal(criticalIssues.length, 0, `Unexpected issues: ${JSON.stringify(criticalIssues)}`);
  });

  it("skips comment lines", () => {
    const cmd = makeCmd("# This is a comment\n# $UNDEFINED_VAR used here\necho ok");
    const r = validatePaths(cmd);
    const unknownVars = r.issues.filter((i) => i.kind === "undefined-var");
    assert.equal(unknownVars.length, 0, "Comment lines should not be checked for undefined vars");
  });

  it("passes for curl to localhost:18802", () => {
    const cmd = makeCmd("curl -sf http://127.0.0.1:18802/api/health | jq .status");
    const r = validatePaths(cmd);
    const criticalIssues = r.issues.filter(
      (i) => i.kind === "double-slash" || i.kind === "undefined-var"
    );
    assert.equal(criticalIssues.length, 0, `Issues: ${JSON.stringify(criticalIssues)}`);
  });
});
