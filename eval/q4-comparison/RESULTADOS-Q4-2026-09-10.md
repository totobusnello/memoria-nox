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
> populações**: nox-mem e mem0 são do **rc4** (2026-06-15), EverOS e Zep são da
> corrida de **2026-09-10**. Juntá-las numa tabela sem nomear a corrida por
> linha convida a ler o 6.822 do EverOS como número do rc4 — e foi o que a
> minha primeira versão desta tabela fez. Comparar mecanismos entre corridas é
> legítimo; atribuir os números à mesma população não é.

| coluna | corrida | retenção | mecanismo | como foi medida |
|---|---|---|---|---|
| nox-mem | **rc4**, 2026-06-15 | **6.822** | `INSERT OR IGNORE INTO eval_chunks(id,…)` | contagem na tabela |
| mem0 | **rc4**, 2026-06-15 | **6.830** | sem dedupe (6.822 `chunk_id` distintos) | contagem no store |
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

## 7. nDCG@10 — PENDENTE

| coluna | retenção | nDCG@10 | recibo |
|---|---|---|---|
| nox-mem | 6.822 | *(publicado, rc4)* | `output/rc4/nox_mem.json` |
| mem0 | 6.830 | *(publicado, rc4)* | `output/rc4/mem0.json` |
| **Zep** | 6.830 | **PENDENTE** | `out/zep-busca/zep.json` |
| **EverOS** | 6.822 | **PENDENTE** | `out/everos-busca/evermind.json` |

**Não preencher por estimativa.** Cada célula só entra com o `meta` do artefato
ao lado, e o `meta` tem de declarar `n_queries`, `limite` e
`queries_file_linhas`.
