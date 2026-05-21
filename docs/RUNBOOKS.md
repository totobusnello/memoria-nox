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
| Gemini API down/quota exhausted/key revoked (SPOF embedding) | [RB-05](#rb-05-gemini-spof-mitigation-p0) |
| Q-pillar full-run trigger (LoCoMo + LongMemEval + Latency) | [RB-06](#rb-06-q-pillar-full-runs-locomo--longmemeval--latency--trigger-overnight) |
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

---

## RB-05: Gemini SPOF mitigation (P0)

> **F12 deliverable** — playbook para quando Gemini API (embedding source-of-truth) fica indisponível por motivos diversos: quota exhausted, key revoked, API outage, deprecation shutdown, custo explosivo, etc.

### Diagnóstico

```bash
# 1. Confirmar que Gemini é o problema (não rede/DNS local):
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  curl -s -w "\nHTTP %{http_code}\n" \
  "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key=${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"content\":{\"parts\":[{\"text\":\"healthcheck\"}]}}" | tail -5'
# Esperado: HTTP 200 + embedding values
# Sintomas problemáticos:
#   HTTP 401 → key revogada (rotacionar ou pegar nova)
#   HTTP 429 → quota stoured (esperar reset 24h ou upgrade plano)
#   HTTP 503 → outage Google (https://status.cloud.google.com)
#   HTTP 400 com "model deprecated" → migrar pra modelo novo
#   timeout/no response → DNS/rede VPS local

# 2. Estado atual do nox-mem:
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  vectorCoverage,
  embeddingSource: .embeddings.provider,
  lastEmbed: .embeddings.last_success
}"'
# Esperado: vectorCoverage.embedded == total. Se embedding está parado: gap crescente.
```

### Severidade & impacto

| Cenário | Impacto imediato | Latência tolerável |
|---|---|---|
| Outage <1h Google | search hybrid degrada para FTS-only via fallback automático | 1-2h sem ação |
| Outage >1h ou quota exhausted | gap chunks novos não-vetorizados acumula; recovery via batch retry | 24h sem ação |
| Key revoked / billing issue | search semantic 100% off, novos ingests sem vetor | 4h pra rotacionar key + canary recovery |
| Modelo deprecated / shutdown | reembed massivo necessário (62k+ chunks, ~3-6h batch) | 7d pre-shutdown ideal |

### Mitigação Tier 1 — fallback automático (ATIVO)

`src/search.ts` já tem fallback FTS-only quando Gemini API falha:
- Erro do call semantic → marca `match_type: "fts-only-fallback"` em search_telemetry
- RRF degrada graciosamente sem semantic candidates
- Canary `*/30min` em `match_type:"semantic"` alerta Discord se zero hits >2h

### Mitigação Tier 2 — switch provedor (degradação aceitável)

Quando outage >2h ou key issue, switch para provedor alternativo. **Pré-requisitos** (preparados antecipadamente, não improvisado durante incident):

#### Provedor A — Voyage AI (`voyage-3`, 1024d)

```bash
# 1. Subscribir conta + obter VOYAGE_API_KEY (uma única vez, fora de incident)
# 2. Manter VOYAGE_API_KEY em /root/.openclaw/.env (commented out até precisar)
# 3. Em incident:
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  curl -s https://api.voyageai.com/v1/embeddings \
  -H "Authorization: Bearer ${VOYAGE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"input\":[\"healthcheck\"],\"model\":\"voyage-3\"}" | jq ".data[0].embedding | length"'
# Esperado: 1024
```

**Mismatch dimensional:** Voyage 1024d vs Gemini 3072d. Não pode usar `vec_chunks` existente. Solução em incident:
- Criar `vec_chunks_voyage` paralelo com `dim=1024`
- `src/embedding.ts` switch via `NOX_EMBEDDING_PROVIDER=voyage` env
- Search consulta TABELA correspondente baseado no provider ativo
- Cobertura inicial 0% → reembed batch durante outage Gemini ou aceitar partial coverage

#### Provedor B — OpenAI (`text-embedding-3-large`, 3072d) — match dimensional ✅

```bash
# Match exato com Gemini 3072d → pode reusar vec_chunks
# Custo: $0.13/1M tokens (similar Gemini)
# 1. Manter OPENAI_API_KEY em /root/.openclaw/.env (commented out até precisar)
# 2. Em incident:
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  curl -s https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"input\":\"healthcheck\",\"model\":\"text-embedding-3-large\"}" | jq ".data[0].embedding | length"'
# Esperado: 3072

# 3. Switch via env var:
ssh root@100.87.8.44 'sed -i "s/^NOX_EMBEDDING_PROVIDER=gemini/NOX_EMBEDDING_PROVIDER=openai/" /root/.openclaw/.env'
ssh root@100.87.8.44 'systemctl restart nox-mem-api nox-mem-watcher'
```

**Caveat:** vetores Gemini-existing podem ter distribuição diferente de OpenAI-new — recall pode degradar até batch reembed completo. Aceitar 7-14d de degradação ou forçar reembed.

### Mitigação Tier 3 — shadow-index trimestral (PROATIVO, recommended)

Para evitar improvisar em incident, manter shadow-index permanente:

```bash
# Cron trimestral: roda 50 chunks pelo provider alternativo, calcula nDCG comparativo
# Resultado em /var/log/nox-embedding-shadow-quarterly.log
# Schedule:
echo "0 3 1 1,4,7,10 * /root/.openclaw/scripts/embedding-shadow-quarterly.sh" >> /etc/cron.d/nox-mem
```

**Script `embedding-shadow-quarterly.sh`** (criar como follow-up F12 task):
- Lê 50 golden queries de R01b
- Para cada, embed com Gemini + Voyage + OpenAI separadamente
- Roda search com cada vector + computa Recall@10 contra expected_chunk_ids
- Output JSON: `{quarter: "2026Q1", gemini: 0.62, voyage: 0.58, openai: 0.61}`
- Discord alert se ranking trocar (ex: Voyage de 0.58 sobe pra 0.65 sugere migração ativa)

### Recovery: reembed massivo após switch

Quando trocar provedor permanentemente:

```bash
# 1. Backup pre-reembed (op-audit não cobre embedding-only ops)
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "VACUUM INTO /var/backups/nox-mem/pre-reembed-$(date +%Y%m%d-%H%M%S).db"'

# 2. Reembed em chunks de 1k via tmux background:
ssh root@100.87.8.44 'tmux new-session -d -s reembed-batch \
  "set -a; source /root/.openclaw/.env; set +a; \
   nox-mem vectorize --batch-size=100 --provider=${NOX_EMBEDDING_PROVIDER} 2>&1 \
   | tee /tmp/reembed-batch.log"'

# 3. Monitor:
ssh root@100.87.8.44 'tail -f /tmp/reembed-batch.log'
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage'

# 4. Rate budget: 62.000 chunks ÷ ~50/min = ~21h. Spread overnight ou usar batch=500 se rate-limit permitir.
```

### Pós-fix verificação

```bash
# Health geral
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  embeddingProvider: .embeddings.provider,
  vectorCoverage,
  recentEmbedSuccess: .embeddings.last_success
}"'

# Search smoke test (deve retornar resultados, semantic ativo)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; \
  nox-mem search "test query reasonably specific" --hybrid 2>&1 | head -5'
```

### Prevenção

- **VOYAGE_API_KEY + OPENAI_API_KEY pre-cadastradas** no `.env` (commented out, prontas pra activate)
- **Cron shadow-index trimestral** roda 50 queries pelos 3 provedores → trend de qualidade
- **Discord alert** quando `match_type:"fts-only-fallback"` >50/h por >2h consecutivas (canary nova)
- **Documentar custo mensal Gemini** em F13 (cost projection alt) — gatilho pra switch se ROI inverter
- **Nunca depender de UM único modelo Gemini** — usar `gemini-2.5-flash-lite` default (não flash full que estoura quota)
- **Manter `gemini-embedding-001` como source-of-truth dimensional** (3072d) até shadow-index trimestral mostrar alternativa superior em ≥2 trimestres consecutivos

---

## RB-06: Q-pillar full runs (LoCoMo + LongMemEval + Latency) — trigger overnight

> **Quando rodar:** quando precisar de números padrão-indústria pra Q4 COMPARISON.md (atualmente todos os números no doc são `[estimated]` — Q4 gate fecha quando ≥2 dos 3 saem `[verified]`). Roda **na VPS** (tem `eval.db` seedado + GEMINI_API_KEY válido).

### Sintoma / Pre-check

```bash
# Cada harness tem read-side: deve retornar PASS na shape check ou indicar corpus absent
gh run list --workflow=eval-harnesses.yml --limit 1
# Last run deve estar success (CI valida shape, não números)
```

### Quick fix

```bash
# Pré-req VPS:
ssh root@187.77.234.79
set -a; source /root/.openclaw/.env; set +a
cd /root/.openclaw/workspace/tools/nox-mem

# Q1 — LoCoMo (n=100, ~2h, ~$0.40)
npx tsx eval/locomo/download.ts                                # primeiro time só
npx tsx eval/locomo/parser.ts --ingest                         # popula eval.db
nohup npx tsx eval/locomo/run.ts --n 100 --seed 42 --cli --full \
  > eval/locomo/full-run-$(date +%Y%m%d).json 2> eval/locomo/full-run-$(date +%Y%m%d).err &
# Quando completar:
npx tsx eval/locomo/score.ts eval/locomo/full-run-YYYYMMDD.json --ci
# Esperado: nDCG@10, R@5, R@1, MRR — todos com CIs

# Q2 — LongMemEval (n=100, ~2-3h, ~$0.50 com LLM judge)
npx tsx eval/longmemeval/download.ts
nohup npx tsx eval/longmemeval/run.ts --n 100 --full \
  > eval/longmemeval/full-run-$(date +%Y%m%d).json 2> eval/longmemeval/full-run-$(date +%Y%m%d).err &
# Quando completar:
npx tsx eval/longmemeval/score.ts eval/longmemeval/full-run-YYYYMMDD.json

# Q3 — Latency benchmark (~1h, ~$0.23 — só embedding cost, no LLM judge)
cd eval/latency && npm run build
nohup node dist/run.js --full \
  > full-run-$(date +%Y%m%d).json 2> full-run-$(date +%Y%m%d).err &
# Resultados em full-run-YYYYMMDD.json — p50, p95, p99 por endpoint
```

### Tempo total estimado

- **Serial (default):** ~5-6h. Pode rodar todos no mesmo tmux session em sequência (preserva embedding cache do Gemini entre Q1 e Q2 → economia ~30%).
- **Paralelo:** não recomendado — Gemini quota 3M req/d em flash-lite, todos os 3 batem o mesmo endpoint, risco de 429.

### Custo total estimado

- Q1: ~$0.40 (embedding novos pra ~600 turns + 100 queries)
- Q2: ~$0.50 (embedding + LLM judge gemini-2.5-flash pra evaluating answers)
- Q3: ~$0.23 (só embedding 100 queries × N variations)
- **Total: ~$1.13** (cobrável ao GEMINI_API_KEY do Toto, projeto pessoal)

### Pós-run: atualizar COMPARISON.md

```bash
# Editar docs/COMPARISON.md, trocar números [estimated] → [verified YYYY-MM-DD]
# para cada métrica que saiu da Q-run. Manter [estimated] no resto.
# Disparar Q4 gate se ≥2 vitórias claras.
```

### Verificação pós-run

```bash
# Validar JSON outputs não vazios e com shape correto:
for f in eval/locomo/full-run-*.json eval/longmemeval/full-run-*.json eval/latency/full-run-*.json; do
  [ -f "$f" ] || continue
  node -e "const d=JSON.parse(require('fs').readFileSync('$f','utf8')); console.log('$f:', d.meta?.n, 'records:', d.records?.length)"
done

# Cross-check: VPS health pós-run não regrediu
curl -sf http://127.0.0.1:18802/api/health | jq '.vectorCoverage'
```

### Prevenção

- **GEMINI_API_KEY rotation:** verificar válido ANTES de iniciar (`nox-mem search "test" 2>&1 | tail -5`). Q-run de 2h falhando 20% por API key expirada custa tempo.
- **Snapshot pré-run:** `withOpAudit` não cobre eval.db (DB separado), mas tirar `VACUUM INTO snapshot.db` manual antes de Q1 caso algo corrompa eval.db.
- **Tmux session named:** `tmux new -s qruns` — sobrevive a disconnect SSH.
- **Discord alert no final:** wrapper script pode disparar webhook quando os 3 terminam (próxima evolução).

### Cross-links

- `eval/locomo/README.md` — Q1 detalhes + 7 decisões de protocolo (D1-D7)
- `eval/longmemeval/README.md` — Q2 detalhes
- `eval/latency/README.md` — Q3 detalhes + budgets p95
- `docs/COMPARISON.md` — onde os números aterrissam
- `docs/ROADMAP.md §Q-pillar` — gates Q4 abrir

---

## RB-07: Multi-agent branch leak recovery (P2 — usually defense-only)

### Sintoma

Você fez `git commit` no main session e:

- **Hook abortou:** message `❌ pre-commit ABORT — parent repo path on branch '<X>' (not main/master)` — defense funcionou
- **OU `git push` deu erro** sobre branch upstream OR `git log` mostra commits em branch que não era a current

Memory: `[[multi-agent-branch-checkout-race]]` documenta root cause. Memory `[[pre-commit-hook-blocks-non-main-commits]]` documenta defense.

### Diagnóstico inicial (read-only)

```bash
# Quem está atualmente checked out em main path?
cd /Users/lab/Claude/Projetos/memoria-nox && git branch --show-current
# Esperado: main
# Se mostrar outro branch: contaminação confirmed

# Qual o último commit + onde está?
git log --oneline -5
git branch -a --contains HEAD

# Worktrees ativos
git worktree list
```

### Decision tree

| Caso | Action |
|---|---|
| Hook abortou + você ainda não commitou | Stash + checkout main + stash pop + retry commit |
| Já commitou em branch errado (sem push) | Cherry-pick to main, delete leak branch |
| Já fez `git push` no branch errado | Cherry-pick to main, push main, deletar branch local + remote |
| Múltiplos commits perdidos em branch errado | `git log <leak-branch>` para encontrar SHAs, cherry-pick na ordem |

### Mitigação — Padrão A (commit em curso bloqueado pelo hook)

```bash
git stash                       # preserve work in progress
git checkout main
git stash pop                   # work returns to main working tree
git status                      # verify clean expected files
git add <files-to-commit>
git commit -m "msg"             # passes hook agora
git push
```

### Mitigação — Padrão B (commit já feito em branch errado, ainda local)

```bash
LEAK_BRANCH=$(git branch --show-current)
LEAK_SHA=$(git rev-parse HEAD)
echo "Leak branch: $LEAK_BRANCH, SHA: $LEAK_SHA"

git checkout main
git pull --ff-only              # sync com remote
git cherry-pick $LEAK_SHA       # recovery
git push origin main
git branch -D $LEAK_BRANCH      # cleanup local
```

### Mitigação — Padrão C (já push em branch errado)

```bash
git push origin --delete <leak-branch> 2>&1 || echo "branch já não existe no remote"
```

### Pós-fix verificação

```bash
git branch --show-current       # Esperado: main
git log --oneline -3 | head -3
git status
gh pr list --state open
```

### Override legítimo (feature branch local intencional)

```bash
COMMIT_TO_NON_MAIN_OK=1 git commit -m "msg"
```

Hook respeita esse env var e libera o commit.

### Prevenção

- **`isolation: "worktree"` mandatory** em qualquer Agent spawn que toca git
- **Pre-commit hook em `~/.git-hooks-global/pre-commit`** — defense automático layer 2
- **Sanity check pré-commit:** `git branch --show-current` antes de `git add` em sessions multi-agent

### Cross-links

- Memory `[[multi-agent-branch-checkout-race]]` — root cause + 3 violations on 2026-05-21
- Memory `[[pre-commit-hook-blocks-non-main-commits]]` — defense layer specs
- `~/Claude/CLAUDE.md` HARD RULE section — multi-agent + git regulations
- `docs/INCIDENTS.md 2026-05-21` — primeira violation + hook install timeline

---

## RB-08: opsAudit metric anomaly (P3 — usually metric noise)

### Sintoma

`/api/health.opsAudit.total_24h` mostra número alto MAS `git log` + crons recentes parecem OK. Operação aparentemente "perdida".

### Diagnóstico inicial (read-only)

```bash
ssh root@<vps-ip> 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db <<SQL
SELECT typeof(started_at), status, COUNT(*) FROM ops_audit GROUP BY 1, 2;
SQL'
```

Se `typeof=text` rows aparecem → schema regrediu pra TEXT (post PR #193 não deveria acontecer)
Se rows com `db_source=unknown` ou `op_name LIKE 'test-%'` → test pollution voltou

### Decision tree

| Caso | Action |
|---|---|
| `typeof(started_at) = text` em alguma row | Schema regrediu — investigate ALTER TABLE ou DEFAULT changes |
| Test ops aparecendo em prod ops_audit | Test fixture sem `db_source='test'` setado — fix em test code |
| `total_24h` ≠ rows reais last 24h | Filter bug em `/api/health` query — check defensive CAST |
| `crashed_24h` alto | Investigar real crashed ops via `WHERE status='crashed' AND started_at > <24h ago>` |

### Mitigação

```bash
# Se schema TEXT voltou: re-aplicar migration de PR #193
ssh root@<vps-ip> 'bash /root/.openclaw/workspace/tools/nox-mem/scripts/migrate-opsaudit-started-at-2026-05-21.sh'

# Se test pollution: cleanup
ssh root@<vps-ip> 'bash /root/.openclaw/workspace/tools/nox-mem/scripts/cleanup-test-ops-audit-2026-05-21.sh'

ssh root@<vps-ip> 'curl -s http://127.0.0.1:18802/api/health | jq .opsAudit'
```

### Cross-links

- Memory `[[opsaudit-hygiene-deployed-2026-05-21]]` — original fix
- Memory `[[opsaudit-investigation-2026-05-21]]` — 3-issue root cause
- Memory `[[sqlite-text-affinity-coerces-int-back]]` — 4 SQLite gotchas during migration
- PR #193 — Issues #1+#3 deploy
- `docs/INCIDENTS.md 2026-05-21` — full incident timeline
