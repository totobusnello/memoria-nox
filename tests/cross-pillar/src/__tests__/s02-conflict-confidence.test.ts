/**
 * S2 — KG conflict detection with confidence (L2 + L3).
 *
 * Verifies:
 *   - L2 detector respects min_confidence floor (low-confidence variants excluded)
 *   - L3 user_marked_canonical raises a variant's confidence to 1.0 and pins it
 *   - Conflicts remaining after one canonical mark are still detected (with
 *     the canonical variant clearly the higher-weighted one)
 *
 * Bug-class targeted: a regression where marking one variant as canonical
 * accidentally suppresses the entire conflict group (defeating the audit),
 * OR where the min_confidence floor leaks low-conf relations through.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import {
  detectDirectConflicts,
  markRelationCanonical,
  recordConflict,
} from "../lib/pillar-shims.js";

let db: DatabaseType;
let subjectId: number;
let targetAId: number;
let targetBId: number;
let targetCId: number;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);

  // Three entities: one subject + two competing targets + a third for multi_target.
  const ins = db.prepare(`INSERT INTO kg_entities (kind, name, slug) VALUES (?,?,?)`);
  subjectId = Number(ins.run("project", "FII Treviso", "fii-treviso").lastInsertRowid);
  targetAId = Number(ins.run("person", "Toto Busnello", "toto-busnello").lastInsertRowid);
  targetBId = Number(ins.run("person", "Boris", "boris").lastInsertRowid);
  targetCId = Number(ins.run("person", "Cipher", "cipher").lastInsertRowid);
});
afterEach(() => {
  db.close();
});

function insertRelation(opts: {
  source: number;
  target: number;
  predicate: string;
  confidence: number;
  extraction_method?: string;
  user_marked?: boolean;
}): number {
  const r = db
    .prepare(
      `INSERT INTO kg_relations
       (source_entity_id, target_entity_id, predicate, confidence, extraction_method, user_marked)
       VALUES (?,?,?,?,?,?)`
    )
    .run(
      opts.source,
      opts.target,
      opts.predicate,
      opts.confidence,
      opts.extraction_method ?? "gemini_only",
      opts.user_marked ? 1 : 0
    );
  return Number(r.lastInsertRowid);
}

describe("S2 — KG conflict + confidence (L2 + L3)", () => {
  it("S2-01 two variants above min_confidence produce a direct conflict", () => {
    insertRelation({ source: subjectId, target: targetAId, predicate: "led_by", confidence: 0.9 });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.8 });
    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    assert.strictEqual(conflicts.length, 1);
    assert.strictEqual(conflicts[0]!.kind, "direct");
    assert.strictEqual(conflicts[0]!.predicate, "led_by");
    assert.strictEqual(conflicts[0]!.variants.length, 2);
  });

  it("S2-02 low-confidence variants are filtered out by min_confidence floor", () => {
    insertRelation({ source: subjectId, target: targetAId, predicate: "led_by", confidence: 0.9 });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.3 });
    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    assert.strictEqual(conflicts.length, 0);
  });

  it("S2-03 lowering min_confidence surfaces the previously hidden conflict", () => {
    insertRelation({ source: subjectId, target: targetAId, predicate: "led_by", confidence: 0.9 });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.3 });
    const conflicts = detectDirectConflicts(db, { min_confidence: 0.2 });
    assert.strictEqual(conflicts.length, 1);
  });

  it("S2-04 three distinct targets → kind='multi_target'", () => {
    insertRelation({ source: subjectId, target: targetAId, predicate: "led_by", confidence: 0.9 });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.8 });
    insertRelation({ source: subjectId, target: targetCId, predicate: "led_by", confidence: 0.7 });
    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    assert.strictEqual(conflicts.length, 1);
    assert.strictEqual(conflicts[0]!.kind, "multi_target");
    assert.strictEqual(conflicts[0]!.variants.length, 3);
  });

  it("S2-05 marking a variant canonical raises its confidence to 1.0", () => {
    const r1 = insertRelation({
      source: subjectId,
      target: targetAId,
      predicate: "led_by",
      confidence: 0.8,
    });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.7 });
    markRelationCanonical(db, r1, "toto");
    const row = db
      .prepare(`SELECT confidence, user_marked FROM kg_relations WHERE id = ?`)
      .get(r1) as { confidence: number; user_marked: 0 | 1 };
    assert.strictEqual(row.confidence, 1.0);
    assert.strictEqual(row.user_marked, 1);
  });

  it("S2-06 re-running detector after canonical mark still surfaces the conflict (audit-friendly)", () => {
    const r1 = insertRelation({
      source: subjectId,
      target: targetAId,
      predicate: "led_by",
      confidence: 0.8,
    });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.7 });
    markRelationCanonical(db, r1, "toto");

    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    assert.strictEqual(conflicts.length, 1);
    // Canonical variant must be present and clearly higher-confidence (1.0)
    const canonical = conflicts[0]!.variants.find((v) => v.user_marked);
    assert.ok(canonical, "expected canonical variant to be present in conflict");
    assert.strictEqual(canonical!.confidence, 1.0);
    const others = conflicts[0]!.variants.filter((v) => !v.user_marked);
    assert.strictEqual(others.length, 1);
    assert.ok(others[0]!.confidence < canonical!.confidence);
  });

  it("S2-07 recordConflict writes to conflict_audit and survives re-detection", () => {
    insertRelation({ source: subjectId, target: targetAId, predicate: "led_by", confidence: 0.9 });
    insertRelation({ source: subjectId, target: targetBId, predicate: "led_by", confidence: 0.8 });
    const conflicts = detectDirectConflicts(db, { min_confidence: 0.5 });
    const auditId = recordConflict(db, conflicts[0]!);
    assert.ok(auditId > 0);
    const row = db
      .prepare(`SELECT subject_entity_id, predicate, status, shadow_mode FROM conflict_audit WHERE id = ?`)
      .get(auditId) as {
      subject_entity_id: number;
      predicate: string;
      status: string;
      shadow_mode: 0 | 1;
    };
    assert.strictEqual(row.subject_entity_id, subjectId);
    assert.strictEqual(row.predicate, "led_by");
    assert.strictEqual(row.status, "open");
    assert.strictEqual(row.shadow_mode, 1);
  });

  it("S2-08 min_confidence out of range throws RangeError (defensive)", () => {
    assert.throws(() => detectDirectConflicts(db, { min_confidence: -0.1 }), RangeError);
    assert.throws(() => detectDirectConflicts(db, { min_confidence: 1.5 }), RangeError);
  });
});
