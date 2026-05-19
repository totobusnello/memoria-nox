# Contributing to memoria-nox

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

memoria-nox is research-grade infrastructure with production discipline. Every commit touches a system that runs against a live corpus of 69k+ chunks, serves multiple agents simultaneously, and has an incident log that documents exactly what happens when the discipline slips. Contributions are welcome — and expected to meet that bar.

This guide covers everything from filing a bug report to shipping a ranking change that earns its place in production. Read it once before opening a PR. The rules here are not bureaucracy; almost every one exists because something broke.

---

## Code of Conduct

This project follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). The short version: treat contributors the way you want the retrieval system to treat your data — with respect, honesty, and no silent data loss.

---

## How to Contribute

### Bug Reports

A good bug report is reproducible. Before filing, check:

1. Is the issue already in [`docs/INCIDENTS.md`](docs/INCIDENTS.md)? Many operational failure modes are documented there — including root causes and fixes.
2. Does the issue affect the live corpus, or only local test data? The distinction matters for triage priority.

**When opening a bug issue, include:**

- Node version (`node --version`)
- OS and SQLite version (`sqlite3 --version`)
- The exact CLI command or HTTP call that failed
- The full log output — not just the last line. The last line is often misleading (see [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md): "nunca confiar na última linha do CLI").
- The output of `curl http://127.0.0.1:18802/api/health | jq .` if the API is running — this shows vector coverage, schema version, and recent ops audit state.
- A minimal repro: the smallest ingest input + search query that triggers the bug.

**Do not redact error messages.** "Something went wrong" is not debuggable. If the error contains a path or a query that you consider sensitive, replace it with a placeholder — but keep the structure.

---

### Feature Proposals

**Spec before code.** Open an issue tagged `proposal` and describe:

1. What problem it solves (link to the relevant pillar: Q / A / P / Lab)
2. The interface you propose (CLI flag, env var, API endpoint, schema change)
3. What you are explicitly **not** doing (scope limits matter as much as scope)

Wait for acknowledgment before writing code. The [`docs/DECISIONS.md`](docs/DECISIONS.md) log captures architectural choices with explicit "NÃO FAZEMOS" sections — your proposal may conflict with a prior decision, and finding that out before you write 400 lines is better than after.

For ranking/scoring features specifically, see the **Shadow Discipline** section below. There is no expedited path.

---

### Pull Requests

**Branch naming:**

```
<type>/<yyyy-mm-dd>/<short-slug>
```

Examples:
```
feat/2026-05-20/answer-primitive-citations
fix/2026-05-21/kg-relation-fk-join
tune(search)/2026-05-22/rrf-pt-weight
docs/2026-05-18/quickstart
```

The `tune(search):` prefix is reserved for commits that touch `src/lib/search.ts`, `src/lib/salience.ts`, or RRF weights. Never sneak a ranking change into a `fix/` or `refactor/` commit — this is rule #5 in [`CLAUDE.md`](CLAUDE.md) and it caused incident v3.4.

**Commit conventions:**

```
<type>(<scope>): <subject>

<body — optional, explain why not what>
```

Types: `feat`, `fix`, `tune(search)`, `docs`, `test`, `refactor`, `chore`, `spec`.

**PR requirements:**

- [ ] `npm test` passes locally (see [Testing requirements](#testing-requirements))
- [ ] No `any` without a justification comment
- [ ] No new env var without a corresponding entry in [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)
- [ ] Destructive operations (reindex, compact, crystallize) use `withOpAudit()` or `--dry-run` — not raw DB writes. See rule #6 in [`CLAUDE.md`](CLAUDE.md).
- [ ] Ranking/scoring changes include shadow-mode plan (see [Shadow Discipline](#shadow-discipline))
- [ ] PR body includes "closes #N" or "addresses #N" — every PR must be linkable to an issue or spec

---

## Development Setup

### Prerequisites

- Node.js 22+ (`node --version`)
- `sqlite3` CLI (for schema inspection)
- ~2 GB free disk (test corpus + build artifacts)
- A Gemini API key for integration tests that hit real embeddings (optional for unit tests)

### Clone and install

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
npm install
npm run build
```

### Verify the build

```bash
node dist/index.js --version
# nox-mem v<version>
```

### Run the test suite

```bash
npm test
```

All tests must be green before opening a PR. The suite runs without a live API key by default — embedding calls are mocked. To run integration tests against real providers:

```bash
NOX_E2E_GEMINI=1 GEMINI_API_KEY=<your-key> npm test
```

### Environment setup (local)

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
# edit .env — at minimum set GEMINI_API_KEY if running integration tests
```

Load the env before any CLI call:

```bash
set -a; source .env; set +a
nox-mem --help
```

This is mandatory. Without it, vectorize and kg-extract fail silently (the CLI shows progress but reports `Done: 0 embedded, N errors` at the end). See rule #1 in [`CLAUDE.md`](CLAUDE.md).

---

## Architecture Orientation

Start with these three files (in order):

| File | Why read it |
|---|---|
| [`docs/VISION.md`](docs/VISION.md) | The three pillars (Q/A/P) and what we refuse to become |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Current sprint, capacity, gates, and wave structure |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every architectural decision with the "NÃO FAZEMOS" sections |

Then orient yourself in the code:

- **Entry point:** `dist/index.js` (not `cli.js` — common confusion). See `package.json.bin`.
- **Ingest router:** `src/lib/ingest-router.ts` — single dispatch for entity files, markdown, graphify. Never call `ingestFile()` in a loop without going through the router (lesson from incident 2026-04-25).
- **Search:** `src/lib/search.ts` — the three-layer pipeline: FTS5 BM25 → Gemini semantic → RRF fusion. Small enough to read in one sitting.
- **Salience:** `src/lib/salience.ts` — `recency × pain × importance`. Shadow-mode by default.
- **Op audit:** `src/lib/op-audit.ts` — `withOpAudit()` wrapper for destructive ops. `safeRestore()` for recovery.
- **Provider abstraction:** `staged-A3/edits/src/providers/` — embedding and LLM provider factories.

---

## Coding Conventions

Full conventions are in [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md). Critical rules:

**TypeScript:**
- Strict mode. No `any` without an explicit `// eslint-disable-next-line` with a reason.
- ESM only. No `require()` — `ReferenceError` at runtime in `type: "module"` packages. Grep `require(` in `src/**/*.ts` before submitting.
- Static module-level `const FOO = process.env.X` captures the empty env at import time. Use dynamic `await import()` in async `before()` hooks when env is set after module load.
- `execFileSync(cmd, [argsArray])` for any user input. Never `execSync` with template strings — command injection. Input regex blocklist + `realpath` allowlist are the defense in layers.

**Schema:**
- Every schema change is additive and idempotent. Never DROP a column or table in a migration.
- Bump `SCHEMA_VERSION` in `db.ts` only when the schema actually changes (not just seed data).
- `busy_timeout=5000ms` is mandatory in `db.ts`. Removing it causes `SQLITE_BUSY` under concurrent watcher + API + CLI writes.

**Append-only philosophy:**
- The `ops_audit` table is append-only. `DELETE` and terminal-row `UPDATE` are blocked by DB triggers (CWE-693 guard). Do not fight this.
- Valid `ops_audit` status enum: `started`, `success`, `failed`, `crashed`. The values `completed` and `rolled_back` are not valid — old docs may say otherwise.

**Ingest router:**
- Always route through `src/lib/ingest-router.ts:routeIngest()`. The generic `ingestFile()` does not handle entity files correctly — it zeros `section` and `retention_days`.

**The `sed` rule:**
- `sed -i` on `.db` files is permanently banned. It corrupts SQLite page boundaries. The recovery cost is hours. Use the appropriate `src/` module or `better-sqlite3` directly. See rule #7 in [`CLAUDE.md`](CLAUDE.md).

---

## Testing Requirements

`npm test` must be green before a PR is merged. Beyond the basic gate:

**Unit tests** live alongside source files in `__tests__/` directories. Each new exported function should have at least one test covering the happy path and one covering the failure mode.

**Integration tests** that touch crypto or checksum code require special attention. The A2 archive module (AES-256-GCM + scrypt) had a critical AAD stability bug — the Additional Authenticated Data field must remain byte-for-byte stable across export/import roundtrips or decryption silently fails. If you touch encryption, add a roundtrip test that:
1. Exports with a passphrase
2. Imports from the exported file
3. Verifies `nDCG@10 ± 0.001` against the original (or, for unit scope, verifies the full chunk count + text match)

**Ranking eval tests** require the golden set. Run:

```bash
npm run eval:golden
# Requires NOX_DB_PATH pointing to a test corpus
```

The golden set is in `eval/golden/`. A PR that regresses `nDCG@10` by more than `0.005` will not merge without a discussion. Show the diff.

---

## Review Process

PRs receive review from three perspectives:

1. **code-reviewer** — logic, structure, TypeScript conventions
2. **security-reviewer** — injection vectors, auth bypass, `execSync` vs `execFileSync`, world-readable file permissions, snapshot ACL (must be `0600`)
3. **tdd-guide** — test coverage, adversarial cases, happy-path-only gaps

For critical modules (`op-audit.ts`, `archive.ts`, providers), all three perspectives apply in the same review session. This is not optional overhead — the 2026-04-25 incident that wiped `section` and `retention_days` from 183 entities was caught only when an audit session ran all three lenses. The code had been in production for days.

---

## Shadow Discipline

**Any PR that touches search ranking — `src/lib/search.ts`, `src/lib/salience.ts`, RRF weights, section_boost, or any new scoring term — must follow the shadow protocol:**

1. Implement the feature gated behind an env var with a default of `disabled` or `shadow`.
2. Run in shadow mode (`/api/health.salience` or a new `/api/health.<feature>` endpoint) for at least 7 days on the production corpus.
3. Compare the A/B delta against the golden eval set (`eval/golden/`). The bar is `+1.0pp nDCG@10` over the current baseline.
4. Include the eval delta JSON in the PR body.
5. Only after the 7-day window + positive eval: flip the default to `active`.

This is **rule #5** in [`CLAUDE.md`](CLAUDE.md). It is not negotiable. The incident that created this rule shipped a multiplicative boost (additive stacking is veneno — "poison") hidden inside a `fix:` commit. The regression was silent for days because the last-line CLI output looked fine.

If you want to propose an exception, open an issue with the reasoning. The bar for exceptions is very high.

---

## Release Cadence

memoria-nox ships in **Waves** — named batches of related work that graduate from `staged-*` directories into the main codebase. The current wave structure:

| Wave | Focus |
|---|---|
| Wave A | Core data safety — op-audit, ingest-router, dry-run, retention invariants |
| Wave B | Provider abstraction, answer primitive, archive (A2/A3), L4 regex extraction, P5 viewer |
| Wave C | Benchmark harnesses Q1+Q2+Q3, zero-vendor CI (A4) |
| Wave D | Lab features — L2 conflict detection, L3 confidence/provenance |
| Wave E | Hooks integration (P2), benchmark results, documentation |

There is no fixed release schedule. Waves close when the DoDs in [`docs/ROADMAP.md`](docs/ROADMAP.md) are met and the eval gate passes. "Ship and see" is not in the vocabulary.

---

## Languages

- **Portuguese (PT-BR, "você" register):** used in narrative docs (CLAUDE.md, DECISIONS.md, HANDOFF.md, ROADMAP.md), commit messages by the maintainer, and inline comments where context is operational and Brazilian-Portuguese.
- **English:** used in the public API surface (CLI help text, HTTP endpoint names, error messages), code identifiers, this file, and any doc that faces external contributors.
- **Never mix** "tu/te/ti/teu" into PT-BR text. São Paulo register only. This is a hard rule across all files in this repo.

---

## Getting Help

- Open an issue tagged `question` for anything not covered here.
- Read [`docs/INCIDENTS.md`](docs/INCIDENTS.md) before assuming a behavior is a bug — most operational edge cases are documented there.
- The retrieval logic in `src/lib/search.ts` is intentionally small. Read it before proposing changes to search behavior.

---

*For the full operational ruleset (SSH env loading, model selection, port allocation, destructive-op guardrails), read [`CLAUDE.md`](CLAUDE.md). For architectural decisions and things we explicitly refuse to build, read [`docs/DECISIONS.md`](docs/DECISIONS.md).*
