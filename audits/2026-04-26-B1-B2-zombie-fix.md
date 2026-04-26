# Audit Fix — B1 reaper coverage + B2 closeDb mid-function (2026-04-26)

**Trigger:** Sanity check 24h pós-sessão de hardening (2026-04-25) detectou anomalia: 6 snapshots `reindex-2026042602*.db` em `/var/backups/nox-mem/pre-op/` MAS `/api/health.opsAudit.total_24h=0`. Investigação revelou bug ativo em produção, NÃO naming collision como hipótese inicial.

**Verdict:** 2 bugs reais (1 HIGH, 1 MEDIUM); ambos fixados + smoke-tested em 6 agent DBs.

---

## Diagnóstico

### Sintoma observado
- 6 zumbis (`status='running'`) há 8h em `ops_audit` nas 6 agent DBs (atlas/lex/forge/nox/boris/cipher)
- Cada zombie correspondia a um snapshot pre-op em `/var/backups/nox-mem/pre-op/reindex-20260426020{003..056}-*.db` (12-13MB cada)
- Origem: `nightly-maintenance.sh` Phase 2 (sábado 2026-04-25 23:00 BRT, DOM=25 odd) — chama `nox-mem reindex` per-agent com `sleep 10` entre cada
- **Dados intactos:** chunks count atual ≥ snapshot count em todos 6 agents (watcher continuou ingerindo após reindex completar). A2 routeIngest preservou estrutura.

### Root cause (B2)
`src/reindex.ts` `_reindexImpl()` chama `closeDb()` **no meio da função** (linha 103 pré-fix):

```ts
// Use closeDb() to properly reset singleton  ← MAL DOCUMENTADO
closeDb();
db.exec("UPDATE chunks SET retention_days = NULL WHERE tier = 'core'");  ← falha em DB fechado
return { files, chunks };  ← retorna pra withOpAudit
```

Cascata:
1. `closeDb()` zera singleton + fecha conexão SQLite
2. `db.exec(...)` na linha seguinte usa local var ainda apontando pra Database fechado → throw silencioso
3. Control retorna pra `withOpAudit` (em `src/lib/op-audit.ts` linha 148), que tem sua própria captura `const db = getDb()` — também stale
4. `db.prepare("UPDATE ops_audit SET status='success' ...").run(...)` → throw em DB fechado
5. catch também tenta `db.prepare("UPDATE ... 'failed' ...")` → throw
6. Process exit sem flush → linha permanece `status='running'` → **zombie**

### Root cause secundário (B1)
`reapZombies()` (criado no A1 v2 fix em 04-25 pra cobrir `nox-mem-api` daemon startup) NÃO era chamado pelo CLI per-agent invocations. Cada `nox-mem reindex` em isolated workspace spawn-and-die nunca limpava zumbis acumulados → table polui indefinidamente.

---

## Fixes aplicados

### Fix B2 — `src/reindex.ts`
- Removido `closeDb()` mid-function (linhas 102-103 pré-fix)
- Removido import `closeDb` (unused agora)
- Adicionado comentário explicando lifecycle (CLI handler owns close)

### Fix B1 — `src/index.ts`
- Adicionado `import { reapZombies } from "./lib/op-audit.js"`
- Adicionado `try { reapZombies(); } catch { /* non-fatal */ }` antes de `program.parse()` — cobre TODOS callers (CLI per-agent + main daemon path)
- Adicionado `closeDb()` ao reindex CLI handler (linha 80) — paridade com search/vectorize/ingest/etc

---

## Smoke tests (todos passaram)

| Teste | Resultado |
|---|---|
| `nox-mem reindex --dry-run` em atlas | ✅ JSON preview correto (45 chunks, 23 files), no mutation |
| `nox-mem reindex` real em atlas | ✅ `[op-audit] reindex success in 54ms (affected=46)` + linha id=2 status='success' |
| Reindex em lex/forge/nox/boris/cipher | ✅ 5/5 success, durations 63-175ms |
| Validação ops_audit pós-fix em 6 agents | ✅ Cada agent: 1 success + 1 crashed (zumbi do 02:00 reaped) |
| Reaper artificial (INSERT zumbi → 1 CLI invoke) | ✅ smoke-zombie marcado `crashed`, `error_message='reaped: process died before completing'` |
| Build TypeScript | ✅ `tsc` sem warnings |

---

## Arquivos modificados (na VPS)

| Arquivo | Backup |
|---|---|
| `src/reindex.ts` | `.bak-pre-B2-fix-20260426` |
| `src/index.ts` | `.bak-pre-B2-fix-20260426` |
| `dist/*.js` | rebuild via `npm run build` |

## ops_audit pós-fix

| Agent | Antes (zumbis) | Depois |
|---|---|---|
| atlas | 1 running | 1 success + 1 crashed |
| lex | 1 running | 1 success + 1 crashed |
| forge | 1 running | 1 success + 1 crashed |
| nox | 1 running | 1 success + 1 crashed |
| boris | 1 running | 1 success + 1 crashed |
| cipher | 1 running | 1 success + 1 crashed |

---

## Lições

1. **`closeDb()` mid-function é code smell** — singleton lifecycle pertence ao caller (CLI handler, daemon, ou test setup). Nunca fechar mid-op, especialmente quando wrapped por outro contexto (withOpAudit) que precisa do mesmo handle pra cleanup.
2. **Reapers precisam cobrir TODOS spawn paths** — daemon startup OU CLI invocations OR ambos. A1 v2 cobriu só daemon; coverage gap pegou 24h pra ser detectado.
3. **Audit duplo não pega tudo** — code-reviewer + security-reviewer em 04-25 bateu em A1+A2 e detectou 27 findings, mas a integração `_reindexImpl()` ↔ `withOpAudit()` não foi exercitada num smoke real (só unit tests do withOpAudit standalone). Próximas sessões: smoke test end-to-end em isolated workspace ANTES de fechar audit.
4. **Schema invariants canary funcionou perfeitamente** — section_nonnull=732, ops_failed=0 nas últimas 12h porque nenhum reindex foi chamado entre os zumbis (ops failed contam só status='failed', não 'running'). Sugestão Wave 2: incluir `running >1h` no canary como sinal precoce.

## Pendências deferred pra Wave 2 cleanup

- Adicionar smoke test E2E `_reindexImpl + withOpAudit` no test suite (cobre regressão dessa classe)
- Modificar canário schema-invariants pra alertar quando `ops_audit WHERE status='running' AND started_at < now-1h` (sinal precoce de zumbi antes do reaper rodar)
- Considerar wrapper de transação SQLite pra garantir UPDATE de ops_audit acontece mesmo se fn() crashar (mais robusto que catch atual)
