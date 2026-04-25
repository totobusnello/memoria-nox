# Runbook — Recovery from Pre-Op Snapshot

**Quando usar:** após op destrutiva (reindex/compact/etc) corromper estado do nox-mem em produção. CLAUDE.md regra #15.

**Pré-requisitos:**
- Snapshot pré-op existe em `/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db`
- Linha correspondente em `ops_audit` (status=`success`/`failed`/`crashed`)
- Acesso root na VPS via Tailscale (`ssh root@100.87.8.44`)

---

## Decision tree — quando restaurar?

```
Sintoma detectado (incident/sanity check fail)
        ↓
Qual a regressão?
   ├─ DB intacto, só metadata zerada (pattern incident 2026-04-25)
   │     → NÃO restaurar full DB; investigar caller (routing, wrapping)
   │     → Reaplicar handler correto (ex: ingest-entity loop) é suficiente
   │
   ├─ Chunks deletados sem reposição automática (irreversível via re-ingest)
   │     → CANDIDATO a restore via safeRestore()
   │
   ├─ Schema migration corrompida (ALTER TABLE drop column accident)
   │     → restore COM `force: true` (schema mismatch esperado)
   │
   └─ DB file corrupto (PRAGMA integrity_check fail)
         → restore via safeRestore() obrigatório
```

**Regra:** restore é última opção. Se o issue pode ser resolvido por re-ingest seletivo (ex: 183 entity files via `nox-mem ingest-entity`), preferir essa rota — preserva tudo o que aconteceu DEPOIS do snapshot.

---

## Identificar o snapshot certo

```bash
# Listar snapshots disponíveis (ordem cronológica)
ssh root@100.87.8.44 'ls -lh /var/backups/nox-mem/pre-op/ | sort -k 9'

# Cruzar com ops_audit pra ver o que cada op fez
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT id, op_name, started_at, finished_at, status, affected_rows, snapshot_path,
         schema_user_version, snapshot_bytes
  FROM ops_audit
  ORDER BY id DESC
  LIMIT 20;
"'
```

**Critérios pra escolher:**
- Snapshot ANTES da op problemática (mais recente bom > mais antigo)
- `status='success'` da op anterior (DB estava saudável quando snapshot foi tirado)
- `schema_user_version` da audit row deve match com schema atual (ou aceitar mismatch via `force:true`)

---

## Procedure (canônica) — usar `safeRestore()`

**NÃO fazer `cp snapshot.db nox-mem.db` direto.** Cria corrupção lógica via WAL/SHM órfãos. Use `safeRestore()` que faz tudo certo.

### Passo 1 — Parar serviços que escrevem no DB

```bash
ssh root@100.87.8.44 '
  systemctl stop openclaw-gateway nox-mem-api nox-mem-watcher
  sleep 3
  systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher
  # Esperado: 3x "inactive"
'
```

### Passo 2 — Snapshot do estado corrompido (CYA)

Antes de sobrescrever, preserva o estado atual pra forensics futura.

```bash
ssh root@100.87.8.44 '
  cp /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
     /var/backups/nox-mem/pre-op/CORRUPTED-pre-restore-$(date +%Y%m%d-%H%M%S).db
'
```

### Passo 3 — Restaurar via `safeRestore()`

```bash
SNAPSHOT="/var/backups/nox-mem/pre-op/reindex-20260425143012-12345-9e0ba8f8.db"

ssh root@100.87.8.44 "
  cd /root/.openclaw/workspace/tools/nox-mem
  set -a; source /root/.openclaw/.env; set +a
  node -e \"
    import('./dist/lib/op-audit.js').then(async m => {
      const r = m.safeRestore('$SNAPSHOT');
      console.log('result:', JSON.stringify(r));
      process.exit(r.ok ? 0 : 1);
    }).catch(err => { console.error(err); process.exit(2); });
  \"
"
```

**Output esperado:**
```json
{ "ok": true, "warnings": [] }
```

**Se houver schema mismatch:**
```
Error: schema mismatch: current user_version=10, snapshot=8.
Pass { force: true } to restore anyway.
```

→ Decidir: restaurar mesmo? Se sim, repetir com `m.safeRestore('$SNAPSHOT', { force: true })`. **Significa que migrations posteriores serão perdidas — re-aplicar manualmente após.**

**Se houver warnings:**
```json
{ "ok": true, "warnings": ["removed stale -wal file", "removed stale -shm file"] }
```

→ OK. Warnings são esperados quando havia transações em-flight. `safeRestore` removeu os arquivos órfãos.

### Passo 4 — Religar serviços

```bash
ssh root@100.87.8.44 '
  systemctl start nox-mem-api nox-mem-watcher openclaw-gateway
  sleep 5
  systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher
'
```

### Passo 5 — Validar saúde

```bash
# Sanity check completo
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  total: .chunks.total,
  vc: .vectorCoverage,
  section: .sectionDistribution,
  retention: .retentionDistribution,
  opsAudit: .opsAudit
}"'

# Schema invariants
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/check-schema-invariants.sh'
# Esperado: exit 0, "OK section_nonnull=... compiled=... ..."

# Canary semantic
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/semantic-canary.sh'
# Esperado: exit 0, OK total>0 semantic>0
```

### Passo 6 — Vectorize (se necessário)

Snapshot pode estar de antes do último vectorize. Validar e completar:

```bash
ssh root@100.87.8.44 '
  set -a; source /root/.openclaw/.env; set +a
  nox-mem vectorize 2>&1 | tail -5
'
```

### Passo 7 — Documentar incident

- Adicionar entry em `docs/INCIDENTS.md` com timeline + root cause + restore procedure usado
- Salvar memory feedback se houve lição arquitetural nova
- Criar issue/follow-up se snapshot escolhido não foi ideal (mensagem pra futuro: documentar critério)

---

## Cenários comuns

### Cenário A — Reindex zerou metadata de entities (incident 2026-04-25 pattern)
**NÃO restaurar.** Patch arquitetural em `ingestFile()`/`ingest-router.ts` previne futuro. Re-aplicar entity ingestion via:
```bash
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a;
for f in $(find /root/.openclaw/workspace/memory/entities -name "*.md"); do
  nox-mem ingest-entity "$f"
done
nox-mem vectorize'
```

### Cenário B — Compact deletou chunks recentes em massa por bug
**Restore obrigatório** se affected_rows alto e re-ingest impraticável. Use `safeRestore()` do snapshot pré-compact.

### Cenário C — Schema migration corrompida (drop column accidental)
**Restore com `force: true`** porque user_version do snapshot é menor. Re-aplicar migration MANUAL após restore (re-rodar `ALTER TABLE` carefully).

### Cenário D — DB file corrupto (`PRAGMA integrity_check` fail)
**Restore obrigatório.** Snapshot mais recente saudável. Aceitar perda de dados desde o snapshot — não há outra opção.

---

## Limitações conhecidas (deferred Wave 2)

- **ops_audit é parte do snapshot:** restore reverte audit history. Se forensics precisar de log persistente, ele está em `/var/log/nox-snapshot-prune.log` parcialmente. Wave 2 cleanup: append-only audit log externo.
- **Sem hash-chain integrity:** adversário com DB access pode editar ops_audit retroativamente. Wave 2: WORM trigger ou hash chain.
- **Schema `force:true` não re-aplica migrations:** operador deve saber quais migrations rodaram entre snapshot e current. Maintain checklist em `docs/INCIDENTS.md` por migration version.

---

## Comandos de validação rápida (post-restore)

```bash
# Single-line health snapshot
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage.embedded==.vectorCoverage.total, section_compiled:.sectionDistribution.compiled, ops_failed_24h:.opsAudit.failed_24h}"'

# Esperado pós-restore bem-sucedido:
# { total: <N>, vc: true, section_compiled: 183 (ou esperado), ops_failed_24h: 0 }
```

---

*Runbook criado: 2026-04-25 ~10:30 BRT após audit A1 v2. Atualizar conforme novos cenários surjam.*
