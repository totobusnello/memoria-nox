# Rascunho — §6.3.1, a assimetria do reranker do EverOS

> ⚠️ **EM ESPERA, não no manuscrito** — entra junto com a coluna do EverOS, e no **mesmo
> parágrafo** que a peça do fan-out do Zep (`rascunho-6.3.1-fanout-zep.md`): as duas são
> diferença de **pipeline**, e ficam mais legíveis lado a lado do que separadas.
>
> Fatos medidos pela sessão par por **leitura de fonte**, não por inferência, 2026-09-10.
> Redação minha.

---

## Peça (a) — evidência, autossuficiente

> **EverOS — rerank ceiling and payload (measured 2026-09-10, from source).** The EverOS
> retrieval pipeline reranks with `Qwen/Qwen3-Reranker-4B`[^qwen3embed] hosted on DeepInfra.
> Its configuration declares `recall_n=200`, `rerank_n=50`, `mass_top_m=50`, `lam=0.1` and
> `top_k_cap=100`, but the binding ceiling is **`rerank_n=50`**: `_run_category_pipeline`
> computes `effective_k = min(top_k, top_k_cap)` and then passes **`rerank_n`** to
> `acategory_retrieve`. The field named `top_k_cap` is the *more generous* of the two limits
> and therefore overstates what the pipeline will actually rerank.
>
> The rerank payload is the `knowledge_topics.content` column — a short per-topic summary,
> **mean 136.6 characters** — retrieved via `_enrich_with_content` → `get_topics_by_ids`, not
> the markdown at `md_path`. The construction is explicit in the source:
> `raw_rerank = build_rerank_fn(reranker, text_field="content")`.
>
> Cost of the rerank stage at benchmark scale: 2,482 queries × 50 pairs × ~140 tokens ≈
> **17.4 M tokens**, at $0.025/1M ⇒ **≈ $0.43**.
>
> **Saturation guard.** At `k=10` with an over-fetch factor of 5 the request is exactly 50 —
> **zero headroom**; at `k=20` the pipeline would return 50 candidates *silently*. The
> harness therefore aborts with the concrete numbers rather than truncating, and records
> `saturou_no_teto` per hit, so a saturated request is visible in the artifact instead of
> being indistinguishable from a short result list.

## Peça (b) — prosa, migrável sem levar número

> The reranking stages of the two systems are fed **payloads of different natures**, and this
> is the second pipeline difference worth declaring alongside Zep's search fan-out. EverOS
> reranks over a short per-topic summary; our stack reranks over the chunk text itself. The
> model class is comparable — a cross-encoder scoring a query-candidate pair — but what it
> reads is not: a distilled topic label and a passage of source text carry different amounts
> of the evidence a reranker is supposed to weigh. Neither choice is wrong. The summary is
> cheaper and matches how EverOS organises memory; the chunk text is what our index holds.
> But a reader comparing the two rerank columns is comparing two operations that share a
> name and not an input, and that has to be said rather than left to be discovered.
>
> The rerank ceiling deserves the same treatment as a **silent truncation**, which is the
> failure mode it produces when unguarded: a request above the ceiling returns fewer
> candidates with no error, and fewer candidates read as a weaker result. This is the same
> class as a retrieval measured before its index finished building — a null manufactured by
> the measurement apparatus, indistinguishable from a finding. It is why the harness aborts
> on saturation instead of proceeding, and why the saturation flag is recorded per hit rather
> than aggregated: an aggregate can hide a systematic ceiling on one category of query.

---

## Notas de redação

1. **Um parágrafo, duas diferenças.** O fan-out do Zep e a carga do reranker do EverOS são a
   mesma espécie de fato — o pipeline difere, a qualidade não está em causa — e a peça (b) de
   cada uma foi escrita para poder ser lida em sequência.
2. **`[^qwen3embed]` já existe** no manuscrito (§7.2 F5, `arXiv:2506.05176`), com
   *"não rodado neste estudo"* explícito. ⚠️ **Se a coluna do EverOS entrar, essa nota fica
   falsa** — o Qwen3-Reranker-4B passa a ter rodado, dentro do EverOS, e não como nosso
   componente. A footnote precisa da distinção: nomeado como candidato **nosso** no F5, e
   executado **pelo EverOS** na sua própria coluna. Editar junto.
3. **A cifra de $0,43 é do estágio de rerank apenas**, não da corrida — não somar com o custo
   de ingestão sem dizer qual é qual.

---

## Atualização 2026-09-10 — o teto foi MEDIDO, e a retenção fechou

O que este rascunho antecipava como leitura do fonte está medido na varredura viva.

### O teto satura em 100% das queries

| | |
|---|---:|
| `rerank_n` (o que liga) | **50** |
| `top_k_cap` (o nome que sobredeclara) | 100 |
| hits devolvidos por query, `method=hybrid` | **50** |
| queries que saturam no teto | **100%** |
| latência por query | ~1,3–1,8 s |

⇒ **Não é previsão do fonte, é medição da corrida.** Todo hit sai com
`saturou_no_teto = true`, e o parâmetro cujo nome anuncia 100 nunca é o que decide.
Consequência para qualquer nDCG@10 daquele serviço: é computado sobre um conjunto de
candidatos **truncado em 50**.

### Retenção: 6.822, e as 4 falhas são os pares colididos

`ok: 6.826 · falhas: 4 · 250,9 min`, e os quatro erros são
`DuplicateDocumentError` nos ids que nomeiam dois documentos distintos. Os cinco
contadores batem: índice pesquisável 6.822, `doc_id` distintos no ledger 6.822, ids
distintos no corpus 6.822 (de 6.830 linhas), diretórios no disco 6.823, `knowledge_topics`
11.414 (1,67 por documento).

**Documentos ausentes que são gold: 0.** Predicado:
`corpus_ids − indexed_ids ∩ ⋃ gold_chunk_ids = ∅`. ⇒ **sem ressalva de nDCG** por falha de
ingestão. *"Zero falhas"* e *"quatro falhas, nenhuma alcançável"* são estados diferentes e
este é o segundo — declarar o predicado é o que impede ler o silêncio como o primeiro.

### A tabela de retenção, agora completa — e é 2 contra 2

| coluna | retenção | mecanismo |
|---|---:|---|
| nox-mem | **6.822** | `INSERT OR IGNORE`, guarda um em silêncio |
| **EverOS** | **6.822** | `DuplicateDocumentError`, recusa o segundo |
| mem0 | 6.830 | sem dedupe (6.822 `chunk_id` distintos) |
| Zep | 6.830 | sem dedupe |

Não é 3-contra-1 nem 1-contra-3. **Dois sistemas, dois mecanismos, um número** — o que faz
de 6.822 a consequência de honrar unicidade de id, e não idiossincrasia do nosso loader.
Entrou no confound (e) do §6.3.2 com a corrida nomeada dos dois lados, e o
`corpus_bench_check` prende essa frase: parágrafo que atribui a contagem a 2+ sistemas
nomeando **uma** corrida falha.

⚠️ **O que NÃO escrever.** Dos 8 ids colididos, o segundo write foi aceito em 4 e recusado
em 4 — mesma operação, resultados opostos. A hipótese de mecanismo (quem atravessou um
`sincroniza()` está no índice e é recusado; quem estava no buffer é sobrescrito) **não está
medida** e não entra no paper. O publicável é o efeito: a retenção final é 6.822 pelos dois
caminhos, e **qual dos dois documentos sobrevive num id colidido depende da ordem de
ingestão** — a mesma frase que já publicamos sobre o nosso `INSERT OR IGNORE`, e que
continua desfavorável a nós, o que é bom declarar.

### O que continua fora do manuscrito

O **nDCG do EverOS**. A varredura estava a correr quando o §6.3.1 foi escrito, e o que
entrou lá é só o que fecha sem ela: a retenção, o predicado das falhas e o teto. O §6.9
continua com a contagem *"as of this revision"*, e passa a **dois** só contra artefato
fechado.
