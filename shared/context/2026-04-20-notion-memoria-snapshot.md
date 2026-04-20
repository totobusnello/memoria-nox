---
chunk_type: context
source: notion-mission-control-migration
date: 2026-04-20
tags: [notion-import, retroactive, snapshot, memoria-decisoes]
supersedes: Notion database Memória & Decisões (30 entries recentes)
---

# Snapshot retroativo — Notion Memória & Decisões (últimas 48h pós-plan)

**Contexto:** agentes continuaram registrando no Notion Mission Control entre 2026-04-13 e 2026-04-20 (pós decisão de tornar Notion read-only legacy). Snapshot capturado antes de enforçar policy nova.

**Motivo do snapshot:** entradas originais já existem em `memory/*.md` (campo `Fonte` do Notion). Preservar aqui garante que o KG capture os títulos/categorias corretos.

**Source Notion database:** `Memória & Decisões` (collection://31d8e299-11ab-815c-a736-000bc62671fb)

---

## 1. Lição: Gerenciar contexto da conversa

- **ID Notion:** 3488e299-11ab-8100-996f-ca035ed779f2
- **Data original:** 2026-04-19
- **Fonte:** `memory/2026-04-19-forge-check-in.md`
- **Categoria:** Lição

### Conteúdo

A necessidade de gerenciar o contexto da conversa para evitar respostas lentas.

Agentes que acumulam histórico de conversa sem limpar contexto passam a responder lentamente porque cada request carrega o contexto completo. Solução: window sliding no contexto (manter só últimas N mensagens), ou summarization periódica do histórico antigo.

**Aplicável a:** Forge, Nox, todos agentes com sessões longas no Discord/Telegram/WhatsApp.

---

## 2. Lição: Filtrar e priorizar skills relevantes

- **ID Notion:** 3488e299-11ab-810f-9bbb-c15b4a265354
- **Data original:** 2026-04-19
- **Fonte:** `memory/2026-04-19-forge-check-in.md`
- **Categoria:** Lição

### Conteúdo

A importância de filtrar e priorizar skills relevantes para o perfil do usuário.

Instalar skills em massa polui o contexto do agente — ele precisa escolher entre dezenas de opções a cada request, aumentando latência e erros. Melhor: curadoria alinhada ao domínio do agente (Forge = DevOps/código, Nox = orquestração, Atlas = research, Lex = jurídico).

**Aplicável a:** processo de instalação de novas skills no OpenClaw.

---

## 3. Pendência: Instalar skills release-tracker + conventional-commits + provider-sync

- **ID Notion:** 3488e299-11ab-81aa-8ed0-c07d2d085d72
- **Data original:** 2026-04-19
- **Fonte:** `memory/2026-04-19-forge-check-in.md`
- **Categoria:** Pendência
- **Owner:** Toto Busnello (a decidir)

### Conteúdo

Toto precisa decidir se vai instalar os skills: `release-tracker`, `conventional-commits`, `provider-sync`.

Relacionada à decisão #4 abaixo. Bloqueia até Toto aprovar/rejeitar cada skill com base no critério da lição #2 (filtrar por perfil do usuário).

---

## 4. Decisão (pendente): Instalar os 3 skills acima?

- **ID Notion:** 3488e299-11ab-8145-a963-ff3a6a117641
- **Data original:** 2026-04-19
- **Fonte:** `memory/2026-04-19-forge-check-in.md`
- **Categoria:** Decisão
- **Status:** Aguardando Toto

### Conteúdo

Decidir se instalar os skills `release-tracker`, `conventional-commits` e `provider-sync`.

**Argumento pró:** automação de release notes + commits padronizados + sync entre providers.
**Argumento contra:** adiciona 3 skills no context window de cada agente (lição #2).

**Próximo passo:** Toto avalia valor vs. custo de contexto antes de aprovar.

---

## 5. Pendência: Configurar acionamento automático do Nox via Discord

- **ID Notion:** 3488e299-11ab-817a-a7d3-f040e1912090
- **Data original:** 2026-04-14
- **Fonte:** `memory/2026-04-14.md`
- **Categoria:** Pendência
- **Owner:** Forge

### Conteúdo

Forge precisa configurar bot/webhook no Discord que ative o Nox automaticamente quando mensagens chegam no canal `nox-chief-of-staff` sem precisar de @mention manual.

**Status:** aguardando implementação pelo Forge.

**Nota cruzada:** já está em `memory/pending.md` como pendência #11 ("agents-hub binding") — evitar duplicação.

---

## 6. Contexto: Nox Discord — otimizações pós-latência

- **ID Notion:** 3488e299-11ab-8107-8030-f6dbe8d8a616
- **Data original:** 2026-04-13
- **Fonte:** `memory/2026-04-13.md`
- **Categoria:** Contexto

### Conteúdo

Otimizações aplicadas no nox-mem + Nox Discord:
- Latência reduzida
- Cold start melhorado

Resultado de fixes iterativos ao longo de 2026-04-13. Detalhes técnicos específicos no memory file origem.

---

## 7. Contexto: nox-mem-session-distill cron

- **ID Notion:** 3488e299-11ab-818f-be6a-c586712293dd
- **Data original:** 2026-04-17
- **Fonte:** `memory/2026-04-17.md`
- **Categoria:** Contexto

### Conteúdo

Fixes aplicados no cron `session-distill` (roda Dom 05:00 extraindo memórias de sessões JSONL dos agentes). Aguardando próximo ciclo semanal (próximo domingo) pra validar que está rodando corretamente.

---

## Meta — por que este arquivo existe

Este é um **snapshot retroativo** pra:

1. Capturar info que agentes registraram no Notion entre 2026-04-13 e 2026-04-20 (período transicional onde policy ainda não estava clara)
2. Garantir que conteúdo importante não fique isolado no Notion (que virou read-only legacy)
3. Permitir que o KG extraia entidades e o search retorne esse conteúdo via nox-mem

**Daqui pra frente:** ninguém registra no Notion. Ver `shared/policies/2026-04-20-memoria-registration-policy.md`.

## Entidades pra KG

- **Agentes**: Forge, Nox, Toto Busnello
- **Sistemas**: nox-mem, Nox Discord, Discord bot/webhook, cron session-distill
- **Skills**: release-tracker, conventional-commits, provider-sync
- **Conceitos**: context management, skill filtering, sliding window, summarization, cold start, latência
- **Decisões**: skills installation (pending), Notion read-only legacy
