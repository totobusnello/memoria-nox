# GitHub Actions Workflows

Five workflows shipped with this repo. All run on GitHub-hosted `ubuntu-latest`.

## Workflow Summary

| File | Trigger | Purpose |
|------|---------|---------|
| `lint-docs.yml` | push/PR | Markdown lint (markdownlint-cli2) + internal link check (lychee) |
| `validate-syntax.yml` | push/PR | YAML, JSON, Python, Bash syntax validation |
| `security.yml` | push/PR + weekly Mon | Secret scan (gitleaks) + npm audit + Trivy FS |
| `eval-smoke.yml` | PR on eval/** + manual | Eval harness smoke (no API calls) |
| `release.yml` | manual (workflow_dispatch) | Full release: preflight + paper PDF + GitHub Release |

## Details

### lint-docs.yml

- `markdownlint-cli2` uses `.markdownlint.yaml` at repo root (relaxed: line-length off, inline HTML allowed).
- `lychee` checks **internal links only** (`--exclude-external`) — catches broken cross-references between docs.
- Both jobs must pass for PR green.

### validate-syntax.yml

Four independent jobs:
- **YAML** — `yamllint -d relaxed` on all `.yml`/`.yaml` (excludes `node_modules`, `.git`).
- **JSON** — `python3 -m json.tool` on all `.json`. Fails on first invalid file.
- **Python** — `python3 -m py_compile` syntax check on all `.py` files. Does NOT run code.
- **Bash** — `shellcheck --severity=error` on all `.sh`. Warnings pass; errors fail.

### security.yml

- **gitleaks** — scans full git history (`fetch-depth: 0`). Blocks on leaked secrets.
- **npm-audit** — scans any `package.json` with an adjacent lockfile. `continue-on-error: true` (advisory only).
- **Trivy** — FS scan HIGH+CRITICAL CVEs. `continue-on-error: true` (advisory; no lockfiles tracked).

Weekly schedule: Monday 06:00 UTC.

### eval-smoke.yml

Only triggers when `eval/q4-comparison/**` changes or via manual dispatch. Runs:
1. `smoke_test.py --no-network` — validates adapter interfaces without API calls.
2. `runner.py --dry-run` — validates argparse + adapter dispatch wiring.

Full eval (expensive, requires live DB + Gemini key) is NOT run in CI.

### release.yml

Manual only (`workflow_dispatch`). Input: `version` string (e.g. `1.0.0-rc1`).

Steps:
1. Preflight: YAML + JSON + shellcheck.
2. Build `paper/*.pdf` via `scripts/build-paper.sh --pdf-only` (LaTeX required; skips gracefully if missing).
3. Create GitHub Release with tag `v<version>`, body from `docs/releases/v<version>.md`, PDF attached.
4. Pre-release flag auto-set if version contains `rc`, `beta`, or `alpha`.

## GitHub Actions Free Tier

Public repos: **2,000 min/month** free.
Estimated usage: ~3–5 min/run × ~20 PRs/month = ~100 min — well within budget.

## Extending Workflows

- Add a new job to an existing workflow or create a new `.yml` file in this directory.
- Markdownlint rules: edit `.markdownlint.yaml` at repo root.
- Lychee exclusions: add `--exclude 'pattern'` to the lychee args in `lint-docs.yml`.
- To run a workflow manually: GitHub UI → Actions → select workflow → "Run workflow".
