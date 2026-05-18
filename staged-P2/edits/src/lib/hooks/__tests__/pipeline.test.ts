/**
 * T6 tests — pipeline.ts (full 5-layer orchestrator)
 *
 * 15 cases covering each layer's short-circuit + happy path + dryrun +
 * telemetry rows + decorator overrides + persistence error handling.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { createPipeline, type IngestFn } from "../pipeline.js";
import { loadConfig, DEFAULTS, type HookConfig } from "../config.js";
import type { HookEvent, HookTelemetryRow } from "../types.js";

function mkEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    event_id: "e1",
    source: "openclaw",
    role: "user",
    content: "This is a proper sentence with enough substance for the classifier.",
    session_id: "s1",
    project_slug: "p1",
    ts: "2026-05-18T00:00:00Z",
    ...overrides,
  };
}

function enabledConfig(overrides: Partial<HookConfig> = {}): HookConfig {
  return {
    ...DEFAULTS,
    enabled: true,
    allowedSources: new Set(["openclaw", "cli", "manual", "api"]),
    ...overrides,
  };
}

function mockIngest(): { fn: IngestFn; calls: number; lastArg?: Parameters<IngestFn>[0] } {
  const ref: { fn: IngestFn; calls: number; lastArg?: Parameters<IngestFn>[0] } = {
    fn: async (arg) => {
      ref.calls += 1;
      ref.lastArg = arg;
      return { chunk_id: 42 };
    },
    calls: 0,
  };
  return ref;
}

describe("T6 pipeline (5-layer orchestrator)", () => {
  it("Layer 1: disabled config → env_disabled", async () => {
    const config = loadConfig({});
    const telemetry: HookTelemetryRow[] = [];
    const pipe = createPipeline({ config, telemetry: (r) => void telemetry.push(r) });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.reason, "env_disabled");
    assert.equal(telemetry.length, 1);
  });

  it("Layer 2: source not allowed", async () => {
    const config = enabledConfig({ allowedSources: new Set(["openclaw"]) });
    const pipe = createPipeline({ config });
    const r = await pipe.run(mkEvent({ source: "cli" }));
    assert.equal(r.reason, "source_not_allowed");
    assert.equal(r.layer, "source-allowlist");
  });

  it("Layer 2: unknown role rejected", async () => {
    const config = enabledConfig();
    const pipe = createPipeline({ config });
    const r = await pipe.run(mkEvent({ role: "tool" }));
    assert.equal(r.captured, false);
    assert.equal(r.layer, "source-allowlist");
  });

  it("Layer 3: drop policy + PII → pii_detected_skip", async () => {
    const config = enabledConfig({ piiPolicy: "drop" });
    const ingest = mockIngest();
    const pipe = createPipeline({
      config,
      redact: (s) => ({
        text: s.replace("sk-", "<private>"),
        redactionCount: s.includes("sk-") ? 1 : 0,
        kinds: s.includes("sk-") ? ["openai-key"] : [],
      }),
      ingest: ingest.fn,
    });
    const r = await pipe.run(mkEvent({ content: "leak sk-xxxxxxx and more proper text here." }));
    assert.equal(r.captured, false);
    assert.equal(r.reason, "pii_detected_skip");
    assert.equal(ingest.calls, 0);
  });

  it("Layer 3: redact policy + PII → captures, ingest gets redacted text", async () => {
    const config = enabledConfig();
    const ingest = mockIngest();
    const pipe = createPipeline({
      config,
      redact: (s) => ({
        text: s.replace("sk-secret", "<private>"),
        redactionCount: s.includes("sk-secret") ? 1 : 0,
        kinds: ["openai-key"],
      }),
      ingest: ingest.fn,
    });
    const r = await pipe.run(
      mkEvent({ content: "Here is a proper full sentence containing sk-secret value." }),
    );
    assert.equal(r.captured, true);
    assert.ok(ingest.lastArg?.text.includes("<private>"));
    assert.ok(!ingest.lastArg?.text.includes("sk-secret"));
    assert.equal(ingest.lastArg?.redaction_count, 1);
  });

  it("Layer 4: low-signal text → classifier_low_signal", async () => {
    const config = enabledConfig();
    const pipe = createPipeline({ config });
    const r = await pipe.run(mkEvent({ content: "{};{};" }));
    assert.equal(r.captured, false);
    assert.equal(r.reason, "classifier_low_signal");
  });

  it("Layer 5: rate-limited after N", async () => {
    const config = enabledConfig({ rateLimitPerMin: 2 });
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn, now: () => 0 });
    const a = await pipe.run(mkEvent({ event_id: "a", content: "Sentence A — substantial real content for capture." }));
    const b = await pipe.run(mkEvent({ event_id: "b", content: "Sentence B — substantial real content for capture." }));
    const c = await pipe.run(mkEvent({ event_id: "c", content: "Sentence C — substantial real content for capture." }));
    assert.equal(a.captured, true);
    assert.equal(b.captured, true);
    assert.equal(c.captured, false);
    assert.equal(c.reason, "rate_limited");
  });

  it("Layer 5: dedup rejects identical content", async () => {
    const config = enabledConfig({ rateLimitPerMin: 100, dedupThreshold: 0.85 });
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn });
    const txt = "Exactly the same long sentence used twice for dedup test purposes.";
    const a = await pipe.run(mkEvent({ event_id: "a", content: txt }));
    const b = await pipe.run(mkEvent({ event_id: "b", content: txt }));
    assert.equal(a.captured, true);
    assert.equal(b.captured, false);
    assert.equal(b.reason, "dedup_hit");
  });

  it("happy path: full pipeline captures, ingest called once", async () => {
    const config = enabledConfig();
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, true);
    assert.equal(r.layer, "persisted");
    assert.equal(r.chunk_id, 42);
    assert.equal(ingest.calls, 1);
  });

  it("dryRun mode: pipeline runs but does NOT ingest", async () => {
    const config = enabledConfig({ dryRun: true });
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.reason, "dry_run");
    assert.equal(r.dry_run, true);
    assert.equal(ingest.calls, 0);
  });

  it("@nox:skip decorator short-circuits at decorator layer", async () => {
    const config = enabledConfig();
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn });
    const r = await pipe.run(
      mkEvent({ content: "// @nox:skip\nthis would otherwise be captured easily because long sentence." }),
    );
    assert.equal(r.captured, false);
    assert.equal(r.reason, "explicit_skip");
    assert.equal(r.layer, "decorator");
    assert.equal(ingest.calls, 0);
  });

  it("@nox:capture bypasses classifier but not other layers", async () => {
    const config = enabledConfig();
    const ingest = mockIngest();
    const pipe = createPipeline({ config, ingest: ingest.fn });
    const r = await pipe.run(
      mkEvent({ content: "// @nox:capture\n{};{};" }),  // would have been low-signal
    );
    assert.equal(r.captured, true);
    assert.equal(ingest.calls, 1);
  });

  it("ingest failure → captured=false with persistence layer", async () => {
    const config = enabledConfig();
    const failIngest: IngestFn = async () => ({ chunk_id: null, error: "db_locked" });
    const pipe = createPipeline({ config, ingest: failIngest });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.layer, "persistence");
  });

  it("telemetry emitted for EVERY pipeline run (rejected or captured)", async () => {
    const config = loadConfig({});
    const rows: HookTelemetryRow[] = [];
    const pipe = createPipeline({ config, telemetry: (r) => void rows.push(r) });
    await pipe.run(mkEvent());
    await pipe.run(mkEvent({ event_id: "e2" }));
    assert.equal(rows.length, 2);
    // No raw content
    for (const r of rows) {
      assert.ok(!r.payload_json.includes("proper sentence"));
    }
  });

  it("telemetry throws → does NOT break pipeline", async () => {
    const config = enabledConfig();
    const pipe = createPipeline({
      config,
      telemetry: () => {
        throw new Error("sink down");
      },
      ingest: async () => ({ chunk_id: 1 }),
    });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, true);
  });
});
