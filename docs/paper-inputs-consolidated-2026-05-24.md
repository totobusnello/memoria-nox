# Paper Inputs Consolidated — 2026-05-24

> Inputs estruturados de **7 repos/competidores estudados** + decisão de como aplicar ao paper técnico, narrativa e implementação. Disparado em sessão pós-análise do paper MeMo (arXiv 2605.15156v2).

**Status:** SOURCE OF TRUTH pra atualização do paper técnico, COMPARISON.md, e roadmap Lab Q1.

---

## 1. Repos analisados (one-liner)

| Repo | Stars | License | O que aprendemos |
|---|---:|---|---|
| **memanto** (moorcheh-ai) | closed | SaaS | `answer` como 3º primitive; temporal queries; framing "Six Gaps" |
| **EverOS / EverMind-AI** | 5k | Apache 2.0 | Único competidor com paper + benchmark + HF dataset; EverMemBench como threshold; plugin OpenClaw (!) |
| **LightRAG** (HKU EMNLP 2025) | 35k | MIT | LLM-summarized KG merge (vs nosso deterministic dedup); bge-reranker-v2-m3 |
| **Mercury Agent** | 2.3k | MIT | Personality files markdown (soul/persona/taste/heartbeat) como layer Product/UX |
| **HippoRAG2** | — | — | Graph + PPR (baseline conhecido) |
| **MeMo** (arXiv 2605.15156) | research | research | Parametric memory paradigm (oposto ao nosso); estilo de paper exemplar |
| **Neural reranker pattern** | — | — | Cross-encoder pós-RRF; bge-reranker-v2-m3 local via vLLM |

---

## 2. Adições ao PAPER (zero/baixo código, alta prioridade)

### P1. "Six Gaps" como spine narrativo da §1

Inspirado em memanto, igual MeMo cravou *reflections*. **Single design principle defensável.** Lista 6 gaps que sistemas de memória atuais sofrem, e cada gap vira coluna da Tabela 1 do paper.

**Tabela 1 — Comparison of desirable properties across memory systems:**

| Gap | nox-mem | mem0 | Letta | Zep | EverOS | LightRAG | MeMo |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1. Static injection | ✅ live writeback | ⚠️ | ✅ | ✅ | ✅ | ❌ batch | ❌ retrain |
| 2. No temporal decay | ✅ salience × recency | ❌ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| 3. No provenance | ✅ chunk_id+source | ⚠️ | ✅ | ✅ | ✅ | ✅ | ❌ em weights |
| 4. Flat memory | ✅ KG+entity files+section_boost | ❌ | ❌ | ✅ | ✅ hyper | ✅ dual | ❌ |
| 5. No writeback | ✅ crystallize/reflect | ⚠️ | ✅ | ✅ | ✅ Evo | ❌ | ❌ |
| 6. Indexing delay | ✅ inotifywait <1s | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ batch | ❌ retrain |

→ **Somos o único ✅ em todos 6.** É a tabela que ganha o paper.

### P2. §4.X "Self-Evolution: How nox-mem Improves Over Time" (counter EverOS EvoAgentBench)

EverOS tem narrativa "agent that evolves". A gente tem mas invisível no paper. Surface:

- **Crystallize loop** — `pending` → `lesson` após N hits, com pain accumulation
- **Pain weighting auto-adjust** — feedback de uso ajusta pain de chunks
- **Salience decay** — recency factor decai continuamente em background
- **Reflect pipeline** — batch nightly que sintetiza lessons cross-session

Custo: zero código, só doc estruturada.

### P3. Tabela "Autonomy quantificada"

Headline factual: **"100× menos overhead que EverOS"**.

| Sistema | Serviços | RAM idle | Cold start | API keys obrigatórias | Setup commands |
|---|---:|---:|---:|---:|---:|
| **nox-mem** | **1** (SQLite file) | **~50MB** | **<1s** | **0** (offline-ok) | **1** (`npm i`) |
| mem0 | 2 (Postgres + Qdrant) | ~800MB | ~15s | 1 (OpenAI) | ~5 |
| Letta | 3 (Docker + PG + OpenAI) | ~1.5GB | ~30s | 1 (OpenAI) | ~8 |
| Zep OSS | 2 (Docker + PG) | ~1.2GB | ~30s | **1 obrigatória (OpenAI)** | ~6 |
| EverOS | **5** (Mongo+ES+Milvus+Redis+PG) | **~4GB+** | **~60s** | 2-3 | ~15+ |
| LightRAG | 2 (Neo4j + vector DB) | ~1GB | ~20s | 1 | ~6 |

### P4. Abstract reframe — "pain-weighted hybrid memory" como single design principle

Estilo MeMo "reflections". Tudo deriva:

- **Salience formula** → recency × **pain** × importance
- **Retention typing** → pain alta = never-decay
- **Section boost** → compiled section = high-pain ground truth
- **Crystallize triggers** → pain acumulado dispara consolidation

**Tagline locked:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

### P5. Citation strategy

Citar explicitamente:
- **MeMo** (parametric paradigm) — como contraste de paradigma
- **LightRAG** (KG state-of-art) — como reference arquitetural pra incremental merge
- **HippoRAG2** (graph + PPR) — como baseline
- **mem0/Letta/Zep** (LoCoMo competitors) — como benchmark peers
- **EverOS** (only published benchmarks) — como threshold benchmark publisher

---

## 3. Adições ao DISCURSO/MOAT (sales/positioning)

### D1. **URGENTE:** Investigar plugin OpenClaw do EverOS

EverOS lista plugin OpenClaw em 20+ use cases. **Se for integration-fortified** = oportunidade partnership. **Se for ameaça-direta** = precisamos cravar diferencial no canal antes deles dominarem.

**Ação:** 1h research GitHub `EverMind-AI/EverOS` + Claude Code plugin marketplace.

### D2. Vendor lock-in matrix — cada competidor tem o seu

| Sistema | Lock-in |
|---|---|
| **Zep** | OpenAI embedding hardcoded |
| **EverOS** | Stack 5 serviços + 2-3 API keys |
| **agentmemory** | Engine proprietário fechado (iii-engine) |
| **mem0** | Postgres + Qdrant + OpenAI default |
| **Letta** | Docker + PG + agent-loop arch |
| **MeMo** | GPU training + per-corpus retrain |
| **nox-mem** | **MIT + SQLite + provider-agnostic** |

→ Vira slide pitch deck + tweet.

### D3. "Three primitives" narrative

`search(q)` + `recall(entity)` + **`answer(q)`** = tagline:

> **"3 primitives, 1 file, any LLM."**

Depende da implementação do C1.1 (`answer` primitive).

---

## 4. IMPLEMENTAR pra mais diferencial técnico

### C1. AGORA (Tier 1, pré-launch, ~7h total)

| # | Feature | Custo | Habilita |
|---|---|---:|---|
| **C1.1** | `answer` primitive — single call hybrid + Gemini synth grounded | ~2-4h | Pitch "3 primitives" + paper §3 |
| **C1.2** | Temporal queries `--as-of <date>` / `--changed-since <date>` | ~3-6h | Gap #2 explicit em tabela |

### C2. Lab Q1 (paralelo ao paper)

| # | Feature | Custo | Habilita |
|---|---|---:|---|
| **C2.1** | Neural reranker `bge-reranker-v2-m3` via vLLM local | ~1 semana | +3-8% nDCG, preserva Autonomy |
| **C2.2** | EverMemBench como 3º benchmark além de LoCoMo+LongMemEval | ~1 semana | Headline "we beat the leading published memory OS on their own harness" se ganharmos |

### C3. Trigger-based / Parking lot

- **LLM-summarized KG merge** (LightRAG pattern) — só quando density >4k entities (hoje ~400)
- **Personality files** (soul/persona/taste/heartbeat) — feature de **nox-supermem**, não nox-mem core

### C4. NÃO copiar (decisões)

| O que | Por quê |
|---|---|
| Closed SaaS backend (memanto) | Conflita com Autonomy |
| 5-service stack (EverOS) | Conflita com Autonomy |
| Dual-level retrieval sem ablation (LightRAG) | Categoria diferente (RAG-over-docs vs episódica), pode não ganhar |
| Parametric memory (MeMo) | Paradigma oposto — mantemos como contraste no paper |

---

## 5. Síntese — 5 entregas concretas (tabela master)

| # | Entrega | Tipo | Custo | Impacto |
|---|---|---|---:|---|
| **1** | Abstract reframe: "pain-weighted hybrid memory" como single design principle | doc | 30min | Tagline defensável |
| **2** | Tabela "Six Gaps" como nova Table 1 do paper | doc | 1h | Spine narrativo igual MeMo |
| **3** | §4.X "Self-Evolution" descrevendo reflect/crystallize/consolidate | doc | 2h | Counter EverOS EvoAgentBench |
| **4** | Tabela "Autonomy quantificada" (serviços/RAM/cold start) | doc | 1h | Headline "100× menos overhead" |
| **5** | `answer` + temporal queries implementadas no CLI/API/MCP | código | ~7h | Habilita "3 primitives" tagline + Gap #2 |

---

## 6. Fontes de cada input (memory backlinks)

- `[[memanto-inspired-ideas]]` — answer primitive, temporal, Six Gaps
- `[[everos-benchmark-publisher-competitor]]` — threshold benchmark
- `[[everos-honest-comparison-benchmark-gap]]` — EverMemBench action item
- `[[lightrag-kg-incremental-merge-pattern]]` — LLM-summarized merge + bge-reranker
- `[[neural-reranker-evolution-vector]]` — cross-encoder Lab Q1
- `[[personality-files-markdown-layer]]` — Mercury Product/UX layer
- `[[benchmark-gap-longmemeval-locomo]]` — agora fechado (Q4 rodou)
- `[[repo-visual-style]]` — landing inspiration

---

## 7. Próximos passos (este doc dispara)

- ✅ Salvar este documento como source of truth
- 🟡 PR paper updater (entregas 1-4 acima)
- 🟡 PR code implementer (entrega 5: `answer` + temporal)
- 🟡 PR COMPARISON.md updater (per-category cross-system + Skip-Zep narrativa)
- ⏳ Agente background: HippoRAG2 + LightRAG adapters (~1-2 dias)
- ⏳ Lab Q1 backlog: EverMemBench harness + bge-reranker

**Última revisão:** 2026-05-24 noite, pós-análise paper MeMo + recuperação memória de 7 repos.
