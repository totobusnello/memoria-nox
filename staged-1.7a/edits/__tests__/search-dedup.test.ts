/**
 * search-dedup.test.ts — unit tests for G12 R3 dedup Layer-4 carve-out
 *
 * Validates the per-row cap selector (_layer4Cap) and the dedupe() pipeline
 * behavior for entity (section != null) vs non-entity (section == null)
 * chunks. NOX_DISABLE_G12_R3=1 rollback path is exercised via separate
 * describe-block with module re-import.
 *
 * Run with: node --test (node:test runner, TS via tsx/ts-node)
 *
 * Cross-link: staged-1.7a/edits/search-dedup.ts
 * Audit: audits/2026-05-21-G12-frontmatter-retrieval-audit.md §6 R3
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import type { SearchResult } from "../search.js";

// ── Helpers ───────────────────────────────────────────────────────────────────

function mkResult(
  overrides: Partial<SearchResult> & { source_file: string; chunk_text: string },
): SearchResult {
  return {
    id: undefined,
    score: 0.5,
    chunk_type: "memory",
    source_date: null,
    section: null,
    pain: null,
    importance: null,
    source_type: null,
    ...overrides,
  };
}

// Re-import dedup with env override. Each describe block sets NOX_DISABLE_G12_R3
// BEFORE the import; cache-bust via query param so module-load const is fresh.
async function importDedup(envOverrides: Record<string, string | undefined>): Promise<
  typeof import("../search-dedup.js")
> {
  const originals: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(envOverrides)) {
    originals[k] = process.env[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  const cacheBust = `?t=${Date.now()}&r=${Math.random()}`;
  const mod = await import(`../search-dedup.js${cacheBust}`);
  // Restore env after import (module already captured DISABLE_G12_R3)
  for (const [k, v] of Object.entries(originals)) {
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  return mod;
}

// ── Tests — default G12 R3 active (env unset) ─────────────────────────────────

describe("dedup Layer-4 carve-out — G12 R3 active (default)", () => {
  test("entity chunk (section=compiled) uses cap=3", async () => {
    const { _layer4Cap, _internals } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    assert.equal(_internals.MAX_PER_FILE_FINAL_ENTITY, 3);
    assert.equal(_layer4Cap({ section: "compiled" }), 3);
    assert.equal(_layer4Cap({ section: "frontmatter" }), 3);
    assert.equal(_layer4Cap({ section: "timeline" }), 3);
  });

  test("non-entity chunk (section=null) uses cap=2", async () => {
    const { _layer4Cap } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    assert.equal(_layer4Cap({ section: null }), 2);
    assert.equal(_layer4Cap({ section: undefined }), 2);
  });

  test("dedupe() keeps 3 entity chunks from same source_file", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    const results: SearchResult[] = [
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana frontmatter A", section: "frontmatter", score: 0.9 }),
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana compiled B", section: "compiled", score: 0.8 }),
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana timeline C", section: "timeline", score: 0.7 }),
      mkResult({ source_file: "memory/foo.md", chunk_text: "filler", chunk_type: "lesson", score: 0.6 }),
    ];
    const final = dedupe(results, 10);
    const fromAna = final.filter((r) => r.source_file === "memory/entities/people/ana.md");
    assert.equal(fromAna.length, 3, "all 3 entity chunks from ana.md should survive Layer 4");
  });

  test("dedupe() caps non-entity chunks at 2 from same source_file", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    // Use distinct chunk_types to bypass Layer 3 type saturation
    const results: SearchResult[] = [
      mkResult({ source_file: "memory/notes/log.md", chunk_text: "log entry one alpha beta gamma", chunk_type: "lesson", score: 0.9 }),
      mkResult({ source_file: "memory/notes/log.md", chunk_text: "log entry two delta epsilon zeta", chunk_type: "decision", score: 0.8 }),
      mkResult({ source_file: "memory/notes/log.md", chunk_text: "log entry three eta theta iota", chunk_type: "code", score: 0.7 }),
    ];
    const final = dedupe(results, 10);
    assert.equal(final.length, 2, "non-entity source_file capped at MAX_PER_FILE_FINAL=2");
  });

  test("dedupe() mixed entity + non-entity respects per-row cap", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    // Different chunk_types to bypass Layer 3 saturation; padding from third file.
    const results: SearchResult[] = [
      mkResult({ source_file: "entity-a.md", chunk_text: "entity a frontmatter", section: "frontmatter", chunk_type: "memory", score: 0.95 }),
      mkResult({ source_file: "entity-a.md", chunk_text: "entity a compiled", section: "compiled", chunk_type: "lesson", score: 0.90 }),
      mkResult({ source_file: "entity-a.md", chunk_text: "entity a timeline", section: "timeline", chunk_type: "decision", score: 0.85 }),
      mkResult({ source_file: "regular.md", chunk_text: "regular doc chunk one", chunk_type: "code", score: 0.80 }),
      mkResult({ source_file: "regular.md", chunk_text: "regular doc chunk two", chunk_type: "memory", score: 0.75 }),
      mkResult({ source_file: "regular.md", chunk_text: "regular doc chunk three", chunk_type: "feedback", score: 0.70 }),
      mkResult({ source_file: "filler.md", chunk_text: "filler one", chunk_type: "project", score: 0.65 }),
      mkResult({ source_file: "filler.md", chunk_text: "filler two", chunk_type: "reference", score: 0.60 }),
    ];
    const final = dedupe(results, 20);
    const fromEntity = final.filter((r) => r.source_file === "entity-a.md");
    const fromRegular = final.filter((r) => r.source_file === "regular.md");
    assert.equal(fromEntity.length, 3, "entity-a.md keeps 3 sections under G12 R3");
    assert.equal(fromRegular.length, 2, "regular.md still capped at 2");
  });
});

// ── Tests — G12 R3 disabled (env=1) ───────────────────────────────────────────

describe("dedup Layer-4 carve-out — G12 R3 disabled (rollback)", () => {
  test("entity chunk falls back to cap=2 when NOX_DISABLE_G12_R3=1", async () => {
    const { _layer4Cap, _internals } = await importDedup({ NOX_DISABLE_G12_R3: "1" });
    assert.equal(_internals.DISABLE_G12_R3, true);
    assert.equal(_layer4Cap({ section: "compiled" }), 2, "rollback: section=compiled now cap=2");
    assert.equal(_layer4Cap({ section: "frontmatter" }), 2);
    assert.equal(_layer4Cap({ section: null }), 2);
  });

  test("dedupe() rollback: entity caps at 2 like pre-R3", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: "1" });
    // Use distinct chunk_types to bypass Layer 3 saturation
    const results: SearchResult[] = [
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana frontmatter A", section: "frontmatter", chunk_type: "memory", score: 0.9 }),
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana compiled B", section: "compiled", chunk_type: "lesson", score: 0.8 }),
      mkResult({ source_file: "memory/entities/people/ana.md", chunk_text: "ana timeline C", section: "timeline", chunk_type: "decision", score: 0.7 }),
    ];
    const final = dedupe(results, 10);
    const fromAna = final.filter((r) => r.source_file === "memory/entities/people/ana.md");
    assert.equal(fromAna.length, 2, "rollback drops 3rd entity chunk (cap=2)");
  });
});

// ── Tests — edge cases ────────────────────────────────────────────────────────

describe("dedup Layer-4 carve-out — edges", () => {
  test("empty results returns empty", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    assert.deepEqual(dedupe([], 5), []);
  });

  test("limit cap honored before per-file cap", async () => {
    const { dedupe } = await importDedup({ NOX_DISABLE_G12_R3: undefined });
    // 5 entity chunks but limit=2 → should stop at 2
    const results: SearchResult[] = [
      mkResult({ source_file: "x.md", chunk_text: "one", section: "compiled", score: 0.9 }),
      mkResult({ source_file: "x.md", chunk_text: "two", section: "frontmatter", chunk_type: "lesson", score: 0.85 }),
      mkResult({ source_file: "x.md", chunk_text: "three", section: "timeline", chunk_type: "decision", score: 0.80 }),
    ];
    const final = dedupe(results, 2);
    assert.equal(final.length, 2);
  });
});
