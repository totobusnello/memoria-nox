# Spare capacity, starved coverage: what a production agent-memory system actually surfaces

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
de 6 agentes: um brief proativo de 10 itens e a busca sob demanda.

O brief entregou **583.973 slots** — **8,7 vezes** o tamanho do corpus, o suficiente para
servir cada um dos 67.187 chunks quase nove vezes. Entregou **1.787 chunks distintos: 2,66%**. A
capacidade **agregada**, portanto, não obrigava esse resultado: havia espaço para mostrar
o corpus inteiro nove vezes. Não se conclui daí que a ordenação esteja errada — só que
não foi a falta de espaço que produziu o número. A capacidade **por sessão** (10 itens)
não é testada aqui. (A cobertura de 99,98% sob serviço uniforme aparece como limite
aritmético do que a capacidade permitiria, não como política recomendada.) Somando a busca, **83,78% do corpus nunca foi
exposto por nenhuma das duas superfícies.**

**Os dois canais da superfície congelam, por motivos opostos e nenhum ligado a
capacidade.** Os 8 slots do pool principal são ordenados por um score cujos termos, com
uma exceção, **não decaem** — o componente de acesso é monótono num contador que só
sobe. Os 3 chunks presentes em **100%** dos 4.632 briefs da semana foram acessados pela
última vez há 90, 30 e 42 dias: o topo do brief é um **fóssil do tráfego de busca de
meses atrás**, e o top-10 leva **47,16%** dos slots. Os outros 2 slots são um canal de
*cobertura*, que existe para dar chance ao nunca-servido — e **congela** por outra razão:
sua população elegível é de **108 chunks num corpus de 67.187** — 0,16%, recortados por
dois padrões de caminho — e ele a esgota **inteira, todo dia**, com 12,4 slots por
candidato. Não sobra nunca-servido para dar chance a. O canal que responderia a um ajuste de score é o que ninguém ajusta; o desenhado
para corrigir o outro é o que não responde a score.

O mecanismo do canal de cobertura é **dedutível do código**. Ele ordena por um comparador
**lexicográfico** `(last_served ASC, salience DESC)`: o score é a coordenada
**subordinada** e só decide dentro de empates da dominante — o que prediz um **teto**,
não uma resposta proporcional, para qualquer bônus aditivo no score **desse canal**.
Testamos com dose crescente em produção e replay fiel ao pipeline real em **350 de 350**
briefs: resposta monótona em cada estado, saturação em `w ∈ (4,0; 4,4]`, teto de
**4,86%** dos briefs. E o teto não é constante do mecanismo, em dois eixos que medimos:
sob a mesma regra com outro sorteio de designados ele chega a **7,43%** (o sorteio em
vigor fica no mínimo da distribuição, empatado com outro), e truncando a resolução do timestamp de segundo para
minuto ou hora vai a **36%** e **80%** — sem alterar uma linha de código. **O alcance do
mecanismo é fixado por decisões que ninguém tomou como política.**

⚠️ **O que não afirmamos.** Nenhum efeito sobre o comportamento do agente: não há
desfecho a jusante instrumentado (§5.4). Que a concentração seja *errada* — uma política
que serve 10 itens por sessão **deve** concentrar, e servir uniformemente seria inútil;
o achado é que a não-exposição é **resultado de política e não limite de capacidade**,
logo é endereçável. E não afirmamos nada sobre a área: é **um** sistema, a generalização
do mecanismo é dedutiva e vale para qualquer ranker com ordem lexicográfica e bônus na
coordenada subordinada. Quantos sistemas têm essa forma é pergunta em aberto, e o
diagnóstico executável que publicamos existe para que outros a respondam um por vez.

⚠️ Duas ressalvas de leitura: dos 10.899 chunks expostos, **9.755 vieram da busca, que é
iniciada pelo agente** — só o brief é entrega decidida pelo sistema, e é sobre ele que
valem as alegações de mecanismo. E o tamanho de coleção, que correlaciona com exposição
(§4.2), pode ser **proxy de como o tipo é produzido**: curadoria não é descartada como
causa comum.

## 1. Introdução

Um sistema de memória para agentes é julgado, hoje, pela qualidade da recuperação: dado
um conjunto de queries, quão bem ele ordena o que é relevante. É a pergunta que os
benchmarks respondem e é a que a engenharia otimiza — embeddings melhores, reranking,
expansão de query. Ela pressupõe, sem dizer, que o que o agente recebe é o topo dessa
ordenação.

A pergunta que ninguém faz é anterior: **o que o agente recebe, de fato?** Ela não é
respondível com um conjunto de queries, porque exige o sistema em operação — e é
respondível, porque toda entrega passa por um número pequeno de superfícies que se pode
instrumentar. Aqui são duas: um brief proativo de 10 itens no início de cada sessão, e a
busca sob demanda.

**A resposta esperada seria "não cabe". Não é.** Em 84,7 dias o brief entregou **583.973
slots** a 67.187 chunks — capacidade para servir cada chunk **8,7 vezes**. Serviu **1.787
distintos, 2,66% do corpus**; sob serviço uniforme a cobertura esperada seria 99,98%.
Somando a busca, **83,78% do corpus nunca foi exposto**. A não-exposição não é imposta
pelo número de slots: é produzida pela ordenação.

⚠️ Isso não é acusação à política. Uma superfície de 10 itens **deve** concentrar —
servir memória ao acaso seria pior que não servir. O que muda com o número é a natureza
do problema: enquanto se acredita que a superfície é pequena demais, a não-exposição é
um fato da vida; medido que ela é 8,7× maior que o corpus, a não-exposição vira uma
**escolha de política**, e escolha se examina.

Examinamos, e o desperdício tem endereço. Os 8 slots do pool principal convergem: 3
chunks aparecem em **100%** dos briefs, e o top-10 leva **47,16%** dos slots de uma
semana. Os 2 slots restantes são um canal de **cobertura**, que existe precisamente para
dar chance ao nunca-servido — e é ele que falha, por dois motivos que nada têm a ver com
relevância:

1. **calendário.** O canal só considera itens com menos de 7 dias, e a ingestão chega em
   **lotes**. Entre lotes o pool fica vazio e o canal serve o mesmo conjunto por dias:
   medimos **cinco dias seguidos** com zero itens novos, com a idade mínima do que foi
   servido subindo exatamente **+1,00 por dia** — a assinatura de um conjunto congelado;
2. **álgebra.** O canal ordena por um comparador **lexicográfico**
   `(last_served ASC, salience DESC)`, no qual o score é a coordenada **subordinada** e
   só decide dentro de empates da dominante. Isso prediz — dedutivamente, a partir de
   sete linhas de código — um **teto** para qualquer bônus aditivo no score desse canal.

A predição é testável e nós a testamos, com dose crescente em produção e replay fiel ao
pipeline real em 350 de 350 briefs: monótona em cada estado, saturando em
`w ∈ (4,0; 4,4]`, teto de **4,86%** dos briefs. Ela sobreviveu ao teste que poderia
tê-la matado — e a um instrumento anterior que a **confirmou pelo motivo errado** (§5.6).

⚠️ **Escopo, dito antes dos resultados e não depois.** É **um** sistema. Não medimos
efeito sobre o comportamento do agente — não há desfecho a jusante instrumentado (§5.4).
Não afirmamos que a área otimiza a coordenada errada: afirmamos que existe uma
coordenada que os benchmarks não medem, damos o instrumento para medi-la, e deixamos a
pergunta em aberto. E, das duas superfícies, só o brief é decidido pelo sistema — a
busca é iniciada pelo agente, e responde por 9.755 dos 10.899 chunks já expostos.

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
- **Por que a pergunta importa.** ~~Se a superfície tem capacidade fixa e pequena, então
  melhorar ranking não melhora exposição, e a área otimiza a coordenada errada.~~ **Essa
  era a hipótese com que este trabalho começou, e a medição a contradiz:** a superfície
  não é pequena — é 8,7× o corpus. O que importa é o que sobra depois disso: uma
  superfície com folga entrega 2,66%, e o canal que existiria para corrigir isso é
  governado por dois padrões de caminho que enxergam 0,16% do corpus, e por uma ordem
  lexicográfica em que o score não decide. Se outros sistemas têm essa forma é pergunta em aberto — não uma alegação
  deste paper — e o diagnóstico publicado existe para que seja respondida.
- **Contribuições.** (i) a medição da superfície de exposição de um sistema de memória
  de agente **em produção**, com o resultado de que a capacidade excede o corpus em 8,7×
  e mesmo assim 83,78% nunca é exposto; (ii) a localização do gargalo no **canal de
  cobertura**, com os dois mecanismos que o congelam — uma população elegível de **108
  chunks (0,16% do corpus)**, recortada por padrões de caminho, e ordem lexicográfica que
  rebaixa o score a coordenada subordinada; (iii)
  uma predição **dedutiva** de teto para bônus aditivos nesse canal, testada com
  dose-resposta e replay fiel; (iv) o **diagnóstico executável** (`measurement/`), para
  que a medição seja reproduzível em outro sistema.

  ⚠️ **O catálogo de defeitos de instrumento (Apêndice E) não entra como contribuição**,
  e a razão é honesta: são **16 defeitos que nós cometemos**, sete deles alterando um
  número que este paper reporta. Reportá-los é obrigação, não mérito — e sobretudo, sete
  achados **não limitam** os não achados. Estão no apêndice porque quem for reproduzir a
  medição vai cair nos mesmos, não porque nos credenciam.

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

### 4.1 Exposição: 83,78% do corpus nunca chegou ao agente — e 74,75% do que passa o piso do próprio sistema

| | |
|---|---|
| corpus **vivo** | **67.187** |
| exposto no brief (histórico) | 1.787 |
| exposto na busca (histórico) | 9.755 |
| união histórica | 11.051 |
| — desses, **apagados depois** | 152 |
| **união viva** = 11.051 − 152 | **10.899** |
| **nunca exposto por nenhuma** = 67.187 − 10.899 | **56.288 = 83,78%** |
| desses, passam o próprio piso de relevância do sistema | **10.008** |

A tabela fecha em **um** universo — o corpus vivo — e a linha dos 152 é o que faz a
ponte. A versão anterior listava a união histórica ao lado do complemento vivo, e quem
subtraísse `67.187 − 11.051` obtinha 56.136 em vez de 56.288. Os números estavam certos
e a tabela, não.

**A linha do piso é uma manchete, não uma nota de rodapé.** Um leitor pode conceder o
agregado e recusar a consequência: se a maior parte dos 56.288 fosse ruído de baixo
valor, não haveria o que entregar. Não é o caso — dos 13.388 chunks que passam o piso de
relevância do **próprio sistema** (`importance ≥ 0,7 OR pain ≥ 0,7`, verbatim de
`brief.ts:642`), **10.008 = 74,75% nunca foram expostos**. Condicionar à relevância
declarada reduz a taxa em 9 pontos e o valor absoluto em 5,6×; não a dissolve.

**A taxa é incondicional, e essa é a objeção com direção desconhecida.** Um chunk criado
na semana 11 da janela teve 7 dias de oportunidade de exposição; um da semana 1 teve 84.
Os dois entram iguais no denominador. Se o corpus tivesse crescido depressa perto do
fim, uma fatia dos 56.288 seria "novo demais para julgar" em vez de "não entregue".
Estratificando por idade (`measurement/exposicao-por-coorte.py`,
`out/EXPOSURE-BY-COHORT-2026-08-29.json`):

| coorte | chunks | nunca expostos | % |
|---|---:|---:|---:|
| < 1 semana | 96 | 90 | 93,75% |
| 1–4 semanas | 1.213 | 753 | 62,08% |
| 4–12 semanas | 4.553 | 3.013 | 66,18% |
| **> 12 semanas** | **61.325** | **52.432** | **85,50%** |

O viés existe e aponta para o **outro lado**. A coorte com oportunidade **máxima** — 91,3%
do corpus, mais de doze semanas de exposição possível — é a **mais** não-exposta (85,50%
contra 83,78% agregado), e as duas coortes jovens juntas são 1,95% do corpus, pequenas
demais para mover o agregado em qualquer direção. Corrigir pela censura temporal
**aumentaria** a taxa reportada. Reportamos a menor.

⚠️ **Uma terceira perna da mesma objeção é incontável por construção, e fica declarada:**
chunk criado e apagado dentro da janela sem nunca ter sido exposto não aparece em
população nenhuma — o complemento é sobre o corpus *vivo*. Que o inverso exista (os 152
servidos e depois apagados) prova que há churn na janela. A direção desse viés é
desconhecida e não é mensurável com os dados que temos.

#### 4.1.1 Capacidade agregada não obriga o resultado — e o que isso não estabelece

⚠️ **Uma objeção que precisa ser respondida antes de qualquer coisa: 583.973 slots
acumulados não são fungíveis.** A superfície entrega **10 itens por sessão**, e se uma
sessão precisasse de mais de 10 itens relevantes, a capacidade estaria vinculante *hoje*,
por mais folga que houvesse no acumulado. A objeção é correta e restringe a alegação:
não afirmamos que 10 slots por sessão sejam muitos.

**A alegação é sobre rotação, não sobre tamanho da sessão.** A pergunta medida é quantos
itens *distintos* a superfície já mostrou alguma vez, e para essa pergunta os slots
**são** fungíveis no tempo: nada obriga a sessão de hoje a mostrar os mesmos 10 itens de
ontem, e mostrar dez itens diferentes por sessão jamais violaria o limite de dez.

**E a evidência de que a capacidade agregada não vincula é uma linha de aritmética, não
um teste:** 583.973 slots contra 67.187 chunks. Havia espaço para mostrar tudo, nove
vezes. Isso é o que se pode afirmar, e basta para o que o parágrafo anterior sustenta.

⚠️ **Uma versão anterior desta seção trazia aqui uma tabela de "predições opostas"** —
razão `slots/distintos` ≈ 1 sob gargalo de capacidade contra ≫ 1 sob gargalo de política,
com 325 observado — apresentada como o teste que separava as duas hipóteses. **Ela foi
retirada, e a razão de retirá-la é instrutiva.** Primeiro, a predição "≈ 1" não é
derivada da hipótese de capacidade: é a hipótese reescrita na unidade da razão, de modo
que observar ≫ 1 *é* observar folga — medida com duas regiões rotuladas, não teste com
taxa de erro. Segundo, a hipótese que ela derrubava já estava morta pela aritmética acima,
enquanto a hipótese que um defensor sustentaria — demanda por sessão acima de 10 — é a
que declaramos fora de escopo. Terceiro, e decisivo: **qualquer política concentradora
produz ≫ 1**, inclusive uma correta. Num corpus com milhares de fragmentos de sessão e
3.231 chunks do tipo `daily`, uma razão perto de 1 significaria servir digests obsoletos
— seria a política *pior*. A razão media concentração, e a inferência para *defeito* vinha
de graça.

📌 É por isso que o contrafactual uniforme (99,98%) aparece neste paper como **limite
superior aritmético** e não como política recomendada. Servir memória ao acaso seria
pior que não servir — o número existe para dizer o que a capacidade *permitiria*, não o
que se deveria fazer.

🔴 **As duas superfícies não são a mesma espécie de coisa, e a maior delas não é uma
decisão do sistema.** Dos 10.899 chunks vivos já expostos, **9.755 vieram da busca** —
que é **iniciada pelo agente**. Exposição por busca reflete o que o agente **procurou**;
só o brief (1.787) é entrega que o sistema decide sozinho. Isso não invalida o
complemento — "nunca exposto" continua sendo ausência de registro nas duas — mas
restringe o que se pode dizer da causa: o número de 83,78% mede **o que não chegou**, e
não **o que o ranker recusou**. As alegações sobre mecanismo (§5) valem para o brief.

⚠️ **As duas linhas contam populações diferentes**, e a soma denuncia: 11.051 + 56.288
= 67.339, **152 a mais** que o corpus. A união conta o que já foi exposto *alguma vez*,
inclusive 152 chunks servidos no brief e **apagados depois**; o complemento conta o que
existe *hoje* e nunca foi. Descontando-os, 10.899 + 56.288 = 67.187 exato. O percentual
citado é sobre o corpus vivo, que é a população da qual se pode dizer "nunca exposto".

⚠️ **E a leitura tentadora é falsa.** Dos 10.008, **8.928** são fragmentos de sessão de
205 caracteres em média. O achado não é "dez mil lições invisíveis".

### 4.2 Resultado secundário: exposição correlaciona com tamanho de coleção

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
**tamanho** (coleções pequenas cabem na superfície). ⚠️ **Nada aqui as separa**, e a
versão anterior desta frase dizia que o teste separava — não separa. O que os testes
abaixo separam é *artefato de filtro* de *sinal*; as parciais mais adiante controlam
idade, importância média e comprimento de texto, e **nenhuma delas é curadoria**. Não
existe no corpus variável que a meça, então "tamanho" e "curadoria" permanecem
confundidos por construção. O que muda de fato conforme a contagem é a força:

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

**β = −0,961.** ⚠️ **Mas "×0,38 por década de tamanho" é uma parametrização que o
eixo não sustenta, e a versão anterior a reportava assim.** Os 15 tipos não se
distribuem ao longo do tamanho: são **duas nuvens** com um vazio entre elas
(`measurement/lacuna-no-eixo-de-tamanho.py`, `out/SIZE-AXIS-GAP-2026-08-29.json`).

| | |
|---|---|
| tipos com n < 100 | **10** (de 3 a 53) |
| tipos com 100 ≤ n < 1.000 | **0** |
| tipos com n ≥ 1.000 | **5** (de 1.046 a 32.920) |
| maior lacuna no eixo log₁₀(n) | **1,295 décadas**, entre `lesson` (53) e `graph_node` (1.046) |
| — como fração da amplitude do eixo | **32,1%, sem um único ponto** |

Uma inclinação ajustada sobre duas nuvens é, aritmeticamente, a diferença entre elas
dividida pela distância entre elas. Ela **descreve** os dados; o que ela não faz é
autorizar leitura pontual dentro do vazio — "um tipo de 300 chunks teria ×0,38 da chance
de um de 30" é uma predição para a qual **não há observação nenhuma** neste corpus. Com
n = 15 unidades independentes e um terço do eixo vazio, a forma defensável do achado é
o contraste entre as nuvens, não a taxa: **os 5 tipos grandes ocupam 10,7–27,0% de
exposição; dos 10 pequenos, 8 estão acima de 32,5% e 2 estão em zero.**

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

🔴 **E o confundidor que sobra depois da idade é o que impede a conclusão forte.** O
§4.3.1 mostra que a ingestão chega em **lotes de arquivos**: tipos grandes são os
alimentados por pipeline automático; tipos pequenos são escritos à mão. Isso é
**curadoria disfarçada de tamanho** — uma causa comum dos dois, que nenhuma correlação
entre eles pode separar. O paper **não descarta** a hipótese de curadoria; o que ele
mostra é que o tamanho prediz melhor do que a *relevância que o próprio sistema
atribui*, que é uma afirmação mais fraca e é a que os dados sustentam.

⚠️ **Duas propriedades da composição do corpus limitam o quanto a separação surpreende.**
Não existe tipo com `n` entre **53 e 1.046** — com um vazio no meio do eixo, alguma
separação entre "grandes" e "pequenos" está garantida pela composição, não descoberta. E
`other` sozinho é **49%** do corpus, então o agregado de 83,78% é, em boa parte, um tipo.

**`lesson` está em 100% porque tem 53 linhas.** A relevância atribuída pelo sistema não
prediz exposição; o tamanho da coleção prediz — com a ressalva, acima, de que o tamanho
pode ser proxy de como o tipo é produzido.

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

🔴 **Uma frase da versão anterior desta seção estava errada, e o erro é o do paper
inteiro em miniatura.** Ela dizia que a distribuição igual era impossível "em princípio,
porque só cabem 201". **Cabiam 46.295** — um por slot. Os 201 são o **medido**, não o
teto, e chamá-los de teto transforma um resultado em pigeonhole e ensina o leitor a achar
a curva inevitável. A diagonal é referência de **leitura**; o achado é que a curva está
tão longe dela com folga de 230× para não estar.

#### 4.3.1 O carrossel não gira porque não há por onde girar

A diversidade diária do canal de cobertura tem degraus, e a explicação que tentamos
primeiro — "cada lote de ingestão alimenta o canal por sete dias e expira" — **foi
refutada por uma predição datada que registramos antes do dia** (§6 e
`PREDICTION-2026-08-29.md`). O que a refutação expôs é melhor que o que ela derrubou.

**O canal enxerga 0,16% do corpus.** Ele é a **união de dois sub-pools**, cada um com seus
padrões de caminho e sua janela (`brief.ts:135,642,645`; `brief-diversity.ts:59-62`):

| sub-pool | padrões | janela | elegíveis |
|---|---|---:|---:|
| por agente | `sessions/<agente>/%` | 7 d | **0** |
| global | `memory/entities/%`, `memory/lessons.md` | 30 d | **108** |

Sobre ambos incide o piso `importance ≥ 0,7 OR pain ≥ 0,7`. Medido em quatro dias
(`measurement/pool-elegivel.py`, `POOL-ELEGIVEL-2026-08-28.json`):

| | |
|---|---:|
| corpus vivo | 67.187 |
| **pool elegível do canal** | **108** — 0,161% |
| desses, nunca servidos | **0** |
| servidos no dia | **108 — 100% do pool**, em 26, 27, 28 e 29/08 |
| slots de cobertura por candidato elegível | **12,4×** (dia fechado) |

⚠️ O último número é de **dia fechado**: em 29/08, medido com o dia ainda em curso, dá
5,6× simplesmente porque menos briefs ocorreram. O script marca `dia_parcial` para que os
dois não sejam comparados.

**O pool é esgotado todos os dias medidos.** Há doze vezes mais slots que candidatos, então a
ordenação `last_served ASC` ordena mas **não exclui ninguém**: todo elegível aparece,
todo dia. Não há carrossel girando nem lote expirando — há um pool pequeno demais para
que a rotação seja uma pergunta.

Isso muda onde a escassez mora. **No dia, a cobertura do pool elegível é 100%.** Num
brief, são 2 slots para 108 candidatos. O que a ordenação decide — e o que a intervenção
do §5 move — é *quais dois aparecem em cada brief*, não *quanto do corpus é alcançado*.
O corpus não é alcançado porque 99,84% dele nunca entra no sorteio.

**Por que a predição falhou, e o que isso ensina.** Há **dois** sub-pools de cobertura,
com padrões e janelas diferentes:

| sub-pool | padrões | janela |
|---|---|---|
| por agente | `sessions/<agente>/%` | `freshMaxAgeDays = 7` |
| global | `memory/entities/%`, `memory/lessons.md` | `freshGlobalMaxAgeDays = 30` |

O lote de 09–10/08, sobre o qual fizemos a retrodição, era **inteiramente**
`sessions/boris/…` — sub-pool por agente, e por isso parou limpo aos 7,0 dias, com idade
máxima servida nunca alcançando 7,00 em oito dias. O lote de 21–22/08, sobre o qual
fizemos a predição, é `entities/%` + `lessons.md` — sub-pool **global**, janela de 30
dias. Aplicamos a janela de um canal a um lote do outro. **A retrodição era válida; a
extrapolação não era.** É o mesmo defeito de "verificar um invariante sobre o conjunto
errado" que o §6 cataloga, cometido desta vez sobre o próprio mecanismo que o paper
descreve.

**A atribuição por canal foi medida, não inferida.** A objeção decisiva a tudo acima é que
`brief_log` não registra a origem de cada serve, e uma regra de elegibilidade **exclui mas
não atribui**: os mesmos 108 serves seriam igualmente compatíveis com "a cobertura parou
aos 7 dias e o pool principal serviu tudo". O teste que separa as duas hipóteses não
precisa de coluna nova — basta rodar o **mesmo estado** duas vezes pelo código real, uma
com `freshSlots = 2` (produção) e outra com `freshSlots = 0`, e diferenciar. O que
desaparece ao desligar o canal é, por construção, o que o canal entregou.

Em 40 briefs de 29/08 (`CHANNEL-ATTRIBUTION-2026-08-29.json`): **80 slots** atribuídos à
cobertura — exatamente 2 por brief, os 40 —, **62 chunks distintos**, e **todos os 62 são
do lote de 21–22/08**. A cobertura *estava* servindo o lote aos 7,4 dias; a hipótese
alternativa está descartada por medição.

⚠️ **Sem esse teste, o argumento era assimétrico.** `brief_log`
**não registra por qual canal cada linha foi servida** — não há coluna de origem. Contar
serves de um lote mede a **união** do pool principal com o de cobertura, e o pool
principal não tem filtro de idade nenhum. Foi por isso que o guarda de corte acusou
"idade 7,42 servida" como violação da janela de 7 dias: parte daqueles serves nunca
esteve sujeita a janela alguma. Usar essa limitação para anular o guarda antigo sem
aplicá-la à explicação nova seria escolher a régua pelo resultado — e a explicação nova
sofria do mesmo viés de união até o teste diferencial acima existir.

**Por que isso é resultado e não nota de rodapé:** a renovação da superfície não é
governada por relevância nem pelo ranker. É governada por quais **caminhos de arquivo**
o canal foi configurado para enxergar — e o corpus cresceu para fora deles.

⚠️ **Uma armadilha de contagem, registrada porque quase nos pegou.** Contar exposição com
`JOIN chunks` faz 20/08 aparecer com 33 distintos onde `brief_log` diz 85 — os outros
**52 não existem mais** (servidos e apagados depois). Contagem de exposição sai de
`brief_log`; só o que precisa de metadado faz JOIN, e declara a perda.

#### 4.3.2 O outro canal também congela — pelo motivo oposto

Se o canal de cobertura falha por calendário e por álgebra, sobra a pergunta que a tese
precisa responder: **por que os outros 8 slots concentram?** Ali o score é a coordenada
dominante e um bônus aditivo não tem teto — logo a concentração não pode ser explicada
por surdez ao score. Ela tem outra causa, e é lida direto da fórmula.

`salience = 0,55·importância + 0,15·recência + 0,10·dor + 0,20·acesso`

Dos quatro termos, **três não decaem**. Importância e dor são estáticas. O termo de
acesso é `0,20 · log1p(access_count)/log(1000)` sobre um contador **monótono**: ele
sobe e nunca desce. Só a recência decai — e para um chunk velho ela já chegou ao piso e
deixou de diferenciar. Resultado: **o score de um chunk antigo e outrora popular é
monótono não-decrescente e fica permanentemente perto do seu teto.**

Os três chunks presentes em **100% dos 4.632 briefs** da semana são exatamente isso:

| chunk | tipo | importância | dor | `access_count` | último acesso | idade |
|---|---|---|---|---|---|---|
| 112241 | `team` | 0,80 | **1,00** | 414 | 2026-05-30 | 125 d |
| 116107 | `team` | 0,80 | **1,00** | 363 | 2026-07-29 | 125 d |
| 116467 | `team` | 0,80 | **1,00** | 911 | 2026-07-17 | 125 d |

**Foram acessados pela última vez há 90, 30 e 42 dias — e ganham todos os briefs de
hoje.** O topo do brief é um **fóssil do tráfego de busca de meses atrás**. E não é caso
isolado: dos 9.755 chunks com algum acesso, **7.908 (81%) estão há mais de 60 dias sem
serem acessados**, com o componente de acesso intacto.

📌 **E os três constantes são provavelmente do pool principal — provavelmente não: são,
por dedução.** O canal de cobertura ordena por `last_served ASC`. Um chunk servido no
brief anterior tem o `last_served` mais recente possível, logo fica no **fim** dessa
ordem, atrás de todo o estrato dos nunca-servidos. Um chunk presente em 4.632 de 4.632
briefs não pode ter sido escolhido por um comparador que prioriza o menos-recentemente-
servido. Isso decompõe a concentração entre os dois canais sem precisar de uma coluna de
posição no log — que não existe.

⚠️ **O laço de realimentação NÃO é fechado pelo sistema, e isso é decisão de desenho
deliberada.** `access_count` é incrementado apenas em `search.ts:396`, e o brief declara
no cabeçalho que é *"read-only sobre `chunks`; NÃO toca `access_count`"*. Então servir no
brief não aumenta a prioridade de nada — o que separa este caso do laço de realimentação
clássico de recomendação (Chaney et al.), em que a exposição se auto-reforça. Aqui a
exposição no brief **não** se auto-reforça; o que existe é uma **codificação permanente,
sem decaimento, de tráfego passado**. Se o laço se fecha, fecha pelo agente — que vê o
item e talvez volte a buscá-lo — e isso nós não medimos.

**A simetria que completa a tese.** Os dois canais da superfície congelam, por motivos
opostos e nenhum deles ligado a capacidade:

| canal | slots | por que congela | responde a ajuste de score? |
|---|---|---|---|
| pool principal | 8 | score determinístico com componente **monótono e sem decaimento** | **sim** — e ninguém ajusta |
| cobertura | 2 | população elegível de **108 chunks** (0,16% do corpus), esgotada 100% por dia; ordem **lexicográfica** | **não** — teto de 4,86% (§5) |

O canal que *poderia* ser corrigido por score é o que ninguém corrige; o que foi
desenhado para corrigir o outro é o que não responde a score. É por isso que a folga de
8,7× não vira cobertura.

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

### 4.5 O que estas medições **não** identificam

Seção obrigatória, e ela vem **antes** da discussão de propósito. O limite mais
importante é o primeiro, e ele vale para tudo que este paper reporta:

- **nada aqui diz que a exposição faltante importa.** Não há desfecho a jusante
  instrumentado: três tabelas de qualidade voltada ao agente com **0 linhas**; a
  telemetria de busca registra sobretudo a **sonda de saúde do cron** — em janela fechada
  de 7 dias, **325 de 343 linhas (94,8%)** caem nos dois minutos por hora em que o cron
  dispara, sobrando **2,6 linha/dia** atribuível a agente; e das 25 colunas dessa tabela,
  **16 não têm escritor** hoje, entre elas a única com identificação por chunk. Que
  83,78% do corpus nunca tenha chegado ao agente é fato sobre a **superfície**, não sobre
  a utilidade do que ficou de fora. Um leitor que conclua "o sistema está perdendo
  informação valiosa" foi além do que se mediu;
- **nada é randomizado, e nada precisa ser.** Este paper não estima efeito de
  intervenção. Toda comparação é descritiva ou dedutiva: a superfície é censo, e o teto
  do §5 é consequência do comparador verificada por replay. A estimação de efeito é o
  objeto do estudo interventivo, que **não** está reportado aqui (ver "Relação com o
  pré-registro");
- **um sistema, um corpus, um operador.** Os números de exposição são deste sistema. O
  que generaliza é o **método** e a forma do argumento — comparador lexicográfico impõe
  teto, e o teto depende da granularidade da chave —, não as porcentagens;
- **o estado de cobertura realimenta.** `last_served` não é congelado: servir em `T`
  altera a estrutura de estratos em `T+1`. Isso limita qualquer extrapolação do teto para
  regimes de tratamento sustentado.

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

**De onde vem `D`, e o que disso importa aqui.** O conjunto designado tem **19 chunks —
um por grupo de assinatura**, sorteados de uma população de 55 por regra com seed
declarada e precedência verificável sobre o beacon (Apêndice B). Para o que este paper
mede, `D` é apenas **um conjunto fixo e rederivável por terceiro**: um revisor
independente reproduziu os 19 usando só o beacon público e o CSV depositado. O critério
que selecionou os 55 é adjudicação de severidade por painel, e pertence ao estudo
interventivo (Apêndice C).

⚠️ **Um dos dois números do §5 herda essa proveniência e o outro não.** O bônus efetivo é
`W = w · Δ_cut · severity_pain`, então o rótulo do painel escala a dose **por chunk**:

- o **teto** (§5.3, §5.7) é medido com `w = 100.000`, dose em que o multiplicador satura
  junto com tudo. É **independente** do rótulo de severidade;
- a **banda de saturação** `(4,0; 4,4]` (§5.4) **não é**: ela localiza uma dose, e a dose
  efetiva de cada chunk depende do multiplicador. Lida como propriedade do comparador,
  ela seria mais geral do que é.

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

🔴 **E a tabela vale para o canal de cobertura, que são 2 dos 10 slots — não para a
superfície inteira.** Os outros 8 vêm do pool principal, ordenado por `salience` **pura**
(§2), onde um bônus aditivo age na coordenada dominante e **não tem teto**. Escrever "o
score não é alavanca" sem essa qualificação seria falso para 80% dos slots, e é uma
qualificação que o Abstract precisa carregar, não só esta seção.

A conclusão correta é mais estreita e continua valendo: **o canal que existe justamente
para dar chance ao não-servido é o único imune a ajustes de relevância.** A superfície
tem duas partes com álgebras diferentes, e a parte reservada à cobertura é a que não
responde ao score.

E é a mesma conclusão da §4 por outro caminho: naquele canal a exposição é governada por
capacidade e por ordem de rotação, não por relevância. A §4 mede isso na população de
chunks; a §5 prova por que nenhum ajuste de relevância poderia mudá-lo **ali**.

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

### 5.7 O teto de 4,86% é propriedade do FORMATO, não do comparador

A Proposição 1 diz que o bônus permuta dentro de um empate de `last_served` e nunca
atravessa. Disso segue, dedutivamente, que o teto de alcançabilidade não é propriedade
do comparador sozinho: é propriedade de **quantos empates o formato de `last_served`
produz**. E a resolução de `served_at` é herdada do `datetime('now')` do SQLite —
segundo. Ninguém a escolheu como parâmetro de desenho; ela é o default de uma função de
biblioteca.

O contrafactual que separa as duas coisas é o mesmo replay com a chave de estrato
truncada e reposta com zeros (`--granularidade`, em `replay-oportunidade.mjs`). Truncar
é cirúrgico aqui por um fato verificado no fonte: **`served_at` tem um único consumidor
vivo no serving**, a chave de estrato. O outro (`serveCounts`, janela do
novelty-penalty) está exportado e testado, mas nenhum caminho de produção o chama — é o
resto do mecanismo A, substituído por cobertura no tune de 06-26 (`brief.ts:588`).

| resolução de `served_at` | briefs que mudam | teto |
|---|---:|---:|
| **segundo — a de produção** | **17** / 350 | **4,86%** |
| minuto | 127 / 350 | 36,29% |
| hora | 281 / 350 | 80,29% |
| dia | 348 / 350 | 99,43% |

Corpus, designação, corte, dose e o conjunto dos 350 estados são **byte a byte os
mesmos** nas quatro linhas; o script consolidador aborta se qualquer um divergir, e a
granularidade nativa tem de reproduzir o `17/350` publicado antes de a tabela ser
emitida (as duas asserções foram testadas por mutação). Artefato:
`CEILING-GRANULARITY-2026-08-28.json`.

A intuição do porquê está no tamanho dos empates, e ela vem de **outra população** —
os 1.787 chunks já servidos alguma vez, sobre o histórico inteiro do `brief_log`, sem a
poda por brief que o replay aplica. Nessa população, truncar leva o número de estratos
distintos de **1.139** (segundo) para 951, 311 e 57, e o maior estrato de **14** para
61, 89 e 186. Os dois conjuntos de números respondem perguntas diferentes e não devem ser
lidos na mesma linha: um descreve a estrutura de empates do corpus servido, o outro conta
briefs que mudam no replay.

**A leitura, e o cuidado que ela exige.** Um mecanismo que alcança 4,86% dos briefs
alcançaria 36% se o sistema gravasse a hora com um campo a menos.

⚠️ Seria overclaim dizer que o teto é "um fato sobre a largura de um campo de texto". Ele
é fato sobre a razão entre **cadência de serving** e **resolução da chave**: são os
serves concentrados no mesmo segundo que criam os empates, e num sistema que servisse um
item por hora a mesma largura de campo não moveria quase nada. O que a medição estabelece
é que **um dos dois termos dessa razão foi herdado de um default** — a resolução vem do
`datetime('now')` do SQLite, não de decisão de desenho — e que mexer só nele desloca o
alcance do mecanismo em uma ordem de grandeza. Não isolamos os dois termos; fazê-lo
exigiria repetir a tabela sobre um corpus com cadência artificialmente espaçada.

#### 5.7.1 E o teto também depende de QUAL chunk o sorteio pegou

A regra de designação escolhe **um chunk por grupo de assinatura** por sorteio com seed
declarada. A escolha dentro do grupo é, por construção, arbitrária — então o `17/350`
pode ser propriedade do comparador ou acidente do sorteio, e a diferença importa para
como o número é lido.

Refizemos o mesmo replay com **oito designações alternativas**, geradas pela mesma regra
sobre a mesma população, variando só a seed. As seeds vêm de família derivada
deterministicamente de uma frase fixa no script — escolhê-las à mão permitiria pescar o
resultado, já que o beacon é público — e **todas as oito são reportadas**
(`CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json`):

| | mexem / 350 | teto |
|---|---:|---:|
| designação **em vigor** | **17** | **4,86%** |
| mínimo das oito alternativas | 17 | 4,86% |
| mediana | 20 | 5,71% |
| máximo | 26 | 7,43% |

A arbitrariedade é limitada por construção: **12 dos 19 grupos são unitários**, então
nenhuma seed pode mexer em mais de 7 designados.

**Duas leituras, e a segunda é desconfortável.** A primeira, que os dados aguentam: o
teto é **robusto em ordem de grandeza** — nove sorteios da mesma regra dão de 4,86% a
7,43%, e nenhum chega perto de mudar a conclusão de que o mecanismo alcança poucos por
cento dos briefs. A segunda: **a designação em vigor está no mínimo da distribuição** —
empatada com `sens-03`, que também dá 17, e não sozinha. Reportar `4,86%` como "o teto do
mecanismo" descreve o extremo, não a regra.

⚠️ **E até aí é preciso não exagerar.** Com 8 alternativas, a probabilidade de a
designação pré-especificada cair no posto 1 é ≈ 11% sob permutação: estar no mínimo **não
estabelece** que ela seja atípica. A mediana `5,71%` é ponto de n = 8, com desvio ≈ 2,9
estados — qualquer intervalo razoável cobre de 17 a 22, então a mediana **não** deve ser
lida como "o valor que a regra produz". O que se sustenta é mais simples e mais fraco:
onde este paper diz `4,86%`, leia-se *o teto sob a designação em vigor*, e o teto da regra
é uma **distribuição** que não medimos com precisão suficiente para resumir num número.

⚠️ E as alternativas não movem só *mais* briefs: elas movem **outros**. A interseção com
os 17 estados originais fica entre 9 e 14 (`estados_em_comum_com_a_publicada` no
artefato — é sobre **estados de replay**, não sobre quais chunks foram designados). Junto com o achado da granularidade — em que o
beneficiário troca de identidade ao mudar a resolução — o padrão é o mesmo: **qual chunk
recebe exposição é decidido por detalhes que ninguém escolheu como política.**

⚠️ Não medimos a interação entre os dois eixos (designação × granularidade); a tabela do
§5.7 é toda sob a designação em vigor, e esta é toda sob resolução de segundo.

⚠️ **Uma parte crescente desta tabela é decidida por um desempate que ninguém declarou.**
Truncar cria empates, e quando dois candidatos empatam em `last_served` **e** em
`salience`, o comparador não os separa — quem decide é a ordem de linha do SQLite. A
expressão de salience deste canal é grossa por construção
(`0,55·importance + 0,10·pain + 0,1 se access > 0`): entre os 108 elegíveis ela assume
apenas **seis valores distintos**. Medida a exposição
(`measurement/empates-por-granularidade.py`, `TIEBREAK-EXPOSURE-2026-08-29.json`):

| resolução | pares indistinguíveis | % dos pares | maior bloco |
|---|---:|---:|---:|
| **segundo — a de produção** | **68** | **1,18%** | 4 |
| minuto | 269 | 4,66% | 10 |
| hora | 917 | 15,87% | 33 |
| dia | 1.656 | 28,66% | 42 |

O contra-argumento natural — "os dois braços compartilham a mesma ordem arbitrária, logo
ela se cancela" — **não vale**: `churn` é diferença simétrica de dois conjuntos, e
permutar a ordem move os dois de maneira não correlacionada justamente na fronteira do
corte, onde o churn nasce e morre.

O que sobrevive e o que não: a **direção** e a **ordem de grandeza** do efeito, porque a
exposição cresce 24× enquanto o teto cresce 20×, e porque na resolução que este paper
efetivamente reporta ela é de **1,18% dos pares**. Os valores exatos das linhas
grosseiras — 127, 281, 348 — carregam um componente arbitrário que **não quantificamos**;
fazê-lo exigiria rerodar as 4×350 com uma terceira coordenada de desempate explícita, e
declaramos que não o fizemos.

⚠️ **Uma predição nossa morreu neste teste, e ela fica.** A nota de desenho dizia:
"coarsening só funde estratos, nunca divide ⇒ o teto é monótono não-decrescente, e essa
monotonia é o autoteste do instrumento". A contagem de fato sobe, mas os **conjuntos não
são aninhados** — 1 estado sai de segundo→minuto, 2 de minuto→hora. O erro é que fundir
estrato mexe também no braço de **controle**, e o churn é a diferença entre os dois
braços. Medidos, os três perdidos se dividem em mecanismos opostos:

- **redundância** — sob minuto, o designado passa a entrar **sozinho** no controle; a
  intervenção fica sem o que fazer;
- **inalcançabilidade** — sob hora, o estrato inteiro do designado desce abaixo do corte
  de seleção, e o bônus não atravessa estrato. É a Proposição 1 mordendo na direção
  contrária.

Logo a monotonia da contagem é empírica, não estrutural, e o consolidador a **reporta**
em vez de a exigir — um guarda que afirmasse aninhamento estaria errado e teria escondido
o achado. E o efeito não é só de quantidade: num dos estados o id que entra muda de
`308284` sob segundo para `308296` sob minuto. A resolução do timestamp decide também
**qual** chunk é beneficiado.

## 6. Defeitos de instrumento — e reportá-los é parte da contribuição

A contribuição declarada (v) **é o método**, então omitir isto tiraria do paper uma das
coisas que ele tem para dar. O catálogo integral tem **16** entradas e vive no Apêndice
E. Aqui ficam as **oito que mudaram um número que este paper reporta** — porque sem elas o
leitor não tem como auditar os números, e é esse o critério de corte, não o interesse da
lição.

⚠️ O critério exclui uma que seria a mais citável de todas: um `κ` agregado de **0,874**
reportado ao lado de uma estratificação que depende de outra fronteira, onde o painel
concorda apenas **0,31–0,53**. Ela não entra porque **não muda nenhum número deste
paper** — muda o estrato de análise do estudo interventivo, e vai reportada lá. Aplicar o
critério contra a lição de que mais gostamos é o que o torna critério.

| defeito | número que ele mudou |
|---|---|
| controle positivo rodado sobre pipeline **reimplementado** | produziu "dose absurda ⇒ efeito zero", que virou retratação central. O pipeline real dá **20** eventos |
| **teste de uma derivação sobre pool RECONSTRUÍDO** (`interleaveFresh` não é exportado) | classificou 25 estados como alteráveis contra 17 reais, e só **1 das 17** caía na classe; 24 violações do pressuposto de prefixo eram o sintoma. O teste válido usa só grandezas **registradas** (§5.6) |
| `served_at` com resolução de **segundo** e 6 agentes disparando em 1–2 s | **46,9%** dos briefs dividem o segundo; nenhum corte temporal reproduz o estado. Sob corte estrito o replay **inventa** 3 e **perde** 1 evento: desfecho sai **14 em vez de 12** (+16,7%) |
| grid grosso | saturação *pareceu* cair exatamente no topo da banda registrada; com 23 doses está em `(4,0 ; 4,4]` |
| telemetria de busca por chunk **muda** desde 2026-05-19 14:47:04, numa fronteira de deploy (buraco de 1h19 nas linhas, e nulo para sempre depois), **sem `CUT`** — a convenção deste projeto para retirada deliberada | comparação entre superfícies **dentro de janela** é impossível, e passou **3,3 meses** sem ninguém notar |
| **janela de um sub-pool aplicada a um lote do outro** | o §4.3.1 dizia que cada lote alimenta a cobertura por 7 dias e expira. São **dois** sub-pools: por agente (`sessions/%`, 7 d) e global (`entities/%` + `lessons.md`, **30 d**). O lote da retrodição era do primeiro, o da predição é do segundo. A predição datada **refutou** a seção, que foi substituída: o pool elegível é de **108 chunks (0,16% do corpus)** e é **esgotado 100% todo dia** |
| **`brief_log` não registra o canal que serviu cada linha** | contar serves de um lote mede a UNIÃO de cobertura com pool principal, e o principal não tem filtro de idade. Fez um guarda acusar "idade 7,42 servida" como violação de janela de 7 dias — serves que nunca estiveram sujeitos a janela alguma. Atribuição correta é por elegibilidade reconstruída do predicado |
| comparação de contagem **filtrada** com **não-filtrada** | inverteu o sinal de uma conclusão: 617×245 cumulativo vira 245×≥151 na janela comum |

O padrão que atravessa as oito, e que é o achado transferível: **cada uma passou por
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
  explicação~~ → **explicada** (§4.3.1), e a primeira explicação que demos foi **refutada
  por predição datada** antes de chegar ao depósito (§6). Não é quebra de regime: o pool
  elegível tem 108 chunks e é esgotado 100% por dia, então a diversidade diária mede
  **quando entrou material novo dentro dos padrões**, não rotação. Vira limite declarado:
  desfecho construído sobre diversidade diária é não-estacionário por dependência do
  calendário de ingestão, e uma janela sem ingestão nova mede zero por construção;
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

🔴 **E este paper não reivindica ser esse precedente**, porque não seria honesto. O
registro prospectivo que depositamos (OSF `yf7d2`) é de **outro estudo**: um crossover
randomizado sobre o **comportamento** do agente, que não rodou — as três tabelas que
mediriam desfecho a jusante estão vazias (§4.5). O que este manuscrito reporta é
**descritivo** e não foi pré-registrado.

O Apêndice A registra os desvios daquele registro assim mesmo, e a razão é estreita:
enquanto o depósito público existir afirmando coisas que a medição contradiz — inclusive
**duas que subestimam o próprio desenho** — deixá-las de pé é escolher que o erro
sobreviva. Isso é obrigação de correção, não credencial metodológica.

O que a ausência de vocabulário experimental no survey sustenta é mais modesto: não há
convenção estabelecida sobre o que declarar antes de intervir num sistema de memória
vivo, e nós descobrimos isso da forma cara.

📌 **Procedência desta seção.** MemoryArena e Evo-Memory foram lidos **integralmente**
em 15/08 (`RELATED-WORK.md` §4 e §4.1); o survey, integralmente em 13/08, com as
contagens recomputadas em 28/08 sobre o PDF pinado por sha256. Os trabalhos de
recomendação da §8.2 foram lidos em **resumo e metadados**, não em texto integral —
declaro porque a afirmação que faço sobre eles é sobre a **pressuposição de
monotonicidade**, e essa é uma afirmação que texto integral poderia refinar.

## 9. Discussão

Três afirmações, e nenhuma além.

**Primeira: a não-exposição deste sistema é resultado de política, não de capacidade.**
É a afirmação que a medição inverteu em relação à hipótese com que começamos, e ela é
falsificável por uma razão simples: **`slots / distintos`**. Sob gargalo de capacidade
essa razão fica perto de 1 — cada slot mostra algo novo até o corpus esgotar. Sob
gargalo de política, ela cresce sem limite. Medimos **325**. Não há aqui restrição
física a remover; há uma ordenação que revisita.

⚠️ A objeção correta a isso é que os slots não são fungíveis: a superfície entrega 10
por sessão, e nada garante que uma sessão tolere mais de 10. Verdade — e a alegação não
depende disso. Mostrar **dez itens diferentes** por sessão nunca violaria o limite de
dez; o que falta não é tamanho de sessão, é **rotação entre sessões** (§4.1.1). Isso muda o
que se pode pedir: enquanto a superfície parece pequena, "expor mais" é um pedido
impossível; medida a folga, é um pedido de **desenho**.

⚠️ E não decorre disso que a política esteja errada. Uma superfície de 10 itens tem de
concentrar, e servir uniformemente destruiria o valor dela. O que decorre é que a
fronteira entre "o que o agente vê" e "o que existe" foi **escolhida**, quase sempre sem
que ninguém a escolhesse explicitamente — `freshSlots = 2` é default de configuração sem
override, e os dois padrões de `GLOBAL_FRESH_PATTERNS` recortam 0,16% do corpus de um
jeito que nenhum documento de desenho previu.

**Segunda: os dois canais congelam, e a assimetria entre eles é o achado.** O de
cobertura — 2 dos 10 slots — falha por **população**: 108 elegíveis num corpus de 67.187,
com zero nunca-servidos restando e 12,4 slots por candidato
e por ser **estruturalmente surdo ao score**, com **teto analítico** de 4,86% derivável
do código antes de qualquer experimento. O pool principal — os outros 8 — falha pelo
motivo contrário: ali o score **é** a coordenada dominante, e três dos seus quatro termos
**não decaem**. O componente de acesso é monótono num contador que só sobe, de modo que o
topo do brief é um fóssil de tráfego de busca de meses atrás (último acesso há 90, 30 e
42 dias, em chunks que ganham 4.632 de 4.632 briefs).

**O canal que responderia a ajuste de score é o que ninguém ajusta; o desenhado para
corrigir o outro é o que não responde a score.** É essa tesoura, e não a capacidade, que
produz os 2,66%.

⚠️ E vale distinguir isto do laço de realimentação clássico de recomendação: aqui a
exposição no brief **não** se auto-reforça — `access_count` só é incrementado pela busca,
e o brief é declaradamente read-only sobre ele. O que existe não é um laço, é uma
**codificação permanente e sem decaimento de tráfego passado**.

A consequência de desenho é desconfortável e vale dizer inteira: **projetamos uma
intervenção cujo teto era derivável do código antes de ela ser implantada.** Quem for
intervir num ranker deveria ler o comparador primeiro e perguntar *em que coordenada
minha alavanca age*; custa uma tarde e economiza uma rodada experimental.

**Terceira: nada disto é visível pelas métricas que a área usa** — e essa é a única
afirmação que passa deste sistema para fora, porque é sobre o **instrumento**, não sobre
o resultado. nDCG e recall são condicionais a uma query ter sido feita; um item que
nenhuma query alcança e nenhum brief inclui não tem score baixo, tem score **indefinido**.
Medir a superfície de entrega exige o sistema em operação e um registro por item do que
foi servido — que este sistema quase não tinha: **16 colunas de telemetria sem escritor**,
em seis instantes distintos, uma delas exatamente a que registrava quais chunks a busca
devolveu (§6).

⚠️ **O que não afirmamos.** Que a área otimiza a coordenada errada: é **um** sistema, e a
única generalização que fazemos é dedutiva — para qualquer ranker com ordem lexicográfica
e bônus na coordenada subordinada, o teto existe. Quantos sistemas têm essa forma é
pergunta em aberto, e é para respondê-la que o diagnóstico está publicado. Que 83,78% de
não-exposição seja *ruim*: parte do corpus é log, e log não precisa ser lido para ser
útil — o número estabelece a **escala** da população que nenhuma métrica de recuperação
alcança, não um prejuízo. E que a exposição mude o comportamento do agente: não medimos.

## Apêndice A — Relação com o pré-registro

Há um pré-registro público (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`) e **este paper
não é o estudo que ele registra.** O registro cobre um estudo **interventivo** — designar
chunks, servir uma dose, estimar efeito — que no fechamento deste manuscrito **não havia
começado**: o serving nunca saiu de shadow e nenhuma alocação de braço foi emitida. Os
resultados interventivos serão reportados separadamente.

O que este paper reporta são as medições feitas **enquanto** aquele estudo era construído:
a superfície, o carrossel, o mecanismo e seu teto. Elas não estavam pré-registradas, e
dizê-lo é a única forma honesta de apresentá-las — são **exploratórias e descritivas**,
não confirmatórias.

⚠️ **Três coisas que medimos aqui contradizem o registro, e vão ditas aqui porque o
registro é público e alguém vai cruzar os dois:**

| o registro afirma | o que se mediu | direção |
|---|---|---|
| `Δ_cut = 0,043` é *"the measured salience spread at the brief cut"* | **não existe cut**: o código não aplica limiar. O comparador é lexicográfico e `salience` só desempata `last_served` idêntico (§5.1) | ⬆ o registro promete mais |
| a banda `{2 · 4 · 7,5}` está entre *"what does not move, and could not"* | **move**: 11 / 15 / 17 estados de 350, monótono, com saturação em `(4,0 ; 4,4]` (§5.4) | ⬇ o registro promete **menos** |
| *(v1.12 §5)* a designação é defeito **aberto** | **fechada** em 26/08 20:28Z, com precedência verificável de 1.056 s sobre a rodada drand (Apêndice B) | ⬇ o registro promete **menos** |

**As duas linhas ⬇ são as que importam**, porque ninguém corrige sozinho um erro que o
favorece: o registro afirma que um parâmetro **não** tem efeito quando tem, e que um
defeito está **aberto** quando foi fechado.

⚠️ E a linha da banda mudou de status por **defeito de instrumento nosso**, não por dado
novo: o controle positivo que produziu o *"não move"* rodava sobre um pool
**reimplementado**. É matéria do §5.6, não nota de rodapé.

A lista íntegra de desvios — inclusive os que só afetam o estudo interventivo, como a
migração do estrato de análise de `S2` para `≥ S1` por concordância do painel — vive em
`DEVIATIONS-FOR-PAPER.md` e pertence ao paper interventivo.

## Apêndice B — Cadeia da designação

Sorteio com seed declarada: rodada drand quicknet **31657512** (emissão 20:25:00Z),
declaração pushada **20:07:24Z** — **1.056 s** de precedência, com a rodada devolvendo
HTTP 425 no momento da escrita. Um revisor independente rederivou o conjunto designado
usando **apenas** o beacon público e o CSV depositado.

## Apêndice C — O painel, e por que ele não está aqui

A população de 55 chunks em 19 grupos vem de `p2_verdict`, produto de um painel de
adjudicação de severidade de 3 famílias. O painel, sua concordância por fronteira e o
parâmetro de taxa que ele estima pertencem ao **estudo interventivo** e são reportados lá
— inclusive o achado de que um `κ` agregado de 0,874 escondia concordância de apenas
0,31–0,53 na fronteira `≥ S2`, contra 0,87–0,93 em `≥ S1`.

Para o que **este** paper reporta, o painel entra de um jeito só: ele fixou uma população.
Os 19 designados são **um conjunto fixo e publicamente rederivável** (Apêndice B), e é
tudo de que o §5 precisa. Ver a ressalva do §5.1 sobre qual dos dois números do §5 depende
do rótulo de severidade e qual não depende.

## Apêndice D — Artefatos

Tudo em `measurement/`, com `--assert-json` travando cada número citado:

| o quê | script | artefato |
|---|---|---|
| superfície de exposição | `superficie-de-exposicao.py` | `out/superficie.json` |
| replay + dose + limiar + gaps | `replay-oportunidade.mjs` · `replay-resumo.py` | `out/c-350-v3.json` · `out/dose-350-v3.json` · `out/limiar-17.json` · `out/gaps.json` |
| granularidade do teto (§5.7) | `replay-oportunidade.mjs --granularidade` · `granularidade-do-teto.py` | `out/gran-{seg,min,hora,dia}.json` · `out/gran3-{seg,min,hora}.json` · `CEILING-GRANULARITY-2026-08-28.json` |
| exposição a desempate arbitrário (§5.7) | `empates-por-granularidade.py` | `TIEBREAK-EXPOSURE-2026-08-29.json` |
| sensibilidade do teto à designação (§5.7.1) | `sensibilidade-da-designacao.py` | `out/sens-*.json` · `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json` |
| pool elegível do canal de cobertura (§4.3.1) | `pool-elegivel.py` | `POOL-ELEGIVEL-2026-08-28.json` |
| atribuição diferencial por canal (§4.3.1) | `replay-oportunidade.mjs --modo canal` | `CHANNEL-ATTRIBUTION-2026-08-29.json` |
| ciclo do lote, e a predição refutada (§4.3.1, §6) | `ciclo-do-lote.py` · `regime-cobertura.py` | `BATCH-CYCLE-2026-08-28.json` · `BATCH-CYCLE-2026-08-29.json` · `PREDICTION-2026-08-29.md` |
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
