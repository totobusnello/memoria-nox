import { test } from "node:test";
import assert from "node:assert/strict";
import { detectDirectConflicts } from "../detector-direct.js";
import { FakeDB, seedEntity, seedRelation } from "./fakes.js";

function makeDB(): FakeDB {
  const db = new FakeDB();
  seedEntity(db, 1, "toto");
  seedEntity(db, 100, "opus-4.6");
  seedEntity(db, 101, "sonnet-4.6");
  seedEntity(db, 102, "haiku-4.6");
  return db;
}

test("detector: zero conflicts on empty DB", () => {
  const db = new FakeDB();
  assert.deepEqual(detectDirectConflicts(db), []);
});

test("detector: zero conflicts when same (subject,predicate,target) repeats", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100 });
  assert.deepEqual(detectDirectConflicts(db), []);
});

test("detector: Type 1 direct conflict — 2 distinct targets", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  const out = detectDirectConflicts(db);
  assert.equal(out.length, 1);
  assert.equal(out[0]!.kind, "direct");
  assert.equal(out[0]!.subject_entity_id, 1);
  assert.equal(out[0]!.predicate, "uses_model");
  assert.equal(out[0]!.variants.length, 2);
});

test("detector: multi_target when 3+ distinct targets", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  seedRelation(db, { id: 3, source_entity_id: 1, predicate: "uses_model", target_entity_id: 102, confidence: 0.7 });
  const out = detectDirectConflicts(db);
  assert.equal(out.length, 1);
  assert.equal(out[0]!.kind, "multi_target");
  assert.equal(out[0]!.variants.length, 3);
});

test("detector: min_confidence filters out low-confidence relations", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.4 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  // Default min_confidence=0.5 — rel 1 dropped, no conflict remains.
  assert.deepEqual(detectDirectConflicts(db), []);
  // Lower threshold restores the conflict.
  const out = detectDirectConflicts(db, { min_confidence: 0.3 });
  assert.equal(out.length, 1);
});

test("detector: superseded relations excluded", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9, superseded_by_relation_id: 2 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  // Rel 1 is superseded → conflict has only 1 active target → no flag.
  assert.deepEqual(detectDirectConflicts(db), []);
});

test("detector: predicate_allowlist restricts surface", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  seedRelation(db, { id: 3, source_entity_id: 1, predicate: "has_owner", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 4, source_entity_id: 1, predicate: "has_owner", target_entity_id: 101, confidence: 0.85 });
  const out = detectDirectConflicts(db, { predicate_allowlist: ["uses_model"] });
  assert.equal(out.length, 1);
  assert.equal(out[0]!.predicate, "uses_model");
});

test("detector: predicate_blocklist filters explicitly", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "mentions", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "mentions", target_entity_id: 101, confidence: 0.85 });
  const out = detectDirectConflicts(db, { predicate_blocklist: ["mentions"] });
  assert.deepEqual(out, []);
});

test("detector: extraction_method weights bias confidence (clamped)", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.8, extraction_method: "regex_only" });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.8, extraction_method: "gemini_only" });
  const out = detectDirectConflicts(db, {
    extraction_method_weights: { regex_only: 1.5, gemini_only: 0.5 },
  });
  assert.equal(out.length, 1);
  const regex = out[0]!.variants.find((v) => v.extraction_method === "regex_only")!;
  const gemini = out[0]!.variants.find((v) => v.extraction_method === "gemini_only")!;
  // 0.8 * 1.5 = 1.2 → clamped to 1.0
  assert.equal(regex.confidence, 1.0);
  // 0.8 * 0.5 = 0.4
  assert.equal(gemini.confidence, 0.4);
});

test("detector: subject_label populated when entity name exists", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "p", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "p", target_entity_id: 101, confidence: 0.85 });
  const out = detectDirectConflicts(db);
  assert.equal(out[0]!.subject_label, "toto");
});

test("detector: limit caps results", () => {
  const db = makeDB();
  // 5 distinct subjects each with conflicts.
  for (let s = 1; s <= 5; s++) {
    seedEntity(db, 200 + s, `subject-${s}`);
    seedRelation(db, { id: s * 10, source_entity_id: 200 + s, predicate: "p", target_entity_id: 100, confidence: 0.9 });
    seedRelation(db, { id: s * 10 + 1, source_entity_id: 200 + s, predicate: "p", target_entity_id: 101, confidence: 0.85 });
  }
  const out = detectDirectConflicts(db, { limit: 2 });
  assert.equal(out.length, 2);
});

test("detector: throws on out-of-range min_confidence", () => {
  const db = new FakeDB();
  assert.throws(() => detectDirectConflicts(db, { min_confidence: 1.5 }), /min_confidence/);
  assert.throws(() => detectDirectConflicts(db, { min_confidence: -0.1 }), /min_confidence/);
});

test("detector: user_marked propagates to variant", () => {
  const db = makeDB();
  seedRelation(db, { id: 1, source_entity_id: 1, predicate: "p", target_entity_id: 100, confidence: 0.9, user_marked: 1 });
  seedRelation(db, { id: 2, source_entity_id: 1, predicate: "p", target_entity_id: 101, confidence: 0.85 });
  const out = detectDirectConflicts(db);
  const marked = out[0]!.variants.find((v) => v.relation_id === 1)!;
  const unmarked = out[0]!.variants.find((v) => v.relation_id === 2)!;
  assert.equal(marked.user_marked, true);
  assert.equal(unmarked.user_marked, false);
});
