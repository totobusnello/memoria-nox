# BACKUP RUNBOOK — nox-mem

> Versão: 1.0 — 2026-05-18
> Maintainer: ver `docs/HANDOFF.md`
> VPS path: `/root/.openclaw/workspace/tools/nox-mem/`

---

## TL;DR — Comandos mais usados

```bash
# Backup manual on-demand
nox-mem export --out /tmp/backup-$(date +%Y%m%d-%H%M%S).tgz

# Verificar último backup automático
ls -lt /var/backups/nox-mem/nightly/ | head -3

# Verificar integridade do DB atual
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "PRAGMA integrity_check;"

# Restore via safeRestore (NUNCA cp direto)
# Ver DISASTER-RECOVERY.md SCENARIO B para procedimento completo
```

---

## 1. O que é feito backup

### 1.1 Dados críticos

| Arquivo | Path na VPS | Criticidade | Motivo |
|---|---|---|---|
| DB principal | `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` | CRÍTICO | Contém chunks, embeddings, KG, ops_audit |
| .env de configuração | `/root/.openclaw/.env` | CRÍTICO | Chaves de API — backup SEPARADO e SEGURO |
| Source compilado | `/root/.openclaw/workspace/tools/nox-mem/dist/` | MÉDIO | Pode ser reconstruído via `npm run build` |

### 1.2 Dados não cobertos pelo backup de DB

| Dado | Localização | Observação |
|---|---|---|
| Logs do serviço | systemd journal | Rotação automática (7 dias journald default) |
| Cron scripts | `/root/.openclaw/workspace/scripts/` | Estão no Git — restaurar de main |
| Prompt templates | `/root/.openclaw/workspace/prompts/` | Estão no Git — restaurar de main |
| Source code | `/root/.openclaw/workspace/tools/nox-mem/src/` | No Git — restaurar de main |

### 1.3 O que o DB cobre

O arquivo `nox-mem.db` contém todas as tabelas:

- `chunks` + `chunks_fts` — corpus textual (62.9k+ registros)
- `vec_chunks` + `vec_chunk_map` — embeddings Float32 3072d (~99.97% coverage)
- `kg_entities` + `kg_relations` — grafo de conhecimento
- `ops_audit` — log append-only de operações destrutivas (CWE-693)
- `answer_telemetry` + `provider_telemetry` + `viewer_telemetry` — telemetria (Wave B+)
- `search_telemetry` — telemetria de buscas (Wave A0)

---

## 2. Cadência de Backups

| Tipo | Quando | Onde | Trigger |
|---|---|---|---|
| **WAL contínuo** | Sempre (SQLite nativo) | `nox-mem.db-wal` | Automático — SQLite WAL mode |
| **Pre-op snapshot** | Antes de cada op destrutiva | `/var/backups/nox-mem/pre-op/` | `withOpAudit()` automático em reindex/consolidate/compact/crystallize/kg-prune |
| **Nightly** | 02:00 BRT diariamente | `/var/backups/nox-mem/nightly/` | `backup-all.sh` via cron |
| **On-demand** | Quando necessário | Path escolhido pelo usuário | `nox-mem export --out <path>` |

### Verificar se cron de backup está ativo

```bash
crontab -l | grep backup
# Deve mostrar linha com 02:00 BRT (23:00 UTC) e backup-all.sh
```

### Verificar horário do último backup nightly

```bash
ls -lt /var/backups/nox-mem/nightly/ | head -3
# Arquivo mais recente deve ter timestamp próximo das 02:00 BRT (23:00 UTC)
```

---

## 3. Comandos de Backup — Copy-Paste Ready

### 3.1 Backup manual on-demand (A2 export)

```bash
# Pré-requisito: set env
set -a; source /root/.openclaw/.env; set +a
export NM=/root/.openclaw/workspace/tools/nox-mem

# Backup completo (pede passphrase interativo)
node ${NM}/dist/index.js export --out /tmp/backup-$(date +%Y%m%d-%H%M%S).tgz

# Backup completo via env (automação)
NOX_BACKUP_PASS=$(cat /root/.openclaw/passphrase) \
node ${NM}/dist/index.js export \
  --out /var/backups/nox-mem/manual-$(date +%Y%m%d-%H%M%S).tgz \
  --passphrase-env NOX_BACKUP_PASS

# Backup sem embeddings (~30x menor — útil para transferência rápida)
node ${NM}/dist/index.js export \
  --out /tmp/backup-no-vec-$(date +%Y%m%d-%H%M%S).tgz \
  --exclude-embeddings

# Backup parcial por período
node ${NM}/dist/index.js export \
  --out /tmp/backup-recente.tgz \
  --since 2026-05-01 \
  --until 2026-05-18
```

### 3.2 Backup manual via VACUUM INTO (mais rápido, sem criptografia)

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Snapshot direto — mais rápido que export, sem criptografia
SNAP=/var/backups/nox-mem/manual/snap-$(date +%Y%m%d-%H%M%S).db
sqlite3 ${NM}/nox-mem.db "VACUUM INTO '${SNAP}'"
chmod 0600 "${SNAP}"
echo "Snapshot criado: ${SNAP}"
ls -lh "${SNAP}"
```

### 3.3 Verificar archive antes de usar

```bash
BACKUP=/tmp/backup-20260518-120000.tgz

# Inspecionar manifest sem passphrase (open-toolchain — zero dep nox-mem)
tar -xzf ${BACKUP} manifest.json -O | jq '{counts, schema_version, created_at, encryption}'

# Listar todos os arquivos no archive
tar -tzf ${BACKUP}

# Verificar integridade completa (--verify, não escreve nada)
set -a; source /root/.openclaw/.env; set +a
node /root/.openclaw/workspace/tools/nox-mem/dist/index.js import ${BACKUP} --verify
# Deve retornar success: true

# Dry-run (preview do que seria importado, sem escrever)
node /root/.openclaw/workspace/tools/nox-mem/dist/index.js import ${BACKUP} --dry-run
```

### 3.4 Listar todos os backups

```bash
echo "=== Pre-op snapshots (7 dias) ==="
ls -lh /var/backups/nox-mem/pre-op/*.db 2>/dev/null | tail -10

echo "=== Nightly backups ==="
ls -lh /var/backups/nox-mem/nightly/ 2>/dev/null | head -10

echo "=== Uso total de disco ==="
du -sh /var/backups/nox-mem/
```

---

## 4. Política de Retenção

| Tipo | Retenção | Base |
|---|---|---|
| Pre-op snapshots (`withOpAudit`) | 7 dias | CLAUDE.md regra #6 |
| Nightly snapshots | 30 dias | Padrão operacional |
| Weekly snapshots (rotação de nightly) | 90 dias | Rotação automática |
| Monthly snapshots (rotação de weekly) | 1 ano | Rotação automática |

### Rotação de backups

A rotação dos backups nightly → weekly → monthly deve ser configurada via cron ou via script. Exemplo de script de rotação:

```bash
#!/bin/bash
# /root/.openclaw/workspace/scripts/rotate-backups.sh
# Executar via cron semanalmente (segunda-feira 03:00 BRT)

BACKUP_DIR=/var/backups/nox-mem

# Apagar pre-op com mais de 7 dias
find ${BACKUP_DIR}/pre-op/ -name "*.db" -mtime +7 -delete

# Promover nightly mais recente a weekly (domingo)
if [ "$(date +%u)" = "7" ]; then
  LATEST_NIGHTLY=$(ls -t ${BACKUP_DIR}/nightly/*.db 2>/dev/null | head -1)
  if [ -n "${LATEST_NIGHTLY}" ]; then
    mkdir -p ${BACKUP_DIR}/weekly
    cp "${LATEST_NIGHTLY}" "${BACKUP_DIR}/weekly/nox-mem-weekly-$(date +%Y-%m-%d).db"
    chmod 0600 "${BACKUP_DIR}/weekly/nox-mem-weekly-$(date +%Y-%m-%d).db"
  fi
fi

# Apagar nightly com mais de 30 dias
find ${BACKUP_DIR}/nightly/ -name "*.db" -mtime +30 -delete

# Apagar weekly com mais de 90 dias
find ${BACKUP_DIR}/weekly/ -name "*.db" -mtime +90 -delete

echo "Rotação concluída: $(date)"
```

---

## 5. Comandos de Restore

### 5.1 Restore via safeRestore (de snapshot SQLite)

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a

# Parar serviço antes de restore
systemctl stop nox-mem-api

# Restore (NUNCA usar cp diretamente)
SNAP=/var/backups/nox-mem/pre-op/<arquivo>.db

node -e "
  import('./dist/src/lib/op-audit.js').then(async (m) => {
    await m.safeRestore('${SNAP}');
    console.log('safeRestore: OK');
  }).catch(e => { console.error(e.message); process.exit(1); });
"

# Reiniciar e verificar
systemctl start nox-mem-api
sleep 3
curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, schemaVersion}'
```

### 5.2 Restore via nox-mem import (de archive .tgz)

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a

ARCHIVE=/path/to/backup.tgz

# Dry-run primeiro para confirmar contagens
node ${NM}/dist/index.js import ${ARCHIVE} --dry-run

# Se dry-run OK, executar restore
# --replace: wipe e reimportar (preserva ops_audit per CLAUDE.md #6)
node ${NM}/dist/index.js import ${ARCHIVE} --replace

# Verificar
curl -sf http://127.0.0.1:18802/api/health | jq '{total, embedded, sectionDistribution}'
```

### 5.3 O que a safeRestore faz (para referência)

`src/lib/op-audit.ts`:

1. Valida que `user_version` do snapshot bate com o DB atual
2. Para o write-ahead log fazendo checkpoint WAL no snapshot
3. Restaura o arquivo `.db` principal
4. Remove arquivos WAL/SHM órfãos do DB antigo (ordem importa — W2-4 fix 2026-04-26)

**Nunca use `cp snapshot.db nox-mem.db`** diretamente. Se o WAL estava ativo no momento do snapshot (ou se o DB destino tem WAL stale), o resultado é corrupção silenciosa.

---

## 6. Verificação de Integridade

### 6.1 Verificação rápida do DB ativo

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Integrity check (pode demorar ~30s em DBs grandes)
sqlite3 ${NM}/nox-mem.db "PRAGMA integrity_check;"
# Deve retornar: ok

# Quick check (mais rápido, menos thorough)
sqlite3 ${NM}/nox-mem.db "PRAGMA quick_check;"
# Deve retornar: ok
```

### 6.2 Hash do backup (verificação de integridade de arquivo)

```bash
BACKUP=/var/backups/nox-mem/nightly/nox-mem-2026-05-18-020000.db

# SHA256 do arquivo
sha256sum ${BACKUP}
# Guardar output para comparação futura

# Ou verificar via manifest do archive .tgz:
tar -xzf /path/to/backup.tgz manifest.json -O | jq .checksums
```

### 6.3 Drill mensal de restore (copy-pasteable)

```bash
#!/bin/bash
# Execute mensalmente para confirmar que backups restauram

DRILL_DIR=/tmp/nox-mem-drill-$(date +%Y%m%d-%H%M%S)
mkdir -p ${DRILL_DIR}

# Usar backup mais recente
LATEST=$(ls -t /var/backups/nox-mem/nightly/*.db 2>/dev/null | head -1)
if [ -z "${LATEST}" ]; then
  echo "ERRO: Nenhum backup nightly encontrado"
  exit 1
fi

echo "Testando backup: ${LATEST}"
cp "${LATEST}" "${DRILL_DIR}/drill.db"

# Verificações
echo -n "integrity_check: "
sqlite3 "${DRILL_DIR}/drill.db" "PRAGMA integrity_check;" 2>&1

echo -n "chunk count: "
sqlite3 "${DRILL_DIR}/drill.db" "SELECT COUNT(*) FROM chunks;" 2>&1

echo -n "user_version: "
sqlite3 "${DRILL_DIR}/drill.db" "PRAGMA user_version;" 2>&1

echo -n "kg_entities: "
sqlite3 "${DRILL_DIR}/drill.db" "SELECT COUNT(*) FROM kg_entities;" 2>&1

# Limpar
rm -rf ${DRILL_DIR}
echo "Drill concluído: $(date)"
```

---

## 7. F09 Off-site Backup — Gap Documentado

### Status: AUSENTE — decisão informada

O usuário rejeitou explicitamente a implementação de off-site backup (F09) em **duas ocasiões**. (Memória: `no-f09-offsite-backup` — "VPS Hostinger nativo basta".)

### Implicação

O estado atual é:
- **2 cópias** (live DB + nightly local snapshot)
- **1 media** (ambas no mesmo nó Hostinger)
- **0 off-site**

Isso viola a regra 3-2-1. Em caso de falha catastrófica do disco + nó (ex: datacenter destruído), não há recovery possível além do que o suporte Hostinger possa oferecer.

### Workaround manual recomendado

Download mensal do backup mais recente para drive local:

```bash
# Rodar em máquina LOCAL (não na VPS)
export VPS_HOST=root@<vps-ip>
export NM=/root/.openclaw/workspace/tools/nox-mem

LOCAL_DEST=~/Backups/nox-mem
mkdir -p ${LOCAL_DEST}

# Criar archive exportado antes de baixar (inclui criptografia)
ssh ${VPS_HOST} "
  set -a; source /root/.openclaw/.env; set +a
  BACKUP_NAME=nox-mem-offsite-$(date +%Y%m%d).tgz
  node ${NM}/dist/index.js export --out /tmp/\${BACKUP_NAME}
  echo \${BACKUP_NAME}
" | tail -1 | xargs -I{} scp ${VPS_HOST}:/tmp/{} ${LOCAL_DEST}/

echo "Backup off-site local salvo em: ${LOCAL_DEST}"
ls -lh ${LOCAL_DEST}
```

### Quando reconsiderar F09

Revisar esta decisão se:
- DB ultrapassar 10 GB (risco de perda aumenta com tamanho)
- Conteúdo tornar-se sensível o suficiente para exigir redundância off-site
- SLA formal for requerido por cliente ou parceiro
- Incidente de perda de dados ocorrer por falha no único nó

---

## 8. Segurança dos Backups

### Permissões esperadas

```bash
# Verificar permissões (ACL 0600 = somente root lê)
stat /var/backups/nox-mem/pre-op/*.db 2>/dev/null | grep -E "Uid|Access"
# Deve mostrar 0600 e owner root

# Verificar diretório
stat /var/backups/nox-mem/pre-op/ | grep -E "Uid|Access"
# Deve mostrar 0700 e owner root
```

### Proteção do .env

O arquivo `.env` contém chaves de API e é o ativo mais sensível. **Nunca incluir em backup automatizado junto com o DB.**

```bash
# NUNCA fazer isto (inclui .env em archive de DB):
tar czf backup.tgz nox-mem.db .env  # ERRADO

# .env deve ser guardado separadamente em password manager (Bitwarden, 1Password, etc.)
# Backup de .env para outro host NUNCA via Git ou arquivo não-criptografado
```

### Criptografia de archives A2

Os archives `.tgz` produzidos por `nox-mem export` são **criptografados por padrão** (AES-256-GCM + scrypt N=2^17). A passphrase **nunca** deve ser passada via argv — apenas via env ou prompt interativo.

```bash
# ERRADO (expõe passphrase em ps aux):
nox-mem export --passphrase=minhasenha --out backup.tgz

# CORRETO:
NOX_EXPORT_PASSPHRASE=minhasenha nox-mem export --out backup.tgz

# CORRETO (interativo):
nox-mem export --out backup.tgz
# (pede passphrase com echo off)
```

Guardar a passphrase em password manager. Archive sem passphrase é **write-off** — scrypt N=2^17 torna brute-force inviável.

---

## 9. Referências cruzadas

| Tópico | Documento |
|---|---|
| Recovery procedures (todos os scenarios) | `docs/ops/DISASTER-RECOVERY.md` |
| Formato do archive .tgz + encryption spec | `docs/EXPORT-IMPORT.md` |
| `withOpAudit()` + `safeRestore()` | `src/lib/op-audit.ts` |
| Monitoramento + alertas de disco | `docs/ops/MONITORING.md` |
| Deploy commands (staging → prod) | `docs/DEPLOY-WAVE-B.md` |
| Regras críticas operacionais | `CLAUDE.md §Regras críticas` |

---

*Preparado: 2026-05-18 | Wave H — Operational Readiness*
