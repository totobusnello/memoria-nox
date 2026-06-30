/**
 * src/lib/answer/__tests__/t5-t10.test.ts
 *
 * P1 T5-T10 integration tests:
 *  - T5: citation accuracy on golden Q/A set (validation harness)
 *  - T6: hallucination_after_retry telemetry hook fires
 *  - T7: telemetry insert/query (privacy: question_hash only, no raw)
 *  - T8: CLI argv parsing + render (human + json) + exit codes
 *  - T9: HTTP body validation + status codes + headers
 *  - T10: MCP tool input schema + result envelope
 *
 * Runner: node:test (node --test). Zero network — MockProvider only.
 * Target: 15+ cases (we land 25 below).
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  __setRawSearchForTests,
  MockProvider,
  AnswerError,
} from "../index.js";
import type { AnswerOpts, AnswerResult } from "../index.js";
import type { RawChunk } from "../types.js";
import { answer as realAnswer } from "../index.js";

import {
  hashQuestion,
  mapFailureReason,
  estimateCost,
  recordAnswer,
  InMemoryTelemetryStore,
  INSERT_SQL,
} from "../telemetry.js";

import {
  parseArgs,
  renderHuman,
  renderJson,
  runCli,
  HELP_TEXT,
  CliArgError,
} from "../../../cli/answer.js";

import {
  handleAnswerRequest,
  validateBody,
  statusFromReason,
  REQUEST_SCHEMA,
} from "../../../api/answer.js";

import {
  noxMemAnswerTool,
  parseInput,
  INPUT_SCHEMA,
} from "../../../mcp/tools/answer.js";

// ─── Fixtures ──────────────────────────────────────────────────────────────

function goldenChunks(): RawChunk[] {
  return [
    {
      chunk_id: 1001,
      file_path: "memory/entities/feedback/salience.md",
      line_range: "L5-L9",
      content: "Salience formula: salience = recency × pain × importance.",
      content_hash: "h-salience",
      score: 0.91,
    },
    {
      chunk_id: 1002,
      file_path: "memory/entities/decision/d41.md",
      content: "D41 #1: default model gemini-2.5-flash-lite.",
      content_hash: "h-d41",
      score: 0.87,
    },
    {
      chunk_id: 1003,
      file_path: "memory/entities/lesson/never-sed.md",
      content: "Never sed -i on .db files — corrupts page boundaries.",
      content_hash: "h-sed",
      score: 0.73,
    },
  ];
}

function bindFixture(): void {
  __setRawSearchForTests(async (_q, _k) => goldenChunks());
}

function bindEmpty(): void {
  __setRawSearchForTests(async () => []);
}

beforeEach(() => bindFixture());

function answerWith(text: string): (opts: AnswerOpts) => Promise<AnswerResult> {
  return (opts: AnswerOpts) => {
    const o: AnswerOpts = {
      ...opts,
      providerOverride: new MockProvider([text], 1),
    };
    return realAnswer(o);
  };
}

// ─── T5 — citation accuracy on golden subset ───────────────────────────────

describe("T5 citation accuracy (golden subset)", () => {
  it("resolves cited markers to real chunk_ids in order of first appearance", async () => {
    const llmText =
      "Salience uses [chunk_1]. The default model is per [chunk_2].";
    const run = answerWith(llmText);
    const res = await run({ question: "What is salience?" });
    assert.strictEqual(res.citations.length, 2);
    assert.strictEqual(res.citations[0]?.marker_id, "chunk_1");
    assert.strictEqual(res.citations[0]?.chunk_id, 1001);
    assert.strictEqual(res.citations[1]?.marker_id, "chunk_2");
    assert.strictEqual(res.citations[1]?.chunk_id, 1002);
  });

  it("dedupes repeated markers (same marker cited twice = one citation)", async () => {
    const run = answerWith("[chunk_1] and again [chunk_1] and [chunk_2].");
    const res = await run({ question: "anything" });
    const ids = res.citations.map((c) => c.marker_id);
    assert.deepStrictEqual(ids, ["chunk_1", "chunk_2"]);
  });

  it("citation snippets are ≤200 chars + line_range preserved", async () => {
    const run = answerWith("[chunk_1] - salience.");
    const res = await run({ question: "salience?" });
    assert.ok(res.citations[0]!.snippet.length <= 200);
    assert.strictEqual(res.citations[0]!.line_range, "L5-L9");
  });
});

// ─── T6 — hallucination_after_retry telemetry hook ─────────────────────────

describe("T6 hallucination_after_retry telemetry", () => {
  it("records telemetry row with failed_reason='hallucinated_citation' (mapped)", async () => {
    const store = new InMemoryTelemetryStore();
    // Mock LLM hallucinates twice → AnswerError with reason='hallucination_after_retry'.
    const hallucinator = new MockProvider(["[chunk_99]", "[chunk_42]"], 0);
    try {
      await realAnswer({
        question: "Adversarial",
        providerOverride: hallucinator,
      });
      assert.fail("should have thrown");
    } catch (err) {
      assert.ok(err instanceof AnswerError);
      assert.strictEqual(err.reason, "hallucination_after_retry");
      // Caller (CLI/HTTP/MCP) is responsible for recording on failure — simulate:
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
        sessionId: "test-session",
      });
    }
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.failed_reason, "hallucinated_citation");
    assert.strictEqual(store.rows[0]!.fallback_used, 1);
    assert.strictEqual(store.rows[0]!.session_id, "test-session");
  });
});

// ─── T7 — telemetry module ─────────────────────────────────────────────────

describe("T7 telemetry — hashing + mapping + insert", () => {
  it("hashQuestion returns deterministic sha256[:16]", () => {
    const a = hashQuestion("What is the salience formula?");
    const b = hashQuestion("What is the salience formula?");
    const c = hashQuestion("Different question");
    assert.strictEqual(a, b);
    assert.notStrictEqual(a, c);
    assert.strictEqual(a.length, 16);
    assert.match(a, /^[0-9a-f]{16}$/);
  });

  it("mapFailureReason maps broad lib reasons to v11 alphabet", () => {
    assert.strictEqual(mapFailureReason("hallucinated_citation"), "hallucinated_citation");
    assert.strictEqual(mapFailureReason("hallucination_after_retry"), "hallucinated_citation");
    assert.strictEqual(mapFailureReason("llm_error"), "provider_down");
    assert.strictEqual(mapFailureReason("llm_timeout"), "provider_down");
    assert.strictEqual(mapFailureReason("retrieval_empty"), null);
    assert.strictEqual(mapFailureReason("invalid_input"), null);
    assert.strictEqual(mapFailureReason(undefined), null);
  });

  it("estimateCost honours flash-lite price table; 0 for unknown model", () => {
    const cost = estimateCost("gemini-2.5-flash-lite", 1_000_000, 1_000_000);
    // 0.10 + 0.40 = 0.50 USD for 1M in + 1M out
    assert.strictEqual(cost, 0.5);
    assert.strictEqual(estimateCost("nonexistent-model", 10000, 10000), 0);
    assert.strictEqual(estimateCost("gemini-2.5-flash-lite", 0, 0), 0);
  });

  it("recordAnswer inserts row; NEVER stores raw question text", () => {
    const store = new InMemoryTelemetryStore();
    const row = recordAnswer(store, {
      question: "What is the salience formula?",
      citationCount: 2,
      metadata: {
        latency_ms: 123,
        tokens_in: 100,
        tokens_out: 50,
        provider: "gemini",
        model: "gemini-2.5-flash-lite",
        retrieval_count: 3,
        fallback_used: false,
      },
      sessionId: "s-1",
      now: () => 1715000000000,
    });
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(row.question_hash.length, 16);
    // Critical: no raw question text anywhere in serialized row
    const serialized = JSON.stringify(row);
    assert.ok(!serialized.includes("salience"), "raw question must not leak");
    assert.ok(!serialized.includes("formula"), "raw question must not leak");
    assert.strictEqual(row.timestamp_ms, 1715000000000);
    assert.strictEqual(row.fallback_used, 0);
    assert.strictEqual(row.cost_estimate_usd >= 0, true);
  });

  it("recordAnswer swallows store errors (telemetry must NOT break the call)", () => {
    const brokenStore = {
      insert() {
        throw new Error("disk full");
      },
    };
    // Should not throw.
    const row = recordAnswer(brokenStore, {
      question: "q",
      citationCount: 0,
      metadata: {
        latency_ms: 1,
        tokens_in: 0,
        tokens_out: 0,
        provider: "mock",
        model: "mock",
        retrieval_count: 0,
        fallback_used: false,
      },
    });
    assert.ok(row.question_hash.length === 16);
  });

  it("INSERT_SQL contains exactly the v11 columns in canonical order", () => {
    assert.match(INSERT_SQL, /INTO answer_telemetry/);
    assert.match(INSERT_SQL, /@question_hash/);
    assert.match(INSERT_SQL, /@cost_estimate_usd/);
    // Forbid raw-text columns
    assert.ok(!INSERT_SQL.includes("@question_text"));
    assert.ok(!INSERT_SQL.includes("@answer_text"));
  });
});

// ─── T8 — CLI ─────────────────────────────────────────────────────────────

describe("T8 CLI — parseArgs + render + runCli", () => {
  it("parses positional question + numeric flags", () => {
    const p = parseArgs([
      "--top-k", "12", "--max-tokens", "500", "--temperature", "0.3",
      "What", "is", "salience?",
    ]);
    assert.strictEqual(p.question, "What is salience?");
    assert.strictEqual(p.topK, 12);
    assert.strictEqual(p.maxTokens, 500);
    assert.strictEqual(p.temperature, 0.3);
    assert.strictEqual(p.showCitations, true);
  });

  it("--json flag flips render; --no-cite suppresses citation block", () => {
    const p = parseArgs(["--json", "--no-cite", "Q"]);
    assert.strictEqual(p.json, true);
    assert.strictEqual(p.showCitations, false);
    assert.strictEqual(p.stripMarkers, false);
  });

  it("--no-citations strips markers from answer body", () => {
    const p = parseArgs(["--no-citations", "Q"]);
    assert.strictEqual(p.stripMarkers, true);
    const res: AnswerResult = {
      answer: "Salience [chunk_1] is recency × pain × importance [chunk_2].",
      citations: [],
      metadata: {
        latency_ms: 10, tokens_in: 5, tokens_out: 5,
        provider: "mock", model: "mock", retrieval_count: 2, fallback_used: false,
      },
    };
    const out = renderJson(res, p);
    assert.ok(!out.includes("[chunk_1]"));
    assert.ok(!out.includes("[chunk_2]"));
  });

  it("rejects unknown flag + missing question", () => {
    assert.throws(() => parseArgs(["--bogus", "Q"]), CliArgError);
    assert.throws(() => parseArgs([]), CliArgError);
    assert.throws(() => parseArgs(["--top-k"]), CliArgError);
    assert.throws(() => parseArgs(["--top-k", "abc", "Q"]), CliArgError);
  });

  it("--help prints HELP_TEXT and exits 0", async () => {
    const lines: string[] = [];
    const code = await runCli({
      argv: ["--help"],
      stdout: (s) => lines.push(s),
      stderr: () => {},
    });
    assert.strictEqual(code, 0);
    assert.ok(lines[0]!.includes("nox-mem answer"));
    assert.ok(HELP_TEXT.includes("--top-k"));
  });

  it("runCli happy path emits human render + exit 0 + writes telemetry", async () => {
    const store = new InMemoryTelemetryStore();
    const out: string[] = [];
    const code = await runCli({
      argv: ["What is salience?"],
      stdout: (s) => out.push(s),
      stderr: () => {},
      runAnswer: answerWith("Salience is [chunk_1]."),
      telemetryStore: store,
    });
    assert.strictEqual(code, 0);
    assert.ok(out[0]!.includes("Salience is"));
    assert.ok(out[0]!.includes("Citations:"));
    assert.ok(out[0]!.includes("chunk_1"));
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.failed_reason, null);
    assert.strictEqual(store.rows[0]!.citation_count, 1);
  });

  it("runCli on AnswerError(hallucination_after_retry) exits 4 + telemetry row written", async () => {
    const store = new InMemoryTelemetryStore();
    const err: string[] = [];
    const code = await runCli({
      argv: ["bad question"],
      stdout: () => {},
      stderr: (s) => err.push(s),
      runAnswer: () => {
        return realAnswer({
          question: "bad question",
          providerOverride: new MockProvider(["[chunk_99]", "[chunk_42]"], 0),
        });
      },
      telemetryStore: store,
    });
    assert.strictEqual(code, 4);
    assert.ok(err.join("\n").includes("hallucination_after_retry"));
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.failed_reason, "hallucinated_citation");
  });

  it("runCli on bad argv exits 2 with stderr help", async () => {
    const err: string[] = [];
    const code = await runCli({
      argv: ["--unknown-flag", "Q"],
      stdout: () => {},
      stderr: (s) => err.push(s),
    });
    assert.strictEqual(code, 2);
    assert.ok(err.join("").includes("unknown flag"));
  });

  it("renderHuman includes metadata footer with model + latency + retrieved", () => {
    const res: AnswerResult = {
      answer: "Body [chunk_1]",
      citations: [
        { chunk_id: 1, marker_id: "chunk_1", file_path: "a.md", snippet: "x" },
      ],
      metadata: {
        latency_ms: 42, tokens_in: 5, tokens_out: 5,
        provider: "mock", model: "gemini-2.5-flash-lite",
        retrieval_count: 1, fallback_used: false,
      },
    };
    const p = parseArgs(["Q"]);
    const out = renderHuman(res, p);
    assert.ok(out.includes("model=gemini-2.5-flash-lite"));
    assert.ok(out.includes("latency=42ms"));
    assert.ok(out.includes("retrieved=1"));
    assert.ok(out.includes("cited=1"));
  });
});

// ─── T9 — HTTP ─────────────────────────────────────────────────────────────

describe("T9 HTTP — validateBody + handleAnswerRequest", () => {
  it("validateBody accepts a minimal valid body", () => {
    const r = validateBody({ question: "hello" });
    assert.strictEqual(r.question, "hello");
  });

  it("validateBody rejects missing/empty/oversize question", () => {
    assert.throws(() => validateBody({}));
    assert.throws(() => validateBody({ question: "   " }));
    assert.throws(() => validateBody({ question: "x".repeat(2001) }));
    assert.throws(() => validateBody({ question: 123 }));
    assert.throws(() => validateBody(null));
    assert.throws(() => validateBody([]));
  });

  it("validateBody rejects wrong types on optional fields", () => {
    assert.throws(() => validateBody({ question: "q", top_k: "8" }));
    assert.throws(() => validateBody({ question: "q", temperature: "0.3" }));
    assert.throws(() => validateBody({ question: "q", no_citations: 1 }));
  });

  it("statusFromReason maps reasons to kickoff §6 codes", () => {
    assert.strictEqual(statusFromReason("retrieval_empty"), 503);
    assert.strictEqual(statusFromReason("hallucination_after_retry"), 422);
    assert.strictEqual(statusFromReason("llm_timeout"), 504);
    assert.strictEqual(statusFromReason("llm_error"), 502);
    assert.strictEqual(statusFromReason("invalid_input"), 400);
    assert.strictEqual(statusFromReason("unauthorized"), 401);
  });

  it("handleAnswerRequest 200 happy path includes citations + headers", async () => {
    const store = new InMemoryTelemetryStore();
    const out = await handleAnswerRequest({
      body: { question: "salience?" },
      headers: { "x-trace-id": "trace-abc" },
      answer: answerWith("Salience [chunk_1]"),
      telemetryStore: store,
    });
    assert.strictEqual(out.status, 200);
    assert.strictEqual(out.headers["X-Trace-Id"], "trace-abc");
    assert.strictEqual(out.headers["X-Model-Used"], "gemini-2.5-flash-lite");
    const body = out.body as { citations: unknown[]; trace_id: string };
    assert.strictEqual(body.citations.length, 1);
    assert.strictEqual(body.trace_id, "trace-abc");
    assert.strictEqual(store.rows.length, 1);
  });

  it("handleAnswerRequest 400 on invalid body shape", async () => {
    const out = await handleAnswerRequest({
      body: { not_question: "x" },
      answer: () => Promise.reject(new Error("should not call")),
    });
    assert.strictEqual(out.status, 400);
    assert.strictEqual((out.body as { reason: string }).reason, "invalid_body");
  });

  it("handleAnswerRequest 422 on hallucination_after_retry + telemetry written", async () => {
    const store = new InMemoryTelemetryStore();
    const out = await handleAnswerRequest({
      body: { question: "adv" },
      answer: () =>
        realAnswer({
          question: "adv",
          providerOverride: new MockProvider(["[chunk_99]", "[chunk_42]"], 0),
        }),
      telemetryStore: store,
    });
    assert.strictEqual(out.status, 422);
    const body = out.body as { reason: string };
    assert.strictEqual(body.reason, "hallucination_after_retry");
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.failed_reason, "hallucinated_citation");
  });

  it("handleAnswerRequest 401 when authCheck fails", async () => {
    const out = await handleAnswerRequest({
      body: { question: "q" },
      authCheck: () => false,
      answer: () => Promise.reject(new Error("should not call")),
    });
    assert.strictEqual(out.status, 401);
    assert.strictEqual((out.body as { reason: string }).reason, "unauthorized");
  });

  it("handleAnswerRequest 503 on retrieval_empty (lib short-circuit)", async () => {
    bindEmpty();
    const out = await handleAnswerRequest({
      body: { question: "nothing matches" },
      answer: realAnswer,
    });
    assert.strictEqual(out.status, 503);
    const body = out.body as { metadata: { failed_reason: string }; answer: string };
    assert.strictEqual(body.metadata.failed_reason, "retrieval_empty");
    assert.ok(body.answer.includes("no memory matches"));
  });

  it("REQUEST_SCHEMA matches kickoff §5 surface", () => {
    assert.deepStrictEqual(REQUEST_SCHEMA.required, ["question"]);
    const props = REQUEST_SCHEMA.properties as Record<string, { type: string } | undefined>;
    assert.strictEqual(props.question?.type, "string");
    assert.strictEqual(props.top_k?.type, "integer");
    assert.strictEqual(props.temperature?.type, "number");
    assert.strictEqual(REQUEST_SCHEMA.additionalProperties, false);
  });

  it("no_citations strips inline [chunk_N] markers but keeps citations array", async () => {
    const out = await handleAnswerRequest({
      body: { question: "q", no_citations: true },
      answer: answerWith("Salience is [chunk_1] for recency."),
    });
    assert.strictEqual(out.status, 200);
    const body = out.body as { answer: string; citations: unknown[] };
    assert.ok(!body.answer.includes("[chunk_1]"));
    assert.strictEqual(body.citations.length, 1);
  });
});

// ─── T10 — MCP ─────────────────────────────────────────────────────────────

describe("T10 MCP — nox_mem_answer tool", () => {
  it("tool metadata matches contract", () => {
    assert.strictEqual(noxMemAnswerTool.name, "nox_mem_answer");
    assert.ok(noxMemAnswerTool.description.includes("nox-mem corpus"));
    assert.ok(noxMemAnswerTool.description.includes("[chunk_N]"));
    const schema = INPUT_SCHEMA as unknown as {
      required: string[];
      properties: Record<string, { minLength?: number; maxLength?: number; type: string } | undefined>;
      additionalProperties: boolean;
    };
    assert.deepStrictEqual(schema.required, ["question"]);
    assert.strictEqual(schema.properties.question?.maxLength, 2000);
    assert.strictEqual(schema.additionalProperties, false);
  });

  it("parseInput rejects malformed input", () => {
    assert.throws(() => parseInput(null));
    assert.throws(() => parseInput({}));
    assert.throws(() => parseInput({ question: "" }));
    assert.throws(() => parseInput({ question: "x".repeat(2001) }));
    assert.throws(() => parseInput({ question: "q", top_k: "8" }));
  });

  it("handler happy path returns content[0].text as JSON with citations", async () => {
    const store = new InMemoryTelemetryStore();
    const res = await noxMemAnswerTool.handler(
      { question: "salience?" },
      {
        sessionId: "s-mcp",
        telemetryStore: store,
        answer: answerWith("Salience is [chunk_1]."),
      }
    );
    assert.strictEqual(res.isError, undefined);
    assert.strictEqual(res.content.length, 1);
    assert.strictEqual(res.content[0]!.type, "text");
    const payload = JSON.parse(res.content[0]!.text) as {
      answer: string;
      citations: Array<{ chunk_id: number }>;
    };
    assert.ok(payload.answer.includes("Salience"));
    assert.strictEqual(payload.citations.length, 1);
    assert.strictEqual(payload.citations[0]!.chunk_id, 1001);
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.session_id, "s-mcp");
  });

  it("handler hallucination_after_retry returns isError:true + telemetry row", async () => {
    const store = new InMemoryTelemetryStore();
    const res = await noxMemAnswerTool.handler(
      { question: "adv" },
      {
        telemetryStore: store,
        answer: () =>
          realAnswer({
            question: "adv",
            providerOverride: new MockProvider(["[chunk_99]", "[chunk_42]"], 0),
          }),
      }
    );
    assert.strictEqual(res.isError, true);
    const payload = JSON.parse(res.content[0]!.text) as { reason: string };
    assert.strictEqual(payload.reason, "hallucination_after_retry");
    assert.strictEqual(store.rows.length, 1);
    assert.strictEqual(store.rows[0]!.failed_reason, "hallucinated_citation");
  });

  it("handler invalid input returns isError:true with reason=invalid_input", async () => {
    const res = await noxMemAnswerTool.handler({ no_question: true });
    assert.strictEqual(res.isError, true);
    const payload = JSON.parse(res.content[0]!.text) as { reason: string };
    assert.strictEqual(payload.reason, "invalid_input");
  });

  it("handler no_citations strips markers from emitted answer", async () => {
    const res = await noxMemAnswerTool.handler(
      { question: "q", no_citations: true },
      { answer: answerWith("Salience is [chunk_1] for recency.") }
    );
    const payload = JSON.parse(res.content[0]!.text) as { answer: string };
    assert.ok(!payload.answer.includes("[chunk_1]"));
  });
});
