# Emenda — `Δ_cut` perde estatuto de parâmetro, e o estudo fica BLOQUEADO

**Registro emendado:** OSF `yf7d2` (registrado 2026-08-18T07:56:44Z) · Zenodo
concept `10.5281/zenodo.21964093`, última versão depositada **v1.12**
(`10.5281/zenodo.22110203`, 2026-08-26T14:01Z).

> 🟡 **STATUS 2026-08-27T16:52 BRT — NÃO DEPOSITADA, por decisão.** O Toto optou por
> **não emendar o registro por enquanto**: o pré-registro fica como registrado e os
> desvios vão no **paper**. Este documento passa a ser o **registro interno** que
> alimenta essa seção do paper, e a obrigação está em `DEVIATIONS-FOR-PAPER.md`.
> A máquina do depósito (`deposit/PLAN-v1.13.md`, `deposit/deposit-v1.13.sh`) está
> pronta e intocada — nada foi enviado ao Zenodo.
>
> ⚠️ Consequência aceita, e ela é assimétrica: enquanto isto não for reportado, o
> registro público afirma três coisas falsas sobre `Δ_cut`, a banda e a alocação, **e**
> declara a designação como defeito *aberto* quando ela está fechada. Essa última é a
> única em que o registro está **pior** que a realidade.

**Versão: não atribuída.** Este arquivo é **rascunho** e não carrega número. Número de
versão é fato do depósito, não rótulo do texto — e como não houve depósito, não há
número. *(A v1.13 preparada em 27/08 permanece preparada, não publicada.)*

**Histórico de redação.** Primeira redação 2026-08-26 à noite. **Segunda redação
26/08 23:40Z**, depois de duas revisões adversariais (GLM-5.3 e Codex/gpt-5.6-sol)
derrubarem **três das cinco decisões** da primeira — o que caiu está no §7, nomeado.
**Terceira passagem 27/08**, depois de mais três revisões (DeepSeek V4-Pro, Kimi, e
Codex como voz decisória) apontarem **defeitos de instrumento**: as medições afetadas
foram **refeitas**, e o que a remediação achou está em
`REMEDIATION-2026-08-27.md`. **Recibos** das cinco vozes em `receipts/`; a **saída
integral** só da voz decisória — as outras quatro não foram persistidas e são
irrecuperáveis (§9).

**Sexta leitura 27/08, 13:00Z (Fable), e foi a primeira a verificar de fora.** Buscou
a rodada drand na API pública, reproduziu a seed, **rederivou os 19 designados a partir
do CSV depositado** e recomputou toda a estatística — o núcleo do §1 e do §2 resistiu.
Achou um defeito que cinco leituras deixaram passar: o documento afirmava ter as saídas
das cinco vozes, e há **uma** (retratação 44). É a mesma classe dos outros dois defeitos
que sobreviveram à revisão — o commit `0087c918` e as cinco sondas: **afirmação
verificável que ninguém verificou**. As três só caíram quando alguém tentou *usar* o
que o texto afirmava.

⚠️ **Duas correções que a terceira rodada me fez propor estavam ERRADAS**, e a
remediação as retirou antes de entrarem aqui (§7.4). O rascunho estava certo nos dois
pontos.

**Código servindo, depositado.** Último commit que tocou `src/`: **`1da78560`**
(2026-08-26T20:25:01+00:00), repo `nox-workspace`. Os blobs estão neste pacote, com
`sha256` por arquivo em `SERVING-CODE-MANIFEST.md`.

| arquivo | commit | data | `sha256` do blob |
|---|---|---|---|
| `src/api/brief.ts` | `1da78560` | 2026-08-26T20:25:01+00:00 | `27dbe9962a2903aa…` |
| `src/paper2/brief-outcome.ts` | `1da78560` | 2026-08-26T20:25:01+00:00 | `b3a3b1a8c72fe791…` |
| `src/__tests__/p2-outcome.test.ts` | `1da78560` | 2026-08-26T20:25:01+00:00 | `62ba78d141aafe4c…` |
| `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23−03:00 | *(v1.12)* |
| `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55−03:00 | *(v1.12)* |

`brief-diversity.ts` está inalterado desde junho, e é onde vive o comparador que
esta emenda mede. A dominância que ela reporta **não é consequência de mudança
recente** — está no código desde antes de o Paper 2 existir.

⚠️ **Redações anteriores desta emenda pinavam o código em `0087c918`, e esse objeto
não existe.** Não é commit, não está em ref nenhuma, não está no reflog. O conteúdo é
o certo — `1da78560` tem o mesmo timestamp de committer e a mesma mensagem, e os
arquivos contêm exatamente as funções que o §1 descreve. O que mudou foi o **nome**:
o merge `5174e0fa` (*"reconcilia VPS (17 commits, 23-26/ago) com origin"*, 21:02:13Z
da mesma noite) reescreveu os hashes dos commits do lado da VPS.

**Hash de commit não é identificador estável através de reconciliação de histórico.**
Um documento que pina código só por commit adquire citação pendurada no instante em
que alguém rebaseia, e a falha é silenciosa: a prosa continua lendo como precisa. Por
isso cada linha da tabela carrega também o `sha256` dos **bytes do arquivo** — esse
pino sobrevive a qualquer reescrita, e é o que um terceiro pode conferir contra o blob
depositado sem acesso ao repositório privado.

---

## §0. Natureza e limites desta emenda

**O que ela faz, e é só isto:**

1. **Fecha** o defeito que a v1.12 §5 declarou aberto — a designação (§1).
2. **Retira `Δ_cut` do estatuto de parâmetro científico**, porque o referente que o
   registro nomeia não existe, e o que existe não está registrado nem validado como
   estável (§2, §3).
3. **INVALIDA a banda `{2,0 · 4,0 · 7,5}` como escala calibrada de dose**, sem
   substituí-la por outra (§3).
4. **BLOQUEIA o início do estudo** até um protocolo de calibração prospectivo
   existir (§5).
5. **Declara e corrige três defeitos de instrumento** nas próprias medições
   (§4.1-bis, §4.2, §9).

**O que ela deliberadamente NÃO faz, e a primeira redação fazia:**

- **NÃO** fixa um braço único em `w = 4,0`. Essa escolha era pós-calibração
  vestida de propriedade derivada (§7.1).
- **NÃO** troca o estimando primário para condicional à oportunidade. Isso
  **reabria a F2**, uma FATAL fechada em 2026-07-12 (§7.2).
- **NÃO** define `N` a partir de taxa de oportunidade medida. Isso **reabria a
  F3** (§7.3).
- **NÃO** afirma que doses absolutas deixem de existir, nem que recalibração futura
  seja impossível. O que morre é a **interpretação spread-relative** da banda.

**Por que descritiva e bloqueante, em vez de redesenhadora.** A v1.12 já foi
depositada como emenda descritiva, e por bom motivo: mudar mecanismo no mesmo
documento que o descreve é indistinguível de racionalizar a mudança. Aqui vale em
dobro — as decisões de desenho que a primeira redação tomou foram justamente as que
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
| congelado em | `DESIGNATION-2026-08-26.json`, preso por path + `sha256` do **arquivo**: `0a04d2d41c4e3f1c86088223ea834b79a39eaedfec4954595436d1632eda0a76` (1.782 B) |
| vigente desde | **20:28Z** |

⚠️ O `sha256` que a env prende é o do **arquivo** (`0a04d2d4…`), não o do conjunto
(`e549420907cd…`). São hashes de coisas diferentes e a primeira redação citava só o
segundo — o Kimi cobrou, com razão: quem for reproduzir precisa do que a env checa.

**`sig_primary` saiu da chave**, corrigido às 19:40Z, antes de congelar: todos os 19
valores reais contêm `|`, o próprio separador, logo o layout aprovado às 14:47Z não
era injetivo. Removido o campo em vez de trocado o separador, porque cada chunk
pertence a exatamente um grupo (0 de 55 em mais de um, excluídas as 225 linhas S0,
que têm `chunk_id NULL`). Propriedade estatística idêntica; ganho é a chave passar
a depender só de ids congelados.

**Verificação cruzada em duas implementações lendo fontes diferentes.** A TS
consultou `p2_verdict` **ao vivo**; o Python leu o **CSV depositado** 16 min antes.
Os `sha256` do conjunto batem, o que prova de uma vez que as derivações são a mesma
regra **e** que o frame corresponde à tabela nos campos que entram na chave. Cinco
mutações do fonte TS foram confirmadas fazendo os testes falharem.

⚠️ **Limite do cruzamento:** ele prova correspondência nos **19 designados** e nos
campos que a chave consome (`chunk_id`, `severity` para o filtro). **Não** prova
correspondência integral das 55 linhas do frame com a tabela — nenhuma coluna fora
da chave é verificada por esse hash.

⚠️ **Isto é o único item desta emenda que está fechado.** Todo o resto é
diagnóstico e bloqueio.

---

## §2. `Δ_cut` não tem o referente que o registro nomeia

A v1.12 §1.5 declarou `Δ_cut = 0,043` *"pendente de definição operacional e de
medição"* — formulação que supõe existir definição a achar, e que o registro nomeia
como *"the measured salience spread at the brief cut"* (`PREREG-DRAFT.md:414`).

O comparador do pool de cobertura é **lexicográfico**
(`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;   // last_served ASC — domina
return bSalience - aSalience;    // salience só desempata last_served IDÊNTICO
```

O boost é aditivo **em `salience`**, a coordenada subordinada. Quando `last_served`
difere, o comparador devolve `al − bl` e **nunca consulta `salience`**. Não existe
"cut": o código não aplica limiar nenhum.

**Esta parte é dedutiva, não estatística**, e é a única afirmação estrutural que
esta emenda faz. Não depende de medição nenhuma.

⚠️ **Delimitação, e ela importa.** A dedução é local ao **comparador**. Ela
estabelece que `salience` não decide entre `last_served` distintos; **não**
estabelece o que o pipeline completo faz com o pool ordenado (§4.1). E o enunciado
correto do que morre é preciso:

> Não existe referente operacional **registrado** para `Δ_cut = 0,043`. Existe uma
> quantidade — o **gap de `salience` dentro de estratos de `last_served` idêntico** —
> mas nenhuma funcional da distribuição dela foi registrada, validada quanto à
> transportabilidade, nem congelada antes da calibração. A banda perde a
> interpretação *spread-relative*. Qualquer escala substituta exige calibração
> prospectiva, replay do pipeline completo e emenda própria **anterior** ao sorteio.

Dizer "não congelável" seria forte demais, e a segunda redação dizia: o gap **é**
congelável como estatística de janela pré-tratamento. O que falta é estabilidade
demonstrada.

### O que a medição mostra, e o que ela NÃO estabelece

Um estado do pool. **O instante exige três declarações, não uma** — sem as três,
a tabela envelhece para falsa:

| | |
|---|---|
| `T_REF` | **2026-08-26 20:35:00Z** |
| corpus | snapshot de epoch `e20260826T060003Z.db` (o que produção serve) |
| estado de serving | `brief_log` **vivo**, limitado a `T_REF` |

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
| pares **adjacentes dentro do grupo de empate** envolvendo estudo | 38 pares, **11 exatamente zero**, 27 positivos |
| gap máximo **intragrupo** | **0,031808734967844865** |

⚠️ **A definição de "par" é parte do número.** No mesmo instante e corpus, três
definições plausíveis dão respostas diferentes:

| definição | pares | zeros | positivos | `gap_max` |
|---|---|---|---|---|
| adjacentes na ordenação global | 67 | 15 | 52 | 0,05680873 |
| **adjacentes DENTRO do grupo de empate** *(a usada)* | **38** | **11** | **27** | **0,031808734967844865** |
| todos os pares dentro do grupo | 60 | 12 | 48 | 0,05553096 |

A segunda é a semanticamente certa — `salience` só decide dentro de empate — e é a
que os números publicados usam. A primeira redação não dizia qual, o GLM cobrou o
escopo, e a remediação de 27/08 mostrou que o descasamento entre reconstruções era
**de definição, não de deriva** (`REMEDIATION-2026-08-27.md` §2).

⚠️ **Nenhum dos 38 pares tem gap negativo, e isso NÃO é achado.** É verdadeiro por
construção: a ordenação é `salience DESC` dentro do empate, logo a diferença entre
adjacentes é ≥ 0 necessariamente. A primeira redação apresentava isso como
propriedade observada.

⚠️ **O estado rotaciona.** Onze horas movem a menor posição de grupo qualificável de
24 para 44, com sondas excluídas nas duas pontas. Nenhum instante — contaminado ou
não — sustenta uma constante de registro. Medido em
`measurement/asof-sonda-vs-tempo.py`.

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

### A taxa histórica não é zero, e NÃO é estacionária

A primeira redação publicou `132 / 3.166 = 4,1693%` como linha de base. **Está
errado por diluição:** as 954 decisões pré-gate têm churn **estruturalmente
impossível** (0 de 954) e inflam o denominador. Comparar contagem filtrada com
não-filtrada é a mesma classe da retratação 2.

Base correta, **pós-gate** (epochs ≥ 23/08), sondas excluídas, janela fechada por
`sha256` do NDJSON (`measurement/tendencia.py`):

| dia | n | com `churn` | taxa | Wilson 95% |
|---|---|---|---|---|
| 23/08 | 308 | 42 | **13,6364%** | [10,25 ; 17,92] |
| 24/08 | 672 | 49 | 7,2917% | [5,56 ; 9,51] |
| 25/08 | 672 | 21 | 3,1250% | [2,05 ; 4,73] |
| 26/08 | 574 | 20 | 3,4843% | [2,27 ; 5,32] |
| **total** | **2.226** | **132** | **5,9299%** | [5,02 ; 6,99] |

*(2.226 é o total com `agent` presente; 2.229 incluindo 3 decisões sem agent. A
segunda redação citava `2.212`, de uma janela anterior mais curta.)*

**A taxa cai ~4× em quatro dias, e 23+24/08 concentram 69% dos eventos em 44% do
n.** Nenhuma taxa agregada pode ser citada como "a" linha de base — e nenhuma
comparação contra o agregado pode ser lida como efeito (§4.1-bis).

⚠️ **A segunda redação dizia que `5,9299%` está a "~11,8 desvios-padrão de zero".
Isso sai.** Zero é a fronteira do espaço binomial; um teste-z contra fronteira não é
válido, e a afirmação nem era necessária — 132 eventos em 2.226 decisões dizem que o
mecanismo age sem precisar de σ. A afirmação defensável é *"a dose age somente via
colisão, e satura acima de um limiar"*, nunca *"a dose não existe"*.

⚠️ Sobre a retratação 8 da v1.12: são **duas** razões distintas sobre a mesma janela
de 1.267 decisões pós-gate, e a segunda redação as somava numa só, errada. **102
decisões com `churn` em 1.267 = 8,0505%**; **111 deslocamentos somados em 1.267 =
8,7609%**. O `8,05%` publicado era a primeira, rotulada como se fosse a segunda.
Recomputado até 25/08 inclusive dá 112/1.652 = 6,78%. Os números não são
incompatíveis; são janelas diferentes de uma série que decai. A v1.12 não errou, e
esta emenda **não a retrata** — mas a comparação exige as janelas na mesa.

---

## §3. A banda é invalidada como escala calibrada, e nenhuma outra é declarada

**`W_OUTCOME = w · Δ_cut · severidade` não define escala de dose**, porque `Δ_cut`
não tem o referente que o registro nomeia. A banda `{2,0 · 4,0 · 7,5}` fica
**invalidada como escala calibrada**.

O que se mede quando há colisão, recomputado a partir dos 27 gaps depositados:

| `w` | limiar S1 (0,25) | vence | limiar S2 (0,5) | vence |
|---|---|---|---|---|
| **2,0** | 0,021500 | **16/27** | 0,043000 | 27/27 |
| 4,0 | 0,043000 | 27/27 | 0,086000 | 27/27 |
| 7,5 | 0,080625 | 27/27 | 0,161250 | 27/27 |
| 100.000 | 1.075 | 27/27 | 2.150 | 27/27 |

O menor `w` que vence todos os 27 em S1 é **2,9590**; acima dele nenhuma dose muda
nada neste estado.

⚠️ **11 dos 27 gaps DISTINGUEM `w = 2,0` de `w = 4,0` para S1.** Logo "a banda tem
níveis indistinguíveis" é **falso** para esse par, e a primeira redação dizia *"a
dimensão de dose não existe — medido, não suposto"*. Os dois revisores apontaram a
mesma contradição interna. O que o estado sustenta é `w = 4,0 ≈ w = 7,5` **naquele
instante**, não que colapsar seja inevitável.

**Por que a banda cai mesmo assim:** não porque os níveis sejam indistinguíveis,
mas porque **a unidade em que estão expressos não tem referente registrado**. Um
multiplicador de uma quantidade cuja unidade não foi registrada não é uma dose,
mesmo quando dois de seus valores produzem resultados diferentes.

⚠️ **E o que NÃO cai:** doses absolutas continuam existindo como constantes
executáveis em `salience`, e recalibração prospectiva continua **aberta**. Esta
emenda não fecha essa porta; ela exige que a escala substituta venha por emenda
própria, anterior ao sorteio (§5, item 4 do §8).

⚠️ **Não é possível ter as duas coisas.** A primeira redação definia o tratamento
como *"magnitude suficiente para vencer qualquer gap dentro de empate"* **e**
fixava valores absolutos. Se a magnitude é fixa, um gap futuro de 0,045 derrota S1
a `w = 4,0`; se ela se adapta aos gaps, deixa de ser fixa e passa a depender de
dado pós-tratamento. Contradição apontada pelo Codex, e real.

Sobre extrapolar dos 27 gaps: sob independência — hipótese **generosa e provavelmente
falsa**, porque os valores se repetem, compartilham grupos e vêm de um só instante —
27 observações todas abaixo de 0,043 dariam limite superior unilateral de ~**10,5%**
para excedência futura. Trate isso como ordem de grandeza, não como bound. A margem
observada é `0,043 / 0,031809 ≈ 1,35×`.

---

## §4. Defeitos que a revisão expôs e que esta emenda declara

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
  afirmou que o mecanismo *"consome a própria oportunidade"* com base em 70,9% dos
  chunks do estudo estarem em grupo puro — **isso superou o dado** e fica retratado
  aqui antes de entrar em qualquer versão depositada.
- **`last_served IS NULL` ⇒ `−∞`.** Nesse estrato os nunca-servidos lideram e o
  boost **funciona** (é o que o teste unitário verifica). Hoje há 0 no pool, mas o
  estrato existe.

Logo **os 5/44 não medem a oportunidade do código**, e não podem sustentar `N`,
poder, nem definição de estimando. A definição correta exige replay do pipeline
completo.

**A hipótese de auto-extinção NÃO foi testada — e a segunda redação dizia que foi.**
Ela prevê que a fração de chunks do estudo em grupo puro-estudo **cresça com o
tratamento**. A série reconstruída (`measurement/autoextincao.py`):

| corte | grupos | puro-estudo | mistos | chunks do estudo em grupo puro |
|---|---|---|---|---|
| 23/08 | 26 | 9 | 8 | 34 de 55 — **61,8%** |
| 24/08 | 40 | 13 | 11 | 36 de 55 — **65,5%** |
| 25/08 | 41 | 15 | 11 | 34 de 55 — **61,8%** |
| 26/08 | 41 | 15 | 12 | 36 de 55 — **65,5%** |

⚠️ **Toda essa janela é anterior ao tratamento** — o mecanismo rodou em `shadow`/
controle o tempo inteiro. Uma série que nunca esteve sob tratamento não pode refutar
uma hipótese **sobre o efeito do tratamento**. O correto: a hipótese fica **não
testada**, e testá-la é item do protocolo prospectivo. A segunda redação escrevia
"testada e NÃO se sustenta"; o Codex apontou, e procede.

O que a série mostra é mais modesto e ainda útil: a fração é **estável e oscilante**
na ausência de tratamento, o que torna a fração alta atribuível ao **corpus** (os
chunks do estudo são co-servidos porque entram no mesmo brief) e não a acúmulo. A
queda de 13,64% para 3,48% na taxa de `churn` fica **sem explicação medida**.

⚠️ Duas ressalvas sobre a tabela: as colunas não somam para `grupos` porque há
grupos unitários e grupos puro-não-estudo fora das duas colunas do meio; e
`autoextincao.py` usa `julianday('now')`, logo a população elegível dele muda a cada
execução — pendência de instrumento registrada em `REMEDIATION-2026-08-27.md` §3.

### 4.1-bis Multiplicar designados por 19 não move a taxa de forma identificável

A regra nova entrou às 20:28Z de 26/08 e designa **19** chunks, um por grupo, contra
**1** da regra anterior por `w_min`. Se o gargalo fosse *quem* é designado, a taxa
de ativação subiria.

⚠️ **A segunda redação media isso com janela ABERTA por cima** (`ts >= REGRA`, sem
teto) e publicou `11/310`. O arquivo cresceu para 359 linhas pós-regra em doze
horas: **uma série viva citada como instante envelhece para falsa.** Refeito com
janela fechada (`measurement/remedia-serie.py`):

| | |
|---|---|
| janela | **`[2026-08-26T20:28:00Z , 2026-08-27T09:00:00Z)`** |
| NDJSON de origem | `sha256` `ca7ff52a7242bb031e5661fcab9d37a130a1f3b8331826175abf6ff0b382310a`, 3.542 linhas, 1.571.982 B — vive no host, **não** depositado |
| extrato **depositado** | `p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson`, 352 linhas, 302.470 B, `sha256` `5734036200316339e308d6c216ed59d75b071eb7f47d1db733856225ca644d28` |
| sondas | 2 decisões sem `agent` na janela, excluídas *(o NDJSON não tem `brief_id`, logo o discriminador ali é `agent` ausente)* |
| conferência | a soma das 13 horas fecha em 11/350, idêntica ao bloco |

⚠️ **"Ativação" aqui é CONTRAFACTUAL, não tratamento entregue.** Conferido no arquivo
depositado: `modo: shadow` e `servido: controle` em **352 de 352** decisões da janela. O
código computa os dois braços por desenho (`alt` e `altBoosted`, com `diffP2` sendo a
diferença) e serve o **controle**. Logo `churn > 0` significa *"o conjunto servido teria
diferido se o boost valesse"* — que é a taxa de **oportunidade**, e não uma taxa de
efeito. Nenhum tratamento foi entregue em nenhuma das 352.

| regime | oportunidade (contrafactual) | taxa | Wilson 95% |
|---|---|---|---|
| regra anterior, pós-gate **agregado** | 132/2.226 | 5,9299% | [5,02 ; 6,99] |
| regra anterior, **último dia** (26/08) | 20/574 | 3,4843% | [2,27 ; 5,32] |
| **regra nova (sorteio com seed)** | **11/350** | **3,1429%** | **[1,76 ; 5,54]** |

E aqui está o ponto que **as duas leituras anteriores erravam, em direções
opostas**:

| comparação | diferença | Newcombe IC95 | Fisher exato |
|---|---|---|---|
| nova vs pós-gate **agregado** | −2,7871 pp | [−4,53 ; −0,22] | **p = 0,0326** |
| nova vs **último dia** da anterior | −0,3415 pp | [−2,64 ; +2,35] | p = 0,8523 |
| nova (3,1429%) vs segmento **plano** 25+26/08 (3,2905%) | −0,1476 pp | — | — |

A comparação agregada é **significante e não deve ser usada**: ela mede composição
de dias, não efeito. Toda a diferença vem de incluir 23 e 24/08, que concentram 69%
dos eventos em 44% do n de uma série declinante. E a comparação adjacente, que é a
defensável, é **subpotente**: o poder para a diferença observada é da ordem de 7%.

**Enunciado defensável, e nada além dele** — lembrando que as três taxas são
contrafactuais em `shadow`, não efeitos:

> Na janela fechada `[2026-08-26T20:28:00Z , 2026-08-27T09:00:00Z)`, sob a regra
> nova, observaram-se 11 ativações em 350 decisões (3,1429%; Wilson [1,76; 5,54]).
> No último dia da regra anterior, 20 em 574 (3,4843%). A comparação não é
> randomizada, os segmentos são temporalmente confundidos, a série anterior é
> declinante e não estacionária, e o n é insuficiente: **não se estabelece aumento,
> redução nem equivalência, e nada aqui identifica o gargalo.** Afirmar
> equivalência exigiria TOST com margem pré-especificada, e nenhuma foi declarada.

Isto retira a suposição que a primeira redação carregava ("com 19 designados a taxa
deve subir") e que sustentava o plano de recalcular `N`, retirado no §7.3 — mas
**por insuficiência de identificação, não por refutação**.

Integridade do mecanismo na mesma janela: `designated_ids` = 19 e `boost_by_id` = 19
em **350 de 350** decisões — todos os designados no pool **e** maduros, sempre.
Recomputável do extrato depositado, e a sexta leitura cobrou justamente que essa
contagem não tinha artefato que a sustentasse.

### 4.2 O processo de verificação contaminou o estado, e o script que "descontaminava" não descontaminava

Sondas minhas em `/api/brief` escreveram em `brief_log`. `/api/brief` **não** tem
`?track=false`: sondar o endpoint escreve o estado que ele mede.

⚠️ **A justificativa que eu dei para não apagá-las usava a variável errada.**
Argumentei que os chunks *"já tinham 47-48 servings"* — mas o comparador não olha
**contagem**, olha **`MAX(served_at)`**. Numa emenda que afirma "um segundo é
barreira absoluta", tratar um deslocamento de 1h51 como inconsequente é incoerente.
O Codex apontou.

⚠️ **E eram cinco sondas, não três — 25 linhas, não 15.** A segunda redação contava
três. Varrendo por assinatura (brief orgânico = 10 linhas com `agent`; sonda = 5 sem
`agent`), desde 25/08 há 1.603 briefs de 10 linhas e exatamente 5 fora do padrão:

| `brief_id` | linhas | quando |
|---|---|---|
| `473f85e8-43ae-4883-baa2-2d76407af941` | 5 | 2026-08-26 19:58:17 |
| `c48e8353-cd95-4bd5-997b-dc921e2a0cac` | 5 | 2026-08-26 19:58:17 |
| `6ff2d9c4-79f2-4526-8eb5-c42d60bbeea6` | 5 | 2026-08-26 19:58:18 |
| `90a105f5-ef33-4135-8e54-b4e978bbb1ee` | 5 | **2026-08-26 20:28:55** |
| `66977ec1-2809-44df-91b8-c158ce0e68e8` | 5 | **2026-08-26 20:28:56** |

As duas últimas caem **dentro** da janela pós-regra, 55 s depois de o mecanismo
subir: são as sondas de *verificação*. **O ato de confirmar que a regra entrou
escreveu no primeiro minuto da série cuja taxa o §4.1-bis reporta.** Nenhuma das
cinco vozes adversariais achou isso; apareceu na remediação.

⚠️ `agent IS NULL` **não** serve como marcador de sonda: são 15.569 linhas em 5.889
briefs desde 2026-06-04, resíduo histórico de antes do campo existir. O
discriminador tem de ser o conjunto **enumerado** de `brief_id`.

⚠️ **`measurement/descontamina.py` fazia rollback temporal, não descontaminação.** A
linha 9 corta `served_at < 19:58`, removendo **3.735 linhas** para excluir **25** de
sonda. Duas leituras do fator, e ambas ficam na mesa porque a prosa anterior misturava
as duas: **149,4× o necessário** (3.735/25) ou **148,4× a mais** que o necessário
((3.735−25)/25). O `README.md` de `measurement/` afirmava que ele "reconstrói
o estado excluindo as 15 linhas das minhas sondas": falso no mecanismo **e** no
número. Fica versionado como registro do erro, marcado.

Refeito com exclusão por `brief_id`, mesmo `T_REF` e mesmo corpus da tabela do §2:

| métrica | observado | descontaminado | muda? |
|---|---|---|---|
| `pool` | 108 | 108 | — |
| grupos de `last_served` | 44 | 43 | sim |
| posição do 1º chunk do estudo | **3** | **0** | sim |
| pares adjacentes no grupo | 38 | 38 | — |
| gaps exatamente zero | 11 | 11 | — |
| gaps positivos | 27 | 27 | — |
| gap máximo | 0,031808734967844865 | *idêntico* | — |

**A contaminação atinge a posição, e nenhuma estatística de gap.** Logo as três
afirmações de saturação do §3 são **independentes** da contaminação. E, medido em
27/08 09:00Z: **efeito das sondas, nenhum** — doze horas de tráfego orgânico
lavaram-no inteiro (`measurement/asof-sonda-vs-tempo.py`).

⚠️ **A exclusão é cega ao braço e pré-randomização** — as sondas antecedem qualquer
designação de braço, e o critério (`brief_id` enumerado) não consulta tratamento.
Não é seleção sobre desfecho.

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

⚠️ **Corolário de instrumento:** `resolveCorpus` resolve o corpus pelo snapshot
**mais recente** de `epochsDir()`. Hoje isso é `e20260827T060001Z.db`, não o
`e20260826T060003Z.db` que sustenta o §2. Quem rodar "o mesmo script" amanhã usa
**outro corpus sem aviso**. Por isso o caminho do snapshot é parâmetro obrigatório
nos scripts remediados, sem default.

Isto interage com a F1 (carry-over) do `REVIEWS-PREREG.md` e **precisa de
tratamento no protocolo prospectivo**, não aqui.

---

## §5. O estudo fica BLOQUEADO. O que precede o desbloqueio

**Estimando primário permanece o INCONDICIONAL registrado** — ITT por
epoch/session-hour. Taxa de ativação, `churn` e composição dos deslocamentos ficam
**secundários mecanísticos**.

**`N` permanece o registrado.** Não é recalculado por esta emenda, e não pode ser
recalculado a partir de contagem de oportunidades.

⚠️ **A alocação registrada `117/39/39/39`** (um braço de controle e os três níveis da
banda) fica **suspensa junto com a banda**: não se aloca a níveis de uma escala
invalidada. Ela não é retratada nem substituída aqui — a alocação da escala
substituta é objeto da emenda que declarar a escala.

O desbloqueio exige um **protocolo de calibração prospectivo**, registrado antes de
observar mais dado, contendo no mínimo:

1. **Definição de oportunidade por replay do pipeline completo** — `interleaveFresh`,
   `pickDedup`, pinned, dedup, `LIMIT 400`, estrato `NULL` — não por censo de
   grupos num pool.
2. **Janela de calendário de calibração**, com início e fim declarados, e o estado
   de `brief_log` **descontaminado por `brief_id` enumerado**, com sensibilidade
   publicada nos dois estados.
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
8. **Toda medição do protocolo com `T_REF`, caminho de snapshot e janela fechada
   declarados**, e reprodução de âncora publicada antes de variar qualquer coisa.
   Esta última é a lição direta da remediação: sem âncora, uma reconstrução com
   definição diferente passa por correção.

⚠️ **`T_seed_assign` continua não declarado**, e agora por razão mais forte: não se
sorteia braço de uma escala invalidada.

---

## §6. Retratações novas

Continuam a numeração da v1.12, que fecha em 28.

| # | data | retratado | o que substitui |
|---|---|---|---|
| **29** | 26/08 | `Δ_cut` está "pendente de definição operacional e de medição" (v1.12 §1.5) — supõe definição a achar | não há definição a achar para o referente **registrado**. `Δ_cut` perde estatuto de parâmetro (§2) |
| **30** | 26/08 | `W_OUTCOME = w × Δ_cut` é *"a multiple of the measured salience spread at the brief cut"* (`PREREG-DRAFT.md:414`) | não há cut. Existe uma quantidade análoga — o gap **intragrupo** — mas ela **não foi registrada nem validada como estável**, logo não serve de unidade de escala registrada (§2) |
| **31** | 26/08 | a banda `{2,0 · 4,0 · 7,5}` está entre *"what does not move, and could not"* (`PREREG-DRAFT.md:44`) | invalidada **como escala calibrada**, sem substituição. Doses absolutas seguem existindo; recalibração prospectiva segue aberta (§3) |
| **32** | 26/08 | o chunk do estudo é nunca-servido, logo está sempre entre os 400 (`brief-outcome.ts:17-22`) | 0 nunca-servidos no pool; os 55 já foram servidos. A conclusão vale por outra razão: o pool tem 108 |
| **33** | 26/08 | a designação é defeito **aberto** (v1.12 §5) | fechada 26/08 20:28Z, com precedência verificável (§1) |
| **34** | 26/08 | linha de base de `churn` = 132/3.166 = 4,1693% | diluída por 954 decisões pré-gate com churn estruturalmente impossível. Base pós-gate, sondas excluídas: **132/2.226 = 5,9299%**, e a série **não é estacionária** (13,64% → 3,48%) (§2) |
| **35** | 26/08 | a oportunidade é "grupo da fronteira misto e maior que `freshSlots`", medida em 5/44 | incompleta: ignora `interleaveFresh`/`pickDedup`/pinned/dedup, o estrato `NULL`, e o fato de grupo puro-estudo entregar tratamento (§4.1) |
| **36** | 27/08 | *(2ª redação)* a hipótese de auto-extinção foi "testada e NÃO se sustenta" | **não testada**: toda a série reconstruída é anterior ao tratamento. Fica como item do protocolo prospectivo (§4.1) |
| **37** | 27/08 | *(2ª redação)* três sondas escreveram 15 linhas em `brief_log` | **cinco** sondas, **25** linhas — duas delas *dentro* da janela pós-regra, às 20:28:55–56 (§4.2) |
| **38** | 27/08 | *(2ª redação)* `measurement/descontamina.py` reconstrói o estado "excluindo as 15 linhas das sondas" | corta por **tempo**, removendo 3.735 linhas para excluir 25 — 148× a mais. Refeito por `brief_id` em `remedia-descontamina.py` (§4.2) |
| **39** | 27/08 | *(2ª redação)* `11/310 = 3,5484%` sob a regra nova, "praticamente idêntico" ao último dia, com "intervalos largamente sobrepostos" | janela era **aberta** por cima (359 linhas 12 h depois). Fechada: **11/350 = 3,1429%**. E sobreposição de IC **não é** equivalência — o teste correto está no §4.1-bis, e não estabelece nada |
| **40** | 27/08 | *(2ª redação)* a base é `132/2.212 = 5,9675%`, e está a "~11,8 desvios-padrão de zero" | **132/2.226 = 5,9299%**. O teste-z contra zero sai: zero é fronteira do espaço binomial (§2) |
| **41** | 27/08 | *(2ª redação)* os `111 deslocamentos` da v1.12 dão `8,05%` sobre 1.267 decisões | são **duas** quantidades: 102 decisões com churn = **8,0505%**; 111 deslocamentos somados = **8,7609%**. O rótulo estava trocado (§2) |
| **42** | 27/08 | *(2ª redação)* nenhum dos 38 pares tem gap negativo, apresentado como observação | verdadeiro **por construção** da ordenação (`salience DESC` dentro do empate) — não é achado (§2) |
| **45** | 27/08 | *(3ª redação)* o §4.1-bis chamava `11/350` de "taxa de ativação", o que lê como tratamento entregue | é taxa de **oportunidade contrafactual**: `modo: shadow` e `servido: controle` em **352 de 352**. Nenhum tratamento foi entregue na janela (§4.1-bis) |
| **44** | 27/08 | *(3ª redação)* "recibos **e saídas** das cinco vozes em `receipts/`" | só **uma** saída existe — as das quatro primeiras vozes nunca foram persistidas e são irrecuperáveis. O `receipts/README.md` do mesmo pacote já declarava o oposto: **dois arquivos do depósito se contradiziam** (§9, Anexo B) |
| **43** | 27/08 | *(2ª redação)* o código servindo está no commit `0087c918` | **esse objeto não existe** no repo — nem commit, nem ref, nem reflog. É `1da78560`; o merge `5174e0fa` reescreveu os hashes do lado da VPS. Conteúdo idêntico, nome pendurado. Blobs agora presos por `sha256` de bytes (cabeçalho e §9) |

---

## §7. O que a revisão adversarial matou, nomeado

Três decisões da primeira redação **caíram**, e duas correções propostas na terceira
rodada foram **retiradas por medição**. Ficam registradas porque uma emenda que
apaga o que a revisão derrubou não é auditável.

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

### 7.4 Duas correções da terceira rodada — RETIRADAS por medição

A terceira rodada me levou a propor duas correções aos números do §2 e do §3. **As
duas estavam erradas**, e o rascunho estava certo:

| eu ia trocar | por | por que estava errado |
|---|---|---|
| `16/27` vitórias de S1 em `w = 2,0` | `19/27` | o `19` vinha do rollback temporal de 148×, não da exclusão das sondas |
| `38 pares / 11 zeros` | `40 / 13` | mesma origem |

Correção feita corretamente (por `brief_id`), **nenhuma** estatística de gap muda.
A lição fica no §5 item 8: **reproduzir âncora publicada antes de variar qualquer
coisa** — sem isso eu teria reportado o número de uma definição diferente como
correção, degradando o documento em nome de consertá-lo.

---

## §8. Ordem de operações

0. ✅ **Blobs de código depositados** (commit `1da78560`) — era pré-requisito do
   depósito desta emenda (§9), e a segunda redação listava isto *depois* do passo 1,
   contradizendo o próprio §9. **Fechado em 27/08.**
1. Esta emenda depositada. Ela **invalida** a banda e **bloqueia** o estudo.
2. Protocolo de calibração prospectivo registrado (§5, os 8 itens).
3. Calibração executada dentro da janela de calendário declarada.
4. Escala de dose — se houver — declarada por emenda própria, com a alocação
   correspondente.
5. `T_seed_assign` e `ASSIGNMENT.json`.
6. `NOX_P2_OUTCOME=active`.
7. Epoch 1.

Nada de 3 a 7 começa antes de 0, 1 e 2.

---

## §9. Reprodutibilidade

✅ **Os scripts estão públicos.** Os **dezenove** que produziram os números desta
emenda estão em `measurement/`, com `README.md` mapeando cada um ao número que
sustenta. ⚠️ **Cinco não estavam versionados em lugar nenhum** —
`autoextincao.py`, `descontamina.py`, `serie.py`, `rebase.py` e `pos-regra.py`
nasceram como heredoc, viveram em `/var/tmp` na VPS, e produziram tabelas que
entraram neste documento. Três estão versionados **explicitamente como registro de
erro**, marcados no `README.md` e não para uso: `dose-response.mjs` (usou o DB vivo
como corpus e serve-state), `descontamina.py` (rollback temporal) e `pos-regra.py`
(janela aberta).

⚠️ **Auditáveis, não executáveis fora da VPS.** Os `.mjs` importam `../dist/…` e
esperam estar em `tools/nox-mem/scripts/` de uma instalação com `dist/` compilado.
Fora dali, um terceiro pode **ler** a derivação e não **rodá-la**. A lacuna está
declarada, não resolvida.

⚠️ **Determinismo é parâmetro, não default.** Três scripts usavam
`julianday('now')`, o que faz a população elegível mudar a cada execução, e o corpus
é resolvido pelo snapshot mais recente (§4.3). Os remediados exigem `T_REF` **e**
caminho de snapshot como argumentos.

⚠️ **Recibos das cinco vozes versionados em `receipts/` — mas só UMA saída.** Antes
desta passagem os recibos viviam em `$TMPDIR`, que o sistema apaga: requisito de
auditoria cujo artefato mora em diretório efêmero não é requisito. Ao copiá-los,
apareceu a lacuna maior — **as saídas das quatro primeiras vozes nunca foram
persistidas** (foram consumidas pelos agents que as chamaram) e hoje são
**irrecuperáveis**: zero arquivos de saída em `$TMPDIR`. Só a do Codex decisório
existe, versionada.

Consequência, e ela é desconfortável: para GLM, Codex-1ª-rodada, DeepSeek e Kimi, um
terceiro pode confirmar **que houve execução** com aquele `prompt_sha256` e
`output_sha256`, e **não pode ler o que a voz disse** nem conferir se o relato que eu
faço no Anexo B é fiel. As caracterizações do Anexo B sobre essas quatro são, portanto,
**inverificáveis por terceiro** — inclusive a afirmação de que o GLM revisou sem os
arquivos. Ficam declaradas como tal, não removidas: removê-las esconderia que a revisão
aconteceu.

⚠️ Uma redação anterior deste §9 e do cabeçalho afirmava "recibos **e saídas** das
cinco vozes", contradizendo o `receipts/README.md` do mesmo pacote, que declara o
oposto. Achado pela sexta leitura (Fable) — dois arquivos do mesmo depósito se
contradiziam, o que é pior que uma afirmação errada isolada. Retratação 44.

Varredura antes de publicar, porque o repositório é público: nenhum IP, hostname de
tailnet ou token; `gitleaks` sem achados. Os caminhos absolutos de servidor ficaram
como estavam — trocá-los por placeholders faria o script **parecer** reproduzível
sem ser.

✅ **Fechado: os blobs de código.** Os depositados na v1.12 eram da regra **anterior**
(designação por `w_min`). Os três arquivos do commit `1da78560` estão neste pacote —
`serving-brief.ts`, `serving-brief-outcome.ts` e `serving-p2-outcome-test.ts` — com
`sha256` por arquivo em `SERVING-CODE-MANIFEST.md`, conferidos **byte a byte** contra
`git show` no host que serve.

O arquivo de teste é novo no depósito e não é decoração: o §1 afirma que *"cinco
mutações do fonte TS foram confirmadas fazendo os testes falharem"*, e sem o teste
essa afirmação é infalsificável por quem lê.

⚠️ **Ao depositar, apareceu o defeito do pino.** O commit que as redações anteriores
citavam (`0087c918`) **não existe** — ver o bloco no cabeçalho. O conteúdo estava
certo e o nome, errado, por reescrita de histórico. Os blobs agora estão presos por
`sha256` de bytes, que é o pino que sobrevive a rebase.

⚠️ **E uma limitação que os scripts não resolvem.** Nenhum deles faz replay do
pipeline completo: não exercitam `interleaveFresh`, `pickDedup`, `pinned`, near-dup
nem o corte do `LIMIT 400` com pool acima de 400. Logo medem **ordenação**, não
**seleção** — a mesma lacuna do §4.1, e o item 1 do protocolo prospectivo. E nada
aqui é randomizado: todas as comparações são antes/depois, logo nenhuma identifica
efeito causal.

✅ **`claims_check.py` consertado, e um dos consertos era erro conceitual meu.** Ele
codificava como invariante que a taxa nova deve cair **dentro** do IC da antiga —
sobreposição de IC não é equivalência, e a asserção transformava um raciocínio
inválido em guarda. Substituída por: (a) recomputo de Wilson a partir de `k/n`;
(b) proibição de afirmar equivalência ou refutação sem TOST; (c) exigência de que a
comparação agregada esteja marcada como inutilizável; (d) exigência de que a
auto-extinção esteja declarada **não testada**.

⚠️ **Duas correções do guarda vieram do teste de mutação, não da revisão.** Na
primeira rodada, 4 de 15 falsificações passaram. Diagnosticadas, as quatro eram
**mutações ruins** — eu havia mutado só a primeira de 2–3 ocorrências. Mas o
diagnóstico expôs o buraco real: `ancorado` se satisfaz com **uma** ocorrência, logo
uma tabela que discorde da citação em bloco passa. Corrigido prendendo a **contagem**
de ocorrências dos quatro valores multi-citados, e conferindo que as duas cópias dos
27 gaps (num artefato de 26/08 e num de 27/08) são idênticas — só uma era lida, e a
outra podia derivar em silêncio. Estado final: **27 falsificações, 27 mordidas** — as quatro últimas cobrindo os blobs depositados, inclusive o defeito exato que eu cometi ao transferi-los: um `rstrip` normalizou o fim de arquivo e produziu 44.749 bytes onde o original tem 44.748. Um blob "depositado" que não era o arquivo, e invisível na prosa.

⚠️ **E um defeito de sentido oposto ao habitual.** A primeira versão da checagem de
frase acusou o próprio documento **três vezes** por ele *citar* o texto que retrata.
É o guarda-decoração invertido: em vez de nunca morder, mordia o inocente. Uma emenda
é obrigada a citar o que retrata; guarda que proíbe a citação proíbe a auditabilidade.
Resolvido isentando linha de tabela de retratação e ocorrência entre aspas — com o
custo declarado no próprio script de que isso abre uma via de evasão.

⚠️ **Pendência que fica:** `DELTA_CUT` e a banda seguem como literais dentro do
`claims_check.py`. É auto-referência — o guarda não pode falhar se o número mudar nos
dois lugares ao mesmo tempo.

---

## Anexo A — proveniência

Medições em duas passagens, ambas sobre snapshot de epoch como corpus e o `brief_log`
**vivo** como estado de serving:

| passagem | janela | corpus | `T_REF` |
|---|---|---|---|
| 2ª redação | 2026-08-26 20:35Z–23:30Z | `e20260826T060003Z.db` | 2026-08-26 20:35:00Z |
| remediação | 2026-08-27 até 12:00Z | `e20260826T060003Z.db` (âncoras) e `e20260827T060001Z.db` (estado corrente) | 2026-08-26 22:00:00Z e 2026-08-27 09:00:00Z |

Nenhum script escreve em `brief_log`: `buildBriefDiverse` não faz tracking — quem
faz é `handleBrief`, e é por isso que as sondas via `/api/brief` contaminaram e os
scripts não (§4.2). Detalhe em `MEASUREMENT-delta-cut-2026-08-26.md` e
`REMEDIATION-2026-08-27.md`; dados brutos em
`DELTA-CUT-MEASUREMENT-2026-08-26.json` e `REMEDIATION-2026-08-27.json`.

Fontes: `AMENDMENT-v1.12.md` §1.5, §4, §5.3 · `PREREG-DRAFT.md:44`, `:414`, `:535` ·
`REVIEWS-PREREG.md` F1, F2, F3, F5 · `DECISION-designacao-2026-08-25.md` ·
`DESIGNATION-SEED-2026-08-26.md` · `DESIGNATION-2026-08-26.json` ·
`p2-verdict-frame-2026-08-26.csv` · `src/api/brief-diversity.ts:130-140`, `:53-63` ·
`src/api/brief.ts:719-748`, `:1086` · `src/paper2/brief-outcome.ts:17-22` ·
`src/lib/epoch-serving.ts:103`.

## Anexo B — revisões adversariais desta emenda

**Seis revisões, cinco famílias de treino distintas, todas com recibo.** ⚠️ A **saída
integral** está versionada apenas para a voz decisória (Codex, 3ª rodada); as das
quatro primeiras não sobreviveram e são irrecuperáveis — ver §9. Para essas quatro, o
que este anexo relata é **inverificável por terceiro**.

### Sobre a primeira redação — as duas recomendaram não depositar

| voz | modelo | `exit` | bytes | `sha256` do output |
|---|---|---|---|---|
| GLM | `glm-5.3` | 0 | 9.535 | `fd0851001d0e285d…` |
| Codex | OpenAI gpt-5.6-sol | 0 | 1.472.973 | `efd9342789d6ed29…` |

⚠️ **O GLM revisou sem os arquivos** — declarou *"nenhum arquivo foi anexado"* e
trabalhou sobre o briefing. Isso invalida os achados dele sobre *o que a emenda
omite*, e preserva os **lógicos**: a circularidade da varredura, a leitura forte da
linha de base, a realimentação de `last_served`, e a natureza de medida-de-conjunto
do `churn`.

**Um achado do GLM foi REFUTADO por medição:** ele levantou que `churn` é
set-difference, logo reordenação interna ao conjunto selecionado seria invisível.
Testei comparando as **sequências** posição a posição — 28 casos, 4 doses × 7
agentes, incluindo `w = 100.000`: **0 casos** com ordem diferente. O ponto
arquitetural é correto e fica registrado como limitação da métrica; o canal
escondido não existe neste estado.

### Sobre a segunda redação

| voz | modelo | `exit` | bytes | `sha256` do output |
|---|---|---|---|---|
| DeepSeek | `deepseek-v4-pro` | 0 | 14.413 | `0197090d5365eae6…` |
| Kimi | Moonshot/K2 | 0 | 58.869 | `b456cf258005e0eb…` |
| Codex *(voz decisória)* | gpt-5.6-sol, v0.149.1 | ⚠️ ver abaixo | 358.332 → **358.342** | `5ad86e369c900c9e…` → **`ddbeaff82c57c8a5…`** |

⚠️ **Dois hashes, e o depositado é o segundo.** O primeiro par (358.332 B,
`5ad86e36…`) é a saída **como emitida**; o segundo (358.342 B, `ddbeaff8…`) é o
**arquivo em `receipts/`**, depois de redigir 2 ocorrências do IP tailnet da VPS e o
hostname do laptop. Conferir a tabela contra o depósito dá mismatch se só um for
citado — apontado pela sexta leitura. Os dois estão no recibo `-REAL`.

DeepSeek e Kimi convergiram, independentemente, no mesmo bloqueador central: o §3 e
a retratação 30 se anulavam. O Codex arbitrou, e apontou que a reformulação que eu
ia adotar ("não congelável") era **forte demais** — daí a redação do §2, que
distingue *referente registrado* de *quantidade existente porém não validada*.

⚠️ **O recibo do Codex desta rodada é irregular, e fica declarado.** A invocação via
`scripts/adversary-run.sh` **falhou** (`exit: 124`, timeout de 1.800 s,
`output_bytes: 39`). O resultado substantivo veio de uma invocação **direta** do
binário, fora do wrapper, logo sem recibo do contrato. O recibo em `receipts/` foi
**cunhado a partir do artefato que existe** — a saída de 358.332 bytes — com
proveniência conferível no próprio cabeçalho (`OpenAI Codex v0.149.1`,
`model: gpt-5.6-sol`, `workdir`, `session_id`). O agent que conduziu a rodada
reportou `exit: 0`, valor que ele havia levantado de um recibo de **outra voz**
citado dentro do texto da saída.

⚠️ **Um achado do Kimi estava errado no fato e certo no risco:** afirmou que o recibo
do GLM não existia, tendo checado só `.remember/` da raiz. Existia, em `$TMPDIR`. Mas
"não achei onde olhei ⇒ não existe" é a própria armadilha que este anexo documenta —
e o diretório efêmero é o que a tornava plausível. Daí `receipts/` existir.

### O que só a remediação achou

Nenhuma das cinco vozes achou os dois defeitos de maior consequência factual: que
eram **cinco** sondas e não três (duas delas dentro da janela medida), e que o
descasamento entre reconstruções era **de definição** e não de deriva. Revisão
adversarial e verificação mecânica pegam classes **disjuntas** de defeito.
