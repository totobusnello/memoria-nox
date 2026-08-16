# Projeção pré-adjudicação do piloto — declarada em 2026-07-29

> **Registrado antes de a adjudicação rodar.** Este arquivo foi commitado
> **antes** de qualquer episódio além dos 300 da calibração ser enviado ao
> painel, e **antes** de a amostra do estrato B ser sorteada. Serve a dois
> propósitos distintos, ambos de precedência: declarar o valor de `K` que a
> projeção produziu, e declarar a regra de sorteio da amostra.

---

## 1. Por que este arquivo existe

`sizing.py` implementa a função pré-registrada `f`, que o §9 item 7a obriga a
rodar **exatamente uma vez**, depois do piloto, sem re-runs e sem escolher MDE
depois de ver o resultado. A garantia que isso oferece — *"não fizemos compras
de tamanho de amostra"* — só vale se ninguém tiver visto `K` antes.

**Eu vi.** Ao decidir quanto do corpus adjudicar, reimplementei a fórmula de
`epochs_per_arm()` num script de rascunho e a avaliei sobre entradas
*projetadas* (não medidas), para descobrir se a precisão comprada por $37
mudava a decisão em relação à comprada por $5. Não mudava — e essa é justamente
a informação que justificava o gasto menor.

Não chamei `f`, e as entradas não são as do piloto. Mas a distinção entre
"reimplementei a fórmula" e "rodei a função" é fina demais para sustentar uma
alegação de integridade. O tratamento honesto é o mesmo do beacon: **declarar o
número agora**, antes de a adjudicação existir. Se o `f` oficial cair em 21, é
confirmação verificável por terceiro; se cair longe, a divergência fica visível
em vez de silenciosa.

Este documento **não substitui** a rodada oficial de `f` e **não é** um
resultado do piloto.

## 2. A projeção

Entradas **projetadas** sobre o snapshot congelado (`CORPUS-FREEZE.md`,
`ba5fcc81…`), com a condição (i) estabelecida por `is_error` anterior — ver §4
sobre por que isso é um piso.

| entrada | valor projetado | origem |
|---|---|---|
| `r_hat` | 28.76 oport./hora-sessão | 2.439 oportunidades / 84.8 h |
| `p0_hat` | 0.1564 | 381.5 repeats esperados / 2.439 |
| `lambda_0` | 4.4966 repeats/hora-sessão | produto dos dois acima |
| `icc` | 0.0078 | medido na peça 2 (`pilot_replay.py`) |
| `hours_per_epoch` (T) | 6.06 | 84.8 h / 14 epochs |
| `session_hours_per_epoch` (m̄) | 70.4 sessões/epoch | unidade = sessão, cluster = epoch |
| `mde` | 0.20 | travado no §3 |

**Resultado projetado: `K = 21` épocas por braço** (42 épocas totais).

Intermediários, para quem quiser refazer sem rodar nada:
`z_sum = 2.8015852181129688` · `k_bruto = 13.016` · `DE = 1.54132`
· `ceil(13.016 × 1.54132) = 21`.

## 3. Uma propriedade do estimando que vale registrar

`K ∝ 1/(T · lambda_0)`, e `T · lambda_0 = repeats/epoch` — as horas-sessão
aparecem no numerador de `T` e no denominador de `lambda_0` e **cancelam**.

A consequência prática: a convenção `PISO_H` (uma sessão de ação única conta
1 minuto em vez de zero), que é arbitrária e foi escolhida por conveniência,
**não afeta `K`**. Escolher 30 s ou 2 min dobraria ou dividiria `lambda_0` pela
metade e deixaria `K` intacto. Só o design effect usa `m̄` separadamente.

Isto não é um resultado; é a razão pela qual uma convenção arbitrária no
harness não contamina o tamanho do estudo.

## 4. Desenho da adjudicação — declarado antes do sorteio

O corpus pós-washout tem **4.577 episódios**. A adjudicação é **estratificada
por `is_error`**, um sinal mecânico que o painel **não recebe** (o prompt
injeta apenas `tool`, `input_excerpt`, `result_excerpt`).

| estrato | N | adjudicados na calibração | plano |
|---|---|---|---|
| A — `is_error = true` | 414 | 47 | **censo** |
| B — `is_error = false` | 4.163 | 178 | **amostra uniforme de 800** |

**Por que A é censo:** os 47 adjudicados vieram **47/47 em ≥S1**. `is_error`
não vaza o rótulo — é quase colinear com ele, porque o painel lê a mensagem de
erro no texto do resultado, que é o mesmo material que um adjudicador humano
leria. Com `p_A` tão perto de 1, o censo de 414 elimina a incerteza do estrato
inteiro por ~$3.

**Por que B é amostra:** `p_B ≈ 0.062` e é aí que mora toda a variância. A
banda de `K` fecha de 17–26 (n=178) para 19–22 (n=800); de 800 em diante o
retorno marginal some — n=2.500 dá 20–21 e n=4.163 dá 21–21, sem mover o ponto.
800 é o joelho da curva.

**Por que não o censo completo dos 4.577:** a passada levaria ~7 dias contra
~2 dias, e nesse prazo o `codex-cli` muda de versão sozinho (medido:
0.144.5 → 0.145.0 em 24 h, sem ação). Drift de versão **dentro** de uma única
adjudicação é pior que uma banda de ±1 época: significa episódios do mesmo
corpus julgados por software diferente. A banda comprada não paga o defeito
introduzido.

**Sub-adjudicar é conservador, e a direção importa.** 34 das 74 assinaturas
primary nunca produzem `is_error` (468 episódios, 8.4% do corpus). Elas só
ganham condição (i) por uma falha adjudicada do estrato B. Sem isso, as
oportunidades ficam em **2.439** contra um teto de **3.870**, os repeats são
subcontados, `lambda_0` é deflacionado e **`K` sai inflado**. O erro é para
estudo mais longo do que o necessário, nunca para underpowered.

### Regra de sorteio do estrato B — declarada antes de ser executada

Seed derivada da seed de calibração já publicada, sem novo round de beacon:

```
SEED_B = SHA256( ascii(SEED_CALIB_hex) || "|stratum-B-800" )
SEED_CALIB_hex = f61f4c463dc86251e0f6620c37c5cece202b36b3c183e13f0ec5e98f488f4319
```

`ascii(...)` é a representação hexadecimal minúscula da seed **como texto**,
64 bytes ASCII — não os 32 bytes que ela codifica. A distinção é explícita
porque a ambiguidade já custou uma rodada em `CALIBRATION-SEED.md`.

Ordenação por hash, **não por PRNG**:

```
chave(e) = SHA256( ascii(SEED_B_hex) || "|" || e.episode_id )
amostra  = os 800 primeiros do estrato B ordenados por chave(e) crescente
```

PRNG de linguagem é um pin de versão ilusório — a mesma lição que tirou o pin
dos CLIs. Ordenação por hash é reproduzível por qualquer implementação de
SHA-256, para sempre.

**Sobreposição com a calibração é esperada e não é corrigida.** Os 178
episódios do estrato B já adjudicados entraram por um desenho estratificado por
assinatura, não uniforme. Os que caírem nos 800 têm o veredito **reaproveitado**
(mesmo prompt, mesmo painel, mesmo hash) — o veredito é função do episódio, não
de como ele foi sorteado. Os que não caírem **não entram** na estimativa de
`p_B`, para que a probabilidade de inclusão permaneça uniforme em 800/4.163.

## 5. Um achado que muda o texto do §4.1, não o desenho

A taxa de falha de **25.5%** que o pré-registro reporta é propriedade da
**amostra de calibração**, e o pré-registro a rotula corretamente como tal
("rater prevalence", "in the calibration set"). Mas a amostra foi estratificada
por assinatura, o que sobre-representou `is_error` em **2.3×**. A taxa
pós-estratificada do corpus é **14.7%**, não 25.5% — inflação de 1.76×.

Consequência: a regra mecânica de prevalência selecionou **Fleiss' κ** com base
numa prevalência que o próprio desenho amostral produziu. Numa adjudicação
representativa do corpus a prevalência cai **fora** de [0.20; 0.80] e a **mesma
regra**, sem alteração, selecionaria **Gwet's AC1**.

Isto **não invalida** τ = S1 nem κ = 0.874 — a estratificação por assinatura é
deliberada e está justificada no §4.1 (uma amostra ingênua seria dominada por
`Bash|shell:other`, ~27% do corpus, e nunca testaria a rubrica na cauda). O que
exige registro é que a comparação entre o coeficiente da calibração e o de uma
adjudicação futura **não é direta**, e que uma queda de κ nessa comparação seria
o paradoxo de prevalência, não degradação do painel.

---

*Commitado antes da seleção da amostra e antes de qualquer chamada de
adjudicação além das 1.685 já registradas.*
