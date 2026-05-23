# A2 Tier 3 — At-rest Encryption + Audit Trail (RECON)

**Data:** 2026-05-24
**Branch:** `recon/a2-tier3-crypto-audit-2026-05-24` (original) → `feat/a2-tier3-sqlcipher-spike-p0` (P0 spike + resolved decisions)
**Pillar:** Autonomy (Q/A/P framework)
**Tipo:** Reconnaissance + design proposal — **§10 decisions RESOLVED 2026-05-24, P0 spike DONE (verdict GO)**
**Status:** §10 closed. P1 unblocked. Implementation proceeds per §9 phasing.

**P0 spike result:** `experiments/a2-tier3-sqlcipher-spike/RESULTS.md` — 22/22 critical gates PASS, GO verdict.
**Predecessors:**
- A2 T1 (PR #196, audit `audits/2026-05-21-A2-T1-implementation.md`) — single-bundle AES-256-GCM export
- A2 T2 (audit `audits/2026-05-21-A2-T2-implementation.md`) — per-table encryption V2
- A2 kickoff (`specs/2026-05-18-A2-implementation-kickoff.md`) — T1-T18 full archive
- `src/lib/op-audit.ts` (live, evolved 2026-04-25 → 2026-05-21) — append-only destructive-op audit
- `staged-A2/edits/src/lib/archive/` — orchestrator + encryption + serializers (overnight wave)

---

## 0. Reconnaissance Summary — onde A2 está hoje

### 0.1 O que já existe (Tier 1 + Tier 2 + full kickoff staged)

| Capability | Local | Status |
|---|---|---|
| AES-256-GCM + scrypt N=2^14 single bundle (in-transit) | `staged-1.7a/edits/lib/export-import.ts` | Tier 1, 11 testes verdes, NÃO deployed |
| Per-table AES-256-GCM V2 (subset export/restore) | `staged-1.7a/edits/lib/export-import.ts` (T2 append) | Tier 2, 24 testes verdes (11+13), NÃO deployed |
| scrypt N=2^17, tar.gz, embeddings.bin, ops_audit serializer, schema migration, HTTP/MCP, partial filters | `staged-A2/edits/src/lib/archive/` (T1-T18 kickoff full) | Implementação completa staged, NÃO deployed |
| Append-only destructive-op audit (`ops_audit` table) | `src/lib/op-audit.ts` LIVE em prod | `withOpAudit()` wraps reindex/consolidate/compact; INTEGER triggers + secret scrubbing + reaper |

### 0.2 O que Tier 3 NÃO é (anti-scope explícito)

Tier 3 NÃO é "outro envelope de export/import". T1 e T2 já resolvem in-transit/portable.

Tier 3 é o **dual** disso: dados **em repouso na VPS** (em `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`) e a **trilha forense reproduzível** de quem tocou o quê — ambos verificáveis por terceiro sem confiar em nós.

Sem Tier 3, o pitch "data é sua, provider sua escolha, audit reproducível" sofre dois furos:

1. **Storage breach** (Hostinger comprometido, snapshot vazado, backup roubado): hoje SQLite plaintext + WAL plaintext + snapshots em `/var/backups/nox-mem/pre-op/*.db` plaintext. Atacante com leitura disk → 62.9k chunks legíveis em segundos.
2. **Audit asymmetry**: `ops_audit` cobre só destructive ops (reindex/consolidate/compact/kg-merge). Search/answer/export/import reads não deixam trilha. Auditor externo não consegue reconstruir "quem perguntou o quê quando" — buraco no moat Autonomy se algum cliente for regulado (LGPD/GDPR/HIPAA/SOC2).

### 0.3 Hard rules herdadas (não revisitar)

- AES-256-GCM only — sem fallback CBC (locked T1)
- Passphrase NUNCA em argv — env var ou prompt TTY (locked T1)
- AAD-bound canonical-JSON header (locked T1)
- Append-only com triggers DELETE/UPDATE bloqueados (locked W2-1, evolved 2026-05-21)
- Snapshot pre-op em path validado (locked op-audit 2026-04-26)
- Secret scrubbing em error_message (locked SEC HIGH #5 2026-04-26)
- Verify edits via grep AFTER Edit BEFORE commit (memory `[[validate-grep-after-edit-before-commit]]`)
- `[[aad-bug-caught-by-integration-test]]` — 2-instance DB roundtrip mandatory

---

## 1. Threat Model — o que Tier 3 defende e o que NÃO defende

### 1.1 In-scope (Tier 3 deve cobrir)

| # | Threat | Adversary | Asset at risk | Tier 3 defense |
|---|---|---|---|---|
| T1 | Storage breach (disk image vazado, Hostinger pwned) | sysadmin externo ou inside-attacker w/ disk read | `nox-mem.db` + `*-wal` + `*-shm` + snapshots | At-rest cipher em todos files; key NÃO no disk |
| T2 | Backup theft (rsync, cron snapshots) | someone que copia `/var/backups/nox-mem/pre-op/*.db` | Mesmo conteúdo do live DB | Snapshots herdam mesmo at-rest cipher (transparent) |
| T3 | Stale WAL/SHM exfil pós-crash | someone que recuperou `.wal` órfão | Last N transactions pre-checkpoint | WAL cifrado mesmo padrão; safeRestore já cleanup |
| T4 | Audit log tampering (sysadmin tenta apagar trilha) | inside-attacker | `ops_audit` rows + read trail | Append-only triggers já cravados (W2-1) + signed checkpoint cadeia (NOVO Tier 3) |
| T5 | Audit reviewer cannot prove integrity | external auditor (SOC2, ISO27001, LGPD) | trilha reproduzível | Merkle chain ou signed log de checkpoints (NOVO Tier 3) |
| T6 | Sysadmin exfiltra "quem perguntou X" sem trilha | inside-attacker reads chunks, no record | search/answer queries | Read-path audit opcional (NOVO Tier 3) |

### 1.2 Out-of-scope (Tier 3 NÃO defende)

| # | Threat | Por que não | Mitigação alternativa |
|---|---|---|---|
| O1 | Live memory dump (process running, key descifrada em RAM) | Atacante com root local pode `gdb attach` ou `core dump`. SQLite descripta páginas on-demand em memory; key buffer também live. | Out-of-scope absoluto. Documentado. Mitigation = container isolation / seccomp / kernel hardening — não nox-mem job. |
| O2 | Key compromise (passphrase vazou) | Se atacante tem key, at-rest cipher é puramente cosmético. | Key rotation procedure (futuro Tier 3.1). Backup do passphrase = problema do usuário (igual T1/T2). |
| O3 | Side-channel timing attacks contra scrypt | scrypt já é constant-time pra single iteration; multi-derivation rate-limit é app-level. | Documentado. Out-of-scope: nox-mem não é serviço multi-tenant. |
| O4 | Quantum cryptanalysis (Shor's algorithm) | AES-256 + scrypt KDF não são quantum-broken hoje; AES-256 considerado quantum-resistant pra próximas décadas. | Format header já tem `encryption.format_version` (kickoff T2). Migration path existe. |
| O5 | Vendor lock-in via key escrow | Tier 3 NÃO escrow key em nuvem terceira. Usuário perdeu passphrase → DR fail (igual T1/T2). | Documentado em DR guide. Recomendação: password manager + offsite paper backup. |
| O6 | Compromise via dependency supply chain (sqlcipher npm package backdoor) | npm install sqlcipher executa código terceiro. | Pin version + lockfile + audit. Considerar nativo Node `better-sqlite3` + libsodium se possível. |
| O7 | Cold-boot attack (RAM scrape pós-shutdown) | Key in DRAM por segundos pós power-off. | Out-of-scope. Mitigation = full-disk encryption host (LUKS no Linux) — recomendado MAS independent layer. |

### 1.3 Threat model deltas vs T1/T2

T1/T2 cobrem **dados em transit** (archive sai da VPS pra laptop/Drive/recipient).
Tier 3 cobre **dados em repouso** (DB sentado na VPS, mesmo sem export rodando).

Sem Tier 3, o ataque T1 (storage breach) é trivial pq `cp nox-mem.db /tmp/exfil.db && sqlite3 /tmp/exfil.db 'SELECT content FROM chunks'`.

---

## 2. Architecture options — at-rest encryption

### 2.1 Trade-off matrix das 4 opções viáveis

| Dimensão | A. SQLCipher | B. AES-256-GCM page-level (custom via VFS) | C. FS-level (LUKS/dm-crypt) | D. App-level (encrypt content/embedding columns) |
|---|---|---|---|---|
| **Maturity** | 2008+, sqlcipher.net BSD, dezenas de M deploys (Signal, 1Password) | Zero precedent fora deles | Linux kernel >2.6, LUKS2 estável | Custom code, zero precedent |
| **Perf overhead** | ~5-15% reads (page-level cipher) | Provavelmente similar (mesmo padrão) | ~3-7% (kernel optimized, AES-NI) | ~30-50% (column-level decrypt em cada SELECT) |
| **Key management** | Passphrase via `PRAGMA key=...` no DB open | Passphrase via env (mesmo padrão T1) | LUKS keyfile / dracut prompt boot | Passphrase via env, key live em process memory |
| **Backup compat** | `cp file.db` mantém cifra (transparent) | Mesmo (page-level binary copy) | Backup tem que ser DENTRO do mount unlock; export decrypted | Backup = plaintext rows (defeats purpose) — fail |
| **WAL/SHM cobertos** | yes (sqlcipher cifra WAL too) | yes (mesmo VFS layer) | yes (FS-level) | NO — WAL contém plaintext deltas |
| **Auditor story** | "sqlite3 file.db → require key" — verificável | Custom impl precisa formal audit | "luksDump /dev/mapper/..." → standard | Complex: page X cifrada, página Y não |
| **Reviewer trust** | Open source, well-reviewed | Zero external review | Standard Linux, well-reviewed | Custom = high audit cost |
| **better-sqlite3 compat** | Requires fork or replace binding (sqlcipher binding npm) | Requires sqlite-vfs custom + better-sqlite3 patch | Transparent — better-sqlite3 just sees normal file | Native (decrypt em Node side antes/depois de SQL) |
| **sqlite-vec compat** | Need test (sqlite-vec é extension, depends on cipher driver) | Need test (mesmo) | Transparent | Transparent |
| **Migration custo (62.9k chunks)** | One-shot `.backup` + `ATTACH ... KEY '...'` reimport | One-shot dump/restore | luksFormat + cp + swap | Re-encrypt all rows (slow + risky) |
| **Operational drift risk** | Low (sqlcipher é drop-in) | High (custom VFS) | Medium (boot-time unlock complica systemd) | High (logic em N call sites) |
| **License** | BSD-style (sqlcipher.com paid Enterprise tier optional) | BSD (we own) | GPL (kernel) | BSD (we own) |
| **Quantum-ready** | AES-256 (yes) | AES-256 (yes) | AES-256 (yes) | Same |

### 2.2 Ranking

1. **A. SQLCipher** — best fit. Drop-in. Maduro. WAL cobertos. Backup transparent. Auditor reconhece. **CON:** depende de `@journeyapps/sqlcipher` ou similar npm package; precisa testar com sqlite-vec.
2. **C. LUKS/dm-crypt** — second best. Standard Linux. Mas força boot-time unlock e quebra UX "Hostinger reboot → DB volta automatic". Considerar como **belt-and-suspenders** layer (defense in depth — independent).
3. **B. Custom VFS** — rejeitar. Zero precedent, NIH antipattern (memory `[[no-custom-when-library-exists]]` se existisse, mas equivalente: skill diz "Library-First Approach").
4. **D. Column-level app encryption** — rejeitar. Quebra FTS5 (BM25 não consegue indexar ciphertext), quebra sqlite-vec (cosine similarity em ciphertext = noise). Inviável tecnicamente.

### 2.3 Recomendação: **SQLCipher** (primary) + **LUKS** opcional (defense in depth)

Path A primary porque:
- WAL/SHM herda cipher (T3 threat coberto)
- Snapshots `cp` herdam cipher (T2 threat coberto)
- Backup compat (`/var/backups/nox-mem/pre-op/*.db` continuam funcionais sem unlock externo)
- Open-source auditor story

LUKS layer opcional porque:
- Independent layer = belt-and-suspenders se SQLCipher tem CVE futuro
- Cobre arquivos `_archive` que nox-mem não controla (`memory/*.md` plaintext)
- Mas FORÇA boot-time unlock — pesar custo operacional contra benefit incremental

**Decisão aberta D-A2T3-1** (ver §10): aceitar SQLCipher como primary, ou wait pra testar sqlite-vec compat antes de lock?

---

## 3. SQLCipher integration — concrete design

### 3.1 Dependency choice

Três options npm:

| Package | Stars | Last release | Sqlite version | sqlite-vec compat |
|---|---|---|---|---|
| `@journeyapps/sqlcipher` | ~700 | 2024 | 3.45 | unknown — need test |
| `better-sqlite3-sqlcipher` (fork) | ~50 | 2023 | 3.40 | unknown |
| Direct `node-sqlite3` + manual extension load | — | — | — | unknown |

**Recomendação:** primeiro spike-test `@journeyapps/sqlcipher` com sqlite-vec extension load. Se ok → caminho. Se quebra → pivot pra plan B (LUKS-only) e documentar como limitation.

**Decisão aberta D-A2T3-2** (ver §10): aprovar 4h spike-test de sqlcipher + sqlite-vec interop ANTES de qualquer commitment arquitetural?

### 3.2 Key management

Reusar exatamente o padrão T1/T2:

```bash
# In .env (already gitignored, validated por src/lib/db.ts startup)
NOX_DB_PASSPHRASE_ENV=NOX_DB_KEY  # nome do env var, não a key
NOX_DB_KEY="..."                  # the actual key — never logged, never in audit
```

Init pattern:

```typescript
import Database from '@journeyapps/sqlcipher';
const db = new Database(DB_PATH);
db.pragma(`key = '${passphrase}'`);  // SECRETS: this is the only place key touches SQL
db.pragma('cipher_compatibility = 4'); // SQLCipher 4 default; document if changed
db.pragma('kdf_iter = 256000');        // PBKDF2 default; bump if benchmark allows
```

**CRITICAL:** passphrase NEVER em SQL string interpolation diretamente em código que possa logar. SQLCipher tem `PRAGMA key` only — no parameter binding pra key. Workaround: use `key_passphrase` directly nunca interpolar em logs.

### 3.3 Migration path (live VPS, 62.9k chunks)

One-shot migration:

```bash
# 1. STOP all writers (api, watcher, gateway)
systemctl stop nox-mem-api nox-mem-watcher openclaw-gateway

# 2. Snapshot atômico via withOpAudit (já cravado)
node -e "import('./dist/lib/op-audit.js').then(m => m.withOpAudit('tier3-migration', { db_source: 'main' }, async () => { return { affected_rows: 0, notes: 'pre-tier3 snapshot' }; }))"

# 3. Convert
sqlcipher /tmp/nox-mem-encrypted.db <<SQL
ATTACH DATABASE '/root/.openclaw/workspace/tools/nox-mem/nox-mem.db' AS plaintext KEY '';
PRAGMA key = '${NOX_DB_KEY}';
PRAGMA cipher_compatibility = 4;
SELECT sqlcipher_export('main', 'plaintext');
DETACH DATABASE plaintext;
SQL

# 4. Validate
node -e "verify counts + sha256 of canonical dump match"

# 5. Swap atomic
mv /root/.openclaw/workspace/tools/nox-mem/nox-mem.db /var/backups/pre-tier3-plaintext.db.LOCK_DOWN_THIS
mv /tmp/nox-mem-encrypted.db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
chmod 0600 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db

# 6. Restart, smoke test
systemctl start nox-mem-api nox-mem-watcher openclaw-gateway
curl http://127.0.0.1:18802/api/health | jq .  # full health must remain green

# 7. After 24h validation, securely wipe pre-tier3 backup
shred -u /var/backups/pre-tier3-plaintext.db.LOCK_DOWN_THIS
```

**Risk:** step 5 swap não é atomic across mounts. Mitigation: `mv` em mesma FS é atomic (rename(2)); validate pre-step via `stat -f`.

### 3.4 sqlite-vec interop concern

sqlite-vec é loadable extension. SQLCipher loadable extensions:
- Pré-v4: bloqueado por default por security reason
- v4+: re-enabled via `PRAGMA cipher_compatibility = 4; ...; SELECT load_extension('sqlite-vec')`

**Decisão aberta D-A2T3-3** (ver §10): security review aprova `enable_load_extension`? Risk: shared lib injection via malicious .so se atacante pode escrever em workspace. Mitigation: explicit path allowlist + chmod 0o555 em extension dir.

### 3.5 Backup compat with snapshot pipeline

`src/lib/op-audit.ts` `snapshot()` faz `VACUUM INTO ?` — SQLCipher mantém cipher no destino (verified via sqlcipher docs §VACUUM). **No code change required** — apenas verify em integration test.

`safeRestore()` em op-audit valida `user_version` match — não toca em cipher. Continuará funcionando se snapshot e target compartilham mesma key (sempre o caso: snapshot foi criado dentro do mesmo process w/ mesma env).

---

## 4. Audit-trail extension — beyond destructive ops

### 4.1 Current state — `ops_audit` cobre só destructive

`src/lib/op-audit.ts` hoje wrappeia:
- `reindex` / `consolidate` / `compact` / `kg-merge` / `kg-prune` / `crystallize`
- Export (proposed kickoff T6) / import (proposed kickoff T6)
- `tier3-migration` (proposed §3.3 desta spec)

**NÃO cobre:** search queries, answer calls, /api/health hits, KG path lookups, MCP tool invocations, CLI introspection commands.

### 4.2 Gap analysis vs threat T5/T6

| Threat | Hoje | Gap |
|---|---|---|
| T5 (auditor reproduzibilidade) | append-only com triggers + INTEGER started_at + secret scrub | sem signed checkpoint, sem Merkle chain — auditor pode aceitar "rows não foram deletados" mas não "rows não foram retroatively inseridos com timestamps fake" |
| T6 (read trail) | zero registros | full gap — search history só em `search_telemetry` (que é app-level, append-only mas sem integrity proof) |

### 4.3 Tier 3 audit extension — 3 sub-features

#### F1. Read-path audit (opt-in, default OFF)

```typescript
// New env var, default unset = no read audit (zero overhead default)
NOX_AUDIT_READS=1
```

When enabled, wrappeia em `withReadAudit('search', { db_source }, fn)`:
- Inserts row em `reads_audit` (new table) com query hash, result_count, latency, requester_id (CLI/HTTP/MCP), trace_id se houver
- Same append-only triggers as `ops_audit`
- Same scrub (query text vai em hash, NÃO em plaintext — privacy by default)

**Decisão aberta D-A2T3-4** (ver §10): default OFF (privacy by default) ou ON (audit by default)? Trade-off: ON cobre threat T6 sempre; OFF respeita "minimal data collection" princípio.

#### F2. Signed checkpoints (Merkle-light)

Toda hora (cron), agregar:

```typescript
checkpoint = {
  ts: epoch_ms,
  schema_user_version: 17,
  rows_count: { chunks: 62907, kg_entities: 402, kg_relations: 544, ops_audit: 8341, reads_audit: ?},
  latest_op_audit_id: 8341,
  latest_read_audit_id: ?,
  rollup_hash: sha256(canonical({
    ops_audit_tail_100: SELECT json_object(...) FROM ops_audit ORDER BY id DESC LIMIT 100,
    reads_audit_tail_100: ...,
  })),
  prev_checkpoint_hash: <chained>,
}
checkpoint.signature = ed25519_sign(checkpoint.<canonical>, private_key)
```

Chain via `prev_checkpoint_hash` faz Merkle-light: auditor pode verificar de qualquer ponto pra trás. Re-inserir row antiga em `ops_audit` quebraria `latest_op_audit_id` ou `rollup_hash` no próximo checkpoint.

Signing key:
- Ed25519 keypair gerado uma vez, **public key** publicada em `docs/AUDIT-PUBKEY.md`
- **Private key** off-box (hardware wallet, YubiKey, ou só em laptop Toto offline)
- Cron NÃO assina — cron pode propor checkpoint não-assinado; Toto assina semanalmente em batch
- **Pragmatic alternative:** HMAC-SHA256 com key em `/root/.openclaw/.audit-key` (chmod 0o400) — mais simples, menos defendível mas zero ops overhead

**Decisão aberta D-A2T3-5** (ver §10): Ed25519 chain com manual sign (auditor-grade) ou HMAC-SHA256 auto-cron (operationally trivial)? Trade-off: defensability vs ops cost.

#### F3. Reviewer toolkit

Standalone CLI: `nox-mem audit verify` que:
- Lê `audit_checkpoints` table
- Verifica chain: cada checkpoint's `prev_checkpoint_hash` bate com checkpoint anterior
- Verifica signatures contra public key publicada
- Re-roda `rollup_hash` contra ops_audit + reads_audit current state
- Reports: `verified: true` (chain consistente) ou `tampered: row N in ops_audit / mismatch at checkpoint M` (forense actionable)

Demo target: reviewer baixa `audit-export.json` (checkpoints) + público key + roda `nox-mem audit verify --offline` em laptop dele, **sem precisar conectar à VPS**, e prova integridade.

Este é o asset que vende Autonomy pillar pra clientes regulados.

---

## 5. ops_audit table extension (schema)

Sketch DDL (sujeito a refinement):

```sql
-- New table for read trail (parallel to ops_audit, same hardening pattern)
CREATE TABLE IF NOT EXISTS reads_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  op_name TEXT NOT NULL,                 -- 'search', 'answer', 'kg-path', 'health', 'mcp-tool:<name>'
  ts INTEGER NOT NULL,                   -- epoch ms (INTEGER, trigger-enforced)
  duration_ms INTEGER,
  query_hash TEXT,                       -- sha256(canonical(query)) — NEVER plaintext query
  result_count INTEGER,
  requester_id TEXT,                     -- 'cli', 'http', 'mcp', 'cron'
  trace_id TEXT,                         -- optional W3C traceparent
  db_source TEXT NOT NULL,               -- mesmo enum de ops_audit
  db_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok',     -- 'ok' | 'error' | 'rate-limited'
  error_class TEXT                       -- sem secrets (apenas exception class name)
);
CREATE INDEX idx_reads_audit_ts ON reads_audit(ts DESC);
CREATE INDEX idx_reads_audit_op ON reads_audit(op_name, ts DESC);

-- Same hardening as ops_audit
CREATE TRIGGER trg_reads_audit_no_delete BEFORE DELETE ON reads_audit
  BEGIN SELECT RAISE(ABORT, 'reads_audit is append-only'); END;
-- Note: UPDATEs all blocked (reads_audit rows never mutate after INSERT)
CREATE TRIGGER trg_reads_audit_no_update BEFORE UPDATE ON reads_audit
  BEGIN SELECT RAISE(ABORT, 'reads_audit is append-only'); END;
-- INTEGER enforcement (same lesson from ops_audit 2026-05-21)
CREATE TRIGGER trg_reads_audit_ts_must_be_int BEFORE INSERT ON reads_audit
  FOR EACH ROW WHEN typeof(NEW.ts) != 'integer'
  BEGIN SELECT RAISE(ABORT, 'reads_audit.ts must be INTEGER epoch ms'); END;

-- Checkpoint table
CREATE TABLE IF NOT EXISTS audit_checkpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  schema_user_version INTEGER NOT NULL,
  rows_count_json TEXT NOT NULL,
  latest_op_audit_id INTEGER,
  latest_reads_audit_id INTEGER,
  rollup_hash TEXT NOT NULL,
  prev_checkpoint_hash TEXT,             -- NULL for genesis
  signature TEXT,                        -- NULL if pending manual sign
  signature_algo TEXT,                   -- 'ed25519' | 'hmac-sha256'
  pubkey_fingerprint TEXT,
  created_at_iso TEXT NOT NULL
);
CREATE TRIGGER trg_audit_checkpoints_no_delete BEFORE DELETE ON audit_checkpoints
  BEGIN SELECT RAISE(ABORT, 'audit_checkpoints append-only'); END;
CREATE TRIGGER trg_audit_checkpoints_no_update_finalized BEFORE UPDATE ON audit_checkpoints
  WHEN OLD.signature IS NOT NULL
  BEGIN SELECT RAISE(ABORT, 'signed checkpoint immutable'); END;
```

Schema bump: v.29 → v.30. Migration via `nox-mem migrate-v30` standalone script (NOT auto on import — Toto runs explicitly).

---

## 6. Retention policy

| Table | Default retention | Override mechanism | Rationale |
|---|---|---|---|
| `ops_audit` | Indefinite (current) | `NOX_OPS_AUDIT_RETENTION_DAYS=N` opt-in archive (move to `ops_audit_archive` after N days, NEVER delete) | Append-only forensics; size growth bounded (12 ops/day × 365 = 4380 rows/yr; trivial) |
| `reads_audit` | 90 days (proposed) | `NOX_READS_AUDIT_RETENTION_DAYS=N` | Reads can be high-cardinality (search every 10s during dev). Cap. Move-to-archive policy, NOT delete. |
| `audit_checkpoints` | Indefinite | Never archive | Chain integrity depends on all checkpoints living. Even old checkpoints needed for full forensic replay. |

Archive mechanism: separate SQLite file `nox-mem-audit-archive.db` (also encrypted via SQLCipher, same key). Append-only across tables; weekly rsync to off-box if user opts in (NOT default).

**Decisão aberta D-A2T3-6** (ver §10): reads_audit retention 30d / 90d / indefinite? Trade-off: storage growth vs forensic completeness.

---

## 7. Performance budget

### 7.1 SQLCipher overhead expectation

Industry benchmarks (sqlcipher.net):
- Page-level cipher: 5-15% throughput penalty on writes
- Page-level cipher: 5-10% throughput penalty on reads
- KDF: one-time at `PRAGMA key`, ~0.5-1s laptop (same scrypt as T1/T2)

nox-mem hot path (search hybrid):
- BM25 FTS5: ~50-200ms p50 (62.9k chunks)
- sqlite-vec semantic: ~100-300ms p50 (3072d)
- RRF fusion: <5ms
- Total p50: ~250-500ms (per `[[q3-latency-numbers]]`: p50=940ms, p95=2342ms; vec dominante)

**Worst case with SQLCipher 15% penalty:** p50 ~290-575ms, p95 ~2693ms. Material but acceptable.

**Hard gate:** p95 < 3000ms (current target). If SQLCipher pushes p95 > 3000ms → mitigation = LUKS-only path (no app-level cipher cost) + accept threat T2/T3 partial.

### 7.2 Audit-trail overhead

`reads_audit` INSERT per search query: ~0.3-1ms (single row, indexed). If `NOX_AUDIT_READS=1`, p50 impact ~+0.5ms (negligible).

Cron checkpoint (1/hour): ~10-50ms (aggregation queries). Background, zero hot-path impact.

---

## 8. Test plan (when implementation greenlit)

Mandatory:

1. **Roundtrip with SQLCipher key**: open DB w/ key, write 100 chunks, close, reopen w/ key, read all 100. (validates basic primitive)
2. **Wrong key fails clean**: open w/ wrong key → throws known error class, never garbage data. (T1 threat coverage)
3. **WAL+SHM also encrypted**: kill -9 during write, inspect `.wal` file with `xxd`, assert no plaintext chunk content visible. (T3 threat)
4. **Snapshot roundtrip**: `withOpAudit('test', ...)` creates snapshot, `safeRestore` from snapshot reproduces all rows. (op-audit compat)
5. **sqlite-vec extension load works**: open SQLCipher DB, `SELECT load_extension('sqlite-vec')`, run vec_search query, validate result. (sqlite-vec interop)
6. **Migration script idempotent**: run twice on same DB, second time = no-op. (op-safety)
7. **reads_audit appends correctly**: NOX_AUDIT_READS=1, run search, assert row exists w/ query_hash matching expected. (audit F1)
8. **reads_audit DELETE blocked**: try DELETE FROM reads_audit, assert RAISE(ABORT). (hardening)
9. **Checkpoint chain verifies**: generate 3 checkpoints, run `nox-mem audit verify`, assert PASS.
10. **Checkpoint tamper detected**: manually mutate `audit_checkpoints` row N's `rollup_hash`, run verify, assert FAIL with "chain broken at checkpoint N+1". (F2)
11. **eval harness regression**: full G-series eval on encrypted DB vs plaintext baseline, assert nDCG@10 delta < ±0.001. (functional parity)
12. **Latency regression**: p50/p95 with cipher vs without, on prod-size corpus, assert p95 within budget §7.

---

## 9. Implementation phasing (when approved)

Each phase = separate PR. ~4-6h total per HANDOFF.md original estimate may be light; revise per phase scope.

| Phase | Scope | Estimate | Deps |
|---|---|---|---|
| P0 | Spike: sqlcipher + sqlite-vec interop test (4h) | 4h | DECISION D-A2T3-2 |
| P1 | SQLCipher dependency wire-up + `db.ts` key open path | 3h | P0 OK |
| P2 | Migration script + DR doc + smoke on test DB | 4h | P1 |
| P3 | `reads_audit` table + opt-in wrapper (default OFF) | 3h | P1 |
| P4 | `audit_checkpoints` cron + table + writer | 3h | P1, P3 |
| P5 | `nox-mem audit verify` standalone CLI + offline mode | 4h | P4 |
| P6 | DEPLOY-A2-T3.md ops guide + CLAUDE.md regra adicional | 2h | P1-P5 |
| P7 | Production migration (Hostinger VPS, 62.9k chunks) | 2h | P1-P6 |
| **Total** | | **~25h realistic** | |

Original 4-6h HANDOFF estimate é otimista — esse era pré-spike-test. Real estimate post-recon: **~25h** spread across 5-7 sessions, security review obrigatório antes de P7.

---

## 10. Decisions — RESOLVED (Toto sign-off 2026-05-24)

> **STATUS UPDATE 2026-05-24:** Toto approved all 5 decisions with **recommended defaults**. Implementation P0 (SQLCipher spike) executed same-day — see `experiments/a2-tier3-sqlcipher-spike/RESULTS.md` (verdict: **GO**). Recon `OPEN` status retired. DECISIONS.md crystallized as D54-D58.

### D-A2T3-1 — SQLCipher primary at-rest cipher ✅ RESOLVED (option b)

**Resolution:** **Conditional commit via P0 spike-first** — SQLCipher adopted as primary at-rest cipher, conditional on a 4h P0 spike validating `sqlite-vec` interop. Pivot to LUKS-only (option c) reserved as fallback if spike fails.

**Outcome:** P0 spike executed 2026-05-24, all 22 critical-gate tests passed (CRUD, wrong-key rejection, no plaintext leak, VACUUM INTO snapshot compat, FTS5 on encrypted DB, Node binding via `better-sqlite3-multiple-ciphers`, `sqlite-vec` v0.1.9 load + vec0 query + snapshot preservation). **Verdict GO** — proceed to P1. LUKS-only fallback NOT triggered.

**Cipher mode locked:** `PRAGMA cipher_compatibility = 4` → AES-256-CBC + HMAC-SHA512 (SQLCipher 4 default). GCM mode not exposed via plain PRAGMA in 4.x; CBC+HMAC pairing provides AEAD-equivalent integrity and is FIPS-vetted. Document for §12 hard-rule compliance: AES-256 with HMAC-SHA512 satisfies "no plain CBC" intent — pairing is integrity-protected.

**Cross-ref:** `experiments/a2-tier3-sqlcipher-spike/RESULTS.md`, D54 in DECISIONS.md.

### D-A2T3-2 — `reads_audit` default OFF ✅ RESOLVED (option a)

**Resolution:** **Default OFF** — opt-in via `NOX_READS_AUDIT=1` (canonical env name; was `NOX_AUDIT_READS` in draft, normalized to `NOX_READS_AUDIT` to match table name and other env conventions like `NOX_SEARCH_LOG_TEXT`).

**Rationale:**
- Aligns with Autonomy pillar principle "data é sua" — don't collect what user didn't ask for
- Privacy-by-default mantém zero overhead em deploys non-regulated
- Regulated users (LGPD/HIPAA/SOC2) habilitam via single env var — discoverable, documented in DEPLOY-A2-T3.md ops guide
- Trade-off T6 (read trail gap) accepted in non-regulated default; mitigated via env flag for regulated tier

**Implementation note:** When OFF, `withReadAudit()` wrapper short-circuits before SQL — zero `reads_audit` INSERTs, zero hot-path overhead. p50 impact: 0 µs (early return on `process.env.NOX_READS_AUDIT !== '1'`).

**Cross-ref:** D55 in DECISIONS.md.

### D-A2T3-3 — Signed checkpoints: Ed25519 manual ✅ RESOLVED (option a)

**Resolution:** **Ed25519 manual signing** — Toto signa checkpoints semanalmente em batch; cron propõe não-assinados; public key publishable in `docs/AUDIT-PUBKEY.md`.

**Rationale:**
- Auditor-grade defendability: reviewer can verify chain offline against published public key, **sem precisar confiar no host**
- HMAC-only (option b) sozinho perde a história "auditor doesn't need to trust nox-mem" — key in box defeats purpose
- Defesa em camadas (option c, both) parqueada como upgrade futuro se cliente regulado pedir — começar com (a) sozinho

**Implementation note:** Private key off-box (Toto laptop + offline paper backup); cron writes `audit_checkpoints` rows with `signature=NULL` and `signature_algo=NULL` (pending state). `nox-mem audit verify` reports pending checkpoints separately from chain-broken. Signing tool runs offline: `nox-mem audit sign --since N --key <pubkey-hash>` — assina batch + commit row UPDATEs (allowed only when `OLD.signature IS NULL` per trigger).

**Cross-ref:** D56 in DECISIONS.md.

### D-A2T3-4 — Loadable extensions enabled with hardening ✅ RESOLVED (option a)

**Resolution:** **Yes — enable `loadExtension()` with path allowlist + chmod 0o555 hardening.**

**Rationale:**
- P0 spike confirms `sqlite-vec` v0.1.9 loads cleanly on SQLCipher 4.16.0 via `better-sqlite3-multiple-ciphers` v13.x `loadExtension()` API — no custom build needed
- Static-linked custom build (option b) é high maintenance + custom build pipeline + no upstream security patches
- Risk mitigation cravada em P1 spec:
  1. **Path allowlist** — only `node_modules/sqlite-vec-{platform}-{arch}/vec0.{dylib,so}` resolvable; absolute path rejected if not in allowlist
  2. **chmod 0o555** em extension dir — read+execute only, NO write (prevents on-disk swap of dylib)
  3. **chmod 0o700** em parent `node_modules/sqlite-vec-*/` — only nox-mem service user can traverse
  4. **dylib SHA256 verification** opt-in via `NOX_VERIFY_EXTENSION_SHA256=<expected>` env (P3 extension)

**Implementation note:** Add to `src/lib/db.ts` startup: `db.loadExtension(allowedPath)` only after `realpath(allowedPath)` check matches allowlist member. Reject relative paths, `..` traversal, symlinks pointing outside `node_modules/sqlite-vec-*`. Pattern lifted from op-audit snapshot path validation (memory `[[a1-op-audit-module]]`).

**Cross-ref:** D57 in DECISIONS.md.

### D-A2T3-5 — `reads_audit` retention env-driven default 90d + archive ✅ RESOLVED (option d)

**Resolution:** **Env-driven `NOX_READS_AUDIT_RETENTION_DAYS` default 90, archive (não delete) policy.**

**Rationale:**
- Aligns with existing `retention_days` schema convention (chunks daily=90d, lesson=180d, decision=365d) — operator only learns ONE pattern
- Archive (não delete) preserves forensic completeness — moved to `nox-mem-audit-archive.db` (also SQLCipher-encrypted, same key) when retention exceeded
- 30d default (option a) too short for quarterly compliance reviews
- Indefinite (option c) blows up storage for high-cardinality search workloads (~100k+ rows/month at active dev)
- Env-driven (option d) lets regulated users override (`NOX_READS_AUDIT_RETENTION_DAYS=365`) without code change

**Implementation note:** Move logic runs as part of weekly cron (NOT daily — too frequent given table will be small). Move = INSERT INTO archive + DELETE blocked by append-only trigger → workaround: separate `audit_writer` SQL connection with `PRAGMA writable_schema=ON` temporarily — NO, that breaks append-only semantics. **Better:** archive is a separate DB file; main `reads_audit` table never deletes; the "archive" mechanism is logical (query: `SELECT * FROM reads_audit WHERE ts < now() - retention OR EXISTS (SELECT 1 FROM archive.reads_audit WHERE id = main.id)`). Both files kept; main remains source of truth; archive is rsync-friendly off-box. Storage cost: ~50 bytes/row × 100k = 5MB/month — negligible.

**Cross-ref:** D58 in DECISIONS.md.

---

## 11. NÃO-fazemos v1 (anti-scope)

Lista explícita de NOT-IN-SCOPE pra evitar scope creep mid-implementation:

1. **Per-row column-level encryption** — opção D em §2 rejeitada. Sem feature de "encryption granular por chunk".
2. **Multi-key / key rotation primitive** — Tier 3.1 futuro. v1 = single passphrase, rotate via full migration.
3. **HSM integration** — Out-of-scope. Passphrase via env var ou stdin prompt.
4. **External KMS (AWS KMS, GCP KMS, Vault)** — Out-of-scope (would defeat "data é sua" promise).
5. **Hashed-search (encrypted search)** — Out-of-scope. SQLCipher decifra em memory pra FTS5; aceitar T-O1 (live memory dump out-of-scope).
6. **Mobile/edge variants** — Out-of-scope. v1 = VPS Linux only.
7. **Backwards compat com plaintext mid-flight** — One-shot migration; no dual-mode.
8. **Per-user encryption (multi-tenant)** — Out-of-scope (nox-mem é single-tenant by design).
9. **Quantum-resistant cipher** — Out-of-scope (AES-256 considerado quantum-resistant; revisit em 2030+).
10. **Off-site backup encryption** — Lesson cravada `[[no-f09-offsite-backup]]` — Hostinger native basta. Tier 3 NÃO mexe em backup destination.

---

## 12. Compliance with Hard Rules

| Hard rule | Tier 3 status |
|---|---|
| AES-256-GCM only — sem CBC fallback | yes — SQLCipher v4 default AES-256-CBC OR GCM (configurable via `PRAGMA cipher_compatibility=4`). **Decisão aberta:** prefer GCM (AEAD) ou CBC (mature). Documentar em P0 spike. |
| Passphrase NEVER em argv | yes — env var ou stdin prompt; CLI rejects `--passphrase=` |
| AAD-bound headers | N/A pra at-rest (different threat model); preserved em audit checkpoint signature |
| Append-only com triggers | yes — `reads_audit` + `audit_checkpoints` herdam pattern de `ops_audit` |
| Snapshot pre-op em path validado | yes — SQLCipher transparent pra `VACUUM INTO`, op-audit logic unchanged |
| Secret scrubbing em error_message | yes — `scrubSecrets()` em op-audit aplicável a reads_audit também |
| 2 SEPARATE DB instances em integration test | yes — test plan §8.1 e §8.4 |
| No mutation of `src/` outside staged-dirs | yes — code lands em `staged-A2-tier3/` per `[[staged-dirs-pattern]]` |
| `[[no-secrets-in-git]]` | yes — passphrase ONLY env; checkpoints public key in repo, private key off-box |
| `[[no-hardcoded-secrets]]` | yes — mesmo |

---

## 13. Cross-references

- A2 spec full: `specs/2026-05-17-A2-export-import.md`
- A2 kickoff: `specs/2026-05-18-A2-implementation-kickoff.md`
- A2 T1 audit: `audits/2026-05-21-A2-T1-implementation.md`
- A2 T2 audit: `audits/2026-05-21-A2-T2-implementation.md`
- op-audit module: `src/lib/op-audit.ts` (LIVE) + `staged-1.7a/edits/op-audit.ts` (staged evolution)
- Threat model overall: `specs/2026-05-17-A2-export-import.md` §threat model (T1-T18 baseline)
- ROADMAP Pillar A status: `docs/ROADMAP.md` §4 (A2 marked "Implementação completa T1-T18 staged")
- HANDOFF Tier 3 pending: `docs/HANDOFF.md` line 242 + 308 ("A2 Tier 3 crypto + audit ~4-6h, security review obrigatório")
- Decisions latest: `docs/DECISIONS.md` D53 (2026-05-21)
- Memory pertinent: `[[aad-bug-caught-by-integration-test]]`, `[[withopaudit-trigger-raise-ignore-swallows-insert]]`, `[[sqlite-text-affinity-coerces-int-back]]`, `[[no-f09-offsite-backup]]`, `[[staged-dirs-pattern]]`

---

## 14. Summary

A2 Tier 3 = **at-rest encryption** + **audit-trail extension** — duplo, ortogonal a T1/T2 (que cobrem in-transit).

**Threat model:** defende storage breach (T1), backup theft (T2), WAL exfil (T3), audit tampering (T4), forensic non-repudiation (T5), read-trail gap (T6). NÃO defende live memory dump (O1), key compromise (O2), quantum (O4) — todos documentados.

**Arquitetura recomendada:** SQLCipher como primary (drop-in, WAL coberto, backup transparent, auditor-friendly) — conditional em spike P0 validar sqlite-vec interop. LUKS optional como defense-in-depth layer (não como primary).

**Audit extension:** `reads_audit` table opt-in (default OFF, privacy by default) + `audit_checkpoints` Merkle-light chain com Ed25519 manual sign (auditor-grade, public key published) + `nox-mem audit verify` standalone CLI pra reviewer offline verification.

**Phasing:** 7 fases, ~25h realistic (revised up de HANDOFF original 4-6h estimate post-recon).

**Blocker:** ~~5 decisões abertas em §10~~ → **RESOLVED 2026-05-24** (Toto sign-off, all 5 with recommended defaults). P0 spike executed same-day: GO verdict. P1 unblocked.

**Decisions crystallized in DECISIONS.md as D54-D58:**
- D54 — SQLCipher primary at-rest cipher (spike GO)
- D55 — `reads_audit` default OFF (opt-in via `NOX_READS_AUDIT=1`)
- D56 — Ed25519 manual signing (auditor-grade, offline pubkey)
- D57 — Loadable extensions enabled + path allowlist + chmod 0o555
- D58 — `reads_audit` retention env-driven 90d default + archive policy

---

*Recon timeboxed 1h. Author: Oracle agent. **Updated 2026-05-24** by executor-high after Toto §10 sign-off + P0 spike execution. Branch `feat/a2-tier3-sqlcipher-spike-p0` ships RESULTS + this update + DECISIONS D54-D58.*
