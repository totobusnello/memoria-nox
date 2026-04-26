# Runbook — Rollback schema migration (DB)

**Quando usar:** após uma migration v8/v9/v10/v11+ no `db.ts` corromper dados ou quebrar invariantes (ex: ALTER TABLE com defaults errados, UPDATE em massa que zerou metadata).

**Diferença vs `recovery-from-snapshot.md`:** aquele é pra incidents que tem snapshot pré-op (`/var/backups/nox-mem/pre-op/`). Este é pra migrations que rodam no startup do `nox-mem-api` (sem snapshot pré-op explícito).

## Pré-requisitos

- SSH root VPS (`ssh root@100.87.8.44`)
- Backup pré-migration existe em `/root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-v<N>-*.db`
- Conhece a versão estável anterior (current schema_version: v10)

## Procedure (15min)

### 1. STOP serviços que escrevem no DB
```bash
ssh root@100.87.8.44 '
systemctl stop nox-mem-api nox-mem-watcher openclaw-gateway
ps -ef | grep -E "nox-mem|openclaw" | grep -v grep | grep -v stop
# Confirmar todos pararam
'
```

### 2. Identificar backup alvo
```bash
ssh root@100.87.8.44 '
ls -la /root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-v* | sort -r
# Escolher o mais recente que preceda a migration buggy

# Validar integridade do snapshot
sqlite3 /root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-vN-<DATE>.db "PRAGMA integrity_check;"
sqlite3 /root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-vN-<DATE>.db "PRAGMA user_version;"
'
```

Esperado: `ok` + `user_version` correto.

### 3. Rollback código (db.ts)

**Se o problema é a migration nova (v11+ broken):**
```bash
ssh root@100.87.8.44 '
cd /root/.openclaw/workspace/tools/nox-mem/src
# Restaurar db.ts pra versão pré-v11
cp db.ts.bak-pre-v11-<DATE> db.ts
npm run build 2>&1 | tail -3
'
```

### 4. Restore DB via safeRestore() (recomendado)

```bash
ssh root@100.87.8.44 '
cd /root/.openclaw/workspace/tools/nox-mem
node -e "
import(\"./dist/lib/op-audit.js\").then(m => {
  const result = m.safeRestore(
    \"/root/.openclaw/workspace/tools/nox-mem/backups/nox-mem-pre-vN-DATE.db\",
    { force: true }  // se schema_user_version difere intencionalmente
  );
  console.log(JSON.stringify(result, null, 2));
}).catch(e => { console.error(e.message); process.exit(1); });
"
'
```

`safeRestore()` faz:
- ✅ integrity_check no snapshot
- ✅ schema_user_version validation (com `force:true` aceita mismatch)
- ✅ ALLOWED_PREFIXES check
- ✅ VACUUM INTO tmp + atomic rename
- ✅ unlink WAL/SHM órfãos APÓS rename (W2-4 fix)

**NÃO usar `cp snapshot.db nox-mem.db`** — corrompe se WAL stale.

### 5. Restart + validate
```bash
ssh root@100.87.8.44 '
systemctl start nox-mem-api nox-mem-watcher openclaw-gateway
sleep 5
systemctl is-active nox-mem-api nox-mem-watcher openclaw-gateway

# Validar schema
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "PRAGMA user_version; SELECT COUNT(*) FROM chunks;"

# Health check
curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, schema:.schemaVersion}"

# Schema invariants
tail -3 /var/log/nox-schema-invariants.log
'
```

### 6. Agent DBs (se a migration afetou todos os 6)

Repetir steps 2-4 pra cada agent DB individualmente:
```bash
for d in nox atlas boris cipher forge lex; do
  AGENT_DB="/root/.openclaw/workspace/agents/$d/tools/nox-mem/nox-mem.db"
  AGENT_BACKUP_DIR="$(dirname $AGENT_DB)/backups"
  # ... safeRestore por agente
done
```

## Pegadinhas

- **schema_user_version mismatch:** se rollback de v10→v9, current DB tem user_version=10 mas snapshot é 9 → `safeRestore` throw a menos que `force:true`. Documentar reason no INCIDENTS.md
- **WAL/SHM órfãos:** se serviços não foram parados antes, WAL pode ter writes não-flushed → safeRestore unlink resolve, mas pode perder ~últimos 60s de chunks ingested
- **vec_chunks orphans:** após restore, rodar `nox-mem vectorize` pra reconciliar embeddings (trigger `trg_chunks_delete_cascade` cuida do cleanup)
- **NÃO rodar reindex pós-rollback** sem confirmar primeiro que o source files match o snapshot (pode causar chunk count divergence)

## Pós-rollback

1. INCIDENTS.md entry com sintoma + migration version + rollback path
2. Audit doc em `audits/<DATE>-rollback-vN-to-vM.md`
3. Code review do migrate function ANTES de retentar (audit duplo recomendado se schema impact)
4. Adicionar test em `__tests__/op-audit-e2e.test.ts` cobrindo o caso (se aplicável)

## Quando NÃO rollback (contraindicações)

- Se migration v(N) já tem dados criados em produção que dependem do schema novo (perderia dados)
- Se a "broken" migration na verdade é correta mas exposed bug pré-existente em outra parte
- Se janela de tolerância > tempo de fix forward (rollback custa downtime, fix forward pode ser <1h)

Em casos assim: fix forward com migration v(N+1) corretiva, deixar v(N) histórico.
