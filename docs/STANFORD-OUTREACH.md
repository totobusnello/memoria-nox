# Stanford — aproximação de colaboração

> **Status:** v0.1, 2026-08-13. Documento operacional. Antes disto, a operação existia só em notas de sessão (`.remember/`), sem canônico.
> **Gate:** 14 dias de telemetria de fases — **verificado**, fecha 21/08.
> **Decisão pendente do Toto:** ordem e corte das 4 aproximações (§4).

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

⚠️ **A confirmar antes do contato:** (i) quais são os 4 eixos da taxonomia — a nota de 07/08 diz que *mutability* é um deles e que seria "nossa célula vazia", mas isso não foi verificado contra o paper; (ii) se o harness foi de fato open-sourced e onde; (iii) afiliações — Tambe e Weissman são Stanford EE pelo que sei, mas a página do abstract não lista afiliação e isso não foi confirmado.

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
3. **Um sistema completo, self-hosted, auditável**, com snapshots atômicos, audit log append-only e provenance por chunk — que pode ser o 11º sistema no harness deles.

**O que não temos:** afiliação, e um Paper 1 com ID público (arXiv em moderação, alto volume). O primeiro não muda; o segundo pode destravar a qualquer momento.

---

## 4. As 4 aproximações — RECONSTRUÍDAS, aguardando corte do Toto

⚠️ **As 4 originais foram sequenciadas em 07/08 e não sobreviveram em documento** — a nota registra que existiram, não o conteúdo. As abaixo são reconstrução a partir das 3 lacunas identificadas naquele dia (*write-path pricing*, *density metrics*, *invalidation cascade*) e do que se sabe hoje. **Ordem e corte são decisão do Toto.**

| # | Aproximação | Pedido concreto | Força | Risco |
|---|---|---|---|---|
| **A1** | **Dados de produção como complemento à caracterização.** "Vocês caracterizaram 10 sistemas em bancada; temos o mesmo perfilamento de fases rodando em produção há N dias numa fleet de 7 agentes. Interessa?" | Oferecer o dataset de telemetria de fases. Sem pedir nada em troca na primeira mensagem. | **Maior.** É o único ativo que ninguém replica sem operar um sistema em produção. Não depende do arXiv ID. Não toca no território do MemoryArena. | Nenhum óbvio. Pode simplesmente não haver resposta. |
| **A2** | **Ser o 11º sistema no harness.** Quando/se o harness for público, rodar o nox-mem nele e devolver os resultados — incluindo os casos em que perdemos. | Pedir o ponteiro do harness; oferecer rodar e publicar o resultado íntegro. | Alta. Custo baixo pra eles, sinal de boa-fé forte. | Depende de o harness ser público — **não verificado**. |
| **A3** | **A célula vazia da taxonomia de 4 eixos** (*mutability*, se a nota estiver certa). | Discussão técnica: onde o nox-mem cai nos 4 eixos e por que a célula está vazia. | Média. Interessante, mas é conversa, não entrega. | **Depende de ler o paper** — hoje é conjectura baseada numa nota. |
| **A4** | **Via survey / James Zou.** A §9.6 descreve o desenho que já implementamos. | Diferente em natureza: é sobre o Paper 2, não sobre sistemas. Pessoas diferentes. | Média-alta, mas **outro canal e outro momento**. | Misturar com A1–A3 confunde a mensagem. Mandar depois, não junto. |

**Recomendação:** **A1 primeiro, sozinho.** É o único que não depende de nada não-verificado, não depende do arXiv ID, e oferece antes de pedir. A2 entra na mesma mensagem só se a checagem do harness confirmar que é público. A3 depois de ler o paper. A4 como canal separado, depois.

---

## 5. O que não escrever

- ❌ Não reivindicar que identificamos o gap de "memória guia decisão" — **é prior art do próprio grupo** (MemoryArena, 02/2026, com He e Pentland).
- ❌ Não citar o Paper 1 como "publicado" nem prometer link — está em moderação sem ID.
- ❌ Não pedir endosso, co-autoria ou revisão na primeira mensagem. A primeira mensagem **oferece**.
- ❌ Não enviar antes de 21/08: com menos de 14 dias, o número que sustenta A1 ainda não existe.

---

## 6. Antes de enviar — checklist

- [ ] 21/08: confirmar 14 dias completos de telemetria e extrair os números finais (custo/query, ratio de construction, custo de manutenção)
- [ ] Ler **2606.06448** integralmente — confirmar os 4 eixos e a tal célula vazia
- [ ] Verificar se o harness é público e onde
- [ ] Confirmar afiliações e o canal de contato correto
- [ ] Toto: cortar e ordenar as aproximações do §4
- [ ] Redigir a mensagem de A1 e revisar contra o §5

---

## Proveniência

- Gate verificado por leitura direta do `provider_telemetry` em prod, 2026-08-13.
- 2606.06448 e 2602.16313 lidos **no nível de abstract**, não integralmente.
- As 4 aproximações originais de 07/08 estão perdidas; estas são reconstrução declarada.
- Contexto do survey: memória `[[project_agent_memory_survey_tmlr_2602_06052]]`; posicionamento: `paper2-interventional/RELATED-WORK.md`.
