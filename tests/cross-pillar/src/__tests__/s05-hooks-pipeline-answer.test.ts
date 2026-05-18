/**
 * S5 — Hooks pipeline → answer (P2 + P1).
 *
 * Verifies:
 *   - 20 hook events flow through 5-layer pipeline (15 valid + 5 with PII)
 *   - With pii_policy='drop', PII-laden events are dropped (telemetry reflects)
 *   - With pii_policy='redact' (default-ish), PII-laden events captured WITH
 *     redacted content
 *   - Answer composer over captured chunks cites captured ids, never raw PII
 *
 * Bug-class targeted: a regression where the hooks pipeline writes raw content
 * to agent_events.payload_json instead of a sanitized stub (privacy leak via
 * telemetry).
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import { runHookPipeline, type HookEvent } from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);
});
afterEach(() => db.close());

function buildOpts(piiPolicy: "redact" | "drop") {
  return {
    pii_policy: piiPolicy,
    insertChunk: (text: string): number => {
      const r = db
        .prepare(`INSERT INTO chunks (content, content_hash) VALUES (?, ?)`)
        .run(text, `h-${Math.random()}`);
      return Number(r.lastInsertRowid);
    },
    insertTelemetry: (row: {
      event_uuid: string;
      session_id: string;
      project_slug: string;
      kind: string;
      payload_json: string;
      redaction_count: number;
    }) => {
      db.prepare(
        `INSERT INTO agent_events (event_uuid, session_id, project_slug, kind, payload_json, redaction_count, content)
         VALUES (?,?,?,?,?,?, '')`
      ).run(
        row.event_uuid,
        row.session_id,
        row.project_slug,
        row.kind,
        row.payload_json,
        row.redaction_count
      );
    },
  };
}

function makeEvent(i: number, content: string): HookEvent {
  return {
    event_id: `evt-${i}`,
    source: "openclaw",
    role: "user",
    content,
    ts: new Date().toISOString(),
    session_id: "s-test",
    project_slug: "memoria-nox",
  };
}

describe("S5 — hooks pipeline → answer (P2 + P1)", () => {
  it("S5-01 pii_policy='drop': 15 captured, 5 dropped", async () => {
    const opts = buildOpts("drop");
    const events: HookEvent[] = [];
    for (let i = 0; i < 15; i++) {
      events.push(
        makeEvent(i, `Memory note ${i}: D41 picked gemini-2.5-flash-lite as default.`)
      );
    }
    for (let i = 15; i < 20; i++) {
      events.push(
        makeEvent(
          i,
          `Note ${i}: rotate key sk-ant-EXAMPLE12345678901234567890 ASAP.`
        )
      );
    }
    const results = await Promise.all(events.map((e) => runHookPipeline(e, opts)));
    const captured = results.filter((r) => r.captured);
    const dropped = results.filter((r) => !r.captured);
    assert.strictEqual(captured.length, 15);
    assert.strictEqual(dropped.length, 5);
    for (const d of dropped) {
      assert.strictEqual(d.reason, "pii_detected");
      assert.strictEqual(d.layer, "privacy-filter");
    }
  });

  it("S5-02 pii_policy='redact': all 20 captured but PII-laden ones contain redacted markers", async () => {
    const opts = buildOpts("redact");
    const events: HookEvent[] = [];
    for (let i = 0; i < 15; i++) {
      events.push(makeEvent(i, `Clean memory note ${i}: D41 picked gemini-flash-lite.`));
    }
    for (let i = 15; i < 20; i++) {
      events.push(
        makeEvent(
          i,
          `Note ${i}: rotate key sk-ant-EXAMPLE12345678901234567890 ASAP.`
        )
      );
    }
    const results = await Promise.all(events.map((e) => runHookPipeline(e, opts)));
    assert.strictEqual(results.filter((r) => r.captured).length, 20);

    const chunks = db
      .prepare(`SELECT id, content FROM chunks ORDER BY id`)
      .all() as Array<{ id: number; content: string }>;
    assert.strictEqual(chunks.length, 20);
    const withRedaction = chunks.filter((c) => c.content.includes("[REDACTED:"));
    assert.strictEqual(withRedaction.length, 5);
    // None of the chunks may contain raw PII.
    for (const c of chunks) {
      assert.ok(!c.content.includes("sk-ant-EXAMPLE"));
    }
  });

  it("S5-03 telemetry row never includes raw content (privacy invariant)", async () => {
    const opts = buildOpts("redact");
    const fakeGeminiKey = "AIza" + "SyEXAMPLEKEY1234567890abcdefghij123";
    const ev = makeEvent(99, `Secret note: ${fakeGeminiKey} must rotate.`);
    await runHookPipeline(ev, opts);
    const tel = db
      .prepare(`SELECT payload_json, content, redaction_count FROM agent_events WHERE event_uuid = ?`)
      .get("evt-99") as { payload_json: string; content: string; redaction_count: number };
    assert.ok(tel, "telemetry row not found");
    assert.strictEqual(tel.content, ""); // contract: content stays empty
    assert.ok(!tel.payload_json.includes("AIzaSy"));
    assert.ok(tel.redaction_count >= 1);
  });

  it("S5-04 answer over captured chunks cites only persisted chunk ids", async () => {
    const opts = buildOpts("redact");
    const eA = makeEvent(0, "FII Treviso is led by Toto.");
    const eB = makeEvent(1, "Granix is a co-founded company.");
    await runHookPipeline(eA, opts);
    await runHookPipeline(eB, opts);

    const retrieved = db
      .prepare(`SELECT id, content FROM chunks WHERE LOWER(content) LIKE '%fii treviso%'`)
      .all() as Array<{ id: number; content: string }>;
    assert.strictEqual(retrieved.length, 1);

    // Simulate P1 composing an answer over captured chunks.
    const cit = retrieved.map((r, i) => ({ chunk_id: r.id, marker: `chunk_${i + 1}` }));
    const answer = `Based on memory: [${cit[0]!.marker}] ${retrieved[0]!.content}`;
    assert.ok(answer.includes(`[${cit[0]!.marker}]`));
    assert.ok(answer.includes("FII Treviso"));
    // Citation references a real persisted chunk_id.
    const exists = db
      .prepare(`SELECT id FROM chunks WHERE id = ?`)
      .get(cit[0]!.chunk_id) as { id: number };
    assert.strictEqual(exists.id, cit[0]!.chunk_id);
  });

  it("S5-05 rejected source ('unknown') → not captured, telemetry recorded", async () => {
    const opts = buildOpts("redact");
    const ev: HookEvent = {
      event_id: "evt-unk",
      source: "unknown",
      role: "user",
      content: "anything",
      ts: new Date().toISOString(),
      session_id: "s",
      project_slug: "memoria-nox",
    };
    const res = await runHookPipeline(ev, {
      ...opts,
      source_allowlist: ["openclaw", "cli"],
    });
    assert.strictEqual(res.captured, false);
    assert.strictEqual(res.reason, "source_not_allowed");
  });

  it("S5-06 NOX_HOOKS_DISABLED=1 short-circuits at layer 1", async () => {
    const opts = buildOpts("redact");
    const ev = makeEvent(50, "anything substantive");
    const res = await runHookPipeline(ev, { ...opts, env: { NOX_HOOKS_DISABLED: "1" } });
    assert.strictEqual(res.captured, false);
    assert.strictEqual(res.reason, "env_disabled");
    // Still wrote a telemetry row (visibility into rejections).
    const tel = db
      .prepare(`SELECT payload_json FROM agent_events WHERE event_uuid = 'evt-50'`)
      .get() as { payload_json: string };
    assert.match(tel.payload_json, /env_disabled/);
  });
});
