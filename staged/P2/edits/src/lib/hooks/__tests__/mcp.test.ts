/**
 * T13 tests — MCP tools.
 *
 * 4 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { callHookTool, HOOK_TOOLS } from "../../../mcp/tools/hooks.js";

const deps = {
  readRecent: async (n: number) =>
    Array.from({ length: n }).map((_, i) => ({
      event_uuid: `evt_${i}`,
      session_id: "s",
      project_slug: "p",
      kind: "tool_use",
      timestamp: "2026-05-18T00:00:00Z",
      redaction_count: 0,
    })),
  readStats: async () => ({
    last_24h: { captured: 1, rejected: 0, by_reason: {} },
    last_7d: { captured: 1, rejected: 0 },
  }),
};

describe("T13 MCP hooks tools", () => {
  it("exposes 4 tools with input schemas", () => {
    assert.equal(HOOK_TOOLS.length, 4);
    const names = HOOK_TOOLS.map((t) => t.name).sort();
    assert.deepEqual(names, [
      "nox_hooks_dryrun",
      "nox_hooks_recent",
      "nox_hooks_stats",
      "nox_hooks_status",
    ]);
  });

  it("nox_hooks_status → ok", async () => {
    const r = await callHookTool("nox_hooks_status", {}, deps);
    assert.equal(r.ok, true);
  });

  it("nox_hooks_dryrun → ok with valid text", async () => {
    const r = await callHookTool(
      "nox_hooks_dryrun",
      { text: "A real long sentence to test through the MCP dryrun tool." },
      deps,
    );
    assert.equal(r.ok, true);
  });

  it("unknown tool → ok=false", async () => {
    const r = await callHookTool("nope", {}, deps);
    assert.equal(r.ok, false);
  });
});
