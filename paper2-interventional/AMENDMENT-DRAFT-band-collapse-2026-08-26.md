# Emenda — `Δ_cut` perde estatuto de parâmetro, e o estudo fica BLOQUEADO

**Registro emendado:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
concept `10.5281/zenodo.21964093`, última versão depositada **v1.12**
(`10.5281/zenodo.22110203`, 2026-08-26T14:01Z).

**Versão: a ser atribuída no depósito.** Este arquivo é **rascunho** e não carrega
número. Número de versão é fato do depósito, não rótulo do texto.

**Redigida:** 2026-08-26 à noite. **Reescrita integralmente às 23:40Z** depois de
duas revisões adversariais (GLM-5.3 e Codex/gpt-5.6-sol, recibos no Anexo B)
derrubarem **duas das cinco decisões** da primeira redação. O que caiu está no §7,
nomeado, porque uma emenda que esconde o que a revisão matou não vale como emenda.

**Código servindo.** Último commit que tocou `src/`: **`0087c918`**
(2026-08-26T20:25:01Z), repo `nox-workspace`.

| arquivo | commit | data |
|---|---|---|
| `src/api/brief.ts` | `0087c918` | 2026-08-26T20:25:01Z |
| `src/paper2/brief-outcome.ts` | `0087c918` | 2026-08-26T20:25:01Z |
| `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23−03:00 |
| `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55−03:00 |

`brief-diversity.ts` está inalterado desde junho, e é onde vive o comparador que
esta emenda mede. A dominância que ela reporta **não é consequência de mudança
recente** — está no código desde antes de o Paper 2 existir.

---

## §0. Natureza e limites desta emenda

**O que ela faz, e é só isto:**

1. **Fecha** o defeito que a v1.12 §5 declarou aberto — a designação (§1).
2. **Retira `Δ_cut` do estatuto de parâmetro científico**, porque a quantidade que
   ele escala é lexicograficamente dominada (§2, §3).
3. **INVALIDA a banda `{2,0 · 4,0 · 7,5}` como escala de dose**, sem substituí-la
   por outra (§3).
4. **BLOQUEIA o início do estudo** até um protocolo de calibração prospectivo
   existir (§5).

**O que ela deliberadamente NÃO faz, e a primeira redação fazia:**

- **NÃO** fixa um braço único em `w = 4,0`. Essa escolha era pós-calibração
  vestida de propriedade derivada (§7.1).
- **NÃO** troca o estimando primário para condicional à oportunidade. Isso
  **reabria a F2**, uma FATAL fechada em 2026-07-12 (§7.2).
- **NÃO** define `N` a partir de taxa de oportunidade medida. Isso **reabria a
  F3** (§7.3).

**Por que descritiva e bloqueante, em vez de redesenhadora.** A v1.12 já foi
depositada como emenda descritiva, e por bom motivo: mudar mecanismo no mesmo
documento que o descreve é indistinguível de racionalizar a mudança. Aqui vale em
dobro — as duas decisões de desenho que a primeira redação tomou foram as duas que
a revisão derrubou.

**A contribuição declarada do Paper 2 é o método.** Um mecanismo que se descobre
inerte, ou cuja oportunidade se descobre mal definida, **antes** de consumir
amostra, é produto do método. Isso não reduz a gravidade; reduz o custo.

---

## §1. Fechado: a designação

A v1.12 §5 declarava, corretamente, que a regra de designação não estava
validamente congelada: consumia `CUT_FRESH` como limiar que o código não aplica, o
desempate registrado nomeava `created_at` (coluna inexistente em `p2_verdict`, logo
**não-implementável**), e `w_min` derivava de `access_count`, mutável por tráfego
de busca exógeno.

**Substituída, declarada, verificada e vigente.**

| | |
|---|---|
| decisão | 2026-08-26T14:47Z, opção B, **antes** de qualquer código, com o custo de 8,8% de dose já medido |
| regra | `designado(g) = argmin_{c ∈ g} SHA256( seed ‖ "\|" ‖ chunk_id )`, global |
| declaração | `DESIGNATION-SEED-2026-08-26.md`, push **20:07:24Z** *(data do GitHub)* |
| rodada | drand quicknet **31657512**, emissão **20:25:00Z** — folga **1.056 s** |
| estado na declaração | `GET .../public/31657512` → **HTTP 425**, não emitida |
| frame | `p2-verdict-frame-2026-08-26.csv`, 55 linhas, `sha256` `9d0d80d6…`, push **20:08:55Z** |
| seed | `e5d134ee110a33870f68963ae47a39bbee208586328d2311ac6626eed42122d7` |
| conjunto | 19 grupos, 19 designados distintos, `sha256` `e549420907cd…da001b` |
| congelado em | `DESIGNATION-2026-08-26.json`, preso por path + `sha256` |
| vigente desde | **20:28Z** |

**`sig_primary` saiu da chave**, corrigido às 19:40Z, antes de congelar: todos os 19
valores reais contêm `|`, o próprio separador, logo o layout aprovado às 14:47Z não
era injetivo. Removido o campo em vez de trocado o separador, porque cada chunk
pertence a exatamente um grupo (0 de 55 em mais de um, excluídas as 225 linhas S0,
que têm `chunk_id NULL`). Propriedade estatística idêntica; ganho é a chave passar
a depender só de ids congelados.

**Verificação cruzada em duas implementações lendo fontes diferentes.** A TS
consultou `p2_verdict` **ao vivo**; o Python leu o **CSV depositado** 16 min antes.
Os `sha256` do conjunto batem, o que prova de uma vez que as derivações são a mesma
regra **e** que o frame corresponde à tabela. Cinco mutações do fonte TS foram
confirmadas fazendo os testes falharem.

⚠️ **Isto é o único item desta emenda que está fechado.** Todo o resto é
diagnóstico e bloqueio.

---

## §2. `Δ_cut` não tem referente a encontrar

A v1.12 §1.5 declarou `Δ_cut = 0,043` *"pendente de definição operacional e de
medição"* — formulação que supõe existir definição a achar.

O comparador do pool de cobertura é **lexicográfico**
(`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;   // last_served ASC — domina
return bSalience - aSalience;    // salience só desempata last_served IDÊNTICO
```

O boost é aditivo **em `salience`**, a coordenada subordinada. Quando `last_served`
difere, o comparador devolve `al − bl` e **nunca consulta `salience`**.

**Esta parte é dedutiva, não estatística**, e é a única afirmação estrutural que
esta emenda faz. Não depende de medição nenhuma.

### O que a medição mostra, e o que ela NÃO estabelece

Um estado do pool, medido 20:35Z–21:00Z (snapshot de epoch como corpus, DB vivo
como estado de serving, `freshSlots = 2`):

| posição | `last_served` | `salience` | do estudo? |
|---|---|---|---|
| 0 | `2026-08-26 18:37:05` | 0,682220 | não |
| 1 | `2026-08-26 18:37:05` | 0,682220 | não |
| 2 | `2026-08-26 18:37:05` | 0,682220 | não |
| **3** | **`2026-08-26 18:37:06`** | **0,712751** | **sim** (308220) |

O chunk do estudo tem `salience` **mais alta** e perde, porque foi servido **um
segundo depois**.

| | |
|---|---|
| candidatos no pool | **108** (o `WHERE` corta antes do `LIMIT 400`) |
| chunks do estudo no pool | **55 de 55** |
| **nunca-servidos no pool** | **0** |
| grupos de `last_served` distintos | 44 |
| tamanhos de grupo | 1: 3 · 2: 29 · 3: 1 · 4: 11 |
| pares adjacentes envolvendo estudo | 38 pares, **11 exatamente zero**, 27 positivos |
| gap máximo **intragrupo** | **0,031809** |

⚠️ **`0,031809` é o gap máximo DENTRO de grupos de `last_served` idêntico**, não do
pool inteiro. A primeira redação não dizia qual, e o GLM cobrou.

### A varredura de dose NÃO é evidência da afirmação estrutural

Varredura offline no caminho de produção, 7 agentes, `n = 10`: `churn` **0** em
`w ∈ {2,0 · 4,0 · 7,5 · 1.000 · 100.000}`, com 19 boosts emitidos por chamada.

⚠️ **Isto tem valor probatório NULO para a afirmação geral**, e a primeira redação
a apresentava como *"demonstração direta da dominância"*. No estado medido não há
grupo qualificável na fronteira; nesse estado `churn = 0` é **garantido pela
estrutura para qualquer `w`**, inclusive 100.000. Corroborar um teorema com um
experimento que não podia dar outro resultado não é corroborar.

O que a varredura foi, de fato: um **controle positivo que falhou**, e cuja falha
me apontou para a estrutura. É diagnóstico, não prova. O GLM identificou a
circularidade.

### A taxa histórica é decisivamente diferente de zero, e NÃO é estacionária

A primeira redação publicou `132 / 3.166 = 4,1693%` como linha de base. **Está
errado por diluição:** as 954 decisões pré-gate têm churn **estruturalmente
impossível** (0 de 954) e inflam o denominador. Comparar contagem filtrada com
não-filtrada é a mesma classe da retratação 2.

Base correta, **pós-gate** (epochs ≥ 23/08), janela fechada
`2026-08-21T22:57:48.194Z` → `2026-08-26T19:52:07.775Z`:

| dia | n | com `churn` | taxa | deslocamentos |
|---|---|---|---|---|
| 23/08 | 308 | 42 | **13,6364%** | 47 |
| 24/08 | 672 | 49 | 7,2917% | 53 |
| 25/08 | 672 | 21 | 3,1250% | 21 |
| 26/08 | 560 | 20 | 3,5714% | 20 |
| **total** | **2.212** | **132** | **5,9675%** | **141** |

**A taxa cai ~4× em quatro dias.** Nenhuma taxa agregada pode ser citada como "a"
linha de base. E `5,9675%` está a ~11,8 desvios-padrão de zero: **o mecanismo age**.
A afirmação defensável é *"a dose age somente via colisão, e satura acima de um
limiar"*, nunca *"a dose não existe"*.

⚠️ Os `111 deslocamentos em 102 decisões` da v1.12 (retratação 8) são **soma de
`churn`** sobre **1.267** decisões pós-gate = 8,05% — janela que termina antes da
desta emenda. Recomputado até 25/08 inclusive dá 112/1.652 = 6,78%. Os números não
são incompatíveis; são janelas diferentes de uma série que decai. A v1.12 não
errou, e esta emenda **não a retrata** — mas a comparação exige as duas janelas na
mesa, e a primeira redação não as punha.

---

## §3. A banda é invalidada, e nenhuma outra é declarada

**`W_OUTCOME = w · Δ_cut · severidade` não define escala de dose**, porque `Δ_cut`
não tem referente. A banda `{2,0 · 4,0 · 7,5}` fica **invalidada como escala**.

O que se mede quando há colisão:

| `w` | S1 (0,25) | vence | S2 (0,5) | vence |
|---|---|---|---|---|
| **2,0** | 0,0215 | 16/27 | 0,0430 | 27/27 |
| 4,0 | 0,0430 | 27/27 | 0,0860 | 27/27 |
| 7,5 | 0,0806 | 27/27 | 0,1613 | 27/27 |

⚠️ **11 dos 27 gaps DISTINGUEM `w = 2,0` de `w = 4,0` para S1.** Logo "a banda tem
níveis indistinguíveis" é **falso** para esse par, e a primeira redação dizia *"a
dimensão de dose não existe — medido, não suposto"*. Os dois revisores apontaram a
mesma contradição interna. O que o snapshot sustenta é `w = 4,0 ≈ w = 7,5`
**naquele estado**, não que colapsar seja inevitável.

**Por que a banda cai mesmo assim:** não porque os níveis sejam indistinguíveis,
mas porque **a unidade em que estão expressos não existe**. Um multiplicador de uma
quantidade sem referente não é uma dose, mesmo quando dois de seus valores produzem
resultados diferentes. A substituição — se houver — é objeto do protocolo
prospectivo do §5, não desta emenda.

⚠️ **Não é possível ter as duas coisas.** A primeira redação definia o tratamento
como *"magnitude suficiente para vencer qualquer gap dentro de empate"* **e**
fixava valores absolutos. Se a magnitude é fixa, um gap futuro de 0,045 derrota S1
a `w = 4,0`; se ela se adapta aos gaps, deixa de ser fixa e passa a depender de
dado pós-tratamento. Contradição apontada pelo Codex, e real.

Sobre extrapolar dos 27 gaps: mesmo sob independência — generosa, porque os valores
se repetem e compartilham grupos — 27 observações todas abaixo de 0,043 dão limite
superior unilateral de ~**10,5%** para excedência futura. Não é garantia de
saturação, e a margem observada é **0,043 / 0,031809 ≈ 1,35×**.

---

## §4. Três defeitos que a revisão expôs e que esta emenda declara sem resolver

### 4.1 A definição de oportunidade NÃO corresponde ao pipeline

A primeira redação definia oportunidade como *"grupo da fronteira misto e maior que
`freshSlots`"*, e media 5 de 44 grupos. **A definição é incompleta**, e por três
razões independentes:

- **`interleaveFresh` + `pickDedup`.** Há dois subpools ordenados separadamente, e
  a seleção rejeita por dedup, near-dup e pinned. A fronteira efetiva é a dos
  **dois primeiros ACEITOS**, não dos dois primeiros brutos. Um grupo de tamanho 2
  pode importar se candidatos anteriores forem rejeitados; um de tamanho 4 pode não
  importar se estiver atrás dos dois aceitos.
- **Grupo puro-estudo não é inerte.** Se o designado impulsionado substitui **outro
  chunk do estudo**, o designado É servido e o tratamento É entregue. O que grupo
  puro-estudo impede é deslocar **controle**. ⚠️ Uma análise intermediária minha
  desta noite afirmou que o mecanismo *"consome a própria oportunidade"* com base
  em 70,9% dos chunks do estudo estarem em grupo puro — **isso superou o dado** e
  fica retratado aqui antes de entrar em qualquer versão depositada.
- **`last_served IS NULL` ⇒ `−∞`.** Nesse estrato os nunca-servidos lideram e o
  boost **funciona** (é o que o teste unitário verifica). Hoje há 0 no pool, mas o
  estrato existe.

Logo **os 5/44 não medem a oportunidade do código**, e não podem sustentar `N`,
poder, nem definição de estimando. A definição correta exige replay do pipeline
completo.

### 4.2 O snapshot foi contaminado pelo processo de verificação, e importa

Três sondas minhas em `/api/brief` às 19:58Z escreveram 15 linhas em `brief_log`,
movendo `last_served` de 3 chunks do estudo de `18:07:0x` para `19:58:1x`.

⚠️ **A justificativa que eu dei para não apagá-las usava a variável errada.**
Argumentei que os 3 *"já tinham 47-48 servings"* — mas o comparador não olha
**contagem**, olha **`MAX(served_at)`**. Numa emenda que afirma "um segundo é
barreira absoluta", tratar um deslocamento de 1h51 como inconsequente é incoerente.
O Codex apontou.

Medido, observado × descontaminado (excluindo `served_at ≥ 19:58:00`):

| métrica | observado | descontaminado |
|---|---|---|
| grupos de `last_served` | 45 | 41 |
| posição do 1º chunk do estudo | 1 | 0 |
| **menor posição de grupo qualificável** | **1** | **18** |
| grupos puro-estudo | 14 | 15 |
| grupos mistos | 18 | 12 |
| chunks do estudo em grupo puro | 32 | 36 |

**A contaminação altera a conclusão.** Posição 1 está **dentro** da fronteira
(`freshSlots = 2` cobre 0–1): no estado observado **há** oportunidade na fronteira,
e no descontaminado o primeiro qualificável está na posição 18.

E há um segundo fato no mesmo par de colunas: às 20:35Z eu medi *"nenhum grupo
qualificável alcança a fronteira"*; às 23:30Z há um na posição 1. **O estado
rotaciona com o tráfego.** Nenhum instante — contaminado ou não — sustenta uma
constante de registro.

### 4.3 `last_served` não é congelado pelo snapshot de epoch, e realimenta

Servir um brief escreve em `brief_log` (`brief.ts:1086`, sem gate de tracking),
`brief_log` define `last_served`, e `last_served` ordena o pool **seguinte**. Logo o
tratamento em `T` altera a estrutura de grupos em `T+1`: o efeito é **dinâmico**, e
nenhuma varredura de estado único pode vê-lo. Apontado pelo GLM.

⚠️ **E o freeze de serving do Route 2-lite não cobre isso.** O snapshot de epoch
congela o **corpus**; `brief_log` vive no **DB vivo**. Portanto a coordenada
**dominante** da ordenação nunca é congelada — o desenho congela os insumos da
coordenada subordinada (`importance`, `pain`, `access_count`) e deixa a dominante
solta, atravessando fronteiras de epoch.

Isto interage com a F1 (carry-over) do `REVIEWS-PREREG.md` e **precisa de
tratamento no protocolo prospectivo**, não aqui.

---

## §5. O estudo fica BLOQUEADO. O que precede o desbloqueio

**Estimando primário permanece o INCONDICIONAL registrado** — ITT por
epoch/session-hour. Taxa de ativação, `churn` e composição dos deslocamentos ficam
**secundários mecanísticos**.

**`N` permanece o registrado.** Não é recalculado por esta emenda, e não pode ser
recalculado a partir de contagem de oportunidades.

O desbloqueio exige um **protocolo de calibração prospectivo**, registrado antes de
observar mais dado, contendo no mínimo:

1. **Definição de oportunidade por replay do pipeline completo** — `interleaveFresh`,
   `pickDedup`, pinned, dedup, `LIMIT 400`, estrato `NULL` — não por censo de
   grupos num pool.
2. **Janela de calendário de calibração**, com início e fim declarados, e o estado
   de `brief_log` **descontaminado** de sondas, com sensibilidade publicada nos dois
   estados.
3. **Unidade de reamostragem** = dia ou epoch, nunca par-de-gap (senão é
   pseudorreplicação).
4. **`N = f(dados)` como script executável commitado antes de rodar** — é a F5 do
   `REVIEWS-PREREG.md`, e horizonte **fixo em blocos/calendário**, nunca em
   contagem de oportunidades (F3).
5. **Regra de no-go explícita**, e proibição de parar quando "houver oportunidades
   suficientes".
6. **Tratamento do carry-over de `last_served`** através das fronteiras de epoch
   (§4.3), em interação com a F1.
7. **Gatilho de monitoramento** que dispare se aparecer gap intragrupo acima da
   magnitude escolhida — sem isso, com braço único, uma falha de saturação é
   indetectável.

⚠️ **`T_seed_assign` continua não declarado**, e agora por razão mais forte: não se
sorteia braço de uma escala invalidada.

---

## §6. Retratações novas

Continuam a numeração da v1.12, que fecha em 28.

| # | data | retratado | o que substitui |
|---|---|---|---|
| **29** | 26/08 | `Δ_cut` está "pendente de definição operacional e de medição" (v1.12 §1.5) — supõe definição a achar | não há: a quantidade é lexicograficamente dominada. Perde estatuto de parâmetro (§2) |
| **30** | 26/08 | `W_OUTCOME = w × Δ_cut` é *"a multiple of the measured salience spread at the brief cut"* (`PREREG-DRAFT.md:414`) | não há cut; o referente que existe é o gap **intragrupo**, publicado no §2 |
| **31** | 26/08 | a banda `{2,0 · 4,0 · 7,5}` está entre *"what does not move, and could not"* (`PREREG-DRAFT.md:44`) | invalidada como escala de dose, **sem substituição** (§3) |
| **32** | 26/08 | o chunk do estudo é nunca-servido, logo está sempre entre os 400 (`brief-outcome.ts:17-22`) | 0 nunca-servidos no pool; os 55 já foram servidos. A conclusão vale por outra razão: o pool tem 108 |
| **33** | 26/08 | a designação é defeito **aberto** (v1.12 §5) | fechada 26/08 20:28Z, com precedência verificável (§1) |
| **34** | 26/08 | linha de base de `churn` = 132/3.166 = 4,1693% | diluída por 954 decisões pré-gate com churn estruturalmente impossível. Base pós-gate: **132/2.212 = 5,9675%**, e a série **não é estacionária** (13,64% → 3,57%) (§2) |
| **35** | 26/08 | a oportunidade é "grupo da fronteira misto e maior que `freshSlots`", medida em 5/44 | incompleta: ignora `interleaveFresh`/`pickDedup`/pinned/dedup, o estrato `NULL`, e o fato de grupo puro-estudo entregar tratamento (§4.1) |

---

## §7. O que a revisão adversarial matou, nomeado

Três decisões da primeira redação desta emenda **caíram**. Ficam registradas porque
uma emenda que apaga o que a revisão derrubou não é auditável.

### 7.1 Fixar um braço único em `w = 4,0` — RETIRADO

Eu apresentava como propriedade derivada (*"vence 27/27 em ambas as severidades"*).
É **pós-calibração informada pelo piloto**: o valor foi escolhido olhando os 27
gaps observados. E o argumento era parcialmente tautológico — S2 já vence 27/27 a
`w = 2,0`, logo a tabela não isola nada sobre 4,0. Some-se a contradição do §3
(magnitude fixa **ou** adaptativa, não as duas) e a margem de 1,35× a partir de 27
observações. Colapsar pode ser boa decisão operacional; **não é conclusão
estrutural**, e não entra por esta emenda.

### 7.2 Estimando condicional à oportunidade — RETIRADO, e era regressão

`REVIEWS-PREREG.md` **F2**, de 2026-07-12, classificou exatamente esta classe como
**FATAL**: *"RFR condicionado a oportunidade tem viés de seleção pós-tratamento
(collider). O denominador (oportunidades elegíveis) é ele próprio afetado pelo
tratamento… Fix: primário **incondicional**."*

Minha retratação 35 da primeira redação dizia literalmente *"o efeito é
incondicional → condicional à oportunidade"*. **Eu retratei o conserto e restaurei
o defeito**, seis semanas depois de ele ter sido fechado, num documento novo. E é
demonstrável que `O_i(1) ≠ O_i(0)`: a oportunidade depende de `last_served`, que o
tratamento altera (§4.3). Condicionar em `O` observado seleciona um mediador
pós-tratamento.

Classe do defeito: **classe de defeito não fica consertada onde foi achada.** O
conserto exigiria grepar toda frase que se apoia na premissa, e eu não grepei
`REVIEWS-PREREG.md` antes de propor.

### 7.3 `N` recalculado sobre taxa de oportunidade — RETIRADO

`REVIEWS-PREREG.md` **F3**: *"Stopping rule em N oportunidades = optional stopping
disfarçado. N de oportunidades é pós-tratamento; o tempo de parada vira função do
efeito. Fix: horizonte fixo em blocos randomizados / calendário."* Minha §5 mandava
*"acumular a janela e recalcular `N` sobre a taxa de oportunidade medida"*. Mesma
regressão que 7.2.

---

## §8. Ordem de operações

1. Esta emenda depositada. Ela **invalida** a banda e **bloqueia** o estudo.
2. Protocolo de calibração prospectivo registrado (§5, os 7 itens).
3. Calibração executada dentro da janela de calendário declarada.
4. Escala de dose — se houver — declarada por emenda própria.
5. `T_seed_assign` e `ASSIGNMENT.json`.
6. `NOX_P2_OUTCOME=active`. 7. Epoch 1.

Nada de 3 a 7 começa antes de 1 e 2.

---

## §9. Reprodutibilidade — uma lacuna aberta

⚠️ **Um terceiro NÃO consegue reproduzir as medições desta emenda hoje.** Duas
razões, ambas a resolver antes do depósito:

- os blobs de código depositados na v1.12 são da regra **anterior** (designação por
  `w_min`); esta emenda cita `0087c918`, que não está depositado;
- os scripts de medição (`mede-delta.mjs`, `dose2.mjs`, `controle-positivo.mjs`,
  `ordem.mjs`, `autoextincao.py`, `descontamina.py`) vivem em `nox-workspace`, repo
  **privado**.

O `DELTA-CUT-MEASUREMENT-2026-08-26.json` e o
`p2-verdict-frame-2026-08-26.csv` estão públicos e cobrem os dados; o **código que
os produziu, não**. Depositar a emenda sem fechar isto repetiria o defeito que a
retratação 1 da v1.12 registra — documento que referencia artefato inexistente.

---

## Anexo A — proveniência

Medições de 2026-08-26, 20:35Z–23:30Z, sobre `e20260826T060003Z.db` (corpus) e o DB
vivo (estado de serving). Nenhum script escreve em `brief_log`:
`buildBriefDiverse` não faz tracking. Detalhe em
`MEASUREMENT-delta-cut-2026-08-26.md`.

Fontes: `AMENDMENT-v1.12.md` §1.5, §4, §5.3 · `PREREG-DRAFT.md:44`, `:414` ·
`REVIEWS-PREREG.md` F1, F2, F3, F5 · `DECISION-designacao-2026-08-25.md` ·
`DESIGNATION-SEED-2026-08-26.md` · `DESIGNATION-2026-08-26.json` ·
`p2-verdict-frame-2026-08-26.csv` · `src/api/brief-diversity.ts:130-140`, `:53-63` ·
`src/api/brief.ts:719-748`, `:1086` · `src/paper2/brief-outcome.ts:17-22`.

## Anexo B — revisões adversariais desta emenda

Duas famílias de treino distintas, ambas com recibo verificável, ambas
**recomendando não depositar a primeira redação**.

| voz | modelo | `exit` | bytes | `sha256` do output | recibo |
|---|---|---|---|---|---|
| GLM | `glm-5.3` | 0 | 9.535 | `fd0851001d0e285d…` | `adversary-receipt-glm-2026-08-26T231155-90950.txt` |
| Codex | OpenAI gpt-5.6-sol | 0 | 1.472.973 | `efd9342789d6ed29…` | `adversary-receipt-codex-2026-08-26T231314-92025.txt` |

⚠️ **O GLM revisou sem os arquivos** — declarou *"nenhum arquivo foi anexado"* e
trabalhou sobre o briefing. Isso invalida os achados dele sobre *o que a emenda
omite*, e preserva os **lógicos**: a circularidade da varredura, os ~11σ da linha
de base contra a leitura forte, a realimentação de `last_served`, e a natureza de
medida-de-conjunto do `churn`.

**Um achado do GLM foi REFUTADO por medição:** ele levantou que `churn` é
set-difference, logo reordenação interna ao conjunto selecionado seria invisível.
Testei comparando as **sequências** posição a posição — 28 casos, 4 doses × 7
agentes, incluindo `w = 100.000`: **0 casos** com ordem diferente. O ponto
arquitetural é correto e fica registrado como limitação da métrica; o canal
escondido não existe neste estado.

O recibo do Codex estava num **terceiro** diretório (`.remember/` da raiz do repo,
não do subdiretório) — a mesma armadilha de 2026-08-25. Ausência de recibo no lugar
esperado não é ausência de recibo.
