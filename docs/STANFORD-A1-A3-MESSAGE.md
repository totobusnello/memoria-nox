# Stanford — mensagem A1 + A3, rascunho

> **NÃO ENVIADO.** Rascunho para o Toto revisar e enviar. Corte A1+A3 decidido em
> 2026-08-15 (`STANFORD-OUTREACH.md` §4); os números foram extraídos em 2026-09-07.
> A1 oferece a telemetria de fases; A3 mostra a política de esquecimento. A4 (survey /
> James Zou) é **canal separado**, depois — não misturar.

## Destinatário

**`yomri@stanford.edu`** (autor de correspondência de `arXiv:2606.06448`). Zexue He e
Alex Pentland assinam o mesmo paper e o MemoryArena, e são o elo com o Alvo B — mas
segundo o §5 a primeira mensagem não se espalha por vários destinatários. **Um
destinatário, o de correspondência.**

## Os números, e de onde vêm

Extraídos do `provider_telemetry` do store compartilhado, leitura read-only em
2026-09-07:

| | |
|---|---|
| janela | 2026-08-07 → 2026-09-08, **33 dias distintos** com dados |
| registros | **3.545** chamadas de provider |
| custo total da série | **USD 0,1352** |
| provedores | `gemini-embedding-001` (3.426) · `gemini-2.5-flash-lite` (119) |

**Atribuição de custo por fase — o número que a bancada não produz:**

| fase | ops | % ops | custo USD | % custo | USD/op |
|---|---:|---:|---:|---:|---:|
| construction | 112 | **3,16%** | 0,0753 | **55,7%** | 0,00067 |
| query | 3.352 | 94,56% | 0,0412 | 30,5% | 0,0000123 |
| maintenance | 81 | 2,28% | 0,0187 | 13,8% | 0,00023 |

Uma operação de `construction` custa **55×** uma de `query`. Contando operações, a
construção é ruído; contando dinheiro, é a maioria. **É a mistura que produz isso, e a
mistura só existe em produção contínua.**

Cadência: `query` em 33 dos 33 dias, `construction` em 19, `maintenance` em 11.

## 🔴 O que NÃO afirmar — três coisas medidas

1. **Não é telemetria de fleet.** Os **6 bancos por agente não têm a tabela
   `provider_telemetry`** (verificado hoje). Todos os 3.545 registros são do **store
   compartilhado do workspace**, que os agentes consultam. Dizer "fleet" a quem escreveu
   o harness de perfilamento por fase seria pego na primeira pergunta.
2. **São 6 agentes, não 7** — Nox, Atlas, Boris, Cipher, Forge, Lex.
3. **Não há amortização demonstrada.** O custo por query por semana é **não-monótono**:
   1,24 → 1,17 → 1,72 → 0,39 → 0,26 → 2,42 (×10⁻⁵ USD). A Recomendação deles sobre
   *amortization via query volume* **não** se confirma nestes dados. Isso vai na
   mensagem como resultado negativo — é mais interessante que silêncio, e protege contra
   ser pego afirmando o contrário.

## Rascunho da mensagem

> **Assunto:** Phase-attributed memory telemetry from a production deployment — 33 days,
> possibly useful for 2606.06448
>
> Dear Dr. Omri,
>
> I read *Agent Memory: Characterization and System Implications of Stateful
> Long-Horizon Workloads* in full. Your phase decomposition — construction, retrieval,
> generation — is the same decomposition I instrumented in a production memory system,
> and I am writing to offer the data, not to ask for anything.
>
> The system serves six agents on a single VPS and has been running continuously since
> 2026. Provider-level telemetry is attributed per phase; over the 33 days from
> 2026-08-07 the shared workspace store logged 3,545 provider calls at a total cost of
> USD 0.135. The phase attribution inverts what operation counts suggest:
> **construction is 3.16% of operations and 55.7% of cost** (USD 0.00067 per
> construction op against USD 0.0000123 per query). A bench characterization on a fixed
> workload cannot produce that ratio, because it is the workload *mix* that produces it,
> and the mix only exists in continuous operation.
>
> Two caveats I would rather state than have you discover. The telemetry covers the
> shared store the agents query, **not** six per-agent stores — those carry no telemetry
> table. And your recommendation on amortization via query volume **does not** reproduce
> here: weekly cost per query is non-monotonic across the series.
>
> Separately, your Recommendation 9 asks operators to add independent pruning or
> forgetting policies, and notes that all ten characterized systems accumulate state
> monotonically. This system has one — retention windows typed per content class,
> salience decay, epoch pruning, graph pruning — and, more usefully, the record of it
> failing: a compounding error in the decay drained the knowledge graph from ~21.5k
> nodes to 554 before it was diagnosed and recovered. On the four axes, it sits at
> mixed construction, multi-store storage, hybrid retrieval, and `mutate` mutability
> **without agent control** — maintenance is deterministic cron, not an LLM in a loop.
> I could not find that combination in Table 1.
>
> Happy to share the telemetry as a dataset, the schema, or the forgetting-policy
> post-mortem — whatever is useful, in whatever form. A technical report on the system
> is at `10.5281/zenodo.22649269`; it is a preprint and has **not** been peer reviewed.
>
> With respect for the work,
> Luiz Antonio Busnello — Independent Researcher

## Conferência contra o §5 antes de enviar

- [x] não reivindica o gap "memória guia decisão" (prior art do próprio grupo)
- [x] cita o Paper 1 **com** DOI e **declara** que não passou por peer review
- [x] não pede endosso, coautoria nem revisão — oferece
- [x] não menciona o harness deles (não é público)
- [x] declara as duas limitações antes de serem descobertas
- [ ] **Toto revisar e enviar** — não enviei
