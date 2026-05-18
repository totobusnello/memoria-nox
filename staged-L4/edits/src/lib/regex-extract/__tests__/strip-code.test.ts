import { test } from "node:test";
import assert from "node:assert/strict";
import { stripCodeBlocks } from "../strip-code.js";

test("strip: keeps plain prose untouched", () => {
  const { stripped, hadFences } = stripCodeBlocks("Hello [[feedback/x]]");
  assert.equal(stripped, "Hello [[feedback/x]]");
  assert.equal(hadFences, false);
});

test("strip: nukes fenced ``` block but preserves newlines", () => {
  const text = "before\n```ts\n[[feedback/bad]]\n```\nafter";
  const { stripped, hadFences } = stripCodeBlocks(text);
  assert.equal(hadFences, true);
  assert.ok(!stripped.includes("[[feedback/bad]]"));
  assert.equal(stripped.split("\n").length, text.split("\n").length);
});

test("strip: blanks inline `code`", () => {
  const { stripped, hadFences } = stripCodeBlocks("see `feedback/foo` ok");
  assert.equal(hadFences, true);
  assert.ok(!stripped.includes("feedback/foo"));
  assert.equal(stripped.length, "see `feedback/foo` ok".length);
});

test("strip: handles fenced block without language tag", () => {
  const { stripped } = stripCodeBlocks("```\n[[feedback/x]]\n```");
  assert.ok(!stripped.includes("[[feedback/x]]"));
});

test("strip: preserves length character-for-character", () => {
  const text = "a `b` c";
  const { stripped } = stripCodeBlocks(text);
  assert.equal(stripped.length, text.length);
});

test("strip: handles indented 4-space code block", () => {
  const text = "ok\n    [[feedback/x]]\n    more code\nback to prose";
  const { stripped, hadFences } = stripCodeBlocks(text);
  assert.equal(hadFences, true);
  assert.ok(!stripped.includes("[[feedback/x]]"));
});
