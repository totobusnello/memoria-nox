/**
 * T11 tests — CLI inspection commands.
 *
 * 6 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { runHooksCommand } from "../../../cli/hooks.js";

const stubDeps = {
  readRecent: async (n: number) => {
    return Array.from({ length: n }).map((_, i) => ({
      event_uuid: `evt_${i}`,
      session_id: "s",
      project_slug: "p",
      kind: "tool_use",
      timestamp: "2026-05-18T00:00:00Z",
      redaction_count: i,
      payload_json: "{}",
    }));
  },
  readStats: async () => ({
    last_24h: { captured: 10, rejected: 5, by_reason: { rate_limited: 2, dedup_hit: 3 } },
    last_7d: { captured: 80, rejected: 40 },
  }),
};

describe("T11 hooks CLI", () => {
  it("status returns config in output", async () => {
    const r = await runHooksCommand(["status"], stubDeps);
    assert.equal(r.ok, true);
    assert.match(r.output, /enabled/);
  });

  it("recent prints metadata only (no payload)", async () => {
    const r = await runHooksCommand(["recent", "3"], stubDeps);
    assert.equal(r.ok, true);
    assert.match(r.output, /evt_0/);
    assert.ok(!r.output.includes('"payload_json"'));
  });

  it("dryrun requires text", async () => {
    const r = await runHooksCommand(["dryrun"], stubDeps);
    assert.equal(r.ok, false);
  });

  it("dryrun runs full pipeline with trace", async () => {
    const r = await runHooksCommand(
      ["dryrun", "This", "is", "a", "long", "enough", "natural", "sentence", "now."],
      stubDeps,
    );
    assert.equal(r.ok, true);
    assert.match(r.output, /dry_run/);
    assert.match(r.output, /trace:/);
  });

  it("stats prints by_reason", async () => {
    const r = await runHooksCommand(["stats"], stubDeps);
    assert.equal(r.ok, true);
    assert.match(r.output, /rate_limited/);
  });

  it("unknown verb errors", async () => {
    const r = await runHooksCommand(["bogus"], stubDeps);
    assert.equal(r.ok, false);
  });
});
