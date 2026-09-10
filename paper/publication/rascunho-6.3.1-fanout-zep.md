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
> **Two things follow, and the second is a caveat against us.** First, this is a genuine
> architectural distinction from the systems whose retrieval is corpus-scoped, including
> nox-mem: our single-index design has no per-session multiplier, and Zep's has no
> cross-session distractor problem. Neither property is strictly better — they answer
> different questions about what a memory *is*. Second, the 510-way multiplier is a
> function of **our corpus mapping** as much as of Zep's API: we mapped one benchmark
> conversation to one Zep session, which is the faithful mapping, but a deployment that
> pooled conversations into fewer sessions would pay a smaller multiplier and lose the
> session semantics that motivate the design. The cost we report is therefore the cost of
> *Zep used as intended on this corpus*, not a ceiling on Zep.

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
