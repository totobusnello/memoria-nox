# Audit: Reindex Overwrite Incident (3rd Occurrence)

**Date:** 2026-05-24 (incident 2026-05-23 23:17 BRT)
**Severity:** P0 — prod data loss class
**Status:** Emergency fix shipped (PR `emergency/reindex-overwrite-fix`)
**Recovery snapshot:** `/root/backups/nox-mem-incident-20260523-2317/` (atlas, 69032 chunks)

---

## Executive summary

Third wipe-class incident in `nox-mem reindex` flow within ~30 days. Root cause in
`src/reindex.ts` `_reindexImpl()`: the function calls `db.exec("DELETE FROM chunks")`
in-band before re-ingesting via `routeIngest`, with no upsert semantics and no
post-condition guard. Any partial failure (Gemini API quota, network blip, file system
error, concurrent write race) leaves the DB in a wipe state. The withOpAudit wrapper
takes a snapshot pre-op but does NOT prevent the destructive operation — recovery
remains manual via `safeRestore()`.

This PR replaces the destructive flow with content-fingerprint UPSERT + 4-layer
defense. Adds canary test that runs on every PR.

---

## Timeline

| Date | Time (BRT) | Event |
|---|---|---|
| 2026-04-25 | ~end-of-day | First incident: cron `nox-mem reindex` wiped section/retention metadata of 183 entities |
| 2026-04-25 | next day | Patched: cron switched to `consolidate` (avoids reindex). Reindex code itself untouched. |
| 2026-05-19 | mid-day | Second incident: eval ingest cruzou pro main DB; ~5828 chunks lost |
| 2026-05-19 | same day | PR #145: 4-layer fix (NOX_DB_PATH priority, large-DB guard, harness isolation, secrets scrub) |
| 2026-05-21 | morning | Vec0 fix deployed: lazy sqlite-vec load before reindex DELETE (audit 2026-05-21) |
| 2026-05-23 | 23:17 | **THIS INCIDENT:** scheduled reindex sobrescreveu chunks. Parallel session diagnosed, snapshot atlas preserved 69032 chunks. |
| 2026-05-24 | early AM | Emergency fix branch + canary test + runbook + audit shipped (this PR) |

---

## Root cause: destructive-then-rebuild pattern

`_reindexImpl()` pre-fix:

```ts
// Phase A: snapshot access metadata into in-memory Map (read-only)
const accessSnapshot = new Map(...);

// Phase B: WIPE
db.exec("DELETE FROM chunks");                                  // <- IRREVERSIBLE
db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");

// Phase C: re-ingest, per-file catch
for (const file of allFiles) {
  try { await routeIngest(file, { externalDb: db, skipDelete: true }); }
  catch (err) { console.error(...); }                          // <- swallowed
}

// Phase D: restore access metadata via UPDATE matching first 80 chars of chunk_text
// ...

// Phase E: clear retention_days for core tier
db.exec("UPDATE chunks SET retention_days = NULL WHERE tier = 'core'");
```

Failure surface:

1. **Quota / network / file errors mid-Phase C**: `routeIngest` throws for individual
   files; per-file catch lets the loop continue with FEWER chunks ingested than
   originally existed. End-of-loop returns a "successful" reindex with 80% / 50% / 10%
   of the original corpus.

2. **Phase D match-by-prefix collision**: two chunks with same `source_file` + first
   80 chars of `chunk_text` (very common in entity files with structured frontmatter)
   would mis-attribute access metadata. Not a wipe, but data corruption.

3. **Concurrent watcher writes between Phase B and Phase C**: the watcher process
   continues ingesting in parallel. Its inserts land BETWEEN the DELETE and the
   for-loop re-ingest, and may be either: (a) overwritten by a stale Phase D UPDATE,
   or (b) deleted by an upstream cron triggering a second reindex.

4. **The `vec_chunks` trigger cascade**: `DELETE FROM chunks` cascades to
   `vec_chunks` via `trg_chunks_delete_cascade`. Pre-2026-05-21 this trigger would
   fail with `no such module: vec0` because CLI didn't load sqlite-vec. The lazy-load
   fix patched the trigger failure but did not address the destructive pattern.

5. **No post-condition check**: Phase E's UPDATE runs unconditionally even if Phase C
   produced 0 chunks. The function returns `{ files: N, chunks: totalChunks }` with
   `totalChunks` reflecting partial ingest. `withOpAudit` marks status='success' and
   updates `affected_rows`. Health endpoint shows degraded state but operator must
   notice.

---

## Why withOpAudit alone wasn't sufficient

`withOpAudit` provides:
- Pre-op VACUUM INTO snapshot at `/var/backups/nox-mem/pre-op/reindex-main-<ts>-<pid>-<uuid>.db`
- Audit row in `ops_audit` with lifecycle (running -> success/failed/crashed)
- Secret-scrubbed error messages

What it does NOT provide:
- Prevention of the destructive op (it wraps, not gates)
- Automatic rollback on partial failure (Phase C errors are swallowed per-file)
- Post-condition validation (success determined by absence of thrown error, not by data integrity)
- Operator notification on chunk-count regression

The 2026-05-23 incident's snapshot DID get taken — recovery was operationally trivial
once detected — but DETECTION required external monitoring (health endpoint + Toto
noticing chunk count dropped).

---

## Fix architecture: 4 defense layers

### Layer 1 — UPSERT via content fingerprint (kills the wipe pattern)

`reindex.ts` no longer calls `db.exec("DELETE FROM chunks")`. The new flow:

```
maxIdBefore = MAX(id)
oldByFingerprint = { sha256(source_file + chunk_text) -> {id, tier, ...} }
                   for each row in chunks

for each file:
  routeIngest(file, { skipDelete: true })   # new chunks get id > maxIdBefore

newChunks = SELECT WHERE id > maxIdBefore
for each newChunk:
  fp = fingerprint(newChunk)
  if fp in oldByFingerprint:
    UPDATE newChunk metadata from old
    mark old as 'seen'

# Phase 4: orphan delete (the ONLY destructive op, runs AFTER all ingests succeed)
for each oldChunk where id NOT IN seen:
  DELETE FROM chunks WHERE id = ?     # prepared stmt, single-row, in transaction

# Phase 5: invariant (Layer 4 below)
```

Identity is `(source_file, sha256(chunk_text))` because the `chunks.id` AUTOINCREMENT
is not stable across reindex.

### Layer 2 — withOpAudit pre-op snapshot (preserved + leveraged)

Unchanged from existing implementation. Layer 4 throws on wipe detection -> withOpAudit
runs the failure path -> snapshot preserved -> operator runs `safeRestore()`.

### Layer 3 — `--dry-run` mode (expanded)

Returns JSON declaring `mode: "UPSERT"`, `protected.wipeGuard`, file breakdown. Does
NOT mutate the DB. Canary test asserts DB row count unchanged after dry-run invocation.

### Layer 4 — Wipe-detection invariant

```ts
ratio = preCount === 0 ? 1 : postCount / preCount;
if (preCount > 0 && ratio < MIN_RETENTION_RATIO && !ALLOW_WIPE) {
  throw new ReindexWipeDetectedError(preCount, postCount, MIN_RETENTION_RATIO);
}
```

Defaults: `MIN_RETENTION_RATIO=0.90`, `ALLOW_WIPE=false`. Both env-overridable.

Throw inside `withOpAudit` -> failure path -> ops_audit row marked status='failed',
error_message='[reindex] WIPE DETECTED ...', snapshot preserved.

---

## Canary test (CI gate)

`src/__tests__/reindex.no-wipe.test.ts` — 5 tests, ~140ms total:

1. UPSERT contract: seed 1000 chunks, simulate reindex SQL, assert >= 990 survive.
2. Metadata inheritance: assert tier/retention_days/section/importance/access_count
   inherited from old row to new row via fingerprint match.
3. Error class instantiation: validate fields + message contains 'WIPE DETECTED' and
   'safeRestore'.
4. Dry-run no-op: verify `mode="UPSERT"` + DB row count unchanged.
5. Source code grep: regex enforces no `db.exec("DELETE FROM chunks")` literal
   anywhere in `reindex.ts`. Future PR re-introducing the pattern fails CI.

**Mandate**: this test runs on EVERY PR. Disabling or skipping it requires explicit
override + Toto sign-off + rationale in commit message.

---

## Open questions / follow-up

| ID | Question | Disposition |
|---|---|---|
| Q1 | Should `routeIngest` itself adopt UPSERT semantics, removing the need for the staging-id approach in reindex? | Yes, follow-up PR. This emergency fix takes the minimal-change path. |
| Q2 | Should `withOpAudit` add post-condition hook to validate `affected_rows >= preCount * threshold`? | Generalize Layer 4 into op-audit. Tracked in follow-up. |
| Q3 | The Phase 4 orphan delete runs per-row in a transaction. For 60k+ chunks with significant churn, this could be slow. Should we batch DELETE BY id IN (?, ?, ...)? | Acceptable for now (transactional, deterministic). Optimize if observed latency exceeds 2x baseline. |
| Q4 | The fingerprint uses first 32 hex chars of sha256 (128 bits). Collision probability over 100k chunks negligible (~10^-20). Acceptable. | Resolved. |
| Q5 | What about `consolidate`, `compact`, `crystallize`, `kg-prune`? Same destructive-then-rebuild pattern? | Audit these as follow-up. CLAUDE.md regra #6 already requires withOpAudit; verify all four wrap correctly. |

---

## Sign-off requirements (Toto)

- [ ] Review PR diff (`src/reindex.ts` before/after)
- [ ] Confirm `MIN_RETENTION_RATIO=0.90` is the right threshold (tighter = more false
      positives on legitimate dedup; looser = wipe risk)
- [ ] Approve cron re-enable on VPS after PR merge
- [ ] Decide whether to make Layer 4 invariant available to `consolidate`/`compact`/etc
      as a follow-up PR

---

## References

- `staged-reindex-emergency/edits/src/reindex.ts` — fixed implementation
- `staged-reindex-emergency/edits/src/reindex-errors.ts` — error class
- `staged-reindex-emergency/edits/src/__tests__/reindex.no-wipe.test.ts` — canary
- `docs/REINDEX-EMERGENCY-FIX-RUNBOOK.md` — deployment procedure
- Memory `[[incident-2026-05-19-wipe]]`
- Memory `[[reindex-must-route-entity-files]]`
- Memory `[[eod-cron-reindex-was-the-real-trigger]]`
- `audits/2026-04-25-A1-A2-review.md`
- `audits/2026-05-21-vec0-reindex-fix-deployed.md`
