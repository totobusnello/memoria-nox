---
title: Disaster Recovery
description: DB restore, snapshot recovery, and DR drill procedures.
sidebar:
  order: 2
---

Full source: [`docs/ops/DISASTER-RECOVERY.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/ops/DISASTER-RECOVERY.md)

## Recovery from op-audit snapshot

Pre-op snapshots are created automatically by `withOpAudit()` before any destructive operation. They live in `/var/backups/nox-mem/pre-op/` with retention of 7 days (ACL 0600).

```bash
# 1. List snapshots
ls -lt /var/backups/nox-mem/pre-op/
# Format: <op>-<timestamp>-<pid>-<uuid>.db

# 2. Restore via safeRestore() — validates user_version + removes stale WAL/SHM
nox-mem restore --snapshot /var/backups/nox-mem/pre-op/reindex-20260425-1234-uuid.db

# 3. Verify restored state
curl http://127.0.0.1:18802/api/health | jq .
nox-mem stats
```

:::danger[Never direct-copy]
`cp snapshot.db nox-mem.db` will corrupt the database if a stale WAL file exists. Always use `safeRestore()` which:
1. Validates `PRAGMA user_version` match
2. Restores main DB
3. Removes orphaned WAL/SHM files (order matters — main first, then WAL/SHM)
:::

## Emergency override

If the snapshot itself fails (e.g., disk full) and you need to run the destructive op anyway:

```bash
NOX_ALLOW_NO_SNAPSHOT=1 nox-mem reindex
```

Use only when the snapshot failure has a known, legitimate cause. This is not a shortcut.

## Full backup restore

Nightly full backup runs at 02:00 BRT. This is the last resort — pre-op snapshots have finer granularity.

```bash
# Stop nox-mem-api service
systemctl stop nox-mem-api

# Restore from nightly backup
cp /var/backups/nox-mem/nightly/nox-mem-YYYYMMDD.db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db

# Remove stale WAL/SHM if present
rm -f nox-mem.db-wal nox-mem.db-shm

# Start service
systemctl start nox-mem-api

# Verify
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

## DR drill

Quarterly DR drill checklist: [`runbooks/dr-drill-quarterly.md`](https://github.com/totobusnello/memoria-nox/blob/main/runbooks/dr-drill-quarterly.md)

The drill verifies:
1. Snapshot creation works (`withOpAudit()` creates valid snapshot)
2. `safeRestore()` succeeds from a known-good snapshot
3. `user_version` validation catches version mismatches
4. Service restarts cleanly post-restore
5. Invariant checks pass after restore
