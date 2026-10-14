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

## 1. Estado medido (2026-10-14)

| o quê | valor | fonte |
|---|---|---|
| chunks | **49.511** (43.284 antes da restauração de 14/10) | `/api/health` |
| vetores | 49.511/49.511, 0 órfãos | `/api/health` |
| entity sections | `compiled == frontmatter == 239` | `/api/health` |
| chunks sem tipo (`other`) | ~67% do corpus | `/api/health` (13/10) |
| KG | 15.620 entidades / 17.753 relações; extração LLM parada desde 16/05 → cobre ~7% do corpus | D-2026-10-14 |
| buscas | 681 em 14 dias, média **1.081 ms**, sem cache de embedding da query | `search_telemetry` |
| quem busca | **desconhecido**: `requesting_agent` é NULL em 100% das linhas | `search_telemetry` |
| embeddings como pergunta | 2,6% de uma amostra de 1.000 (corrigido no código em 14/10; passada de troca em curso) | censo 13/10 |
| `compact` | **pausado** (`/root/.openclaw/DISABLE_COMPACT`) | openclaw-vps#45 |

---

## 2. O que o produto tem, contra o que o discurso dizia

| item | produção (`nox-workspace`) | npm `nox-mem@3.5.1` | v5 dizia |
|---|---|---|---|
| busca híbrida FTS5 + Gemini + RRF, boost stack, salience v2 | ✅ | ✅ | ✅ |
| `/api/brief`, `/api/answer` com citação, privacy filter no ingest | ✅ | ✅ | ✅ |
| KG path, multi-query, MA-protection, classificador adaptativo, RRF por idioma, IterB, Self-Ask | ❌ (só `eval/evermembench/`) | ❌ | "SHIPPED opt-in" |
| `NOX_TEMPORAL_BOOST_MODE` | flag no `.env`, módulo só importado pelo teste | ❌ | ativo |
| `NOX_TEMPORAL_PATH=active` | existe, mas não muda o ranking (`search.ts:722`) | — | D49/D50 pendente |
| troca de provider de embedding (A3) | ❌ (Gemini direto no `embed.ts`) | ✅ `NOX_EMBEDDING_PROVIDER` | ✅ |
| A2 export/import, P4 `nox-mem connect` | ❌ | ❌ | staged / spec |
| abstenção (piso de confiança) | ❌ | ❌ | S2 gated |

O README, o `COMPARISON.md` e o `COMPETITIVE-POSITIONING.md` ainda mandam ligar
`NOX_KG_PATH_ENABLED=1` e destacam "KG path 2.5 ms p50". O item 1 abaixo corrige isso.

---

## 3. Prioridades

### Feito em 2026-10-14

- **`compact` pausado; 182 arquivos restaurados; 681 relações do KG com evidência de volta.**
  `D-2026-10-14`, openclaw-vps#45, memoria-nox#575.
- **Embedding de documento como `RETRIEVAL_DOCUMENT`** no ingest e no `crystallize`
  (nox-mem#40, nox-workspace#54, em produção). Falta a passada que troca os vetores antigos
  embedados como pergunta (ver HANDOFF).

### Fila, em ordem

| # | item | por quê | primeiro passo / gate |
|---|---|---|---|
| **1** | **Discurso = produto.** README, COMPARISON e POSITIONING só citam o que o npm tem; flags mortas saem do `.env`; decidir, knob a knob, entre portar e rebaixar a "resultado de pesquisa" (o KG path é SQL puro e o candidato natural a port, mas o D75 mediu −0,01pp no Gemini) | O GTM é em novembro e o diferencial declarado é honestidade de trade-off | lista feita na §2; PR de docs + release 3.5.2 do npm com o nox-mem#40 |
| **2** | **Telemetria de quem busca**: gravar `requesting_agent` e marcar sonda vs agente | Na data note, 62,8% das consultas eram sondas; sem isso nenhuma prioridade de retrieval tem base | coluna já existe; falta o escritor + teste que proteja (regra 12) |
| **3** | **Escrita sem perda**: (a) NOOP por hash de conteúdo, reaproveitando vetor e **id** quando o texto não mudou; (b) tombstone soft em delete/rename (rebaixa e lista para revisão, nunca apaga sozinho, respeitando o D-2026-09-30); (c) `ingestFile` parar de fechar o handle do `getDb()` | Hoje regravar um arquivo recria todos os chunks com ids novos e quebra `brief_log`, telemetria e evidência do KG; rename deixa duplicata | a conferir junto: `reindex` com `skipDelete` pode duplicar markdown; `mark.ts` escreve `superseded_by`, coluna que nenhuma migração cria; `SCHEMA_VERSION = 18` no código contra "v22" nos docs |
| **4** | **KG como endereço.** S1 (precisão amostrada, n ≥ 100) → decidir extração LLM sobre os ~93% não cobertos (poucos dólares com flash-lite) → usar o KG para apontar chunks, não para substituí-los. `kg-build` passa a logar inserções; resíduo de teste (`test_a`, `test_b`, `alpha`, `beta`) sai | O grafo está saturado e as vault facts (`active`) servem 3 triplas por busca de um grafo velho | S1 antes de qualquer extração; o D64 trata do KG do eval, não deste |
| **5** | **Esquecimento com métrica**: `retention_days` passa a rebaixar no ranking (shadow 7 d) ou sai do discurso. Decidir os 28 arquivos de `memory/` compactados que já não existem em disco (3.448 chunks, só em backup) | Retenção hoje é decorativa: nenhum código age sobre ela | decisão de conteúdo (Toto) para os 28 |
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

### Fechar sem fazer

- **D49/D50 (temporal path):** o modo `active` não muda ranking. Ou se implementa de verdade
  com gate, ou entra no NÃO FAZEMOS. Decidir junto com o item 1.

---

## 4. GTM Phase 2 — novembro/2026

Continua no calendário, **depois** do item 1 (discurso = produto) e com o npm 3.5.2 publicado
(o nox-mem#40 entra nele). Assets, pricing Stripe-first (D44) e `COMPARISON.md` existem desde
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
