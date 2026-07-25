# Metodologia — desenho + guardas (Paper 2)

> "80% do paper é metodologia, não escrita." Este é o núcleo onde ele se ganha ou se perde.

## Desenho experimental

### As duas figuras que fecham a história

- **Figura A — "metrics lie":** scatter mostrando **nDCG/recall descorrelacionados** com *evitar-a-repetição*, entre políticas de memória. Prova que o instrumento antigo é cego.
- **Figura B — o efeito:** braço A/B ao vivo → memória **outcome-weighted** vs. flat reduz *repeated-failure-rate / task regret*. Os incidentes reais (`docs/INCIDENTS.md`, ex. *double-reindex-wipe*) são os **gold decision episodes**.

### Abordagem híbrida (não withholding puro)

Combinar, pra matar dano-à-produção + confounds:

1. **Counterfactual replay** (Codex, plano B) — pro **grosso**: simular políticas offline sobre o fluxo real de brief/priming. Zero dano, N grande, mas **observacional**.
2. **A/B randomizado pequeno, ao vivo, só em decisões low-stakes** — pra **validar** a fidelidade do replay. É o **único** elemento causal.

## As guardas (survival kit — GLM, prioridade zero)

### 1. Pré-registro público (OSF, timestamp ANTES do A/B)

- Outcome primário: **repeated-failure-rate** com definição operacional completa (o que conta como "repeat", janela temporal, granularidade de action).
- Sample size + **stopping rule**.
- Estratégia de randomização (ver SUTVA abaixo).
- Análise pré-commitada (estimador, testes, correção pra múltiplas comparações).
- **Por que crítico:** Paper 1 "descobriu" pain insignificante *post hoc* → o laboratório já está marcado por *researcher degrees of freedom*. Pré-registro é o antídoto.

### 2. SUTVA / interferência cross-agent (🆕 GLM)

Os 6 agentes compartilham memória e conversam. Randomização **ingênua** on/off por sessão viola SUTVA (um agente contaminado interage com um tratado → interferência → efeito médio quebra).

- **Desenho obrigatório:** **cluster-randomized** (por agente, ou por bloco de tempo) e/ou **washout** entre condições. Documentar explicitamente como se lida com os 6.

### 3. Adjudicação independente do outcome

- Quem decide "essa ação repetida conta como failure" **não pode ser parte** (juiz = parte).
- Adjudicação **cega** quanto ao braço.
- ~~**Auditor externo**~~ **REVISADO 2026-07-25 (Toto): sem auditor humano.** Que o pipeline `trace-bruto → action → outcome → failure` é determinístico e especificado **antes** da análise passa a ser *provado*, não *atestado*: commit congelado + hash, veredictos hasheados e timestampados **antes** do join com os rótulos de braço, exclusões como código incapaz de ler braço. Verificável por qualquer leitor, a qualquer momento. Ver `PREREG-DRAFT.md` §0b.

### 4. Artefato público

- Benchmark **anonimizado** (ids hasheados, buckets, zero texto) + esquema de labels documentado + **IAA** (inter-annotator agreement) reportado.
- **≥2 baselines** rodados por alguém **de fora** do time.
- Código de análise.

### 5. Conflito de interesse

Declaração explícita: somos donos do sistema, do benchmark e da métrica proposta.

## Reusa vs. constrói novo

| Reusa do nox-mem | Constrói novo |
|---|---|
| `brief_log`, traces de priming | Benchmark decision-replay de ação-desfecho (sanitizado, público) |
| `docs/INCIDENTS.md` (decision episodes) | Harness de withholding randomizado low-stakes ao vivo |
| 6 agentes vivos, memória compartilhada | Variante **outcome-weighted** (evolução honesta do pain) |
| metadata: access, pain, contradição, salience | Pipeline auditável trace → action → outcome → failure + pré-registro OSF |
