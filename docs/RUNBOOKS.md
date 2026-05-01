# nox-mem — Incident Runbooks

> **Última atualização:** 2026-05-01 — split memoria/plataforma
> **Maintainer:** Toto (bus factor = 1)
> **Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings
>
> ⚠️ **Runbooks de plataforma OpenClaw** (gateway down, monkey-patch invalidado, OpenClaw upgrade quebrou, claude-cli auth flap, disk space, graph-memory probe, heartbeat queue) migraram pra `~/Claude/Projetos/openclaw-vps/infra/runbooks/`. Versão mestra pré-split em `_archive-pre-split-20260501/RUNBOOKS.md.bak`.

## Índice rápido por sintoma (memoria-only)

| Sintoma | Runbook |
|---------|---------|
| `vectorCoverage <95%` ou embedding congelado | [RB-02](#rb-02-vector-coverage-drop-p1) |
| Alerta Discord `[schema-invariants]` | [RB-03](#rb-03-schema-invariants-violation-p1) |
| Search retorna lixo após ativação de salience | [RB-04](#rb-04-salience-activation-degradou-ranking-p0) |
| Recovery via snapshot `op_audit` | [`runbooks/recovery-from-snapshot.md`](../runbooks/recovery-from-snapshot.md) |
| Rollback de versão nox-mem | [`runbooks/rollback-nox-mem-version.md`](../runbooks/rollback-nox-mem-version.md) |
| Rollback de schema migration | [`runbooks/rollback-schema-migration.md`](../runbooks/rollback-schema-migration.md) |

> Runbooks plataforma (RB-01 gateway, RB-05 claude-cli, RB-06 monkey-patch, RB-07 OpenClaw upgrade, RB-08 disk, RB-09 graph-memory, RB-10 heartbeat, RB-11 upgrade) → `openclaw-vps/infra/runbooks/RUNBOOKS-master-pre-split.md`.

---

## RB-02: Vector coverage drop (P1)

**Severity:** P1 — search degradado (FTS-only, sem semântico), briefings incompletos
**Tempo médio resolução:** 5-20min (depende de volume a embedar)
**Última ocorrência:** 2026-04-27 (session-distill travou 8h, 11k chunks sem embedding)

### Sintoma

- Morning report mostra `vectorCoverage: X/Y embedded` com gap >5%
- `/api/health` retorna `embedded < total - 100`
- Busca semântica retorna resultados ruins ou `match_type: "fts"` em todos os resultados
- Canário `*/30min` falha (`Canary: FAIL` no Discord)

### Diagnóstico inicial (read-only)

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{embedded: .vectorCoverage.embedded, total: .vectorCoverage.total, orphans: .vectorCoverage.orphans}"'
# Checar se nightly travou (lock preso)
ssh root@100.87.8.44 'ls -la /tmp/nox-maintenance.lock 2>/dev/null && echo "LOCK ATIVO" || echo "lock ok"'
# Checar se session-distill ou outro step está pendurado
ssh root@100.87.8.44 'ps aux | grep -E "nox-mem|session-distill" | grep -v grep'
ssh root@100.87.8.44 'tail -20 /var/log/nox-maintenance.log'
```

### Decision tree

```
Lock /tmp/nox-maintenance.lock existe + ps mostra session-distill rodando há horas?
  → SIM: matar session-distill + liberar lock → rodar vectorize manual

Lock existe mas processo morreu (orphan lock)?
  → SIM: só remover lock → nightly vai funcionar no próximo run

embedded congelado (não cresceu em 24h) mas sem lock + sem nightly ativo?
  → Checar env vars: `env | grep GEMINI` deve retornar GEMINI_API_KEY
  → Se vazio: source env ausente (ver Mitigação)

Orphans > 0?
  → Trigger cascade ausente ou inconsistência: checar RB-03 (schema invariants)
```

### Mitigação

```bash
# Se session-distill pendurado (kill + liberar lock):
ssh root@100.87.8.44 'pids=$(ps aux | grep "session-distill\|nox-maintenance" | grep -v grep | awk "{print \$2}"); kill $pids 2>/dev/null; rm -f /tmp/nox-maintenance.lock; echo "Limpo"'

# Rodar vectorize manual (SEMPRE com env source):
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem vectorize 2>&1 | tail -5'

# Se vectorize falha silenciosamente (Done: 0 embedded, N errors):
# Validar chave Gemini antes de tudo:
ssh root@100.87.8.44 'grep GEMINI_API_KEY /root/.openclaw/.env | head -1'
# Se vazia ou chave revogada: atualizar .env com chave nova → restart nox-mem-api
ssh root@100.87.8.44 'systemctl restart nox-mem-api nox-mem-watcher'
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem vectorize 2>&1 | tail -5'
```

### Pós-fix verificação

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{embedded: .vectorCoverage.embedded, total: .vectorCoverage.total}"'
# Esperado: embedded == total (ou gap < 50 — recém-ingestados)

# Canário manual:
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem search "nox-mem sistema de memória" --hybrid 2>&1 | head -5'
# Esperado: match_type incluindo "semantic"
```

### Prevenção

- Nightly `nightly-maintenance.sh` agora tem `timeout 1800` em session-distill (fix 2026-04-27)
- Filtro HEARTBEAT em `src/session-distill.ts` cobre user + assistant (fix 2026-04-27) — reduz O(N²)
- Morning report deve incluir campo "última nightly: duração + phases OK" (backlog item)
- Poda de checkpoints velhos (mtime>14d): rodar manualmente se checkpoints crescerem novamente

---

## RB-03: Schema invariants violation (P1)

**Severity:** P1 — dados corrompidos, entity sections perdidas, retries/prune funcionando errado
**Tempo médio resolução:** 5-30min (depende de qual invariante quebrou)
**Última ocorrência:** 2026-04-25 (section/retention wipe via reindex, 183 entities afetadas)

### Sintoma

- Alerta Discord `[schema-invariants]` (canary `*/15min` em `/var/log/nox-schema-invariants.log`)
- `/api/health.sectionDistribution.compiled` < 183
- `retention.never_decay` abaixo de 92
- Chunks de entity files retornando sem `section` em search results

### Diagnóstico inicial (read-only)

```bash
ssh root@100.87.8.44 'tail -10 /var/log/nox-schema-invariants.log'
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{section: .sectionDistribution, retention: .retention, total: .chunks.total}"'
# Checar se reindex rodou recentemente:
ssh root@100.87.8.44 'journalctl -u nox-mem-watcher --since "1 hour ago" --no-pager | grep -i "reindex\|ingest" | tail -20'
ssh root@100.87.8.44 'openclaw cron list 2>/dev/null | grep -i reindex'
```

### Decision tree

```
compiled == 0 (ou muito abaixo de 183)?
  → reindex rodou com ingestFile() genérico (não ingestEntityFile)
  → Checar se ingest-router está ativo: `grep routeIngest /root/.openclaw/workspace/tools/nox-mem/dist/lib/ingest-router.js | wc -l`
  → Se 0: build pode estar desatualizado → rebuild + reingest entities

never_decay muito abaixo de 92?
  → Chunks feedback/person foram recriados sem retention override
  → Checar cron end-of-day: `openclaw cron list | grep ee15b430`
  → Se step ainda for "reindex": mudar pra "consolidate" (ver Fix #2 do incident 2026-04-25)

ops_audit mostra op recente com status "failed" ou "running" há horas?
  → withOpAudit() não fechou corretamente → checar lifecycle do singleton DB
```

### Mitigação

```bash
# Reingestar todos os entity files (após confirmar que ingest-router está correto no build):
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  find /root/.openclaw/workspace/tools/nox-mem/memory/entities -name "*.md" | \
  while read f; do nox-mem ingest-entity "$f"; done 2>&1 | tail -10'

# Vectorizar os novos chunks:
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem vectorize 2>&1 | tail -5'

# Se cron end-of-day (ee15b430) ainda tem "reindex" no step 11:
ssh root@100.87.8.44 'openclaw cron list | grep ee15b430'
```

### Pós-fix verificação

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{compiled: .sectionDistribution.compiled, never_decay: .retention.never_decay}"'
# Esperado: compiled=183, never_decay>=92

ssh root@100.87.8.44 'tail -3 /var/log/nox-schema-invariants.log'
# Esperado: "All invariants OK" no próximo ciclo de 15min
```

### Prevenção

- Canary `*/15min` em `/etc/cron.d/nox-invariants` (já ativo)
- Guard em `ingestFile()` garante routing entity files → `ingestEntityFile()` automaticamente
- Cron end-of-day mudado de `reindex` → `consolidate` (fix 2026-04-25, confirmar ativo)
- Antes de qualquer reindex manual: `nox-mem reindex --dry-run` primeiro, validar output

---

## RB-04: Salience activation degradou ranking (P0)

**Severity:** P0 — search retorna resultados errados, briefings corrompidos com lixo de alta dor
**Tempo médio resolução:** 2min (rollback é instantâneo)
**Última ocorrência:** Ainda não ocorreu em prod (shadow-mode ativo; gate 2026-04-30)

### Sintoma

- Após rodar `activate-salience.sh --apply` ou setar `NOX_SALIENCE_MODE=active`
- Resultados de search claramente piores (chunks triviais no top, conteúdo importante enterrado)
- `/api/health.salience.mode` mostra `active` mas promote/archive stats parecem incoerentes
- Usuário reporta "memórias erradas" nas respostas dos agents

### Diagnóstico inicial (read-only)

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{salience: .salience, searchTelemetry: .searchTelemetry}"'
# Verificar quando foi ativado:
ssh root@100.87.8.44 'journalctl -u nox-mem-api --since "30 min ago" --no-pager | grep -i "salience\|NOX_SALIENCE" | tail -20'
# Baseline shadow antes da ativação (para comparação):
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq ".salience.stats"'
```

### Decision tree

```
NOX_SALIENCE_MODE está como "active" no env?
  → SIM: rollback imediato pra "shadow" (ver Mitigação)

NOX_SALIENCE_MODE está "shadow" mas ranking ainda ruim?
  → Outro fator causando degradação (boost stacking? section_boost ativado errado?)
  → Checar NOX_SECTION_BOOST_MODE no env
  → Checar se houve commit recente em search.ts com boost multiplicativo

Stats mostram archive_candidates absurdamente alto (ex: >50% do corpus)?
  → Formula errada — pain/recency mal calibrado
  → Shadow rollback + análise antes de reativar
```

### Mitigação

```bash
# Rollback salience para shadow-mode (IMEDIATO):
ssh root@100.87.8.44 'grep -n "NOX_SALIENCE_MODE" /root/.openclaw/.env'
# Editar .env: NOX_SALIENCE_MODE=shadow
ssh root@100.87.8.44 "sed -i 's/^NOX_SALIENCE_MODE=active/NOX_SALIENCE_MODE=shadow/' /root/.openclaw/.env"
ssh root@100.87.8.44 'systemctl restart nox-mem-api && sleep 3 && curl -s http://127.0.0.1:18802/api/health | jq .salience.mode'
# Esperado: "shadow"

# Se section_boost também foi ativado:
ssh root@100.87.8.44 "sed -i 's/^NOX_SECTION_BOOST_MODE=active/NOX_SECTION_BOOST_MODE=shadow/' /root/.openclaw/.env"
ssh root@100.87.8.44 'systemctl restart nox-mem-api'
```

### Pós-fix verificação

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq ".salience.mode"'
# Esperado: "shadow"

# Teste de sanidade de ranking (query de referência conhecida):
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  nox-mem search "memoria semantica nox" --limit 3 2>&1'
# Esperado: resultado relevante no top 3
```

### Prevenção

- Nunca ativar salience sem ≥7 dias de shadow baseline documentado
- Gate `activate-salience.sh check` DEVE retornar "READY" antes de `--apply`
- Ranking changes SEMPRE em commit separado com prefix `tune(search):` ou `feat(search):`
- Boost multiplicativo empilhável é proibido — usar aditivo (lição do incident v3.4)
- Manter rollback via env var (não hardcode) para reversão em <2min
