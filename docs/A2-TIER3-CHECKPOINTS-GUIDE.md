# A2 Tier 3 — Ed25519 Signed Audit Checkpoints (Phase 4)

**Status:** staged in `staged-A2-T3/` — VPS deploy gated on Toto sign-off.
**Spec:** `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md` §4.3 F2 + §10 D-A2T3-3
**Decision:** `docs/DECISIONS.md` D56 — Ed25519 manual signing, public key publishable, auditor-grade.

---

## 1. What this delivers

A reviewer with the published public key can verify the integrity of the entire ops_audit + reads_audit history **offline**, without ever touching nox-mem source code and without trusting the operator. Tampering with audit rows (after signing) breaks the corresponding checkpoint and is detectable.

Tamper-detection coverage:

| Adversary action | Detected by |
|---|---|
| Delete a row from `ops_audit` or `reads_audit` | Re-hash of range produces different digest → `verifyCheckpoint(id, pub)` returns `valid: false` with `hash mismatch` |
| Insert a retroactive row in past range | Same as above |
| Mutate a column in past range | Same as above |
| Delete a row from `audit_checkpoints` | Trigger `trg_audit_checkpoints_no_delete` → `RAISE(ABORT)` |
| Mutate a signed checkpoint | Trigger `trg_audit_checkpoints_no_update_signed` → `RAISE(ABORT)` |
| Forge a new checkpoint with attacker key | `signature_b64` is by attacker key → `verify` rejects when given the *expected* (published) public key |
| Substitute the published public key | Fingerprint mismatch in cross-check against `docs/AUDIT-PUBKEY.md` |

Out of scope: live-memory key extraction, private-key compromise, host root takeover with code-injection — see specs §1.2 for the full list.

---

## 2. When to checkpoint

| Scenario | Frequency | Trigger |
|---|---|---|
| Routine (production) | Hourly (cron) | `audit-checkpoint create --scope ops` + same for `reads` |
| After migration (P2 plaintext→encrypted) | Once, post-swap | manual |
| Before a routine audit / external review | Once, fresh | manual |
| After bulk destructive op (`reindex`, `compact`) | Once, post-op | manual |
| Monthly compliance archival | Once a month, retain checkpoint files | `cron` + offline archive |

The `create` subcommand is **idempotent**: if there are no new rows in the target audit table since the last checkpoint, it returns `{"status":"noop"}` and exits 0. Safe to run as often as desired.

---

## 3. Key management

### 3.1 Generation (one-time, off-box)

```bash
# Generate a fresh keypair. Do this on Toto's laptop, NOT on the VPS.
node dist/edits/scripts/audit-checkpoint-cli.js gen-key --out-dir /Users/toto/secure/nox-audit-keys
```

Outputs:

- `audit-checkpoints-private-<fingerprint>.b64` (mode `0600`, **NEVER commit to git**)
- `audit-checkpoints-public-<fingerprint>.b64` (mode `0644`)
- JSON summary including the fingerprint to cross-reference in `docs/AUDIT-PUBKEY.md`

Both files contain the base64 of the raw 32-byte Ed25519 halves — no PEM wrapper. The fingerprint is `sha256(public_key_raw)[:16]` (first 16 hex chars). Long enough to detect substitution (64 bits) yet short enough to read aloud over a phone call.

### 3.2 Private-key storage

**Inviolable rules:**

1. The private key **NEVER touches the VPS**.
2. The private key is **NEVER in git** (no exception, including a placeholder).
3. The private key is **NEVER pasted in chat, email, or any system Anthropic-style messaging stores** — they index conversation content.

**Recommended setup (defense in depth):**

| Storage | Purpose | Recovery |
|---|---|---|
| Toto's laptop (`~/Documents/Vault/`) encrypted FileVault | Primary | Laptop loss → restore from #2 |
| YubiKey FIDO2 / PIV slot OR password manager item (1Password, Bitwarden) | Secondary | Laptop wipe → re-export from manager |
| Paper backup (printed base64 in a sealed envelope, fireproof safe) | Tertiary (cold) | Both digital copies lost — last resort |

Paper backup format: 32 bytes base64 = 44 chars. Two lines, printed in `Courier` or `Inconsolata` font (no ambiguous `0/O/l/1`). Include the public-key fingerprint on the same page so the auditor can cross-check during recovery.

### 3.3 Public-key publication

After `gen-key`:

```bash
# 1. Copy the public key + fingerprint into the published doc
cat /Users/toto/secure/nox-audit-keys/audit-checkpoints-public-<fp>.b64

# 2. Append/replace the entry in docs/AUDIT-PUBKEY.md with the new fingerprint
#    + base64 + ISO date + revocation policy entry for the prior key (if rotating)

# 3. git commit -m "audit(pubkey): rotate to fingerprint <fp> from <fp_old>"
```

For routine cron-driven verification on the VPS, the public key (NOT private) can be deployed to `/etc/nox-mem/audit-checkpoints-public.b64` (mode `0644`) and the verifier reads it from there:

```bash
NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  audit-checkpoint verify-chain --scope all --key-file /etc/nox-mem/audit-checkpoints-public.b64
```

### 3.4 Rotation

Single passphrase / single keypair v1 (per `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md` §11.2 "multi-key parked"). To rotate:

1. Gen new key (Section 3.1).
2. Publish new public key in `docs/AUDIT-PUBKEY.md`, mark the old fingerprint as `RETIRED <date>`. Keep the old entry forever — auditors checking older checkpoints still need it.
3. The next `create` call signs with the new private key. Old checkpoints remain valid under the OLD key (stored `public_key_b64` in each row is self-contained).
4. Verifier passes the matching public key per checkpoint — or chains both keys during a transition period (NOT yet implemented; verify-chain currently accepts a single key, fails per-row if mismatch).

Rotation cadence: **at least every 24 months** (cryptographic hygiene) or **immediately on suspected compromise**.

---

## 4. Auditor workflow (third-party verification, OFFLINE)

This is the moneyshot — the auditor does not need to trust nox-mem.

### 4.1 Inputs the auditor needs

1. **The audit_checkpoints table** — exported as SQLite file (or JSON/CSV dump).
2. **The published public key** — from `docs/AUDIT-PUBKEY.md` or a notarized PDF copy.
3. **The audit table being verified** — `ops_audit` or `reads_audit`, same SQLite file or dump.

The auditor does NOT need:

- The nox-mem source code (the verification algorithm is published in this doc + `audit-checkpoints.ts`).
- A live connection to the VPS.
- Any cooperation from the operator after the initial export.

### 4.2 Verification procedure

```bash
# 1. Open the auditor's working directory
cd /audit-evidence/

# 2. Confirm the public key fingerprint matches the one in the published doc
sha256sum public-key.b64 | awk '{print substr($1, 1, 16)}'
# → should match the fingerprint in docs/AUDIT-PUBKEY.md

# 3. Point the verifier at the exported DB
NOX_DB_PATH=/audit-evidence/nox-mem.db \
  audit-checkpoint verify-chain --scope all --key-file /audit-evidence/public-key.b64

# 4. Inspect the JSON output
# {
#   "status": "ok",
#   "scopes": {
#     "ops":   { "total": 743, "verified": 743, "broken": 0, "breaks": [], "errors": {} },
#     "reads": { "total":  91, "verified":  91, "broken": 0, "breaks": [], "errors": {} }
#   }
# }
```

If `broken > 0`, the `breaks` array lists each tampered checkpoint, and `errors[<id>]` explains exactly which range failed (hash mismatch with prev_last_id / last_id endpoints). The auditor can then drill into the exact row range that diverged — forensic actionable signal, not just a yes/no.

### 4.3 What `valid: true` proves

- The set of audit rows in `(prev_last_id, last_id]` for each checkpoint has the exact hash that was signed at checkpoint time.
- The signature is valid under the public key the auditor supplied (i.e. the published one).

What it does NOT prove:

- That the checkpoint cadence captured every adversary action (an adversary could insert + delete + checkpoint, but D56's intent is that the rotating cron + Toto's offline signing makes that window narrow).
- That `nox-mem` correctly produced audit rows in the first place (the audit hook coverage is a separate audit dimension — see ops_audit Issue #3 2026-05-21).

---

## 5. Cron schedule (recommended)

```cron
# /etc/cron.d/nox-mem-audit-checkpoint
#
# Hourly checkpoint of ops_audit + reads_audit. Idempotent — no-op when no
# new rows since last checkpoint. Uses the OFF-BOX private key mounted via
# tmpfs (NOT on disk; private key staged at boot only).
#
# Path note: NOX_DB_KEY must be in /root/.openclaw/.env for encrypted DBs.

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin
NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
SHELL=/bin/bash

# Hourly ops checkpoint (signed)
3 * * * * root . /root/.openclaw/.env; /usr/local/bin/node /opt/nox-mem/dist/edits/scripts/audit-checkpoint-cli.js create --scope ops   --key-file /run/nox-mem-keys/private.b64 >> /var/log/nox-mem/audit-checkpoint.log 2>&1

# Hourly reads checkpoint (signed)
4 * * * * root . /root/.openclaw/.env; /usr/local/bin/node /opt/nox-mem/dist/edits/scripts/audit-checkpoint-cli.js create --scope reads --key-file /run/nox-mem-keys/private.b64 >> /var/log/nox-mem/audit-checkpoint.log 2>&1

# Daily self-verification (sanity guard against silent failures)
15 2 * * * root . /root/.openclaw/.env; /usr/local/bin/node /opt/nox-mem/dist/edits/scripts/audit-checkpoint-cli.js verify-chain --scope all --key-file /etc/nox-mem/public.b64 >> /var/log/nox-mem/audit-verify.log 2>&1 || logger -t nox-mem-audit -p user.crit "CHECKPOINT CHAIN VERIFICATION FAILED"
```

**Private-key on tmpfs caveat:** the cron schedule above assumes `/run/nox-mem-keys/` is a tmpfs mount populated at boot from a sealed source (e.g. systemd-credentials, HashiCorp Vault agent, age-encrypted file unsealed with TPM). Putting the private key on the VPS at all is a defense-in-depth weakening of D56 (which says "off-box"); the alternative is **periodic offline signing** — Toto exports the unsigned-pending rows to laptop weekly, signs in batch, re-imports. The current `create` subcommand is single-shot create-AND-sign; the pending-then-batch-sign flow is reserved for P4.1 (schema already supports it via `signature_b64 IS NULL` semantics).

For organizations that prefer pure off-box signing today, the cron schedule reduces to the verify-only line — checkpoints accumulate as `signature_b64 NULL` rows (proposed by the cron, signed by Toto on laptop weekly).

---

## 6. Operational checklist

### 6.1 First-time setup

- [ ] Run `gen-key` on Toto's laptop (off the VPS)
- [ ] Append the public key fingerprint + base64 to `docs/AUDIT-PUBKEY.md`
- [ ] Stash the private key per Section 3.2 (laptop + manager + paper)
- [ ] Decide signing-cadence (real-time on VPS via tmpfs, OR weekly batch off-box)
- [ ] Deploy public key to `/etc/nox-mem/public.b64` on the VPS
- [ ] Set up cron per Section 5
- [ ] Trigger initial checkpoint manually to validate end-to-end:
  ```bash
  NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    audit-checkpoint create --scope ops --key-file /tmp/priv.b64
  audit-checkpoint verify --id 1 --key-file /etc/nox-mem/public.b64
  ```
- [ ] Document the fingerprint + initial-checkpoint-id in `docs/HANDOFF.md`

### 6.2 Periodic ops review

Monthly:

- [ ] `audit-checkpoint verify-chain --scope all --key-file ...` exits 0
- [ ] No `signature_b64 IS NULL` checkpoints older than the chosen signing-cadence window
- [ ] Backup of audit_checkpoints rows to off-site storage (encrypted)
- [ ] Public key fingerprint in `docs/AUDIT-PUBKEY.md` matches the one in `/etc/nox-mem/public.b64`

Quarterly:

- [ ] Spot-check: pick a recent checkpoint, tamper a row in `ops_audit` in a TEST clone, confirm `verify` reports `hash mismatch` with the correct range info
- [ ] Validate cron is firing (last log entry < 90 min for hourly)

Annually:

- [ ] Audit fire-drill: hand a fresh checkpoint dump to a non-nox-mem-engineer, watch them reproduce the verify procedure with only the published public key and the algorithm spec. Time-box: 15 min.

---

## 7. Reference — internals worth knowing

### 7.1 Canonical-JSON contract

The bytes that get hashed for each audit-row range are:

```
{"<col_a>":<val>,"<col_b>":<val>,...,"<col_z>":<val>}\n
{"<col_a>":<val>,...}\n
...
{"<col_a>":<val>,...}\n
```

Rules:

- One JSON object per row, keys sorted alphabetically.
- BigInts → decimal-string. Numbers → JSON number. Strings → JSON string. NULL/undefined → JSON null. Buffers → base64 string.
- Rows joined by `\n`, trailing `\n` on the last row.
- Empty range → literal bytes `<empty>\n` (so an empty checkpoint is distinguishable from a one-row checkpoint of the literal string `<empty>`).
- UTF-8 encoding.

Then `sha256(<concatenation>)` is the `sha256_hex` column.

### 7.2 Signature payload

The bytes signed by Ed25519 are a **separate** canonical JSON encoding the checkpoint metadata that binds the hash to its position in the chain:

```json
{"last_id":<int>,"prev_last_id":<int|null>,"scope":"<str>","sha256_hex":"<hex>","ts":<int>}
```

Same canonical-JSON rules (sorted keys, etc). Ed25519 detached signature → base64 → `signature_b64`.

This prevents replay (move a valid hash from checkpoint N to checkpoint M) because `prev_last_id` and `last_id` are part of the signature.

### 7.3 Algorithm pin

- **Hash:** SHA-256 (NIST FIPS 180-4)
- **Signature:** Ed25519 (RFC 8032)
- **Encoding:** raw 32-byte halves base64-encoded
- **Canonical JSON:** custom (sorted keys, BigInt-aware, see `_internals.canonicalRowJson` in `audit-checkpoints.ts`)

Out-of-scope quantum-resistance per spec §11 — revisit at the AES-256 retirement date (estimated 2030+).

---

## 8. Cross-references

- `staged-A2-T3/edits/src/lib/audit-checkpoints.ts` — module source
- `staged-A2-T3/edits/src/lib/audit-checkpoints-schema.sql` — DDL source-of-truth
- `staged-A2-T3/edits/scripts/audit-checkpoint-cli.ts` — CLI
- `staged-A2-T3/edits/src/lib/__tests__/audit-checkpoints.test.ts` — 23 tests
- `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md` — design spec
- `docs/DECISIONS.md` D54-D58 — locked defaults (D56 specifically for this phase)
- `docs/A2-TIER3-READS-AUDIT-GUIDE.md` — sibling P3 doc
- `docs/A2-TIER3-MIGRATION-RUNBOOK.md` — sibling P2 doc
- `docs/AUDIT-PUBKEY.md` — public-key publication target (create on first deploy)
