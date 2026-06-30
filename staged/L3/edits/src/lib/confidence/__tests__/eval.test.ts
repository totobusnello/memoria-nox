/**
 * T10 — Eval scaffold tests (6 tests).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ndcgAtK,
  runConfidenceEval,
  type GoldenQuery,
  type SearchRunner,
  type EvalVariant,
  type SearchResultRow,
} from "../../../../eval/confidence-eval.js";

const goldenSet: GoldenQuery[] = Array.from({ length: 12 }, (_, i) => ({
  query_id: `Q-${String(i + 1).padStart(3, "0")}`,
  query_text: `test query ${i}`,
  expected_chunk_ids: [i + 1, i + 2, i + 3],
}));

function makeRunner(
  fn: (variant: EvalVariant, q: GoldenQuery) => SearchResultRow[]
): SearchRunner {
  return {
    async run(variant: EvalVariant, query: GoldenQuery, _topK: number) {
      return fn(variant, query);
    },
  };
}

test("T10.1 ndcgAtK perfect match → 1.0", () => {
  const r = ndcgAtK([1, 2, 3], [1, 2, 3], 10);
  assert.ok(Math.abs(r - 1.0) < 0.001);
});

test("T10.2 ndcgAtK no overlap → 0", () => {
  const r = ndcgAtK([99, 98, 97], [1, 2, 3], 10);
  assert.equal(r, 0);
});

test("T10.3 runConfidenceEval insufficient queries returns INSUFFICIENT", async () => {
  const runner = makeRunner((_v, q) =>
    q.expected_chunk_ids.map((id) => ({ chunk_id: id, score: 1 }))
  );
  const verdict = await runConfidenceEval({
    goldenSet: goldenSet.slice(0, 5),
    runner,
  });
  assert.equal(verdict.verdict, "INSUFFICIENT");
});

test("T10.4 runConfidenceEval all-equal returns FAIL (no lift)", async () => {
  const runner = makeRunner((_v, q) =>
    q.expected_chunk_ids.map((id) => ({ chunk_id: id, score: 1 }))
  );
  const verdict = await runConfidenceEval({ goldenSet, runner });
  assert.equal(verdict.verdict, "FAIL");
  assert.equal(verdict.per_variant.A.mean_delta, 0);
});

test("T10.5 runConfidenceEval lift in variant B returns PASS", async () => {
  // Baseline A always returns wrong-order; B/C/D return perfect order
  const runner = makeRunner((v, q) => {
    if (v === "A") {
      // Reverse order so nDCG is poor
      return q.expected_chunk_ids
        .slice()
        .reverse()
        .map((id) => ({ chunk_id: id, score: 0.5 }));
    }
    return q.expected_chunk_ids.map((id) => ({ chunk_id: id, score: 1 }));
  });
  const verdict = await runConfidenceEval({ goldenSet, runner });
  assert.equal(verdict.verdict, "PASS");
  assert.ok(verdict.per_variant.B.mean_delta > 0);
});

test("T10.6 runConfidenceEval logSink invoked per (query × variant)", async () => {
  const runner = makeRunner((_v, q) =>
    q.expected_chunk_ids.map((id) => ({ chunk_id: id, score: 1 }))
  );
  const sink: unknown[] = [];
  await runConfidenceEval({
    goldenSet: goldenSet.slice(0, 10),
    runner,
    logSink: (d) => sink.push(d),
  });
  // 10 queries × 4 variants = 40
  assert.equal(sink.length, 40);
});
