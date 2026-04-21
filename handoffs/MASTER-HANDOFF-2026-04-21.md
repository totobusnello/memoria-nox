# MASTER HANDOFF — memoria-nox

**Documento consolidado. Leitura única pra próxima janela retomar sem gaps.**

**Data da consolidação:** 2026-04-21 (final do dia)
**Versão do sistema:** v3.6d
**Última sessão:** 2026-04-21 (manhã + tarde + noite — audit sistêmica completa)

---

## TL;DR EXECUTIVO

Sistema nox-mem hoje está **de ponta**: 2073 chunks 100% embedded, hybrid search com self-heal */30min, auto-vectorize inline, RelayPlane roteando tráfego real (budget cap $5/dia ativo), delegação inter-agente validada, cross-agent operacional (7 DBs), active-memory plugin 10x mais barato, 6 serviços active, zero restart counter anômalo.

**Próximo passo aprovado:** `IM` (Import repos locais pra nox-mem, ~45 min). Depois: Fase 2 Graphify scale 3→15 repos. Depois: Fase 1.7b Memory Quality advanced. **Produtização NOX-Supermem fica pra FINAL**, só depois do plano implementado e funcionando.

---

## 1. ROADMAP — ONDE ESTAMOS vs. PARA ONDE VAMOS

### Fases ✅ concluídas (cumulativo)

| Fase | Status | Data | Evidência |
|------|--------|------|-----------|
| 1 — Quick Wins (wip, feedback, L1) | ✅ DONE | 2026-04-11 | — |
| 1.5 — KG Migration Ollama→Gemini | ✅ DONE | 2026-04-11 | 1489 entities |
| 0.5 — Foundation Repair | ✅ DONE | 2026-04-18 | embedded=100% |
| 1.6 — Search Quality | ✅ DONE | 2026-04-19 | expansion+dedup |
| 1.7a — Core Memory Quality | ✅ DONE | 2026-04-19 | user profile + ontology |
| 24h — Observação pós-0.5 | ✅ DONE | 2026-04-21 | 3d estável |
| 2.5 — graph-memory plugin | ✅ DONE | 2026-04-21 | afterTurn em produção |
| D1-D4 — Audit sistêmica | ✅ DONE | 2026-04-21 | 17 fixes |
| RP — RelayPlane de verdade | ✅ DONE | 2026-04-21 | Sonnet+Haiku passando |

### Próximas fases (ordem aprovada pelo Toto)

```
v3.6d (estado atual)
   ↓
IM — Import repos locais pra nox-mem                [⏳ READY, ~45min]
   ↓
C — Auditoria detalhada Fases 1.6/1.7a/1.8/2.5/2    [pendente, checklist grande em plans/2026-04-20-next-session-checklist.md]
   ↓
Fase 2 — Graphify scale 3 repos → 15               [🔧 IN PROGRESS]
   ↓
Fase 1.7b — Memory Quality advanced                 [🔒 BLOCKED by 2]
   ↓
Fase 3 — HD rsync + enrichment tiered              [🔒 BLOCKED by 1.7b]
   ↓
Fase 4 — Obsidian view-only                        [🔒 BLOCKED by 3]
   ↓
Path B-lite — Semantic reflect cache, Path C — WAL shipping, SEH — Self-Evolving Hooks
   ↓
   ↓  (tudo estável 30+ dias)
   ↓
P — Produtização NOX-Supermem                       [🔒 HORIZONTE FINAL]
```

**Regra do Toto (reiterada 2026-04-21):** *"B (produtização supermem) deve ser a última coisa depois de todo o plano implementado e funcionando."*

---

## 2. ESTADO ATUAL DO SISTEMA (2026-04-21 final)

### Infra
- **VPS:** Hostinger KVM 4 @ `root@100.87.8.44` (Tailscale) / `root@187.77.234.79` (público)
- **OpenClaw:** v2026.4.15 (commit `041266a`) + monkey-patch Issue #62028 ativo
- **Node.js:** v22.22.2 com wrapper `--no-warnings`
- **6 serviços active:** openclaw-gateway, nox-mem-watcher, nox-mem-api, relayplane-proxy, tailscaled, fail2ban
- **Discovery/mDNS:** off (defesa fratricide path 2)

### nox-mem DB
- 2073 chunks / 2073 embedded (100%) / 0 orphans
- 6 DBs de agente com trigger + vetores (atlas, boris, cipher, forge, lex, nox)
- `cross-stats` retorna todos 7 DBs

### Pipelines ativos
- Nightly maintenance 23:00 com Phase 6 diário de vectorize (idempotente)
- Canary `*/30min` com self-heal (5 OKs consecutivos)
- Check discord heartbeat `*/30min` (exit=0, 6/6 agents ok)
- Heartbeat-sync `*/15min` (bash+find, zero-custo)
- Logrotate em 9 logs nox-*
- Cron `nox-mem-session-distill` corrigido (max-sessions=20, timeout 3600s)

### RelayPlane (budget cap)
- Ativo: `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` **E** `openclaw.json providers.anthropic.baseUrl` — ambos obrigatórios
- Budget: $5/dia (warn 50/80%) + $1/hora + $0.50/request (block)
- Cascade fallback: Sonnet→Haiku→DeepSeek R1→Qwen3→Llama 70B
- Stats após 1h de tráfego real: 24+ requests, Sonnet+Haiku roteados, 100% success

### Plugins (observações recentes)
- **active-memory:** migrado Haiku→Gemini Flash-Lite, timeout 5s→15s → plugin finalmente contribui (10x mais barato, preserva OAuth Anthropic)
- **graph-memory:** ativo em produção (afterTurn events normais)

---

## 3. TIMELINE DE FIXES DA SESSÃO 2026-04-21

### Manhã — Incident response (v3.6)
Alerta Discord 06:30 UTC: `🔴 vectorCoverage: 0/2073 embedded + 🔴 Canary: FAIL`.

Root cause: às 01:09 UTC algo disparou `nox-mem reindex`. `dist/reindex.js:41` fazia `DELETE FROM chunks` sem vectorize subsequente → trigger `trg_chunks_delete_cascade` limpava vec tables → janela de cegueira de até 5 dias (até Sunday).

**Fixes aplicados** (3 camadas de defesa):
- **B** — Nightly Phase 6 diário de vectorize (era só Sunday)
- **C** — Canary self-heal inline (detecta total=0 ou semantic=0, vectorize, retry, alerta Discord)
- **A** (raiz) — `dist/reindex.js` patchado: import vectorize + try/catch após restore antes de closeDb

### Tarde — Audit sistêmica round 1 (crítico/alto)
Descobertos + resolvidos:
- DB path errado em nightly-maintenance (Phase 2 pulava silenciosamente há 1 mês)
- Watcher duplicado (nox-mem-watch.service legado)
- Canary `0 6 → */30` (24h → 30min detecção)
- RelayPlane env var `ANTHROPIC_BASE_URL` (insuficiente sozinho!)
- Logrotate em 9 logs nox-*

### Round 2 (M1-M5)
- M1 — `discovery.mdns.mode: "off"` explícito no openclaw.json
- M2 — Ollama removido dos docs (inativo desde Apr 11)
- M3 — apt guard file reescrito (syntax error + `node.real` → `node.bin`)
- M4 — heartbeat-sync `*/5 → */15 min`
- M5 — Cross-agent ressuscitado (trigger + vetores em 6 DBs)

### Noite — RelayPlane de verdade + git hygiene (v3.6c)
- **Descoberto**: `openclaw.json` `providers.anthropic.baseUrl` hardcoded **sobrescrevia** o env var. Por isso RelayPlane zumbi 12.9 dias mesmo com env var configurado
- Fix: mudar JSON pra `http://127.0.0.1:4100`, restart → tráfego real confirmado
- `.gitignore` corrigido (tinha `\n` literal), `.remember/` adicionado
- `.claude/CLAUDE.md` espelho deletado (source único: `memoria-nox/CLAUDE.md`)

### Final — Item D (v3.6d)
Fechou os 5 pendentes do `Handoff_20.04.docx`:
- **D1** — `check-discord-heartbeat-validation.sh` criado + cron */30min
- **D2** — cron `nox-mem-session-distill` fixado (timeout + max-sessions)
- **D3** — delegação Nox→Atlas validada end-to-end
- **D4** — roadmap v3.5 → v1.2 (fases DONE com evidência)
- **Bônus** — active-memory plugin migrado Haiku→Gemini Flash-Lite

---

## 4. DECISÕES E PRINCÍPIOS CONFIRMADOS NA SESSÃO

### Ordem de prioridade (reiterada Toto 2026-04-21)
1. **Executar plano operacional primeiro** (importar repos, fases 2/1.7b/3/4)
2. **Auditoria detalhada depois**
3. **POR ÚLTIMO produtização NOX-Supermem** — "só depois de todo o plano implementado e funcionando"

### Princípios arquiteturais
- **OAuth Claude MAX é cobrado como extra usage** em gateway 3rd-party (política Anthropic 2026) — RelayPlane é obrigatório pra ter budget cap
- **Boost multiplicativo é veneno quando empilhável** (lição v3.4)
- **`/api/health` nunca deve derivar de tabela sozinha — sempre JOIN** com source-of-truth
- **Teste canário é obrigatório** pra evitar fake-green
- **Sempre `set -a; . .env; set +a` antes de CLI nox-mem** via SSH/cron
- **Dois paths de fratricide cleanStale precisam dois bloqueios** (wrapper unset + monkey-patch)
- **Source-of-truth CLAUDE.md é único** (espelhos drift fast)

### Modelos padronizados
- Heartbeats + crons + active-memory plugin: `gemini/gemini-2.5-flash-lite`
- Agentes turn principal: `anthropic/claude-sonnet-4-6`
- Agent main: `anthropic/claude-sonnet-4-6` (nunca OpenAI sem créditos)
- KG extraction: Gemini 2.5 Flash (full) enquanto volume baixo
- NUNCA: `gemini-2.0-flash` (deprecated 2026-06-01), OpenAI como primary

---

## 5. PENDÊNCIAS OPERACIONAIS

### Housekeeping local (quick)
- [ ] `git rm --cached -r .remember/` no memoria-nox (parar de trackear 8 arquivos .log/.pid já trackeados)
- [ ] Commit das mudanças: CLAUDE.md v3.6d, .gitignore, reindex.js patch, handoffs novos, roadmap v1.2

### Monitoramento (passivo)
- [ ] Morning report Apr 22 06:30 UTC deve vir limpo (0 RED, 0 yellow)
- [ ] Canary continua OK a cada 30min
- [ ] RelayPlane stats: se `failedRequests > 0` ou `escalations > 0`, investigar
- [ ] `check-discord-heartbeat-validation` continua exit=0 a cada 30min
- [ ] active-memory plugin: se vier `status=empty` em 100% continuar, investigar prompt

### Próxima janela deve escolher (em ordem de prioridade)

**1º — Executar plano operacional (IM — Import repos locais)**
- Plano em `plans/2026-04-21-session-start.md` (intacto)
- Escopo: docs-only (*.md) de 10 projetos ~/Claude/Projetos/ + raiz
- 4 fases: Inventário → Pilot → Batch → KG rebuild
- Estimativa: 45 min

**2º — Auditoria detalhada (checklist pendente)**
- Arquivo: `plans/2026-04-20-next-session-checklist.md`
- Cobre: Fase 1.6 search quality, 1.7a core memory, 1.8-lite daily briefing, 2.5 graph-memory, 2 Graphify, Infra geral
- 20+ bullets específicos

**3º — Fase 2 Graphify (scale 3 repos → 15)**
- Pré-req: IM concluído
- Indexa GitHub repos adicionais no nox-mem

**99º — Produtização NOX-Supermem** (só no final, decisão firme do Toto)

---

## 6. ARQUIVOS-CHAVE PRA PRÓXIMA JANELA

### Source-of-truth
- `memoria-nox/CLAUDE.md` — **v3.6d**, Evolution completa + Incident Log + Convenções
- `memoria-nox/handoffs/MASTER-HANDOFF-2026-04-21.md` — este arquivo

### Plans vivos
- `plans/2026-04-19-unified-evolution-roadmap.md` — **v1.2** (atualizado hoje) — roadmap executivo
- `plans/2026-04-21-session-start.md` — plano IM (importar repos)
- `plans/2026-04-20-next-session-checklist.md` — checklist auditoria detalhada

### Handoffs históricos (leitura opcional)
- `plans/2026-04-20-session-handoff-cost-reduction.md` — 12 fixes cost-reduction de ontem
- `plans/2026-04-20-session-summary-completo.md` — sumário sessão monstro Apr 20
- `plans/2026-04-19-session-handoff-noite.md` — sessão Apr 19 noite
- `handoffs/2026-04-21-session-handoff.md` — handoff detalhado de hoje (antes deste master)

### Lessons críticas na VPS
- `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`
- `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`
- `shared/lessons/2026-04-20-gemini-quota-blowout-and-cron-hidden-burn.md`

### Backups preservados da sessão 2026-04-21
- `openclaw.json.bak-m1-20260421` (pre discovery.mdns)
- `openclaw.json.bak-pre-relayplane-baseurl-20260421` (pre RelayPlane fix crítico)
- `openclaw.json.bak-pre-active-memory-gemini-20260421` (pre active-memory migration)
- `.env.bak-pre-relayplane-20260421`
- `nightly-maintenance.sh.bak-2026-04-21` + `.bak-c2`
- `semantic-canary.sh.bak-2026-04-21`
- `dist/reindex.js.bak-pre-autovectorize-20260421`
- `99-node-wrapper-guard.bak-20260421`
- `crontab-backup-d1-20260421.txt`, `crontab-backup-m4-20260421.txt`, `crontab-backup-pre-canary-bump-20260421.txt`
- `cron/jobs.json.bak-d2-20260421`

---

## 7. COMANDOS QUE SALVAM TEMPO

```bash
# Antes de qualquer nox-mem CLI via SSH/cron
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem <comando>'

# Verificar saúde real do sistema
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# RelayPlane stats
curl http://127.0.0.1:4100/health

# Canary manual
bash /root/.openclaw/scripts/semantic-canary.sh; echo exit=$?

# Discord heartbeat validation
bash /root/.openclaw/scripts/check-discord-heartbeat-validation.sh; echo exit=$?

# Delegação inter-agente (triggera active-memory plugin)
openclaw agent --agent nox -m "Delegue ao Atlas (sessions_send agent:atlas:discord:channel:1480059433324380160) ..."

# Triggerar turn direto (sem delegação)
openclaw agent --agent atlas -m "mensagem"

# Listar crons internos OpenClaw (30+)
openclaw cron list

# Editar cron
openclaw cron edit <id> --timeout-seconds 3600 --model gemini/gemini-2.5-flash-lite
```

---

## 8. CLOSING NOTE

A sessão de 2026-04-21 entregou 22 tasks concluídas, encadeou 18 fixes (incluindo o root cause arquitetural do reindex), validou delegação inter-agente end-to-end, ressuscitou RelayPlane com budget cap real, migrou active-memory plugin pra 10x mais barato, limpou drift de docs, e consolidou tudo em docs estruturados.

O sistema está **em estado produção** pela primeira vez desde v3.3 (Mar 23) sem fragilidades conhecidas. Próxima janela entra com mapa claro + ordem de prioridade reiterada pelo Toto: **plano primeiro, produto por último**.

---

*Documento gerado: 2026-04-21 ~11:00 BRT. Próxima janela pode começar direto por **IM — Import repos locais** usando `plans/2026-04-21-session-start.md`.*
