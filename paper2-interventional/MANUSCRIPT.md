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

Sistemas de memória para agentes são avaliados pela qualidade da recuperação sobre
conjuntos de queries. Ninguém mede o que o agente **de fato recebe** em produção — e a
recuperação é condicional a uma query ter sido feita, de modo que o item que nenhuma
query alcança tem nDCG indefinido, não baixo. Instrumentamos, por 12 semanas, as duas
superfícies pelas quais um sistema de memória em operação entrega conteúdo a uma frota
de 6 agentes: um brief proativo de 10 itens e a busca sob demanda. **83,78% de 67.187
chunks nunca foram expostos por nenhuma das duas.**

O que decide a exposição não é a relevância que o próprio sistema atribui, e sim o
**tamanho da coleção** a que o item pertence: `r = −0,728` entre `log₁₀(tamanho)` e
`% exposto`, sem uma única sobreposição entre tipos grandes (10,7–27,0%) e pequenos
(32,5–100%). A renovação da superfície tampouco é governada pelo ranker: o canal de
cobertura é alimentado por **lotes de ingestão** com janela de 7 dias e, entre lotes,
serve exatamente o mesmo conjunto por dias seguidos.

O mecanismo é **dedutível do código**, não inferido dos dados. O canal de cobertura
ordena por um comparador **lexicográfico** `(last_served ASC, salience DESC)`: o score é
a coordenada **subordinada** e só decide dentro de empates da dominante. Isso prediz um
**teto** — não uma resposta proporcional — para qualquer bônus aditivo no score.
Testamos a predição com dose crescente em produção e replay fiel ao pipeline real em
**350 de 350** briefs: a resposta é monótona em cada estado, satura em `w ∈ (4,0; 4,4]`
e o teto é **4,86%** dos briefs.

Reportamos também o catálogo dos **defeitos de instrumento** que a medição exigiu, dos
quais sete mudaram um número aqui reportado. Cada um passou por verificação e
sobreviveu, porque o verificador compartilhava a premissa errada do que verificava —
e quatro foram achados porque um número **bateu bem demais**.

⚠️ **Não afirmamos efeito sobre o comportamento do agente**: não há desfecho a jusante
instrumentado (§5.4). O objeto medido é a superfície, não a consequência dela. E é
**um** sistema: a generalização do mecanismo é dedutiva, válida para qualquer ranker com
ordem lexicográfica e bônus na coordenada subordinada, e quantos sistemas têm essa forma
é pergunta que o diagnóstico executável publicado permite responder um por vez.

## 1. Introdução

Um sistema de memória para agentes é julgado, hoje, pela qualidade da recuperação:
dado um conjunto de queries, quão bem ele ordena o que é relevante. É a pergunta que os
benchmarks respondem e é a pergunta que a engenharia otimiza — embeddings melhores,
reranking, expansão de query. Ela pressupõe, sem dizer, que o que o agente recebe é o
topo dessa ordenação.

Em produção, não é. O que chega ao agente passa antes por uma **superfície de entrega**
de capacidade fixa: um brief de 10 itens no início da sessão, e a busca sob demanda.
Dez slots, servidos algumas centenas de vezes por dia, contra um corpus de dezenas de
milhares de itens. Se essa superfície é o gargalo, então melhorar a ordenação não
melhora a exposição, e boa parte do esforço da área está otimizando uma coordenada que
não é a que decide. Isso é verificável, e ninguém verificou: medir exige acesso ao
sistema **em operação**, não a um conjunto de queries.

Este paper mede. Por 12 semanas, instrumentamos as duas superfícies de exposição de um
sistema de memória em produção — 6 agentes, ~670 briefs/dia, 67.187 chunks — e
registramos, item a item, o que cada uma entregou. **83,78% do corpus nunca foi exposto
por nenhuma das duas.** E o que decide quem entra não é a relevância que o próprio
sistema atribui: é o **tamanho da coleção** a que o item pertence
(`r = −0,728` entre `log₁₀(tamanho)` e `% exposto`, sem uma única sobreposição entre
tipos grandes e pequenos). Um tipo com 53 itens é exposto em 100%; um com 32.920, em
10,7%.

O achado tem mecanismo, e o mecanismo é **dedutível do código** em vez de inferido dos
dados: os slots de cobertura são ordenados por um comparador **lexicográfico**
`(last_served ASC, salience DESC)`, que só consulta o score quando a primeira
coordenada empata. Qualquer bônus aditivo no score age, portanto, na coordenada
**subordinada** — e isso prediz um **teto**, não uma resposta proporcional. Testamos a
predição intervindo em produção com dose crescente e replay fiel ao pipeline real em
350 de 350 briefs: a resposta é monótona, satura em `w ∈ (4,0; 4,4]`, e o teto é
**4,86%** dos briefs. A predição sobrevive ao teste que poderia tê-la matado.

⚠️ **O que este paper não afirma:** que a exposição mudou o **comportamento** do agente.
Não há desfecho a jusante instrumentado, e a §5.4 diz por quê. O objeto medido é a
superfície, não o efeito dela.

- **O gap.** O survey canônico da área (TMLR 2602.06052v4, 218 papers) mapeia
  arquiteturas e benchmarks de memória para agentes. Benchmarks medem nDCG/recall sobre
  conjuntos de queries. Nenhum mede a **superfície de entrega**: quantos itens distintos
  um agente em produção realmente vê, e quais.

  E o vocabulário de metodologia experimental **não está lá**. Recomputado sobre o PDF
  v4 (`measurement/survey-string-count.py`, sha256 `497e9549…b46a6`, 429.387 caracteres,
  63 hifenizações de fim de linha costuradas antes de contar):

  | termo | corpo | bibliografia |
  |---|---|---|
  | `pre-registration` / `preregistration` (e as 6 outras grafias) | **0** | **0** |
  | `randomized` / `randomised` | **0** | **0** |
  | `ablation` / `ablations` | **0** | **0** |
  | `interventional` | 1 | 0 |
  | `counterfactual` | 1 | 0 |

  Não é ausência de uma palavra: é ausência da **família inteira**. Um survey de 218
  papers que diz `memory` 1.169 vezes e `randomized` nenhuma não está omitindo um
  termo — está descrevendo um campo cujo instrumento é o benchmark offline, não o
  experimento. As duas ocorrências que existem são singulares e uma delas, a de
  `counterfactual`, aparece como direção futura sugerida.

  ⚠️ **Zero é o resultado que uma extração quebrada produz de graça**, então a contagem
  roda com controle positivo (`memory`, `agent`, `benchmark`, `evaluation` acima de
  pisos) e aborta se ele falhar. O controle chegou a disparar por `ablation=0`: era o
  **piso** que estava errado — survey cataloga, não ablaciona — e a checagem direta
  (`memory`=1.208, `benchmark`=126 no mesmo texto) mostrou a extração íntegra. O termo
  saiu do controle e virou dado.
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

O sistema é a memória persistente de uma frota de **6 agentes** de codificação em
operação contínua, servindo ~**670 briefs/dia**. O corpus é um SQLite único com busca
léxica (FTS5), vetores densos e um grafo de entidades; no instante da medição,
**67.187** chunks. Um chunk é uma unidade de texto com tipo (`lesson`, `decision`,
`daily`, …), data de origem e três escalares que alimentam a ordenação: `importance`,
`pain` e `access_count`. Nada disto é específico do sistema; o que importa para o paper
é a **forma** da superfície, não a implementação por baixo.

Há exatamente **duas** superfícies pelas quais um chunk pode chegar a um agente, e é o
que torna a população mensurável:

1. o **brief proativo** (`/api/brief`), montado no início de cada sessão e **sempre com
   10 itens**. Nenhum agente pede: ele recebe;
2. a **busca sob demanda**, quando o agente decide procurar.

Toda exposição passa por uma das duas. "Nunca exposto" é, portanto, uma propriedade
verificável e não uma inferência — é a ausência de registro nas duas.

A composição do brief é onde o mecanismo vive. Dos 10 slots, `10 − freshSlots` vêm de um
pool principal ordenado por `salience` (uma soma aditiva de importância, recência, dor e
acesso), e até `freshSlots` são reservados a um pool de **cobertura**, cuja função
declarada é dar chance ao que ainda não foi servido. O pool de cobertura é ordenado por
um comparador **lexicográfico** `(last_served ASC, salience DESC)`.

Três parâmetros dessa descrição são, eles mesmos, resultados — e o §5 os estabelece:

- **`freshSlots = 2`** em produção, e por *default de configuração sem override*: o
  número que governa a renovação inteira da superfície nunca foi escolhido;
- é **teto**, não cota — os 2 slots são preenchidos *se* houver candidato elegível, e o
  §4.3.1 mostra cinco dias seguidos em que não houve;
- e o comparador ser **lexicográfico** — e não uma soma ponderada — é o que dá ao
  `salience` o papel de coordenada **subordinada** dentro do canal de cobertura.

⚠️ **É um sistema.** A generalização do mecanismo (§5) é **dedutiva**, a partir da
álgebra do comparador, e não empírica; quantos sistemas compartilham essa forma é
pergunta aberta que o diagnóstico publicado permite responder um sistema por vez.

**Figura 0** — `measurement/out/fig0-arquitetura.svg`: corpus → dois canais → 10 slots,
com o comparador anotado no canal de cobertura e os 2 slots dele destacados.

⚠️ É a **única** figura do paper que não deriva de dado: um diagrama de arquitetura é
afirmação sobre o **código**, não sobre uma medição, e a geometria é escrita à mão. Mas
todo **número** rotulado nela vem de `out/superficie.json` — rótulo digitado envelhece
para falso em silêncio, e neste projeto já envelheceu uma vez. O gerador **aborta** se a
identidade `expostos-vivos + nunca-expostos = corpus` deixar de fechar; foi ele que
expôs, ao ser escrito, que a soma ingênua excede o corpus em 152.

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

⚠️ **As duas linhas contam populações diferentes**, e a soma denuncia: 11.051 + 56.288
= 67.339, **152 a mais** que o corpus. A união conta o que já foi exposto *alguma vez*,
inclusive 152 chunks servidos no brief e **apagados depois**; o complemento conta o que
existe *hoje* e nunca foi. Descontando-os, 10.899 + 56.288 = 67.187 exato. O percentual
citado é sobre o corpus vivo, que é a população da qual se pode dizer "nunca exposto".

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

⚠️ **A tabela acima usa um filtro, e ele estava no código e não no texto.**
`superficie-de-exposicao.py` seleciona tipos com `HAVING total >= 10`, o que exclui
`pending` (n=6) e `procedure` (n=3). **Ambos têm 0% de exposição e ambos são pequenos**
— ou seja, o filtro remove exatamente a evidência que contraria "pequeno ⇒ muito
exposto". Um filtro que só pode ajudar precisa ser declarado, e o efeito dele, medido
(`measurement/robustez-tamanho-exposicao.py`).

Duas explicações competem: **curadoria** (tipos mais curados são mais expostos) e
**tamanho** (coleções pequenas cabem na superfície). O teste separa — mas a força do
teste depende de como se conta:

| análise | 13 tipos (com filtro) | 15 tipos (sem filtro) |
|---|---|---|
| Pearson `r` (log₁₀ n × % exposto) | **−0,728** | **−0,334** |
| Spearman ρ | −0,687 | **−0,098** |
| **β binomial** (logit, ponderado por n) | **−0,982** | **−0,961** |

🔴 **A correlação de percentuais é frágil ao filtro; o modelo binomial não é.** A razão
é que correlacionar percentuais dá a um tipo de 3 chunks o mesmo peso de um com 32.920.
O modelo binomial usa todos os tipos e pesa cada um pela informação que carrega — os
dois excluídos movem o coeficiente em **2%**, não pela metade. **É o binomial que este
paper reporta**, e a correlação fica como descrição da figura, não como teste.

**β = −0,961 ⇒ as chances de exposição caem para ×0,38 a cada década de tamanho.**

⚠️ **E o erro-padrão do modelo é inutilizável.** Ele dá `± 0,027` (z = −35) porque supõe
67.187 observações independentes; o preditor é **constante dentro do tipo**, então a
unidade de independência é o tipo e o `n` efetivo é **15**. Pelo jackknife sobre tipos:
**EP = 0,471, z = −2,0**. Deixar **um** tipo de fora move β para dentro de
`[−1,12 ; −0,51]`. O achado sobrevive, e sobrevive **por pouco** — dizer o contrário
seria vender como robusto um resultado que uma única coleção pode quase pela metade.

📌 **Corolário que o mesmo argumento impõe:** recalcular a correlação "no nível do
chunk" **não** responde à objeção ecológica. Como `log₁₀(tamanho)` não varia dentro do
tipo, o `r` ponto-bisserial sobre 67.187 chunks (**−0,150**) apenas repondera os mesmos
15 pontos. Desagregar um preditor que é propriedade do grupo não cria informação.

**O que sobrevive intacto, e é a forma mais forte do achado:** *nenhum tipo pequeno cai
dentro da faixa dos grandes.* Os 5 tipos com n ≥ 1.000 ocupam **10,7–27,0%**, e nenhum
dos 10 tipos com n < 100 está nesse intervalo — eles estão **acima** (32,5% a 100%) ou
**em zero**. ⚠️ A frase "sem sobreposição" da versão anterior era mais forte que isso e
**falsa com os 15 tipos**: incluindo `pending` e `procedure`, a faixa dos pequenos passa
a ser 0–100%, que contém a dos grandes inteira. Os dois casos em zero são explicáveis
(`pending` tem 6 dias de idade; `procedure` tem 3 chunks) e a explicação é *post hoc* —
está aqui como limite, não como defesa.

**E o confundidor idade não explica o achado.** Tipos grandes são, de fato, mais velhos
(`r(log n, idade) = +0,41`), mas a parcial controlando idade fica em **−0,709** — quase
inalterada. Restringindo aos 9 tipos com idade média ≥ 70 dias, onde a idade é
aproximadamente constante, a relação **fortalece**: `r = −0,843`, ρ = −0,883. O mesmo
vale para importância média (parcial −0,685) e para o tamanho do texto (−0,732).

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

**Figura 2** — `measurement/out/fig2-concentracao.svg`: curva de Lorenz do carrossel
(rank × share cumulativo dos slots), com marca nos 3 constantes — que sozinhos tomam
**30,0%** dos slots — e no corte do top-10. Gerada por `fig2-concentracao.py --dados
out/superficie.json`, e o script aborta se a curva não somar `slots_7d`.

⚠️ A diagonal de igualdade na figura é referência de **leitura**, não hipótese nula: um
brief de 10 slots servido 4.632 vezes não poderia distribuir 46.295 slots igualmente
entre 67.187 chunks nem em princípio — só cabem 201.

#### 4.3.1 O carrossel não gira: ele salta, e entre saltos congela

A diversidade diária tinha uma "quebra de regime" em 21–22/08 que ficou listada como
ameaça sem explicação. Ela tem explicação, é mecânica, e o mecanismo importa mais que
a quebra (`measurement/regime-cobertura.py`):

| dia | distintos | ∩ com ontem | retido | novos | frescos ≤7d | idade mín. servida |
|---|---|---|---|---|---|---|
| 16/08 | 100 | 89 | 80,9% | 3 | 54 | 5,92 |
| **17/08** | 49 | 43 | 43,0% | 1 | **0** | **13,96** |
| 18/08 | 49 | 41 | 83,7% | 0 | **0** | **14,96** |
| 19/08 | 35 | 35 | 71,4% | 0 | **0** | **15,96** |
| 20/08 | 87 | 35 | 100% | 52 | **0** | **16,96** |
| 21/08 | 85 | 85 | 97,7% | 0 | **0** | **17,96** |
| **22/08** | 193 | 85 | 100% | **108** | **108** | **0,72** |
| 23–27/08 | 141–146 | 141 | ~100% | 0–5 | 108–113 | 0,92 → 4,92 |

Três leituras, e cada uma precisa da anterior:

1. **a interseção com o dia anterior é ~100%** quase todo dia. Nada *sai* do conjunto
   servido; o que varia é só o que **entra**. Não é carrossel girando, é acréscimo;
2. **de 17 a 21/08 nenhum chunk com menos de 7 dias foi servido — cinco dias seguidos**
   — e a idade mínima servida sobe **exatamente +1,00 por dia** (13,96 → 17,96). Essa
   é a assinatura de um conjunto **literalmente congelado**, envelhecendo;
3. **as entradas são duas injeções discretas.** A de 22/08 é uma **única leva de
   ingestão**: 108 chunks criados entre 21/08 22:51 e 22/08 02:01, de 56 arquivos.

O mecanismo, então, é a interação de duas coisas já documentadas: o pool de cobertura
exige `freshMaxAgeDays = 7`, e a ingestão chega **em lotes**. Cada lote alimenta o canal
por exatamente 7 dias e depois expira; entre lotes o pool fica **vazio**,
`interleaveFresh([], global) === global`, e os 2 slots de cobertura caem no pool global,
que está congelado. A leva de 09–10/08 alimentou até 16/08 e morreu em 17/08 — sete dias
depois de 10/08.

📌 **Predição datada, e é falsificável antes da submissão:** a leva de 21–22/08 tem
5,92–6,47 dias em 28/08. Ela **expira em 29/08**, e o canal volta a servir zero frescos
a menos que outro lote chegue. Se isso não acontecer, o mecanismo aqui descrito está
errado.

**Por que isso é resultado e não nota de rodapé:** a renovação da superfície não é
governada pela relevância nem pelo ranker — é governada por **quando alguém ingeriu um
lote**. É a mesma tese do §4.2 num segundo eixo: capacidade e calendário decidem, não
mérito.

⚠️ **Uma armadilha de contagem, registrada porque quase me pegou.** Contar isto com
`JOIN chunks` faz 20/08 aparecer com 33 distintos onde `brief_log` diz 85 — os outros
**52 não existem mais** (servidos e apagados depois; é a injeção de 20/08, cujos 52
chunks sumiram por inteiro). Contagem de exposição sai de `brief_log`; só o que precisa
de metadado faz JOIN, e declara a perda.

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

**Figura 3** — `measurement/out/fig3-dose-resposta.svg`: as duas séries de dose-resposta
em eixo `w` logarítmico — grid grosso (9 doses × 350 estados) e grid fino (23 doses × os
17 que se movem) — com a banda registrada `{2 · 4 · 7,5}` marcada no eixo, a linha do
teto `17/350` e a região de saturação. Gerada por `fig3-dose-resposta.py`.

⚠️ **As duas séries têm denominadores diferentes e o mesmo numerador**, e é o que
autoriza sobrepô-las: um estado fora dos 17 não se move em dose alguma. Isso não é
argumento, é conferível — as séries compartilham exatamente **uma** dose (`w = 1`) e ali
as duas dão **8**. O script **aborta** se deixarem de bater, porque duas curvas no mesmo
eixo que discordam onde se cruzam são uma figura mentindo em silêncio.

⚠️ E o **controle negativo** `w = 0 ⇒ 0/350` aparece como anotação, não como ponto: zero
não existe em eixo log. Espremê-lo no primeiro tick seria plotar `w = 0,015`, que não foi
medido; omiti-lo seria não reportar o controle.

⚠️ **A grandeza que governa é distância, não passo.** O maior `w_min` (4,4) vale bônus
`0,0946`, **1,79×** o maior gap entre candidatos adjacentes no pool (`0,05272`). Bônus
maior que qualquer passo entre vizinhos e ainda insuficiente ⇒ o item atravessa
**várias** posições até alcançar os 2 slots.

### 4.5 O que este desenho **não** identifica

Seção obrigatória, e ela vem **antes** da discussão de propósito:

- **nenhum efeito sobre o agente.** Não há desfecho a jusante instrumentado: três
  tabelas de qualidade voltada ao agente com **0 linhas**; a telemetria de busca
  registra a **sonda de saúde do cron** — em janela fechada de 7 dias, **325 de 343
  linhas (94,8%)** caem nos dois minutos por hora em que o cron dispara, sobrando
  **2,6 linha/dia** atribuível a agente; e das 25 colunas dessa tabela, **16 não
  têm escritor** hoje, entre elas a única com identificação por chunk;
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

A contribuição declarada (v) **é o método**, então omitir isto tiraria do paper uma das
coisas que ele tem para dar. O catálogo integral tem **16** entradas e vive no Apêndice
E. Aqui ficam as **sete que mudaram um número que este paper reporta** — porque sem elas
o leitor não tem como auditar os números, e é esse o critério de corte, não o interesse
da lição.

| defeito | número que ele mudou |
|---|---|
| controle positivo rodado sobre pipeline **reimplementado** | produziu "dose absurda ⇒ efeito zero", que virou retratação central. O pipeline real dá **20** eventos |
| **teste de uma derivação sobre pool RECONSTRUÍDO** (`interleaveFresh` não é exportado) | classificou 25 estados como alteráveis contra 17 reais, e só **1 das 17** caía na classe; 24 violações do pressuposto de prefixo eram o sintoma. O teste válido usa só grandezas **registradas** (§5.6) |
| `served_at` com resolução de **segundo** e 6 agentes disparando em 1–2 s | **46,9%** dos briefs dividem o segundo; nenhum corte temporal reproduz o estado. Sob corte estrito o replay **inventa** 3 e **perde** 1 evento: desfecho sai **14 em vez de 12** (+16,7%) |
| grid grosso | saturação *pareceu* cair exatamente no topo da banda registrada; com 23 doses está em `(4,0 ; 4,4]` |
| telemetria de busca por chunk **muda** desde 2026-05-19 14:47:04, numa fronteira de deploy (buraco de 1h19 nas linhas, e nulo para sempre depois), **sem `CUT`** — a convenção deste projeto para retirada deliberada | comparação entre superfícies **dentro de janela** é impossível, e passou **3,3 meses** sem ninguém notar |
| comparação de contagem **filtrada** com **não-filtrada** | inverteu o sinal de uma conclusão: 617×245 cumulativo vira 245×≥151 na janela comum |
| **um κ agregado reportado ao lado de uma estratificação que depende de outra fronteira** | `κ = 0,874` é o veredito falha/sucesso ≈ o corte S0/S1 (κ **0,868–0,930**). Na fronteira S1/S2, que é a que define o estrato, o κ é **0,309–0,528**. O painel concorda sobre **se** falhou e não sobre **quão grave** — e um número só escondia isso (Apêndice C.1) |

O padrão que atravessa as sete, e que é o achado transferível: **cada uma passou por
verificação e sobreviveu.** Não são erros de descuido — são erros em que o instrumento
de verificação compartilhava a premissa errada do que verificava. Um controle positivo
rodado sobre o pipeline reimplementado confirma o pipeline reimplementado; um censo de
colunas mortas feito por `grep` herda a cegueira do `grep`. A defesa que funcionou, nas
sete, foi a mesma: **reproduzir uma âncora publicada antes de variar qualquer coisa**.

⚠️ E há uma assimetria que vale dizer: quatro dos sete foram achados porque um número
**bateu bem demais** — saturação exatamente no topo da banda registrada, dose absurda
com efeito exatamente zero. Concordância suspeita foi um detector melhor que discordância.

## 7. Ameaças à validade

- ⚠️ **`n = 1` sistema.** É a ameaça principal e não tem mitigação dentro deste paper.
  A generalização do mecanismo é **dedutiva** (§5), não empírica: vale para qualquer
  ranker com ordem lexicográfica e bônus na coordenada subordinada, e **se** outros
  sistemas têm essa estrutura é questão aberta. Mitigação parcial: publicar o
  diagnóstico executável para que terceiros meçam o próprio sistema;
- tipos pequenos (`decision` n=11, `person` n=14, `feedback` n=17) não sustentam
  leitura individual — entram só no teste de correlação;
- `access_count` é "exposto alguma vez", sem histórico por evento;
- ~~a diversidade de cobertura por dia tem quebra de regime em 21–22/08, ainda sem
  explicação~~ → **explicada** (§4.3.1): não é quebra, é canal alimentado a lotes com
  janela de 7 dias. Vira **limite declarado**, não ameaça aberta: qualquer desfecho
  construído sobre diversidade diária é não-estacionário por dependência do calendário
  de ingestão, e uma janela que não contenha um lote mede zero por construção;
- a intervenção correu em modo **shadow**: o contrafactual é observado, mas nada foi
  servido tratado. Toda taxa é **taxa de oportunidade**, não efeito.

## 8. Trabalho relacionado

### 8.1 O que a área de memória para agentes mede

O survey canônico (TMLR 2602.06052v4) particiona as métricas em uso em três famílias —
baseadas em acurácia, em similaridade e em LLM-como-juiz — e todas as três pontuam a
**representação**: dado um conjunto de queries, quão bem o sistema recupera o que é
relevante. MemoryArena (2602.16313) e Evo-Memory (2511.20857) são as vizinhas mais
próximas e ambas comparam **sistemas** sobre tarefas fixas. Nenhuma mede o que o
sistema **entregou** ao agente sob o tráfego que ele de fato recebeu.

A célula vazia não é um detalhe de cobertura: uma métrica de recuperação é condicional
a uma query ter sido feita. Um item que nenhuma query alcança e que nenhum brief inclui
tem nDCG indefinido, não baixo — e é exatamente a população que este paper mede
(83,78%).

### 8.2 Exposição em recomendação — onde o vocabulário existe

A noção de que a atenção entregue é um recurso **finito e alocável**, distinto da
relevância estimada, está madura em recuperação e recomendação. Singh e Joachims
(KDD '18) formulam alocação de exposição como restrição otimizável; Diaz et al.
(CIKM '20) tornam a **exposição esperada** uma métrica de avaliação, sobre rankings
estocásticos. A literatura de *popularity bias* mede o fenômeno correlato do lado do
catálogo — itens da cauda longa recebem exposição desproporcionalmente menor que sua
prevalência (survey de Klimashevskaia et al., UMUAI 2024, sobre 123 trabalhos) — e
Chaney et al. (RecSys '18) mostram que o laço de realimentação entre o que é exposto e
o que é aprendido aumenta homogeneidade ao longo do tempo.

Nosso resultado é *popularity bias* onde a "popularidade" é **o tamanho da coleção a
que o item pertence**, e o laço de realimentação de Chaney tem análogo direto:
`access_count` entra na `salience`, então o que foi exposto fica mais exposível.

O trabalho mais próximo do nosso achado é Bower et al. (2022), que mostra que a
desigualdade de exposição se origina **antes** da ordenação, no conjunto de candidatos
— e que randomizar o passo seguinte pode até piorá-la. Concordamos na localização e
divergimos no mecanismo, e a divergência é o ponto:

> ⚠️ **Essa literatura pressupõe que exposição é monótona no score que se controla** —
> é o que autoriza redistribuir exposição tornando o ranking estocástico. Aqui a
> pressuposição **falha estruturalmente**: os slots de cobertura são ordenados por um
> comparador **lexicográfico**, o score é a coordenada **subordinada**, e um bônus
> aditivo no score só age dentro de **empates** da coordenada dominante (§5.2). Um
> lever construído sobre score não move o que a coordenada dominante já decidiu — e
> isso não é uma questão de magnitude do bônus, é a álgebra do comparador.

Daí a ponte não ser só terminológica. O vocabulário de capacidade de superfície importa
para memória de agente, e a técnica padrão de redistribuição **não transfere** sem
antes verificar em que coordenada a ordenação decide. Essa verificação é o diagnóstico
que publicamos.

⚠️ Duas ressalvas de escopo. A analogia é de **mecanismo**, não de aplicação: lá quem
consome é um usuário humano com posição e atenção decrescentes, aqui é um agente que
recebe 10 itens de uma vez, e não há modelo de posição. E "justiça de exposição" é uma
questão normativa que **não** levantamos: o argumento aqui é de utilidade e de
diagnóstico, não de equidade entre itens.

### 8.3 Pré-registro em CS de sistemas

O registro prospectivo de hipótese, desfecho e análise é rotina em ensaios clínicos e
em partes da psicologia; em CS de sistemas, não. O survey de 218 papers da §8.1 tem
**zero** ocorrências de qualquer grafia de *pre-registration* — e, medido junto,
**zero** de `randomized`/`randomised` e de `ablation` (§1). A ausência é da família
metodológica inteira, não de um termo.

Isso condiciona o que este paper pode oferecer como precedente: não há convenção
estabelecida sobre o que declarar antes de intervir num sistema de memória vivo. O
Apêndice A registra nossos desvios do próprio pré-registro — inclusive os que
invalidaram medições publicadas — porque um precedente que só mostra o caminho limpo
não é precedente utilizável.

📌 **Procedência desta seção.** MemoryArena e Evo-Memory foram lidos **integralmente**
em 15/08 (`RELATED-WORK.md` §4 e §4.1); o survey, integralmente em 13/08, com as
contagens recomputadas em 28/08 sobre o PDF pinado por sha256. Os trabalhos de
recomendação da §8.2 foram lidos em **resumo e metadados**, não em texto integral —
declaro porque a afirmação que faço sobre eles é sobre a **pressuposição de
monotonicidade**, e essa é uma afirmação que texto integral poderia refinar.

## 9. Discussão

Duas afirmações, e nenhuma além.

**Primeira: quando a capacidade é o gargalo, melhorar a ordenação não melhora a
exposição.** Neste sistema a superfície entrega 10 itens por brief contra 67.187
chunks, e o que decide quem entra correlaciona com o tamanho da coleção
(`r = −0,728`), não com a relevância atribuída. Um embedding melhor reordena os
candidatos; não cria slot. Isso não diz que trabalho de *ranking* é inútil — diz que
o ganho dele é limitado por uma quantidade que a área não mede, e que **é medível**:
o diagnóstico publicado (`measurement/`) computa a superfície de exposição de qualquer
sistema que registre o que entregou. A pergunta "quantos itens distintos meu sistema já
serviu, e quais?" deveria ser barata de responder, e hoje não é — não por dificuldade
técnica, mas porque ninguém instrumenta para ela. Foram **16 colunas de telemetria sem
escritor** neste próprio sistema, em seis instantes distintos, uma delas a que
registrava exatamente quais chunks a busca devolveu (§6).

**Segunda: uma intervenção em memória viva tem de declarar em que coordenada age.**
Um bônus aditivo na coordenada **subordinada** de um comparador lexicográfico tem teto
**analítico**, não empírico: ele só pode mover o que está empatado na coordenada
dominante (§5.2). Medimos o teto — 4,86% dos briefs, saturando em `w ∈ (4,0; 4,4]` — e
a predição veio da leitura do comparador, antes da dose-resposta. A consequência de
desenho é desconfortável e vale dizer inteira: **projetamos uma intervenção cujo teto
era derivável do código antes de ela ser implantada.** Quem for intervir num ranker
deveria fazer essa derivação primeiro; custa uma tarde de leitura e economiza uma
rodada experimental.

⚠️ **O que não afirmamos.** Que a exposição mudou o comportamento do agente — não há
desfecho a jusante instrumentado (§5.4). Que 83,78% de não-exposição seja *ruim* —
parte do corpus é log, e log não precisa ser lido para ser útil; o que o número
estabelece é a **escala** da população que nenhuma métrica de recuperação alcança. E
que o mecanismo generalize empiricamente: ele generaliza **dedutivamente**, para
qualquer ranker com ordem lexicográfica e bônus na coordenada subordinada, e quantos
sistemas têm essa forma é uma pergunta aberta que o diagnóstico permite responder uma
instalação por vez.

## Apêndice A — Desvios do pré-registro

Íntegro em `DEVIATIONS-FOR-PAPER.md`. O pré-registro está depositado (OSF `yf7d2`,
Zenodo `10.5281/zenodo.22110203`) e **não foi emendado**: a escolha foi deixá-lo como
registrado e declarar cada desvio aqui. Isso só é honesto se a lista for completa e se
os desvios que **favorecem** o estudo aparecerem com a mesma proeminência dos que o
prejudicam — então a coluna de direção é obrigatória.

| o registro afirma | o que se mediu | direção |
|---|---|---|
| `Δ_cut = 0,043` é *"the measured salience spread at the brief cut"* | **não existe cut**: o código não aplica limiar. O comparador é lexicográfico e `salience` só desempata `last_served` idêntico | ⬆ superestima |
| a banda `{2 · 4 · 7,5}` está entre *"what does not move, and could not"* | **move**: 11 / 15 / 17 estados de 350, monótono. A dose superior está **acima** da saturação, que fica em `(4,0 ; 4,4]` | ⬇ **subestima** |
| a alocação é `117/39/39/39` | suspensa junto com a banda — e a razão mudou: não é que as doses sejam indistinguíveis, é que a escala não tem referente | ⬆ superestima |
| *(v1.12 §5)* a designação é defeito **aberto** | **fechada** em 26/08 20:28Z, com precedência verificável de **1.056 s** sobre a rodada drand | ⬇ **subestima** |
| estratificação por severidade com **S2** como estrato de análise | o painel tem κ **0,31–0,53** nessa fronteira; análises substantivas migram para **`≥ S1`** (κ 0,87–0,93). Ver Apêndice C.1 | ⬆ superestima |

⚠️ **As duas linhas ⬇ são as que incomodam, e são as que o tempo não conserta.** As ⬆
fazem o registro prometer mais do que o desenho entrega — quem ler acha o estudo mais
forte do que é, e corrigi-las custa alegação mas ganha rigor. As ⬇ fazem o oposto: o
registro afirma que um parâmetro **não** tem efeito quando tem, e que um defeito está
**aberto** quando foi fechado. Ninguém corrige sozinho um erro que o favorece.

⚠️ **E a linha da banda mudou de status por um defeito de instrumento meu**, não por
dado novo: o controle positivo que produziu o *"não move"* rodava sobre um pool
**reimplementado**. Isso é matéria do §5.6, não nota de rodapé.

**Sobre o desvio de S2, especificamente.** Trocar o estrato de análise depois de ver os
dados é exatamente o movimento que um pré-registro existe para impedir, então ele
precisa de justificativa que não seja o resultado: a justificativa é uma propriedade do
**instrumento** (concordância entre painelistas), medida sobre os votos e independente
de qualquer desfecho. Nenhuma estimativa foi comparada entre as duas opções antes de
escolher — e o critério, "usar a fronteira em que o painel concorda", teria sido o mesmo
qualquer que fosse o sinal.

## Apêndice B — Cadeia da designação

Sorteio com seed declarada: rodada drand quicknet **31657512** (emissão 20:25:00Z),
declaração pushada **20:07:24Z** — **1.056 s** de precedência, com a rodada devolvendo
HTTP 425 no momento da escrita. Um revisor independente rederivou o conjunto designado
usando **apenas** o beacon público e o CSV depositado.

## Apêndice C — Painel de adjudicação

Painel de 3 famílias (`moonshot` · `xai` · `zhipu`), 280 episódios com voto dos três,
870 chamadas. Adjudicações: **S0 = 225 · S1 = 33 · S2 = 22**, e **zero** em S3/S4.

### C.1 🔴 Um κ agregado escondia que o painel é confiável numa fronteira e não na outra

O `κ = 0,874` publicado descreve o veredito **falha/sucesso**. Reportá-lo ao lado da
tabela de estratos convida a ler os estratos como igualmente confiáveis. Medido por
fronteira (`painel-limiar-vs-desacordo.py`):

| par | **κ(≥S1)** | **κ(≥S2)** | Jaccard do conjunto ≥S2 |
|---|---|---|---|
| moonshot × xai | **0,868** | 0,528 | 0,395 |
| moonshot × zhipu | **0,870** | 0,309 | 0,208 |
| xai × zhipu | **0,930** | 0,442 | 0,316 |

O painel concorda quase perfeitamente sobre **se** houve falha e mal concorda sobre
**quão grave** ela foi. O 0,874 é, essencialmente, o corte S0/S1.

E o diagnóstico fino desmonta a leitura fácil de que "o problema é o `xai`":

- `xai` é **quase superconjunto** dos outros dois — 1 de 16 e 1 de 13 fora. Isso é
  **deslocamento de limiar**, e limiar deslocado se corrige normalizando;
- mas `moonshot` × `zhipu`, que têm severidade quase igual (16 e 13 graves), têm
  interseção **5**, com 11 e 8 exclusivos. Esses dois **não** discordam sobre onde
  cortar: discordam sobre **quais** episódios são graves. Nenhuma normalização resolve.

📌 **Controle positivo do instrumento:** a nota de 21/08 registra que "sem `xai`
sobreviveriam 5". `|moonshot ∩ zhipu| = 5`, reproduzido exatamente — o script lê a mesma
coisa que a rodada original.

⚠️ **Não se usa leave-one-family-out para nada disto.** Com 3 painelistas a mediana
inferior é o valor do meio; com 2, vira o mínimo. O LOO mistura mudança de estimador com
mudança de painel, e indicava 40% → 9,3% no share de S2, número que carrega o artefato.
Tudo acima é contagem direta sobre os votos.

**Consequência adotada:** as análises substantivas usam **`≥ S1`**, que é onde o painel
tem κ 0,87–0,93; a divisão S1/S2 é reportada como **achado de instrumento**, não como
estrato de análise. Isso é desvio do pré-registro e está declarado no Apêndice A.

### C.2 A regra de parada degenerou

A regra pré-registrada usa incidentes **≥ S3**, cujo baseline medido é **zero** em 870
chamadas. Isso a reduz a "≥ 1 evento derruba". É lição de desenho, e entra como tal:
uma regra de parada calibrada sobre um estrato que nunca ocorre não é conservadora — é
inexistente até o primeiro evento, e depois é absoluta.

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

## Apêndice E — Catálogo integral de defeitos de instrumento

As sete do §6 mais as nove abaixo. A separação é por **consequência**, não por
importância: estas não mudaram nenhum número reportado neste paper — o que não as torna
menos transferíveis, e três delas são as lições que eu esperaria serem as mais úteis a
terceiros.

| defeito | consequência medida |
|---|---|
| relógio do banco dentro do filtro de elegibilidade, apesar de a função receber o instante por argumento | o brief não é função pura de (corpus, estado, `nowMs`); replay ingênuo mede outra população |
| o ordenador **descarta** a chave que ordenou o pool | agrupar por ela dá **um** grupo, em silêncio |
| gatilho de monitoramento calibrado sobre gap **adjacente** | vigia grandeza que não limita o mecanismo: fica **verde enquanto satura** |
| **atribuir a morte de um instrumento a um commit, sem conferir o horário** | eu publiquei que `7fdaab4f` a apagou; o commit é de **2026-05-20 01:03 UTC** e a escrita parou **dez horas antes**. Ele removeu código que já estava mudo. Um diff que *explica* o efeito não é prova de que o *causou* |
| **censo de "colunas sem escritor" por grep, por não-nulo, ou por distintos>1** | os três dão respostas diferentes e todas erradas: grep perde `UPDATE` e SQL dinâmico (−3 colunas), `DEFAULT` produz 11 falsos vivos, e o histórico pré-morte infla os distintos (`reranker_latency_ms`: **394**, todos anteriores). O censo válido é **distintos numa janela posterior**, cruzado com a lista literal da `INSERT`: **16** colunas, em **seis** instantes distintos ao longo de 10 dias — e num deles existe `CUT`, logo é **retirada**, não regressão |
| campo sem escritor usado como **assinatura de origem** | `requesting_agent` nulo foi por mim tratado como prova de que a telemetria media o cron; é nulo para todo mundo desde 2026-05-18. O teste válido é o **minuto do cron** (94,8%) |
| série viva citada como instantâneo | um `n` mudou em minutos e a asserção pegou |
| valor **digitado** dentro do próprio instrumento de verificação | `w_min` máximo ficou fixado em `7,5` no script e envelheceu para falso quando o grid fino deu `4,4`; agora é argumento obrigatório vindo do artefato de dose |
| **"o problema é o painelista discordante"** — que aqui era falso | `xai` é quase superconjunto dos outros (1 de 16 e 1 de 13 fora): deslocamento de limiar, corrigível por normalização. O desacordo irredutível está entre as **duas famílias de severidade parecida** (16 e 13 graves, interseção **5**), que discordam sobre **quais** episódios. Culpar o outlier teria "consertado" a família errada |

## O que falta, em ordem de quem bloqueia quem

Feito em 28/08, salvo indicação:

✅ **§1, §2, §8, §9** escritos · **§5** em 27/08 · **Abstract** escrito.
✅ **Figuras 1, 2 e 3** — cada uma derivada de artefato travado, com guarda próprio.
✅ **contagem do survey** recomputada sobre o PDF pinado por sha256, com controle positivo.
✅ **quebra de regime de 21–22/08** — explicada (§4.3.1), com predição datada para 29/08.
✅ **S2** — decidido pela medição: substantivas em `≥ S1` (κ 0,87–0,93), a divisão S1/S2
vira achado de instrumento (κ 0,31–0,53). Desvio declarado no Apêndice A.
✅ **catálogo de defeitos** — 7 no corpo (as que mudaram número reportado), 16 no
Apêndice E. Sem paper de métodos separado.

Falta:

1. **figura de arquitetura** do §2 — corpus → dois canais → 10 slots, com o comparador
   anotado no canal de cobertura. É a única figura que não deriva de artefato, porque
   descreve estrutura e não dado;
2. **verificar a predição de 29/08** — se a leva de 21–22/08 não secar, o §4.3.1 está
   errado e tem de ser reescrito antes de qualquer depósito;
3. **passagem de revisão adversarial** — vozes de famílias distintas sobre o manuscrito
   inteiro; a lição registrada é que revisão adversarial e censo mecânico pegam classes
   **disjuntas** de defeito, e só o segundo foi feito até aqui;
4. **depósito** com o manuscrito + artefatos, e aí a emenda agrupada faz sentido: um
   registro só, declarando os desvios **e** o resultado novo.
