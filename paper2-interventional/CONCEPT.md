# Conceito — Interventional Memory

## O problema (spine)

As métricas dominantes de avaliação de memória/retrieval de agentes — **nDCG, recall, MRR** — medem se o sistema recupera o documento *certo*. Mas pra um **agente que age**, o que importa não é rankear bem: é **não repetir a ação que deu errado**. Isso é uma propriedade da **decisão downstream**, não da lista rankeada. Uma métrica de IR é **estruturalmente cega** ao que a memória do agente existe pra fazer.

## O reframe do pain (por que Paper 2 nasce do Paper 1)

Paper 1 apostou em **pain-weighting** (pesar memórias pela severidade do que deu errado). O resultado foi honesto e negativo: **pain estatisticamente insignificante**; o ganho real veio de *section-aware boosting* (~99,85% do efeito).

**Diagnóstico:** o pain não falhou como mecanismo — falhou porque foi **medido com o instrumento errado**. `pain` é o sinal de desfecho de uma **intervenção** ("quando fiz X, doeu"). Um benchmark de *retrieval* (nDCG) não consegue premiar isso, porque não mede desfecho de ação. O nulo é **artefato de medição**, não prova de que o sinal é inútil.

→ Paper 2 troca o headline: sai o *pain como mecanismo-protagonista* (beco morto), entra o **valor interventional da memória** (o que o pain queria capturar), medido por uma avaliação que **consegue** vê-lo.

## O claim (1 frase)

> Para agentes LLM, o valor da memória é **interventional** — evitar repetir ações custosas —, uma propriedade a que as métricas de retrieval são estruturalmente cegas; introduzimos uma avaliação de ação-desfecho sobre traces de produção + um braço A/B randomizado ao vivo, e mostramos que memória **outcome-weighted** reduz *repeated-failure-rate* onde o nDCG não distingue nada.

## Âncora de fronteira

Agenda atual do **Nando de Freitas** (DeepMind → Microsoft AI): *continual, interactive, causal agents* + o paper *"Shaking the foundations: delusions in sequence models for interaction and control"* (2021) — modelos autoregressivos usados como agentes **confundem observação com intervenção** e se auto-iludem.

Paper 2 dá uma **resposta de engenharia** a esse problema nomeado: uma camada de **memória externa** que tipa e pondera episódios pelo papel causal (o que **observei** vs. o que **causei** + desfecho). `pain` era o primitivo desse sinal interventional.

> ⚠️ Ver `DECISIONS.md`: **"causal" é palavra a ser usada com parcimônia extrema** — só pro braço randomizado. A âncora do Nando é *framing*, não licença terminológica. Codex e GLM alertaram: "causal" como claim guarda-chuva = desk-reject.

## O moat (por que só nós escrevemos isso)

1. **Traces longitudinais de produção** — meses de um sistema de memória multi-agente vivo (6 agentes: Nox/Atlas/Boris/Cipher/Forge/Lex), com access counts, sinais de pain, contradições, correções, logs de priming. Academia simula; nós temos ground truth de deployment.
2. **Testbed multi-agente vivo** com memória compartilhada — raríssimo.
3. **Disciplina de benchmark honesto** — o resultado *negativo* do Paper 1 (pain insignificante) é **ativo de credibilidade epistêmica**: histórico de reportar o que não funcionou (GLM: "vale ouro num reviewer").

Sem vantagem de compute/escala — a defesa é o **dado e o rigor**, não GPU.
