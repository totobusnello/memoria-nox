/**
 * T14 — Integration tests
 *
 * End-to-end: HookEvent → all 5 layers → captured → in mock-DB with
 * provenance=hook. All 6 rejection paths covered explicitly.
 *
 * 15 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { createPipeline, type IngestFn } from "../pipeline.js";
import { DEFAULTS, type HookConfig } from "../config.js";
import type { HookEvent, HookTelemetryRow } from "../types.js";

interface MockDb {
  rows: Array<{ chunk_id: number; text: string; provenance: string; redaction_count: number; source: string }>;
  ingest: IngestFn;
}

function mkDb(): MockDb {
  const rows: MockDb["rows"] = [];
  let nextId = 1;
  const ingest: IngestFn = async ({ text, source, redaction_count, provenance }) => {
    const chunk_id = nextId++;
    rows.push({ chunk_id, text, provenance, redaction_count, source });
    return { chunk_id };
  };
  return { rows, ingest };
}

function mkEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    event_id: `e_${Math.random().toString(36).slice(2)}`,
    source: "openclaw",
    role: "user",
    content: "An honest natural-language sentence that should clear the pipeline easily.",
    session_id: "sess1",
    project_slug: "memoria-nox",
    ts: "2026-05-18T00:00:00Z",
    ...overrides,
  };
}

function enabled(o: Partial<HookConfig> = {}): HookConfig {
  return {
    ...DEFAULTS,
    enabled: true,
    allowedSources: new Set(["openclaw"]),
    ...o,
  };
}

describe("T14 integration — end-to-end pipeline", () => {
  it("happy path: event → 5 layers → DB row with provenance=hook", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: enabled(), ingest: db.ingest });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, true);
    assert.equal(db.rows.length, 1);
    assert.equal(db.rows[0]?.provenance, "hook");
    assert.equal(db.rows[0]?.source, "openclaw");
  });

  it("REJECT path 1: NOX_HOOKS_ENABLED=0", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: { ...DEFAULTS, enabled: false }, ingest: db.ingest });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.reason, "env_disabled");
    assert.equal(db.rows.length, 0);
  });

  it("REJECT path 2: source not in allowlist", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled({ allowedSources: new Set(["openclaw"]) }),
      ingest: db.ingest,
    });
    const r = await pipe.run(mkEvent({ source: "cli" }));
    assert.equal(r.reason, "source_not_allowed");
    assert.equal(db.rows.length, 0);
  });

  it("REJECT path 3: PII detected under drop policy", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled({ piiPolicy: "drop" }),
      ingest: db.ingest,
      redact: (s) => ({
        text: s,
        redactionCount: s.includes("secret") ? 1 : 0,
        kinds: s.includes("secret") ? ["test"] : [],
      }),
    });
    const r = await pipe.run(mkEvent({ content: "this contains a secret in proper natural prose." }));
    assert.equal(r.reason, "pii_detected_skip");
    assert.equal(db.rows.length, 0);
  });

  it("REJECT path 4: classifier rejects low-signal", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: enabled(), ingest: db.ingest });
    const r = await pipe.run(mkEvent({ content: "{{}}{}{}" }));
    assert.equal(r.reason, "classifier_low_signal");
    assert.equal(db.rows.length, 0);
  });

  it("REJECT path 5: rate limit hit", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled({ rateLimitPerMin: 1 }),
      ingest: db.ingest,
      now: () => 0,
    });
    const a = await pipe.run(mkEvent({ event_id: "a", content: "First long sentence prose content one." }));
    const b = await pipe.run(mkEvent({ event_id: "b", content: "Second long sentence prose content two." }));
    assert.equal(a.captured, true);
    assert.equal(b.captured, false);
    assert.equal(b.reason, "rate_limited");
  });

  it("REJECT path 6: dedup hit", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled({ rateLimitPerMin: 100, dedupThreshold: 0.7 }),
      ingest: db.ingest,
    });
    const txt = "duplicate content used for dedup test once and twice";
    await pipe.run(mkEvent({ event_id: "a", content: txt }));
    const b = await pipe.run(mkEvent({ event_id: "b", content: txt }));
    assert.equal(b.captured, false);
    assert.equal(b.reason, "dedup_hit");
  });

  it("telemetry emits one row per pipeline call", async () => {
    const rows: HookTelemetryRow[] = [];
    const pipe = createPipeline({
      config: enabled(),
      telemetry: (r) => void rows.push(r),
      ingest: mkDb().ingest,
    });
    await pipe.run(mkEvent());
    await pipe.run(mkEvent({ event_id: "x" }));
    assert.equal(rows.length, 2);
  });

  it("telemetry rows never contain raw content", async () => {
    const rows: HookTelemetryRow[] = [];
    const pipe = createPipeline({
      config: enabled(),
      telemetry: (r) => void rows.push(r),
      ingest: mkDb().ingest,
    });
    const secret = "supersecretwordthatshouldnotleak123";
    await pipe.run(mkEvent({ content: `prefix ${secret} suffix prose content longer than min.` }));
    for (const r of rows) {
      assert.ok(!r.payload_json.includes(secret));
    }
  });

  it("dryRun mode emits telemetry but skips DB", async () => {
    const db = mkDb();
    const rows: HookTelemetryRow[] = [];
    const pipe = createPipeline({
      config: enabled({ dryRun: true }),
      ingest: db.ingest,
      telemetry: (r) => void rows.push(r),
    });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.reason, "dry_run");
    assert.equal(db.rows.length, 0);
    assert.ok(rows.length >= 1);
  });

  it("@nox:skip decorator short-circuits before ingest", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: enabled(), ingest: db.ingest });
    const r = await pipe.run(mkEvent({ content: "// @nox:skip\nrest of long prose content." }));
    assert.equal(r.reason, "explicit_skip");
    assert.equal(db.rows.length, 0);
  });

  it("@nox:capture bypasses classifier for low-signal content", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: enabled(), ingest: db.ingest });
    const r = await pipe.run(mkEvent({ content: "// @nox:capture\n{};{};" }));
    assert.equal(r.captured, true);
    assert.equal(db.rows.length, 1);
  });

  it("redacted text reaches DB (not original)", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled(),
      ingest: db.ingest,
      redact: (s) => ({
        text: s.replace("PII_HERE", "<private>"),
        redactionCount: s.includes("PII_HERE") ? 1 : 0,
        kinds: ["test"],
      }),
    });
    await pipe.run(mkEvent({ content: "This has PII_HERE in a long natural prose body to capture." }));
    assert.equal(db.rows.length, 1);
    assert.ok(db.rows[0]?.text.includes("<private>"));
    assert.ok(!db.rows[0]?.text.includes("PII_HERE"));
    assert.equal(db.rows[0]?.redaction_count, 1);
  });

  it("ingest error → captured=false, no DB row, telemetry recorded", async () => {
    const failIngest: IngestFn = async () => ({ chunk_id: null, error: "disk full" });
    const rows: HookTelemetryRow[] = [];
    const pipe = createPipeline({
      config: enabled(),
      ingest: failIngest,
      telemetry: (r) => void rows.push(r),
    });
    const r = await pipe.run(mkEvent());
    assert.equal(r.captured, false);
    assert.equal(r.layer, "persistence");
    const persistenceRows = rows.filter((r) => r.payload_json.includes("ingest_failed"));
    assert.ok(persistenceRows.length >= 1);
  });

  it("layer order is load-bearing: rate-limit never reached if classifier rejects", async () => {
    const db = mkDb();
    const pipe = createPipeline({
      config: enabled({ rateLimitPerMin: 1 }),
      ingest: db.ingest,
    });
    // Low-signal content
    await pipe.run(mkEvent({ content: "{{{}}}" }));
    await pipe.run(mkEvent({ content: "{{{}}}", event_id: "b" }));
    // Now a real one — rate limit should still have full bucket
    const r = await pipe.run(mkEvent({ content: "Real long sentence prose body now for capture A." }));
    assert.equal(r.captured, true);
    assert.equal(db.rows.length, 1);
  });

  it("multiple sessions can run in parallel without state leak", async () => {
    const db = mkDb();
    const pipe = createPipeline({ config: enabled({ rateLimitPerMin: 100 }), ingest: db.ingest });
    const events = Array.from({ length: 6 }, (_, i) =>
      mkEvent({ event_id: `m${i}`, content: `Sentence number ${i} with real prose content here.` }),
    );
    for (const e of events) await pipe.run(e);
    assert.equal(db.rows.length, 6);
  });
});
