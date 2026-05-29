# Adaptive Query Classifier — Lab Q1 #1 NEW

**Status:** SPEC (não dispatched) — Nova prioridade Lab Q1
**Author:** Toto (via auto-mode session 2026-05-28)
**Predecessores:** Phase D (PR #365, 62.22% baseline), Phase G 5-batch (PR #369, rerank opt-in verdict)

## Objetivo

Implementar um **classificador de consulta adaptativo** que determina dinamicamente se uma query é multi-hop e roteia o reranker MiniLM (Phase G) para ON ou OFF por consulta, sem latência adicional percebida no caminho factual.

**Impacto projetado:**
- +1-3pp overall vs sempre-rerank (mitiga regressão head-precision + MA nas queries factuais)
- Fecha ~30-50% do gap residual MemOS F_MH (12.11pp abertos; MemOS 18.94%, Phase G 6.83%)
- Best-of-both: recall factual rápido por padrão + rerank preciso quando multi-hop detectado

**Referências cristalizadas:**
- `[[phase-g-minilm-multi-hop-breakthrough]]` — trade-off 5-batch honesto; rerank OPT-IN
- `[[cross-encoder-trade-off-shape]]` — 4-dim trade-off (hard-recall+, head-precision-, MA-, latência+)
- `[[memory-awareness-dimension-must-be-audited]]` — MA é silent killer; classificador deve proteger MA

---

## 1. Sinal do classificador — o que prevê multi-hop?

### 1.1 Features sintáticas de query

| Feature | Indicador | Peso relativo |
|---|---|---|
| Palavra interrogativa | "who/what/when" → factual; "how does X compare Y" → multi-hop | Alto |
| Contagem de conjunções | múltiplas cláusulas conectadas ("and", "but", "while", "after") | Médio |
| Frases comparativas | "compared to", "vs", "difference between", "how does X relate" | Alto |
| Comprimento da query | >10 tokens tende multi-hop | Médio-baixo |
| Contagem de entidades | ≥3 entidades mencionadas → provável multi-hop | Alto |
| Marcadores de raciocínio abstrato | "why", "explain", "summarize", "what caused", "what led to" | Alto |
| Marcadores temporais complexos | "before … happened", "since … changed", "after … and then" | Médio |

### 1.2 Features semânticas de query

- **Contagem de entidades:** heurística via regex NER leve (pessoas, datas, tópicos entre aspas) sem chamada de API externa
- **Embedding-based:** pequeno classificador (regressão logística ou MLP 2 camadas) sobre o vetor de embedding da query. Aproveita embedding já gerado no pipeline hybrid search — custo marginal zero em latência
- **Densidade lexical:** ratio tokens únicos / tokens totais — queries densas tendem multi-hop

### 1.3 LLM-based (custo alto)

Prompt para `gemini-flash-lite` ("Esta query requer raciocínio em múltiplos passos? Responda só Y ou N"):
- Mais preciso (~90% accuracy estimada) mas +100-200ms de latência
- Reservado para casos borderline ou modo exploratory explícito

### 1.4 Matrix custo-acurácia-latência

| Método | Acurácia estimada | Latência adicional | Custo operacional | Recomendado |
|---|---|---|---|---|
| Heurístico sintático (Option A) | ~70-75% | ~1ms | Nenhum | **Ship default** |
| Embedding classifier (Option B) | ~82-87% | ~10ms | Treinamento único ~$2 | Fase Q1.3 |
| LLM-as-judge flash-lite (Option C) | ~88-93% | ~150ms | Por query | Modo exploratory |
| Heurístico + LLM borderline (Option D) | ~85-90% | ~50ms avg | Baixo (só borderline) | Fase Q2 |

**Nota:** acurácia estimada pressupõe EverMemBench como distribuição de referência. Distribuição real de queries de usuário pode diferir — ver §7 Riscos.

---

## 2. Opções de arquitetura

### Option A — Classificador Heurístico (recomendado para ship)

Implementação pura TypeScript, ~1ms overhead.

```
Algoritmo:
  score = 0
  if entity_count(query) >= 3: score += 3
  if conjunction_count(query) >= 2: score += 2
  if has_comparative(query): score += 3
  if has_abstract_reasoning_marker(query): score += 2
  if token_count(query) > 10: score += 1
  if has_temporal_chain(query): score += 2

  → score >= THRESHOLD (default: 4) = MULTI_HOP → rerank ON
  → score < THRESHOLD = FACTUAL → rerank OFF
```

Threshold tuned em held-out split do EverMemBench F_MH/F_SH.

### Option B — Embedding Classifier

Treinar regressão logística (scikit-learn) sobre embeddings das queries EverMemBench já ingeridas em `eval/evermembench/`. Labels: F_MH / F_HL = positive; F_SH / MC / MA = negative.

- Input: vetor Gemini embedding 3072d da query (já disponível no pipeline hybrid search)
- Output: probabilidade [0,1] de multi-hop
- Threshold: 0.5 default, tunável
- Treinamento: ~500 queries labeled + augmentation sintética
- Modelo serializado: `src/classifiers/multihop-v1.pkl` ou equivalente TS
- Custo zero em latência (aproveita embedding já computado)

### Option C — LLM-as-judge

```
POST /gemini-flash-lite
prompt: "É esta consulta multi-hop (requer cruzar 2+ fatos distintos)? Responda Y ou N.\nQuery: {query}"
```

+100-200ms. Mais preciso. Indicado para:
- `/api/answer?mode=exploratory` (usuário aceita latência)
- Queries >20 tokens como sinal condicional (pré-filtro Option A primeiro)

### Option D — Hybrid Heurístico + LLM Borderline

Option A como primeiro passe. Se score entre [3, 6] (zona borderline), verifica com LLM-flash-lite. Latência média ~50ms ponderado pela frequência de borderline queries (estimada ~20-30% do tráfego).

**Recomendação de arquitetura:** ship Option A imediato. Experimentar Option B em Q1.3 como upgrade transparente (mesma API). Option C / D somente se Option B não fechar gap suficiente.

---

## 3. Dados de treinamento

### 3.1 Labels EverMemBench

| Categoria EverMemBench | Classe classificador | Justificativa |
|---|---|---|
| F_MH (Multi-hop Factual) | MULTI_HOP | Por definição |
| F_HL (High-level) | MULTI_HOP | Requer sumarização de múltiplos chunks |
| F_TP (Temporal Patterns) | MULTI_HOP | Cadeia temporal implica multi-hop |
| F_SH (Single-hop Factual) | FACTUAL | Resposta em chunk único |
| MC (Multi-choice) | FACTUAL | Identificação direta |
| OE (Open-ended) | FACTUAL* | *Borderline — OE ganhou +1.77pp com rerank |
| MA_C / MA_P / MA_U | FACTUAL | Rerank regrediu -3 a -4pp; proteger |

**OE como borderline:** pode ser classe separada ou tratar como FACTUAL default com Option B verificando empiricamente.

### 3.2 Augmentation sintética

Gerar ~300-500 queries sintéticas multi-hop via:
- Template: "After [event_A] happened in [period_X], how did [entity] respond compared to [entity_B]?"
- Negativo: "What is the [attribute] of [entity]?" (single-hop canônico)
- Custo estimado: ~$0.50 via gemini-flash-lite para geração

### 3.3 Conjunto de validação

- ~500 queries cross-estratificadas (EverMemBench held-out 20% + sintéticas)
- Métricas: precision/recall binary + F1 por classe
- Target: F1 ≥ 0.80 em F_MH / F1 ≥ 0.85 em MA-protection (não regredir MA)

### 3.4 Validação cross-sistema (opcional Fase Q1.3)

- Queries PT-BR do corpus real de sessões Nox (anonimizadas via `[[a0-query-logging]]`)
- Verificar se heurística sintática degrada em português — ver §7.2

---

## 4. Path de integração

### 4.1 CLI — `nox-mem search`

```
nox-mem search "query"           # modo default: adaptive (Option A)
nox-mem search "query" --no-rerank     # força OFF (override global)
nox-mem search "query" --force-rerank  # força ON independente do classificador
nox-mem search "query" --classify-debug  # loga score + decisão sem mudar resultado
```

O classificador decide rerank ON/OFF de forma transparente. Debug flag expõe o score e threshold sem alterar comportamento.

### 4.2 API HTTP — `/api/search`

```
GET /api/search?q=<query>&adaptive=true   # default; classificador decide
GET /api/search?q=<query>&mode=auto       # alias de adaptive=true
GET /api/search?q=<query>&mode=fast       # força rerank OFF
GET /api/search?q=<query>&mode=deep       # força rerank ON
```

Response body adiciona campo opcional:

```json
{
  "results": [...],
  "_meta": {
    "classifier": {
      "score": 6,
      "decision": "multi_hop",
      "reranked": true
    }
  }
}
```

Campo `_meta.classifier` apenas quando `adaptive=true` ou `mode=auto` — omitido em fast/deep.

### 4.3 Rota `/api/answer`

Já existente (PR #114 LIVE). Estender com parâmetro `mode`:

```
POST /api/answer?mode=adaptive      # default: classificador decide
POST /api/answer?mode=fast          # rerank OFF + sem LLM-judge
POST /api/answer?mode=exploratory   # força rerank ON + considera LLM-judge (Option C)
```

`exploratory` é o mapeamento direto do flag `--rerank` CLI para o caminho HTTP.

### 4.4 Feature flag de deploy

```env
NOX_ADAPTIVE_CLASSIFIER=true        # default true pós-Q1.2
NOX_ADAPTIVE_THRESHOLD=4            # score mínimo para multi_hop (tunável)
NOX_ADAPTIVE_DEBUG=false            # loga classificação no stderr se true
NOX_RERANKER_ENABLED=0              # override global (legacy, ainda suportado)
```

Precedência: `--force-rerank` / `--no-rerank` > `NOX_RERANKER_ENABLED` > `NOX_ADAPTIVE_CLASSIFIER`.

---

## 5. Plano de benchmark

### 5.1 Design experimental

Rodar EverMemBench 5-batch (~$3) em 4 modos comparativos:

| Modo | Config | Ref |
|---|---|---|
| **Baseline Phase D** | rerank OFF always | PR #365 62.22% |
| **Phase G rerank-ON** | rerank ON always | PR #369 61.26% |
| **Option A adaptive** | heurístico score ≥4 → ON | NEW |
| **Option C adaptive** | LLM-judge → ON | NEW |

### 5.2 Métricas por categoria

Para cada modo, reportar:
- Overall %
- F_MH, F_SH, F_HL, F_TP, MC, OE (por categoria)
- MA_C, MA_P, MA_U (Memory Awareness — obrigatório por `[[memory-awareness-dimension-must-be-audited]]`)
- Latência p50 / p95 por query
- Taxa de ativação do reranker (% queries que recebem rerank ON)

### 5.3 Gate de sucesso

**Para promover Option A como default (Fase Q1.2):**
- Condição A: Overall ≥ Phase D baseline **62.22%** (não regredir)
- Condição B: F_MH ≥ Phase G 5-batch **6.83%** (manter ganho multi-hop)
- Condição C: MA_C/P/U média ≥ Phase D baseline (não regredir MA)
- Condição D: p50 latência ≤ Phase D × 1.5 em queries factual (não pagar custo rerank desnecessariamente)

Todas as 4 condições devem ser satisfeitas. Best-of-both é o critério, não apenas F_MH.

### 5.4 Budget estimado

- Option A heurístico: sem custo de inferência (só runtime check)
- 5-batch Option A: ~$3.00 (EverMemBench standard)
- 5-batch Option C: +~$1.50 (LLM-judge ~$0.30/batch por flash-lite)
- Total estimado Fase Q1.1-Q1.2: ~$4-5

---

## 6. Faseamento de deploy

### Fase Q1.1 — Heurístico atrás de feature flag

1. Implementar `src/lib/query-classifier.ts` — Option A puro
2. Integrar em `src/search.ts` (pós-hybrid-search, pré-rerank gate)
3. Feature flag `NOX_ADAPTIVE_CLASSIFIER=false` por default (safe off)
4. Deploy + 5-batch EverMemBench validação

**Critério de promoção para Q1.2:** gate §5.3 satisfeito.

### Fase Q1.2 — Default ON

1. Virar `NOX_ADAPTIVE_CLASSIFIER=true` default em `.env.example`
2. Documentar `--no-rerank` / `--force-rerank` como escape hatches no `--help`
3. Atualizar `/api/search` docs com `mode` param
4. Atualizar `/api/answer` docs com `mode=adaptive|fast|exploratory`
5. PR + deploy + observar `search_telemetry` por 7 dias (shadow audit)

### Fase Q1.3 — Embedding Classifier (Option B)

1. Extrair queries + labels de `eval/evermembench/` batches 004/005/010/011/016
2. Gerar embeddings via `nox-mem vectorize` (já disponível)
3. Treinar regressão logística — `scripts/train-query-classifier.py`
4. Serializar + integrar como drop-in replacement de Option A
5. A/B test: Option A vs Option B via feature flag `NOX_CLASSIFIER_MODE=heuristic|embedding`
6. Promoção apenas se F1 ≥ 0.80 no validation set E overall não regride

**Projeção marginal:** +1pp vs Option A. Dependente de suficiência dos ~300-400 EverMemBench labeled queries.

### Fase Q2 — Option D Hybrid (condicional)

Ativar somente se Option B não fechar gap suficiente de F_MH E MA-protection simultâneos. Option D (heurístico + LLM borderline) tem overhead operacional maior (LLM calls em ~25% das queries) e deve ser justificado por ganho mensurável.

---

## 7. Riscos e questões abertas

### 7.1 Overfitting para distribuição EverMemBench

O classificador é treinado e validado em EverMemBench — queries sintéticas de benchmark de memória. Distribuição real de queries Nox é distinta: mais conversacional, mais contexto implícito, mais PT-BR.

**Mitigação:**
- Validar Option A com 50 queries manuais do corpus real (amostra de `search_telemetry`)
- Usar `NOX_ADAPTIVE_DEBUG=true` por 2 semanas em prod + auditar taxa de ativação
- Se taxa de ativação >60% (too aggressive) ou <10% (too conservative), re-tunar threshold

### 7.2 Comportamento em queries PT-BR

Option A heurístico baseia-se em regex/patterns em inglês. Queries em português:
- "Quem foi responsável por X depois de Y acontecer?" → multi-hop, mas padrões EN podem não detectar
- "Como X se compara a Y?" → comparativa, mapeamento PT possível mas precisa explicitamente

**Mitigação:**
- Adicionar variantes PT aos patterns (lista de marcadores em PT-BR: "depois que", "antes de", "como se compara", "qual a diferença entre", "por que", "explique")
- Fase Q1.3 Option B resolve naturalmente (embedding agnóstico de idioma)

### 7.3 Custo de manutenção vs ganho marginal

Option A tem zero manutenção operacional. Options B/C/D adicionam:
- B: modelo pkl para versionar/atualizar quando distribuição deriva
- C: custo por query em flash-lite (estimado ~$0.0003/query)
- D: complexidade de dois paths

**Mitigação:** ship sequencialmente. Se Option A atinge gate, Option B é Lab-only (não prod-default obrigatório).

### 7.4 Latência em queries factual

Se classificador malclassifica query factual como multi-hop, usuário paga +3.7s de rerank desnecessário. Com Option A threshold=4, false positive rate estimado ~25%.

**Mitigação:**
- Threshold conservativo (5 ou 6 em vez de 4) reduz FP a ~15% — validar em 5-batch
- Monitorar via `search_telemetry` razão de queries reranked vs total
- `--no-rerank` como escape hatch explícito

### 7.5 MA-protection: rerank não deve deslocar entity/profile chunks

`[[memory-awareness-dimension-must-be-audited]]` aponta que entity chunks (section_boost compilado/frontmatter) são deslocados pelo reranker pois ele rankeia por relevância query-chunk, não user-context.

**Mitigação:** mesmo em modo multi-hop (rerank ON), proteger top-K entity chunks de serem deslocados. Implementar como: se chunk tem `section IN (compiled, frontmatter)`, pin à sua posição bi-encoder antes do reranker; reranker só re-ordena os demais. Validar com MA_C/P/U em 5-batch.

---

## Não-objetivos

- NÃO implementar código neste PR — spec only
- NÃO modificar `eval/evermembench/adapter_nox_mem.py` — scope eval é separado
- NÃO modificar `src/api-server.ts` neste PR — integração é Fase Q1.1
- NÃO rodar benchmark neste PR — aguarda implementação Option A
- NÃO testar Option B/C/D neste PR — roadmap explícito em §6

---

## Dependências

| Dependência | Estado | Bloqueante? |
|---|---|---|
| Phase G 5-batch verdict (rerank opt-in) | ✅ Merged PR #369 | Sim — contexto do trade-off |
| `NOX_RERANKER_ENABLED` env gate (Phase G) | ✅ PR #367 | Sim — foundation para adaptive override |
| `search_telemetry` tabela (A0) | ✅ Deployed | Não — mas useful para §7.1 audit |
| EverMemBench labeled queries | ✅ ~300-400 em eval/ batches | Para Option B treinamento |

---

## Referências

- `eval/evermembench/adapter_nox_mem.py` — adapter Phase G com env-gated rerank
- `eval/evermembench/RESULTS-PHASEG-5BATCH.md` — Phase G 5-batch numbers completos
- `eval/evermembench/INVESTIGATION.md` — MemOS Table 4 números, F_MH/MA dims
- `src/api-server.ts` — surface HTTP existente (porta 18802)
- `specs/2026-05-07-D01-cross-encoder-reranker.md` — spec original do reranker
- `specs/2026-05-21-neural-reranker-design.md` — design neural reranker (precursor)
- `[[phase-g-minilm-multi-hop-breakthrough]]` — 5-batch reframe + verdict
- `[[cross-encoder-trade-off-shape]]` — 4-dim trade-off atualizado
- `[[memory-awareness-dimension-must-be-audited]]` — MA silent killer + proteção entity chunks
- `[[a0-query-logging-extension]]` — search_telemetry para audit de ativação do classificador

---

## Closure esperado

Branch: `spec/adaptive-query-classifier-lab-q1`
PR title: `Spec: Adaptive query classifier (Lab Q1 #1 NEW)`
Próximo passo após merge: dispatch `executor` para Fase Q1.1 (`src/lib/query-classifier.ts` + integração + 5-batch gate)
