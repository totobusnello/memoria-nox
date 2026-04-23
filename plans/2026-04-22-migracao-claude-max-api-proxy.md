# Plano de Migração: Anthropic API pay-per-token → Claude Max API Proxy

**Data:** 2026-04-22
**Contexto:** Após spike de consumo Anthropic 21→22 Abr, descoberto o provider `claude-max-api-proxy` que faz bridge via Claude Code CLI OAuth, transferindo custo do pay-per-token para a subscription flat do plan Max/Pro.
**Fonte:** https://docs.openclaw.ai/providers/claude-max-api-proxy
**Autor:** Toto (CEO/CTO)

## Objetivo

Migrar os 7 agents OpenClaw (main, nox, atlas, boris, cipher, forge, lex) do fluxo atual — que paga Anthropic API por token via extra usage — para o fluxo com `claude-max-api-proxy`, que usa a subscription Claude Max/Pro flat. Manter RelayPlane como fallback durante transição.

## Fluxo atual (antes)

```
agent → openclaw-gateway → ANTHROPIC_BASE_URL=http://127.0.0.1:4100 (RelayPlane)
      → api.anthropic.com (API key, pay-per-token EXTRA USAGE em cima do Pro plan)
```

## Fluxo alvo (depois)

```
agent → openclaw-gateway → OPENAI_BASE_URL=http://127.0.0.1:3456/v1 (claude-max-api-proxy)
      → claude CLI (OAuth session) → api.anthropic.com via Claude Max subscription flat
```

RelayPlane :4100 permanece rodando como **fallback** durante Fase 1 e parte da Fase 2. Só é retirado da cascata quando Fase 2 completar com sucesso.

## Critérios de aceite globais

- [ ] Gateway NRestarts=0 durante toda a migração
- [ ] Canary semantic search continua verde (`nox-mem search` funciona)
- [ ] Morning report green para 3 dias consecutivos pós-migração total
- [ ] Anthropic extra usage cai > 80% (medição via dashboard Anthropic)
- [ ] Zero "503 cooled down" originados do agent piloto/migrado durante 48h
- [ ] claude-max-api-proxy :3456 tem uptime >99% via systemd

## Riscos mapeados

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Plan Max rate limit não documentado | Média | Monitor durante piloto; rollback imediato se degradação |
| Anthropic revogar política "sanctioned" | Baixa | Tweet informal; manter RelayPlane como fallback plug-and-play |
| Community tool sem suporte oficial | Alta | Testar em 1 agent primeiro; preparar rollback script |
| Claude CLI OAuth expira/desloga | Média | Systemd monitora processo; alerta no morning report |
| Modelo naming diferente (claude-opus-4 vs claude-sonnet-4-6) | Média | Mapear modelos no setup; testar modelo por modelo |
| Volume + concurrency do OpenClaw saturar proxy local | Média | maxConcurrent=8 do gateway está baixo; monitor timeoutMs |

## Rollback universal

Em qualquer fase, se algo quebra:

```bash
# Restore config from backup
cp /root/.openclaw/backups/openclaw.json.pre-claude-max-$(date +%Y%m%d) /root/.openclaw/openclaw.json
systemctl restart openclaw-gateway
# claude-max-api-proxy continua rodando (não remove)
# Apenas o config do agent volta pra ANTHROPIC_BASE_URL
```

---

## FASE 1 — Piloto com `cipher`

**Duração esperada:** 48-72h de observação + 30min de setup
**Agent piloto:** `cipher` (baixo volume, menos crítico que nox/atlas)
**Estado inicial:** claude-max-api-proxy NÃO instalado; cipher usa sonnet-4-6 via RelayPlane

### Chunk 1.1 — Preparação (sem tocar em prod)

- [ ] Verificar que `claude --version` roda na VPS e está autenticado no plan Max/Pro
  - [ ] `ssh root@100.87.8.44 "claude --version"`
  - [ ] `ssh root@100.87.8.44 "claude /login status 2>&1 || echo 'manual login needed'"`
- [ ] Documentar plano atual da subscription (Max ou Pro) — anotar para monitor de rate limit
- [ ] Snapshot de métricas baseline (para comparação pós-piloto):
  - [ ] RelayPlane: `curl http://127.0.0.1:4100/status | jq` — salvar em `/root/.openclaw/backups/baseline-2026-04-22.json`
  - [ ] Cipher volume 7d: `journalctl -u openclaw-gateway --since "7 days ago" | grep -c "agent=cipher"`
  - [ ] Nox-mem health: `curl http://127.0.0.1:18802/api/health | jq` — salvar

### Chunk 1.2 — Instalar `claude-max-api-proxy`

- [ ] Backup do state atual
  - [ ] `cp /root/.openclaw/openclaw.json /root/.openclaw/backups/openclaw.json.pre-claude-max-$(date +%Y%m%d-%H%M%S)`
- [ ] Instalar global: `npm install -g claude-max-api-proxy`
- [ ] Testar inicialização manual: `claude-max-api &` por 30s, depois `kill`
- [ ] Validar endpoints manualmente:
  - [ ] `curl http://localhost:3456/health`
  - [ ] `curl http://localhost:3456/v1/models` — listar modelos disponíveis (mapear naming)
  - [ ] `curl -X POST http://localhost:3456/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"<primeiro modelo listado>","messages":[{"role":"user","content":"ping"}]}'`
- [ ] Anotar no plan o nome exato do modelo equivalente a claude-sonnet-4-6 no proxy

### Chunk 1.3 — Systemd unit para o proxy

- [ ] Criar `/etc/systemd/system/claude-max-api-proxy.service`:

```ini
[Unit]
Description=Claude Max API Proxy (:3456)
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/claude-max-api --host 127.0.0.1 --port 3456
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
EnvironmentFile=/root/.openclaw/.env
Environment=HOME=/root

[Install]
WantedBy=multi-user.target
```

- [ ] `systemctl daemon-reload`
- [ ] `systemctl enable --now claude-max-api-proxy`
- [ ] Validar: `systemctl status claude-max-api-proxy`, `ss -tlnp | grep 3456`
- [ ] Health check cíclico: `for i in 1 2 3; do curl -s http://127.0.0.1:3456/health; sleep 2; done`

### Chunk 1.4 — Override no `cipher` para usar proxy

- [ ] Editar openclaw.json. No bloco `agents.list[] | select(.id=="cipher")`, adicionar override de provider.
  - Opção A (mais comum): adicionar bloco `env` no cipher apontando `OPENAI_BASE_URL` + `model` usando novo naming
  - Opção B: usar `providers` override específico
  - **Decisão tomada durante execução** com base no schema real descoberto em `/providers/model-providers`
- [ ] Validar JSON: `jq empty /root/.openclaw/openclaw.json`
- [ ] Validar schema: `openclaw doctor` (sem restart ainda)
- [ ] `systemctl restart openclaw-gateway`
- [ ] Verificar subiu sem crash loop: `systemctl show openclaw-gateway -p NRestarts -p MainPID`
- [ ] Port :18789 listening
- [ ] Log inicial: `journalctl -u openclaw-gateway --since "1 min ago" | grep -iE "cipher|error"`

### Chunk 1.5 — Teste direcionado do cipher

- [ ] Mandar mensagem de teste ao canal Discord do cipher (`1480060305697673317`)
- [ ] Confirmar resposta chegou no Discord
- [ ] Verificar no log que o cipher **usou** o proxy:
  - [ ] `journalctl -u openclaw-gateway --since "5 min ago" | grep -E "agent=cipher.*(openai|3456|claude-max)"`
- [ ] Verificar no proxy que recebeu requisição:
  - [ ] `journalctl -u claude-max-api-proxy --since "5 min ago" | tail -30`
- [ ] Confirmar que a chamada NÃO foi para RelayPlane: nenhum novo request em `curl :4100/status`

### Chunk 1.6 — Observação 48h

- [ ] Morning report dia +1 post-piloto: verificar
  - [ ] Cipher teve atividade
  - [ ] Zero erros originados de cipher
  - [ ] Gateway NRestarts=0
- [ ] Morning report dia +2: idem
- [ ] Spot check de latência vs baseline (cipher devia responder em <5s para msgs simples)
- [ ] Dashboard Anthropic: confirmar que cipher não aparece como consumo extra usage

### Gate de saída da Fase 1

**Avançar para Fase 2 apenas se TODOS:**
- [ ] 48h observadas sem incidente no cipher
- [ ] Consumo Anthropic extra usage atribuível a cipher = zero
- [ ] Rate limit do plan Max não foi atingido
- [ ] Gateway estável (NRestarts=0)
- [ ] Modelo respondendo com qualidade equivalente (comparação subjetiva de respostas)

**Se NÃO passar:** executar Rollback (ver topo), abrir lessons.md entry e reavaliar.

---

## FASE 2 — Rollout gradual para todos os agents

**Duração esperada:** 1-2 semanas (um agent por vez, 24-48h de observação entre cada)
**Estado inicial:** cipher já migrado e estável
**Estado final:** todos os 7 agents usando claude-max-api-proxy, RelayPlane opcional

### Ordem de rollout (do menos crítico ao mais crítico)

1. ✅ cipher (já feito em Fase 1)
2. lex (baixo volume histórico)
3. boris
4. atlas (alto volume — observar 72h)
5. forge (tem crons automatizados — CUIDADO)
6. nox (agent principal dos humanos)
7. main (orquestrador — ÚLTIMO)

### Chunk 2.1 — Migrar `lex`

- [ ] Backup openclaw.json
- [ ] Aplicar override no lex (mesmo padrão validado no cipher)
- [ ] `jq empty && openclaw doctor && systemctl restart openclaw-gateway`
- [ ] Smoke test: mensagem no canal do lex, verificar resposta
- [ ] Observar 24h
- [ ] Gate: Lex OK + baseline metrics OK?

### Chunk 2.2 — Migrar `boris`

- [ ] Mesmo padrão (backup → override → validate → restart → smoke → 24h)
- [ ] Gate: Boris OK?

### Chunk 2.3 — Migrar `atlas`

- [ ] Mesmo padrão, **observação 72h** (agent de alto volume)
- [ ] Monitor especial: timeouts, rate limits, comparação de qualidade vs pré-migração
- [ ] Gate: Atlas OK após 72h?

### Chunk 2.4 — Migrar `forge`

- [ ] **Atenção:** forge tem cron jobs automatizados (`daily-briefing`, etc)
- [ ] Listar crons ativos: `openclaw cron list | grep forge`
- [ ] Mesmo padrão de migração
- [ ] Smoke test em **cron manual**: `openclaw cron run <cron-id-forge>` e validar execução
- [ ] Observar 48h incluindo pelo menos 1 ciclo de cada cron do forge
- [ ] Gate: Forge OK + todos os crons executaram com sucesso?

### Chunk 2.5 — Migrar `nox`

- [ ] **Atenção:** agent principal da conversa com o humano. Interrupção = impacto direto.
- [ ] Escolher janela de baixo uso (madrugada SP, ex: 03h-05h)
- [ ] Mesmo padrão de migração
- [ ] Smoke test extenso:
  - [ ] DM no canal 1480051272508772372
  - [ ] Pedir que invoque um subagent (força cascata nested)
  - [ ] Validar que subagent usa provider certo
- [ ] Observar 48h
- [ ] Gate: Nox OK + subagent dispatch OK?

### Chunk 2.6 — Migrar `main`

- [ ] **Último.** `main` é o orquestrador que invoca os outros.
- [ ] Já que todos os subagents estão migrados, `main` migrando completa o círculo.
- [ ] Mesmo padrão + janela de baixo uso
- [ ] Smoke test: todos os subagents via main
- [ ] Observar 48h

### Chunk 2.7 — Retirar RelayPlane da cascata (opcional)

- [ ] Após 1 semana de estabilidade com todos migrados, avaliar se RelayPlane ainda tem valor:
  - [ ] Como fallback: manter
  - [ ] Zero uso: considerar `systemctl stop relayplane-proxy && systemctl disable`
- [ ] **Recomendado:** manter RelayPlane rodando como safety net por 30 dias antes de desligar

### Chunk 2.8 — Cleanup + documentação

- [ ] Remover `anthropic` do `agents.defaults.model.fallbacks` (se ainda houver)
- [ ] Atualizar CLAUDE.md do memoria-nox:
  - [ ] Remover regra #5 sobre RelayPlane como obrigatório (ou revisar)
  - [ ] Adicionar seção sobre claude-max-api-proxy como novo padrão
- [ ] Adicionar lesson em `/root/.openclaw/workspace/memory/lessons.md`:
  - [ ] Data de migração completa
  - [ ] Economia real observada (dashboard Anthropic antes vs depois)
  - [ ] Surpresas encontradas (model naming, rate limits reais, etc)
- [ ] Salvar memória persistente `project_claude_max_proxy_migration.md` no auto-memory

### Gate final Fase 2

- [ ] Todos 7 agents usando proxy
- [ ] Dashboard Anthropic: extra usage caiu >80% em relação ao baseline
- [ ] Nenhum incident atribuível ao proxy nas últimas 7 dias
- [ ] Morning report green 7 dias seguidos

---

## Anexos

### A. Modelos a mapear durante Fase 1 (preencher no Chunk 1.2)

| OpenClaw name hoje | Claude CLI name no proxy | Observado |
|---|---|---|
| anthropic/claude-sonnet-4-6 | ? | preencher |
| anthropic/claude-haiku-4-5 | ? | preencher |
| anthropic/claude-opus-4-6 | ? | preencher |

### B. Comandos de rollback rápido (cola-e-roda)

```bash
# Rollback de 1 agent específico (ex: cipher)
ssh root@100.87.8.44 "cp /root/.openclaw/backups/openclaw.json.pre-claude-max-<TIMESTAMP> /root/.openclaw/openclaw.json && systemctl restart openclaw-gateway"

# Rollback full: desligar proxy + voltar config original
ssh root@100.87.8.44 "systemctl stop claude-max-api-proxy && cp /root/.openclaw/backups/openclaw.json.pre-claude-max-<TIMESTAMP> /root/.openclaw/openclaw.json && systemctl restart openclaw-gateway"

# Remoção completa do proxy (não destrutiva do openclaw.json)
ssh root@100.87.8.44 "systemctl disable --now claude-max-api-proxy && rm /etc/systemd/system/claude-max-api-proxy.service && systemctl daemon-reload && npm uninstall -g claude-max-api-proxy"
```

### C. Check list de métricas diárias durante a migração

- [ ] `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — `.embedded == .total`
- [ ] `systemctl show openclaw-gateway -p NRestarts` — deve ser 0 (ou o valor baseline)
- [ ] `journalctl -u openclaw-gateway --since "24h ago" | grep -c "cooled down"` — deve estar baixando
- [ ] `curl http://127.0.0.1:3456/health` — proxy up
- [ ] `curl http://127.0.0.1:4100/status | jq .totalRequests` — RelayPlane deve ir pra zero

### D. Pontos de atenção operacional

- **Claude CLI auth expira?** Anthropic não documenta TTL. Se expirar, todos os agents param. Mitigação: monitor no morning report para detectar "auth required" no proxy.
- **OpenClaw v2026.4.15 monkey-patch** (regra #6 do CLAUDE.md) — restart do gateway durante migração precisa respeitar o patch de fratricide. Usar wrapper `openclaw-gateway-wrapper`.
- **Memory/KG segue em Gemini** — não tocar. Essa migração é só pro provider dos agents, não dos plugins.
- **Concurrency:** `agents.defaults.maxConcurrent=8`. Proxy local pode gargalar se 8 agents chamam simultâneo — testar durante atlas (alto volume).
