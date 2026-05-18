# deploy-validator

Local dry-run validation framework for `docs/DEPLOY-WAVE-B.md` — catches syntax errors,
broken rsync paths, migration order issues, and wrong ports before touching production.

## Quick start

```bash
cd scripts/deploy-validator
npm install
npm test          # run all unit tests
npm run validate-deploy   # run full validator against DEPLOY-WAVE-B.md
```

## What it catches

| Category | What is validated |
|---|---|
| `bash-syntax` | `bash -n` on every bash block — unmatched quotes, brackets, bad heredocs |
| `rsync` | Rewrites remote paths to local tmp dirs, runs `--dry-run`, checks path typos |
| `sqlite-migration` | Applies v11 → v19 → v20 chain against in-memory SQLite, verifies `PRAGMA user_version` |
| `path-validator` | Double slashes, unknown `$VAR` references, leaked worktree paths |
| `url-validator` | URL syntax, wrong port (catches `:18800` → should be `:18802` per CLAUDE.md regra #4) |
| `smoke` | curl commands against local nox-mem API (if running); marked `vps-only` if no local API |

## What it does NOT catch

- SSH execution correctness — remote commands are categorized but not executed
- VPS filesystem state (missing source files, disk space, ACLs)
- TypeScript build errors (run `npm run build` on VPS after deploy)
- Runtime behavior of new features
- Destructive commands (`rm -rf`, `dd`) — marked `destructive, manual review only`

## CLI flags

```
npm run validate-deploy [options]

Options:
  --guide <path>       Guide file (default: docs/DEPLOY-WAVE-B.md)
  --category <list>    Comma-separated categories to run: rsync,sqlite3,curl,other
  --quick              Skip slow validators (rsync dry-run, smoke tests)
  --no-smoke           Skip smoke test harness
  --json               Output raw JSON to stdout (CI-friendly)
  --output <dir>       Report output dir (default: validation/)
```

## Output

Running `npm run validate-deploy` writes two files to `validation/`:

- `deploy-report-YYYY-MM-DD.md` — markdown table with per-command results
- `deploy-report-YYYY-MM-DD.json` — machine-readable full report

Exit code: `0` = all checks passed, `1` = at least one failure.

## Status icons

| Icon | Meaning |
|---|---|
| `ok` | Validation passed |
| `FAIL` | Validation failed — must fix before deploying |
| `WARN` | Non-fatal issue (e.g., worktree path in command) |
| `vps-only` | Cannot validate locally — verify manually on VPS |
| `skip` | Intentionally skipped |

## Architecture

```
src/
  parser.ts            T1 — Markdown code block extractor
  categorize.ts        T2 — Command type detector
  validators/
    bash-syntax.ts     T3a — bash -n syntax check
    rsync.ts           T3b — rsync --dry-run simulation
    sqlite-migration.ts T3c — in-memory SQLite migration chain
    path-validator.ts  T3d — path/arg/env-var checker
    url-validator.ts   T3e — URL syntax + port checker
  smoke-runner.ts      T4 — live curl against local API
  reporter.ts          T5 — markdown + JSON report formatter
  cli.ts               T6 — CLI entry point + orchestrator
fixtures/
  v11.sql              Migration fixture (copy of staged-migrations/v11.sql)
  v19.sql              Migration fixture (copy of staged-migrations/v19.sql)
  v20-viewer-telemetry.sql  Migration fixture (from staged-P5/edits/migrations/)
```

## Extending — adding a validator for a new command type

1. Add a new `CommandType` to `src/categorize.ts` and add detection logic in `detectLine()`.
2. Create `src/validators/your-type.ts` with the validator function signature:
   ```typescript
   export function validateYourType(cmd: CategorizedCommand): YourTypeResult
   ```
3. Add `YourTypeResult` to the `AnyResult` union in `src/reporter.ts`.
4. Add a `case "your-type":` handler in `resultToEntries()` in `src/reporter.ts`.
5. Wire up in `src/cli.ts` under the appropriate `opts.categories` check.
6. Add tests in `src/validators/your-type.test.ts`.

### Example: adding a `chmod` validator

To verify that `chmod` commands use correct modes (0600 for secrets, 0700 for dirs):

```typescript
// src/validators/chmod-validator.ts
import type { CategorizedCommand } from "../categorize.ts";

export interface ChmodResult {
  type: "chmod-validator";
  passed: boolean;
  issues: string[];
  durationMs: number;
}

export function validateChmod(cmd: CategorizedCommand): ChmodResult {
  const issues: string[] = [];
  for (const c of cmd.commands.filter((c) => c.type === "perm-op")) {
    const line = c.line;
    // Warn if snapshot files get world-readable permissions
    if (/chmod\s+0?644/.test(line) && line.includes("nox-mem.db")) {
      issues.push(`${line}: DB file should be 0600, not 0644 (SEC HIGH)`);
    }
  }
  return { type: "chmod-validator", passed: issues.length === 0, issues, durationMs: 0 };
}
```

## CI integration

The workflow at `.github/workflows/deploy-validator.yml` runs automatically on PRs that
modify `docs/DEPLOY-WAVE-B.md`, `staged-*/`, or `staged-migrations/`. It:

1. Installs `rsync`, `sqlite3`, `bash` (system) and `better-sqlite3` (npm).
2. Runs `npm test` — all unit tests must pass.
3. Runs `npm run validate-deploy -- --no-smoke --json` and fails the PR if any check fails.
4. Posts a summary comment on the PR with pass/fail counts and failure details.
5. Uploads `validation/deploy-report-*.{md,json}` as a CI artifact.

To test the CI workflow locally:

```bash
act pull_request --job validate-deploy  # requires https://github.com/nektos/act
```

## Migration fixture management

The `fixtures/` directory contains copies of migration SQL files:

```
fixtures/v11.sql                    ← from staged-migrations/v11.sql
fixtures/v19.sql                    ← from staged-migrations/v19.sql
fixtures/v20-viewer-telemetry.sql   ← from staged-P5/edits/migrations/
```

If migration files change, regenerate fixtures:

```bash
cp staged-migrations/v11.sql scripts/deploy-validator/fixtures/
cp staged-migrations/v19.sql scripts/deploy-validator/fixtures/
# For v20, find in any staged-P5 worktree:
find . -path '*/staged-P5/edits/migrations/v20*' -exec cp {} scripts/deploy-validator/fixtures/ \;
```
