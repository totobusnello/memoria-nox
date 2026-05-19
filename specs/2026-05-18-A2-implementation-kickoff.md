# A2 Implementation Kickoff — Export/Import (Encrypt-by-Default)

**ID:** A2-impl (Autonomy pillar centerpiece — Q/A/P framework)
**Status:** Kickoff aberto 2026-05-18. Implementation pending T1 start.
**Owner:** Toto (gate) — Forge (execução, sprint paralelo a P1)
**Trigger:** D41 #5 — A2 PARALLEL com P1 se capacity permitir.
**Branch base:** `main` (PR #9 spec merge precede T1 — confirmar antes de iniciar).

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."* — D45 tagline (D40 superseded).
> A2 é o **único** sprint que torna o pitch "data é sua, portable" verificável end-to-end.

---

## 0. Cross-References

| Origem | Conteúdo | Path |
|---|---|---|
| **A2 spec** | 602 linhas, 3,403 palavras, 18 sections — design completo, NÃO-fazemos v1, threat model | PR #9 / `specs/2026-05-17-A2-export-import.md` |
| **D41 #2** | **Encryption = opt-out** (encrypt by default). `--unencrypted` flag opt-out. Resolve a question #2 da spec PR #9. | `docs/DECISIONS.md` (D41 entry — registrar formalmente como parte do T0 deste kickoff) |
| **D41 #5** | A2 roda em PARALELO com P1 — não fila atrás. | `docs/DECISIONS.md` |
| **D40** | Q/A/P pivot — A2 é A2 (Autonomy pillar). 60/40 capacity split. Tagline. | `docs/DECISIONS.md` linha 448-491 |
| **CLAUDE.md repo** | Schema atual v.29 (drift-checked), 62.9k+ chunks, sqlite-vec 3072d, FTS5, KG entidades+relações | `CLAUDE.md` |
| **HANDOFF.md** | Estado vivo — confirmar ausência de blockers no início do sprint | `docs/HANDOFF.md` |

**Pré-condição absoluta:** PR #9 (A2 spec) merged antes de T1. Sem spec mergeado, kickoff é hipótese.

---

## 1. Decisão Locked: Encryption Default (D41 #2)

**Princípio:** *secure by default, transparent by manifest*. Resolve a question #2 da PR #9 a favor de opt-out.

### O que fica encriptado

- `chunks.jsonl`, `embeddings.bin`, `embeddings.idx`, `kg_entities.jsonl`, `kg_relations.jsonl`, `ops_audit.jsonl`, `schema.sql`, `provenance/**` (se `--include-sources`).

### O que fica em claro (sempre)

- `manifest.json` — counts, schema version, hostname, created_at, checksums, encryption metadata (algorithm, scrypt params, nonce, AAD hash). **Nunca chaves/valores de chunks.**

Justificativa: usuário pode `tar -xzf archive.tar.gz manifest.json && jq .` pra inspecionar archive sem passphrase — counts, versão, integridade. Crítico pra triagem operacional (qual archive importar quando há vários backups), zero leakage do conteúdo memorial.

### Flag opt-out

```bash
nox-mem export --out /backup/nox.tar.gz                          # encrypted (default, D41 #2)
nox-mem export --out /backup/nox.tar.gz --unencrypted             # plain (opt-out explícito)
```

`--unencrypted` exige confirmação interativa OU `NOX_EXPORT_UNENCRYPTED_ACK=1` em env (proteção contra accidente em scripts).

### Algorithm stack (locked)

| Camada | Escolha | Justificativa |
|---|---|---|
| Cipher | **AES-256-GCM** | Authenticated encryption — detecta tampering via GCM tag, AEAD nativo no Node `crypto.createCipheriv`. |
| KDF | **scrypt** N=2²⁷=131072, r=8, p=1, salt 16 bytes random | Memory-hard, anti-bruteforce. Node nativo (`crypto.scryptSync`). ~0.5-1s derive em laptop moderno — UX OK, attacker cost alto. |
| Nonce | Random 12 bytes per encryption (GCM standard) | Stored em manifest plano. Reuse com mesma key = catastrófico, por isso por-arquivo. |
| AAD | `sha256(manifest_plaintext_bytes)` | Tampering em manifest quebra GCM auth tag → import falha clean. |
| Passphrase input | `NOX_EXPORT_PASSPHRASE` env **ou** prompt interativo (`readline` w/ echo off). **Nunca** flag CLI (`ps` leak). | Hard rule — input validation no CLI rejeita `--passphrase=` flag. |

### Manifest encryption metadata (sempre claro)

```jsonc
{
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "kdf": "scrypt",
    "kdf_params": { "N": 131072, "r": 8, "p": 1 },
    "kdf_salt_b64": "...",
    "files": {
      "chunks.jsonl.enc": { "nonce_b64": "...", "tag_b64": "...", "ciphertext_sha256": "..." },
      "embeddings.bin.enc": { ... }
    },
    "aad_source": "sha256(manifest_pre_encryption_bytes)"
  }
}
```

Manifest é montado em duas fases: (1) plaintext manifest com counts/checksums/schema → (2) AAD = sha256(plaintext) → (3) encrypt files com AAD → (4) inject encryption metadata em manifest final, re-escreve. Counts e schema version já estão immutáveis na fase 1 (são source do AAD).

---

## 2. Archive Layout (Locked)

```
archive.tar.gz
├── manifest.json                  (UNENCRYPTED, sempre — D41 #2)
├── schema.sql                     (UNENCRYPTED — CREATE TABLE statements, plano)
├── chunks.jsonl.enc               (encrypted se default; sem .enc se --unencrypted)
├── embeddings.bin.enc             (idem)
├── embeddings.idx.enc             (idem — chunk_id → offset/length packing)
├── kg_entities.jsonl.enc
├── kg_relations.jsonl.enc
├── ops_audit.jsonl.enc
└── provenance/<project>/<files>   (opt-in via --include-sources)
```

`.enc` suffix sinaliza encryption per-file. `--unencrypted` produz `chunks.jsonl` sem suffix.

`tar -tzf archive.tar.gz` lista layout sem decryption. `tar -xzf archive.tar.gz manifest.json` extrai só manifest. Ambos são DoD obrigatório.

---

## 3. Task Breakdown (dependency-ordered)

> Convenção: cada task é checkpoint commit. PR final agrupa T1..T18. Tests vivem ao lado do módulo (`__tests__/`).

### Foundation (T1-T2)

#### T1. Archive format module (TAR.gz packer/unpacker)
- **Path:** `src/lib/archive/format.ts`
- **Estimativa:** 3h
- **Depende de:** nada
- **DoD:**
  - `pack(files: ArchiveEntry[], dest: WritableStream): Promise<void>` — streaming, **nunca buffer full archive em RAM** (DB 1.24GB → archive pode ultrapassar).
  - `unpack(src: ReadableStream, dest: string): Promise<ArchiveEntry[]>` — extract listing + paths, streaming.
  - `list(src: ReadableStream): Promise<string[]>` — só lista entries sem extract (para `--verify` rápido).
  - Usar `tar-stream` (npm, streaming) + `zlib.createGzip()` — nada de syscall ao `tar` binário.
  - Unit tests: pack→unpack round-trip de 10MB e 500MB synthetic data, validar byte-equality + memory peak <100MB.

#### T2. Manifest schema + writer/parser
- **Path:** `src/lib/archive/manifest.ts`, `src/lib/archive/types.ts`
- **Estimativa:** 2h
- **Depende de:** T1 (para append na ordem certa no tar)
- **DoD:**
  - `ManifestV1` TypeScript type cobrindo: `schema_version`, `created_at`, `source_hostname`, `nox_mem_version`, `counts: { chunks, embeddings, kg_entities, kg_relations, ops_audit }`, `checksums: { [file]: sha256 }`, `encryption` (object | null), `partial_filters: { project?, since? }`.
  - `writeManifest(m: ManifestV1): Buffer` — JSON canonical (sorted keys, no whitespace ambiguity — necessário para AAD stability).
  - `parseManifest(buf: Buffer): ManifestV1` — Zod validation, throws com mensagem clara em version mismatch.
  - JSON Schema export em `specs/schema/manifest-v1.schema.json` para third-party tooling.

### Serializers (T3-T6, paralelizáveis)

#### T3. Chunks serializer
- **Path:** `src/lib/archive/serializers/chunks.ts`
- **Estimativa:** 3h
- **Depende de:** T2
- **DoD:**
  - `exportChunks(db, filters): AsyncIterable<string>` — streaming JSONL (uma row por linha), respeita `--project` e `--since` filters via prepared statements.
  - `importChunks(stream, db, mode): Promise<ImportStats>` — modes `merge` (skip se chunk_id existe) e `replace` (DELETE + INSERT em transaction).
  - Preserva **todos** schema v.29 columns: `retention_days`, `pain`, `section`, `section_boost`. Faltar qualquer um = test failure.
  - Round-trip: SELECT count + sha256(canonical_dump) idêntico pré/pós.

#### T4. Embeddings serializer
- **Path:** `src/lib/archive/serializers/embeddings.ts`
- **Estimativa:** 4h
- **Depende de:** T2, T3
- **DoD:**
  - Binário packed: `embeddings.bin` = concatenação de Float32Array (3072 dim × N rows × 4 bytes). Cabeçalho 16 bytes: magic `NOXEMBED`, version uint32, dim uint32.
  - `embeddings.idx` = JSONL `{ chunk_id, offset, length, model_name, embedded_at }` — permite seek O(1) sem load all.
  - **CRITICAL — Buffer pool aliasing trap (memory feedback `feedback_buffer_pool_aliasing_in_typed_arrays`):** ao reconstruir Float32Array no import, copiar via Uint8Array intermediate, **nunca** `new Float32Array(buffer.buffer, offset, len)` direto.
  - sqlite-vec version pinned em manifest (`embeddings.sqlite_vec_version`). Import falha clean se mismatch (risk #2).
  - `--exclude-embeddings` flag pula este serializer, manifest registra `embeddings.skipped: true`.

#### T5. KG serializer
- **Path:** `src/lib/archive/serializers/kg.ts`
- **Estimativa:** 3h
- **Depende de:** T2, T3
- **DoD:**
  - `kg_entities.jsonl` — uma entity per line, todos campos schema v.29 (incluindo `kind`, `slug`, `aliases`, `frontmatter_json`).
  - `kg_relations.jsonl` — `{ source_entity_id, target_entity_id, predicate, confidence, ... }`. **Memory feedback `feedback_kg_relations_uses_fk_ids_not_inline_strings`:** FK ids inteiros, NÃO strings inline. Import precisa de mapping pass se merge.
  - Merge mode: remap IDs via slug+kind unique key (entities) e dual-join (relations). Stats reportam `entities_added`, `entities_skipped`, `relations_added`, `relations_skipped_due_to_missing_fk`.

#### T6. ops_audit serializer
- **Path:** `src/lib/archive/serializers/ops_audit.ts`
- **Estimativa:** 1.5h
- **Depende de:** T2
- **DoD:**
  - `ops_audit.jsonl` — append-only preservation. CLAUDE.md regra #6: ops_audit é append-only (W2-1 trigger CWE-693). Importer **nunca** DELETE/UPDATE rows existentes; sempre INSERT.
  - Replace mode em outras tabelas NÃO afeta ops_audit (log histórico preservado).
  - Test: export + import com `--merge` em DB já populado mantém todas rows source + dest, ordenadas por id.

### Encryption (T7-T8)

#### T7. Encryption wrapper
- **Path:** `src/lib/archive/encryption.ts`
- **Estimativa:** 4h
- **Depende de:** T2 (AAD source = manifest plaintext)
- **DoD:**
  - `deriveKey(passphrase: string, salt: Buffer): Buffer` — scrypt N=131072 r=8 p=1, 32 bytes output.
  - `encryptStream(plaintext: Readable, key: Buffer, aad: Buffer): { ciphertext: Readable, nonce: Buffer, tag: Buffer }` — streaming, GCM, nonce random.
  - `getPassphrase(): Promise<string>` — primeiro `NOX_EXPORT_PASSPHRASE`, fallback `readline` echo-off interactive. **Rejects** `--passphrase=` flag pattern via CLI argv pre-validation.
  - Tampering test: modify ciphertext byte → decrypt throws com mensagem que distingue "bad passphrase" vs "ciphertext tampered" (GCM tag mismatch é detectável).

#### T8. Decryption wrapper + integrity validation
- **Path:** `src/lib/archive/encryption.ts` (mesmo arquivo, função `decryptStream`)
- **Estimativa:** 2h
- **Depende de:** T7
- **DoD:**
  - `decryptStream(ciphertext: Readable, key: Buffer, nonce: Buffer, tag: Buffer, aad: Buffer): Readable`.
  - AAD recomputado de manifest plaintext local — se manifest foi tampered, AAD diverge → GCM tag rejection.
  - Erros claros: `BadPassphraseError`, `TamperedArchiveError`, `MissingAADError`.

### Migration (T9)

#### T9. Schema migration logic
- **Path:** `src/lib/archive/migration.ts`
- **Estimativa:** 3h
- **Depende de:** T2 (lê schema_version do manifest)
- **DoD:**
  - `canImport(archive_version: number, current_version: number): { ok: true } | { ok: false, reason: string }`.
  - Forward auto-migrate v18 → v19 → ... → current (chain de patches em `src/lib/archive/migrations/v18_to_v19.ts`, etc).
  - Backward fail clearly: archive v19 + DB v18 → erro `"Archive schema version 19 is newer than current nox-mem schema version 18. Upgrade nox-mem before importing."` (mensagem actionable, não cryptic).
  - Same-version no-op.
  - Migrations rodam em transaction; falha em qualquer step rollback completo + erro propaga.

### CLI (T10-T11)

#### T10. CLI `nox-mem export`
- **Path:** `src/cli/export.ts`
- **Estimativa:** 4h
- **Depende de:** T1-T9
- **DoD:**
  - Flags: `--out <path>` (mandatory), `--project <name>`, `--since <iso8601>`, `--exclude-embeddings`, `--unencrypted`, `--include-sources`.
  - Default: encrypted (D41 #2). `--unencrypted` exige `NOX_EXPORT_UNENCRYPTED_ACK=1` env ou prompt `[Y/N]`.
  - Wrapped em `withOpAudit('export', ...)` — append-only audit row antes/após (CLAUDE.md regra #6).
  - Output stream: stdout `[1/6] Packing chunks (12345 rows)...` etc — UX visível em archives grandes.
  - Exit code: 0 success, 1 user error (bad flag), 2 system error (disk full, db lock).

#### T11. CLI `nox-mem import`
- **Path:** `src/cli/import.ts`
- **Estimativa:** 4h
- **Depende de:** T1-T9
- **DoD:**
  - Flags: `--in <path>` (mandatory), `--merge` | `--replace` (mutually exclusive, `--merge` default), `--dry-run`, `--verify`.
  - `--dry-run`: extract + validate manifest + checksums + schema compat + count diffs, **never writes to DB**. Memory feedback aplicado: dry-run produz JSON preview.
  - `--verify`: extract + decrypt + integrity check (checksums, GCM tags, FK referential integrity em KG) **never writes to DB**.
  - `--merge`: skip duplicates por chunk_id / entity (slug, kind).
  - `--replace`: TRUNCATE chunks/embeddings/kg_*/ + bulk insert, em transaction. ops_audit append-only preservado.
  - Wrapped em `withOpAudit('import', ...)`. Snapshot pre-import obrigatório (CLAUDE.md regra #6).

### HTTP API (T12)

#### T12. HTTP endpoints
- **Path:** `src/api/export.ts`, `src/api/import.ts`
- **Estimativa:** 3h
- **Depende de:** T10, T11
- **DoD:**
  - `POST /api/export` — body JSON com flags subset (project, since, encrypted, exclude_embeddings); response streams `application/gzip`. Content-Disposition com nome canonical.
  - `POST /api/import` — multipart upload do archive + JSON params (mode, verify). Response streams progress NDJSON.
  - Auth: reusa middleware existente da API porta 18802 (CLAUDE.md regra #4).
  - Streaming throughout — never buffer full archive server-side.

### MCP tools (T13)

#### T13. MCP tools
- **Path:** `src/mcp/tools/export.ts`, `src/mcp/tools/import.ts`
- **Estimativa:** 2h
- **Depende de:** T10, T11
- **DoD:**
  - `nox_mem_export` tool — params iguais ao CLI, output: path do archive criado.
  - `nox_mem_import` tool — params iguais ao CLI, output: JSON stats (rows imported, conflicts, duration).
  - Adiciona aos 16 tools existentes (CLAUDE.md MCP Server count vira 18).

### Tests (T14-T17)

#### T14. Round-trip test suite (golden path)
- **Path:** `src/lib/archive/__tests__/roundtrip.test.ts`
- **Estimativa:** 3h
- **Depende de:** T10, T11, T13
- **DoD:**
  - Export DB A → import em DB B vazio → SELECT counts + sha256 dumps idênticos.
  - Round-trip preserva nDCG@10 ±0.001 em eval harness (run 10 queries golden set pre/post).
  - Round-trip preserva ranking de top-50 chunks em search hybrid.
  - Tested com encrypted e `--unencrypted`.

#### T15. Encryption round-trip + tamper tests
- **Path:** `src/lib/archive/__tests__/encryption.test.ts`
- **Estimativa:** 3h
- **Depende de:** T7, T8, T14
- **DoD:**
  - Encrypt → decrypt round-trip preserva bytes 100%.
  - Modify 1 byte em `chunks.jsonl.enc` → import throws `TamperedArchiveError` com GCM tag mismatch.
  - Modify 1 byte em `manifest.json` (e.g. counts) → AAD diverge → import throws.
  - Wrong passphrase → `BadPassphraseError`, nunca silent garbage.
  - `strings archive.tar.gz` em encrypted archive **não** retorna texto reconhecível de chunks (smoke pra "encryption real, não cosmética").
  - Passphrase via env override testado; CLI `--passphrase=` flag rejeitado em parse.

#### T16. Partial export tests
- **Path:** `src/lib/archive/__tests__/partial.test.ts`
- **Estimativa:** 2h
- **Depende de:** T10, T14
- **DoD:**
  - Export `--project nox-mem` → archive contém só chunks com project tag, manifest counts batem.
  - Export `--since 2026-05-01` → só chunks created_at ≥ data.
  - KG referential integrity: relations cujos endpoints estão fora do filtro são **excluded** (com warning count), nunca dangling FK no import.

#### T17. Schema version mismatch tests
- **Path:** `src/lib/archive/__tests__/migration.test.ts`
- **Estimativa:** 2h
- **Depende de:** T9, T14
- **DoD:**
  - Archive v18 + DB v19 → auto-migrate, success, counts match após migration.
  - Archive v19 + DB v18 → fail clean com mensagem actionable ("Upgrade nox-mem...").
  - Archive v18 + DB v18 → no-op direct import.
  - Migration failure mid-chain → transaction rollback, DB intacto.

### Docs (T18)

#### T18. Documentation
- **Path:** `docs/EXPORT-IMPORT.md` + updates em `CLAUDE.md` + entry em `docs/HANDOFF.md`
- **Estimativa:** 2h
- **Depende de:** T1-T17
- **DoD:**
  - User-facing guide cobrindo: backup workflow, laptop migration, multi-project split, encryption mental model, tamper detection.
  - "How to inspect archive without passphrase" — `tar -xzf archive.tar.gz manifest.json && jq .` documentado prominently (vende o design choice).
  - CLAUDE.md regra adicional: pre-import sempre `--verify` em archives untrusted.
  - DECISIONS.md D41 formalizado com pointer pra este kickoff.

---

## 4. File Structure

```
src/
├── cli/
│   ├── export.ts                              # T10
│   └── import.ts                              # T11
├── lib/archive/
│   ├── index.ts                               # public exports
│   ├── format.ts                              # T1 — TAR.gz packer/unpacker
│   ├── manifest.ts                            # T2 — schema, writer, parser
│   ├── types.ts                               # T2 — TypeScript types
│   ├── encryption.ts                          # T7+T8 — AES-256-GCM + scrypt
│   ├── migration.ts                           # T9 — schema version handling
│   ├── migrations/
│   │   └── v18_to_v19.ts                      # placeholder; populated when v19 lands
│   ├── serializers/
│   │   ├── chunks.ts                          # T3
│   │   ├── embeddings.ts                      # T4
│   │   ├── kg.ts                              # T5
│   │   └── ops_audit.ts                       # T6
│   └── __tests__/
│       ├── roundtrip.test.ts                  # T14
│       ├── encryption.test.ts                 # T15
│       ├── partial.test.ts                    # T16
│       └── migration.test.ts                  # T17
├── api/
│   ├── export.ts                              # T12
│   └── import.ts                              # T12
└── mcp/tools/
    ├── export.ts                              # T13
    └── import.ts                              # T13

specs/schema/
└── manifest-v1.schema.json                    # T2 — JSON Schema for third-party tooling

docs/
└── EXPORT-IMPORT.md                           # T18
```

---

## 5. Test Plan (Consolidated)

| Categoria | Tests | Owner task |
|---|---|---|
| Round-trip golden path | export → import → diff (counts, sha256 dumps, nDCG@10 ±0.001) | T14 |
| Encryption round-trip | encrypt → decrypt → byte-identity; `strings` smoke | T15 |
| Encryption tamper | ciphertext byte-flip, manifest byte-flip → throws | T15 |
| Encryption auth | wrong passphrase, missing env, `--passphrase=` flag rejection | T15 |
| Partial export | `--project`, `--since`, KG FK integrity | T16 |
| Version mismatch | v18→v19 forward, v19→v18 fail, v18→v18 no-op | T17 |
| Streaming/memory | export of 1.24GB DB → peak RSS <500MB | T1, T14 |
| Dry-run parity | `--dry-run` produces preview JSON, **zero DB writes** (assert via mtime + ops_audit) | T11 |
| --verify mode | decrypt + integrity check, **zero DB writes** | T11 |
| FK referential | partial export excludes dangling KG relations with warning | T16 |
| Sources opt-in | `--include-sources` adds `provenance/`, defaults excluded | T10 |
| ops_audit append-only | merge + replace preservam todas rows ops_audit pré-existentes | T6, T11 |

---

## 6. Definition of Done (Overall — 6 numbered criteria)

1. **Round-trip integrity:** export → import preserva nDCG@10 ±0.001 em golden set de 10 queries, validado pelo eval harness (W2.1).
2. **Encryption by default:** sem flag, archive sai encrypted; `--unencrypted` exige ACK explícito; default cobre 100% do conteúdo memorial (chunks, embeddings, KG, ops_audit, schema, provenance).
3. **Encryption real:** `strings encrypted.tar.gz` **não retorna texto recognizível** de chunks; tampering detectado clean via GCM tag.
4. **Open-toolchain inspect:** `tar -tzf archive.tar.gz` lista entries e `tar -xzf archive.tar.gz manifest.json` extrai manifest **sem qualquer ferramenta nox-mem proprietária**. Manifest é JSON canonical legível.
5. **--verify completes without DB write:** integrity check (checksums, GCM tags, FK referential) prova sanidade do archive sem modificar nox-mem. Validado via `stat -c %Y` da DB pre/pós + `ops_audit.count` invariante.
6. **All 18 tasks (T1-T18) merged, tests passing CI verde, docs updated (CLAUDE.md + HANDOFF.md + EXPORT-IMPORT.md).**

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Partial export breaks KG relation FK refs (dangling source/target ids) | M | H | T16 test + `--verify` mode roda referential integrity check; partial export exclui relations com endpoints fora do filtro + warning count em manifest. |
| Embedding format drift across sqlite-vec versions | L | H | Pin sqlite-vec version em `manifest.embeddings.sqlite_vec_version`; import falha clean se mismatch. T4 DoD. |
| Large archive RAM blowup (1.24GB DB → archive maior) | M | M | Streaming throughout — `tar-stream` + `zlib.createGzip()` pipe, **nunca** `Buffer.concat()` em payload. T1 DoD test com 500MB synthetic + memory peak <100MB. T14 valida 1.24GB real. |
| Passphrase leakage via process listing | L | CRITICAL | Hard rule: NUNCA aceitar `--passphrase=` flag; só env ou interactive prompt; T7 DoD inclui CLI argv rejection test. |
| `--replace` mode wipes ops_audit accidentally | L | H | ops_audit append-only enforced at serializer level (T6); test cobre merge+replace preservation. CLAUDE.md regra #6 reinforced. |
| Manifest JSON canonicalization drift entre engines | L | M | T2 usa stable serializer (sorted keys, fixed encoding); AAD = sha256 do output desse serializer. Documentado em manifest schema. |
| User runs `--unencrypted` por acidente em script | L | H | T10 exige `NOX_EXPORT_UNENCRYPTED_ACK=1` em env quando stdin não é TTY; prompt interativo em TTY. Belt + suspenders. |
| sqlite-vec ABI break em minor version bump | L | H | Manifest pinning (T4) + CI canary que importa archive antigo após version bump do sqlite-vec; falha alerta. |

---

## 8. Timeline Estimate

| Task | Hours |
|---|---|
| T1 — Archive format | 3 |
| T2 — Manifest | 2 |
| T3 — Chunks serializer | 3 |
| T4 — Embeddings serializer | 4 |
| T5 — KG serializer | 3 |
| T6 — ops_audit serializer | 1.5 |
| T7 — Encryption wrapper | 4 |
| T8 — Decryption wrapper | 2 |
| T9 — Schema migration | 3 |
| T10 — CLI export | 4 |
| T11 — CLI import | 4 |
| T12 — HTTP endpoints | 3 |
| T13 — MCP tools | 2 |
| T14 — Round-trip tests | 3 |
| T15 — Encryption tests | 3 |
| T16 — Partial export tests | 2 |
| T17 — Migration tests | 2 |
| T18 — Documentation | 2 |
| **Total** | **50.5h** |

**Sprint window:** 4-5 dias de execução Forge focado, ou ~7-8 dias em paralelo com P1 (D41 #5). Buffer 20% para integração / debugging cross-task → **~60h realistic**.

**Crítica de paralelização:** T3-T6 podem rodar em paralelo após T2 done. T14-T17 podem rodar em paralelo após T10+T11 done. Caminho crítico: T1 → T2 → T3 → T10 → T11 → T14 ≈ 23h.

---

## 9. Open Questions (Non-Blocking)

1. **Compression algo default — gzip vs zstd?** Spec PR #9 propõe gzip (Linux/Mac native, ferramenta padrão). zstd dá ~20-30% melhor ratio + 3x speed mas exige `zstd` instalado. **Recomendação:** gzip default (open-toolchain DoD #4), `--compression zstd` flag opt-in pra power users. Decidir até T1.
2. **Max archive size warning threshold?** Em 5GB? 10GB? Manifest pode prever `--split <N_GB>` futuro. **Recomendação:** warn em ≥10GB no T10 export, no split em v1.
3. **`--include-sources` path resolution rules?** Symlinks resolved ou preserved? Files outside `OPENCLAW_WORKSPACE` skipped ou error? **Recomendação:** symlinks resolved via `realpathSync`, files outside workspace = error com `--allow-external-sources` opt-in flag. Decidir antes de T10.
4. **Encryption header version field?** Quando subirmos para post-quantum cipher em v2, manifest precisa de `encryption.format_version: 1`. **Recomendação:** já adicionar em T2 manifest schema, mesmo só com valor 1, pra forward-compat.

---

## 10. Handoff

Após PR merge:

```bash
nox-mem export --out /tmp/test.tar.gz                           # encrypted default
tar -tzf /tmp/test.tar.gz                                       # lista entries (manifest plain)
tar -xzf /tmp/test.tar.gz manifest.json -O | jq .counts         # inspect sem passphrase
nox-mem import --in /tmp/test.tar.gz --dry-run                  # preview JSON
nox-mem import --in /tmp/test.tar.gz --verify                   # integrity only
nox-mem import --in /tmp/test.tar.gz --merge                    # apply
```

Demo end-to-end vira asset de marketing pra Autonomy pillar — "data é sua, portable" verificável em 5 comandos.

---

*Origem: D41 (encrypt-by-default) + D40 (Q/A/P pivot) + A2 spec PR #9. Sprint kickoff 2026-05-18 overnight push. Implementação iniciar após PR #9 merged.*
