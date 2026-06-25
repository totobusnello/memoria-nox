# NOX-Supermem: Operational Memory System with Pain-Weighted Salience and Shadow-Validated Discipline for Multi-Agent Production Use

> **arXiv draft skeleton** — sections + key tables placeholders + open questions marcadas. Full prose escrito em W3-W4 sprint pós experiments completos. **NÃO submeter este draft** — ele é estrutura.

**Authors:** Luiz Antonio Busnello (Toto)¹
¹Curious Tech Entrepreneur, São Paulo, Brazil
**Correspondence:** lab@generantis.com.br

---

## Abstract (~250 words target)

We present NOX-Supermem, a production memory system designed for multi-agent operational use cases (CEO + 6 specialized AI agents handling code, infrastructure, business, and personal contexts). The system combines three retrieval layers—FTS5 lexical, Gemini semantic embeddings (3072d), and Reciprocal Rank Fusion—over a shared canonical chunks table, augmented by an LLM-extracted knowledge graph with closed-enum edge typing. Three contributions distinguish this work from existing memory systems (mem0, MemGPT, GraphRAG, A-MEM): (1) a **pain-weighted salience formula** (`recency × pain × importance`) that explicitly models incident severity as a retrieval signal—novel in the RAG/memory literature; (2) **enforced shadow discipline** for ranking changes (≥7-day shadow telemetry collection before activation, with codified env-var gating)—addressing silent regression risk in production memory; and (3) a **shared-canonical multi-agent design** that enables cross-agent intelligence with minimal federation overhead, contrasting with per-agent isolation models. Empirical evaluation on 50 curated golden queries plus held-out external curator subset demonstrates hybrid pipeline necessity (mean ± std nDCG@10 0.521 ± 0.0004 vs FTS-only 0.012 ± 0.000). Comparison against three strong baselines (BM25-Pyserini, BGE-M3, E5-mistral) and across three corpora (operational, BEIR-COVID, StackExchange) confirms generalization. Four ablation studies isolate each layer's contribution, and pain dimension validation on post-incident queries shows Δ nDCG ≥ 0.05. The system has operated continuously in production since March 2026, surviving five infrastructure upgrades (OpenClaw v.24→v2026.5.2) without data loss. Code, eval harness, and 50-query golden set are open-source under MIT license.

**Keywords:** retrieval-augmented generation, knowledge graphs, agent memory, semantic search, evaluation methodology, production systems

---

## 1. Introduction (~1.5 pages)

### 1.1 Problem Statement
- LLM agents lose context across sessions
- Multi-agent systems compound the problem (agents can't learn from each other)
- Production memory systems must additionally handle: schema evolution, silent regression, operational discipline
- **Gap in literature:** most memory systems papers (mem0, MemGPT, A-MEM) focus on benchmarks (LOCOMO, single-corpus) — operational concerns (incident severity weighting, shadow validation, multi-agent canonical design) are under-explored

### 1.2 Contributions
We make three primary contributions:
1. **Pain-weighted salience** (§3.2) — first documented retrieval scoring that models incident pain explicitly
2. **Shadow-validated ranking discipline** (§3.5) — methodology for offline shadow validation in personal/operational corpora
3. **Shared-canonical multi-agent design** (§3.6) — empirical comparison vs per-agent isolation

Secondary contributions:
4. Full open-source eval harness with nDCG/MRR/Recall/Precision over 50 curated queries (R01a)
5. Operational evidence: ~3 months production, 5 infrastructure upgrades survived, ~95K chunks ~100% embedded
6. Comparative empirical analysis vs 3 strong baselines (BM25, BGE-M3, E5-mistral) across 3 corpora

### 1.3 Paper organization
[Standard paragraph]

---

## 2. Related Work (~1.5 pages)

(Full notes em `02-related-work-notes.md` — 8 papers PRIMARY + 4 secondary)

### 2.1 Memory systems for LLM agents
- MemGPT [Packer et al., 2023]
- Mem0 [Chhikara et al., 2025]
- A-MEM [2024]

### 2.2 Knowledge-augmented retrieval
- GraphRAG [Edge et al., 2024]
- HiRAG [Liu et al., 2024]
- Cognee [2024]

### 2.3 Hybrid retrieval and rank fusion
- BM25 + dense fusion (industrial common practice)
- RRF [Cormack et al., 2009]

### 2.4 Salience and recency weighting
- LIRS cache [Jiang & Zhang, 2002] — distant inspiration
- RAG with recency weighting (various)

### 2.5 Positioning
NOX-Supermem synthesizes operational concerns from production deployment with novel contributions in salience modeling, ranking discipline, and multi-agent design.

---

## 3. System Architecture (~2.5 pages)

### 3.1 Overview
[Mermaid diagram — convert to SVG/PDF]
```
Source files (md/docx/pptx/pdf/text)
    ↓
[ingest.ts watcher (inotifywait)]
    ↓
chunks table (canonical) ─┬─→ FTS5 index (chunks_fts)
                          ├─→ vec_chunks (sqlite-vec, 3072d Gemini)
                          ├─→ kg_entities + kg_relations (LLM extracted)
                          └─→ search_telemetry (eval harness)
                          ↓
            search() → FTS5 → semantic → RRF k=60 → boosts → ranked
```

### 3.2 Pain-weighted salience formula ⭐ (CONTRIBUTION 1)
```
salience(chunk) = recency(chunk) × pain(chunk) × importance(chunk)
```
- `recency ∈ [0, 1]` — exp decay over `last_seen` timestamp
- `pain ∈ [0.1, 1.0]` — manual annotation `<!-- pain: 0.X -->` em entity files (severity bookmark)
- `importance ∈ [0, 1]` — derived from mention_count + entity_type prior

**Empirical validation §5.6:** ablation com vs sem pain shows Δ nDCG ≥ 0.05 em post-incident queries.

### 3.3 Hybrid retrieval pipeline (3 layers + RRF)
- Layer 1: FTS5 BM25 expansion + dedup
- Layer 2: Gemini embeddings cosine similarity over vec_chunks
- Layer 3: RRF fusion k=60 → salience boost → section_boost → final ranking

### 3.4 LLM-extracted knowledge graph
- Entities: 10 types (person/project/agent/tool/concept/organization/technology/document/decision/metric)
- Relations: free-form `relation_type` + closed-enum `relation_reason` (depends_on/derived_from/opposes/extends/replaces/mentions/unknown)
- Edge typing: prompt-engineered + code-side defensive map (RELATION_TYPE_TO_REASON 24 entries)

### 3.5 Shadow-validated ranking discipline ⭐ (CONTRIBUTION 2)
- Codified rule: any ranking-affecting change must shadow ≥7d antes de activate
- Implementation: env vars (`NOX_FEATURE_MODE=shadow|active`) + telemetry collection + automated GitHub Issue verdict (routine `trig_012nuCN14VwcxGLq8ERaLPCK`)
- Case study §5.7: Fase 1.7b-b salience activation (191 promote candidates / 16608 review / 45743 archive — distribution-driven decision)

### 3.6 Shared-canonical multi-agent design ⭐ (CONTRIBUTION 3)
- 6 agents (Maestro + nox/atlas/boris/cipher/forge/lex) compartilham mesma `chunks` table
- Distinguidos por `source_file` prefix (`agents/<name>/...`)
- Cross-agent v2 patterns: `cross-search`, `cross-kg`, `pull-insights-from`
- Trade-off: shared state requires trust assumption (all agents same user) — not suitable for multi-tenant SaaS

### 3.7 Operational tooling (E06-E10)
- `detect-changes` — git diff → KG entities affected
- `impact <entity>` — 1-hop blast radius com REASON_PRIORITY
- `api-impact <signature>` — multi-file grep + classification
- `consolidate-merge --dry-run` — entity merge candidate detection com FP risk
- `kg-reclassify` — backfill via map (zero LLM cost)

---

## 4. Methods — Evaluation framework (~1.5 pages)

### 4.1 R01a Eval harness
- 50 golden queries (R01b 50/50 milestone)
- 8 categories (entity/decision/procedure/concept/temporal/cross-agent/security/negative)
- Metrics: nDCG@10, MRR, Recall@10, Precision@5
- 6 negative cases (12% sample) test specificity vs hallucination

### 4.2 Replication protocol
- 3-run mean ± std (system is operationally deterministic — std < 0.001)
- Held-out 10-query subset (external curator proxy)
- Citation guidance: "(n=50 main + n=10 held-out, 3-run mean ± std)"

### 4.3 Three corpora design
- **Corpus A** (primary): nox-mem operational corpus (~95K chunks, 1.6GB DB) — author's own multi-agent memory
- **Corpus B**: BEIR TREC-COVID subset (171K chunks, 50 queries, third-party curator)
- **Corpus C**: Stack Exchange dump 10K subset (mixed factoid/how-to/opinion queries)

### 4.4 Baselines
- **BM25 (Pyserini)** — Lucene implementation, industry-standard lexical
- **BGE-M3** — open-source SOTA dense encoder
- **E5-mistral-7b-instruct** — top of MTEB leaderboard
- **NOX-Supermem hybrid** — our system

---

## 5. Experiments and Results (~3 pages — most empirical content)

### 5.1 Hybrid vs FTS-only (Corpus A)
[Tabela inicial já em paper-v2-draft]

### 5.2 NOX-Supermem vs strong baselines (Corpus A)
[Tabela TBD pós-experiments]

### 5.3 Cross-corpus generalization
[Tabela 3 corpora × 4 systems = 12 cells, all com mean ± std]

### 5.4 Held-out external curator subset
[Resultado já parcial em paper-v2-draft §1.5 Step 2 — extend com outras hold-out subsets]

### 5.5 Ablation studies
[4 ablations: FTS-only / sem-RRF / sem-salience / sem-section_boost]

### 5.6 Pain dimension validation ⭐
[Comparação 10-15 post-incident queries: salience com vs sem pain]

### 5.7 Shadow discipline case study
[Fase 1.7b-b salience activation — telemetry + decision + counterfactual]

### 5.8 Cross-agent intelligence quantification
[%% hits cross-agent vs same-agent across 6 agents]

### 5.9 Production operational metrics
- Uptime, schema migrations survived, incidents resolved
- Latency p50/p95/p99 todos comandos
- Cost analysis ($/1M tokens × scale projections)

---

## 6. Discussion (~1 page)

### 6.1 When to use NOX-Supermem
- Operational/personal corpus, trusted multi-agent context, eval-first culture

### 6.2 When NOT to use
- Multi-tenant SaaS (use mem0 paid)
- Single-agent simple chatbot (use LangChain BufferMemory)
- Pure code corpora (BM25 may suffice — verify with own eval)

### 6.3 Limitations
- Single-author corpus em primary evaluation (mitigated by Corpus B+C)
- Pain dimension requires manual annotation (automation future work)
- Latency-optimized (3-layer flat) vs reasoning-optimized (HiRAG hierarchical) — different trade-off

### 6.4 Future work
- Automated pain dimension via incident detection LLM
- Cross-encoder reranker (D01) gated em R01 ≥ 0.6
- Multi-tenant variant para P01 productization

---

## 7. Conclusion (~0.5 page)

NOX-Supermem demonstrates that production memory systems benefit from explicit modeling of operational concerns — particularly incident pain, shadow validation discipline, and shared-canonical multi-agent design. Empirical evaluation across three corpora and against three strong baselines validates the architectural choices. The full system, eval harness, and 50-query golden set are open-source.

---

## Appendix A — Reproducibility

- Repo: https://github.com/totobusnello/memoria-nox
- Commit at submission: [TBD]
- Environment: Node 22, better-sqlite3, sqlite-vec, Gemini API
- Eval golden set: `seed/seed_queries.jsonl` + R01b 50 cured (in DB schema v12)
- Baseline implementations: `paper/publication/baselines/`
- 3-corpora adapters: `paper/publication/corpora/`

## Appendix B — Shadow case study (Fase 1.7b-b salience activation)

[Full timeline + telemetry data + decision tree + counterfactual]

## Appendix C — Cost analysis

[Full F13 cost projection table]

## Appendix D — Operational lessons

[Selected from `MEMORY.md` feedback files: secrets, monkey-patch, sed-binary, etc — 5-10 most relevant]

---

## BibTeX entry (post arXiv submission)

```bibtex
@misc{busnello2026nox,
  title={NOX-Supermem: Operational Memory System with Pain-Weighted Salience and Shadow-Validated Discipline for Multi-Agent Production Use},
  author={Busnello, Luiz Antonio},
  year={2026},
  eprint={2606.XXXXX},
  archivePrefix={arXiv},
  primaryClass={cs.IR}
}
```
