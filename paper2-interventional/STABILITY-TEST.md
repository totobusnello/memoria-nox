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

## 7. Proveniência

- Colisão detectada 2026-08-13 ~13:39Z; loop automático parado às 13:39:59Z.
- Contagem de duplicatas e comparação de vereditos: varredura de `extensao-moonshot-cycle-*.jsonl` em `~/.paper2-verdicts/`.
- Contexto: `[[feedback_safety_probe_output_is_paid_work]]`, `docs/INCIDENTS.md#2026-08-13`.
