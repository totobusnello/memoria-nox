# nox-mem DB Audit Deepening — 2026-04-18

Evidence collected read-only from VPS `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` and `src/db.ts`.

## Gap 1 — vec_chunk_map: 100% orphan CONFIRMED (worse than reported)

Measured on VPS:

| metric | value |
|---|---|
| vec_chunk_map rows | **6,627** |
| rows whose chunk_id exists in chunks | **0** |
| orphan rows | **6,627** (100%) |
| chunks total | **1,951** |
| chunks WITHOUT any vec_chunk_map row | **1,951** (100%) |
| MAX(chunks.id) | 62,897 |
| MIN/MAX(vec_chunk_map.chunk_id) | 17,114 / 45,435 |
| MAX(vec_chunk_map.vec_rowid) | 14,458 |

Implication: semantic layer is fully dead. Every `[hybrid]` result is pure BM25 + RRF with one empty input. `vec_chunks` (vec0 virtual) could not be opened from the system sqlite3 CLI (`no such module: vec0`) — expected, loaded via `loadVecSafe()` at runtime only.

### Remediation SQL (Gap 1)

```sql
-- 0. Safety snapshot
.backup '/root/.openclaw/workspace/tools/nox-mem/backups/pre-vec-cleanup-2026-04-18.db'

-- 1. Wipe orphan map AND matching vec0 rows in one txn
BEGIN IMMEDIATE;
CREATE TEMP TABLE _to_drop AS
  SELECT vec_rowid FROM vec_chunk_map
  WHERE chunk_id NOT IN (SELECT id FROM chunks);

DELETE FROM vec_chunks    WHERE rowid IN (SELECT vec_rowid FROM _to_drop);
DELETE FROM vec_chunk_map WHERE vec_rowid IN (SELECT vec_rowid FROM _to_drop);
DROP TABLE _to_drop;
COMMIT;

-- 2. Prevent recurrence (SQLite FKs on virtual tables are fragile, so use a trigger)
CREATE TRIGGER IF NOT EXISTS trg_chunks_ad_vec
AFTER DELETE ON chunks
BEGIN
  DELETE FROM vec_chunks
    WHERE rowid IN (SELECT vec_rowid FROM vec_chunk_map WHERE chunk_id = OLD.id);
  DELETE FROM vec_chunk_map WHERE chunk_id = OLD.id;
END;

-- 3. Verify
SELECT COUNT(*) AS should_be_zero
  FROM vec_chunk_map WHERE chunk_id NOT IN (SELECT id FROM chunks);
```

Rollback: `.restore` the pre-cleanup backup, then `DROP TRIGGER trg_chunks_ad_vec`.

### Re-vectorize roadmap
- Chunks needing embeddings: **1,951**.
- Model: `gemini-embedding-001` at 3072d.
- Est. cost: Gemini embeddings are billed per input token. Avg chunk ~500 tokens => ~975K tokens. At current `gemini-embedding-001` price (~$0.15 / 1M input tokens) => **~$0.15 one-shot**. Throughput ~60 req/min on free tier; full re-embed ~35–40 min. Run `node dist/cli.js vectorize --all` inside the normal Sunday 04:00 slot (currently unused after cron consolidation) to avoid collision.

## Gap 3 — busy_timeout = 0 CONFIRMED

`src/db.ts` `getDb()` sets `journal_mode`, `foreign_keys`, `cache_size`, `mmap_size`, `synchronous` — **no `busy_timeout`**. Default is 0 => any writer contending with checkpoint / watcher / API returns `SQLITE_BUSY` immediately.

### Fix (exact patch, line 17 area)

In `/root/.openclaw/workspace/tools/nox-mem/src/db.ts`, inside `getDb()` after `_db.pragma("journal_mode = WAL");`:

```ts
  _db.pragma("busy_timeout = 5000");       // wait up to 5s for locks
  _db.pragma("wal_autocheckpoint = 1000"); // keep WAL small (default 1000 pages, re-affirm)
```

Verify: `sqlite3 ... "PRAGMA busy_timeout;"` returns `5000` after service restart.
Rollback: remove the two lines; restart `nox-mem-api` + `nox-mem-watcher`.

## Gap 4 — Missing composite index

Hot queries observed in `src/search.ts` / digest:

1. `SELECT * FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT 20` — FTS5 `rank` is internal; no index helps, OK.
2. Type-scoped recency: `WHERE chunk_type=? ORDER BY created_at DESC LIMIT N` — currently forces TEMP B-TREE.
3. KG path walker joins `kg_relations(source_id, target_id)`.

### Indexes (idempotent)

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_type_created
  ON chunks(chunk_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_kg_rel_source ON kg_relations(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_target ON kg_relations(target_id, source_id);

ANALYZE;
```

Verify with `EXPLAIN QUERY PLAN SELECT ... WHERE chunk_type='decision' ORDER BY created_at DESC LIMIT 20;` — expect `USING INDEX idx_chunks_type_created`, no `USE TEMP B-TREE FOR ORDER BY`.
Rollback: `DROP INDEX idx_chunks_type_created; DROP INDEX idx_kg_rel_source; DROP INDEX idx_kg_rel_target;`

## Concurrency / collisions

Current live crontab is **not** the 29-entry list in CLAUDE.md. It has been consolidated:

```
*/5  *  *  *  *   health-probe.sh
*/10 *  *  *  *   gateway-drift-check.sh
*/30 *  *  *  *   config-drift-monitor.sh
0    2  *  *  *   backup-all.sh
0    23 *  *  *   nightly-maintenance.sh   # runs reindex → consolidate → kg → vectorize sequentially
0    */4 * *  *   token-refresh-max.sh
0    6  *  *  *   sync-verify.sh
```

Implications:
- Heavy writers (reindex/consolidate/kg/vectorize) are now **serial inside nightly-maintenance.sh** — good. Previous collision model in CLAUDE.md is stale.
- Remaining race: `nightly-maintenance.sh` (23:00) vs `backup-all.sh` (02:00) — non-overlapping, safe.
- Live races: `nox-mem-watcher` ingest + API writes + user CLI. With `busy_timeout=0` these still storm; Gap 3 fix resolves.
- `sync-verify.sh` at 06:00 can write if it reindexes — verify; if so, it must acquire `busy_timeout`.

CLAUDE.md "29 cron entries" section is out of date and should be updated after this audit lands.

## Action checklist (apply in order)

1. Patch `src/db.ts` (Gap 3), rebuild, restart `nox-mem-api` + `nox-mem-watcher`.
2. Apply indexes (Gap 4) — zero-downtime, online.
3. Snapshot DB, run Gap 1 cleanup SQL, install trigger.
4. Run `node dist/cli.js vectorize --all` to repopulate 1,951 embeddings.
5. Post-check: `SELECT COUNT(*) FROM vec_chunk_map` should equal chunks count; orphan count 0.
6. Update CLAUDE.md cron section to reflect consolidated schedule.
