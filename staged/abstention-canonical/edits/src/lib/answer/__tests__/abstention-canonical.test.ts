/**
 * src/lib/answer/__tests__/abstention-canonical.test.ts
 *
 * Step 7b: an answer with NO citation is replaced by the canonical refusal.
 *
 * Why this file exists. The 73 tests already in this module all pass against
 * the change, which means none of them reaches the new path — and a fix no test
 * reaches is indistinguishable from a fix that was never applied. The first
 * case below FAILS without step 7b (it asserts the canonical text where the
 * unpatched code returns the model's prose), so it is a mutation test and not a
 * restatement.
 *
 * The behaviour, and the reason for it: the system prompt requires every
 * factual claim to carry a [chunk_N] marker. An answer with no marker therefore
 * violates that contract — nothing in it is anchored in the retrieved context
 * and the caller cannot check any of it. Measured on 2026-10-27 against a
 * bounded judge over 48 items: `citations.length === 0` identifies abstention
 * at TP=23 FP=0 FN=3 (kappa 0.8754), against the evaluation harness's
 * five-substring predicate at TP=21 FP=0 FN=5 (kappa 0.7938).
 *
 * Runner: node:test (node --test)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  answer,
  __setRawSearchForTests,
  MockProvider,
} from "../index.js";
import type { RawChunk } from "../types.js";

// Shape copied from integration.test.ts's fixtureChunks(), not invented: the
// field names are `file_path` and `content`, and a hand-written fixture using
// `source_file`/`chunk_text` threw inside assembleUserPrompt on a field the
// prompt builder reads but the fixture did not carry.
function chunks(): RawChunk[] {
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
  ];
}

function bind(): void {
  __setRawSearchForTests(async () => chunks());
}

describe("step 7b — unanchored answer becomes the canonical refusal", () => {
  it("MUTATION: prose with no [chunk_N] marker is replaced, and the reason recorded",
     async () => {
    bind();
    // The model answers in prose, citing nothing. Unpatched, this text is served
    // verbatim and `failed_reason` stays undefined — which is what the five
    // substrings then have to guess at.
    const provider = new MockProvider(
      ["O tier_decay nao e explicitamente explicado no contexto fornecido."], 0);
    const res = await answer({ question: "o que e tier_decay", providerOverride: provider });

    assert.match(res.answer, /no memory matches/i,
      "an answer with no citation must be replaced by the canonical refusal");
    assert.deepStrictEqual(res.citations, []);
    assert.strictEqual(res.metadata.failed_reason, "model_abstained");
    // retrieval DID return chunks: this is not retrieval_empty, and conflating
    // the two would hide which half of the pipeline came up empty.
    assert.strictEqual(res.metadata.retrieval_count, 2);
    assert.ok(res.metadata.tokens_in > 0,
      "the LLM was called, unlike the retrieval_empty short-circuit");
  });

  it("an answer WITH a citation is left untouched — the guard must not over-mark",
     async () => {
    bind();
    const provider = new MockProvider(
      ["The default answer model is gemini-2.5-flash-lite. [chunk_1]"], 0);
    const res = await answer({ question: "qual o modelo padrao", providerOverride: provider });

    assert.match(res.answer, /gemini-2\.5-flash-lite/);
    assert.doesNotMatch(res.answer, /no memory matches/i);
    assert.strictEqual(res.citations.length, 1);
    assert.strictEqual(res.metadata.failed_reason, undefined);
  });

  it("empty retrieval still reports retrieval_empty, not model_abstained",
     async () => {
    // The two paths produce the same TEXT and must stay distinguishable by
    // reason: one spent no tokens, the other called the model and was declined.
    __setRawSearchForTests(async () => []);
    const provider = new MockProvider(["should not be called"], 0);
    const res = await answer({ question: "nada casa", providerOverride: provider });

    assert.match(res.answer, /no memory matches/i);
    assert.strictEqual(res.metadata.failed_reason, "retrieval_empty");
    assert.strictEqual(res.metadata.retrieval_count, 0);
    assert.strictEqual(res.metadata.tokens_in, 0);
  });
});
