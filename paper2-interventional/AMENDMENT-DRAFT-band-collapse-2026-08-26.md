# Emenda — colapso da banda e eliminação de `Δ_cut`

**Registro emendado:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
concept `10.5281/zenodo.21964093`, última versão depositada **v1.12**
(`10.5281/zenodo.22110203`, 2026-08-26T14:01Z).

**Versão: a ser atribuída no depósito.** Este arquivo é **rascunho** e não carrega
número. A lição é de 2026-08-25: número de versão é fato do depósito, não rótulo do
texto — chamar um rascunho de "v1.13" já criou uma v1.12 fantasma numa redação
anterior, quando a última real era a v1.11.

**Redigida:** 2026-08-26, à noite, depois de a designação ser congelada às 20:28Z e
de `Δ_cut` ser medido entre 20:35Z e 21:00Z.

**Código servindo.** Último commit que tocou `src/`: **`0087c918`**
(2026-08-26T20:25:01Z), no repo `nox-workspace`. Pinos por arquivo, para os que
esta emenda cita por linha:

| arquivo | commit | data |
|---|---|---|
| `src/api/brief.ts` | `0087c918` | 2026-08-26T20:25:01Z |
| `src/paper2/brief-outcome.ts` | `0087c918` | 2026-08-26T20:25:01Z |
| `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23−03:00 |
| `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55−03:00 |

`brief-diversity.ts` está inalterado desde junho, e é onde vive o comparador que
esta emenda mede. Isso importa: a dominância lexicográfica que ela reporta **não é
consequência de mudança recente** — está no código desde antes de o Paper 2
existir.

---

## §0. Natureza e limites desta emenda

**O que ela é.** Duas coisas, e nada mais: **fecha** o defeito que a v1.12 §5
declarou aberto — a designação —, e **abre e resolve** o item 3 do §5.3 daquela
emenda, `Δ_cut`.

**O que ela faz de substantivo.** Retira do desenho um fator manipulado que, medido,
não existe. A banda `w ∈ {2,0 · 4,0 · 7,5}` deixa de ser três níveis de dose e
passa a **um** braço de tratamento. `Δ_cut` deixa de ser parâmetro.

**O que ela NÃO faz.** Não muda o mecanismo de intervenção (o boost continua
aditivo em `salience`, no estágio (b)). Não reabre λ, nem a série de piloto, nem as
28 retratações da v1.12. Não declara o `T_seed_assign`.

**⚠️ Ela move um elemento declarado imóvel.** `PREREG-DRAFT.md:44` lista a banda
`{2.0, 4.0, 7.5}` entre *"what does not move, and could not"*. Ela move. A razão
não é conveniência nem resultado: é que a quantidade pela qual a banda multiplica
(`Δ_cut`) não tem referente, e um multiplicador sem multiplicando não define
níveis. Mover um elemento imóvel exige exatamente o que este documento faz —
declarar, medir, e depositar antes do sorteio de braço.

**Uma coisa boa, dita sem consolo.** A ausência de dose foi detectada **antes** de
o experimento consumir amostra. A contribuição declarada do Paper 2 é o **método**;
um mecanismo que se descobre inerte antes de rodar é produto do método, não falha
dele. Isso não reduz a gravidade do achado — reduz o custo.

---

## §1. Fechado: a designação

A v1.12 §5 declarava, corretamente, que a regra de designação não estava
validamente congelada, por três defeitos medidos: consumia `CUT_FRESH` como
limiar que o código não aplica, o desempate registrado nomeava `created_at`
(coluna inexistente em `p2_verdict`, logo **não-implementável**), e `w_min`
derivava de `access_count`, mutável por tráfego de busca exógeno.

**Substituída, declarada e vigente.**

| | |
|---|---|
| decisão | 2026-08-26T14:47Z, opção B, **antes** de qualquer código, com o custo de 8,8% de dose já medido |
| regra | `designado(g) = argmin_{c ∈ g} SHA256( seed ‖ "\|" ‖ chunk_id )`, global |
| declaração | `DESIGNATION-SEED-2026-08-26.md`, push **20:07:24Z** *(data do GitHub)* |
| rodada | drand quicknet **31657512**, emissão **20:25:00Z** — folga **1.056 s** |
| estado na declaração | `GET .../public/31657512` → **HTTP 425**, não emitida |
| frame | `p2-verdict-frame-2026-08-26.csv`, 55 linhas, `sha256` `9d0d80d6…`, push **20:08:55Z** — também antes do sorteio |
| seed | `e5d134ee110a33870f68963ae47a39bbee208586328d2311ac6626eed42122d7` |
| conjunto | 19 grupos, 19 designados distintos, `sha256` `e549420907cd…da001b` |
| congelado em | `DESIGNATION-2026-08-26.json`, preso por path + `sha256` no serving |
| vigente desde | **20:28Z** |

**`sig_primary` saiu da chave**, e isso foi corrigido às 19:40Z, antes de congelar.
Todos os 19 valores reais contêm `|` — o próprio separador —, então o layout
aprovado às 14:47Z não era injetivo: `seed ‖ "Bash|shell:outro" ‖ 308226` e
`seed ‖ "Bash" ‖ "shell:outro|308226"` são a mesma sequência de bytes. A correção
foi remover o campo, não trocar o separador, porque cada chunk pertence a
exatamente um grupo (0 de 55 em mais de um, excluídas as 225 linhas S0, que têm
`chunk_id NULL`). A propriedade estatística é idêntica; o ganho é a chave passar a
depender só de ids congelados.

**Verificação cruzada em duas implementações lendo fontes diferentes.** A TS
(`designadosGlobais`) consultou `p2_verdict` **ao vivo**; o Python
(`designation_verify.py`) leu o **CSV depositado** 16 minutos antes. Os `sha256` do
conjunto batem, o que prova de uma vez que as derivações são a mesma regra **e** que
o frame publicado corresponde à tabela real. Cinco mutações do fonte TS foram
confirmadas fazendo os testes falharem (separador removido, seed como bytes, sha1
no lugar de sha256, filtro de S0 removido, desempate entregue à ordem de linha).

---

## §2. Medido: `Δ_cut` não tem referente a encontrar

A v1.12 §1.5 declarou `Δ_cut = 0,043` como *"pendente de definição operacional e de
medição"*. Essa formulação supõe que existe definição a achar. **Não existe**, e a
razão é estrutural.

O comparador do pool de cobertura é lexicográfico
(`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;   // last_served ASC — domina
return bSalience - aSalience;    // salience só desempata last_served IDÊNTICO
```

O boost é aditivo **em `salience`**, a coordenada subordinada. Quando `last_served`
difere, o comparador devolve `al − bl` e **nunca consulta `salience`**. Nenhum
valor de `w · Δ_cut · severidade` atravessa a diferença.

### O estado medido do pool

Snapshot de epoch `e20260826T060003Z.db` como corpus, DB vivo como estado de
serving, `freshSlots = 2`:

| posição | `last_served` | `salience` | do estudo? |
|---|---|---|---|
| 0 | `2026-08-26 18:37:05` | 0,682220 | não |
| 1 | `2026-08-26 18:37:05` | 0,682220 | não |
| 2 | `2026-08-26 18:37:05` | 0,682220 | não |
| **3** | **`2026-08-26 18:37:06`** | **0,712751** | **sim** (308220) |

O chunk do estudo tem `salience` **mais alta** e perde, porque foi servido **um
segundo depois**. Um segundo é barreira absoluta.

| | |
|---|---|
| candidatos no pool | **108** (o `WHERE` corta bem antes do `LIMIT 400`) |
| chunks do estudo no pool | **55 de 55** |
| **nunca-servidos no pool** | **0** |
| grupos de `last_served` distintos | 44 |
| tamanhos de grupo | 1: 3 · 2: 29 · 3: 1 · **4: 11** |

### Barredura de dose, dual-compute offline

Sete agentes (`nox`, `lex`, `atlas`, `boris`, `cipher`, `forge`, sem agente),
`n = 10`, provedor instrumentado:

| `w` | boosts emitidos | `churn` |
|---|---|---|
| 2,0 | 19 | **0** em 7/7 |
| 4,0 | 19 | **0** em 7/7 |
| 7,5 | 19 | **0** em 7/7 |
| **1.000** | 19 | **0** em 7/7 |
| **100.000** | 19 | **0** em 7/7 |

Os 19 boosts **são** emitidos, e `churn` é zero até em `w = 100.000`.

### A banda satura no braço mais baixo

Gaps de `salience` entre pares adjacentes **dentro de grupos de empate** que
envolvem estudo: 38 pares, dos quais **11 (28,9%) exatamente zero**, e 27
positivos com máximo **0,031809**.

| `w` | S1 (0,25) | vence | S2 (0,5) | vence |
|---|---|---|---|---|
| **2,0** | 0,0215 | 16/27 | 0,0430 | **27/27** |
| 4,0 | 0,0430 | **27/27** | 0,0860 | 27/27 |
| 7,5 | 0,0806 | 27/27 | 0,1613 | 27/27 |

**A única faixa com discriminação de dose é S1 entre `w = 2,0` e `w = 4,0`.** Todo
o resto da banda é indistinguível de si mesmo.

### A condição de ativação, e ela existe no código

Os grupos de empate são **os lotes de um mesmo brief**: um brief insere N linhas em
`brief_log` na mesma transação, logo com o mesmo `served_at` — e `served_at` tem
resolução de **segundo**. Daí a ativação exigir que o grupo **na fronteira de
seleção** seja:

1. **misto** — contenha estudo e não-estudo; se puro-estudo, o boost reordena
   estudo contra estudo e não desloca controle;
2. **maior que `freshSlots`** — se `|grupo| ≤ 2`, todos entram e não há disputa.

Medido: **5 de 44 grupos (11,4%)** qualificariam se estivessem na fronteira. O
melhor colocado entre eles começa na **posição 15**, e a fronteira é 0–1.

⚠️ Não confundir com a posição 3: lá há um grupo **misto**, mas de tamanho 2, e
tamanho 2 não qualifica — com `freshSlots = 2` os dois membros entram e não há
disputa. O primeiro grupo que satisfaz **as duas** condições está na posição 15.
A distinção importa porque é ela que separa "há um chunk do estudo perto da
fronteira" de "há oportunidade de tratamento".

Compare com o `churn` positivo histórico: **132 de 3.166 = 4,1693%**, em janela
fechada por `sha256` do NDJSON (`2026-08-21T22:57:48.194Z` →
`2026-08-26T19:52:07.775Z`). Mesma ordem de grandeza — o que é o que se espera, já
que qualificar não basta: o boost ainda tem de vencer o gap e o deslocado tem de
estar no brief.

### O que a medição NÃO estabelece

⚠️ **Não estabelece que o mecanismo é inerte.** A varredura mediu **um** estado do
pool, e zero num instante é compatível com uma taxa de 4%. O achado é
**estrutural**: *sem colisão na fronteira, dose nenhuma age*. A frequência da
colisão é propriedade da série temporal.

⚠️ **O controle positivo que passa não é o harness offline.** Montei dois, e ambos
deram zero em `w = 100.000`. O primeiro estava genuinamente errado — usei o DB vivo
como corpus **e** como estado de serving, quando produção serve o corpus do
snapshot de epoch (`NOX_EPOCH_SNAPSHOT=active`) e o `brief_log` do vivo, o que
ativa caminho de código diferente. Corrigido. O segundo, no caminho certo, também
deu zero, e aí não era defeito. O controle positivo que **passa** é o teste
unitário que constrói dois chunks **nunca-servidos** — empate em `NULL` — e vê o
boost deslocar. O mecanismo funciona exatamente onde há empate.

---

## §3. As cinco decisões

### 3.1 A banda colapsa para um braço

`w ∈ {2,0 · 4,0 · 7,5}` → **dois braços: controle e tratamento**, com o tratamento
em `w = 4,0`.

**Por que 4,0 e não 2,0:** a `w = 4,0` o boost vence **27/27** dos gaps positivos
em **ambas** as severidades; a `w = 2,0` o S1 vence apenas 16/27. Escolher o valor
que satura em toda a população evita que a severidade se torne, de fato, um segundo
fator de tratamento não declarado.

**Por que colapsar e não manter três:** manter níveis indistinguíveis gasta poder
estatístico para estimar zero, e a diferença medida entre eles é **menor que o
gap máximo do pool** em toda a banda exceto uma célula. Um desenho de resposta-dose
cujo braço mais baixo já satura não pode exibir resposta-dose.

### 3.2 `Δ_cut` é eliminado, não redefinido

O tratamento passa a ser definido por propriedade, não por produto de constantes:

> **Tratamento:** termo aditivo em `salience`, aplicado ao chunk designado, de
> magnitude suficiente para vencer qualquer gap de `salience` dentro de um grupo de
> `last_served` idêntico.

O valor operacional (`0,172 = 4,0 · 0,043 · 1,0` no teto de severidade; `0,043`
para S1, `0,086` para S2) fica registrado como **implementação da propriedade**,
justificado pelo máximo medido de **0,031809**, e não como parâmetro com
interpretação própria.

⚠️ **Não é renomeação.** Renomear preservando o valor é a classe de defeito da
retratação 2 da v1.12 — trocar o rótulo e manter a aritmética. Aqui a aritmética
deixa de ter estatuto: nenhuma afirmação do paper passa a depender do valor de
`Δ_cut`, porque a única propriedade que importa é *vencer o gap*, e ela é
verificável por consulta.

### 3.3 O estimando passa a ser condicional à oportunidade

A v1.12 e o pré-registro tratam o efeito como incondicional. Medido, isso é
insustentável: em briefs sem colisão na fronteira o tratamento é **estruturalmente
incapaz** de agir, e incluí-los no denominador estima a taxa de colisão, não o
efeito.

> **Conjunto de oportunidade:** decisões de brief em que o grupo de `last_served`
> na fronteira de seleção é misto e tem mais membros que `freshSlots`.

Essa definição é **computável a partir do registro** — `designated_ids` e
`boost_by_id` no log de serving, mais `brief_log`, dão os dois predicados. É o
contraste com `Δ_cut`, cuja definição registrada ("spread no cut") nomeava algo que
o código não tem.

O efeito incondicional continua reportável, e **deve** ser, como produto do efeito
condicional pela taxa de oportunidade. O que sai do desenho é tratá-lo como o
estimando primário.

### 3.4 O boost NÃO se move para `last_served`

A saída óbvia seria pôr o tratamento na coordenada dominante — tratar o chunk como
servido `k` segundos antes. Aí a dose existiria de verdade, mensurável em segundos,
e a resposta-dose voltaria.

**Recusado aqui, e não por mérito.** Isso é **mecanismo novo**, não calibração:
muda o que a emenda declara intervir. Se algum dia valer, vale com a disciplina
que a opção B teve — medir, decidir com o número na mesa, declarar antes de
implementar, depositar. Enfiá-lo nesta emenda seria trocar o mecanismo no mesmo
documento que o descreve.

### 3.5 A taxa de colisão NÃO se torna o estimando

A terceira saída seria assumir que o tratamento é *por construção* gated por
colisão e reportar a taxa como o resultado.

**Rejeitada.** É promover uma limitação estrutural a achado, o que é precisamente
o movimento condenado pela retratação 2. A colisão é propriedade do esquema de
`served_at` com resolução de segundo — um detalhe de implementação do `brief_log`,
não um fenômeno de memória.

---

## §4. Retratações novas

Continuam a numeração da v1.12, que fecha em 28.

| # | data | retratado | o que substitui |
|---|---|---|---|
| **29** | 26/08 | `Δ_cut` está "pendente de definição operacional e de medição" (v1.12 §1.5) — supõe definição a achar | não há: a quantidade é lexicograficamente dominada. Eliminado como parâmetro (§3.2) |
| **30** | 26/08 | `w ∈ {2,0 · 4,0 · 7,5}` são três níveis de dose | satura no braço mais baixo para S2; ≤ 2 níveis distinguíveis, e só para S1. Colapsa para um braço (§3.1) |
| **31** | 26/08 | a banda está entre *"what does not move, and could not"* (`PREREG-DRAFT.md:44`) | move, e a razão é o multiplicando não existir (§0) |
| **32** | 26/08 | `W_OUTCOME = w × Δ_cut` é "a multiple of the measured salience spread at the brief cut" (`PREREG-DRAFT.md:414`) | não há cut; o referente honesto é o gap dentro de grupo de empate, cuja distribuição está publicada (§2) |
| **33** | 26/08 | o chunk do estudo é nunca-servido, logo está sempre entre os 400 (`brief-outcome.ts:17-22`) | zero nunca-servidos no pool; os 55 já foram servidos, os 3 amostrados com 47-48 servings cada. A conclusão (estar no pool) segue verdadeira por outra razão: o pool tem 108, não 400 |
| **34** | 26/08 | a designação é defeito **aberto** (v1.12 §5) | fechada 26/08 20:28Z, com precedência verificável (§1) |
| **35** | 26/08 | o efeito é incondicional | condicional à oportunidade, com o conjunto definido por predicado computável (§3.3) |

**Refinamento, não retratação.** A retratação 8 da v1.12 afirma que o boost atua —
*"111 deslocamentos em 102 decisões"* — já hedgeada como condicional à designação
executada. Ela permanece verdadeira, e agora se sabe **onde**: aqueles 111
deslocamentos ocorreram nas situações de colisão. O número não muda; sua
interpretação fica mais estreita.

---

## §5. Consequência para `N`, e o que fica pendente

**`N` não pode ser fixado agora, e fixá-lo com o número velho seria erro.** Os
4,1693% de `churn` positivo são de quando havia **1** designado por grupo escolhido
por `w_min`. Sob a regra nova há **19** designados, e a taxa de oportunidade deve
subir. A magnitude do aumento é medível, mas só com janela real: a regra nova está
vigente desde 20:28Z e a série acumula a ~26 linhas/h.

**Recomendação operacional:** deixar a janela acumular — um dia dá ~600 decisões —
e recalcular `N` sobre a taxa de oportunidade medida sob a regra vigente, com a
mesma disciplina de janela fechada por `sha256` que esta emenda usa em toda parte.

Pendente, e explicitamente fora desta emenda:

- **`T_seed_assign`.** Continua não declarado. Sortear braço de uma banda que esta
  emenda colapsa seria gastar o sorteio, e a decisão de 2026-08-17 já condiciona o
  sorteio ao mecanismo congelado.
- **`N` final**, dependente da janela acima.
- **Mover o boost para `last_served`** (§3.4), se algum dia.

---

## §6. Ordem de operações

1. Esta emenda depositada. *(A banda está no pré-registro; mudá-la sem depósito
   seria alterar desenho registrado sem selo.)*
2. Janela de ativação acumulada sob a regra vigente; taxa de oportunidade medida.
3. `N` recalculado sobre essa taxa.
4. Registro prospectivo do estimando condicional.
5. `T_seed_assign` declarado, com precedência verificável, e `ASSIGNMENT.json`
   publicado.
6. `NOX_P2_OUTCOME=active`.
7. Epoch 1.

Nada de 4 a 7 começa antes de 1 a 3.

---

## Anexo — proveniência

**Medições desta emenda.** Todas de 2026-08-26, entre 20:35Z e 21:00Z, sobre
`e20260826T060003Z.db` (corpus) e o DB vivo (estado de serving). Scripts
versionados em `nox-workspace`, commit `1b0d7df6`:
`scripts/mede-delta.mjs` (estrutura de empate), `scripts/dose2.mjs` (dual-compute
no caminho de produção), `scripts/controle-positivo.mjs` (doses absurdas),
`scripts/dose-response.mjs` (**a primeira versão, errada** — mantida versionada
como registro do erro, não para uso). Nenhum escreve em `brief_log`:
`buildBriefDiverse` não faz tracking, logo a medição não contamina `last_served`.
Detalhe completo em `MEASUREMENT-delta-cut-2026-08-26.md`.

**Achado colateral registrado.** `/api/brief` **não tem gate de tracking** —
`brief.ts:1086` insere em `brief_log` sempre, e `brief_log` alimenta `last_served`.
Não existe equivalente ao `?track=false` do `/api/search`. Três sondas minhas de
verificação escreveram 15 linhas tocando 3 chunks do estudo; **não foram apagadas**,
e a razão inverteu minha decisão inicial: os 3 já tinham 47-48 servings, o último
1h51 antes, logo são as linhas 48/49 de uma série que o tráfego real já produzia —
não a mudança qualitativa nunca-servido → servido, que seria consequente. Registro
em `DECISION-designacao-2026-08-25.md`.

**Fontes.** `AMENDMENT-v1.12.md` §1.5, §4, §5.3 · `PREREG-DRAFT.md:44`, `:414` ·
`DECISION-designacao-2026-08-25.md` · `DESIGNATION-SEED-2026-08-26.md` ·
`DESIGNATION-2026-08-26.json` · `p2-verdict-frame-2026-08-26.csv` ·
`MEASUREMENT-delta-cut-2026-08-26.md` · `src/api/brief-diversity.ts:130-140`,
`:53-63` · `src/api/brief.ts:719-748`, `:1086` · `src/paper2/brief-outcome.ts:17-22`.
