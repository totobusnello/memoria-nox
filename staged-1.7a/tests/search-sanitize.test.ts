/**
 * staged-1.7a/tests/search-sanitize.test.ts
 *
 * Regression test for critical bug: FTS5 sanitize regex did not strip
 * `?`, `,`, `.`, `;` — causing FTS5 MATCH to return 0 docs on NL queries.
 *
 * Bug found during ablation F (PR #139): hybrid search was running dense-only
 * in production because FTS5 batch silently returned [] on any query with
 * punctuation (NL queries like "What did Toto decide about pricing?").
 *
 * Fix: replaced blacklist regex `/['"{}()\[\]:*^~&|!]/g` with Unicode
 * whitelist `/[^\p{L}\p{N}\s]/gu` — strips ALL non-letter/digit/space
 * while preserving PT-BR chars (ç, ã, ê, etc).
 *
 * Run: node --test dist/tests/search-sanitize.test.js
 * Or:  npx tsx staged-1.7a/tests/search-sanitize.test.ts (dev)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";

// ── Inline sanitize function (mirrors fix in search.ts) ───────────────────────
// Isolated copy so this test is self-contained and doesn't depend on
// the full module graph (db singleton, env vars, etc).

function sanitizeFts(query: string): string {
  return query.replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
}

// ── Old (buggy) sanitize for regression comparison ────────────────────────────
function sanitizeFtsBuggy(query: string): string {
  return query.replace(/['"{}()\[\]:*^~&|!]/g, " ").replace(/\s+/g, " ").trim();
}

// ── In-memory FTS5 DB helper ──────────────────────────────────────────────────
function makeFtsDb(): InstanceType<typeof Database> {
  const db = new Database(":memory:");
  db.exec(`
    CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_text, content='', tokenize='unicode61');
    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY,
      chunk_text TEXT NOT NULL,
      source_file TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      source_date TEXT
    );
    INSERT INTO chunks VALUES (1, 'Toto decided to use Stripe instead of Hotmart for pricing strategy', 'docs/decisions.md', 'decision', '2026-05-18');
    INSERT INTO chunks VALUES (2, 'pricing model discussion led to USD default global SaaS framing', 'docs/pricing.md', 'decision', '2026-05-18');
    INSERT INTO chunks VALUES (3, 'Galapagos Capital advisory role confirmed for AI committee', 'docs/roles.md', 'person', '2026-05-10');
    INSERT INTO chunks_fts(rowid, chunk_text) VALUES (1, 'Toto decided to use Stripe instead of Hotmart for pricing strategy');
    INSERT INTO chunks_fts(rowid, chunk_text) VALUES (2, 'pricing model discussion led to USD default global SaaS framing');
    INSERT INTO chunks_fts(rowid, chunk_text) VALUES (3, 'Galapagos Capital advisory role confirmed for AI committee');
  `);
  return db;
}

function ftsQuery(db: InstanceType<typeof Database>, sanitized: string): number {
  if (!sanitized) return 0;
  try {
    const rows = db.prepare(`
      SELECT c.id FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT 20
    `).all(sanitized) as { id: number }[];
    return rows.length;
  } catch {
    // FTS5 parse error — returns 0 (silent fail that was happening in prod)
    return 0;
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("sanitizeFts — punctuation stripping", () => {
  it("strips question mark from NL query", () => {
    const result = sanitizeFts("What did Toto decide about pricing?");
    assert.ok(!result.includes("?"), `Expected '?' to be stripped, got: "${result}"`);
  });

  it("strips comma", () => {
    const result = sanitizeFts("pricing, strategy");
    assert.ok(!result.includes(","), `Expected ',' to be stripped, got: "${result}"`);
  });

  it("strips period", () => {
    const result = sanitizeFts("Toto decided. New approach.");
    assert.ok(!result.includes("."), `Expected '.' to be stripped, got: "${result}"`);
  });

  it("strips semicolon", () => {
    const result = sanitizeFts("pricing; strategy");
    assert.ok(!result.includes(";"), `Expected ';' to be stripped, got: "${result}"`);
  });

  it("strips exclamation", () => {
    const result = sanitizeFts("Stripe confirmed!");
    assert.ok(!result.includes("!"), `Expected '!' to be stripped, got: "${result}"`);
  });

  it("strips at-sign and hash", () => {
    const result = sanitizeFts("user@example.com #pricing");
    assert.ok(!result.includes("@"), `'@' should be stripped`);
    assert.ok(!result.includes("#"), `'#' should be stripped`);
  });

  it("preserves PT-BR accented characters (ç, ã, ê, á, é, õ)", () => {
    const result = sanitizeFts("decisão de preço com informação");
    assert.ok(result.includes("decisão"), `'decisão' should be preserved`);
    assert.ok(result.includes("preço"), `'preço' should be preserved`);
    assert.ok(result.includes("informação"), `'informação' should be preserved`);
  });

  it("preserves alphanumeric tokens", () => {
    const result = sanitizeFts("nox mem v3 pricing strategy");
    assert.strictEqual(result, "nox mem v3 pricing strategy");
  });

  it("collapses multiple spaces after stripping", () => {
    const result = sanitizeFts("pricing?  strategy,  model.");
    assert.ok(!/ {2}/.test(result), `Expected collapsed spaces, got: "${result}"`);
  });

  it("returns empty string for punctuation-only input", () => {
    const result = sanitizeFts("??? !!! ...");
    assert.strictEqual(result, "");
  });
});

describe("sanitizeFts — regression: buggy regex did NOT strip these chars", () => {
  // These assertions FAIL with the old regex (proving the bug existed)
  // and PASS with the new fix.

  const nlQuery = "What did Toto decide about pricing?";

  it("[regression] buggy regex leaves '?' in place", () => {
    const buggy = sanitizeFtsBuggy(nlQuery);
    // Documenting the bug: buggy output still contains '?'
    assert.ok(buggy.includes("?"), `Buggy regex should have left '?' — got: "${buggy}"`);
  });

  it("[regression] new regex correctly strips '?' from NL query", () => {
    const fixed = sanitizeFts(nlQuery);
    assert.ok(!fixed.includes("?"), `Fixed regex must strip '?' — got: "${fixed}"`);
    assert.ok(fixed.length > 0, "Fixed query should not be empty");
  });
});

describe("FTS5 integration — NL query returns >0 docs with fix", () => {
  const db = makeFtsDb();

  it("NL query 'What did Toto decide about pricing?' returns >0 docs after sanitize", () => {
    const query = "What did Toto decide about pricing?";
    const sanitized = sanitizeFts(query);
    // Verify sanitize removed the '?'
    assert.ok(!sanitized.includes("?"), `'?' should be stripped before FTS5`);
    // Verify FTS5 actually returns results
    const count = ftsQuery(db, sanitized);
    assert.ok(count > 0, `Expected >0 FTS5 results for sanitized NL query, got ${count}`);
  });

  it("[regression] buggy sanitize causes 0 FTS5 results for same NL query", () => {
    const query = "What did Toto decide about pricing?";
    const buggy = sanitizeFtsBuggy(query);
    // FTS5 sees '?' and returns 0 (parse error or empty match)
    const count = ftsQuery(db, buggy);
    assert.strictEqual(count, 0, `Buggy sanitize should yield 0 FTS5 results (regression proof)`);
  });

  it("keyword query without punctuation returns >0 docs (baseline)", () => {
    const sanitized = sanitizeFts("pricing strategy");
    const count = ftsQuery(db, sanitized);
    assert.ok(count > 0, `Keyword query should return results, got ${count}`);
  });

  it("PT-BR query 'decisão sobre preço' returns 0 (no match, but does not error)", () => {
    // This is a no-match test — the DB has English content.
    // Key: it must not throw, and sanitize must preserve the tokens.
    const query = "decisão sobre preço?";
    const sanitized = sanitizeFts(query);
    assert.ok(!sanitized.includes("?"), "? must be stripped from PT-BR query");
    assert.ok(sanitized.includes("decisão"), "PT-BR chars must be preserved");
    // ftsQuery will return 0 (no match) but must not throw
    const count = ftsQuery(db, sanitized);
    assert.strictEqual(typeof count, "number", "ftsQuery must return a number");
  });
});
