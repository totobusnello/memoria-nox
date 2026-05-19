# Zero-Vendor Validation Suite

**Purpose:** Prove that nox-mem has no critical third-party proprietary runtime dependency. Every check is CI-runnable and fails loudly on violation.

**Pillar A tagline:** "Pain-weighted hybrid memory with shadow discipline — yours by design."

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
npx ts-node validation/zero-vendor/runner.ts

# Individual checks
npx ts-node validation/zero-vendor/license-check.ts
npx ts-node validation/zero-vendor/runtime-deps-check.ts
npx ts-node validation/zero-vendor/offline-mode-check.ts
bash validation/zero-vendor/sqlite-portable-check.sh
bash validation/zero-vendor/no-daemon-check.sh

# CI (GitHub Actions runs this automatically on every PR)
# See: validation/zero-vendor/ci-action.yml
```

---

## The 8 Checks

| # | Name | File | Status |
|---|------|------|--------|
| 1 | **license-check** | `license-check.ts` | Runnable in CI (no VPS needed) |
| 2 | **runtime-deps-check** | `runtime-deps-check.ts` | Requires VPS deploy (needs live nox-mem) |
| 3 | **offline-mode-check** | `offline-mode-check.ts` | Requires VPS deploy (needs embedding cache) |
| 4 | **sqlite-portable-check** | `sqlite-portable-check.sh` | Runnable in CI with test fixture DB |
| 5 | **no-daemon-check** | `no-daemon-check.sh` | Runnable in CI with test fixture DB |
| 6 | **embedding-cache-replay** | inline in `offline-mode-check.ts` | Requires VPS deploy |
| 7 | **provider-substitution-dry-run** | inline in `runtime-deps-check.ts` | Runnable in CI (error path test) |
| 8 | **archive-portability** | inline in `runner.ts` | Runnable in CI (export + tar) |

### Check Details

#### 1. license-check
Parses `package.json` + `node_modules/.package-lock.json`, classifies every direct and transitive dependency by SPDX license.

**PASS:** All deps have licenses in the OSS allow-set:
`MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, CC-BY-4.0, Unlicense, 0BSD, BlueOak-1.0.0`

**FAIL:** Any dep with `GPL-*`, `AGPL-*`, `LGPL-*`, `Custom`, `Proprietary`, `Commercial`, `UNLICENSED`, `SEE LICENSE IN ...`, `(Unlicense AND ...)` combinations, or any unknown/empty license field.

**Override:** Add to `allowlist.json` with documented reason. Overrides are logged in the JSON report.

#### 2. runtime-deps-check
Boots a sandboxed nox-mem instance with `NOX_OFFLINE_MODE=1`, captures outbound TCP via `/proc/net/tcp` diff (Linux VPS) or `lsof -i` (macOS CI). 

**PASS:** Only Gemini API (`generativelanguage.googleapis.com`) attempted, only when `NOX_OFFLINE_MODE=0`.

**FAIL:** Any egress to telemetry endpoints, "phone home" domains, package registries, or unexpected third-party services.

#### 3. offline-mode-check
Starts nox-mem with `NOX_OFFLINE_MODE=1` + pre-populated embedding cache. Ingests a sample entity file, runs a search query, verifies the full workload completes.

**PASS:** Zero outbound network calls. All operations use cached embeddings.

**FAIL:** Any network call attempted during the test workload.

#### 4. sqlite-portable-check
Copies `nox-mem.db` to a fresh temp directory, opens it with the system `sqlite3` CLI (no nox-mem code), runs schema introspection and basic SELECT queries.

**PASS:** `.schema` shows expected tables, `SELECT count(*) FROM chunks` returns > 0, `SELECT count(*) FROM kg_entities` returns ≥ 0.

**FAIL:** `sqlite3` cannot open the file, schema is missing critical tables, or any SQLITE_CORRUPT error.

**What this proves:** The memory file is a standard SQLite database openable by any SQLite client. No proprietary format, no vendor-specific extensions required.

#### 5. no-daemon-check
Kills all nox-mem processes (`nox-mem-api`, `nox-mem-watcher`, any process holding nox-mem.db WAL), then opens the DB with `sqlite3` and confirms queries work.

**PASS:** Queries succeed with zero nox-related processes running.

**FAIL:** Database locked, WAL corruption, or queries fail without daemon.

**What this proves:** You own your data. No background process required to read your memory.

#### 6. embedding-cache-replay
Runs the same search query twice. Second run must complete without triggering a Gemini API call. Validates via network intercept + embedding cache hit counter in `/api/health`.

**PASS:** `health.embeddingCacheHits` increments, no new outbound connections on second run.

**FAIL:** Every query re-embeds unconditionally (network dependency for reads).

#### 7. provider-substitution-dry-run
Sets `NOX_LLM_PROVIDER=anthropic` with an intentionally invalid API key. Verifies nox-mem fails with a clear, actionable error message (not a silent hang or cryptic crash).

**PASS:** Clear error within 5s: "Invalid API key for provider: anthropic. Check NOX_ANTHROPIC_API_KEY."

**FAIL:** Silent hang, timeout > 30s, cryptic error message, or segfault.

**What this proves:** Provider substitution is architecturally supported. Switching away from Gemini doesn't break the binary — it fails cleanly on misconfiguration.

#### 8. archive-portability
Runs `nox-mem export --format sqlite`, then `tar -czf archive.tar.gz export/` and `tar -tzf archive.tar.gz`. Verifies the archive can be created and inspected with standard Unix tooling.

**PASS:** Archive created, `tar -tzf` lists expected files with no errors, total size < 2× DB size.

**FAIL:** Export requires proprietary tooling, tar fails, or archive is unreadable.

---

## Failure Modes & Remediation

| Failure | Immediate action |
|---------|-----------------|
| New GPL dep detected | Check if dep is dev-only (`devDependencies`). If yes, add to allowlist.json with reason "dev-only, not shipped". If runtime, find OSS alternative or get legal sign-off. |
| Unexpected egress domain | Audit recent dependency updates (`npm diff`). Check for analytics/telemetry flags in new dep's README. |
| Offline mode fails | A dep updated and added network-mandatory behavior. Bisect with `npm diff` + git log. |
| sqlite3 can't open DB | Check WAL mode — if WAL file present, DB may be mid-transaction. Run `PRAGMA wal_checkpoint(TRUNCATE)` on VPS first. |
| No-daemon check fails | WAL file left by crashed process. Safe to remove `.db-shm` + `.db-wal` if nox-mem is confirmed dead. |
| Provider substitution hangs | Timeout logic missing in provider adapter. Check `src/lib/providers/` for missing `AbortController` usage. |
| Archive portability fails | `nox-mem export` command missing or broken after refactor. Check `dist/index.js --help`. |

---

## Blocked Checks (BLOCKED.md rationale)

See `BLOCKED.md` if any check cannot be fully implemented. Currently: none blocked.

---

## CI Integration

GitHub Actions workflow at `validation/zero-vendor/ci-action.yml` runs:
- Checks 1, 4, 5, 7, 8 on every PR (no VPS needed)
- Checks 2, 3, 6 gated behind `requires-vps` label (manual trigger or VPS-connected runner)

---

## Design Decisions

1. **Temp DB only** — checks never touch the production `nox-mem.db`. All DB operations use a fixture copy or `VACUUM INTO` clone.
2. **allowlist.json is auditable** — every override requires a documented reason. The runner logs which overrides were applied in the JSON report.
3. **Shell scripts for SQLite checks** — deliberately avoids Node.js for checks 4 and 5 to prove the DB is readable by any standard tooling, not just nox-mem's own runtime.
