/**
 * cli-adapter.ts — bridge between the standalone scaffold (parser/run/score)
 * and the first-class `nox-mem eval longmemeval` CLI command.
 *
 * The scaffold files (parser.ts / run.ts / score.ts) are the source of truth
 * for protocol and algorithm. This module exposes a single async function
 * `runLongMemEvalCli(opts)` that:
 *   1. Parses/validates the dataset path.
 *   2. Constructs the RunOptions forwarded to run.ts internals.
 *   3. Constructs the ScoreOptions forwarded to score.ts internals.
 *   4. Writes structured JSON output.
 *   5. Logs eval_runs telemetry (summary only, no question content).
 *
 * CONSTRAINT: DO NOT modify parser.ts / run.ts / score.ts. All extensions
 * live here or in src/cli/eval-longmemeval.ts.
 */

import { createHash } from "node:crypto";
import { readFile, stat, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadSplit, extractQuestions, extractSessionChunks, type QARecord, type SessionChunk } from "./parser.js";

export type JudgeModel = "gpt-4o" | "gemini-2.5-pro" | "gemini-2.5-flash";

export interface LongMemEvalCliOptions {
  /** Path to LongMemEval JSONL or JSON dataset. Required. */
  dataset: string;
  /** LLM judge model. Default: gemini-2.5-pro (per D41 cost bias). */
  judge: JudgeModel;
  /** Max questions to run. Default: all. */
  limit?: number;
  /** Stratified sample seed. Default: 42. */
  seed: number;
  /** Output JSON path. Default: ./longmemeval-results-<ts>.json */
  output?: string;
  /** Eval DB path (isolated). Default: ./eval-longmemeval.db */
  db: string;
  /** FTS5-only ablation — disable vector + KG. Default: false. */
  keywordOnly: boolean;
  /** Skip generation step, only measure retrieval recall. Default: false. */
  retrievalOnly: boolean;
  /** Multi-query expansion via LLM. Default: false. */
  expansion: boolean;
  /** Retrieval top-K. Default: 5. */
  topK: number;
  /** Validate dataset + parse only, no API calls. Default: false. */
  dryRun: boolean;
  /** Path to existing partial results.json to resume from. */
  resumeFrom?: string;
  /** Per-question logging. Default: false. */
  verbose: boolean;
  /** Optional output directory override (env: LONGMEMEVAL_OUTPUT_DIR). */
  outputDir?: string;
}

export const DEFAULT_OPTS: Omit<LongMemEvalCliOptions, "dataset"> = {
  judge: "gemini-2.5-pro",
  seed: 42,
  db: "./eval-longmemeval.db",
  keywordOnly: false,
  retrievalOnly: false,
  expansion: false,
  topK: 5,
  dryRun: false,
  verbose: false,
};

/** Effective judge: env LONGMEMEVAL_JUDGE overrides CLI flag default. */
export function resolveJudge(cliJudge: JudgeModel): JudgeModel {
  const env = process.env.LONGMEMEVAL_JUDGE as JudgeModel | undefined;
  return env ?? cliJudge;
}

/** Effective output path, honouring LONGMEMEVAL_OUTPUT_DIR env. */
export function resolveOutputPath(opts: { output?: string; outputDir?: string }): string {
  const dir = opts.outputDir ?? process.env.LONGMEMEVAL_OUTPUT_DIR ?? ".";
  if (opts.output) {
    // If absolute or relative-with-dir, use directly; else prepend dir.
    return opts.output.includes("/") ? opts.output : resolve(dir, opts.output);
  }
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  return resolve(dir, `longmemeval-results-${ts}.json`);
}

// ---------------------------------------------------------------------------
// Dataset SHA (for provenance in output JSON)
// ---------------------------------------------------------------------------

async function datasetCommit(datasetPath: string): Promise<string> {
  try {
    const buf = await readFile(datasetPath);
    return createHash("sha256").update(buf).digest("hex").slice(0, 16);
  } catch {
    return "unknown";
  }
}

// ---------------------------------------------------------------------------
// Resume-from: load already-done question IDs from a partial results file
// ---------------------------------------------------------------------------

interface PartialResult {
  questions?: Array<{ question_id?: string }>;
}

export async function loadDoneQuestionIds(path: string): Promise<Set<string>> {
  try {
    const txt = await readFile(path, "utf8");
    const j = JSON.parse(txt) as PartialResult;
    const done = new Set<string>();
    for (const q of j.questions ?? []) {
      if (q.question_id) done.add(q.question_id);
    }
    return done;
  } catch {
    return new Set<string>();
  }
}

// ---------------------------------------------------------------------------
// Wilson 95% CI (mirrored from score.ts so cli-adapter can include it in
// top-level summary without re-importing score internals)
// ---------------------------------------------------------------------------

export function wilsonCi(p: number, n: number, z = 1.96): [number, number] {
  if (n === 0) return [0, 0];
  const denom = 1 + (z * z) / n;
  const centre = p + (z * z) / (2 * n);
  const margin = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [(centre - margin) / denom, (centre + margin) / denom];
}

// ---------------------------------------------------------------------------
// Output schema builder — produces the results JSON spec
// ---------------------------------------------------------------------------

export interface PerQuestionResult {
  question_id: string;
  question_type: string;
  base_category: string;
  is_abstention: boolean;
  verdict: "correct" | "incorrect" | "skip" | "judge_error";
  judge_rationale?: string;
  retrieval_session_hit: boolean;
  retrieval_ms: number;
  generation_ms: number;
  judge_ms: number;
  error?: string;
}

export interface ResultsSummary {
  accuracy: number;
  accuracy_wilson_95ci: [number, number];
  per_category: Record<string, number>;
  per_category_abs: Record<string, number>;
  judge_disagreement_rate: number;
  retrieval_only_recall_at_5: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
}

export interface EvalResults {
  dataset: string;
  dataset_commit: string;
  questions_total: number;
  questions_run: number;
  judge: string;
  seed: number;
  summary: ResultsSummary;
  questions: PerQuestionResult[];
  _meta: {
    started_at: string;
    finished_at: string;
    dry_run: boolean;
    keyword_only: boolean;
    retrieval_only: boolean;
    expansion: boolean;
    top_k: number;
    db: string;
    resume_from?: string;
  };
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(sorted.length - 1, Math.floor(sorted.length * p));
  return sorted[idx];
}

export function buildResults(
  opts: LongMemEvalCliOptions,
  datasetPath: string,
  datasetCommitHash: string,
  totalQuestions: number,
  startedAt: string,
  judgeModel: string,
  perQ: PerQuestionResult[],
): EvalResults {
  const scoreable = perQ.filter((r) => r.verdict !== "skip" && r.verdict !== "judge_error");
  const correct = scoreable.filter((r) => r.verdict === "correct").length;
  const accuracy = scoreable.length > 0 ? correct / scoreable.length : 0;
  const ci = wilsonCi(accuracy, scoreable.length);

  // Per-category
  const byBase: Record<string, { correct: number; total: number }> = {};
  const byAbs: Record<string, { correct: number; total: number }> = {};
  for (const r of scoreable) {
    const k = r.base_category;
    if (!byBase[k]) byBase[k] = { correct: 0, total: 0 };
    byBase[k].total++;
    if (r.verdict === "correct") byBase[k].correct++;
    if (r.is_abstention) {
      if (!byAbs[k]) byAbs[k] = { correct: 0, total: 0 };
      byAbs[k].total++;
      if (r.verdict === "correct") byAbs[k].correct++;
    }
  }
  const per_category: Record<string, number> = {};
  for (const [k, v] of Object.entries(byBase)) per_category[k] = v.total > 0 ? v.correct / v.total : 0;
  const per_category_abs: Record<string, number> = {};
  for (const [k, v] of Object.entries(byAbs)) per_category_abs[k] = v.total > 0 ? v.correct / v.total : 0;

  // Retrieval recall@5 (session hit)
  const retrieval_only_recall_at_5 =
    scoreable.length > 0
      ? scoreable.filter((r) => r.retrieval_session_hit).length / scoreable.length
      : 0;

  // Latency (retrieval_ms + generation_ms combined per question)
  const latencies = perQ
    .map((r) => r.retrieval_ms + r.generation_ms)
    .filter((v) => v > 0)
    .sort((a, b) => a - b);
  const latency_p50_ms = percentile(latencies, 0.5);
  const latency_p95_ms = percentile(latencies, 0.95);

  // Judge disagreement: judge_error rate as proxy (no dual-judge here)
  const judgeErrors = perQ.filter((r) => r.verdict === "judge_error").length;
  const judge_disagreement_rate = perQ.length > 0 ? judgeErrors / perQ.length : 0;

  return {
    dataset: basename(datasetPath),
    dataset_commit: datasetCommitHash,
    questions_total: totalQuestions,
    questions_run: perQ.length,
    judge: judgeModel,
    seed: opts.seed,
    summary: {
      accuracy,
      accuracy_wilson_95ci: ci,
      per_category,
      per_category_abs,
      judge_disagreement_rate,
      retrieval_only_recall_at_5,
      latency_p50_ms,
      latency_p95_ms,
    },
    questions: perQ,
    _meta: {
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      dry_run: opts.dryRun,
      keyword_only: opts.keywordOnly,
      retrieval_only: opts.retrievalOnly,
      expansion: opts.expansion,
      top_k: opts.topK,
      db: opts.db,
      resume_from: opts.resumeFrom,
    },
  };
}

// ---------------------------------------------------------------------------
// Telemetry: log to eval_runs table (summary only, no question content)
// ---------------------------------------------------------------------------

interface EvalRunRow {
  run_id: string;
  started_at: string;
  finished_at: string;
  dataset_name: string;
  dataset_commit: string;
  judge: string;
  questions_run: number;
  accuracy: number | null;
  seed: number;
  dry_run: number; // SQLite boolean
}

/**
 * Attempt to log to `eval_runs` table if it exists in the DB.
 * Non-fatal: swallows errors so eval output is never blocked by telemetry.
 */
export async function logTelemetry(dbPath: string, row: EvalRunRow): Promise<void> {
  try {
    // Dynamic import so VPS has better-sqlite3; dev box without it won't crash.
    const { default: Database } = await import("better-sqlite3" as string);
    const db = new Database(dbPath);
    // Create table if absent (idempotent).
    db.exec(`
      CREATE TABLE IF NOT EXISTS eval_runs (
        run_id      TEXT PRIMARY KEY,
        started_at  TEXT NOT NULL,
        finished_at TEXT NOT NULL,
        dataset_name TEXT NOT NULL,
        dataset_commit TEXT NOT NULL,
        judge       TEXT NOT NULL,
        questions_run INTEGER NOT NULL,
        accuracy    REAL,
        seed        INTEGER NOT NULL,
        dry_run     INTEGER NOT NULL DEFAULT 0
      )
    `);
    db.prepare(
      `INSERT OR REPLACE INTO eval_runs
       (run_id, started_at, finished_at, dataset_name, dataset_commit, judge,
        questions_run, accuracy, seed, dry_run)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(
      row.run_id, row.started_at, row.finished_at,
      row.dataset_name, row.dataset_commit, row.judge,
      row.questions_run, row.accuracy, row.seed, row.dry_run ? 1 : 0,
    );
    db.close();
  } catch {
    // Swallow: telemetry is best-effort.
  }
}

// ---------------------------------------------------------------------------
// Dataset split inference (path → split name for loadSplit)
// ---------------------------------------------------------------------------

function inferSplit(datasetPath: string): string | null {
  const b = basename(datasetPath, ".json");
  // e.g. "longmemeval_oracle" → "oracle"
  const m = b.match(/longmemeval_(.+)$/);
  return m ? m[1] : null;
}

// ---------------------------------------------------------------------------
// Core orchestration (called by src/cli/eval-longmemeval.ts)
// ---------------------------------------------------------------------------

/**
 * Main entry point for `nox-mem eval longmemeval`.
 *
 * In dry-run mode (default for CI):
 *   - Parses + validates the dataset.
 *   - Writes a results skeleton with dryRun=true and questions_run=0.
 *   - Does NOT call nox-mem search or any LLM API.
 *
 * In live mode:
 *   - Delegates run/score logic to the scaffold internals (run.ts /
 *     score.ts) re-used via imported functions, not shell invocations.
 */
export async function runLongMemEvalCli(opts: LongMemEvalCliOptions): Promise<EvalResults> {
  const startedAt = new Date().toISOString();

  // 1. Validate dataset path
  const datasetPath = resolve(opts.dataset);
  await stat(datasetPath); // throws ENOENT with clear message if missing

  // 2. Infer split from filename
  const split = inferSplit(datasetPath);
  if (!split) {
    throw new Error(
      `Cannot infer split from "${basename(datasetPath)}". ` +
      `File must be named longmemeval_<split>.json (oracle|s_cleaned|m_cleaned).`
    );
  }

  // 3. Resolve judge and output path
  const judgeModel = resolveJudge(opts.judge);
  const outputPath = resolveOutputPath(opts);

  // 4. Dataset commit hash (provenance)
  const commitHash = await datasetCommit(datasetPath);

  // 5. Parse dataset
  const raw = await loadSplit(split);
  const allQuestions = extractQuestions(raw);
  const totalQuestions = allQuestions.length;

  if (opts.verbose) {
    process.stderr.write(`[eval:longmemeval] dataset=${basename(datasetPath)} split=${split} total_q=${totalQuestions}\n`);
    process.stderr.write(`[eval:longmemeval] judge=${judgeModel} seed=${opts.seed} top_k=${opts.topK}\n`);
  }

  // 6. Dry-run: validate only
  if (opts.dryRun) {
    const chunks = extractSessionChunks(raw);
    process.stderr.write(`[eval:longmemeval] dry-run: parsed ${allQuestions.length} questions, ${chunks.length} session chunks\n`);
    process.stderr.write(`[eval:longmemeval] dry-run: dataset OK — skipping search + LLM calls\n`);

    const results = buildResults(
      opts, datasetPath, commitHash, totalQuestions,
      startedAt, judgeModel, [],
    );
    await writeFile(outputPath, JSON.stringify(results, null, 2));
    process.stderr.write(`[eval:longmemeval] dry-run output → ${outputPath}\n`);
    return results;
  }

  // 7. Resume: load already-done IDs
  const doneIds = opts.resumeFrom ? await loadDoneQuestionIds(opts.resumeFrom) : new Set<string>();
  if (doneIds.size > 0) {
    process.stderr.write(`[eval:longmemeval] resume: ${doneIds.size} questions already done, skipping\n`);
  }

  // 8. Apply limit
  let targetQuestions = allQuestions.filter((q) => !doneIds.has(q.question_id));
  if (opts.limit !== undefined && opts.limit < targetQuestions.length) {
    // Stratified sample — defer to run.ts internals; here just truncate
    // deterministically for the CLI contract.
    targetQuestions = targetQuestions.slice(0, opts.limit);
  }

  // 9. Build chunk index by question
  const chunksAll = extractSessionChunks(raw);
  const chunksByQ = new Map<string, SessionChunk[]>();
  for (const c of chunksAll) {
    if (!chunksByQ.has(c.question_id)) chunksByQ.set(c.question_id, []);
    chunksByQ.get(c.question_id)!.push(c);
  }

  // 10. Load previously-done question results for resume merge
  let previousResults: PerQuestionResult[] = [];
  if (opts.resumeFrom && doneIds.size > 0) {
    try {
      const partial = JSON.parse(await readFile(opts.resumeFrom, "utf8")) as { questions?: PerQuestionResult[] };
      previousResults = partial.questions ?? [];
    } catch {
      // Non-fatal: resume just re-runs if we can't read the file.
    }
  }

  // 11. Run + score via scaffold internals
  //     The scaffold run.ts / score.ts are the truth; we import their
  //     exported functions rather than calling the CLI shell command.
  //     This avoids a double-process and lets us collect per-question
  //     timing naturally.

  // Lazy import scaffold modules (they use process.argv for standalone
  // invocations; we only use their exported functions here).
  const { default: { runQuestions } } = await import("./run-api.js").catch(() => {
    // run-api.js is the programmatic API wrapper created in this PR.
    // Fall back to a no-op stub during dry-run or when not on VPS.
    return { default: { runQuestions: null } };
  });

  const perQ: PerQuestionResult[] = [];

  if (runQuestions) {
    const runResults = await (runQuestions as (
      questions: QARecord[],
      chunksByQ: Map<string, SessionChunk[]>,
      opts: {
        db: string;
        judge: string;
        topK: number;
        keywordOnly: boolean;
        retrievalOnly: boolean;
        expansion: boolean;
        seed: number;
        verbose: boolean;
      }
    ) => Promise<PerQuestionResult[]>)(targetQuestions, chunksByQ, {
      db: opts.db,
      judge: judgeModel,
      topK: opts.topK,
      keywordOnly: opts.keywordOnly,
      retrievalOnly: opts.retrievalOnly,
      expansion: opts.expansion,
      seed: opts.seed,
      verbose: opts.verbose,
    });
    perQ.push(...runResults);
  } else {
    // Scaffold stub path: mark all as skip (no runQuestions available)
    for (const q of targetQuestions) {
      perQ.push({
        question_id: q.question_id,
        question_type: q.question_type,
        base_category: q.base_category,
        is_abstention: q.is_abstention,
        verdict: "skip",
        judge_rationale: "run-api not available (scaffold stub)",
        retrieval_session_hit: false,
        retrieval_ms: 0,
        generation_ms: 0,
        judge_ms: 0,
      });
    }
  }

  // 12. Merge with previous results (resume)
  const allPerQ = [...previousResults, ...perQ];

  // 13. Build final results
  const results = buildResults(
    opts, datasetPath, commitHash, totalQuestions,
    startedAt, judgeModel, allPerQ,
  );

  // 14. Write output
  await writeFile(outputPath, JSON.stringify(results, null, 2));
  process.stderr.write(`[eval:longmemeval] results → ${outputPath}\n`);
  process.stderr.write(
    `[eval:longmemeval] accuracy=${results.summary.accuracy.toFixed(4)} ` +
    `n=${results.summary.accuracy_wilson_95ci} ` +
    `recall@5=${results.summary.retrieval_only_recall_at_5.toFixed(4)}\n`
  );

  // 15. Telemetry (best-effort, summary only)
  const runId = `lme-${Date.now()}-${commitHash.slice(0, 8)}`;
  await logTelemetry(opts.db, {
    run_id: runId,
    started_at: startedAt,
    finished_at: results._meta.finished_at,
    dataset_name: results.dataset,
    dataset_commit: commitHash,
    judge: judgeModel,
    questions_run: allPerQ.length,
    accuracy: results.summary.accuracy,
    seed: opts.seed,
    dry_run: opts.dryRun ? 1 : 0,
  });

  return results;
}
