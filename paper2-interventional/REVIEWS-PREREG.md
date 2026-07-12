# Review adversarial do PREREG-DRAFT — GLM-5.2 (2026-07-12)

> Alvo: `PREREG-DRAFT.md` v0.1. Método: challenge mode, mesmo protocolo das 3 vozes de 2026-07-05.
> Resultado: **5 FATAL · 7 GRAVE · 10 MENOR**. v0.2 incorpora tudo que não depende de decisão de rota; F1 exige decisão do Toto (ver §Rotas).

## FATAL

- **F1 — SUTVA continua aberto. Disclosure ≠ fix.** O "write path constante" não segura: o *conteúdo* escrito é downstream do tratamento (brief tratado → comportamento → writes → o que o braço controle lê depois). E os 6 agentes compartilham o store **simultaneamente** — cluster agente×bloco não isola contaminação cross-agent em tempo real. Com carry-over, a permutação de labels não preserva a distribuição conjunta → o teste perde exatidão. Fixes possíveis: (1) estimando restrito à primeira sessão pós-washout completo; (2) switch por agente inteiro + store per-arm (flush) — caro, limpo; (3) bounds sob interferência (Aronow-Samii / partial identification) em vez de point estimate; (4) desistir do claim causal (replay vira contribuição principal).
- **F2 — RFR condicionado a oportunidade tem viés de seleção pós-tratamento (collider).** O denominador (oportunidades elegíveis) é ele próprio afetado pelo tratamento; se o tratamento reduz P(executar|oportunidade), o braço tratado fica com os "hard cases" e o RFR condicional pode *subir* mesmo com a política funcionando. Fix: primário **incondicional** (repeated-failure density por session-hour) + co-primárias (opportunity rate, repeat-attempt rate, RFR condicional) com Holm.
- **F3 — Stopping rule em N oportunidades = optional stopping disfarçado.** N de oportunidades é pós-tratamento; o tempo de parada vira função do efeito. Fix: horizonte fixo em **blocos randomizados / calendário** (pré-tratamento). Abort assimétrico (só tratamento) = censoring informativo — reportar + sensitivity.
- **F4 — Permutation test só é exato pra sharp null de efeito-total-zero**, não pro estimando serving-policy (que nem está formalizado). Trend secular quebra exchangeability entre blocos. Fix: residualizar tendência antes de permutar; p-value da permutação separado do CI (bootstrap cluster); sensitivity A-B-A-B pra carry-over; declarar o que a sharp null cobre.
- **F5 — Pilot não pré-registrado reabre researcher DOF.** Escolher N/MDE/granularidade olhando o pilot sem transparência = o kill-shot original. Fix: pré-registrar a **função** N = f(pilot) (script executável commitado) antes de rodar o pilot.

## GRAVE

- **G1** Poder ficcional: 40% relative reduction é implausível pra nudge de brief; realista 5–15%. Fix: power curve + MDE explícito, target ~20%, declarar limiar de underpowered.
- **G2** H1 direcional ("lower") com teste two-sided = inconsistência. Fix: reframe "differs" two-sided (direção como expectativa) ou one-sided declarado.
- **G3** Exclusões pós-tratamento não-arm-blind (incident windows, coverage <95% podem correlacionar com braço). Fix: toda exclusão arm-blind, determinística, auditada; sensitivity com/sem.
- **G4** Estimando não escrito em potential outcomes. Com interferência, "effect of serving policy" não é operacional. Fix: E[Y(1,g₋ᵢ)−Y(0,g₋ᵢ)] com vetor de atribuição especificado.
- **G5** Abort só-tratamento sem data monitor independente (auditor ≠ monitor). Fix: nomear monitor distinto com critério operacionalizado.
- **G6** Sensibilidade à interferência só qualitativa. Fix: co-estimativas pré-commitadas (blocks sem overlap, lag-K adjustment, bounds).
- **G7** Agent como random effect com n=6 não se sustenta (≥20 recomendado). Fix: agent como fixed stratum.

## MENOR (M1–M10, todos incorporados no v0.2)

Ethics/IRB (adjudicadores humanos = subjects) · PAP executável com input sintético + hash do output esperado · deviations log versionado · seed custody por terceiro (monitor) · specs das figuras de H3 pré-unblind · sharing plan com DOI (Zenodo/OSF) + Docker · "agent" definido por identificador de OS · κ ≥ 0.75 (sensitivity {0.6, 0.7, 0.8}) · sensitivity do severity threshold {0.4, 0.5, 0.6} · fallback arm-blind pro floor de coverage.

## Síntese

> "Se não consegue defender o estimando em uma página de math, o resto não importa." — resolver F1 primeiro; F2/F3/F5/G4 na sequência. A linguagem não pode ficar na frente do desenho (mesmo diagnóstico de 2026-07-05).

## Rotas (decisão do Toto — bloqueia o lock)

| Rota | O que muda | Custo | Venue |
|---|---|---|---|
| **1. Conservadora** | Replay observacional = contribuição principal; A/B vira validação qualitativa de fidelidade, **sem claim causal point-identified** | Baixo (mata F1/F2 por remoção do claim) | COLM/EMNLP resource track |
| **2. Redesenho** | Switch por **agente inteiro** + store per-arm (flush) entre braços; elimina o vazamento | Alto (ops: 2 stores, flush discipline) | COLM full / D&B |
| **3. Análise formal** | Mantém desenho; estimando em PO + co-primárias + bounds de interferência + pilot pré-registrado | Médio | Viável, mas F1/F4 seguem difíceis de defender em D&B |

GLM: rota 3 **não** é segura pra D&B sem a rota 2. Recomendação da casa registrada no v0.2 §0.

**→ DECIDIDO (Toto, 2026-07-12): Rota 2-lite** — epochs fleet-wide + serving-side snapshots. Rota 1 fica como fallback documentado. Detalhe em `DECISIONS.md` + `PREREG-DRAFT.md` §0.
