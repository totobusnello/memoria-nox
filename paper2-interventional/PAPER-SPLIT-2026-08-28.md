# Separação em dois papers — decidido 2026-08-28

> **Decisão do Toto, 2026-08-28:** dois trabalhos. O da **superfície** vai a depósito
> assim que o gate de 29/08 passar; o **interventivo** vira trabalho próprio, com registro
> prospectivo feito com calma. O motivo é de estado, não de gosto: o resultado da
> superfície está completo e verificado com dados na mão, enquanto o estudo interventivo
> **nunca começou** — `NOX_P2_OUTCOME=shadow` desde sempre, sem `ASSIGNMENT.json`, Fase 3
> do plano de designação intocada. Segurar um pelo outro custa semanas.

## Paper A — a superfície (este manuscrito)

**Tese.** A não-exposição deste sistema é resultado de política, não de capacidade:
83,78% do corpus vivo nunca chegou ao agente; o brief entregou 8,7× o corpus em slots e
cobriu 2,66% (325 slots por chunk distinto); a renovação é governada por **tamanho de
coleção** e por **calendário de ingestão**, não por curadoria; e o mecanismo que poderia
corrigir isso tem teto de 4,86% dos briefs — teto que é, em boa medida, fato sobre a
**resolução de um campo de texto**.

Nada dessa tese depende de rodar intervenção nenhuma. Tudo é medição sobre o serving real
e replay do código real.

## Paper B — o estudo interventivo (ainda não começou)

Registro prospectivo do estimando → `ASSIGNMENT.json` → `active` → Epoch 1 → janelas de
tratamento. Pré-registro já público (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`).

## Onde cada peça fica, e por quê

| seção | destino | razão |
|---|---|---|
| Abstract, §1, §2, §3 | **A** | enquadramento e método da medição |
| §4.1, 4.1.1, 4.2, 4.3, 4.3.1, 4.3.2, 4.4 | **A** | são os resultados de superfície |
| §4.5 "o que este desenho não identifica" | **A, reescrito** | hoje lista o que a *intervenção* não identifica. O Paper A não alega efeito de intervenção; precisa da lista dele — sem desfecho a jusante instrumentado, nada randomizado, um sistema só |
| §5.1–5.7 (mecanismo, teto, saturação, formato) | **A** | o teto é resultado sobre a superfície. Deriva do comparador e é verificado por replay; não precisa da intervenção ter rodado |
| §6, §7, §8, §9 | **A** | defeitos de instrumento são contribuição declarada do método |
| Apêndice A — desvios do pré-registro | **B**, com nota curta em A | o pré-registro cobre o estudo **interventivo**. O Paper A não é o estudo pré-registrado, e carregar a tabela inteira sugeriria que é. Em A fica uma seção "relação com o pré-registro" |
| Apêndice B — cadeia da designação | **A** | 7 linhas, e é o que torna os 19 designados um conjunto fixo e rederivável por terceiro |
| Apêndice C — painel de adjudicação | **B** | severidade S0–S4, κ por fronteira, λ. Nada em A depende disso — ver a ressalva abaixo |
| Apêndice D, E | **A** | artefatos e catálogo de defeitos |
| "O que falta, em ordem de quem bloqueia quem" | **nenhum** | seção de trabalho, não de publicação |

## ⚠️ O acoplamento real, e o que ele exige

Os 19 designados vêm de `p2_verdict`, que é **produto do painel**. O Paper A usa esse
conjunto no §5. Dois números, e eles se comportam diferente:

- **o teto (17/350)** é medido com dose absurda (`w = 100.000`), em que o multiplicador
  por severidade satura junto com tudo. É **independente da severidade**;
- **a banda de saturação `(4,0; 4,4]`** não é: `W = w · Δ_cut · severity_pain` escala por
  chunk, logo a dose efetiva depende do rótulo do painel. Isso precisa de uma frase
  explícita em A, não de silêncio.

O Paper A portanto pode descrever os 19 como **um conjunto fixo, publicamente
rederivável, de um chunk por grupo de assinatura**, apontando para B o critério que
produziu a população — e declarando a dependência da banda.

⚠️ **Aberto até a sensibilidade da designação voltar:** se o teto balançar entre seeds, o
`4,86%` é ponto amostral e o §5.7 tem de reportar dispersão em vez de ponto. A análise
varia só o que pode variar — **12 dos 19 grupos são unitários**, então nenhuma seed mexe
em mais de 7. Rodando em 28/08; o §5 só é editado depois dela.

## O que este documento não decide

Veículo, ordem de submissão e se o Paper B reaproveita o texto de método do A. Nada disso
bloqueia o depósito, e decidir agora seria decidir sem informação.
