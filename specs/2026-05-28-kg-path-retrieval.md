# KG Path Retrieval — Lab Q1 #4 NEW

**Status:** SPEC (não implementado) — Lab Q1 priority #4, alternative multi-hop attack via KG
**Date:** 2026-05-28
**Author:** Toto (via agent session 2026-05-28 BRT)
**Branch spec:** `spec/multi-query-and-kg-path-retrieval`

**Predecessores:**
- Phase D (PR #365, 62.22% Gemini-2.5-flash baseline)
- Phase H v2 (PR #372, 54.15% GPT-4.1-mini cross-backbone WIN)
- Phase G 5-batch (PR #369, rerank trade-off 5-batch, MA hidden cost revealed)
- Lab Q1 #1 (PR #373 spec — adaptive classifier)
- Lab Q1 #2 (PR #374 spec — MA-protection)
- Lab Q1 #3 (specs/2026-05-28-multi-query-expansion.md — multi-query expansion)

**Cross-links:**
- `[[phase-h-v2-cross-backbone-win]]` — baseline F_MH 10%, F_TP 11.67%; MA dims lead vs MemOS
- `[[cross-encoder-trade-off-shape]]` — remaining 12.11pp F_MH gap; rerank insufficient
- `[[memory-awareness-dimension-must-be-audited]]` — MA é silent killer; KG paths incluem entity chunks, potencialmente AJUDAM MA
- `[[kg-relations-uses-fk-ids-not-inline-strings]]` — schema real: source_entity_id/target_entity_id FK, não strings inline
- `[[nox-mem-backbone-portability]]` — structural advantage via adapter
- `[[lightrag-kg-incremental-merge-pattern]]` — KG retrieval precedent (LightRAG, MIT, EMNLP 2025)

---

## 1. Hypothesis

**Multi-hop queries que requerem raciocínio sobre relações entre entidades beneficiam de graph walks explícitos.**

O pipeline atual (BM25 + dense + RRF) trata o corpus como bolsa de chunks. Não há mecanismo para propagar relevância via relações semânticas: se o chunk A menciona X, e X está relacionado a Y via `kg_relations`, chunks sobre Y não ganham boost mesmo que Y seja diretamente relevante para a query.

**Mecanismo proposto:** extrair entidades mencionadas na query → consultar `kg_relations` por vizinhos → boost nos scores de chunks que contêm as entidades relacionadas. Operação SQL de baixo custo que aproveita **infraestrutura KG existente** (402 entidades + 544 relações já em produção).

**Hipótese diferencial MA (único neste Lab Q1):**
- Multi-query expansion (Lab Q1 #3) tem risco de regredir MA (LLM calls + union podem promover chunks não-entity acima de entity chunks)
- KG path retrieval opera **diretamente sobre entity chunks** — as entidades relacionadas são, por definição, entity files ingested via `ingest-entity`. Boost KG **preserva e potencialmente melhora MA**.
- Gate MA ≥ +1pp é **único neste spec**: única técnica Lab Q1 onde MA lift é hipótese positiva, não apenas gate de não-regressão.

**Evidência motivadora:**
- nox-mem KG: 402 entidades + 544 relações (`kg_entities` + `kg_relations`) — incremental nightly via Gemini 2.5 Flash extraction
- Multi-hop gap: F_MH 10.00% (nox-mem Phase H v2) vs 18.88% (MemOS) = -8.88pp
- MA lead: nox-mem já lidera MemOS em MA_C +18.10pp, MA_P +12.01pp, MA_U +23.82pp (Phase H v2) — KG entity-centric approach pode ampliar esse lead

**Alinhamento com literatura:**
- LightRAG (Edge et al., HKU EMNLP 2025, 35k+ stars): KG entity-relation dual retrieval; local mode recupera entidades específicas via relações. nox-mem implementação seria especialização para memória pessoal
- HippoRAG2 (Guo et al., 2025): PPR (Personalized PageRank) sobre KG de entidades recupera contexto multi-hop; nox-mem tem entidades próprias, BFS é análogo mais simples
- KGRAG pattern genérico: entity extraction → KG lookup → chunk augmentation (padrão consolidado em literatura desde 2023)

---

## 2. Infraestrutura Existente a Reutilizar

### 2.1 Schema `kg_entities`

```sql
-- Schema real (v10, 2026-04-23)
CREATE TABLE kg_entities (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT,           -- person, project, concept, event, etc.
  description TEXT,
  created_at INTEGER,
  updated_at INTEGER
);
```

**402 entidades** ativas em prod (2026-05-24 baseline). Entidades são extraídas automaticamente via `kg-extract` CLI (Gemini 2.5 Flash, incremental nightly).

### 2.2 Schema `kg_relations` — `[[kg-relations-uses-fk-ids-not-inline-strings]]`

```sql
-- Schema real — FKs, NÃO strings inline
CREATE TABLE kg_relations (
  id INTEGER PRIMARY KEY,
  source_entity_id INTEGER REFERENCES kg_entities(id),
  predicate TEXT NOT NULL,   -- "works_with", "is_part_of", "led_by", etc.
  target_entity_id INTEGER REFERENCES kg_entities(id),
  confidence REAL DEFAULT 1.0,
  created_at INTEGER
);
```

**544 relações** ativas em prod. SPO lookup requer JOIN dual. Lookup 1-hop para entidade X:

```sql
SELECT e2.name, e2.id, kr.predicate, kr.confidence
FROM kg_relations kr
JOIN kg_entities e1 ON kr.source_entity_id = e1.id
JOIN kg_entities e2 ON kr.target_entity_id = e2.id
WHERE LOWER(e1.name) = LOWER(:entity_name)

UNION

SELECT e1.name, e1.id, kr.predicate, kr.confidence
FROM kg_relations kr
JOIN kg_entities e1 ON kr.source_entity_id = e1.id
JOIN kg_entities e2 ON kr.target_entity_id = e2.id
WHERE LOWER(e2.name) = LOWER(:entity_name)
```

### 2.3 Ligação chunks ↔ entities

Chunks de entity files são ingeridos via `ingestEntityFile()` com `section IN ('compiled', 'frontmatter', 'timeline')`. O slug da entidade está no path `memory/entities/<type>/<slug>.md` — o slug é canonicamente derivado do `name` da entidade.

**Link chunk → entity:** não há FK direta `chunks.entity_id` no schema atual. Ligação via:
```sql
-- Aproximação: chunk contém nome da entidade no content ou source_path
SELECT chunk_id FROM chunks
WHERE content LIKE '%' || :entity_name || '%'
   OR source_path LIKE '%' || :slug || '%'
```

Para Approach A (1-hop, simples), lookup por `source_path LIKE '%<slug>%'` é mais confiável que content match (evita falsos positivos em content).

**Consideração para schema Q2:** adicionar `entity_id INTEGER REFERENCES kg_entities(id)` em `chunks` tornaria o link O(1) via FK — mas é schema migration e está fora do escopo deste spec.

### 2.4 CLI e API existentes

- `nox-mem kg-build` — constrói/atualiza KG (CLI existente)
- `/api/kg` — lista entidades e relações (API existente)
- `/api/kg/path?from=<e1>&to=<e2>` — shortest path (API existente se implementado — verificar)
- `nox-mem cross-search` — busca cross-entity (CLI existente, não é o mesmo mecanismo)

---

## 3. Três Abordagens

### Approach A — 1-hop neighbor boost (RECOMENDADO para Q1.6)

**Mecanismo:**
1. Extrair entidades mencionadas na query (LLM call leve ou heurística NER)
2. Consultar `kg_relations` por vizinhos diretos (1-hop) de cada entidade
3. Boost nos scores de chunks cujo `source_path` contém o slug das entidades vizinhas

**Pipeline:**
```python
# 1. Entity extraction from query
query_entities = extract_entities(query)  # ["X", "Y"]

# 2. 1-hop KG lookup (SQL, ~1-5ms)
neighbors = []
for entity in query_entities:
    neighbors.extend(kg_1hop_neighbors(entity))  # SQL JOIN

# 3. Retrieve chunks for neighbor entities
neighbor_slugs = [e.slug for e in neighbors]
neighbor_chunks = get_chunks_by_entity_slugs(neighbor_slugs)  # source_path match

# 4. Boost neighbor chunks in existing results
for chunk in hybrid_search_results:
    if chunk in neighbor_chunks:
        chunk.kg_boost = BASE_KG_BOOST * decay(0, confidence)
        # 0 hops from mentioned entities → max boost
```

**Boost design:**
- `BASE_KG_BOOST = 1.3` (multiplicativo sobre RRF score)
- 1-hop neighbors: `1.3 × confidence` (onde `confidence` é `kg_relations.confidence`)
- Entidades diretamente mencionadas: `1.5×` (menção explícita = mais forte)

**Custo estimado por query:**
- Entity extraction: 1 LLM call (flash-lite) ~$0.0002 OU heurística regex ~$0
- SQL 1-hop lookup: 2 JOINs sobre 544 rows ≈ 1-3ms
- Chunk lookup by source_path: SQL LIKE ≈ 2-5ms
- **Total: ~$0.0002/query (LLM) ou ~$0/query (heurística)**

**Latência adicional:** ~5-10ms (SQL only) ou +150ms com LLM entity extraction.
Approach A com heurística regex é **o mais barato de todos os Lab Q1 #3/4 approaches**.

---

### Approach B — N-hop walk with decay

**Mecanismo:** BFS sobre `kg_relations` até depth N (default: 2), com boost decaindo por hop:

```python
def kg_bfs(start_entities, max_depth=2, decay_factor=0.5):
    visited = {e: (0, 1.0) for e in start_entities}  # entity → (hop, weight)
    queue = [(e, 0, 1.0) for e in start_entities]
    
    while queue:
        entity, hop, weight = queue.pop(0)
        if hop >= max_depth:
            continue
        
        neighbors = kg_1hop_neighbors(entity)
        for n in neighbors:
            if n not in visited:
                new_weight = weight * decay_factor * n.confidence
                visited[n] = (hop + 1, new_weight)
                queue.append((n, hop + 1, new_weight))
    
    return visited  # entity → (hop, weight)
```

**Boost fórmula:** `chunk.kg_boost = BASE_KG_BOOST × visited[entity].weight`

**Parâmetros:**
- `max_depth=2` default (depth 3 com 544 relações pode explodir — ver §7.2)
- `decay_factor=0.5` (2-hop = 50% do boost 1-hop)
- `BASE_KG_BOOST=1.3`

**Custo estimado:**
- Entity extraction: ~$0.0002
- SQL BFS depth 2: ~3-7ms (544 relações × 2 iterations = max ~1088 SQL rows visited)
- Chunk lookups: ~5-10ms
- **Total: ~$0.0003/query**

**Quando preferir Approach B sobre A:**
- Queries que mencionam entidades "distantes" no KG (ex: menciona "Treviso" → 2-hop chega em "FII" → boost em chunks sobre FII)
- Apenas se Approach A mostrar F_MH lift insuficiente em benchmarks

---

### Approach C — Path-based scoring

**Mecanismo:** extrair pares de entidades da query → encontrar caminho mais curto via `kg_relations` → score de chunks com base na cobertura do caminho (quantos nós do caminho o chunk referencia).

**Pseudocódigo:**
```python
entity_pairs = extract_entity_pairs(query)  # [("X", "Y"), ("Y", "Z")]

for (e1, e2) in entity_pairs:
    path = kg_shortest_path(e1, e2)  # BFS / Dijkstra sobre kg_relations
    path_entities = set(path.nodes)
    
    for chunk in results:
        path_coverage = len([e for e in path_entities if e in chunk.mentioned_entities])
        chunk.kg_path_score += path_coverage / len(path_entities)
```

**SQL shortest path:** com 544 relações, Dijkstra em Python sobre grafo in-memory é viável:
```python
import networkx as nx
G = build_kg_graph_from_db()  # one-time build, cache
path = nx.shortest_path(G, e1, e2, weight="confidence_inv")
```

**Custo estimado:**
- Entity pair extraction: 1 LLM call ~$0.0005 (mais complexo que simples extraction)
- Graph build (one-time, cached): ~50ms first query, ~0ms cached
- Shortest path: ~20ms (NetworkX, 544 edges)
- **Total: ~$0.0006/query** (com cache warm)

**Quando preferir C:** queries tipo "como X e Y se relacionam?" onde o caminho relacional explícito é o que o usuário busca. Mais alinhado com raciocínio relacional explícito do que com recall multi-hop implícito.

**Limitação principal:** shortest path só existe se há caminho no grafo. Com 402 entidades + 544 relações, o grafo é esparso (~1.36 relações por entidade em média) — muitos pares de entidades não têm path. Approach C tem recall limitado pela cobertura do KG.

---

## 4. Custo-Benefício Comparativo

### 4.1 Tabela comparativa de abordagens

| Approach | LLM calls | SQL complexity | Custo est./query | Latência adicional est. | Cobertura KG dep. |
|---|---:|---|---:|---|---|
| **A — 1-hop (heurística)** | **0** | O(N) 1 JOIN | **~$0** | **~5ms** | Baixa |
| **A — 1-hop (LLM extract)** | **1 (flash-lite)** | O(N) 1 JOIN | **~$0.0002** | **~155ms** | Baixa |
| B — N-hop BFS | 1 | O(N×depth) BFS | ~$0.0003 | ~160ms | Média |
| C — Path scoring | 1 (complex) | O(N log N) Dijkstra | ~$0.0006 | ~200ms | Alta |
| Lab Q1 #3 — MQ Decompose | 1 | 4× pipeline | ~$0.0009 | ~300ms | Nenhuma |

**KG path retrieval Approach A (LLM extract)** é mais barato que Lab Q1 #3 MQ Decompose e tem hipótese de MA improvement único.

### 4.2 Custo de benchmark (5-batch EverMemBench)

- Approach A: ~$5/batch × 5 = **$25** (similar Lab Q1 #3)
- Approach B: ~$5/batch × 5 = **$25**
- Approach C: ~$6/batch × 5 = **$30**

Budget prioritário: **Approach A primeiro** ($25). Approach B/C só se A mostra lift insuficiente.

---

## 5. Integration Points

### 5.1 Adapter eval Python — `adapter_nox_mem_kg.py`

Para benchmark, implementar em cópia separada do adapter:

```python
class NoxMemKGAdapter(NoxMemAdapter):
    def __init__(self, ...):
        super().__init__(...)
        self.kg_mode = os.environ.get("NOX_KG_RETRIEVAL_MODE", "off")
        # values: "off", "1hop", "nhop", "path"
        self.kg_depth = int(os.environ.get("NOX_KG_DEPTH", "2"))
        self.kg_boost = float(os.environ.get("NOX_KG_BOOST", "1.3"))
        self._kg_graph = None  # lazy-loaded NetworkX graph (Approach C)
    
    def retrieve(self, query: str, top_k: int = 20) -> list[dict]:
        results = super().retrieve(query, top_k * 2)  # fetch larger pool
        
        if self.kg_mode != "off":
            entities = self._extract_entities(query)
            if entities:
                if self.kg_mode == "1hop":
                    neighbors = self._get_1hop_neighbors(entities)
                elif self.kg_mode == "nhop":
                    neighbors = self._get_nhop_neighbors(entities, self.kg_depth)
                elif self.kg_mode == "path":
                    neighbors = self._get_path_entities(entities)
                
                results = self._apply_kg_boost(results, neighbors)
        
        return sorted(results, key=lambda r: r["score"], reverse=True)[:top_k]
```

**Feature flags:**
```env
NOX_KG_RETRIEVAL_MODE=off      # "off" | "1hop" | "nhop" | "path"
NOX_KG_DEPTH=2                 # max BFS depth para "nhop"
NOX_KG_BOOST=1.3               # multiplicador base
NOX_KG_ENTITY_EXTRACT=llm      # "llm" | "regex" — método de entity extraction
```

### 5.2 Novo endpoint `/api/cross-kg` (ou extensão de `/api/kg/path`)

Para integração na API TypeScript (`src/api-server.ts`):

```
GET /api/cross-kg?query=<q>&depth=<N>&boost=<B>
```

Response:
```json
{
  "results": [...],
  "_meta": {
    "kg_retrieval": {
      "mode": "1hop",
      "query_entities": ["X", "Y"],
      "neighbors_found": 8,
      "chunks_boosted": 3
    }
  }
}
```

**Alternativa mais simples:** extensão do endpoint `/api/search` existente:
```
GET /api/search?q=<q>&kg_walk=1    # 1-hop
GET /api/search?q=<q>&kg_walk=2    # 2-hop
```

Recomendação: `kg_walk` param em `/api/search` — reutiliza superfície API existente sem novo endpoint.

### 5.3 CLI flag

```
nox-mem search "query" --kg-walk=1    # Approach A (1-hop)
nox-mem search "query" --kg-walk=2    # Approach B (2-hop)
nox-mem search "query" --kg-path      # Approach C (path scoring)
```

Flag opt-in. Default: nenhum KG walk (backward compatible).

### 5.4 Posição no pipeline

```
FTS5 BM25 ──┐
Gemini vec ─┤─ RRF fusion ──→ top-N candidates
            └─────────────────────────────────────┐
                                     KG neighbor lookup (SQL)
                                           │
                                    boost scores de chunks
                                    cujos source_path match
                                    entity neighbors
                                           │
                              [Optional] cross-encoder rerank
                                           │
                                     top-K results
```

KG boost é **post-RRF, pre-rerank** (ou pre-rerank se rerank desativado). Isso garante:
1. KG boost não quebra RRF calibração
2. Se rerank ativo, reranker vê chunks KG-boosted em posições mais altas → menor risco de deslocamento

### 5.5 Composability com Lab Q1 #1 (classifier) e Lab Q1 #2 (MA-protection)

```
query → classifier (Lab Q1 #1)
  ├─ "multi_hop" → KG walk (Lab Q1 #4) + opcional rerank
  ├─ "MA query" → skip KG walk + MA-protection (Lab Q1 #2)
  └─ "single-hop" → standard pipeline (no KG, no rerank)
```

KG walk e MA-protection (Lab Q1 #2) são **complementares e não conflitantes**: KG walk boost entity chunks (ajuda MA), MA-protection bypassa entity chunks de rerank (protege MA de deslocamento). Usando ambos juntos: entity chunks ganham boost KG + ficam protegidos do reranker.

---

## 6. Plano de Benchmark

### 6.1 Design experimental

Rodar EverMemBench 5-batch em configurações KG:

| Modo | Config | Custo est. | Hipótese |
|---|---|---:|---|
| **Baseline Phase H v2** | kg=off, rerank=off | — | 54.15% (batch 004) |
| **Approach A — 1-hop (regex)** | kg=1hop, extract=regex | ~$3/batch × 5 = **$15** | F_MH +2pp, MA +1pp |
| **Approach A — 1-hop (LLM)** | kg=1hop, extract=llm | ~$4/batch × 5 = **$20** | F_MH +3pp, MA +1pp |
| **Approach B — 2-hop** | kg=nhop, depth=2 | ~$4/batch × 5 = **$20** | F_MH +4pp, MA +1pp |

**Prioridade de execução:** Approach A regex primeiro (cheapest, $15) → se insuficiente, A LLM ($20) → se insuficiente, B ($20).

**Budget total máximo:** ~$55 (3 runs). Budget mínimo: **$15** (Approach A regex only, já estabelece se KG walk tem sinal).

### 6.2 Métricas obrigatórias por run

Obrigatório per `[[memory-awareness-dimension-must-be-audited]]`:
- Overall %
- F_MH, F_SH, F_HL, F_TP
- **MA_C, MA_P, MA_U** — crítico para validar hipótese de MA lift
- MC, OE
- % de queries com ≥1 entity extracted (cobertura KG)
- % de queries com ≥1 neighbor found (efetividade lookup)
- Latência p50/p95

**Report format:** `eval/evermembench/RESULTS-LAB-Q1-4-KG.md`

### 6.3 Análise por sub-categoria EverMemBench

Categorias que hipótese KG prevê ganho:
- **F_MH (multi-hop factual):** relações entity explícitas deveriam ajudar
- **MA_C (constancy):** entity neighbors incluem profile entities → MA boost esperado
- **F_TP (temporal):** entidades com relações temporais (event → outcome) podem ajudar

Categorias neutras/risco:
- **F_SH (single-hop):** KG walk pode adicionar ruído se entidades erradas boosted
- **MC (multi-choice):** head-precision; KG boost pode promover entidades incorretas

---

## 7. Gate Criteria

### 7.1 Gates para ship como opt-in feature

| Critério | Threshold | Justificativa |
|---|---|---|
| **F_MH lift vs baseline** | **≥ +2pp** (5-batch) | Objetivo primário multi-hop |
| **MA lift (MA_C + MA_P + MA_U avg)** | **≥ +1pp** | Hipótese diferencial positiva: KG beneficia MA |
| **Overall não-regressão** | **≥ 0pp vs baseline** | KG não deve degradar casos não-multi-hop |
| **Latência p50** | **≤ 1.2× baseline** | SQL ops baratos — 20% overhead é máximo aceitável |
| **Cobertura mínima** | **≥ 30% queries com ≥1 neighbor** | KG com cobertura muito baixa não tem sinal real |

**Nota:** gate MA ≥ +1pp é **único neste Lab Q1** (outros gates são não-regressão). Diferenciador que justifica implementar KG path mesmo se F_MH lift for modesto.

### 7.2 Gate para default-on (mais rigoroso)

- F_MH lift ≥ +3pp
- MA_C + MA_P + MA_U todos ≥ +1pp
- Overall ≥ +1pp
- Latência p50 ≤ 1.1× baseline

### 7.3 Threshold de abort

Se cobertura < 15% (menos de 15% das queries com neighbor encontrado), o KG é insuficientemente denso para ter sinal. Ação: enriquecimento KG via Q2 spec separado antes de re-testar.

---

## 8. Riscos e Questões Abertas

### 8.1 Qualidade da entity extraction limita o teto

O boost KG depende de extrair corretamente as entidades mencionadas na query. Com heurística regex (Option A/regex), erros de extração limitam recall do lookup. Entidades com nomes compostos, abreviações, ou em PT-BR podem não ser capturadas.

**Mitigação:**
- LLM extraction (flash-lite) para produção → >90% accuracy estimada
- Normalização: lowercase + remoção de acentos antes do match
- Fallback: se extraction returns 0 entities, skip KG walk sem custo

### 8.2 KG incompleteness — 544 relações pode não cobrir paths multi-hop

Com ~402 entidades e ~544 relações, densidade média é ~1.36 relações/entidade. Muitos pares de entidades não têm path:
- Grafo provavelmente não é totalmente conectado
- Relações de tipos raros (ex: event → outcome) podem não estar bem representadas

**Mitigação:**
- Medir cobertura antes do benchmark: `% of F_MH queries onde ≥1 entity encontrada no KG`
- Se cobertura < 30%, considerar enrichment KG via `kg-build` rodando mais extrações antes do benchmark
- Approach C (path scoring) particularmente vulnerável a gaps — preferir A/B

### 8.3 Composability com rerank — KG boost pre vs post rerank

KG boost no score antes do reranker:
- **Pro:** reranker vê KG-boosted chunks em posições altas → menor risco de deslocamento
- **Con:** cross-encoder pode ainda deslocar se KG chunk não é lexicalmente similar à query

KG boost post-reranker:
- **Pro:** KG como segundo sinal independente do cross-encoder
- **Con:** reranker pode ter deslocado o chunk antes do KG boost ser aplicado

**Recomendação:** KG boost pre-rerank (antes do cross-encoder, se rerank ativo). Testar composição em Q2 após A/B validated isoladamente.

### 8.4 PT-BR entity recognition

`kg_build` usa Gemini 2.5 Flash que é multilingual — entidades em PT-BR provavelmente extraídas corretamente nas relações. Porém queries em PT-BR podem referenciar entidades por nome parcial ou em inglês ("Treviso" vs "FII Treviso").

**Mitigação:**
- Normalização de nome: lowercase match + substring match (`LIKE '%entity_name%'`) além de exact match
- Alias table para abreviações comuns (Q2 se necessário — não block para Q1.6)

### 8.5 Freshness das relações (incremental nightly)

`kg_relations` é atualizado nightly via `kg-build`. Relações novas criadas durante o dia não aparecem até o próximo `kg-build` run. Para memórias recentes (ingested hoje), o KG pode não ter as relações ainda.

**Mitigação:**
- Relações nightly são suficientes para retrieval — usuário raramente faz query sobre chunk ingerido no mesmo dia que a query
- `kg-build` pode ser triggado manualmente via CLI se necessário
- Não bloqueia Q1.6

### 8.6 Boost multiplicativo vs aditivo

`[[scoring-boost-multiplicative-empilhavel-e-veneno]]` (regra crítica memoria-nox §5): boost multiplicativo empilhável é veneno — usar aditivo.

KG boost design:
- **Errado:** `score_final = rrf_score × kg_boost × section_boost` (multiplicativo empilhável)
- **Correto:** `score_final = rrf_score + kg_additive_delta` onde `kg_additive_delta = f(neighbor_confidence, hop)`

**Proposta de fórmula aditiva:**
```
kg_delta = BASE_DELTA × confidence × (1 / hop_distance)
# BASE_DELTA = 0.05 (escalonado para range de RRF scores típicos: 0.01-0.1)
```

Testar magnitude de `BASE_DELTA` em ablation (0.02, 0.05, 0.10) no primeiro batch antes do 5-batch.

---

## 9. Deployment Phasing

### Q1.6 — Implement Approach A (1-hop boost) — lowest risk, cheapest

**Scope:**
1. Implementar entity extraction leve (regex) em `adapter_nox_mem_kg.py`
2. Implementar `_get_1hop_neighbors()` via SQL sobre `kg_relations` (FK join)
3. Implementar boost aditivo no score dos chunks (`kg_additive_delta`)
4. Feature flag `NOX_KG_RETRIEVAL_MODE=1hop` no adapter
5. Nenhuma mudança em `src/` — eval-only no primeiro step

**Deliverables:**
- `eval/evermembench/adapter_nox_mem_kg.py` — adapter com KG support
- `eval/evermembench/RESULTS-LAB-Q1-4-KG.md` — 5-batch results Approach A

**Custo do run:** $15-20 (5-batch, ~$3-4/batch)

### Q1.7 — Benchmark + decide ship como opt-in

Se gate §7.1 satisfeito (F_MH ≥ +2pp AND MA ≥ +1pp AND overall ≥ 0pp):
- PR: `--kg-walk=<N>` CLI flag em `src/index.ts`
- PR: `kg_walk` param em `/api/search` (`src/api-server.ts`)
- Retornar `section` + `entity_slug` (se disponível) em API response para suporte ao boost
- Deploy + shadow monitoring via `search_telemetry` 7 dias

### Q2 — Options B/C e composability

Se Approach A mostra lift (≥ +2pp F_MH):
- Spec separado Q2 para Approach B (N-hop BFS) e Approach C (path scoring)
- Composability matrix: KG × rerank × multi-query × classifier

Se Approach A mostra cobertura baixa (<30%):
- Antes de Q2, enriquecimento KG: spec separado para `kg-build` com prompt de extração mais agressiva + mais passes sobre corpus

### Q2 — Schema enhancement (condicional)

Se KG retrieval é validado como feature permanente:
- `ALTER TABLE chunks ADD COLUMN entity_id INTEGER REFERENCES kg_entities(id)`
- Preencher via `UPDATE chunks SET entity_id = <id> WHERE source_path LIKE '%<slug>%'`
- Isso torna o link chunk↔entity O(1) FK join em vez de LIKE scan
- Escopo: spec separado `2026-Q2-chunks-entity-fk.md`

---

## 10. Posicionamento Competitivo Único

### 10.1 Landscape de KG em sistemas de memória

| Sistema | KG infrastructure | Uso em retrieval | Integração |
|---|---|---|---|
| **nox-mem** | ✅ 402 ent + 544 rel, incremental nightly | **SPEC: primeiro-sinal de retrieval** | Nativa |
| mem0 | Parcial (entity extraction sem KG persistido) | Não — apenas para dedup | Não |
| HippoRAG2 | ✅ PPR sobre KG textual | ✅ PPR walk = retrieval signal primário | Separado do pipeline |
| LightRAG | ✅ Dual KG (local + global) | ✅ KG como modo de retrieval alternativo | Separado; MIT license |
| Zep | ✅ Graphiti (temporal KG) | ❌ Temporal graph ≠ retrieval signal direto | Separado |
| MemOS | Não documentado em paper | Não | — |

### 10.2 Diferenciador vs competidores

1. **vs mem0:** mem0 extrai entidades mas não mantém KG persistido com relações. nox-mem tem 544 relações prontas para uso.

2. **vs HippoRAG2:** HippoRAG2 usa PPR sobre KG construído de documentos — state of art acadêmico mas não integrado em memória pessoal conversacional. nox-mem KG é sobre memórias reais do usuário = sinal personalizado.

3. **vs LightRAG:** `[[lightrag-kg-incremental-merge-pattern]]` — LightRAG mantém descrições sumarizadas de entidades merged por LLM; nox-mem usa entity files com `compiled/frontmatter/timeline` — estrutura mais rica e chunk-first. KG retrieval nox-mem como sinal de boost em pipeline existente é **complemento**, não substituição do pipeline (ao contrário de LightRAG que usa KG como modo alternativo).

4. **vs Zep (Graphiti):** Zep tem temporal KG separado do retrieval. nox-mem KG path retrieval seria **integrado no mesmo pipeline BM25+dense+RRF** — não um layer separado.

### 10.3 Narrativa de paper (§6.3 draft)

"nox-mem maintains a persistent knowledge graph (402 entities, 544 relations) incrementally extracted nightly via Gemini 2.5 Flash. In Lab Q1 #4, we integrate this KG as a retrieval signal: entity mentions in queries trigger 1-hop neighbor lookups, with matched chunks receiving an additive score boost proportional to relation confidence. Unlike HippoRAG2's document-derived PPR or LightRAG's KG-mode retrieval, nox-mem KG path retrieval boosts existing BM25+dense+RRF results, preserving the hybrid pipeline advantages while adding relational context coverage. Uniquely, the entity-centric nature of KG-boosted chunks hypothesizes *positive* Memory Awareness impact — validating this hypothesis empirically is a primary objective of the Q1.7 benchmark run."

---

## Dependências

| Dependência | Estado | Bloqueante? |
|---|---|---|
| `kg_entities` + `kg_relations` em prod | ✅ 402 + 544, nightly update | Sim — dados fonte do boost |
| `kg-build` CLI incremental | ✅ Deployed | Não bloqueante (KG já populado) |
| Phase H v2 5-batch baseline | Pendente (Toto sign-off, ~$4.60) | Para gate comparison apples-to-apples |
| `eval/evermembench/adapter_nox_mem.py` | ✅ Phase H stable | NÃO modificar; usar cópia `_kg.py` |
| Lab Q1 #1 spec (classifier) | ✅ PR #373 | Para Q2 composability (não Q1.6) |
| Lab Q1 #2 spec (MA-protection) | ✅ PR #374 | Para Q2 composability (não Q1.6) |
| `[[kg-relations-uses-fk-ids-not-inline-strings]]` | ✅ Memory cristalizada | SQL correto com FK join, não string match |

---

## Referências

- `src/lib/kg-builder.ts` — extração KG incremental (código produção)
- `src/api-server.ts` — `/api/kg` endpoint existente
- `eval/evermembench/adapter_nox_mem.py` — adapter base (NÃO modificar diretamente)
- `eval/evermembench/RESULTS-PHASEG-5BATCH.md` — baseline MA dims (MA_C 81.40%, MA_P 83.00%, MA_U 85.02%)
- `eval/evermembench/INVESTIGATION.md` — MemOS Table 4 F_MH; F_TP; MA dims baseline
- `specs/2026-05-28-adaptive-query-classifier.md` — Lab Q1 #1 (composability alvo)
- `specs/2026-05-28-ma-protection-rerank.md` — Lab Q1 #2 (composability alvo + seção_boost precedent)
- `specs/2026-05-28-multi-query-expansion.md` — Lab Q1 #3 (parallel alternative attack)
- `[[phase-h-v2-cross-backbone-win]]` — baseline F_MH 10%, MA lead +12-24pp vs MemOS
- `[[cross-encoder-trade-off-shape]]` — MA reg Phase G; KG não tem esse problema
- `[[memory-awareness-dimension-must-be-audited]]` — MA silent killer; KG hipótese positiva
- `[[kg-relations-uses-fk-ids-not-inline-strings]]` — schema FK ids (obrigatório para SQL correto)
- `[[lightrag-kg-incremental-merge-pattern]]` — KG retrieval precedent; diferenciação
- `[[nox-mem-backbone-portability]]` — structural advantage; KG como adapter feature

---

## Closure esperado

Branch: `spec/multi-query-and-kg-path-retrieval`
PR: junto com `specs/2026-05-28-multi-query-expansion.md` (Lab Q1 #3 + #4 paired spec PR)
Próximo passo após merge: dispatch `executor` para Q1.6 (`adapter_nox_mem_kg.py` + 5-batch gate)
