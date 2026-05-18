# ADR-002: Append-only audit logs for destructive operations

Date: 2026-04-25

## Status

Accepted

## Context

nox-mem performs destructive operations on its SQLite database: `reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune`. An incident on 2026-04-25 caused section/retention metadata to be wiped across 183 entity chunks (~12 min recovery) when `reindex.ts` used generic `ingestFile()` instead of `ingestEntityFile()`. The OpenClaw end-of-day cron had been running `nox-mem reindex` daily without any pre-operation snapshot.

Two specific failure modes emerged from that incident and subsequent audit:

1. **No pre-op snapshot**: destructive op ran directly on production DB; no rollback point.
2. **Audit trail mutability**: if ops were logged without immutability guarantees, an attacker or a buggy cleanup routine could silently DELETE or UPDATE audit rows, hiding the history of what ran.

A secondary incident on 2026-04-26 introduced 6 zombie `ops_audit` rows: `closeDb()` was called mid-function inside a `withOpAudit()` wrapper, which invalidated the final UPDATE that marks the operation complete.

CWE-693 (Protection Mechanism Failure) applies: a mutable audit table provides false assurance; an attacker who compromises the system can erase their tracks.

## Decision

All destructive database operations are wrapped with `withOpAudit()` from `src/lib/op-audit.ts`, which:

1. Creates an **atomic pre-op snapshot** via SQLite `VACUUM INTO` at `/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db`. ACL 0600, directory 0700, symlink-aware path via `realpathSync`. Retention 7 days (separate from daily backup).
2. Writes a row to `ops_audit` with status `'started'`.
3. On success, updates to `'success'`; on application error, `'failed'`; on uncaught crash, `'crashed'`.

The `ops_audit` table is **append-only** enforced by two database triggers:
- `trg_ops_audit_no_delete` — ABORT on any DELETE.
- `trg_ops_audit_terminal_immutable` — ABORT on UPDATE of rows whose status is already terminal (`success`, `failed`, `crashed`).

Valid status enum: `started` (initial), `success` (terminal OK), `failed` (terminal app error), `crashed` (terminal system error). Values `completed` and `rolled_back` are NOT valid despite historical mentions in older docs.

Additional safety rules:
- `closeDb()` belongs to the **caller** (CLI handler / daemon), never inside a wrapped function. Calling it mid-function invalidates the `withOpAudit` final UPDATE (incident B2, 2026-04-26).
- `--dry-run` flag on `reindex` and `consolidate` produces a JSON preview (wouldDelete/wouldProcess/estimatedDuration) without mutating the DB.
- Emergency override `NOX_ALLOW_NO_SNAPSHOT=1` is available when snapshot fails due to disk-full; use only when the reason is known and legitimate, never as a shortcut.
- Recovery via `safeRestore()` in `src/lib/op-audit.ts`: validates `user_version` match, restores main DB first, then removes stale WAL/SHM. Direct `cp snapshot.db nox-mem.db` is forbidden (can corrupt if WAL is stale).

## Consequences

- **Positive:** Every destructive operation has a rollback point. Audit trail is tamper-evident. `ops_audit` breakdown by agent is exposed via `/api/health.opsAudit.byDbSource`.
- **Positive:** Pre-op snapshots enable `safeRestore()` even if the main DB is corrupted.
- **Negative:** `VACUUM INTO` snapshot adds ~2-3s overhead per destructive op. Disk usage grows: snapshot retention requires ~2× DB size free space (enforced by pre-flight `statfsSync` check).
- **Negative:** `ops_audit` rows with stale `snapshot_path` accumulate after snapshot pruning. Accepted trade-off: audit trail completeness > disk minimalism.
- **Risks:** If VPS disk is full and `NOX_ALLOW_NO_SNAPSHOT=1` is misused habitually, the safety net erodes silently.

## Alternatives considered

- **Daily backup only (no pre-op snapshot)** — rejected: daily backup is at most 24h stale; a destructive op can wipe data that was never in a backup window. Incident 2026-04-25 confirmed this gap.
- **Mutable audit log with soft-delete** — rejected: violates CWE-693; attacker or buggy cron could hide evidence; `ABORT` triggers are the only reliable enforcement.
- **External audit service** — rejected: over-engineering for single-VPS deployment; SQLite triggers provide the same immutability guarantee with zero operational overhead.

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` §3.Operations & Safety items 8, 9, 10, 11
  - `docs/DECISIONS.md` §4 (incidents 2026-04-25 and 2026-04-26)
  - `docs/DECISIONS.md` §5 (constraints: `ops_audit` append-only)
  - `docs/DECISIONS.md` D34 (op-audit canonical patterns 2026-05-15)
  - `reference_a1_op_audit_module.md`
  - `audits/2026-04-26-W2-cleanup.md` W2-1
  - `docs/INCIDENTS.md#2026-04-25`
