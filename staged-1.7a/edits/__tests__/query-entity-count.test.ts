/**
 * query-entity-count.test.ts — unit tests for G10d entity detection
 *
 * Uses better-sqlite3 in-memory DB to isolate from VPS state.
 * Run with: node --test (node:test runner, TS via tsx/ts-node)
 *
 * Cross-link: staged-1.7a/edits/query-entity-count.ts
 * Spec: specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md §3
 */

import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import {
  countQueryEntities,
  clearQueryEntityCache,
  type QueryEntityCountResult,
} from "../query-entity-count.js";

// ── Fixture helpers ───────────────────────────────────────────────────────────

function makeFixtureDb(): Database.Database {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE kg_entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      entity_type TEXT
    );
    INSERT INTO kg_entities (name, entity_type) VALUES
      ('Toto', 'person'),
      ('Fundo Lombardia', 'organization'),
      ('Galapagos Capital', 'organization'),
      ('Granix', 'organization'),
      ('nox-mem', 'project'),
      ('Nuvini', 'organization'),
      ('FII Treviso', 'organization');
  `);
  return db;
}

function makeEmptyKgDb(): Database.Database {
  const db = new Database(":memory:");
  db.exec("CREATE TABLE kg_entities (id INTEGER PRIMARY KEY, name TEXT, entity_type TEXT)");
  return db;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("countQueryEntities — KG lookup (Option B)", () => {
  beforeEach(() => clearQueryEntityCache());

  // Test 1 — zero entities
  test("zero entities — query with no KG names", () => {
    const db = makeFixtureDb();
    const result = countQueryEntities("what is happening today", db);
    assert.equal(result.count, 0);
    assert.equal(result.method, "kg_lookup");
    assert.deepEqual(result.matchedEntities, []);
  });

  // Test 2 — one entity (single-hop query)
  test("one entity — single-hop query", () => {
    const db = makeFixtureDb();
    const result = countQueryEntities("what is Toto's current role", db);
    assert.equal(result.count, 1);
    assert.equal(result.method, "kg_lookup");
    assert.ok(result.matchedEntities.includes("toto"));
  });

  // Test 3 — two entities (multi-hop query)
  test("two entities — multi-hop query", () => {
    const db = makeFixtureDb();
    const result = countQueryEntities(
      "how does Toto interact with Fundo Lombardia",
      db,
    );
    assert.equal(result.count, 2);
    assert.equal(result.method, "kg_lookup");
    assert.ok(result.matchedEntities.includes("toto"));
    assert.ok(result.matchedEntities.includes("fundo lombardia"));
  });

  // Test 4 — three entities (compound query)
  test("three entities — compound multi-hop query", () => {
    const db = makeFixtureDb();
    const result = countQueryEntities(
      "what is the relationship between Toto Fundo Lombardia and Galapagos Capital",
      db,
    );
    assert.equal(result.count, 3);
    assert.equal(result.method, "kg_lookup");
  });

  // Test 5 — dedup: same entity mentioned twice → count = 1
  test("same entity twice — deduped to count=1", () => {
    const db = makeFixtureDb();
    // "Granix" appears twice, should count as 1 matched entity
    const result = countQueryEntities(
      "what does Granix do and how does Granix make money",
      db,
    );
    assert.equal(result.count, 1);
    assert.equal(result.matchedEntities.length, 1);
  });

  // Test 6 — case-insensitive match
  test("case-insensitive — 'toto' matches 'Toto' in KG", () => {
    const db = makeFixtureDb();
    const result = countQueryEntities("what does toto do at nuvini", db);
    assert.equal(result.count, 2); // toto + nuvini
    assert.equal(result.method, "kg_lookup");
  });

  // Test 7 — greedy longest-match: "Fundo Lombardia" counts as 1 not 2
  test("greedy longest-match — Fundo Lombardia = 1 entity", () => {
    const db = makeFixtureDb();
    // Add standalone "Fundo" entity to test that longest-match wins
    db.prepare("INSERT INTO kg_entities (name, entity_type) VALUES (?, ?)").run(
      "Fundo",
      "organization",
    );
    clearQueryEntityCache(); // force index reload after insert

    const result = countQueryEntities("Fundo Lombardia performance in 2026", db);
    // Should match "Fundo Lombardia" (longest) and consume it,
    // leaving "Fundo" unable to match the already-consumed span.
    assert.equal(result.count, 1);
    assert.ok(result.matchedEntities.includes("fundo lombardia"));
  });

  // Test 8 — cache hit returns same object reference
  test("cache hit — second call returns same result", () => {
    const db = makeFixtureDb();
    const first = countQueryEntities("Toto at Granix", db);
    const second = countQueryEntities("Toto at Granix", db);
    // Same Map entry — reference equality
    assert.equal(first, second);
    assert.equal(first.count, 2);
  });

  // Test 9 — PascalCase fallback when KG empty
  test("PascalCase fallback — KG empty returns regex-based count", () => {
    const db = makeEmptyKgDb();
    const result = countQueryEntities(
      "What does Toto think about Granix strategy",
      db,
    );
    // Regex fallback detects PascalCase tokens: "What", "Toto", "Granix"
    // Note: "What" is a false positive — acceptable per spec (conservative fallback)
    assert.equal(result.method, "fallback_regex");
    // At minimum Toto and Granix should be detected
    assert.ok(result.count >= 2);
  });

  // Test 10 — empty KG returns 0 for all-lowercase query
  test("empty KG + lowercase query — count=0, fallback_regex", () => {
    const db = makeEmptyKgDb();
    const result = countQueryEntities("what is happening", db);
    assert.equal(result.method, "fallback_regex");
    assert.equal(result.count, 0);
  });

  // Test 11 — ambiguous title-case NOT in KG returns 0 (via KG path)
  test("title-case NOT in KG — kg_lookup returns 0 (no false positives)", () => {
    const db = makeFixtureDb();
    // "How", "Does", "It", "Work" are title-case but not in kg_entities
    const result = countQueryEntities("How Does It Work", db);
    assert.equal(result.count, 0);
    assert.equal(result.method, "kg_lookup");
  });

  // Test 12 — cache bypass via cacheable=false
  test("cacheable=false — skips cache, result not stored", () => {
    const db = makeFixtureDb();
    const r1 = countQueryEntities("Toto at Nuvini", db, { cacheable: false });
    const r2 = countQueryEntities("Toto at Nuvini", db, { cacheable: false });
    // Two distinct objects (not same reference) since cache was bypassed
    assert.notEqual(r1, r2);
    assert.equal(r1.count, r2.count); // same result, different instance
  });
});

describe("QueryEntityCountResult interface", () => {
  beforeEach(() => clearQueryEntityCache());

  test("result shape has count, matchedEntities, method", () => {
    const db = makeFixtureDb();
    const result: QueryEntityCountResult = countQueryEntities("Toto", db);
    assert.ok(typeof result.count === "number");
    assert.ok(Array.isArray(result.matchedEntities));
    assert.ok(result.method === "kg_lookup" || result.method === "fallback_regex");
  });
});
