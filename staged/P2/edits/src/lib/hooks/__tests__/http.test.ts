/**
 * T12 tests — HTTP endpoints (handler-level).
 *
 * 6 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { handleHooksRequest } from "../../../api/hooks.js";

const deps = {
  readRecent: async (n: number) =>
    Array.from({ length: n }).map((_, i) => ({
      event_uuid: `evt_${i}`,
      session_id: "s",
      project_slug: "p",
      kind: "tool_use",
      timestamp: "2026-05-18T00:00:00Z",
      redaction_count: i,
    })),
};

describe("T12 hooks HTTP API", () => {
  it("GET /api/hooks/status returns 200", async () => {
    const r = await handleHooksRequest({ method: "GET", path: "/api/hooks/status" }, deps);
    assert.equal(r.status, 200);
    assert.ok((r.body as { config: unknown }).config);
  });

  it("GET /api/hooks/recent honors limit + drops payload_json", async () => {
    const r = await handleHooksRequest(
      { method: "GET", path: "/api/hooks/recent", query: { limit: "3" } },
      deps,
    );
    assert.equal(r.status, 200);
    const rows = (r.body as { rows: Array<{ event_uuid: string }> }).rows;
    assert.equal(rows.length, 3);
    for (const row of rows) {
      assert.ok(!("payload_json" in row));
    }
  });

  it("POST /api/hooks/dryrun missing text → 400", async () => {
    const r = await handleHooksRequest(
      { method: "POST", path: "/api/hooks/dryrun", body: {} },
      deps,
    );
    assert.equal(r.status, 400);
  });

  it("POST /api/hooks/dryrun valid → 200 + trace", async () => {
    const r = await handleHooksRequest(
      {
        method: "POST",
        path: "/api/hooks/dryrun",
        body: { text: "A real natural language sentence for the dry run test." },
      },
      deps,
    );
    assert.equal(r.status, 200);
    const body = r.body as { result: { dry_run: boolean }; trace: Array<{ layer: string }> };
    assert.equal(body.result.dry_run, true);
    assert.ok(body.trace.length >= 1);
  });

  it("unknown route → 404", async () => {
    const r = await handleHooksRequest({ method: "GET", path: "/api/hooks/wat" }, deps);
    assert.equal(r.status, 404);
  });

  it("readRecent throw → 500", async () => {
    const bad = { readRecent: async () => { throw new Error("db down"); } };
    const r = await handleHooksRequest({ method: "GET", path: "/api/hooks/recent" }, bad);
    assert.equal(r.status, 500);
  });
});
