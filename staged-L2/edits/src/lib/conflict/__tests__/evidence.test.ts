import { test } from "node:test";
import assert from "node:assert/strict";
import { collectEvidence } from "../evidence.js";
import { FakeDB, seedChunk } from "./fakes.js";
import type { Conflict } from "../types.js";

function fixtureConflict(): Conflict {
  return {
    kind: "direct",
    subject_entity_id: 1,
    predicate: "uses_model",
    variants: [
      {
        relation_id: 10,
        target_entity_id: 100,
        confidence: 0.9,
        extraction_method: "regex_only",
        evidence_chunk_id: 5000,
        created_at: 1_700_000_000_000,
      },
      {
        relation_id: 11,
        target_entity_id: 101,
        confidence: 0.8,
        extraction_method: "gemini_only",
        evidence_chunk_id: 5001,
        created_at: 1_700_000_100_000,
      },
    ],
  };
}

test("evidence: empty chunks when relation has no evidence_chunk_id", () => {
  const db = new FakeDB();
  const c: Conflict = fixtureConflict();
  c.variants = c.variants.map((v) => ({ ...v, evidence_chunk_id: null }));
  const ev = collectEvidence(db, c);
  for (const ve of ev.variants) {
    assert.equal(ve.chunks.length, 0);
  }
});

test("evidence: chunks hydrated when evidence_chunk_id matches a row", () => {
  const db = new FakeDB();
  seedChunk(db, { id: 5000, content: "We deployed opus-4.6 on 2026-05-01" });
  seedChunk(db, { id: 5001, content: "Actually we switched to sonnet-4.6 on 2026-05-10" });
  const ev = collectEvidence(db, fixtureConflict());
  // variants returned newest-first → variant 11 (ts=...100) before variant 10 (ts=...000)
  assert.equal(ev.variants[0]!.variant.relation_id, 11);
  assert.equal(ev.variants[0]!.chunks[0]!.chunk_id, 5001);
  assert.equal(ev.variants[1]!.variant.relation_id, 10);
  assert.equal(ev.variants[1]!.chunks[0]!.chunk_id, 5000);
});

test("evidence: snippet truncated to default len with ellipsis", () => {
  const db = new FakeDB();
  const long = "x".repeat(1_000);
  seedChunk(db, { id: 5000, content: long });
  const c = fixtureConflict();
  c.variants = [c.variants[0]!];
  const ev = collectEvidence(db, c);
  const snip = ev.variants[0]!.chunks[0]!.snippet;
  assert.ok(snip.length <= 320, `snippet too long: ${snip.length}`);
  assert.ok(snip.endsWith("…"), "expected ellipsis on truncated snippet");
});

test("evidence: snippet collapses internal whitespace", () => {
  const db = new FakeDB();
  seedChunk(db, { id: 5000, content: "hello\n\n\tworld   foo" });
  const c = fixtureConflict();
  c.variants = [c.variants[0]!];
  const ev = collectEvidence(db, c);
  assert.equal(ev.variants[0]!.chunks[0]!.snippet, "hello world foo");
});

test("evidence: custom snippet_len honored", () => {
  const db = new FakeDB();
  seedChunk(db, { id: 5000, content: "abcdefghij" });
  const c = fixtureConflict();
  c.variants = [c.variants[0]!];
  const ev = collectEvidence(db, c, { snippet_len: 6 });
  assert.ok(ev.variants[0]!.chunks[0]!.snippet.length <= 6);
});

test("evidence: snippet_len ≤0 throws", () => {
  const db = new FakeDB();
  assert.throws(() => collectEvidence(db, fixtureConflict(), { snippet_len: 0 }), /snippet_len/);
});

test("evidence: weighted_score uses relation conf only when no chunk", () => {
  const db = new FakeDB();
  const c = fixtureConflict();
  c.variants = c.variants.map((v) => ({ ...v, evidence_chunk_id: null }));
  const ev = collectEvidence(db, c);
  // No chunk → weighted equals variant.confidence
  assert.equal(ev.variants[0]!.weighted_score, ev.variants[0]!.variant.confidence);
});

test("evidence: weighted_score averages relation + chunk confidence", () => {
  const db = new FakeDB();
  // chunk conf = 0.6, variant conf = 0.9 (per fixture variant 0) → weighted = 0.75
  seedChunk(db, { id: 5000, content: "x", confidence: 0.6 });
  const c = fixtureConflict();
  c.variants = [c.variants[0]!];
  const ev = collectEvidence(db, c);
  assert.equal(ev.variants[0]!.weighted_score, 0.75);
});
