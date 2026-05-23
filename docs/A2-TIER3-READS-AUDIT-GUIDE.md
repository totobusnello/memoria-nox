# A2 Tier 3 — `reads_audit` Operator Guide

> Status: staged in `staged-A2-T3/edits/` — P3 of the A2 Tier 3 sequence.
> Lands LIVE on prod nox-mem when src/lib/reads-audit.ts + reads-audit-schema.sql + scripts/reads-audit-sweep.ts are promoted from `staged-A2-T3/edits/` to `src/`/`scripts/`.
>
> Author: A2 Tier 3 P3 (2026-05-24).
> Decisions cravadas: **D55** (default OFF, opt-in via `NOX_READS_AUDIT=1`) + **D58** (env-driven retention default 90d + archive policy). See `docs/DECISIONS.md` 2026-05-24 entry.

---

## 1. What this is

`reads_audit` is an **opt-in append-only table** that records every search/answer/read operation that runs through the `withReadAudit()` wrapper. It is the **read-side complement to `ops_audit`** (which already records destructive writes — reindex/consolidate/compact/etc.).

The pair (`ops_audit` + `reads_audit`) is the foundation of the **A2 Autonomy pillar** for regulated tier customers — Toto wants to be able to hand an auditor a `nox-mem audit verify` output that proves "this read happened, this row was untouched between then and now". P3 ships the read trail; P4 (next phase) adds signed checkpoints (Ed25519 manual signing per **D56**).

### What gets recorded (per call)

| Column | Meaning |
|---|---|
| `id` | autoincrement PK |
| `ts` | epoch milliseconds (INTEGER, trigger-enforced) |
| `query` | sanitized + truncated ≤200 chars; OR sha256-hex if `NOX_READS_AUDIT_HASH_QUERIES=1` |
| `k` | top-k requested by the search call (NULL if not applicable) |
| `n_results` | rows returned post-rerank (derived from `Array.length` / `.results.length` / explicit `.n_results`) |
| `latency_ms` | wall-clock duration of the wrapped `fn()` |
| `user_id` | `sha256(salt + user_id)` if `NOX_READS_AUDIT_USER_HASH=<salt>`; NULL otherwise |
| `source_app` | free-form (`cli` / `http` / `mcp` / `cron` / custom) |

What is **NOT** recorded: raw embeddings, raw user_id, raw stack traces, full result payloads, plaintext queries when hash mode is on.

---

## 2. When to enable

The wrapper is **default OFF** (D55). Reasons to flip it on:

| Trigger | Recommendation |
|---|---|
| LGPD / HIPAA / SOC2 audit prep | Yes — enable + hash mode + user_id hashing |
| Forensic investigation of suspected exfiltration | Yes — enable, gather a week of data, then disable again |
| Debugging "search returns nothing" patterns in dev | Maybe — enable locally, NOT in prod (privacy first) |
| Default prod deploy with no compliance posture | **No** — keep OFF (Autonomy pillar default) |
| You want to see what queries hit `/api/answer` | Maybe — temporary, off again after analysis |

Cost: each audited read is a single indexed INSERT on a small table. Measured overhead: ~+0.3-0.5 ms p50 per call (search itself is ~940ms p50 hybrid — the audit row is in the noise).

---

## 3. Configuration matrix

All env vars are read at the START of every audited call — no restart needed to flip flags.

| Env var | Default | Effect |
|---|---|---|
| `NOX_READS_AUDIT` | unset (off) | `=1` enables the wrapper. Any other value (including `0`) keeps it off. |
| `NOX_READS_AUDIT_HASH_QUERIES` | unset | `=1` stores `sha256-hex(query)` instead of plaintext (defense-in-depth for regulated tier). |
| `NOX_READS_AUDIT_USER_HASH` | unset | If set + caller passes `user_id`, stored value is `sha256(salt + user_id)`. **Required** when caller passes `user_id` — else the wrapper throws (fail-closed). |
| `NOX_READS_AUDIT_RETENTION_DAYS` | `90` | Cutoff for the sweep CLI. |
| `NOX_READS_AUDIT_ARCHIVE_PATH` | sibling of `NOX_DB_PATH` named `nox-mem-audit-archive.db` | Where the sweep moves old rows. |
| `NOX_DB_PATH` | `${OPENCLAW_WORKSPACE}/tools/nox-mem/nox-mem.db` | Main DB. |
| `NOX_DB_KEY` | unset | If set, archive DB is opened with same cipher key (D54). |

### Quick-start recipes

**Non-regulated default (do nothing):**
```bash
# .env / systemd EnvironmentFile
# (no audit env vars — wrapper is a pure pass-through)
```

**Regulated tier minimum (audit on, queries hashed, no user-id collection):**
```bash
NOX_READS_AUDIT=1
NOX_READS_AUDIT_HASH_QUERIES=1
```

**Regulated tier with stable user identifier (HIPAA-style):**
```bash
NOX_READS_AUDIT=1
NOX_READS_AUDIT_HASH_QUERIES=1
NOX_READS_AUDIT_USER_HASH=<long-random-base64-salt>
```
Then the caller (HTTP API / MCP server) is expected to pass `user_id: <stable_id>` into the `withReadAudit()` call site. The stored value will be `sha256(salt + ':' + user_id)` — auditor can correlate across sessions but cannot deanonymize without the salt.

**Rotation:** changing `NOX_READS_AUDIT_USER_HASH` invalidates linkability of historical rows. Acceptable trade-off: rotate annually (or after a salt exposure incident) and document the cutover date.

---

## 4. Privacy considerations

1. **Default OFF** is the design intent (D55). The Autonomy pillar tagline is *"data é sua, provider sua escolha"* — we do NOT collect what the user didn't ask us to collect.
2. **Plaintext queries are stored if `NOX_READS_AUDIT_HASH_QUERIES` is unset.** For a non-regulated deploy this is fine — the operator IS the user. For multi-tenant or compliance deploys, set hash mode.
3. **NUL bytes + control chars are stripped** from queries before storage (prevents binary embedding leakage if a caller accidentally passes a Float32Array buffer through).
4. **Raw user_id is NEVER stored.** The wrapper REFUSES to bind a raw `user_id` unless the operator has explicitly set `NOX_READS_AUDIT_USER_HASH`. Fail-closed by design.
5. **Append-only on disk.** Rows cannot be DELETE'd or UPDATE'd via the main app handle — triggers fire `RAISE(ABORT)`. The only "purge" path is the sweep CLI (which actually copies-not-deletes; main table grows monotonically; archive is a separate file).
6. **Encryption at rest.** When `NOX_DB_KEY` is set (D54 SQLCipher), the reads_audit rows are encrypted alongside the rest of nox-mem.db. The archive DB inherits the same key — `cp archive.db /elsewhere` does not leak data without the key.

---

## 5. Operator runbook

### 5.1 Enable on prod (one-time)

```bash
ssh root@<vps>
cd /root/.openclaw
# Append to .env (or systemd EnvironmentFile)
cat >> .env <<'EOF'

# A2 Tier 3 / P3 — reads_audit (opt-in)
NOX_READS_AUDIT=1
NOX_READS_AUDIT_HASH_QUERIES=1
NOX_READS_AUDIT_RETENTION_DAYS=90
EOF

systemctl restart nox-mem-api nox-mem-watcher
```

Verify:
```bash
# After a few search calls have run...
curl http://127.0.0.1:18802/api/health | jq '.readsAudit // "endpoint not yet wired"'
# Or inspect the table directly (read-only):
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT count(*) FROM reads_audit"
```

> If `NOX_DB_KEY` is set, use `nox-mem` CLI or a SQLCipher-aware client. Plain `sqlite3` will print "file is not a database".

### 5.2 Sweep cron (weekly, recommended per D58)

Daily is overkill — the table grows slowly even on heavy workloads. Weekly Sunday 03:00 BRT (06:00 UTC) suffices.

```cron
# /etc/cron.d/nox-mem-reads-audit-sweep
0 6 * * 0 root set -a; source /root/.openclaw/.env; set +a; \
  /usr/local/bin/node /root/.openclaw/workspace/tools/nox-mem/dist/scripts/reads-audit-sweep.js \
    --retention-days "${NOX_READS_AUDIT_RETENTION_DAYS:-90}" \
    --archive-path /var/backups/nox-mem/audit-archive.db \
  >> /var/log/nox-mem/reads-audit-sweep.log 2>&1
```

Note the `set -a; source .env; set +a` preamble — same pattern as `[[nox-mem-cli-env-source-required]]`. Without it, `NOX_DB_KEY` won't be in cron's env and the sweep will silently fail on encrypted DBs.

Manual run:
```bash
# Dry-run first (reports counts, doesn't write)
node dist/scripts/reads-audit-sweep.js \
  --retention-days 90 \
  --archive-path /var/backups/nox-mem/audit-archive.db \
  --dry-run

# Real run
node dist/scripts/reads-audit-sweep.js \
  --retention-days 90 \
  --archive-path /var/backups/nox-mem/audit-archive.db
```

### 5.3 Sweep semantics (READ THIS CAREFULLY)

Per **D58**, the sweep does NOT delete from the main table. It COPIES rows older than the cutoff into the archive DB. The main table is append-only (trigger-enforced); attempting to DELETE from it produces `RAISE(ABORT, 'reads_audit is append-only')`.

> **Why?** Append-only is the security property that lets an auditor say "I can verify nothing was tampered with". DELETE-on-sweep would break that. The archive policy gives operators a way to query "old + new" without breaking the invariant: `SELECT * FROM main.reads_audit UNION ALL SELECT * FROM archive.reads_audit`.

Consequence: **storage grows monotonically** on the main DB. Worst case projection (heavy dev usage, ~10 queries/second through the API): ~864k rows/day × 90 bytes/row ≈ 75 MB/day on the main DB, plus identical amount in archive. Over 1 year: ~27 GB main + ~27 GB archive ≈ 54 GB total. That's well within VPS disk budget but worth eyeballing quarterly via:

```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT count(*) AS rows, sum(length(query) + length(coalesce(user_id,'')) + 80) AS bytes_est FROM reads_audit"
```

If the main table grows beyond an operationally comfortable size (~10 GB say), the **only** safe purge path is via the SQLCipher VACUUM+rebuild ceremony (offline, scheduled maintenance window). Do NOT manually `DELETE` — the trigger will fire.

### 5.4 Query across archive (operator pattern)

```sql
-- One-shot query that unions main + archive
ATTACH DATABASE '/var/backups/nox-mem/audit-archive.db' AS archive KEY '<your-key>';
SELECT * FROM reads_audit WHERE ts >= ?cutoff
UNION ALL
SELECT * FROM archive.reads_audit WHERE ts >= ?cutoff
ORDER BY ts DESC LIMIT 100;
DETACH DATABASE archive;
```

For programmatic access from JS:
```js
import { getReadsAuditStats } from '../staged-A2-T3/edits/src/lib/reads-audit.js';
const stats = getReadsAuditStats();
// → { total_rows: BigInt, rows_24h: BigInt, oldest_ts: BigInt|null, newest_ts: BigInt|null }
```

### 5.5 Disable + cleanup (audit period ends)

```bash
# Stop recording new rows
sed -i '/^NOX_READS_AUDIT=/d' /root/.openclaw/.env
systemctl restart nox-mem-api nox-mem-watcher

# Optionally pause the sweep cron — table won't grow once recording is off
sed -i '/reads-audit-sweep/d' /etc/cron.d/nox-mem-reads-audit-sweep

# Existing rows STAY on disk (append-only). If you must remove them:
#  - Offline maintenance window
#  - Stop nox-mem-api + watcher
#  - SQLCipher VACUUM cycle that excludes reads_audit (manual SQL — out of scope here)
```

---

## 6. Integration: how to wrap a search call

This is the snippet for the eventual prod migration (when `staged-A2-T3/edits/` gets promoted into `src/`):

```typescript
// src/server/api-server.ts (or wherever the search HTTP handler lives)
import { withReadAudit } from '../lib/reads-audit.js';

app.post('/api/search', async (req, res) => {
  const { query, k = 10 } = req.body;
  // Audit the call. If NOX_READS_AUDIT is unset, this is a pure pass-through.
  const results = await withReadAudit(
    {
      op_name: 'search',
      query,                         // sanitized + truncated in the wrapper
      k,
      source_app: 'http',
      user_id: req.user?.id,         // requires NOX_READS_AUDIT_USER_HASH env or wrapper throws
    },
    () => doHybridSearch(query, k),
  );
  res.json({ results });
});
```

Same pattern for MCP tool handlers, CLI subcommands, and `/api/answer`.

---

## 7. Testing your enable

A one-liner smoke test (run as the same UID as the API service):

```bash
set -a; source /root/.openclaw/.env; set +a
NOX_READS_AUDIT=1 node -e "
  const { withReadAudit, getReadsAuditStats } = require('/path/to/dist/edits/src/lib/reads-audit.js');
  await withReadAudit(
    { op_name: 'smoke', query: 'hello', k: 5, source_app: 'cli' },
    async () => ['fake-result'],
  );
  console.log(getReadsAuditStats());
" | jq .
# Expected:
# {
#   "total_rows": 1,
#   "rows_24h": 1,
#   "oldest_ts": <epoch ms>,
#   "newest_ts": <same epoch ms>
# }
```

Then disable and confirm no new rows:
```bash
unset NOX_READS_AUDIT
# Re-run the search — getReadsAuditStats() should still return total_rows=1 (no new INSERT)
```

---

## 8. Known limitations & follow-ups

| Limitation | Plan |
|---|---|
| `/api/health` doesn't expose readsAudit stats yet | P4 — same PR as audit checkpoints |
| No call-site instrumentation in prod search/answer paths yet | P5 promotion of `staged-A2-T3/edits/` → `src/` |
| Sweep cron is operator-managed, not auto-installed by the package | By design (D58: env-driven, not opinionated about systemd/cron flavor) |
| Archive DB has same cipher key as main | Intentional (D54); cross-key migration is out of A2 Tier 3 scope |
| `audit_checkpoints` Merkle-light chain not wired in P3 | P4 (D56 — Ed25519 manual signing) |
| `nox-mem audit verify` CLI not in P3 | P4/P5 — operator-facing forensic tool |

---

## 9. Cross-references

- Recon spec: `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md` §4.3 F1 + §10 D-A2T3-2/5
- Decisions: `docs/DECISIONS.md` D54-D58 (2026-05-24)
- Parent pattern: `staged-1.7a/edits/op-audit.ts` (the write-side `withOpAudit()` wrapper)
- P1 PR #280 — SQLCipher key-open wire-up (`staged-A2-T3/edits/src/lib/db.ts`)
- P2 PR #286 — migration tool for encrypted ↔ plaintext
- Memory: `[[a1-op-audit-module]]`, `[[no-getdb-in-eval-scripts]]`, `[[sqlite-text-affinity-coerces-int-back]]`
