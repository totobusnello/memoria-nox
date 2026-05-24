# A2 Tier 3 P5 — Deployment Dry-Run Validation
**Date:** 2026-05-24
**Auditor:** Sisyphus-Junior (Sonnet 4.6)
**Scope:** End-to-end dry-run validation of PR #299 deployment automation — no actual VPS deploy performed.
**Verdict:** GO-WITH-FIXES (1 minor script bug found; tests 96/96 pass; all dry-run modes clean)

---

## Environment

- Repo: `/Users/lab/Claude/Projetos/memoria-nox` (main, ce44cd8)
- staged-A2-T3 package: `nox-mem-a2-tier3-staged@0.5.0-a2-tier3-p5`
- TypeScript: `^5.4.0`
- better-sqlite3-multiple-ciphers: `^11.10.0` (installed fresh via npm install)

---

## 1. Script Syntax + Help

### bash -n (syntax check)
```
bash -n scripts/deploy-a2-tier3.sh
SYNTAX OK
```
Exit 0. No parse errors.

### --help
```
Usage: scripts/deploy-a2-tier3.sh [flags]

Flags:
  --dry-run         Print plan without executing destructive commands.
  --phase <list>    Comma-separated phases A..K (e.g. 'A,B,C').
  --all             Equivalent to --phase A,B,C,D,E,F,G,H,I,J,K.
  --pre-flight      Run pre-flight checks only.
  --vps-host <h>    VPS hostname for SSH-based phases.
  --log-dir <p>     Override audit log directory (default: ./audits).
  --help, -h        This help.
```
Exit 0. Usage correct, all flags documented.

### --dry-run --all (no VPS_HOST)
Correctly reaches Phase A (local only), prints [DRY] for all commands in A, then exits 4 at Phase B
because `require_env VPS_HOST` fires. This is **correct behavior** — B through K require VPS.

### --dry-run --phase A (no VPS_HOST)
Exit 0. Full Phase A plan printed with [CMD]/[DRY] for both build and gen-key commands. Manual
instructions block printed correctly.

### --dry-run --phase B,C --vps-host fake-nox-prod (after fix)
Exit 0. All SSH commands wrapped as [CMD]/[DRY] — no real SSH attempted for phase body. Pre-flight
PF-1 through PF-7 all printed as [CMD]/[DRY].

### --pre-flight --dry-run
Exit 0. PF-1 skipped gracefully (no VPS_HOST), PF-5 npm view printed as [DRY], PF-6/PF-7 skipped.
Log file written to audits/ (timestamped ISO filename). All 7 pre-flight checks accounted for.

---

## 2. Bug Found + Fixed: Phase B Post-Condition Probe Bypasses dry-run

**Severity:** Low (cosmetic SSH noise in dry-run; no data mutation)
**Location:** `scripts/deploy-a2-tier3.sh`, `phase_b()`, post-condition check

**Root cause:** The idempotency check used raw `ssh "${VPS_HOST}" 'grep -c ...'` directly instead
of the `run()` wrapper, so it executed even with `--dry-run`. With a real but unreachable VPS this
would add a 30s SSH timeout. With `|| true` the failure was swallowed.

**Fix applied:** Wrapped the raw `ssh` call in `if (( DRY_RUN == 0 )); then ... fi`. In dry-run
mode `check` defaults to `"0"` (no-op — assume not yet deployed) so Phase B body prints [DRY] cleanly.

**Verification:** After fix, `--dry-run --phase B,C --vps-host fake-nox-prod` exits 0 with zero
live SSH connections; all commands are [CMD]/[DRY].

---

## 3. TypeScript Compile (noEmit)

```
cd staged-A2-T3 && npx tsc --noEmit
TSC EXIT: 0
```

Zero errors. All types clean across:
- `edits/src/lib/db.ts` — SQLCipher wire-up
- `edits/src/lib/reads-audit.ts` + schema SQL
- `edits/src/lib/audit-checkpoints.ts` + schema SQL
- `edits/scripts/audit-checkpoint-cli.ts`
- `edits/scripts/reads-audit-sweep.ts`
- `scripts/migrate-encrypt-db.ts`

---

## 4. Checkpoint CLI Parse

### Top-level --help
```
audit-checkpoint — A2 Tier 3 / Phase 4 — Ed25519 signed forensic checkpoints

Usage:
  audit-checkpoint gen-key      --out-dir <path>
  audit-checkpoint create       --scope <ops|reads>   --key-file <private.b64>
  audit-checkpoint verify       --id <int>            --key-file <public.b64>
  audit-checkpoint verify-chain --scope <ops|reads|all> --key-file <public.b64>

Exit codes: 0=success / 1=usage error / 2=runtime failure / 3=verify FAILED
```
Exit 0. All subcommands documented.

### gen-key subcommand --help
```
[audit-checkpoint] runtime error: gen-key requires --out-dir <path>
EXIT: 2
```
**Gotcha (info only):** `gen-key --help` is not implemented — CLI expects `--out-dir` and exits 2.
Top-level `--help` covers all usage. Not a blocker.

---

## 5. Build

```
npm run build
> tsc && npm run copy-sql
BUILD EXIT: 0
```

All output artifacts present:
- `dist/edits/scripts/audit-checkpoint-cli.js`
- `dist/edits/scripts/reads-audit-sweep.js`
- `dist/scripts/migrate-encrypt-db.js`
- `dist/edits/src/lib/reads-audit-schema.sql`
- `dist/edits/src/lib/audit-checkpoints-schema.sql`

---

## 6. Test Suite

```
npm test
ℹ tests 96
ℹ suites 36
ℹ pass 96
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3245.829583
TEST EXIT: 0
```

**96/96 pass.** Matches PR #299 baseline.

### Coverage by suite (selected)

| Suite | Tests | Status |
|---|---|---|
| generateKeyPair | 3 | PASS |
| canonical row JSON (hash determinism) | 4 | PASS |
| createCheckpoint | 4 | PASS |
| tamper detection | 4 | PASS |
| verifyChain | 2 | PASS |
| schema triggers | 4 | PASS |
| encrypted DB checkpoint | 1 | PASS |
| encrypted round-trip | 1 | PASS |
| wrong-key rejection | 2 | PASS |
| plaintext mode (backward-compat) | 2 | PASS |
| VACUUM INTO encrypted snapshot | 1 | PASS |
| db.ts integration — env-driven open paths | 3 | PASS |
| reads_audit DISABLED (default) | 2 | PASS |
| reads_audit ENABLED — basic round-trip | 3 | PASS |
| reads_audit PII sanitization | 3 | PASS |
| reads_audit hash mode | 4 | PASS |
| reads_audit append-only triggers | 3 | PASS |
| reads_audit on encrypted DB | 1 | PASS |
| reads_audit retention sweep | 4 | PASS |
| reads-audit-sweep parseArgs | 4 | PASS |
| end-to-end migration of synthetic nox-mem-like DB | 5 | PASS |
| already-encrypted source detection | 2 | PASS |
| swapEncryptedIntoSource | 3 | PASS |
| Test 1 — encrypted DB opens with key | 3 | PASS |
| Test 2 — row counts match pre-migration | 4 | PASS |
| Test 3 — FTS5 query roundtrip on encrypted DB | 3 | PASS |
| Test 4 — BigInt INTEGER round-trip on encrypted DB | 2 | PASS |
| Test 5 — initial checkpoint creation + verify-chain | 4 | PASS |
| smoke suite discovery sanity | 2 | PASS |

---

## 7. Pre-Flight Mode — Local Checks (sans VPS)

With no `NOX_VPS_HOST`:
- PF-1: skipped gracefully — "no VPS_HOST set; manual baseline required"
- PF-2 through PF-4: skipped (VPS-only) — correct
- PF-5: `npm view better-sqlite3-multiple-ciphers@^11.10` — [DRY] in dry-run mode
- PF-6, PF-7: skipped (VPS-only) — correct
- Exit 0

---

## 8. Dry-Run Behavior Summary

| Mode | Exit | All destructive cmds [DRY]? | Notes |
|---|---|---|---|
| `--help` | 0 | N/A | Usage prints correctly |
| `--pre-flight --dry-run` | 0 | Yes | PF-5 npm view [DRY]; VPS checks skipped |
| `--dry-run --phase A` | 0 | Yes | Build + gen-key both [DRY] |
| `--dry-run --phase B,C --vps-host fake` | 0 | Yes (after fix) | Post-condition SSH guard applied |
| `--dry-run --all` (no VPS_HOST) | 4 | Yes (A only) | Exits correctly at B require_env |

---

## 9. Findings Summary

| # | Severity | Description | Status |
|---|---|---|---|
| F1 | Low | `phase_b()` post-condition `ssh` call bypassed `run()` in dry-run | FIXED in this PR |
| F2 | Info | `gen-key --help` exits 2 (no subcommand help) | Accepted; top-level --help covers it |
| F3 | Info | `--dry-run --all` exits 4 at B when no VPS_HOST — operator must use `--vps-host` | Expected behavior |

---

## 10. Verdict

**GO-WITH-FIXES**

All 96 tests pass. TypeScript compiles clean. All dry-run modes exit 0 correctly. One minor bug
(F1: Phase B post-condition SSH fired outside `run()`) was found and fixed in `scripts/deploy-a2-tier3.sh`.
No blockers to proceeding with production deployment once `NOX_VPS_HOST` and `NOX_DB_KEY` are set
in operator environment. Manual steps (Phase A key custody, Phase E key backup, Phase J offline signing)
are correctly gated with `[MANUAL]` blocks and `read -p` prompts that are automatically skipped in
`--dry-run` mode.
