# Revisão adversarial de 3 vozes — Paper 2

> Método: 3 vozes independentes de **famílias de treino distintas** (mesmo padrão do Paper 1) atacando a tese. O valor está na divergência — não harmonizar.
> - **Codex** (OpenAI)
> - **Kimi** (Moonshot)
> - **GLM-5.2** (Zhipu / Z.ai)
>
> Data: 2026-07-05. Verbatim completo das respostas no transcript da sessão.

## Convergência (as 3 concordam)

- A intuição **representação ≠ decisão** é forte e subexplorada. Há paper aí.
- Existe risco sério de "**log study** disfarçado" — precisa ser assumido, não escondido.
- **Artefato público sanitizado** (dataset + código) é **não-negociável**.
- O resultado negativo do Paper 1 é **ativo de credibilidade**.

## Codex (OpenAI)

**Ideia #1:** *"When Agent Memory Is Injected, Retrieval Metrics Lie: Longitudinal Evaluation of Session Priming Policies"* — memória injetada no início da sessão não pode ser avaliada por re-query/follow-up; métricas de RAG falham porque a memória já está no contexto. Defensável só por quem tem tráfego longitudinal real.

- Venue: COLM (interactions/multi-agent/eval) ou EMNLP (negative-finding + resource). NeurIPS D&B **só** com artefato público sério.
- Alerta: use o Nando só como **framing**, não como tese; sem A/B randomizado, "causal" é hype. **Policy-eval longitudinal primeiro, causal depois.**
- **Ideia #2:** *Supersession, Not Recall* (contradições temporais / stale recall) — mais crowded (Engram/bi-temporal já perto).
- **Plano B (mitigação-chave):** *counterfactual replay harness* — simular políticas offline sobre o fluxo real, sem tocar produção.

## Kimi (Moonshot)

- Rejeita como tema: pain-weighting sozinho, section-aware sozinho, shadow-discipline sozinho.
- Aposta: **"Interventional Memory: Causal Retrieval from Production Multi-Agent Traces"** — ancorada na distinção observação-vs-intervenção do Nando, usando os **incidentes reais** do `docs/INCIDENTS.md` (destaque: o *double-reindex-wipe*) como *decision episodes*.
- Plano B mais seguro: **auto-curação longitudinal** via snapshots mensais do corpus de produção.

## GLM-5.2 (Zhipu) — a voz que achou o furo

Veredito: intuição correta, mas o framing "interventional/causal" **sobrevendido** e o A/B in-house tem um buraco que "um reviewer de topo detecta em 90 segundos".

- **🆕 SUTVA / interferência cross-agent** (o achado único): os 6 agentes conversam entre si → um agente sem-priming interagindo com um tratado **contamina o efeito médio**; o estimador quebra. Em multi-agente é **quase certo**. Nenhuma outra voz viu isso.
- **"Causal" é hype** se usado como está: só o braço randomizado é interventional; o resto é observacional. Reservar "causal" pro braço randomizado.
- **É largamente log study** — assumir explicitamente em 2 camadas nos Methods.
- **A ÚNICA coisa pra sobreviver COLM/D&B:** pré-registro público (OSF, timestamp antes do A/B) + auditoria externa independente da adjudicação de outcome + release do benchmark anonimizado + código. Sem isso = whitepaper de vendor.
- Riscos que o reviewer caça, em ordem: (1) pré-registro do outcome primário, sample size, stopping rule; (2) independência da adjudicação; (3) SUTVA; (4) selection de traces (survivorship); (5) Hawthorne/novelty/drift.
- Por que **pode** ser forte: empiricamente grounded (6 agentes vivos), teoria legítima, Paper-1-honesto = credibilidade, consequência prática real. Mas **"a linguagem está na frente do desenho"** — corrija o gap ou desk-reject provável.

## Divergência que resolvemos

- **Kimi** quer "causal" no headline agora; **Codex + GLM** dizem que sem randomização isso é hype.
- **Resolução (martelo):** framing do **gap de avaliação** como headline; "causal" **só** pro braço randomizado. Ver `DECISIONS.md`.

## Nota operacional

O GLM falhou 2× nesta sessão (timeout de 120s no wrapper) antes de entregar. Causa-raiz: o agent `glm-adversary` chamava o Bash sem subir o timeout default. Corrigido 2026-07-05 (agent → `timeout: 600000` + modelo default sem `[1m]`). O veredito acima é do run pós-fix (113s, `exit=0`).
