# Op-Audit Gaps Review — Diagnóstico + 4 Fixes Propostos
**Data:** 2026-05-15
**Autor diagnóstico:** Maestro (read-only investigation)
**Reviewer requested:** Forge (op-audit code owner)
**Status:** 📋 AWAITING FORGE REVIEW antes de implementação
**Origem:** Análise sistema 15/05 revelou anomalia em snapshots pre-op (13MB vs 1.2GB DB main)

---

## TL;DR

**Achado inicial (15/05 manhã):** Snapshots pre-op de 13MB no `/var/backups/nox-mem/pre-op/` pareciam corrupted (DB main é 1.2GB) — alerta CRÍTICO levantado.

**Diagnóstico fechado (15/05 tarde):** Snapshots 13MB **são esperados e funcionais** — pertencem aos 6 sub-DBs dos agentes secundários (atlas/boris/cipher/forge/lex/nox), não ao main. Severidade revisada de 🔴 → 🟢.

**Mas:** 4 gaps reais de severidade média foram identificados durante a investigação. Este doc propõe fixes priorizados.

**Pedido pro Forge:** revisar 4 fixes propostos, dar opinião + ajustes, antes da implementação começar.

---

## 1. Evidência coletada (read-only)

### 1.1 Inventário de DBs no sistema

```
Main DB:         /root/.openclaw/workspace/tools/nox-mem/nox-mem.db      1.2 GB / 69.290 chunks
Agent atlas:     /root/.openclaw/workspace/agents/atlas/tools/nox-mem/   13 MB / ~50 chunks
Agent boris:     /root/.openclaw/workspace/agents/boris/tools/nox-mem/   13 MB / ~180 chunks
Agent cipher:    /root/.openclaw/workspace/agents/cipher/tools/nox-mem/  13 MB / ~50 chunks
Agent forge:     /root/.openclaw/workspace/agents/forge/tools/nox-mem/   13 MB / ~395 chunks
Agent lex:       /root/.openclaw/workspace/agents/lex/tools/nox-mem/     13 MB / ~55 chunks
Agent nox:       /root/.openclaw/workspace/agents/nox/tools/nox-mem/     13 MB / ~600 chunks
```

### 1.2 Snapshots pre-op (último 14d)

| Tipo | Path | Tamanho | Chunks | Embedded | DB de origem |
|---|---|---|---|---|---|
| `compact-20260511020004` | `/var/backups/nox-mem/pre-op/` | 1.24 GB | 70.077 | 70.012 | **Main** ✅ |
| `compact-20260504020107` | `/var/backups/nox-mem/pre-op/` | 1.04 GB | (não validado) | (não validado) | **Main** ✅ |
| `reindex-*-02:00:05` | `/var/backups/nox-mem/pre-op/` | 13 MB | 48-53 | 0 | Atlas? |
| `reindex-*-02:00:15` | `/var/backups/nox-mem/pre-op/` | 13 MB | 177-182 | 0 | Boris? |
| `reindex-*-02:00:26` | `/var/backups/nox-mem/pre-op/` | 13 MB | 49-54 | 0 | Cipher? |
| `reindex-*-02:00:37` | `/var/backups/nox-mem/pre-op/` | 13 MB | 393-399 | 0 | Forge? |
| `reindex-*-02:00:47` | `/var/backups/nox-mem/pre-op/` | 13 MB | 50-55 | 0 | Lex? |
| `reindex-*-02:00:57` | `/var/backups/nox-mem/pre-op/` | 13 MB | 591-650 | 0 | Nox? |

### 1.3 Validação manual

```
$ time sqlite3 -readonly /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
       "VACUUM INTO '/tmp/test-vacuum-snapshot.db'"
real    0m7.151s
Result: size=1243865088 chunks=69290 embedded=69291  ✅ VACUUM INTO funciona
```

### 1.4 Comparação de schema (Main vs Agent snapshot)

| Tabelas presentes | Main (compact) | Agent (reindex) |
|---|---|---|
| `chunks`, `chunks_fts*`, `kg_entities`, `kg_relations`, `meta`, `vec_*`, `ops_audit` | ✅ | ✅ |
| `daily_metrics` | ✅ | ❌ |
| `decision_versions` | ✅ | ❌ |
| `noise_prototypes` | ✅ | ❌ |
| `reflect_cache` | ✅ | ❌ |
| `session_distill_log` | ✅ | ❌ |
| `consolidated_files`, `dedup_log`, `eval_*`, `search_telemetry`, `cli_telemetry`, `ocr_jobs` | ✅ | ✅ |

**Schema dos agents é subset do main** → confirma origem distinta.

### 1.5 Código relevante

- `src/lib/op-audit.ts` (425 linhas, last modified 06/05 19:37)
  - Linha 87-170: `function snapshot()` — VACUUM INTO atômico
  - Linha 118: `const finalPath = join(dir, ${opName}-${ts}-${process.pid}-${uid}.db)` ← **naming sem db_source**
  - Linha 121: `db.prepare('VACUUM INTO ?').run(tmpPath)` ← usa `getDb()` cujo path depende de env `NOX_DB_PATH`
- `src/reindex.ts`:
  - Linha 1: `import { getDb } from "./db.js"`
  - Linha 141: `return withOpAudit<ReindexResult>("reindex", async () => {`

### 1.6 Cron / orchestration

```cron
0 23 * * *   /root/.openclaw/scripts/nightly-maintenance.sh  # main DB orchestra
30 5  * * *  /root/.openclaw/workspace/tools/cross-agent-sync.sh  # cross-agent
```

Snapshots às 02:00:05-57 não correspondem a cron visível — provável trigger via `backup-all.sh` (02:00) ou subprocess invocado por nightly que itera os 6 agent DBs com `NOX_DB_PATH` env var apontando pra cada um. **Confirmar com Forge** qual script orquestra.

---

## 2. Diagnóstico definitivo

### 2.1 Causa raiz dos snapshots 13MB

O `withOpAudit()` é chamado durante reindex de cada agent DB. O script orchestrador (a confirmar — provavelmente parte de `nightly-maintenance.sh` ou subprocess análogo) define `NOX_DB_PATH` apontando pro DB do agente alvo antes de invocar `nox-mem reindex`. O `getDb()` em `op-audit.ts:118` resolve o path correto → VACUUM INTO produz snapshot daquele agent DB → arquivo gravado em `/var/backups/nox-mem/pre-op/reindex-*.db` **sem qualificador de qual DB foi**.

**Comportamento operacional: correto.**
**Visibilidade operacional: pobre.**

### 2.2 Severidade revisada

| Alerta original | Severidade real |
|---|---|
| 🔴 Snapshots inválidos | 🟢 Falso alarme — são válidos pra sub-DBs |
| 🟡 6 ocr zombies | 🟢 4/6 foram kills intencionais — 2 zombies reais |
| ❌ openclaw-api inactive | ❌ Não existe (erro de inferência inicial) |

---

## 3. Gaps reais identificados (severidade média)

### Gap A — Frequência baixa de snapshot do main DB

**Problema:** snapshot do main DB acontece apenas quando uma operação destrutiva é invocada (compact, reindex manual). Compact roda **~1×/semana** (últimos: 04/05 e 11/05). Entre 2 compacts, se uma operação manual quebrar, **perde-se ~7 dias de chunks novos**.

**Impacto:** ingestão diária de ~500-1000 chunks; janela de 7d = 3.500-7.000 chunks em risco.

**Fix proposto:**
```cron
# Snapshot diário do main DB (independente de ops destrutivas)
0 3 * * * /root/.openclaw/scripts/snapshot-main-db.sh >> /var/log/nox-snapshot.log 2>&1
```

```bash
# /root/.openclaw/scripts/snapshot-main-db.sh
#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d%H%M%S)
DEST="/var/backups/nox-mem/daily-main/main-${TS}.db"
mkdir -p "$(dirname "$DEST")" && chmod 0700 "$(dirname "$DEST")"
sqlite3 -readonly /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "VACUUM INTO '${DEST}.tmp'"
sqlite3 -readonly "${DEST}.tmp" "PRAGMA integrity_check;" | grep -q "^ok$"
mv "${DEST}.tmp" "$DEST"
chmod 0600 "$DEST"
# Retention 7d
find /var/backups/nox-mem/daily-main/ -name "main-*.db" -mtime +7 -delete
```

**Esforço:** ~30min (script + cron + teste)
**Risco:** Baixo (read-only do main + write em pasta dedicada). Mas vale validar: o VACUUM INTO via sqlite3 CLI (não app context) funciona em DB com extensions sqlite-vec carregadas? Forge testou isso antes?

**Pergunta pro Forge:**
- Q1: VACUUM INTO via sqlite3 CLI standalone consegue copiar tabelas `vec_chunks_*` (que requerem extension)? Ou precisa app context com better-sqlite3 + extension load?
- Q2: Disk impact: 1.2GB/dia × 7d retention = ~8.5GB. OK ou prefere retention menor / compressão gz pós-snapshot?

---

### Gap B — Naming dos snapshots ambíguo

**Problema:** `reindex-20260514020058-992857-d4ed1874b6594e7c82b4092246ea1c0a.db` não identifica qual DB foi snapshoteado. Em incident de recovery, requer adivinhar pelo timestamp/PID.

**Impacto:** tempo de mean-time-to-recover ↑. Risco de restaurar snapshot errado em panic.

**Fix proposto:** modificar `op-audit.ts` linha ~118 pra extrair basename do DB path:

```typescript
// op-audit.ts, antes da linha 118:
const dbPath = process.env.NOX_DB_PATH ?? '<DB_PATH from getDb()>';
const dbSource = basename(dirname(dbPath));  // 'agents/atlas' → 'atlas'; main = 'tools'
const finalPath = join(dir, `${opName}-${dbSource}-${ts}-${process.pid}-${uid}.db`);
```

Resultado: `reindex-atlas-20260514020005-...db`, `reindex-main-20260511020004-...db`.

**Esforço:** ~30min (edit + tests + deploy)
**Risco:** Médio — altera filename convention. Scripts existentes que dependem do nome (ex: `prune-pre-op-snapshots.sh`) podem quebrar.

**Pergunta pro Forge:**
- Q3: Confirma que `process.env.NOX_DB_PATH` reflete o DB ativo no momento do snapshot? Ou getDb() resolve via outro caminho (ex: hardcoded fallback)?
- Q4: Qual a heurística mais confiável pra derivar `dbSource`? Sugestões:
  - (a) `basename(dirname(dbPath))` → `atlas`, `boris`, ..., `tools`
  - (b) Parse explícito: extrair `<agent>` de `/agents/<agent>/tools/nox-mem/nox-mem.db`
  - (c) Adicionar env var explícito `NOX_DB_SOURCE` setado pelo orchestrator
- Q5: `prune-pre-op-snapshots.sh` faz match em `reindex-*.db` ou `*-*.db`? Vai precisar atualizar o regex?

---

### Gap C — Falta de visibilidade operacional

**Problema:** `/api/health.opsAudit` e listagem CLI não distinguem qual DB cada operação afetou. Eu (e o Toto) não tínhamos como saber que esses snapshots 13MB eram de agents — investigação levou ~1h.

**Impacto:** operação cega. Decisões baseadas em métricas erradas (ex: falso CRÍTICO levantado inicialmente).

**Fix proposto:**

1. **Schema migration v.17:**
```sql
ALTER TABLE ops_audit ADD COLUMN db_source TEXT;
ALTER TABLE ops_audit ADD COLUMN db_path TEXT;
UPDATE ops_audit SET db_source='unknown' WHERE db_source IS NULL;
```

2. **`op-audit.ts` — popular as colunas em `withOpAudit()`:**
```typescript
const dbPath = process.env.NOX_DB_PATH ?? '<resolved by getDb()>';
const dbSource = deriveDbSource(dbPath);
// ... no INSERT INTO ops_audit:
INSERT INTO ops_audit (op_name, snapshot_path, db_source, db_path, ...) VALUES (?, ?, ?, ?, ...)
```

3. **`/api/health.opsAudit` — incluir `db_source` no breakdown:**
```json
{
  "opsAudit": {
    "byDbSource": {
      "main": { "success": 3, "crashed": 0 },
      "atlas": { "success": 7, "crashed": 0 },
      "boris": { "success": 7, "crashed": 0 },
      "...": "..."
    }
  }
}
```

**Esforço:** ~2h (migration + code + tests + health endpoint)
**Risco:** Médio — migration em prod requer cuidado (regra crítica #6: snapshot pré-op). Mas migration é additive (ADD COLUMN), rollback trivial.

**Pergunta pro Forge:**
- Q6: Tem preferência pelo nome das colunas? `db_source` + `db_path` ou `target_db` + `target_path`?
- Q7: Migration v.17 quebra alguma invariante atual? (i.e., há código que assume schema fixo de ops_audit?)
- Q8: Backfill: marcar rows antigas como `'unknown'` ou tentar inferir do snapshot_path retroativamente (regex sobre filename)?

---

### Gap D — OCR-batch-cloud orchestrator sem timeout

**Problema:** `ocr-engine-stub.ts` tem timeouts internos (5min conversion, 2min/page, 15-30s outros). Mas o **orchestrator pai** (`ocr-batch.ts` / processo wrapper) não tem hard timeout. Resultado: 2 zombies reais nos últimos 14d com erro `reaped: process died before completing (>6h, pid not alive)`.

**Impacto:** ocupa slot de execução; ops_audit fica em estado terminal-mas-confuso (`crashed` por reaper, não por erro real). Não há perda de dados (OCR é idempotente, retry recupera).

**Fix proposto:** 3 camadas defensivas:

1. **Hard timeout no orchestrator:**
```typescript
// ocr-batch.ts — wrapper com timeout total
const HARD_TIMEOUT_MS = 4 * 60 * 60 * 1000; // 4h
const timeoutId = setTimeout(() => {
  console.error('[ocr-batch] hard timeout 4h reached, terminating');
  process.exit(124); // standard timeout exit code
}, HARD_TIMEOUT_MS);
// ... orchestrator logic ...
clearTimeout(timeoutId);
```

2. **Heartbeat write no ops_audit a cada 5min:**
```typescript
// dentro do orchestrator loop
const heartbeatId = setInterval(() => {
  db.prepare('UPDATE ops_audit SET notes = ? WHERE id = ?')
    .run(`heartbeat: ${processed}/${total} (${pct}%)`, opId);
}, 5 * 60 * 1000);
```

3. **Watchdog cron `*/15min`:**
```bash
# /root/.openclaw/scripts/ocr-watchdog.sh
# Mata qualquer ocr-batch-cloud em ops_audit com status='running'
# E sem heartbeat há >20min
```

**Esforço:** ~1.5h (3 mudanças + tests)
**Risco:** Médio — heartbeat UPDATE em ops_audit. Trigger `trg_ops_audit_terminal_immutable` permite UPDATE em status='running' (não terminal), confirmar.

**Pergunta pro Forge:**
- Q9: 4h hard timeout é seguro pro batch maior conhecido? Largest batch histórico foi quantas horas?
- Q10: Heartbeat via `notes` column ou criar coluna dedicada `last_heartbeat_at`?
- Q11: Watchdog cron `*/15min` ou prefere fazer parte do canary `*/15min` existente?

---

## 4. Prioridade ordenada

| # | Gap | Criticality | Esforço | Risco | Quando |
|---|---|---|---|---|---|
| 1 | **B (naming)** | Médio | 30min | Baixo-médio | **Primeiro** — barato, alta utilidade operacional |
| 2 | **A (snapshot diário main)** | Médio-alto | 30min | Baixo | **Segundo** — protege main DB contra gap de 7d |
| 3 | **D (ocr timeout)** | Médio | 1.5h | Médio | Terceiro — estabilidade OCR |
| 4 | **C (visibilidade)** | Médio | 2h | Médio | Último — refactor maior, prep schema v.17 |

**Total esforço:** ~4.5h spread over 1-2 dias.

---

## 5. Plano de execução proposto

### Fase 0 — Forge review (este doc)
**Output:** Forge responde Q1-Q11 + sugere ajustes.

### Fase 1 — Gap B (naming)
1. Edit `op-audit.ts` linha 118 (derive `dbSource`)
2. Edit `prune-pre-op-snapshots.sh` (regex update se necessário — Q5)
3. Tests: rodar reindex manual em 1 agent + verificar filename novo
4. Deploy: `npm run build` + reload services
5. **Checkpoint:** Forge confirma snapshots novos têm naming correto

### Fase 2 — Gap A (snapshot diário main)
1. Criar `/root/.openclaw/scripts/snapshot-main-db.sh`
2. Adicionar cron `0 3 * * *`
3. Dry run manual primeiro (`bash snapshot-main-db.sh`)
4. Verificar disk impact em 3 dias
5. **Checkpoint:** Forge valida snapshot é restorable via `safeRestore()`

### Fase 3 — Gap D (ocr timeout)
1. Edit `ocr-batch.ts` (timeout + heartbeat)
2. Criar `ocr-watchdog.sh`
3. Adicionar cron `*/15 * * * *`
4. Test: rodar OCR batch curto + force timeout + verificar exit code
5. **Checkpoint:** Forge confirma zombie patern não recorre por 7d

### Fase 4 — Gap C (visibilidade)
1. Schema migration v.17 (`scripts/migrate-v17-ops-audit-db-source.sql`)
2. **PRÉ-MIGRATION:** snapshot atômico via `withOpAudit('schema-v17-ops-audit')` 
3. Edit `op-audit.ts` (popular `db_source`, `db_path`)
4. Edit health endpoint (`/api/health` adicionar `opsAudit.byDbSource`)
5. Backfill rows antigas
6. **Checkpoint:** Forge valida health endpoint + ops_audit estrutura

---

## 6. Critérios de Done

### Gap B done
- [ ] Snapshot novo tem formato `<opName>-<dbSource>-<ts>-<pid>-<uid>.db`
- [ ] `prune-pre-op-snapshots.sh` ainda funciona (não deleta snapshots fora de retention)
- [ ] Snapshot antigo (sem dbSource) continua válido pra recovery
- [ ] 27/27 tests pass

### Gap A done
- [ ] Cron `0 3 * * *` cria snapshot diário
- [ ] Snapshot tem ~1.2GB, contém todas tabelas, integrity_check OK
- [ ] Retention 7d funciona (`find -mtime +7 -delete`)
- [ ] Disk não ultrapassa 50% após 7d de snapshots acumulados
- [ ] `safeRestore()` consegue restaurar de daily-main snapshot

### Gap D done
- [ ] ocr-batch-cloud com timeout 4h não cria zombie em test deliberado
- [ ] Heartbeat aparece em `ops_audit.notes` a cada 5min
- [ ] Watchdog mata processo sem heartbeat há >20min
- [ ] 0 zombies em 14d pós-deploy

### Gap C done
- [ ] Migration v.17 aplicada, schema match meta+PRAGMA
- [ ] `ops_audit.db_source` populado em novas rows
- [ ] `/api/health.opsAudit.byDbSource` retorna breakdown por agent + main
- [ ] Backfill rows antigas concluído
- [ ] 27/27 tests pass

---

## 7. Perguntas explícitas pro Forge (resumo Q1-Q11)

| # | Pergunta | Gap |
|---|---|---|
| Q1 | VACUUM INTO via sqlite3 CLI consegue copiar `vec_chunks_*` (requer extension)? | A |
| Q2 | Daily snapshot ~1.2GB × 7d = 8.5GB OK? Ou retention menor / gzip? | A |
| Q3 | `NOX_DB_PATH` env reflete DB ativo no snapshot, ou getDb() outro path? | B |
| Q4 | Heurística pra `dbSource`: basename, parse explícito, ou env var dedicada? | B |
| Q5 | `prune-pre-op-snapshots.sh` regex precisa update? | B |
| Q6 | Naming colunas: `db_source`+`db_path` ou `target_db`+`target_path`? | C |
| Q7 | Migration v.17 quebra invariantes? Há código que assume schema ops_audit fixo? | C |
| Q8 | Backfill rows antigas: `'unknown'` ou inferir do snapshot_path? | C |
| Q9 | 4h hard timeout OCR seguro? Maior batch histórico foi quantas horas? | D |
| Q10 | Heartbeat via `notes` column ou criar `last_heartbeat_at`? | D |
| Q11 | Watchdog próprio cron ou integrar ao canary `*/15min` existente? | D |

**Bonus question:** algum gap que eu missed na investigação? Outro alerta operacional que vale tratar junto?

---

## 8. Quem executa o quê

| Quem | O quê |
|---|---|
| **Forge** (review) | Responder Q1-Q11 + sugerir ajustes no plano até **16/05 18:00 BRT** |
| **Maestro** (impl) | Implementar Fases 1-4 após Forge sign-off, com checkpoint após cada fase |
| **Toto** (oversight) | Aprovar Fases após Forge checkpoint OK, decidir se prosseguir |

---

## 9. Cross-references

- Sistema canonical: `docs/HANDOFF.md` (estado), `docs/ROADMAP.md` (sprint pós-R03 — E14)
- Regras críticas: `CLAUDE.md` §regra #6 (op destrutiva só com snapshot atômico)
- Op-audit owner: Forge (escreveu em 25-26/04, ver `docs/DECISIONS.md` §A1)
- Audits relevantes: `audits/2026-04-26-W2-cleanup.md` (W2-1 trigger immutable, W2-2 dbpath validation)

---

*Doc preparado por Maestro 2026-05-15. Aguardando Forge review antes da implementação.*
