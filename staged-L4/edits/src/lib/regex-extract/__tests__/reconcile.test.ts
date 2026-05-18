/**
 * T7 — Tests for stale-link reconciliation (reconcile.ts).
 *
 * 12 tests covering:
 *  - Rename detection
 *  - Auto-rename mode (NOX_L4_AUTO_RENAME=1)
 *  - Stale-mark mode (default)
 *  - Edge cases: multiple renames, circular detection, noop
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  reconcileEntityLinks,
  extractTargetSlugsFromContent,
  detectSlugChange,
  rewriteChunksForRename,
  detectCircularRename,
  STALE_CONFIDENCE,
  STALE_REASON,
  type ReconcilerRelation,
} from "../reconcile.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRel(
  targetSlug: string,
  overrides: Partial<ReconcilerRelation> = {},
): ReconcilerRelation {
  return {
    key: `feedback/src|${targetSlug}|references`,
    sourceSlug: "feedback/src",
    targetSlug,
    relationType: "references",
    extraction_method: "regex",
    confidence: 0.9,
    superseded: false,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// extractTargetSlugsFromContent
// ---------------------------------------------------------------------------

test("extractTargetSlugs: wikilinks extracted", () => {
  const slugs = extractTargetSlugsFromContent("see [[feedback/foo]] and [[decision/d1]]");
  assert.ok(slugs.has("feedback/foo"));
  assert.ok(slugs.has("decision/d1"));
  assert.equal(slugs.size, 2);
});

test("extractTargetSlugs: frontmatter references field included", () => {
  const content = "---\nreferences: [feedback/a, lesson/b]\n---\n\nbody";
  const slugs = extractTargetSlugsFromContent(content);
  assert.ok(slugs.has("feedback/a"));
  assert.ok(slugs.has("lesson/b"));
});

test("extractTargetSlugs: empty content returns empty set", () => {
  const slugs = extractTargetSlugsFromContent("");
  assert.equal(slugs.size, 0);
});

// ---------------------------------------------------------------------------
// detectSlugChange
// ---------------------------------------------------------------------------

test("detectSlugChange: detects slug change via frontmatter", () => {
  const oldContent = "---\nslug: old-slug\n---\n# Old content";
  const newContent = "---\nslug: new-slug\n---\n# New content";
  const result = detectSlugChange(oldContent, newContent);
  assert.equal(result.changed, true);
  assert.equal(result.oldSlug, "old-slug");
  assert.equal(result.newSlug, "new-slug");
});

test("detectSlugChange: no change when slugs match", () => {
  const content = "---\nslug: same\n---\n# Same";
  const result = detectSlugChange(content, content);
  assert.equal(result.changed, false);
});

test("detectSlugChange: falls back to H1 heading when no frontmatter slug", () => {
  const old = "# My Old Title";
  const fresh = "# My New Title";
  const result = detectSlugChange(old, fresh);
  assert.equal(result.changed, true);
  assert.equal(result.oldSlug, "My Old Title");
  assert.equal(result.newSlug, "My New Title");
});

// ---------------------------------------------------------------------------
// reconcileEntityLinks — stale-mark mode (default)
// ---------------------------------------------------------------------------

test("reconcile stale-mark: removed link gets mark_stale action with STALE_CONFIDENCE", () => {
  const existing = [makeRel("decision/d1")];
  // New content no longer references decision/d1.
  const result = reconcileEntityLinks(
    "feedback/src",
    "nothing here",
    existing,
  );
  assert.equal(result.mode, "stale_mark");
  assert.equal(result.removed.length, 1);
  assert.equal(result.removed[0], "decision/d1");
  const action = result.actions.find((a) => a.type === "mark_stale");
  assert.ok(action, "expected mark_stale action");
  if (action?.type === "mark_stale") {
    assert.equal(action.newConfidence, STALE_CONFIDENCE);
    assert.equal(action.supersededReason, STALE_REASON);
  }
});

test("reconcile stale-mark: unchanged link gets noop action", () => {
  const existing = [makeRel("feedback/foo")];
  const result = reconcileEntityLinks(
    "feedback/src",
    "see [[feedback/foo]]",
    existing,
  );
  assert.equal(result.unchanged.length, 1);
  assert.equal(result.actions.find((a) => a.type === "noop")?.targetSlug, "feedback/foo");
});

test("reconcile stale-mark: new link gets add action", () => {
  const result = reconcileEntityLinks(
    "feedback/src",
    "see [[decision/new]]",
    [], // no existing
  );
  assert.equal(result.added.length, 1);
  const addAction = result.actions.find((a) => a.type === "add");
  assert.ok(addAction);
  if (addAction?.type === "add") {
    assert.equal(addAction.targetSlug, "decision/new");
  }
});

test("reconcile stale-mark: gemini relations are NOT touched", () => {
  const existing = [
    makeRel("feedback/gemini-only", { extraction_method: "gemini" }),
    makeRel("decision/regex-link"),
  ];
  // New content only has decision/regex-link; feedback/gemini-only not present.
  const result = reconcileEntityLinks(
    "feedback/src",
    "[[decision/regex-link]]",
    existing,
  );
  // Only the regex relation gets reconciled; gemini relation is invisible to reconciler.
  assert.ok(!result.removed.includes("feedback/gemini-only"), "gemini relation must not be marked stale");
  assert.equal(result.unchanged.includes("decision/regex-link"), true);
});

// ---------------------------------------------------------------------------
// reconcileEntityLinks — auto-rename mode
// ---------------------------------------------------------------------------

test("reconcile auto-rename: emits auto_rename action with old→new slug", () => {
  const existing = [makeRel("feedback/old-slug")];
  const result = reconcileEntityLinks(
    "feedback/src",
    "content with no explicit links",
    existing,
    { autoRename: true, newSlug: "feedback/new-slug" },
  );
  assert.equal(result.mode, "auto_rename");
  const renameAction = result.actions.find((a) => a.type === "auto_rename");
  assert.ok(renameAction, "expected auto_rename action");
  if (renameAction?.type === "auto_rename") {
    assert.equal(renameAction.oldTargetSlug, "feedback/old-slug");
    assert.equal(renameAction.newTargetSlug, "feedback/new-slug");
  }
});

test("reconcile auto-rename: falls back to stale-mark when newSlug not provided", () => {
  const existing = [makeRel("feedback/old")];
  const result = reconcileEntityLinks(
    "feedback/src",
    "no links here",
    existing,
    { autoRename: true }, // no newSlug
  );
  // Without newSlug, even with autoRename=true, mode is stale_mark.
  assert.equal(result.mode, "stale_mark");
  assert.ok(result.actions.find((a) => a.type === "mark_stale"));
});

// ---------------------------------------------------------------------------
// rewriteChunksForRename
// ---------------------------------------------------------------------------

test("rewriteChunks: rewrites wikilink in chunk content", () => {
  const chunks = [{ chunkId: "c1", content: "see [[feedback/old-slug]] here" }];
  const results = rewriteChunksForRename(chunks, "feedback/old-slug", "feedback/new-slug");
  assert.equal(results.length, 1);
  assert.equal(results[0]?.changed, true);
  assert.ok(results[0]?.rewritten.includes("feedback/new-slug"));
  assert.ok(!results[0]?.rewritten.includes("feedback/old-slug"));
});

test("rewriteChunks: identical oldSlug=newSlug returns unchanged", () => {
  const chunks = [{ chunkId: "c1", content: "[[feedback/slug]]" }];
  const results = rewriteChunksForRename(chunks, "feedback/slug", "feedback/slug");
  assert.equal(results[0]?.changed, false);
});

// ---------------------------------------------------------------------------
// detectCircularRename
// ---------------------------------------------------------------------------

test("detectCircularRename: A→B→C no cycle → null", () => {
  const renames = [
    { from: "feedback/a", to: "feedback/b" },
    { from: "feedback/b", to: "feedback/c" },
  ];
  const result = detectCircularRename(renames);
  assert.equal(result, null);
});

test("detectCircularRename: A→B→A cycle detected", () => {
  const renames = [
    { from: "feedback/a", to: "feedback/b" },
    { from: "feedback/b", to: "feedback/a" },
  ];
  const result = detectCircularRename(renames);
  assert.ok(result !== null, "expected cycle error");
  assert.ok(result?.includes("Circular rename detected"));
});
