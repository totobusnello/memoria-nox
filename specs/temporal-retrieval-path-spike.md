# Temporal Retrieval Path — Q1 R&D Spike

> Spike paralelo (não bloqueia features atuais). Investiga camada de **proximity-rerank temporal** complementar a E13 (section-boost flip). Disparado pela surpresa #5 da G4 ablation (2026-05-19) onde queries temporais zeram nDCG e Q2 full results 2026-05-19 confirmaram multi-session/temporal como weak spot persistente (0.84–0.85 enquanto knowledge-update bate 1.0).

**Status:** Research spike — design + spike isolado, **não deploy**
**Branch:** `research/temporal-q1-spike-2026-05-20`
**Owner:** Q1 Lab (40% capacity, retrieval research)
**Data:** 2026-05-20
**Cross-ref:** `specs/2026-05-06-E13-temporal-aware-ranking.md` (section-boost flip — abordagem complementar)

---

## 1. Problema (calibrado pelos números reais)

Você tem 4 queries no `eval/golden-queries.jsonl` marcadas `category: "temporal"` (Q70/Q71/Q87/Q88). 2 dessas 4 têm `expected_chunk_ids=[]` (gold vazio — E13 já flagged). Nas 2 curadas, nDCG@10 = 0.466 média (E13 análise). Q2 LongMemEval full n=100: multi-session/temporal = 0.84–0.85 vs knowledge-update 1.0. G4 ablation surpresa #5: queries temporais zeraram nDCG em alguns sub-buckets.

**Hipótese da E13:** o problema é a *demote* de `section=timeline` (×0.8) — onde info temporal mora. Solução: flip de `SECTION_BOOST` quando query é temporal.

**Hipótese complementar deste spike:** nem todos os chunks têm `section=timeline` (NULL = 68.246 chunks = 98.9% do corpus em audit 2026-05-19). Pra esses, E13 não resolve. **Existe sinal extra em `source_date` / `created_at` que pode rerankear quando a query referencia um instante específico** (ex: "schema v12 em abril", "incident 2026-04-25").

**Lente:** este spike é a perna *proximity rerank* do problema; E13 é a perna *section flip*. Os dois compõem o "temporal retrieval path" completo. Se ambos passarem shadow, ativam juntos.

---

## 2. Design

### 2.1 Temporal intent detector

Dois sinais ortogonais que disparam o path:

1. **Adverbial/verbal** (regex herdado E13): `quando`, `que dia`, `primeira/última`, `deploy(ed/ado)`, `ativ(ou/ado)`, `subiu`, `started`, `before/after/during/in`, etc.
2. **Anchor temporal explícito**: ISO date (`2026-04-25`), mês+ano (`abril 2026`, `April 2026`), trimestre (`Q1 2026`), ano isolado (`2026`).

Detector retorna `{ isTemporal: boolean, anchor: Date | null, anchorRange: [start, end] | null }`. Sem anchor → fallback puro pra E13 path (sem rerank por proximity, só section flip). Com anchor → ativa proximity rerank desta camada.

### 2.2 Proximity rerank (camada nova, este spike)

Após FTS5 + semantic + RRF rodarem normalmente, **se** `isTemporal && anchor`:

- Top-K (K=20, configurável) é reordenado por uma função aditiva (regra crítica #5):
  ```
  boostSum += proximityDelta(chunk.source_date ?? chunk.created_at, anchor)
  ```
- `proximityDelta` é uma gaussiana truncada: `0.5 * exp(-Δdays² / (2σ²))` com σ=30 dias (configurável via `NOX_TEMPORAL_SIGMA_DAYS`).
- Chunks sem `source_date` E sem `created_at` → delta = 0 (não penalizar — princípio "missing data ≠ negative signal").
- Anchor range (mês/trimestre) → usa midpoint do range pra Δdays.

### 2.3 Env opt-in (shadow discipline — regra #6)

```
NOX_TEMPORAL_PATH=off (default)   # nada acontece
NOX_TEMPORAL_PATH=shadow          # detecta + computa delta + loga, NÃO muta ranking
NOX_TEMPORAL_PATH=active          # aplica delta no score (mesmo padrão E13)
NOX_TEMPORAL_SIGMA_DAYS=30        # tunável
```

### 2.4 Telemetry

Cada query temporal loga em stderr (JSON line, padrão E13/salience shadow probes):
```json
{"type":"temporal_path","query_hash":"...","is_temporal":true,
 "anchor_iso":"2026-04-25","anchor_source":"iso_date",
 "k_reranked":12,"top1_delta_days":2,"applied":false}
```

`applied=false` em shadow; `true` em active. Permite eval pre/post sem flip de DB schema.

---

## 3. Inputs reais (não inventados — verified 2026-05-20)

| Campo | Schema | Cobertura corpus prod (audit 2026-05-19) |
|---|---|---|
| `chunks.source_date` | TEXT ISO (V1) | ~100% chunks têm valor (default = ingest date) |
| `chunks.created_at` | TEXT ISO (V1) | 100% (DB-generated) |
| `chunks.last_accessed_at` | TEXT ISO (V1) | ~13% non-null (87% nunca acessado) |
| `chunks.section` | TEXT V10 | 1.1% populated (compiled/frontmatter/timeline) |

**source_date** é o feedstock primário (alta cobertura). `created_at` é fallback. `last_accessed_at` NÃO usado neste path (já consumido por salience recency component).

---

## 4. Open questions (research mode)

1. **Sigma tuning:** σ=30 days é chute. Optimization grid em eval set (σ ∈ {7, 14, 30, 60, 90}) provavelmente revela ponto ótimo dependente da query category.
2. **Anchor parsing PT-BR:** "em abril" sem ano explícito → assumir ano corrente? Próximo passado? Spike usa "ano corrente, fallback ano anterior se data futura".
3. **Multi-anchor queries:** "entre março e maio" → range bigger-than-sigma. Spike usa midpoint; pode precisar de delta bimodal.
4. **Interação com E13:** se ambos paths shadow ativos, deltas somam aditivo (regra #5) ou um substitui outro? Spike assume aditivo (E13 mexe em section, este em proximity — eixos ortogonais).
5. **Queries temporais sem anchor** (Q70 "quando o salience foi ativado") — proximity rerank não dispara (sem anchor). Cobertura desse subset depende 100% de E13. Spike documenta a falha gracefully.

---

## 5. Eval plan

### 5.1 Golden subset isolation
Q70+Q71 (curadas) e Q87+Q88 (vazias — precisam ser curadas antes do gate). Filtrar `category=="temporal"` no harness.

### 5.2 LongMemEval temporal slice
`paper/publication/baselines/longmemeval_hybrid_eval.py` já roda full bench. Adicionar split por category `temporal_*` + `multi_session` em score.ts.

### 5.3 Métricas
- **Primary:** Δ nDCG@10 temporal subset (target ≥ +0.10 vs G5 baseline 0.466).
- **Guardrail:** Δ nDCG@10 non-temporal ≥ −0.005 (regression hard cap, mesmo padrão E13).
- **Coverage:** % queries detectadas como temporal em 5%–25% (sanity).
- **Anchor recall:** % queries temporais onde anchor parseado com sucesso.

### 5.4 Ablation matrix (Q1 Lab)
| Run | Path | Detector | Anchor | Expectativa |
|---|---|---|---|---|
| T0 | off | — | — | baseline (G5 atual) |
| T1 | active | adverbial only | NULL | match E13 sem proximity |
| T2 | active | adverbial + ISO | parse | full spike |
| T3 | active | T2 + month/quarter | parse | full + PT-BR fuzzy |

---

## 6. Comparação com competidores (sobre temporal/time-aware)

- **Mem0**: documenta `memory.update_at` mas não publica reranking temporal explícito. Time é metadata, não signal.
- **Letta (MemGPT)**: stratifica memória em working/archival; nenhum rerank time-aware publicado nos papers.
- **Zep**: KG temporal-aware é o diferencial publicado deles — graph edges têm `valid_at` / `invalid_at`. Mais sofisticado que proximity rerank, mas exige KG denso (nox-mem tem 402 entities, Zep escala em milhares). **Lente para nox-mem:** proximity rerank em chunks (proxy barato do que Zep faz em KG); evoluir pra KG-temporal se Q1 mostrar tração.
- **LongMemEval paper**: temporal queries são a categoria mais difícil reportada (média 67% accuracy across rankers); confirma que o weak spot é estrutural do problema, não específico de nox-mem.

---

## 7. Não-objetivos deste spike

- NÃO substitui E13 (section-boost flip continua sendo o path principal pra `section=timeline` chunks).
- NÃO toca `search.ts` em prod (módulo isolado em `staged-temporal-spike/`).
- NÃO migra schema (`source_date`/`created_at` já existem).
- NÃO troca KG temporal (Q1+ ou Lab Q2).

---

## 8. Definition of Done (spike)

- [x] Spec aprovado (este doc)
- [x] `temporal-retrieval.ts` standalone (~150 LOC, sem dep em search.ts)
- [x] 3–5 unit tests cobrindo detector + anchor parser + proximityDelta
- [ ] Q87+Q88 gold curados (handoff Toto, fora do escopo deste spike)
- [ ] Shadow run 7d em ambiente eval (Q1 Lab)
- [ ] Σ tuning ablation matrix
- [ ] Activate gate decision em `docs/DECISIONS.md` (D49 candidato)

---

## 9. Como testar manualmente

```bash
# Compile spike isolado
cd staged-temporal-spike
# Não tem package.json próprio (depende de TS direto). Sugestão:
npx tsc --target es2022 --module nodenext --moduleResolution nodenext \
  --outDir dist edits/temporal-retrieval.ts

# Rodar tests (assumindo o mesmo runner do staged-1.7a)
npx tsc -p tsconfig.tests.json && node --test dist/tests/*.test.js

# Sanity check do detector
node -e "import('./dist/edits/temporal-retrieval.js').then(m => \
  console.log(m.detectTemporal('quando o salience foi ativado em 2026-04-25')))"
```

---

## 10. Risk register

| # | Risco | Mitigação |
|---|---|---|
| 1 | Anchor parser PT-BR pega falsos positivos ("em apenas 2 horas" ≠ data) | regex conservadora + shadow telemetry |
| 2 | σ=30 errado pra corpus → over/under boost | ablation matrix antes de activate |
| 3 | NULL `source_date` chunks ignorados → cobertura baixa | aceitar; corpus tem ~100% cobertura |
| 4 | Interação com E13 dupla-conta | shadow rodar ambos; verificar boost stacking aditivo (regra #5) |
| 5 | LLM-extract source_date é texto livre incorreto | reuse de validator existente em ingest pipeline |

---

*Spike isolado. Não bloqueia roadmap atual. Q1 Lab parking-lot.*
