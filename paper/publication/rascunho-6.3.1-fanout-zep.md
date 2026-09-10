# Rascunho — §6.3.1, a peça do fan-out do Zep

> ⚠️ **EM ESPERA, não no manuscrito.** O texto abaixo está pronto para entrar no minuto em
> que o artefato do Zep fechar com nDCG dentro. Não entra antes: enquanto o Zep é um gap
> declarado do §6.3.1, uma subseção descrevendo o custo de busca **dele como coluna**
> pressupõe a coluna.
>
> A varredura de workers, ao contrário da hora de parede, foi medida em **condição
> controlada** e é final. Medições da sessão par; redação minha.

---

## Peça (a) — evidência, autossuficiente

*Para entrar no §6.3.1 como bloco fechado. Não depende de nenhuma frase da prosa.*

> **Zep — search fan-out and its worker optimum (measured 2026-09-10).** Zep's search API is
> scoped to a session. The benchmark corpus maps to **510 sessions** (one per `conv_id`), so
> a single benchmark query issues 510 search calls, each ~272–370 ms server-side. Throughput
> is therefore governed by client concurrency, set via `NOX_ZEP_SEARCH_WORKERS`:
>
> | workers | median per query | note |
> |---:|---|---|
> | 16 | 11.92 s | |
> | 48 | 4.16 s | |
> | **96** | **3.39 s** | optimum |
> | 192 | 10.86 s | **degrades, and loses sessions** — server returns `[Errno 9] Bad file descriptor` per session |
>
> The curve is **not monotonic**: past 96 workers the Zep server degrades *and drops
> sessions*, so the inflection is a property of the server's connection pool, not of the
> client. All runs on the same host and corpus; 96 workers used for the reported column.
>
> **Scan-integrity floor.** Because a query answered from 480 of 510 sessions has lower
> recall *by scan failure* rather than by retrieval quality — and would be published as
> Zep's quality — the harness aborts the run when more than **1%** of sessions fail their
> scan (`ZEP_MAX_ERRO_SESSAO=0.01`). The Zep column therefore carries a declared integrity
> floor rather than a silent partial scan.

> **Surface census (measured 2026-09-10 against the running 0.27.2 container, from the
> host, with `/healthz → 200` as positive control).** The build exposes two retrieval
> surfaces:
>
> | route | GET | POST | reading |
> |---|---|---|---|
> | `/api/v1/sessions/{id}/search` | 405 | **200** | per-session memory search — **the surface measured** |
> | `/api/v1/collection` | **200** | 405 | collection index — returns `[]`: no collection was ever created |
> | `/api/v1/collection/{name}/search` | 405 | 404 | corpus-wide document search — exists, **not exercised** |
> | `/api/v1/search`, `/api/v1/documents`, `/api/v1/graph/search` | 404 | 404 | absent in this build (the last is Zep Cloud) |
>
> The `405` on a route is the router refusing the *method*, which is itself evidence the
> route exists; a `404` on `/collection/{name}/search` is the named collection being absent,
> not the route. The empty `/collection` listing is the direct evidence that the
> document-collection surface was never populated.

## Peça (b) — prosa, migrável sem levar número

*Para entrar como parágrafo do §6.3.1. Contém zero números: pode migrar para suplemento
sem quebrar a evidência da peça (a).*

> The fan-out is worth stating as a **pipeline difference, not a limitation of our
> measurement**, and it cuts in a direction that is easy to misread. Zep scopes retrieval to
> a session because its memory model is conversational: a session is the unit that carries
> temporal and participant context, and searching within it is what makes its temporal
> knowledge graph meaningful. The consequence is that Zep's search cost scales with the
> **fragmentation of the history** — the number of sessions — and not with the size of the
> corpus. A single long conversation and a thousand short ones can hold the same number of
> tokens and cost order-of-magnitude different amounts to query.
>
> **Three things follow, and two of them are caveats against us.** First, this is a genuine
> architectural distinction from the systems whose retrieval is corpus-scoped, including
> nox-mem: our single-index design has no per-session multiplier, and Zep's has no
> cross-session distractor problem. Neither property is strictly better — they answer
> different questions about what a memory *is*.
>
> Second, the multiplier is a function of **our corpus mapping** as much as of Zep's API: we
> mapped one benchmark conversation to one Zep session, which is the faithful mapping, but a
> deployment that pooled conversations into fewer sessions would pay a smaller multiplier and
> lose the session semantics that motivate the design.
>
> Third, and most important: **Zep offers two retrieval surfaces and we exercised one, by
> choice.** The column measures Zep's *per-session memory surface*, which is where its
> contribution lives — per-conversation summarization and temporal extraction. The same
> build also exposes a *document-collection surface* with its own corpus-wide search, and we
> created no collections against it, so it was never touched. Measuring that surface would
> measure Zep as a vector store, which is not what the system proposes and not what our
> question asks. We therefore report the cost and the quality of the **memory surface under
> a faithful one-conversation-per-session mapping** — a declared choice of surface, not a
> ceiling on Zep, and not the only search Zep offers.
>
> Whether the collection surface would score differently on this benchmark is **untested**.
> We do not claim it would score the same, and we do not claim it would score worse.

---

## Frase de método — o piso de contagem, ao lado do piso de erro

> Acrescentada 2026-09-10 a pedido da sessão que conduz as corridas, depois de um artefato
> falso: `WROTE out/zep-busca/zep.json (0 errors)`, `meta` bem formado, 899 KB — e **100
> das 2.482 queries (4,0%), num só dos dois datasets, cada uma medida duas vezes**. Dois
> defeitos que só juntos produzem algo plausível: um `--limit` com default 100, desenhado
> para o caminho de amostra, aplicado também ao `--queries-file` explícito; e um laço por
> dataset que relia o mesmo arquivo combinado. Corrigido em `f79dbbf`/`dca83da`, com os
> artefatos `rc4` já publicados conferidos **antes** do conserto e intactos
> (`n_queries: 2482`, ambos os datasets).

Redação proposta, uma frase junto do piso de erro de sessão já declarado no §6.3.1:

> The run declares `n_queries`, the requested `limit`, and the line count of the queries
> file, and aborts when the number of queries measured differs from the file's line count
> with no ceiling requested — a query-count floor alongside the 1% session-error floor.
> Both are integrity conditions on the sweep, not on the system under test.

**Por que a frase é necessária e não é enfeite.** O piso de erro de sessão cobre a falha
que se **anuncia**; este cobre a que **não se anuncia**, porque cortar entrada não é erro:
o artefato sai bem formado, com `meta` coerente, e o número que ele carrega descreve uma
varredura que não aconteceu. `meta.n_queries: 200` era honesto e ininterpretável — sem
denominador, 200 lê-se como o tamanho do corpus e não como um teto que alguém aplicou.

⇒ **Um default é uma afirmação sobre o caso comum. Quando o chamador passa entrada
explícita e autocontida, o default deixa de descrever o caso comum e passa a contradizer o
pedido — em silêncio.** A mesma classe do `rerank_n=50` contra `top_k_cap=100` do rascunho
irmão, com o sinal trocado: lá o nome **overstates** o limite; aqui o campo **subdeclara**
que houve corte.

---

## Notas de redação, para quando entrar

1. **A hora de parede fica fora.** Três medições deram 2,34 h, 3,4 h e 4,1 h, e não se sabe
   se a diferença é contenção ou variação de carga. A única publicável é a duração real no
   `fecho` do artefato. Ver `fatos-medidos-para-o-6-2026-09-10.md` §1.
2. **O gatilho do §6.9 é separado disto.** Quando a coluna existir, o parágrafo *"three of
   five competitors could not produce a number"* passa a **dois** e a nota de escopo do #510
   sai. São duas edições distintas; esta peça não a dispensa.
3. **O `[^zep]` já tem localizador** (`arXiv:2501.13956`) e o `[^zep-stack]` já ancora no
   fonte `v0.27.2`. Nenhuma referência nova é necessária para esta peça.
