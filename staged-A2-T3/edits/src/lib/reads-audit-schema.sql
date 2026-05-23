-- staged-A2-T3/edits/src/lib/reads-audit-schema.sql
--
-- A2 Tier 3 / Phase 3 — reads_audit table schema (opt-in read-path audit).
--
-- Decisions resolved (docs/DECISIONS.md):
--   D55 (D-A2T3-2) — default OFF, opt-in via NOX_READS_AUDIT=1
--   D58 (D-A2T3-5) — retention env-driven default 90d, archive (NOT delete)
--
-- Design pattern: parallel to ops_audit (src/lib/op-audit.ts).
--   - Append-only (BEFORE DELETE + BEFORE UPDATE → RAISE(ABORT))
--   - INTEGER ts enforcement (lesson cravada 2026-05-21 ops_audit Issue #1A/#1C —
--     better-sqlite3 binds JS number as REAL; need CAST + typeof='integer' guard)
--   - db_source explicit (no implicit 'unknown' fallback — Issue #3B precedent)
--   - Indexes on (ts) + (op_name, ts) for retention sweep + reporting
--
-- Hardening choices vs ops_audit:
--   - reads_audit has NO running-state lifecycle (reads are atomic — succeed or
--     fail in <1s typically). All rows are immediately terminal. Therefore
--     trg_no_update is unconditional (not WHEN OLD.status terminal).
--   - reads_audit allows query plaintext (sanitized + truncated ≤200 chars) per
--     task brief §1. Optional hash-mode (NOX_READS_AUDIT_HASH_QUERIES=1) stores
--     sha256(query) instead — defense for regulated tier (recon §4.3 F1 intent).
--   - user_id is NULL by default. If NOX_READS_AUDIT_USER_HASH env is set and
--     caller provides user_id, the WRAPPER hashes it before INSERT — never store
--     raw PII.
--
-- This file is the source-of-truth schema. It is exec()'d once at first
-- enableReadsAudit() call. Idempotent — uses CREATE ... IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS reads_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  -- ts: epoch milliseconds. INTEGER affinity ENFORCED by trigger below.
  -- (Lesson: ops_audit had REAL-as-TEXT regression — see memory
  -- [[sqlite-text-affinity-coerces-int-back]] + Issue #1A 2026-05-21.)
  ts INTEGER NOT NULL,
  -- query: sanitized + truncated ≤200 chars (sanitization done in JS wrapper
  -- BEFORE bind — embeddings/binary stripped, NUL bytes removed). May contain
  -- sha256-hex if NOX_READS_AUDIT_HASH_QUERIES=1.
  query TEXT,
  -- k: requested top-k (Number param of search call). Optional (some ops don't
  -- have a k, e.g. /api/health). Bound as INTEGER via CAST in wrapper.
  k INTEGER,
  -- n_results: actual rows returned (post-filter, post-rerank). Bound as
  -- INTEGER via CAST.
  n_results INTEGER,
  -- latency_ms: wall-clock duration of fn() execution. INTEGER ms.
  latency_ms INTEGER,
  -- user_id: nullable. If provided by caller AND NOX_READS_AUDIT_USER_HASH is
  -- set, this column stores sha256(salt + user_id) — never raw. If env unset
  -- and caller still provides user_id, wrapper REFUSES (fail-closed — see
  -- recordRead() in reads-audit.ts).
  user_id TEXT,
  -- source_app: 'cli' | 'http' | 'mcp' | 'cron' | <custom>. Free-form TEXT
  -- (no enum at SQL layer; wrapper validates).
  source_app TEXT
);

-- Index on ts for retention sweep (WHERE ts < cutoff) — single most important
-- index since sweeper is the only "slow" read pattern.
CREATE INDEX IF NOT EXISTS idx_reads_audit_ts ON reads_audit(ts);

-- Compound index on (source_app, ts DESC) for byApp reporting if /api/health
-- exposes a breakdown in the future. Cheap (small fanout).
CREATE INDEX IF NOT EXISTS idx_reads_audit_app_ts ON reads_audit(source_app, ts DESC);

-- Append-only enforcement (CWE-693). Parallel to ops_audit:
--   trg_ops_audit_no_delete (W2-1, 2026-04-26)
--   trg_ops_audit_terminal_immutable (W2-1, 2026-04-26)
--
-- reads_audit has no lifecycle ('running' → 'success'/'failed') — every row is
-- terminal at INSERT time — so the UPDATE block is unconditional.
CREATE TRIGGER IF NOT EXISTS trg_reads_audit_no_delete
  BEFORE DELETE ON reads_audit
  BEGIN
    SELECT RAISE(ABORT, 'reads_audit is append-only (CWE-693 protection)');
  END;

CREATE TRIGGER IF NOT EXISTS trg_reads_audit_no_update
  BEFORE UPDATE ON reads_audit
  BEGIN
    SELECT RAISE(ABORT, 'reads_audit rows are immutable after INSERT');
  END;

-- INTEGER affinity enforcement on ts (CWE-704 style — type confusion).
-- Lesson cravada from ops_audit 2026-05-21 Issue #1A: better-sqlite3 binds
-- JS number as REAL, and SQLite TEXT > INTEGER always in lexicographic compare
-- → retention sweep would silently retain all rows. The wrapper uses
-- CAST(? AS INTEGER) at INSERT time AND this trigger is belt-and-suspenders.
CREATE TRIGGER IF NOT EXISTS trg_reads_audit_ts_must_be_int
  BEFORE INSERT ON reads_audit
  FOR EACH ROW WHEN NEW.ts IS NOT NULL AND typeof(NEW.ts) != 'integer'
  BEGIN
    SELECT RAISE(ABORT, 'reads_audit.ts must be INTEGER epoch ms — got non-integer value');
  END;
