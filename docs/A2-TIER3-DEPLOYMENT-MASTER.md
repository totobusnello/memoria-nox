# A2 Tier 3 — Master Deployment Runbook (Phases A → K)

> **Status:** READY for production. Final phase of A2 Tier 3 (P0 spike → P5 deployment).
>
> **Audience:** operator (Toto) running the first-time encryption + audit migration on the production VPS.
>
> **Risk class:** destructive on Phases E/F (atomic swap) and G (env wiring). Read every phase before invoking. Phase order is non-commutative.
>
> **Estimated wall-clock:** 30 min for migration + smoke on the current 62.9k-chunk prod DB (Phase D-H). Total runbook ~45 min including key-gen, code deploy, env update, and first checkpoint baseline.
>
> **Disk space required:** `2.2 × size(nox-mem.db)` free during Phases E-F (source + encrypted dest concurrently + 1× swap backup). For current 51MB prod DB → need ≥ 115 MB free.

---

## Index

- [Why this runbook exists](#why)
- [Pre-flight checklist (gating)](#pre-flight)
- [Phase A — Generate Ed25519 keypair + publish public key](#phase-a)
- [Phase B — Deploy P1 code (db.ts wire-up)](#phase-b)
- [Phase C — Verify smoke on plaintext (no-regression)](#phase-c)
- [Phase D — Stop ingest pipeline](#phase-d)
- [Phase E — Run P2 migration script (create encrypted dest)](#phase-e)
- [Phase F — Atomic swap (encrypted dest → canonical path)](#phase-f)
- [Phase G — Set NOX_DB_KEY + NOX_DB_REQUIRE_KEY in systemd](#phase-g)
- [Phase H — Smoke encrypted DB (queries, /api/health, vec0)](#phase-h)
- [Phase I — Re-enable ingest pipeline](#phase-i)
- [Phase J — Initial Ed25519 checkpoint (auditor baseline)](#phase-j)
- [Phase K — Cron schedule P3 reads-audit sweep + P4 weekly checkpoint](#phase-k)
- [Rollback table (per-phase)](#rollback)
- [Validation contracts (machine-checkable)](#validation)
- [Automation entry-point — scripts/deploy-a2-tier3.sh](#automation)
- [Change log](#changelog)

---

<a id="why"></a>
## Why this runbook exists

A2 Tier 3 is the encryption-at-rest + signed-audit upgrade for nox-mem. It composes 4 separately-merged PRs:

| PR | Phase | Component |
|---|---|---|
| #280 (P1) | Phase B | `src/lib/db.ts` SQLCipher key-open wire-up + BigInt fix |
| #286 (P2) | Phase E | `scripts/migrate-encrypt-db.ts` — plaintext → encrypted migration |
| #292 (P3) | Phase K | `src/lib/reads-audit.ts` + `reads-audit-sweep.ts` retention sweep |
| #294 (P4) | Phase A, J | `src/lib/audit-checkpoints.ts` Ed25519 signed checkpoints + CLI |
| THIS PR  | Phase A-K | Master runbook + automation + smoke contract |

Each PR is individually tested (78 tests pre-P5; 96 with P5 smoke). What this runbook adds: the **sequencing, rollback discipline, and validation contracts** that make the 4 PRs callable as one atomic prod upgrade.

**HARD RULE:** the 4 PRs together do NOT auto-deploy. P1 ships db.ts code that is BACKWARD-COMPATIBLE (no NOX_DB_KEY in env → plaintext open). P2/P3/P4 ship code paths that are INERT until Phase G flips the env. This runbook is the only place that flips the env, and it does so AFTER the migration has produced a valid encrypted DB.

---

<a id="pre-flight"></a>
## Pre-flight checklist (gating — stop on any fail)

Run every item below before Phase A. Each is independently fatal.

### PF-1. Disk space + DB size baseline

```bash
df -h /root/.openclaw/workspace/tools/nox-mem
ls -lh /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT count(*) FROM chunks;"
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT count(*) FROM kg_entities;"
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT count(*) FROM kg_relations;"
```

**Record these counts.** They are the validation targets for Phase E + H smoke. Save them in `/tmp/nox-mem-pre-encrypt-counts.txt`:

```bash
SRC=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
{
  echo "chunks=$(sqlite3 $SRC 'SELECT count(*) FROM chunks;')"
  echo "kg_entities=$(sqlite3 $SRC 'SELECT count(*) FROM kg_entities;')"
  echo "kg_relations=$(sqlite3 $SRC 'SELECT count(*) FROM kg_relations;')"
  echo "vec_chunks=$(sqlite3 $SRC 'SELECT count(*) FROM vec_chunks;' 2>/dev/null || echo 0)"
  echo "size_bytes=$(stat -c %s $SRC)"
  echo "iso_ts=$(date -Is)"
} > /tmp/nox-mem-pre-encrypt-counts.txt
cat /tmp/nox-mem-pre-encrypt-counts.txt
```

### PF-2. Recent nightly backup exists

```bash
ls -lht /var/backups/nox-mem/ | head -5
```

Most recent must be < 24h old. If older, run nightly manually first:

```bash
/root/.openclaw/workspace/tools/nox-mem/scripts/backup-all.sh
```

### PF-3. op-audit table clean (no running ops)

```bash
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit'
```

No rows with `status='started'` may be in flight. If any, wait for them to terminate (success/failed/crashed). Concurrent reindex during migration = data drift.

### PF-4. Schema invariants OK

```bash
/root/.openclaw/workspace/tools/nox-mem/scripts/check-schema-invariants.sh
```

All 4 invariants must return OK. The migration faithfully copies any pre-existing schema rot.

### PF-5. better-sqlite3-multiple-ciphers installable

```bash
cd /root/.openclaw/workspace/tools/nox-mem
npm view better-sqlite3-multiple-ciphers@^11.10 version
```

Verifies network + npm registry reachable. The Phase B SCP brings the build, but the dependency lookup must work.

### PF-6. systemd unit override directory exists + writable

```bash
ls -la /etc/systemd/system/nox-mem-api.service.d/
```

If missing:

```bash
mkdir -p /etc/systemd/system/nox-mem-api.service.d/
```

### PF-7. Secrets directory exists with correct ACL

```bash
ls -la /root/.openclaw/secrets/
# Expected mode: 0700, owned by root
```

If missing:

```bash
mkdir -p /root/.openclaw/secrets/
chmod 0700 /root/.openclaw/secrets/
chown root:root /root/.openclaw/secrets/
```

---

<a id="phase-a"></a>
## Phase A — Generate Ed25519 keypair + publish public key

**Goal:** create a signing key pair for forensic checkpoints (P4). Public key goes in repo (`docs/AUDIT-PUBKEY.md`); private key goes off-box.

**Wall-clock:** 5 min.

### A.1 Generate keypair via P4 CLI

```bash
cd /root/.openclaw/workspace/tools/nox-mem
# After P4 code is deployed (post-Phase B). For this phase, do it locally on Toto's laptop:
node staged-A2-T3/dist/edits/scripts/audit-checkpoint-cli.js gen-key \
     --out-dir /tmp/nox-audit-keys-$(date +%Y%m%d)
```

Output:

```json
{
  "status": "ok",
  "public_key_fingerprint": "<16-hex-chars>",
  "private_key_path": "/tmp/nox-audit-keys-2026-05-23/audit-checkpoints-private-<fp>.b64",
  "public_key_path": "/tmp/nox-audit-keys-2026-05-23/audit-checkpoints-public-<fp>.b64",
  "next_steps": [...]
}
```

### A.2 Move private key OFF-BOX

```bash
# On Toto's laptop (NOT the VPS):
scp root@<vps>:/tmp/nox-audit-keys-*/audit-checkpoints-private-*.b64 ~/Documents/nox-secrets/

# Verify mode 0600:
chmod 0600 ~/Documents/nox-secrets/audit-checkpoints-private-*.b64

# Also write to paper backup (per D56):
cat ~/Documents/nox-secrets/audit-checkpoints-private-*.b64
# Print → store in safe deposit box / fireproof folder.

# On the VPS: wipe the private key (does NOT live on VPS in steady-state)
shred -u /tmp/nox-audit-keys-*/audit-checkpoints-private-*.b64
```

**HARD RULE:** the private key MUST NOT remain on the VPS. The whole point of the signed-checkpoint design (D56) is that even if the VPS is fully compromised, an attacker cannot forge new checkpoints. If the private key is left on the VPS, this property is forfeited.

### A.3 Publish public key in repo

```bash
# On laptop:
PUBKEY=$(cat /tmp/nox-audit-keys-*/audit-checkpoints-public-*.b64)
FP=$(echo -n "$PUBKEY" | base64 -d | sha256sum | head -c 16)

cat > docs/AUDIT-PUBKEY.md <<EOF
# nox-mem A2 Tier 3 — Audit Public Key

> **DO NOT EDIT** unless rotating the audit key (see operator card §Key rotation).

- **Algorithm:** Ed25519 (raw 32-byte public key, base64-encoded)
- **Fingerprint:** \`${FP}\` (SHA-256 prefix, first 16 hex chars)
- **Public key:** \`${PUBKEY}\`
- **Generated:** $(date -Is)
- **Generated by:** Toto Busnello (lab@nuvini.com.br)

## Verification

To verify an audit-checkpoint chain offline:

\`\`\`bash
# Export the audit_checkpoints table to a portable file
sqlite3 nox-mem.db ".dump audit_checkpoints" > audit-checkpoints-export.sql

# Verify the chain using ONLY this public key + the audit table
audit-checkpoint verify-chain --scope all --key-file <(echo -n '${PUBKEY}')
\`\`\`

A clean chain returns exit 0 + \`broken: 0\`. Any mismatch is a tamper indicator — see \`docs/A2-TIER3-CHECKPOINTS-GUIDE.md#tamper-response\`.
EOF

git add docs/AUDIT-PUBKEY.md && git commit -m "ops(audit): publish A2 Tier 3 public key fingerprint ${FP}"
git push origin main
```

### A.4 Validation

```bash
# Public key is readable + decodes to exactly 32 raw bytes:
echo -n "$PUBKEY" | base64 -d | wc -c
# Expect: 32
```

PASS = exactly `32`. Any other value = bad key file; restart Phase A.

---

<a id="phase-b"></a>
## Phase B — Deploy P1 code (db.ts wire-up)

**Goal:** put the staged P1 db.ts on the VPS so the API can recognize NOX_DB_KEY. Until Phase G flips the env, the API still opens the DB as plaintext — this phase is back-compat-safe.

**Wall-clock:** 5 min.

### B.1 SCP staged code

```bash
# From laptop, with the merged branch checked out:
cd /Users/lab/Claude/Projetos/memoria-nox
rsync -avz --progress \
  staged-A2-T3/edits/src/lib/db.ts \
  root@<vps>:/root/.openclaw/workspace/tools/nox-mem/src/lib/db.ts.staged

rsync -avz --progress \
  staged-A2-T3/edits/src/lib/reads-audit.ts \
  staged-A2-T3/edits/src/lib/reads-audit-schema.sql \
  staged-A2-T3/edits/src/lib/audit-checkpoints.ts \
  staged-A2-T3/edits/src/lib/audit-checkpoints-schema.sql \
  root@<vps>:/root/.openclaw/workspace/tools/nox-mem/src/lib/

rsync -avz --progress \
  staged-A2-T3/scripts/migrate-encrypt-db.ts \
  root@<vps>:/root/.openclaw/workspace/tools/nox-mem/scripts/

rsync -avz --progress \
  staged-A2-T3/edits/scripts/audit-checkpoint-cli.ts \
  staged-A2-T3/edits/scripts/reads-audit-sweep.ts \
  root@<vps>:/root/.openclaw/workspace/tools/nox-mem/scripts/
```

### B.2 Install new dependency + build

```bash
ssh root@<vps>
cd /root/.openclaw/workspace/tools/nox-mem

# Install the cipher driver (P1 dependency):
npm install better-sqlite3-multiple-ciphers@^11.10

# Atomic swap of db.ts (back up the current one first):
cp src/lib/db.ts src/lib/db.ts.pre-a2-t3-$(date +%Y%m%d-%H%M).bak
mv src/lib/db.ts.staged src/lib/db.ts

# Rebuild
npm run build
```

### B.3 Restart API (still plaintext mode — NOX_DB_KEY not set yet)

```bash
systemctl restart nox-mem-api
systemctl status nox-mem-api | head -15
```

### B.4 Validation

```bash
# /api/health must respond OK + isEncrypted=false (env has no NOX_DB_KEY)
curl -s http://127.0.0.1:18802/api/health | jq '{ok, totalChunks, isEncrypted}'
```

PASS = `ok: true`, `totalChunks` equals PF-1 chunks count, `isEncrypted: false`. Any error = revert db.ts via the .bak file + restart, then debug.

---

<a id="phase-c"></a>
## Phase C — Verify smoke on plaintext (no-regression)

**Goal:** confirm the P1 code deploy did NOT introduce a regression. The DB is still plaintext at this point. All existing query paths must work identically.

**Wall-clock:** 5 min.

```bash
# C.1 — total chunk count (must match PF-1)
curl -s http://127.0.0.1:18802/api/health | jq '.totalChunks'

# C.2 — FTS5 query returns results
curl -s 'http://127.0.0.1:18802/api/search?q=nox' | jq 'length'
# Expect: > 0

# C.3 — hybrid search (BM25 + Gemini + RRF)
curl -s 'http://127.0.0.1:18802/api/search?q=memoria+nox+pain+weighted&hybrid=true' \
  | jq '.[0] | {id, score, chunk_text: (.chunk_text | .[0:80])}'

# C.4 — KG endpoint
curl -s 'http://127.0.0.1:18802/api/kg?entity=Toto' | jq 'length'

# C.5 — vector coverage unchanged
curl -s http://127.0.0.1:18802/api/health | jq '.vectorCoverage'
# Expect: same as pre-deploy (typically 99.97%)
```

PASS = all 5 return non-zero / non-error responses. Any FAIL = Phase B regression — investigate + fix before proceeding.

---

<a id="phase-d"></a>
## Phase D — Stop ingest pipeline

**Goal:** quiesce all writers to the plaintext DB so the migration (Phase E) sees a stable snapshot.

**Wall-clock:** 2 min.

```bash
# D.1 — disable end-of-day cron (reindex/consolidate)
crontab -l > /tmp/crontab-pre-a2-t3.bak
crontab -l | grep -v 'nox-mem' | crontab -
crontab -l   # verify nox-mem lines removed

# D.2 — kill inotifywait watcher process
pkill -f 'inotifywait.*nox-mem' || true
ps -ef | grep -E 'inotifywait|nox-mem' | grep -v grep
# Expect: no nox-mem processes other than api-server

# D.3 — stop the API (it holds an open file handle)
systemctl stop nox-mem-api
systemctl status nox-mem-api | head -5
# Expect: inactive (dead)

# D.4 — verify no other writer holds the DB open
lsof | grep nox-mem.db || echo "no holders — good"
```

PASS = lsof shows no holders. Any holder = identify + stop before Phase E.

---

<a id="phase-e"></a>
## Phase E — Run P2 migration script

**Goal:** create an encrypted copy of the plaintext DB at a new path. Source untouched at this phase.

**Wall-clock:** 5 min (62k chunks @ ~51MB → ~3 min migration, ~1 min validation).

```bash
# E.1 — generate cipher key (DIFFERENT from audit-checkpoint Ed25519 key!)
openssl rand -base64 48 > /root/.openclaw/secrets/nox-mem-cipher.key
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.key
chown root:root /root/.openclaw/secrets/nox-mem-cipher.key

# E.2 — back up the cipher key to laptop IMMEDIATELY (mirrors Phase A.2 for cipher)
# On laptop:
scp root@<vps>:/root/.openclaw/secrets/nox-mem-cipher.key ~/Documents/nox-secrets/
chmod 0600 ~/Documents/nox-secrets/nox-mem-cipher.key

# IF THIS KEY IS LOST, THE ENCRYPTED DB IS UNRECOVERABLE.

# E.3 — run migration (non-destructive: source untouched)
cd /root/.openclaw/workspace/tools/nox-mem
export NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)
node dist/scripts/migrate-encrypt-db.js \
     ./nox-mem.db \
     ./nox-mem.encrypted.db \
     "$NOX_DB_KEY" \
     2>&1 | tee /tmp/migrate-encrypt-$(date +%Y%m%d-%H%M).log
```

Expected exit code: **0**. Expected log tail:

```
[migrate] SUCCESS — <N> tables, <bytes> bytes, <ms> ms
```

### E.4 Validation (manual count + script's own validation)

```bash
# Reopen encrypted DB and count chunks
node -e "
const Database = require('better-sqlite3-multiple-ciphers');
const db = new Database('./nox-mem.encrypted.db');
db.pragma(\"cipher='sqlcipher'\", { simple: true });
db.pragma(\"legacy=4\", { simple: true });
db.pragma(\"cipher_compatibility=4\", { simple: true });
db.pragma(\"key='\${process.env.NOX_DB_KEY}'\", { simple: true });
db.defaultSafeIntegers(true);
console.log('chunks:',       Number(db.prepare('SELECT count(*) AS n FROM chunks').get().n));
console.log('kg_entities:',  Number(db.prepare('SELECT count(*) AS n FROM kg_entities').get().n));
console.log('kg_relations:', Number(db.prepare('SELECT count(*) AS n FROM kg_relations').get().n));
console.log('FTS nox:',      Number(db.prepare(\"SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'nox'\").get().n));
"
```

PASS = these 4 numbers EXACTLY match PF-1 records.

Any mismatch = **DO NOT PROCEED**. Delete the encrypted DB:
```bash
rm ./nox-mem.encrypted.db
```
Investigate the diff in `/tmp/migrate-encrypt-*.log` before re-running.

---

<a id="phase-f"></a>
## Phase F — Atomic swap (encrypted dest → canonical path)

**Goal:** make the encrypted DB the canonical one at `./nox-mem.db`. Plaintext source preserved as `.pre-encrypt-<ts>.db`.

**Wall-clock:** < 1 min.

```bash
cd /root/.openclaw/workspace/tools/nox-mem
export NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)

# F.1 — verify API still stopped (Phase D held)
systemctl status nox-mem-api | head -3
# Expect: inactive

# F.2 — perform swap
node dist/scripts/migrate-encrypt-db.js \
     ./nox-mem.db \
     ./nox-mem.encrypted.db \
     "$NOX_DB_KEY" \
     --swap

# Note: migrate-encrypt-db with --swap and dest already created will fail
# because the script refuses to overwrite. Use the dedicated swap helper:
# (preferred — also resolves the "dest already exists" guard)
node -e "
const { swapEncryptedIntoSource } = require('./dist/scripts/migrate-encrypt-db.js');
const backup = swapEncryptedIntoSource('./nox-mem.db', './nox-mem.encrypted.db');
console.log('plaintext backup at:', backup);
"
```

### F.3 Validation

```bash
ls -la ./nox-mem.db ./nox-mem.db.pre-encrypt-*.db
# Expect: both exist; .pre-encrypt-<ts>.db is the original plaintext size

# Encrypted DB is unreadable without key (proof of encryption)
sqlite3 ./nox-mem.db "SELECT count(*) FROM sqlite_master;"
# Expect: error "file is not a database" or "file is encrypted"
```

PASS = sqlite3 (no-key) reports NOTADB error. The plaintext backup is at `./nox-mem.db.pre-encrypt-<ts>.db`.

---

<a id="phase-g"></a>
## Phase G — Set NOX_DB_KEY + NOX_DB_REQUIRE_KEY in systemd

**Goal:** wire the cipher key into the systemd-managed API process via an `EnvironmentFile` (key not visible in `systemctl show`).

**Wall-clock:** 3 min.

### G.1 Create EnvironmentFile

```bash
cat > /root/.openclaw/secrets/nox-mem-cipher.env <<EOF
NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)
NOX_DB_REQUIRE_KEY=1
EOF
chmod 0400 /root/.openclaw/secrets/nox-mem-cipher.env
chown root:root /root/.openclaw/secrets/nox-mem-cipher.env
```

### G.2 Update systemd unit override

Create `/etc/systemd/system/nox-mem-api.service.d/override.conf`:

```ini
[Service]
EnvironmentFile=/root/.openclaw/secrets/nox-mem-cipher.env
```

(Append `EnvironmentFile=` if other env-files already exist; do NOT replace them.)

```bash
systemctl daemon-reload
systemctl cat nox-mem-api | grep -E 'EnvironmentFile|Environment'
# Should now include /root/.openclaw/secrets/nox-mem-cipher.env
```

### G.3 Validation

```bash
# Key is loaded but not echoed by systemd:
systemctl show nox-mem-api -p Environment | head -3
# Expect: Environment= (empty — keys live in EnvironmentFile, not Environment)

# File ACL is locked:
stat -c '%a %U:%G %s' /root/.openclaw/secrets/nox-mem-cipher.env
# Expect: 400 root:root <size>
```

PASS = ACL is `0400 root:root`, daemon-reload succeeded. Do NOT start the API yet — Phase H drives that.

---

<a id="phase-h"></a>
## Phase H — Smoke encrypted DB

**Goal:** start the API on the encrypted DB and prove every query path works.

**Wall-clock:** 5 min.

```bash
# H.1 — start API
systemctl start nox-mem-api
sleep 3
systemctl status nox-mem-api | head -10
# Expect: active (running)

# H.2 — health endpoint reports encrypted mode
curl -s http://127.0.0.1:18802/api/health | jq '{
  ok, totalChunks, vectorCoverage, isEncrypted
}'
# Expect: ok=true, isEncrypted=true, totalChunks equals PF-1
```

**STOP** if `isEncrypted` is false (or absent) — the API picked up an old code path or the env didn't load. Stop the API + investigate.

```bash
# H.3 — FTS5 search smoke (validates chunks_fts decryption + tokenizer)
curl -s 'http://127.0.0.1:18802/api/search?q=nox' | jq 'length'
# Expect: > 0

# H.4 — hybrid search (BM25 + Gemini + RRF)
curl -s 'http://127.0.0.1:18802/api/search?q=memoria+pain+weighted&hybrid=true' \
  | jq '.[0] | {id, score, chunk_text: (.chunk_text | .[0:80])}'

# H.5 — KG endpoint
curl -s 'http://127.0.0.1:18802/api/kg?entity=Toto' | jq 'length'

# H.6 — vec0 vector search (BLOB column decryption proof)
curl -s 'http://127.0.0.1:18802/api/search?q=hybrid+memory&hybrid=true&topK=5' \
  | jq '.[] | {id, score}' | head -30
# Expect: 5 rows with non-zero scores

# H.7 — /api/answer flagship endpoint (P1 feature LIVE since 2026-05-18)
curl -s 'http://127.0.0.1:18802/api/answer?q=what+is+nox-mem' \
  | jq '{answer: (.answer | .[0:100]), latency_ms, sources: (.sources | length)}'
# Expect: non-empty answer, latency < 3000ms
```

### H.8 Run programmatic smoke suite (optional but recommended)

The P5 staged smoke tests are hermetic (synthetic fixtures), but they can ALSO be repointed at the prod DB:

```bash
# On a separate SSH session, against a snapshot — NEVER prod write-mode:
cp ./nox-mem.db /tmp/nox-mem-snapshot-h8.db
cd /root/.openclaw/workspace/tools/nox-mem/staged-A2-T3
NOX_DB_PATH=/tmp/nox-mem-snapshot-h8.db \
  NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key) \
  npm run test:p5
# Expect: all P5 smoke tests pass (96 total, 18 new in this PR)
rm /tmp/nox-mem-snapshot-h8.db
```

PASS = all 7 (H.2-H.7) return non-error responses, H.8 optional all-green.

---

<a id="phase-i"></a>
## Phase I — Re-enable ingest pipeline

**Goal:** restore the cron + inotifywait watchers so daily ingest resumes.

**Wall-clock:** 2 min.

```bash
# I.1 — restore crontab
crontab /tmp/crontab-pre-a2-t3.bak
crontab -l | grep nox-mem
# Expect: cron lines restored

# I.2 — restart inotifywait watcher (depends on your deployment — typical script):
nohup /root/.openclaw/workspace/tools/nox-mem/scripts/watch-and-ingest.sh \
  > /var/log/nox-mem/watch.log 2>&1 &
# OR if managed by systemd:
systemctl start nox-mem-watcher

# I.3 — validate
ps -ef | grep -E 'inotifywait|nox-mem' | grep -v grep
crontab -l | grep -c nox-mem
# Expect: at least 1 inotifywait process + cron lines present
```

### I.4 Validation — write a tracer through ingest

```bash
echo "post-encryption tracer $(date -Is)" > /tmp/nox-mem-tracer-i4.txt
nox-mem ingest /tmp/nox-mem-tracer-i4.txt

# Confirm it appears in the encrypted DB via API:
curl -s 'http://127.0.0.1:18802/api/search?q=tracer-i4' | jq 'length'
# Expect: 1
```

PASS = tracer round-trips through the encrypted DB.

---

<a id="phase-j"></a>
## Phase J — Initial Ed25519 checkpoint (auditor baseline)

**Goal:** create the FIRST audit checkpoint over `ops_audit` + `reads_audit` so the chain has a verifiable genesis point.

**Wall-clock:** 3 min.

This step requires the private key from Phase A — it lives off-box. Run it from Toto's laptop with a temporary ssh ATTACH (or copy the private key to the VPS for ONE command then shred). Recommended: laptop.

```bash
# On laptop:
PRIV=~/Documents/nox-secrets/audit-checkpoints-private-*.b64
PUB=~/Documents/nox-secrets/audit-checkpoints-public-*.b64

# J.1 — bridge: query the encrypted DB remotely OR pull a snapshot
ssh root@<vps> 'cp /root/.openclaw/workspace/tools/nox-mem/nox-mem.db /tmp/nox-mem-checkpoint-bridge.db'
scp root@<vps>:/tmp/nox-mem-checkpoint-bridge.db /tmp/

# J.2 — create checkpoint for ops scope (signed offline)
cd /Users/lab/Claude/Projetos/memoria-nox/staged-A2-T3
NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db \
  NOX_DB_KEY=$(cat ~/Documents/nox-secrets/nox-mem-cipher.key) \
  node dist/edits/scripts/audit-checkpoint-cli.js create \
    --scope ops \
    --key-file "$PRIV"

# Expected: { "status": "ok", "scope": "ops", "row_count": <N>, ... }
# If "noop": ops_audit is empty (no destructive ops have run yet) — that's OK,
# the first real reindex/consolidate will populate it.

# J.3 — create checkpoint for reads scope
NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db \
  NOX_DB_KEY=$(cat ~/Documents/nox-secrets/nox-mem-cipher.key) \
  node dist/edits/scripts/audit-checkpoint-cli.js create \
    --scope reads \
    --key-file "$PRIV"

# J.4 — verify the just-created chain
NOX_DB_PATH=/tmp/nox-mem-checkpoint-bridge.db \
  NOX_DB_KEY=$(cat ~/Documents/nox-secrets/nox-mem-cipher.key) \
  node dist/edits/scripts/audit-checkpoint-cli.js verify-chain \
    --scope all \
    --key-file "$PUB"

# Expected: { "status": "ok", "scopes": { "ops": {"broken": 0, ...}, "reads": {...} } }
```

### J.5 Sync checkpoints back to VPS

The checkpoint rows were written to the snapshot on laptop. To get them back into prod:

```bash
# Option A: dump + import via SQL
sqlite3 /tmp/nox-mem-checkpoint-bridge.db ".dump audit_checkpoints" > /tmp/checkpoints.sql
scp /tmp/checkpoints.sql root@<vps>:/tmp/

ssh root@<vps>
cd /root/.openclaw/workspace/tools/nox-mem
export NOX_DB_KEY=$(cat /root/.openclaw/secrets/nox-mem-cipher.key)
node -e "
const Database = require('better-sqlite3-multiple-ciphers');
const fs = require('fs');
const db = new Database('./nox-mem.db');
db.pragma(\"cipher='sqlcipher'\", { simple: true });
db.pragma(\"legacy=4\", { simple: true });
db.pragma(\"cipher_compatibility=4\", { simple: true });
db.pragma(\"key='\${process.env.NOX_DB_KEY}'\", { simple: true });
db.exec(fs.readFileSync('/tmp/checkpoints.sql', 'utf8'));
console.log('imported');
"

# Cleanup snapshot
rm /tmp/nox-mem-checkpoint-bridge.db /tmp/checkpoints.sql
```

PASS = `verify-chain --scope all` on the VPS-side encrypted DB returns `broken: 0`.

> **Operational note:** the bridge-snapshot pattern in J.1-J.5 is appropriate for the INITIAL checkpoint where the chain is empty. For ongoing weekly checkpoints (Phase K), prefer the SSH-then-shred pattern (Phase J variant in `docs/A2-TIER3-CHECKPOINTS-GUIDE.md`).

---

<a id="phase-k"></a>
## Phase K — Cron schedule (P3 reads-audit sweep + P4 weekly checkpoint)

**Goal:** put the ongoing maintenance on cron so the system runs unattended.

**Wall-clock:** 3 min.

### K.1 P3 — reads-audit retention sweep (90d default)

Add to root crontab (`crontab -e`):

```cron
# A2 Tier 3 / P3 — reads_audit retention sweep, weekly Sunday 03:00 BRT (06:00 UTC)
0 6 * * 0  cd /root/.openclaw/workspace/tools/nox-mem && \
           set -a && source /root/.openclaw/.env && \
           source /root/.openclaw/secrets/nox-mem-cipher.env && \
           set +a && \
           node dist/scripts/reads-audit-sweep.js \
             --retention-days 90 \
             --archive-path /var/backups/nox-mem/reads-audit-archive.db \
             >> /var/log/nox-mem/reads-audit-sweep.log 2>&1
```

### K.2 P4 — weekly audit checkpoint (proposal — DOES NOT SIGN)

The signing step requires the off-box private key. Cron can PROPOSE unsigned checkpoints (signature_b64=NULL); Toto signs them in batch on laptop. This requires P4.1 (batch-sign) which is a future enhancement; for now, schedule a reminder:

```cron
# A2 Tier 3 / P4 — weekly checkpoint REMINDER (Mon 09:00 BRT)
# P4.1 will replace this with a cron-proposed unsigned checkpoint; for now,
# this just emits a notification that it's time to sign offline.
0 12 * * 1  echo "Weekly nox-mem audit checkpoint due — run from laptop: ssh + audit-checkpoint create --scope all" \
           | mail -s "[nox-mem] weekly checkpoint reminder" lab@nuvini.com.br
```

### K.3 Validation

```bash
crontab -l | grep -c -E 'reads-audit-sweep|checkpoint'
# Expect: 2

# Trigger a dry-run sweep to confirm wiring (no destructive action):
cd /root/.openclaw/workspace/tools/nox-mem
set -a && source /root/.openclaw/.env && source /root/.openclaw/secrets/nox-mem-cipher.env && set +a
node dist/scripts/reads-audit-sweep.js --dry-run --retention-days 90
# Expect: "[reads-audit-sweep] DRY RUN — would archive N rows..."
```

PASS = dry-run sweep produces sane output, both cron lines present.

---

<a id="rollback"></a>
## Rollback table (per phase)

| Phase | Failure mode | Rollback |
|---|---|---|
| A | Lost private key file mid-Phase | Restart Phase A from scratch; the published public key in repo is from THIS attempt — revert via `git revert` of A.3 commit. |
| B | API fails to start with new db.ts | `mv src/lib/db.ts.pre-a2-t3-*.bak src/lib/db.ts` → `systemctl restart nox-mem-api`. |
| C | Smoke fails on plaintext | Same as Phase B — revert db.ts. No DB changes have occurred yet. |
| D | Inotifywait fails to stop | Phase D is reversible by re-enabling the cron + watcher; no state change. |
| E | Migration row counts diverge | `rm ./nox-mem.encrypted.db` → investigate `/tmp/migrate-encrypt-*.log` → re-run. |
| F | Swap leaves both files broken | `mv ./nox-mem.db.pre-encrypt-<ts>.db ./nox-mem.db` (the plaintext is intact). |
| G | systemd refuses to reload | `mv override.conf.bak override.conf` → `daemon-reload`. API not yet started under new env. |
| H | API starts but queries fail | **Stop API** → restore plaintext via Phase F rollback → revert Phase G env → restart. Lose the cipher key as collateral; this attempt is dead. |
| I | Ingest pipeline misbehaves | Revert crontab from `/tmp/crontab-pre-a2-t3.bak`; investigate watcher logs. |
| J | Checkpoint chain breaks | Bug in P4 — investigate, re-create checkpoints (signing is idempotent per scope). |
| K | Cron fires before key is ready | Disable cron line + investigate; sweep is safe to skip a cycle. |

### Disaster path — all encrypted DB attempts failed

Restore from nightly:

```bash
systemctl stop nox-mem-api
mv ./nox-mem.db ./nox-mem.encrypted-failed-$(date -Is).db
cp /var/backups/nox-mem/<most-recent>.db ./nox-mem.db
# Revert env (remove EnvironmentFile= line)
systemctl daemon-reload
systemctl start nox-mem-api
# Investigate why both primary copies were lost. Document in docs/INCIDENTS.md.
```

---

<a id="validation"></a>
## Validation contracts (machine-checkable per phase)

| Phase | PASS criterion |
|---|---|
| A | `wc -c < public_key.b64` = base64 of exactly 32 raw bytes; `docs/AUDIT-PUBKEY.md` committed |
| B | `curl /api/health \| jq .isEncrypted` = false, `totalChunks` = PF-1 |
| C | All 5 (C.1-C.5) curls return non-error, vectorCoverage unchanged |
| D | `lsof \| grep nox-mem.db` empty; `systemctl status nox-mem-api` = inactive |
| E | migrate-encrypt-db.js exits 0; reopened count matches PF-1 for every table |
| F | `sqlite3 ./nox-mem.db "..."` returns NOTADB error; `.pre-encrypt-<ts>.db` exists |
| G | `stat ./nox-mem-cipher.env` = 400 root:root; `systemctl cat` includes EnvironmentFile= |
| H | `curl /api/health \| jq .isEncrypted` = true, `totalChunks` = PF-1, H.3-H.7 all non-error |
| I | tracer round-trips: `curl /api/search?q=tracer-i4 \| jq length` = 1 |
| J | `verify-chain --scope all` returns `{ status: "ok", broken: 0 }` for both scopes |
| K | `crontab -l \| grep -c reads-audit-sweep` ≥ 1; dry-run sweep returns sane output |

---

<a id="automation"></a>
## Automation — `scripts/deploy-a2-tier3.sh`

The shell wrapper at `scripts/deploy-a2-tier3.sh` ties the manual sequence into a single tool with:

- `--dry-run`: prints the plan WITHOUT executing
- `--phase A|B|C|...|K`: runs ONE phase (idempotent re-runs are safe)
- `--all`: runs Phase A → K in order, halting on first failure
- Logs to `audits/a2-tier3-deploy-<ISO-ts>.log`
- Pre-flight validation gates each phase

**Recommended invocation:**

```bash
# First time:
./scripts/deploy-a2-tier3.sh --dry-run --all

# Phase-by-phase (interactive — recommended for first prod migration):
./scripts/deploy-a2-tier3.sh --phase A
./scripts/deploy-a2-tier3.sh --phase B
# ...

# After validation:
./scripts/deploy-a2-tier3.sh --all
```

The script is non-destructive in `--dry-run` mode and can be re-run safely on any phase that has been completed (each phase exits early if its post-condition already holds).

See `scripts/deploy-a2-tier3.sh --help` for full flag reference.

---

<a id="changelog"></a>
## Change log

| Date | Author | Change |
|---|---|---|
| 2026-05-23 | executor-high A2-T3-P5 | Initial — master runbook covering Phases A-K, rollback table, validation contracts, automation entry-point. Closes A2 Tier 3 P0-P5. |

---

## References

- P0 spike: `experiments/a2-tier3-sqlcipher-spike/RESULTS.md`
- P1 code: `staged-A2-T3/edits/src/lib/db.ts` (PR #280)
- P2 migration: `staged-A2-T3/scripts/migrate-encrypt-db.ts` (PR #286)
- P2 runbook: `docs/A2-TIER3-MIGRATION-RUNBOOK.md` (extended by this doc)
- P3 reads-audit: `staged-A2-T3/edits/src/lib/reads-audit.ts` (PR #292)
- P3 guide: `docs/A2-TIER3-READS-AUDIT-GUIDE.md`
- P4 checkpoints: `staged-A2-T3/edits/src/lib/audit-checkpoints.ts` (PR #294)
- P4 guide: `docs/A2-TIER3-CHECKPOINTS-GUIDE.md`
- P5 smoke: `staged-A2-T3/scripts/__tests__/post-deployment-smoke.test.ts` (this PR)
- Operator card: `docs/A2-TIER3-OPERATOR-CARD.md` (this PR)
- Automation: `scripts/deploy-a2-tier3.sh` (this PR)
- Memory pins: `[[multi-agent-branch-checkout-race]]`, `[[sqlite-text-affinity-coerces-int-back]]`, `[[validate-features-with-db-not-logs]]`, `[[no-secrets-in-git]]`

<!-- end of A2-TIER3-DEPLOYMENT-MASTER.md -->
