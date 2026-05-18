/**
 * index-eval-patch.ts — patch snippet for src/index.ts
 *
 * Add these two blocks to src/index.ts to register
 * `nox-mem eval longmemeval` as a first-class CLI command.
 *
 * BLOCK 1 — add import at the top of src/index.ts (with the other imports):
 *
 *   import { registerEvalLongMemEval } from "./cli/eval-longmemeval.js";
 *
 * BLOCK 2 — add before `program.parse(process.argv)` (or
 * `program.parseAsync(process.argv)`):
 *
 *   // ─── Eval commands ──────────────────────────────────────────────────────
 *   registerEvalLongMemEval(program);
 *
 * That's it. The `eval longmemeval <dataset>` subcommand will then be
 * available in `nox-mem --help` under the eval group.
 *
 * ---------------------------------------------------------------------------
 * Full diff context (for automated patching on VPS deploy):
 * ---------------------------------------------------------------------------
 *
 * @@ src/index.ts @@
 *
 * + import { registerEvalLongMemEval } from "./cli/eval-longmemeval.js";
 *
 *   // ... existing commands ...
 *
 * + // ─── Eval commands ──────────────────────────────────────────────────────
 * + registerEvalLongMemEval(program);
 *
 *   program.parse(process.argv);  // or parseAsync(process.argv)
 *
 * ---------------------------------------------------------------------------
 * Files to copy to VPS (relative to repo root):
 * ---------------------------------------------------------------------------
 *
 *   staged-Q2.1/src/cli/eval-longmemeval.ts   → src/cli/eval-longmemeval.ts
 *   eval/longmemeval/cli-adapter.ts            → eval/longmemeval/cli-adapter.ts
 *   eval/longmemeval/run.ts                    → eval/longmemeval/run.ts   (unchanged from PR #12)
 *   eval/longmemeval/parser.ts                 → eval/longmemeval/parser.ts (unchanged from PR #12)
 *   eval/longmemeval/score.ts                  → eval/longmemeval/score.ts (unchanged from PR #12)
 *
 * Then apply the BLOCK 1 + BLOCK 2 patch to src/index.ts and run `npm run build`.
 *
 * ---------------------------------------------------------------------------
 * Run-api bridge (run-api.ts):
 * ---------------------------------------------------------------------------
 *
 * cli-adapter.ts does a dynamic import of "../../eval/longmemeval/run-api.js".
 * run-api.ts exports `runQuestions()` — the programmatic API version of the
 * per-question run loop from run.ts (so we don't shell out or re-parse argv).
 *
 * run-api.ts is declared as a separate file (staged-Q2.1/eval/longmemeval/run-api.ts)
 * to be placed at eval/longmemeval/run-api.ts on VPS.
 *
 * If run-api.js is absent (not yet deployed), cli-adapter falls back to the
 * scaffold stub path (marks all questions as "skip" with a note). This makes
 * the dry-run always safe even before VPS deployment.
 */

// This file is intentionally NOT a module with executable code.
// It documents the patch required in src/index.ts.
export {};
