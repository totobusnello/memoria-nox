# nox-mem Audit Public Key (Ed25519)

This file contains the **public verification key** for nox-mem's A2 Tier 3 audit checkpoint
system. Every signed forensic checkpoint stored in the `audit_checkpoints` table was signed
with the corresponding private key. Auditors use this public key to verify the integrity of
the checkpoint chain without needing access to any secrets.

## Key Metadata

| Field | Value |
|---|---|
| Algorithm | Ed25519 (RFC 8032) |
| Key encoding | Raw 32-byte public key, base64url-safe standard encoding |
| Fingerprint | `b6c84b1fd751ab56` (SHA-256 of raw key bytes, first 16 hex chars) |
| Generated | 2026-05-24 |
| Purpose | Verify `audit_checkpoints` rows in nox-mem production DB |

## Public Key (Base64, raw 32 bytes)

```
GdNgLSCH5j07NLbZF1yHSGw3YFrQ9hDhH6wHq9DOm+A=
```

> **Note:** This is the raw 32-byte Ed25519 public key encoded in standard base64, NOT a
> PEM-wrapped key. The audit-checkpoint-cli and the `audit-checkpoints` library consume it
> directly in this format.

## Smoke Test Result

Verified 2026-05-24 via direct Node.js `crypto.sign`/`crypto.verify` round-trip:

```json
{
  "smoke": "PASS",
  "priv_bytes": 32,
  "pub_bytes": 32,
  "fingerprint": "b6c84b1fd751ab56",
  "sig_length_bytes": 64
}
```

## Auditor Verification Workflow

### Prerequisites

- Node.js >= 18 (Ed25519 native support)
- Access to the staged CLI: `staged-A2-T3/dist/edits/scripts/audit-checkpoint-cli.js`
- Read access to the nox-mem DB (`NOX_DB_PATH` set)

### Step 1 — Save the public key locally

```bash
# Copy the public key value from this file into a local file:
echo -n "GdNgLSCH5j07NLbZF1yHSGw3YFrQ9hDhH6wHq9DOm+A=" > /tmp/audit-pub.b64
```

### Step 2 — Verify a single checkpoint

```bash
export NOX_DB_PATH=/path/to/nox-mem.db
node staged-A2-T3/dist/edits/scripts/audit-checkpoint-cli.js \
  verify \
  --id <checkpoint_id> \
  --key-file /tmp/audit-pub.b64
```

Expected successful output:

```json
{
  "status": "ok",
  "id": 1,
  "valid": true,
  ...
}
```

### Step 3 — Verify the full chain

```bash
export NOX_DB_PATH=/path/to/nox-mem.db
node staged-A2-T3/dist/edits/scripts/audit-checkpoint-cli.js \
  verify-chain \
  --scope all \
  --key-file /tmp/audit-pub.b64
```

Exit code 0 means the chain is intact. Exit code 3 means a checkpoint is invalid or the
chain is broken — escalate immediately.

### Step 4 — Confirm fingerprint matches this document

```bash
# The fingerprint embedded in each checkpoint row must match the value above.
# Any mismatch means a different key signed that checkpoint — treat as anomaly.
node -e "
  const k = 'GdNgLSCH5j07NLbZF1yHSGw3YFrQ9hDhH6wHq9DOm+A=';
  const raw = Buffer.from(k, 'base64');
  const { createHash } = require('crypto');
  console.log(createHash('sha256').update(raw).digest('hex').slice(0, 16));
"
# Expected: b6c84b1fd751ab56
```

## References

- Checkpoint implementation: `staged-A2-T3/edits/src/lib/audit-checkpoints.ts`
- CLI reference: `staged-A2-T3/edits/scripts/audit-checkpoint-cli.ts`
- Key management guide: [`docs/A2-TIER3-CHECKPOINTS-GUIDE.md`](A2-TIER3-CHECKPOINTS-GUIDE.md)
- Deployment runbook: [`docs/A2-TIER3-DEPLOYMENT-MASTER.md`](A2-TIER3-DEPLOYMENT-MASTER.md)
- A2 Tier 3 Phase A description: `docs/A2-TIER3-DEPLOYMENT-MASTER.md` § Phase A

## Security Notes

- The **private key** is stored offline (operator's 1Password or encrypted local storage).
  It is never committed to this repository.
- Rotating this key requires generating a new keypair, updating this file via PR, and
  re-signing all historical checkpoints (or documenting the rotation boundary by checkpoint ID).
- If you suspect key compromise, open a security incident immediately and rotate before
  next checkpoint creation.
