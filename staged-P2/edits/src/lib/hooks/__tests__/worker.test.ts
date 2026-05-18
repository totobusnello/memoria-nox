/**
 * T9 tests — worker.ts (async queue + drain)
 *
 * 10 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { createWorker } from "../worker.js";
import { createPipeline } from "../pipeline.js";
import { DEFAULTS, type HookConfig } from "../config.js";
import type { HookEvent, HookTelemetryRow } from "../types.js";

function mkEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    event_id: `e_${Math.random()}`,
    source: "openclaw",
    role: "user",
    content: "Sensible long content that should pass classifier threshold easily.",
    session_id: "s",
    project_slug: "p",
    ts: "2026-05-18T00:00:00Z",
    ...overrides,
  };
}

function enabledConfig(o: Partial<HookConfig> = {}): HookConfig {
  return {
    ...DEFAULTS,
    enabled: true,
    allowedSources: new Set(["openclaw"]),
    ...o,
  };
}

describe("T9 worker queue", () => {
  it("enqueue accepts events under capacity", () => {
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, maxSize: 5 });
    for (let i = 0; i < 5; i++) {
      const r = w.enqueue(mkEvent());
      assert.equal(r.accepted, true);
    }
  });

  it("queue full drops oldest + accepts new", () => {
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, maxSize: 2 });
    w.enqueue(mkEvent());
    w.enqueue(mkEvent());
    const r = w.enqueue(mkEvent());
    assert.equal(r.accepted, true);
    assert.match(r.reason, /dropped_oldest/);
    assert.equal(w.stats().dropped, 1);
  });

  it("drain processes all queued events via pipeline", async () => {
    let captured = 0;
    const pipeline = createPipeline({
      config: enabledConfig({ dedupThreshold: 0.99 }),
      ingest: async () => {
        captured += 1;
        return { chunk_id: captured };
      },
    });
    const w = createWorker({ pipeline });
    const distinct = [
      "The user asked about the salience formula in nox-mem today.",
      "We discussed the FTS5 BM25 ranking strategy for hybrid search.",
      "Forge ran a code review on the new privacy filter patterns yesterday.",
    ];
    for (let i = 0; i < 3; i++) {
      w.enqueue(mkEvent({ event_id: `evt_${i}`, content: distinct[i]! }));
    }
    const out = await w.drain();
    assert.equal(out.length, 3);
    assert.equal(captured, 3);
  });

  it("start + stop cleans up timer", async () => {
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, tickMs: 10 });
    w.start();
    await new Promise((r) => setTimeout(r, 30));
    await w.stop();
  });

  it("stats include enqueued/processed/dropped counters", async () => {
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, maxSize: 1 });
    w.enqueue(mkEvent());
    w.enqueue(mkEvent()); // drops one
    const stats = w.stats();
    assert.equal(stats.enqueued, 2);
    assert.equal(stats.dropped, 1);
  });

  it("queueDepth reported", () => {
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, maxSize: 10 });
    w.enqueue(mkEvent());
    w.enqueue(mkEvent());
    assert.equal(w.stats().queueDepth, 2);
  });

  it("pipeline errors do not stop worker", async () => {
    const pipeline = {
      run: async () => {
        throw new Error("boom");
      },
      resetState: () => {},
      inspect: () => ({ config: enabledConfig(), rateLimitTokens: 0, recentBufferSize: 0 }),
    };
    const w = createWorker({ pipeline });
    w.enqueue(mkEvent());
    w.enqueue(mkEvent());
    await w.drain();
    assert.equal(w.stats().errors, 2);
  });

  it("overflow emits telemetry row", () => {
    const rows: HookTelemetryRow[] = [];
    const pipeline = createPipeline({ config: enabledConfig() });
    const w = createWorker({ pipeline, maxSize: 1, telemetry: (r) => void rows.push(r) });
    w.enqueue(mkEvent());
    w.enqueue(mkEvent());
    const overflowRows = rows.filter((r) => r.payload_json.includes("queue_full"));
    assert.ok(overflowRows.length >= 1);
  });

  it("drained pipeline yields HookResult objects", async () => {
    const pipeline = createPipeline({
      config: enabledConfig(),
      ingest: async () => ({ chunk_id: 7 }),
    });
    const w = createWorker({ pipeline });
    w.enqueue(mkEvent());
    const out = await w.drain();
    assert.equal(out.length, 1);
    assert.equal(out[0]?.captured, true);
    assert.equal(out[0]?.chunk_id, 7);
  });

  it("stop drains remaining queue", async () => {
    let captured = 0;
    const pipeline = createPipeline({
      config: enabledConfig({ dedupThreshold: 0.99 }),
      ingest: async () => {
        captured += 1;
        return { chunk_id: captured };
      },
    });
    const w = createWorker({ pipeline, tickMs: 5 });
    w.start();
    const distinct = [
      "The user asked about the cosine threshold for dedup tuning here.",
      "We compared the BM25 ranking output to Gemini embedding cosine output.",
      "Forge spotted a flaky test in the worker drain integration suite.",
    ];
    for (let i = 0; i < 3; i++) {
      w.enqueue(mkEvent({ event_id: `e${i}`, content: distinct[i]! }));
    }
    await w.stop();
    assert.equal(captured, 3);
  });
});
