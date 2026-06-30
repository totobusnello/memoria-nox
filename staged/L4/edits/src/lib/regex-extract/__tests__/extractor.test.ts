import { test } from "node:test";
import assert from "node:assert/strict";
import {
  extractEntityRefsRegex,
  extractCodeRefs,
} from "../extractor.js";

// =====================================================================
// POSITIVE — per entity type (16 cases, one per NOX_ENTITY_TYPES entry-ish)
// =====================================================================

test("md-link: feedback entity matches", () => {
  const r = extractEntityRefsRegex("see [no secrets](feedback/no_secrets.md)");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "feedback/no_secrets");
  assert.equal(r[0]?.source, "markdown_link");
  assert.equal(r[0]?.display, "no secrets");
});

test("md-link: with relative ../ prefix", () => {
  const r = extractEntityRefsRegex("[x](../feedback/no_secrets)");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "feedback/no_secrets");
});

test("md-link: with tooltip stripped", () => {
  const r = extractEntityRefsRegex('[x](feedback/foo "my tooltip")');
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "feedback/foo");
});

test("md-link: with #anchor stripped", () => {
  const r = extractEntityRefsRegex("[x](decision/d41#part-2)");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "decision/d41");
});

test("wikilink: person entity matches", () => {
  const r = extractEntityRefsRegex("[[person/toto]]");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.entityType, "person");
  assert.equal(r[0]?.source, "wikilink");
});

test("wikilink: with entities/ prefix", () => {
  const r = extractEntityRefsRegex("[[entities/lesson/foo]]");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "lesson/foo");
});

test("wikilink: with display pipe", () => {
  const r = extractEntityRefsRegex("[[decision/d41|D41 ruling]]");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.display, "D41 ruling");
});

test("wikilink: with #anchor and pipe", () => {
  const r = extractEntityRefsRegex("[[project/p1#scope|P1 scope]]");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "project/p1");
  assert.equal(r[0]?.display, "P1 scope");
});

test("bare-ref: at line start", () => {
  const r = extractEntityRefsRegex("incident/i1 was bad");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "incident/i1");
  assert.equal(r[0]?.source, "bare_ref");
});

test("bare-ref: after whitespace mid-sentence", () => {
  const r = extractEntityRefsRegex("see spec/e15 for details");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "spec/e15");
});

test("bare-ref: at end of sentence", () => {
  const r = extractEntityRefsRegex("the lesson is audit/a1.");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "audit/a1");
});

test("positive: agent entity", () => {
  const r = extractEntityRefsRegex("[[agent/atlas]]");
  assert.equal(r[0]?.entityType, "agent");
});

test("positive: team entity", () => {
  const r = extractEntityRefsRegex("see team/forge");
  assert.equal(r[0]?.entityType, "team");
});

test("positive: daily entity in md-link", () => {
  const r = extractEntityRefsRegex("[log](daily/2026-05-18)");
  assert.equal(r[0]?.entityType, "daily");
});

test("positive: pending entity bare-ref", () => {
  const r = extractEntityRefsRegex("track pending/p1");
  assert.equal(r[0]?.key, "pending/p1");
});

test("positive: graph_node entity", () => {
  const r = extractEntityRefsRegex("[[graph_node/n7]]");
  assert.equal(r[0]?.entityType, "graph_node");
});

test("positive: skill entity", () => {
  const r = extractEntityRefsRegex("[[skill/graphify]]");
  assert.equal(r[0]?.entityType, "skill");
});

test("positive: persona + reference entities both", () => {
  const r = extractEntityRefsRegex("[[persona/toto]] and [[reference/r1]]");
  assert.equal(r.length, 2);
});

// =====================================================================
// DEDUP — multiple forms collapse to one entry
// =====================================================================

test("dedup: same key across md-link + wikilink + bare", () => {
  const r = extractEntityRefsRegex(
    "[x](feedback/foo) and [[feedback/foo]] and feedback/foo here",
  );
  assert.equal(r.length, 1);
  assert.equal(r[0]?.key, "feedback/foo");
});

test("dedup: prefers earlier display from md-link", () => {
  const r = extractEntityRefsRegex("[Name](feedback/foo) and feedback/foo");
  assert.equal(r[0]?.display, "Name");
});

// =====================================================================
// NEGATIVE — 10+ false-positive defenses
// =====================================================================

test("neg: ignores reference inside fenced code", () => {
  const r = extractEntityRefsRegex("```\n[[feedback/foo]]\n```");
  assert.equal(r.length, 0);
});

test("neg: ignores reference inside inline code", () => {
  const r = extractEntityRefsRegex("see `feedback/foo` here");
  assert.equal(r.length, 0);
});

test("neg: ignores URL with /feedback/ path", () => {
  const r = extractEntityRefsRegex("https://example.com/feedback/foo here");
  assert.equal(r.length, 0);
});

test("neg: ignores entity-like word without slash form", () => {
  const r = extractEntityRefsRegex("the feedback was great");
  assert.equal(r.length, 0);
});

test("neg: ignores unknown entity type", () => {
  const r = extractEntityRefsRegex("[[unknown/foo]] and bogus/bar");
  assert.equal(r.length, 0);
});

test("neg: ignores UUID-like token", () => {
  const r = extractEntityRefsRegex("id 550e8400-e29b-41d4-a716-446655440000");
  assert.equal(r.length, 0);
});

test("neg: ignores generic [[file.md]]", () => {
  const r = extractEntityRefsRegex("[[file.md]] generic");
  assert.equal(r.length, 0);
});

test("neg: ignores bare-ref glued to letters (no boundary)", () => {
  const r = extractEntityRefsRegex("xfeedback/foo");
  assert.equal(r.length, 0);
});

test("neg: ignores `feedback/foo` inline code", () => {
  const r = extractEntityRefsRegex("see `feedback/foo`");
  assert.equal(r.length, 0);
});

test("neg: ignores cron schedule '*/15'", () => {
  const r = extractEntityRefsRegex("cron */15 * * * * runs");
  assert.equal(r.length, 0);
});

test("neg: empty content returns []", () => {
  assert.deepEqual(extractEntityRefsRegex(""), []);
});

test("neg: ignores entity-type-only string (no slug)", () => {
  const r = extractEntityRefsRegex("feedback/");
  assert.equal(r.length, 0);
});

// =====================================================================
// EDGE — Unicode + mixed
// =====================================================================

test("edge: slug with hyphens and digits", () => {
  const r = extractEntityRefsRegex("[[spec/e15-codegraph-2026]]");
  assert.equal(r[0]?.slug, "e15-codegraph-2026");
});

test("edge: slug with underscores", () => {
  const r = extractEntityRefsRegex("see feedback/no_secrets_in_git");
  assert.equal(r[0]?.slug, "no_secrets_in_git");
});

test("edge: PT accented surrounding word does not break", () => {
  const r = extractEntityRefsRegex("regra é feedback/no_secrets, certo?");
  assert.equal(r.length, 1);
});

test("edge: multiple distinct entities in one chunk", () => {
  const r = extractEntityRefsRegex(
    "[[feedback/a]] [[feedback/b]] [[decision/c]]",
  );
  assert.equal(r.length, 3);
});

// =====================================================================
// CODE REFS — T5
// =====================================================================

test("code-ref: src/lib/x.ts:42", () => {
  const r = extractCodeRefs("see src/lib/op-audit.ts:42 for details");
  assert.equal(r.length, 1);
  assert.equal(r[0]?.path, "lib/op-audit.ts");
  assert.equal(r[0]?.line, 42);
});

test("code-ref: spec md file", () => {
  const r = extractCodeRefs(
    "specs/2026-05-17-E15-codegraph-inspired-improvements.md is canonical",
  );
  assert.equal(r.length, 1);
  assert.equal(r[0]?.root, "specs");
});

test("code-ref: ignores src/ inside code fence", () => {
  const r = extractCodeRefs("```\nsrc/x.ts:1\n```");
  assert.equal(r.length, 0);
});

test("code-ref: dedupes multiple mentions of same path", () => {
  const r = extractCodeRefs("src/a.ts and src/a.ts again");
  assert.equal(r.length, 1);
});
