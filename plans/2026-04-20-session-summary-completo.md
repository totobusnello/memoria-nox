# Session Summary — 2026-04-20 (dia inteiro)

> Sessão maratona: audit Notion migration → gateway fratricide bug → fix definitivo → memory policy → OpenClaw upgrade
> Duração: ~8h úteis (09:07 detecção inicial → 17:32 upgrade concluído)
> Estado inicial: gateway em crash loop desde 09:07, Notion ainda mandatório, systemd=failed
> Estado final: gateway v2026.4.15 estável, policy nova enforced, monkey-patch Issue #62028 ativo

## Escopo original vs. executado

**Original (vindo do handoff 2026-04-21-session-start.md):**
- Audit da Fase 1 do Notion import
- Se aprovado, Fase 2 (pilot 6 deals)

**O que aconteceu na prática:**
- Audit descobriu bug latente crítico no gateway + várias regressões
- 6h+ debugando gateway (3 agents em paralelo + research profunda)
- Migração Notion ficou em stand-by (snapshot parcial feito)
- Pilot 6 deals NÃO executado — ainda pendente pra próxima sessão

## Entregas consolidadas

### 🔧 1. Gateway fratricide — Issue #62028 (resolvido)

**Problema:** OpenClaw v2026.4.14 em crash loop via `cleanStaleGatewayProcessesSync` auto-matando parent. 6h downtime (09:07→14:39).

**Investigação (3 agents paralelos):**
- devops-incident-responder — kernel tracing, identificou fratricide pattern
- debugger — binary analysis, achou código exato em `dist/gateway-cli-DhgfjzZ0.js:766-806`
- sre-engineer — desenhou alternativas arquiteturais
- researcher — achou Issue #62028 no GitHub (regression desde v2026.4.5, sem fix em release)

**Fix aplicado (4 camadas):**

1. **Wrapper** `/usr/local/bin/openclaw-gateway-wrapper` (chattr +i):
   ```bash
   unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND
   export OPENCLAW_NO_RESPAWN=1
   exec /usr/local/bin/openclaw gateway run --bind loopback
   ```

2. **Config `openclaw.json`:**
   - `commands.restart=false`
   - `gateway.reload.mode=off`
   - `discovery.mdns.mode=off`

3. **🔑 Monkey-patch `dist/restart-stale-pids-*.js`** — função `cleanStaleGatewayProcessesSync` retorna `[]` imediatamente (**a camada decisiva**)

4. **health-probe.sh com auto-recovery:** `reset-failed + start` quando port 18789 morrer

**Backup:** `*.bak-20260420*` em todos arquivos tocados.

**Lesson completa:** `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`

### 📦 2. OpenClaw upgrade v2026.4.14 → v2026.4.15

**Motivação:** fix Issue #67436 (manifest.db corruption silenciosa em auto-provisioning systemd). Outras features irrelevantes pro nosso setup.

**Procedimento (17:26-17:32):**
1. Backup completo: binary (282M), nox-mem DB (41M), config, wrapper → `/root/backups/*preupgrade*`
2. `npm install -g openclaw@2026.4.15` (1 min)
3. `reapply-gateway-fix.sh` (monkey-patch re-aplicado no novo arquivo `restart-stale-pids-HQYy2vGd.js`)
4. `systemctl restart openclaw-gateway`
5. Monitor 75s → 0 crashes, 0 restarts, port estável

**Resultado:** upgrade sem incident. Issue #62028 persiste mas patch cobre. Issue #67436 agora corrigido.

### 🧠 3. Nox-mem v3.4 — fixes secundários

**Consolidações falhadas (10 → 1 persistente):**
- `nox-mem retry-failed` recuperou 9/10
- 3 files persistentes (content-specific bugs, não rate-limit): `memory/2026-03-20.md`, `memory/2026-04-05.md`, `memory/2026-04-15.md`
- Schema não tem `last_error` → debug requer leitura manual

**Gemini model migration (2.5 → 2.0 Flash):**
- `Gemini 2.5 Flash` estava em 116% do TPM quota (3.48M / 3M)
- Migrated em 6 arquivos: `digest.ts`, `reflect.ts`, `compact.ts`, `kg-llm.ts`, `search-expansion.ts`, `consolidate.ts`
- `gemini-2.0-flash-001` tem 10M TPM (3.3× mais headroom) + 33% mais barato
- Backups em `src/.bak-20260420/`

**Embed retry exponential backoff:**
- `src/embed.ts` — `embedBatchAPI` agora faz retry em 429 e 5xx
- Backoff: 1s → 2s → 4s → 8s → fail
- Script one-off `vectorize-slow.mjs` (batch 10, pause 3s) pra contornar burst 429

**Vector coverage:** 1775/1978 → **2046/2046 = 100%** (após upgrade + re-embed)

**Briefing fix:** `head -6` → `head -10` em `prepare-briefing-context.sh` (agora mostra os 7 Altas do pending.md, antes cortava em 6)

### 📋 4. Memory registration policy (substitui mandato Notion)

**Problema:** SOULs do Forge e Nox tinham seção "Notion — Registro obrigatório (MANDATO 13/04/2026)" que forçava agentes a escrever no Notion mesmo após decisão de torná-lo legacy.

**Entregas:**

- **Policy document** (`shared/policies/2026-04-20-memoria-registration-policy.md`, 18 chunks ingeridos):
  - Decision tree: WHAT/HOW/WHERE/WHEN
  - Frontmatter standard
  - Filename convention
  - Regras institucionais derivadas
  - Verification procedure

- **SOULs atualizadas** (Forge + Nox, backups em `.bak-20260420`):
  - Seção Notion removida
  - Nova seção "Memória — Registro obrigatório (UPDATE 2026-04-20)"
  - Lista de documentação atualizada (shared/lessons, shared/decisions, nox-mem decision-set)
  - Forge-specific: comando `"decisão: [texto]"` agora vai pra `nox-mem decision-set` não Notion

- **Destinos oficiais:**

| Tipo | Onde |
|---|---|
| Lição / postmortem | `shared/lessons/YYYY-MM-DD-<slug>.md` |
| Decisão atômica | `nox-mem decision-set <key> <value>` |
| Decisão narrativa | `shared/decisions/YYYY-MM-DD-<slug>.md` |
| Contexto cross-project | `shared/context/<slug>.md` |
| Policy / protocolo | `shared/policies/YYYY-MM-DD-<slug>.md` |
| Task urgente | WhatsApp → Toto → pending.md |

### 🗂️ 5. Notion snapshot retroativo (Fase 1.5 da migração)

**Escopo:** 15 entries recentes no Notion (2026-04-13 → 2026-04-20). 7 relevantes importadas, 8 descartadas (entities puras).

**Categorização importada** (`shared/context/2026-04-20-notion-memoria-snapshot.md`, 16 chunks):
- 2 lições: gerenciar contexto, filtrar skills
- 2 pendências: instalar skills (release-tracker + cia), Nox Discord webhook
- 1 decisão: aprovar/rejeitar instalação dos skills
- 2 contextos: Nox Discord otimizações, session-distill cron

**Observação cruzada:** pendência "Nox Discord webhook" duplica `pending.md #11` (agents-hub binding, 7 dias sem entrega do Forge).

### 📊 6. Monitor de versão + dedup

**Arquivo:** `/root/.openclaw/scripts/openclaw-version-monitor.sh`

**Checks:**
1. Versão npm atual vs. instalada vs. pinned
2. Monkey-patch presente no binary (grep pelo marker)
3. Auto-reapply se patch sumir (via `reapply-gateway-fix.sh`)
4. Port 18789 listening

**Cron:** `0 9 * * 1` (toda segunda 9h)

**Dedup:** alert só dispara se versão mudou desde último alerta (cache `/tmp/openclaw-version-last-alerted`). Evita noise semanal sobre mesma info.

**Pinned version file:** `/root/.openclaw/PINNED_VERSION = 2026.4.15` (atualizado pós-upgrade).

### 🔨 7. Scripts criados (2026-04-20)

- `/root/.openclaw/scripts/openclaw-version-monitor.sh` — monitor + dedup + auto-reapply
- `/root/.openclaw/scripts/reapply-gateway-fix.sh` — idempotent monkey-patch re-apply (criado por Forge)
- `/root/.openclaw/workspace/tools/nox-mem/vectorize-slow.mjs` — one-off slow vectorize (batch=10 pause=3s)

### 📝 8. Crons adicionados

| Cron | Horário | Propósito |
|---|---|---|
| `delivery-queue-cleanup.sh` | Dom 04:00 | Limpar delivery queue stale (preventivo) |
| `openclaw-version-monitor.sh` | Seg 09:00 | Check version + patch integrity |

### 🐛 9. Bugs descobertos e documentados

- **Gateway fratricide** (Issue #62028) — **fix aplicado**
- **Config reload trigger** em `commands.restart=true` — desabilitado via config
- **Health-probe reportava OK mesmo com systemd failed** (orphan serving port) — patched + revertido pra manter comportamento observacional
- **Forge declarou cron ativo mas não estava no crontab** — reincidência do padrão fake-green v3.4 (documentar pra ele)

## Commits (memoria-nox repo)

```
c8e2170  feat(memory): new registration policy + SOULs updated + Notion snapshot
7eea05e  docs(lesson): add Issue #62028 status nuance — closed upstream, bug persists
80c364e  fix(gateway): document OpenClaw Issue #62028 fratricide bug + monkey-patch solution
```

## Arquivos criados/modificados neste dia

### No repo memoria-nox (local)

```
plans/2026-04-20-notion-import-e-whatsapp-tasks.md          (plan original)
plans/2026-04-20-session-summary-completo.md                (ESTE arquivo)
plans/2026-04-20-gateway-resilience-sigkill-bug.md          (plano SRE agent)
plans/2026-04-21-session-start.md                           (handoff manhã 21)
shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md  (19 chunks)
shared/policies/2026-04-20-memoria-registration-policy.md   (18 chunks)
shared/context/2026-04-20-notion-memoria-snapshot.md        (16 chunks)
CLAUDE.md                                                    (incident log + 4 convenções + v2026.4.14 note)
```

### Na VPS

```
/usr/local/bin/openclaw-gateway-wrapper                     (rewritten, chattr +i)
/usr/lib/node_modules/openclaw/*                            (upgraded 2026.4.14 → 2026.4.15)
/usr/lib/node_modules/openclaw/dist/restart-stale-pids-HQYy2vGd.js  (monkey-patched)
/root/.openclaw/openclaw.json                               (3 config changes)
/root/.openclaw/PINNED_VERSION                              (new: 2026.4.15)
/root/.openclaw/scripts/openclaw-version-monitor.sh         (new)
/root/.openclaw/scripts/reapply-gateway-fix.sh              (new, by Forge)
/root/.openclaw/scripts/health-probe.sh                     (reset-failed patch)
/root/.openclaw/workspace/tools/prepare-briefing-context.sh (cap 6→10, regex fix)
/root/.openclaw/workspace/tools/nox-mem/src/*.ts            (model migration + retry)
/root/.openclaw/workspace/tools/nox-mem/vectorize-slow.mjs  (new, one-off)
/root/.openclaw/workspace/memory/pending.md                 (7 novos items de migração)
/root/.openclaw/workspace/agents/forge/SOUL.md              (3 patches, Notion → shared/)
/root/.openclaw/workspace/agents/nox/SOUL.md                (2 patches, Notion → shared/)
/root/.openclaw/workspace/shared/github-comments/issue-62028-comment-draft.md (by Forge)
crontab                                                      (2 novos crons)
```

## Backups VPS (preservados)

```
/root/backups/openclaw-2026.4.14-20260420-1726.tar.gz       (282M binary rollback)
/root/backups/nox-mem-preupgrade-20260420-1727.db           (41M DB pre-upgrade)
/root/backups/openclaw.json-preupgrade-20260420-1727
/root/backups/wrapper-preupgrade-20260420-1727

/usr/local/bin/openclaw-gateway-wrapper.bak-20260420-1320   (wrapper original)
/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js.bak-20260420*  (binary original)
/root/.openclaw/openclaw.json.bak-20260420-1235             (config pre-changes)
/root/.openclaw/scripts/health-probe.sh.bak-20260420        (pre-orphan-detection-patch)
/root/.openclaw/workspace/tools/prepare-briefing-context.sh.bak-20260420-1235
/root/.openclaw/workspace/memory/pending.md.bak-20260420
/root/.openclaw/workspace/tools/nox-mem/src/.bak-20260420/  (ts files pre-migration)
/root/.openclaw/workspace/agents/forge/SOUL.md.bak-20260420
/root/.openclaw/workspace/agents/nox/SOUL.md.bak-20260420
```

## Estado final do sistema (17:32)

| Componente | Estado |
|---|---|
| OpenClaw gateway | ✅ v2026.4.15, active, uptime crescendo, 0 restarts pós-upgrade |
| nox-mem DB | ✅ 2046 chunks, 2046 embedded = 100% |
| Semantic search | ✅ Funcional (match_type=semantic em PT-BR) |
| Knowledge graph | ✅ Atualizado (kg-build rodado) |
| Canary semantic | ✅ Verde |
| Consolidations | 55 done, 3 persistentes content-bug |
| Monitor versão | ✅ Ativo, dedup enabled |
| Health-probe | ✅ Observacional + auto-recovery |
| SOULs enforced | ✅ Forge + Nox atualizados |
| Notion Mission Control | 🔒 Read-only legacy (enforcement via SOUL) |

## Lessons institucionais derivadas (consolidadas)

1. **Dois paths destrutivos precisam dois bloqueios** (lição fratricide)
2. **Monkey-patch em dist/ é legítimo** quando upstream não tem fix + documentar bem + re-apply script
3. **Issue tracker upstream primeiro** antes de debug local profundo (economia de 2h confirmada)
4. **GitHub Issue status ≠ bug status** — verificar CÓDIGO não status (nuance pós-Forge review)
5. **Fake-green recidiva** — Forge declarou cron ativo 2× hoje sem verificar. Regra: `crontab -l | grep <nome>` obrigatório pós-criação
6. **Wrapper env unsets podem virar incompatíveis** em versões novas do binary
7. **SIGKILL externo nem sempre é OOM** — pode ser fratricide via fuser -k no ExecStartPre
8. **Spawning 3 agents paralelos** colapsou tempo de debug de dias pra 40min

## Pendências pra próxima sessão

### Alta
- **Fase 2 do plan original** — pilot Notion (6 deals Projetos & Deals). NÃO executado hoje devido ao gateway incident.
- **Monitorar 24h pós-upgrade** v2026.4.15 — nenhum sintoma esperado, mas watch
- **Forge executa:** `ggshield-scanner` ou code review final dos scripts criados hoje

### Média
- Full import Notion (5 DBs restantes: Memória & Decisões completo, Tasks do Time, Lições Aprendidas, Claude Code Setup page, Biblioteca Jurídica Lex page)
- Comunicar à Atlas/Boris/Cipher/Lex se SOULs deles ainda têm mandato Notion antigo (só Forge + Nox foram atualizados)
- Investigar 3 consolidations persistentes (content-bug)

### Baixa
- Reportar Issue #62028 ao upstream quando reabrir (draft em `shared/github-comments/`)
- Cron de audit automático comparando memory/ vs. Notion retroativamente

## Referências

- **Handoff inicial:** `plans/2026-04-21-session-start.md` (escrito noite anterior, era pra guiar hoje manhã)
- **Plan Notion migration:** `plans/2026-04-20-notion-import-e-whatsapp-tasks.md`
- **Lesson fratricide:** `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`
- **Policy registro:** `shared/policies/2026-04-20-memoria-registration-policy.md`
- **Snapshot Notion:** `shared/context/2026-04-20-notion-memoria-snapshot.md`
- **SRE agent plan:** `plans/2026-04-20-gateway-resilience-sigkill-bug.md`
- **Commits:** `80c364e`, `7eea05e`, `c8e2170`

## Timeline compacta

| Hora | Evento |
|---|---|
| 09:07 | Gateway entra em crash loop (detectado no audit matinal) |
| 09:10 | drift-check detecta systemd=failed |
| 12:00-13:00 | Audit Notion migration + descobertas 429 Gemini |
| 13:00-13:30 | 3 agents paralelos investigando gateway |
| 13:30-14:00 | Wrapper fixes, migração Gemini 2.5→2.0, retry backoff |
| 14:00-14:30 | Researcher descobre Issue #62028 + workarounds |
| 14:30-14:39 | **Monkey-patch aplicado — gateway estável** |
| 14:45-15:30 | Lesson escrita + ingest + CLAUDE.md |
| 15:30-16:00 | Forge code review + scripts + draft Issue comment |
| 16:00-16:30 | Fact-check Forge: cron não tava ativo (reincidência fake-green) |
| 16:30-17:00 | Policy de registro + SOULs patch + snapshot Notion |
| 17:00-17:20 | Version monitor + dedup |
| 17:20-17:32 | **Upgrade v2026.4.14 → v2026.4.15 sem incident** |

## Métricas finais

- **Downtime total:** 6h (09:07→14:39, inédito)
- **Chunks ingeridos hoje:** ~60 (lesson + policy + snapshot + re-retries)
- **Commits no memoria-nox:** 3
- **Agents spawnados:** 7 (3 investigação + 2 researchers + 1 policy-review + 1 background)
- **Arquivos tocados na VPS:** 12+
- **Scripts novos:** 3
- **Crons novos:** 2
- **Tasks completed:** 13 (ver task list)
- **Tempo total sessão:** ~8h úteis
