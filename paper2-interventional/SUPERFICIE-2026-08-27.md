# A superfície de exposição — a manchete do paper, medida

> **2026-08-27, depois do reframe aprovado.** O paper deixa de perguntar *"a memória
> interventiva funciona?"* e passa a responder **"o que uma memória de agente em
> produção realmente entrega, e por que uma intervenção plausível não muda isso"*.
> A intervenção deixa de ser o resultado e passa a ser o **instrumento** que prova
> que o teto é estrutural.
>
> Medição: `measurement/superficie-de-exposicao.py`; artefato
> `measurement/out/superficie.json`, travado por
> `measurement/out/esperado-superficie.json`. Nenhum número desta nota é digitado.
>
> Reproduzir: `./superficie-de-exposicao.py --db <nox-mem.db> --fim 2026-08-27
> --assert-json out/esperado-superficie.json`

---

## 1. As duas superfícies, e por que a contagem é exata

Um chunk só chega ao agente por dois caminhos:

| superfície | instrumento | cobertura |
|---|---|---|
| **brief proativo** | `brief_log` | vida INTEIRA do `/api/brief` (F1 subiu 2026-06-04) e **sem poda** — a única `DELETE FROM brief_log` do repo está num teste |
| **busca** | `chunks.access_count`, incrementado em `src/search.ts:396` | desde sempre. O brief **nunca** escreve nessa coluna: `brief.ts` só a lê |

Como as duas cobrem desde o início, a união é uma contagem **exata** de
já-exposto-alguma-vez, e o complemento também. Nenhum dos dois é bound.

| | |
|---|---|
| corpus | **67.187** |
| exposto no brief | 1.787 |
| exposto na busca | 9.755 |
| **união** | **11.051** |
| **nunca exposto por nenhuma** | **56.288 = 83,78%** |
| desses, passam o **próprio piso de relevância** do sistema (`importance ≥ 0,7` ou `pain ≥ 0,7`) | **10.008** |

*(152 chunks servidos no brief foram depois apagados do corpus — é por isso que
`corpus − união ≠ nunca-exposto`, e não por erro de query.)*

## 2. O achado: exposição é governada por TAMANHO, não por curadoria

A leitura tentadora dos 10.008 invisíveis-mas-elegíveis é "dez mil lições
preciosas invisíveis". É falsa: **8.928 deles são `distilled`** — fragmentos de
sessão de 205 caracteres em média. A leitura seguinte, "a curadoria funciona, o
gradiente de tipo prova", também não sobrevive ao teste.

| tipo | exposto / total | % |
|---|---|---|
| `lesson` | 53/53 | **100,0** |
| `test` | 14/14 | 100,0 |
| `project` | 36/43 | 83,7 |
| `feedback` | 12/17 | 70,6 |
| `digest` | 15/25 | 60,0 |
| `person` | 8/14 | 57,1 |
| `decision` | 4/11 | 36,4 |
| `shared` | 13/40 | 32,5 |
| `graph_node` | 282/1.046 | 27,0 |
| `daily` | 798/3.231 | 24,7 |
| `team` | 3.327/15.308 | 21,7 |
| `distilled` | 2.822/14.456 | 19,5 |
| `other` | 3.515/32.920 | **10,7** |

**O teste que separa as duas explicações.** Correlação entre `log₁₀(tamanho do
tipo)` e `% exposto`: **Pearson r = −0,728**, **Spearman ρ = −0,714** — o tamanho
explica **53%** da variância. E a separação não tem sobreposição:

- **5 tipos com n ≥ 1.000:** exposição de **10,7% a 27,0%**;
- **8 tipos com n < 100:** exposição de **32,5% a 100,0%**.

Dentro dos grandes a ordem é quase monótona **em tamanho**
(1.046 → 27,0% · 3.231 → 24,7% · 15.308 → 21,7% · 14.456 → 19,5% · 32.920 → 10,7%),
não em curadoria.

> **Logo: o que o agente vê não é decidido pela relevância que o próprio sistema
> atribui, e sim pela capacidade fixa e pequena da superfície.** Coleção pequena é
> coberta exaustivamente porque cabe; coleção grande não é coberta por mais
> relevante que seja. `lesson` está em 100% porque tem 53 linhas, não porque é
> lição.

## 3. Por que a intervenção não podia funcionar — e é a mesma medida

A capacidade da superfície do brief, em janela **fechada**
`[2026-08-20 , 2026-08-27)`:

| | |
|---|---|
| slots servidos | **46.295** em **4.632** briefs |
| chunks **distintos** | **201** |
| chunks presentes em **100%** dos briefs | **3** |
| top-10 chunks | **47,16%** de todos os slots · top-20: **61,46%** |

⚠️ O total histórico de slots (≈580 mil desde 04/06) é **série viva** e por isso não
entra no guarda: travar série viva faz o guarda falhar por passagem do tempo, e
guarda que grita sozinho deixa de ser lido. A primeira versão desta seção citava
`5.199 briefs` de uma janela `date('now','-7 day')`; em minutos virou 5.206, e o
`--assert-json` pegou. É o mesmo defeito que já custou uma retratação aqui.

O mecanismo, do código: comparador **lexicográfico** (`last_served` decide antes
de `salience` ser consultada), e bônus **aditivo** em `salience` só age nos slots
de cobertura — `freshSlots = 2` de 10. ⚠️ Esse 2 é **default de configuração**
(`DIVERSITY_DEFAULTS`, sem override na unit nem no `.env` — verificado) e é
**teto** dos slots preenchidos, não cota: `brief_log` não tem coluna de origem de
slot, então a divisão 8/2 não é observável no registro. Medido em 350 briefs com
replay fiel 350/350: teto de **17/350 = 4,86%** dos briefs, saturando em
`w ∈ (4,0; 4,4]`.

**Não são dois resultados, é um.** Uma superfície de capacidade fixa não se move
com bônus de score — e o teto de 4,86% é o mesmo fato que os 201 distintos por
semana, visto pelo lado da intervenção.

## 4. O que NÃO se pode afirmar, e uma inversão que quase entrou

⚠️ **Comparação brief-vs-busca DENTRO de janela é impossível hoje.**
`search_telemetry.top_chunk_ids` — o único instrumento com timestamp por chunk —
parou em **2026-05-19 14:47:04** e tem **zero** linhas na janela comum.

E aqui a classificação mudou depois de eu procurar o motivo, o que importa porque
"desligada de propósito" seria escolha de desenho a respeitar e "apagada" é
regressão a consertar. O commit `7fdaab4f` (*"eod: 2026-05-19 — nox-mem repair
(import mismatch)"*) **removeu** o `INSERT` de 23 colunas junto com o tipo
`topChunkIds?: number[]`, num commit de fim de dia que também mexeu em
`CONTEXT.md` e em memória de agentes; sobrou o `INSERT` de 7 colunas em
`src/search.ts:608`. **13 colunas** ficaram sem nenhum escritor
(`top_chunk_ids`, `top_scores`, `requesting_agent`, os 3 `reason_boost_*`, os 2
`temporal_*`, os 5 `reranker_*`).

Este projeto **registra** retirada deliberada com `CUT` no título do commit (ex.:
*"CUT E05b reason-boost — bias arquitetural confirmado"*). **Não existe `CUT`
para esta telemetria** ⇒ regressão, sem ninguém notar por 3,3 meses. Logo religar
o escritor é proposta legítima, não violação de desenho.

⚠️ **E a comparação INVERTE quando escopada.** Cumulativamente a busca alcança 617
das 865 entities curadas contra 245 do brief, o que sugere "a busca alcança o
acervo curado e o brief não". Na **janela comum** (2026-06-04 →): brief **245**,
busca **≥ 151**. O brief alcança *mais*. A frase anterior era artefato de comparar
períodos diferentes — a busca tinha 6,5 semanas extras, quase todas no período em
que a instrumentação ainda gravava.

⚠️ **O limite inferior protege a direção chata.** `last_accessed_at` guarda só o
último acesso, então exposição-na-janela é um **limite inferior**: sustenta
"invisibilidade no MÁXIMO tanto", não "no mínimo tanto". Para a alegação de
invisibilidade **alta** vale só o cumulativo, que é exato.

## 5. Não existe desfecho a jusante instrumentado — e o reframe não precisa de um

Inventário, medido:

| candidato | estado |
|---|---|
| `search_telemetry` (buscas/dia) | ⛔ **é o canário, não o agente.** Janela fechada `[20/08, 27/08)`: **325 de 343 linhas (94,8%)** caem nos minutos do cron `22,52 * * * *` (± 1 min) do `semantic-canary.sh`. Sobra **2,6 linha/dia** que possa ser agente |
| `answer_telemetry` | ⛔ **0 linhas** |
| `confidence_eval_log` | ⛔ **0 linhas** |
| `agent_events` | ⛔ **0 linhas** |
| diversidade de cobertura por dia (`brief_log`) | ✅ tem variância real (35 → 49 → 87 → 193 → 141 distintos/dia) mas ⚠️ **não estacionária**, com mudança de regime em 21–22/08 |

⚠️ **A evidência do canário foi trocada, e o motivo é a mesma lição.** A primeira
versão desta linha apoiava a conclusão em *"`requesting_agent` não populado"*.
Isso não distingue nada: aquela coluna é nula para **todo mundo** porque o
escritor dela foi apagado no `7fdaab4f` (§4). Um campo sem escritor não é
assinatura de origem — é ausência de instrumento. O teste que separa de fato é o
**minuto do cron**, acima, e ele é forte: 94,8% em dois minutos por hora.

As três tabelas que mediriam qualidade voltada ao agente estão **vazias**. Logo a
escolha honesta é uma de duas: instrumentar algo novo (trabalho real, atrasa o
estudo) **ou** escrever o paper que não precisa disso.

**O reframe é o segundo caso, e isso é a maior simplificação disponível:** a
manchete (§1–§3) é medição de superfície e mecanismo, e a evidência interventiva do
teto **não exige randomização nem desfecho a jusante**, porque o dual-compute
**observa** o contrafactual por brief. Os itens 2 e 4 do protocolo passam a ser
opcionais — só voltam a morder se a alegação interventiva for promovida a manchete.

## 6. O que fica declarado como limite

- `access_count` é "retornado por busca alguma vez", sem histórico por evento. Não
  dá para dizer **quando** nem **quantas** vezes por janela;
- os tipos pequenos (`decision` n=11, `person` n=14, `feedback` n=17) não sustentam
  leitura individual — entram só no teste de correlação;
- `distinct/slots` por dia tem quebra de regime em 21–22/08 e precisa de explicação
  antes de virar desfecho;
- a diversidade de cobertura é medida **na mesma superfície** onde a intervenção
  age; usá-la como desfecho exige declarar que é estimando de política, não efeito
  sobre o agente.
