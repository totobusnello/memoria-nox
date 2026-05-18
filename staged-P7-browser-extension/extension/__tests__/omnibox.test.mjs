/**
 * omnibox.test.mjs — formatOmniboxSuggestion + escapeXml.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { formatOmniboxSuggestion, escapeXml } from "../src/omnibox.js";

test("formatOmniboxSuggestion — title from .title", () => {
  const s = formatOmniboxSuggestion(
    { id: 42, title: "Decision: SQLite vs Postgres" },
    0,
  );
  assert.equal(s.content, "42");
  assert.ok(s.description.includes("Decision: SQLite vs Postgres"));
  assert.ok(s.description.includes("#42"));
});

test("formatOmniboxSuggestion — falls back to snippet → text → 'result'", () => {
  assert.match(
    formatOmniboxSuggestion({ snippet: "foo" }, 0).description,
    /foo/,
  );
  assert.match(
    formatOmniboxSuggestion({ text: "bar" }, 1).description,
    /bar/,
  );
  assert.match(
    formatOmniboxSuggestion({}, 2).description,
    /result/,
  );
});

test("formatOmniboxSuggestion — clips long title to 100 chars", () => {
  const long = "a".repeat(300);
  const s = formatOmniboxSuggestion({ id: 1, title: long }, 0);
  // Description contains the trimmed title (100 chars) + suffix
  assert.ok(s.description.length < long.length);
});

test("formatOmniboxSuggestion — uses URL as content when present", () => {
  const s = formatOmniboxSuggestion(
    { id: 7, title: "X", url: "https://example.com/page" },
    0,
  );
  assert.equal(s.content, "https://example.com/page");
});

test("escapeXml — round trip on all entities", () => {
  assert.equal(
    escapeXml(`<a href="x" foo='bar'>&</a>`),
    "&lt;a href=&quot;x&quot; foo=&apos;bar&apos;&gt;&amp;&lt;/a&gt;",
  );
});
