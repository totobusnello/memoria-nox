# DR Drill Quarterly (F14)

> **Última execução inicial:** 2026-05-01 21:01 BRT
> **Próxima execução:** 2026-08-01 (Q3 2026)
> **Owner:** Toto
> **Cross-ref:** `docs/RUNBOOKS.md#rb-05-gemini-spof-mitigation-p0` (F12), `docs/ROADMAP.md` F14 row

---

## Objetivo

Validar trimestralmente que:
1. Snapshots SQLite são **restauráveis** (não corrompidos em transit)
2. Schema/dados sobrevivem ao VACUUM INTO + restore round-trip
3. Tempo de recovery está dentro do RTO aceitável (definido como ≤30min)

Sem drill, descobrimos que o backup quebrou no momento do incident — pior cenário.

---

## Procedimento (10min)

### Step 1: snapshot fresco via VACUUM INTO

```bash
ssh root@100.87.8.44 '
  set -a; source /root/.openclaw/.env; set +a
  TS=$(date +%Y%m%d-%H%M%S)
  DRILL=/tmp/nox-mem-drill-$TS.db
  START=$(date +%s)
  sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "VACUUM INTO \"$DRILL\""
  echo "VACUUM duration: $(($(date +%s)-START))s"
  ls -lah $DRILL
'
```

**Esperado:** ~1-2s pra DB <2GB. Se >10s, investigar I/O bottleneck.

### Step 2: integrity check

```bash
ssh root@100.87.8.44 '
  DRILL=$(ls -t /tmp/nox-mem-drill-*.db | head -1)
  START=$(date +%s)
  RESULT=$(sqlite3 $DRILL "PRAGMA integrity_check;" | head -3)
  echo "integrity: $RESULT"
  echo "duration: $(($(date +%s)-START))s"
'
```

**Esperado:** `ok` em <5s. Qualquer outra resposta = SNAPSHOT CORROMPIDO, abortar drill + investigar storage layer.

### Step 3: schema + counts validation

```bash
ssh root@100.87.8.44 '
  DRILL=$(ls -t /tmp/nox-mem-drill-*.db | head -1)
  sqlite3 $DRILL "
    SELECT \"user_version\" AS k, user_version AS v FROM pragma_user_version;
    SELECT \"chunks\" AS k, COUNT(*) AS v FROM chunks;
    SELECT \"kg_entities\" AS k, COUNT(*) AS v FROM kg_entities;
    SELECT \"kg_relations\" AS k, COUNT(*) AS v FROM kg_relations;
    SELECT \"vec_chunks\" AS k, COUNT(*) AS v FROM vec_chunks;
  "
'
```

**Esperado:** valores próximos do prod atual. Validar contra `/api/health` da prod no momento.

### Step 4: invariants check (section + retention)

```bash
ssh root@100.87.8.44 '
  DRILL=$(ls -t /tmp/nox-mem-drill-*.db | head -1)
  sqlite3 $DRILL "
    SELECT section, COUNT(*) FROM chunks WHERE section IS NOT NULL GROUP BY section;
    SELECT COUNT(*) AS never_decay FROM chunks WHERE retention_days IS NULL;
  "
'
```

**Esperado:**
- `compiled|183`, `frontmatter|183`, `timeline|366` (entity files)
- `never_decay >= 92` (feedback/person memories)

Desvios sinalizam que prod já está em deriva (drill expõe issue ao invés de mascarar).

### Step 5: smoke search end-to-end (opcional, F14b futuro)

Atualmente bloqueado: `db.js:7` não honra `NOX_DB_PATH`, logo `nox-mem search` sempre aponta pra prod DB. Quando F14b for executado (após op-audit-e2e fix), drill incluirá:

```bash
# placeholder F14b futuro
ssh root@100.87.8.44 '
  DRILL=$(ls -t /tmp/nox-mem-drill-*.db | head -1)
  set -a; source /root/.openclaw/.env; set +a
  NOX_DB_PATH=$DRILL nox-mem search "nox-mem sistema memoria" --hybrid 2>&1 | head -5
'
# Esperado: 5 results, match_type include "semantic"
```

### Step 6: cleanup

```bash
ssh root@100.87.8.44 'rm -f /tmp/nox-mem-drill-*.db && echo "cleaned"'
```

---

## Resultado da execução inicial 2026-05-01

| Metric | Valor | Status |
|---|---|---|
| snapshot_size | 1.015 GB | OK (~prod) |
| VACUUM_duration | 1s | ✅ excelente (esperado ≤2s) |
| integrity_check | ok | ✅ |
| integrity_duration | 2s | ✅ |
| chunks | 62.927 | ≈ prod 62.923 |
| kg_entities | 402 | ✅ prod match |
| kg_relations | 544 | ✅ prod match |
| section.compiled | 183 | ✅ |
| section.frontmatter | 183 | ✅ |
| section.timeline | 366 | ✅ |
| never_decay | 11.686 | OK (≥92) |
| **user_version** | **0** | ⚠️ **BUG ACHADO** |

### ⚠️ Issue achado durante drill

**user_version = 0 na prod DB**, apesar de `chunks` ter colunas `retention_days`/`pain`/`section`/`section_boost` (schema v10 features completos). Schema migrations adicionam colunas mas **não bumpam `PRAGMA user_version`**.

**Implicações:**
1. F05 canary invariants não pode usar `user_version` como sentinel de migração
2. R01a spec proposed `PRAGMA user_version = 12` — vai funcionar como bump *único* em vez de sequencial
3. `safeRestore()` em `op-audit.ts` valida `schema_user_version` match — se prod=0 e snapshot=0, sempre passa (OK por enquanto, mas frágil)

**Ação proposta (não fixar agora — fora do escopo F14):**
- Adicionar migration `0011_bump_user_version.sql` que faz `PRAGMA user_version = 11` (declara estado atual)
- Atualizar regra invariants pra exigir `user_version >= 11`
- R01a impl bumpa pra 12 normalmente

Item adicionado ao backlog: registar em DECISIONS.md como observação técnica.

### RTO real medido

| Step | Duration |
|---|---|
| VACUUM INTO | 1s |
| integrity_check | 2s |
| schema query | <1s |
| invariants query | <1s |
| **Total** | **~5s pra validate snapshot** |

RTO recovery efetivo (restore + service start) ≈ 30s (mv + restart). Bem dentro do alvo ≤30min.

---

## Schedule cron (criar)

```bash
# /etc/cron.d/nox-mem-dr-drill (criar como F14b follow-up)
# Q1: Jan, Q2: Apr, Q3: Jul, Q4: Oct — 1ª segunda do mês 09:00 BRT
0 9 1 1,4,7,10 1 /root/.openclaw/scripts/dr-drill.sh
```

**Script `dr-drill.sh`** (criar como F14b deliverable):
- Wrap das steps 1-4 acima em script idempotente
- Output JSON pra `/var/log/nox-dr-drill-quarterly.log`
- Discord notify success/failure
- Auto-cleanup snapshot pós-drill
- **Falha em qualquer step = Discord alert P0** (snapshot quebrado é incident)

---

## Cross-reference

| Item | Onde |
|---|---|
| F12 Gemini SPOF | `docs/RUNBOOKS.md#rb-05-gemini-spof-mitigation-p0` |
| Schema invariants F05 | `docs/CLAUDE.md` regra 6 |
| safeRestore in op-audit | `src/lib/op-audit.ts` |
| Roadmap F14 | `docs/ROADMAP.md` Foundation table |
| R01a schema bump v12 | `specs/2026-04-27-R01a-eval-harness.md` |
