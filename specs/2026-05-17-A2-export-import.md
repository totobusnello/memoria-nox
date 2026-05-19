# A2 — Schema Export/Import Portability

**ID:** A2 (Autonomy pillar — Q/A/P framework)
**Status:** 📐 Spec aberto 2026-05-17. Implementação NÃO iniciada — autorização explícita pendente.
**Owner:** Toto (decisão) — Forge (execução proposta)
**Data:** 2026-05-17
**Cross-link:** `docs/VISION.md` (Q/A/P pillars), `docs/DECISIONS.md` (a registrar: D40 — portability format), `docs/HANDOFF.md` (próxima ação pós-A2 spec)
**Disambiguação:** este "A2" é o **ID da feature do pilar Autonomia (A) #2 — export/import**. NÃO confundir com "A2" do E14 (alavanca refutada de dense-pool expansion, ver `specs/2026-05-10-E14-retrieval-evolution.md`).

---

## 1. Motivação

**Tagline pilar Autonomia:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

A2 é o **centerpiece operacional** desse tagline. Não basta o DB rodar localmente em SQLite — autonomia real é o usuário poder pegar a memória dele e levar para **qualquer lugar**: outro laptop, outro OS, outro provedor de embeddings, outra versão de schema. Sem proprietary tooling. Sem servidor remoto. Sem refém de versão.

**Pitch interno:** *"Your memory is a portable archive you can take anywhere — `tar -tzf` your brain."*

### Diferenciação competitiva

| Concorrente | Modelo de dados | Portabilidade |
|-------------|-----------------|---------------|
| **memanto** | SaaS — dados em servidores Moorcheh | ❌ Refém do provedor |
| **agentmemory** | Local mas exige `iii-engine` rodando | ⚠️ Sem engine → DB inacessível |
| **mem0** | Cloud-first (mem0 platform) ou self-host complexo | ⚠️ Export limitado a snapshots JSON simples |
| **nox-mem (hoje)** | SQLite local (`cp nox-mem.db /backup/` funciona) | ✅ DB é seu — mas binário, não portável cross-version |
| **nox-mem + A2** | SQLite + arquivo portátil (`tar -tzf`, diffável, opcionalmente encriptado) | ✅✅ **Self-sovereign by design** |

A2 fecha o gap: hoje você já tem o DB, mas mover entre máquinas (especialmente com schema diferente) exige ritual manual. A2 transforma isso em um one-liner.

### Por que agora

- v3.7 estabilizou em ~63K chunks. Volume real importa pra teste de portabilidade.
- Schema v18 (LATEST após v10 base + 8 migrations) — pipeline de migração maduro o suficiente pra honrar version-forward semântica.
- Shadow discipline empírica (paper R02): qualquer feature de Autonomy deve seguir mesma discipline — A2 entrega valor sem mutar ranking, é ortogonal ao retrieval. Ship safe.

---

## 2. User Stories

### Story (a) — Backup para destino arbitrário

> *"Como usuário, quero exportar minha memória para um arquivo único que posso copiar pra S3, Dropbox, USB, qualquer coisa — sem dependência do nox-mem rodando no destino."*

```bash
# Backup semanal cron na VPS
nox-mem export --out /var/backups/nox-mem/weekly-$(date +%Y%m%d).tar.gz

# Usuário pipa pra onde quiser
nox-mem export | aws s3 cp - s3://my-bucket/nox-mem-backup.tar.gz
nox-mem export | rclone rcat dropbox:backups/nox-mem.tar.gz
```

**Aceite:** archive resultante abre com `tar -tzf` standard. Nenhuma ferramenta proprietária pra inspecionar.

### Story (b) — Migração laptop → nova máquina

> *"Comprei MacBook novo. Quero pegar memória do velho (Linux/VPS), trazer pro novo (macOS), e continuar de onde parei — inclusive se o nox-mem novo tem schema mais novo."*

```bash
# Máquina antiga
nox-mem export --out ~/nox-mem-migration.tar.gz

# Máquina nova (schema v19 vs export v18)
nox-mem import ~/nox-mem-migration.tar.gz --merge
# → detecta v18 < v19, aplica migrations forward, importa
```

**Aceite:** zero perda de chunks. KG entities preservadas. Embeddings re-utilizáveis (mesmo provider) ou re-geráveis (provider diferente).

### Story (c) — Split de memória por projeto

> *"Quero separar memória de Granix (confidencial cliente) da memória de hobby projects. Exportar só Granix pra arquivo encriptado, deletar do DB principal."*

```bash
# Export filtrado + encriptado
nox-mem export --project granix --since 2026-01-01 --encrypt - --out granix-mem.tar.gz.enc
# Prompt seguro pede password (não argv leak)

# Verificar antes de qualquer destrutiva
nox-mem import --verify granix-mem.tar.gz.enc --decrypt -
```

**Aceite:** `--project` filtra chunks com tag/metadata correspondente. Referential integrity validada (sem KG dangling refs).

---

## 3. CLI Shape

### Export

```
nox-mem export [OPTIONS]

OPTIONS:
  --out <path>              Caminho do archive de saída. Default: stdout (pipe-friendly).
  --project <name>          Filtro: só chunks com metadata.project == <name>. Repetível.
  --since <ISO8601>         Filtro: chunks com created_at >= <date>.
  --until <ISO8601>         Filtro: chunks com created_at <= <date>.
  --format tar|zip|sqlite-dump  Default: tar (tar.gz). zip pra Windows-friendly. sqlite-dump = raw .sql dump (debug).
  --exclude-embeddings      Pula embeddings.bin. Reduz ~80% do tamanho. Reimport re-embedda.
  --exclude-kg              Pula kg_entities + kg_relations. Standalone chunks-only archive.
  --exclude-audit           Pula ops_audit. Default: incluído (append-only invariant).
  --include-sources         Inclui arquivos originais em provenance/<project>/<file>.
  --encrypt <password|->    Encripta payload (AES-256-GCM). "-" lê de stdin (sem argv leak).
  --compression-level <0-9> Default: 6. 0 = sem compressão. 9 = max.
  --dry-run                 Não escreve; reporta tamanho estimado + counts.
```

### Import

```
nox-mem import <archive> [OPTIONS]

OPTIONS:
  --merge                   Default. Dedup via content_hash + canonical_name. ops_audit append.
  --replace                 Full DB drop + rebuild from archive. EXIGE --force.
  --force                   Confirma operação destrutiva (--replace).
  --dry-run                 Não muta; reporta o que seria inserido/updated/skipped.
  --verify                  Read-only: valida checksums + schema compat. Não toca DB.
  --decrypt <password|->    Decripta archive. "-" lê de stdin.
  --skip-embeddings         Importa metadata mas pula vec_chunks (regenera depois via vectorize).
  --on-conflict skip|error  Default: skip (merge mode). error aborta no primeiro conflito.
  --concurrency <N>         Workers para inserção paralela. Default: 4.
```

### Exemplos

```bash
nox-mem export --out backup.tar.gz
nox-mem export --project granix --encrypt - --out granix.enc.tar.gz
nox-mem import backup.tar.gz --merge --dry-run
nox-mem import --verify backup.tar.gz   # read-only check
nox-mem import old.tar.gz --replace --force   # nuke + restore
```

---

## 4. HTTP API Shape

Autenticação obrigatória (`Authorization: Bearer <token>` — token configurado em `.env`).

### `POST /api/export`

```http
POST /api/export HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "project": "granix",
  "since": "2026-01-01",
  "format": "tar",
  "exclude_embeddings": false,
  "encrypt": false
}
```

**Response:** stream `application/gzip` ou `application/octet-stream` (se encriptado). Headers:
- `X-Nox-Export-Manifest-Checksum: <sha256>` — checksum do manifest pra integridade out-of-band.
- `X-Nox-Export-Chunks-Count: <N>`.
- `X-Nox-Export-Schema-Version: <V>`.

Streaming obrigatório (transfer-encoding chunked) — DBs grandes (~1.5GB) não cabem em buffer.

### `POST /api/import`

```http
POST /api/import?mode=merge&dry_run=false HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/gzip
Content-Length: <N>

<binary archive>
```

**Response (JSON):**
```json
{
  "op_id": "import-2026-05-18-001",
  "schema_version_archive": 18,
  "schema_version_target": 19,
  "migration_applied": ["v18_to_v19_add_pain_normalize"],
  "chunks_inserted": 12455,
  "chunks_skipped_dedup": 873,
  "kg_entities_inserted": 402,
  "kg_entities_merged": 56,
  "ops_audit_appended": 198,
  "embeddings_skipped": 0,
  "duration_ms": 47832,
  "warnings": []
}
```

**Error response:** schema downgrade detectado, decrypt fail, checksum mismatch → 4xx com payload `{ error_code, message, archive_schema, target_schema }`.

---

## 5. Archive Format

**Container:** `tar.gz` (default) | `zip` (Windows-friendly) | `sqlite-dump` (debug-only, NOT portable).

### Estrutura

```
nox-mem-export-2026-05-17-<hostname>.tar.gz
├── manifest.json                  # SEMPRE PRIMEIRO (header-readable mesmo encriptado)
├── schema.sql                     # CREATE TABLE statements full
├── chunks.jsonl                   # 1 row JSON por linha
├── embeddings.bin                 # packed float32 (3072d × N_chunks × 4 bytes)
├── embeddings.idx                 # {chunk_id: byte_offset} map
├── kg_entities.jsonl
├── kg_relations.jsonl
├── ops_audit.jsonl
├── search_telemetry.jsonl         # opt-in: --include-telemetry
└── provenance/                    # opt-in: --include-sources
    └── <project>/
        └── <original-files>
```

### `manifest.json` (schema)

```json
{
  "format_version": "1.0",
  "schema_version": 18,
  "created_at": "2026-05-17T22:14:08-03:00",
  "source_hostname": "vps-hostinger-amsterdam",
  "source_nox_mem_version": "3.7.2",
  "embedding_provider": "gemini",
  "embedding_model": "gemini-embedding-001",
  "embedding_dim": 3072,
  "includes": ["chunks", "embeddings", "kg", "audit"],
  "filters": {
    "project": "granix",
    "since": "2026-01-01",
    "until": null
  },
  "counts": {
    "chunks": 12455,
    "embeddings": 12450,
    "kg_entities": 402,
    "kg_relations": 544,
    "ops_audit": 198
  },
  "checksums": {
    "chunks.jsonl": "sha256:abc...",
    "embeddings.bin": "sha256:def...",
    "kg_entities.jsonl": "sha256:...",
    "kg_relations.jsonl": "sha256:...",
    "ops_audit.jsonl": "sha256:...",
    "schema.sql": "sha256:..."
  },
  "encryption": {
    "enabled": false,
    "algorithm": null,
    "kdf": null
  }
}
```

### Por que JSONL ao invés de sqlite direto

- **Diffável:** `diff <(jq -S .id chunks.jsonl)` cross-archive.
- **Portável cross-version:** schema v18 → v19 migration roda no import, JSONL é format-stable.
- **Streamable:** parse line-by-line sem carregar tudo em RAM.
- **Tool-agnostic:** `jq`, `awk`, Python sem sqlite3 binding — qualquer um lê.

**Tradeoff:** archive ~30% maior que sqlite raw. Aceito — autonomia > tamanho.

### Embeddings: binário packed

JSONL pra embeddings (3072 floats × 63K chunks) seria absurdo (~3GB texto). Solução:

- `embeddings.bin` — concatenação raw float32 little-endian (Node `Buffer.writeFloatLE`).
- `embeddings.idx` — JSON map `{chunk_id: byte_offset}`. Permite seek random.

Documentar layout no manifest pra cross-version reads.

---

## 6. Schema Version Handling

| Archive Schema | Target Schema | Comportamento |
|----------------|---------------|---------------|
| v18 | v18 | Import direto. |
| v18 | v19 (newer) | **Forward migration:** roda migrations v18→v19 nos dados importados antes de inserir. Log em ops_audit. |
| v19 | v18 (older) | **FAIL HARD.** Mensagem clara: *"Archive schema v19 newer than target v18. Upgrade target nox-mem first (`npm install -g openclaw-nox-mem@latest`) ou export com `--target-schema v18` no source (não implementado v1)."* Sem auto-downgrade — risco de perda de campos. |
| v18 | v20 (+2) | Chain v18→v19→v20 (cada migration roda). Auditado. |

### Migrations forward

Migrations vivem em `src/migrations/v<N>_to_v<N+1>.ts`. Cada uma:
1. Recebe rows JSONL no schema antigo.
2. Retorna rows JSONL no schema novo (transform pure).
3. Idempotente (re-rodar = no-op).

Import pipeline aplica em sequência:
```
archive (v18) → migrate v18→v19 → migrate v19→v20 → insert (v20)
```

Cada migration registra entrada em `ops_audit` (status='success'|'failed', metadata={migration_id, rows_transformed}).

---

## 7. Encryption

### Modelo

- **Algoritmo:** AES-256-GCM (Node crypto built-in, FIPS-validatable).
- **KDF:** scrypt (N=2^17, r=8, p=1) → 32-byte key from password.
- **IV:** random 12 bytes por archive (armazenado em manifest header).
- **AAD:** sha256(manifest.json) — autentica manifest contra tampering.
- **Salt:** random 16 bytes por archive (manifest header).

### Layout encriptado

```
[ manifest.json (UNENCRYPTED, ~2KB) ]    # User sees what's inside
[ encryption_header (salt + iv) ]
[ encrypted_payload (everything else, GCM-protected) ]
[ gcm_tag (16 bytes) ]
```

**Por que manifest unencrypted:**
- Usuário consegue `tar -xzf archive.enc.tar.gz manifest.json` e ler counts/version/hostname sem decrypt.
- Manifest **não vaza conteúdo** (só metadata estatística).
- Decrypt requer password → payload selado.

### Password input

- CLI: `--encrypt -` lê stdin (`getpass`-style, sem echo). NUNCA argv.
- HTTP: `X-Nox-Encryption-Password` header sobre TLS-only (recusa se conexão HTTP plain).

### Threat model documentado

| Ataque | Mitigação |
|--------|-----------|
| Roubo de archive no trânsito | AES-256-GCM cobre payload. Manifest stat-only. |
| `strings` exfiltration | Payload encriptado — strings retorna lixo binário (gcm_tag detecta tamper). |
| Brute-force password fraco | scrypt N=2^17 → ~250ms/tentativa em CPU moderna. 8-char alphanumeric = ~2.5 anos GPU. Documentar uso de passphrase ≥16 chars. |
| Replay attack | Cada archive tem IV+salt único → mesma password produz ciphertext diferente. Não impede replay do mesmo archive — mitigação out-of-scope v1 (usuário rota password). |
| Manifest tamper (mudar counts pra confundir audit) | AAD = sha256(manifest) → GCM tag falha decrypt se manifest editado. |

**Out of scope v1:** key rotation, hardware tokens (YubiKey), per-field encryption.

---

## 8. Verify Mode

```bash
nox-mem import --verify archive.tar.gz
```

**Read-only. NÃO toca DB.** Roda:

1. **Tar integrity:** `tar -tzf` exit code 0.
2. **Manifest parse:** schema válido, version supported.
3. **Checksums:** sha256 de cada arquivo bate com manifest.
4. **Schema compat:** archive schema_version vs target — reporta migrations needed ou fail (downgrade).
5. **Referential integrity:** sample 1% das kg_relations — checa que source_entity_id + target_entity_id existem em kg_entities.jsonl.
6. **Decrypt test (se encrypted):** decripta manifest+header só, valida GCM tag — payload não decriptado.

**Output:**
```
✓ Tar integrity OK (sha256 archive: abc...)
✓ Manifest valid (format_version 1.0, schema v18)
✓ Checksums match (6/6 files)
✓ Schema compat: v18 → v19 (1 migration: v18_to_v19_add_pain_normalize)
✓ KG referential sample (124/124 relations valid)
✓ Encryption header valid (AES-256-GCM, scrypt KDF)
─────────────────────────────────────
Archive verified. Ready to import with --merge or --replace.
```

Failure: exit code não-zero + JSON detalhado em stderr.

---

## 9. Merge Semantics

`--merge` é o **default**. Política:

| Tabela | Dedup key | Conflict resolution |
|--------|-----------|---------------------|
| `chunks` | `content_hash` (SHA256 do conteúdo normalizado) | Skip (já existe) — log em telemetry. |
| `vec_chunks` | `chunk_id` (FK) | Skip se chunk_id já mapeado. |
| `kg_entities` | `canonical_name` + `type` | **Merge:** unifica timeline events + frontmatter (newer wins se conflict). Log warning. |
| `kg_relations` | `(source_id, predicate, target_id)` tuple | Skip se duplicate. |
| `ops_audit` | `id` (autoincr) | **Append always.** Re-id se collision (preserva append-only). |
| `search_telemetry` | timestamp + query_hash | Skip duplicates. |

### Dedup edge cases

- **Chunk com mesmo content_hash mas project diferente:** merge metadata (union de projects array). Não duplica row.
- **KG entity merge conflict (mesma canonical_name, frontmatter divergente):** Usar `updated_at` mais recente. Antigo vai pra timeline como event.

---

## 10. Replace Semantics

`--replace --force` é o **botão vermelho**.

1. Snapshot atômico pré-op via `withOpAudit()` (já existe em `src/lib/op-audit.ts`). Path: `/var/backups/nox-mem/pre-op/replace-<ts>-<pid>-<uuid>.db`.
2. **DROP TABLE** todas as tabelas user-data (chunks, vec_chunks, kg_*, ops_audit, search_telemetry).
3. Recreate schema do archive (schema.sql) — se diferente do target, migrate forward primeiro.
4. Bulk insert tudo.
5. VACUUM final.
6. `ops_audit` registra op completa: snapshot path + counts + duration.

**Hard requirement:** `--force` explícito. Sem `--force`, CLI aborta com:
```
ERROR: --replace é destrutivo (drop all tables). Use --force para confirmar.
       Snapshot será criado em /var/backups/nox-mem/pre-op/ antes da operação.
       Recovery: nox-mem restore <snapshot-path>
```

`NOX_ALLOW_NO_SNAPSHOT=1` permite skip snapshot em emergency (mesma regra do reindex — ver CLAUDE.md §6).

---

## 11. Sources Separation (`--exclude-embeddings`)

**Tradeoff:**

| Modo | Tamanho típico (63K chunks) | Re-import cost |
|------|----------------------------|----------------|
| Full (com embeddings) | ~1.5GB | Zero — embeddings prontos. |
| `--exclude-embeddings` | ~300MB (-80%) | Re-embed: ~2h Gemini API + ~$8 quota (63K × 2K tokens). |

**Quando usar `--exclude-embeddings`:**
- Backup periódico onde armazenamento custa.
- Migration cross-provider (Gemini → Cohere): embeddings antigos inúteis mesmo.
- Sharing archive entre pares (peer A não precisa de quota peer B).

**Quando NÃO usar:**
- Disaster recovery (precisa estar operacional ASAP).
- Air-gapped restore (sem internet pra re-embed).

**Default:** inclui embeddings. Conservador.

### Cross-provider re-embedding

Manifest registra `embedding_provider + embedding_model + embedding_dim`. Se import-target usa provider diferente:

```
WARNING: Archive embeddings: gemini/gemini-embedding-001/3072d
         Target config: cohere/embed-multilingual-v3/1024d
         Embeddings incompatíveis — usar --skip-embeddings + re-vectorize após import.
```

Não tenta conversão automática (out of scope v1 — embedding spaces não são transferíveis).

---

## 12. Telemetria

Toda op (export+import) emite evento em `ops_audit` + opcionalmente `search_telemetry`:

```json
{
  "op": "export",
  "started_at": "2026-05-17T22:14:08-03:00",
  "completed_at": "2026-05-17T22:15:42-03:00",
  "duration_ms": 94000,
  "archive_size_bytes": 1573429184,
  "chunks_count": 62836,
  "embeddings_count": 62820,
  "kg_entities_count": 402,
  "format": "tar.gz",
  "encrypted": true,
  "filters": { "project": "granix", "since": "2026-01-01" },
  "status": "success"
}
```

**HARD RULE: NUNCA logar conteúdo** (chunks.content, kg entity frontmatter). Apenas counts + metadata estatística. Se `NOX_SEARCH_LOG_TEXT=1` (já existe pra search), **NÃO se aplica a export/import** — controle separado `NOX_EXPORT_LOG_PATHS=1` log archive output paths (default: off).

---

## 13. Tests Plan

### Round-trip (golden path)

```bash
nox-mem export --out /tmp/r.tar.gz
nox-mem import /tmp/r.tar.gz --replace --force  # em DB clean
# Assert: chunks_count, kg counts, ops_audit counts bate
# Assert: eval golden set nDCG@10 dentro de ±0.001 do baseline
```

### Version mismatch

- v18 archive → v19 target: import OK, migration logada.
- v19 archive → v18 target: import FAIL com erro claro.
- v18 archive → v20 target: chain migration OK.

### Encryption round-trip

```bash
echo "test-password-16-chars-min" | nox-mem export --encrypt - --out /tmp/enc.tar.gz
strings /tmp/enc.tar.gz | grep -i "secret-content"  # MUST RETURN ZERO MATCHES
echo "test-password-16-chars-min" | nox-mem import /tmp/enc.tar.gz --decrypt - --merge
```

### Partial export

- `--project granix`: archive contém apenas chunks com metadata.project == granix.
- `--since 2026-05-01`: chunks com created_at >= 2026-05-01.
- Combo `--project X --since Y`: AND.

### Dry-run parity

```bash
nox-mem import archive.tar.gz --merge --dry-run > /tmp/preview.json
nox-mem import archive.tar.gz --merge > /tmp/applied.json
diff <(jq -S 'del(.duration_ms,.op_id)' /tmp/preview.json) \
     <(jq -S 'del(.duration_ms,.op_id)' /tmp/applied.json)
# Deve ser idêntico (exceto duration + op_id)
```

### Adversarial / fuzz

- Archive tampered (flip byte no meio do payload encriptado) → GCM tag fail → import abort.
- Archive truncated (cut last 1KB) → checksum mismatch → import abort.
- Manifest com counts mentidos (counts.chunks=999K mas chunks.jsonl tem 100) → import detecta mismatch após parse → abort.
- KG relation refs chunk não exportado → import warning + skip relation.

### Performance

- Export 63K chunks: target <120s (atual DB size 1.24GB).
- Import 63K chunks: target <180s.
- Verify-only: target <10s.

Test files em `tests/A2-export-import/`. Usar `node:test` (consistente com A3+A4 retention tests — ver `reference_a3_a4_invariants_canary`).

---

## 14. DoD (Definition of Done)

Spec considera implementação **DONE** quando:

1. **Round-trip preserva nDCG@10 dentro de ±0.001:** export → DB clean → import → rodar eval harness (R01a golden set) → delta nDCG@10 < 0.001 absoluto. *Pain-weighted hybrid memory with shadow discipline — yours by design* sobrevive viagem.
2. **Archive abre com tooling standard:** `tar -tzf archive.tar.gz` lista todos arquivos. `jq . manifest.json` parse OK. **Zero binários proprietários** (embeddings.bin é float32 packed — documentado, parseable em qualquer linguagem).
3. **Encrypted archive resiste a `strings` exfiltration:** `strings encrypted.tar.gz | grep -E '(content_hash|chunk_text|password|api_key)' | wc -l` retorna 0 matches relevantes (só manifest stat-strings + lixo binário).
4. **Forward migration roda automaticamente:** archive v18 importado em target v19 dispara migrations chain sem intervenção manual. Auditado em `ops_audit`.
5. **HTTP API streaming:** export endpoint stream `Transfer-Encoding: chunked` (validado com archive >500MB sem OOM no server). Import endpoint aceita stream sem buffer full.

---

## 15. NÃO-Fazemos (v1)

| Out of scope | Razão |
|--------------|-------|
| **Cloud destination integration** (S3/GCS/Dropbox built-in) | Usuário pipa `nox-mem export | aws s3 cp - s3://...`. Não vamos virar gestão de credenciais cloud. Lock-in zero. |
| **Continuous replication** (streaming export to remote) | Out of scope v1. Snapshot one-shot. Replicação contínua = projeto separado (B1? — pillar Backup/Sync). |
| **Cross-provider embedding conversion** | Gemini 3072d ↔ Cohere 1024d não é transformação linear válida. Export preserva provider; reimport com provider diferente exige re-vectorize. |
| **Selective export por chunk_id explícito** | Usuário pode fazer via `--project` + metadata tagging. `--chunk-ids file.txt` adia pra v2 se demanda real. |
| **Compression algorithm alternativo** (zstd, brotli) | gzip cobre 95% do caso. Adicionar zstd = +dependency + +complexity. v2 se needed. |
| **Key rotation / hardware tokens** | Password-based AES-256-GCM cobre threat model documentado. Hardware tokens pra v2 (pillar Sovereignty). |
| **Partial restore** (importar só algumas tabelas de archive completo) | `--exclude-*` flags no import resolvem 80% dos casos. Granularidade chunk-level pra v2. |

---

## 16. Riscos

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| **Partial export quebra referential integrity** (KG relation referencia chunk não exportado por `--since` cutoff) | 🟡 MEDIUM | Verify mode + import com warning automático. Drop relations com refs missing (log). Documentar em manifest.json (`integrity_warnings` array). |
| **Embedding format drift across sqlite-vec versions** | 🟡 MEDIUM | embeddings.bin é raw float32 (não sqlite-vec internal format). Sobrevive upgrades de sqlite-vec. Manifest registra `embedding_provider/model/dim` pra validação no import. |
| **Large archive size para DB grandes** (>5GB) | 🟠 HIGH | **Streaming obrigatório** — tanto export quanto import operam em stream (parse JSONL line-by-line, embeddings via seek+read fixed-size). Buffer máximo 64MB. Tested com DB de 5GB sintético. |
| **`--replace --force` apaga DB sem snapshot se disk full** | 🟠 HIGH | `withOpAudit()` snapshot FAIL → abort op (mesma regra de reindex). Override só com `NOX_ALLOW_NO_SNAPSHOT=1` consciente. |
| **Schema migration v18→v19 perde campos não-mapeados** | 🟡 MEDIUM | Migration tests no node:test obrigatórios pra cada step. Dry-run reporta campos que serão dropped. |
| **Password fraco em encrypted archive** | 🟢 LOW | scrypt N=2^17 + docs recomendando passphrase ≥16 chars. CLI emite warning se password <12 chars (não bloqueia). |
| **Archive encriptado corrompido sem recovery** | 🟠 HIGH | GCM tag detecta tamper mas não recupera. **Documentar:** sempre manter cópia raw (não encriptada) em local seguro pra DR — ou hash de manifest out-of-band (envio separado). |
| **HTTP import endpoint usado como DoS** (upload absurdo) | 🟢 LOW | Auth obrigatória + limite `NOX_IMPORT_MAX_SIZE` env (default: 10GB). Streaming evita OOM. |
| **Worker concorrente em insert paralelo causa race em vec_chunks** | 🟡 MEDIUM | Concurrency aplicado a JSONL parse + transform; insert via single writer transaction (better-sqlite3 single-thread anyway). Bench `--concurrency 4` vs 1 antes de default. |

---

## 17. BLOCKED.md — NÃO ATIVADO

Avaliado: sqlite-vec binary format é interno do extension, MAS extraímos embeddings via SELECT vec_chunks → float32 raw → `embeddings.bin`. **Não dependemos do binary format on-disk do sqlite-vec.** Portabilidade não bloqueada por esse fator.

Caso futuro upgrade do sqlite-vec mude API de extração (não format on-disk), implementaremos shim. Risco baixo — sqlite-vec API estável desde v0.1.

**Conclusão:** sem `BLOCKED.md`. Spec pode avançar pra implementação após approval do Toto.

---

## 18. Próximos passos (NÃO executar agora)

1. Toto aprova spec (ou pede revisões).
2. Registrar **D40** em `docs/DECISIONS.md`: "Archive format v1 = tar.gz + JSONL + embeddings.bin packed; manifest unencrypted permite inspect sem decrypt."
3. Sprint A2-impl: ~3-5 dias devs (export 1d + import 1d + encryption 0.5d + migrations 1d + tests 1.5d).
4. Shadow discipline N/A — A2 é ortogonal ao retrieval. Validation = round-trip nDCG@10 invariant (DoD §1).

---

*Spec gerada por planner agent (overnight automode 2026-05-17). Implementação pendente autorização explícita Toto.*
