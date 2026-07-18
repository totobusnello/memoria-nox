# nox-mem — Fundações técnicas

**Os artigos, repositórios e bases de conhecimento sobre os quais o sistema foi construído.**

> Documento de referência para leitura externa. As fontes abaixo foram curadas a
> partir da bibliografia verificada do paper (checada em 2026-05-22: URLs, DOIs,
> arXiv IDs e autoria). Dados operacionais e proprietários (infraestrutura, chaves,
> endpoints, resultados sob embargo) foram deixados de fora de propósito — este é
> um mapa das *fontes*, não do deployment.

---

## 1. Em uma frase

nox-mem é um sistema de memória de longo prazo para agentes LLM: um único arquivo
SQLite que combina busca híbrida (lexical + semântica), um knowledge graph e um
ranqueamento por *salience* ponderado por severidade ("pain-weighted"). A ideia de
design é que a memória seja portável e sua — um arquivo, sem vendor lock-in, com o
provider de embeddings à sua escolha.

---

## 2. Artigos acadêmicos

### 2.1 Fundamentos de retrieval — a base do ranker

- **Robertson & Zaragoza (2009).** *The Probabilistic Relevance Framework: BM25 and Beyond.*
  Foundations and Trends in IR, 3(4). DOI: [10.1561/1500000019](https://doi.org/10.1561/1500000019).
  → Base teórica do BM25, que é o componente lexical (via FTS5 do SQLite).

- **Cormack, Clarke & Buettcher (2009).** *Reciprocal Rank Fusion Outperforms Condorcet
  and Individual Rank Learning Methods.* SIGIR '09.
  DOI: [10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114).
  → RRF é o método usado para fundir os rankings lexical (BM25) e semântico (k=60).

### 2.2 Sistemas de memória para agentes — o campo

- **Packer et al. (2023).** *MemGPT: Towards LLMs as Operating Systems.*
  arXiv:[2310.08560](https://arxiv.org/abs/2310.08560).
  → Fundador da linha "LLM como OS de memória"; produtizado depois como Letta.

- **Guo, Xia, Yu, Ao & Huang (2024).** *LightRAG: Simple and Fast Retrieval-Augmented
  Generation.* arXiv:[2410.05779](https://arxiv.org/abs/2410.05779) (grupo HKUDS/HKU).
  → Referência para o padrão de *incremental KG-merge com sumarização por LLM*.

- **Hu et al. (2026).** *EverMemOS: A Self-Organizing Memory Operating System for
  Structured Long-Horizon Reasoning.* arXiv:[2601.02163](https://arxiv.org/abs/2601.02163).
  → Sistema concorrente; publica o benchmark EverMemBench (ver §4).

### 2.3 Benchmarks — como se mede memória

- **Maharana et al. (2024).** *Evaluating Very Long-Term Conversational Memory of
  LLM Agents.* ACL 2024 (Long Papers). arXiv:[2402.17753](https://arxiv.org/abs/2402.17753).
  → Dataset **LoCoMo**, um dos dois benchmarks primários.

- **Wu et al. (2024).** *LongMemEval: Benchmarking Chat Assistants on Long-Term
  Interactive Memory.* ICLR 2025. arXiv:[2410.10813](https://arxiv.org/abs/2410.10813).
  → Dataset **LongMemEval (LME)**, o segundo benchmark primário.

- **Yang et al. (2018).** *HotpotQA: A Dataset for Diverse, Explainable Multi-hop
  Question Answering.* EMNLP 2018. arXiv:[1809.09600](https://arxiv.org/abs/1809.09600).
  → Multi-hop QA, usado em experimentos auxiliares de retrieval.

- **Bueno et al. (2024).** *Quati: A Brazilian Portuguese Information Retrieval Dataset
  from Native Speakers.* STIL 2024. arXiv:2404.06976.
  → Referência multilíngue (PT-BR) para robustez de retrieval fora do inglês.

---

## 3. Repositórios open-source

### 3.1 Stack — o que faz o nox-mem rodar

| Componente | Repositório / fonte | Papel no sistema |
|---|---|---|
| **SQLite FTS5** | módulo nativo do SQLite | Busca lexical BM25 (full-text) |
| **sqlite-vec** | [asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) | Vector search dentro do SQLite (vetores de 3072 dimensões) |
| **better-sqlite3** | driver Node/TypeScript | Acesso síncrono ao arquivo SQLite |
| **Gemini Embedding** | [`gemini-embedding-001`](https://ai.google.dev/gemini-api/docs/models) (Google DeepMind) | Embeddings semânticos 3072d |

> O provider de embeddings é intercambiável por design — Gemini é o default, mas a
> arquitetura aceita outros (OpenAI-compatible etc.). Essa é a tese de "autonomia":
> os dados e a escolha de provider são do usuário.

### 3.2 Sistemas comparados / relacionados

| Sistema | Repositório | Natureza |
|---|---|---|
| **Mem0** | [mem0ai/mem0](https://github.com/mem0ai/mem0) | Memory layer para agentes (backend PostgreSQL/Qdrant) |
| **Zep** | [getzep/zep](https://github.com/getzep/zep) | Memória por temporal knowledge-graph |
| **Letta** (ex-MemGPT) | [letta-ai/letta](https://github.com/letta-ai/letta) | Agent framework com memória stateful |
| **agentmemory** | [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) | Memória persistente para coding agents |
| **EverOS** | [EverMind-AI/EverOS](https://github.com/EverMind-AI/EverOS) | Memory OS; publica o EverMemBench |
| **LightRAG** | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | RAG com KG incremental (MIT) |

---

## 4. Bases de conhecimento / datasets de avaliação

**Primários** (os que sustentam as comparações do paper):

- **LoCoMo** — memória conversacional de muito longo prazo (Maharana et al. 2024).
- **LongMemEval (LME)** — memória interativa de longo prazo (Wu et al. 2024).
- **EverMemBench** — benchmark publicado junto do EverOS/EverMemOS (Hu et al. 2026).

**Auxiliares** (explorados no desenvolvimento do retrieval, multi-hop QA):

- **HotpotQA** (Yang et al. 2018), **MuSiQue** (Trivedi et al. 2022),
  **2WikiMultihopQA** (Ho et al. 2020), **NarrativeQA** (Kočiský et al. 2018).
- **Quati** (Bueno et al. 2024) — validação de retrieval em português.

---

## 5. Como as peças se encaixam (arquitetura conceitual)

```
ingest → chunks (SQLite)
           ├── FTS5 index  ──► BM25            (lexical)
           └── sqlite-vec  ──► Gemini 3072d    (semântico)
                                    │
                             RRF fusion (k=60)
                                    │
                        salience re-rank
              (importance + recency + pain + access)
                                    │
                                 resposta
        + knowledge graph (entidades/relações) por cima do corpus
```

O diferencial conceitual do nox-mem em relação aos sistemas da §3.2 é a combinação
de: (a) **um único arquivo** portável (SQLite), (b) **provider de embeddings
substituível** (sem lock-in), e (c) **ranqueamento por *pain-weighted salience*** —
memórias associadas a eventos mais severos/importantes decaem mais devagar e sobem
no ranking.

---

## Nota sobre o que ficou de fora (de propósito)

Este documento lista apenas *fontes públicas* — artigos, repos open-source e datasets
citáveis. Foram deliberadamente omitidos: detalhes de infraestrutura (servidores,
IPs, portas, endpoints, tokens), configuração de deployment, tabelas de resultados
competitivos ainda sob embargo de publicação, e qualquer dado de negócio. Para os
números e a metodologia completa, a referência é o paper do próprio sistema quando
publicado.

*Fontes verificadas em 2026-05-22 (URLs/DOIs/arXiv/autoria). Curadoria: bibliografia canônica do paper nox-mem.*
