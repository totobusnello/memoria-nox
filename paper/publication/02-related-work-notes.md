# Related Work Notes — para §2 Related Work do paper arXiv

> **Goal:** 8-10 papers citados corretamente, posicionar nox-mem honest. Reviewer técnico vai cobrar fitness com prior work — melhor cobrir aqui agora.

---

## 🎓 Papers PRIMARY (citation obrigatória)

### 1. GraphRAG (Microsoft, Edge et al. 2024)
- **Paper:** "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (arXiv:2404.16130)
- **TL;DR:** LLM extrai entities + relations sobre chunks → community detection (Leiden) → multi-level summarization → query-time hybrid retrieval
- **Como nox-mem se relaciona:**
  - Same: KG construction via LLM (Gemini 2.5 Flash em nox-mem, GPT-4 em GraphRAG)
  - Diferencia: GraphRAG = community summarization pra global queries; nox-mem = entity-centric local retrieval + edge typing closed enum
- **Citation positioning:** "Following GraphRAG's KG construction methodology [Edge et al., 2024], we focus on operational entity-centric retrieval rather than community summarization, with closed-enum edge typing for downstream blast-radius analysis"

### 2. MemGPT / Letta (Berkeley, Packer et al. 2023)
- **Paper:** "MemGPT: Towards LLMs as Operating Systems" (arXiv:2310.08560)
- **TL;DR:** Hierarchical memory (main context + external context) com LLM-managed paging via function calls; "OS for agents" metaphor
- **Como nox-mem se relaciona:**
  - Same: persistent memory pra LLM agents
  - Diferencia: MemGPT = per-agent state managed BY agent itself; nox-mem = shared canonical state managed by external pipeline (watcher + ingest)
- **Citation positioning:** "Unlike MemGPT's [Packer et al., 2023] OS-inspired per-agent paging where the agent autonomously manages context, we adopt a shared-canonical model with external pipeline management for trusted multi-agent deployments"

### 3. Mem0 (Chhikara et al. 2025)
- **Paper:** "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (arXiv:2504.19413)
- **TL;DR:** Self-improving memory via LLM-driven extraction + dedup + temporal updates; vector-only retrieval; +26% LOCOMO accuracy vs baselines
- **Como nox-mem se relaciona:**
  - Same: production focus, long-term memory, LLM extraction
  - Diferencia: Mem0 self-improves via LLM editing decisions; nox-mem requires human validation (shadow-mode) before any retrieval-affecting change
- **Citation positioning:** "While Mem0 [Chhikara et al., 2025] explores autonomous LLM-driven memory editing, we prioritize human-in-the-loop validation through enforced shadow periods to mitigate silent regression risk"
- **Comparison opportunity:** se possible, run nox-mem na LOCOMO benchmark pra direct apples-to-apples

### 4. A-MEM (2024)
- **Paper:** "A-MEM: Agentic Memory for LLM Agents" (arXiv:2502.12110)
- **TL;DR:** Zettelkasten-inspired auto-tagging + auto-linking; agentic memory updates
- **Como nox-mem se relaciona:**
  - Same: structured memory beyond flat chunks
  - Diferencia: A-MEM auto-links via LLM, nox-mem manual entity files com `<!-- retention: -->` annotations + KG extraction
- **Citation positioning:** Cite as inspiration for §3 (Knowledge Graph Construction)

### 5. HiRAG (2024)
- **Paper:** "HiRAG: Retrieval-Augmented Generation with Hierarchical Knowledge" (arXiv:2503.10150)
- **TL;DR:** Multi-level hierarchical KG + iterative retrieval com reasoning chains; SOTA em multiple QA benchmarks
- **Como nox-mem se relaciona:**
  - Same: hybrid retrieval combining structured + unstructured
  - Diferencia: HiRAG = hierarchical reasoning chains (depth-oriented), nox-mem = flat 3-layer fusion (latency-oriented)
- **Citation positioning:** "Unlike HiRAG's [Liu et al., 2024] hierarchical reasoning approach optimized for accuracy, we maintain flat 3-layer RRF fusion to preserve sub-second latency for operational use cases (p95 < 1s on 64K chunk corpus)"

### 6. Cognee (2024)
- **Paper:** Cognee project (open-source, white paper Dec 2024)
- **TL;DR:** Open-source AI memory framework com KG + hybrid + ECL pipeline (Extract-Cognify-Load)
- **Como nox-mem se relaciona:**
  - Same: hybrid retrieval + KG nativo
  - Diferencia: Cognee = generic framework pra qualquer use case; nox-mem = vertical solution otimizada pra operational/multi-agent + eval-harness gated
- **Citation positioning:** "Cognee provides a general-purpose framework with similar architectural primitives; we differentiate through enforced shadow validation and operational-specific tuning"

---

## 🎓 Papers SECONDARY (citação contextual)

### 7. RAG (Lewis et al. 2020) — foundational
- **Paper:** "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (NeurIPS 2020)
- **Citation:** Background section, single mention.

### 8. Reciprocal Rank Fusion (Cormack et al. 2009)
- **Paper:** "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (SIGIR 2009)
- **Citation:** Methods section §4 quando descrever fusion layer.

### 9. BGE-M3 (Chen et al. 2024)
- **Paper:** "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings" (arXiv:2402.03216)
- **Citation:** Used as one of the baselines em experiments.

### 10. E5-mistral (Wang et al. 2024)
- **Paper:** "Improving Text Embeddings with Large Language Models" (arXiv:2401.00368)
- **Citation:** Used as second strong baseline em experiments.

---

## 🎓 Papers OPCIONAL (citar se cabe space)

### 11. LIRS cache (Jiang & Zhang 2002)
- **Reason:** Salience formula tem analogia com cache replacement policies (recency × frequency × cost)
- **Citation:** Diferencial #1 — pode citar como inspiration distante pra "pain dimension"

### 12. LangChain Memory primitives
- **Reason:** Industrial baseline mais comum
- **Citation:** Methods §4 quando comparar API design

---

## 📊 Comparison table draft (para §5 Experiments)

| Sistema | KG nativo | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline |
|---|---|---|---|---|---|
| **nox-mem (ours)** | ✅ closed-enum edge typing | ✅ FTS5+Gemini+RRF | ✅ R01a nDCG/MRR/Recall | ✅ shared canonical | ✅ enforced ≥7d |
| GraphRAG | ✅ + community detection | ⚠️ via KG queries | ❌ | ❌ | ❌ |
| MemGPT/Letta | ❌ | ⚠️ embedding-first | ❌ | ✅ per-agent state | ❌ |
| Mem0 | ⚠️ optional v2 | ❌ vector-only | ⚠️ LOCOMO benchmark only | ⚠️ user_id partition | ❌ |
| A-MEM | ⚠️ Zettelkasten auto-links | ⚠️ semantic-first | ❌ | ❌ | ❌ |
| HiRAG | ✅ hierarchical | ✅ multi-level | ⚠️ task-specific | ❌ | ❌ |
| Cognee | ✅ ECL pipeline | ✅ hybrid | ⚠️ ad-hoc | ⚠️ optional | ❌ |
| LangChain Memory | ❌ | ❌ key-value/buffer | ❌ | ⚠️ session_id | ❌ |

---

## ⚠️ Potential reviewer objections + preempção

### Objection 1: "nox-mem é só engineering, sem novelty teórica"
**Response em paper:** Section 6 (Discussion) explicitly frames as "operational synthesis paper" with 3 specific novel contributions (pain dimension, shadow discipline, shared-canonical multi-agent), each with empirical validation in §5.

### Objection 2: "Edge typing é só RDF/OWL re-discovered"
**Response:** RDF/OWL define schema in advance; we LLM-extract closed-enum reasons from unstructured text. Diferencia in *acquisition*, not in *expressivity*.

### Objection 3: "Comparison only against weak FTS-only baseline"
**Response:** Addressed in revisions — added BM25 (Pyserini), BGE-M3, E5-mistral baselines em §5. (Gap #3 fix mandatory before submit.)

### Objection 4: "Single corpus, single curator"
**Response:** Addressed in revisions — BEIR subset + Stack Exchange dump em §5.X. Internal-curator bias documented em §1.4 + held-out subset analysis. (Gap #1+#2 fix.)

### Objection 5: "Shadow discipline é trivial — só A/B testing"
**Response:** A/B testing requires production traffic; shadow discipline em personal/operational corpus has no traffic — we develop methodology for offline shadow validation via telemetry comparison. Frame as methodology contribution.
