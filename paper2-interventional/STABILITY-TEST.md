# Teste de estabilidade intra-painelista (test–retest) — spec

> **Status:** declarado 2026-08-13T13:47Z, **antes de a seed existir** e antes de qualquer sorteio.
> **Natureza:** **exploratório**, não confirmatório. Não altera o PREREG, não toca H1–H3, não entra em nenhuma família corrigida.
> **Origem:** acidente operacional (§1). O achado veio antes do desenho — por isso a cegueira precisa ser reconstruída, e o §4 diz como.

---

## 1. Como isto apareceu

Em 2026-08-13, dois processos adjudicaram o mesmo backlog em paralelo: o loop automático (`extensao-moonshot-loop.sh`, ciclo 29, gravado 12:34Z) e um ciclo manual disparado nesta sessão (`cycle-m2`, gravado ~12:36Z). Ambos leram o mesmo `extensao-moonshot-ainda-restante.jsonl` antes de qualquer um gravar. Nenhum lock existia.

Resultado: **40 episódios adjudicados duas vezes pelo mesmo painelista** (`moonshot`), com o mesmo `prompt_sha256` (`5b22f02c…`), em execuções independentes.

Comparando os 40 pares: **39 concordam, 1 diverge** (`b1ec491db1b16642`: `failure` na execução do ciclo 29, `abstain` na do m2).

Ou seja: uma corrida acidental produziu, de graça, a única medida de **estabilidade intra-avaliador** que este projeto tem. É uma dimensão que o κ do painel **assume** e nunca testou — κ mede concordância *entre* painelistas partindo do princípio de que cada um é estável consigo mesmo.

## 2. Por que os 40 acidentais não bastam

Três limitações, todas fatais para uso publicável:

1. **n = 40** — o intervalo de confiança binomial de 39/40 é aproximadamente **[87,7% ; 99,9%]**. Largo demais para sustentar afirmação.
2. **Amostra não aleatória** — são os 40 primeiros episódios da fila naquele instante, um bloco contíguo. Não representa o corpus.
3. **Cegueira perdida** — o resultado foi inspecionado antes de haver desenho. Qualquer regra escolhida agora sobre *esses* 40 é suspeita por construção.

Servem como **indício** que motiva o teste. Não como estimativa.

## 3. Desenho

**Pergunta.** Dado o mesmo episódio, o mesmo painelista e o mesmo prompt, com que frequência o veredito se repete?

**População de sorteio.** Todos os episódios do backlog da extensão com veredito `ok` do painelista `moonshot` no momento do sorteio, **excluindo os 40 da colisão** — esses já tiveram o resultado visto, e incluí-los importaria a quebra de cegueira para dentro da amostra.

**Tamanho.** n = 100. Com concordância verdadeira em torno de 97%, o IC de Wilson fica em cerca de ±3,3 pp — estreito o bastante para ser reportável, e 100 chamadas é custo desprezível.

**Sorteio.** Amostra aleatória simples sem reposição, semeada pelo beacon drand (§4).

**Execução.** Re-adjudicar os 100 sorteados com `run_panel.py --only moonshot`, mesmos `--workers 2`, e **o mesmo `prompt_sha256`** — se o hash do prompt divergir, o teste está medindo outra coisa e deve ser abortado.

**Saída.** `extensao-moonshot-stability-<round>.jsonl`, **fora** do glob `extensao-moonshot-cycle-*.jsonl` — não pode entrar na contabilidade do backlog nem virar voto no painel.

## 4. Seed — declarada antes de existir

| | |
|---|---|
| Chain | drand mainnet, `8990e7a9aaed2ffe…`, período 30 s |
| Round observado ao declarar | **6.373.253** (2026-08-13T13:43:55Z) |
| **Round alvo declarado** | **6.373.493** |
| Ocorre em | ≈ 2026-08-13T15:37Z (≈ 1h54 após a declaração) |

No momento desta declaração o round alvo **ainda não havia sido gerado**, portanto o `randomness` era desconhecido para todos, inclusive para quem escreve. O sorteio usa `random.Random(int(randomness, 16))` sobre a população ordenada por `episode_id` — determinístico e reproduzível por qualquer terceiro que baixe o mesmo round.

Isto reconstrói a cegueira que o §1 perdeu: a amostra não pode ter sido escolhida para produzir resultado nenhum.

## 5. Métrica e o que se pode afirmar

- **Primária:** proporção de pares idênticos, com IC de Wilson 95%.
- **Secundária, descritiva:** matriz de transição entre categorias de veredito — importa saber se a instabilidade se concentra na fronteira com `abstain` (como no único caso divergente observado) ou se atinge as categorias substantivas.

**Não se pode afirmar** com este teste: nada sobre H1–H3; nada sobre os outros painelistas (o teste é só do `moonshot`); nada causal.

**Uso pretendido:** um parágrafo de limitação/validação metodológica. Se a estabilidade for alta, o κ do painel ganha um piso justificado. Se for baixa, é uma ameaça real ao desenho e precisa ser reportada como tal — **este teste pode gerar resultado inconveniente, e o compromisso é publicá-lo do mesmo jeito**.

## 6. Tratamento das 40 duplicatas na consolidação

Independente do teste, o corpus tem 40 episódios com dois vereditos do mesmo painelista. **Isto precisa ser resolvido antes de qualquer replay**, ou eles viram voto duplo do `moonshot`.

**Regra, escolhida por ser independente do conteúdo:** manter a adjudicação **cronologicamente anterior** (a do `cycle-29`, gravado 12:34Z, sobre a do `cycle-m2`, 12:36Z), descartando a posterior. A regra não olha o veredito, só a ordem de gravação.

⚠️ **Declaração obrigatória:** esta regra foi escrita **depois** de eu ter visto que 39 dos 40 concordam e qual é o par divergente. A escolha é defensável por não depender do conteúdo, mas a cegueira não existe e isso fica registrado aqui em vez de ser omitido.

### 6.1 Verificado — e medido (2026-08-13T19:2xZ)

O pipeline **não dedupa**. `pilot_replay.carregar_verdicts()` agrega por `episode_id` apenas:

```python
por_ep[r["episode_id"]].append(NIVEIS.index(nivel))
...
out[ep] = "failure" if n_falha * 2 > len(v) else "not_failure"
```

Sem `panelist` na chave, a segunda adjudicação do `moonshot` entra como voto adicional. Medição sobre o corpus real (`extensao-pass1.jsonl` + todos os `extensao-moonshot-cycle-*.jsonl`, τ=S1):

| | |
|---|---|
| Episódios com painelista repetido (após filtrar `abstain`) | **39** |
| Desses, com painel **par** (4 votos em vez de 3) | **39** |
| Vereditos consolidados **alterados** | **0** |

**Zero mudanças** — porque os 39 pares concordavam, e o voto duplo apenas reforçou o mesmo lado. O empate 2–2, que a maioria estrita resolveria silenciosamente para `not_failure`, nunca chegou a ocorrer.

⚠️ **Isto é resultado benigno por acidente, não por desenho.** A premissa de painel ímpar — "sem empate por construção" — foi violada em 39 episódios, e só não produziu dano porque a estabilidade intra-painelista era alta naqueles casos. É exatamente a classe de falha registrada em `[[feedback_by_construction_can_be_voided_by_ops_failure]]`: a garantia estrutural morre por falha operacional, e o harness decide em silêncio o que a spec não disse.

**Correção necessária mesmo com impacto zero:** dedupe por `(episode_id, panelist)` mantendo o registro cronologicamente anterior. Restaura a imparidade e impede que a próxima colisão — que pode não ser benigna — passe sem ser notada. **Patch no `pilot_replay.py` pendente de aprovação**: mexer no pipeline de análise de um estudo pré-registrado não é alteração a se fazer sem decisão explícita, mesmo quando o efeito medido é nulo.

## 8. RESULTADO — executado 2026-08-14T09:16–09:27Z

100/100 adjudicadas, `prompt_sha256` = `5b22f02c…` (idêntico ao das rodadas originais), 0 pendências de cota.

```
concordam: 99   divergem: 1
estabilidade: 0.9900   IC95 Wilson: [0.9455 ; 0.9982]

not_failure -> not_failure: 55
failure     -> failure:     44
failure     -> not_failure:  1
```

### 8.1 A magnitude não ameaça o κ

Com estabilidade de 99% (piso do IC em 94,6%), a instabilidade individual **não é o fator que limita** o κ de 0,8747 do painel — o teto que ela impõe fica bem acima disso. Logo o desacordo entre painelistas é **genuíno** (critério ou dificuldade), não ruído de reamostragem do modelo. Isto fortalece a interpretação do κ.

### 8.2 ⚠️ Mas a média esconde onde a divergência cai

O único caso divergente, `aa6591cf2a05c044`:

| | veredito | level |
|---|---|---|
| moonshot 1ª | `failure` | S1 |
| moonshot 2ª | `not_failure` | S0 |
| xai | `failure` | S2 |
| zhipu | `not_failure` | S0 |

**xai e zhipu já discordavam entre si.** O moonshot era o voto de desempate — e é ele que oscila, **invertendo o consolidado** (2/3 acima de τ vira 1/3).

Contexto: **21 dos 100** episódios da amostra tinham discordância xai×zhipu, e a única divergência caiu nesse grupo.

- instabilidade global: **1%**
- condicional a desempate: **1/21 ≈ 4,8%**
- condicional a não-desempate: **0/79 = 0%**

Sob independência, a chance de a única divergência cair no grupo de 21% é 21% — **n=1 não prova nada** (p≈0,21). Mas a estrutura é a pior possível: nos ~21% do corpus onde os outros dois divergem, o moonshot decide sozinho, e a média global de 99% **dilui** essa borda com os 79% fáceis. Mesma classe de erro que [[feedback_by_construction_can_be_voided_by_ops_failure]] e [[feedback_always_check_then_recheck_conclusions]] registram: agregado tranquilizador encobrindo concentração na borda que decide.

### 8.3 Próximo teste — estratificado no desempate

O teste acima foi amostra **uniforme**, e por isso tem quase todo o seu poder onde não importa. O que falta: amostra **estratificada nos episódios de desempate** (xai×zhipu discordantes). No corpus completo devem ser ~300 (21% de 1.442); replicar 100 *desses* separa 4,8% de 0% com poder real. Custo: 100 chamadas, mesma mecânica, **nova seed drand declarada antes de existir**.

**Regra condicional, a pré-declarar antes de rodar:** se a concentração se confirmar, episódio cujo voto de desempate oscila entre execuções vira **`unknown`** — coerente com o tratamento que o desenho já dá a "menos de 3 vereditos substantivos". Instabilidade vira ausência de evidência, não voto de moeda.

**Não fazer:** ajustar prompt, temperatura ou parâmetros do painelista. Invalidaria os 1.442 vereditos já coletados e seria escolher o instrumento depois de ver o resultado.

## 9. CENSO DOS DESEMPATES — executado 2026-08-14T09:33–09:49Z

O §8.3 previa amostra estratificada de ~100 sobre ~300. **Errado:** a estimativa de 300 vinha de discordância de *level* (240 no corpus, ~17%); a discordância que **atravessa τ=S1** — a única que cria desempate sobre `failure`/`not_failure` — são **21 episódios em 1.442 (1,46%)**. População pequena o bastante para **censo**, o que elimina amostragem e seed: não há como acusar escolha de amostra.

**Desenho:** os 21 episódios, **5 réplicas cada** (105 chamadas, 100% ok, mesmo `prompt_sha256`), somadas à adjudicação original = 6 observações por episódio.

```
UNÂNIMES nas 6:   11
OSCILANTES:       10   (47,6%)

08dbe564  FNFFNN  3F/3N     14eeb72e  NFNFNN  2F/4N
1a46289e  NFFNFN  3F/3N     dc56238c  NFNFFF  4F/2N
5d9ba5d9  FNNNFF  3F/3N     e15081c2  NFNFFF  4F/2N
480d41a6  FNFFFF  5F/1N     ec03b721  FFNFFN  4F/2N
4f77fa6f  NNNFNN  1F/5N     f962162d  FFFFFN  5F/1N
```

**Confirma a hipótese do §8.2, e por censo, não por inferência.** Nestes 21 o `moonshot` é voto de minerva por definição (xai e zhipu em lados opostos de τ), logo **em 10 episódios o desfecho consolidado muda conforme a execução**. Três são 3–3: o veredito sai literalmente no cara-ou-coroa.

| | |
|---|---|
| instabilidade global (§8, amostra uniforme) | **1%** |
| observações discordantes dentro dos desempates | **20 de 126 = 15,9%** |
| episódios de desempate que oscilam | **10 de 21 = 47,6%** |

A média de 99% não estava errada — media o lugar errado. Os 98,5% de episódios fáceis afogavam a borda onde o painel decide.

### 9.1 Impacto ponderado — a preocupação NÃO se confirmou

O desenho pondera por Horvitz-Thompson: estrato A (`is_error=true`) é censo, peso 1,0; estrato B, amostra de 800 em 4.163, peso ≈ 5,2. Havia razão para temer amplificação: este projeto já viu 1,4% de empates × peso 5,2 virarem 20% de influência.

| | |
|---|---|
| oscilantes por estrato | A: **3** · B: **7** |
| fração não-ponderada | 0,69% |
| **fração ponderada** | **0,79%** |

Amplificação de **1,14×**, não 15×: o denominador também é dominado por B, então o peso se cancela em boa parte. **Os resultados do estudo não estão ameaçados.** Hipótese levantada, medida, e não sustentada — fica registrada porque o registro do que se testou e não se confirmou é parte do método.

### 9.2 Regra proposta

**Episódio de desempate cujo veredito oscila entre execuções → `unknown`.** Coerente com o tratamento que o desenho já dá a "menos de 3 vereditos substantivos": instabilidade vira ausência de evidência, não voto de moeda. Custo: **0,8% da massa ponderada**.

**Custo operacional, agora conhecido:** replicar os desempates 5×. São ~1,5% do corpus — 21 hoje, mais ~11 quando os 737 restantes forem adjudicados.

⚠️ **Limites desta evidência, declarados:**
- A hipótese veio de observação **post-hoc** (p=0,02 sobre n=2). O **censo** é a evidência; aquele p-valor é motivação, não confirmação.
- "Oscilante" está definido por 6 observações. Um 5–1 pode ser genuinamente estável com um outlier, e a regra o trata igual a um 3–3. Um critério graduado (ex.: só 4–2 e 3–3) é defensável e **não foi pré-especificado** — por isso não o adotei sozinho.
- O censo cobre o corpus **atual**. Os 737 não adjudicados gerarão novos desempates.

## 7. Proveniência

- Colisão detectada 2026-08-13 ~13:39Z; loop automático parado às 13:39:59Z.
- Contagem de duplicatas e comparação de vereditos: varredura de `extensao-moonshot-cycle-*.jsonl` em `~/.paper2-verdicts/`.
- Contexto: `[[feedback_safety_probe_output_is_paid_work]]`, `docs/INCIDENTS.md#2026-08-13`.
