/**
 * bash-syntax.test.ts — T3a tests (6 tests)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { checkBashSyntax } from "./bash-syntax.js";
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

describe("T3a — bash-syntax", () => {
  it("passes for valid bash", () => {
    const r = checkBashSyntax(makeCmd('rsync -avz src/ dest/\necho "done"'));
    assert.equal(r.passed, true, `Should pass: ${r.errorOutput}`);
  });

  it("fails for unmatched quote", () => {
    const r = checkBashSyntax(makeCmd('echo "unclosed quote'));
    assert.equal(r.passed, false, "Expected syntax error for unclosed quote");
    assert.ok(r.exitCode !== 0);
  });

  it("fails for missing fi (unclosed if block)", () => {
    // A missing `fi` is a reliable bash -n syntax error
    const r = checkBashSyntax(makeCmd("if [ 1 -eq 1 ]; then\n  echo yes\n# fi is missing"));
    assert.equal(r.passed, false, "Expected syntax error for missing fi");
  });

  it("passes for complex valid heredoc-style command", () => {
    const content = `
export VPS_HOST="root@example.com"
ssh "$VPS_HOST" "
  set -euo pipefail
  echo hello
"
`;
    const r = checkBashSyntax(makeCmd(content));
    assert.equal(r.passed, true, `Should pass: ${r.errorOutput}`);
  });

  it("passes for multiline rsync + systemctl", () => {
    const content = `
rsync -avz --dry-run staged-P1/edits/src/lib/ dest/src/lib/
ssh root@vps "systemctl restart nox-mem-api && sleep 3"
`;
    const r = checkBashSyntax(makeCmd(content));
    assert.equal(r.passed, true, `Should pass: ${r.errorOutput}`);
  });

  it("returns errorOutput for failed syntax check", () => {
    const r = checkBashSyntax(makeCmd('function {'));
    assert.equal(r.passed, false);
    assert.ok(typeof r.errorOutput === "string");
    assert.ok(r.errorOutput.length > 0, "Expected error output for bad syntax");
  });
});
