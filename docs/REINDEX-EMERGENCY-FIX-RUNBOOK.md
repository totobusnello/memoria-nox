# Reindex Emergency Fix Runbook

> **Status:** EMERGENCY — 3rd wipe incident (2026-05-23 23:17 BRT). Next nightly cron Sun 2026-05-24 23:00 BRT will wipe again if this fix is not deployed.
>
> **Scope:** UPSERT-based reindex + 4-layer defense (UPSERT / withOpAudit / dry-run / wipe-invariant) + canary test.
>
> **Artifacts:** `staged-reindex-emergency/edits/src/{reindex.ts,reindex-errors.ts,__tests__/reindex.no-wipe.test.ts}` (real prod files live at `/root/.openclaw/workspace/tools/nox-mem/src/`).

---

## TL;DR

```
ssh root@vps
# Phase A: stop the bleeding
crontab -l | grep -v 'nox-mem reindex' | crontab -

# Phase B: snapshot current state (belt-and-suspenders)
cp /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
   /root/backups/nox-mem-pre-emergency-fix-$(date -u +%Y%m%dT%H%MZ).db

# Phase C: deploy the fix
cd /root/.openclaw/workspace/tools/nox-mem
git fetch origin
git checkout emergency/reindex-overwrite-fix
npm run build
npm test -- --grep "reindex.no-wipe"  # MUST pass before proceeding

# Phase D: dry-run on prod DB (read-only)
node dist/index.js reindex --dry-run | tee /tmp/reindex-dryrun.json

# Phase E: re-enable cron with fixed code
crontab -e  # restore the reindex line, verify timing

# Phase F: monitor 24h
watch -n 60 'curl -s http://127.0.0.1:18802/api/health | jq "{chunks: .totalChunks, opsAudit: .opsAudit.last_op}"'
```

---

## Background: 3 wipe incidents, same class

| Date | Symptom | Trigger | Patch |
|---|---|---|---|
| 2026-04-25 | 183 entities lost section/retention metadata | end-of-day cron ran `nox-mem reindex` (no protection) | Cron switched to `consolidate`. Reindex code itself stayed buggy. |
| 2026-05-19 | ~5828 chunks lost — eval ingest cruzou pro main DB | NOX_DB_PATH ignored by db.ts before #145 | PR #145 4-layer fix (NOX_DB_PATH priority + checkLargeDbIngestGuard + harness isolation + secrets scrub) |
| 2026-05-23 23:17 | nightly reindex sobrescreveu chunks (recovery: snapshot `atlas` 69032 chunks) | `db.exec("DELETE FROM chunks")` in `_reindexImpl()` followed by ingest — partial failure = partial DB | **THIS RUNBOOK** |

Common pattern: **destructive-then-rebuild** mid-band, no UPSERT path. Layer-1 fix removes that pattern entirely.

---

## Root Cause Analysis (2026-05-23 incident)

`src/reindex.ts` `_reindexImpl()`:

```ts
// Lines 73-74 of pre-fix reindex.ts
db.exec("DELETE FROM chunks");                              // <-- IRREVERSIBLE in-band
db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");

for (const file of allFiles) {
  try {
    const result = await routeIngest(file, { externalDb: db, skipDelete: true });
    totalChunks += result.chunks;
  } catch (err) {
    console.error(`[ERROR] ${file}: ${err}`);   // <-- swallowed per-file; loop continues
  }
}
```

Failure modes:

| Mode | Outcome |
|---|---|
| Gemini API quota mid-loop | All subsequent `routeIngest` calls fail. DB has partial chunks. |
| Network blip | Same as above. |
| File system error on one file | Single file dropped; rest OK. **Acceptable.** |
| Concurrent watcher write between DELETE and re-INSERT | Race; watcher's chunks overwritten by older snapshot logic, then re-deleted by orphan delete. |
| `db.exec("DELETE FROM chunks")` itself fails (sqlite-vec trigger) | Fixed 2026-05-21 via lazy vec0 load. Still leaves DB in INDETERMINATE state. |

`withOpAudit` DOES wrap the call and takes a snapshot pre-op, but **recovery is manual**:
operator must `ssh` in, find the snapshot, run `safeRestore()`. This is the operational
gap that caused the 2026-04-25, 2026-05-19, and 2026-05-23 incidents to all leak into
prod before recovery — the destructive op completes too fast to intervene.

---

## Fix: 4 Defense Layers

### Layer 1 — UPSERT via content fingerprint

`reindex.ts` no longer calls `db.exec("DELETE FROM chunks")`. Instead:

1. Snapshot existing chunks: `(source_file, sha256(chunk_text))` -> metadata map.
2. Capture `maxIdBefore = MAX(id)`.
3. For each file, `routeIngest(...)` — new chunks get fresh ids `> maxIdBefore`.
4. For each new chunk, lookup fingerprint in map. If matched: inherit `tier`,
   `access_count`, `importance`, `last_accessed_at` via UPDATE. If not matched:
   keep defaults.
5. Delete only the OLD chunks whose fingerprint did NOT survive (truly removed
   content). Uses prepared `DELETE FROM chunks WHERE id = ?` per-row in a
   transaction — never the naked `db.exec("DELETE FROM chunks")`.

Identity is `(source_file, sha256(chunk_text))` because the `chunks.id` column
is autoincrement and not stable across reindex.

### Layer 2 — withOpAudit snapshot pre-op

Preserved from existing code. `withOpAudit('reindex', async () => {...})` (2-arg, matches prod):
- VACUUM INTO atomic snapshot at `/var/backups/nox-mem/pre-op/reindex-<ts>-<pid>-<uuid>.db`
- ACL 0600, dir 0700.
- Audit row in `ops_audit` with status lifecycle (running -> success/failed/crashed).
- `db_source=main` is recorded inside `notes` of the audit row (not via an options bag) —
  matches the existing 2-arg prod signature. Earlier draft of this runbook referenced a
  3-arg signature that never existed in prod (corrected after 2026-05-24 deploy smoke).
- On `ReindexWipeDetectedError` throw (Layer 4), `withOpAudit` runs the failure path
  and the snapshot is preserved for `safeRestore()`.

### Layer 3 — `--dry-run` mode (expanded)

`nox-mem reindex --dry-run` returns JSON:

```json
{
  "dryRun": true,
  "operation": "reindex",
  "mode": "UPSERT (emergency fix 2026-05-23)",
  "wouldUpsert": { "currentChunks": 69032, "note": "existing chunks preserved by content-fingerprint" },
  "wouldProcess": { "totalFiles": N, "breakdown": {...} },
  "protected": {
    "snapshotPreOp": "YES via withOpAudit",
    "coreTierRetention": "YES",
    "entityRouting": "YES via routeIngest",
    "wipeGuard": "YES via Layer-4 invariant (min ratio 0.9)",
    "upsert": "YES via content-fingerprint match (no DELETE FROM chunks)"
  }
}
```

Does NOT mutate the DB. Verified by canary test #4.

### Layer 4 — Post-reindex invariant (`ReindexWipeDetectedError`)

After all phases complete:

```ts
const ratio = preCount === 0 ? 1 : postCount / preCount;
if (preCount > 0 && ratio < MIN_RETENTION_RATIO && !ALLOW_WIPE) {
  throw new ReindexWipeDetectedError(preCount, postCount, MIN_RETENTION_RATIO);
}
```

- `MIN_RETENTION_RATIO = 0.90` (env-override `NOX_REINDEX_MIN_RETENTION_RATIO`).
- `ALLOW_WIPE` env override `NOX_REINDEX_ALLOW_WIPE=1` ONLY for intentional content removal.
- Throw inside `withOpAudit` -> failure path -> snapshot preserved -> manual `safeRestore()` available.
- Error message includes recovery command path.

Throw-on-detection rationale: refuse to leave the DB in wipe state. Operator must
explicitly opt in to wipe (NOX_REINDEX_ALLOW_WIPE=1) or restore the snapshot.

---

## Canary Test (mandatory CI gate)

`src/__tests__/reindex.no-wipe.test.ts` — 5 tests, ~140ms:

1. **`CANARY: reindex does not wipe chunks (UPSERT contract)`** — seed 1000 fixture chunks, simulate reindex SQL operations, assert final count >= 990 (99% retention on deterministic fixture).
2. **`CANARY: tier/retention_days/section/importance/access_count preserved`** — assert metadata inherited across UPSERT cycle.
3. **`CANARY: ReindexWipeDetectedError thrown when post < 90% of pre`** — instantiate error class, validate fields + message contents.
4. **`CANARY: dryRun returns mode=UPSERT and does NOT mutate`** — source-code grep + DB row-count delta assertion.
5. **`CANARY: source code grep — no naked DELETE FROM chunks outside guarded blocks`** — regex grep enforces that no future PR re-introduces `db.exec("DELETE FROM chunks")`. This is the literal guard against incident class.

**MUST run on every PR touching `src/reindex.ts`, `src/reindex-errors.ts`, or any of its imports.**

CI integration: add to `package.json` test script + GH Actions workflow.

---

## Deployment Runbook (VPS)

### Pre-deploy verification

1. Recovery snapshot intact:
   ```bash
   ssh root@vps "ls -la /root/backups/nox-mem-incident-20260523-2317/ && \
     sqlite3 /root/backups/nox-mem-incident-20260523-2317/nox-mem.db 'SELECT COUNT(*) FROM chunks'"
   # Expected: 69032
   ```

2. Current prod state:
   ```bash
   ssh root@vps "curl -s http://127.0.0.1:18802/api/health | jq '.totalChunks, .vectorCoverage'"
   ```

3. Cron table inspection (find the offending line):
   ```bash
   ssh root@vps "crontab -l | grep -n reindex"
   ```

### Phase A — Stop the bleeding (5 min)

```bash
ssh root@vps
# Snapshot crontab
crontab -l > /root/backups/crontab-$(date -u +%Y%m%dT%H%MZ).txt
# Comment out reindex line (DO NOT delete — easier rollback)
crontab -e
# Prefix the offending line with '# EMERGENCY-DISABLED 2026-05-23'
# Verify:
crontab -l | grep reindex
```

### Phase B — Snapshot current state

```bash
TS=$(date -u +%Y%m%dT%H%MZ)
mkdir -p /root/backups
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "VACUUM INTO '/root/backups/nox-mem-pre-emergency-fix-${TS}.db'"
ls -lh /root/backups/nox-mem-pre-emergency-fix-${TS}.db
```

### Phase C — Build + test on VPS

```bash
cd /root/.openclaw/workspace/tools/nox-mem
git fetch origin
git checkout emergency/reindex-overwrite-fix
# Inspect diff before touching prod:
git diff main..HEAD -- src/reindex.ts
# Build:
npm run build
# Run canary (MUST pass before proceeding):
npm test -- --test-name-pattern='CANARY'
```

If any canary test fails: HALT. Do NOT proceed. Page on-call.

### Phase D — Dry-run on prod DB (READ-ONLY)

```bash
set -a; source /root/.openclaw/.env; set +a
node dist/index.js reindex --dry-run | tee /tmp/reindex-dryrun-${TS}.json
# Verify JSON shows mode="UPSERT" and wipeGuard="YES"
jq '.mode, .protected.wipeGuard' /tmp/reindex-dryrun-${TS}.json
```

### Phase E — Re-enable cron (production cutover)

```bash
crontab -e
# Uncomment the reindex line. Verify timing (production = 23:00 BRT = 02:00 UTC daily).
crontab -l | grep -E "(reindex|EMERGENCY)"
```

### Phase F — Monitor 24h

```bash
# Continuous health watch:
watch -n 60 'curl -s http://127.0.0.1:18802/api/health | \
  jq "{totalChunks, vectorCoverage, opsAudit: {last_op: .opsAudit.last_op, total_24h: .opsAudit.total_24h}}"'

# Schema invariants canary (cron */15min via check-schema-invariants.sh):
ls -la /var/log/nox-mem/schema-invariants.log

# After next scheduled reindex (Sun 23:00 BRT), verify:
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT op_name, status, affected_rows, notes FROM ops_audit \
   WHERE op_name='reindex' ORDER BY id DESC LIMIT 1"
# Expected: status='success', affected_rows ≈ pre-reindex count, no wipe.
```

### Rollback (if canary fires post-deploy)

```bash
# Stop services that write to DB
systemctl stop nox-mem-api nox-mem-watcher openclaw-gateway

# Restore from snapshot (Layer 2 produced this automatically)
node -e "import('./dist/lib/op-audit.js').then(m => m.safeRestore('/var/backups/nox-mem/pre-op/reindex-main-YYYYMMDDTHHMMSS-PID-UUID.db'))"

# Restart
systemctl start nox-mem-api nox-mem-watcher openclaw-gateway

# Disable cron again
crontab -e   # re-comment reindex line
```

### Sign-off checklist

- [ ] Recovery snapshot `atlas` at `/root/backups/nox-mem-incident-20260523-2317/` verified 69032 chunks
- [ ] `nox-mem-pre-emergency-fix-<TS>.db` snapshot created
- [ ] `git checkout emergency/reindex-overwrite-fix` clean
- [ ] `npm run build` no errors
- [ ] All 5 canary tests pass
- [ ] Dry-run JSON shows `mode="UPSERT"` and `wipeGuard="YES"`
- [ ] Cron re-enabled with verified timing
- [ ] First post-deploy reindex run: status=success, affected_rows >= 90% of pre
- [ ] /api/health 24h showing no chunk-count regression
- [ ] PR merged to main only AFTER Sun 2026-05-24 23:00 BRT cron run completes cleanly

---

## NOT modifying production in this PR

Per the emergency protocol: this PR ships:

1. `staged-reindex-emergency/edits/src/reindex.ts` — fixed implementation
2. `staged-reindex-emergency/edits/src/reindex-errors.ts` — error class (test-friendly)
3. `staged-reindex-emergency/edits/src/__tests__/reindex.no-wipe.test.ts` — canary
4. `staged-reindex-emergency/edits/src/db.ts` + `lib/{op-audit,ingest-router}.ts` — stubs for staged-dir build only (DO NOT deploy)
5. `docs/REINDEX-EMERGENCY-FIX-RUNBOOK.md` — this file
6. `audits/2026-05-24-reindex-incident-analysis.md` — root cause writeup

Production cutover is a SEPARATE step performed by Toto or the on-call session
after PR review. The parallel session handling recovery is not blocked by this PR.

---

## References

- Memory `[[incident-2026-05-19-wipe]]` — eval ingest cross-contamination (PR #145)
- Memory `[[reindex-must-route-entity-files]]` — generic ingest drops section/retention
- Memory `[[eod-cron-reindex-was-the-real-trigger]]` — 04-25 root cause
- `audits/2026-04-25-A1-A2-review.md` — A1 snapshot + A2 ingest-router fixes
- `audits/2026-04-26-A1v2-A3-A4-A5-review.md` — 7 highs + cleanup
- `audits/2026-05-21-vec0-reindex-fix-deployed.md` — sqlite-vec lazy load
- CLAUDE.md regra #6 — "Operações destrutivas só com --dry-run ou snapshot atômico"
