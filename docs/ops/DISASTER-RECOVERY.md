# DISASTER RECOVERY — nox-mem

> Versão: 1.0 — 2026-05-18
> Maintainer: ver `docs/HANDOFF.md`
> Stack: TypeScript · better-sqlite3 · FTS5 · sqlite-vec · Gemini 3072d
> VPS path: `/root/.openclaw/workspace/tools/nox-mem/`

---

## TL;DR — O que fazer agora

| Situação | Seção | Duração estimada |
|---|---|---|
| VPS morreu / DC fora | [SCENARIO A](#scenario-a-vps-morreu) | 2-3h |
| DB corrompido | [SCENARIO B](#scenario-b-db-corrompido) | 30min |
| Migration travou no meio | [SCENARIO C](#scenario-c-migration-crashed-mid-run) | 1h |
| Chave de API comprometida | [SCENARIO D](#scenario-d-provider-key-comprometida) | 15min |
| Shell da VPS invadida | [SCENARIO E](#scenario-e-shell-comprometida) | 4-8h |
| Op destrutiva acidental | [SCENARIO F](#scenario-f-operação-destrutiva-acidental) | 30min-2h |

---

## 1. Threat Model

O que pode dar errado com o nox-mem em produção. Listado por probabilidade × impacto.

### 1.1 VPS morre / disco falha / DC fora

**Probabilidade:** baixa. **Impacto:** máximo — perda total se não houver backup.

Causas: falha de hardware do nó Hostinger, migração forçada de DC, disco SSD queimado, fatura não paga.

**Janela de exposição atual:** até 24h (backup nightly 02:00 BRT). Todo chunk ingestado depois do último `backup-all.sh` e antes da falha está em risco.

### 1.2 Corrupção do arquivo SQLite

**Probabilidade:** baixa mas não nula. **Impacto:** alto — DB ilegível sem recovery.

Causas documentadas:
- `sed -i` aplicado em arquivo `.db` (CLAUDE.md regra #7 — causou incident 2026-05-01; corrompeu `nox-mem.db` + `graph-memory.db` + 8 backups)
- Kill -9 durante write (WAL não flushed)
- Disco cheio durante VACUUM INTO snapshot (página escrita parcialmente)

**Prevenção:** WAL mode (default) garante journal em arquivo separado. Qualquer write abortado é replayável do WAL.

### 1.3 Schema migration travada no meio

**Probabilidade:** média (cada deploy de migração é uma janela de risco). **Impacto:** médio — DB fica em versão inconsistente se migration não for atômica.

Causas: SSH drop durante `sqlite3 db < migration.sql`, disk full no meio de `ALTER TABLE`, processo killed.

**Mitigação atual:** migrations v11/v20 usam `CREATE TABLE IF NOT EXISTS` (idempotente). v19 usa `ALTER TABLE ADD COLUMN` (NÃO idempotente — ver SCENARIO C).

### 1.4 Provider lockout (Gemini quota / chave revogada)

**Probabilidade:** média (quota 3M/d estoura se não usar flash-lite). **Impacto:** médio — search funciona (FTS5 puro), mas vetorização e KG extraction param.

Causas:
- Chave revogada por vazamento (hardcoded em commit, `ps aux` leak)
- Quota diária `gemini-2.5-flash` estoura (CLAUDE.md regra #3 — usar flash-lite)
- Rotação de chave sem restart de serviço

**Sinais:** `"Done: 0 embedded, N errors"` no CLI sem set de `.env` (CLAUDE.md regra #1). `curl /api/health` mostra `vectorCoverage.embedded < total`.

### 1.5 Comprometimento de shell

**Probabilidade:** baixa. **Impacto:** catastrófico — exfiltração de dados + chaves.

Causas: CVE no OpenClaw gateway, senha SSH fraca, token Git exposto, supply chain.

Sinais: processos inesperados, `authorized_keys` modificado, uploads anômalos no `iftop`.

### 1.6 Operação destrutiva acidental

**Probabilidade:** média-alta (ocorreu 2026-04-25). **Impacto:** médio-alto — perda de `section`/`retention` em 183 entity chunks.

Causas documentadas:
- Cron 22:00 BRT rodava `nox-mem reindex` sem `--dry-run` (patched 2026-04-25)
- `rm -rf` em path errado
- `sed -i` em `.db` (ver 1.2)
- Rollback manual com `cp snapshot.db nox-mem.db` (corrompe se WAL stale — NUNCA fazer isso)

**Proteção atual:** `withOpAudit()` cria snapshot atômico antes de qualquer op destrutiva em `/var/backups/nox-mem/pre-op/`.

### 1.7 Bit-flip silencioso (corrupção cósmica)

**Probabilidade:** muito baixa. **Impacto:** difícil de detectar — dado errado sem erro visível.

SQLite tem `PRAGMA integrity_check` para detectar. Embeddings Float32 corrompidos produzem resultados de search piores mas não erros explícitos.

**Prevenção:** integrity_check periódico (ver seção 7 — drills).

---

## 2. Recovery Objectives

| Métrica | Objetivo | Justificativa |
|---|---|---|
| **RTO** (Recovery Time Objective) | 4 horas | Tempo máximo aceitável de indisponibilidade para restaurar serviço funcional |
| **RPO** (Recovery Point Objective) | 24 horas | Janela máxima de perda de dados — alinhado com backup nightly 02:00 BRT |

### Criticidade dos dados

| Componente | Criticidade | Backup coverage |
|---|---|---|
| `chunks` (62.9k+) | CRÍTICO | nightly + pre-op |
| `vec_chunks` (embeddings) | CRÍTICO | nightly + export A2 |
| `kg_entities` (~402) + `kg_relations` (~544) | CRÍTICO | nightly + pre-op |
| `ops_audit` | ALTO | nightly (append-only) |
| `answer_telemetry` / `provider_telemetry` | MÉDIO | nightly |
| `viewer_telemetry` | BAIXO | nightly (nice-to-have) |

### Gap conhecido: off-site backup

**O usuário rejeitou explicitamente F09 (off-site backup) em duas ocasiões.** (Memória: `no-f09-offsite-backup` — "VPS Hostinger nativo basta".)

Estado atual: apenas `live DB` + `nightly local snapshot` = **2 cópias, 1 media, 0 off-site**.

**Isso viola a regra 3-2-1.** Em caso de falha catastrófica do nó Hostinger (disco + backup no mesmo nó), o RPO é ilimitado. Este risco está documentado e é uma decisão informada.

Workaround recomendado: download manual mensal do backup mais recente para drive local (ver `docs/ops/BACKUP-RUNBOOK.md §7`).

---

## 3. Backup Strategy

### 3-2-1 rule — estado atual

| Regra | Ideal | Estado atual |
|---|---|---|
| 3 cópias | live + backup-local + off-site | live + backup-local (**gap off-site**) |
| 2 media | SQLite file + .tgz | SQLite `VACUUM INTO` snapshot + .tgz via A2 export |
| 1 off-site | externo / S3-compatible | **AUSENTE** — user decision |

### Localização dos backups

```
/var/backups/nox-mem/
├── pre-op/                   ← snapshots withOpAudit (retention 7 dias, ACL 0600)
│   ├── reindex_<ts>_<pid>_<uuid>.db
│   ├── migrate_v11_<ts>.db
│   └── ...
├── nightly/                  ← backup-all.sh 02:00 BRT (retention 30 dias)
│   ├── nox-mem-2026-05-18-020000.db
│   └── ...
└── weekly/                   ← rotação de nightly (retention 90 dias)
    └── nox-mem-2026-05-11.db
```

### Verificar última execução do backup

```bash
ls -lt /var/backups/nox-mem/nightly/ | head -5
# O arquivo mais recente deve ter timestamp próximo de 02:00 BRT do dia atual
```

---

## 4. Recovery Procedures

> **Regra antes de qualquer recovery:** query o estado real. Não confie em logs. Não confie em diagnóstico de sub-agentes.
> (Memória: `audit-must-check-prod-state-not-only-code`)

---

### SCENARIO A: VPS Morreu

**Sintomas:** SSH timeout em todos os attempts. Painel Hostinger mostra VM em estado de erro. Sem acesso ao nó.

**Pré-requisito:** você tem um backup (nightly snapshot ou .tgz exportado). Se não tem — contacte suporte Hostinger primeiro (podem ter snapshot interno).

#### Passo 1 — Provisionar nova VPS (15-30min)

```bash
# No painel Hostinger:
# 1. Criar nova VPS Ubuntu 22.04 LTS na mesma região
# 2. Configurar SSH key (use chave NOVA se suspeitar comprometimento — ver SCENARIO E)
# 3. Anotar novo IP

export NEW_VPS=root@<novo-ip>
export NM=/root/.openclaw/workspace/tools/nox-mem

# Verificar acesso
ssh $NEW_VPS "echo ok"
```

#### Passo 2 — Instalar dependências (20-30min)

```bash
ssh $NEW_VPS "bash -s" << 'EOF'
set -euo pipefail

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs sqlite3 inotify-tools

# Verificar versões
node --version   # deve ser >= 20.x
sqlite3 --version

# Criar estrutura de diretórios
mkdir -p /root/.openclaw/workspace/tools/
mkdir -p /var/backups/nox-mem/pre-op
chmod 700 /var/backups/nox-mem/pre-op
mkdir -p /var/backups/nox-mem/nightly

echo "Dependencies OK"
EOF
```

#### Passo 3 — Restaurar .env (5min)

```bash
# O .env contém todas as chaves de API — armazene em password manager
# NUNCA commitar em Git (CLAUDE.md hard rule)

# Opção A: você tem cópia local do .env
scp /path/to/local-backup/.env $NEW_VPS:/root/.openclaw/.env
chmod 600 /root/.openclaw/.env (rodar no novo VPS)

# Opção B: reconstruir do zero
ssh $NEW_VPS "cat > /root/.openclaw/.env << 'ENVEOF'
GEMINI_API_KEY=<sua-chave>
NOX_API_PORT=18802
NOX_SALIENCE_MODE=shadow
# ... demais vars conforme DEPLOY-WAVE-B.md §10
ENVEOF
chmod 600 /root/.openclaw/.env"
```

#### Passo 4 — Restaurar código nox-mem (10min)

```bash
# Clonar repo no novo VPS
ssh $NEW_VPS "
  git clone https://github.com/totobusnello/memoria-nox.git \
    /root/.openclaw/workspace/tools/nox-mem
  cd /root/.openclaw/workspace/tools/nox-mem
  npm ci
  npm run build
  echo 'Build OK'
"
```

#### Passo 5 — Restaurar DB do backup (15-30min)

**Opção A: de snapshot SQLite local**

```bash
# Copiar snapshot para novo VPS
scp /path/to/local-backup/nox-mem-<date>.db $NEW_VPS:/tmp/restore.db

# Verificar integridade antes de restaurar
ssh $NEW_VPS "sqlite3 /tmp/restore.db 'PRAGMA integrity_check;'"
# Deve retornar: ok

# Restaurar (NUNCA usar cp direto se o arquivo era WAL-mode ativo — usar safeRestore)
ssh $NEW_VPS "
  set -a; source /root/.openclaw/.env; set +a
  cd /root/.openclaw/workspace/tools/nox-mem
  node -e \"
    import('./dist/src/lib/op-audit.js').then(async (m) => {
      await m.safeRestore('/tmp/restore.db');
      console.log('safeRestore: OK');
    }).catch(e => { console.error(e); process.exit(1); });
  \"
"
```

**Opção B: de archive .tgz (A2 export)**

```bash
# Copiar archive para novo VPS
scp /path/to/backup.tgz $NEW_VPS:/tmp/restore.tgz

# Verificar manifest sem passphrase primeiro
ssh $NEW_VPS "tar -xzf /tmp/restore.tgz manifest.json -O | jq .counts"

# Importar (interactive passphrase prompt)
ssh $NEW_VPS "
  set -a; source /root/.openclaw/.env; set +a
  cd /root/.openclaw/workspace/tools/nox-mem
  node dist/index.js import /tmp/restore.tgz --dry-run
"
# Revisar saída do dry-run. Se OK:
ssh $NEW_VPS "
  set -a; source /root/.openclaw/.env; set +a
  cd /root/.openclaw/workspace/tools/nox-mem
  node dist/index.js import /tmp/restore.tgz
"
```

#### Passo 6 — Configurar e iniciar serviço (10min)

```bash
# Instalar systemd unit (ver DEPLOY-WAVE-B.md para o arquivo .service)
ssh $NEW_VPS "systemctl enable nox-mem-api && systemctl start nox-mem-api"
ssh $NEW_VPS "systemctl is-active nox-mem-api"
# Deve retornar: active

# Health check
ssh $NEW_VPS "curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, schemaVersion}'"
# Deve retornar status: "ok"
```

#### Passo 7 — Verificação pós-restore

Ver [seção 5 — Recovery Verification](#5-recovery-verification).

**Duração esperada:** 2-3 horas (maior parte em instalação de deps + copy de dados).

---

### SCENARIO B: DB Corrompido

**Sintomas:** `nox-mem search` retorna erro de I/O, `curl /api/health` retorna 500, `sqlite3 nox-mem.db "SELECT 1"` falha.

**Diagnóstico primeiro:**

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Testar legibilidade básica
sqlite3 ${NM}/nox-mem.db "PRAGMA integrity_check;" 2>&1 | head -20
# Se retornar "ok" -> não está corrompido (procure outra causa)
# Se retornar erros de page -> corrompido, proceder

# Verificar journal mode
sqlite3 ${NM}/nox-mem.db "PRAGMA journal_mode;"
# WAL = modo esperado

# Checar WAL stale
ls -lh ${NM}/nox-mem.db-wal ${NM}/nox-mem.db-shm 2>/dev/null
# Se arquivos -wal/-shm existem e db está corrompido: WAL não foi flushed no crash
```

#### Opção 1: Restaurar via withOpAudit snapshot (preferida)

```bash
# Listar snapshots disponíveis (do mais recente ao mais antigo)
ls -lt /var/backups/nox-mem/pre-op/*.db 2>/dev/null | head -10

# Verificar integridade do snapshot antes de restaurar
SNAP=/var/backups/nox-mem/pre-op/<arquivo>.db
sqlite3 ${SNAP} "PRAGMA integrity_check;"
# Deve retornar: ok

# Restaurar via safeRestore (NUNCA cp direto — corrompe se WAL stale)
set -a; source /root/.openclaw/.env; set +a
cd ${NM}
node -e "
  import('./dist/src/lib/op-audit.js').then(async (m) => {
    await m.safeRestore('${SNAP}');
    console.log('safeRestore: OK');
  }).catch(e => { console.error(e.message); process.exit(1); });
"

# Reiniciar serviço
systemctl restart nox-mem-api
sleep 3
curl -sf http://127.0.0.1:18802/api/health | jq .status
```

`safeRestore()` faz em ordem (W2-4 fix 2026-04-26): valida `user_version` match → restaura main DB → remove WAL/SHM órfãos. A ordem importa — nunca remover WAL antes de restaurar o DB principal.

#### Opção 2: Restaurar via nightly backup

```bash
# Se não há snapshot pré-op ou todos estão corrompidos:
ls -lt /var/backups/nox-mem/nightly/ | head -5

NIGHTLY=/var/backups/nox-mem/nightly/nox-mem-<data>.db
sqlite3 ${NIGHTLY} "PRAGMA integrity_check;"

set -a; source /root/.openclaw/.env; set +a
cd ${NM}
node -e "
  import('./dist/src/lib/op-audit.js').then(async (m) => {
    await m.safeRestore('${NIGHTLY}');
    console.log('safeRestore: OK');
  });
"
systemctl restart nox-mem-api
```

#### O que NÃO fazer

```bash
# NUNCA isto — corrompe DB se WAL stale:
cp /var/backups/nox-mem/pre-op/snapshot.db ${NM}/nox-mem.db

# NUNCA isto:
sed -i 's/corrupt/fix/' ${NM}/nox-mem.db  # sed em .db destrói page boundaries
```

**Duração esperada:** 30 minutos.

---

### SCENARIO C: Migration Crashed Mid-Run

**Sintomas:** `PRAGMA user_version` retorna valor inesperado (ex: 10 após tentativa de v11, ou schema com colunas incompletas). Serviço retorna 500 em endpoints que dependem das novas tabelas.

**Diagnóstico:**

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Checar user_version atual
sqlite3 ${NM}/nox-mem.db "PRAGMA user_version;"

# Checar quais tabelas existem
sqlite3 ${NM}/nox-mem.db ".tables"

# Checar integridade
sqlite3 ${NM}/nox-mem.db "PRAGMA integrity_check;"

# Checar journal mode (garante que WAL está funcionando)
sqlite3 ${NM}/nox-mem.db "PRAGMA journal_mode;"
```

#### Caso 1: user_version = 10, migration v11 travou

v11 usa `CREATE TABLE IF NOT EXISTS` — é **idempotente**. Pode retentar diretamente:

```bash
# Verificar se snapshot pré-v11 existe
ls /var/backups/nox-mem/pre-op/migrate_v11*.db 2>/dev/null

# Antes de retentar, garantir que service está parado (evita lock contention)
systemctl stop nox-mem-api

# Retentar migration v11
sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11.sql

# Verificar
sqlite3 ${NM}/nox-mem.db "PRAGMA user_version;"
# Deve retornar: 11

# Rodar testes de validação
sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v11-tests.sql
# Todo output deve começar com PASS:

systemctl start nox-mem-api
```

#### Caso 2: user_version = 11, migration v19 travou no meio

v19 usa `ALTER TABLE ADD COLUMN` — **NÃO é idempotente**. Tentativa de re-run vai falhar com `duplicate column name`.

```bash
# Checar quais colunas de v19 já foram adicionadas
sqlite3 ${NM}/nox-mem.db "PRAGMA table_info(chunks);" | grep -E "confidence|provenance_kind"
sqlite3 ${NM}/nox-mem.db "PRAGMA table_info(kg_relations);" | grep -E "valid_from|valid_to|superseded"

# Opção A: Se NENHUMA coluna de v19 foi adicionada — DB intacto em v11
# Restaurar não é necessário. Retentar com snapshot pré-v19:
SNAP=/var/backups/nox-mem/pre-op/migrate_v19*.db
# (se existe e está integro, é mais seguro)

# Opção B: Se ALGUMAS colunas foram adicionadas (estado parcial)
# NÃO retentar v19.sql direto — vai falhar nas colunas já existentes
# Melhor path: aplicar rollback via snapshot

set -a; source /root/.openclaw/.env; set +a
SNAP=$(ls -t /var/backups/nox-mem/pre-op/migrate_v19*.db 2>/dev/null | head -1)
if [ -n "${SNAP}" ]; then
  node -e "
    import('./dist/src/lib/op-audit.js').then(async (m) => {
      await m.safeRestore('${SNAP}');
      console.log('Rollback to pre-v19 snapshot: OK');
    });
  "
else
  echo "WARN: sem snapshot pre-v19. Usar nightly backup."
fi

# Após restaurar: retentar v19 do zero
systemctl stop nox-mem-api
sqlite3 ${NM}/nox-mem.db "PRAGMA user_version;"  # deve ser 11
sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19.sql
sqlite3 ${NM}/nox-mem.db "PRAGMA user_version;"  # deve ser 19
sqlite3 ${NM}/nox-mem.db < ${NM}/staged-migrations/v19-tests.sql
systemctl start nox-mem-api
```

#### Caso 3: estado completamente inconsistente

Se integrity_check retorna erros E user_version é inesperado — tratar como [SCENARIO B](#scenario-b-db-corrompido).

**Duração esperada:** 1 hora incluindo diagnóstico + restore + retentar migration.

---

### SCENARIO D: Provider Key Comprometida

**Sintomas:** Gemini retorna 401/403. Rotação preventiva por vazamento detectado.

**Diagnóstico:**

```bash
# Testar chave atual via HTTP direto (não via nox-mem)
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
  | jq '.error.code // "OK"'
# 401 = chave inválida/revogada
# 429 = quota (não comprometida, só limitada)
# OK = chave válida

# Checar se vectorCoverage está degradado
curl -sf http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

#### Procedimento de rotação

```bash
# 1. Gerar nova chave no Google AI Studio / console.cloud.google.com
# 2. Testar nova chave antes de remover a antiga:
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=<NOVA_CHAVE>" \
  | jq '.models | length'
# Deve retornar > 0

# 3. Atualizar .env via editor (NUNCA via openclaw config set para Gemini)
#    IMPORTANTE: não usar openclaw models auth login — wipa registry (memória: openclaw-models-auth-login)
nano /root/.openclaw/.env
# Alterar: GEMINI_API_KEY=<nova-chave>

# 4. Recarregar .env e reiniciar serviços
set -a; source /root/.openclaw/.env; set +a
systemctl restart nox-mem-api
sleep 3

# 5. Smoke test
curl -sf http://127.0.0.1:18802/api/answer \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}' | jq '{model: .metadata.model, error: .error}'
# model deve ser "gemini-2.5-flash-lite" (D41 #1 locked), error deve ser null

# 6. Revogar chave antiga no console Google
# Nunca deixar chave comprometida ativa — revogar imediatamente após confirmar nova funciona
```

**Duração esperada:** 15 minutos.

---

### SCENARIO E: Shell Comprometida

**Sintomas:** processo inesperado rodando (`ps aux | grep -v grep`), `authorized_keys` modificado, uploads anômalos, alertas de segurança Hostinger.

> Este é o cenário mais grave. Assuma que TODOS os segredos na VPS estão comprometidos.

#### Fase 1 — Isolamento imediato (5min)

```bash
# No painel Hostinger: desconectar VPS da rede (ou firewall deny-all)
# Isso impede exfiltração adicional mas pode interromper o serviço

# Se ainda tiver SSH:
# Adicionar regra temporária para negar todo tráfego de saída exceto SSH
iptables -I OUTPUT -m state --state NEW -j DROP
iptables -I OUTPUT -d <SEU_IP_LOCAL> -j ACCEPT
```

#### Fase 2 — Rotacionar TODAS as chaves (30-60min)

A rotação deve ser feita **em máquina limpa**, não na VPS comprometida. Acesse os consoles via browser local.

| Serviço | Onde revogar | Nota |
|---|---|---|
| Gemini API Key | console.cloud.google.com | CLAUDE.md regra #3 |
| OpenAI API Key | platform.openai.com | se usada em A3 providers |
| Anthropic API Key | console.anthropic.com | se usada |
| Voyage AI Key | voyageai.com | se usada em embeddings |
| GitHub token | github.com/settings/tokens | para deploy e push |

```bash
# Após gerar novas chaves, auditar todos os repos por vazamentos:
# (rodar em máquina LIMPA, não na VPS comprometida)
gitleaks detect --source /path/to/local/memoria-nox
gitleaks detect --source /path/to/local/openclaw-vps

# Checar histórico Git por chaves expostas:
git log --all --full-history -p -- "*.env" | grep -E "GEMINI|ANTHROPIC|OPENAI|key=" | head -20
# Se encontrar algo: usar BFG Repo Cleaner para limpar histórico
```

#### Fase 3 — Re-key SSH (15min)

```bash
# Em máquina LIMPA: gerar novo par de chaves
ssh-keygen -t ed25519 -C "nox-mem-recovery-$(date +%Y%m%d)" -f ~/.ssh/nox-mem-new

# No painel Hostinger: adicionar nova chave pública e remover todas as antigas
# Verificar acesso com nova chave antes de remover as antigas

# No novo VPS (após reinstalar): checar authorized_keys
cat /root/.ssh/authorized_keys
# Deve conter APENAS suas chaves legítimas
```

#### Fase 4 — Restaurar código (30min)

```bash
# Assume que staged-* dirs na VPS podem estar tampered
# Clonar de main (commit assinado, confiável)
git clone https://github.com/totobusnello/memoria-nox.git /root/.openclaw/workspace/tools/nox-mem-clean
cd /root/.openclaw/workspace/tools/nox-mem-clean

# Verificar último commit assinado
git log --show-signature -1
# Confirmar que corresponde ao commit esperado no GitHub

# Build limpo
npm ci
npm run build
```

#### Fase 5 — Restaurar dados (30-60min)

Se o DB foi exfiltrado, os dados estão expostos. Avaliar se o conteúdo é sensível e informar usuários afetados.

Restaurar DB do backup mais recente **anterior** ao comprometimento (verificar timestamp com `ls -lt /var/backups/nox-mem/nightly/`).

Seguir procedimento de [SCENARIO A §Passo 5](#passo-5--restaurar-db-do-backup-15-30min).

#### Fase 6 — Documentar incidente

Ver [seção 6 — Incident Response Template](#6-incident-response-template).

**Duração esperada:** 4-8 horas.

---

### SCENARIO F: Operação Destrutiva Acidental

**Sintomas:** chunk count caiu drasticamente, `section` e `retention_days` zerados em entity chunks, KG relations deletadas, `sectionDistribution.compiled` < 183.

**Diagnóstico:**

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Checar chunk count atual vs baseline esperado (>62k)
curl -sf http://127.0.0.1:18802/api/health | jq '{total, embedded, sectionDistribution}'

# Checar ops_audit para identificar a operação causadora
sqlite3 ${NM}/nox-mem.db "
  SELECT op_name, started_at, status, snapshot_path
  FROM ops_audit
  ORDER BY started_at DESC
  LIMIT 10;
"

# Se snapshot_path está populado: a operação foi wrapped em withOpAudit
# Esse snapshot pode ser usado para recovery

# Listar snapshots pre-op disponíveis
ls -lt /var/backups/nox-mem/pre-op/*.db 2>/dev/null | head -10
```

#### Opção 1: Restaurar via withOpAudit snapshot (mais preciso)

```bash
# Identificar snapshot do ops_audit (mais próximo antes da operação)
SNAP=$(sqlite3 ${NM}/nox-mem.db "
  SELECT snapshot_path FROM ops_audit 
  WHERE status IN ('success','failed','crashed') 
  ORDER BY started_at DESC 
  LIMIT 1;
")
echo "Snapshot: ${SNAP}"

# Verificar integridade
sqlite3 "${SNAP}" "PRAGMA integrity_check;"
sqlite3 "${SNAP}" "PRAGMA user_version;"
# user_version deve ser igual ao DB atual

# Parar serviço
systemctl stop nox-mem-api

# Restaurar (via safeRestore — nunca cp direto)
set -a; source /root/.openclaw/.env; set +a
node -e "
  import('./dist/src/lib/op-audit.js').then(async (m) => {
    await m.safeRestore('${SNAP}');
    console.log('safeRestore: OK');
  });
"

systemctl start nox-mem-api
sleep 3
curl -sf http://127.0.0.1:18802/api/health | jq '{total, sectionDistribution}'
```

#### Opção 2: Sem snapshot pré-op — restaurar de nightly

```bash
# Apenas se não há snapshot pré-op disponível
ls -lt /var/backups/nox-mem/nightly/ | head -5

# Perda máxima: chunks ingestados desde último backup (até 24h)
NIGHTLY=/var/backups/nox-mem/nightly/nox-mem-<data>.db
sqlite3 ${NIGHTLY} "SELECT count(*) FROM chunks;"

set -a; source /root/.openclaw/.env; set +a
systemctl stop nox-mem-api
node -e "
  import('./dist/src/lib/op-audit.js').then(async (m) => {
    await m.safeRestore('${NIGHTLY}');
    console.log('OK');
  });
"
systemctl start nox-mem-api
```

#### Documentar o incidente

Todo acidente destrutivo deve ser documentado em `docs/INCIDENTS.md`. Usar template da [seção 6](#6-incident-response-template).

**Duração esperada:** 30 minutos (com snapshot) a 2 horas (restauração de nightly + re-ingest de chunks perdidos).

---

## 5. Recovery Verification

Executar TODOS os checks após qualquer restore. Não confie no log do restore — verifique o estado real.

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a

# 5a. Serviço respondendo
curl -sf http://127.0.0.1:18802/api/health | jq .status
# Deve ser: "ok"

# 5b. Schema version correto
curl -sf http://127.0.0.1:18802/api/health | jq .schemaVersion
# Deve ser 20 (post-Wave-B) ou 10 (pre-Wave-B baseline)

# 5c. Chunk count razoável (>50k indica restore bem-sucedido)
curl -sf http://127.0.0.1:18802/api/health | jq '{total, embedded}'
# total >= 62000 (valor de referência 2026-05-01)

# 5d. Vector coverage (CLAUDE.md regra #2)
curl -sf http://127.0.0.1:18802/api/health | jq .vectorCoverage
# embedded deve ser igual ou próximo de total (>=99.9%)

# 5e. Section distribution (entity chunks intactos)
curl -sf http://127.0.0.1:18802/api/health | jq .sectionDistribution
# .compiled deve ser >= 183

# 5f. KG intacto
curl -sf http://127.0.0.1:18802/api/health | jq '{kg_entities, kg_relations}'
# ~402 entities, ~544 relations

# 5g. Search funcional (teste com query conhecida)
curl -sf "http://127.0.0.1:18802/api/search?q=salience+formula&limit=3" \
  | jq '{count: (.results | length), first_id: .results[0].id}'
# count deve ser >= 1

# 5h. Integridade do DB
sqlite3 ${NM}/nox-mem.db "PRAGMA integrity_check;"
# Deve retornar: ok

# 5i. Spot-check 5 chunks conhecidos
sqlite3 ${NM}/nox-mem.db "
  SELECT id, length(chunk_text) as len, section 
  FROM chunks 
  WHERE section = 'compiled' 
  ORDER BY id DESC 
  LIMIT 5;
"
# Todos devem ter section='compiled' e len > 0
```

Se qualquer check falhar, **não considere o restore concluído**. Investigar e corrigir antes de retomar operação normal.

---

## 6. Incident Response Template

Usar este template em `docs/INCIDENTS.md` para cada incidente real.

```markdown
## [YYYY-MM-DD] — <título breve do incidente>

**Severidade:** CRITICAL / HIGH / MEDIUM / LOW
**Duração do impacto:** HH:MM UTC → HH:MM UTC
**Scenario aplicado:** A / B / C / D / E / F

### Timeline (UTC)

| Hora UTC | Evento |
|---|---|
| HH:MM | Alerta detectado / sintoma observado |
| HH:MM | Diagnóstico iniciado |
| HH:MM | Causa raiz identificada |
| HH:MM | Recovery iniciado |
| HH:MM | Serviço restaurado |
| HH:MM | Verification checks passados |

### Impact Assessment

- **Chunks perdidos:** N (ou 0 se restore completo)
- **RPO efetivo:** X horas (gap entre backup usado e momento do incidente)
- **RTO efetivo:** X horas (tempo total de recovery)
- **Funcionalidades afetadas:** search / KG / answer / viewer / all

### Causa Raiz

<descrição técnica em 2-5 linhas>

### Actions Taken

1. <passo 1>
2. <passo 2>
...

### Verification Output

```bash
# Colar output do /api/health pós-restore
```

### Lessons Learned

- <o que mudou no processo>
- <nova proteção adicionada>

### Cross-references

- Snapshot usado: `/var/backups/nox-mem/pre-op/<arquivo>.db`
- ops_audit row: ID = <N>
- PR de fix (se aplicável): #<número>
```

---

## 7. Drills — Cronograma de Prática

**Por quê drills?** O backup não serve de nada se o processo de restore nunca foi testado. O incident 2026-04-25 mostrou que produção pode surpreender com comportamento que nenhum teste local capturou.

### Mensal — Backup Restore Drill (30-45min)

**Objetivo:** confirmar que o arquivo de backup mais recente restaura limpo em ambiente scratch.

```bash
# Criar instância temporária SQLite (não substitui prod)
DRILL_DIR=/tmp/nox-mem-drill-$(date +%Y%m%d)
mkdir -p ${DRILL_DIR}

# Copiar backup mais recente para drill dir
cp /var/backups/nox-mem/nightly/$(ls -t /var/backups/nox-mem/nightly/ | head -1) \
   ${DRILL_DIR}/drill.db

# Verificar integridade
sqlite3 ${DRILL_DIR}/drill.db "PRAGMA integrity_check;"
# Deve retornar: ok

sqlite3 ${DRILL_DIR}/drill.db "SELECT COUNT(*) FROM chunks;"
# Deve ser > 50000

sqlite3 ${DRILL_DIR}/drill.db "PRAGMA user_version;"
# Deve corresponder à versão esperada

# Limpar drill dir
rm -rf ${DRILL_DIR}
echo "Drill mensal: PASSED $(date)"
```

### Trimestral — Full DR Drill (2-3h)

**Objetivo:** simular falha completa de VPS e restaurar em novo ambiente.

1. Provisionar VPS temporária (pode ser VM local com multipass/UTM)
2. Seguir SCENARIO A do zero
3. Executar todos os checks da [seção 5](#5-recovery-verification)
4. Documentar RTO efetivo alcançado
5. Destruir VPS temporária
6. Atualizar este doc se o procedimento precisar de ajustes

### Anual — Tabletop Exercise (2h)

**Objetivo:** walk-through verbal dos cenários A-F com a equipe.

Para cada cenário:
1. "O que detectaria este problema primeiro?" (alerta / check manual / usuário reporta)
2. "Quais são os primeiros 3 passos?" (diagnóstico, não recovery direto)
3. "O que pode dar errado durante o recovery?" (pitfalls)
4. "Como sabemos que o recovery funcionou?" (verification checks)

---

## 8. Referências cruzadas

| Tópico | Documento |
|---|---|
| Backup commands detalhados | `docs/ops/BACKUP-RUNBOOK.md` |
| Monitoramento e alertas | `docs/ops/MONITORING.md` |
| Deploy commands (staging → prod) | `docs/DEPLOY-WAVE-B.md` |
| Export/import archive A2 | `docs/EXPORT-IMPORT.md` |
| Incident log histórico | `docs/INCIDENTS.md` |
| Decisões arquiteturais | `docs/DECISIONS.md` |
| `withOpAudit()` e `safeRestore()` | `src/lib/op-audit.ts` |
| Regras críticas operacionais | `CLAUDE.md §Regras críticas` |

---

*Preparado: 2026-05-18 | Wave H — Operational Readiness*
