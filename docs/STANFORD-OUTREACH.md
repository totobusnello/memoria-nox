# Stanford — aproximação de colaboração

> **Status:** v0.2, 2026-08-15. Documento operacional. Antes da v0.1 a operação existia só em notas de sessão (`.remember/`), sem canônico.
> **Gate:** 14 dias de telemetria de fases — **verificado**, fecha 21/08.
> **Corte decidido 2026-08-15:** ~~A2~~ descartado (harness não é público), **A1 + A3 juntos**, A4 em canal separado depois. As duas verificações que o corte esperava (§2, ✅) estão feitas.

---

## 1. Por que agora — o gate é real

A Task #1 ("Stanford contact ~21/08") é *data-gated*, não *date-gated*: depende de 14 dias de coleta da telemetria de custo por fase (PR #40/#41).

**Verificado em prod 2026-08-13** (leitura direta do DB, read-only):

| | |
|---|---|
| `provider_telemetry` | **1.214 registros** |
| Por fase | query **1.121** · construction **62** · maintenance **31** |
| Primeiro registro | **2026-08-07** (~10h30 UTC) |
| Último | 2026-08-13 |
| Dias distintos com dados | 7 |

O encadeamento merge → pull → build fechou (a memória de 07/08 registrava risco de prod não coletar). **14 dias completam em 21/08** — a data estava bem dimensionada.

---

## 2. Os dois alvos, e por que são canais diferentes

### Alvo A — o paper de caracterização de sistemas

**arXiv:2606.06448** — *Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads* (Omri, Gan, Broveak, Geens, Zexue He, Alex Pentland, Verhelst, Weissman, Tambe; 04/06/2026).

Do abstract: *"first systems characterization of agent memory"*; taxonomia orientada a sistemas em **4 eixos**; um **phase-aware profiling harness attributing cost to construction, retrieval, and generation**; 10 sistemas representativos sobre 2 benchmark suites; 10 recomendações cobrindo *construction scheduling, capability floors, amortization via query volume, freshness-latency tradeoffs* e **fleet-scale management**.

**Por que isso é o alvo forte:** o PR #40/#41 instrumentou exatamente essa decomposição — nossas fases são `construction` / `query` / `maintenance` — mas **em produção contínua sobre uma fleet real**, não em bancada sobre benchmark suites. Eles caracterizaram 10 sistemas em ambiente controlado; nós temos o mesmo tipo de perfilamento rodando 24/7 num sistema em uso, e "fleet-scale management" é uma das próprias recomendações deles.

### ✅ Verificado 2026-08-15 — paper lido na íntegra

**(i) Os 4 eixos são `construction` · `storage` · `retrieval` · `mutability`.** A nota de 07/08 estava certa: *mutability* é um deles. A Tabela 1 dá três valores ao eixo — `append`, `consolidate`, `mutate` — e a distribuição é informativa: os três sistemas com `mutate` (A-Mem, Letta, MIRIX) são **todos** Paradigma IV, isto é, todos têm `Agent Ctrl ✓` — a mutação é decidida por um LLM em loop.

**(ii) O harness NÃO está público.** O texto diz *"(to be open-sourced)"* nas duas vezes em que o menciona — no §3.3 e na lista de contribuições. **A2 está morto por ora**, e a mensagem não pode pedir um ponteiro que ainda não existe. Vira, no máximo, uma frase de disponibilidade futura.

**(iii) Afiliações confirmadas: Stanford.** Correspondência `yomri@stanford.edu`; agradecimentos ao Stanford Marlowe computing cluster, ao Stanford PORTAL e ao programa de afiliados industriais MemoryDAX, e à Knight-Hennessy Fellowship. Verhelst e Geens são de outra instituição (índice 3); Pentland aparece com dupla afiliação (1,4).

### A célula vazia existe, e é mais concreta do que a conjectura

Não é só que nossa combinação de eixos não aparece — é que **os autores pedem explicitamente o que temos**, duas vezes:

> §2.1, sobre a etapa de manutenção: *"In many current systems, maintenance is weak or absent: memory accumulates indefinitely with no freshness or pruning policy, which becomes critical for long-lived agents…"*

> **Recomendação 9:** *"Because all evaluated systems accumulate state monotonically by default, operators must add independent pruning or forgetting policies to bound fleet-scale storage and token costs."*

**Nenhum dos dez sistemas caracterizados tem política de esquecimento.** O nox-mem tem: `retention_days` tipado por classe de conteúdo, decaimento por salience, `pruneEpochs`, `kg-prune`, `consolidate`. E tem algo que vale mais do que ter: **o registro de quando isso deu errado** — o decaimento com compounding que drenou o grafo de ~21,5k para 554 nós, com diagnóstico e recuperação documentados (`docs/INCIDENTS.md#2026-07-25`). Um operador que só afirma ter política de forgetting é menos crível que um que mostra a fatura de tê-la operado.

A posição precisa nos quatro eixos, para a mensagem: construção **mista** (determinística para FTS5/embeddings, LLM-mediada só no `kg-build`, amostrada); storage **multi-store** (SQLite + FTS5 + sqlite-vec + KG tipado); retrieval **híbrido** (BM25 + denso + RRF); mutability **`mutate`, mas sem controle agêntico** — a manutenção é cron determinístico, não decisão de LLM em loop. É essa última célula que a Tabela 1 não contém: mutabilidade de Paradigma IV com o perfil de custo de Paradigma III.

### Alvo B — o survey

**arXiv:2602.06052v4** (TMLR 07/2026). **James Zou** (co-supervisor) e **Wanjia Zhao** assinam, afiliação Stanford. A §9.6 nomeia como direção aberta o desenho que o Paper 2 pré-registra.

**Canal distinto do A**, com pessoas distintas. Não misturar numa mensagem só.

### O que liga os dois (e um alerta)

**Zexue He** e **Alex Pentland** assinam o alvo A **e** o MemoryArena (2602.16313). É o mesmo cluster. Consequência prática: qualquer mensagem que reivindique o gap "retrieval mede representação, não decisão" como observação nossa vai bater direto em quem publicou essa frase primeiro. Ver `paper2-interventional/RELATED-WORK.md` §4.

---

## 3. O ativo — o que temos que eles não têm

Ordenado por raridade, não por esforço:

1. **Telemetria de fases em produção contínua**, sobre uma fleet de 7 agentes, com custo e latência por fase. Caracterização de bancada não captura amortização real por volume de query nem o padrão de manutenção ao longo de semanas — e ambos estão entre as recomendações deles.
2. **Um experimento randomizado pré-registrado** rodando sobre essa mesma fleet (Paper 2), com seed declarada antes do round existir e outcome adjudicado por painel multi-modelo com κ registrado.
3. **Uma política de esquecimento em produção** — `retention_days` tipado, decay por salience, `pruneEpochs`, `kg-prune` — que é literalmente a **Recomendação 9** deles, e que **nenhum dos 10 sistemas caracterizados possui**. Com o incidente de 25/07 documentado: ter operado a política vale mais que anunciá-la.
4. **Um sistema completo, self-hosted, auditável**, com snapshots atômicos, audit log append-only e provenance por chunk — candidato a 11º sistema **quando** o harness for liberado.

**O que não temos:** afiliação, e um Paper 1 com ID público (arXiv em moderação, alto volume). O primeiro não muda; o segundo pode destravar a qualquer momento.

---

## 4. As 4 aproximações — RECONSTRUÍDAS, aguardando corte do Toto

⚠️ **As 4 originais foram sequenciadas em 07/08 e não sobreviveram em documento** — a nota registra que existiram, não o conteúdo. As abaixo são reconstrução a partir das 3 lacunas identificadas naquele dia (*write-path pricing*, *density metrics*, *invalidation cascade*) e do que se sabe hoje. **Ordem e corte são decisão do Toto.**

| # | Aproximação | Pedido concreto | Força | Risco |
|---|---|---|---|---|
| **A1** | **Dados de produção como complemento à caracterização.** "Vocês caracterizaram 10 sistemas em bancada; temos o mesmo perfilamento de fases rodando em produção há N dias numa fleet de 7 agentes. Interessa?" | Oferecer o dataset de telemetria de fases. Sem pedir nada em troca na primeira mensagem. | **Maior.** É o único ativo que ninguém replica sem operar um sistema em produção. Não depende do arXiv ID. Não toca no território do MemoryArena. | Nenhum óbvio. Pode simplesmente não haver resposta. |
| ~~**A2**~~ | ~~**Ser o 11º sistema no harness.**~~ **MORTO por ora (verificado 15/08):** o paper diz *"(to be open-sourced)"* — o harness **não existe publicamente**. | — | — | Não se pede ponteiro para o que não foi liberado. Sobrevive só como uma frase de disponibilidade futura dentro de A1. |
| **A3** | **A célula vazia — CONFIRMADA e mais forte que a conjectura (15/08).** Os 4 eixos são construction/storage/retrieval/**mutability**; nenhum dos 10 sistemas tem política de esquecimento, e a **Recomendação 9 deles pede exatamente isso**. | Mostrar `retention_days` tipado + decay + prune **e o incidente de 25/07** (decay com compounding drenou o grafo 21,5k→554, com recuperação documentada). | **Subiu para alta.** Deixou de ser conversa: é a recomendação deles já implementada, com a fatura de tê-la operado. | Nenhum. Não depende de arXiv ID nem do harness. |
| **A4** | **Via survey / James Zou.** A §9.6 descreve o desenho que já implementamos. | Diferente em natureza: é sobre o Paper 2, não sobre sistemas. Pessoas diferentes. | Média-alta, mas **outro canal e outro momento**. | Misturar com A1–A3 confunde a mensagem. Mandar depois, não junto. |

**Recomendação REVISTA após as verificações de 15/08:** **A1 + A3 na mesma mensagem, A2 descartado, A4 como canal separado depois.**

O que mudou: A2 morreu (harness não é público) e A3 subiu de "conversa" para "entrega", porque deixou de ser conjectura sobre uma célula vazia e virou *a Recomendação 9 deles, implementada e operada em produção, com incidente documentado*. A1 e A3 se reforçam — a telemetria de fases mostra o custo do write path em produção contínua; a política de forgetting mostra o que fazemos com o estado que esse write path acumula. São as duas metades da mesma coisa, e separá-las enfraquece as duas.

A mensagem segue **oferecendo, sem pedir nada** — a única mudança é que agora oferece duas coisas verificadas em vez de uma verificada e uma conjectural.

---

## 5. O que não escrever

- ❌ Não reivindicar que identificamos o gap de "memória guia decisão" — **é prior art do próprio grupo** (MemoryArena, 02/2026, com He e Pentland).
- ❌ Não citar o Paper 1 como "publicado" nem prometer link — está em moderação sem ID.
- ❌ Não pedir endosso, co-autoria ou revisão na primeira mensagem. A primeira mensagem **oferece**.
- ❌ Não enviar antes de 21/08: com menos de 14 dias, o número que sustenta A1 ainda não existe.

---

## 6. Antes de enviar — checklist

- [ ] 21/08: confirmar 14 dias completos de telemetria e extrair os números finais (custo/query, ratio de construction, custo de manutenção)
- [x] Ler **2606.06448** integralmente — ✅ 15/08. Eixos: construction/storage/retrieval/**mutability**. Célula vazia confirmada, e a Recomendação 9 pede o que temos.
- [x] Verificar se o harness é público e onde — ✅ 15/08. **Não é**: "(to be open-sourced)". A2 descartado.
- [x] Confirmar afiliações — ✅ Stanford (`yomri@stanford.edu`, Marlowe cluster, PORTAL/MemoryDAX, Knight-Hennessy). Falta decidir **para quem** escrever: correspondência é Omri, mas o cluster que liga ao MemoryArena é He/Pentland.
- [x] Toto: cortar e ordenar as aproximações do §4 — ✅ 15/08, **A1 + A3**.
- [ ] Redigir a mensagem de A1 e revisar contra o §5

---

## Proveniência

- Gate verificado por leitura direta do `provider_telemetry` em prod, 2026-08-13.
- 2606.06448 lido **na íntegra** 2026-08-15 (eixos, harness, afiliações, Recomendação 9). 2602.16313 lido na íntegra 2026-08-15 — ver `paper2-interventional/RELATED-WORK.md` §4.
- As 4 aproximações originais de 07/08 estão perdidas; estas são reconstrução declarada.
- Contexto do survey: memória `[[project_agent_memory_survey_tmlr_2602_06052]]`; posicionamento: `paper2-interventional/RELATED-WORK.md`.
