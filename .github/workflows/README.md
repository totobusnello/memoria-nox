# GitHub Actions Workflows — memoria-nox

All workflows run on **ubuntu-latest**, use **Node 22 + tsx@4**, and operate in
dry-run / mock / synthetic mode — **no real API calls, no real datasets, no prod DB**.

---

## Workflow inventory

| File | Name | Triggers | Est. time |
|------|------|----------|-----------|
| `eval-harnesses.yml` | Eval Harnesses (Dry-Run) | PR touching `eval/**`, push to main | ~3–5 min |
| `privacy-filter.yml` | A1 Privacy Filter Tests | PR touching `staged-privacy/**`, push to main | ~1 min |
| `zero-vendor.yml` | A4 Zero-Vendor Validation | All PRs, push to main, weekly Sunday | ~2–3 min |
| `lint-and-typecheck.yml` | Lint + Typecheck | All PRs, push to main | ~3–5 min |

---

## eval-harnesses.yml

Runs three eval harness dry-runs:

**Q1 — LoCoMo** (`eval/locomo/run.ts`):
- Dry-run is the **default** — absence of `--full` flag sets `dryRun=true` inside `run.ts`.
- Validates output shape against `eval/locomo/dry-run-sample.json` (committed fixture).
- If `eval.db` is absent (corpus not downloaded), `run.ts` exits early with a JSON stub.
  This is expected in CI and results in a `::notice::` annotation, not a failure.

**Q2 — LongMemEval** (`eval/longmemeval/run.ts`):
- Same pattern as Q1. `--no-llm` flag additionally skips generator invocation.
- Validates output shape against `eval/longmemeval/dry-run-sample.json`.

**Q3 — Latency** (`eval/latency/src/dry-run.ts`):
- Uses the dedicated `dry-run.ts` script (synthetic samples, no binary).
- Output is piped through the aggregator; validates `p50_ms/p95_ms/p99_ms` shape.

### Running locally

```bash
# Q1
cd eval/locomo && npm install && npx tsc && npx tsx run.ts --n 10

# Q2
cd eval/longmemeval && npm install && npx tsc && npx tsx run.ts --n 10 --no-llm

# Q3
cd eval/latency && npm install && npx tsc && node dist/dry-run.js
```

### BLOCKED scenarios

If `eval/locomo`, `eval/longmemeval`, or `eval/latency` are not merged yet, the jobs
emit a `::warning::` annotation and exit 0 (skip gracefully). Look for:
```
::warning::eval/locomo not merged yet — skipping Q1 dry-run
```

---

## privacy-filter.yml

Runs the 68 node:test unit tests in `staged-privacy/edits/privacy/__tests__/filter.test.ts`
via the `npm test` script in `staged-privacy/package.json`:

```
npm run build && node --test dist/privacy/__tests__/filter.test.js
```

Also runs a secret-pattern scan on `staged-privacy/edits/` to ensure no real AWS/OpenAI
keys are present in test fixtures (allowlist includes known synthetic patterns like
`AKIAIOSFODNN7EXAMPLE` and `sk-ant-test-`).

### Running locally

```bash
cd staged-privacy && npm install && npm test
```

---

## zero-vendor.yml

Ports the logic from `validation/zero-vendor/ci-action.yml` (PR #20 original) to the
canonical `.github/workflows/` location. Key differences:

- Uses `tsx@4` instead of `ts-node --esm` (avoids ESM loader quirks in Node 22)
- All 8 checks run in CI — checks 2, 3, 6, 7 use mock infrastructure from A4-completion
- Weekly cron (Sunday 06:00 UTC) catches dependency drift between PRs
- Posts a summary comment to the PR via `gh pr comment`

**Check inventory** (from `runner.ts`):
1. `license-check` — all deps must be in `allowlist.json`
2. `runtime-deps-check` — no unexpected runtime modules (mock in CI)
3. `offline-mode-check` — no outbound sockets (socket-guard.cjs preload)
4. `sqlite-portable-check` — `better-sqlite3` linked against bundled sqlite3
5. `no-daemon-check` — no background processes spawned
6. `embedding-cache-replay` — embeddings served from cache, not API
7. `provider-substitution-dry-run` — provider swap does not break search path
8. `archive-portability` — export/import round-trip produces identical chunk count

### Running locally

```bash
npm install -g tsx@4
sudo apt-get install sqlite3
npx tsx validation/zero-vendor/runner.ts
```

### Debugging CI failures

1. Download the `zero-vendor-report-<sha>` artifact from the Actions run.
2. Check `summary.fail` to identify which checks failed.
3. Re-run locally with `NOX_MEM_DIR=$(pwd)` set.
4. For checks 2/3/6 (mock-dependent): ensure `validation/zero-vendor/fixtures/` is present.

---

## lint-and-typecheck.yml

Runs `npx tsc --noEmit` for each package that has a `tsconfig.json`:
- `staged-privacy/`
- `eval/locomo/`
- `eval/longmemeval/`
- `eval/latency/`
- `validation/zero-vendor/`

Steps use `continue-on-error: true` so scaffold packages with type errors don't block
the gate. A consolidated summary table is posted to the Actions step summary.

**This job is advisory, not blocking** for packages that are still scaffolds.
Add `continue-on-error: false` per-package once the package is declared stable.

---

## Adding a new workflow

1. Copy `privacy-filter.yml` as a template.
2. Set `on.pull_request.paths` to match the new feature directory.
3. Add a presence check step (`hashFiles(...)` or `[ -d "..." ]`) so the job
   skips gracefully when the feature branch isn't merged yet.
4. Keep `timeout-minutes` ≤ 10 for ubuntu-latest (prevents runaway billing).
5. Use `actions/upload-artifact@v4` for any JSON reports (retention 7–30d).

---

## Time budget (ubuntu-latest, cold)

| Workflow | Step breakdown | Total |
|----------|---------------|-------|
| eval-harnesses | npm install×3 (~60s) + tsc×3 (~30s) + runs×3 (~30s) | ~3 min |
| privacy-filter | npm install (~20s) + build (~10s) + 68 tests (~20s) | ~1 min |
| zero-vendor | npm install (~20s) + sqlite3 apt (~10s) + 8 checks (~60s) | ~2 min |
| lint-and-typecheck | npm install×5 (~90s) + tsc×5 (~90s) | ~4 min |
