import { test } from "node:test";
import assert from "node:assert/strict";
import { detectDirectConflicts } from "../detector-direct.js";
import {
  recordConflict,
  updateConflictStatus,
  listConflicts,
  getConflictById,
  statusCounts,
} from "../audit-writer.js";
import { collectEvidence } from "../evidence.js";
import {
  runConflictPass,
  annotateRelations,
  getConflictsForRelations,
} from "../shadow.js";
import { FakeDB, seedEntity, seedRelation, seedChunk } from "./fakes.js";

/**
 * End-to-end integration:
 *   1. Seed a synthetic KG with 5 known conflicts + 50 normal relations.
 *   2. Run detector pass → expect exactly 5 conflicts.
 *   3. Record audit rows → expect 5.
 *   4. Resolve 2 of them (pick + dismiss).
 *   5. Re-scan → expect dedupe (3 remain open, no new inserts).
 *   6. Confirm annotations only fire in active mode.
 *   7. Confirm statusCounts reflects mixed terminal/open states.
 */

function buildSyntheticDB(): FakeDB {
  const db = new FakeDB();
  db.enableConflictAuditTriggers();

  // Entities — subjects 1..10 + targets 100..120
  for (let i = 1; i <= 10; i++) seedEntity(db, i, `subject-${i}`, "person");
  for (let i = 100; i <= 120; i++) seedEntity(db, i, `target-${i}`, "model");

  // ── 50 normal (non-conflict) relations ────────────────────────────────────
  let relId = 1;
  let chunkId = 5000;
  for (let s = 1; s <= 10; s++) {
    for (let k = 0; k < 5; k++) {
      const pred = `pred_norm_${k}`;
      const target = 100 + ((s + k) % 21);
      seedChunk(db, { id: chunkId, content: `${s} ${pred} ${target}` });
      seedRelation(db, {
        id: relId,
        source_entity_id: s,
        predicate: pred,
        target_entity_id: target,
        confidence: 0.8,
        evidence_chunk_id: chunkId,
        created_at: 1_700_000_000_000 + relId * 1000,
      });
      relId++;
      chunkId++;
    }
  }

  // ── 5 conflicts: subject S has uses_model→A and uses_model→B ──────────────
  const conflictSubjects = [1, 2, 3, 4, 5];
  for (const s of conflictSubjects) {
    const tA = 100 + s;
    const tB = 110 + s;
    seedChunk(db, { id: chunkId, content: `${s} switched to A` });
    seedRelation(db, {
      id: relId,
      source_entity_id: s,
      predicate: "uses_model",
      target_entity_id: tA,
      confidence: 0.9,
      evidence_chunk_id: chunkId,
      created_at: 1_700_000_000_000 + relId * 1000,
    });
    relId++;
    chunkId++;
    seedChunk(db, { id: chunkId, content: `${s} switched back to B` });
    seedRelation(db, {
      id: relId,
      source_entity_id: s,
      predicate: "uses_model",
      target_entity_id: tB,
      confidence: 0.85,
      evidence_chunk_id: chunkId,
      created_at: 1_700_000_000_000 + relId * 1000,
    });
    relId++;
    chunkId++;
  }

  return db;
}

test("integration: detect finds exactly 5 conflicts (no false positives)", () => {
  const db = buildSyntheticDB();
  const conflicts = detectDirectConflicts(db);
  assert.equal(conflicts.length, 5);
  for (const c of conflicts) {
    assert.equal(c.kind, "direct");
    assert.equal(c.predicate, "uses_model");
    assert.equal(c.variants.length, 2);
  }
});

test("integration: shadow pass records 5 audit rows", () => {
  const db = buildSyntheticDB();
  const result = runConflictPass(db, {}, "shadow");
  assert.equal(result.detected, 5);
  assert.equal(result.recorded, 5);
  assert.equal(result.deduplicated, 0);
});

test("integration: second pass yields 5 dedupe hits, 0 new rows", () => {
  const db = buildSyntheticDB();
  runConflictPass(db, {}, "shadow");
  const second = runConflictPass(db, {}, "shadow");
  assert.equal(second.recorded, 0);
  assert.equal(second.deduplicated, 5);
});

test("integration: resolve 2 conflicts → re-scan does not re-open them", () => {
  const db = buildSyntheticDB();
  const r1 = runConflictPass(db, {}, "shadow");
  assert.equal(r1.audit_ids.length, 5);
  // resolve first two
  updateConflictStatus(db, r1.audit_ids[0]!, {
    status: "resolved_pick_one",
    resolved_by: "test",
    resolution_kind: "pick_one",
    picked_relation_id: 51,
  });
  updateConflictStatus(db, r1.audit_ids[1]!, {
    status: "dismissed",
    resolved_by: "test",
    resolution_kind: "dismissed",
  });

  // Now rescan — only 3 remain "open"; dedupe finds 3, not 5.
  const r2 = runConflictPass(db, {}, "shadow");
  assert.equal(r2.detected, 5);
  // 2 audit rows are now terminal → no open row exists for those subjects →
  // dedupe pre-check returns nothing → a NEW open row would be inserted for
  // those subjects. This is the desired flow (re-flag after resolution).
  // For the 3 still-open subjects, dedupe hits.
  // Net: 2 new rows + 3 dedupes.
  assert.equal(r2.recorded, 2);
  assert.equal(r2.deduplicated, 3);
});

test("integration: terminal rows cannot be reopened by trigger", () => {
  const db = buildSyntheticDB();
  const r1 = runConflictPass(db, {}, "shadow");
  const id = r1.audit_ids[0]!;
  updateConflictStatus(db, id, {
    status: "dismissed",
    resolved_by: "test",
    resolution_kind: "dismissed",
  });
  // Attempt to flip back → trigger blocks.
  assert.throws(
    () =>
      updateConflictStatus(db, id, {
        // Cast to bypass TS guard; runtime trigger should still reject.
        status: "open" as never,
        resolved_by: "test",
        resolution_kind: "dismissed",
      }),
    /reopened|forbidden|append-only/i,
  );
});

test("integration: collectEvidence joins chunks for every variant", () => {
  const db = buildSyntheticDB();
  const [conflict] = detectDirectConflicts(db);
  assert.ok(conflict);
  const ev = collectEvidence(db, conflict!);
  // Every variant in the seeded set has an evidence_chunk_id → expect ≥1 chunk per variant.
  for (const ve of ev.variants) {
    assert.ok(ve.chunks.length >= 1, "expected evidence chunk for variant");
  }
});

test("integration: annotateRelations returns flags only in active mode", () => {
  const db = buildSyntheticDB();
  runConflictPass(db, {}, "active");
  // Pick a relation id known to be in a conflict (the last seeded pair is rel id 60-61).
  // Use first audit row's target_relation_ids as ground truth.
  const rows = listConflicts(db, "open", 10);
  const idsFromAudit = rows[0]!.target_relation_ids;
  const flagged = annotateRelations(db, idsFromAudit, "active");
  assert.equal(flagged.size, idsFromAudit.length);
  // In shadow mode, returns empty set even when rows exist.
  const flaggedShadow = annotateRelations(db, idsFromAudit, "shadow");
  assert.equal(flaggedShadow.size, 0);
});

test("integration: getConflictsForRelations returns rich payload", () => {
  const db = buildSyntheticDB();
  runConflictPass(db, {}, "shadow");
  const rows = listConflicts(db, "open", 1);
  const someRel = rows[0]!.target_relation_ids[0]!;
  const matched = getConflictsForRelations(db, [someRel]);
  assert.equal(matched.length, 1);
  assert.equal(matched[0]!.predicate, "uses_model");
});

test("integration: statusCounts reports mixed terminal/open mix", () => {
  const db = buildSyntheticDB();
  const r = runConflictPass(db, {}, "shadow");
  updateConflictStatus(db, r.audit_ids[0]!, {
    status: "resolved_both_valid",
    resolved_by: "test",
    resolution_kind: "both_valid",
  });
  updateConflictStatus(db, r.audit_ids[1]!, {
    status: "resolved_merged",
    resolved_by: "test",
    resolution_kind: "merged",
    merge_target: "newcanon",
  });
  const counts = statusCounts(db);
  assert.equal(counts.open, 3);
  assert.equal(counts.resolved_both_valid, 1);
  assert.equal(counts.resolved_merged, 1);
  assert.equal(counts.resolved_pick_one, 0);
});

test("integration: confidence threshold gates noise", () => {
  const db = buildSyntheticDB();
  // Insert a low-confidence conflict that must NOT be detected by default (0.5).
  seedRelation(db, { id: 9001, source_entity_id: 7, predicate: "shaky_pred", target_entity_id: 100, confidence: 0.3 });
  seedRelation(db, { id: 9002, source_entity_id: 7, predicate: "shaky_pred", target_entity_id: 101, confidence: 0.3 });
  const out = detectDirectConflicts(db);
  // Should still only find the 5 'uses_model' conflicts, not the shaky one.
  assert.equal(out.length, 5);
  // But with min_confidence lowered, it surfaces.
  const out2 = detectDirectConflicts(db, { min_confidence: 0.2 });
  assert.equal(out2.length, 6);
});

test("integration: limit caps results at boundary", () => {
  const db = buildSyntheticDB();
  const out = detectDirectConflicts(db, { limit: 2 });
  assert.equal(out.length, 2);
});

test("integration: predicate_blocklist on uses_model zeros conflicts", () => {
  const db = buildSyntheticDB();
  const out = detectDirectConflicts(db, { predicate_blocklist: ["uses_model"] });
  assert.equal(out.length, 0);
});

test("integration: full lifecycle audit row → terminal → counted in stats", () => {
  const db = buildSyntheticDB();
  const conflicts = detectDirectConflicts(db);
  const id = recordConflict(db, conflicts[0]!).id;
  updateConflictStatus(db, id, {
    status: "resolved_pick_one",
    resolved_by: "test",
    resolution_kind: "pick_one",
    picked_relation_id: conflicts[0]!.variants[0]!.relation_id,
    notes: "smoke test",
  });
  const row = getConflictById(db, id)!;
  assert.equal(row.status, "resolved_pick_one");
  assert.equal(row.notes, "smoke test");
});
