/**
 * parser.test.ts — T1 tests (8 tests)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { parseMarkdownSource } from "./parser.js";

describe("T1 — parser", () => {
  it("extracts a single bash block", () => {
    const md = `
# Setup

\`\`\`bash
echo hello
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0].language, "bash");
    assert.equal(blocks[0].content.trim(), "echo hello");
    assert.equal(blocks[0].contextHeading, "Setup");
  });

  it("captures correct 1-based line number", () => {
    const md = `line1\nline2\n\`\`\`bash\ncode\n\`\`\``;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks[0].lineNumber, 3);
  });

  it("extracts multiple blocks with different languages", () => {
    const md = `
# Step 1
\`\`\`bash
rsync -avz src/ dest/
\`\`\`

# Step 2
\`\`\`sql
PRAGMA user_version;
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks.length, 2);
    assert.equal(blocks[0].language, "bash");
    assert.equal(blocks[1].language, "sql");
  });

  it("handles empty language tag", () => {
    const md = `
\`\`\`
plain block
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks[0].language, "");
  });

  it("assigns contextHeading from nearest preceding heading", () => {
    const md = `
## Section A
### Sub-section B
\`\`\`bash
ls
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks[0].contextHeading, "Sub-section B");
  });

  it("builds sectionPath with heading hierarchy", () => {
    const md = `
# Top
## Mid
### Deep
\`\`\`bash
cmd
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks[0].sectionPath, "Top > Mid > Deep");
  });

  it("returns empty array for markdown with no code blocks", () => {
    const md = `# Just a heading\n\nSome prose.\n`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks.length, 0);
  });

  it("handles multiline code block content correctly", () => {
    const md = `
\`\`\`bash
export VPS_HOST=root@vps
ssh $VPS_HOST "echo ok"
sqlite3 db.sqlite 'PRAGMA user_version;'
\`\`\`
`;
    const blocks = parseMarkdownSource(md);
    assert.equal(blocks.length, 1);
    const lines = blocks[0].content.split("\n");
    assert.equal(lines.length, 3);
    assert.ok(lines[0].includes("VPS_HOST"));
    assert.ok(lines[2].includes("PRAGMA"));
  });
});
