# Product Review — Fase 1.8 (2026-04-19)

**Verdict: Parcialmente resolve.** Plano diagnostica certo (gap = ativação, não identidade) mas propõe infraestrutura antes de product-market fit.

## Top 3 Things Wrong

1. **Matcher reativo resolve 20%, event triggers resolvem 80%.** Totó raramente diz "faz um valuation" no WhatsApp — isso é trabalho de semana de deal review. Ativação real vem de: Fathom terminou call → Atlas 1-pager; Gmail recebeu PDF contrato → Lex thread; cron detectou FII delta → Atlas alerta. **Event bus > keyword matcher.**

2. **Audit 60 arquivos + schema v7 + FTS inbox + telemetria = 6h de infra para 1 usuário.** Para 3-5 dispatches/semana de Atlas, `agent_inbox` pode começar como `.md` append-only. Telemetria por agente pra 1 humano é vaidade — KPI real é "Atlas entregou algo útil esta semana?" (1 bit), não dashboard.

3. **Confirm-by-default vira atrito no solo-user.** Para 1 usuário tentando ativar agentes, cada "quer passar pro Atlas?" é fricção. **Silent dispatch + resumo diário** ("enquanto você fazia X, Atlas preparou Y") fecha loop sem interromper fluxo.

## Cortar (fechar em 3h)

- Audit 60 arquivos → spot-check de 6 SOULs
- Schema v7 `agent_inbox` + FTS → `/agents/<x>/inbox.md` append-only
- Telemetria por agente em `/api/health.agentMesh` → adia até ter volume
- Consolidation dos 10 arquivos → não resolve ativação

## Manter

- Cipher cron semanal (JTBD do próprio Totó)
- Nox `dispatch_to` tool
- Matcher em meta (simples, auditável)

## Adicionar

- **Event triggers** (gap central): Fathom webhook → Atlas; IMAP Gmail → Lex; FII price delta cron → Atlas
- **Discovery no boot do Nox:** primeiro turno do dia lista "agentes disponíveis, o que cada um pode fazer hoje"
- **Silent dispatch + digest noturno** no Discord `#daily-brief`
- **Outcome metric honesto:** "Atlas entregou 1 artefato útil/semana sem pedido explícito"

## Veredicto

Ship Fase 1.8-lite (Cipher cron + `dispatch_to` + 3 event triggers + inbox.md) em 3h. Reavalia em 30d com dados reais antes de construir schema/telemetria.
