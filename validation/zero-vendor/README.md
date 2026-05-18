# Zero-Vendor Validation Suite

**Purpose:** Prove that nox-mem has no critical third-party proprietary runtime dependency. Every check is CI-runnable and fails loudly on violation.

**Pillar A tagline:** "Hybrid memory with shadow discipline — yours by design."

**Status (2026-05-18):** All 8 checks runnable in GitHub Actions — no VPS dependency. The full suite completes in ~1 second on a hosted runner.

---

## Why This Exists

Competitor analysis reveals a lock-in pattern:
- **agentmemory** requires `iii-engine` proprietary runtime
- **memanto** requires Moorcheh SaaS connectivity

nox-mem claims zero proprietary runtime deps. This suite makes that claim **auditable and enforceable on every PR**.

---

## Quick Start

```bash
# Full suite (CI mode — JSON report + exit code)
npx tsx validation/zero-vendor/runner.ts

# Individual checks
npx tsx validation/zero-vendor/license-check.ts
npx tsx validation/zero-vendor/runtime-deps-check.ts
npx tsx validation/zero-vendor/offline-mode-check.ts
npx tsx validation/zero-vendor/embedding-cache-replay.ts
npx tsx validation/zero-vendor/provider-substitution-dry-run.ts
bash validation/zero-vendor/sqlite-portable-check.sh
bash validation/zero-vendor/no-daemon-check.sh

# CI (GitHub Actions runs this automatically on every PR)
# See: validation/zero-vendor/ci-action.yml
```

---

## The 8 Checks

| # | Name | File | CI Mode | Live Mode |
|---|------|------|---------|-----------|
| 1 | **license-check** | `license-check.ts` | Runnable | Same code |
| 2 | **runtime-deps-check** | `runtime-deps-check.ts` | Mock CLI | Live nox-mem if `NOX_MEM_DIR` set |
| 3 | **offline-mode-check** | `offline-mode-check.ts` | Mock + socket-guard preload | Live nox-mem |
| 4 | **sqlite-portable-check** | `sqlite-portable-check.sh` | CI fixture DB | Real `nox-mem.db` |
| 5 | **no-daemon-check** | `no-daemon-check.sh` | CI fixture DB | Real `nox-mem.db` |
| 6 | **embedding-cache-replay** | `embedding-cache-replay.ts` | Mock + `NOX_FAIL_IF_EMBED=1` | Live nox-mem |
| 7 | **provider-substitution-dry-run** | `provider-substitution-dry-run.ts` | Mock provider contract | Live nox-mem |
| 8 | **archive-portability** | inline in `runner.ts` | Synthetic SQLite header + tar | `nox-mem export` + tar |

The CI-mode checks 2/3/6/7 use a self-contained mock CLI in `fixtures/mock-nox-mem.cjs` that obeys the SAME env-var contract as the real binary (`NOX_OFFLINE_MODE`, `NOX_LLM_PROVIDER`, `NOX_FAIL_IF_EMBED`...). When the real binary is present (`NOX_MEM_DIR` env set + `dist/index.js` exists), the checks transparently swap it in.

### Check Details

#### 1. license-check
Parses `package.json` + `node_modules/.package-lock.json`, classifies every direct and transitive dependency by SPDX license.

**PASS:** All deps have licenses in the OSS allow-set:
`MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, CC-BY-4.0, Unlicense, 0BSD, BlueOak-1.0.0`

**FAIL:** Any dep with `GPL-*`, `AGPL-*`, `LGPL-*`, `Custom`, `Proprietary`, `Commercial`, `UNLICENSED`, `SEE LICENSE IN ...`, `(Unlicense AND ...)` combinations, or any unknown/empty license field.

**Override:** Add to `allowlist.json` with documented reason. Overrides are logged in the JSON report.

#### 2. runtime-deps-check
Spawns the mock (or live binary) and records every outbound URL attempt via the `NOX_NETWORK_REPORT` env-var contract. Two sub-checks:

- **offlineEgress** — with `NOX_OFFLINE_MODE=1`, zero non-loopback URLs attempted
- **geminiOnlyEgress** — with `NOX_OFFLINE_MODE=0` + an unprimed query, only `generativelanguage.googleapis.com` (and `127.0.0.1`/`localhost`) is reached

**PASS:** Only Gemini API and loopback contacted. No telemetry, no phone-home, no package registries.

**FAIL:** Any egress to an unexpected destination.

#### 3. offline-mode-check
Sets `NOX_OFFLINE_MODE=1`, pre-seeds the fixture DB with primed embeddings, and runs a full ingest + search workload. A `socket-guard.cjs` preload module patches `net.Socket.prototype.connect` and rejects any non-loopback connect — catching even native code that bypasses Node's HTTP stack.

- **ingestOffline** — entity file ingests successfully (FTS-only path)
- **searchOffline** — search returns ≥1 result via cache replay
- **zeroNetworkCalls** — no non-loopback socket attempts across the whole workload

**PASS:** Full workload completes with zero outbound socket connects.

**FAIL:** Any non-loopback connect attempted.

#### 4. sqlite-portable-check
Copies `nox-mem.db` to a fresh temp directory, opens it with the system `sqlite3` CLI (no nox-mem code), runs schema introspection and basic SELECT queries.

**PASS:** `.schema` shows expected tables, `SELECT count(*) FROM chunks` returns > 0.

**FAIL:** `sqlite3` cannot open the file, schema is missing critical tables, or any SQLITE_CORRUPT error.

#### 5. no-daemon-check
Kills all nox-mem processes (`nox-mem-api`, `nox-mem-watcher`, any process holding `nox-mem.db` WAL), then opens the DB with `sqlite3` and confirms queries work.

**PASS:** Queries succeed with zero nox-related processes running.

**FAIL:** Database locked, WAL corruption, or queries fail without daemon.

#### 6. embedding-cache-replay
Pre-seeds the fixture DB with 5 chunks + 4 primed queries. Runs the same search twice; second run sets `NOX_FAIL_IF_EMBED=1`, which makes the mock (and the future live binary) throw if the embedding code path is taken. Also runs an unprimed distinct query to confirm graceful FTS-only fallback.

- **primedCacheHit** — primed query returns results with `cacheHit=true`
- **noEmbedOnReplay** — second run does NOT invoke the embedder
- **distinctQueryFallback** — unprimed query degrades to FTS without crashing

**PASS:** All three sub-checks pass.

**FAIL:** The embedder runs unconditionally → every query becomes network-dependent.

#### 7. provider-substitution-dry-run
Sets `NOX_LLM_PROVIDER=anthropic` with various failure modes. Asserts each produces a structured, actionable error (not a hang, not a stack trace, not a silent fallback).

- **invalidKeyFailsClearly** — `ANTHROPIC_API_KEY=invalid-key-xxxxxx` → structured `PROVIDER_AUTH_FAILED` within 5s
- **missingKeyFailsClearly** — no key set → `PROVIDER_AUTH_MISSING` mentioning the env var
- **unknownProviderFailsClearly** — `NOX_LLM_PROVIDER=totally-fictional-vendor` → `PROVIDER_UNKNOWN` with allowed-list
- **noSilentFallback** — anthropic configured with invalid key + valid `GEMINI_API_KEY` in env → still fails (does NOT silently use Gemini)

**PASS:** All four sub-checks pass.

**FAIL:** Silent hang, swallowed error, raw stack trace, or fallback to a different provider.

**A3 status:** Provider abstraction is spec-only as of 2026-05-18. This check enforces the contract NOW so when A3 lands the CI gate validates it without rework.

#### 8. archive-portability
Runs `nox-mem export --format sqlite`, then `tar -czf archive.tar.gz export/` and `tar -tzf archive.tar.gz`. In CI mode (no live binary), synthesizes a SQLite-shaped fixture file + manifest and confirms tar works against it.

**PASS:** Archive created and inspected with standard Unix tooling.

**FAIL:** Export requires proprietary tooling, tar fails, or archive is unreadable.

---

## CI Integration

GitHub Actions workflow at `validation/zero-vendor/ci-action.yml` runs **all 8 checks** on every PR against `main`. No VPS-gated job, no `requires-vps` label — the moat is auditable from any github-hosted runner.

When the workflow runs on a self-hosted VPS runner (`NOX_MEM_DIR` env set + `dist/index.js` present), the same checks transparently switch to the live binary instead of the mock. Same code, two modes.

---

## How the Mock Contract Works

`fixtures/mock-nox-mem.cjs` implements a 4-command subset of the real nox-mem CLI (`stats`, `search`, `ingest-entity`, `answer`). It honours the following env-var contract — the same one the real binary respects:

| Env var | Effect |
|---|---|
| `NOX_OFFLINE_MODE=1` | Refuse all outbound HTTP. Embed calls throw, search falls back to FTS. |
| `NOX_LLM_PROVIDER=gemini\|anthropic\|...` | Routes provider; emits structured errors for missing/invalid keys. |
| `NOX_ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEY` | Anthropic provider credentials. |
| `GEMINI_API_KEY` | Gemini provider credentials. |
| `NOX_FAIL_IF_EMBED=1` | Throw `EMBED_CALLED_UNEXPECTEDLY` if the embedding path runs. |
| `NOX_FIXTURE_DB` | Path to the JSON-backed fixture DB (default: `fixtures/fixture-db.json`). |
| `NOX_NETWORK_REPORT` | Append outbound URL attempts to this file (one per line). |

The mock is the **contract under test**. When A3 lands and the real binary implements provider abstraction, the same checks run against `dist/index.js` automatically.

---

## Failure Modes & Remediation

| Failure | Immediate action |
|---------|-----------------|
| New GPL dep detected | Check if dep is dev-only (`devDependencies`). If yes, add to `allowlist.json` with reason "dev-only, not shipped". If runtime, find OSS alternative or get legal sign-off. |
| Unexpected egress domain | Audit recent dependency updates (`npm diff`). Check for analytics/telemetry flags in new dep's README. |
| Offline mode fails | A dep updated and added network-mandatory behavior. Bisect with `npm diff` + git log. |
| sqlite3 can't open DB | Check WAL mode — if WAL file present, DB may be mid-transaction. Run `PRAGMA wal_checkpoint(TRUNCATE)` on VPS first. |
| No-daemon check fails | WAL file left by crashed process. Safe to remove `.db-shm` + `.db-wal` if nox-mem is confirmed dead. |
| Embed-cache replay fails | Search re-embeds on every call. Check `src/lib/embed-cache.ts` for cache lookup before Gemini fetch. |
| Provider substitution hangs | Timeout logic missing in provider adapter. Check `src/lib/providers/` for missing `AbortController` usage. |
| Archive portability fails | `nox-mem export` command missing or broken after refactor. Check `dist/index.js --help`. |

---

## Design Decisions (updated 2026-05-18)

1. **Mock CLI mirrors the real CLI contract.** `fixtures/mock-nox-mem.cjs` exposes `stats`, `search`, `ingest-entity`, `answer` against a JSON-backed fixture DB. When `NOX_MEM_DIR/dist/index.js` exists, the checks use the real binary instead. Same checks, same assertions, two modes.

2. **Socket-level enforcement via NODE_OPTIONS preload.** The offline-mode check loads `fixtures/socket-guard.cjs` via `NODE_OPTIONS=--require ...`, patching `net.Socket.prototype.connect` to reject non-loopback peers. This catches native code that bypasses Node's HTTP stack — far more robust than `http_proxy` env tricks.

3. **`NOX_FAIL_IF_EMBED` is part of the public contract.** The embedding-cache-replay check requires the real binary to throw if the embedding path runs when this env var is set. This is a forcing function for the planned A3 provider abstraction work — the contract is enforced in CI today, the implementation will follow.

4. **Temp DB only** — checks never touch the production `nox-mem.db`. All DB operations use a fixture copy or `VACUUM INTO` clone.

5. **allowlist.json is auditable** — every override requires a documented reason. The runner logs which overrides were applied in the JSON report.

6. **Shell scripts for SQLite checks** — deliberately avoids Node.js for checks 4 and 5 to prove the DB is readable by any standard tooling, not just nox-mem's own runtime.
