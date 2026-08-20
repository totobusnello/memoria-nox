# Retratação: a "barra" do slot de cobertura não é um limiar de salience

**Data:** 2026-08-20 · **Retrata:** `OPTION2-MEASURED-2026-08-20.md`, a validação
"barra viva 0,7345 ≈ `CUT_FRESH` registrado 0,7342".

## O que eu afirmei e por que estava errado

Publiquei que a barra medida do slot 2 era **0,7345**, e tratei a proximidade com
a constante registrada `CUT_FRESH = 0,7342` como confirmação de que o modelo de
serving do §2 sobrevivia sob o pool restaurado.

Os 0,7345 existem no corpus, mas são o **topo do subconjunto já servido** — não a
barra. A coincidência com 0,7342 é numerologia: duas grandezas sem relação causal
que caem no terceiro decimal.

Detectei porque o `main_slot_ingress` deu um resultado impossível sob a minha
própria barra: S2 (base 0,6945) entrando a `w = 0` embora 0,6945 < 0,7345.

## O mecanismo real

`fetchFreshCandidates` (`src/api/brief.ts:698-701`) ordena

```sql
ORDER BY last_served ASC,          -- NULLs first: nunca-servido primeiro
         (0.55*importance + 0.10*pain + 0.1*[access>0]) DESC
LIMIT 400
```

e o `ranked.sort` seguinte repete a hierarquia: **tempo-desde-último-serve
primeiro, salience só como desempate.**

Consequência estrutural: **não existe barra em unidades de salience.** Um chunk
nunca-servido passa à frente de *todo* chunk já servido, qualquer que seja a
salience dos dois. Salience decide apenas entre nunca-servidos.

Medido no corpus de produção (`memory/lessons.md`, 52 chunks):

| estado | `pain` | n | salience |
|---|---|---|---|
| já-servido | 0,9 | 10 | 0,734477 |
| já-servido | 0,4 | 4 | 0,684477 |
| **nunca-servido** | **0,4** | **38** | **0,684477** |

Os 10 chunks de `pain = 0,9` — o topo por salience — estão **no fundo da fila**
porque já foram servidos. Os slots 1 e 2 são ocupados por dois dos 38
nunca-servidos, ambos a 0,684477. Daí a barra efetiva de hoje: **0,684477**,
e S2/S3/S4 entram a `w = 0` enquanto S1 (0,66942 a 1 d) não entra. Que é
exatamente o que o `INGRESS-RESTORED` mediu.

## A barra é um estoque em dreno, não uma constante

O conserto do prefixo (PR #44) religou o mecanismo hoje. Primeiros-serves por dia
no pool de cobertura:

```
2026-08-20 : 14     <- religado hoje
2026-07-10 :  1
2026-06-21 : 184    <- último dia com o prefixo válido
```

Estoque nunca-servido elegível **hoje: 38**. Dreno observado ~14/dia ⇒ o estoque
esvazia em **~3 dias**. Depois disso o pool só contém já-servidos, e qualquer
chunk novo — todo chunk de falha adjudicada é nunca-servido por construção —
**ganha o slot 1 sem competir por salience**.

Ou seja: a competição em regime não é chunk-do-estudo *contra o corpus*. É
chunk-do-estudo **contra outros chunks-do-estudo escritos no mesmo dia**, todos
nunca-servidos, disputando 2 slots por salience — onde a única diferença entre
eles é `severity` (via `pain`) e idade.

## O que isso faz com a dose

`W_OUTCOME = w · Δ_cut · severity` **escala com a severidade**. No regime de
estado estacionário, onde a disputa é entre chunks do próprio estudo, a dose
alarga a distância entre severidades mas **não pode inverter a ordem delas**.
Ela não levanta um piso; ela amplifica uma escada que já existe.

Tabela contra a barra medida de hoje (0,684477), `Δ_cut = 0,043`:

| severidade | `w` mínimo @1 d | @7 d | @30 d |
|---|---|---|---|
| S1 (0,25) | **1,40** | 1,72 | 2,87 |
| S2 (0,50) | 0 | 0 | 0,27 |
| S3 (0,75) | 0 | 0 | 0 |
| S4 (1,00) | 0 | 0 | 0 |

A ordem registrada (S1 > S2 > S3 > S4) sobrevive; **os níveis não**. A tabela
depositada (6,03 / 1,85 / 0,46 / 0) media contra 0,7342 num pool que estava
vazio. E `w = 2,0` — que o depósito descreve como quase-inerte — na barra de hoje
alcança S1 até **~12,5 dias** de idade e S2/S3/S4 sempre. Perto de saturar, não
de inerte.

⚠️ Nenhum destes números é depositável: a barra é o estoque de nunca-servidos, e
o estoque está drenando agora. Em ~3 dias todos os `w` mínimos vão a 0 e a
tabela acima deixa de valer. O que é depositável é o **mecanismo**: rank por
`last_served`, desempate por salience, dose que amplifica a escada.

## O argumento 2a-sobre-2b: sobrevive, por outra razão

Escolhi 2a alegando que o pool era um ponto de massa homogêneo. O pool **não** é
homogêneo em `pain` (0,4 e 0,9 coexistem). Mas os 38 **nunca-servidos** — os
únicos que competem — são todos `pain = 0,4`, salience idêntica a 0,684477. A
homogeneidade vale no subconjunto que decide. A conclusão fica; a razão que dei
estava errada.

## Para a emenda v1.12

Acrescentar às cinco correções já listadas:

6. **Não há barra em salience.** O critério de entrada no caminho de cobertura é
   **rank por `last_served`**, com salience apenas como desempate entre
   nunca-servidos. `CUT_FRESH` não modela isso — nem como constante nem como
   quantil.
7. **A barra é um estoque, não um parâmetro.** Qualquer `w` mínimo publicado é
   condicionado ao estoque de nunca-servidos na data da medição.
8. **A dose amplifica a escada de severidade; não levanta um piso.** Como
   `W_OUTCOME ∝ severity`, nenhum `w` reordena as severidades.

## Lição de método

Terceira vez neste ciclo que substituí um modelo-de-limiar errado por **outro
modelo-de-limiar** em vez de perguntar se o código aplica algum limiar. O sinal
que ignorei duas vezes: três constantes candidatas à "barra" (0,7342 / 0,744495 /
0,7345) — a dispersão era a evidência de que a grandeza não existia.
