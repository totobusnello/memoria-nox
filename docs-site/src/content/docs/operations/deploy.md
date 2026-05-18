---
title: Deploy Guide
description: VPS deploy steps for staged-* patches — Wave B and beyond.
sidebar:
  order: 1
---

Full source: [`docs/DEPLOY-WAVE-B.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/DEPLOY-WAVE-B.md)

## Prerequisites

- SSH access to VPS (Hostinger)
- `.env` sourced: `set -a; source /root/.openclaw/.env; set +a`
- nox-mem stopped or in maintenance mode

:::caution[Source .env first]
Without sourcing `.env`, `vectorize` and `kg-extract` fail silently — last line shows `Done: 0 embedded, N errors`. Always source before any CLI operation.
:::

## Apply a staged patch

Staged patches live in `staged-<sprint>/edits/` in the repo. Each contains modified source files ready to copy over the VPS installation.

```bash
# On VPS, from nox-mem installation directory
INSTALL_DIR=/root/.openclaw/workspace/tools/nox-mem

# 1. Create pre-deploy snapshot
nox-mem reindex --dry-run    # verify state
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# 2. Apply patch files
rsync -av /path/to/staged-P1/edits/src/ $INSTALL_DIR/src/

# 3. Rebuild
cd $INSTALL_DIR && npm run build

# 4. Verify
curl http://127.0.0.1:18802/api/health | jq .
nox-mem stats
```

## Post-deploy validation

```bash
# Vector coverage should be ≈ 1.0
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# Schema invariants (should pass 4/4)
bash /root/scripts/check-schema-invariants.sh

# Semantic canary smoke test
nox-mem search "salience formula" | head -5
```

## Rollback

If the deploy breaks something, use the op-audit snapshot:

```bash
# List available snapshots
ls -lt /var/backups/nox-mem/pre-op/

# Restore via safeRestore() (validates user_version + removes stale WAL/SHM)
nox-mem restore --snapshot /var/backups/nox-mem/pre-op/<snapshot>.db
```

**Never** `cp snapshot.db nox-mem.db` directly — stale WAL files will corrupt the database.

See [Disaster Recovery](/memoria-nox/operations/disaster-recovery) for full procedures.

## Cron schedule

| Time (BRT) | Job |
|---|---|
| 23:00 | reindex → consolidate → vectorize → kg-build → kg-prune → session-distill |
| */30min | Semantic canary smoke test → Discord alert |
| */15min | Schema invariants check → Discord alert |
| */5min | `/api/health` probe |
| 02:00 | Full DB backup |

:::note
The nightly cron uses `consolidate` (not bare `reindex`) since 2026-04-25 patch, to avoid wiping `section`/`retention` on entity chunks.
:::
