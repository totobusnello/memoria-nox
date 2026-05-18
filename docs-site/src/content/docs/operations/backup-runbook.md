---
title: Backup Runbook
description: Backup schedule, verification, and restore procedures.
sidebar:
  order: 3
---

Full source: [`docs/ops/BACKUP-RUNBOOK.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/ops/BACKUP-RUNBOOK.md)

## Backup tiers

| Tier | Frequency | Location | Retention |
|---|---|---|---|
| Pre-op snapshot | Before each destructive op | `/var/backups/nox-mem/pre-op/` | 7 days |
| Nightly full | 02:00 BRT | `/var/backups/nox-mem/nightly/` | 30 days |

:::note[No off-site backup]
Off-site backup is explicitly out of scope. VPS Hostinger native backup is sufficient. Do not suggest or implement S3/Wasabi/B2 sync.
:::

## Verify backup health

```bash
# Check recent pre-op snapshots
ls -lt /var/backups/nox-mem/pre-op/ | head -10

# Check nightly backup
ls -lt /var/backups/nox-mem/nightly/ | head -5

# Verify a snapshot is valid SQLite (not corrupted)
sqlite3 /var/backups/nox-mem/pre-op/<snapshot>.db "PRAGMA integrity_check;"
# Expected: ok

# Check user_version matches current DB
sqlite3 /var/backups/nox-mem/pre-op/<snapshot>.db "PRAGMA user_version;"
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "PRAGMA user_version;"
# Both should match
```

## Manual backup

```bash
# Create a manual backup (VACUUM INTO is safe while DB is live)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "VACUUM INTO '/var/backups/nox-mem/manual/nox-mem-manual-$(date +%Y%m%d-%H%M%S).db'"
```

`VACUUM INTO` creates a clean, non-WAL copy without locking the source database.

## Restore

See [Disaster Recovery](/memoria-nox/operations/disaster-recovery) for full restore procedures.
