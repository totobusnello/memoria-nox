# Competitive Analysis — 2026-05-19

> **Propósito:** documento de revisão pra outra sessão decidir, insight a insight, o que **adota / parqueia / rejeita** dos 3 repos analisados. Não é decisão tomada — é menu pra você avaliar.

---

## Contexto

Rodada de análise comparativa em 2026-05-19 noite, pós-G3 ablation e PR #148 (Wave A boost LIVE em 500 chunks). Objetivo: validar trincheira competitiva de nox-mem (Q/A/P) contra 3 repos relevantes do espaço retrieval/memory/RAG.

Comparação feita contra estado atual nox-mem:
- Schema v18, ~69k chunks prod
- Hybrid BM25 + Gemini dense 3072d + RRF (k=60)
- ~402 KG entities + ~544 relations
- Salience `recency × pain × importance` + section_boost (compiled 2.0 / frontmatter 1.5 / timeline 0.8)
- LongMemEval n=100: nDCG@10 = 0.9126 (D2, dense-only era, pre G1 sanitize fix)
- Single-file sqlite + sqlite-vec + FTS5 + Gemini API

---

## Repos analisados

| Repo | Stars | License | Categoria | Threat level |
|---|---|---|---|---|
| **cosmicstack-labs/mercury-agent** | 2.3k | MIT | Agent framework (FTS5-only memory embutida) | Baixo (categoria diferente) |
| **EverMind-AI/EverOS** | 5.0k | Apache 2.0 | Memory OS com papers + EverMemBench + HyperMem | **Alto** (mesma categoria, papers publicados) |
| **hkuds/lightrag** | 35.4k | MIT | Graph-RAG framework over documents (HKU, EMNLP 2025) | Baixo (categoria diferente, mas referência arquitetural forte) |

**Observação cross-cutting:** EverOS tem **OpenClaw plugin** no catálogo de use-cases — checar antes de qualquer decisão se é integration channel ou ameaça direta à VPS.

---

## Insights extraídos — menu de decisão

Cada insight tem: descrição, vetor estratégico (Q/A/P/Lab/GTM), custo estimado, pre-reqs, decisão proposta, perguntas pendentes.

---

### Insight 1 — Personality files markdown layer (Mercury-inspired)

**Descrição:** Mercury Agent usa `soul.md` + `persona.md` + `taste.md` + `heartbeat.md` em `~/.mercury/` como camada de identidade do agente, lidos pelo loop em runtime. Ortogonal ao memory schema, complementar.

**Vetor:** Product (não toca Quality nem Autonomy)

**Custo estimado:** Baixo (~1-2 sprints) se aplicado em nox-supermem; conceitual, não exige re-arquitetura

**Pre-reqs:** Decisão Stripe-first pivot consolidada [[D44]]; nox-supermem com surface real (hoje pre-launch)

**Decisão proposta:** **PARK** — interessante mas não prioridade Q0/Q1

**Perguntas pendentes:**
- Faz sentido em produto SaaS B2B ou só em produto pessoal/individual?
- Conflita com positioning "memory as substrate, agent-agnostic"?
- Tem ROI de adoção real ou é só polish que Mercury monetizou por timing?

**Memória relacionada:** `project_personality_files_markdown_layer.md`

---

### Insight 2 — EverOS publica papers + benchmarks; threshold pra paper técnico subiu

**Descrição:** EverOS publica 2 papers arxiv (2601.02163 EverCore, 2604.08256 HyperMem) + EverMemBench + EvoAgentBench + HF dataset. Mercury não tem números. memanto é closed. nox-mem precisa subir bar de credibility no paper técnico.

**Vetor:** Quality (paper credibility) + GTM (positioning)

**Custo estimado:** Médio — não é trabalho técnico novo, mas exige paper com números defensáveis contra benchmarks publicados

**Pre-reqs:** G1 sanitize fix consolidado + G3 ablation results + decisão se publica arxiv ou só blog

**Decisão proposta:** **ADOPT como threshold reference**, não como peer comparison ainda

**Perguntas pendentes:**
- Qual o caminho de publicação? Arxiv? Blog técnico? Whitepaper PDF?
- Vale tentar peer review acadêmica ou industry-only?
- Quem assina o paper? Issue de positioning autoral.

**Memória relacionada:** `project_everos_benchmark_publisher_competitor.md`

---

### Insight 3 — Neural reranker (bge-reranker-v2-m3) como vetor evolutivo pós-RRF

**Descrição:** EverOS usa neural reranker (deepinfra/vLLM). LightRAG recomenda bge-reranker-v2-m3 ou Jina como camada após retrieval. Ganhos típicos literatura: +3-8% nDCG sobre RRF puro. Stateless add-on, não altera schema.

**Vetor:** Quality + Lab (Q1/Q2 research)

**Custo estimado:** Médio (~2 sprints + ablation real obrigatória)
- Implementação: ~3-5 dias
- Ablation 4-way (none/cohere/deepinfra/local-bge): ~1 semana
- Shadow-mode validation: ≥1 semana

**Pre-reqs:**
- G3 ablation results consolidados (entender drivers atuais primeiro)
- Latency budget — p95 atual já em 2.3s, rerank tem que ficar ≤+200ms ou justificar via Quality jump
- Decisão de provider (Autonomy: vLLM local preferred sobre Cohere/deepinfra)

**Decisão proposta:** **PARK em Lab Q1/Q2** — não bloqueia Q0/Q1 atual (latency Q3 + Stripe pivot + Q4 gate mais críticos)

**Perguntas pendentes:**
- Vale o latency hit se nDCG já está em 0.9126?
- Cohere Rerank API é deal-breaker em Autonomy?
- Roda no mesmo container Gemini ou serviço separado?

**Memória relacionada:** `project_neural_reranker_evolution_vector.md`

---

### Insight 4 — Rodar nox-mem no EverMemBench (honest comparison)

**Descrição:** EverOS publica EverMemBench + HF dataset `EverMind-AI/everos_Eval_Results`. Comparação direta hoje é apples-to-oranges (nDCG vs accuracy via judge LLM). Rodar nox-mem no harness deles fecha benchmark gap [[benchmark-gap-longmemeval-locomo]] e dá número comparable.

**Vetor:** Quality + Lab Q1

**Custo estimado:** Médio (~3-5 dias)
- Fetch dataset HF + harness `methods/EverCore/evaluation/`
- Adapter layer: nox-mem search API → EverMemBench format
- Rodar em isolation (NOX_DB_PATH + large-DB guard)
- Análise + report

**Pre-reqs:**
- G1 sanitize fix consolidado
- G3 ablation results finalizados
- Eval harness com defesa em 4 camadas [[eval-harness-must-explicit-isolate-db]]
- NOX_ALLOW_PROD_INGEST=1 guard validado

**Decisão proposta:** **ADOPT em Lab Q1** — alto ROI (resolve gap + dá narrativa comparable)

**Perguntas pendentes:**
- Se nox-mem perde, publica mesmo assim com análise de drivers? Ou parqueia até fechar gap?
- Métrica accuracy via judge LLM é defensável ou viesada pelo judge model deles?
- EverMemBench é maintainable harness ou one-shot benchmark?

**Memória relacionada:** `project_everos_honest_comparison_benchmark_gap.md`

---

### Insight 5 — LightRAG KG incremental merge LLM-summarized

**Descrição:** LightRAG faz KG-extraction com merge incremental onde **LLM summariza descriptions duplicadas** (não overwrite, não append-naive). Approach mais escalável que deterministic dedup do nox-mem se density aumentar.

**Vetor:** Quality (KG quality) + Lab Q2+

**Custo estimado:** Médio (~1-2 sprints) quando triggered
- Estudar `lightrag/prompt.py` patterns
- Adaptar pra schema atual kg_entities/kg_relations FK
- Considerar Gemini 2.5 Pro pro merge step (Flash pode ser fraco em summarization)

**Pre-reqs:** **Trigger-based** — só faz sentido quando density crescer ≥10× (>4k entities). Hoje 402 entities, deterministic dedup serve.

**Decisão proposta:** **PARK em Lab Q2+ com trigger condition** — não fazer agora

**Perguntas pendentes:**
- Quando density realisticamente vai escalar? Indexar Granix/Galapagos/meetings é roadmap real?
- Vale Gemini 2.5 Pro pro merge ou Flash já basta?
- Approach LightRAG é provider-agnostic — manter compat com Gemini-locked atual ou abrir multi-provider em paralelo?

**Memória relacionada:** `project_lightrag_kg_incremental_merge_pattern.md`

---

## Cross-cutting takeaways

### Trincheiras defensáveis confirmadas

Nenhum dos 3 repos tem:
- **Pain-weighted salience explícita** — diferenciador único
- **Retention typed** (lesson 180d / decision 365d / daily 90d / feedback never_decay)
- **Section_boost com entity files** (compiled/frontmatter/timeline)
- **Single-file deployment** (1 sqlite + 1 API key vs 4-5 service docker stacks)

**Implicação:** "Hybrid memory with shadow discipline — yours by design" continua tagline defensável. Reforçar **deployment cost** como parte do "yours" — single-file sqlite é diferencial comercial real vs EverOS (MongoDB + ES + Milvus + Redis + Postgres + Vectorize.io API key).

### Gaps identificados

1. **Paper técnico com números publicados** — bar subiu (EverOS publica 2 papers arxiv + HF dataset)
2. **Catalog de use-cases reais** — EverOS tem 20+ catalogados, nox-mem tem dogfooding interno não-surfaced
3. **Neural reranker mainstream** — bge-reranker-v2-m3 é state-of-art 2025, RRF puro vai parecer datado
4. **Provider-agnostic real** — Gemini-locked operacional vs swap-able em teoria. LightRAG/EverOS provam em produção que multi-provider funciona
5. **WebUI + Ollama-compatible API** — polish que LightRAG tem (server SKU) e nox-mem não

### Wake-up call específico (Mercury)

Mercury capturou 2.3k stars em 30 dias com **FTS5 puro** porque embrulhou em multi-channel (CLI Ink TUI + Telegram + Web + Kanban) + personality + daemon cross-platform + DX impecável. Lição: **product surface vende mais que retrieval excellence**. Moat técnico do nox-mem (hybrid + pain + KG + section_boost) só importa se não for invisível.

---

## Action items pra outra sessão considerar

### Decisões binárias (sim/não)

- [ ] **Adopta Insight 2** (subir bar do paper técnico)? Implica decidir caminho de publicação.
- [ ] **Adopta Insight 4** (rodar EverMemBench)? Implica alocar Lab Q1 capacity (~3-5 dias).
- [ ] **Parqueia Insights 1, 3, 5** com triggers? OK?
- [ ] **Rejeita algum**? Justifica.

### Investigações pendentes

- [ ] **Confirmar threat vs opportunity do OpenClaw plugin no catálogo EverOS** (use-cases page). Critical — se é ameaça direta, muda prioridade.
- [ ] **Catalogar use-cases reais nox-mem** (Atlas/Boris/Cipher/Forge/Lex + Nox secretary + Granix integration + dogfooding) — para README/site/paper
- [ ] **Decidir narrativa "como nox-mem evolui"** (reflect/crystallize/consolidate) — vetor self-evolution que EverOS está vendendo

### Reforços de memórias existentes (não exige decisão nova)

- [[shadow-mode-for-ranking-changes]] aplicável a reranker quando vier
- [[static-analysis-vs-real-ablation]] aplicável a qualquer Insight 3/4/5 implementação
- [[eval-harness-must-explicit-isolate-db]] aplicável a Insight 4 (EverMemBench)
- [[no-getdb-in-eval-scripts]] aplicável a Insight 4

---

## Memórias salvas durante a rodada (cross-ref)

Todas em `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`:

1. `project_personality_files_markdown_layer.md` — Mercury soul/persona/taste
2. `project_everos_benchmark_publisher_competitor.md` — EverOS threshold
3. `project_neural_reranker_evolution_vector.md` — bge-reranker post-RRF
4. `project_everos_honest_comparison_benchmark_gap.md` — EverMemBench action
5. `project_lightrag_kg_incremental_merge_pattern.md` — LightRAG KG merge

Pointers no índice: `memory/MEMORY.md` linhas 74-78.

---

## Status doc

- **Criado:** 2026-05-19 noite (pós Wave A LIVE + G4-v3 SSH-blocked)
- **Autor:** sessão análise competitive (Toto + Claude)
- **Próximo:** revisão em outra sessão pra decisões binárias acima
- **Versão:** v1
