/**
 * src/lib/answer/__tests__/e2e-gemini.test.ts — P1 T12.
 *
 * **GATED** end-to-end tests against the real Gemini API. SKIPPED unless
 * `NOX_E2E_GEMINI=1` is set in the environment AND `GEMINI_API_KEY` is
 * present.
 *
 * Cost cap: hardcoded `MAX_TOKENS_TEST = 200` on every call. Total run
 * (4 tests × ~250 tokens in + 200 tokens out, flash-lite pricing
 * $0.10/M in + $0.40/M out) ≈ $0.0004 — well under the $0.01 budget.
 *
 * Coverage when active (4 tests):
 *   E2E-01 real Gemini call returns non-empty answer + at least one citation
 *   E2E-02 citations resolve to real chunk_ids from the synthetic fixture
 *   E2E-03 telemetry row written; model = 'gemini-2.5-flash-lite'
 *   E2E-04 adversarial out-of-corpus question yields "no memory matches" via retrieval_empty
 *
 * When gated off, ONE skip-marker test runs that logs the gate reason —
 * keeps the report honest ("test skipped because NOX_E2E_GEMINI != 1").
 *
 * The Gemini provider is wired inline here using the public REST endpoint
 * (no SDK dependency required — keeps staged-P1 installable without
 * `@google/genai` in the dev dep set). Replace with the SDK in the VPS
 * apply step if/when A3 provider abstraction merges.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

import {
  answer as realAnswer,
  __setRawSearchForTests,
} from "../index.js";
import type { LLMProvider, LLMCallOpts, LLMCallResult } from "../provider.js";
import type { RawChunk } from "../types.js";
import {
  recordAnswer,
  INSERT_SQL,
  type TelemetryStore,
  type AnswerTelemetryRow,
} from "../telemetry.js";

// ─── Gating ────────────────────────────────────────────────────────────────

const GATE_ON = process.env.NOX_E2E_GEMINI === "1";
const API_KEY = process.env.GEMINI_API_KEY ?? "";
const ACTIVE = GATE_ON && API_KEY.length > 0;

const MAX_TOKENS_TEST = 200;
const MODEL = "gemini-2.5-flash-lite";

// ─── Skip-marker stub ──────────────────────────────────────────────────────

describe("T12 E2E Gemini — gating", () => {
  it("gate is honoured (active iff NOX_E2E_GEMINI=1 AND GEMINI_API_KEY set)", () => {
    if (!ACTIVE) {
      const reason = !GATE_ON
        ? "NOX_E2E_GEMINI != 1"
        : "GEMINI_API_KEY empty";
      // node:test prints this in default reporter; humans see why we skipped.
      process.stdout.write(
        `[T12] SKIPPED real-Gemini suite — reason: ${reason}\n`
      );
      assert.ok(true, "skip path");
      return;
    }
    process.stdout.write(
      "[T12] real-Gemini suite ACTIVE — running 4 tests against API\n"
    );
    assert.ok(API_KEY.length > 0);
  });
});

// ─── Real Gemini provider (REST, no SDK) ───────────────────────────────────

interface GeminiResp {
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> };
    finishReason?: string;
  }>;
  usageMetadata?: {
    promptTokenCount?: number;
    candidatesTokenCount?: number;
  };
}

class GeminiRestProvider implements LLMProvider {
  public readonly name = "gemini";
  constructor(
    private readonly apiKey: string,
    private readonly maxTokensCap: number = MAX_TOKENS_TEST
  ) {}

  public async complete(opts: LLMCallOpts): Promise<LLMCallResult> {
    const t0 = Date.now();
    const url =
      `https://generativelanguage.googleapis.com/v1beta/models/` +
      `${opts.model}:generateContent?key=${this.apiKey}`;
    const body = {
      systemInstruction: { parts: [{ text: opts.system }] },
      contents: [{ role: "user", parts: [{ text: opts.user }] }],
      generationConfig: {
        temperature: opts.temperature,
        maxOutputTokens: Math.min(opts.maxTokens, this.maxTokensCap),
      },
    };
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      throw new Error(`Gemini HTTP ${resp.status}: ${await resp.text()}`);
    }
    const data = (await resp.json()) as GeminiResp;
    const text =
      data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";
    return {
      text,
      tokensIn: data.usageMetadata?.promptTokenCount ?? 0,
      tokensOut: data.usageMetadata?.candidatesTokenCount ?? 0,
      latencyMs: Date.now() - t0,
    };
  }
}

// ─── Synthetic corpus (no real DB needed for E2E quality smoke) ────────────

const E2E_CHUNKS: RawChunk[] = [
  {
    chunk_id: 9001,
    file_path: "memory/entities/decision/d41.md",
    line_range: "L1-L5",
    content:
      "Decision D41 #1 — Default model for the nox-mem answer primitive " +
      "is gemini-2.5-flash-lite. Rationale: cost optimized vs quality. " +
      "Override with NOX_ANSWER_MODEL or --model flag.",
    content_hash: "h-d41",
    score: 0.95,
  },
  {
    chunk_id: 9002,
    file_path: "memory/entities/feedback/salience.md",
    line_range: "L1-L3",
    content:
      "Salience formula in nox-mem is salience = recency × pain × " +
      "importance. Exposed via /api/health.salience.",
    content_hash: "h-sal",
    score: 0.9,
  },
  {
    chunk_id: 9003,
    file_path: "memory/entities/lesson/never-sed.md",
    line_range: "L1-L2",
    content:
      "Never use sed -i on SQLite .db files — it corrupts page boundaries. " +
      "Filter file lists by extension before sweeps.",
    content_hash: "h-sed",
    score: 0.8,
  },
];

// ─── Telemetry adapter (real SQLite in-memory) ─────────────────────────────

class Sqlite3TelemetryStore implements TelemetryStore {
  private readonly stmt;
  constructor(private readonly db: DatabaseType) {
    this.stmt = db.prepare(INSERT_SQL);
  }
  public insert(row: AnswerTelemetryRow): void {
    this.stmt.run(row);
  }
  public latest(): AnswerTelemetryRow | undefined {
    return this.db
      .prepare("SELECT * FROM answer_telemetry ORDER BY id DESC LIMIT 1")
      .get() as AnswerTelemetryRow | undefined;
  }
}

const SCHEMA_V11 = `
CREATE TABLE IF NOT EXISTS answer_telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_hash TEXT NOT NULL, session_id TEXT,
  timestamp_ms INTEGER NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
  retrieval_count INTEGER NOT NULL, citation_count INTEGER NOT NULL,
  tokens_in INTEGER, tokens_out INTEGER, latency_ms INTEGER NOT NULL,
  fallback_used INTEGER NOT NULL DEFAULT 0, failed_reason TEXT,
  cost_estimate_usd REAL NOT NULL DEFAULT 0,
  CHECK (failed_reason IS NULL OR failed_reason IN
         ('hallucinated_citation', 'provider_down', 'token_budget'))
);
`;

// ─── Active suite (only if gated on) ───────────────────────────────────────

if (ACTIVE) {
  describe("T12 E2E Gemini — real API calls (flash-lite, capped)", () => {
    let db: DatabaseType;
    let store: Sqlite3TelemetryStore;
    let provider: LLMProvider;

    before(() => {
      db = new Database(":memory:");
      db.exec(SCHEMA_V11);
      store = new Sqlite3TelemetryStore(db);
      provider = new GeminiRestProvider(API_KEY, MAX_TOKENS_TEST);
      __setRawSearchForTests(async () => E2E_CHUNKS);
    });

    after(() => {
      db.close();
    });

    it("E2E-01 returns non-empty answer with ≥1 citation", async () => {
      const res = await realAnswer({
        question: "What is the default model for the answer primitive?",
        providerOverride: provider,
        maxTokens: MAX_TOKENS_TEST,
        temperature: 0,
      });
      assert.ok(res.answer.length > 0, "answer text non-empty");
      assert.ok(res.citations.length >= 1, "≥1 citation parsed");
    });

    it("E2E-02 citation resolves to a real chunk_id from fixture", async () => {
      const res = await realAnswer({
        question: "What is the salience formula in nox-mem?",
        providerOverride: provider,
        maxTokens: MAX_TOKENS_TEST,
        temperature: 0,
      });
      assert.ok(res.citations.length >= 1);
      const validIds = new Set(E2E_CHUNKS.map((c) => c.chunk_id));
      for (const c of res.citations) {
        assert.ok(
          validIds.has(c.chunk_id),
          `citation chunk_id=${c.chunk_id} not in fixture`
        );
      }
    });

    it("E2E-03 telemetry row persists with model=gemini-2.5-flash-lite", async () => {
      const question = "Never use what on .db files?";
      const res = await realAnswer({
        question,
        providerOverride: provider,
        maxTokens: MAX_TOKENS_TEST,
        temperature: 0,
      });
      recordAnswer(store, {
        question,
        citationCount: res.citations.length,
        metadata: res.metadata,
        sessionId: "e2e-03",
      });
      const row = store.latest()!;
      assert.strictEqual(row.model, MODEL);
      assert.strictEqual(row.session_id, "e2e-03");
      assert.ok((row.tokens_in ?? 0) > 0, "real tokens reported");
      assert.ok((row.tokens_out ?? 0) > 0, "real tokens reported");
      assert.ok(row.cost_estimate_usd > 0, "real cost estimate > 0");
    });

    it("E2E-04 empty retrieval → canonical 'no memory matches' (no real LLM spend)", async () => {
      __setRawSearchForTests(async () => []);
      const res = await realAnswer({
        question: "What is the capital of Mars?",
        providerOverride: provider,
        maxTokens: MAX_TOKENS_TEST,
        temperature: 0,
      });
      assert.match(res.answer, /no memory matches/i);
      assert.strictEqual(res.citations.length, 0);
      assert.strictEqual(res.metadata.failed_reason, "retrieval_empty");
      assert.strictEqual(res.metadata.tokens_in, 0);
      assert.strictEqual(res.metadata.tokens_out, 0);
      // restore for any subsequent tests
      __setRawSearchForTests(async () => E2E_CHUNKS);
    });
  });
}
