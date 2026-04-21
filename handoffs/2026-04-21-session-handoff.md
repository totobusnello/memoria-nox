# Handoff — Sessão 2026-04-21 (nox-mem v3.6 → v3.6c)

**Data:** 2026-04-21 (manhã + tarde + noite)
**Trigger inicial:** Alerta Discord 06:30 UTC
> 🚨 nox-mem morning report: 2 RED / 0 yellow
> chunks embedded : 0/2073
> canary: FAIL: 0 results for canary query

**Desfecho:** Sistema passou de "semantic layer morto por ~5h + múltiplas fragilidades escondidas" pra "produção de ponta com auto-heal, budget caps reais e zero drift conhecido". 17 findings da audit sistemática resolvidos.

---

## 1. Estado ANTES da sessão

- `/api/health.vectorCoverage`: **embedded=0/2073** (wipe total)
- Canary: FAIL desde 06:00 UTC
- Gateway: estável (fratricide fix Apr 20 ativo)
- RelayPlane: **zumbi há 12.9 dias** (1 único request de teste em toda a vida)
- `openclaw-gateway` config: `ANTHROPIC_BASE_URL` não no env
- Canary cron: `0 6 * * *` (1x/dia) — detecção até 24h
- Dois watchers rodando em paralelo (`nox-mem-watcher` + `nox-mem-watch` legado)
- `nightly-maintenance.sh` apontando pra DB path vazio (Phase 2 pulava silenciosamente há 1 mês)
- `dist/reindex.js` fazia `DELETE FROM chunks` sem re-vectorizar → cascade trigger limpava vetores
- `.gitignore` do memoria-nox tinha `\n` literal (1 linha) — ineficaz
- 300+ logs untracked poluindo `git status`
- Agent DBs (atlas/boris/cipher/forge/lex/nox) sem trigger, sem vetores, abandonados desde Mar 22
- `/etc/apt/apt.conf.d/99-node-wrapper-guard` com syntax error + nome errado (`node.real` vs `node.bin`)
- `discovery` key ausente do `openclaw.json` (CLAUDE.md exigia "off" como defesa do fratricide path 2)
- Doc mencionava Ollama como serviço ativo (desabilitado desde Apr 11)
- `heartbeat-sync.sh` */5min (overkill)
- Zero logrotate pra `/var/log/nox-*.log`

---

## 2. Root cause principal (v3.6)

Às 01:09 UTC Apr 21, algo rodou `nox-mem reindex` (1884 chunks recriados em 1 minuto).

- `dist/reindex.js:41` faz `db.exec("DELETE FROM chunks")`
- Trigger `trg_chunks_delete_cascade` (instalado v3.3) cascadeia DELETE em `vec_chunks` + `vec_chunk_map`
- **Reindex não chamava `vectorize()` no fim** → vetores ficavam zerados até Sunday (Phase 4 do nightly-maintenance)
- Janela de cegueira semântica: até **5 dias** sem que ninguém perceba, porque FTS continuava respondendo queries keyword mas hybrid search degradava silenciosamente pra FTS-only

Trigger exato do reindex 01:09 UTC não foi identificado (não em crontab Linux, não em cron OpenClaw com "reindex" no prompt). Provável heartbeat/MCP tool de agente. Irrelevante — o fix arquitetural cobre qualquer invocador.

---

## 3. Fixes aplicados (17 total, em ordem)

### Fixes de recuperação imediata
1. **Re-vectorize manual** com `.env` carregado → 2073/2073 embedded em 114s
2. **Canary validado** passando (`total=10 semantic=10`)

### Fixes de mitigação (3 camadas de defesa)
3. **Fix B — Nightly Phase 6 diário:** `nightly-maintenance.sh` ganhou etapa final `nox-mem vectorize` (idempotente, 2s quando nada mudou). Antes só rodava domingo.
4. **Fix C — Canary self-heal:** `semantic-canary.sh` ganhou função `self_heal()` que ao detectar `total=0` OU `semantic=0` dispara `timeout 300 nox-mem vectorize` + retry + alerta Discord como `**auto-healed**` ou `FAILED — manual intervention`
5. **Fix A (arquitetural, raiz)** — `dist/reindex.js` patchado: `import { vectorize } from "./vectorize.js"` + bloco try/catch após restore metadata, antes de `closeDb()`. Qualquer invocador de `reindex()` (CLI, MCP, agentes) agora auto-re-embeda inline. Validado end-to-end: reindex manual executou `[reindex] Auto-vectorize complete: 2073 embedded, 0 errors`.

### Cleanup sistêmico (audit round 1 — crítico/alto)
6. **DB path correto** em `nightly-maintenance.sh` (era arquivo 0 bytes) — Phase 2 reindex/consolidate de agentes voltou a funcionar
7. **Watcher duplicado** eliminado: `nox-mem-watch.service` legado stopped+disabled (explica ingest 2x nos logs Apr 20)
8. **Canary `0 6 → */30`** — detecção de wipe cai de 24h pra 30min
9. **RelayPlane env var** — adicionado `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no `.env`, gateway restart (mas ver ponto 14 abaixo — não foi suficiente)
10. **Logrotate `/etc/logrotate.d/nox`** cobrindo 9 logs (nox-*, heartbeat-sync, config-drift, gateway-recovery, etc.) — daily, 14 rotations, compress, copytruncate

### Cleanup sistêmico (audit round 2 — médios)
11. **M1 — `discovery: {mdns: {mode: "off"}}`** adicionado ao `openclaw.json` (defesa do fratricide path 2)
12. **M2 — Ollama removido dos docs ativos** (serviço inativo desde Apr 11 quando KG migrou pra Gemini)
13. **M3 — apt guard file reescrito** — era syntax error + nome errado (`node.real`), agora checa `node.bin` e hook funciona
14. **M4 — heartbeat-sync `*/5 → */15 min`** (threshold "active" é 30min, sobra margem)
15. **M5 — Cross-agent ressuscitado (opção A):** trigger `trg_chunks_delete_cascade` instalado nos 6 DBs agentes + vectorize (462 chunks total, ~25s, ~$0.01 Gemini). `nox-mem cross-stats` retorna todos os 7 DBs

### Fix crítico final (descoberto no debug do P2)
16. **`openclaw.json` `providers.anthropic.baseUrl: "https://api.anthropic.com"` → `http://127.0.0.1:4100`** — o env var `ANTHROPIC_BASE_URL` sozinho NÃO funciona porque o JSON hardcoded sobrescreve. Esse era o motivo do RelayPlane zumbi há 12.9 dias. Fix aplicado + restart → tráfego real confirmado: stats saltaram de `requests=1` pra `requests=6` (claude-haiku-4-5: 3, claude-sonnet-4-6: 3, 100% success)
17. **`.gitignore` corrigido** — tinha `\n` literal (1 linha), reescrito com newlines reais + adicionado `.remember/`. `git status` foi de 300+ linhas pra 10

---

## 4. Estado APÓS a sessão

- `/api/health.vectorCoverage`: **embedded=2073/2073, orphans=0** ✅
- Canary rodando */30min — 5 OKs consecutivos ✅
- Gateway NRestarts=0, uptime estável ✅
- RelayPlane: **requests=6**, success 100%, recebendo tráfego Anthropic real ✅
- Budget caps ativos: $5/dia / $1/hora / $0.50/req + cascade fallback ✅
- 6 services active (openclaw-gateway, nox-mem-watcher, nox-mem-api, relayplane-proxy, tailscaled, fail2ban)
- Apenas 1 inotifywait (era 2)
- Cross-agent funcional (7 DBs com vetores + triggers)
- Logrotate ativo
- `.gitignore` efetivo — `git status` limpo

---

## 5. Backups preservados

- `/root/.openclaw/openclaw.json.bak-m1-20260421` (antes de discovery.mdns.mode)
- `/root/.openclaw/openclaw.json.bak-pre-relayplane-baseurl-20260421` (antes do fix crítico do baseUrl)
- `/root/.openclaw/.env.bak-pre-relayplane-20260421` (antes de ANTHROPIC_BASE_URL)
- `/root/.openclaw/scripts/nightly-maintenance.sh.bak-2026-04-21` + `.bak-c2` (antes do Phase 6 e DB path fix)
- `/root/.openclaw/scripts/semantic-canary.sh.bak-2026-04-21` (antes do self-heal)
- `/root/.openclaw/workspace/tools/nox-mem/dist/reindex.js.bak-pre-autovectorize-20260421`
- `/etc/apt/apt.conf.d/99-node-wrapper-guard.bak-20260421`
- `/root/crontab-backup-m4-20260421.txt` + `crontab-backup-pre-canary-bump-20260421.txt`

---

## 6. Pendências pra próxima sessão

### Opcional (housekeeping local)
- `git rm --cached -r .remember/` no memoria-nox pra parar de rastrear arquivos de log já trackeados (os 8 `M .remember/**` que ainda aparecem no `git status`)
- Commit das mudanças nesta sessão (CLAUDE.md v3.6c, .gitignore, .claude/CLAUDE.md deletado, este handoff)

### Produto
- **NOX-Supermem** (repo: `github.com/totobusnello/nox-supermem`, local `~/Claude/Projetos/nox-supermem/`): Plan tem 24 tasks em 4 chunks (scaffold / modules / installer / docs). Nenhum chunk começado formalmente nesta sessão — todo trabalho foi infra/nox-mem.

### ⏳ PRÓXIMO PASSO APROVADO — Import repos locais pra nox-mem

Prioridade confirmada pelo Toto em 2026-04-21: **primeiro fechar plano original, depois auditoria Fase 1.6/1.7a/1.8/2.5/2/Infra, e só POR ÚLTIMO produtização NOX-Supermem**.

Plano em `plans/2026-04-21-session-start.md` — **intacto, pronto pra executar (~45 min)**:
- Escopo: docs only (`*.md`, specs, plans, audits, CLAUDE.md) de 10 projetos em `~/Claude/Projetos/` + raiz `~/Claude/`
- 4 fases: Inventário → Pilot (daily-tech-digest sugerido) → Batch 9 projetos → KG rebuild + docs update
- Fora do escopo: skills/agents/commands/source code

Fluxo do Roadmap v1.2 atualizado mostra:
```
v3.6c (DONE) → IM (Import repos, READY) → Fase 2 Graphify (IN PROGRESS, scale 3→15 repos) → Fase 1.7b → Fase 3 HD rsync → Fase 4 Obsidian → ... → Fase P Produtização (HORIZONTE)
```

### Itens do handoff.docx de ontem — ✅ TODOS FECHADOS 2026-04-21 tarde/noite

Do `Handoff_20.04.docx` (resumo curto, Desktop):
1. ✅ **Decidir RelayPlane** — FEITO (ativo, RelayPlane roteando Sonnet+Haiku real, budget cap $5/$1/$0.50 efetivo)
2. ✅ **`scripts/check-discord-heartbeat-validation.sh`** — CRIADO (não existia antes) + cron `*/30min` + exit=0 (6/6 agents reachable e ativos, bot Maestro autenticado)
3. ✅ **2 crons em error state** — INVESTIGADO: só 1 de fato (`nox-mem-session-distill`). Causa: timeout com 322 session files × max-sessions=50. Fix: max-sessions=20, timeout=3600s, consecutiveErrors reset
4. ✅ **Delegação inter-agente (Nox → Atlas)** — VALIDADA end-to-end via `openclaw agent --agent nox -m "..."`. Atlas respondeu "Online e operacional — aguardando tarefas. ✅", Nox reportou de volta, `sessions_send` tool calls=1 failures=0, winner `anthropic/claude-sonnet-4-6` via RelayPlane
5. ✅ **Fechar roadmap v3.5** — ATUALIZADO pra v1.2: fases 24h/2.5/Path A marcadas DONE, RelayPlane+D1-D4+IM adicionadas, changelog v1.2 com 10 bullet points, executive summary atualizado pra v3.6c

### Pendências do `2026-04-20-next-session-checklist.md` (maior)

Auditoria completa das Fases 1.6 / 1.7a / 1.8-lite / 2.5 / 2 / Infra — **não executada**. Lista completa nos 20+ bullets do arquivo. Alguns já cobertos incidentalmente pela audit de hoje (restart counts, services, backup freshness) mas muitos específicos de search quality, KG, graphify pilot, etc não foram tocados.

### Monitoramento
- Aguardar primeiro run natural do canary às :30 da hora. Se aparecer `auto-healed` em algum momento, é sinal de que outro caminho (reindex/consolidate/ingest) escapou do Fix A e caiu no fallback do Fix C — investigar
- Próximo morning report 06:30 UTC Apr 22 deve vir limpo (0 RED, 0 yellow)
- RelayPlane budget cap: observar `curl http://127.0.0.1:4100/health` — se `failedRequests > 0` ou algum `escalations`, ver detalhe

### Documentação
- `.claude/CLAUDE.md` foi deletado (era espelho desatualizado com 145 linhas de drift do principal). Source-of-truth único: `memoria-nox/CLAUDE.md`

---

## 7. Contexto crítico pra agente continuar

### Sobre o OAuth MAX (ponto levantado pelo Toto)
Você usa Anthropic majoritariamente via **OAuth Claude MAX + extra usage**. Pós-política Anthropic 3rd-party 2026, OAuth MAX via gateway externo (OpenClaw) é cobrado como **extra usage (API rates)**, não incluído no flat MAX. **Só o RelayPlane oferece budget cap pra esse tráfego** — sem ele, consumo pode disparar silenciosamente (foi o incident v3.5 Apr 20 com burn oculto de Sonnet).

### Sobre o fratricide Issue #62028
v2026.4.15 (commit `041266a`) — bug upstream ainda ativo. Três camadas de defesa:
1. Wrapper `/usr/local/bin/openclaw-gateway-wrapper` faz `unset OPENCLAW_SERVICE_MARKER`
2. `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off` no openclaw.json
3. **Monkey-patch em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-HQYy2vGd.js`** — `cleanStaleGatewayProcessesSync` retorna `[]`. Hash do arquivo muda a cada upgrade — **antes de `npm update -g openclaw`**, checar issue tracker e re-aplicar patch se ainda aberto

### Comando crítico que salva tempo
Antes de qualquer `nox-mem` CLI via SSH/cron/script:
```bash
set -a; source /root/.openclaw/.env; set +a
```
Sem isso, GEMINI_API_KEY/ANTHROPIC_API_KEY/etc não estão no env → operações falham silenciosamente (foi o incident v3.4 — Forge declarou "1969/1969 vetorizados" quando era 0).

### Verificar estado real pós-operação
Nunca confiar na última linha do CLI. Sempre:
```bash
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

---

## 8. Referências

- CLAUDE.md principal: `/Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md` (v3.6c — tem Evolution completa + Incident Log + Convenções)
- Lessons relacionadas na VPS:
  - `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`
  - `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`
  - `shared/lessons/2026-04-20-gemini-quota-blowout-and-cron-hidden-burn.md`
- Audits anteriores: `memoria-nox/audits/*.md`
- Paper técnico: `paper-tecnico-nox-mem.md`

---

*Gerado: 2026-04-21 ~10:30 BRT.*

---

## 9. Contexto adicional do handoff de ontem (`Handoff_20.04.docx`)

3 commits memoria-nox ontem:
- `4bd333c` — Docs CLAUDE.md: v3.5 cost reduction pass
- `ccdd377` — Docs handoff: session 2026-04-20 cost reduction pass
- `11ac5d5` — Docs handoff: agent-map + inter-agent delegation context

Plano que esse docx explicitava pra hoje: 5 itens (detalhados na seção 6). **Só o item 2 (RelayPlane) foi executado nesta sessão.**

## 10. Arquivos de plan relevantes pra próxima janela

Em `memoria-nox/plans/`:
- `2026-04-21-session-start.md` — plano originalmente aprovado pra hoje (importar repos). **Intacto, pronto pra execução.**
- `2026-04-20-session-handoff-cost-reduction.md` — handoff ontem (12 fixes cost-reduction)
- `2026-04-20-next-session-checklist.md` — checklist de auditoria detalhado (Fases 1.6/1.7a/1.8/2.5/2/Infra)
- `2026-04-19-unified-evolution-roadmap.md` — roadmap v3.5 unificado (37KB)
- `2026-04-20-gateway-resilience-sigkill-bug.md` — contexto do fratricide (já resolvido v3.6)

**Recomendação de leitura pra próxima janela:**
1. Este handoff (completo)
2. `memoria-nox/CLAUDE.md` (v3.6c, fonte única de verdade)
3. Se for retomar plano original: `2026-04-21-session-start.md`
4. Se for pro produto: `nox-supermem/plans/`

---

*Próxima janela decide: (a) retomar importação de repos do plano original, (b) NOX-Supermem produto, (c) auditoria detalhada pendente, (d) outro.*
