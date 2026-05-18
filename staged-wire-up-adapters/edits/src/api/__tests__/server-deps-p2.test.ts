/**
 * Tests for `src/api/server-deps-p2.ts` + `src/lib/hooks/server-deps.ts`.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  buildHooksDeps,
  __setQueueProbeForTests,
  __resetHooksDepsForTests,
} from "../../lib/hooks/server-deps.js";
import {
  dryRunHook,
  warmupHooksDeps,
} from "../server-deps-p2.js";
import {
  __setDbFactoryForTests,
  resetDepsRegistryForTests,
} from "../../lib/deps/deps-registry.js";

beforeEach(() => {
  resetDepsRegistryForTests();
  __resetHooksDepsForTests();
});

describe("server-deps-p2: buildHooksDeps", () => {
  it("returns readRecent + inspectQueue when DB unavailable", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildHooksDeps();
    assert.equal(typeof deps.readRecent, "function");
    assert.equal(typeof deps.inspectQueue, "function");
    const rows = await deps.readRecent(20);
    assert.deepEqual(rows, []);
  });

  it("readRecent returns rows from agent_events when table present", async () => {
    const rows = [
      {
        event_uuid: "u1",
        session_id: "s1",
        project_slug: "p1",
        kind: "user",
        timestamp: "2026-05-18T00:00:00Z",
        redaction_count: 0,
      },
      {
        event_uuid: "u2",
        session_id: "s1",
        project_slug: "p1",
        kind: "assistant",
        timestamp: "2026-05-18T00:00:01Z",
        redaction_count: 1,
      },
    ];
    const fake = {
      prepare(_sql: string) {
        return {
          all<T = unknown>(): T[] {
            return rows as T[];
          },
          get() {
            return undefined;
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildHooksDeps();
    const out = await deps.readRecent(10);
    assert.equal(out.length, 2);
    assert.equal(out[0]!.event_uuid, "u1");
  });

  it("readRecent caps limit defensively", async () => {
    const captured: unknown[][] = [];
    const fake = {
      prepare(_sql: string) {
        return {
          all<T = unknown>(...params: unknown[]): T[] {
            captured.push(params);
            return [] as T[];
          },
          get() {
            return undefined;
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildHooksDeps();
    await deps.readRecent(9999);
    assert.equal(captured[0]![0], 500); // capped to 500
  });

  it("readRecent returns empty when table missing", async () => {
    const fake = {
      prepare(_sql: string) {
        return {
          all() {
            throw new Error("no such table: agent_events");
          },
          get() {
            return undefined;
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildHooksDeps();
    const out = await deps.readRecent(20);
    assert.deepEqual(out, []);
  });

  it("inspectQueue uses test override when set", async () => {
    __setQueueProbeForTests(() => ({ queueDepth: 42, rateLimitTokens: 12 }));
    const deps = await buildHooksDeps();
    const q = deps.inspectQueue!();
    assert.equal(q.queueDepth, 42);
    assert.equal(q.rateLimitTokens, 12);
  });

  it("inspectQueue falls back to {queueDepth: 0} when worker module absent", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildHooksDeps();
    const q = deps.inspectQueue!();
    assert.equal(q.queueDepth, 0);
  });

  it("buildHooksDeps overrides honor passed readRecent", async () => {
    const custom = async (n: number) => [
      {
        event_uuid: `custom-${n}`,
        session_id: "x",
        project_slug: "y",
        kind: "user",
        timestamp: "z",
        redaction_count: 0,
      },
    ];
    const deps = await buildHooksDeps({ readRecent: custom });
    const out = await deps.readRecent(3);
    assert.equal(out[0]!.event_uuid, "custom-3");
  });

  it("warmupHooksDeps resolves without error", async () => {
    __setDbFactoryForTests(() => null);
    await warmupHooksDeps();
    // No assertion needed — no-throw == pass.
  });

  it("dryRunHook returns null when staged-P2 modules absent", async () => {
    // The dynamic import targets ../lib/hooks/config.js + pipeline.js,
    // which are not in the staged-wire-up-adapters tree.
    const out = await dryRunHook("hello world");
    assert.equal(out, null);
  });
});
