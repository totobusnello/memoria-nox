/**
 * Tests for src/observability/cardinality.ts (T8 — 8 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  CardinalityGuard,
  applyDefaultPolicies,
} from "../cardinality.ts";

test("T8.1 guard admits within budget", () => {
  const g = new CardinalityGuard(() => {});
  g.policy("m", { maxSeries: 3 });
  for (let i = 0; i < 3; i++) {
    const out = g.guard("m", { k: `v${i}` });
    assert.ok(out, `series ${i} should be admitted`);
  }
});

test("T8.2 guard drops over budget", () => {
  const logs: string[] = [];
  const g = new CardinalityGuard((m) => logs.push(m));
  g.policy("m", { maxSeries: 2 });
  assert.ok(g.guard("m", { k: "a" }));
  assert.ok(g.guard("m", { k: "b" }));
  assert.equal(g.guard("m", { k: "c" }), null);
  assert.equal(g.guard("m", { k: "d" }), null);
  assert.equal(g.dropCount("m"), 2);
  assert.ok(logs.some((l) => l.includes("cardinality")));
});

test("T8.3 same label-set is idempotent (no new series counted)", () => {
  const g = new CardinalityGuard(() => {});
  g.policy("m", { maxSeries: 1 });
  assert.ok(g.guard("m", { k: "a" }));
  assert.ok(g.guard("m", { k: "a" }));
  assert.ok(g.guard("m", { k: "a" }));
  assert.equal(g.seriesCount("m"), 1);
});

test("T8.4 allowlist rewrites unknown values to 'other'", () => {
  const g = new CardinalityGuard(() => {});
  g.policy("m", {
    maxSeries: 10,
    labelAllowlist: { method: ["cli", "api"] },
  });
  const a = g.guard("m", { method: "cli" });
  const b = g.guard("m", { method: "evil-payload-xyz" });
  assert.equal(a?.method, "cli");
  assert.equal(b?.method, "other");
});

test("T8.5 denylist strips forbidden labels", () => {
  const g = new CardinalityGuard(() => {});
  g.policy("m", { maxSeries: 10, labelDenylist: ["user_id", "query"] });
  const out = g.guard("m", { method: "api", user_id: "42", query: "secret" });
  assert.equal(out?.method, "api");
  assert.equal(out?.user_id, undefined);
  assert.equal(out?.query, undefined);
});

test("T8.6 default policies forbid user_id everywhere", () => {
  const g = new CardinalityGuard(() => {});
  applyDefaultPolicies(g);
  const cases = [
    "nox_search_requests_total",
    "nox_answer_requests_total",
    "nox_provider_calls_total",
    "nox_viewer_events_total",
  ];
  for (const m of cases) {
    const out = g.guard(m, { user_id: "alice", method: "api" });
    assert.equal(out?.user_id, undefined, `${m} must strip user_id`);
  }
});

test("T8.7 default policies allow legitimate method values", () => {
  const g = new CardinalityGuard(() => {});
  applyDefaultPolicies(g);
  const ok = g.guard("nox_search_requests_total", {
    method: "cli",
    outcome: "success",
  });
  assert.equal(ok?.method, "cli");
  assert.equal(ok?.outcome, "success");
});

test("T8.8 warn cooldown — multiple drops, one log per minute", () => {
  const logs: string[] = [];
  const g = new CardinalityGuard((m) => logs.push(m));
  g.policy("m", { maxSeries: 1 });
  g.guard("m", { k: "a" });
  for (let i = 0; i < 50; i++) {
    g.guard("m", { k: `over-${i}` });
  }
  // Only one warning expected within 60s window.
  assert.equal(logs.length, 1);
  assert.equal(g.dropCount("m"), 50);
});
