# Audit — nox-mem-watch 2 errors investigation (2026-05-31)

**Trigger:** Openclaw monitoring reported 2 errors from `nox-mem-watch` in 12h, surfaced 2026-05-30 14:07 BRT.
**Investigation date:** 2026-05-31 (post-incident audit).
**VPS:** 187.77.234.79 (srv1465941).
**Service:** `nox-mem-watch.service` → `nox-mem-watch.sh` → `inotifywait` → `nox-mem ingest`.

---

## Timeline of the 2 errors

Both errors **PRE-DATE** the vec0 fix and the watch-script `NOX_ALLOW_PROD_INGEST=1` patch (deployed 13:44 BRT). They are NOT vec0-related and NOT post-fix regressions.

### Error #1 — 2026-05-30 07:07:48 BRT

```
nox-mem-watcher[1545491]: [db] ABORT: Large-DB ingest guard triggered on operation 'ingest'.
  DB path:     /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  Chunk count: 69135 (threshold: 10000)
  This DB appears to be the production nox-mem.db.
  If you intend to ingest into production, set:
    NOX_ALLOW_PROD_INGEST=1 nox-mem ingest ...
```

### Error #2 — 2026-05-30 12:47:39 BRT

```
nox-mem-watcher[1601313]: [db] ABORT: Large-DB ingest guard triggered on operation 'ingest'.
  DB path:     /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  Chunk count: 69135 (threshold: 10000)
  …
```

### Watcher restart sequence (fix deployment)

- **13:44:59 BRT** — service stopped/started (first attempt; script patched in place but Toto restarted to pick up patched version)
- **13:53:15 BRT** — service stopped/started (final restart, current PID 1666474)
- **Backup file:** `nox-mem-watch.sh.bak-pre-allow-prod-20260530-134459` (timestamp confirms patch ~13:44 BRT)

### First successful ingest post-fix

- **2026-05-31 07:06:33 BRT** — `nox-mem-watcher[2051117]: [INFO] Ingested /root/.openclaw/workspace/memory/obra-bvv-log.md: 15 chunks`

---

## Error class

**`guard`** — Large-DB ingest guard (postmortem 2026-05-19 wipe incident).

Code: `src/db.ts` → `checkLargeDbIngestGuard()`:

```typescript
const PROD_CHUNK_THRESHOLD = 10_000;
if (process.env.NOX_ALLOW_PROD_INGEST === "1") return;
// ... aborts with process.exit(1) if chunks > 10k
```

**Not vec0.** Not sqlite. Not transient retry.

---

## Root cause

The watch script `nox-mem-watch.sh` was missing `NOX_ALLOW_PROD_INGEST=1` on the ingest invocation. When `inotifywait` detected modifications to `.md`/`.json` files under `/root/.openclaw/workspace/{memory,shared}` and tried to ingest into the 69,135-chunk production DB, the guard correctly aborted.

### Diff of the fix (deployed 13:44 BRT 2026-05-30)

```diff
< /usr/local/bin/nox-mem ingest "$file" 2>&1 | logger -t nox-mem-watcher
> NOX_ALLOW_PROD_INGEST=1 /usr/local/bin/nox-mem ingest "$file" 2>&1 | logger -t nox-mem-watcher
```

The guard was introduced after the 2026-05-19 incident (eval ingest crossed into main DB, ~5828 chunks lost, 50min RTO). The watch script was never updated to explicitly opt-in for the prod-ingest path. Symptom remained dormant until two file modifications happened during the day on 2026-05-30 (07:07 and 12:47 BRT) and triggered the abort.

---

## Severity assessment

**Real failure**, NOT transient retry. But **low severity**:

| Dimension | Assessment |
|---|---|
| Data loss | **None.** Guard fired before any write — DB integrity intact (69,130 chunks today, ~unchanged). |
| Service health | **OK.** Watcher process running 19h continuous since 13:53 BRT restart. Heartbeat fresh (2026-05-31 07:06:40 BRT). |
| Vector coverage | **99.98%.** 69,115 / 69,130 embedded (15 chunks lag, normal). |
| API health | **OK.** `/api/health` responsive. |
| User-facing impact | **Two files failed to auto-index** between modification and 13:44 BRT fix. Re-touching those files would now ingest correctly. |
| Vec0 fix status | **Confirmed deployed.** `src/db.ts` + `dist/db.js` both have `sqlite-vec-linux-x64/vec0` loadExtension at module init. API loads it; the standalone `sqlite3` CLI does NOT (expected — CLI doesn't auto-load extensions). |

The `sqlite3` CLI's `Error: no such module: vec0` when run by hand is **not** a bug — it just means the CLI binary doesn't preload extensions. The nox-mem Node process does load it, evidenced by the 99.98% vector coverage and zero orphans.

---

## Recommendation

**Monitor only.** No further action required. The fix is in place and validated.

### Suggested follow-ups (optional, not blocking)

1. **(P3) Document the watcher contract.** The watch script is one of two known callers that legitimately ingest into prod (the other is manual CLI ops). Add a comment in `nox-mem-watch.sh` explaining why `NOX_ALLOW_PROD_INGEST=1` is required there and that removing it will trigger the postmortem-2026-05-19 guard.
2. **(P3) Add the watcher to monitored services in openclaw healthcheck.** Already partially covered via heartbeat file `/tmp/nox-mem-watcher-heartbeat` — confirm `staleness > 1h` alert is wired.
3. **(P4) Consider lowering noise level of guard message in production paths.** Current message is 10 lines per abort; could be condensed to one-liner when invoked from automation paths. Cosmetic only.
4. **(P4) No-op:** the two failed ingests (07:07 + 12:47 BRT 2026-05-30) — verify the source files were eventually re-indexed by another touch or daily sweep. If important enough, run a one-shot reingest of any files modified between 00:00 and 13:44 BRT on 2026-05-30.

---

## Evidence pointers

- **Guard code:** `/root/.openclaw/workspace/tools/nox-mem/src/db.ts` (`checkLargeDbIngestGuard`)
- **Watch script:** `/root/.openclaw/workspace/tools/nox-mem/nox-mem-watch.sh`
- **Backup pre-fix:** `/root/.openclaw/workspace/tools/nox-mem/nox-mem-watch.sh.bak-pre-allow-prod-20260530-134459`
- **Service unit:** `/etc/systemd/system/nox-mem-watch.service`
- **Vec0 fix (src):** `src/db.ts:` `loadExtension(VEC0_PATH)` block
- **Vec0 fix (dist):** `dist/db.js:` same block
- **Related lesson:** `[[eval-harness-must-explicit-isolate-db]]` + `[[reindex-bypasses-openclaw-workspace-hits-main]]`
- **Related incident:** `docs/INCIDENTS.md#2026-05-19` (the wipe that motivated the guard)
