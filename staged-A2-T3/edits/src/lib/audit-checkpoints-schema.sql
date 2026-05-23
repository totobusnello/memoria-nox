-- staged-A2-T3/edits/src/lib/audit-checkpoints-schema.sql
--
-- A2 Tier 3 / Phase 4 — audit_checkpoints table schema (Ed25519 signed
-- forensic checkpoints over ops_audit / reads_audit rows).
--
-- Decisions resolved (docs/DECISIONS.md):
--   D56 (D-A2T3-3) — Ed25519 manual signing — public key publishable, reviewer
--                    doesn't need to trust nox-mem. Cron may propose unsigned
--                    rows (signature_b64 NULL); Toto signs offline in batch.
--                    P4 INITIAL release ships single-shot create-AND-sign path;
--                    pending-then-sign batch flow is a P4.1 extension (NULL
--                    signature_b64 reserved in schema for that).
--
-- Design pattern: parallel to ops_audit + reads_audit (same append-only
-- hardening). What is DIFFERENT vs reads_audit:
--   - audit_checkpoints rows store CRYPTOGRAPHIC EVIDENCE (sha256 + Ed25519
--     signature). A reviewer downloading this table + the published public
--     key can verify integrity of ops_audit / reads_audit OFFLINE, without
--     ever touching nox-mem source code or trusting the operator.
--   - The `metadata` JSON column captures everything an offline verifier
--     needs to RE-COMPUTE the hash: scope identifier, range of row ids
--     covered, count, schema version. This is deliberately self-contained
--     so an auditor can reconstruct the canonical bytestring that was
--     hashed without consulting the original DB.
--
-- INTEGER affinity enforcement on `ts` follows the same lesson as
-- ops_audit / reads_audit (memory `[[sqlite-text-affinity-coerces-int-back]]`
-- + ops_audit Issue #1A 2026-05-21).
--
-- Append-only enforcement (CWE-693) is unconditional for DELETE. UPDATE is
-- ALLOWED ONLY when transitioning a pending checkpoint (signature_b64 IS NULL)
-- into a signed one. This is the "batch sign offline" pathway from D56:
--   cron writes audit_checkpoints with signature_b64=NULL → Toto signs offline
--   on laptop → upload signed rows via `audit-checkpoint sign --batch` which
--   uses a one-shot UPDATE allowed by trg_audit_checkpoints_no_update_signed.
-- Once `signature_b64 IS NOT NULL`, the row becomes fully immutable.
--
-- Idempotent — uses CREATE ... IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS audit_checkpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  -- ts: epoch milliseconds. INTEGER affinity ENFORCED by trigger below.
  ts INTEGER NOT NULL,
  -- scope: which audit table this checkpoint covers. Free-form TEXT so future
  -- callers can add scopes (e.g. 'kg_audit') without schema change, but the
  -- wrapper validates against the known set ('ops', 'reads').
  scope TEXT NOT NULL,
  -- last_id: the MAX(id) from <scope>_audit at checkpoint time. Used by the
  -- next checkpoint as the lower-bound (inclusive of last_id + 1) to define
  -- the row range. NULL is INVALID — every checkpoint covers at least one row
  -- OR an explicit "empty range" via last_id = previous_last_id (idempotent).
  last_id INTEGER NOT NULL,
  -- sha256_hex: 64-char lowercase hex digest of the canonical JSON
  -- representation of all rows in (prev_last_id, last_id] for this scope.
  -- Canonicalization rules are pinned in audit-checkpoints.ts (sorted keys,
  -- INTEGER bigints serialized as decimal strings — see canonicalRowJson).
  sha256_hex TEXT NOT NULL,
  -- signature_b64: base64-encoded Ed25519 detached signature over the bytes
  -- of (id || ts || scope || last_id || sha256_hex), as canonical-JSON. May
  -- be NULL when row is in PENDING state (cron wrote, Toto hasn't signed yet
  -- — D56 batch sign workflow).
  signature_b64 TEXT,
  -- public_key_b64: base64-encoded Ed25519 public key that paired with the
  -- private key used to produce signature_b64. Stored INLINE so the row is
  -- self-contained: an offline verifier needs only this table + the
  -- expected fingerprint (and optionally the published pubkey for double-
  -- check). NULL iff signature_b64 IS NULL.
  public_key_b64 TEXT,
  -- metadata: JSON. Captures ENOUGH to re-compute sha256_hex offline:
  --   {
  --     "prev_last_id": <int|null>,   // start of range (exclusive); null for genesis
  --     "row_count": <int>,           // last_id - prev_last_id (sanity check)
  --     "schema_version": <int>,      // ops_audit / reads_audit DDL version
  --     "ts_iso": "2026-05-23T..."    // human-readable ts
  --   }
  metadata TEXT NOT NULL DEFAULT '{}'
);

-- ts index: most common query (recent checkpoints, retention reporting).
CREATE INDEX IF NOT EXISTS idx_audit_checkpoints_ts ON audit_checkpoints(ts);

-- Scope + ts index: chain-walk lookups (latest per-scope, range queries).
CREATE INDEX IF NOT EXISTS idx_audit_checkpoints_scope_ts ON audit_checkpoints(scope, ts);

-- Append-only enforcement: DELETE is ALWAYS blocked.
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_no_delete
  BEFORE DELETE ON audit_checkpoints
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints is append-only (CWE-693 protection)');
  END;

-- UPDATE allowed ONLY for the pending → signed transition (signature_b64
-- transition NULL → non-NULL). Any other mutation is REJECTED. After a row
-- has signature_b64 set, it is fully immutable.
--
-- The trigger also enforces that the public_key_b64 is set concurrently
-- with signature_b64 — they form an inseparable pair.
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_no_update_signed
  BEFORE UPDATE ON audit_checkpoints
  WHEN
    -- Block: already signed (OLD has signature) → row is immutable
    OLD.signature_b64 IS NOT NULL
    OR
    -- Block: attempting to mutate non-signature columns
    NEW.ts != OLD.ts
    OR NEW.scope != OLD.scope
    OR NEW.last_id != OLD.last_id
    OR NEW.sha256_hex != OLD.sha256_hex
    OR (NEW.metadata IS NOT NULL AND OLD.metadata IS NOT NULL AND NEW.metadata != OLD.metadata)
    OR
    -- Block: clearing a signature (downgrade attack)
    (NEW.signature_b64 IS NULL AND OLD.signature_b64 IS NOT NULL)
    OR
    -- Block: signature without matching public key
    (NEW.signature_b64 IS NOT NULL AND NEW.public_key_b64 IS NULL)
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints rows are immutable except for the pending→signed transition');
  END;

-- INTEGER affinity enforcement on ts (CWE-704 style — type confusion).
-- Lesson cravada from ops_audit 2026-05-21 Issue #1A.
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_ts_must_be_int
  BEFORE INSERT ON audit_checkpoints
  FOR EACH ROW WHEN typeof(NEW.ts) != 'integer'
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints.ts must be INTEGER epoch ms — got non-integer value');
  END;

-- INTEGER affinity on last_id (same rationale; range arithmetic depends on it).
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_last_id_must_be_int
  BEFORE INSERT ON audit_checkpoints
  FOR EACH ROW WHEN typeof(NEW.last_id) != 'integer'
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints.last_id must be INTEGER — got non-integer value');
  END;

-- Scope must be one of the known audit tables. Free-form TEXT allows future
-- extension but the trigger enforces current allowlist. To add a scope, the
-- trigger DDL has to be updated explicitly (intentional friction).
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_valid_scope
  BEFORE INSERT ON audit_checkpoints
  FOR EACH ROW WHEN NEW.scope NOT IN ('ops', 'reads')
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints.scope must be one of: ops, reads');
  END;

-- sha256_hex format check — 64 lowercase hex chars. Defense vs malformed
-- inserts that would defeat offline verification.
CREATE TRIGGER IF NOT EXISTS trg_audit_checkpoints_sha256_format
  BEFORE INSERT ON audit_checkpoints
  FOR EACH ROW WHEN length(NEW.sha256_hex) != 64
    OR NEW.sha256_hex GLOB '*[^0-9a-f]*'
  BEGIN
    SELECT RAISE(ABORT, 'audit_checkpoints.sha256_hex must be 64-char lowercase hex');
  END;
