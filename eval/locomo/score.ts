/**
 * score.ts — compute LoCoMo retrieval metrics from run.ts output.
 *
 * Metrics:
 *   R@1, R@5, R@10  : recall at K. Numerator = retrieved-in-gold within top-K;
 *                     denominator = |gold| (capped by K).
 *   MRR             : mean reciprocal rank of the first gold hit (0 if absent).
 *   nDCG@10         : standard ndcg, binary relevance, log2(i+2).
 *   coverage        : share of questions where at least one gold was retrieved
 *                     in any top-20 position. Diagnostic only.
 *
 * Aggregation: simple mean across questions. Per-category breakdown emitted.
 * --ci adds Wilson 95% binomial CI for R@K (rough, for headline guidance).
 *
 * Usage:
 *   npx tsx eval/locomo/score.ts eval/locomo/dry-run-sample.json
 *   npx tsx eval/locomo/score.ts full-run.json --ci
 */

import { readFile } from "node:fs/promises";

interface RunRecord {
  question_id: string;
  category: number;
  category_name: string;
  question: string;
  gold_chunk_ids: string[];
  retrieved_chunk_ids: string[];
  retrieved_scores: number[];
  retrieval_ms: number;
  error?: string;
}

interface RunFile {
  meta: { n: number; seed: number; mode: string; dryRun: boolean };
  records: RunRecord[];
}

function recallAtK(retrieved: string[], gold: Set<string>, k: number): number {
  if (gold.size === 0) return 0;
  const denom = Math.min(gold.size, k);
  let hits = 0;
  for (let i = 0; i < Math.min(retrieved.length, k); i++) {
    if (gold.has(retrieved[i])) hits++;
  }
  return hits / denom;
}

function mrr(retrieved: string[], gold: Set<string>): number {
  for (let i = 0; i < retrieved.length; i++) {
    if (gold.has(retrieved[i])) return 1 / (i + 1);
  }
  return 0;
}

function ndcgAtK(retrieved: string[], gold: Set<string>, k: number): number {
  let dcg = 0;
  for (let i = 0; i < Math.min(retrieved.length, k); i++) {
    if (gold.has(retrieved[i])) dcg += 1 / Math.log2(i + 2);
  }
  const idealCount = Math.min(gold.size, k);
  let idcg = 0;
  for (let i = 0; i < idealCount; i++) idcg += 1 / Math.log2(i + 2);
  return idcg > 0 ? dcg / idcg : 0;
}

function wilsonCi(p: number, n: number, z = 1.96): [number, number] {
  if (n === 0) return [0, 0];
  const denom = 1 + (z * z) / n;
  const centre = p + (z * z) / (2 * n);
  const margin = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [(centre - margin) / denom, (centre + margin) / denom];
}

function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

interface MetricSet {
  n: number;
  r1: number;
  r5: number;
  r10: number;
  mrr: number;
  ndcg10: number;
  coverage: number;
  ci?: { r5: [number, number]; r1: [number, number] };
}

function computeMetrics(records: RunRecord[], withCi: boolean): MetricSet {
  const r1: number[] = [];
  const r5: number[] = [];
  const r10: number[] = [];
  const mrrs: number[] = [];
  const ndcgs: number[] = [];
  const covered: number[] = [];

  for (const rec of records) {
    if (rec.error) continue;
    const gold = new Set(rec.gold_chunk_ids);
    const retr = rec.retrieved_chunk_ids;
    r1.push(recallAtK(retr, gold, 1));
    r5.push(recallAtK(retr, gold, 5));
    r10.push(recallAtK(retr, gold, 10));
    mrrs.push(mrr(retr, gold));
    ndcgs.push(ndcgAtK(retr, gold, 10));
    covered.push(retr.slice(0, 20).some((c) => gold.has(c)) ? 1 : 0);
  }

  const m: MetricSet = {
    n: r5.length,
    r1: mean(r1),
    r5: mean(r5),
    r10: mean(r10),
    mrr: mean(mrrs),
    ndcg10: mean(ndcgs),
    coverage: mean(covered),
  };
  if (withCi) {
    m.ci = {
      r1: wilsonCi(m.r1, m.n),
      r5: wilsonCi(m.r5, m.n),
    };
  }
  return m;
}

async function main(): Promise<void> {
  const file = process.argv[2];
  const withCi = process.argv.includes("--ci");
  if (!file) {
    console.error("Usage: score.ts <run-output.json> [--ci]");
    process.exit(2);
  }
  const data: RunFile = JSON.parse(await readFile(file, "utf8"));
  const overall = computeMetrics(data.records, withCi);

  const byCat = new Map<string, RunRecord[]>();
  for (const r of data.records) {
    const k = r.category_name;
    if (!byCat.has(k)) byCat.set(k, []);
    byCat.get(k)!.push(r);
  }
  const perCategory: Record<string, MetricSet> = {};
  for (const [k, rs] of byCat) perCategory[k] = computeMetrics(rs, withCi);

  const errors = data.records.filter((r) => r.error).length;

  const summary = {
    meta: data.meta,
    overall,
    per_category: perCategory,
    errors,
    notes: data.meta.dryRun
      ? "DRY-RUN — sample too small for statistical inference. Numbers validate plumbing only."
      : "Full run. R@5 is the headline metric.",
    generated_at: new Date().toISOString(),
  };

  process.stdout.write(JSON.stringify(summary, null, 2) + "\n");

  // Print a human summary on stderr.
  console.error(`[score] n=${overall.n} errors=${errors}`);
  console.error(`[score] overall: R@1=${overall.r1.toFixed(4)}  R@5=${overall.r5.toFixed(4)}  R@10=${overall.r10.toFixed(4)}  MRR=${overall.mrr.toFixed(4)}  nDCG@10=${overall.ndcg10.toFixed(4)}  coverage=${overall.coverage.toFixed(4)}`);
  for (const [k, m] of Object.entries(perCategory)) {
    console.error(`[score]   ${k}: n=${m.n}  R@5=${m.r5.toFixed(4)}  MRR=${m.mrr.toFixed(4)}  nDCG@10=${m.ndcg10.toFixed(4)}`);
  }
  if (data.meta.dryRun) {
    console.error("[score] DRY-RUN — do not publish.");
  }
}

main().catch((e) => {
  console.error("[score] ERROR:", e instanceof Error ? e.message : e);
  process.exit(1);
});
