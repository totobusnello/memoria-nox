# Baselines SRE — Fase 1.8 (medidos 2026-04-19 08:55 BRT)

Medidos na VPS `ssh root@100.87.8.44` antes de escrever código.

## Resultados

| # | Baseline | Valor medido | Esperado SRE | Interpretação |
|---|---|---|---|---|
| 1 | Writes/dia nox-mem (normal) | ~300-400/dia (hoje parcial: 339; pós-Foundation Repair ontem: 1951 anômalo) | não especificado | Inbox adicionaria ~30 writes/dia (1%). Magnitude trivial |
| 2 | SQLITE_BUSY count 7d | **0** | preocupação SEV-1 | **Sistema atual aguenta bem**. Enfraquece argumento SRE contra inbox-em-DB (mas Path A ainda é boa higiene pra Fase 2) |
| 3 | Discord webhook req/min pico 48h | não medido em tempo real (logs não granulares) | 30/min hard cap | Inconcluso. Recomendação: ativar log dedicado antes de escalar A2A chatter |
| 4 | Gemini $/dia atual | indiretamente: ~2290 embeds hoje (re-embed completo), uso normal ~50-200/dia | $5/dia warn | Muito abaixo do cap. A2A adicionaria pouco |
| 5 | Heartbeat success rate 7d | **TODOS os 6 agentes com HEARTBEAT.md stale há 6-14 dias** | esperado vivo | **Gap descoberto: feature de heartbeat está desligada/quebrada**. Fix é parte da Fase 1.8 |
| 6 | systemd-run cold start (5 samples) | 34ms, 35ms, 36ms, 37ms, 44ms (P50 ~36ms, P95 ~44ms) | SRE estimou 500ms | **Ordem de magnitude melhor do que esperado**. Dispatch síncrono é perfeitamente viável |
| 7 | Cron overlap 04:30 Dom (Cipher proposto) | limpo — nada entre 04:00 e 06:00 domingo; 23:00 nightly-maintenance é único pesado | risco conflito | **Janela livre para Cipher cron** |

## Descobertas colaterais (relevantes pra plano v2)

- **Canal `#agents-hub` no Discord já existe** e tem histórico — bot "Maestro" (ID 1480048785282306139) postou "Resumo semanal" em 23/mar-2026 sumarizando atividade dos 6 agentes. Então a infra de comunicação cross-agent no Discord **já roda em produção** há pelo menos 1 mês. Fase 1.8 reutiliza, não cria.
- **Fathom, Gmail, FII — nenhuma credencial/config na VPS.** Os 3 event triggers exigem setup não trivial de infra (1-2h cada, mínimo).

## Implicações para Fase 1.8-lite v2

1. **SQLITE_BUSY = 0 em 7d** reduz o risco percebido do inbox-em-DB. Mas arquitetura limpa (Path A) ainda é boa meta — a decisão "inbox como .md por enquanto" continua certa por simplicidade + auditabilidade, não por medo de corrupção.
2. **Dispatch síncrono é viável** (40ms cold start). Async + digest noturno vira **escolha de UX**, não constrainment técnico.
3. **Heartbeat stale é gap novo descoberto** — adicionar ao escopo. Sem heartbeat, Nox não sabe quem está vivo.
4. **Reuso `#agents-hub`** já existente elimina design de canal do zero.
5. **3 triggers simultâneos = 3-6h extra de infra** (além da base 1.8-lite). Totó autorizou mas precisa estar ciente do custo de tempo.
