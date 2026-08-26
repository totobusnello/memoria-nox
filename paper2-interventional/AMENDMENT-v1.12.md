# Emenda v1.12 — Interventional Memory

**Registro emendado:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
`10.5281/zenodo.21978476` (concept `10.5281/zenodo.21964093`)

**Versão:** v1.12. O último depósito efetivo é a **v1.11** (2026-08-17); nada foi
publicado sob o número v1.12, e esta é a primeira redação a ser depositada com
ele.

**Redigida:** 2026-08-25. **Uma** emenda, conforme decidido em 2026-08-19.

**Código servindo.** Último commit que tocou `src/`: **`1464db87`**
(2026-08-22T01:04:13+02:00). Pinos por arquivo, para os cinco que esta emenda
transcreve ou cita por linha:

| arquivo | commit | data |
|---|---|---|
| `src/api/brief.ts` | `c3c14c19` | 2026-08-22T00:57:18+02:00 |
| `src/paper2/brief-outcome.ts` | `c3c14c19` | 2026-08-22T00:57:18+02:00 |
| `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55-03:00 |
| `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23-03:00 |
| `src/search.ts` | `aee41849` | 2026-06-07T21:42:53-03:00 |

⚠️ Uma redação anterior escrevia *"commit `2740ded3` (2026-08-25T02:43:16Z)"*.
`2740ded3` era apenas o `HEAD` daquele dia — um commit de encerramento de sessão
que **não tocou `src/`**. Citar o `HEAD` é citar um artefato cuja relação com a
afirmação é incidental, e que envelhece: em 2026-08-26 o `HEAD` já era
`5466276b`, também sem nenhuma mudança em `src/`. Os pinos acima são estáveis
porque nomeiam o commit que produziu **cada** trecho citado.

**Janela de piloto — FECHADA.** Todo número de série desta emenda é computado
sobre `[2026-08-21T22:57:00Z ; 2026-08-25T10:22:00Z]`, e **somente** sobre ela.
A série continua crescendo em produção (o cron produz 28 registros/hora), então
qualquer contagem citada como instante envelheceria dentro de um depósito
imutável. Os números são emitidos por `pilot_window_stats.mjs` e congelados em
`PILOT-WINDOW-2026-08-25.json`; o script aceita `--assert-json` e falha se a
janela deixar de reproduzir o snapshot.

⚠️ Este é o conserto de um defeito encontrado na própria redação: uma versão
anterior citava `n = 2.256` como medido "às 10:22Z", quando 2.256 era a contagem
de um instante posterior (~11:25Z). Na janela declarada o valor é **2.221**. O
rótulo e a medição não correspondiam.

---

## §0. Natureza e limites desta emenda

Esta emenda é **descritiva**. Ela declara fatos sobre o mecanismo de serving, o
corpus e a série de piloto; retrata afirmações anteriores; e nomeia os defeitos
que precisam ser corrigidos antes que o estudo confirmatório comece.

Ela **não** especifica estimando, não fixa `N`, e não estabelece efeito causal.
Três razões, todas verificáveis:

1. **Não há desfecho observado sob tratamento.** Em 2.221 de 2.221 registros
   (2026-08-21T22:57Z a 2026-08-25T10:22Z), `modo = "shadow"` e
   `servido = "controle"`. O braço tratado é computado, logado e descartado.
2. **A regra de designação não está congelada de forma válida** (§5). Enquanto
   quem recebe tratamento depender de uma constante cujo referente esta emenda
   retrata, e enquanto o desempate registrado não estiver implementado, não há
   população tratada estável para a qual especificar um estimando.
3. **Qualquer estimando redigido agora seria pós-observacional.** A série de
   piloto foi observada antes desta redação. Escolher o que estimar sabendo o
   que é estimável é um grau de liberdade do pesquisador, e nenhuma exatidão
   aritmética o dissolve.

**Consequência declarada:** os 2.221 registros são **piloto descritivo**. Não
entram em análise confirmatória. O estimando, o estimador, a variância e a
população-alvo vão em **registro prospectivo separado**, posterior a esta emenda
e às correções do §5, rotulado como informado pelo piloto.

**E o que esta emenda *é*, positivamente:** a descrição de uma série de decisões
de serving **condicional à designação que foi de fato executada** — não a uma
regra re-executável. Em 4 dos 19 grupos de assinatura o designado saiu da ordem
incidental de linhas do SQLite (§5.2-bis), e a designação é recomputada a cada
brief. Os agregados (111 deslocamentos, 8,1%, tabela de autoria do §3.3) são
**reproduzíveis** — o snapshot os congela — e **não são atribuíveis** a uma regra
determinística. Toda leitura desta emenda como medição de mecanismo, e não como
descrição de execução, está fora do que ela sustenta.

O termo **"by construction"** não é usado nesta emenda em nenhuma afirmação
substantiva: foi a frase que carregou os defeitos de 16 e 17/08, e a v1.11
mostrou que uma garantia dessa forma pode ser anulada por falha operacional.

---

## §1. O mecanismo de serving

### 1.1 O que o registro modela, e por que não descreve o sistema

O registro modela a entrada de um chunk nos slots de cobertura como **cruzar um
limiar**. Três formas dessa afirmação caem:

- **Não existe comparação com limiar no código.** `pick`, fase 3, toma os
  primeiros `freshSlots` do pool já ordenado; não há comparação com constante.
- **O cut não é constante do sistema.** O campo `cut_principal` de
  `CUTS-MEASURED-2026-08-18.json` é agente-heterogêneo: **0,610 a 0,792**, span
  0,182 (nox 0,6851 · atlas 0,7613 · boris 0,6925 · …).

  > ⚠️ **Um nome, duas coisas — e a confusão é o achado, não um descuido da
  > redação.** `cut_principal` (o campo, medido) e "main-pool cut = 0,8524" (o
  > registro, `PREREG-DRAFT.md:438`) **nomeiam a mesma grandeza** e **não têm o
  > mesmo valor**: 0,8524 está **fora** do span 0,610–0,792 medido em 18/08.
  >
  > A leitura correta não é "há duas quantidades e uma colisão de nome". É:
  > **existe uma grandeza, ela é agente-heterogênea, e o registro publicou a
  > medição de um agente como se fosse constante do sistema.** Um valor fora do
  > span medido não é uma segunda quantidade — é a mesma, mal generalizada.
  >
  > Consequência de leitura: onde esta emenda escreve "cut do pool principal =
  > 0,8524", está **citando o registro**, nunca uma medição vigente. Duas
  > revisões adversariais independentes (2026-08-25 e 2026-08-26) reportaram este
  > ponto como colisão de referente; a segunda depois de uma primeira tentativa
  > minha de desambiguar. Duas leituras tropeçando no mesmo lugar é evidência
  > sobre a redação, então ela está agora enunciada como achado, e não como
  > ressalva.
- **Publiquei quatro valores em quatro dias** (0,7342 → 0,744495 → 0,7345 →
  0,684477) tratando cada um como "a barra". Não são medições concorrentes do
  mesmo parâmetro: são **estados** de um estoque em dreno, medidos em datas
  diferentes.

⚠️ **Correção de identificação.** Uma redação anterior desta emenda atribuiu a
`CUT_FRESH` o valor **0,8524**. Errado: o registro distingue **cut do pool
principal = 0,8524** de **cut do slot de cobertura = 0,7342**
(`PREREG-DRAFT.md:438`), e o congelado como `CUT_FRESH` é **0,7342**
(`PREREG-DRAFT.md:525`). A confusão importa porque é `0,7342` — não `0,8524` —
que a regra de designação consome (§5).

### 1.2 O que o código executa

Duas funções decidem, e são reproduzidas aqui em vez de referenciadas por path
(o defeito de reprodutibilidade do §7).

**`coverageCompare`** — `src/api/brief-diversity.ts:130-140`:

```js
export function coverageCompare(aLastServedMs, aSalience, bLastServedMs, bSalience) {
  const al = aLastServedMs ?? Number.NEGATIVE_INFINITY; // nunca-servido primeiro
  const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
  if (al !== bl) return al - bl;   // ASC — chave DOMINANTE
  return bSalience - aSalience;    // empate — salience decide
}
```

**`ordenarCobertura`** — `src/api/brief.ts:607-618`, onde a dose entra:

```js
const eff = (c) => c.salience + (boosts?.get(c.row.id) ?? 0);
ranked.sort((a, b) => coverageCompare(a.lastServedMs, eff(a), b.lastServedMs, eff(b)));
```

`lastServedMs` provém de `MAX(served_at)` em `brief_log`, convertido por
`parseDbDateMs` (`src/api/brief.ts:270-273`, que é `Date.parse` sem truncamento).
`served_at` é gravado por `datetime('now')`: **zero de 559.158 linhas** têm fração
de segundo. Logo `lastServedMs` é sempre múltiplo de 1000, e igualdade em
segundo e em milissegundo são o mesmo conjunto neste dado.

Consequência: `last_served` é a chave dominante; `W_OUTCOME`, somado à salience,
atua **somente entre candidatos cujo `last_served` é igual**.

### 1.3 O que a salience faz não é desempatar — é selecionar

Uma redação anterior chamou a salience de "critério de desempate" e nomeou o
estimando "inversão de desempate". A medição não sustenta essa palavra:

| quantidade | medida |
|---|---|
| slots de cobertura por brief (`fresh_added`) | **2**, em 2.221 de 2.221 registros |
| itens no brief (`ids_controle`) | 10, em todos |
| chunks no grupo de `last_served` da frente do pool | **12 a 31** (amostra de 6 decisões) |

Com 12–31 candidatos empatados disputando 2 slots, a salience não resolve um
empate residual: ela **seleciona 2 entre 12–31**. `last_served` escolhe o
*bloco*; a salience aloca os slots dentro dele. A dose atua sobre uma seleção,
não sobre um desempate.

Isso retrata o vocabulário e, com ele, o estimando que dele derivava (§4,
retratação 12).

### 1.4 O canal, medido

O canal não estava previsto no registro, então é caracterizado empiricamente.
Sobre a série de piloto (2.221 registros, 2026-08-25T10:22Z):

| quantidade | valor |
|---|---|
| registros com `churn > 0` | **102** |
| deslocamentos (soma de `churn`) | **111** |
| magnitude: 1 item de 10 | 93 registros |
| magnitude: 2 itens de 10 | 9 registros |
| registros em que **todos** os chunks envolvidos compartilham o mesmo `last_served` | **100 de 102** |
| registros com algum envolvido **nunca-servido** (`NULL`) | **0 de 102** |

Os 2 registros restantes têm `last_served` distintos entre os envolvidos. Não
são declarados como violação do mecanismo: a reconstrução usada aqui recupera o
estado por `MAX(served_at) < timestamp da decisão`, o que não isola o segundo do
próprio registro, e essa é a explicação mais simples. O teste mais estrito —
excluindo o segundo da própria decisão — deu **86/86 sem violação** em revisão
adversarial independente de 2026-08-24 (recibo
`adversary-receipt-kimi-2026-08-24T195720`), sobre a série então disponível.

**Duas afirmações ficam retratadas aqui**, ambas erradas na mesma direção:

- que a salience decidiria "entre nunca-servidos" — **0 de 102** registros têm
  envolvido nunca-servido;
- que o canal primário seria o grupo `NULL` — o mesmo dado o refuta.

Na população deste estudo, o grupo `NULL` esteve vazio: os 55 chunks foram
servidos pela primeira vez entre 2026-08-22T19:23:43 e 21:07:19, antes de o gate
de maturidade abrir.

### 1.5 `Δ_cut` perdeu referente

`Δ_cut = 0,043` foi medido como spread no cut do brief. Sem cut, a quantidade não
tem referente. Esta emenda **não** propõe definição nova: renomear a constante
preservando o valor seria trocar o rótulo e manter a aritmética, que é a classe
de defeito da retratação 2. `Δ_cut` fica declarado como **pendente de definição
operacional e de medição**, e é pré-requisito do registro prospectivo (§5).

---

## §2. λ — a taxa de falha adjudicada

Rodada de painel de 2026-08-21, 870/870 chamadas. Declaração da seed pushada
22:17:50Z; rodada `31515871` emitida 22:22:57Z — precedência verificável.

λ̂ é **Horvitz-Thompson estratificado**, não proporção simples:

**População-alvo: 1.305 episódios** — universo dos epochs 2026-08-15 → 08-20,
fronteira 09:00 UTC (`LAMBDA-SEED-2026-08-21.md:36`). Desenho travado **antes**
da amostra, no mesmo documento:

| estrato | frame | amostra | adjudicados | falhas |
|---|---|---|---|---|
| A (`is_error`) — **censo** | 48 | 48 | 46 | 44 |
| B (complemento) — **amostra** | 1.257 | 242 (**19,25%**) | 234 | 11 (4,70%) |
| | **1.305** | **290** | **280** | |

| | |
|---|---|
| peso HT do estrato B | **5,194215** = 1.257 / 242 |
| inadjudicáveis (abaixo do piso de 3 vereditos) | 10 de 290 (3,45%) — 2 em A, 8 em B |
| **λ̂** | **0,077499** |
| SE | 0,012023 |
| **IC95** | **[0,0539 ; 0,1011]** |

Reprodução completa: `(44 + 5,194215 × 11) / 1.305 = 101,136 / 1.305 = 0,077499`
e `0,077499 ± 1,96 × 0,012023 = [0,0539 ; 0,1011]`.

Seleção do estrato B: ordenação por `SHA256(seed ‖ "|" ‖ episode_id)` e tomada
dos 242 primeiros — amostra pseudoaleatória sem reposição, `seed` declarada e
pushada antes da rodada (`LAMBDA-SEED-2026-08-21.md:66-75`). Os 10
inadjudicáveis ficam **fora do numerador e dentro do denominador**.

⚠️ A taxa de projeto declarada no desenho é **19,235%** ("idêntica à das
extensões 1 e 2", `LAMBDA-SEED-2026-08-21.md:41`); a taxa **realizada** é
`242/1.257 = 19,25%`. Os dois números não são o mesmo e nenhum deriva do outro —
o de projeto é herdado das extensões anteriores, o realizado é o quociente. O
peso HT usa o realizado.

⚠️ **Publicado por exigência de reconstrução** (GLM, 2026-08-25): a versão
anterior desta tabela dava o peso `5,194215` e os *adjudicados*, mas não o
denominador nem os tamanhos de frame e amostra. Quem tentasse reconstruir a
população multiplicando `234 × 5,194215 + 46` chegaria a **1.261,4** e a λ̂
`0,0802` — o peso divide o frame pela **amostra** (242), não pelos adjudicados
(234), e o estrato A tem frame 48, não 46. A lacuna era documental, não
aritmética, mas num depósito imutável é o mesmo defeito.

⚠️ **Nota de leitura, registrada porque duas revisões adversariais tropeçaram
aqui.** λ̂ **não** é `22/280 = 0,0786`, e o IC não é binomial. Sob Wald com
n = 280 o intervalo seria [0,047; 0,110] — diferente do publicado. Quem reconstruir
λ̂ como proporção simples encontrará inconsistência aparente; o estimador é HT
com o SE acima.

**Reconciliação com o registro.** O `~30%` registrado é *share das falhas*; o
parâmetro do desenho é `p̂0 = 0,111813`, taxa de falha entre **oportunidades**.
λ̂ = 7,75% é taxa entre **todos os episódios** — denominador mais largo. Uma taxa
menor num denominador mais largo é o esperado: λ̂ é **consistente** com o desenho.
Fica retratada a afirmação de que λ̂ seria "4× menor que o registrado", que
comparava referentes distintos.

**Limitação: o estrato S2 repousa numa família do painel.** Share de S2 nas
próprias falhas: moonshot 24,2% · zhipu 25,9% · **xai 72,2%**. Dos 22 S2
consolidados, **22 têm `xai = S2`**; sem xai sobreviveriam 5. Como
`W_OUTCOME ∝ severity` e a §2 do registro trata "S2 e acima" como população
tratada, o tamanho dessa população depende da calibração de severidade de uma
família de modelo.

⚠️ E isso **não** é auditável por leave-one-family-out: com 3 painelistas a
mediana inferior é o valor do meio; com 2, é o **mínimo**. O estimador muda junto
com a remoção, então o teste não isola o efeito do painelista. Declarado como
limitação, sem correção proposta.

---

## §3. A série de piloto

### 3.1 Composição

| dia civil | registros | `churn > 0` | dos quais pós-gate | taxa **pós-gate** |
|---|---|---|---|---|
| 21/08 (parcial, desde 22:57Z) | 30 | 0 | 0 | — (pré-gate) |
| 22/08 | 672 | 0 | 0 | — (pré-gate) |
| 23/08 (dois hiatos, §6) | 560 | 42 | 308 | **13,6%** |
| 24/08 | 672 | 49 | 672 | **7,3%** |
| 25/08 (parcial, até 10:22Z) | 287 | 11 | 287 | **3,8%** |
| **total** | **2.221** | **102** | **1.267** | **8,1%** |

⚠️ **A coluna de taxa é pós-gate, e a distinção não é cosmética.** Dividir os 42
eventos de 23/08 pelos 560 registros do dia civil dá **7,5%** — número que uma
redação anterior desta tabela publicava. Ele mistura no denominador as 252
decisões de 23/08 anteriores às 09:00Z, que são pré-gate e têm zero por
construção mecânica (§3.2). É a **mesma contaminação de denominador** da
retratação 14, uma linha abaixo na mesma emenda. A taxa pós-gate de 23/08 é
`42/308 = 13,6%`.

Dia completo = 672 registros = 96 ciclos × 7 personas (cron nos minutos
07/22/37/52, 4 ciclos/hora). O dia 21/08 tem 30 registros porque a coleta começou
às 22:57Z, e não fecha em múltiplo de 7 por ter sido interrompida em ciclo
parcial: o ciclo das 22:52Z cavalgou o início da janela (22:57Z), entrando com 2 das 7 personas.

### 3.2 O zero das primeiras 954 decisões é o gate de maturidade

Os 280 registros de `p2_verdict` foram escritos em **2026-08-21T22:51:23 — um
único segundo**. O gate (`src/paper2/brief-outcome.ts:162-173`, PR #47) exige
`written_at <= epochInicio − 24h`, e epochs abrem às 09:00Z:

| epoch | corte | batch maduro? | consequência |
|---|---|---|---|
| 22/08 | 21/08 09:00 | **não** (escrito 22:51) | mapa de boost vazio ⇒ `churn = 0` |
| 23/08 em diante | 22/08 09:00 | **sim** | boost existe |

Medido: **954 decisões nos epochs 21–22/08, `churn > 0` em 0.** ⚠️ O corte é por **epoch**, não por dia civil: como epochs abrem às 09:00Z, o epoch 22/08 cruza a meia-noite, e 954 = 30 (21/08) + 672 (22/08) + **252 registros de 23/08 anteriores às 09:00Z**. Quem recensear pela tabela do §3.1, que é por dia civil, encontrará 702 e deve somar esses 252. Esse zero é
efeito do gate registrado — não de população ausente, não de mecanismo inerte,
não de hardware.

Ficam retratadas as duas explicações anteriores para esse zero: "ausência de
população" (2026-08-22) e "inércia arquitetural do boost" (2026-08-24).

### 3.3 Ativação, com o denominador correto

Porque as 954 decisões pré-gate têm zero por efeito do gate, incluí-las no
denominador mistura um artefato mecânico com a quantidade de interesse:

| denominador | taxa |
|---|---|
| série inteira (2.221) | 4,6% ← **não usar** |
| **decisões pós-gate (epochs ≥ 23/08, n = 1.267)** | **8,1%** |

**8,1%** é a taxa a citar. Fica retratado o 4,6% de redações anteriores.

**Autoria do deslocamento, quantificada** na janela congelada:

| | ids distintos | do estudo | eventos | do estudo |
|---|---|---|---|---|
| **entram** sob tratamento | 16 | **16 (100%)** | 111 | **111 (100%)** |
| **saem** | 33 | 25 (75,8%) | 111 | 99 (89,2%) |

Todo deslocamento é causado por um chunk da população do estudo, sem exceção nos
111 eventos. Do lado que sai, 89,2% dos eventos também atingem chunks do estudo
— não-designados. Isso é o mecanismo previsto: a regra designa um chunk por
grupo de assinatura, o pool mistura designados e não-designados, e a dose atua
sobre essa mistura.

⚠️ **Ler "designa" a menos do §5.2-bis.** A designação é determinística **só até
o empate**: em 4 dos 19 grupos ela caiu na ordem incidental do SQLite, e é
recomputada a cada brief. Os 16 ids que entram são portanto a **união dos
conjuntos designados ao longo da série**, não um conjunto estável de designados
— o "100% do estudo" sobrevive, a leitura de "os 16 designados" não. Os 12 eventos de saída (10,8%) que atingem chunks de fora do
estudo são o contato da intervenção com o resto do corpus.

### 3.4 A série ainda não depletou — e as duas leituras são indistinguíveis

Série horária pós-gate na janela congelada — **47 horas, 1.267 registros, 102
eventos**, que fecha exatamente com o agregado do §3.3:

| estatística | valor |
|---|---|
| média das taxas horárias | **7,8%** |
| mediana | 3,6% |
| mínimo — máximo | **0,0% — 46,4%** |
| horas com zero eventos | 14 de 47 |

A série completa está em `PILOT-WINDOW-2026-08-25.json`
(`serie_horaria_pos_gate.taxas_pct`), emitida pelo script.

O que o dado sustenta: a série **ainda não depletou** — o último dia da janela
tem 11 eventos — e tem **variância horária alta** (0% a 46,4%, mediana 3,6%
contra média 7,8%: distribuição assimétrica com cauda de rajadas). Médias
diárias pós-gate: 13,6% → 7,3% → 3,8%.

⚠️ **O que o dado NÃO sustenta, e fica retratado:** que a série "oscila sem
tendência". Três médias diárias decrescentes não identificam ausência de
tendência mais do que identificam depleção; com 47 horas e essa variância,
nenhuma das duas leituras é distinguível.

🔴 **Retratado nesta versão** (GLM, 2026-08-25): a redação anterior fechava com
"incompatível com depleção monotônica até zero … e nada além". Na leitura estrita
("não depletou *dentro da janela*") isso se sustenta; na leitura larga
("incompatível com um processo de depleção em curso") é **refutado pelo próprio
dado** — 13,6 → 7,3 → 3,8 é estritamente decrescente e compatível com transiente
que atingiria zero *depois* da janela. Enunciado defensável: **ainda não
depletada; compatível tanto com regime persistente quanto com transiente
decrescente não concluído.** Escolher entre os dois exige janela maior.

Fica retratada também a leitura de 2026-08-24 de que a série seria um transiente
de depleção monotônica até zero: ela se apoiava num recorte de cinco pontos
decrescentes.

> ### 🚫 SUPERADO — os números deste bloco NÃO são desta emenda
>
> Todo valor entre as marcas 🚫 abaixo é **retratado**. Nenhum deles descreve a
> série vigente, que é a das **47 horas / 1.267 registros / 102 eventos** da
> tabela acima. Este bloco existe para que o registro superado fique legível,
> não para ser lido como medição.
>
> 🚫 Uma versão anterior deste §3.4 publicou uma série de **25 valores** que
> somava **85 eventos**. Quem calcular a média sobre ela obtém ~12%, e esse
> número **não é uma taxa desta emenda** — é aritmética sobre um recorte
> defeituoso. O recorte começava em 2026-08-23T15:52Z, a **retomada da coleta
> após a migração**, e não na abertura do gate às 09:00Z, com regra de seleção
> não declarada. Pior: era o único número da emenda que não estava no snapshot
> nem era computado pelo script, de modo que o `--assert-json` não o protegia. 🚫
>
> A série agora é emitida pelo script e congelada em
> `PILOT-WINDOW-2026-08-25.json`.
>
> ⚠️ **Por que a quarentena é explícita.** Uma revisão adversarial de 2026-08-26
> leu este parágrafo como se os 25 valores fossem a série corrente, recomputou a
> média em 12,1% e reportou divergência contra os 102 congelados. A leitura era
> compreensível: o parágrafo citava os números retratados e os vigentes na mesma
> frase, e a única marca de tempo passado era o verbo. Num depósito imutável,
> texto que **pode** ser lido como vigente **será**.

### 3.5 A ativação medida é de um batch, e é teto

A população nasceu em **um único segundo**. Os 55 chunks compartilham
`written_at` e `created_at`, entram e saem do pool em bloco, e formam grupos de
empate grandes e sincronizados. A ativação medida descreve **um batch**, não um
regime de ingest contínuo. Ressalva já registrada no próprio drop-in de
configuração (`p2s1-active.conf`): *"o soak não testa o mecanismo sob carga — o
corpus está estático desde 10/07."*

E é **teto**, não estimativa: sob `active`, o item tratado servido gravaria
`brief_log`, avançaria seu `last_served` e sairia do grupo de empate —
realimentação que o modo `shadow` não exercita, porque toda decisão seguinte
parte de um estado gerado pela trajetória de controle.

⚠️ **A ativação medida não entra no dimensionamento de `N`.** E o enunciado
precisa ser mais cuidadoso do que "N deriva de λ̂, ICC e MDE pré-especificados",
porque essa pipeline não está mais vigente: o `N = 234` registrado derivava de
λ̂, ICC e MDE pré-especificados **para o estimando retirado na retratação 12**, e
λ̂ não migra automaticamente para um estimando novo. O sizing vai ao registro
prospectivo, junto com o estimando. Em nenhuma das duas situações — nem a
registrada, nem a nova — os 8,1% entram nele.

---

## §4. Retratações consolidadas

| # | data | retratado | o que substitui |
|---|---|---|---|
| 1 | 16/08 | o §2 registrava artefato (script de alocação com hash de commit) que não existia | artefato criado e versionado |
| 2 | 17/08 | DE de cluster vindo de fórmula inaplicável ao desenho de 1–115 sessões | `N` re-derivado 174 → 234 |
| 3 | 18/08 | entrar nos slots de cobertura é "cruzar `CUT_FRESH`" | não há limiar no código (§1.1) |
| 4 | 20/08 | "a barra" como parâmetro — 4 valores em 4 dias | não há barra; é estoque em dreno (§1.1) |
| 5 | 21/08 | a intervenção é nula em todos os braços | não é nula; a designação mistura o pool (§3.3) |
| 6 | 21/08 | "três platôs" de dose-resposta | aritmética sem desfecho; margens 0,0070/0,0035 contra spread de 0,1822 |
| 7 | 22/08 | `churn = 0` mede ausência de população | mede o gate de maturidade (§3.2) |
| 8 | 24/08 | o boost é arquiteturalmente inerte | atua, e o canal existe: 111 deslocamentos em 102 decisões (§1.4) — ⚠️ agregado condicional à designação executada (§5.2-bis) |
| 9 | 24/08 | a série é transiente de depleção monotônica | **ainda não depletada**; as duas leituras são indistinguíveis em 47 h (§3.4) |
| 10 | 24/08 | a transição coincide com a migração de host | coincide com o gate, 2h37 antes do snapshot (§6) |
| 11 | 25/08 | a salience decide "entre nunca-servidos" | 0 de 102 envolvem nunca-servido (§1.4) |
| 12 | 25/08 | a salience "desempata", e o estimando é "inversão de desempate" | ela **seleciona 2 entre 12–31** (§1.3); estimando retirado, vai a registro prospectivo (§0) |
| 13 | 25/08 | `CUT_FRESH = 0,8524` | 0,8524 é o cut do pool **principal**; `CUT_FRESH` é **0,7342** (§1.1) |
| 14 | 25/08 | a taxa de ativação é 4,6% | 8,1% pós-gate; 4,6% contamina o denominador (§3.3) |
| 15 | 25/08 | `w_min` é função apenas da severidade porque `written_at` é idêntico | `salienceBase` não tem termo em `written_at` e tem termo log-proporcional em `access_count`; 9 bases distintas (§5.2-bis) |
| 16 | 25/08 | o empate de `w_min` ocorre em **5 de 7** grupos, na severidade **mínima** | **4 de 7**, na severidade **máxima** — `w_min` decresce em severidade (§5.2-bis) |
| 17 | 25/08 | a série é "incompatível com depleção monotônica até zero, e nada além" | sustenta-se só na leitura estrita; a larga é refutada por 13,6 → 7,3 → 3,8 (§3.4) |
| 18 | 26/08 | "código servindo: commit `2740ded3`" | era o `HEAD` do dia, um `chore` que **não tocou `src/`**; o pino estável é `1464db87` mais os cinco por arquivo (cabeçalho, §7) |
| 19 | 26/08 | o título do §3.4, "a série oscila; não decai" | o corpo do próprio §3.4 já retratava as duas metades; título trocado |
| 20 | 26/08 | taxa de 23/08 = **7,5%** na tabela do §3.1 | `42/560` mistura 252 decisões pré-gate; pós-gate é `42/308` = **13,6%** — a contaminação da retratação 14, reincidindo na mesma emenda (§3.1) |
| 21 | 26/08 | o Anexo A citava `p2-serving.ndjson` como fonte | esse nome não existe no depósito; a fonte depositada é `p2-serving-WINDOW-2026-08-25.ndjson`, o recorte da janela (7 citações) |
| 22 | 26/08 | Anexo A: "amostra B 242 (19,235%)" | põe num parêntese só a contagem realizada e a taxa **de projeto**, como se uma derivasse da outra; realizada é `242/1.257` = 19,25% (§2) |
| 23 | 26/08 | a capa do depósito dizia "everything measured … **over a historical corpus**" | verdade na v1.11; a v1.12 acrescenta 2.221 decisões de serving **ao vivo** e a rodada de painel sobre episódios de 15–20/08. Segue pré-tratamento, não segue só-corpus (`DEPOSIT-README.md`) |
| 24 | 26/08 | a capa listava `PREREG-DRAFT.md` como "the central document (v1.11)" e não mencionava a emenda | a emenda é a razão de existir a v1.12 e não aparecia na capa; guia de arquivos reescrito com os 12 novos, e os renders `PREREG-v1.11-*` declarados como **não** re-renderizados |

| 25 | 26/08 | o §7 dizia "isto mitiga, não resolve — o registro prospectivo deve carregar o blob" | adiava um conserto que não precisava de adiamento; os 5 módulos vão **nesta** versão, com `SERVING-CODE-MANIFEST.md` (§7) |
| 26 | 26/08 | o §3.4 citava os números retratados e os vigentes na mesma frase | quarentena explícita 🚫: uma revisão de 26/08 leu os 25 valores como série corrente e recomputou média 12,1% (§3.4) |
| 27 | 26/08 | o §1.1 tratava `cut_principal` × 0,8524 como ressalva de leitura | é **achado**: uma grandeza agente-heterogênea cuja medição de um agente foi publicada como constante; duas revisões tropeçaram (§1.1) |
| 28 | 26/08 | duas faixas de linha citadas estavam deslocadas | `brief-diversity.ts:131-142` (a função é **130-140**; a faixa começava no meio da assinatura e invadia a `interface` seguinte) e `brief.ts:608-618` (é **607-618**, perdia a linha do `function`). Descoberto **porque** os blobs foram depositados — o §7 se auto-verificou |
Correções pontuais que permanecem válidas:

- **`0,7344` supera 4 dos 6 agentes**, não 5 (lex, nox, boris, forge; não atlas
  nem cipher).
- **O contraste primário é pooled 117 vs 117** (`§3:344-351`). A linha 521 do
  registro está errada e é a fonte do engano.
- **O boost entra no estágio `ranked.sort` (JS)**, não no pré-rank SQL. O
  pré-rank não tem termo de recência; se o boost entrasse ali, o degrau de
  severidade e o span de recência não existiriam. O registro dizia apenas *"in
  the coverage-slot ranking"*, sem nomear o estágio.
- **`memory/entities/%` contribui zero** ao pool incumbente: os 190 chunks têm
  42,1 a 78,9 dias contra janela de 30, e são excluídos pela `WHERE` de
  `fetchFreshCandidates`. Confirmado por medição.
- **`source_date` registra o evento de ingest, não a proveniência.** Os 52
  chunks de `lessons.md` carregam uma única data. Re-ingest **rejuvenesce o
  arquivo inteiro**, para elegibilidade e para o termo de recência. A taxa de
  autoria não é estimável de `created_at`; os "232 chunks em 7 dias" citados
  antes são provavelmente artefato de re-ingest, e ficam retirados.
- **Proveniência do seeding sintético:** `cuts_measure.mjs:28-29` planta
  `max(1, ceil(396 × share))`, forçando ≥1 S4/dia onde Poisson daria ~0,32. As
  fotos derivadas dali são **piso**, não estimativa.
- **Unidade das shares:** por-veredito (S1 69,73 / S2 29,62 / S3 0,58 / S4 0,08)
  vs consolidada por-episódio (S1 78,93 / S2 21,07 / S3 0 / S4 0). O registro usa
  a primeira; a análise usa episódios.

---

## §5. Defeito aberto: a designação não está validamente congelada

Este é o defeito que bloqueia o registro prospectivo, e é declarado aqui em vez
de consertado em silêncio.

### 5.1 A regra consome uma constante cujo referente esta emenda retrata

`src/paper2/brief-outcome.ts:186-188` designa um chunk por grupo de assinatura:

```js
const wMin = (cDesignacao - base) / (P2_DELTA_CUT * sev);
const atual = porSig.get(l.sig_primary);
if (!atual || wMin < atual.wMin) porSig.set(l.sig_primary, { chunk_id: l.chunk_id, sev, wMin });
```

E `cDesignacao` (`brief-outcome.ts:235-238`) tem default **`0.7342`** — que é
`CUT_FRESH`.

O código **segue** o registro: `PREREG-DRAFT.md:525` congela `CUT_FRESH = 0.7342`
deliberadamente, com razão declarada (recomputá-lo do pool vivo faria da
designação uma quantidade pós-randomização). O defeito não é divergência
código-registro; é que **esta emenda retira o significado da constante e a
designação continua dependendo dela.** Retratado o modelo de limiar (§1.1),
`0,7342` deixa de ser "o cut medido" e passa a ser um número congelado sem
referente — e ele decide *quem recebe tratamento*.

O próprio docstring do código já anotava a tensão: *"Registrada como
`CUT_FRESH = 0.7342` — um limiar que o `pick` não aplica (ver
BAR-RETRACTION-2026-08-20)."*

### 5.2 O desempate registrado não está implementado

`PREREG-DRAFT.md:535` registra: *"Ties: lowest `w_min`, then earliest
`created_at`, then lexicographic `chunk_id`."*

O código não implementa nenhum dos dois níveis subsequentes: a query
(`brief-outcome.ts:169-171`) seleciona `chunk_id, severity, sig_primary` e não
tem `ORDER BY`; a atualização é `wMin < atual.wMin`, estritamente menor. Em
empate de `w_min`, **vence a ordem incidental que o SQLite devolver.**

⚠️ E é pior do que não-implementado: **`p2_verdict` não tem coluna `created_at`.**
O schema é `episode_id, severity, sig_primary, sig_coarse, chunk_id,
source_file, panel_hash, adjudicated_at, written_at`. O campo que o registro
nomeia como primeiro critério de desempate **não existe na tabela** — o desempate
registrado não é implementável como escrito, e precisa ser reformulado, não só
codificado.

### 5.2-bis O empate não é hipotético: ocorre em 4 dos 7 grupos

`w_min = (c_designação − base) / (Δ_cut · severidade)`, onde `base` é o
`salienceBase` do próprio chunk — `calculateSalience` (`src/salience.ts:246`),
não a expressão do `ORDER BY`:

```
base = 0,55·importância + 0,15·recência + 0,10·pain + 0,20·acesso
acesso = clamp01( log1p(access_count) / log(1000) )
```

Medido nos 55 chunks em `2026-08-25T10:22:00Z`: `importance` é uniforme (0,9) e
`created_at` é idêntico, mas `access_count` (1 a 5) e `last_accessed_at` (dois
valores) variam — e o termo de acesso é **log-proporcional, não binário**.
`base` assume **9 valores distintos**, e o empate em `w_min` exige empate em
`base`, não só em severidade.

Onde `base < c_designação` — **50 dos 55** chunks — o numerador é positivo e
`w_min` **decresce** em severidade. Nos outros **5** (`base` = 0,7394 em quatro,
0,7446 em um) o numerador é negativo e o sinal se inverte: `w_min` é negativo,
isto é, o chunk seria designado já em `w = 0`. Medido, o mínimo de cada um dos 7
grupos multi-membro cai sobre os membros de severidade **máxima** — mas por
composição das duas regiões, não por uma monotonicidade única.

| | |
|---|---|
| grupos de assinatura | 19 |
| com mais de um membro | 7 |
| **com empate exato no mínimo de `w_min`** | **4 de 7** |

| grupo | n | severidade do mínimo | empatados | `w_min` (·Δ_cut) |
|---|---|---|---|---|
| `Bash\|build/run` | 4 | S2 | **3** | 0,04273 |
| `Bash\|fs:mutacao` | 2 | S2 | 1 | 0,04273 |
| `Bash\|shell:outro` | 17 | S2 | 1 | −0,020887 |
| `Edit\|arquivo:doc` | 2 | S1 | **2** | 0,185461 |
| `Read\|arquivo:outro` | 4 | S1 | **4** | 0,185461 |
| `mcp__openclaw__message\|sem-alvo` | 6 | S2 | 1 | 0,04273 |
| `mcp__openclaw__web_fetch\|rede` | 8 | S2 | **5** | 0,04273 |

Em 4 desses 7 grupos (**4 dos 19** totais) dois ou mais chunks disputam o mínimo
com `w_min` idêntico, e **quem foi designado saiu da ordem incidental de linhas
do SQLite.** O defeito é material, não teórico.

🔴 **Retratado nesta versão** (encontrado por revisão adversarial GLM, 2026-08-25):
a redação anterior dizia **5 de 7**, derivando de que "todos compartilham
`written_at`, logo `w_min` é função apenas da severidade". A derivação é falsa —
`salienceBase` não tem termo em `written_at`, e tem termo em `access_count`.
Reincidência da classe *uma reconstrução pode modelar uma regra que o código
nunca aplica*: eu medi empates em `severidade × sig_primary` no banco e **afirmei**
que eram empates em `w_min`, por um argumento que o código refuta.

⚠️ **A estrutura de empates varia no tempo.** `base` depende de `access_count`,
que é mutável. O 4 de 7 é medido no fechamento da janela; **não é a estrutura
vigente durante os 111 deslocamentos**, e essa não é recuperável — o log de
designação ausente (§5.3) é exatamente o que a teria registrado.

✅ **Mas o laço que isso poderia implicar não existe, e fica declarado.**
`access_count` é incrementado **somente** por `recordAccess`
(`src/search.ts:396`), chamado apenas pelos caminhos de `search`. **O serving de
brief não incrementa.** Logo não há realimentação designação → serving →
designação, e a designação **não é** quantidade pós-randomização. O que ela é:
**não congelada** — dependente de tráfego de busca exógeno ao experimento
(qualquer `/api/search` sem `?track=false` pode mover o designado). Defeito menor
do que uma realimentação, e ainda assim incompatível com um registro prospectivo.

**Consequência retroativa, declarada:** os 111 deslocamentos, os 8,1% e a tabela
de autoria do §3.3 foram medidos sob essa designação. Eles são **reproduzíveis
como agregado** — o snapshot os congela — mas **não são atribuíveis a uma regra
de designação determinística**: a sua magnitude é condicional à designação
incidental que foi de fato executada, e uma re-execução da mesma regra poderia
designar outro chunk em até 4 dos 19 grupos. Isso não invalida o piloto como
descrição do que aconteceu; invalida qualquer leitura dele como medição de uma
regra re-executável.

⚠️ Consequência adicional não resolvida: o §5.3 pede log de `designated_ids` por
chamada porque hoje a designação **é recomputada a cada brief**. Sob empate
incidental, a identidade do designado pode variar **dentro da própria série** de
piloto, entre chamadas. Não é mensurável retroativamente — é precisamente o que o
log ausente teria registrado.

### 5.3 O que precisa acontecer antes do registro prospectivo

1. **Substituir a regra de designação** por uma regra **total**, independente de
   `CUT_FRESH` e que leia **só colunas imutáveis** de `p2_verdict` — a atual lê
   `access_count` através de `base` e por isso não está congelada. As opções, os
   requisitos e a recomendação estão em `DECISION-designacao-2026-08-25.md`; a
   escolha é decisão de desenho e precede o `ASSIGNMENT.json`.
2. **Registrar a regra nova de desempate.** A registrada não pode ser
   implementada: `created_at` não existe em `p2_verdict`. Substituir, não codificar.
3. **Definir e medir `Δ_cut`** sob referente novo (§1.5), ou substituí-lo por
   quantidade que exista.
4. **Logar por chamada** `designated_ids` e `boost_by_id`. Hoje o log guarda os
   conjuntos finais (`ids_controle`, `ids_tratado`, `would_enter`,
   `would_leave`, `fresh_added`) e `brief_log` guarda apenas
   `chunk_id, scope, agent, served_at, brief_id`. **Quem foi designado e com que
   boost não é recuperável do registro histórico** — o que também torna
   irrecuperável qualquer replay por posto sobre a série de piloto.

---

## §6. Integridade da série: dois hiatos, reconciliados

Em 2026-08-23 a infraestrutura foi migrada de host. O dia tem 560 registros
contra 672 de um dia completo — **112 registros, 16 ciclos**. Os dois hiatos são
de naturezas diferentes e não se sobrepõem:

| hiato | janela | ciclos | registros | natureza |
|---|---|---|---|---|
| **(a)** dado perdido | 11:52 – 12:37Z | 4 | **28** | registros **foram escritos** no host de origem e perdidos ao apagá-lo |
| **(b)** não amostrado | 12:52 – 15:37Z | 12 | 84 | o cron **não disparou**; nenhum brief servido, nenhum evento a registrar |
| | | **16** | **112** | fecha com 672 − 560 |

O snapshot de migração foi tirado às 11:37Z; o host de origem foi apagado por
volta de 12:38Z. O intervalo entre os dois é o hiato (a): o log continuou
recebendo linhas que não estavam em backup algum, porque os backups programados
são anteriores por definição. O hiato (b) começa depois: o cron
(`nox-mem-brief-refresh.sh`, minutos 07/22/37/52) só voltou a disparar às 15:52Z.

**Hiato (a) — recuperação descartada.** Verificados: ausência de descritor de
arquivo aberto no host, ausência de backup posterior ao snapshot, ausência de
cópia em lixeira. O tamanho foi fechado por três caminhos independentes:
contagem de linhas (1.059 − 1.031), contagem pós-gate (105 − 77) e por-agente
(5 × (15 − 11) + (30 − 22)) — **28** nos três.

⚠️ **Mitigação parcial, e é parcial mesmo.** As estatísticas agregadas sobre
esses 28 registros foram computadas às ~12:40Z, sobre o arquivo íntegro, antes da
perda (n = 105 pós-gate, `churn > 0` = 0, `fresh_added` não-vazio em 105/105).
Esses agregados são citáveis, mas **número sem microdado não é evidência
reprodutível** — o dado bruto não está disponível para reanálise, e a distinção
fica registrada para que ninguém suponha reprodutibilidade que não existe.

**Hiato (b) — não é perda de observação.** O cron **é** o instrumento: 97,7% dos
registros da série caem exatamente nos seus minutos. Sonda que não dispara não
deixa evento a registrar. Custa oportunidade de amostragem.

**Consequência para as conclusões.** Os hiatos custam a **resolução temporal da
transição** `churn = 0 → > 0`, que caiu dentro de (b). Eles não sustentam nem
derrubam a conclusão do §3.2, que é verificável no código e independente da
série: o gate abriu às 09:00Z, **2h37 antes** do snapshot de migração (11:37Z), e o primeiro
`churn > 0` ocorreu às **17:52:04Z**, ~2h depois de a coleta retomar. Além disso o
tamanho médio de grupo de empate foi 13,5 em 22/08 (host antigo) e 15,5 em 24/08
(host novo) — sem quebra na fronteira.

⚠️ Uma redação anterior afirmou que a consequência dos hiatos era "nenhuma". A
formulação era autoindulgente: a perda de resolução é real. O que é defensável, e
fica assim declarado, é que **nenhuma conclusão desta emenda repousa sobre a
janela censurada.**

---

## §7. Reprodutibilidade

Defeito registrado em revisão adversarial de 2026-08-21: `src/api/brief.ts` não
existe no repositório do depósito — o código que carrega o argumento vive no host
de produção e era inauditável por quem lê o registro.

Conserto: os trechos que decidem o mecanismo estão reproduzidos em linha no §1.2
e §5, com arquivo e número de linha, amarrados aos **pinos por arquivo** do
cabeçalho. A regra que gerou o defeito fica declarada:

> Todo número desta emenda é datado e amarrado ao commit que produziu **o arquivo
> citado**, não ao `HEAD` do dia. Nomear o **arquivo e a linha** que produz o
> número, não o script que o recomputa.

⚠️ E a razão de a regra dizer "o arquivo citado": a redação anterior amarrava
tudo ao `HEAD`, que naquele dia era um commit de encerramento de sessão sem
nenhuma mudança em `src/`. O pino era verdadeiro e irrelevante — nomeava um
objeto que não tinha relação causal com o trecho citado.

✅ **E o blob entra nesta versão.** Uma redação anterior deste §7 fechava com
*"isto mitiga, não resolve — o registro prospectivo deve carregar o blob dos
módulos de serving e designação"*, adiando o conserto. Não há razão para adiar:
os cinco módulos que esta emenda transcreve ou cita por linha vão depositados,
com proveniência em `SERVING-CODE-MANIFEST.md` (path original, commit, data,
tamanho e sha256 de cada um):

`serving-brief.ts` · `serving-brief-diversity.ts` · `serving-brief-outcome.ts` ·
`serving-salience.ts` · `serving-search.ts`

⚠️ **E o que isso não é.** São os módulos, não o sistema. Eles importam do resto
do pacote (`db.js`, o cliente de embeddings, a camada FTS5), que **não** vai
depositado — logo os blobs são **auditáveis, não executáveis** isoladamente. É
uma afirmação mais estreita que reprodutibilidade, e é a honesta. O que muda:
quem lê a citação `brief.ts:607-618` agora pode abrir a linha 608 em vez de
confiar na transcrição.

---

## §8. Ordem de operações

A ordem é imposta pelo desenho: o `ASSIGNMENT.json` **é** o sorteio, e o registro
determina que o sorteio ocorre depois de o mecanismo estar congelado. No momento
desta redação `NOX_P2_ASSIGNMENT` e `NOX_P2_ASSIGNMENT_SHA256` não estão
definidos e o arquivo não existe — verificado no ambiente do processo servindo em
2026-08-25T09:57Z.

1. **Depositar esta emenda** (Zenodo v1.12 + emenda no OSF `yf7d2`).
2. **Corrigir a designação** — os quatro itens do §5.3.
3. **Registro prospectivo** do estimando, estimador, variância e população-alvo,
   rotulado como informado pelo piloto, declarando que os 2.221 registros são
   descritivos e não entram na análise confirmatória.
4. **Gerar o `ASSIGNMENT.json`** — este passo **é** o `T_seed_assign` — com
   sha256 registrado e seed ancorada no OSF.
5. **Passar a `active`**: definir as duas variáveis via drop-in de systemd, não
   editando `.env`.
6. **Verificar por estado observável** que `servido` alterna entre `tratado` e
   `controle` conforme o `ASSIGNMENT.json`, e que `p2_arm_unresolved` é zero. Não
   confiar em log de startup: um drop-in mal formado desliga a flag em silêncio,
   e `systemctl is-active` responde sobre o serviço, não sobre o modo.
7. **Epoch 1.**

⚠️ **`p2_arm_unresolved` não é falha neutra.** O comentário no código a nomeia:
*"NÃO neutro: converte tratamento em controle e enviesa pro nulo. Contagem e
quantidade pré-comprometida de reporte."* Esta emenda registra a regra analítica
que decorre disso, e a declara como **decisão minha, mais estrita que o código**:
a contagem por epoch é reporte obrigatório, e um epoch com qualquer ocorrência é
declarado contaminado, não aproveitado como controle.

⚠️ Arquivos no Zenodo são imutáveis; conserto é versão nova. Antes do passo 1,
reler campo a campo contra a v1.11 publicada, em formato InvenioRDM — um `PUT` de
formato legado retorna 200 e descarta autor e licença em silêncio.

---

## Anexo A — proveniência

| número | fonte | data da medição |
|---|---|---|
| λ̂ = 0,077499 · SE 0,012023 · IC [0,0539; 0,1011] | `LAMBDA-RESULTS-2026-08-21.md` | 2026-08-21 |
| estrato A 44/46 · estrato B 11/234 · peso HT 5,194215 | `LAMBDA-RESULTS-2026-08-21.md` | 2026-08-21 |
| população 1.305 · frame A 48 / B 1.257 · amostra B 242 · taxa de projeto 19,235% (realizada 19,25%) | `LAMBDA-SEED-2026-08-21.md:36-41` | travado antes da amostra |
| seleção do estrato B: `SHA256(seed ‖ "\|" ‖ episode_id)`, 242 primeiros | `LAMBDA-SEED-2026-08-21.md:66-75` | seed pushada 2026-08-21 22:17:50Z |
| 870/870 chamadas · 10 inadjudicáveis · 3,45% | `LAMBDA-RESULTS-2026-08-21.md` | 2026-08-21 |
| `p̂0 = 0,111813` | `PREREG-DRAFT.md` | registro 2026-08-18 |
| shares por família: moonshot 24,2 · zhipu 25,9 · xai 72,2 | `LAMBDA-RESULTS-2026-08-21.md` | 2026-08-21 |
| 22 de 22 S2 consolidados com `xai = S2` | `LAMBDA-RESULTS-2026-08-21.md` | 2026-08-21 |
| 2.221 registros · 102 com `churn > 0` · 111 deslocamentos · 93/9 | `pilot_window_stats.mjs` + `PILOT-WINDOW-2026-08-25.json` | janela fechada |
| pré-gate 954 com 0 · pós-gate 1.267 com 102 = 8,1% | `p2-serving-WINDOW-2026-08-25.ndjson` × campo `epoch` | 2026-08-25T10:22Z |
| 100 de 102 com `last_served` comum · 0 com `NULL` | `p2-serving-WINDOW-2026-08-25.ndjson` × `brief_log` | 2026-08-25T10:22Z |
| 86/86 sem violação (teste estrito) | recibo `adversary-receipt-kimi-2026-08-24T195720` | 2026-08-24 |
| `fresh_added` = 2 em 2.221 de 2.221 | `p2-serving-WINDOW-2026-08-25.ndjson` | 2026-08-25T10:22Z |
| grupo de `last_served` da frente: 12 a 31 | `brief_log`, amostra de 6 decisões | 2026-08-25 |
| grupo de empate médio 13,5 (22/08) vs 15,5 (24/08) | `brief_log` | 2026-08-24 |
| `written_at` = 2026-08-21 22:51:23, único para os 280 | `p2_verdict` | 2026-08-25 |
| primeiro serve dos 55: 22/08 19:23:43 → 21:07:19 | `brief_log` | 2026-08-25 |
| primeiro `churn > 0`: 2026-08-23T17:52:04Z | `p2-serving-WINDOW-2026-08-25.ndjson` | 2026-08-25 |
| `served_at` sem fração de segundo: 0 de 559.158 | `brief_log` | 2026-08-25 |
| autoria: entram 16/16 ids e 111/111 eventos do estudo; saem 25/33 ids e 99/111 eventos (89,2%) | `p2-serving-WINDOW-2026-08-25.ndjson` × `p2_verdict`, janela fechada | janela fechada |
| série horária pós-gate: 47 horas · média 7,8% · mediana 3,6% · 0,0–46,4% · 14 horas com zero | `pilot_window_stats.mjs` → `serie_horaria_pos_gate` | janela fechada |
| `salienceBase` dos 55: 9 valores distintos · `importance` uniforme 0,9 · `access_count` ∈ {1..5} · 50 abaixo e 5 acima de 0,7342 | `calculateSalience` (`src/salience.ts:246`) × `chunks`, em `nowMs = 2026-08-25T10:22:00Z` | 2026-08-25 |
| empate exato de `w_min`: **4 de 7** grupos multi-membro (19 grupos totais) | `w_min = (0,7342 − base)/(Δ_cut·sev)` sobre `salienceBase` computado | 2026-08-25 |
| `p2_verdict` **não tem** coluna `created_at` | `.schema p2_verdict` | 2026-08-25 |
| 954 = 30 + 672 + 252 (corte por epoch, não por dia civil) | `p2-serving-WINDOW-2026-08-25.ndjson` × campo `epoch` | janela fechada |
| 97,7% dos registros nos minutos do cron (07/22/37/52) | `p2-serving-WINDOW-2026-08-25.ndjson`, distribuição de minuto | 2026-08-24 |
| shares por-veredito S1 69,73 · S2 29,62 · S3 0,58 · S4 0,08 | `SHARES-PROVENANCE-2026-08-19.md:41` | 2026-08-19 |
| shares por-episódio S1 78,93 · S2 21,07 · S3 0 · S4 0 | `SHARES-PROVENANCE-2026-08-19.md:42` | 2026-08-19 |
| `Δ_cut = 0,043` (valor herdado, referente pendente) | `AUDIT-SECTION2-SERVING-2026-08-18.md` | 2026-08-18 |
| `0,7344` supera 4 de 6 agentes | `CUTS-MEASURED-2026-08-18.json` (medição de 18/08; comparação feita 21/08) | 2026-08-18 |
| reconciliação do hiato (a): 1.059 − 1.031 · 105 − 77 | medido no arquivo íntegro em 2026-08-23T~12:40Z; **bruto não disponível** | 2026-08-23 |
| cut agente-heterogêneo 0,610–0,792 (span 0,182) | `CUTS-MEASURED-2026-08-18.json` | 2026-08-18 |
| cut principal 0,8524 · cut de cobertura 0,7342 | `PREREG-DRAFT.md:438` | registro |
| `CUT_FRESH = 0,7342` congelado para designação | `PREREG-DRAFT.md:525` | registro |
| desempate registrado: `w_min`, `created_at`, `chunk_id` | `PREREG-DRAFT.md:535` | registro |
| `cDesignacao` default 0.7342 | `brief-outcome.ts:235-238` | commit `c3c14c19` |
| 190 chunks `entities/%` com 42,1–78,9 dias | `chunks` × janela de 30 d | 2026-08-21 |
| último commit em `src/`: `1464db87` · pinos por arquivo (5) | `git log -1 -- src/` e `git log -1 -- <arquivo>` no host | 2026-08-26T10:35Z |

## Anexo B — revisões adversariais

Sete passagens, quatro famílias de modelo, todas com recibo verificado. As
segundas rodadas foram instruídas a atacar a **hipótese revisada da rodada
anterior**, não a pergunta original.

| voz | rodada | contribuição incorporada |
|---|---|---|
| Kimi | 1 | premissa "nunca servidos antes de 23/08" é falsa (187 serves em backup de 22/08); `servido:"controle"` 100%; o canal é seleção, não depleção |
| DeepSeek | 1 | confundimento temporal migração × tratamento; curva compatível não é prova |
| Kimi | 2 | o gate de maturidade explica o zero; teste 86/86; hardware descartado por medição de grupo de empate; ativação é de batch |
| DeepSeek | 2 | `coverageCompare` é determinístico; shadow não estima `N`; risco de MDE shopping; exigência de tabela de reconciliação dos hiatos (§6) |
| Grok | prosa | citação falsa no Anexo A; "76/9" obsoleto; "129 pares" inflado; off-by-one nos ciclos; 4,6% com denominador contaminado; **"desempate" é o nome errado** |
| GLM | decisão | separou a defesa em três superfícies: magnitude protegida, **escolha de estimando não protegida**, leitura de código não é contaminação; λ̂ **não migra** para estimando novo |
| Codex | decisão | veto ao estimando retroativo; replay contrafactual é descritivo da população finita, não confirmatório; `D(i)` por posto **não é recuperável** dos logs; **a designação ainda consome `CUT_FRESH`** (§5) |
| GLM | prosa | **`base` pode não ser invariante entre chunks de mesma severidade** → mediu-se, e não é: retratações 15 e 16, o empate cai de 5/7 para **4/7**; denominador 1.305 ausente do §2; desenho amostral do estrato B não citado; §3.4 afirma mais do que o dado sustenta na leitura larga; §0 declarava três vezes o que o piloto não é e nenhuma vez o que é |

Alegações de revisão verificadas e **rejeitadas** por medição, registradas para
que não reapareçam:

| alegação | refutação |
|---|---|
| λ̂ = 0,0775 é inconsistente (esperado 22/280 = 0,0786; IC implicaria n ≈ 490) | o estimador é HT estratificado com SE 0,012023, não proporção simples (§2) |
| o canal primário é o grupo `NULL` de nunca-servidos | 0 de 102 registros envolvem nunca-servido (§1.4) |
| `brief_log` foi reinicializado na migração | é sequencial e contínuo: id 551680 às 11:37:09, id 551819 às 15:52:08 |
| há incompatibilidade segundo × milissegundo em `lastServedMs` | `served_at` não tem fração de segundo em 0 de 559.158 linhas; `parseDbDateMs` não trunca (§1.2) |
| a população 1.305 é inconsistente com o peso publicado (`46 + 234 × 5,194215 = 1.261,4`) | o peso é frame/**amostra** = 1.257/242, e o frame de A é 48, não 46: `48 + 1.257 = 1.305` exato (§2). A lacuna era de publicação, e foi sanada |
| o desenho amostral do estrato B (mecanismo, fração, frame) não está declarado em nenhum documento | está em `LAMBDA-SEED-2026-08-21.md:36-75`, travado antes da amostra — não foi passado à revisão. Agora citado no §2 e no Anexo A |

Cinco das seis alegações rejeitadas vieram de rodadas executadas sem acesso ao
sistema ou ao artefato citado — em dois casos porque **eu não passei o artefato**.
Fica registrado como nota de método: **revisão sem acesso produz mecanismo
plausível e não verificado**, e as suas alegações factuais precisam ser medidas
antes de aceitas.

⚠️ E a contrapartida, que a rodada do GLM demonstrou: uma alegação **rejeitada**
pode carregar um defeito **real**. A hipótese "`base` pode não ser invariante" foi
levantada com hedge explícito e sem acesso ao código; medida, ela derrubou duas
afirmações do §5.2-bis. Rejeitar a alegação e descartar a dúvida não são a mesma
operação.

Duas invocações do Grok em 2026-08-25 **não produziram análise** e ficam
registradas para que os seus resultados não sejam citados: uma sem recibo, outra
com recibo `exit: 124` (timeout de 31 min, 94 bytes). Causa em ambas: eu montei o
briefing com paths de servidor remoto, e o wrapper adversarial não faz SSH. A
contribuição do Grok nesta tabela é apenas a da rodada de prosa
(recibo `exit: 0`, 11.423 bytes).
