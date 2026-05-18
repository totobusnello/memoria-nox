/**
 * src/lib/answer/__tests__/integration.test.ts
 *
 * T1-T4 integration tests: end-to-end answer() with mocked retrieval +
 * mocked LLM provider. No network, no DB, deterministic.
 *
 * Runner: node:test (node --test)
 *
 * Coverage (15+ cases):
 *   - retrieval wrapper: marker_id assignment, dedupe by content_hash, topK cap
 *   - prompt builder: system/user shape, chunk markers preserved
 *   - provider: selectProvider returns gemini default, mock honours queue
 *   - end-to-end: tokens accounted, latency_ms > 0, citations resolved
 *   - empty retrieval → canonical "no memory matches"
 *   - hallucinated citation → retry with strict prompt
 *   - hallucination after retry → throws AnswerError(hallucination_after_retry)
 *   - provider throws → AnswerError(llm_error)
 *   - empty question → AnswerError(invalid_input)
 *   - env model override
 *   - retrieval ordering: marker_id 1..N in result citations
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  answer,
  AnswerError,
  parseCitations,
  retrieveContext,
  __setRawSearchForTests,
  selectProvider,
  MockProvider,
  buildPrompt,
  buildRetryPrompt,
} from "../index.js";
import type { RawChunk, RetrievedChunk } from "../types.js";

// ─── Fixtures ──────────────────────────────────────────────────────────────

function fixtureChunks(): RawChunk[] {
  return [
    {
      chunk_id: 101,
      file_path: "memory/entities/decision/d41.md",
      line_range: "L10-L20",
      content: "D41 #1: default model is gemini-2.5-flash-lite per Toto morning review.",
      content_hash: "h-d41",
      score: 0.92,
    },
    {
      chunk_id: 202,
      file_path: "memory/entities/feedback/salience.md",
      content: "Salience formula: salience = recency × pain × importance.",
      content_hash: "h-salience",
      score: 0.88,
    },
    {
      chunk_id: 303,
      file_path: "memory/entities/lesson/never-sed-binary.md",
      content: "Never sed -i on .db files — corrupts page boundaries.",
      content_hash: "h-sed",
      score: 0.71,
    },
    // Near-duplicate of 303 — should be deduped by content_hash.
    {
      chunk_id: 304,
      file_path: "memory/entities/lesson/never-sed-binary.md",
      content: "Never sed -i on .db files — corrupts page boundaries.",
      content_hash: "h-sed",
      score: 0.65,
    },
  ];
}

function bindFixtureSearch(chunks: RawChunk[] = fixtureChunks()): void {
  __setRawSearchForTests(async (_q: string, _k: number) => {
    void _q;
    void _k;
    return chunks;
  });
}

// ─── retrieval.ts ──────────────────────────────────────────────────────────

describe("retrieveContext", () => {
  it("returns chunks with marker_id assigned 1..N in score-desc order", async () => {
    bindFixtureSearch();
    const got = await retrieveContext("anything", 8);
    assert.ok(got.length > 0);
    assert.strictEqual(got[0]?.marker_id, "chunk_1");
    assert.strictEqual(got[1]?.marker_id, "chunk_2");
    // chunk_id 101 has highest score → must be marker_id chunk_1
    assert.strictEqual(got[0]?.chunk_id, 101);
  });

  it("dedupes near-duplicates by content_hash, keeping highest score", async () => {
    bindFixtureSearch();
    const got = await retrieveContext("anything", 8);
    const ids = got.map((c) => c.chunk_id);
    assert.ok(ids.includes(303), "high-score dup survivor present");
    assert.ok(!ids.includes(304), "low-score dup filtered out");
  });

  it("caps results to topK", async () => {
    bindFixtureSearch();
    const got = await retrieveContext("anything", 2);
    assert.strictEqual(got.length, 2);
    assert.strictEqual(got[0]?.marker_id, "chunk_1");
    assert.strictEqual(got[1]?.marker_id, "chunk_2");
  });

  it("returns [] for empty question", async () => {
    bindFixtureSearch();
    const got = await retrieveContext("   ", 8);
    assert.deepStrictEqual(got, []);
  });

  it("returns [] when topK is 0", async () => {
    bindFixtureSearch();
    const got = await retrieveContext("anything", 0);
    assert.deepStrictEqual(got, []);
  });
});

// ─── prompt.ts ─────────────────────────────────────────────────────────────

describe("buildPrompt", () => {
  it("system message contains anti-hallucination guard", () => {
    const chunks: RetrievedChunk[] = [
      {
        chunk_id: 1,
        marker_id: "chunk_1",
        file_path: "x.md",
        content: "alpha",
        score: 1,
      },
    ];
    const { system, user } = buildPrompt("q", chunks);
    assert.ok(system.includes("Answer ONLY"));
    assert.ok(system.includes("Cite EVERY"));
    assert.ok(user.includes("[chunk_1]"));
    assert.ok(user.includes("alpha"));
  });

  it("retry prompt uses STRICT MODE language", () => {
    const chunks: RetrievedChunk[] = [
      {
        chunk_id: 1,
        marker_id: "chunk_1",
        file_path: "x.md",
        content: "alpha",
        score: 1,
      },
    ];
    const { system } = buildRetryPrompt("q", chunks);
    assert.ok(system.includes("STRICT MODE"));
    assert.ok(system.includes("only cite markers literally listed"));
  });
});

// ─── provider.ts ───────────────────────────────────────────────────────────

describe("selectProvider", () => {
  it("returns gemini placeholder by default", () => {
    const p = selectProvider();
    assert.strictEqual(p.name, "gemini");
  });

  it("returns mock when name='mock'", () => {
    const p = selectProvider("mock");
    assert.strictEqual(p.name, "mock");
  });

  it("falls back to gemini for unknown provider name", () => {
    const p = selectProvider("does-not-exist");
    assert.strictEqual(p.name, "gemini");
  });
});

describe("MockProvider", () => {
  it("dequeues canned responses in order", async () => {
    const m = new MockProvider(["first", "second"], 0);
    const a = await m.complete({
      system: "s",
      user: "u",
      maxTokens: 100,
      temperature: 0,
      model: "mock",
    });
    const b = await m.complete({
      system: "s",
      user: "u",
      maxTokens: 100,
      temperature: 0,
      model: "mock",
    });
    assert.strictEqual(a.text, "first");
    assert.strictEqual(b.text, "second");
  });

  it("reports tokensIn/tokensOut > 0", async () => {
    const m = new MockProvider(["hello world"], 0);
    const r = await m.complete({
      system: "system prompt",
      user: "user prompt",
      maxTokens: 100,
      temperature: 0,
      model: "mock",
    });
    assert.ok(r.tokensIn > 0);
    assert.ok(r.tokensOut > 0);
    assert.ok(r.latencyMs >= 0);
  });
});

// ─── end-to-end answer() ───────────────────────────────────────────────────

describe("answer() end-to-end", () => {
  it("happy path: returns answer + citations + metadata", async () => {
    bindFixtureSearch();
    const provider = new MockProvider(
      ["Default model is gemini-2.5-flash-lite [chunk_1]."],
      0
    );
    const res = await answer({
      question: "What is the default answer model?",
      providerOverride: provider,
    });

    assert.ok(res.answer.includes("[chunk_1]"));
    assert.strictEqual(res.citations.length, 1);
    assert.strictEqual(res.citations[0]?.chunk_id, 101);
    assert.strictEqual(res.citations[0]?.marker_id, "chunk_1");
    assert.ok(res.metadata.tokens_in > 0);
    assert.ok(res.metadata.tokens_out > 0);
    assert.ok(res.metadata.latency_ms >= 0);
    assert.strictEqual(res.metadata.provider, "mock");
    assert.strictEqual(res.metadata.retrieval_count, 3);
    assert.strictEqual(res.metadata.retry_count, 0);
    assert.strictEqual(res.metadata.fallback_used, false);
    assert.strictEqual(res.metadata.failed_reason, undefined);
  });

  it("empty retrieval → canonical 'no memory matches'", async () => {
    __setRawSearchForTests(async () => []);
    const provider = new MockProvider(["should not be called"], 0);
    const res = await answer({
      question: "Nothing matches this",
      providerOverride: provider,
    });
    assert.match(res.answer, /no memory matches/i);
    assert.deepStrictEqual(res.citations, []);
    assert.strictEqual(res.metadata.retrieval_count, 0);
    assert.strictEqual(res.metadata.tokens_in, 0);
    assert.strictEqual(res.metadata.tokens_out, 0);
    assert.strictEqual(res.metadata.failed_reason, "retrieval_empty");
  });

  it("provider error throws AnswerError(llm_error)", async () => {
    bindFixtureSearch();
    const provider = new MockProvider([], 0);
    provider.throwNext(new Error("network timeout"));
    await assert.rejects(
      () => answer({ question: "q", providerOverride: provider }),
      (err: unknown) => {
        assert.ok(err instanceof AnswerError);
        assert.strictEqual((err as AnswerError).reason, "llm_error");
        return true;
      }
    );
  });

  it("hallucinated citation triggers retry and recovers", async () => {
    bindFixtureSearch();
    // First response cites chunk_99 (out of range, retrieval has only 3).
    // Retry response cites chunk_1 (valid).
    const provider = new MockProvider(
      [
        "Per memory [chunk_99] the answer is gemini-2.5-flash-lite.",
        "Per memory [chunk_1] the answer is gemini-2.5-flash-lite.",
      ],
      0
    );
    const res = await answer({
      question: "Which model is default?",
      providerOverride: provider,
    });
    assert.ok(res.answer.includes("[chunk_1]"));
    assert.strictEqual(res.metadata.fallback_used, true);
    assert.strictEqual(res.metadata.retry_count, 1);
    assert.strictEqual(res.metadata.failed_reason, undefined);
    assert.strictEqual(res.citations.length, 1);
    assert.strictEqual(res.citations[0]?.chunk_id, 101);
  });

  it("hallucination after retry throws AnswerError(hallucination_after_retry)", async () => {
    bindFixtureSearch();
    const provider = new MockProvider(
      [
        "Bogus [chunk_99] answer.",
        "Still bogus [chunk_77] answer.",
      ],
      0
    );
    await assert.rejects(
      () => answer({ question: "q", providerOverride: provider }),
      (err: unknown) => {
        assert.ok(err instanceof AnswerError);
        assert.strictEqual(
          (err as AnswerError).reason,
          "hallucination_after_retry"
        );
        assert.strictEqual((err as AnswerError).metadata.fallback_used, true);
        assert.strictEqual((err as AnswerError).metadata.retry_count, 1);
        return true;
      }
    );
  });

  it("invalid_input: empty question rejected", async () => {
    await assert.rejects(
      () => answer({ question: "" }),
      (err: unknown) => {
        assert.ok(err instanceof AnswerError);
        assert.strictEqual((err as AnswerError).reason, "invalid_input");
        return true;
      }
    );
  });

  it("env override NOX_ANSWER_MODEL flows into metadata.model", async () => {
    bindFixtureSearch();
    const prev = process.env.NOX_ANSWER_MODEL;
    process.env.NOX_ANSWER_MODEL = "gemini-2.5-flash";
    try {
      const provider = new MockProvider(["Answer [chunk_1]"], 0);
      const res = await answer({
        question: "Which model?",
        providerOverride: provider,
      });
      assert.strictEqual(res.metadata.model, "gemini-2.5-flash");
    } finally {
      if (prev === undefined) delete process.env.NOX_ANSWER_MODEL;
      else process.env.NOX_ANSWER_MODEL = prev;
    }
  });

  it("retrieveOverride injection path works without binding search", async () => {
    // No __setRawSearchForTests call — using opts.retrieveOverride directly.
    const provider = new MockProvider(["Direct [chunk_1]"], 0);
    const res = await answer({
      question: "test",
      providerOverride: provider,
      retrieveOverride: async () => [
        {
          chunk_id: 999,
          marker_id: "chunk_1",
          file_path: "inline.md",
          content: "inline content",
        },
      ],
    });
    assert.strictEqual(res.citations[0]?.chunk_id, 999);
    assert.strictEqual(res.metadata.retrieval_count, 1);
  });
});

// ─── parseCitations() unit tests ───────────────────────────────────────────

describe("parseCitations", () => {
  const chunks: RetrievedChunk[] = [
    { chunk_id: 11, marker_id: "chunk_1", file_path: "a.md", content: "alpha", score: 1 },
    { chunk_id: 22, marker_id: "chunk_2", file_path: "b.md", content: "beta", score: 0.5 },
  ];

  it("extracts valid markers into citations", () => {
    const { citations, hallucinated } = parseCitations(
      "alpha is [chunk_1] and beta is [chunk_2]",
      chunks
    );
    assert.strictEqual(citations.length, 2);
    assert.deepStrictEqual(hallucinated, []);
    assert.strictEqual(citations[0]?.chunk_id, 11);
    assert.strictEqual(citations[1]?.chunk_id, 22);
  });

  it("flags out-of-range markers as hallucinated", () => {
    const { citations, hallucinated } = parseCitations(
      "Bogus [chunk_99] reference",
      chunks
    );
    assert.strictEqual(citations.length, 0);
    assert.deepStrictEqual(hallucinated, ["chunk_99"]);
  });

  it("dedupes repeated markers in the same response", () => {
    const { citations } = parseCitations(
      "[chunk_1] foo [chunk_1] bar [chunk_1]",
      chunks
    );
    assert.strictEqual(citations.length, 1);
  });

  it("returns empty arrays for text with no markers", () => {
    const { citations, hallucinated } = parseCitations("no citations here", chunks);
    assert.deepStrictEqual(citations, []);
    assert.deepStrictEqual(hallucinated, []);
  });

  it("snippet is trimmed to ≤200 chars", () => {
    const longChunk: RetrievedChunk = {
      chunk_id: 1,
      marker_id: "chunk_1",
      file_path: "long.md",
      content: "x".repeat(500),
      score: 1,
    };
    const { citations } = parseCitations("[chunk_1]", [longChunk]);
    assert.ok((citations[0]?.snippet.length ?? 0) <= 200);
  });
});
