# A2 Tier 3 — Plaintext-to-Encrypted Migration Runbook

> **Status:** ready for prod (validated 2026-05-23 against synthetic + smoke fixtures, 19/19 P2 tests + 11/11 P1 tests pass)
>
> **Audience:** operator running the migration on the production VPS `nox-mem.db` (~62.9k chunks).
>
> **Risk class:** destructive on `--swap`. Read every section before invoking.
>
> **Time-box estimate:** 15–30 min on prod (5 min migration + 10 min validation + 10 min restart cycle). Plus ~6h roll-forward window for shadow plaintext fallback.

---

## TL;DR

```bash
# 1. Pre-flight (read § Pre-flight below first)
# 2. Migration (NON-destructive: source DB untouched)
NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key) \
  node /root/.openclaw/workspace/tools/nox-mem/dist/scripts/migrate-encrypt-db.js \
       /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
       /root/.openclaw/workspace/tools/nox-mem/nox-mem.encrypted.db \
       "$NOX_DB_KEY"

# 3. Validate (§ Post-migration validation)

# 4. Atomic swap (destructive on source, creates backup):
node /root/.openclaw/workspace/tools/nox-mem/dist/scripts/migrate-encrypt-db.js \
     /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
     /root/.openclaw/workspace/tools/nox-mem/nox-mem.encrypted.db \
     "$NOX_DB_KEY" --swap

# 5. Update systemd unit env: NOX_DB_KEY=... NOX_DB_REQUIRE_KEY=1

# 6. Restart nox-mem-api + run smoke checks
```

---

## Pre-flight checklist

Run **before** any migration step. Each item is gating — stop on failure.

### 1. Disk space

```bash
df -h /root/.openclaw/workspace/tools/nox-mem
ls -lh /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
```

The encrypted DB will be **the same size or slightly larger** (cipher headers + reserved space; expect ≤ +10%). The temporary backup adds another 1× during swap.

**Minimum free space required:** `2.2 × size(nox-mem.db)`. For current 62.9k-chunk prod DB at ~51 MB → need ≥ 115 MB free. Hostinger VPS typically has plenty; this is a guard not a constraint.

### 2. Cipher key generated and stored

```bash
# Generate (do this ONCE, store securely; do NOT regenerate without re-migration)
openssl rand -base64 48 > /root/.openclaw/secrets/nox-mem-cipher.key
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.key
chown root:root /root/.openclaw/secrets/nox-mem-cipher.key

# Verify
stat -c '%a %U:%G %s' /root/.openclaw/secrets/nox-mem-cipher.key
# Expect: 400 root:root 65
```

**HARD RULE:** the key file MUST be mode `0400`, owned by `root`. World-readable = key compromise = full DB compromise post-migration. The migration script does **not** read the key file; the operator passes it via environment to the CLI.

**Key recovery:** if the key file is lost, the encrypted DB is **unrecoverable** (no rekey, no master key, no recovery codes — that's the point). The `.pre-encrypt-<ts>.db` backup (created by `--swap`) is the only rollback path.

### 3. op-audit clean

The migration is itself a destructive op. We do **not** route it through `withOpAudit` because the migration touches a different DB (the new encrypted one); the audit table would need to be initialized post-migration. Instead, the script's own `.pre-encrypt-<ts>.db` backup serves as the snapshot.

Before starting, confirm no other destructive op is in flight:

```bash
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit'
```

Look for `running` rows. If any, wait for them to terminate (`success` / `failed` / `crashed`). Migration during a concurrent reindex risks data drift between source-read and copy.

### 4. Active connections

```bash
# Identify processes holding nox-mem.db open
lsof | grep nox-mem.db
```

For migration WITHOUT `--swap`: open connections are tolerable (we read source plaintext, write a separate file).

For `--swap`: **stop nox-mem-api first** to release the file handle. The migration itself does not require shutdown — but the swap step uses `rename(2)`, which on Linux succeeds even with open handles (but leaves zombie inodes). On macOS dev boxes the swap may fail outright if the file is open.

```bash
# Production swap procedure (paranoid path):
systemctl stop nox-mem-api
node .../migrate-encrypt-db.js <src> <dst> "$KEY" --swap
# update env in /etc/systemd/system/nox-mem-api.service.d/override.conf
systemctl daemon-reload
systemctl start nox-mem-api
```

### 5. Recent backup exists

```bash
ls -lht /var/backups/nox-mem/ | head -5
```

The nightly `backup-all.sh` cron (02:00 BRT) writes here. If the most recent backup is >24h old, **abort and investigate** before migrating — you want a known-good restore point that is *not* the script's own `.pre-encrypt-<ts>.db` artifact.

### 6. Schema invariants

```bash
/root/.openclaw/workspace/tools/nox-mem/scripts/check-schema-invariants.sh
```

Must return all 4 invariants OK. If any fail, fix them first (the migration will faithfully copy any pre-existing schema rot).

---

## Migration sequence (the actual procedure)

### Step 1 — Build the script

The migration script lives in `staged-A2-T3/scripts/migrate-encrypt-db.ts` and ships compiled JS at `dist/scripts/migrate-encrypt-db.js`. Toto's manual integration step moves it to `src/scripts/` in the prod tree.

```bash
cd /root/.openclaw/workspace/tools/nox-mem
# After SCP from staged-A2-T3/:
npm install better-sqlite3-multiple-ciphers@^11.10
npm run build  # if your tsconfig already includes scripts/
```

### Step 2 — Dry-run migration (non-destructive)

```bash
export NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)

node dist/scripts/migrate-encrypt-db.js \
     ./nox-mem.db \
     ./nox-mem.encrypted.db \
     "$NOX_DB_KEY"
```

**Expected output:**

```
[migrate] verifying source is plaintext: ./nox-mem.db
[migrate] opening encrypted destination: ./nox-mem.encrypted.db
[migrate] attaching source (plaintext) for streaming copy
[migrate] schema: <N> items, virtual=<V>, vec0=<C>
[migrate]   chunks: 62853 → 62853 OK
[migrate]   kg_entities: 402 → 402 OK
[migrate]   kg_relations: 544 → 544 OK
[migrate]   ...
[migrate]   FTS rebuild: chunks_fts OK
[migrate] validating destination by reopen-with-key
[migrate] SUCCESS — <N> tables, <bytes> bytes, <ms> ms
```

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Migration + validation OK |
| 1 | Source already encrypted (or pre-flight failed) |
| 2 | Dest path already exists — refusing overwrite |
| 3 | Row counts diverged — DO NOT swap, investigate |
| 4 | Usage / argument error |

Anything other than 0 → stop and investigate. Do not proceed to `--swap`.

### Step 3 — Manual validation pass

Before swapping, manually validate the encrypted DB:

```bash
# A) Open with key and count chunks
sqlite3 ./nox-mem.encrypted.db <<EOF
.load sqlcipher  -- only if you installed sqlcipher CLI
PRAGMA cipher_compatibility=4;
PRAGMA key='$NOX_DB_KEY';
SELECT count(*) FROM chunks;
EOF
# Or via node:
node -e "
const Database = require('better-sqlite3-multiple-ciphers');
const db = new Database('./nox-mem.encrypted.db');
db.pragma(\"cipher='sqlcipher'\");
db.pragma(\"cipher_compatibility=4\");
db.pragma(\"key='\${process.env.NOX_DB_KEY}'\");
console.log('chunks:', db.prepare('SELECT count(*) AS n FROM chunks').get().n);
console.log('kg_entities:', db.prepare('SELECT count(*) AS n FROM kg_entities').get().n);
console.log('FTS sample:', db.prepare(\"SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'nox'\").get().n);
"
```

**Match against source:**

```bash
sqlite3 ./nox-mem.db <<EOF
SELECT 'chunks',       count(*) FROM chunks;
SELECT 'kg_entities',  count(*) FROM kg_entities;
SELECT 'kg_relations', count(*) FROM kg_relations;
SELECT 'FTS nox',      count(*) FROM chunks_fts WHERE chunks_fts MATCH 'nox';
EOF
```

Numbers MUST match exactly. The script's own validation only checks insert/reopen counts; this manual check additionally confirms FTS rebuild parity.

### Step 4 — Atomic swap

If Step 3 numbers match:

```bash
systemctl stop nox-mem-api  # paranoid, see § Pre-flight #4
node dist/scripts/migrate-encrypt-db.js \
     ./nox-mem.db \
     ./nox-mem.encrypted.db \
     "$NOX_DB_KEY" --swap
```

The `--swap` mode performs:

1. `mv nox-mem.db → nox-mem.db.pre-encrypt-<ISO-ts>.db`
2. `mv nox-mem.encrypted.db → nox-mem.db`

Result: the canonical path `nox-mem.db` now contains the **encrypted** DB; the pre-swap plaintext is preserved as `nox-mem.db.pre-encrypt-<ts>.db` (retain ≥ 7 days; see § Rollback).

### Step 5 — Update systemd env

Edit `/etc/systemd/system/nox-mem-api.service.d/override.conf`:

```ini
[Service]
Environment="NOX_DB_KEY=<paste-key-here-OR-Environmentfile=/root/.openclaw/secrets/nox-mem-cipher.env>"
Environment="NOX_DB_REQUIRE_KEY=1"
```

Prefer `EnvironmentFile=` so the key is not visible in `systemctl show`:

```bash
echo "NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)" \
     > /root/.openclaw/secrets/nox-mem-cipher.env
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.env
```

Then in the unit:

```ini
[Service]
EnvironmentFile=/root/.openclaw/secrets/nox-mem-cipher.env
Environment="NOX_DB_REQUIRE_KEY=1"
```

Reload + restart:

```bash
systemctl daemon-reload
systemctl start nox-mem-api
```

### Step 6 — Smoke checks (mandatory)

Run all of these and confirm green before walking away:

```bash
# A) Health endpoint responds + reports encrypted-mode active
curl -s http://127.0.0.1:18802/api/health | jq '{
  ok,
  totalChunks: .totalChunks,
  vectorCoverage: .vectorCoverage,
  isEncrypted: .isEncrypted
}'

# Expect: ok=true, isEncrypted=true (if the P1 health-endpoint surface includes isDbEncrypted())
# totalChunks must equal pre-migration source count

# B) FTS5 search smoke
curl -s 'http://127.0.0.1:18802/api/search?q=nox' | jq 'length'
# Expect: > 0

# C) Semantic search (Gemini path) — confirms BLOB columns decrypt cleanly
curl -s 'http://127.0.0.1:18802/api/search?q=memory+pain+weighted&hybrid=true' | jq '.[0] | {id, score, chunk_text: (.chunk_text | .[0:80])}'

# D) KG endpoint
curl -s 'http://127.0.0.1:18802/api/kg?entity=Toto' | jq 'length'

# E) Ingest smoke (writes a tracer chunk + reads it back)
echo "post-migration tracer $(date -Is)" > /tmp/migrate-tracer.txt
nox-mem ingest /tmp/migrate-tracer.txt
curl -s 'http://127.0.0.1:18802/api/search?q=migrate-tracer' | jq 'length'
# Expect: 1
```

### Step 7 — vec0 reindex check (optional but recommended)

If sqlite-vec is loaded in your build (most prod deployments), confirm vector retrieval still works:

```bash
nox-mem stats | grep -i 'vector\|coverage'
# Expect vector_coverage ≥ 99% (matches pre-migration)
```

If vector coverage dropped, force a re-vectorize:

```bash
nox-mem vectorize --missing-only
```

The vec0 table's backing storage was copied verbatim during migration, so this should be a no-op. A reindex failure here means the BLOB columns did not round-trip through the cipher — **escalate, this is a P0 incident**.

---

## Rollback procedure

Two rollback paths depending on what failed and when.

### Path A — Migration produced bad output, swap NOT yet performed

The encrypted file `nox-mem.encrypted.db` is suspect; source is untouched.

```bash
rm /root/.openclaw/workspace/tools/nox-mem/nox-mem.encrypted.db
# Investigate root cause; re-run migration after fix
```

Service was never restarted, no user-facing impact.

### Path B — Swap performed, prod is broken (encrypted DB issues)

The plaintext is preserved at `<source>.pre-encrypt-<ts>.db`.

```bash
systemctl stop nox-mem-api

# 1. Identify the backup
ls -1t /root/.openclaw/workspace/tools/nox-mem/nox-mem.db.pre-encrypt-*.db | head -1
# (record exact filename)

# 2. Move current encrypted DB aside (do NOT delete — forensic value)
mv ./nox-mem.db ./nox-mem.encrypted-failed-$(date -Is).db

# 3. Restore plaintext
mv ./nox-mem.db.pre-encrypt-<ts>.db ./nox-mem.db

# 4. Revert env (remove NOX_DB_KEY + NOX_DB_REQUIRE_KEY from systemd override)
# Edit /etc/systemd/system/nox-mem-api.service.d/override.conf, remove key lines
systemctl daemon-reload
systemctl start nox-mem-api

# 5. Smoke check
curl -s http://127.0.0.1:18802/api/health | jq '.ok'
# Expect: true
```

Service should resume on the plaintext DB exactly as before migration.

### Path C — Both encrypted DB and the .pre-encrypt-<ts>.db backup are corrupt

This is the **disaster** path. Recovery via `/var/backups/nox-mem/` nightly backup:

```bash
ls -lht /var/backups/nox-mem/
cp /var/backups/nox-mem/<most-recent>.db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
# Investigate why both primary copies were lost
```

Data loss window: hours between last nightly backup and the failed migration. For a 02:00 BRT nightly cron + 14:00 BRT migration, that's ~12h of writes lost. Document the incident in `docs/INCIDENTS.md`.

---

## Retention of `.pre-encrypt-<ts>.db`

Default retention: **7 days minimum**, then operator-discretion.

```bash
# After 7 days of clean post-migration operation:
find /root/.openclaw/workspace/tools/nox-mem -name 'nox-mem.db.pre-encrypt-*.db' -mtime +7 -ls
# Review then:
find /root/.openclaw/workspace/tools/nox-mem -name 'nox-mem.db.pre-encrypt-*.db' -mtime +7 -delete
```

**HARD RULE:** never delete the backup within the first 7 days, even if you "tested everything." Cipher-format regressions can surface days later in cold paths (e.g. backup-restore cycles, weekly cron jobs that exercise rare schema paths).

---

## Known limitations + non-goals

1. **No rekey path.** This script migrates **plaintext → encrypted**. Changing the key on an already-encrypted DB requires `PRAGMA rekey`, which is a separate (and simpler) operation not covered here.

2. **No partial / incremental migration.** Full DB copy, single transaction. For multi-GB DBs (we are nowhere near this) consider a stream-based approach using `sqlite3_backup_step`.

3. **No `vec0` virtual-table rebuild.** The script copies the backing aux tables verbatim (this works because vec0 stores its data in ordinary tables; the virtual table is just an index over them). If the vec0 format changes between sqlite-vec versions, run `nox-mem vectorize --missing-only` post-migration.

4. **Operator-driven swap.** No daemon / automated trigger. The migration is a planned op, not a recovery action.

5. **Single-process.** The script holds an exclusive ATTACH on the source. Stop other writers before running.

6. **No FFS / sparse-file optimization.** Output file is a regular SQLite file, sized similarly to source.

---

## References

- Script source: `staged-A2-T3/scripts/migrate-encrypt-db.ts`
- Tests: `staged-A2-T3/scripts/__tests__/migrate-encrypt-db.test.ts` (19 cases)
- Spike report: `experiments/a2-tier3-sqlcipher-spike/RESULTS.md`
- P1 db.ts: `staged-A2-T3/edits/src/lib/db.ts` + `db.crypto.test.ts`
- Design spec: `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md`
- Memory pins: `[[multi-agent-branch-checkout-race]]`, `[[sqlite-text-affinity-coerces-int-back]]`, `[[validate-features-with-db-not-logs]]`

---

## Change log

| Date | Author | Change |
|---|---|---|
| 2026-05-23 | executor-high A2-T3-P2 | Initial — covers migration + swap + rollback for first-time encryption migration |

<!-- end of A2-TIER3-MIGRATION-RUNBOOK.md -->
