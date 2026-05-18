/**
 * eval/confidence-eval.ts — shadow-mode eval scaffold for L3 ranking gate.
 *
 * Runs the golden set across variants A/B/C/D (spec §6) and computes per-query
 * nDCG@10 delta vs baseline A. Writes deltas to `confidence_eval_log`
 * (migration v22) for later analysis.
 *
 * Gate decision: returns PASS if mean delta ≥ +1.0pp (0.01) across n>=10
 * queries AND no individual variant regresses by >2.0pp.
 *
 * IMPORTANT: this is the SCAFFOLD only. The actual search runner is pluggable
 * (`SearchRunner` interface) so the implementation can wire to nox-mem's
 * hybrid search later. A mock runner is provided for tests + CI.
 *
 * Spec ref: specs/2026-05-17-L3-confidence-field.md §6, §10 DoD-B.
 */

import type {
  ConfidenceEvalDelta,
} from "../src/lib/confidence/types.js";

export interface GoldenQuery {
  query_id: string;
  query_text: string;
  /** Expected chunk_ids in ideal ranked order. */
  expected_chunk_ids: number[];
}

export interface SearchResultRow {
  chunk_id: number;
  /** Pre-confidence salience score. */
  score: number;
  confidence?: number | null;
  provenance_kind?: string | null;
  superseded_by?: number | null;
}

export type EvalVariant = "A" | "B" | "C" | "D";

export interface SearchRunner {
  /** Run a search for the given variant. Returns ranked chunk list (top-K). */
  run(variant: EvalVariant, query: GoldenQuery, topK: number): Promise<SearchResultRow[]>;
}

export interface EvalRunOpts {
  goldenSet: GoldenQuery[];
  runner: SearchRunner;
  /** Top-K cutoff for nDCG. Default 10. */
  topK?: number;
  /** Minimum delta to pass gate (default 0.01 = +1.0pp). */
  minDeltaToPass?: number;
  /** Maximum tolerated regression magnitude (default 0.02). */
  maxRegression?: number;
  /** When non-null, append per-query delta to this sink. */
  logSink?: (delta: ConfidenceEvalDelta) => void;
  /** Override ISO timestamp for reproducibility. */
  now?: () => string;
}

export interface EvalVerdict {
  verdict: "PASS" | "FAIL" | "INSUFFICIENT";
  reason: string;
  per_variant: Record<
    EvalVariant,
    {
      mean_ndcg: number;
      mean_delta: number;
      n_queries: number;
      regression_count: number;
    }
  >;
  total_queries: number;
}

/**
 * Computes DCG@K — sum(rel_i / log2(i+2)) for i in [0, K).
 * Relevance score = 1 if chunk is in expected set, weighted by inverse rank
 * of expected position (cap at K).
 */
function dcg(
  resultIds: number[],
  expectedIds: number[],
  k: number
): number {
  let s = 0;
  const top = resultIds.slice(0, k);
  for (let i = 0; i < top.length; i++) {
    const id = top[i]!;
    const expectedRank = expectedIds.indexOf(id);
    if (expectedRank === -1) continue;
    // Higher relevance when expected rank is low (earlier in golden order)
    const rel = expectedRank < k ? 1 / (1 + expectedRank * 0.1) : 0.5;
    s += rel / Math.log2(i + 2);
  }
  return s;
}

function idealDcg(expectedIds: number[], k: number): number {
  const top = expectedIds.slice(0, k);
  let s = 0;
  for (let i = 0; i < top.length; i++) {
    const rel = 1 / (1 + i * 0.1);
    s += rel / Math.log2(i + 2);
  }
  return s;
}

/** nDCG@K — normalised DCG (0..1+). */
export function ndcgAtK(
  resultIds: number[],
  expectedIds: number[],
  k: number
): number {
  if (expectedIds.length === 0) return 0;
  const ideal = idealDcg(expectedIds, k);
  if (ideal === 0) return 0;
  return dcg(resultIds, expectedIds, k) / ideal;
}

/** Mean of an array (defensive against empty). */
function mean(vals: number[]): number {
  if (vals.length === 0) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

/**
 * runConfidenceEval() — execute golden set across variants A/B/C/D.
 *
 * Returns a verdict and per-variant summary stats. Logs every (query × variant)
 * delta via the optional `logSink`.
 */
export async function runConfidenceEval(
  opts: EvalRunOpts
): Promise<EvalVerdict> {
  const topK = opts.topK ?? 10;
  const minDelta = opts.minDeltaToPass ?? 0.01;
  const maxRegression = opts.maxRegression ?? 0.02;
  const now = opts.now ?? (() => new Date().toISOString());

  const variants: EvalVariant[] = ["A", "B", "C", "D"];
  const perVariantNdcg: Record<EvalVariant, number[]> = {
    A: [],
    B: [],
    C: [],
    D: [],
  };
  const perVariantDeltas: Record<EvalVariant, number[]> = {
    A: [],
    B: [],
    C: [],
    D: [],
  };
  const perVariantRegressions: Record<EvalVariant, number> = {
    A: 0,
    B: 0,
    C: 0,
    D: 0,
  };

  for (const query of opts.goldenSet) {
    // Run baseline first to compute deltas
    let baselineNdcg = 0;
    for (const variant of variants) {
      const results = await opts.runner.run(variant, query, topK);
      const ndcg = ndcgAtK(
        results.map((r) => r.chunk_id),
        query.expected_chunk_ids,
        topK
      );
      perVariantNdcg[variant].push(ndcg);
      if (variant === "A") {
        baselineNdcg = ndcg;
        perVariantDeltas.A.push(0);
      } else {
        const delta = ndcg - baselineNdcg;
        perVariantDeltas[variant].push(delta);
        if (delta < -maxRegression) {
          perVariantRegressions[variant]++;
        }
      }
      if (opts.logSink) {
        opts.logSink({
          query_id: query.query_id,
          variant,
          ndcg_at_10: ndcg,
          delta_vs_baseline: variant === "A" ? 0 : ndcg - baselineNdcg,
          ran_at: now(),
        });
      }
    }
  }

  const per_variant: EvalVerdict["per_variant"] = {
    A: {
      mean_ndcg: mean(perVariantNdcg.A),
      mean_delta: mean(perVariantDeltas.A),
      n_queries: opts.goldenSet.length,
      regression_count: perVariantRegressions.A,
    },
    B: {
      mean_ndcg: mean(perVariantNdcg.B),
      mean_delta: mean(perVariantDeltas.B),
      n_queries: opts.goldenSet.length,
      regression_count: perVariantRegressions.B,
    },
    C: {
      mean_ndcg: mean(perVariantNdcg.C),
      mean_delta: mean(perVariantDeltas.C),
      n_queries: opts.goldenSet.length,
      regression_count: perVariantRegressions.C,
    },
    D: {
      mean_ndcg: mean(perVariantNdcg.D),
      mean_delta: mean(perVariantDeltas.D),
      n_queries: opts.goldenSet.length,
      regression_count: perVariantRegressions.D,
    },
  };

  if (opts.goldenSet.length < 10) {
    return {
      verdict: "INSUFFICIENT",
      reason: `n=${opts.goldenSet.length} queries, need ≥10`,
      per_variant,
      total_queries: opts.goldenSet.length,
    };
  }

  const bestNonBaseline = Math.max(
    per_variant.B.mean_delta,
    per_variant.C.mean_delta,
    per_variant.D.mean_delta
  );

  if (bestNonBaseline >= minDelta) {
    return {
      verdict: "PASS",
      reason: `best variant delta=${bestNonBaseline.toFixed(4)} ≥ ${minDelta}`,
      per_variant,
      total_queries: opts.goldenSet.length,
    };
  }

  return {
    verdict: "FAIL",
    reason: `best variant delta=${bestNonBaseline.toFixed(4)} < ${minDelta} (annotation-only mode recommended)`,
    per_variant,
    total_queries: opts.goldenSet.length,
  };
}
