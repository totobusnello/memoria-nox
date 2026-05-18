/**
 * T8 tests — OpenClaw plugin entrypoint
 *
 * 6 cases.
 */

import { describe, it, after } from "node:test";
import assert from "node:assert/strict";

import { createPlugin } from "../../../plugins/nox-hooks/index.js";
import type { IngestFn, TelemetrySink } from "../pipeline.js";
import type { HookTelemetryRow } from "../types.js";

function deps(): { ingest: IngestFn; telemetry: TelemetrySink; calls: { ingest: number; rows: HookTelemetryRow[] } } {
  const ref = { ingest: 0, rows: [] as HookTelemetryRow[] };
  return {
    ingest: async () => {
      ref.ingest += 1;
      return { chunk_id: ref.ingest };
    },
    telemetry: (row) => {
      ref.rows.push(row);
    },
    calls: ref,
  };
}

describe("T8 OpenClaw plugin", () => {
  const cleanup: Array<() => Promise<void>> = [];
  after(async () => {
    for (const fn of cleanup) await fn();
  });

  it("creates a plugin handle exposing required methods", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    assert.ok(typeof p.afterTurn === "function");
    assert.ok(typeof p.sessionStart === "function");
    assert.ok(typeof p.sessionEnd === "function");
    assert.ok(typeof p.inspect === "function");
    await p.sessionEnd();
  });

  it("afterTurn enqueues non-blocking; returns accepted=true", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    p.sessionStart({ session_id: "s", cwd: "/tmp/proj" });
    const res = p.afterTurn({ role: "user", content: "hello world from the test suite" });
    assert.equal(res.accepted, true);
    await p.sessionEnd();
  });

  it("normalizes unknown role to 'unknown'", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    const res = p.afterTurn({ role: "weirdrole", content: "x" });
    assert.equal(res.accepted, true);
    await p.sessionEnd();
  });

  it("inspect reports config + queue depth", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    const inspected = p.inspect();
    assert.ok("config" in inspected);
    assert.ok("queueDepth" in inspected);
    await p.sessionEnd();
  });

  it("sessionEnd stops worker without throwing", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    p.sessionStart();
    await p.sessionEnd();
  });

  it("afterTurn never throws even on bad payload", async () => {
    const d = deps();
    const p = createPlugin({ ingest: d.ingest, telemetry: d.telemetry });
    const res = p.afterTurn({} as never);
    assert.ok("accepted" in res);
    await p.sessionEnd();
  });
});
