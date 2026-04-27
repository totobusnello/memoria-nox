# Session Log — Tier 0 + Tier 1 Memory Integrity Restoration

**Data:** 2026-04-18 (+ iteração 2026-04-19 07:25 — fixes pós-primeira execução do nightly)
**Duração:** ~3h + 30min follow-up
**Status final:** Sistema hiper-saudável. Primeira execução do nightly-maintenance trouxe 2 issues corrigidas: (1) ordem `session-distill → vectorize` invertida no script deixava 339 distilled chunks sem embedding; (2) threshold do morning-report disparava RED em drift normal de <10%. Ambos corrigidos e espelhados em `scripts/vps-mirror/`.

> **⚠️ Source of truth daqui em diante:** `plans/2026-04-19-unified-evolution-roadmap.md`
> Este session log documenta o que FOI FEITO hoje (Fase 0.5). O **plano unificado** é o que EXECUTAMOS.
> Também atualizamos a visão estratégica em `docs/nox-neural-memory.md` (v12 — corrigiu status falso sobre Layer 2).

---

## TL;DR (leia isso primeiro amanhã)

Hoje restauramos a camada semântica do nox-mem que estava silenciosamente quebrada há semanas (hybrid search era FTS-only disfarçado). Aplicamos 2 tiers de fixes reversíveis, criamos scripts de autodefesa, e deixamos um canário diário vigiando pra regressão não acontecer de novo.

**Próximo passo lógico amanhã:** rodar o checklist de verificação (seção "Checklist para amanhã"). Se tudo verde → avançar pro **Tier 3 (observability real)**. Se algo vermelho → restore backup e investigar.

---

## O que mudou hoje (resumo executivo)

### Tier 0 — Stop the bleeding (fixes reversíveis, zero risco)
1. `/root/.openclaw/scripts/health-probe.sh` agora lê `${NOX_API_PORT}` do `.env` em vez de hardcoded `18800` → elimina 288 restarts/dia causados por probe batendo em porta errada (Chrome remote-debugging squata :18800)
2. `src/db.ts` recebeu `_db.pragma("busy_timeout = 5000")` → elimina SQLITE_BUSY silencioso sob contention
3. `/api/health.vectorCoverage` agora usa INNER JOIN com `chunks` → para de mentir (antes reportava 6627 embeddings quando tinham 0 válidos)

### Tier 1 — Restaura integridade da camada semântica
4. DELETE dos 6,627 órfãos em `vec_chunk_map` + 2,587 unreferenced em `vec_chunks`
5. Trigger `trg_chunks_delete_cascade AFTER DELETE ON chunks` instalado → previne recorrência
6. `src/vectorize.ts` bug corrigido (consultava `vec_chunks.chunk_id` — coluna inexistente)
7. `src/embed.ts` ganhou `embedBatchAPI()` usando `batchEmbedContents` do Gemini → 3 → 26.4 chunks/s (9×)
8. Re-embed completo dos 1,951 chunks em **74 segundos, zero 429**

### Tier 4 — Índice preemptivo (5 min, não toca dados)
9. `CREATE INDEX idx_chunks_type_date ON chunks(chunk_type, source_date DESC)` → elimina TEMP B-TREE em queries type+recency

### Autodefesa + automação
10. `/root/.openclaw/scripts/semantic-canary.sh` + cron `0 6 * * *` — valida camada semantic diariamente, alerta Discord
11. `/root/.openclaw/scripts/morning-report.sh` + cron `30 6 * * *` — resumo dos 6 sinais no Discord (log em `/var/log/nox-morning.log`)
12. `~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh` (local no Mac) — 1 comando executa toda verificação via SSH

---

## Estado do sistema (snapshot 12:51 UTC-3)

```json
{
  "chunks": { "total": 1951 },
  "vectorCoverage": { "embedded": 1951, "total": 1951, "orphans": 0 },
  "knowledgeGraph": { "entities": 371, "relations": 500 },
  "reflectCache": { "entries": 13, "total_hits": 12 },
  "procedures": 0,
  "services": {
    "openclaw-gateway": true,
    "nox-mem-watcher": true,
    "nox-mem-api": true,
    "ollama": false,
    "tailscaled": true
  }
}
```

- **Restarts automáticos pós-fix:** 0 (em ~35 min de observação)
- **429 Gemini pós-re-embed:** 0 (em ~20 min)
- **Semantic canary:** 10/10 resultados com `match_type: "semantic"` em query natural
- **reflect_cache hit rate:** 92% (organicamente, sem calibração)

---

## Backups (para rollback em caso de incidente)

| Localização | Conteúdo | Uso |
|---|---|---|
| `/root/.openclaw/workspace/backups/tier0-20260418-121338/` | `health-probe.sh`, `db.ts`, `api-server.ts` + dist | Rollback do Tier 0 |
| `/root/.openclaw/workspace/backups/tier1-20260418-122336/` | `embed.ts`, `vectorize.ts` + dist | Rollback do Tier 1 |
| `/root/.openclaw/workspace/backups/gaps-fix-20260418-114325/` | `crystallize.ts`, `reflect.ts`, `api-server.ts`, `mcp-server.ts`, `index.ts` + dist | Rollback das melhorias da 1ª parte da sessão |
| `/root/.openclaw/workspace/backups/api-server-20260418-111829/` | Primeiros endpoints HTTP adicionados | Rollback de reflect/crystallize endpoints |
| `/root/.openclaw/workspace/backups/nox-mem-pre-nightly-20260418-125019.db` | **Snapshot completo do DB** (136MB, integrity_check OK) | Restore total se nightly corromper algo |

### Comando de rollback total (DB)
```bash
ssh root@100.87.8.44 'systemctl stop nox-mem-api nox-mem-watcher && \
  cp /root/.openclaw/workspace/backups/nox-mem-pre-nightly-20260418-125019.db \
     /root/.openclaw/workspace/tools/nox-mem/nox-mem.db && \
  systemctl start nox-mem-api nox-mem-watcher'
```

### Comando de rollback do código (exemplo Tier 1)
```bash
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && \
  cp /root/.openclaw/workspace/backups/tier1-20260418-122336/*.ts src/ && \
  cp /root/.openclaw/workspace/backups/tier1-20260418-122336/*.js dist/ && \
  systemctl restart nox-mem-api'
```

---

## Deliverables escritos hoje

### Docs novos
- `audits/audit-2026-04-18-db-gaps-remediation.md` — database-optimizer: SQL exato + rollback para cada gap
- `audits/sre-deepening-2026-04-18.md` — sre-engineer: Gap 2 RCA com descoberta do Chrome squatter, Path A blueprint, SLOs propostos
- `audits/perf-baseline-2026-04-18.md` — performance-engineer: p50/p95/p99 baseline real, Path B critique

### Docs atualizados
- `CLAUDE.md` (raiz) — v3.3 evolution entry, incidente 2026-04-18 completo, 8 convenções novas (busy_timeout, batch API, trigger cascade, canário semantic, etc.)
- `.claude/CLAUDE.md` — **não sincronizado** (hook do claude-mem bloqueou edição do bloco `<claude-mem-context>`). Priorizar resolução manual se divergência for problema — o raiz está completo.

---

## ⚡ Atalho automatizado (rode isto primeiro)

```bash
~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh
```

Faz tudo em 1 SSH round-trip: lê `/api/health`, conta restarts, 429s, verifica trigger, pega últimas entradas dos logs de canary/morning/nightly, imprime **colored report** com GO/NO-GO explícito no fim.

Se todos verdes → avança pro Tier 3.
Se algum vermelho → abre este doc na seção correspondente.

### Automação rodando na VPS (sem você fazer nada)

| Horário | Script | O que faz |
|---|---|---|
| 06:00 | `semantic-canary.sh` | Query natural → valida pelo menos 1 `match_type: "semantic"`, alerta Discord se falhar |
| 06:30 | `morning-report.sh` | Resumo completo dos 6 sinais, posta no Discord (se webhook configurado) |
| 23:00 | `nightly-maintenance.sh` | Stress test diário (reindex → consolidate → vectorize → kg-build → kg-prune) |

**Observação:** `DISCORD_WEBHOOK` NÃO está configurado em `/root/.openclaw/.env` (só `DISCORD_BOT_TOKEN` do bot). Se quiser receber ping no celular às 06:30, adicionar a webhook URL:
```bash
ssh root@100.87.8.44 'echo "DISCORD_WEBHOOK=<url_aqui>" >> /root/.openclaw/.env'
```
Sem isso, morning-report ainda roda e loga em `/var/log/nox-morning.log` — o script local `check-nox-mem.sh` mostra a última entrada.

## Checklist manual (se o script falhar ou quiser detalhe)

Abra SSH para a VPS e rode um por um. **Todos devem retornar verde.** Se algum falhar, pare e investigue.

### 1. Nightly-maintenance rodou limpo?
```bash
ssh root@100.87.8.44 'tail -50 /var/log/nox-maintenance.log'
```
Esperado: logs de reindex → consolidate → vectorize → kg-build → kg-prune sem erros. Se o vectorize reclamou de 429, Gemini quota pode estar batendo.

### 2. Canary passou?
```bash
ssh root@100.87.8.44 'tail -5 /var/log/nox-canary.log'
```
Esperado: `OK: total=10 semantic=N fts=M orphans=0` onde `semantic > 0`. Se semantic=0 → camada voltou a quebrar, investigar.

### 3. Sistema íntegro?
```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | python3 -m json.tool'
```
Esperado:
- `vectorCoverage.orphans = 0`
- `vectorCoverage.embedded >= 1951` (pode ter crescido se watcher ingestou novos chunks)
- `services.openclaw-gateway = true, nox-mem-api = true, nox-mem-watcher = true`

### 4. Zero restarts automáticos em 24h?
```bash
ssh root@100.87.8.44 'journalctl -u nox-mem-api --since "24 hours ago" --no-pager | grep -c "Started nox-mem-api"'
```
Esperado: **0 ou 1** (1 se houve manutenção programada). Qualquer número > 2 → probe está quebrado de novo ou serviço crashando.

### 5. 429 Gemini sob controle?
```bash
ssh root@100.87.8.44 'journalctl --since "24 hours ago" --no-pager 2>/dev/null | grep -cE "Resource exhausted"'
```
Esperado: **0-5**. Valores maiores sugerem loop runaway em algum cron (como Apr 12-15).

### 6. Trigger CASCADE ativo?
```bash
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "SELECT name FROM sqlite_master WHERE type=\"trigger\" AND name=\"trg_chunks_delete_cascade\";"'
```
Esperado: `trg_chunks_delete_cascade`. Se vazio → alguém removeu, reinstalar.

---

## O que fazer DEPOIS do checklist (próximas decisões)

### Se tudo verde → avançar pro Tier 3 (observability real)

Escopo:
- Wrapper 1-line em `mcp-server.ts` registrando `(tool, agent, args_hash, duration_ms, success, timestamp)` em nova tabela `mcp_tool_calls`
- `/api/metrics` Prometheus-style com 8 métricas: tool call rate, embed throughput, reflect hit rate, search p95, orphans, restart count, db size, quota
- Split `/api/health` pra pura liveness <10ms (sem SQL pesado)
- Zero breaking changes

Arquivos a tocar: `src/mcp-server.ts`, `src/api-server.ts`, novo `src/metrics.ts` (já existe stub). Estimativa: ~30 min.

**Por que Tier 3 agora:** em 7 dias de dados teremos resposta empírica sobre quais MCP tools são usadas de fato (Gap 5 do architect — "features fantasma"). Isso determina Path B (vale adaptive reflect cache?) e Path C (worth tiered storage?).

### Se algo vermelho → diagnóstico guiado

Abra este doc + o relatório relevante:
- Se vectorCoverage regrediu → `audits/audit-2026-04-18-db-gaps-remediation.md` (trigger + orphan cleanup)
- Se restarts > 2 → `audits/sre-deepening-2026-04-18.md` (Gap 2 RCA, Chrome squatter)
- Se latência p95 > 1s → `audits/perf-baseline-2026-04-18.md` (bottleneck map)

---

## Evoluções estratégicas deferidas (Tier 5)

Listadas do relatório dos specialists, NÃO atacar sem o Tier 3 rodando 7+ dias:

1. **Path A — Write coordinator (single writer)** — SRE-engineer: "apropriado, não prematuro". Unix socket > HTTP. 2 semanas migração começando por `crystallize`. Solves: contenção + CASCADE consistency + WAL checkpoint boundaries. Doc: `audits/sre-deepening-2026-04-18.md` seção Path A.
2. **Path B-lite — Semantic reflect cache** (sem dep-set invalidation — perf-engineer mostrou que é correctness trap). Só viável se hit rate > 15% confirmado (hoje 92% em sample minúsculo). Doc: `audits/perf-baseline-2026-04-18.md` Path B critique.
3. **Path C — WAL shipping + cold tier storage** — horizonte 60d. Mantém DB hot <50MB perpetuamente. Solves: long-term latency growth.

---

## Gaps conhecidos (NÃO atacar ainda — estão documentados)

- **Ollama reportado desabilitado pelo user (2026-04-17).** Health endpoint mostra `ollama: false`. KG extraction migrou pra Gemini 2.5 Flash em 11/Abr, então sem impacto. Confirmar intenção se for religar.
- **.claude/CLAUDE.md divergente do CLAUDE.md raiz.** Hook do claude-mem bloqueou edição. Ambos são lidos por Claude como project instructions — raiz tem info completa, .claude/ tem schema antigo. Resolver manualmente se virar problema de confusão.
- **Paper técnico (`paper-tecnico-nox-mem.md`) reflete v3.0.0, não v3.3.** Não urgente.
- **`procedures: 0` no health** — crystallize shipped hoje mas sem workflow que force uso. Gap 5 do architect.
- **Dashboard (`agent-hub-dashboard`) pode estar mostrando `embedded: 6627` stale.** Reduce TanStack Query cache ou hard-reload pra pegar os novos números honestos.

---

## Comandos úteis (cola e roda)

### Re-embed total se precisar (~74s, zero 429)
```bash
ssh root@100.87.8.44 'set -a; . /root/.openclaw/.env; set +a; \
  cd /root/.openclaw/workspace/tools/nox-mem && \
  node dist/index.js vectorize --force'
```

### Crystalize uma procedure
```bash
curl -X POST http://100.87.8.44:18802/api/crystallize \
  -H "Content-Type: application/json" \
  -d '{"title":"...","steps":["step 1","..."],"agent":"nox","tags":["tag"]}'
```

### Reflect com cache
```bash
curl -G "http://100.87.8.44:18802/api/reflect" \
  --data-urlencode "q=your question here"
```

### Ver reflect cache stats
```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | \
  python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)[\"reflectCache\"],indent=2))"'
```

### Verificar se um chunk específico tem embedding
```bash
ssh root@100.87.8.44 'sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT c.id, c.chunk_type, CASE WHEN m.chunk_id IS NOT NULL THEN \"yes\" ELSE \"NO\" END as embedded \
   FROM chunks c LEFT JOIN vec_chunk_map m ON m.chunk_id = c.id WHERE c.id = <ID>;"'
```

---

## Créditos da sessão

4 agentes disparados em paralelo produziram o diagnóstico:
- **architect (Opus)** — primeiro a identificar os 5 gaps e propor Paths A/B/C
- **database-optimizer** — SQL exato + descoberta que 100% dos chunks estavam sem embedding
- **sre-engineer** — descoberta do Chrome squatter em :18800 (architect tinha passado)
- **performance-engineer** — baseline numérica + crítica do Path B (dep-set invalidation era trap)

Cada relatório está nos `audits/` — usar como referência em futuros debugs.

---

**Abra amanhã: este doc + `audits/audit-2026-04-18-db-gaps-remediation.md` + `audits/sre-deepening-2026-04-18.md` + `audits/perf-baseline-2026-04-18.md`.** Continuar daqui mesmo.
