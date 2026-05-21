# Wave A — opsAudit Hygiene Deployment Guide

> **What this does**: fixes Issues #1 (`started_at` type chaos) + #3 (test ops + db_source NULL pollute /api/health metrics) from `audits/2026-05-21-opsAudit-investigation.md`. Two code patches + one schema constraint + two one-time data migrations.

> **Do not deploy without snapshots.** The data migrations are wrapped in `withOpAudit` which creates atomic snapshots, but the order matters (deploy code first, then run migrations, then restart API).

---

## Files

| Source (in this repo)                       | VPS destination                                                  |
|---------------------------------------------|------------------------------------------------------------------|
| `staged-1.7a/edits/op-audit.ts`             | `/root/.openclaw/workspace/tools/nox-mem/src/lib/op-audit.ts`    |
| `scripts/migrate-opsaudit-started-at-2026-05-21.sh` | `/root/.openclaw/workspace/tools/nox-mem/scripts/`        |
| `scripts/cleanup-test-ops-audit-2026-05-21.sh`      | `/root/.openclaw/workspace/tools/nox-mem/scripts/`        |

### Code changes in `op-audit.ts`

1. **`ensureAuditTable()` — Issue #1C**: adds `BEFORE INSERT`/`BEFORE UPDATE OF started_at` triggers that abort if `typeof(started_at) != 'integer'`. Prevents regression to TEXT formats.
2. **`getOpAuditStats()` — Issue #1B + #3A**: wraps `started_at` comparisons in `CAST(... AS INTEGER)` and adds `op_name NOT LIKE 'test-%'` filter to all 24h-window queries.
3. **`reapZombies()` — Issue #1B**: same defensive CAST for the running-row threshold check.

No new exports, no signature changes — drop-in replacement.

---

## Pre-flight (on the VPS)

```bash
ssh root@187.77.234.79
cd /root/.openclaw/workspace/tools/nox-mem

# 1. Load env (sqlite3, Gemini, snapshot dir validation).
set -a; source /root/.openclaw/.env; set +a

# 2. Capture baseline state for the audit file.
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit | {total_24h, success_24h, failed_24h, crashed_24h, byDbSource}'

sqlite3 nox-mem.db "SELECT typeof(started_at), COUNT(*) FROM ops_audit GROUP BY 1"
sqlite3 nox-mem.db "SELECT op_name, status, COUNT(*) FROM ops_audit WHERE op_name LIKE 'test-%' GROUP BY 1,2"

# 3. Sanity-check snapshot dir + free space.
ls -lh /var/backups/nox-mem/pre-op/ | tail -3
df -h /var/backups/nox-mem
```

---

## Deploy

```bash
# From laptop, in the worktree:
WORKTREE=/Users/lab/Claude/Projetos/memoria-nox/.claude/worktrees/agent-ac2417bd98be581cf
VPS=/root/.openclaw/workspace/tools/nox-mem

# 1. Push files.
scp "$WORKTREE/staged-1.7a/edits/op-audit.ts" \
    root@187.77.234.79:$VPS/src/lib/op-audit.ts
scp "$WORKTREE/scripts/migrate-opsaudit-started-at-2026-05-21.sh" \
    root@187.77.234.79:$VPS/scripts/
scp "$WORKTREE/scripts/cleanup-test-ops-audit-2026-05-21.sh" \
    root@187.77.234.79:$VPS/scripts/

# 2. Build + verify CAST present in compiled output.
ssh root@187.77.234.79 << 'EOF'
cd /root/.openclaw/workspace/tools/nox-mem
npx tsc -p tsconfig.json 2>&1 | tail
grep -c "CAST(started_at AS INTEGER)" dist/lib/op-audit.js
grep -c "NOT LIKE 'test-%'" dist/lib/op-audit.js
grep -c "trg_ops_audit_started_at_must_be_int" dist/lib/op-audit.js
EOF

# Expected: ≥6 CAST, ≥6 NOT LIKE, ≥2 trigger refs.
```

---

## Run migrations (order matters)

```bash
ssh root@187.77.234.79
cd /root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a
chmod +x scripts/migrate-opsaudit-started-at-2026-05-21.sh scripts/cleanup-test-ops-audit-2026-05-21.sh

# Step A — normalize started_at TEXT → INTEGER (rebuilds in transaction, terminal trigger toggled).
bash scripts/migrate-opsaudit-started-at-2026-05-21.sh

# Step B — remove historical test-% rows (toggles no-delete trigger).
bash scripts/cleanup-test-ops-audit-2026-05-21.sh

# Step C — restart API to load new code + install new INT-check trigger.
systemctl restart nox-mem-api
sleep 3

# Step D — verify trigger installed.
sqlite3 nox-mem.db "SELECT name FROM sqlite_master WHERE name LIKE 'trg_ops_audit_%' ORDER BY 1"
# Expected: trg_ops_audit_no_delete, trg_ops_audit_started_at_must_be_int,
#           trg_ops_audit_started_at_must_be_int_upd, trg_ops_audit_terminal_immutable
```

---

## Validation

```bash
# 1. typeof distribution — all INTEGER.
sqlite3 nox-mem.db "SELECT typeof(started_at), COUNT(*) FROM ops_audit GROUP BY 1"
# Expected: integer | <N>

# 2. No test-% rows.
sqlite3 nox-mem.db "SELECT COUNT(*) FROM ops_audit WHERE op_name LIKE 'test-%'"
# Expected: 0

# 3. /api/health.opsAudit shows realistic 24h count.
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit'
# Expected: total_24h << 48; byDbSource no longer dominated by 'unknown' test pollution.

# 4. Trigger blocks bad inserts (sanity).
sqlite3 nox-mem.db "INSERT INTO ops_audit (op_name, started_at, status) VALUES ('test-trigger', 'bad-text', 'running')"
# Expected: Error: ops_audit.started_at must be INTEGER epoch ms — got non-integer value
```

---

## Recovery

If migration fails mid-transaction, SQLite ROLLBACK restores everything. If the new code is broken post-restart, both scripts wrote snapshots to `/var/backups/nox-mem/pre-op/`:

```bash
ssh root@187.77.234.79
cd /root/.openclaw/workspace/tools/nox-mem
ls -lt /var/backups/nox-mem/pre-op/ | head -5

# Restore using safeRestore (validates user_version + cleans WAL/SHM).
systemctl stop nox-mem-api nox-mem-watcher
node -e "import('./dist/lib/op-audit.js').then(m => m.safeRestore('/var/backups/nox-mem/pre-op/<migrate-...>.db'))"
systemctl start nox-mem-api nox-mem-watcher
```

---

## Rollback (code-only)

If only the new triggers misbehave, just revert the code and restart — historical data is preserved by the migration (one-way safe):

```bash
ssh root@187.77.234.79
cd /root/.openclaw/workspace/tools/nox-mem
git checkout HEAD~1 -- src/lib/op-audit.ts  # or restore prior copy
npx tsc -p tsconfig.json
systemctl restart nox-mem-api
# Then manually drop the new triggers:
sqlite3 nox-mem.db "DROP TRIGGER IF EXISTS trg_ops_audit_started_at_must_be_int; DROP TRIGGER IF EXISTS trg_ops_audit_started_at_must_be_int_upd;"
```

---

## Issue #3B deferred

The audit recommended making `db_source` an explicit required param in `withOpAudit` signature. **Not done in this wave** — it's a refactor touching all callers and the reporting filter (Issue #3A) handles the immediate metric noise. Park for a future op-audit signature pass.

---

## Lessons cravadas durante o deploy 2026-05-21

1. **`vec0` extension required for any sqlite3 CLI session against `nox-mem.db`** — `trg_chunks_delete_cascade` references `vec0` module functions; SQLite parses ALL triggers when handling schema-touching operations (DROP TABLE, ALTER TABLE, even some SELECTs when schema-rebuild is forced). Without `.load <vec0.so>` the CLI errors out before transaction even starts.

2. **TEXT column affinity coerces INTEGER bound values to TEXT** — even `INSERT INTO t(text_col) VALUES (CAST(? AS INTEGER))` lands as TEXT in the column, and SQLite triggers see the post-affinity value. A simple `UPDATE` migration is therefore impossible for typeof checks; full table rebuild (CREATE NEW + COPY + DROP + RENAME) is the only path to an INTEGER-typed column.

3. **`sqlite3` CLI defaults `.bail off`** — it continues past failures. A partial transaction can leave `_new` tables around with rows but no rename; first migration attempt left `ops_audit_new` populated but ops_audit dropped. Always `.bail on` in destructive migrations.

4. **better-sqlite3 binds JS `number` as REAL, not INTEGER** — even safe integers. The historical `"1779242511707.0"` rows in prod are literal evidence (`.0` suffix = REAL storage in TEXT-affinity column). Solution: wrap parameter in `CAST(? AS INTEGER)` server-side inside the INSERT SQL, which evaluates BEFORE column affinity rules apply.
