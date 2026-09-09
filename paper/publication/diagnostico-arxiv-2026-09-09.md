# O que o Paper 1 tem de diferente dos papers que o arXiv aceitou — medido

> Levantamento de 2026-09-09. Comparação do nosso manuscrito contra a população de
> papers de *agent memory* efetivamente aceitos no arXiv em 2026, medida por script
> sobre os HTML canônicos (`arxiv.org/html/<id>`) e sobre a API de metadados.
>
> ⚠️ **Delimitação que a leitura deste documento exige.** A recusa de 2026-09-03
> (`submit/7771319`) **não trouxe feedback item-a-item** — o texto foi *"would benefit
> from additional review and revision that is outside of the services we provide"*.
> Nada aqui é a razão da recusa; é a lista das diferenças **mensuráveis** entre o nosso
> artefato e os aceitos. Um diff que *explica* um efeito não é prova de que o *causou*.
> O que se pode afirmar: cada item abaixo é um lugar em que somos outlier, e vários são
> defeitos independentes da recusa — valem conserto de todo jeito.

---

## 1. A hipótese do perfil segue morta — mas por um caso mais fraco do que eu escrevi primeiro

🔴 **Correção de uma medição minha, feita antes de publicar este documento.** A primeira
versão desta seção afirmava que o **MemMachine tem 1 autor sem afiliação** e concluía
"é exatamente o nosso perfil, e foi aceito". **Falso.** O regex que eu usei sobre o HTML
capturava só o **primeiro** `ltx_personname` e eu imprimi `au[0]`. Conferido nas duas
fontes independentes (API de metadados e HTML), o MemMachine tem **7 autores**: Shu Wang,
Edwin Yu, Oscar Love, Tom Zhang, Tom Wong, Steve Scargall, Charles Fan. É um time de
indústria, não um autor solo.

O que **sobra** medido, e ainda serve:

| paper aceito | autores | afiliação |
|---|---:|---|
| MemMachine (`2604.04853`) — *system paper*, 18 pág. | **7** | time de indústria |
| **MERIT** (`2609.05441`) — benchmark + harness | **2** | 🔑 **"Independent Research"**, e-mails gmail, nenhuma instituição |
| Human-Inspired Memory Architecture (`2605.08538`) — 10 pág. | 5 | não declarada no metadata |
| Theoria (`2607.16848`) — 40 pág. | 3 | não declarada no metadata |

⇒ **Autores sem nenhuma afiliação institucional entram** (MERIT, com dois gmails e o
rótulo literal "Independent Research"). Isso é o que a hipótese do perfil precisava
sobreviver, e não sobrevive. Somado ao que a pesquisa de 09-03 já havia estabelecido —
Dernoncourt, com 166 papers no arXiv, e Jian Pei receberam o **mesmo template** de recusa
— a conclusão é a mesma de antes: **afiliação e histórico não são o filtro.**

⚠️ O que eu **não** posso afirmar, e a primeira versão afirmava: que um *system paper*
de autor solo sem afiliação foi aceito neste recorte. Nenhum dos quatro é isso.

---

## 2. A régua, medida

Prosa contada com blocos de código e linhas de tabela removidos, para não inflar o
nosso número com as 354 linhas de tabela que ele tem.

| | **nosso** | MemMachine | MERIT | Human-Insp. | Theoria |
|---|---:|---:|---:|---:|---:|
| palavras de prosa | **22.255** | 10.724 | 6.662 | 5.787 | 18.956 |
| seções de topo | **18** | 11 | 8 | — | — |
| subseções | **49** | — | — | — | — |
| apêndices | **7** | **0** | **0** | — | — |
| **referências** | **7** | 21 | 16 | 11 | 51 |
| **refs / 1.000 palavras** | **0,31** | 1,96 | 2,40 | 1,90 | 2,69 |
| arXiv IDs citados | **2** | 12 | 17 | 1 | 42 |
| ocorrências de "SOTA" | 20 | 0 | 0 | — | — |
| "state-of-the-art" | 5 | 1 | 0 | — | — |
| "outperform" | 8 | 7 | 0 | — | — |
| "outperform" **por mil palavras** | **0,36** | **0,65** | 0 | — | — |

⚠️ As três linhas de linguagem **não** são um déficit nosso — ao serem lidas em contexto
elas se invertem. Ver §2.3, que corrige a leitura que eu mesmo havia feito delas.

### 2.1 O outlier que se vê em dez segundos: a bibliografia

**Sete referências.** E a composição é pior que o número:

| footnote | o que é |
|---|---|
| `[^mem0]` | link de repo GitHub |
| `[^letta]` | link de repo GitHub |
| `[^zep]` | link de repo GitHub |
| `[^everos]` | link de repo GitHub |
| `[^lightrag]` | **paper** (EMNLP 2025) |
| `[^memo]` | **paper** (arXiv 2605.15156v2) |
| `[^hipporag2]` | 🔴 **sem localizador nenhum** — nem arXiv ID, nem URL, nem venue |

⇒ Dois papers de verdade, quatro repos, e uma entrada que não permite ao leitor achar o
trabalho citado. Estamos **6 a 8 vezes abaixo** do aceito menos citante em
referências-por-palavra. Num campo cujo survey canônico (`2602.06052`, TMLR 07/2026)
cataloga **218 papers**, um manuscrito de 22 mil palavras com 7 referências é, para
quem lê rápido, indistinguível de documentação de produto — independentemente da
qualidade do que está medido dentro.

Isto é o item mais barato de consertar e o de maior efeito: a vizinhança já está mapeada
em `EXTERNAL-REFERENCES.md` e na memória (`project_agent_memory_survey_tmlr_2602_06052`
lista Evo-Memory `2511.20857`, LifelongAgentBench `2505.11942`, OdysseyBench
`2508.09124`, InterruptBench `2604.00892`, HaluMem `2511.03506`, MemoryArena
`2602.16313`), e o levantamento de hoje acrescenta ~25 IDs de 2025-2026 que ainda não
são citados em lugar nenhum.

### 2.2 Os apêndices: nós temos 7, os aceitos têm 0

Os nossos são `A. Knowledge Graph v2`, `B. Cross-Agent Intelligence`, `C. MCP Server
Interface`, `D. HTTP API Server`, `E. Operational Infrastructure` (cron schedule, backup
strategy, LLM fallback chain), `F. Dashboard Integration`, `G. Evolution History`.

**Os apêndices C, D, E e F são documentação de operação, não material experimental.**
Listagem de endpoints HTTP, tabela de cron, estratégia de backup e integração de
dashboard são coisas que um leitor procura num README. Nos aceitos, apêndice — quando
existe — carrega prompt, hiperparâmetro e tabela extra; MemMachine e MERIT não têm
nenhum. `G. Evolution History` (v1.0 → v3.6d) é changelog.

### 2.3 A linguagem de alegação — o achado se inverteu ao ser conferido

🔴 **A primeira versão desta seção estava errada e a correção importa.** Eu havia
contado **20 ocorrências de "SOTA"** contra 0 em MemMachine e 0 em MERIT, e concluído
"densidade de alegação alta". Ao ler os 20 contextos, a leitura não se sustenta: a
esmagadora maioria é **ressalva**, não alegação —

> *"roughly 10-12 pp below current SOTA (Beam Retrieval)"* · *"The backbones differ, and
> the deltas are **not SOTA claims**"* · *"competent, with headroom"* · *"§5.2 now states
> them as competent-but-below"* · *"below Mem0 SOTA 66.88%"*

A palavra aparece muito porque o paper insiste em dizer **onde ele perde**. E na régua
de assertividade o resultado inverte: **"outperform" aparece 8× em 22.255 palavras nossas
(0,36 por mil) contra 7× em 10.724 do MemMachine (0,65 por mil)** — somos quase **duas
vezes menos** assertivos por palavra que o system paper aceito. Contar palavra sem ler o
contexto é a classe *número certo atribuído à população errada*, e eu caí nela aqui.

**O que sobra como defeito real, e é pouco:**

- §5.7.1: *"no published competitor reports retrieval latency in this band"* — universal
  não verificável sobre a literatura inteira. Este é o pior da lista.
- §5.7.1: *"Zep markets <100 ms p50, unverified independently"* — compara **nossa
  medição** contra o **material de marketing** do competidor, declarando que não
  verificou. Ou se verifica, ou se retira a comparação.
- "breakthrough" (3×) como rótulo de resultado (§5.5). Cosmético.

⚠️ E nada disto é o defeito das alegações **falsas** de SOTA já retiradas em 09-01/09-03
(MuSiQue 58,62 → 69,2; HotPotQA 73,37 → 85,04, corrigidas contra o fonte primário).
Aquelas eram números errados; estas são frases mal-formadas, e são três.

---

## 3. Defeitos internos, medidos hoje — estes valem conserto independente do arXiv

### 3.1 🔴 O mesmo "~95k" atribuído a duas populações diferentes, e uma referência cruzada que não existe

Quatro tamanhos de corpus aparecem no manuscrito:

| onde | número | estado |
|---|---:|---|
| §2.4 | 1.481 chunks | *"initial-deployment snapshot, March 2026"* — ✅ **datado** |
| §5.1 | 69.000 (implícito de 67.949 = 98,48%) | corpus do backfill, maio — datável pelo PR |
| §5.7.1 | 69k → 70,7k | *"as the corpus grew"*, junho |
| §2.4 | **"the main store has since grown to ~95k chunks — see Abstract"** | 🔴 sem data |
| §7.1 L3 | **"~95k chunks across 7 databases … as of 2026-06-04"** | ✅ datado |

**Dois defeitos distintos, e o primeiro é o mais sério:**

**(a) O mesmo número, duas populações.** §2.4 atribui ~95k ao **main store**; §7.1 L3
atribui ~95k à **soma dos 7 bancos**. No máximo uma das duas pode estar certa, porque
as populações não são a mesma coisa. Medido em 2026-09-09:

| população | chunks |
|---|---:|
| main store (`workspace/tools/nox-mem/nox-mem.db`) | **67.724** |
| soma dos 7 bancos (main + atlas 1.054 + boris 1.422 + cipher 3.090 + forge 1.894 + lex 426 + nox 3.610) | **79.220** |

Diferença de 11.496 chunks. É a classe *número certo atribuído à população errada* — o
número pode ter sido medido corretamente uma vez, e a frase que o carrega diz de qual
conjunto ele é, em duas versões incompatíveis.

**(b) A referência cruzada de §2.4 não resolve.** Ela manda *"see Abstract"*, e o
Abstract **não traz nenhuma contagem de corpus** (conferido: só menciona "six
specialized agents", latência, custo e RSS). O leitor que segue o ponteiro não acha o
número.

⚠️ **O que NÃO é defeito:** o L3 está **datado** (`as of 2026-06-04`) e, como afirmação
histórica, é defensável — a discrepância com hoje é o corpus ter **encolhido** pela
deduplicação de junho (100,5k → 71,6k) e pela limpeza de skills aposentadas (−5,6k).
Um paper pode reportar o corpus do momento da medição. O que ele não pode é ter a mesma
grandeza sem data em §2.4, e apontando para onde ela não está.

Conserto: fixar **um** corpus de medição, dizer qual população é, e datá-lo em toda
menção.

### 3.2 🔴 Um número de latência que o próprio paper contradiz

§5.7.1 traz **tabela com KG p50 = 2,5 ms** e, no parágrafo seguinte, *"Re-validated
2026-06-15 … p50 = 2,9 ms"*. O abstract usa **2,9 ms**. A tabela não está marcada como
superada. Dois valores para a mesma grandeza no mesmo parágrafo é a primeira coisa que
um revisor circula.

### 3.3 🔴 Contagem de entity files defasada

§5.1.3 afirma *"769 entity files × 3 sections ~ 2.307 boost-bearing chunks"* e atribui a
elas a maioria do ganho da headline. Medido hoje:

| grandeza | no paper | medido 2026-09-09 |
|---|---:|---:|
| entity files | 769 | **184** (em `memory/entities/**/*.md`) |
| `source_file` distintos com `section` não-nula | — | 239 |
| chunks `compiled` | — | 239 |
| chunks `frontmatter` | — | 239 |
| chunks `timeline` | — | 387 |
| **chunks com `section`** | **~2.307** | **865** |

865 contra 2.307, e 184 arquivos contra 769 — queda de ~4×, consistente com a limpeza de
skills aposentadas de junho. O mecanismo da headline (`section_boost` explica 99,85% de
A8) está apoiado nesse volume, então o número não é decorativo: se for remedido no corpus
de hoje, a força do argumento muda. Datar ou remedir — não deixar como está.

### 3.4 🟡 Três de cinco competidores não rodaram

§6.2 lista Mem0, Zep, Letta, agentmemory e EverMind. O abstract declara com honestidade:
*"two produced head-to-head quality numbers and three were documented deployment
non-runs"*. As razões estão na tabela: Zep = `[GAP — Docker unavailable on pod]`,
EverMind = `[GAP — keys/auth]`.

A declaração é correta e está no lugar certo. O problema é o que sobra: **uma comparação
"cross-system" com n=2 competidores**, um deles (Mem0) já com Chroma trocado por faiss
para contornar um thread-leak. Os aceitos comparam contra 3 (MERIT), 8 (Theoria), ou
5 estratégias sob condições idênticas (AgentMemBench). "Docker indisponível no pod" é
uma limitação de infraestrutura nossa, não uma propriedade do competidor — e um revisor
vai perguntar por que não se rodou em outra máquina.

⚠️ **Isto é o item mais caro da lista e o único que exige medição nova.** Ele não se
resolve escrevendo melhor.

### 3.5 🟡 Referências internas que o leitor não pode resolver

A seção `Internal references` aponta para números de PR e para
`docs/COMPETITIVE-ANALYSIS-2026-05-19.md`. O repo é público, então não é irresolúvel —
mas um paper que sustenta afirmação em "PR #150" está pedindo ao revisor que navegue um
histórico de commits. O que se cita num paper é o artefato versionado com DOI, e ele
existe: `10.5281/zenodo.22649269`.

---

## 4. O que consertar, em ordem de razão-benefício

| # | conserto | custo | o que muda |
|---|---|---|---|
| 1 | **Bibliografia: 7 → 35-50 referências reais**, com a vizinhança de 2025-2026 citada e discutida em Related Work. Dar localizador ao `[^hipporag2]` ou tirá-lo. | baixo | tira o sinal mais visível de "não é paper". É o item de maior efeito por hora gasta |
| 2 | **Datar ou remedir os quatro números de corpus** (§3.1), a latência dupla (§3.2) e os entity files (§3.3). Fixar **um** corpus de medição declarado. | baixo | mata três defeitos que um revisor acha em 10 min |
| 3 | **Cortar os apêndices C, D, E, F, G** para o repo/Zenodo, deixando no paper só o que é experimental (A e B, se sustentarem). | baixo | −4 apêndices de documentação; aproxima da forma aceita |
| 4 | **Corrigir três frases, não a densidade** (§2.3): o universal *"no published competitor reports…"*, a comparação contra o marketing do Zep, e os 3 "breakthrough". **Não** mexer nas 20 "SOTA" — são ressalvas, e são o diferencial. | trivial | tira as únicas frases que um revisor pode chamar de infundadas |
| 5 | **Reestruturar para a forma canônica**, que é a mesma nos quatro aceitos: Introduction · Related Work · Method · Experimental Setup · Results · Discussion · **Limitations and Threats to Validity** · Conclusion. Hoje temos 18 seções de topo e 49 subseções; o alvo é 8-11 e ~10-12 mil palavras de prosa. | **médio-alto** | é o corte que transforma um relatório de engenharia num paper |
| 6 | **Rodar Zep e EverMind de verdade**, em máquina com Docker, e refazer §6 com 4-5 competidores. | **alto** | é o único item que muda a força da evidência, não a forma dela |

⚠️ **A ordem não é a ordem de importância.** O item 6 é o que um revisor de journal vai
cobrar primeiro; os itens 1-4 são o que faz o manuscrito parar de parecer outra coisa.
Se o destino for **TMLR** (a rota decidida, porque a apelação no arXiv é de uso único e
só se abre com publicação em journal convencional), os dois conjuntos são necessários —
e o item 5 já estava previsto no escopo decidido em 07-09: *§6 como espinha, §5.1 como
mecanismo, construído sobre o `rc4` apenas*, com a ausência de artefato da corrida
canônica declarada.

---

## 5. O que NÃO mexer — é diferencial, e os aceitos não têm

Medido no mesmo levantamento: nenhum dos quatro papers aceitos tem qualquer destes.

- **Pré-registro da comparação** (§6.7) com declaração anti-cherry-pick (§6.6). O survey
  TMLR tem **zero** ocorrências de "pre-registration" em 54 páginas e 218 papers.
- **Protocolo de 5 batches com IC 95% e limiar de alegação** (§5.8.1), mais a medição de
  que gate de batch único **superestima efeito 3-6×** (§5.8.2), com a tabela dos próprios
  overclaims que o protocolo evitou. Isso é metodologia publicável por si.
- **Três achados que contrariam a própria headline**, no abstract: pain não é
  significativo isolado; `section_boost`, não pain, é o driver dominante; F_MH em 3-7%.
- **Limitações L1-L8** nomeadas e específicas, incluindo L6 ("a comparação cross-system é
  metodologicamente parcial").

Este material é mais rigoroso que a média do que foi aceito. O problema do manuscrito
nunca foi excesso de otimismo — é que a forma esconde o rigor.

---

## 6. Procedência de cada número deste documento

| número | de onde |
|---|---|
| palavras/refs/seções dos aceitos | script sobre `arxiv.org/html/<id>`, contando `ltx_bibitem` e `ltx_title_section` |
| autores e afiliações | `export.arxiv.org/api/query`, campos `author` e `comment`, **cruzado** com todos os `ltx_personname` do HTML |
| palavras/refs/seções do nosso | script sobre `paper/paper-tecnico-nox-mem.md`, com blocos de código e linhas de tabela removidos |
| 67.724 chunks, 865 com section, 3,92% tier core | `SELECT` no banco **vivo** `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`, 2026-09-09 |
| 67.187 chunks servidos, `MAX(created_at)=2026-08-24` | snapshot `corpus-SERVING-REAL-e20260903-recuperado.db` — o corpus que o serving lê pelo `fd`, congelado desde 03/09 |

### 6.1 Duas medições minhas que estavam erradas, e como cada uma foi pega

Ficam registradas porque a classe se repete e o registro é o que impede a terceira vez.

| erro | como apareceu | o que o pegou |
|---|---|---|
| **"MemMachine tem 1 autor"** | `re.findall` devolve todos os nomes; eu imprimi `au[0]` e li como "o autor". Sustentava a frase mais forte do documento | cruzar com a **API de metadados**, que devolve `author` como lista. Duas fontes para a mesma grandeza |
| **"densidade de alegação alta: 20× SOTA"** | contagem correta, caracterização errada — quase toda ocorrência é *ressalva* (*"below current SOTA"*, *"not SOTA claims"*) | **ler os 20 contextos** em vez de confiar no contador. E normalizar por palavra, o que inverteu o sinal em "outperform" |

Nas duas, o número estava certo e a frase que o carregava estava errada. É a classe
*número certo atribuído à população errada*, duas vezes em um documento — e as duas
foram pegas por olhar a mesma grandeza por uma segunda via.

⚠️ **Os dois últimos são grandezas diferentes e o paper precisa dizer qual usa.** Até o
realinhamento de 2026-09-10 09:00Z, o `nox-mem-api` serve de um snapshot congelado: o
banco vivo tem 67.724 chunks e o corpus **servido** tem 67.187, com o mais recente de
2026-08-24. Qualquer frase do tipo "o sistema em operação indexa N chunks" medida entre
03/09 e o realinhamento tem de declarar de qual dos dois saiu. Ver
`DEVIATIONS-FOR-PAPER.md` §10.10 e §10.11.
