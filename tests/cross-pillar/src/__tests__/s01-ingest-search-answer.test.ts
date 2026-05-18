/**
 * S1 — Ingest → search → answer chain (P1 + A1 + L4).
 *
 * Verifies:
 *   - A1 privacy filter redacts PII before chunk write
 *   - L4 regex-first extractor picks up typed entity refs from redacted content
 *   - search returns the redacted chunk (PII is gone from the indexed text)
 *   - P1 answer cites the chunk and never leaks PII into the answer body
 *
 * Bug-class targeted: a regression that lets raw PII leak through the
 * search → answer path because some layer reads from a pre-redaction
 * copy of the content. We assert REDACTED text wins everywhere.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import {
  redact,
  extractEntityRefs,
  scoreEntityRef,
} from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);
});
afterEach(() => {
  db.close();
});

/** Minimal P1-style answer composer for cross-pillar tests. */
function composeAnswer(
  question: string,
  retrieved: Array<{ id: number; content: string }>
): { answer: string; citations: Array<{ chunk_id: number; snippet: string }> } {
  if (retrieved.length === 0) {
    return {
      answer: "I have no memory matches for this question.",
      citations: [],
    };
  }
  // Compose answer text using REDACTED content of the chunks. The shim mirrors
  // the contract that P1 always grounds its answer on retrieved chunks (passed
  // through buildPrompt + LLM → text + citations parsed from `[chunk_N]`).
  const lines: string[] = [];
  const citations: Array<{ chunk_id: number; snippet: string }> = [];
  for (let i = 0; i < retrieved.length; i++) {
    const c = retrieved[i]!;
    lines.push(`[chunk_${i + 1}] ${c.content}`);
    citations.push({ chunk_id: c.id, snippet: c.content.slice(0, 200) });
  }
  return {
    answer: `Based on memory: ${lines.join(" — ")}. Question was: ${question}`,
    citations,
  };
}

function ingestChunk(content: string, opts: { confidence?: number } = {}): number {
  const r = redact(content);
  const res = db
    .prepare(
      `INSERT INTO chunks (content, content_hash, confidence, provenance_kind, section)
       VALUES (?, ?, ?, ?, 'compiled')`
    )
    .run(r.text, `h-${Date.now()}-${Math.random()}`, opts.confidence ?? 0.8, "observed");
  return Number(res.lastInsertRowid);
}

function naiveSearch(query: string, k: number): Array<{ id: number; content: string }> {
  // Simple LIKE-based search for cross-pillar tests (real codebase uses FTS5/vec).
  const tokens = query.toLowerCase().split(/\s+/).filter((t) => t.length > 2);
  if (tokens.length === 0) return [];
  const clauses = tokens.map(() => "LOWER(content) LIKE ?").join(" OR ");
  const params = tokens.map((t) => `%${t}%`);
  return db
    .prepare(`SELECT id, content FROM chunks WHERE ${clauses} LIMIT ?`)
    .all(...params, k) as Array<{ id: number; content: string }>;
}

describe("S1 — ingest → search → answer chain (P1 + A1 + L4)", () => {
  it("S1-01 PII redacted at ingest persists redacted text only", () => {
    const raw =
      "Production cluster used api key sk-ant-EXAMPLE12345678901234567890 and AKIAIOSFODNN7EXAMPLE for backup.";
    const id = ingestChunk(raw);
    const row = db.prepare(`SELECT content FROM chunks WHERE id = ?`).get(id) as {
      content: string;
    };
    assert.ok(!row.content.includes("sk-ant-EXAMPLE"));
    assert.ok(!row.content.includes("AKIAIOSFODNN7EXAMPLE"));
    assert.ok(row.content.includes("[REDACTED:anthropic-key]"));
    assert.ok(row.content.includes("[REDACTED:aws-access-key-id]"));
  });

  it("S1-02 L4 extracts typed entity refs from redacted content", () => {
    const raw =
      "We crystallized [Toto](person/toto-busnello) per [[decision/d41]] using ghp_TOKEN1234567890abcdefghij for CI.";
    const id = ingestChunk(raw);
    const row = db.prepare(`SELECT content FROM chunks WHERE id = ?`).get(id) as {
      content: string;
    };
    const refs = extractEntityRefs(row.content);
    const keys = refs.map((r) => r.key).sort();
    assert.deepStrictEqual(keys, ["decision/d41", "person/toto-busnello"]);
    assert.ok(row.content.includes("[REDACTED:github-token]"));
    // Confidence scores produced by L4 are within expected band.
    for (const r of refs) {
      const conf = scoreEntityRef(r);
      assert.ok(conf >= 0.75 && conf <= 0.95);
    }
  });

  it("S1-03 search returns redacted chunk; never the raw PII version", () => {
    // Synthetic test fixture: build the gemini-key-shaped literal at runtime
    // so static gitleaks scans don't false-positive on the test source itself.
    const fakeGeminiKey = "AIza" + "SyEXAMPLEKEY1234567890abcdefghij123";
    ingestChunk(
      `The deployment uses gemini key ${fakeGeminiKey} in production cluster.`
    );
    const results = naiveSearch("deployment production", 5);
    assert.ok(results.length >= 1);
    for (const r of results) {
      assert.ok(!r.content.includes("AIzaSy"));
      assert.ok(r.content.includes("[REDACTED:gemini-key]"));
    }
  });

  it("S1-04 answer cites the chunk and never leaks raw PII", () => {
    const raw =
      "Use auth header Authorization: Bearer sk-ant-EXAMPLE12345678901234567890 for the deployment.";
    const id = ingestChunk(raw);
    const retrieved = naiveSearch("deployment auth", 5);
    assert.ok(retrieved.length >= 1);
    const out = composeAnswer("how do I auth the deployment?", retrieved);
    assert.ok(out.citations.length >= 1);
    assert.strictEqual(out.citations[0]!.chunk_id, id);
    // The crucial assertion: answer body MUST NOT contain the raw secret.
    assert.ok(!out.answer.includes("sk-ant-EXAMPLE"));
    assert.ok(out.answer.includes("[REDACTED:anthropic-key]"));
  });

  it("S1-05 empty search returns canonical 'no memory matches' answer", () => {
    ingestChunk("unrelated content goes here for the chunk table");
    const retrieved = naiveSearch("xyzzy-nonexistent-token-zzz", 5);
    assert.strictEqual(retrieved.length, 0);
    const out = composeAnswer("does this question match anything?", retrieved);
    assert.match(out.answer, /no memory matches/i);
    assert.strictEqual(out.citations.length, 0);
  });

  it("S1-06 chain handles mixed PII + entity refs in one chunk without losing refs", () => {
    // The integration-bug class targeted: a regression where the privacy filter
    // would accidentally consume entity-ref syntax (e.g. greedy regex eats
    // `decision/d41` because of `[A-Za-z0-9_-]{20,}` patterns).
    const fakeGeminiKey = "AIza" + "SyEXAMPLEKEY1234567890abcdefghij123";
    const raw = `Per [[decision/d41]] and [Lex](agent/lex-agent), key was ${fakeGeminiKey} (rotated). Reference person/toto-busnello here.`;
    const id = ingestChunk(raw);
    const row = db.prepare(`SELECT content FROM chunks WHERE id = ?`).get(id) as {
      content: string;
    };
    const refs = extractEntityRefs(row.content);
    const keys = refs.map((r) => r.key).sort();
    assert.deepStrictEqual(keys, [
      "agent/lex-agent",
      "decision/d41",
      "person/toto-busnello",
    ]);
    assert.ok(row.content.includes("[REDACTED:gemini-key]"));
    assert.ok(!row.content.includes("AIzaSy"));
    // And the answer reflects all three refs without leaking the key.
    const out = composeAnswer("d41?", [{ id, content: row.content }]);
    assert.ok(out.answer.includes("decision/d41"));
    assert.ok(!out.answer.includes("AIzaSy"));
  });
});
