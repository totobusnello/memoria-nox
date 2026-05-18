/**
 * eval-longmemeval.ts — first-class CLI command: `nox-mem eval longmemeval`
 *
 * Registered in src/index.ts (or wherever the Commander program lives) as:
 *
 *   program
 *     .command("eval longmemeval <dataset>")
 *     ...
 *     .action(...)
 *
 * See staged-Q2.1/src/index-eval-patch.ts for the exact registration diff.
 *
 * All heavy logic lives in eval/longmemeval/cli-adapter.ts and the scaffold
 * (parser.ts / run.ts / score.ts). This file is deliberately thin: flag
 * declaration, env resolution, help text, error formatting.
 *
 * DEPLOYMENT: copy this file to src/cli/eval-longmemeval.ts on the VPS.
 * The import path assumes this is placed at dist/cli/eval-longmemeval.js
 * after tsc compilation, importing from ../../eval/longmemeval/cli-adapter.js.
 *
 * STAGED (Q2.1): this file is NOT yet wired into src/index.ts.
 * See staged-Q2.1/src/index-eval-patch.ts for the registration snippet.
 */

import { Command } from "commander";
import { resolve, relative } from "node:path";

import {
  runLongMemEvalCli,
  resolveJudge,
  resolveOutputPath,
  DEFAULT_OPTS,
  type JudgeModel,
  type LongMemEvalCliOptions,
} from "../../eval/longmemeval/cli-adapter.js";

// ---------------------------------------------------------------------------
// Exported function called from src/index.ts program registration
// ---------------------------------------------------------------------------

/**
 * Register the `eval longmemeval` command on a Commander `program`.
 *
 * Usage in src/index.ts:
 *   import { registerEvalLongMemEval } from "./cli/eval-longmemeval.js";
 *   registerEvalLongMemEval(program);
 *
 * @param program Commander Command instance (the nox-mem root program).
 */
export function registerEvalLongMemEval(program: Command): void {
  program
    .command("eval longmemeval <dataset>")
    .description(
      "Run the LongMemEval benchmark against memoria-nox.\n" +
      "  <dataset>  Path to LongMemEval JSON file (oracle|s_cleaned|m_cleaned).\n" +
      "             Download first: npx tsx eval/longmemeval/download.ts --split oracle\n\n" +
      "  Mirrors gbrain eval longmemeval UX. Default: --dry-run (no API calls)."
    )
    .option(
      "--judge <model>",
      "LLM judge: gpt-4o | gemini-2.5-pro | gemini-2.5-flash\n" +
      "           (env LONGMEMEVAL_JUDGE overrides; default: gemini-2.5-pro)",
      DEFAULT_OPTS.judge,
    )
    .option("--limit <N>", "Number of questions to run (default: all)", undefined)
    .option("--seed <N>", "Stratified sample seed", String(DEFAULT_OPTS.seed))
    .option(
      "--output <path>",
      "JSON results output path\n           (env LONGMEMEVAL_OUTPUT_DIR sets directory;\n            default: ./longmemeval-results-<ts>.json)",
      undefined,
    )
    .option(
      "--db <path>",
      "Eval DB path — isolated from prod nox-mem.db\n           (default: ./eval-longmemeval.db)",
      DEFAULT_OPTS.db,
    )
    .option("--keyword-only", "FTS5 ablation: disable vector + KG retrieval", false)
    .option("--retrieval-only", "Skip generation — measure recall only", false)
    .option("--expansion", "Multi-query expansion via LLM (off by default)", false)
    .option("--top-k <N>", "Retrieval top-K (default: 5)", String(DEFAULT_OPTS.topK))
    .option(
      "--dry-run",
      "Validate dataset + parse; NO search or LLM calls.\n           Safe default for CI.",
      false,
    )
    .option(
      "--resume-from <path>",
      "Path to partial results.json — skips already-done questions",
      undefined,
    )
    .option("--verbose", "Log per-question detail to stderr", false)
    .action(async (dataset: string, cmdOpts: Record<string, unknown>) => {
      const opts = buildOptions(dataset, cmdOpts);

      // Print effective config before running
      const effectiveJudge = resolveJudge(opts.judge);
      const effectiveOutput = resolveOutputPath(opts);

      process.stderr.write(
        `[nox-mem eval longmemeval]\n` +
        `  dataset      : ${opts.dataset}\n` +
        `  judge        : ${effectiveJudge}` +
        (process.env.LONGMEMEVAL_JUDGE ? ` (from env LONGMEMEVAL_JUDGE)` : "") + "\n" +
        `  seed         : ${opts.seed}\n` +
        `  limit        : ${opts.limit ?? "all"}\n` +
        `  top-k        : ${opts.topK}\n` +
        `  db           : ${opts.db}\n` +
        `  output       : ${effectiveOutput}\n` +
        `  keyword-only : ${opts.keywordOnly}\n` +
        `  retrieval-only: ${opts.retrievalOnly}\n` +
        `  expansion    : ${opts.expansion}\n` +
        `  dry-run      : ${opts.dryRun}\n` +
        (opts.resumeFrom ? `  resume-from  : ${opts.resumeFrom}\n` : "") +
        "\n"
      );

      try {
        const results = await runLongMemEvalCli(opts);

        // Print compact summary to stdout
        const s = results.summary;
        const ciLo = s.accuracy_wilson_95ci[0].toFixed(3);
        const ciHi = s.accuracy_wilson_95ci[1].toFixed(3);
        process.stdout.write(
          `\n--- LongMemEval results ---\n` +
          `  questions_run      : ${results.questions_run} / ${results.questions_total}\n` +
          `  accuracy           : ${(s.accuracy * 100).toFixed(1)}%  [${ciLo}, ${ciHi}] 95% CI\n` +
          `  recall@5 (session) : ${(s.retrieval_only_recall_at_5 * 100).toFixed(1)}%\n` +
          `  p50 latency        : ${s.latency_p50_ms.toFixed(0)} ms\n` +
          `  p95 latency        : ${s.latency_p95_ms.toFixed(0)} ms\n` +
          `  judge              : ${results.judge}\n` +
          `  output             : ${effectiveOutput}\n` +
          "\n  per-category accuracy:\n"
        );
        for (const [cat, acc] of Object.entries(s.per_category)) {
          process.stdout.write(`    ${cat.padEnd(30)}: ${(acc * 100).toFixed(1)}%\n`);
        }
        if (opts.dryRun) {
          process.stdout.write("\n  [DRY-RUN] no LLM calls made — numbers above are placeholders\n");
        }
      } catch (e) {
        process.stderr.write(
          `[nox-mem eval longmemeval] FATAL: ${e instanceof Error ? e.message : String(e)}\n`
        );
        if (opts.verbose && e instanceof Error && e.stack) {
          process.stderr.write(e.stack + "\n");
        }
        process.exit(1);
      }
    });
}

// ---------------------------------------------------------------------------
// Option builder (CLI flags → LongMemEvalCliOptions)
// ---------------------------------------------------------------------------

function buildOptions(dataset: string, raw: Record<string, unknown>): LongMemEvalCliOptions {
  const judge = (raw.judge as JudgeModel | undefined) ?? DEFAULT_OPTS.judge;
  const limit = raw.limit !== undefined ? parseInt(String(raw.limit), 10) : undefined;
  const seed = raw.seed !== undefined ? parseInt(String(raw.seed), 10) : DEFAULT_OPTS.seed;
  const topK = raw.topK !== undefined ? parseInt(String(raw.topK), 10) : DEFAULT_OPTS.topK;
  const db = String(raw.db ?? DEFAULT_OPTS.db);
  const output = raw.output ? String(raw.output) : undefined;
  const resumeFrom = raw.resumeFrom ? String(raw.resumeFrom) : undefined;
  const outputDir = process.env.LONGMEMEVAL_OUTPUT_DIR;

  // Validate limit
  if (limit !== undefined && (isNaN(limit) || limit < 1)) {
    throw new Error(`--limit must be a positive integer, got: ${raw.limit}`);
  }
  // Validate seed
  if (isNaN(seed)) {
    throw new Error(`--seed must be an integer, got: ${raw.seed}`);
  }
  // Validate topK
  if (isNaN(topK) || topK < 1) {
    throw new Error(`--top-k must be a positive integer, got: ${raw.topK}`);
  }
  // Validate judge
  const validJudges: JudgeModel[] = ["gpt-4o", "gemini-2.5-pro", "gemini-2.5-flash"];
  if (!validJudges.includes(judge)) {
    throw new Error(`--judge must be one of: ${validJudges.join(", ")}. Got: ${judge}`);
  }
  // Validate judge key availability (warn, not error)
  const effectiveJudge = resolveJudge(judge);
  if (effectiveJudge === "gpt-4o" && !process.env.OPENAI_API_KEY) {
    process.stderr.write(`[warn] --judge gpt-4o but OPENAI_API_KEY is not set. Will fail at judge step.\n`);
  }
  if (effectiveJudge.startsWith("gemini") && !process.env.GEMINI_API_KEY && !process.env.GOOGLE_API_KEY) {
    process.stderr.write(`[warn] --judge ${effectiveJudge} but GEMINI_API_KEY / GOOGLE_API_KEY is not set. Will fail at judge step.\n`);
  }

  return {
    dataset,
    judge,
    limit,
    seed,
    output,
    db,
    keywordOnly: Boolean(raw.keywordOnly),
    retrievalOnly: Boolean(raw.retrievalOnly),
    expansion: Boolean(raw.expansion),
    topK,
    dryRun: Boolean(raw.dryRun),
    resumeFrom,
    verbose: Boolean(raw.verbose),
    outputDir,
  };
}

// ---------------------------------------------------------------------------
// Standalone entry (for direct `node dist/cli/eval-longmemeval.js` usage)
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const standalone = new Command();
  standalone
    .name("nox-mem eval longmemeval")
    .description("Run the LongMemEval benchmark (standalone)")
    .version("Q2.1");
  registerEvalLongMemEval(standalone);
  await standalone.parseAsync(process.argv);
}

const thisFile = new URL(import.meta.url).pathname;
if (process.argv[1] && resolve(process.argv[1]) === thisFile) {
  main().catch((e) => {
    process.stderr.write(`FATAL: ${e instanceof Error ? e.message : e}\n`);
    process.exit(1);
  });
}
