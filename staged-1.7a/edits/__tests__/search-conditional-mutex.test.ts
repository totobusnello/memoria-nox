/**
 * search-conditional-mutex.test.ts — G10d conditional Hard Mutex tests
 *
 * Tests the sourceTypeDelta function with the G10d conditional layer,
 * extracted via _internals for unit-testability without spinning up the
 * full search stack.
 *
 * Pattern: tests import _internals.sourceTypeDelta directly.
 * Env flags are set BEFORE module import (module-load snapshot pattern).
 *
 * Cross-link: staged-1.7a/edits/search.ts — sourceTypeDelta implementation
 * Spec: specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md §4 Step 2
 */

import { test, describe, before, after } from "node:test";
import assert from "node:assert/strict";

// ── Helper: fresh import with env override ────────────────────────────────────
//
// search.ts captures env flags at module-load time via const DISABLE_X = ...
// To test different flag combinations we use dynamic import with cache-busting.
// Each describe block sets env BEFORE the import and restores after.

async function importWithEnv(
  envOverrides: Record<string, string | undefined>,
): Promise<typeof import("../search.js")> {
  const originals: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(envOverrides)) {
    originals[k] = process.env[k];
    if (v === undefined) {
      delete process.env[k];
    } else {
      process.env[k] = v;
    }
  }

  // Cache-bust by appending a random query param (ESM import cache keyed by URL)
  const cacheBust = `?t=${Date.now()}&r=${Math.random()}`;
  const mod = await import(`../search.js${cacheBust}`);

  // Restore
  for (const [k, v] of Object.entries(originals)) {
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }

  return mod;
}

// ── Default-env tests (threshold=1, conditional=enabled) ─────────────────────
//
// These tests call sourceTypeDelta via _internals using the module already
// loaded with default env. We verify the G10d conditional behaviour.

describe("sourceTypeDelta — G10d conditional mutex (default env: threshold=1)", () => {
  let sourceTypeDelta: (
    sourceType: string | null | undefined,
    section: string | null | undefined,
    queryEntityCount?: number,
  ) => number;

  before(async () => {
    // Clear relevant env so module loads with defaults
    const mod = await importWithEnv({
      NOX_DISABLE_CONDITIONAL_MUTEX: undefined,
      NOX_MUTEX_QUERY_ENTITY_THRESHOLD: undefined,
      NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE: undefined,
      NOX_DISABLE_SOURCE_TYPE_BOOST: undefined,
      NOX_DISABLE_SECTION_BOOST: undefined,
    });
    sourceTypeDelta = mod._internals.sourceTypeDelta;
  });

  // Test 1 — queryEntityCount=0 → mutex active (count ≤ threshold=1)
  test("queryEntityCount=0 → mutex active, returns 0", () => {
    // entity + compiled: mutex should suppress source_type boost
    const delta = sourceTypeDelta("entity", "compiled", 0);
    assert.equal(delta, 0, "mutex active for count=0 (≤ threshold 1)");
  });

  // Test 2 — queryEntityCount=1 → mutex active (count ≤ threshold=1, G10 behaviour)
  test("queryEntityCount=1 → mutex active, returns 0 (current G10 behaviour)", () => {
    const delta = sourceTypeDelta("entity", "compiled", 1);
    assert.equal(delta, 0, "mutex active for count=1 (≤ threshold 1)");
  });

  // Test 3 — queryEntityCount=2 → mutex disabled (G10d new behaviour)
  test("queryEntityCount=2 → mutex disabled, returns source_type delta", () => {
    // entity has factor=2.0, so delta = 2.0 - 1.0 = 1.0
    const delta = sourceTypeDelta("entity", "compiled", 2);
    assert.equal(delta, 1.0, "mutex bypassed for count=2 (> threshold 1)");
  });

  // Test 4 — queryEntityCount=5 → mutex disabled (any count > threshold)
  test("queryEntityCount=5 → mutex disabled, preserves chain traversal", () => {
    const delta = sourceTypeDelta("entity", "compiled", 5);
    assert.equal(delta, 1.0, "mutex bypassed for count=5 (> threshold 1)");
  });

  // Test 5 — null section → mutex never applies (section guard fails)
  test("entity + null section + count=1 → mutex N/A, returns delta", () => {
    // Mutex requires section to be in SECTION_BOOST; null section skips mutex entirely
    const delta = sourceTypeDelta("entity", null, 1);
    assert.equal(delta, 1.0, "no mutex when section is null");
  });

  // Test 6 — unknown section → mutex never applies
  test("entity + unknown-section + count=1 → mutex N/A, returns delta", () => {
    const delta = sourceTypeDelta("entity", "unknown-section-xyz", 1);
    assert.equal(delta, 1.0, "no mutex for section not in SECTION_BOOST");
  });

  // Test 7 — frontmatter section (also in SECTION_BOOST) → same conditional logic
  test("entity + frontmatter section + count=2 → mutex bypassed", () => {
    const delta = sourceTypeDelta("entity", "frontmatter", 2);
    assert.equal(delta, 1.0, "mutex bypassed for count=2 on frontmatter section");
  });

  // Test 8 — non-entity source_type with section + count=1 → mutex applies
  test("lesson + compiled + count=1 → mutex active (lesson factor=1.8)", () => {
    const delta = sourceTypeDelta("lesson", "compiled", 1);
    assert.equal(delta, 0, "mutex active for lesson+compiled+count=1");
  });

  // Test 9 — default queryEntityCount (no arg) → behaves as count=0 → mutex active
  test("no queryEntityCount arg → default=0, mutex active", () => {
    const delta = sourceTypeDelta("entity", "compiled");
    assert.equal(delta, 0, "default count=0 preserves backward-compat mutex");
  });
});

// ── NOX_DISABLE_CONDITIONAL_MUTEX=1 → Hard Mutex always-on ───────────────────

describe("sourceTypeDelta — NOX_DISABLE_CONDITIONAL_MUTEX=1 (hard mutex always-on)", () => {
  let sourceTypeDelta: (
    sourceType: string | null | undefined,
    section: string | null | undefined,
    queryEntityCount?: number,
  ) => number;

  before(async () => {
    const mod = await importWithEnv({
      NOX_DISABLE_CONDITIONAL_MUTEX: "1",
      NOX_MUTEX_QUERY_ENTITY_THRESHOLD: undefined,
      NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE: undefined,
      NOX_DISABLE_SOURCE_TYPE_BOOST: undefined,
      NOX_DISABLE_SECTION_BOOST: undefined,
    });
    sourceTypeDelta = mod._internals.sourceTypeDelta;
  });

  // Test 10 — DISABLE_CONDITIONAL_MUTEX=1 + count=5 → mutex still active
  test("count=5 with DISABLE_CONDITIONAL_MUTEX=1 → hard mutex active, returns 0", () => {
    const delta = sourceTypeDelta("entity", "compiled", 5);
    assert.equal(delta, 0, "conditional disabled: hard mutex always-on regardless of count");
  });

  // Test 11 — count=2, DISABLE_CONDITIONAL_MUTEX=1 → mutex active (reverts G10)
  test("count=2 with DISABLE_CONDITIONAL_MUTEX=1 → reverts to G10 hard mutex", () => {
    const delta = sourceTypeDelta("entity", "compiled", 2);
    assert.equal(delta, 0, "hard mutex applies even for multi-entity query");
  });
});

// ── NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2 → threshold tunable ───────────────────

describe("sourceTypeDelta — NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2 (threshold tuning)", () => {
  let sourceTypeDelta: (
    sourceType: string | null | undefined,
    section: string | null | undefined,
    queryEntityCount?: number,
  ) => number;

  before(async () => {
    const mod = await importWithEnv({
      NOX_DISABLE_CONDITIONAL_MUTEX: undefined,
      NOX_MUTEX_QUERY_ENTITY_THRESHOLD: "2",
      NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE: undefined,
      NOX_DISABLE_SOURCE_TYPE_BOOST: undefined,
      NOX_DISABLE_SECTION_BOOST: undefined,
    });
    sourceTypeDelta = mod._internals.sourceTypeDelta;
  });

  // Test 12 — threshold=2: count=1 → mutex active
  test("count=1 with threshold=2 → mutex active", () => {
    const delta = sourceTypeDelta("entity", "compiled", 1);
    assert.equal(delta, 0, "count=1 ≤ threshold=2: mutex active");
  });

  // Test 13 — threshold=2: count=2 → mutex active (≤ threshold)
  test("count=2 with threshold=2 → mutex still active (≤ threshold)", () => {
    const delta = sourceTypeDelta("entity", "compiled", 2);
    assert.equal(delta, 0, "count=2 ≤ threshold=2: mutex active");
  });

  // Test 14 — threshold=2: count=3 → mutex disabled (> threshold)
  test("count=3 with threshold=2 → mutex disabled (> threshold)", () => {
    const delta = sourceTypeDelta("entity", "compiled", 3);
    assert.equal(delta, 1.0, "count=3 > threshold=2: mutex bypassed");
  });
});

// ── NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1 → entire mutex off ────────────────

describe("sourceTypeDelta — NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1 (Tier 2 rollback)", () => {
  let sourceTypeDelta: (
    sourceType: string | null | undefined,
    section: string | null | undefined,
    queryEntityCount?: number,
  ) => number;

  before(async () => {
    const mod = await importWithEnv({
      NOX_DISABLE_CONDITIONAL_MUTEX: undefined,
      NOX_MUTEX_QUERY_ENTITY_THRESHOLD: undefined,
      NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE: "1",
      NOX_DISABLE_SOURCE_TYPE_BOOST: undefined,
      NOX_DISABLE_SECTION_BOOST: undefined,
    });
    sourceTypeDelta = mod._internals.sourceTypeDelta;
  });

  after(() => {
    delete process.env.NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE;
  });

  // Test 15 — Tier 2 rollback: mutex off entirely, count=1 → delta returned
  test("DISABLE_MUTEX=1 + count=1 → entire mutex off, returns source_type delta", () => {
    const delta = sourceTypeDelta("entity", "compiled", 1);
    assert.equal(delta, 1.0, "Tier 2 rollback: mutex disabled, source_type delta restored");
  });
});
