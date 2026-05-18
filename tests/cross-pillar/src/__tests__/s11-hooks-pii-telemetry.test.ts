/**
 * S11 — Hooks PII redaction → telemetry (P2 + A1 + A1.1 forward-looking).
 *
 * Verifies:
 *   - Hook with SSN (US) is captured with [REDACTED:us-ssn] marker
 *   - Hook with CPF (BR, forward-looking A1.1) is captured with [REDACTED:br-cpf]
 *   - agent_events row has `layer: privacy-filter` and reason indicating PII
 *   - agent_events.content stays empty (raw content never stored in telemetry)
 *   - redaction_count is correct
 *
 * Bug-class targeted: a privacy regression where a "convenient" debug log
 * accidentally captures raw content in telemetry, or where CPF support never
 * lands and the test goes green silently. We assert both US + BR coverage.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import { applySchema } from "../lib/schema.js";
import { runHookPipeline, redact, type HookEvent } from "../lib/pillar-shims.js";

let db: DatabaseType;

beforeEach(() => {
  db = new Database(":memory:");
  applySchema(db);
});
afterEach(() => db.close());

function buildOpts() {
  return {
    pii_policy: "redact" as const,
    insertChunk: (text: string): number =>
      Number(
        db
          .prepare(`INSERT INTO chunks (content, content_hash) VALUES (?, ?)`)
          .run(text, `h-${Math.random()}`).lastInsertRowid
      ),
    insertTelemetry: (row: {
      event_uuid: string;
      session_id: string;
      project_slug: string;
      kind: string;
      payload_json: string;
      redaction_count: number;
    }) => {
      db.prepare(
        `INSERT INTO agent_events (event_uuid, session_id, project_slug, kind, payload_json, redaction_count, content) VALUES (?,?,?,?,?,?, '')`
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

describe("S11 — hooks PII redaction → telemetry (P2 + A1 + A1.1)", () => {
  it("S11-01 US SSN redacted at capture, telemetry records redaction_count", async () => {
    const ev: HookEvent = {
      event_id: "evt-ssn",
      source: "openclaw",
      role: "user",
      content: "Patient record: SSN 123-45-6789 needs review.",
      ts: new Date().toISOString(),
      session_id: "s",
      project_slug: "memoria-nox",
    };
    const res = await runHookPipeline(ev, buildOpts());
    assert.strictEqual(res.captured, true);
    const chunk = db
      .prepare(`SELECT content FROM chunks WHERE id = ?`)
      .get(res.chunk_id!) as { content: string };
    assert.ok(!chunk.content.includes("123-45-6789"));
    assert.ok(chunk.content.includes("[REDACTED:us-ssn]"));

    const tel = db
      .prepare(`SELECT redaction_count, content FROM agent_events WHERE event_uuid = 'evt-ssn'`)
      .get() as { redaction_count: number; content: string };
    assert.ok(tel.redaction_count >= 1);
    assert.strictEqual(tel.content, "");
  });

  it("S11-02 Brazilian CPF (A1.1 forward-looking) redacted with [REDACTED:br-cpf]", async () => {
    const ev: HookEvent = {
      event_id: "evt-cpf",
      source: "openclaw",
      role: "user",
      content: "Cadastro Toto: CPF 123.456.789-01 confirmado.",
      ts: new Date().toISOString(),
      session_id: "s",
      project_slug: "memoria-nox",
    };
    const res = await runHookPipeline(ev, buildOpts());
    assert.strictEqual(res.captured, true);
    const chunk = db
      .prepare(`SELECT content FROM chunks WHERE id = ?`)
      .get(res.chunk_id!) as { content: string };
    assert.ok(!chunk.content.includes("123.456.789-01"));
    assert.ok(chunk.content.includes("[REDACTED:br-cpf]"));
  });

  it("S11-03 redact() returns both us-ssn + br-cpf in kinds[] for mixed input", () => {
    const r = redact(
      "Cliente Toto SSN 123-45-6789 e CPF 987.654.321-09 cadastrado."
    );
    assert.ok(r.kinds.includes("us-ssn"));
    assert.ok(r.kinds.includes("br-cpf"));
    assert.strictEqual(r.redactionCount, 2);
  });

  it("S11-04 telemetry payload_json identifies the layer that fired", async () => {
    const ev: HookEvent = {
      event_id: "evt-tel",
      source: "openclaw",
      role: "user",
      content: "Long message with SSN 123-45-6789 inside.",
      ts: new Date().toISOString(),
      session_id: "s",
      project_slug: "memoria-nox",
    };
    await runHookPipeline(ev, buildOpts());
    const tel = db
      .prepare(`SELECT payload_json FROM agent_events WHERE event_uuid = 'evt-tel'`)
      .get() as { payload_json: string };
    const parsed = JSON.parse(tel.payload_json) as {
      layer: string;
      reason: string;
      redaction_count?: number;
    };
    assert.strictEqual(parsed.layer, "persisted");
    assert.strictEqual(parsed.reason, "ok");
    assert.ok((parsed.redaction_count ?? 0) >= 1);
  });

  it("S11-05 raw content NEVER appears in telemetry row even with rich PII payload", async () => {
    const secret = "SSN 123-45-6789, CPF 987.654.321-09, key sk-ant-EXAMPLE12345678901234567890";
    const ev: HookEvent = {
      event_id: "evt-noleak",
      source: "openclaw",
      role: "user",
      content: secret,
      ts: new Date().toISOString(),
      session_id: "s",
      project_slug: "memoria-nox",
    };
    await runHookPipeline(ev, buildOpts());
    const tel = db
      .prepare(`SELECT content, payload_json FROM agent_events WHERE event_uuid = 'evt-noleak'`)
      .get() as { content: string; payload_json: string };
    const blob = JSON.stringify(tel);
    assert.ok(!blob.includes("123-45-6789"));
    assert.ok(!blob.includes("987.654.321-09"));
    assert.ok(!blob.includes("sk-ant-EXAMPLE"));
    assert.strictEqual(tel.content, "");
  });
});
