# Lab Q3 — Iterative Retrieval Mechanism

**Status:** SPEC (não implementado) — Lab Q3 priority, sequenced após Wave C results
**Date:** 2026-05-29
**Author:** Toto (via agent session 2026-05-29 evening BRT)
**Branch spec:** `spec/iterative-retrieval-q3`

**Cross-links:**
- `specs/2026-05-29-profile-chunk-identification-q2.md` — Lab Q2 spec (sequencing dependency)
- `specs/2026-05-28-multi-query-expansion.md` — Lab Q1 #3 MQ (single-shot predecessor)
- `specs/2026-05-28-kg-path-retrieval.md` — Lab Q1 #4 KG path (complementar mechanism)
- `specs/2026-05-28-ma-protection-rerank.md` — Lab Q1 #2 MAP (rerank stage anchor)
- `docs/DECISIONS.md §D68` — Wave B orthogonal-stages hypothesis (composability rationale)
- `docs/ROADMAP.md` — Wave C row + Lab Q3 placement
- PR #379 KG path (3/4 gates), PR #385 MQ (3/4 gates), PR #386 MAP corpus-inert
- PR #389 KG+MQ (REJECTED overlap), PR #390 KG+MAP (SHIPPED opt-in +4.04pp F_MH)
- PR #391 docs Wave B closure, PR #392 Profile-chunk Q2 spec
- Memory `[[f-mh-retrieval-bound-not-generation-bound]]` — gap backbone-invariant = retrieval problem
- Memory `[[lab-q1-3-multi-query-expansion-3of4-gates-win]]` — MQ +3.61pp F_MH opt-in shipped
- Memory `[[lab-q1-4-kg-path-3of4-gates-win]]` — KG path +2.81pp F_MH opt-in shipped
- Memory `[[single-batch-gates-unreliable-5x-overstate]]` — methodology: 5-batch + 95% CI required

---

## 1. Problem Statement

### 1.1 F_MH ceiling após single-shot enhancements

Todas as melhorias Lab Q1 + Wave B operam sobre o mesmo paradigma: **recuperação em round único** sobre a query original ou suas variações. O pipeline recupera K chunks em uma única passagem e os entrega ao backbone para síntese.

Estado atual após Wave C triple (estimado — Wave C em andamento 2026-05-29):

| Config | F_MH (GPT-4.1-mini) | vs Phase H v2 baseline (10.00%) | vs MemOS (18.88%) |
|---|---:|---:|---:|
| Phase H v2 baseline | 10.00% | — | -8.88pp |
| Best single-shot (KG+MAP PR #390) | ~14.04% | +4.04pp | -4.84pp |
| Wave C triple (predicted) | ~15-17% | +5-7pp | ~-2 a -4pp |
| **Residual gap** | — | — | **~2-4pp unclosed** |

O gap residual pós-Wave-C é estrutural: há uma classe de queries em EverMemBench para a qual a evidência necessária para resposta correta está distribuída em múltiplos chunks **cuja conexão não é recuperável em uma única passagem**, independente de quantas sub-queries MQ gere ou de quantos chunks KG injete.

### 1.2 Multi-hop reasoning chain: por que single-shot falha

Considere a query EverMemBench:

> *"After the SQL optimization of the submission API, what was the peak CPU during the 300-user stress test?"*

O pipeline single-shot — mesmo com MQ + KG + MAP — enfrenta o seguinte problema estrutural:

```
Round único (single-shot):
  Query: "SQL optimization submission API + 300-user stress test CPU"
  Embedding: média das sub-intenções → representação diluída
  Top-K recuperados: chunks sobre SQL optimization OU stress test (raramente AMBOS no top-5)
  Backbone: sem evidência de timing entre eventos → resposta incorreta
```

A chain de raciocínio correta exige **dois retrieval rounds sequenciais** com raciocínio intermediário:

```
Round 1: retrieve("SQL optimization submission API")
  → chunk: "SQL optimization deployed 2026-03-15, reduced query time 40%"
  Reasoning: evento ocorreu em 2026-03-15

Round 2: retrieve("stress test 300 users post-2026-03-15")
  → chunk: "Stress test 2026-03-18: 300 users, peak CPU 87%"
  Synthesis: peak CPU = 87%
```

O problema não é vocabulário nem backbone. É que o **bridge entity** (o timestamp do evento SQL optimization) só existe no chunk recuperado no Round 1. Sem ele, o Round 2 é cego — e uma query single-shot não tem como formular o Round 2 precisamente.

Essa é a razão pela qual:
1. F_MH é backbone-invariant (memory `[[f-mh-retrieval-bound-not-generation-bound]]`): tanto Gemini quanto GPT-4.1-mini travam no mesmo gap porque ambos recebem o mesmo conjunto incompleto de evidências
2. MQ +3.61pp (PR #385) foi o maior single-shot knob — decompõe bem, mas sem bridge entity intermediário o Round 2 ainda erra
3. KG path +2.81pp (PR #379) ajuda via graph walk, mas KG não captura eventos temporais pontuais como "CPU durante teste X"

### 1.3 Quantificação do gap residual

Baseado em EverMemBench task distribution e estimativas pós-Wave C:

- Queries multi-hop com **bridge entity temporal** (tipo do exemplo acima): ~15-20% de F_MH queries
- Queries multi-hop com **bridge entity relacional** (A→B→C via KG): ~25-30% de F_MH queries (já endereçadas por KG path)
- Gap residual estimado como multi-round-obrigatório após Wave C triple: **~2-5pp F_MH** (consultas onde o bridge entity é temporal ou depende de contexto em chunk A para formular a query do chunk B)

**Hipótese Q3:** mecanismo iterativo que recupera → raciocina → refina a query → recupera de novo fecha esse gap residual em +3-6pp F_MH adicional sobre o melhor config single-shot.

---

## 2. Três Abordagens Candidatas

### 2.1 Approach A — Single-shot Chain-of-Thought com query enriquecida (CoT-Enrich)

**Mecanismo:** antes do retrieval, o LLM gera uma cadeia de pensamento explícita que decompõe a query em sub-evidências necessárias. A decomposição é usada para enriquecer a query original e gerar um conjunto expandido de termos de busca, mas o retrieval ainda ocorre **em um único round** usando a query enriquecida.

```python
cot_prompt = """
Query: {query}
Identifique os conceitos-chave necessários para responder esta query:
1. O que precisa ser estabelecido primeiro?
2. O que depende do item 1?
3. Termos de busca relevantes para cada conceito:
   Conceito 1: [termos]
   Conceito 2: [termos que pressupõem resposta do conceito 1]
Consulta enriquecida: [combine todos os termos em uma única query de busca]
"""
enriched_query = llm.generate(cot_prompt, model="gemini-flash-lite")
results = retrieve(enriched_query, k=30)  # top-K expandido para compensar
```

**Racional:** CoT forçado melhora a qualidade da query expandida vs simples MQ — o modelo raciocina sobre dependências antes de formular termos de busca, não apenas decompõe em sub-queries independentes.

**Prós:**
- Latência mínima vs Multi-round (1 LLM call + 1 retrieval round)
- Custo baixo (~$0.0001-0.0003/query com flash-lite)
- Composável com MQ (pode substituir ou complementar sub-queries atuais do PR #385)
- Sem mudança de arquitetura de retrieval

**Contras:**
- NÃO resolve o problema de bridge entity — o chunk B ainda não é acessível via query enriquecida se depende de conteúdo do chunk A
- Benefício marginal sobre MQ (PR #385 já faz decomposição similar, +3.61pp)
- Risco de over-expansion dilui ranking via RRF

**Cobertura de gap F_MH residual estimada:** +1-2pp (aborda queries onde os termos de busca eram subótimos, mas NÃO aborda bridge entity gap)

**Veredicto:** Approach de menor risco, mas teto baixo. **Útil como fallback barato** dentro de budget de rounds, não como knob principal Q3.

---

### 2.2 Approach B — Multi-round Retrieve-Reason loop (ReAct-style)

**Mecanismo:** implementação canônica de ReAct (Yao et al., 2022) adaptada para nox-mem. O LLM itera entre Thought (raciocínio sobre evidências acumuladas) e Act (formulação de nova query de busca), até atingir critério de terminação.

```python
evidence_buffer = []
query_history = []

for round_n in range(max_rounds=5):
    # Thought
    thought = llm.generate(
        prompt=react_prompt(original_query, evidence_buffer, query_history),
        model=backbone  # requer backbone forte — ver §4.4
    )
    
    # Terminate check
    if thought.contains_answer_signal():
        break
    if budget_exceeded(round_n, tokens_used):
        break
    
    # Act
    next_query = thought.extract_next_retrieval_query()
    if next_query in query_history:  # dedup
        break
    
    # Retrieve
    new_chunks = retrieve(
        query=next_query,
        k=10,  # menor por round vs single-shot 20-30
        exclude=already_retrieved_chunk_ids  # dedup §4.2
    )
    evidence_buffer.extend(new_chunks)
    query_history.append(next_query)

final_answer = synthesize(original_query, evidence_buffer, backbone)
```

Estrutura do `react_prompt`:
```
Query original: {query}
Evidências acumuladas até agora:
  [Round 1 query]: {query_1}
  [Round 1 chunks]: {summary_chunks_1}
  [Round 2 query]: {query_2}
  [Round 2 chunks]: {summary_chunks_2}
  ...
Pensamento: O que ainda falta para responder a query? Preciso recuperar mais informação?
Se sim, qual seria a melhor query de busca para encontrar o que falta?
Se não, formule a resposta final.
```

**Prós:**
- Resolve diretamente o bridge entity problem — Round 2 é formulado com conteúdo de Round 1
- Arquitetura canônica da literatura (ReAct Yao et al. 2022; HippoRAG iterative)
- Terminação flexível (max_rounds / confidence / budget)
- Composável com pipeline nox-mem existente (cada round usa hybrid retrieval completo)
- Qualquer backbone pode ser testado (ver §4.4)

**Contras:**
- Latência alta: p95 com 3 rounds ~6-9s (estimado: 2s embed + 0.8s LLM × 3)
- Custo por query: ~$0.003-0.008 (3 rounds com gpt-4.1-mini; $0.001-0.003 com flash-lite)
- Complexidade de implementação: state management entre rounds + dedup
- Risco de loop: LLM pode gerar queries circulares sem bridge entity novo

**Cobertura de gap F_MH residual estimada:** +3-5pp (resolve bridge entity temporal + parte relacional não coberta por KG)

**Veredicto:** Abordagem de maior teto. **Candidata principal Q3.** Latência e custo são aceitáveis para batch eval (gate: p95 ≤ 8s); para produção, gate adicional de custo/query.

---

### 2.3 Approach C — Self-Ask with Search (Press et al. 2022 pattern)

**Mecanismo:** adaptação direta de Self-Ask (Press et al., "Measuring and Narrowing the Compositionality Gap", 2022). O LLM primeiro responde "Esta query requer sub-perguntas explícitas?" — se sim, gera N sub-perguntas sequencialmente, recupera para cada uma, e sintetiza. A diferença de Approach B (ReAct) é estrutural: as sub-perguntas são geradas **antes** do retrieval (não em loop) e cada sub-pergunta é respondida (RAG parcial) antes de prosseguir para a próxima.

```python
# Phase 1: Decomposition decision
decomposition = llm.generate(
    f"""Query: {query}
    Does this require intermediate sub-questions to answer?
    If yes, list the sub-questions in dependency order.
    Format:
    NEEDS_DECOMPOSITION: yes/no
    SUB_QUESTIONS: [q1, q2, q3, ...]""",
    model="gemini-flash-lite"
)

if not decomposition.needs_decomposition:
    # Fallback to standard pipeline
    return standard_retrieve_and_answer(query)

# Phase 2: Sequential sub-question RAG
partial_answers = {}
for sub_q in decomposition.sub_questions:
    enriched_sub_q = f"{sub_q} (context: {partial_answers})"
    chunks = retrieve(enriched_sub_q, k=10)
    partial_answers[sub_q] = synthesize_partial(sub_q, chunks, model="gemini-flash-lite")

# Phase 3: Final synthesis with all partial answers
final_answer = synthesize(
    query=query,
    evidence=partial_answers,
    model=backbone
)
```

**Prós:**
- Estrutura mais previsível que ReAct (número de rounds determinado no Phase 1)
- Custo moderado: Phase 1 (decomposition) + N sub-questions × (retrieval + partial_synth)
- Self-Ask permite fallback para single-shot quando query não precisa decomposição (preserva latência das queries simples)
- Composável com MQ: sub-questions podem alimentar MQ para cada round de retrieval

**Contras:**
- Fallback para standard pipeline quando NEEDS_DECOMPOSITION=no pode perder bridge entity cases onde o modelo não reconhece a necessidade de decomposição
- Sub-question sequencing é fixo (gerado no Phase 1) — menos adaptativo que ReAct loop que pode descobrir novos gaps em runtime
- Partial synthesis por sub-question pode perder contexto cruzado entre sub-respostas

**Cobertura de gap F_MH residual estimada:** +2-4pp (intermediário entre A e B; melhor que CoT-Enrich por ser multi-round, mas menos adaptativo que ReAct)

**Veredicto:** Opção equilibrada entre custo/latência e teto de performance. **Recomendada como fallback dentro do orçamento de rounds** quando Approach B excede budget de latência ou custo.

---

## 3. Decision Matrix

| Critério | Peso | A — CoT-Enrich | B — ReAct multi-round | C — Self-Ask |
|---|---:|---:|---:|---:|
| F_MH ceiling closure (gap residual) | 35% | +1-2pp (baixo) | +3-5pp (alto) | +2-4pp (médio) |
| Latência p95 (batch aceitável ≤8s) | 15% | ~1.5s (excelente) | ~6-9s (no limite) | ~4-6s (OK) |
| Custo por query (alvo ≤$0.01) | 15% | $0.0001-0.0003 | $0.003-0.008 | $0.001-0.004 |
| Complexidade de implementação | 10% | Baixa (~1 semana) | Alta (~3 semanas) | Média (~2 semanas) |
| Composabilidade com Wave C triple | 15% | Alta (add-on sub-query) | Alta (cada round usa pipeline completo) | Alta (sub-questions usam pipeline) |
| Backbone-independence | 10% | Alta (flash-lite basta) | Média (requer CoT forte — ver §4.4) | Média (decomposition precisa CoT) |
| **Score ponderado** | 100% | **38/100** | **72/100** | **59/100** |

**Recomendação:** B+C híbrido — Approach B como mecanismo principal com fallback para Approach C quando budget de latência/custo é excedido. Approach A como sub-componente do Phase 1 de B (enriquecimento da query inicial antes do Round 1).

---

## 4. Arquitetura Recomendada (B+C Híbrido)

### 4.1 Query-time flow

```
User query
   ↓
[1] Budget estimator (heuristic: query length + entity count → complexity score)
   → complexity < threshold → single-shot pipeline (preserve latência atual)
   → complexity ≥ threshold → iterative path
   ↓
[2] Iterative path:
   Phase 1 — Decomposition (Self-Ask / Approach C style):
     - LLM: "NEEDS_DECOMPOSITION: yes/no + SUB_QUESTIONS: [...]"
     - Model: gemini-flash-lite (barato, ~500ms)
     - Result: ordered_sub_questions OU flag→ReAct_direct

   Phase 2 — Multi-round retrieve-reason (ReAct / Approach B style):
     For each round (max N rounds):
       - Formulate next_query from thought (Round 1: sub_question_1 enriched with A-style CoT;
                                            Round 2+: informed by evidence_buffer)
       - retrieve(next_query, k=10, exclude=seen_ids)  ← nox-mem hybrid pipeline completo
       - evidence_buffer.append(retrieved_chunks)
       - llm_thought: "enough evidence?" → terminate OR next_query
       - budget check: tokens_used, round_count, elapsed_ms

   Phase 3 — Final synthesis:
     - synthesize(original_query, evidence_buffer, backbone)
     ↓
[3] Answer + debug metadata (rounds_executed, queries_per_round, termination_reason)
```

### 4.2 Termination criteria (multi-critério, primeiro que acionar)

| Critério | Threshold | Racional |
|---|---|---|
| `max_rounds` | 5 (hard ceiling) | Budget guard; 5 rounds → ~10s p95 — aceitável em batch, marginal em prod |
| `answer_confidence` | LLM self-rate ≥ 0.8 | Se backbone considera evidência suficiente, para |
| `cost_budget` | $0.01/query hard cap | Previne runaway; gpt-4.1-mini: ~3-4 rounds antes do cap |
| `chunk_overlap` | ≥ 80% overlap com round anterior | Se Round N recupera quase os mesmos chunks que Round N-1, a busca convergiu |
| `query_similarity` | cosine(next_query, any_past_query) ≥ 0.95 | Evita loop circular de queries quase-idênticas |

**Re-retrieval deduplication:** `exclude=seen_chunk_ids` em cada round subsequente. Evita re-ranquear os mesmos chunks e desperdiçar budget. A deduplicação é por `chunk_id` (não por conteúdo), portanto chunks similares de diferentes entidades ainda são elegíveis.

### 4.3 Adapter mode

`NOX_ADAPTER_MODE=phaseIter` ativa:
- Budget estimator (heuristic complexity score)
- Self-Ask decomposition (Phase 1)
- ReAct multi-round loop (Phase 2)
- Per-round telemetria (rounds_executed, termination_reason)
- Compõe com phaseKGMAP: cada round de retrieval usa KG path + MAP quando ativos

`NOX_ITER_MAX_ROUNDS=3` — override do default (5 rounds) para budget mais conservador.

`NOX_ITER_BACKBONE=gpt-4.1-mini` — backbone para as etapas de thought/decomposition (pode ser diferente do backbone de síntese final).

### 4.4 Backbone considerations

Approach B requer backbone com **CoT raciocínio forte** para:
1. Detectar o que falta na evidência acumulada
2. Formular a next_query relevante (não circular)
3. Decidir termination com confiança

| Backbone | CoT quality | Custo/1k tokens | Estimativa F_MH Iter ceiling |
|---|---|---|---|
| gemini-flash-lite | Fraco (decomposição simples OK; bridge entity inference fraco) | $0.000075 | +1-2pp (Approach A range) |
| gpt-4.1-mini | Médio-forte (bridge entity inference OK para maioria dos casos) | $0.00075 | +3-5pp (Approach B range) |
| Claude Sonnet 4.6 | Forte (CoT profundo; bridge entity inference melhor) | $0.003 | +4-6pp (Approach B ceiling) |
| Claude Opus 4.7 | Muito forte (ceiling máximo) | $0.015 | +5-7pp (stretch) |

**Recomendação para Phase IterB bench:** gpt-4.1-mini como backbone de thought (consistência com baseline Phase H v2) + flash-lite para decomposition Phase 1. Resultados com gpt-4.1-mini são diretamente comparáveis ao baseline F_MH.

**Nota importante:** gpt-4.1-mini pode ser insuficiente para bridge entity inference em queries de alta complexidade. Se Phase IterB demonstrar teto em ~+2-3pp com gpt-4.1-mini, Phase IterB-Sonnet como variante com Claude Sonnet 4.6 para thought pode abrir +1-2pp adicionais. Budget separado na fase de escalação.

---

## 5. Plano de Avaliação 5-Batch

### 5.1 Fases de benchmark

| Fase | Componentes | Hipótese testada | Backbone thought |
|---|---|---|---|
| **Phase IterA** | CoT-Enrich single-shot (Approach A isolado) | CoT enriquecimento resolve sub-set de F_MH gap sem overhead de rounds | gemini-flash-lite |
| **Phase IterC** | Self-Ask decomposição (Approach C isolado) | Estrutura de sub-perguntas pré-retrieval fecha mais gap que CoT-Enrich | gemini-flash-lite → gpt-4.1-mini |
| **Phase IterB** | ReAct multi-round (Approach B — max 3 rounds) | Loop iterativo com bridge entity inference fecha gap residual | gpt-4.1-mini |
| **Phase IterTripleB** | KG+MQ+MAP + Approach B (composabilidade máxima) | Pipeline completo 3 stages + iterativo fecha ≥50% MemOS F_MH gap total | gpt-4.1-mini |

Sequenciamento:
- Phase IterA roda em paralelo com Phase IterC (independentes, sem dependência de resultado)
- Phase IterB sequencial após IterA + IterC (usa learnings de cobertura e terminação)
- Phase IterTripleB somente se IterB atinge Gate 1 (F_MH ≥ +3pp)

### 5.2 Gate matrix (4 gates, IterB referência)

| Gate | Threshold | Racional |
|---|---|---|
| 1. F_MH lift | ≥ +3pp vs Wave C triple baseline | Justifica custo e complexidade de multi-round |
| 2. Overall regression | ≤ -2pp vs Phase H v2 (51.68%) | Custo de iterativo OK se F_MH compensar |
| 3. Latência p95 | ≤ 8s por query (batch eval) | Aceitável para avaliação; prod gate seria ≤ 3s |
| 4. Custo por query | ≤ $0.01 (avg) | ~3-4 rounds com gpt-4.1-mini dentro do cap |

Gates para Phase IterTripleB (stretch):
- F_MH ≥ 22% absoluto (closes ≥50% MemOS 18.88% gap from Phase H v2 baseline 10.00%)
- MA composite ≥ Phase H v2 -2pp (iterativo NÃO deve agravar MA — ver §7 NÃO FAZEMOS)

### 5.3 Set E instrumentation (métricas por query)

Para cada query no EverMemBench 5-batch (n=500, 100 por batch):

```python
metadata_per_query = {
    "rounds_executed": int,           # 1-5; 1 = single-shot fallback
    "termination_reason": str,        # "max_rounds"|"answer_confidence"|"cost_budget"|
                                      # "chunk_overlap"|"query_similarity"|"single_shot_fallback"
    "cost_usd": float,                # custo total da query (decomposition + rounds + synthesis)
    "latency_ms": float,              # wall clock total da query
    "unique_chunks_retrieved": int,   # union de todos os rounds (pós-dedup)
    "per_round_chunk_overlap": list,  # [overlap_r1_r2, overlap_r2_r3, ...] — detecção de loop
    "complexity_score": float,        # heuristic do budget estimator
    "decomposition_fired": bool,      # Phase 1 Self-Ask decidiu NEEDS_DECOMPOSITION=yes?
    "sub_questions_count": int,       # 0 se decomposition não disparou
}
```

Análise pós-bench crítica:
- Distribuição de `rounds_executed`: quantas queries precisaram >1 round?
- `termination_reason` breakdown: qual critério domina a terminação?
- Correlação `rounds_executed` × F_MH score: confirma que queries multi-round têm maior F_MH lift?
- Correlação `complexity_score` × `rounds_executed`: valida o heuristic do budget estimator

### 5.4 Estimativa de orçamento

| Fase | n queries | Rounds médios | Custo/query estimado | Total |
|---|---:|---:|---:|---:|
| Phase IterA | 500 | 1 (single-shot) | $0.0003 | ~$1.50 |
| Phase IterC | 500 | 2 (decomp + 2 rounds) | $0.002 | ~$1.00 |
| Phase IterB | 500 | 2.5 (avg 3 rounds) | $0.006 | ~$3.00 |
| Phase IterTripleB | 500 | 3 (KG+MQ+MAP+Iter) | $0.008 | ~$4.00 |
| 5-batch overhead (×5 batches) | — | — | — | ×5 = ~$47.50 |
| Backbone escalation (IterB-Sonnet, condicional) | 500 | 2.5 | $0.015 | +~$7.50 |
| **Q3 budget total (sem escalação)** | — | — | — | **~$35-40** |
| **Q3 budget total (com escalação Sonnet)** | — | — | — | **~$45-50** |

**Nota:** orçamento é ~2-4× mais caro que Lab Q1 experiments (~$8-10 cada). Custo justificado apenas se Wave C triple + Q2 Profile ainda deixar gap ≥ 3pp F_MH residual. **Gate de GO/NO-GO pré-Q3:** verificar resultados Wave C + Q2 Profile antes de autorizar IterB spend.

---

## 6. Open Questions

1. **Loop termination heuristic ótimo:** qual critério de terminação domina na prática? `chunk_overlap ≥ 80%` é o mais confiável para evitar loops, mas o threshold adequado depende de distribuição do corpus. Alternativa: treinar um classificador leve de "suficiência de evidência" com exemplos do EverMemBench — viável se Phase IterA fornecer dados de calibração.

2. **Re-retrieval deduplication agressividade:** excluir `seen_chunk_ids` completamente (rígido) vs penalizar via score (suave)? Exclusão rígida evita loops mas pode forçar o modelo a recuperar chunks de qualidade inferior em Round 2+. Penalização suave mantém a opção mas complica o ranking. **Recomendação inicial:** exclusão rígida na Phase IterB; testar penalização suave em variante se houver gap residual.

3. **Reasoning chain caching:** o custo de LLM thought por round (gpt-4.1-mini) é ~$0.001-0.002/round. Para queries com sub-structure similar (mesmo evento, mesma timeline), o thought de Round 1 pode ser cacheável via hash(partial_query). Estimar taxa de cache hit em EverMemBench — se ≥ 20% das queries tem subtree compartilhado, caching reduz custo em ~15-20%.

4. **Backbone routing entre etapas:** usar backbone diferente para CoT/thought (flash-lite) vs síntese final (gpt-4.1-mini)? Trade-off: custo cai ~70% nos rounds intermediários com flash-lite, mas qualidade da bridge entity inference cai (ver §4.4). Phase IterB testa backbone uniforme; Phase IterB-Mixed como variante pós-resultado.

5. **F_TP / F_HL side effects:** multi-round retrieval com reasoning temporal (Round 1 ancora timeline → Round 2 navega cronologicamente) pode beneficiar F_TP (temporal precision) e F_HL (high-level reasoning) além de F_MH. Medir esses dims em Phase IterB como secondary metrics.

---

## 7. NÃO FAZEMOS

1. **Não rodar Phase IterB antes de conhecer Wave C triple results** — se Wave C triple já fecha ≥70% do MemOS F_MH gap, o ROI de iterative retrieval cai drasticamente e o $35-40 de budget Q3 pode ser realocado para Q2 Profile-chunk ou GTM. Gate explícito: Wave C triple resultado + Q2 bench antes de GO/NO-GO Q3.

2. **Não shipar iterative retrieval como ON por default** — custo/latência (3+ rounds, $0.006-0.008/query, p95 ~8s) é inaceitável para produção genérica. Iterative retrieval é sempre opt-in via `NOX_ADAPTER_MODE=phaseIter`; usuários que precisam de máximo F_MH accuracy em batch workloads. Mesma filosofia de PR #379 / #385 / #390.

3. **Não usar gemini-flash-lite como backbone de thought para Phase IterB** — flash-lite não tem CoT suficiente para bridge entity inference (vide §4.4). Usar gpt-4.1-mini para manter comparabilidade com Phase H v2 baseline. Flash-lite é aceitável APENAS para Phase 1 decomposition (Self-Ask, query simples de decomposição).

4. **Não pular auditoria de MA dimension** — lesson `[[memory-awareness-dimension-must-be-audited]]`: mudanças de retrieval têm custo MA escondido. Multi-round retrieval pode piorar MA se evidence_buffer de múltiplos rounds diluir profile chunks. Medir MA_C / MA_P / MA_U em cada phase de bench obrigatoriamente.

5. **Não implementar reasoning chain caching antes de validar hit rate** — caching de LLM thoughts adiciona complexidade (hash colisão, TTL, invalidação) sem ROI comprovado. Estimar hit rate em Phase IterA data (análise pós-bench) antes de investir em implementação.

6. **Não misturar iterative retrieval com KG density experiments** — KG density foi REFUTADO (memory `[[kg-density-refuted-sparse-canonical]]`): mais entidades/relações pioram F_MH. O KG canonicamente sparse deve ser o baseline para todos os rounds em Phase IterTripleB.

---

## 8. Critérios de Sucesso (Q3 close)

| Tier | Métrica alvo | Equivalência |
|---|---|---|
| **Mínimo** | Phase IterB F_MH ≥ +3pp vs Wave C triple baseline | Justifica custo; fecha ≥50% do gap residual pós-Wave-C |
| **Target** | Phase IterB F_MH ≥ +4pp + MA composite não-regressivo (≥ Phase H v2 -2pp) | Iterativo ADICIONA valor sem custo MA |
| **Stretch** | Phase IterTripleB F_MH ≥ 22% absoluto (closes ≥50% MemOS F_MH gap total desde baseline 10.00%) | Milestone estratégico Q3 |

Condição adicional de Q3 close: **latência p95 ≤ 5s para prod deployment** (Phase IterB gate 3 é ≤ 8s para batch; prod exige ≤ 5s). Se Phase IterB passa Gate 1-4 mas p95 = 7s, investigar otimizações (parallel rounds para sub-queries independentes, flash-lite para thought intermediário) antes de declarar Q3 closed.

---

## 9. Trabalhos Relacionados

- **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., 2022, arxiv:2210.03629) — arquitetura canônica Thought-Act-Observe; Approach B é adaptação direta para retrieval augmented memory. Demonstrou +12-19pp em HotpotQA vs RAG baseline sem reasoning loop.

- **Self-Ask: Measuring and Narrowing the Compositionality Gap** (Press et al., 2022, arxiv:2210.03350) — Approach C. Demonstrou que LLMs cometem erros em queries composicionais resolvíveis via sub-questions explícitas. Gap fechamento médio: +10-15pp em multi-hop Q&A. Nox-mem adaptation: sub-questions alimentam retrieval em vez de internal LLM knowledge.

- **STaR: Bootstrapping Reasoning With Reasoning** (Zelikman et al., 2022) — relevante para calibrar o backbone de reasoning: modelos maiores beneficiam mais de CoT iterativo. Corrobora §4.4 consideração de Claude Sonnet 4.6 para Phase IterB-Sonnet.

- **HippoRAG** — iterative retrieval via Personalized PageRank em KG; similar em espírito a Approach B mas usa estrutura de grafo em vez de LLM reasoning para navegar. nox-mem KG path (PR #379) é análogo ao primeiro hop; Iterative Q3 complementa com LLM-guided multi-hop.

- **MemGPT** — context recall iteration: MemGPT realiza múltiplas chamadas de retrieve para construir working context incrementalmente. Mesma ideia, mas MemGPT usa paged memory architecture; nox-mem usa SQL hybrid retrieval.

- **Multi-hop QA literatura:** HotpotQA (Yang et al., 2018), MuSiQue (Trivedi et al., 2022) — benchmarks que validam empiricamente que single-shot retrieval teva na faixa 40-55% accuracy em multi-hop queries; multi-round retrieval eleva para 65-75%.

---

## 10. Ownership & Timeline

- **Owner:** Toto (research + go/no-go decisions) + Claude Code (implementação + bench dispatch)
- **Gate pré-Q3:** Wave C triple results + Q2 Profile-chunk bench results (esperado 2026-06-15 a 2026-06-22) — confirmar gap residual ≥ 3pp F_MH antes de autorizarQ3 spend

| Milestone | Data alvo | Dependências |
|---|---|---|
| Q3 spec freeze | 2026-06-15 | Wave C results para ajustar gate thresholds |
| Phase IterA + IterC POC bench | 2026-06-30 | Q3 spec frozen + eval harness com Set E instrumentation |
| Phase IterB 5-batch bench | 2026-07-15 | IterA + IterC results; gpt-4.1-mini backbone confirmed |
| Phase IterTripleB (stretch) | 2026-07-30 | IterB Gate 1 passed |
| Q3 ship decision | 2026-08-01 | 5-batch IterTripleB results + prod latency profiling |

**Budget authorization:** $35-40 base (sem escalação backbone). Escalação para Phase IterB-Sonnet (+$7-10) depende de resultado de Phase IterB com gpt-4.1-mini — autorizar somente se gpt-4.1-mini capping em ≤ +2pp e Sonnet estimativa credível de +1-2pp adicionais.

---

*Spec drafted 2026-05-29 evening BRT durante Wave B closure + Wave C dispatch. Lab Q3 sequenciado pós-Wave-C + Q2 Profile-chunk per ROADMAP v4.7 Lab pillar. GO/NO-GO gate explícito: resultados Wave C + Q2 antes de autorizarrun IterB budget.*
