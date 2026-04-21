# Handoff — Cost Reduction Session (2026-04-20)

**Continuação:** 2026-04-21 manhã (pós rotina 07h-12h)
**Autor:** Claude (sessão orquestrada por Toto)
**Status:** aplicado; validações pendentes

---

## 🎯 Objetivo inicial
Triar "41 crons" querendo eliminar burn de Anthropic. Descoberta real: crons internos do OpenClaw (30+ jobs em `/root/.openclaw/cron/jobs.json`), não crontab Linux.

---

## ✅ Aplicado hoje (12 fixes)

### 1. Modelo Gemini default (heartbeat + crons)
- `agents.defaults.heartbeat.model` migrou `gemini-2.5-flash` (quota estourada 4.31M/3M) → `gemini-2.5-flash-lite` (quota saudável)
- Catálogo `openclaw.json` recebeu entry `gemini-2.5-flash-lite`

### 2. `lightContext: true` uniformizado
Adicionado em 5 agentes (atlas, boris, cipher, forge, lex) que não tinham no override. Heartbeat antes mandava 200-365K tokens/call por agente.

### 3. Patches nox-mem/dist (4 arquivos)
- `session-distill.js`: `gemini-2.0-flash` → `gemini-2.5-flash-lite`
- `consolidate.js`: idem
- `search-expansion.js`: `gemini-2.0-flash-001` → `gemini-2.5-flash-lite`
- **`digest.js` (adicionado no teste do memory-review):** `gemini-2.0-flash-001` → `gemini-2.5-flash-lite` E `llama-3.3-70b-versatile` → `moonshotai/kimi-k2-instruct`

### 4. 19 crons internos OpenClaw migrados
Todos com `gemini/gemini-2.5-flash` → `gemini/gemini-2.5-flash-lite` via `openclaw cron edit <id> --model`.

### 5. Timeout aumentado
`auto-update-skills-clawhub` (300s → 900s) — estava timing out com 30 skills.

### 6. Fallback chain REAL ativada
Antes: todos os 7 agentes tinham `fallbacks: []` (vazio) — `??` coalesce retornava array vazio e ignorava o default = **fallback efetivamente morto**.
Agora: `fallbacks` removido dos overrides, default atualizado:
```
primary:    anthropic/claude-sonnet-4-6
fallback 1: openai-codex/gpt-5.4 (57 intel, OAuth Business)
fallback 2: groq/moonshotai/kimi-k2-instruct (47 intel, grátis)
fallback 3: gemini/gemini-2.5-pro (47 intel)
fallback 4: anthropic/claude-haiku-4-5 (cheap)
```

### 7. Discord heartbeat — formato `to`
Todos os 6 agentes com `heartbeat.to = "<channel_id>"` SEM prefixo `channel:` (plugin Discord normaliza auto via regex `/^\d+$/`). Chave `channelId` era inválida no schema (causou 323 falhas `Unknown Channel` em 14 dias).

Channel map por agente:
- nox: `1480051272508772372`
- atlas: `1480059433324380160`
- boris: `1480059552719306842`
- cipher: `1480060305697673317`
- forge: `1480060616021643336`
- lex: `1480261696722567348`

### 8. Relatórios consolidados/silenciados (11 → 6)
Desabilitados:
- `memory-digest` (Dom 21h) — consolidado no memory-review
- `generate-user-profile` (Dom 21h) — consolidado no memory-review
- `slack-20f-daily-summary` (07:15) — coberto pelo daily-briefing
- `Relatório Semanal Nuvini` (Seg 11h) — user decidiu acabar

Silenciado (deliver=none):
- `nox-mem-vectorize-weekly` — failure alert configurado pro Discord nox-chief (`1480051272508772372`)

### 9. Memory-review prompt consolidado
Prompt reescrito pra executar 4 passos em sequência:
1. `nox-mem digest`
2. `generate-user-profile.js`
3. Review .md files + MEMORY.md update
4. Git commit + push

Resposta: `HEARTBEAT_OK` se tudo OK, ou resumo (≤500 chars) com o que falhou.

**Testado manualmente hoje 22:12 BRT:** chegou no WhatsApp em 31s. Digest tinha falhado (gemini-2.0-flash-001 deprecated) — **patch aplicado em digest.js**, re-teste passou.

### 10. CLAUDE.md atualizado e commitado
Commit `4bd333c` — Evolution v3.5 + Incident Log 2026-04-20 + 5 novas convenções.

---

## ⏳ Validações pendentes pra amanhã 2026-04-21

### 🔥 PRIORIDADE 1: Discord heartbeat end-to-end
Crons que deveriam entregar no Discord amanhã:
- **Seg 08:15 L-V:** `Boris — Curadoria matinal LinkedIn` → Discord Boris channel
- **Seg 12:00:** `weekly-team-status` → Discord (channel `1482903100519088131`)

Verificar que `delivered: true` nos runs.

### PRIORIDADE 2: Fallback chain nova
Validar em logs se algum `failover decision: decision=cascaded from=X to=Y` apareceu (em vez do antigo `decision=surface_error`). Se não houver falhas amanhã, não há como testar sem forçar.

### PRIORIDADE 3: Memory-review Dom 22:30
Primeiro run automático no domingo. Esperar mensagem no WhatsApp.

---

## 🔍 Commands pra verificar amanhã

```bash
# 1. Últimos agent runs e modelos
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager | grep -E "agent.*end:" | tail -30'

# 2. Heartbeats Discord — chegaram?
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager | grep -iE "heartbeat.*(sent|failed|delivered)"'

# 3. Model usage (distribution)
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager | grep -oE "model=[a-z0-9.-]+ provider=[a-z]+" | sort | uniq -c'

# 4. Crons delivery status (Boris, weekly-team, etc)
ssh root@100.87.8.44 'openclaw cron runs --id b1592ecb-e512-428e-81df-93d68147d5ca 2>&1 | jq ".entries[0] | {ts, status, deliveryStatus, delivered}"'

ssh root@100.87.8.44 'openclaw cron runs --id ec44dd9b-af29-4468-8bf8-08d34917fcc9 2>&1 | jq ".entries[0] | {ts, status, deliveryStatus, delivered}"'

# 5. Erros 429 ou model_not_found (não devem aparecer)
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager | grep -cE "429|model_not_found"'

# 6. Gemini quota (via AI Studio) — confirmar 2.5-flash-lite saudável
# (manual no browser)
```

---

## ❓ Decisões pendentes pra amanhã

### A) RelayPlane: ressuscitar ou desligar?
Hoje está **zumbi** (service active, config com chaves mas `ANTHROPIC_BASE_URL` não no env do gateway). Budget cap inerte.

**Ressuscitar** (~20-30min config):
- Adicionar `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no systemd unit + `.env`
- Configurar `/root/.relayplane/config.json` com budget + cascade
- Restart gateway
- Validar rotas via `data.db`

**Desligar:**
- `systemctl stop relayplane-proxy && systemctl disable relayplane-proxy`
- Perde proteção de budget (critical com OAuth Claude MAX cobrando como API extra)

### B) Continuar investigando erros de cron?
Status `error` hoje:
- `bb08a230 plano-evolutivo-multi-agent` (haiku, disabled) — curioso
- `39dba631 reabilitar-health-monitor` (lite, desconhecido enabled state) — curioso

Vale investigar amanhã se forem úteis.

### C) `bvv-session-logger` every 30min (32 runs/dia) — reduzir pra 1h?
Hoje tá barato (rodando em 2.5-flash-lite). Mas ainda assim, 32 runs/dia é muito. Reduzir pra 1h = 16 runs.

---

## 🔐 Backups criados hoje (rollback)

```
/root/.openclaw/openclaw.json.bak-pre-forge-lightctx-20260420-?  (Item 2)
/root/.openclaw/openclaw.json.bak-pre-25flashlite-20260420-193059 (Item 1)
/root/.openclaw/openclaw.json.bak-discord-channels-20260420-195707 (Fase 1 rollback)
/root/.openclaw/openclaw.json.bak-nox-toformat-20260420-*
/root/.openclaw/openclaw.json.bak-fallback-chain-20260420-215317 (Fallback chain)
/root/.openclaw/cron/jobs.json.bak-pre-migrate-20260420-211800 (19 crons)
/root/.openclaw/cron/jobs.json.bak-memory-review-consolidated-20260420-*
/root/.openclaw/workspace/tools/nox-mem/dist/session-distill.js.bak-*
/root/.openclaw/workspace/tools/nox-mem/dist/consolidate.js.bak-*
/root/.openclaw/workspace/tools/nox-mem/dist/search-expansion.js.bak-*
/root/.openclaw/workspace/tools/nox-mem/dist/digest.js.bak-*
```

**Rollback config openclaw.json:**
```bash
ssh root@100.87.8.44 'cp /root/.openclaw/openclaw.json.bak-fallback-chain-20260420-215317 /root/.openclaw/openclaw.json && systemctl stop openclaw-gateway && fuser -k 18789/tcp; systemctl reset-failed openclaw-gateway && systemctl start openclaw-gateway'
```

**Rollback crons jobs.json:**
```bash
ssh root@100.87.8.44 'cp /root/.openclaw/cron/jobs.json.bak-memory-review-consolidated-* /root/.openclaw/cron/jobs.json'
```

---

## 📊 Estimativa de economia

- Antes: 19 crons × 3 runs/dia × ~30K tokens × Sonnet fallback = **$25-60/mês**
- Agora: 19 crons × lite quota Google = **$2-5/mês**
- **Economia: ~$23-55/mês** (extra usage Anthropic)

Heartbeat: zero queimando hoje (falhava antes do LLM). Quando task disparar real, roda em lite (barato).

---

## 🗂 Crons ativos finais (pós-limpeza)

### Diários
- 07:30 `daily-briefing` (WhatsApp, Haiku)
- 08:15 L-V `Boris — Curadoria matinal LinkedIn` (Discord Boris, Haiku)
- 23:00 `relatorio-eod` (WhatsApp, Haiku)

### Semanais
- Dom 10:00 `cipher-weekly-audit` (WhatsApp, lite)
- Dom 22:30 `memory-review` ⭐ consolidado (WhatsApp, Haiku) — **novo prompt**
- Seg 12:00 `weekly-team-status` (Discord, lite)

### Silenciosos (só alertam em falha)
- Dom 21:30 `nox-mem-vectorize-weekly` — failure alert → Discord nox

### Desativados
- `memory-digest`, `generate-user-profile`, `slack-20f-daily-summary`, `Relatório Semanal Nuvini`

---

## 🧠 Lições a arquivar

- `gemini/gemini-2.0-flash*` deprecated pra **new AI Studio accounts** (por data da conta, não data global — shutdown 2026-06-01)
- `heartbeat.channelId` **não é chave válida** — schema rejeita; `to` é a chave certa (plugin Discord normaliza)
- `fallbacks: []` no override **sobrescreve** default via `??` (null coalesce não substitui array vazio)
- OpenClaw tem **30+ crons internos** em `/root/.openclaw/cron/jobs.json` separados do crontab Linux
- `[cron] payload.model 'X' not allowed, falling back to agent defaults` no log = sinal de cron queimando fallback Sonnet
- OAuth Claude MAX em gateway 3rd-party = cobrado como API extra (política Anthropic 2026)

---

## 🤝 Também aplicado em paralelo nesta sessão (por outro agente/tarefa)

**Agent-map + delegação inter-agente** (feito ~15h-17h no dia):

- Criado `/root/.openclaw/workspace/shared/agent-map.md` (VPS) — fonte de verdade com sessionKeys do time
- Todos os 6 SOUL.md atualizados (nox, atlas, boris, cipher, forge, lex) com instruções de delegação
- Padrão estabelecido: **sempre `sessions_send()`** pro canal persistente; **NUNCA `sessions_spawn()`** (cria subagente efêmero sem memória)
- Fluxos documentados: Pesquisa → Implementação (Atlas → Forge), Pesquisa → Auditoria → Implementação (Atlas → Cipher → Forge), etc

SessionKeys do time:
```
agent:nox:discord:channel:1480051272508772372     (Chief of Staff)
agent:atlas:discord:channel:1480059433324380160   (Pesquisador Sênior)
agent:boris:discord:channel:1480059552719306842   (Jornalista)
agent:cipher:discord:channel:1480060305697673317  (Segurança)
agent:forge:discord:channel:1480060616021643336   (CTO/Dev)
agent:lex:discord:channel:1480261696722567348     (Jurídico)
```

Isso se integra bem com o Discord heartbeat `to` que configuramos (mesmo channel IDs). Quando heartbeat disparar real, agentes aparecem no próprio canal; delegação inter-agente pelo `sessions_send` também usa o mesmo canal.

## Próxima sessão: plano de ataque

1. Rodar `scripts/check-discord-heartbeat-validation.sh` (criado nesta sessão)
2. Decidir RelayPlane (A ou B)
3. Investigar 2 crons em error state se fizer sentido
4. Testar delegação inter-agente via `sessions_send` (ex: pedir Nox pra delegar pro Atlas e ver se volta)
5. Se tudo OK: fechar o roadmap v3.5 no CLAUDE.md
