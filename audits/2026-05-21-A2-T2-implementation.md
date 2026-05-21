# Audit — A2 Tier 2: Per-table Encryption Export/Import (V2)

**Data:** 2026-05-21
**Branch:** `impl/a2-export-import-t2`
**Pillar:** Autonomy (Q/A/P framework)
**Scope:** Tier 2 — per-table encryption (V2 bundle format) + V1 backward compat
**Predecessor:** T1 (PR #196, commit `e71efb8`, audit `2026-05-21-A2-T1-implementation.md`)
**Status:** Implementation complete, tests green (24/24 = 11 T1 + 13 T2), no deploy

---

## 1. T1 → T2 Migration Narrative

Tier 1 shipped a whole-DB JSON serialization inside a single AES-256-GCM ciphertext. That delivered the cryptographic core but blocked four capabilities that the Autonomy pillar needs at production scale:

| Capability blocked by T1 | T2 unlock |
|---|---|
| Selective export — exporting only one table without exposing the others | `exportEncryptedV2(db, pp, out, { tables: ['chunks'] })` produces a bundle whose `tables` map contains only the requested entries. |
| Selective restore — restoring only `kg_entities` from a full bundle without touching `chunks` | `importEncryptedV2(db, pp, in, { strategy: 'replace', tables: ['kg_entities'] })` truncates and re-inserts only the named table. |
| Streaming friendliness — per-table ciphertext means future T3 can stream table-by-table without loading the whole DB into RAM | Format groundwork; T3 will swap `JSON.parse` with NDJSON streamed decryption. |
| Independent rotation — re-key one table on suspicion without touching the rest | Per-table IV + per-table AAD means each table's ciphertext is independent. T3 will ship a rekey-one-table CLI. |

T2 ships the format change and the per-table primitives. It deliberately does NOT ship T3 (streaming, NDJSON, HTTP/MCP, schema migration, embeddings.bin, ops_audit serialization) — those layer on top of an unchanged V2 envelope.

**The cryptographic core is shared.** T2 reuses `deriveKey()`, `canonicalJson()`, `sha256()`, `timingSafeEqual()`, `createCipheriv()`/`createDecipheriv()`, `randomBytes()`, KDF params, IV/auth-tag lengths — all verbatim from T1. No new crypto primitives.

---

## 2. Bundle Format V2 Spec

### 2.1 Envelope layout

```jsonc
{
  "version": 2,                       // bumps from 1
  "created_at": "<iso8601>",          // AAD-bound per table
  "encrypted": true,
  "cipher": "aes-256-gcm",
  "key_derivation": "scrypt",
  "kdf_params": { "N": 16384, "r": 8, "p": 1, "keylen": 32 },
  "salt": "<b64>",                    // SHARED salt across tables (single passphrase → single key)
  "tables": {
    "chunks": {
      "rows_count": N,                // AAD-bound
      "iv":         "<b64, 12 bytes>",// per-table (unique nonce mandatory for GCM key reuse)
      "authTag":    "<b64, 16 bytes>",// per-table
      "aad":        "<b64, 32 bytes>",// sha256(canonical(per-table-header))
      "ciphertext": "<b64>"           // AES-GCM(JSON.stringify(rows[]))
    },
    "kg_entities":  { ... },
    "kg_relations": { ... }
  }
}
```

### 2.2 Per-table AAD computation

```
AAD_t = sha256(canonicalJson({
  version:      2,
  created_at:   <bundle.created_at>,
  table_name:   t,                    // ← binds ciphertext to specific table
  rows_count:   <table[t].rows_count>,
  cipher:       "aes-256-gcm",
  key_derivation: "scrypt",
  kdf_params:   <bundle.kdf_params>,
  salt:         <bundle.salt>,        // shared salt also AAD-bound
  iv:           <table[t].iv>         // per-table IV
}))
```

The `table_name` field is the new defense: an attacker who swapped the entire `chunks` envelope with the `kg_entities` envelope would now fail AAD verification because the recomputed AAD would mismatch (table name in the header would not match the ciphertext's encrypted-for table name).

### 2.3 Key derivation reuse

Each export performs **exactly one** scrypt KDF, producing a single 32-byte key. That single key encrypts all N tables in the bundle, each with its own fresh random 12-byte IV. This is safe under GCM provided IVs are unique — which `crypto.randomBytes(12)` guarantees with overwhelming probability (collision space `2^96`).

Alternative considered: per-table salt + per-table key. Rejected because:
- It costs N scrypt invocations per export (~150ms each × 3 = 450ms unnecessary CPU).
- It does NOT add cryptographic strength under our threat model — an attacker who derives one key from the passphrase has derived them all.
- It would prevent partial-rotation use cases (T3) where the user wants to rotate ONE table's encryption without re-deriving N keys.

### 2.4 Bundle size overhead vs V1

For the test fixture (3 chunks + 2 entities + 1 relation):
- V1 bundle: ~1.6 KB (single ciphertext over canonical JSON of `{chunks, entities, relations}`).
- V2 bundle: ~1.9 KB (three ciphertexts + three IVs + three AADs + three authTags).

Overhead is dominated by the per-table envelope JSON (~75 bytes × 3 = ~225 bytes). Independent of corpus size — at the prod scale of 62.9k chunks, the V2 overhead is negligible (~<0.05%).

---

## 3. Backward Compatibility Strategy

The T2 PR introduces a new public function `importEncryptedAuto()` that reads the bundle header, branches on `version`, and routes:

| Bundle `version` | Routed handler | Result shape |
|---|---|---|
| `1` | `importEncrypted()` (T1) | `ImportV2Result` with `tablesImported` derived from `{chunks_imported, entities_imported, relations_imported}` |
| `2` | `importEncryptedV2()` | Native `ImportV2Result` |
| other | throws `UNSUPPORTED_VERSION` | — |

The CLI now defaults to V2 for **export** (`--tier 2`) but uses `importEncryptedAuto` for **import**, meaning:
- A user who exported a V1 bundle yesterday can import it today after upgrading to T2 with no flag changes.
- A user who exports new bundles after T2 gets V2 by default.
- `--tier 1` is still available for users who need to send a bundle to a non-T2 recipient.

**T1 public API preserved verbatim:**
- `exportEncrypted(db, pp, out)` — unchanged signature, unchanged output.
- `importEncrypted(db, pp, in, { strategy, dryRun })` — unchanged signature, unchanged output.
- `ExportBundle` interface (V1) — unchanged.
- Type union `ExportImportError.code` — additive only (`UNKNOWN_TABLE`, `TABLE_NOT_IN_BUNDLE` added; pre-existing codes unchanged).

**CLI JSON output backward compat:**
- The CLI still emits the V1 flat fields (`chunks_exported`, `entities_exported`, `relations_exported`, `chunks_imported`, `entities_imported`, `relations_imported`) regardless of whether tier=1 or tier=2 is in use. They are now derived from the V2 `tablesImported`/`tablesExported` arrays.
- A new `tier: 1|2` field and a `tables_exported`/`tables_imported` array are added for v2-aware consumers.
- Verified: T1 case 11 (CLI happy-path roundtrip) still passes against the new CLI.

---

## 4. Cryptographic Differences vs T1

| Dimension | T1 (V1) | T2 (V2) |
|---|---|---|
| KDF invocations per export | 1 | 1 (shared salt + shared key) |
| Salt count | 1 (16 bytes) | 1 (16 bytes, shared) |
| IV count | 1 (12 bytes) | N (12 bytes per table) — IV uniqueness within key required for GCM |
| AAD count | 1 (header sha256) | N (per-table header sha256) |
| AuthTag count | 1 (16 bytes) | N (16 bytes per table) |
| AAD binds | counts, salt, IV, KDF params, timestamp, version | + `table_name`, + per-table `rows_count` |
| Tamper detection granularity | whole-bundle (any byte flip fails all) | per-table (a byte flip in `chunks` only kills `chunks` import — others can still be restored via subset import) |
| Cross-table swap attack | implicit (one big ciphertext) | explicit — `table_name` AAD prevents ciphertext relocation |
| Wrong passphrase | indistinguishable from tamper (no oracle) | same — first table decrypted throws `TAMPERED_BUNDLE` |
| Min passphrase length | 8 chars (`WEAK_PASSPHRASE` at export) | same — T2 reuses `deriveKey()` |
| Memory wipe of key buffer | yes (`key.fill(0)` in `finally`) | yes (same pattern, applies after all N tables encrypted/decrypted) |

**No new attack surface introduced.** T2's only crypto novelty is the per-table AAD binding `table_name` — strictly additive defense.

---

## 5. Files Added / Modified

| Path | Status | LOC | Purpose |
|---|---|---|---|
| `staged-1.7a/edits/lib/export-import.ts` | MODIFIED | +462 | T2 section appended below T1 section. Adds `exportEncryptedV2`, `importEncryptedV2`, `importEncryptedAuto`, `applyImportV2`, `detectMergeConflictsTable`, `buildAadHeaderV2`, V2 types, two new error codes. |
| `staged-1.7a/edits/cli/export-import-cli.ts` | MODIFIED | +75 / -25 | Adds `--tier 1|2` and `--tables a,b,c` flags. Import path now uses `importEncryptedAuto`. CLI output preserves all v1 flat fields for backward compat. |
| `staged-1.7a/tests/export-import-v2-tier2.test.ts` | NEW | 446 | 13 test cases: V2 roundtrip + per-table tamper + subset export + subset import + V1 backward compat + dry-run + replace/merge per-table + AAD tamper per table + CLI happy-path + CLI V1 force + 2 error-path cases. |
| `staged-1.7a/tsconfig.export-import.json` | MODIFIED | +1 | Adds new test file to `include`. |
| `audits/2026-05-21-A2-T2-implementation.md` | NEW | this file | T2 audit. |

**Touched (no production `src/`):** only `staged-1.7a/`. Deploy path is the staged-dirs pattern (memory `[[staged-dirs-pattern]]`), not direct merge into `src/`.

**Memory references respected:**
- `[[aad-bug-caught-by-integration-test]]` — all roundtrip cases use two separate `Database` instances at distinct paths.
- `[[no-secrets-in-git]]` — passphrase paths preserved from T1, CLI still refuses `--passphrase=`.
- `[[no-hardcoded-secrets]]` — same.

---

## 6. Test Coverage

24 cases total = 11 T1 (preserved) + 13 T2 (new).

| # | Case | Why it matters |
|---|---|---|
| 1 | V2 roundtrip preserves all 3 tables across two separate DB instances | Core integration test — `[[aad-bug-caught-by-integration-test]]`. |
| 2 | Per-table tamper — flip `chunks` ciphertext byte → import chunks fails; subset import of others still succeeds | The headline T2 capability. Proves per-table independence. |
| 3 | Subset export — only `chunks` in bundle | Validates `--tables` filter at export. |
| 4 | Subset import — pull only `kg_entities` from a full bundle | Validates `--tables` filter at import. |
| 5 | Backward compat — old V1 bundle imports correctly via auto-detect | Forward-compat for existing V1 archives. |
| 6 | V2 dry-run returns per-table counts, does not mutate target | Pre-flight contract preserved. |
| 7 | Replace per-table — chunks replaced, kg_entities untouched (subset import) | Critical: replace strategy is now SCOPED to subset, does NOT mass-truncate. |
| 8 | Merge per-table — preserves existing rows where IDs collide; conflicts reported per table | Same as T1 case 8 but split across all three tables. |
| 9 | Per-table AAD tamper — flipping `kg_entities.rows_count` in envelope triggers `AAD_MISMATCH` | Validates per-table AAD defense layer. |
| 10 | CLI V2 export with `--tables chunks,kg_relations` subset + auto-detect import | End-to-end CLI happy path. |
| 11 | CLI `--tier 1` forces V1 path; import auto-detect handles V1 transparently | Validates `--tier 1` escape hatch + auto-detect. |
| 12 | Unknown table in `--tables` yields typed `UNKNOWN_TABLE` error | Error-path coverage. |
| 13 | Requesting table absent from bundle yields `TABLE_NOT_IN_BUNDLE` | Error-path coverage. |

**Run:**
```bash
cd staged-1.7a && \
  npx tsc -p tsconfig.export-import.json && \
  node --test \
    dist/tests/export-import-roundtrip.test.js \
    dist/tests/export-import-v2-tier2.test.js
```

**Result:** 24/24 pass, total ~1.0 s.

---

## 7. Deployment Plan

**This PR does NOT deploy to VPS.** It lives in `staged-1.7a/edits/{lib,cli}/` per the staged-dirs deployment pattern.

Future landing steps (deferred to a separate deploy PR — see `DEPLOY-A2.md` to be authored when T3 lands):

1. **T3 first or T2 alone?** T2 is operationally complete on its own — selective export/restore + V1 compat already deliver Autonomy value. Deploy decision: only after T3 (tar.gz + embeddings + schema migration + HTTP/MCP) when the full A2 surface is ready.
2. **rsync to VPS** `staged-1.7a/edits/lib/export-import.ts` → `/root/.openclaw/workspace/tools/nox-mem/src/lib/export-import.ts`. Same for `cli/`. Rebuild `dist/index.js` on VPS via `npm run build`.
3. **CLI wire-up** — the existing `nox-mem export|import` subcommands gain `--tier` and `--tables` flags automatically. No new bin entries required.
4. **Documentation** — CLAUDE.md §7 to be amended with operational rule:
   - "Pre-import sempre `--dry-run` em archives untrusted antes de `--strategy replace`."
   - "T2 default: `--tier 2` (per-table). Para enviar bundle a recipient pre-T2, usar `--tier 1`."
5. **Smoke test on prod** — 10-row chunks-only subset export + import to `/tmp/test.db` first. Validate via row counts + `nox-mem stats` post-import.

---

## 8. Rollback Paths

| Failure mode | Rollback |
|---|---|
| Export crashes mid-write | `writeFileSync` is single-shot; partial write leaves the source DB untouched. No rollback needed. |
| Import crashes mid-insert (any table) | All mutations wrapped in `db.transaction(...)` — better-sqlite3 rolls back automatically on throw. |
| V2 decryption throws on table N | Transaction never starts (decryption happens before `tx()`). Target DB untouched. Verified in case 2 (tamper). |
| Subset import partial commit | Transaction wraps all subset inserts → all-or-nothing. |
| User accidentally re-imports same V2 bundle with `--strategy replace` over fresh DB | Idempotent — same result. With `--strategy merge` → 100% conflict, all rows reported as duplicates, 0 inserted. Confirmed by case 8 logic. |
| Wrong passphrase / tampered ciphertext | First table decrypt throws `TAMPERED_BUNDLE`. Target DB untouched (decryption before tx). |
| Pre-T2 V1 bundle imported by T2 CLI | `importEncryptedAuto` routes to V1 handler. Result shape matches T1 (case 5). |
| Forgot passphrase | Documented; no recovery. Same as T1. |
| Want to re-export from a bundle (round-trip without source DB) | NOT supported in T2. Re-export is a deploy-time concern handled by `nox-mem export` against the live DB. |

---

## 9. Compliance with Hard Rules

| Hard rule (from task spec) | Status |
|---|---|
| AES-256-GCM only — no fallback | yes — `const CIPHER = "aes-256-gcm"` reused from T1, no branch. |
| 2 SEPARATE DB instances in integration test | yes — case 1 + all roundtrip cases. |
| Per-table tamper test mandatory | yes — case 2 flips 1 byte in `chunks` ciphertext; full import fails; subset import of `kg_entities`+`kg_relations` succeeds. |
| Passphrase NEVER in code — env var only | yes — preserved from T1. |
| No mutation of `src/` — only `staged-1.7a/edits/` | yes — verified via `git diff --stat`. |
| No mutation of `main` — only `impl/a2-export-import-t2` | yes. |
| No PR merge (this audit only opens it) | yes. |
| No breaking changes to T1 paths | yes — T1 public functions preserved; CLI JSON output preserves v1 flat fields; 11/11 T1 tests still pass. |
| Pre-commit hook + gitleaks scan active | yes — no secrets in source; passphrases via env only. |

---

## 10. Known Gaps (documented for Tier 3)

1. **No streaming.** Per-table ciphertext is still loaded as a single `Buffer`. T3 will swap for NDJSON streaming for large tables.
2. **No `ops_audit` row for export/import.** T3 = wrap in `withOpAudit('export-v2', ...)` to land in the audit log with a snapshot.
3. **No HTTP API endpoints.** T3 = T12 from the full kickoff.
4. **No MCP tools.** T3 = T13.
5. **No schema-version migration.** T3 = T9 — for now, source/target schemas must match.
6. **No embeddings serialization.** T3 = T4 (with `[[buffer-pool-aliasing-in-typed-arrays]]` test mandatory).
7. **scrypt N=2^14.** T3 will bump to N=2^17. KDF params already AAD-bound, so format is forward-compat.
8. **Merge mode drops `id` column for `kg_relations`.** Inherited from T1. T3 implements FK remapping pass.
9. **No `--verify` integrity-only mode.** T3 = T11 sub-mode.
10. **Independent rekey-per-table CLI not implemented.** Format supports it (per-table IV/AAD/authTag); T3 will ship `nox-mem export --rekey-table chunks --new-passphrase-env X`.

---

## 11. Summary

A2 Tier 2 delivers per-table encryption (V2 bundle format), selective export, selective restore, and backward compatibility with V1 bundles through an auto-detecting importer. 24 tests pass (11 T1 preserved + 13 new T2). The cryptographic core is unchanged — same AES-256-GCM + scrypt + AAD-bound headers — extended with a new `table_name` AAD field that prevents cross-table ciphertext relocation attacks.

The PR is non-breaking. T1 public functions, CLI JSON output (including v1 flat fields), and existing test suite all preserved. Future T3 layers tar.gz, embeddings.bin, schema migration, HTTP/MCP, and `ops_audit` integration on top of an unchanged V2 envelope.

**Tier 2 unlocks the Autonomy pillar's most-requested capability:** users can now hand someone a `chunks-only` bundle without exposing their KG, or restore one table on a partner's machine without trampling the other two. Data is yours — and yours alone, table by table.
