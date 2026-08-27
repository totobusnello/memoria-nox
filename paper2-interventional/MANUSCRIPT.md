# Capacity, not relevance: what a production agent-memory system actually surfaces

> 🟡 **ESQUELETO, 2026-08-27.** Primeira versão do manuscrito do Paper 2, escrita
> depois do reframe. **Regra deste arquivo:** onde há número, ele vem de artefato
> travado por `--assert-json` e o comando de reprodução está citado. Onde não há, está
> escrito **`[FALTA]`** com o que exatamente falta — nunca prosa de enchimento que
> pareça pronta. Um esqueleto que finge estar escrito é pior que um vazio.
>
> Fontes: `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` ·
> `REMEDIATION-2026-08-27.md` · `DEVIATIONS-FOR-PAPER.md` ·
> `PROTOCOL-CALIBRATION-2026-08-27.md`.

---

## Abstract

**[FALTA — escrever por último.]** O que ele tem de dizer, na ordem, e nada além:

1. sistemas de memória para agentes são avaliados por qualidade de *retrieval* sobre
   queries; ninguém mede o que o agente **de fato recebe** em produção;
2. medimos as duas superfícies de exposição de um sistema em produção por 12 semanas:
   **83,78%** de 67.187 chunks nunca foram expostos por nenhuma delas;
3. a exposição é governada pelo **tamanho da coleção**, não pela relevância que o
   próprio sistema atribui: `r = −0,728` entre `log₁₀(tamanho)` e `% exposto`, e
   nenhuma sobreposição entre tipos grandes (10,7–27,0%) e pequenos (32,5–100%);
4. o mecanismo é dedutível do código — um comparador **lexicográfico** deixa o score
   como coordenada **subordinada**, e só os slots de cobertura (`freshSlots = 2` de 10)
   o consultam — e isso prediz um **teto** para qualquer bônus aditivo no score;
5. testamos a predição com uma intervenção de dose crescente em produção, com replay
   fiel ao pipeline real em **350 de 350** briefs: resposta monótona, teto de
   **4,86%** dos briefs, saturação em `w ∈ (4,0; 4,4]`;
6. e reportamos o catálogo de defeitos de **instrumento** que a medição exigiu, porque
   sem ele nenhum dos números acima seria verificável.

⚠️ O abstract **não** pode afirmar efeito sobre o comportamento do agente. Não há
desfecho a jusante instrumentado (§5.4).

## 1. Introdução

**[FALTA — parágrafos 1–3.]** Esqueleto do argumento:

- **O gap.** O survey canônico da área (TMLR 2602.06052v4) mapeia arquiteturas e
  benchmarks de memória para agentes. Benchmarks medem nDCG/recall sobre conjuntos de
  queries. Nenhum mede a **superfície de entrega**: quantos itens distintos um agente
  em produção realmente vê, e quais. E o survey tem **zero** ocorrências de
  "pre-registration" — a área não tem literatura de metodologia experimental para
  intervenções em memória viva. **[FALTA: confirmar a contagem de ocorrências contra o
  PDF v4 antes de submeter; hoje o número vem de nota de leitura, não de recomputo.]**
- **Por que a pergunta importa.** Se a superfície tem capacidade fixa e pequena,
  então melhorar *ranking* não melhora *exposição* — e a maior parte do trabalho de
  engenharia de memória (embeddings melhores, reranking, expansão de query) está
  otimizando a coordenada errada. Essa é uma alegação verificável e é o que o paper
  testa.
- **Contribuições.** (i) a primeira medição de superfície de exposição de um sistema de
  memória de agente em produção; (ii) o achado capacidade-sobre-relevância, com o teste
  que descarta a explicação por curadoria; (iii) uma predição dedutiva de teto para
  intervenções aditivas, testada com dose-resposta e replay fiel; (iv) o **diagnóstico
  executável** (`measurement/`), para que a medição seja reproduzível em outro sistema;
  (v) um catálogo de defeitos de instrumento que a área ainda não documentou.

## 2. Sistema sob medição

**[FALTA — descrição de 3 parágrafos + 1 figura de arquitetura.]** O que precisa estar
lá, e nada mais que isso:

- corpus SQLite com FTS5 + vetores; **67.187** chunks no instante da medição;
- **duas** superfícies de exposição, e só duas: o **brief proativo** (`/api/brief`,
  consumido no início de cada sessão de agente, 10 itens) e a **busca** sob demanda;
- o brief compõe 10 slots: `n − freshSlots` pelo pool principal ordenado por
  `salience`, e até `freshSlots` reservados a um pool de *cobertura* ordenado por
  um comparador **lexicográfico** `(last_served ASC, salience DESC)`. Em produção
  `freshSlots = 2` — default de configuração sem override, e **teto** dos slots
  preenchidos, não cota (§5.3);
- 6 agentes, ~670 briefs/dia.

⚠️ Declarar explicitamente que é **um** sistema. A generalização do §7 é **dedutiva**
(da álgebra do comparador), não empírica.

## 3. Método

### 3.1 As duas superfícies, e por que a contagem é exata

| superfície | instrumento | cobertura |
|---|---|---|
| brief | `brief_log` | vida inteira do endpoint (subiu 2026-06-04) e **sem poda** — a única `DELETE FROM brief_log` do repositório está num teste |
| busca | `chunks.access_count`, incrementado no caminho de resultados da busca | desde sempre; o brief **nunca** escreve nessa coluna |

Como as duas cobrem desde o início, a união é contagem **exata** de
já-exposto-alguma-vez, e o complemento também. Nenhum dos dois é *bound*.

### 3.2 Disciplina de medição

Cinco regras, e cada uma existe porque a violação já produziu número errado neste
trabalho (§6):

1. **janela fechada nos dois extremos**, com `sha256` do recorte;
2. **derivação em script**, nunca em prosa: prosa que afirma resultado calculado é
   cache sem invalidação. Todo número do paper sai de `measurement/*.py|mjs` e é
   travado por `--assert-json`;
3. **reproduzir âncora publicada antes de variar qualquer coisa**;
4. **exato vs. limite** declarado por número, com a direção que o limite protege;
5. **replay pelo código real**, importado — nunca reimplementado.

### 3.3 Fidelidade do replay

A evidência interventiva depende de um replay do pipeline de serving. Ele importa a
função de composição do binário de produção e é validado contra o que a produção
**registrou**, brief a brief:

| corte de serve-state | briefs | controle bate | churn bate | churn produção | churn replay | inventado | perdido |
|---|---|---|---|---|---|---|---|
| **por ordem de inserção** | 350 | **350** | **350** | 12 | **12** | **0** | **0** |
| por timestamp (estrito) | 350 | — | 346 | 12 | 14 | 3 | 1 |

Conferir a composição do **braço de controle** é o que impede fidelidade por
coincidência: sem essa coluna, um brief com controle e tratado ambos errados poderia
bater no desfecho.

`replay-resumo.py --campo out/c-350-v3.json --campo-estrito out/c-350.json`

## 4. Resultados

### 4.1 Exposição: 83,78% do corpus nunca chegou ao agente

| | |
|---|---|
| corpus | **67.187** |
| exposto no brief | 1.787 |
| exposto na busca | 9.755 |
| união | 11.051 |
| **nunca exposto por nenhuma** | **56.288 = 83,78%** |
| desses, passam o próprio piso de relevância do sistema | **10.008** |

*(152 chunks servidos no brief foram depois apagados do corpus — daí
`corpus − união ≠ nunca-exposto`.)*

⚠️ **E a leitura tentadora é falsa.** Dos 10.008, **8.928** são fragmentos de sessão de
205 caracteres em média. O achado não é "dez mil lições invisíveis".

### 4.2 O achado: capacidade, não relevância

| tipo | exposto/total | % |
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

Duas explicações competem: **curadoria** (tipos mais curados são mais expostos) e
**tamanho** (coleções pequenas cabem na superfície). O teste separa:

- `log₁₀(tamanho)` × `% exposto`: **Pearson r = −0,728**, **Spearman ρ = −0,714**,
  **r² = 0,530**;
- **sem sobreposição**: 5 tipos com n ≥ 1.000 ficam em **10,7–27,0%**; 8 tipos com
  n < 100, em **32,5–100%**;
- dentro dos grandes a ordem é quase monótona **em tamanho**
  (1.046→27,0% · 3.231→24,7% · 15.308→21,7% · 14.456→19,5% · 32.920→10,7%).

**`lesson` está em 100% porque tem 53 linhas.** A relevância atribuída pelo sistema não
prediz exposição; o tamanho da coleção prediz.

**Figura 1** — `measurement/out/fig1-capacidade.svg`: dispersão `log₁₀(tamanho)` ×
`% exposto`, um ponto por tipo com rótulo, reta de regressão e as duas faixas
(n ≥ 1.000 · n < 100) sombreadas, porque **a ausência de sobreposição é o achado** e
precisa ser vista, não afirmada. Gerada por `fig1-capacidade.py --dados
out/superficie.json` — derivada do artefato travado, então muda se o dado mudar;
figura desenhada à mão seria prosa afirmando resultado calculado.

### 4.3 A superfície do brief é um carrossel de 201 itens

Janela fechada `[2026-08-20 , 2026-08-27)`:

| | |
|---|---|
| slots servidos | **46.295** em **4.632** briefs |
| chunks distintos | **201** |
| presentes em **100%** dos briefs | **3** |
| top-10 | **47,16%** dos slots · top-20 **61,46%** |

**[FALTA — Figura 2:]** curva de concentração (rank × share cumulativo) dos chunks
servidos, com marca nos 3 constantes e no top-10.

### 4.4 A predição dedutiva, e o teste

O comparador de cobertura é **lexicográfico**: quando `last_served` difere, `salience`
**nunca é consultada**. Um bônus aditivo em `salience` só decide **dentro** de estratos
de `last_served` idêntico. Logo qualquer intervenção desse tipo tem **teto**, e o teto é
a fração de briefs em que a decisão cai num empate de `last_served`.

Teste em produção, dose crescente, 350 estados reais, replay fiel:

| `w` | 0 | 0,5 | 1 | **2** (servido) | 4 | 7,5 | 15 | 100 | 100.000 |
|---|---|---|---|---|---|---|---|---|---|
| estados que mudam | **0** | 5 | 8 | **11** | 15 | 17 | 17 | 17 | **17** |
| eventos de deslocamento | 0 | 5 | 8 | 12 | 18 | 20 | 20 | 20 | 20 |

- **controle negativo passa:** `w = 0` dá 0 em 350/350;
- **monótono em cada um dos 350 estados**, não só no agregado;
- **teto 17/350 = 4,86%**;
- **saturação em `w ∈ (4,0 ; 4,4]`** — grid fino de 23 doses sobre os 17 estados que
  se movem: `w_min` mínimo **0,02**, mediana **1,7**, máximo **4,4** (espalhamento
  **220×**), 0 estados não monótonos, 0 sem limiar no grid;
- a dose servida reproduz a taxa publicada: `w = 2` dá **11/350 = 3,1429%**.

**[FALTA — Figura 3:]** dose-resposta em eixo `w` logarítmico, com a banda registrada
`{2,0 · 4,0 · 7,5}` marcada e a região de saturação sombreada.

⚠️ **A grandeza que governa é distância, não passo.** O maior `w_min` (4,4) vale bônus
`0,0946`, **1,79×** o maior gap entre candidatos adjacentes no pool (`0,05272`). Bônus
maior que qualquer passo entre vizinhos e ainda insuficiente ⇒ o item atravessa
**várias** posições até alcançar os 2 slots.

### 4.5 O que este desenho **não** identifica

Seção obrigatória, e ela vem **antes** da discussão de propósito:

- **nenhum efeito sobre o agente.** Não há desfecho a jusante instrumentado: três
  tabelas de qualidade voltada ao agente com **0 linhas**, e a telemetria de busca
  registra a **sonda de saúde do cron** — em janela fechada de 7 dias, **325 de 343
  linhas (94,8%)** caem nos dois minutos por hora em que o cron dispara, sobrando
  **2,6 linha/dia** atribuível a agente;
- **nada randomizado.** Toda comparação temporal é antes/depois. A comparação contra o
  agregado pós-gate mede **composição de dias** (p = 0,0326 e inutilizável); a
  comparação adjacente defensável é subpotente (~7%);
- **auto-extinção não testada** — a série é toda anterior ao tratamento;
- **carry-over não modelado.** O estado de cobertura não é congelado e realimenta:
  tratar em `T` altera a estrutura de estratos em `T+1`.

## 5. Mecanismo

Esta seção é dedutiva. O que ela prova vale para qualquer ranker com a mesma
forma, e é a razão pela qual um estudo em `n = 1` sistema ainda diz algo geral
(§7). Toda a estrutura vem de sete linhas de código, citadas em vez de
parafraseadas.

### 5.1 O objeto

Seja `P` o conjunto de candidatos elegíveis (o *pool*). Cada `c ∈ P` tem:

- `ℓ(c) ∈ ℝ ∪ {−∞}` — instante do último serve, com `−∞` para nunca-servido;
- `s(c) ∈ ℝ` — a `salience`.

O comparador de produção, verbatim (`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;      // ASC: menos-recentemente-servido primeiro
return bSalience - aSalience;       // tie: maior salience
```

Isto é exatamente a ordem lexicográfica `≺` sobre o par `(ℓ(c), −s(c))`:

> `c ≺ c′` ⟺ `ℓ(c) < ℓ(c′)`, ou `ℓ(c) = ℓ(c′)` e `s(c) > s(c′)`.

A intervenção é uma função `b : P → ℝ₊`, nula fora do conjunto designado `D`. Ela
entra em um único ponto (`src/api/brief.ts:612-614`):

```ts
const eff = (c) => c.salience + (boosts?.get(c.row.id) ?? 0);
ranked.sort((a, b) => coverageCompare(a.lastServedMs, eff(a), b.lastServedMs, eff(b)));
```

Ou seja: `b` desloca **apenas** o segundo argumento de `coverageCompare`. Escreva
`≺_b` para a ordem resultante.

### 5.2 Proposição 1 — invariância entre estratos

*Para quaisquer `c, c′` com `ℓ(c) ≠ ℓ(c′)`, a ordem relativa de `c` e `c′` é a
mesma sob `≺` e sob `≺_b`, para toda `b`.*

**Prova.** Se `ℓ(c) ≠ ℓ(c′)`, o comparador retorna na primeira linha, cujo valor
`al − bl` não depende de nenhum dos argumentos de `salience`. Logo `b` não pode
alterá-lo. ∎

Defina `c ∼ c′` ⟺ `ℓ(c) = ℓ(c′)`. As classes de equivalência são os **estratos**.
Note que todos os nunca-servidos caem num único estrato (`ℓ = −∞`).

**Corolário 1 (a ordem é uma concatenação).** A sequência ordenada sob `≺_b` é a
concatenação, sobre os estratos em ordem crescente de `ℓ`, de cada estrato
ordenado internamente por `−s_b`. Em consequência, **`b` permuta dentro de
estratos e nunca move um item de um estrato para outro.**

### 5.3 Corolário 2 — o teto, e onde ele vive

A superfície tem capacidade fixa: dos 10 slots do brief, o pool de cobertura
alimenta no máximo `K = freshSlots`. Em produção `K = 2`, e a procedência desse
número precisa ser dita com cuidado, porque ele **não** é medido no log:

- é o default `DIVERSITY_DEFAULTS.freshSlots = 2`, sobrescrevível por
  `NOX_BRIEF_DIV_FRESH_SLOTS`, e **não há override** nem na unit systemd nem no
  `.env` — verificado;
- é um **teto**, não uma cota: o laço de preenchimento sai em
  `if (freshGot >= freshSlots) break`, então um brief pode ter menos;
- e `brief_log` **não tem coluna** que marque a origem do slot, logo a divisão
  "8 principais + 2 de cobertura" não é observável no registro. É configuração
  mais código, e está declarada como tal.

O conjunto servido pelo pool de cobertura é o prefixo de tamanho `≤ K` de `≺_b`.

*O conjunto servido muda sob `b` somente se existir um estrato que contenha ao
mesmo tempo um item selecionado e um não-selecionado.*

**Prova.** Por Corolário 1, `b` só permuta dentro de estratos. Um estrato
inteiramente contido no prefixo tem seus itens permutados entre posições todas
selecionadas ⇒ o **conjunto** não muda. Um estrato inteiramente fora do prefixo,
idem. Resta o estrato que **atravessa** o corte, e por Corolário 1 há no máximo
um. ∎

Três consequências, e as três são mensuráveis em vez de argumentáveis:

1. o teto de decisões alteráveis é a fração de estados em que o corte cai
   **estritamente dentro** de um estrato **e** um designado está do lado
   não-selecionado. Medido em §4.4: **17/350 = 4,86%** — e em §5.6 esses mesmos 17
   estados são exatamente aqueles em que há troca, com **todas** as 20 entradas
   ocorrendo dentro do estrato de quem saiu;
2. **se `ℓ` fosse injetiva, `b` não teria efeito nenhum.** Todo estrato seria
   unitário, nada atravessaria o corte, e a intervenção seria identicamente
   inerte. Todo o espaço de manobra da intervenção vem de **empates na
   coordenada dominante** — no nox-mem, do estrato dos nunca-servidos e da
   resolução de segundo de `served_at`;
3. o teto **não é um parâmetro do desenho**: é uma propriedade da distribuição de
   `ℓ` no pool, que o próprio tráfego produz.

### 5.4 Corolário 3 — saturação, e por que passo não é a grandeza

Dentro do estrato que atravessa o corte, a ordem é por `−s_b`. Seja `c_K` o item
selecionado de menor posição nesse estrato (o que está imediatamente acima do
corte). Um designado `d` não-selecionado entra no conjunto servido se e somente se

```
b(d)  >  s(c_K) − s(d)
```

O lado direito é uma **distância até o corte**, não o passo até o vizinho
imediato de `d`. Como o pool é finito e há finitos estados, existe

```
b* = max sobre os estados  ( s(c_K) − s(d) )   <  ∞
```

e para toda `b > b*` nenhuma ordem mais muda: **a saturação é uma identidade, não
um limiar escolhido.** Medida: `b*` corresponde a `w ∈ (4,0 ; 4,4]`, com
`w_min` variando **220×** entre estados (0,02 a 4,4).

⚠️ **É aqui que um gatilho de monitoramento erra.** O item 7 do registro vigiava
`max_j (s(c_j) − s(c_{j+1}))`, o maior passo entre **adjacentes**. Vale sempre
`passo ≤ distância`, e medido: o maior `w_min` (4,4) vale bônus 0,0946, **1,79×**
o maior passo adjacente do pool (0,05272). Um gatilho calibrado no passo fica
**verde enquanto o canal satura** — foi o que forçou a reimplementação do item 7
como a identidade `churn(w_servido) = churn(w_absurdo)`.

### 5.5 A consequência de desenho

Uma superfície de capacidade fixa ordenada lexicograficamente é **imune, por
construção, a intervenções na coordenada subordinada**. Para mover o que o agente
vê há três alavancas, e o score não é uma delas:

| alavanca | efeito |
|---|---|
| a coordenada **dominante** (`ℓ`: política de rotação) | reordena entre estratos — sem teto |
| a **capacidade** `K` | muda quantos estratos atravessam o corte |
| a **elegibilidade** (quem entra em `P`) | muda o objeto, não a ordem |
| ~~o score subordinado~~ | limitado por Corolário 2, saturando em `b*` |

E é a mesma conclusão da §3 por outro caminho: a exposição é governada por
capacidade, não por relevância. A §3 mede isso na população de chunks; a §5
prova por que nenhum ajuste de relevância poderia mudá-lo.

### 5.6 O teste que esta derivação tem de passar

A derivação é falsificável, e vale contar como a primeira tentativa de testá-la
**falhou por defeito do teste** — porque o episódio pertence ao §6 e é a razão de
o teste atual ter a forma que tem.

**Tentativa 1, inválida.** Classificar os 350 estados pela posição do designado no
pool ordenado: fora do pool / já selecionado / em estrato diferente do corte /
no estrato do corte. A predição era que a última classe tivesse exatamente as 17
do teto. Resultado: **25**, e — decisivo — apenas **1 das 17** caía nela.
`interleaveFresh` e `FRESH_CANDIDATE_POOL` **não são exportados** pelo binário de
produção, então aquele pool era uma **reconstrução**, e as **24** violações do
pressuposto de prefixo eram o sintoma. Testar uma derivação contra um pipeline
reconstruído não testa a derivação: testa a reconstrução.

**Teste 2, sobre grandezas registradas.** A Proposição 1 tem uma consequência que
não exige montar pool nenhum:

> Em todo estado em que o conjunto servido muda, cada id que **entra** tem de
> compartilhar `last_served` com algum id que **sai**.

Se um id entra vindo de um estrato em que ninguém saiu, o bônus atravessou
estrato e a Proposição 1 é falsa. As três grandezas — `would_enter`,
`would_leave` e `last_served` no serve-state podado — são **registradas** pela
produção e pelo replay validado 350/350, não derivadas.

`replay-oportunidade.mjs --modo porque --corte rowid --so-ts-file ts-350.txt`
aborta se houver uma única entrada sem parceiro.

**Resultado.**

| | |
|---|---|
| estados replayados | **350** (erros: 0) |
| estados em que o conjunto servido muda | **17** |
| ids que entram, somados | **20** |
| **entradas sem saída no mesmo estrato** | **0** |
| Proposição 1 | **sobrevive** |

Os `17` e os `20` **reproduzem exatamente** o artefato de dose independente
(`mexeu = 17`, `churn_total = 20` em `w = 100.000`), e essa reprodução é o que
torna o zero interpretável: garante que as duas rodadas falam da mesma população.

⚠️ **E o zero foi verificado contra a possibilidade de ser um teste que não
olha.** Mutando a função de estrato para dar a cada id um estrato próprio — sob o
que nenhuma entrada teria parceiro — o modo reporta **20 violações em 17
estados** e aborta. A asserção morde no máximo possível, logo o `0` da tabela é
resultado, não silêncio de instrumento.

**Procedência da rodada.** Corpus = snapshot de epoch
`e20260826T060003Z.db`, exclusão de sondas = nenhuma, corte por ordem de
inserção, designação com `sha256` conferido — idênticos ao artefato de dose. ⚠️ A
primeira execução deste teste divergiu (13 estados, não 17) porque eu havia
trocado **duas** coisas de uma vez, corpus vivo e exclusão de 6 sondas; o diff do
bloco `procedencia` dos dois artefatos mostrou as duas. **Diff de procedência
antes de comparar número** é regra, não zelo.

## 6. Defeitos de instrumento — e reportá-los é parte da contribuição

O paper perde a contribuição declarada se omitir isto, porque a contribuição **é o
método**. Catálogo, com o custo medido de cada um:

| defeito | consequência medida |
|---|---|
| relógio do banco dentro do filtro de elegibilidade, apesar de a função receber o instante por argumento | o brief não é função pura de (corpus, estado, `nowMs`); replay ingênuo mede outra população |
| `served_at` com resolução de **segundo** e 6 agentes disparando em 1–2 s | **46,9%** dos briefs dividem o segundo; nenhum corte temporal reproduz o estado. Sob corte estrito o replay **inventa** 3 e **perde** 1 evento: desfecho sai **14 em vez de 12** (+16,7%) |
| o ordenador **descarta** a chave que ordenou o pool | agrupar por ela dá **um** grupo, em silêncio |
| controle positivo rodado sobre pipeline **reimplementado** | produziu "dose absurda ⇒ efeito zero", que virou retratação central. O pipeline real dá **20** eventos |
| grid grosso | saturação *pareceu* cair exatamente no topo da banda registrada; com 23 doses está em `(4,0 ; 4,4]` |
| gatilho de monitoramento calibrado sobre gap **adjacente** | vigia grandeza que não limita o mecanismo: fica **verde enquanto satura** |
| telemetria de busca por chunk **apagada** por commit de fim de dia (`7fdaab4f`, 2026-05-19): `INSERT` de 23 colunas trocado por um de 7, deixando **13 colunas sem escritor** e **sem `CUT`** no título — a convenção deste projeto para retirada deliberada | comparação entre superfícies **dentro de janela** é impossível, e passou **3,3 meses** sem ninguém notar. Além disso um campo sem escritor (`requesting_agent`) foi por mim usado como se fosse assinatura de origem: nulo para todo mundo não distingue nada |
| comparação de contagem **filtrada** com **não-filtrada** | inverteu o sinal de uma conclusão: 617×245 cumulativo vira 245×≥151 na janela comum |
| série viva citada como instantâneo | um `n` mudou em minutos e a asserção pegou |
| **teste de uma derivação sobre pool RECONSTRUÍDO** (`interleaveFresh` não é exportado) | classificou 25 estados como alteráveis contra 17 reais, e só **1 das 17** caía na classe; 24 violações do pressuposto de prefixo eram o sintoma. O teste válido usa só grandezas **registradas** (§5.6) |
| valor **digitado** dentro do próprio instrumento de verificação | `w_min` máximo ficou fixado em `7,5` no script e envelheceu para falso quando o grid fino deu `4,4`; agora é argumento obrigatório vindo do artefato de dose |

**[FALTA]** decidir se este catálogo é seção do paper ou **apêndice + paper de métodos
separado**. Recomendação: seção curta aqui (as 4 linhas que afetam os números
reportados) e o catálogo integral em apêndice.

## 7. Ameaças à validade

- ⚠️ **`n = 1` sistema.** É a ameaça principal e não tem mitigação dentro deste paper.
  A generalização do mecanismo é **dedutiva** (§5), não empírica: vale para qualquer
  ranker com ordem lexicográfica e bônus na coordenada subordinada, e **se** outros
  sistemas têm essa estrutura é questão aberta. Mitigação parcial: publicar o
  diagnóstico executável para que terceiros meçam o próprio sistema;
- tipos pequenos (`decision` n=11, `person` n=14, `feedback` n=17) não sustentam
  leitura individual — entram só no teste de correlação;
- `access_count` é "exposto alguma vez", sem histórico por evento;
- a diversidade de cobertura por dia tem **quebra de regime** em 21–22/08, ainda sem
  explicação;
- a intervenção correu em modo **shadow**: o contrafactual é observado, mas nada foi
  servido tratado. Toda taxa é **taxa de oportunidade**, não efeito.

## 8. Trabalho relacionado

**[FALTA — ~1 página.]** Eixos:
- benchmarks de memória para agentes e o que eles medem (e não medem);
- literatura de *exposure/position bias* em recomendação — é onde existe o vocabulário
  de "capacidade da superfície", e a ponte ainda não foi feita para memória de agente;
- pré-registro em CS de sistemas: o gap que o survey evidencia.

## 9. Discussão

**[FALTA]** Duas afirmações, e nenhuma além:
1. otimizar ranking não melhora exposição quando a capacidade é o gargalo — e
   capacidade é medível com o diagnóstico publicado;
2. intervenções em memória viva precisam declarar a **coordenada** em que agem, porque
   um bônus na coordenada subordinada de um comparador lexicográfico tem teto
   analítico.

## Apêndice A — Desvios do pré-registro

Íntegro em `DEVIATIONS-FOR-PAPER.md`. O pré-registro (OSF `yf7d2`, Zenodo
`10.5281/zenodo.22110203`) afirma quatro coisas que a medição contradiz, **duas delas
em direção que subestima o próprio desenho**, e o apêndice tem de listar as quatro com
a mesma proeminência.

## Apêndice B — Cadeia da designação

Sorteio com seed declarada: rodada drand quicknet **31657512** (emissão 20:25:00Z),
declaração pushada **20:07:24Z** — **1.056 s** de precedência, com a rodada devolvendo
HTTP 425 no momento da escrita. Um revisor independente rederivou o conjunto designado
usando **apenas** o beacon público e o CSV depositado.

## Apêndice C — Painel de adjudicação

`κ = 0,874`, `α = 0,852`. Adjudicações: **S0 = 225 · S1 = 33 · S2 = 22**, e
**zero** em S3/S4.

⚠️ **Duas fragilidades a declarar, não a esconder:** (i) o estrato **S2 repousa numa
única família** do painel (72,2% do share) — o paper deve reportar S1 e S2 separados e
tratar S2 como exploratório, ou remover S2; (ii) a regra de parada pré-registrada usa
incidentes ≥ S3, cujo baseline é **zero**, o que a degenera para "≥ 1 evento derruba".
Isso é lição de desenho e entra como tal.

## Apêndice D — Artefatos

Tudo em `measurement/`, com `--assert-json` travando cada número citado:

| o quê | script | artefato |
|---|---|---|
| superfície de exposição | `superficie-de-exposicao.py` | `out/superficie.json` |
| replay + dose + limiar + gaps | `replay-oportunidade.mjs` · `replay-resumo.py` | `out/c-350-v3.json` · `out/dose-350-v3.json` · `out/limiar-17.json` · `out/gaps.json` |
| exposição ao defeito de resolução | `irmaos-no-segundo.py` | — |
| gatilhos de monitoramento | `gatilho-saturacao.sh` · `gatilho-composicao.mjs` | `implantacao/` |

**[FALTA]** DOI de um depósito que contenha **este** manuscrito e os artefatos na
versão citada. Hoje o último depósito é a v1.12, anterior a tudo isto.

---

## O que falta, em ordem de quem bloqueia quem

1. **Figura 1** (tamanho × exposição) — é a figura do paper e o dado está pronto;
2. **§5, derivação formal** — pura escrita, nada a medir;
3. **§1 e §8** — introdução e trabalho relacionado; exige leitura, não medição;
4. **recomputar a contagem de "pre-registration" no survey** antes de afirmá-la;
5. **explicar a quebra de regime de 21–22/08** na diversidade de cobertura;
6. **decidir S2**: reportar separado como exploratório, ou remover;
7. **Abstract**, por último;
8. **depósito** com o manuscrito + artefatos, e aí a emenda agrupada faz sentido: um
   registro só, declarando os desvios **e** o resultado novo.
