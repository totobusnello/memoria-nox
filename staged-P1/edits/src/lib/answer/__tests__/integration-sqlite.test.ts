/**
 * src/lib/answer/__tests__/integration-sqlite.test.ts — P1 T11.
 *
 * End-to-end integration against a REAL `better-sqlite3` in-memory database
 * with the v11 `answer_telemetry` schema applied. NO mocking of the DB
 * (lesson from feedback memory: integration tests that mock the DB are
 * useless — they catch nothing real).
 *
 * Pipeline exercised per call:
 *   question → retrieval (fixture stub) → prompt → MockProvider LLM →
 *     citation parse → telemetry INSERT into real SQLite → query back
 *
 * Coverage (10 tests):
 *   IT-01 happy path persists row with failed_reason=NULL
 *   IT-02 retrieval_empty path persists row with failed_reason=NULL (canonical message)
 *   IT-03 hallucination retry SUCCESS persists row with fallback_used=1, failed_reason=NULL
 *   IT-04 hallucination_after_retry persists row with failed_reason='hallucinated_citation'
 *   IT-05 llm_error persists row with failed_reason='provider_down'
 *   IT-06 invalid_input does NOT persist (lib throws before lazy provider build)
 *   IT-07 question_hash is sha256[:16], never raw text
 *   IT-08 timestamp_ms is monotonic + populated
 *   IT-09 cost_estimate_usd > 0 for flash-lite model, = 0 for unknown
 *   IT-10 CHECK constraint blocks invalid failed_reason values
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import {
  answer as realAnswer,
  AnswerError,
  __setRawSearchForTests,
  MockProvider,
} from "../index.js";
import type { AnswerOpts, AnswerResult } from "../index.js";
import type { RawChunk } from "../types.js";
import {
  recordAnswer,
  INSERT_SQL,
  type AnswerTelemetryRow,
  type TelemetryStore,
} from "../telemetry.js";

// ─── v11 schema (canonical for staged-P1 INSERT_SQL alignment) ─────────────
//
// CHECK constraint matches mapFailureReason() codomain:
//   ('hallucinated_citation', 'provider_down', 'token_budget') OR NULL.

const SCHEMA_V11 = `
CREATE TABLE IF NOT EXISTS answer_telemetry (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  question_hash       TEXT NOT NULL,
  session_id          TEXT,
  timestamp_ms        INTEGER NOT NULL,
  provider            TEXT NOT NULL,
  model               TEXT NOT NULL,
  retrieval_count     INTEGER NOT NULL,
  citation_count      INTEGER NOT NULL,
  tokens_in           INTEGER,
  tokens_out          INTEGER,
  latency_ms          INTEGER NOT NULL,
  fallback_used       INTEGER NOT NULL DEFAULT 0,
  failed_reason       TEXT,
  cost_estimate_usd   REAL NOT NULL DEFAULT 0,
  CHECK (failed_reason IS NULL OR failed_reason IN
         ('hallucinated_citation', 'provider_down', 'token_budget'))
);

CREATE INDEX IF NOT EXISTS idx_answer_telemetry_timestamp
  ON answer_telemetry(timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_answer_telemetry_failed
  ON answer_telemetry(failed_reason)
  WHERE failed_reason IS NOT NULL;
`;

// ─── Real SQLite-backed TelemetryStore (test-only adapter) ─────────────────

class Sqlite3TelemetryStore implements TelemetryStore {
  private readonly stmt;
  constructor(private readonly db: DatabaseType) {
    this.stmt = db.prepare(INSERT_SQL);
  }
  public insert(row: AnswerTelemetryRow): void {
    this.stmt.run(row);
  }
  public count(): number {
    const r = this.db
      .prepare("SELECT COUNT(*) as c FROM answer_telemetry")
      .get() as { c: number };
    return r.c;
  }
  public latest(): AnswerTelemetryRow | undefined {
    return this.db
      .prepare(
        "SELECT * FROM answer_telemetry ORDER BY id DESC LIMIT 1"
      )
      .get() as AnswerTelemetryRow | undefined;
  }
  public byFailure(reason: string | null): AnswerTelemetryRow[] {
    if (reason === null) {
      return this.db
        .prepare(
          "SELECT * FROM answer_telemetry WHERE failed_reason IS NULL"
        )
        .all() as AnswerTelemetryRow[];
    }
    return this.db
      .prepare(
        "SELECT * FROM answer_telemetry WHERE failed_reason = ?"
      )
      .all(reason) as AnswerTelemetryRow[];
  }
}

// ─── Fixtures (synthetic chunks) ───────────────────────────────────────────

function fixtureChunks(): RawChunk[] {
  return [
    {
      chunk_id: 5001,
      file_path: "memory/entities/decision/d41.md",
      line_range: "L10-L20",
      content: "D41 #1: default model is gemini-2.5-flash-lite per Toto.",
      content_hash: "h-d41",
      score: 0.94,
    },
    {
      chunk_id: 5002,
      file_path: "memory/entities/feedback/salience.md",
      content: "Salience formula: recency × pain × importance.",
      content_hash: "h-sal",
      score: 0.88,
    },
    {
      chunk_id: 5003,
      file_path: "memory/entities/lesson/never-sed.md",
      content: "Never sed -i on .db files — corrupts page boundaries.",
      content_hash: "h-sed",
      score: 0.71,
    },
  ];
}

function bindFixture(): void {
  __setRawSearchForTests(async () => fixtureChunks());
}

function bindEmpty(): void {
  __setRawSearchForTests(async () => []);
}

// ─── Test scaffolding ──────────────────────────────────────────────────────

let db: DatabaseType;
let store: Sqlite3TelemetryStore;

beforeEach(() => {
  db = new Database(":memory:");
  db.exec(SCHEMA_V11);
  store = new Sqlite3TelemetryStore(db);
  bindFixture();
});

afterEach(() => {
  db.close();
});

function answerWith(text: string): (opts: AnswerOpts) => Promise<AnswerResult> {
  return (opts: AnswerOpts) =>
    realAnswer({
      ...opts,
      providerOverride: new MockProvider([text], 0),
    });
}

// ─── IT-01 happy path persists row ────────────────────────────────────────

describe("T11 integration — real SQLite v11 schema", () => {
  it("IT-01 happy path inserts row with failed_reason NULL", async () => {
    const res = await answerWith("Salience is [chunk_1] formula.")({
      question: "What is salience?",
    });
    recordAnswer(store, {
      question: "What is salience?",
      citationCount: res.citations.length,
      metadata: res.metadata,
      sessionId: "sess-it-01",
    });

    assert.strictEqual(store.count(), 1);
    const row = store.latest()!;
    assert.strictEqual(row.failed_reason, null);
    assert.strictEqual(row.fallback_used, 0);
    assert.strictEqual(row.session_id, "sess-it-01");
    assert.strictEqual(row.citation_count, 1);
    assert.strictEqual(row.retrieval_count, 3);
    assert.strictEqual(row.model, "gemini-2.5-flash-lite");
    assert.ok(row.timestamp_ms > 0);
    assert.ok(row.latency_ms >= 0);
  });

  // ─── IT-02 retrieval_empty persists ─────────────────────────────────────

  it("IT-02 retrieval_empty short-circuit persists row (failed_reason NULL after mapping)", async () => {
    bindEmpty();
    const res = await realAnswer({
      question: "Nothing matches",
      providerOverride: new MockProvider([], 0),
    });
    assert.match(res.answer, /no memory matches/i);
    recordAnswer(store, {
      question: "Nothing matches",
      citationCount: 0,
      metadata: res.metadata,
      sessionId: "sess-it-02",
    });

    const row = store.latest()!;
    // mapFailureReason('retrieval_empty') → null (not an SQL failure column)
    assert.strictEqual(row.failed_reason, null);
    assert.strictEqual(row.retrieval_count, 0);
    assert.strictEqual(row.citation_count, 0);
    assert.strictEqual(row.tokens_in, 0);
    assert.strictEqual(row.tokens_out, 0);
  });

  // ─── IT-03 retry success ────────────────────────────────────────────────

  it("IT-03 hallucination retry SUCCESS persists row with fallback_used=1, failed_reason NULL", async () => {
    const provider = new MockProvider(
      [
        "Bad [chunk_99] first attempt.",
        "Good [chunk_1] retry attempt.",
      ],
      0
    );
    const res = await realAnswer({
      question: "Which model is default?",
      providerOverride: provider,
    });
    recordAnswer(store, {
      question: "Which model is default?",
      citationCount: res.citations.length,
      metadata: res.metadata,
      sessionId: "sess-it-03",
    });

    const row = store.latest()!;
    assert.strictEqual(row.failed_reason, null);
    assert.strictEqual(row.fallback_used, 1);
    assert.strictEqual(row.citation_count, 1);
    assert.strictEqual(res.metadata.retry_count, 1);
  });

  // ─── IT-04 hallucination_after_retry ────────────────────────────────────

  it("IT-04 hallucination_after_retry persists row with failed_reason='hallucinated_citation'", async () => {
    const provider = new MockProvider(
      ["[chunk_99] first", "[chunk_42] retry"],
      0
    );
    try {
      await realAnswer({
        question: "Adversarial",
        providerOverride: provider,
      });
      assert.fail("expected AnswerError");
    } catch (err) {
      assert.ok(err instanceof AnswerError);
      assert.strictEqual(err.reason, "hallucination_after_retry");
      recordAnswer(store, {
        question: "Adversarial",
        citationCount: 0,
        metadata: {
          latency_ms: (err.metadata.latency_ms as number) ?? 0,
          tokens_in: 0,
          tokens_out: 0,
          provider: "mock",
          model: "gemini-2.5-flash-lite",
          retrieval_count: 3,
          fallback_used: true,
          failed_reason: err.reason,
        },
        sessionId: "sess-it-04",
      });
    }
    const rows = store.byFailure("hallucinated_citation");
    assert.strictEqual(rows.length, 1);
    assert.strictEqual(rows[0]!.fallback_used, 1);
  });

  // ─── IT-05 llm_error → provider_down ────────────────────────────────────

  it("IT-05 llm_error persists row with failed_reason='provider_down'", async () => {
    const provider = new MockProvider([], 0);
    provider.throwNext(new Error("ETIMEDOUT"));
    try {
      await realAnswer({
        question: "Network down",
        providerOverride: provider,
      });
      assert.fail("expected AnswerError");
    } catch (err) {
      assert.ok(err instanceof AnswerError);
      assert.strictEqual(err.reason, "llm_error");
      recordAnswer(store, {
        question: "Network down",
        citationCount: 0,
        metadata: {
          latency_ms: 5,
          tokens_in: 0,
          tokens_out: 0,
          provider: "mock",
          model: "gemini-2.5-flash-lite",
          retrieval_count: 3,
          fallback_used: false,
          failed_reason: err.reason,
        },
      });
    }
    const rows = store.byFailure("provider_down");
    assert.strictEqual(rows.length, 1);
  });

  // ─── IT-06 invalid_input does NOT call telemetry (caller bug) ───────────

  it("IT-06 invalid_input throws before any telemetry write", async () => {
    try {
      await realAnswer({ question: "" });
      assert.fail("expected invalid_input");
    } catch (err) {
      assert.ok(err instanceof AnswerError);
      assert.strictEqual(err.reason, "invalid_input");
    }
    // Caller (CLI/HTTP/MCP) may choose to record; lib doesn't auto-record.
    // We assert that no spurious row appeared on the store from the lib call.
    assert.strictEqual(store.count(), 0);
  });

  // ─── IT-07 question_hash privacy ────────────────────────────────────────

  it("IT-07 question_hash is sha256[:16] and never leaks raw text", async () => {
    const secret = "What is my API key SUPER_SECRET_HERE?";
    const res = await answerWith("safe [chunk_1]")({ question: secret });
    recordAnswer(store, {
      question: secret,
      citationCount: res.citations.length,
      metadata: res.metadata,
    });

    const row = store.latest()!;
    assert.strictEqual(row.question_hash.length, 16);
    assert.match(row.question_hash, /^[0-9a-f]{16}$/);
    // Critical: the persisted serialization MUST NOT contain raw text.
    const serialized = JSON.stringify(row);
    assert.ok(!serialized.includes("SUPER_SECRET_HERE"));
    assert.ok(!serialized.includes("API key"));
  });

  // ─── IT-08 timestamp monotonic ──────────────────────────────────────────

  it("IT-08 timestamp_ms populated + monotonically non-decreasing across calls", async () => {
    for (let i = 0; i < 3; i++) {
      const res = await answerWith(`call ${i} [chunk_1]`)({
        question: `Q${i}`,
      });
      recordAnswer(store, {
        question: `Q${i}`,
        citationCount: res.citations.length,
        metadata: res.metadata,
      });
      // tiny delay so wall-clock ms advances
      await new Promise((r) => setTimeout(r, 2));
    }
    const rows = db
      .prepare(
        "SELECT timestamp_ms FROM answer_telemetry ORDER BY id ASC"
      )
      .all() as Array<{ timestamp_ms: number }>;
    assert.strictEqual(rows.length, 3);
    assert.ok(rows[0]!.timestamp_ms <= rows[1]!.timestamp_ms);
    assert.ok(rows[1]!.timestamp_ms <= rows[2]!.timestamp_ms);
  });

  // ─── IT-09 cost_estimate_usd ────────────────────────────────────────────

  it("IT-09 cost_estimate_usd > 0 for flash-lite, = 0 for unknown model", async () => {
    // First insert: real-shaped metadata (model=gemini-2.5-flash-lite via default).
    const res = await answerWith("[chunk_1]")({ question: "cost?" });
    // Override model in metadata copy to trigger price-table hit/miss.
    recordAnswer(store, {
      question: "cost-known",
      citationCount: 0,
      metadata: { ...res.metadata, model: "gemini-2.5-flash-lite", tokens_in: 1000, tokens_out: 500 },
    });
    recordAnswer(store, {
      question: "cost-unknown",
      citationCount: 0,
      metadata: { ...res.metadata, model: "unknown-xyz", tokens_in: 1000, tokens_out: 500 },
    });

    const rows = db
      .prepare(
        "SELECT model, cost_estimate_usd FROM answer_telemetry ORDER BY id ASC"
      )
      .all() as Array<{ model: string; cost_estimate_usd: number }>;
    assert.ok(rows[0]!.cost_estimate_usd > 0);
    assert.strictEqual(rows[1]!.cost_estimate_usd, 0);
  });

  // ─── IT-10 CHECK constraint enforces enum ───────────────────────────────

  it("IT-10 v11 CHECK constraint blocks bogus failed_reason values", () => {
    // Bypass mapFailureReason to write a forbidden value directly — must throw.
    assert.throws(() => {
      db.prepare(INSERT_SQL).run({
        question_hash: "0000000000000000",
        session_id: null,
        timestamp_ms: Date.now(),
        provider: "mock",
        model: "mock",
        retrieval_count: 0,
        citation_count: 0,
        tokens_in: 0,
        tokens_out: 0,
        latency_ms: 1,
        fallback_used: 0,
        failed_reason: "not_a_valid_enum_value",
        cost_estimate_usd: 0,
      });
    }, /CHECK constraint failed/);

    // Valid enums work.
    db.prepare(INSERT_SQL).run({
      question_hash: "1111111111111111",
      session_id: null,
      timestamp_ms: Date.now(),
      provider: "mock",
      model: "mock",
      retrieval_count: 0,
      citation_count: 0,
      tokens_in: 0,
      tokens_out: 0,
      latency_ms: 1,
      fallback_used: 0,
      failed_reason: "token_budget",
      cost_estimate_usd: 0,
    });
    const ok = store.byFailure("token_budget");
    assert.strictEqual(ok.length, 1);
  });
});
