import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseCronExpression,
  nextRunAfter,
  shouldRunScan,
  runScheduledScan,
} from "../scheduler.js";
import { FakeDB, seedEntity, seedRelation } from "./fakes.js";

test("scheduler: parseCronExpression accepts 'M H * * *'", () => {
  const c = parseCronExpression("0 3 * * *");
  assert.equal(c.minute, 0);
  assert.equal(c.hour, 3);
});

test("scheduler: parseCronExpression rejects unsupported patterns", () => {
  assert.throws(() => parseCronExpression("*/5 * * * *"), /invalid cron minute/);
  assert.throws(() => parseCronExpression("0 3 1 * *"), /v1 supports only/);
  assert.throws(() => parseCronExpression("0 25 * * *"), /invalid cron hour/);
  assert.throws(() => parseCronExpression("0 3 *"), /5 fields/);
});

test("scheduler: nextRunAfter advances forward correctly across the boundary", () => {
  const cron = parseCronExpression("30 4 * * *");
  // 2026-05-18 09:00 UTC = 2026-05-18 06:00 BRT → next 04:30 BRT is 2026-05-19 04:30 BRT
  const now = Date.UTC(2026, 4, 18, 9, 0, 0);
  const next = nextRunAfter(now, cron, -180);
  const d = new Date(next);
  assert.equal(d.getUTCDate(), 19);
  assert.equal(d.getUTCHours(), 7);  // 04:30 BRT = 07:30 UTC
  assert.equal(d.getUTCMinutes(), 30);
});

test("scheduler: shouldRunScan returns true after first scheduled time has passed", () => {
  const cron = parseCronExpression("0 3 * * *");
  // last run was yesterday at 03:00 BRT; now is today at 04:00 BRT
  const last = Date.UTC(2026, 4, 17, 6, 0, 0); // 03 BRT
  const now = Date.UTC(2026, 4, 18, 7, 0, 0);  // 04 BRT next day → way past 03 BRT
  assert.equal(shouldRunScan(now, last, cron, -180), true);
});

test("scheduler: shouldRunScan false when not yet due", () => {
  const cron = parseCronExpression("0 3 * * *");
  // last run was today at 03 BRT (06 UTC); now is today at 04 BRT (07 UTC)
  const last = Date.UTC(2026, 4, 18, 6, 0, 0);
  const now = Date.UTC(2026, 4, 18, 7, 0, 0);
  assert.equal(shouldRunScan(now, last, cron, -180), false);
});

test("scheduler: runScheduledScan returns 'disabled' when mode disabled", () => {
  const db = new FakeDB();
  const r = runScheduledScan(db, { modeOverride: "disabled" });
  assert.equal(r.ran, false);
  assert.equal(r.reason, "disabled");
  assert.equal(r.result, null);
});

test("scheduler: runScheduledScan executes when due", () => {
  const db = new FakeDB();
  seedEntity(db, 1, "toto");
  seedEntity(db, 100, "opus");
  seedEntity(db, 101, "sonnet");
  seedRelation(db, { id: 10, source_entity_id: 1, predicate: "uses_model", target_entity_id: 100, confidence: 0.9 });
  seedRelation(db, { id: 11, source_entity_id: 1, predicate: "uses_model", target_entity_id: 101, confidence: 0.85 });
  // Force "due" by passing last-run very far in the past + now at a time after 03 BRT.
  const last = 0;
  const now = Date.UTC(2026, 4, 18, 10, 0, 0); // 07 BRT
  const r = runScheduledScan(db, {
    modeOverride: "shadow",
    now,
    lastRunAt: last,
  });
  assert.equal(r.ran, true);
  assert.ok(r.result);
  assert.equal(r.result!.detected, 1);
});
