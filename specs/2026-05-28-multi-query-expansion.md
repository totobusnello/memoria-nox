# Multi-Query Expansion — Lab Q1 #3 NEW

**Status:** SPEC (não implementado) — Lab Q1 priority #3, alternative multi-hop attack
**Date:** 2026-05-28
**Author:** Toto (via agent session 2026-05-28 BRT)
**Branch spec:** `spec/multi-query-and-kg-path-retrieval`

**Predecessores:**
- Phase D (PR #365, 62.22% Gemini-2.5-flash baseline)
- Phase H v2 (PR #372, 54.15% GPT-4.1-mini cross-backbone WIN)
- Phase G 5-batch (PR #369, rerank OPT-IN verdict — fecha só ~11.7% do MemOS F_MH gap)
- Lab Q1 #1 (PR #373 spec — adaptive classifier)
- Lab Q1 #2 (PR #374 spec — MA-protection)

**Cross-links:**
- `[[phase-h-v2-cross-backbone-win]]` — baseline F_MH 10% (GPT-4.1-mini), gap vs MemOS 18.88% = -8.88pp
- `[[cross-encoder-trade-off-shape]]` — rerank fecha só 11.7% do MemOS F_MH gap; remaining 12.11pp open
- `[[memory-awareness-dimension-must-be-audited]]` — MA é silent killer; multi-query deve auditar MA dim
- `[[nox-mem-backbone-portability]]` — structural advantage é no adapter, não no backbone
- `[[lightrag-kg-incremental-merge-pattern]]` — LLM-augmented retrieval precedent

---

## 1. Hypothesis

**Multi-hop queries que cruzam múltiplos chunks beneficiam de decomposição explícita.**

O pipeline nox-mem atual (BM25 + dense + RRF) opera sobre a query original como um único vetor de intenção. Queries multi-hop como "what did X do with Y after Z happened in period W?" carregam múltiplas sub-intenções que um único embedding não representa com fidelidade. O espaço de embedding de uma query complexa é uma média ponderada das sub-intenções — cada uma individualmente mais próxima dos chunks relevantes do que a query composta.

**Mecanismo proposto:** gerar N sub-queries via LLM que cobrem diferentes aspectos da query original, recuperar top-K para cada sub-query, fazer union/dedup/rerank dos resultados. A união aumenta recall para queries que distribuem evidências em múltiplos chunks.

**Evidência motivadora:**
- EverMemBench Phase H v2 F_MH: nox-mem 10.00% vs MemOS 18.88% = **-8.88pp gap**
- Phase G rerank 5-batch: F_MH lift apenas +1.61pp (95% CI marginal) — rerank insuficiente
- Rerank fecha ~11.7% do gap MemOS: `1.61 / (18.88 - 5.22) × 100 ≈ 11.7%`
- Remaining gap: ~12.11pp — requer abordagem alternativa
- GPT-4.1-mini F_MH +8pp vs Gemini-2.5-flash na mesma evidência de recuperação confirma que o gargalo não é raciocínio do backbone mas **cobertura de recuperação (recall)**

**Alinhamento com literatura:**
- HyDE (Gao et al., 2022): hypothetical document embeddings melhora recall denso ~3-8pp em benchmarks BEIR
- Sub-query decomposition (Press et al., "Measuring and Narrowing the Compositionality Gap", 2022): decomposição melhora multi-hop Q&A em +10-15pp vs direct query
- LLM-augmented retrieval (RAG-Fusion, 2023): multi-query union + RRF re-merge melhora NDCG@10 ~3-5pp

---

## 2. Três Abordagens

### Approach A — HyDE (Hypothetical Document Embeddings)

**Mecanismo:** LLM gera resposta hipotética plausível para a query; essa resposta é então embedded; recuperação usa similaridade com a resposta hipotética em vez da query.

**Racional:** o embedding de uma resposta bem formada (que menciona entidades, atributos, relações) é mais próximo dos chunks de evidência do que o embedding de uma pergunta. "After X happened, Y did Z" como resposta hipotética → embedding próximo de chunks contendo X, Y, Z.

**Pseudocódigo:**
```
hypothetical_answer = llm.generate(
  prompt="Answer this question as if you know the answer, even speculatively:\n{query}",
  max_tokens=100,
  model="gemini-flash-lite"
)
embedding_h = embed(hypothetical_answer)
results = dense_search(embedding_h, top_k=20)
```

**Custo estimado por query:**
- 1 LLM call: ~500 tokens in + 100 tokens out ≈ $0.0003 (gemini-flash-lite)
- 1 embedding call: ~100 tokens ≈ $0.0001
- **Total: ~$0.0004/query**

**Vantagem única:** uma única chamada LLM gera evidência que combina múltiplas sub-intenções naturalmente.

**Limitação:** se LLM alucina na resposta hipotética, embedding se distancia do corpus real. Particularmente arriscado em domínio pessoal (nox-mem contém eventos únicos do usuário — o LLM não sabe o que aconteceu).

**Risco de judge bias:** se backbone da eval (GPT-4.1-mini) gera a resposta hipotética E avalia a resposta final, pode haver sobreposição de sinal (ver §7.1).

---

### Approach B — Sub-query Decomposition (RECOMENDADO para Q1.4)

**Mecanismo:** LLM decompõe a query original em 3-5 sub-queries cobrindo aspectos distintos; retrieval é executado para cada sub-query; resultados são unificados via dedup + RRF re-merge.

**Prompt design:**
```
Decompose this question into 3-5 focused sub-questions that together cover all
aspects needed to answer the original. Each sub-question should be answerable
independently. Return a JSON array of strings.

Query: {original_query}
```

**Exemplo:**
```
Query original: "What role did X play in the Y project, and how did that affect X's
relationship with Z after the Q4 review?"

Sub-queries geradas:
  1. "What was X's role in the Y project?"
  2. "What happened in the Q4 review related to Y?"
  3. "What is the relationship between X and Z?"
  4. "How did the Q4 review outcomes affect X?"
  5. "What changes occurred in X's relationships after Q4?"
```

**Retrieval:**
```python
sub_queries = llm_decompose(query, n=4)
all_results = []
for sq in sub_queries:
    results = hybrid_search(sq, top_k=10)  # BM25 + dense + RRF
    all_results.extend(results)

# Dedup by chunk_id + re-rank by union score
final = rrf_merge(deduplicate(all_results), top_k=10)
```

**RRF re-merge:** usar RRF padrão (k=60) sobre os ranks de cada sub-query. Chunks que aparecem em múltiplas sub-queries ganham boost natural do RRF — cross-sub-query evidence convergence como sinal de qualidade.

**Custo estimado por query:**
- 1 LLM call decomposição: ~800 tokens in + 150 tokens out ≈ $0.0005
- N×retrieval (4 sub-queries): 4 × embedding + 4 × SQL ≈ $0.0004 + ~20ms
- **Total: ~$0.0009/query** (≈ 2× baseline sem multi-query)

**Vantagem sobre A:** sub-queries são explícitas e inspecionáveis; diagnóstico mais fácil; menos suscetível a alucinação de domínio (pergunta, não resposta).

---

### Approach C — Query Reformulation Chain

**Mecanismo:** LLM gera 3-5 reformulações da mesma intenção com variações estilísticas/lexicais (não decomposição — todas cobrem a intenção completa). Diversidade lexical aumenta cobertura de termos BM25 + diversidade de vizinhança dense.

**Racional:** FTS5 BM25 é sensível a termos exatos. "When did X happen?" vs "What date was X?" vs "At what time did X occur?" → vocabulário diferente → chunks diferentes ranqueados primeiro. Union aumenta recall BM25 para queries com variação lexical natural.

**Prompt design:**
```
Generate 4 reformulations of this query with different phrasing but the same intent.
Vary vocabulary, structure, and specificity. Return JSON array.

Query: {original_query}
```

**Custo estimado por query:**
- 1 LLM call reformulação: ~600 tokens in + 100 tokens out ≈ $0.0004
- N×retrieval (4 reformulações): 4 × pipeline ≈ $0.0004 + ~20ms
- **Total: ~$0.0008/query**

**Limitação principal:** reformulações cobrem mesma intenção → não resolve fragmentação de evidência entre chunks distintos. Abordagem C beneficia principalmente BM25 coverage, não recall multi-hop genuíno.

**Recomendação:** Approach C é complementar a B, não alternativa. Potencialmente combinar B + C em modo avançado (Q2).

---

## 3. Análise de Custo-Benefício

### 3.1 Comparativo por abordagem

| Approach | LLM calls/query | Embed calls/query | SQL calls/query | Custo est./query | Latência adicional est. |
|---|---:|---:|---:|---:|---|
| Baseline (nenhuma) | 0 | 1 | 2 (FTS5+vec) | ~$0.0001 | 0ms |
| A — HyDE | 1 | 2 | 2 | ~$0.0004 | +150ms |
| **B — Decomposition** | **1** | **4-5** | **8-10** | **~$0.0009** | **+300ms** |
| C — Reformulation | 1 | 4 | 8 | ~$0.0008 | +280ms |
| B + C combined | 1 | 7-8 | 14-16 | ~$0.0015 | +450ms |

Valores assumem gemini-flash-lite para LLM calls e gemini-embedding-001 para embeds.

### 3.2 Latência p50 estimada vs baseline

- Baseline Phase H v2: p50 ~1.6s (Phase H v2 session measurement, `/api/answer`)
- Approach B: p50 ~1.9s (+300ms = +19% overhead)
- Gate: latência p50 ≤ 2× baseline (§6 gate criteria) → Approach B comfortable

**Nota:** LLM call (gemini-flash-lite) é dominante em latência adicional (~200-250ms). Embed calls parallelizáveis em Python asyncio → overhead de 4 embeds ≈ 1 embed wall-clock.

### 3.3 Custo em produção (estimativa)

Assuminedo 100 queries/dia na API nox-mem (uso típico atual):
- Baseline: ~$0.01/dia
- Approach B (opt-in, ~20% das queries = multi-hop): ~$0.012/dia (overhead negligível)
- Approach B (on para todas as queries): ~$0.09/dia

**Conclusão:** modo opt-in não tem impacto material de custo. Modo default-on seria aceitável mas desnecessário para queries single-hop.

---

## 4. Integration Points

### 4.1 Localização primária — `eval/evermembench/adapter_nox_mem.py`

Para benchmark e validação, multi-query expansion é implementado no adapter Python. Integração pré-retrieval: intercept a query antes do `hybrid_search` call e expandir conforme `--multi-query` flag.

```python
class NoxMemAdapter:
    def __init__(self, ...):
        self.multi_query_mode = os.environ.get("NOX_MULTI_QUERY_MODE", "off")
        # values: "off", "hyde", "decompose", "reformulate"
    
    def retrieve(self, query: str, top_k: int = 20) -> list[dict]:
        if self.multi_query_mode == "decompose":
            sub_queries = self._decompose_query(query, n=4)
            return self._multi_retrieve_merge(sub_queries, top_k)
        elif self.multi_query_mode == "hyde":
            hyp = self._generate_hypothetical(query)
            return self._dense_only_retrieve(hyp, top_k)
        elif self.multi_query_mode == "reformulate":
            reformulations = self._reformulate_query(query, n=4)
            return self._multi_retrieve_merge(reformulations, top_k)
        else:
            return self._standard_retrieve(query, top_k)
```

**NUNCA modificar `adapter_nox_mem.py` durante runs de benchmark ativos** (Phase H 5-batch + Tier B efficiency PR). Implementar em cópia separada `adapter_nox_mem_mq.py` para Lab runs.

### 4.2 CLI — `nox-mem search`

```
nox-mem search "query"                          # padrão — sem multi-query
nox-mem search "query" --multi-query=decompose  # Approach B
nox-mem search "query" --multi-query=hyde       # Approach A
nox-mem search "query" --multi-query=reformulate # Approach C
```

Flag é opt-in. Sem custo adicional quando ausente. Debug log via `NOX_MULTI_QUERY_DEBUG=true`.

### 4.3 HTTP API — `/api/search`

```
GET /api/search?q=<query>                        # padrão, sem expansão
GET /api/search?q=<query>&mq=decompose           # Approach B
GET /api/search?q=<query>&mq=hyde                # Approach A
GET /api/search?q=<query>&mq=reformulate         # Approach C
```

Response body inclui campo `_meta.multi_query` quando ativo:
```json
{
  "results": [...],
  "_meta": {
    "multi_query": {
      "mode": "decompose",
      "sub_queries": ["q1", "q2", "q3", "q4"],
      "merged_from": 28,
      "deduped_to": 18
    }
  }
}
```

### 4.4 Feature flags

```env
NOX_MULTI_QUERY_MODE=off          # "off" | "hyde" | "decompose" | "reformulate"
NOX_MULTI_QUERY_N=4               # número de sub-queries/reformulações (2-6)
NOX_MULTI_QUERY_DEBUG=false       # loga sub-queries + merge stats no stderr
NOX_MULTI_QUERY_LLM=gemini-2.5-flash-lite  # modelo para expansão (default flash-lite)
```

Precedência: CLI flag `--multi-query=X` > `NOX_MULTI_QUERY_MODE`. Default `off` = backward compatible.

### 4.5 Composability com Lab Q1 #1 (adaptive classifier)

O adaptive classifier (Lab Q1 #1, PR #373 spec) detecta queries multi-hop. Integração natural:

```
query → classifier (Lab Q1 #1)
  ├─ "multi_hop" score ≥ threshold → ativar multi-query Approach B
  ├─ "factual/single-hop" → desativar multi-query (custo zero)
  └─ "MA query" → desativar multi-query (MA não beneficia de decomposição)
```

Isso cria adaptive routing zero-custo-overhead para queries single-hop. Ver §8 (deployment phasing) para sequência.

---

## 5. Plano de Benchmark

### 5.1 Design experimental

Rodar EverMemBench 5-batch em 4 configurações:

| Modo | Config | Custo est. | Alvo |
|---|---|---:|---|
| **Baseline Phase H v2** | GPT-4.1-mini, mq=off, rerank=off | — | 54.15% (batch 004) |
| **Approach A — HyDE** | mq=hyde, N=1 | ~$5/batch × 5 = **$25** | F_MH target 13%+ |
| **Approach B — Decompose** | mq=decompose, N=4 | ~$5/batch × 5 = **$25** | F_MH target 15%+ |
| **Approach C — Reformulate** | mq=reformulate, N=4 | ~$5/batch × 5 = **$25** | F_MH target 12%+ |

**Budget total:** ~$75 (3 abordagens × 5-batch cada). Com orçamento limitado: priorizar **Approach B** (melhor hipótese teórica) — $25.

### 5.2 Métricas obrigatórias por run

Para cada run, reportar **obrigatoriamente** (per `[[memory-awareness-dimension-must-be-audited]]`):
- Overall %
- F_MH, F_SH, F_HL, F_TP (hard-recall + single-hop)
- MA_C, MA_P, MA_U (Memory Awareness — silent killer dimension)
- MC, OE (head-precision / recall-leaning)
- Latência p50 / p95 por query
- Custo total do run ($) — para calibrar cost-benefit

**Report format:** `eval/evermembench/RESULTS-LAB-Q1-3-MQ.md` (espelho do `RESULTS-PHASEG-5BATCH.md`)

### 5.3 Comparação com Phase G 5-batch baseline

Para qualquer abordagem considerada para ship, comparar diretamente vs Phase H v2 5-batch baseline (quando disponível — Phase H atualmente 1 batch). Usar batches 004/005/010/011/016 como Phase G para consistência de batches.

### 5.4 Budget mínimo (prioridade)

Com $25 para um round: rodar somente Approach B (decomposition). Approach B tem a hipótese mais fundamentada na literatura (sub-query decomposition) e é a abordagem mais inspecionável.

---

## 6. Gate Criteria

Para promover qualquer abordagem de multi-query como opt-in feature:

| Critério | Threshold | Justificativa |
|---|---|---|
| **F_MH lift vs Phase H v2 baseline** | **≥ +3pp** (5-batch) | Objetivo primário: fechar gap MemOS F_MH |
| **MA não-regressão (MA_C + MA_P + MA_U)** | **≥ 0pp vs baseline** | `[[memory-awareness-dimension-must-be-audited]]` — silent killer |
| **Overall não-regressão** | **≥ -1pp vs baseline** | Multi-query não deve regredir overall |
| **Latência p50** | **≤ 2× baseline** | LLM call overhead aceitável até 2× |
| **Custo por query** | **≤ $0.002** | Teto operacional razoável para opt-in |

**Gate de promoção como default-on (mais rigoroso):**
- F_MH lift ≥ +5pp 5-batch
- Overall ≥ baseline
- Latência p50 ≤ 1.5× baseline
- MA não-regressão (todos 3 sub-dims)

---

## 7. Riscos e Questões Abertas

### 7.1 LLM judge bias se mesmo backbone é usado

**Risco:** se o mesmo backbone (ex: GPT-4.1-mini) é usado para gerar sub-queries E para julgar a resposta final no EverMemBench, o eval pode favorecer framing gerado pelo mesmo modelo.

**Mitigação:**
- Usar gemini-flash-lite para expansão + GPT-4.1-mini para eval judge (padrão EverMemBench)
- Ou usar backbone separado para expansão quando rodando cross-backbone eval
- Documentar backbone da expansão em metadata de run para rastreabilidade

### 7.2 Alucinação em domínio pessoal (HyDE específico)

O nox-mem contém memórias únicas do usuário (eventos, relações, preferências). Em HyDE, o LLM gera resposta hipotética sobre conteúdo que não conhece — pode alucinar entidades, datas, relações. Embedding de resposta alucinada → retrieval de chunks incorretos.

**Mitigação:**
- Approach B (decomposition) é mais seguro: pergunta, não resposta
- Para HyDE: adicionar heurística de detecção de alucinação (`[[entity-in-hypothetical]]`) — se hipotético menciona N entidades não presentes no corpus, descartar e usar query original
- Considerar prompt com instrução "se não souber, descreva a estrutura da resposta, não a resposta"

### 7.3 Custo de escala em produção

Modo default-on com 4 sub-queries × embed call seria ~4× custo de embed. Para volumes altos (1000+ queries/dia), custo torna-se relevante.

**Mitigação:** opt-in exclusivo inicialmente. Adaptive integration com Lab Q1 #1 classifier limita ativação para queries multi-hop (estimado ~20-30% do tráfego real) — overhead efetivo ~0.8× vs 4× naive.

### 7.4 Qualidade da decomposição em PT-BR

LLM (gemini-flash-lite) decompõe queries em inglês com qualidade alta. Para queries em português:
- Marcadores de multi-hop em PT-BR ("depois que X aconteceu", "como X se relaciona com Y") devem ser reconhecidos pelo LLM
- Teste rápido: validar manualmente 10 queries PT-BR decompostas antes de Q1.4 run

**Mitigação:** prompt explicitamente instrui "return sub-questions in the same language as the input query". Gemini-flash-lite é multilingual — risco baixo.

### 7.5 Composability com Phase G rerank

Multi-query + rerank = composto mais agressivo. Se as duas técnicas se beneficiam dos mesmos casos (multi-hop), a combinação pode ser redundante. Se conflitam (multi-query dilui relevância dos top chunks → rerank piora MA), a combinação pode ser contraproducente.

**Mitigação:** benchmarkar separadamente antes de combinar. Matriz de composabilidade é Q2 (§8).

### 7.6 Dedup e merge — qualidade do RRF cross-sub-query

RRF (k=60) foi calibrado para BM25 + dense fusion. Usando o mesmo k=60 para fusão cross-sub-query pode não ser ótimo:
- Sub-queries correlacionadas → chunks redundantes inflam rank
- Sub-queries independentes → chunks distintos não têm boost

**Mitigação:** experimentar k=30 (mais agressivo) e k=90 (mais suave) em ablation. Reportar k value usado em todos os run reports.

---

## 8. Deployment Phasing

### Q1.4 — Implement Approach B (decomposition) — simplest, most explainable

**Scope:**
1. Implementar `_decompose_query()` em adapter eval Python (`adapter_nox_mem_mq.py`)
2. Implementar `_multi_retrieve_merge()` com RRF re-merge
3. Feature flag `NOX_MULTI_QUERY_MODE=decompose` no adapter
4. Nenhuma mudança em `src/` — eval-only neste primeiro step

**Deliverables:**
- `eval/evermembench/adapter_nox_mem_mq.py` — adapter com multi-query support
- `eval/evermembench/RESULTS-LAB-Q1-3-MQ.md` — 5-batch results Approach B

**Custo do run:** ~$25 (5-batch × ~$5/batch com gemini-flash-lite decomposition)

### Q1.5 — Benchmark + decide ship como opt-in

Se F_MH lift ≥ +3pp (gate §6):
- PR: adicionar `--multi-query` CLI flag em `src/index.ts`
- PR: adicionar `mq` param em `/api/search` endpoint (`src/api-server.ts`)
- Feature flag `NOX_MULTI_QUERY_MODE` com default `off`
- Deploy + observar via `search_telemetry` por 7 dias

### Q2 — Composability matrix (multi-query × rerank × classifier)

Matriz completa a validar em Q2 após Lab Q1 concluído:

| Config | Expected outcome |
|---|---|
| Multi-query B + no-rerank | Melhor cobertura + sem MA cost |
| Multi-query B + rerank ON | Melhor recall + melhor precision (risco MA) |
| Multi-query B + rerank + MA-protection | Ideal teórico: cobertura + precision + MA safe |
| Classifier → multi-query B para MH | Adaptive, menor custo médio |
| Classifier → MA-protection para MA | Adaptive, MA safe |

Composabilidade plena requer Lab Q1 #1 + #2 + #3 todos deployed. Benchmarkar combinações em Q2 com orçamento separado.

---

## 9. Posicionamento Competitivo

### 9.1 O que os competidores fazem

| Sistema | Multi-query support | Detalhes |
|---|---|---|
| mem0 | Não documentado | Pipeline não-público; retrieval básico |
| MemOS | Não (Table 4 pipeline implica single-query) | F_MH 18.88% com modelo forte |
| Zep (Graphiti) | Não — temporal KG layer, não retrieval expansion | KG separado de retrieval |
| LightRAG | Sim — local + global KG search modes | HKU EMNLP 2025; não é sub-query |
| HippoRAG2 | Sim — PPR graph-augmented (não LLM expansion) | Academic |

### 9.2 Posicionamento nox-mem

Multi-query Approach B (decomposition) seria uma **feature distintiva explícita** vs mem0, MemOS, Zep. LightRAG faz algo conceitualmente similar mas via KG mode, não decomposição LLM direta.

**Paper framing (§6 draft):** "nox-mem implements optional sub-query decomposition (Lab Q1 #3) for multi-hop queries, generating N focused sub-questions and merging results via RRF. Combined with the adaptive classifier (Lab Q1 #1), this provides query-type-aware routing with zero overhead for factual queries."

---

## 10. Dependências

| Dependência | Estado | Bloqueante? |
|---|---|---|
| Phase H v2 5-batch baseline | Pendente ($4.60, Toto sign-off needed) | Para gate comparison apples-to-apples |
| Phase G 5-batch verdict (rerank trade-off) | ✅ PR #369 merged | Contexto do gap 12.11pp |
| Lab Q1 #1 (classifier spec) | ✅ PR #373 merged | Para Q2 composability (não Q1.4) |
| Lab Q1 #2 (MA-protection spec) | ✅ PR #374 merged | Para Q2 composability (não Q1.4) |
| gemini-flash-lite API access | ✅ Deployed em prod | LLM expansion calls |
| `eval/evermembench/adapter_nox_mem.py` | ✅ Phase H active run stable | NÃO modificar; usar cópia `_mq.py` |

---

## Referências

- `eval/evermembench/adapter_nox_mem.py` — adapter base (NÃO modificar diretamente)
- `eval/evermembench/RESULTS-PHASEG-5BATCH.md` — Phase G 5-batch, F_MH gap quantificado
- `eval/evermembench/INVESTIGATION.md` — MemOS Table 4 F_MH 18.88% (GPT-4.1-mini)
- `specs/2026-05-28-adaptive-query-classifier.md` — Lab Q1 #1 (classifier, composability alvo)
- `specs/2026-05-28-ma-protection-rerank.md` — Lab Q1 #2 (MA protection, composability alvo)
- `[[phase-h-v2-cross-backbone-win]]` — baseline F_MH 10.00%, gap -8.88pp
- `[[cross-encoder-trade-off-shape]]` — rerank fecha 11.7% do gap; remaining 12.11pp
- `[[memory-awareness-dimension-must-be-audited]]` — MA silent killer; auditar em todas runs
- `[[nox-mem-backbone-portability]]` — structural advantage via adapter framework
- `[[lightrag-kg-incremental-merge-pattern]]` — LLM-augmented retrieval precedent (LightRAG, MIT)

---

## Closure esperado

Branch: `spec/multi-query-and-kg-path-retrieval`
PR: junto com `specs/2026-05-28-kg-path-retrieval.md` (Lab Q1 #3 + #4 paired spec PR)
Próximo passo após merge: dispatch `executor` para Q1.4 (`adapter_nox_mem_mq.py` + 5-batch run)
