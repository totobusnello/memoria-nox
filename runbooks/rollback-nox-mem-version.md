# Runbook — Rollback nox-mem version (TS code)

**Quando usar:** após `git pull` ou edit em `/root/.openclaw/workspace/tools/nox-mem/src/` introduzir bug em prod (CLI quebrado, /api/health falhando, schema invariants vermelho, etc).

**NÃO usar:** se o problema é dado (chunks/section/retention) — use `runbooks/recovery-from-snapshot.md`.

## Pré-requisitos

- SSH root na VPS via Tailscale (`ssh root@100.87.8.44`)
- Backup `.bak-pre-<feature>-<date>` existe em `src/` (sempre fazer ANTES de editar — convenção)
- Conhecer qual feature/commit introduziu o problema

## Procedure (5min)

### 1. Identificar arquivo + backup
```bash
ssh root@100.87.8.44 '
ls -la /root/.openclaw/workspace/tools/nox-mem/src/lib/op-audit.ts*
# espera ver: op-audit.ts + 1+ .bak-pre-<feature>-<date>
'
```

### 2. Restaurar versão anterior
```bash
ssh root@100.87.8.44 '
cd /root/.openclaw/workspace/tools/nox-mem/src
# Identificar .bak alvo (mais recente que precede o bug)
ls lib/op-audit.ts.bak* | sort -r | head -3

# Restore
cp lib/op-audit.ts.bak-pre-<FEATURE>-<DATE> lib/op-audit.ts
'
```

### 3. Rebuild TS + restart serviços
```bash
ssh root@100.87.8.44 '
cd /root/.openclaw/workspace/tools/nox-mem
npm run build 2>&1 | tail -5
# se ok: tsc deve sair sem warning
'

# Restart serviços que carregam o código rollback'd
ssh root@100.87.8.44 'systemctl restart nox-mem-api nox-mem-watcher'
```

### 4. Validação imediata
```bash
ssh root@100.87.8.44 '
sleep 3
curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, opsAudit:.opsAudit}"
systemctl is-active nox-mem-api nox-mem-watcher
'
```

Esperado: `total>0`, `embedded==total`, services `active`.

### 5. Test suite
```bash
ssh root@100.87.8.44 '
cd /root/.openclaw/workspace/tools/nox-mem
node --test dist/__tests__/ 2>&1 | tail -5
'
```

Esperado: `pass=N fail=0`.

### 6. Rodar smoke específico do problema
Se o bug era em reindex, rodar `nox-mem reindex --dry-run` em workspace de teste (NUNCA em main). Se em search, query simples via `nox-mem search "test"`.

## Pós-rollback

1. **Documentar:** abrir entry em `docs/INCIDENTS.md` com timestamp, sintoma, rollback feito
2. **Reproduzir bug em isolado:** copy DB pra `/tmp/test.db`, refazer feature com TDD pra fix correto
3. **NÃO re-deployar** versão buggy até teste E2E pegar o caso

## Pegadinhas

- **closeDb mid-op:** se o rollback foi por bug B2 (ops_audit zumbi), confirmar que `_reindexImpl` NÃO chama `closeDb()` mid-function (lição feedback memory `closedb_mid_function_invalidates_withopaudit.md`)
- **Singleton getDb():** se mudou tipo de DB connection, pode precisar restart watcher/api separadamente
- **Ops em flight:** se `ops_audit` tem rows status='running', deixar reaper resolver (>6h) ou marcar `crashed` manualmente antes do rebuild
