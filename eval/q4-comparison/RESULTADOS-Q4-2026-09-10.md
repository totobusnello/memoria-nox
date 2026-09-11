# Q4 head-to-head — peça (a), evidência

> **Escopo.** Este arquivo é a **peça (a)** do §6: tabela, recibo e número,
> autossuficientes. A prosa explicativa — peça (b) — vive no manuscrito e é da
> sessão que redige. A separação existe para que um corte futuro no texto não
> leve a medição com ele.
>
> **Estado:** ingestões fechadas nas quatro colunas; buscas do Zep e do EverOS
> em curso em 2026-09-10. As células de nDCG estão marcadas `PENDENTE` e **não
> devem ser preenchidas por estimativa**.

## 1. Corpus e queries — idênticos nas quatro colunas

| grandeza | valor |
|---|---|
| linhas do corpus | **6.830** (`cache/locomo.jsonl` 5.882 + `cache/longmemeval.jsonl` 948) |
| ids distintos | **6.822** — 8 ids nomeiam **dois documentos diferentes** cada |
| `corpus_sha256` | `d150c703e3dd2d39ee067d6ad3b7c87f34447b86972758fb72b3a23618e32908` |
| queries | **2.482** (`cache/queries-rc4-all.jsonl`: 1.982 locomo + 500 longmemeval) |
| hash do arquivo de queries | `4993e9ebd09211ef…` (16 primeiros), 593.578 bytes |
| queries com gold num id ambíguo | **10 de 2.482 (0,40%)** |
| golds sem documento | **0** |

⚠️ O `corpus_sha256` é sobre os **bytes concatenados** dos dois arquivos em ordem
lexicográfica de caminho, não sobre o JSON reserializado.

### 1.1 As duas metades diferem 40× em tamanho por documento

| arquivo | linhas | média de caracteres por documento |
|---|---|---|
| `locomo.jsonl` | 5.882 | **356** |
| `longmemeval.jsonl` | 948 | **14.410** |

⇒ Qualquer custo ou latência **por documento** tem de ser reportado **por
metade**. Agregado, o número é dominado pelos 5.882 pequenos e subdeclara o
custo dos grandes em ~40×. Medido na ingestão do EverOS: 1,73 s/doc na metade
LoCoMo contra 5,0–6,7 s/doc na metade LongMemEval, com a **média cumulativa**
do recibo a marcar 2,03 s/doc e um ETA cego à mudança de regime.

## 2. Retenção por adapter — o denominador não é o mesmo nas quatro

> 🔴 **A coluna `corrida` não é decoração.** As quatro medições vêm de **duas
> populações**: nox-mem e mem0 são do **rc4** (2026-06-29), EverOS e Zep são da
> corrida de **2026-09-10**. Juntá-las numa tabela sem nomear a corrida por
> linha convida a ler o 6.822 do EverOS como número do rc4 — e foi o que a
> minha primeira versão desta tabela fez. Comparar mecanismos entre corridas é
> legítimo; atribuir os números à mesma população não é.

| coluna | corrida | retenção | mecanismo | como foi medida |
|---|---|---|---|---|
| nox-mem | **rc4**, 2026-06-29 | **6.822** | `INSERT OR IGNORE INTO eval_chunks(id,…)` | contagem na tabela |
| mem0 | **rc4**, 2026-06-29 | **6.830** | sem dedupe (6.822 `chunk_id` distintos) | contagem no store |
| **EverOS** | **2026-09-10** | **6.822** | `DuplicateDocumentError` no 2º write do id | `SELECT COUNT(*) FROM knowledge_documents` **após o sync final** |
| **Zep** | **2026-09-10** | **6.830** | sem dedupe | `COUNT(*)` em `message` no Postgres (`-U zep -d zep`; 6.830 linhas e 6.830 em `message_embedding`) |

⇒ **Dois sistemas, dois mecanismos, um número.** O EverOS chega ao mesmo 6.822
do nox-mem por caminho **diferente** — erro explícito em vez de ignorar em
silêncio — o que faz de 6.822 a consequência de **honrar a unicidade do id**, e
não idiossincrasia do nosso loader.

⚠️ Isto **não** diminui a assimetria do rc4: lá, dentro da mesma corrida, o
nox-mem retinha 6.822 contra os 6.830 do mem0, e essa comparação continua de pé
com a sua própria população. O EverOS é evidência sobre o **mecanismo**, não uma
quarta coluna do confound (e). Qual dos dois
documentos de um id colidido sobrevive depende da **ordem de ingestão** nas duas
colunas que deduplicam, e isso é desfavorável a nós tanto quanto ao EverOS.

⚠️ **Três contagens de "quanto foi ingerido" divergem por desenho** e só uma é a
que a busca vê. Medido a meio da corrida do EverOS: ledger 6.654 · diretórios em
disco 6.652 · sqlite 6.500. O ledger é registro de **escrita**; os diretórios são
o que o extractor gravou; o **sqlite é o índice pesquisável**, atualizado só por
`sincroniza()`. A retenção publicável é a do sqlite **após o sync final** — ler
antes subdeclarava em 154 documentos.

## 3. Ingestão do EverOS — recibo

```json
{"evento": "fecho", "ok": 6826, "falhas": 4, "no_ledger_agora": 6822,
 "de_um_total_de": 6830, "minutos": 250.9}
```

| | |
|---|---|
| documentos no índice | **6.822** |
| tópicos no índice | **11.414** (1,67 por documento) |
| falhas | **4**, todas `DuplicateDocumentError` |
| ids ausentes do índice | **0** |
| **falhas que são gold de alguma query** | **0** |

Predicado da última linha, escrito: `(corpus_ids − indexed_ids) ∩ ⋃ gold_chunk_ids = ∅`.

⚠️ *"0 falhas"* e *"4 falhas, nenhuma alcançável por query"* são estados
**diferentes**, e o nosso é o segundo. Declarar o predicado é o que impede que o
silêncio seja lido como o primeiro.

**Assimetria não explicada, e por isso não atribuída a mecanismo:** dos 8 ids
colididos, o segundo write foi **aceite em 4** e **recusado em 4** — mesma
operação, mesma forma de caso, resultados opostos. O efeito publicável é que a
retenção final é 6.822 pelos dois caminhos.

## 4. Configuração de busca do EverOS — o teto que o nome sobredeclara

| parâmetro | valor |
|---|---|
| `recall_n` | 200 |
| **`rerank_n`** | **50** ← o teto que morde |
| `mass_top_m` | 50 |
| `lam` | 0,1 |
| `top_k_cap` | 100 ← **o mais generoso dos dois, e portanto o que mente** |

`_run_category_pipeline` faz `effective_k = min(top_k, top_k_cap)` mas passa
`rerank_n` a `acategory_retrieve` ⇒ **o teto efetivo é 50**.

**Medido na corrida:** todas as queries devolvem `hits=50`, `method=hybrid`,
1,3–1,8 s ⇒ **saturação em 100%**. O adapter marca `saturou_no_teto: true` por
hit e **aborta** se o over-fetch pedido exceder o teto, em vez de truncar em
silêncio.

Carga do rerank = a **coluna** `knowledge_topics.content`, **média 136,6
caracteres**, via `_enrich_with_content` → `get_topics_by_ids`. Não é o markdown
do `md_path`. Literal: `raw_rerank = build_rerank_fn(reranker, text_field="content")`.

Superfície paga por query: **embedding (Gemini) + rerank (DeepInfra)**.
Estabelecido pela **assinatura** de `search_knowledge(*, query, method, top_k,
score_threshold, include_content, app_id, project_id)` — não tem `category_id`,
logo não dispara a classificação por LLM que outras funções do mesmo módulo
oferecem. Custo: 2.482 × 50 pares × ~140 tokens ≈ 17,4 M tokens a $0,025/1M
⇒ **~$0,43**.

### 4.1 A configuração de retrieval não está no `meta` — recibo à parte

O `meta` do artefato registra `datasets, finished_at, harness_version, k,
n_errors, n_queries, started_at, system, version` (+ `limite`, `queries_file`,
`queries_file_linhas`, acrescentados hoje). **Nada sobre modelo, reranker ou
dimensão.** Um nDCG publicado só com isso não diz sob que configuração foi
produzido — é a lição "medição em artefato versionado nomeia o commit" aplicada
a variável de ambiente em vez de commit.

Capturado do `/proc/<pid>/environ` do processo **vivo**, porque depois do fecho
deixa de ser observável (`everos-config-retrieval-2026-09-10.txt`):

| | valor |
|---|---|
| embedding | `gemini-embedding-001`, **3072d** |
| LLM | `gemini-2.5-flash-lite` |
| reranker | **`Qwen/Qwen3-Reranker-4B`** via DeepInfra |
| `EVEROS_SEARCH_METHOD` | **não definida** ⇒ default |
| `EVEROS_OVERFETCH` | **não definida** ⇒ default |

⚠️ `method=hybrid` é **observado no log do serviço** (2.482 ocorrências, valor
único), não inferido do env — o env prova o que pedimos, o log prova o que
correu. As duas chaves de Gemini têm o mesmo `sha256` de prefixo: é uma chave só,
usada nas duas superfícies.

⇒ O `meta` devia carregar isto. Enquanto não carrega, o recibo fica ao lado e a
célula do §7 aponta para ele.

## 5. Configuração de busca do Zep — fan-out por sessão

| parâmetro | valor |
|---|---|
| superfície | `POST /api/v1/sessions/{id}/search` |
| sessões | **510** (uma por conversa do benchmark) |
| `NOX_ZEP_SEARCH_WORKERS` | **96** |
| `ZEP_MAX_ERRO_SESSAO` | **0,01** — aborta se >1% das 510 falhar **numa mesma query** |

### 5.1 Varredura de workers, medida 2026-09-10 em condição controlada

| workers | s/query | observação |
|---|---|---|
| 16 | 11,92 | |
| 48 | 4,16 | |
| **96** | **3,39** | ótimo |
| 192 | 10,86 | **e com `[Errno 9] Bad file descriptor` por sessão** |

⇒ Não monotónico: acima de 96 o servidor degrada **e perde sessões**. Uma query
respondida a partir de 480 das 510 sessões tem menos recall **por falha de
varredura**, não por qualidade — daí o piso de 1%.

### 5.2 Duas superfícies de retrieval, e exercitámos uma — por escolha

Censo de rotas contra o container em serviço (`ghcr.io/getzep/zep:0.27.2`), com
controle positivo (`/healthz → 200`):

| rota | GET | POST | leitura |
|---|---|---|---|
| `/api/v1/search` | 404 | 404 | não existe |
| `/api/v1/graph/search` | 404 | 404 | não existe (é do Zep Cloud) |
| **`/api/v1/collection`** | **200** | 405 | existe — devolve `[]` |
| **`/api/v1/collection/{n}/search`** | **405** | 404 | existe (405 = router recusa o método; 404 = coleção inexistente) |
| `/api/v1/sessions/{id}/search` | 405 | **200** | a que usámos |

⇒ O Zep 0.27.2 expõe também uma busca **corpus-wide** de coleção de documentos,
e o `[]` prova que **nunca foi populada**. Medimos a superfície de **memória por
sessão**, onde vive a contribuição do Zep (sumarização e extração por conversa);
a de coleção mediria o Zep como armazém vetorial. O custo de 510 buscas por
query é, portanto, o da superfície de memória sob o mapeamento fiel de uma
conversa por sessão — **não um teto do Zep**. Se a busca de coleção daria nDCG
diferente é **não testado**, e não afirmamos que daria igual nem pior.

### 5.3 O NLP server foi removido por nossa escolha

`compose/docker-compose.yml` linha 25: *"ZEP_NLP_SERVER_URL removed — no NLP
server in this stack"*, e não há bloco `NLP` no `zep-config.yaml`. O Zep 0.27.2
**tem** caminho de embedding local (`Service: local` → `POST
{NLP.ServerURL}/embeddings/{message,document}`, sem chave). Removê-lo foi decisão
de **comparabilidade** — embedar com `text-embedding-3-small` a 1536d como as
outras colunas —, não restrição do Zep.

### 5.4 Superfície paga por query — tabela CRUZADA, e o custo total

> ⚠️ Esta subseção **não é do Zep**, apesar da numeração: compara as duas
> colunas e só pode vir depois de ambas as configurações estarem declaradas
> (§4 EverOS, §5 Zep). Cada linha nomeia o sistema. A numeração fica para não
> quebrar as referências que a sessão par já escreveu.

Simétrica à do EverOS (§4): declarada pela **configuração em serviço**, não por
suposição sobre a arquitetura.

| sistema | superfície paga por query | preço |
|---|---|---|
| EverOS | embedding (Gemini) + **rerank** de 50 pares (DeepInfra) | $0,025/1M |
| **Zep** | embedding da **query** (`text-embedding-3-small`, 1536d, OpenAI) | $0,02/1M |

O Zep **não** rerankeia: o `limit=10` por sessão sai do índice pgvector e a fusão
é nossa. O EverOS **não** classifica por LLM: a assinatura de `search_knowledge`
não tem `category_id`.

**Custo, e o que é medição e o que é cota superior:**

| linha | valor | natureza |
|---|---|---|
| DeepInfra rerank (EverOS) | $0,43 | **medido** — 2.482 × 50 × ~140 tok |
| OpenAI embed, ingestão do Zep | $0,027 | **medido** — 6.830 msgs × ~200 tok |
| OpenAI embed, query do Zep | **≤ $0,51** | **cota superior** |
| Gemini embed (EverOS) | prepago | fora de fatura marginal |

⚠️ A terceira linha é **cota, não medição**. O piso é $0,001 (uma embedagem por
query, reusada nas 510 sessões) e o teto é $0,51 (uma por *sessão*, zero cache:
2.482 × 510 × ~20 tok = 25,3 M). Não sabemos onde cai: o medidor autoritativo é
`/v1/organization/usage/embeddings` e a chave deste projeto **não tem o escopo
`api.usage.read`**. O log do container só registra o router — `grep -ci embed`
devolve `0` com `exit 1`, que é um zero legítimo do `grep` e **mudo** sobre a
camada perguntada. Reportar $0,51 como "o custo" seria dar a uma cota o estatuto
de medição; a decisão que ela sustenta (o gasto está dentro do aprovado) não
precisa de mais precisão que isso.

### 5.5 As 17 falhas de sessão, por origem

Contá-las não diz nada; **classificá-las** diz. Sobre 522.750 varreduras
(0,0033%):

| origem | n | de quem é |
|---|---|---|
| `timed out` | 13 | nosso cliente |
| `[Errno 9] Bad file descriptor` | 2 | pool do nosso cliente |
| OpenAI 500 em `/v1/embeddings` (após 6 tentativas) | 2 | provedor externo |

⇒ **Nenhuma é falha de retrieval do Zep.** Cada uma retira **uma** das 510
sessões do conjunto de candidatos daquela query; nenhuma query passou do limiar
de aborto (>5 de 510). O efeito no nDCG é, no pior caso, a ausência de um
candidato entre 510 em 17 queries — declarado, não corrigido.

## 6. Piso de integridade da varredura — duas condições, não uma

| piso | condição | a falha que cobre |
|---|---|---|
| erro de sessão | aborta se >1% das 510 sessões falhar numa query | a que **se anuncia** |
| **contagem de queries** | recibo declara `n_queries`, `limite` e `queries_file_linhas`, e **aborta** se o carregado divergir das linhas do arquivo sem teto pedido | a que **não se anuncia** |

O segundo piso existe porque **cortar entrada não é erro**. Em 2026-09-10 uma
corrida do Zep escreveu artefato de aparência completa — `(0 errors)`, `meta`
bem formado — com **100 de 2.482 queries, cada uma duplicada, de um só dataset**:
`--limit` tinha default 100 (desenhado para `dry-run-sample`) e era aplicado ao
`--queries-file` explícito, e o laço por dataset relia o mesmo arquivo
combinado. O `meta.n_queries: 200` era honesto e **ininterpretável**: sem
denominador, 200 lê-se como o tamanho do corpus.

⚠️ Os artefatos `rc4` publicados **não** foram afetados: `n_queries: 2482` e
`datasets: ["locomo","longmemeval"]` nos quatro
(`output/rc4/{nox_mem,mem0}.json`, `output/rc4-ablation/`). Conferido **antes**
de qualquer conserto.

## 7. nDCG@10 — EverOS FECHADO, Zep pendente

| coluna | corrida | retenção | nDCG@10 | recibo |
|---|---|---|---|---|
| nox-mem | rc4 2026-06-29 | 6.822 | *(publicado, rc4)* | `output/rc4/nox_mem.json` |
| mem0 | rc4 2026-06-29 | 6.830 | *(publicado, rc4)* | `output/rc4/mem0.json` |
| **Zep** | **2026-09-10** | 6.830 | **PENDENTE** | `out/zep-busca/zep.json` |
| **EverOS** | **2026-09-10** | 6.822 | **0,6455** | `output-2026-09-10/evermind.json` |

⚠️ **Errata 2026-09-10:** estas linhas diziam `rc4 2026-06-15` até agora. **15/06
é a corrida canônica; o rc4 rodou em 29/06**, provado pelo `finished_at` dos
próprios artefatos (`output/rc4/nox_mem.json` → `2026-06-29T13:58:58Z`,
`mem0.json` → `2026-06-29T14:57:04Z`). Eu criei esta coluna hoje justamente para
impedir que duas populações se misturassem, e rotulei a corrida com a data da
outra — o rótulo errado no instrumento feito contra rótulos errados.

⚠️ A coluna `corrida` não é decoração: as duas primeiras linhas e as duas últimas
são populações diferentes. Comparar **mecanismos** entre corridas é legítimo;
atribuir os **números** a uma só população não é.

**Não preencher por estimativa.** Cada célula só entra com o `meta` do artefato
ao lado, e o `meta` tem de declarar `n_queries`, `limite` e
`queries_file_linhas`.

### 7.0 ⚠️ Zep — onde o artefato está se a sessão fechar antes dele

Escrito **antes** do fecho, de propósito: se a sessão que conduz a corrida
terminar primeiro, este parágrafo é a única coisa que sabe onde o artefato ficou.
Nenhum CI o encontra — a perna `contagem/L2` varre `eval/q4-comparison/**` do
repositório, não uma máquina remota.

⚠️ **Este repositório é público.** O host da corrida é identificado por
**capacidade**, nunca por endereço: hostname e IP de tailnet não entram no git.
O valor vive fora daqui — no `~/.ssh/config` de quem opera, ou na variável
`NOX_Q4_HOST` do ambiente. Um `chore(repo): public-readiness — infra scrub`
(`d5bba83`) já removeu endereços deste repositório uma vez; reintroduzi-los
desfaria uma decisão tomada.

**Estado em 2026-09-10 21:11 BRT:** `2.150/2482`, `ZEP_FALHA=0`,
`ZEP_ERRO_SESSAO=41` em ~1,1 M varreduras (0,0033%, sem tendência por janela).
ETA ~21:43 a ~10 q/min.

**Onde ele aterra** (o runner escreve `output_dir / "{system}.json"`):

```
host:    $NOX_Q4_HOST        (o host do benchmark do Q4 — NÃO é a VPS de
                              produção, que está proibida de hospedar benchmark
                              até 2026-09-21 pelo ensaio do Paper 2)
caminho: /root/q4-everos/out/zep-busca/zep.json
tmux:    zep-busca           (capture com -t zep-busca:0.0, NÃO -t=)
console: /root/q4-everos/out/zep-busca-console.log
```

**Recuperação, na ordem que importa:**

```sh
# 1. fechou de verdade? sessão morta NÃO distingue fecho de morte a meio
ssh root@"$NOX_Q4_HOST" 'cd /root/q4-everos && bash scripts/classifica-erro-busca.sh out/zep-busca-console.log ZEP && ls -l out/zep-busca/*.json'

# 2. trazer para um diretório PRÓPRIO — nunca `output/zep.json`, que o
#    manuscrito cita nominalmente (paper-tecnico linhas 1161 e 1184)
scp root@"$NOX_Q4_HOST":/root/q4-everos/out/zep-busca/zep.json eval/q4-comparison/output-2026-09-10/

# 3. as quatro verificações do §7.1, depois o agregador COMMITADO
python3 eval/q4-comparison/aggregate.py --output-dir eval/q4-comparison/output-2026-09-10 --k 10
```

⚠️ **Não preencher a célula sem as quatro verificações.** O campo de id chama-se
`question_id` — pedir `query_id` devolve `1 id distinto` sobre 2.482, que é a
assinatura exata do bug de truncamento e é **falso**.

⚠️ **A configuração de retrieval não está no `meta`.** Para o Zep ela é
`text-embedding-3-small` a 1536d pela OpenAI (`zep-config.yaml`,
`Extractors.Messages.Embeddings`), sem reranker. Se o processo ainda estiver vivo,
capturar do `/proc/<pid>/environ` **antes** de ele morrer, como foi feito para o
EverOS.

### 7.1 EverOS — fechado 2026-09-10T22:49:43Z

**`meta` do artefato, verbatim:**

```
system = evermind                       n_queries = 2482
version = everos==1.3.1                 limite = None
k = 10                                  queries_file_linhas = 2482
n_errors = 0                            queries_file = cache/queries-rc4-all.jsonl
started_at = 2026-09-10T21:34:34Z       datasets = ['locomo', 'longmemeval']
finished_at = 2026-09-10T22:49:43Z
```

| métrica | valor |
|---|---|
| **nDCG@10** | **0,6455** |
| recall@10 | 0,7629 |
| MRR | 0,6403 |
| locomo (n=1982) | nDCG 0,6585 |
| longmemeval (n=500) | nDCG 0,5942 |
| latência p50 / p95 / p99 | 1.592 / 2.986 / 4.214 ms |

Calculado pelo `aggregate.py` **committado** (`ndcg_at_k`, relevância binária),
não por conta ad-hoc: monitor que reimplementa predicado do código omite caso.
Instrumento exercitado antes em entrada conhecida (o smoke de n=20 de 25/05, que
devolveu 0,3909) — para descobrir defeito da ferramenta antes de ter o artefato
real na mão, não depois.

**Quatro verificações de integridade, todas passadas:**

| # | verificação | resultado |
|---|---|---|
| 1 | `n_queries` / `limite` / `queries_file_linhas` / `n_errors` | 2482 / `None` / 2482 / 0 |
| 2 | entradas e **`question_id` distintos** | 2482 e **2482**, 0 repetidos |
| 3 | por dataset | locomo **1982** + longmemeval **500** |
| 4 | com gold · com resultado · `len(results)` | 2482 · 2482 · **10 em todas** |
| — | `n_scored == n_queries` (agregador) | 2482 == 2482 |

⚠️ A perna 2 nasceu de um susto meu: a primeira sonda devolveu **`ids distintos =
1`**, que é a assinatura exata do bug das 100 duplicadas. O campo chama-se
`question_id`; eu pedi `query_id` e `id`, ambos ausentes, e
`set([None]*2482)` tem tamanho 1. **"2.482 ids idênticos" e "sonda com o nome
errado" produzem o mesmo `1`** — e o `1` é plausível como medição. Resolvido por
listar as chaves de uma entrada antes de concluir, que é a única perna que separa
os dois casos.

⚠️ **2.470 textos** de query distintos contra 2.482 ids: 12 queries partilham
enunciado com outra. É propriedade do conjunto de queries, análoga aos 8 ids
ambíguos do corpus, e não afeta contagem nem denominador.

### 7.2 🔴 Confound de pipeline — e a sua magnitude NÃO é medida

Levantado pela sessão par, e ela está certa que existe. Verifiquei na biblioteca
instalada e o achado é **mais forte** do que "nós configurámos generosamente":

```
everos/service/knowledge.py:1264  def _require_search_providers() -> tuple[EmbeddingProvider, RerankProvider]
everos/service/knowledge.py:1363      embedder, reranker = _require_search_providers()
```

⇒ **O EverOS recusa buscar sem reranker** (`ProviderNotConfiguredError`). Dar-lhe
o `Qwen/Qwen3-Reranker-4B` não foi escolha nossa de generosidade — é a
configuração **mínima viável** do sistema. É propriedade dos sistemas comparados,
não do experimentador.

Do outro lado, o adapter do nox-mem **não tem estágio de cross-encoder nenhum**:
o que ele chama "rerank" é re-ordenação por RRF e multiplicação de score por
vizinhança de 1-hop no KG (`adapters/nox_mem.py`, caminhos E+F+H). Logo a
comparação confunde *arquitetura de retrieval* com *ter um cross-encoder no
pipeline*.

⚠️ **Mas a magnitude do confound é NÃO MEDIDA neste benchmark**, e afirmar que ela
é "do tamanho do efeito" vai além do que temos. A única medição que possuímos do
efeito de um cross-encoder neste sistema é de **outro** benchmark
(EverMemBench, 5-batch) e por **outras** métricas:

| categoria | Δ com cross-encoder |
|---|---|
| **overall** | **−0,96pp** |
| hard-recall (multi-hop / high-level / temporal) | +1,6 a +2,6pp |
| Memory Awareness (constancy / proactivity / update) | **−2,8 a −4,0pp** |

Ela **não transfere** — benchmark diferente, métrica diferente, caminho de código
diferente (produto, não este harness). Mas é a única evidência que temos sobre o
tamanho da contribuição de um cross-encoder aqui, e ela não sustenta uma diferença
de dois dígitos; sustenta ~1pp, com sinal negativo no agregado. Foi por isso que o
cross-encoder foi enviado **opt-in** e não por omissão.

⇒ **Como se resolveria:** acrescentar um estágio de cross-encoder ao adapter do
nox-mem e correr o mesmo corpus. **Não é virar uma flag** — o estágio não existe
neste harness. É código novo e uma corrida paga, logo é decisão de escopo do Toto,
não minha.

⇒ **Enquanto não for medido**, a frase correta declara o confound e diz que a
magnitude é desconhecida. Dizer "é do tamanho do efeito" erra na direção de
subdeclarar a nossa própria coluna, o que é a direção honesta de errar — mas
continua a ser um número que a nossa evidência não produz.

🔑 **Sobre o teto do §4:** o log do serviço mostra `hits=50` em todas as 2.482
queries (100% de saturação do `rerank_n`), e o artefato tem `len(results) == 10`
em todas. Não é contradição: 50 é o conjunto de candidatos que o reranker
devolve, 10 é o `k` do harness. O teto que morde a **qualidade** é o 50, porque
é ele que limita o que pode chegar ao top-10.
