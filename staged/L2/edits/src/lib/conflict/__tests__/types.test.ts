import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_MIN_CONFIDENCE,
  DEFAULT_SCAN_LIMIT,
  DEFAULT_EVIDENCE_SNIPPET_LEN,
  DEFAULT_CONFLICT_MODE,
  type Conflict,
  type VariantRelation,
  type ConflictAuditRow,
  type ResolutionInput,
} from "../types.js";

test("types: DEFAULT_MIN_CONFIDENCE matches spec §3 (0.5)", () => {
  assert.equal(DEFAULT_MIN_CONFIDENCE, 0.5);
});

test("types: DEFAULT_SCAN_LIMIT bounded (avoid runaway result sets)", () => {
  assert.ok(DEFAULT_SCAN_LIMIT > 0 && DEFAULT_SCAN_LIMIT <= 10_000);
});

test("types: DEFAULT_EVIDENCE_SNIPPET_LEN UI-renderable size", () => {
  assert.ok(DEFAULT_EVIDENCE_SNIPPET_LEN >= 80 && DEFAULT_EVIDENCE_SNIPPET_LEN <= 1_000);
});

test("types: DEFAULT_CONFLICT_MODE is 'disabled' (shadow-first rule)", () => {
  // Spec regra de ouro #1 — default disabled, opt-in via env.
  assert.equal(DEFAULT_CONFLICT_MODE, "disabled");
});

test("types: Conflict shape minimum required fields compile", () => {
  const variant: VariantRelation = {
    relation_id: 1,
    target_entity_id: 99,
    confidence: 0.8,
    created_at: Date.now(),
  };
  const c: Conflict = {
    kind: "direct",
    subject_entity_id: 42,
    predicate: "has_status",
    variants: [variant, { ...variant, relation_id: 2, target_entity_id: 100 }],
  };
  assert.equal(c.variants.length, 2);
  assert.equal(c.kind, "direct");
  assert.equal(c.subject_entity_id, 42);
});

test("types: ConflictAuditRow status enum covers spec §5 lifecycle", () => {
  const row: ConflictAuditRow = {
    id: 1,
    ts: Date.now(),
    kind: "direct",
    subject_entity_id: 1,
    predicate: "x",
    target_relation_ids: [1, 2],
    variants: [],
    status: "open",
    resolved_by: null,
    resolved_at: null,
    resolution_kind: null,
    picked_relation_id: null,
    merge_target: null,
    notes: null,
    shadow_mode: 1,
  };
  assert.equal(row.status, "open");
  assert.equal(row.shadow_mode, 1);

  // Cycle through all expected status values — TS will reject typos at compile time.
  // Use the broader ConflictStatus type rather than typeof row.status (narrowed to 'open').
  const statuses: Array<import("../types.js").ConflictStatus> = [
    "open",
    "reviewed",
    "resolved_pick_one",
    "resolved_both_valid",
    "resolved_merged",
    "dismissed",
  ];
  assert.equal(statuses.length, 6);
});

test("types: ResolutionInput excludes 'open'/'reviewed' from status", () => {
  // 'open' and 'reviewed' are NOT terminal statuses — ResolutionInput rejects them at compile time.
  const r: ResolutionInput = {
    status: "resolved_pick_one",
    resolved_by: "toto",
    resolution_kind: "pick_one",
    picked_relation_id: 7,
  };
  assert.equal(r.status, "resolved_pick_one");
  assert.equal(r.resolution_kind, "pick_one");

  // Type-level negative test (caught by tsc): the following would not compile:
  //   const bad: ResolutionInput = { status: "open", ... };
});
