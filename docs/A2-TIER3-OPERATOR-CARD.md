# A2 Tier 3 — Operator Quick-Reference Card

> One-page summary. Print + tape to monitor. For full procedure, see `docs/A2-TIER3-DEPLOYMENT-MASTER.md`.

---

## Environment variables (systemd EnvironmentFile)

| Variable | Required? | Set in | Purpose |
|---|---|---|---|
| `NOX_DB_KEY` | YES (post-deploy) | `/root/.openclaw/secrets/nox-mem-cipher.env` | SQLCipher cipher key (base64, 48 bytes). LOSS = unrecoverable DB. |
| `NOX_DB_REQUIRE_KEY` | YES (prod) | same file | `1` → API refuses to open plaintext (tripwire). |
| `NOX_DB_PATH` | optional | `/root/.openclaw/.env` | Override canonical path. Default: `${OPENCLAW_WORKSPACE}/tools/nox-mem/nox-mem.db`. |
| `NOX_READS_AUDIT_RETENTION_DAYS` | optional | `/root/.openclaw/.env` | Days before reads_audit rows are archived. Default 90. |
| `NOX_READS_AUDIT_ARCHIVE_PATH` | optional | `/root/.openclaw/.env` | Archive DB path. Default: sibling `nox-mem-audit-archive.db`. |
| `NOX_AUDIT_CHECKPOINT_PUBKEY` | optional | `/root/.openclaw/.env` | Cached public key for `verify-chain` (avoids file path). |

**File ACL contract:** `0400 root:root` for every file in `/root/.openclaw/secrets/`. World-readable = key compromise = full DB compromise.

---

## Key rotation

### Cipher key rotation (SQLCipher)

```bash
# 1. Generate new key
openssl rand -base64 48 > /root/.openclaw/secrets/nox-mem-cipher.key.NEW
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.key.NEW

# 2. Stop API + ingest (Phase D from master runbook)
systemctl stop nox-mem-api

# 3. Re-key via PRAGMA rekey (different from initial migration!):
node -e "
const Database = require('better-sqlite3-multiple-ciphers');
const db = new Database('/root/.openclaw/workspace/tools/nox-mem/nox-mem.db');
db.pragma(\"cipher='sqlcipher'\");
db.pragma(\"cipher_compatibility=4\");
db.pragma(\"key='\${process.env.OLD_KEY}'\");
db.pragma(\"rekey='\${process.env.NEW_KEY}'\");
console.log('rekey done');
db.close();
"
# Provide OLD_KEY + NEW_KEY via env to this command.

# 4. Update EnvironmentFile + restart
mv /root/.openclaw/secrets/nox-mem-cipher.key /root/.openclaw/secrets/nox-mem-cipher.key.OLD
mv /root/.openclaw/secrets/nox-mem-cipher.key.NEW /root/.openclaw/secrets/nox-mem-cipher.key
# Regenerate .env file:
cat > /root/.openclaw/secrets/nox-mem-cipher.env <<EOF
NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)
NOX_DB_REQUIRE_KEY=1
EOF
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.env
systemctl start nox-mem-api

# 5. After 7 days of clean operation, delete the OLD key:
shred -u /root/.openclaw/secrets/nox-mem-cipher.key.OLD
```

**HARD RULE:** retain the OLD key for ≥ 7 days. Encrypted backups taken before the rekey use the OLD key; restoring from one requires it.

### Audit signing key rotation (Ed25519)

```bash
# 1. Generate new keypair
audit-checkpoint gen-key --out-dir /tmp/new-audit-keys/

# 2. Publish new public key to docs/AUDIT-PUBKEY.md (commit + push)

# 3. Move new private key off-box (laptop + paper backup)

# 4. From this point forward, sign new checkpoints with the new key.
#    OLD checkpoints remain verifiable with the OLD public key — never
#    delete prior AUDIT-PUBKEY.md entries; append a "Rotation history" table.
```

Rotation is **forward-only**. Past checkpoints stay valid under their old key. Auditors verifying historical rows need access to all historical public keys.

---

## Checkpoint frequency

| Cadence | Scope | Trigger |
|---|---|---|
| Weekly | `ops` + `reads` | Cron reminder Mon 09:00 BRT (Phase K), Toto signs offline within 7 days |
| Post-incident | `ops` | Immediately after any `withOpAudit` reindex/consolidate/restore |
| Pre-audit | `all` | Any time an external auditor will receive the DB export |

**Skip-cycle policy:** A skipped weekly checkpoint widens the range of the NEXT checkpoint (which covers all rows from previous `last_id` to current MAX). Auditor verification still works; coverage just lumpier.

---

## Emergency rollback command

If the encrypted DB is broken and you must revert to plaintext NOW:

```bash
systemctl stop nox-mem-api

# 1. Find the pre-encrypt backup (Phase F artifact)
BACKUP=$(ls -1t /root/.openclaw/workspace/tools/nox-mem/nox-mem.db.pre-encrypt-*.db | head -1)
echo "rolling back to: $BACKUP"

# 2. Move encrypted aside (forensic value)
mv /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
   /root/.openclaw/workspace/tools/nox-mem/nox-mem.encrypted-rollback-$(date -Is).db

# 3. Restore plaintext
mv "$BACKUP" /root/.openclaw/workspace/tools/nox-mem/nox-mem.db

# 4. Revert env (remove EnvironmentFile line OR rename the file)
mv /root/.openclaw/secrets/nox-mem-cipher.env /root/.openclaw/secrets/nox-mem-cipher.env.DISABLED
systemctl daemon-reload
systemctl start nox-mem-api

# 5. Validate plaintext open works
curl -s http://127.0.0.1:18802/api/health | jq '{ok, isEncrypted, totalChunks}'
# Expect: ok=true, isEncrypted=false, totalChunks unchanged
```

After rollback: document the incident in `docs/INCIDENTS.md` and DO NOT re-attempt deployment without root-cause analysis.

---

## Daily health checks

Add to your morning routine (or wire into Atlas/Cipher):

```bash
# 1. Encryption mode active?
curl -s http://127.0.0.1:18802/api/health | jq '.isEncrypted'
# Expect: true

# 2. Chunk count drifting?
curl -s http://127.0.0.1:18802/api/health | jq '.totalChunks'
# Compare against /tmp/nox-mem-pre-encrypt-counts.txt for the floor;
# growth is expected (ingest); shrinkage is a red flag.

# 3. ops_audit healthy?
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit'
# Look for: total_24h reasonable (1-10), no stuck status='started' rows.

# 4. Last checkpoint age?
sqlite3 -cmd "PRAGMA cipher='sqlcipher'" \
        -cmd "PRAGMA cipher_compatibility=4" \
        -cmd "PRAGMA key='$NOX_DB_KEY'" \
        /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT scope, MAX(ts), datetime(MAX(ts)/1000, 'unixepoch') FROM audit_checkpoints GROUP BY scope;"
# Alert if any scope's latest ts is > 8 days old.
```

---

## Pinned secrets locations

```
/root/.openclaw/secrets/                       (0700 root:root)
├── nox-mem-cipher.key                          (0400 root:root) — SQLCipher key
├── nox-mem-cipher.env                          (0400 root:root) — systemd EnvironmentFile
└── (no Ed25519 private key — that lives off-box per D56)

~/Documents/nox-secrets/  (laptop)             (0700 owner)
├── nox-mem-cipher.key                          (0600) — cipher key copy
├── audit-checkpoints-private-<fp>.b64          (0600) — Ed25519 signing key
└── audit-checkpoints-public-<fp>.b64           (0644) — Ed25519 verify key (also in repo)

Paper backup (safe deposit / fireproof folder):
├── Cipher key — handwritten OR printed
└── Ed25519 private key — handwritten OR printed
```

---

## Troubleshooting cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| API fails to start: "NOX_DB_REQUIRE_KEY=1 but NOX_DB_KEY is unset" | EnvironmentFile not loaded by systemd | `systemctl cat nox-mem-api` to verify, then `daemon-reload` |
| API starts but queries return "file is not a database (26)" | Wrong NOX_DB_KEY in env | Compare against `/root/.openclaw/secrets/nox-mem-cipher.key`; restart |
| `nox-mem ingest` fails: "Large-DB ingest guard triggered" | NOX_ALLOW_PROD_INGEST not set OR NOX_DB_PATH points wrong | Confirm path; set `NOX_ALLOW_PROD_INGEST=1` for prod writes |
| `verify-chain` returns `broken > 0` | Tamper OR rotation without keeping history | See `docs/A2-TIER3-CHECKPOINTS-GUIDE.md#tamper-response` |
| `BigInt` errors in eval scripts | Pre-P1 db.ts in path | `which nox-mem` → rebuild with P1 db.ts |
| Vec0 query: "Only integers are allowed for primary key values" | `defaultSafeIntegers(true)` missing | P1 db.ts fix; verify deployed version |

---

## References

- Master runbook: `docs/A2-TIER3-DEPLOYMENT-MASTER.md`
- Migration: `docs/A2-TIER3-MIGRATION-RUNBOOK.md`
- Reads audit: `docs/A2-TIER3-READS-AUDIT-GUIDE.md`
- Checkpoints: `docs/A2-TIER3-CHECKPOINTS-GUIDE.md`
- Public key: `docs/AUDIT-PUBKEY.md`
- Automation: `scripts/deploy-a2-tier3.sh --help`

---

*Last updated: 2026-05-23 — A2 Tier 3 P5 (final phase).*
*Tape to monitor. Replace when keys rotate.*
