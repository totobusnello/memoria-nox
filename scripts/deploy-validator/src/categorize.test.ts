/**
 * categorize.test.ts — T2 tests (12 tests)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { categorizeBlock } from "./categorize.js";
import type { CodeBlock } from "./parser.js";

function makeBlock(content: string, heading = "Test"): CodeBlock {
  return {
    lineNumber: 1,
    language: "bash",
    content,
    contextHeading: heading,
    sectionPath: heading,
  };
}

describe("T2 — categorize", () => {
  it("detects rsync command", () => {
    const c = categorizeBlock(makeBlock('rsync -avz staged-A3/edits/src/providers/ $VPS_HOST:/opt/nox-mem/src/providers/'));
    assert.ok(c.types.includes("rsync"), `expected rsync in ${JSON.stringify(c.types)}`);
  });

  it("extracts rsync src and dest meta", () => {
    const c = categorizeBlock(makeBlock('rsync -avz staged-A3/edits/src/providers/ $VPS_HOST:/opt/nox-mem/src/providers/'));
    const rsyncCmd = c.commands.find((cmd) => cmd.type === "rsync");
    assert.ok(rsyncCmd, "no rsync command found");
    assert.ok(rsyncCmd.meta.rsyncSrc?.includes("staged-A3"), `bad rsyncSrc: ${rsyncCmd.meta.rsyncSrc}`);
  });

  it("detects sqlite3 with pipe input", () => {
    const c = categorizeBlock(makeBlock('sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11.sql'));
    assert.ok(c.types.includes("sqlite3"));
    const sqlCmd = c.commands.find((cmd) => cmd.type === "sqlite3");
    assert.ok(sqlCmd?.meta.sqliteInput?.includes("v11.sql"), `bad sqliteInput: ${sqlCmd?.meta.sqliteInput}`);
  });

  it("detects sqlite3 with inline SQL", () => {
    const c = categorizeBlock(makeBlock("sqlite3 ${NM}/nox-mem.db 'PRAGMA user_version;'"));
    assert.ok(c.types.includes("sqlite3"));
    const sqlCmd = c.commands.find((cmd) => cmd.type === "sqlite3");
    assert.ok(sqlCmd?.meta.sqliteInput?.includes("PRAGMA"), `bad sqliteInput: ${sqlCmd?.meta.sqliteInput}`);
  });

  it("detects ssh remote command", () => {
    const c = categorizeBlock(makeBlock('ssh $VPS_HOST "systemctl restart nox-mem-api && sleep 3"'));
    assert.ok(c.types.includes("ssh-remote"));
    const sshCmd = c.commands.find((cmd) => cmd.type === "ssh-remote");
    assert.ok(sshCmd?.meta.sshHost === "$VPS_HOST");
  });

  it("detects systemctl", () => {
    const c = categorizeBlock(makeBlock("systemctl restart nox-mem-api"));
    assert.ok(c.types.includes("systemctl"));
    const sysCmd = c.commands.find((cmd) => cmd.type === "systemctl");
    assert.equal(sysCmd?.meta.systemctlAction, "restart");
    assert.equal(sysCmd?.meta.systemctlUnit, "nox-mem-api");
  });

  it("detects curl with URL", () => {
    const c = categorizeBlock(makeBlock("curl -sf http://127.0.0.1:18802/api/health | jq .status"));
    assert.ok(c.types.includes("curl"));
    const curlCmd = c.commands.find((cmd) => cmd.type === "curl");
    assert.ok(curlCmd?.meta.curlUrl?.includes("18802"), `bad curlUrl: ${curlCmd?.meta.curlUrl}`);
  });

  it("detects chmod perm-op", () => {
    const c = categorizeBlock(makeBlock('chmod 0600 "/var/backups/nox-mem/pre-op/snapshot.db"'));
    assert.ok(c.types.includes("perm-op"));
  });

  it("detects tar archive op", () => {
    const c = categorizeBlock(makeBlock("tar -czf archive.tar.gz -C /tmp nox-mem-archive"));
    assert.ok(c.types.includes("archive"));
  });

  it("flags rm -rf as destructive and sets hasDestructive", () => {
    const c = categorizeBlock(makeBlock("rm -rf ${NM}/src"));
    assert.ok(c.hasDestructive, "expected hasDestructive = true");
    assert.ok(c.types.includes("destructive"));
  });

  it("detects cp -r as file-op", () => {
    const c = categorizeBlock(makeBlock("cp -r ${NM}/src /tmp/src.bak-$(date +%Y%m%d)"));
    assert.ok(c.types.includes("file-op"));
  });

  it("detects mixed block with multiple types", () => {
    const content = `
rsync -avz staged-P1/edits/src/lib/answer/ $VPS_HOST:/opt/nox-mem/src/lib/answer/
ssh $VPS_HOST "systemctl restart nox-mem-api"
curl -sf http://127.0.0.1:18802/api/health
`;
    const c = categorizeBlock(makeBlock(content));
    assert.ok(c.types.includes("rsync"));
    assert.ok(c.types.includes("ssh-remote"));
    assert.ok(c.types.includes("curl"));
  });
});
