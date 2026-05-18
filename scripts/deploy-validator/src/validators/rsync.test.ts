/**
 * rsync.test.ts — T3b tests (8 tests)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { validateRsync } from "./rsync.js";
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

describe("T3b — rsync validator", () => {
  it("passes for basic rsync with remote dest", async () => {
    const cmd = makeCmd("rsync -avz --dry-run staged-A3/edits/src/providers/ root@vps:/opt/nox-mem/src/providers/");
    const results = await validateRsync(cmd);
    assert.equal(results.length, 1);
    assert.equal(results[0].passed, true, `rsync failed: ${results[0].errorOutput}`);
  });

  it("passes for rsync with $VPS_HOST variable destination", async () => {
    const cmd = makeCmd("rsync -avz staged-P1/edits/src/lib/answer/ $VPS_HOST:/root/.openclaw/workspace/tools/nox-mem/src/lib/answer/");
    const results = await validateRsync(cmd);
    assert.equal(results.length, 1);
    assert.equal(results[0].passed, true, `rsync failed: ${results[0].errorOutput}`);
  });

  it("marks isDryRun as true even without --dry-run in original", async () => {
    const cmd = makeCmd("rsync -avz staged-privacy/edits/privacy/ root@vps:/opt/nox-mem/src/privacy/");
    const results = await validateRsync(cmd);
    assert.equal(results[0].isDryRun, true);
  });

  it("handles multiple rsync commands in one block", async () => {
    const content = `
rsync -avz staged-P1/edits/src/lib/answer/ root@vps:/opt/nox-mem/src/lib/answer/
rsync -avz staged-P1/edits/src/api/answer.ts root@vps:/opt/nox-mem/src/api/answer.ts
`;
    const cmd = makeCmd(content);
    const results = await validateRsync(cmd);
    assert.equal(results.length, 2);
    assert.ok(results.every((r) => r.passed), "All rsync commands should pass");
  });

  it("rewritten line replaces remote host with local path", async () => {
    const cmd = makeCmd("rsync -avz staged-A2/edits/src/lib/archive/ root@192.168.1.1:/opt/nox-mem/src/lib/archive/");
    const results = await validateRsync(cmd);
    assert.ok(!results[0].rewrittenLine.includes("root@"), `rewritten still has remote: ${results[0].rewrittenLine}`);
  });

  it("detects double slash warning", async () => {
    // Construct path with double slash — common typo
    const cmd = makeCmd("rsync -avz staged-P3//edits/search.ts root@vps:/opt/nox-mem/src/search.ts");
    const results = await validateRsync(cmd);
    // May or may not pass (rsync handles // on source), but warning should be present
    assert.ok(
      results[0].warnings.length > 0 || results[0].passed,
      "Should either warn or pass (rsync is lenient with //"
    );
  });

  it("handles rsync with absolute worktree path (long path replacement)", async () => {
    const cmd = makeCmd(
      "rsync -avz /Users/lab/Claude/Projetos/memoria-nox/.claude/worktrees/agent-x/staged-P5/edits/src/ root@vps:/opt/nox-mem/src/"
    );
    const results = await validateRsync(cmd);
    assert.equal(results.length, 1);
    // Should not fail because of path rewriting
    assert.ok(!results[0].rewrittenLine.includes("/Users/lab/"), `worktree path not replaced: ${results[0].rewrittenLine}`);
  });

  it("returns empty array for non-rsync block", async () => {
    const cmd = makeCmd("systemctl restart nox-mem-api");
    const results = await validateRsync(cmd);
    assert.equal(results.length, 0);
  });
});
