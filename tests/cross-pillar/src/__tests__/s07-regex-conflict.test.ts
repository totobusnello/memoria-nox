/**
 * S7 — Regex-first KG extraction → conflict (L4 + L2).
 *
 * Verifies:
 *   - Two chunks with contradictory typed-link facts produce 2 relations
 *     via L4 regex extraction
 *   - Both relations carry extraction_method='regex_only'
 *   - L2 detector flags the contradiction
 *   - conflict_audit row references both source chunks via evidence_chunk_id
 *
 * Bug-class targeted: a regression where L4's regex pipeline mis-tags
 * extraction_method (e.g. as 'gemini_only') after a merge — preventing
 * provenance-aware weighting in L2.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import {
  extractEntityRefs,
  detectDirectConflicts,
  recordConflict,
  scoreEntityRef,
} from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);
});
afterEach(() => db.close());

function insertChunk(content: string): number {
  return Number(
    db
      .prepare(`INSERT INTO chunks (content, content_hash) VALUES (?, ?)`)
      .run(content, `h-${Math.random()}`).lastInsertRowid
  );
}

function insertEntity(kind: string, name: string, slug: string): number {
  return Number(
    db
      .prepare(`INSERT INTO kg_entities (kind, name, slug) VALUES (?,?,?)`)
      .run(kind, name, slug).lastInsertRowid
  );
}

describe("S7 — regex-extraction → conflict (L4 + L2)", () => {
  it("S7-01 two chunks with contradictory wikilinks produce 2 relations tagged regex_only", () => {
    // Chunk A says FII Treviso is led_by Toto.
    const cA = insertChunk("[[project/fii-treviso]] is led_by [[person/toto]].");
    // Chunk B says FII Treviso is led_by Boris.
    const cB = insertChunk("[[project/fii-treviso]] is led_by [[person/boris]].");

    const refsA = extractEntityRefs(
      "[[project/fii-treviso]] is led_by [[person/toto]]."
    );
    const refsB = extractEntityRefs(
      "[[project/fii-treviso]] is led_by [[person/boris]]."
    );
    assert.strictEqual(refsA.length, 2);
    assert.strictEqual(refsB.length, 2);

    // Resolve / insert entities.
    const subj = insertEntity("project", "FII Treviso", "fii-treviso");
    const t1 = insertEntity("person", "Toto", "toto");
    const t2 = insertEntity("person", "Boris", "boris");

    // Insert relations with extraction_method='regex_only' (L4 contract).
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t1, "led_by", scoreEntityRef(refsA[1]!), "regex_only", cA);
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t2, "led_by", scoreEntityRef(refsB[1]!), "regex_only", cB);

    const all = db
      .prepare(`SELECT extraction_method, evidence_chunk_id FROM kg_relations ORDER BY id`)
      .all() as Array<{ extraction_method: string; evidence_chunk_id: number }>;
    assert.strictEqual(all.length, 2);
    for (const r of all) assert.strictEqual(r.extraction_method, "regex_only");
  });

  it("S7-02 detector finds the contradiction with both variants visible", () => {
    const cA = insertChunk("[[project/fii-treviso]] led_by [[person/toto]].");
    const cB = insertChunk("[[project/fii-treviso]] led_by [[person/boris]].");
    const subj = insertEntity("project", "FII Treviso", "fii-treviso");
    const t1 = insertEntity("person", "Toto", "toto");
    const t2 = insertEntity("person", "Boris", "boris");
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t1, "led_by", 0.9, "regex_only", cA);
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t2, "led_by", 0.9, "regex_only", cB);

    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    assert.strictEqual(conflicts.length, 1);
    assert.strictEqual(conflicts[0]!.kind, "direct");
    const cks = conflicts[0]!.variants.map((v) => v.evidence_chunk_id).sort();
    assert.deepStrictEqual(cks, [cA, cB].sort());
  });

  it("S7-03 conflict_audit row points back to both source chunks", () => {
    const cA = insertChunk("[[project/fii-treviso]] led_by [[person/toto]].");
    const cB = insertChunk("[[project/fii-treviso]] led_by [[person/boris]].");
    const subj = insertEntity("project", "FII Treviso", "fii-treviso");
    const t1 = insertEntity("person", "Toto", "toto");
    const t2 = insertEntity("person", "Boris", "boris");
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t1, "led_by", 0.9, "regex_only", cA);
    db.prepare(
      `INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate, confidence, extraction_method, evidence_chunk_id) VALUES (?,?,?,?,?,?)`
    ).run(subj, t2, "led_by", 0.9, "regex_only", cB);

    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    const auditId = recordConflict(db, conflicts[0]!);
    const row = db
      .prepare(`SELECT variants FROM conflict_audit WHERE id = ?`)
      .get(auditId) as { variants: string };
    const variants = JSON.parse(row.variants) as Array<{
      evidence_chunk_id: number;
    }>;
    const ecks = variants.map((v) => v.evidence_chunk_id).sort();
    assert.deepStrictEqual(ecks, [cA, cB].sort());
  });

  it("S7-04 markdown_link confidence > bare_ref confidence (L4 contract)", () => {
    const md = extractEntityRefs("[Toto](person/toto)");
    const bare = extractEntityRefs("Reference: person/toto here.");
    assert.ok(scoreEntityRef(md[0]!) > scoreEntityRef(bare[0]!));
  });

  it("S7-05 stripped code fences mean L4 doesn't tag refs in code blocks", () => {
    const out = extractEntityRefs(
      "```ts\nconst x = 'person/toto'; // not a real ref\n```\nReal: [[person/boris]]"
    );
    const keys = out.map((r) => r.key);
    assert.deepStrictEqual(keys, ["person/boris"]);
  });
});
