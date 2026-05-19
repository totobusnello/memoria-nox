# Export / Import — Guia de uso, formato e recuperação

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."* (D45 tagline — D40 superseded.)
>
> A2 entrega o **único** mecanismo que torna a promessa de Autonomy verificável end-to-end: seu corpus inteiro empacotado em um único `.tgz` portátil, criptografado por padrão (D41 #2), abrível por qualquer toolchain Linux/macOS sem nox-mem instalado para inspeção do manifest.

Este documento cobre:

- Visão geral e modelo mental
- Especificação do formato (tar.gz layout + manifest schema)
- Justificativa da escolha de criptografia (AES-256-GCM + scrypt N=2^17)
- Threat model
- Uso via CLI, HTTP API e MCP tools
- Cenários de recuperação (passphrase perdida, archive corrompido, schema antigo)
- FAQ

---

## 1. Visão geral

O sistema de export/import existe para responder três perguntas operacionais:

1. **Backup** — "se a VPS sumir agora, o que vai pra próxima?"
2. **Migration** — "como movo memória entre máquinas (laptop ↔ VPS)?"
3. **Portability** — "como provo pro Toto que os dados são dele, não meus?"

A resposta é um único arquivo `.tgz` que:

- Pode ser inspecionado parcialmente sem passphrase (`tar -xzf x.tgz manifest.json`)
- É criptografado por padrão (D41 #2) — cifra AES-256-GCM com chave derivada via scrypt
- Detecta tampering byte-a-byte via GCM auth tag + manifest AAD
- Migra schema antigo automaticamente para a versão atual ao importar (forward-only)
- Preserva 100% das colunas v.29: `retention_days`, `pain`, `section`, `section_boost`
- Mantém `ops_audit` append-only mesmo em modo `--replace` (regra #6 do CLAUDE.md)

---

## 2. Formato do archive

### Layout `tar.gz`

```
nox-mem-export-2026-05-18.tgz
├── manifest.json                  ← SEMPRE plaintext (D41 #2)
├── schema.sql                     ← SEMPRE plaintext (CREATE TABLE)
├── chunks.jsonl[.enc]             ← criptografado por padrão
├── embeddings.bin[.enc]           ← binário (header NOXEMBED + Float32 LE)
├── embeddings.idx[.enc]           ← JSONL com offsets para seek O(1)
├── kg_entities.jsonl[.enc]
├── kg_relations.jsonl[.enc]
└── ops_audit.jsonl[.enc]
```

Sufixo `.enc` aparece quando o arquivo está criptografado. `--unencrypted` produz arquivos sem sufixo, ainda dentro do mesmo layout.

### Manifest v1

```jsonc
{
  "format_version": "1.0",
  "schema_version": 18,
  "created_at": "2026-05-18T12:34:56.789Z",
  "source_hostname": "nox-vps",
  "source_nox_mem_version": "v3.7",
  "embedding_provider": "gemini",
  "embedding_model": "gemini-embedding-001",
  "embedding_dim": 3072,
  "sqlite_vec_version": "0.1.6",
  "includes": ["chunks", "embeddings", "kg", "audit"],
  "filters": { "project": null, "since": null, "until": null },
  "counts": {
    "chunks": 62836,
    "embeddings": 62830,
    "kg_entities": 402,
    "kg_relations": 544,
    "ops_audit": 1283
  },
  "checksums": {
    "chunks.jsonl": "ab12...64hex",
    "embeddings.bin": "...",
    "embeddings.idx": "...",
    "kg_entities.jsonl": "...",
    "kg_relations.jsonl": "...",
    "ops_audit.jsonl": "...",
    "schema.sql": "..."
  },
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "kdf": "scrypt",
    "kdf_params": { "N": 131072, "r": 8, "p": 1 },
    "kdf_salt_b64": "...",
    "files": {
      "chunks.jsonl.enc": {
        "nonce_b64": "...",
        "tag_b64": "...",
        "ciphertext_sha256": "..."
      }
    },
    "aad_source": "sha256(manifest_pre_encryption_bytes)",
    "format_version": 1
  },
  "integrity_warnings": []
}
```

### Canonicalização do manifest

O manifest é serializado em **JSON canônico**: chaves ordenadas alfabeticamente, sem espaço extra, UTF-8. Isso é mandatório porque o manifest plaintext é o **AAD source** (Additional Authenticated Data) do AES-256-GCM. Qualquer drift de whitespace/key-order quebra a verificação de tag no importer.

Implementação: `staged-A2/edits/src/lib/archive/manifest.ts` — `canonicalize()` recursivo + `manifestAADHash()`.

---

## 3. Encryption — por que AES-256-GCM + scrypt

### Cipher: AES-256-GCM

| Critério | Razão |
|---|---|
| **AEAD nativo** | Authenticated Encryption with Associated Data — único modo do AES que detecta tampering via tag de 128 bits embutida. |
| **Suporte Node nativo** | `crypto.createCipheriv('aes-256-gcm', ...)` — zero dependência externa. |
| **256-bit key** | Resiste a ataques quânticos parciais (Grover reduz a 128 bits efetivos, ainda forte). |
| **Per-file nonce de 12 bytes** | Padrão GCM. Random por arquivo dentro do mesmo archive — nunca reuse com mesma key (catastrófico). |

### KDF: scrypt

```
N = 131072  (2^17)
r = 8
p = 1
salt = 16 bytes random per archive
output = 32 bytes (chave AES)
maxmem = 256 MB
```

| Critério | Razão |
|---|---|
| **Memory-hard** | scrypt força attacker a usar RAM tanto quanto CPU — bloqueia GPU/ASIC offline brute-force barato. |
| **N=2^17** | ~0.5-1s para derivar em laptop moderno — UX OK para o usuário, custo proibitivo para attacker. |
| **Node nativo** | `crypto.scryptSync` — zero dep. |
| **Salt único por archive** | Mesmo passphrase produz chaves diferentes em archives diferentes — invalida rainbow tables. |

### AAD chain

```
AAD = sha256(manifest_plaintext_bytes_with_encryption_block_zeroed)
```

O bloco de encryption metadata no manifest começa zerado (estado "disabled"), AAD é calculado, files são encriptados com esse AAD, depois o bloco é preenchido com nonce/tag/ciphertext_sha256 por arquivo. Ao decryptar, o importer **recalcula AAD do manifest recebido com encryption block zerado** — se o manifest foi tampered (mesmo um byte em `counts.chunks`), o AAD diverge e todos os files falham GCM auth.

Resultado: **manifest também é tamper-evident**, sem precisar criptografá-lo. Pode ser inspecionado sem passphrase, mas não pode ser modificado sem detecção.

### Passphrase input — NUNCA via argv

Hard rule (regra de ouro #1 do worker preamble):

```
✗ nox-mem export --passphrase=hunter2          # REJEITADO no parser
✗ nox-mem export --passphrase hunter2          # REJEITADO no parser
✓ NOX_EXPORT_PASSPHRASE=hunter2 nox-mem export # OK (env)
✓ nox-mem export --passphrase-env MY_PASS      # OK (lê env MY_PASS)
✓ nox-mem export                               # OK (prompt interativo, echo off)
```

Razão: `ps aux` lista argv de todo processo do sistema. Pass via argv = leak instantâneo. O parser do CLI (`parseExportArgs` em `src/cli/export.ts`) rejeita explicitamente `--passphrase` e `-p` com exit code 2.

---

## 4. Threat model

### O que o sistema protege

1. **Confidencialidade do conteúdo** — chunks, embeddings, KG, ops_audit ficam ilegíveis sem passphrase
2. **Integridade end-to-end** — qualquer byte modificado em qualquer arquivo é detectado (GCM tag) e qualquer byte modificado no manifest também (AAD chain)
3. **Forward-compat de schema** — arquivos antigos podem ser importados em DB novo após migração automática
4. **Passphrase não-vazável** — nunca em argv, nunca em logs, nunca em env de outro processo

### O que o sistema NÃO protege

1. **Roubo da passphrase em RAM** — se um attacker já tem RCE no host de export, ele lê a passphrase direto da memória. Não há defesa contra isso a nível de arquivo.
2. **Disclosure pelo manifest plaintext** — counts, hostname, schema version, embedding model são visíveis sem passphrase. Decisão de design (open-toolchain inspect), NÃO um bug.
3. **Side-channel scrypt timing** — `crypto.scryptSync` é constant-time-ish no Node, mas timing attacks em scrypt KDF não estão dentro do escopo de defesa (assumimos archive não-acessível a attacker durante derive).
4. **Compromise do host de import** — se a DB de destino já está comprometida, importar archive limpo não conserta nada.

### Adversary models

| Adversary | Capability | Mitigation |
|---|---|---|
| Eavesdropper em backup S3/disk | Lê archive em repouso | AES-256-GCM stops at confidentiality |
| Tampered backup | Modifica byte do archive ou manifest | GCM tag + AAD chain rejeitam |
| Offline brute-force passphrase | Tem archive + tempo + GPU | scrypt N=2^17 r=8 — custo R$ milhares por passphrase fraca |
| Wrong passphrase | Tenta passphrase errado | `BadPassphraseError` distinta de `TamperedArchiveError` |

---

## 5. CLI

### Export

```bash
# Padrão: prompt interativo para passphrase
nox-mem export --out /backup/nox.tgz

# Automação: passphrase via env
NOX_BACKUP_PASS=$(cat /root/.openclaw/passphrase) \
nox-mem export --out /backup/nox.tgz --passphrase-env NOX_BACKUP_PASS

# Filtros parciais
nox-mem export --out /tmp/recent.tgz \
  --project nox-mem \
  --since 2026-05-01 \
  --until 2026-05-15

# Opt-out de encryption (requer TTY ou NOX_EXPORT_UNENCRYPTED_ACK=1)
NOX_EXPORT_UNENCRYPTED_ACK=1 nox-mem export --unencrypted --out /tmp/plain.tgz

# Excluir embeddings (archive ~30x menor)
nox-mem export --out /tmp/no-vec.tgz --exclude-embeddings
```

**Exit codes:**
- `0` — sucesso
- `1` — erro de sistema (disk full, DB lock, falha de write)
- `2` — erro de usuário (flag inválida, prompt cancelado, env var ausente, --unencrypted sem ACK em non-TTY)

### Import

```bash
# Padrão: merge (skip duplicates) + interactive passphrase prompt
nox-mem import /backup/nox.tgz

# Replace: wipe target tables, mantém ops_audit (regra #6)
nox-mem import /backup/nox.tgz --replace

# Verify only: integrity check sem write
nox-mem import /backup/nox.tgz --verify

# Dry-run: preview JSON, sem write
nox-mem import /backup/nox.tgz --dry-run

# Automação: passphrase via env
NOX_RESTORE_PASS=hunter2 \
nox-mem import /backup/nox.tgz --passphrase-env NOX_RESTORE_PASS --merge
```

### Inspect sem passphrase (open-toolchain DoD #4)

```bash
# Listar entries
tar -tzf /backup/nox.tgz

# Extrair só o manifest pra revisão
tar -xzf /backup/nox.tgz manifest.json -O | jq .

# Validar contagens antes de importar
tar -xzf /backup/nox.tgz manifest.json -O | jq .counts
```

Funciona em qualquer Linux/macOS com `tar` + `gzip` + `jq` — zero dependência de nox-mem.

---

## 6. HTTP API

Disponível em `:18802/api/{export,import}` (porta canonical — regra #4 do CLAUDE.md).

### POST /api/export

Body JSON:

```json
{
  "unencrypted": false,
  "passphrase": "via-TLS-only",
  "project": "nox-mem",
  "since": "2026-05-01T00:00:00Z",
  "until": "2026-05-18T00:00:00Z",
  "exclude_embeddings": false
}
```

Response:

```
HTTP/1.1 200 OK
Content-Type: application/gzip
Content-Disposition: attachment; filename="nox-mem-export-2026-05-18.tgz"
Content-Length: 1234567
X-Archive-Encrypted: true
X-Archive-Chunks: 62836
X-Archive-Duration-Ms: 4321

<gzip bytes>
```

Erros: `400` (bad body), `413` (archive > maxBytes), `499` (cancelled), `500` (system).

### POST /api/import

Body JSON com archive em base64:

```json
{
  "archive_b64": "H4sI...base64...",
  "passphrase": "via-TLS-only",
  "mode": "merge",
  "dry_run": false,
  "verify_only": false
}
```

Response:

```json
{
  "mode": "merge",
  "dry_run": false,
  "verify_only": false,
  "encrypted": true,
  "schema_version_archive": 18,
  "schema_version_target": 19,
  "stats": {
    "chunks": { "inserted": 5000, "skipped": 12, "merged": 0, "warnings": [] },
    "kg_entities": { "inserted": 40, "skipped": 0, "merged": 360, "warnings": [] },
    "kg_relations": { "inserted": 80, "skipped": 4, "merged": 0, "warnings": ["Relation 91 skipped: FK endpoint missing (src=99, tgt=42)"] },
    "ops_audit": { "inserted": 1283, "skipped": 0, "merged": 0, "warnings": [] },
    "embeddings": { "embedded": 5000, "skipped": 0 }
  },
  "duration_ms": 12345
}
```

Erros: `400` (bad body), `401` (passphrase missing/wrong), `409` (tampered), `499` (cancelled), `500` (system).

---

## 7. MCP tools (`archive_export`, `archive_import`)

Schema completo em `src/mcp/tools/archive.ts`. Cliente MCP pode invocar:

```jsonc
// archive_export
{
  "tool": "archive_export",
  "args": {
    "passphrase_env": "NOX_EXPORT_PASSPHRASE",  // server-side env var name
    "project": "nox-mem",
    "exclude_embeddings": true
  }
}
// → returns { success: true, archive_b64, bytes, encrypted, manifest: { counts, ... }, duration_ms }

// archive_import
{
  "tool": "archive_import",
  "args": {
    "archive_b64": "<base64>",
    "passphrase_env": "NOX_RESTORE_PASSPHRASE",
    "mode": "merge",
    "verify_only": true
  }
}
// → returns { success: true, encrypted, applied, stats, duration_ms }
```

Total MCP tools agora: **18** (16 originais + `archive_export` + `archive_import`).

---

## 8. Recovery scenarios

### Cenário 1 — Passphrase perdida

**Sintoma:** `nox-mem import x.tgz` falha com `BadPassphraseError`.

**Diagnóstico:** Manifest plaintext confirma `encryption.enabled: true`. Não há recuperação possível — scrypt N=2^17 é desenhado para ser inviável de brute-force.

**Ação:** Se você tem backup pré-encryption (período de transição) ou outro archive com outra passphrase do mesmo período, use esse. Caso contrário, archive é write-off. **Sempre escreva a passphrase em password manager separado.**

### Cenário 2 — Archive corrompido

**Sintoma:** `nox-mem import x.tgz` falha com `TamperedArchiveError` ou `Plaintext checksum mismatch`.

**Diagnóstico:** 
```bash
tar -tzf x.tgz                                # listar entries — falha se tar quebrado
tar -xzf x.tgz manifest.json -O | jq .        # manifest legível?
```

**Ações em ordem:**
1. Tente outro backup do mesmo dia (rotação)
2. Se a corruption é só em `embeddings.bin.enc`, importe `--exclude-embeddings` na origem e re-vetorize na destino
3. Se manifest está OK mas `chunks.jsonl.enc` quebrou, o archive é write-off — KG/ops_audit/chunks são interdependentes

### Cenário 3 — Schema mismatch

**Sintoma:** `nox-mem import x.tgz` falha com `Archive schema version 19 is newer than current nox-mem schema version 18. Upgrade nox-mem before importing.`

**Ação:** 
```bash
npm install -g openclaw-nox-mem@latest
nox-mem migrate                  # roda PRAGMA user_version migrations no DB local
nox-mem import x.tgz             # retry
```

**Inverso (archive antigo, DB novo):** automatic forward migration. Manifest reporta `schema_version_archive: 18`, importer roda chain `v18 → v19 → v(current)` e aplica. Em failure mid-chain, transaction rolla back inteira e DB fica intacto.

### Cenário 4 — Out of disk durante export

**Sintoma:** `nox-mem export` falha em ENOSPC.

**Ação:** Estime tamanho via `du -sh /var/lib/nox-mem/`. Archive comprimido fica tipicamente 30-50% do tamanho do DB original (texto comprime bem, embeddings já são float32 sem redundância). Limpe espaço, retry com `--exclude-embeddings` se necessário.

### Cenário 5 — Importação parcial precisa rollback

**Sintoma:** Import rodou, mas você descobriu que era o archive errado.

**Ação:**
```bash
ls /var/backups/nox-mem/pre-op/  # snapshot do withOpAudit antes do import
nox-mem restore <snapshot-path>   # regra #6 do CLAUDE.md
```

Snapshot é criado automaticamente porque `runImport` é wrapped em `withOpAudit('import', ...)` na produção. Em staged-A2, o wrapper é injeção do caller — produção wira em CLI.

---

## 9. FAQ

**Q: Por que não criptografar o manifest também?**
R: Counts e versão precisam ser inspecionáveis sem passphrase para triagem operacional (qual archive importar quando há 30 backups acumulados). Tamper detection via AAD chain dá o melhor dos dois mundos: legível mas não modificável.

**Q: Posso usar zstd em vez de gzip?**
R: V1 = gzip only (open-toolchain rule: tar -xzf precisa funcionar zero-dep). Open question na spec — pode virar `--compression zstd` em v2.

**Q: Embeddings ficam encriptados?**
R: Sim. `embeddings.bin.enc` cobre o blob inteiro (header magic + Float32 LE concatenado). Sem passphrase, é binary noise.

**Q: Por que scrypt e não argon2id?**
R: argon2 não tem suporte nativo no Node sem nan/node-gyp. scrypt é built-in e suficientemente memory-hard com N=2^17. Pode subir pra argon2 em v2 com bump de `encryption.format_version`.

**Q: O que acontece se eu rodar `nox-mem export` duas vezes em sequência?**
R: Cada export tem salt + nonces aleatórios — os archives serão byte-different mesmo com mesma passphrase e mesmo corpus. Determinismo intencionalmente evitado (anti-fingerprint).

**Q: `ops_audit` é apagado em `--replace`?**
R: **Não.** Regra #6 do CLAUDE.md: ops_audit é append-only via trigger CWE-693. Mesmo em `--replace`, a tabela é preservada e linhas incoming são anexadas (com re-ID em caso de colisão).

**Q: Posso importar archive em DB diferente do original?**
R: Sim. Esse é o uso primário pra migration laptop ↔ VPS. Schema version precisa ser compatível (forward auto-migrate; backward fail clean).

**Q: Como faço dual-write (encrypted + unencrypted) para teste?**
R: Não suportado nativamente. Rode 2x: `nox-mem export --out a.tgz` + `nox-mem export --unencrypted --out b.tgz`. Confirma byte-identity dos chunks via `tar -xzf b.tgz chunks.jsonl -O | sha256sum`.

**Q: Round-trip preserva ranking de search hybrid?**
R: Sim — preserva 100% das colunas v.29 (`retention_days`, `pain`, `section`, `section_boost`, embeddings byte-identical). Memory feedback `feedback_buffer_pool_aliasing_in_typed_arrays` evitado via `Uint8Array` intermediate em `parseEmbeddings`.

---

## 10. Referências

- **Spec original:** `specs/2026-05-17-A2-export-import.md` (PR #9)
- **Kickoff:** `specs/2026-05-18-A2-implementation-kickoff.md` (T1-T18)
- **D40:** Q/A/P pivot + tagline (Autonomy pillar)
- **D41:** `docs/DECISIONS.md` — encryption opt-out lock + A2 parallel com P1
- **Memória feedback aplicada:**
  - `feedback_buffer_pool_aliasing_in_typed_arrays` (T4 serializer)
  - `feedback_kg_relations_uses_fk_ids_not_inline_strings` (T5 serializer)
  - Regra de ouro: passphrase nunca via argv

---

*Doc autorado durante sprint Wave B T10-T18 (2026-05-18). Última verificação: 129 testes passando staged-A2 (68 originais + 61 novos T10-T14).*
