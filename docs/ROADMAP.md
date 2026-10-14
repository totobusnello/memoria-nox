# nox-mem ROADMAP v6 — o produto real primeiro

> **"Pain-weighted hybrid memory with shadow discipline — yours by design."**
>
> **v6, 2026-10-14.** Reescrito depois de uma auditoria que cruzou o v5 com o código de
> produção, com o pacote npm `nox-mem@3.5.1` e com o banco de produção. Parte do que o v5
> marcava como SHIPPED só existia nos harnesses de eval; o `compact` apagava conteúdo toda semana
> sem decisão registrada; o KG estava saturado. O v5 está intacto em
> `docs/_archive/ROADMAP-v5-pre-v6-2026-10-14.md` (e o v1 em `ROADMAP-v1-pre-Q-A-P-2026-05-17.md`).
>
> Estado vivo e próxima ação: `docs/HANDOFF.md`. Porquês e NÃO FAZEMOS: `docs/DECISIONS.md`.

---

## 0. Princípios (valem para todo item abaixo)

1. **O roadmap descreve o que o usuário instala.** Uma feature só é "no produto" quando a flag ou
   o código existe no src de produção **e** no pacote npm. Conferir com `grep`, nunca de memória.
   O que só roda num harness de eval é **resultado de pesquisa**, e é chamado assim.
2. **O índice aponta para o original, nunca o substitui.** Resumo, entidade e relação do KG são
   endereços para a evidência bruta, que continua no banco (NÃO FAZEMOS #32; EnSIMem, 2026).
3. **Esquecer é rebaixar com métrica, nunca apagar sem medida.** Deleção só por decisão
   explícita, com dry-run, snapshot e validação pós-op (regra 6 do `CLAUDE.md`).
4. **Um contador conta efeito, não tentativa.** O `kg-build` logava "Built: 705 relations" e
   inseria zero. Guarda que conta tentativa é guarda que mente (catálogo "como um guarda mente").
5. **Acurácia nunca sai sozinha:** todo número de qualidade vem com custo e latência ao lado.
6. **Gate de ranking:** shadow ≥ 7 d, 5 batches com IC 95%, **mais uma rodada A/A** para medir o
   chão de ruído antes de ler qualquer diferença (Recuris, 2026: A/A mexeu ±7 pontos).

---

## 1. Estado medido (2026-10-14, fim do dia)

| o quê | valor | fonte |
|---|---|---|
| chunks | **52.928** (43.284 antes das restaurações de 14/10: +182 arquivos em disco, +27 arquivos de backup) | `/api/health` |
| vetores | 52.928/52.928, 0 órfãos, **todos `RETRIEVAL_DOCUMENT`** (919 trocados) | `/api/health`, `ops_audit` 356 |
| entity sections | `compiled == frontmatter == 239` | `/api/health` |
| chunks sem tipo (`other`) | ~67% do corpus | `/api/health` (13/10) |
| KG | 15.620 entidades / 17.753 relações; extração LLM parada desde 16/05 → cobre ~7% do corpus | D-2026-10-14 |
| buscas | 681 em 14 dias, média **1.081 ms**, sem cache de embedding da query | `search_telemetry` |
| quem busca | `requesting_agent` gravado desde 14/10 (`<superfície>:<agente>`, `probe:*`); os agentes ainda não se identificam → `*:unknown` | nox-workspace#55 |
| `compact` | **pausado** (`/root/.openclaw/DISABLE_COMPACT`); 1 resumo restante (waiver da Nuvini, sem backup anterior) | openclaw-vps#45 |
| npm | **`nox-mem@3.5.2` = latest** (fix de embedding; shasum `0f615820`) | nox-mem#41 |

---

## 2. O que o produto tem, contra o que o discurso dizia

| item | produção (`nox-workspace`) | npm `nox-mem@3.5.2` | v5 dizia |
|---|---|---|---|
| busca híbrida FTS5 + Gemini + RRF, boost stack, salience v2 | ✅ | ✅ | ✅ |
| `/api/brief`, `/api/answer` com citação, privacy filter no ingest | ✅ | ✅ | ✅ |
| KG path, multi-query, MA-protection, classificador adaptativo, RRF por idioma, IterB, Self-Ask | ❌ (só `eval/evermembench/`) | ❌ | "SHIPPED opt-in" |
| `NOX_TEMPORAL_BOOST_MODE` | removida do `.env` em 14/10 (módulo só importado pelo teste) | ❌ | ativo |
| `NOX_TEMPORAL_PATH=active` | existe, mas não muda o ranking (`search.ts:722`) | — | D49/D50 → NÃO FAZEMOS #33 (D-2026-10-14b) |
| troca de provider de embedding (A3) | ❌ (Gemini direto no `embed.ts`) | ✅ `NOX_EMBEDDING_PROVIDER` | ✅ |
| A2 export/import, P4 `nox-mem connect` | ❌ | ❌ | staged / spec |
| abstenção (piso de confiança) | ❌ | ❌ | S2 gated |

README, `CONFIGURATION.md`, `COMPARISON.md` e `COMPETITIVE-POSITIONING.md` corrigidos em 14/10
(memoria-nox#577): os números de eval continuam lá, rotulados como do harness de pesquisa.

---

## 3. Prioridades

### Feito em 2026-10-14

- **`compact` pausado; 182 arquivos restaurados; 681 relações do KG com evidência de volta.**
  `D-2026-10-14`, openclaw-vps#45, memoria-nox#575.
- **Embedding de documento como `RETRIEVAL_DOCUMENT`** no ingest e no `crystallize`
  (nox-mem#40, nox-workspace#54) + passada que trocou os **919** vetores embedados como
  pergunta (`ops_audit` 356). Publicado no npm 3.5.2.
- **27 arquivos compactados sem disco restaurados** do backup de 28/04 (`ops_audit` 357,
  filtro de privacidade reaplicado).
- **Item 1 (discurso = produto): docs feitos** (memoria-nox#577), flag morta fora do `.env`.
  Decisão knob a knob: nenhum port agora; todos ficam como resultado de pesquisa.
- **Item 2 (quem busca): escritor em produção** (nox-workspace#55). Falta os agentes se
  identificarem (amanhã, junto com o item 3).
- **D49/D50 decidido** pelo Toto: rerank temporal implícito entra no NÃO FAZEMOS (#33).

### Plano aprovado pelo Toto (executado a partir de 2026-10-14)

1. Conferir o `kg-confirm` das 23:00 UTC de 14/10 (`evidence_gone` ~85, era 753).
2. ✅ **Item 3 (escrita sem perda)**, inteiro: em produção desde 2026-10-14 14:34 UTC
   (nox-mem#42 `95ccf0ea`, nox-workspace#56 `9a509eab`; D-2026-10-14c).
3. **Item 2, fecho:** agentes mandam `X-Agent-Name` (HTTP) / `NOX_AGENT_NAME` (MCP).
4. **D49/D50, execução:** tirar o drop-in `NOX_TEMPORAL_PATH=shadow`; dar escritor ao
   `was_temporal_query` (gatilho de reabertura do #33). Portar o `requesting_agent` para o npm.

### Fila, em ordem

| # | item | por quê | primeiro passo / gate |
|---|---|---|---|
| **1** ✅ docs | **Discurso = produto.** README, COMPARISON e POSITIONING só citam o que o npm tem; flags mortas saem do `.env`; decidir, knob a knob, entre portar e rebaixar a "resultado de pesquisa" (o KG path é SQL puro e o candidato natural a port, mas o D75 mediu −0,01pp no Gemini) | O GTM é em novembro e o diferencial declarado é honestidade de trade-off | lista feita na §2; PR de docs + release 3.5.2 do npm com o nox-mem#40 |
| **2** ◐ escritor feito | **Telemetria de quem busca**: gravar `requesting_agent` e marcar sonda vs agente | Na data note, 62,8% das consultas eram sondas; sem isso nenhuma prioridade de retrieval tem base | coluna já existe; falta o escritor + teste que proteja (regra 12) |
| **3** ✅ prod 14/10 | **Escrita sem perda** (D-2026-10-14c; ainda abertos: `mark.ts` escreve `superseded_by` sem migração, `SCHEMA_VERSION` 18 vs "v22" nos docs): (a) NOOP por hash de conteúdo, reaproveitando vetor e **id** quando o texto não mudou; (b) tombstone soft em delete/rename (rebaixa e lista para revisão, nunca apaga sozinho, respeitando o D-2026-09-30); (c) `ingestFile` parar de fechar o handle do `getDb()` | Hoje regravar um arquivo recria todos os chunks com ids novos e quebra `brief_log`, telemetria e evidência do KG; rename deixa duplicata | a conferir junto: `reindex` com `skipDelete` pode duplicar markdown; `mark.ts` escreve `superseded_by`, coluna que nenhuma migração cria; `SCHEMA_VERSION = 18` no código contra "v22" nos docs |
| **4** | **KG como endereço.** S1 (precisão amostrada, n ≥ 100) → decidir extração LLM sobre os ~93% não cobertos (poucos dólares com flash-lite) → usar o KG para apontar chunks, não para substituí-los. `kg-build` passa a logar inserções; resíduo de teste (`test_a`, `test_b`, `alpha`, `beta`) sai | O grafo está saturado e as vault facts (`active`) servem 3 triplas por busca de um grafo velho | S1 antes de qualquer extração; o D64 trata do KG do eval, não deste |
| **5** | **Esquecimento com métrica**: `retention_days` passa a rebaixar no ranking (shadow 7 d) ou sai do discurso. (Os 28 arquivos sem disco: 27 restaurados em 14/10; 1 ficou como resumo.) | Retenção hoje é decorativa: nenhum código age sobre ela | — |
| **6** | **Latência**: cache de embedding da query; meta p95 < 500 ms | Média de 1.081 ms por busca | depois do item 2, para não otimizar sonda |
| **7** | **O brief serve?** Sonda de ação (o agente age certo sem que perguntem, à la DolphinBench) e tamanho do brief (Recuris: mais itens no prompt rendeu menos) | É o carro-chefe do pilar P; o Paper 2 não detectou efeito da dose | depende do item 2 |
| **8** | **Abstenção (S2)**: checagem de suficiência da evidência como piso do `/api/answer` | Hoje o answer sempre responde se houver qualquer match | negativas vêm do item 9 |
| **9** | **Golden set PT-BR** com filtro oráculo: a query entra só se a resposta passa com o chunk-fonte e falha sem ele | O corpus é majoritariamente português; condição (b) do D-2026-09-21c | 50 candidatas, rodar com/sem fonte |
| **10** | **Procedural (S3)**: injetar procedimento no momento da chamada de ferramenta, ranquear por taxa de sucesso (`validateProcedure` já grava desfechos), medir alcance | Só existem 3 procedimentos; o distill descarta tool_use | capturar trajetórias reabre o P2 autocapture (GATED, NÃO FAZEMOS §1) |
| **11** | **Confiança por chunk (S5)**: `confidence` e `provenance_kind` já existem em `chunks` e ninguém lê; ler no ranking ou remover | Decidir antes do próximo bump de schema | — |

### Lab (pesquisa, não produto)

- **Unidade de chunk por tema** (EnSIMem: agrupar trechos do mesmo tema bateu o recorte por
  turno). Rechunkar um subconjunto e medir no golden set.
- **Mapa por diretório** (JAM: memo por arquivo + README por pasta, +3 F1 e menos latência).
  Os memos seriam chunks **ao lado** dos originais: a forma de resumo que o NÃO FAZEMOS #32
  deixa aberta. Candidato a "modo profundo" opt-in do `/api/answer`.
- **Grid search dos pesos da salience v2** (desenho no PR #169).

### Fechado sem fazer

- **D49/D50 (temporal path) → NÃO FAZEMOS #33** (D-2026-10-14b). O produto temporal são os
  filtros explícitos `--as-of` / `--changed-since`. Reabre só com (a) fração relevante de buscas
  reais com expressão temporal, medida pelo `was_temporal_query`, **e** (b) gold temporal em que
  o rerank implícito vence o filtro explícito.

---

## 4. GTM Phase 2 — novembro/2026

Continua no calendário. Os dois pré-requisitos foram cumpridos em 14/10: docs = produto (#577) e
npm 3.5.2 publicado. Assets, pricing Stripe-first (D44) e `COMPARISON.md` existem desde
maio; o `COMPARISON.md` passa a reportar acurácia **com** custo e latência (princípio 5).

---

## 5. Saiu do roadmap (fica como registro de pesquisa)

IterB e Self-Ask (Q3 iterative retrieval), matriz de backbones, capstone da Wave 2 (D76),
E15 CodeGraph (L1), reranker no caminho default (D-2026-09-21c), Docker (removido em 29/09),
MMR na `/api/search` (o `search-dedup` já tem 4 camadas, incluindo Jaccard). Os números
continuam válidos onde foram publicados (Paper 1, `COMPARISON.md` como eval), só não são
features do produto.

---

## 6. Ponteiros

| conteúdo | arquivo |
|---|---|
| estado vivo + próxima ação | `docs/HANDOFF.md` |
| decisões + NÃO FAZEMOS | `docs/DECISIONS.md` |
| regras operacionais | `CLAUDE.md` |
| visão de longo prazo | `docs/VISION.md` |
| roadmap anterior (v5) | `docs/_archive/ROADMAP-v5-pre-v6-2026-10-14.md` |
| papers lidos em 13/10 | EnSIMem (UIUC/Amazon), JAM (BAAI/PKU), Recuris (NUS/Princeton/Stanford/Oxford), DolphinBench (Mem0), Metis (MemTensor); citados nos itens acima |
