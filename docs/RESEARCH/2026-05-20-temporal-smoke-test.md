# Smoke Test — Temporal Proximity Rerank vs Baseline

**Data:** 2026-05-20
**Branch:** `research/temporal-smoke-2026-05-20`
**Spike PR:** #157 (`staged-temporal-spike/edits/temporal-retrieval.ts`)
**Gold PR:** #159 (Q87 + Q88 curados)
**Status:** R&D — read-only contra prod VPS, zero mutação

## TL;DR

Smoke test de 4 queries temporais (Q70/Q71/Q87/Q88) contra `/api/search` prod
mostra que **proximity rerank simulado NÃO melhora ranking em nenhuma query**
no estado atual. Causas distintas por query — ceiling effect (Q87/Q88), gold
drift (Q70), tie-break perdido por score absoluto (Q71). Decisão: **NÃO ir pra
implementação real ainda**. Caminho viável requer: (a) revalidar com queries
onde gold NÃO está em rank 1-2, (b) tornar boost proporcional ao gap de score,
(c) wire `source_date` real do DB (não regex sobre `chunk_text`).

## Setup

- **API:** `POST http://127.0.0.1:18802/api/search` com `limit=20` via SSH read-only
- **Modo simulado:** mirror em Node.js de `detectTemporal()` + `proximityDelta()`
  + `rerankByTemporalProximity()` (staged-temporal-spike/edits/temporal-retrieval.ts)
- **Parâmetros:** `sigmaDays=30`, `kRerank=20`, mode=active (`score + delta*10`)
- **Fonte de data do chunk:** primeiro match `\d{4}-\d{2}-\d{2}` em `chunk_text`
  (proxy — API não expõe `source_date` populado em todos os chunks; ~maioria
  retorna `source_date:null`)
- **nDCG@10:** fórmula clássica `DCG/IDCG` com relevance binário (1 se gold,
  0 caso contrário)

## Queries avaliadas

Identificadas via `grep "temporal" eval/golden-queries.jsonl` — 4 matches:

| QID | Query | Gold chunk | Difficulty |
|-----|-------|-----------|------------|
| 70 | "quando o salience foi ativado" | 117852 | easy |
| 71 | "qual a primeira lição do incident reindex 2026-04-25" | 117767 | hard |
| 87 | "quando o E05 edge typing foi deployado" | 216203 | easy |
| 88 | "quando subiu o schema v12" | 216204 | easy |

## Resultados

| Query | Intent | Anchor | Baseline rank | Rerank rank | Baseline nDCG@10 | Rerank nDCG@10 | Δ |
|-------|--------|--------|---------------|-------------|------------------|----------------|---|
| Q70 | adverbial | none | **not in top-20** | **not in top-20** | 0.0000 | 0.0000 | 0.0000 |
| Q71 | iso_date | 2026-04-25 | 2 | 2 | 0.6309 | 0.6309 | 0.0000 |
| Q87 | adverbial | none | **1** | 1 | 1.0000 | 1.0000 | 0.0000 |
| Q88 | adverbial | none | **1** | 1 | 1.0000 | 1.0000 | 0.0000 |

**nDCG@10 mean baseline:** 0.6577
**nDCG@10 mean rerank:** 0.6577
**Δ médio:** **0.0000 (+0.0%)**

## Análise por query

### Q70 — "quando o salience foi ativado" (gold drift)

Gold chunk `117852` **não aparece no top-20**. API retorna chunk `216199` em
posição 1, conteúdo equivalente:

> `**2026-04-30** — [gate] G01 salience activation `recency × pain × importance` at...`

Diagnóstico: gold chunk foi superseded por re-ingest da entity (`memory/entities/
systems/nox-mem.md` recompilada). Chunk_id drift conhecido (CLAUDE.md memo).
Proximity rerank não pode resgatar gold que não está no candidate pool.

**Ação:** atualizar gold em `golden-queries.jsonl` linha 26 → `216199`
(fora do escopo deste smoke; sugestão pra Q4 gate).

### Q71 — "qual a primeira lição do incident reindex 2026-04-25" (tie-break perdido)

Gold `117767` em rank 2 baseline (score 16.13). Chunk em rank 1: `117769`
(score 16.39), mesma família (lesson Forge fake-green, 2026-04-19).

Após rerank: gold continua rank 2 — proximity delta gaussiano (sigma=30d)
entre anchor `2026-04-25` e:
- 117769 (date 2026-04-19, Δ=6d) → delta≈0.4917, boost +4.917
- 117767 (date 2026-04-18, Δ=7d) → delta≈0.4884, boost +4.884

Diferença de 0.033 em delta < diferença de 0.26 no score original. Boost
absoluto multiplicado por 10 ainda fica abaixo do gap necessário pra flipar
rankings de chunks no mesmo cluster temporal.

**Observação interessante:** chunk `216196` (date 2026-04-25 — **match
perfeito** do anchor) ficou em rank 3 baseline. Após rerank com delta=0.5,
score sobe pra 20.87 mas ainda fica abaixo do 21.31 do 117769. Boost
absoluto+10 não é forte o suficiente quando score base original é dominante.

### Q87 + Q88 — ceiling effect

Gold já em rank 1 baseline. Rerank não pode melhorar (top-1 já é o
chunk-alvo). Boosts aplicados corretamente mas inócuos. Δ=0 por construção.

Esse cenário valida que o detector **identifica corretamente as queries
adverbiais** (signal `"deployado"`, `"subiu"` matched). Falha não está na
detecção — está na arquitetura do boost quando o pipeline base já acerta.

## Observações cruzadas

1. **`source_date` ausente em 90%+ dos chunks** retornados. Mesmo chunks com
   data clara no texto retornam `source_date: null`. O spike depende desse
   campo (`r.source_date ?? r.created_at ?? null`). Implementação real
   precisa do fallback `extractChunkDate(chunk_text)` que eu usei aqui ou
   backfill no schema.

2. **Boost gaussiano com sigma=30d gera deltas muito próximos** pra chunks
   no mesmo mês (típico em clusters de incident/lesson). O `delta*10`
   adiciona +4 a +5 em scores baseline de ~16. Inferior à variação de
   ~0.26 entre chunks adjacentes — ineficaz pra discriminar tie-breaks.

3. **Adverbial-only sem anchor** (Q70/Q87/Q88) cai no fallback de "qualquer
   data recente boost", que é heurística fraca. O E13 spec original delega
   adverbial pra outra camada — confirmado que faz sentido.

## Decisão

**NÃO ir pra implementação real (active mode) ainda.** Justificativa:

1. 4 queries com ceiling effect ou gold drift = sinal insuficiente
2. Único caso testável real (Q71) mostra que boost atual não vira ranking
3. Sample size muito pequeno; queries que efetivamente exercem o path
   (gold em rank 5-10, anchor explícito, mesma decade temporal disponível
   no candidate pool) ainda não existem no golden set

**Próximos passos sugeridos** (em ordem):

1. **Curar 6-8 queries adicionais** onde gold cai entre rank 5-15 baseline
   e há ISO date explícito na query → teste real de lift
2. **Re-medir gold drift Q70** — atualizar pra 216199 e validar baseline rank
3. **Tornar boost proporcional ao gap de score** entre top-1 e candidato:
   `score_new = score_old + delta * (top1_score - own_score) * factor`
4. **Wire `source_date` real** ou aceitar `extractChunkDate` como fallback
5. **Considerar shadow-mode em prod** após ajustes — coletar telemetria por
   1 semana antes de active

Decisão final: **spike fica em #157 staged**, smoke é evidence pra rejeitar
merge precipitado e pra refinar o experimento antes de Q4 gate.

## Artefatos

- Script de análise: `/tmp/temporal-smoke/analyze.mjs` (não comitado, scratch)
- JSON raw das 4 queries: `/tmp/temporal-smoke/q{70,71,87,88}.json`
- Results estruturado: `/tmp/temporal-smoke/results.json`
- Spike implementation: `staged-temporal-spike/edits/temporal-retrieval.ts`
- Spec: `specs/temporal-retrieval-path-spike.md`
- Golden file: `eval/golden-queries.jsonl` (linhas 26, 27, 43, 44)

---

*Conduzido por executor-high em ~25min de wall-clock, read-only contra prod.
Time-box respeitado.*
