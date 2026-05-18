/**
 * G15 — conflict_audit FK validation tests.
 *
 * Uses a hand-rolled stub DB to avoid better-sqlite3 dep, since the
 * function only needs `prepare(sql).get(args) / .all(args)` shape.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  validateConflictAuditFK,
  assertConflictAuditFK,
  ConflictAuditFKError,
  type DBHandleMinimal,
} from "../audit-fk-check.js";

// ── stub DB ─────────────────────────────────────────────────────────────────

function makeStubDb(state: {
  entities: Set<number>;
  relations: Set<number>;
}): DBHandleMinimal {
  return {
    prepare(sql: string) {
      return {
        get(...params: unknown[]) {
          if (/FROM kg_entities WHERE id = \?/.test(sql)) {
            const id = params[0] as number;
            return state.entities.has(id) ? { id } : undefined;
          }
          if (/FROM kg_relations WHERE id = \?/.test(sql)) {
            const id = params[0] as number;
            return state.relations.has(id) ? { id } : undefined;
          }
          return undefined;
        },
        all(...params: unknown[]) {
          if (/FROM kg_relations.*json_each/.test(sql)) {
            const idsJson = params[0] as string;
            const ids = JSON.parse(idsJson) as number[];
            return ids
              .filter((id) => state.relations.has(id))
              .map((id) => ({ id }));
          }
          return [];
        },
      };
    },
  };
}

describe("validateConflictAuditFK", () => {
  it("returns valid when all FKs present", () => {
    const db = makeStubDb({ entities: new Set([1, 2]), relations: new Set([10, 20]) });
    const r = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [10, 20],
    });
    assert.equal(r.valid, true);
    assert.equal(r.missingSubject, false);
    assert.deepEqual(r.missingRelationIds, []);
  });

  it("detects missing subject_entity_id", () => {
    const db = makeStubDb({ entities: new Set([2]), relations: new Set([10]) });
    const r = validateConflictAuditFK(db, {
      subject_entity_id: 99,
      target_relation_ids: [10],
    });
    assert.equal(r.valid, false);
    assert.equal(r.missingSubject, true);
  });

  it("detects subset of missing target_relation_ids", () => {
    const db = makeStubDb({ entities: new Set([1]), relations: new Set([10, 30]) });
    const r = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [10, 20, 30, 40],
    });
    assert.equal(r.valid, false);
    assert.deepEqual(r.missingRelationIds.sort(), [20, 40]);
  });

  it("flags missing picked_relation_id (resolution path)", () => {
    const db = makeStubDb({ entities: new Set([1]), relations: new Set([10]) });
    const r = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [10],
      picked_relation_id: 999,
    });
    assert.equal(r.valid, false);
    assert.equal(r.missingPicked, true);
  });

  it("ignores picked_relation_id when omitted / null / undefined", () => {
    const db = makeStubDb({ entities: new Set([1]), relations: new Set([10]) });
    const r1 = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [10],
    });
    assert.equal(r1.missingPicked, false);
    assert.equal(r1.valid, true);

    const r2 = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [10],
      picked_relation_id: null,
    });
    assert.equal(r2.missingPicked, false);
    assert.equal(r2.valid, true);
  });

  it("empty target_relation_ids is valid (caller decides if business-allowed)", () => {
    const db = makeStubDb({ entities: new Set([1]), relations: new Set() });
    const r = validateConflictAuditFK(db, {
      subject_entity_id: 1,
      target_relation_ids: [],
    });
    assert.equal(r.valid, true);
  });
});

describe("assertConflictAuditFK", () => {
  it("throws ConflictAuditFKError on failure", () => {
    const db = makeStubDb({ entities: new Set(), relations: new Set() });
    let caught: unknown;
    try {
      assertConflictAuditFK(db, {
        subject_entity_id: 1,
        target_relation_ids: [10],
      });
    } catch (e) {
      caught = e;
    }
    assert.equal(caught instanceof ConflictAuditFKError, true);
    assert.equal((caught as ConflictAuditFKError).result.valid, false);
  });

  it("does not throw on success", () => {
    const db = makeStubDb({ entities: new Set([1]), relations: new Set([10]) });
    assert.doesNotThrow(() =>
      assertConflictAuditFK(db, {
        subject_entity_id: 1,
        target_relation_ids: [10],
      }),
    );
  });
});
