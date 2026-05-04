# Positioning Strategy — NOX-Supermem

> **Goal:** posicionar honestamente como sólida engenharia operacional + 3 contribuições genuinamente novas, sem oversell que reviewer técnico vai derrubar.

---

## 🎯 3 diferenciais REAIS a exaltar (foco em substantia)

### Diferencial #1 — Pain dimension em salience formula ⭐ MAIS PROMISSOR
**Claim:** Primeira retrieval system documentada que modela **severity/pain de incidents passados** como signal explícito de retrieval, separado de recency e importance.

**Por quê é novo:**
- Recency-weighted retrieval: existe (RAG, vector DBs implementam decay)
- Importance scoring: existe (BM25 pondera, PageRank pondera)
- **Pain dimension** (lessons learned from incidents): **nenhum paper RAG/memory system anterior modela isso explicitamente**

**Formula nox-mem:** `salience = recency × pain × importance` onde:
- `recency` ∈ [0, 1]: exponential decay sobre `last_seen`
- `pain` ∈ [0.1, 1.0]: severity bookmark (0.1 trivial → 1.0 prod-outage), set manualmente em entity files com `<!-- pain: 0.8 -->` tag
- `importance` ∈ [0, 1]: derived from mention_count + entity_type prior

**Como provar empiricamente:**
- Ablation study: `nDCG@10 com pain` vs `nDCG@10 sem pain (uniform 1.0)` em queries categorizadas como "post-incident questions" (Q47 withOpAudit, Q67 rsync delete, Q71 reindex incident lesson)
- Hipótese: queries pós-incident têm Δ nDCG ≥ 0.05 favorecendo pain-aware

**Risco:** `pain` é manual annotation — viability em corpus público é questão aberta.

### Diferencial #2 — Shadow-mode discipline obrigatório pra ranking changes ⭐ METHODOLOGY NOVA
**Claim:** Primeira RAG/memory system com regra arquitetural codificada de **"every ranking change must shadow ≥7d antes de activate"** + automation pra enforcement.

**Por quê é novo:**
- A/B testing em search: existe há 20 anos (Google, Amazon)
- Shadow deployments: existe em ML serving (Kubeflow, Seldon)
- **Combinação enforced via env vars + DB telemetry + cron alert + automated GitHub Issue verdict**: nenhum competitor de memory system faz isso explicit

**Como provar empiricamente:**
- Document case study: Fase 1.7b-b salience activation em 2026-04-30
  - Shadow 7d telemetry coletada
  - 191 promote_candidates / 16608 review_needed / 45743 archive_candidates
  - Activate baseado em distribution analysis, NÃO opinião
- Comparar vs counterfactual: "what if we activated immediately?" — referenciando incident 2026-04-25 que foi exatamente isso (reindex sem dry-run)

**Risco:** este é methodology paper, não system paper — venue choice importa (RecSys industrial > NeurIPS).

### Diferencial #3 — Multi-agent canonical chunks (não silos por agente) ⭐ CONTRARIAN
**Claim:** Diferente de MemGPT/Letta (per-agent isolated state) e mem0 (per-user isolation), nox-mem usa **shared canonical `chunks` table com agent-scoped views via `source_file` filtering**, permitindo cross-agent intelligence sem federação overhead.

**Por quê é diferente:**
- MemGPT: agent é memory boundary — agents não veem decisões uns dos outros sem explicit handoff
- mem0: user_id partitioning — projetado pra B2C com isolation strong
- nox-mem: 6 working agents (Maestro orchestrator + 5 specialized personas) compartilham mesmo `chunks` table, distinguidos por `source_file` prefix (`agents/<name>/...`) + `cross-agent v2` patterns pra synthesis

**Como provar empiricamente:**
- Quantificar `cross_agent_search` queries hits — quantos chunks que ajudam um agent vieram de outro?
- Latency comparison: nox-mem cross-agent (single SELECT vs LangChain multi-call federation pattern)
- Storage: 1 DB de 1GB serve 6 agents vs 7 DBs separados

**Risco:** "shared state" é controversial em multi-agent literature — argumento de isolation pra security é forte. Posicionar como "design choice for trusted multi-agent within single user", NÃO como "multi-tenant SaaS".

---

## ⚠️ 5 GAPS técnicos a cobrir antes de submit

### Gap #1 — Single corpus (CRITICAL)
**Status:** Todos resultados em corpus único Toto's operational memory.
**Fix:** Adicionar 2 corpora extra:
- **BEIR subset** (TREC-COVID, NFCorpus, FiQA-2018) — public benchmark padrão IR
- **Stack Exchange dump** (subset de 10K posts) — público, técnico, queryable
**Effort:** ~6h impl adapter + ~2h runs + 2h analysis = **10h total**

### Gap #2 — Internal-curator bias (HIGH)
**Status:** §1.4 documenta, mas é honest disclosure, não fix.
**Fix:** External curator real — pedir 10 queries pra someone outside the project. Se inviable, usar BEIR queries (já curated by ≠ pessoas).
**Effort:** ~2h coordination + 1h curate.

### Gap #3 — Sem comparison vs strong baselines (CRITICAL)
**Status:** Comparou só com FTS-only (straw man).
**Fix:** Adicionar 3 baselines fortes:
- **BM25 puro** (Pyserini implementation) — lexical baseline industry standard
- **BGE-M3 dense retrieval** — open-source SOTA encoder
- **E5-mistral-7b-instruct** — top of MTEB leaderboard
**Effort:** ~4h impl Python adapter (each) × 3 = **12h** (parallel-ize via subagent)

### Gap #4 — Sem ablation studies (HIGH)
**Status:** Sistema treated as monolithic.
**Fix:** 4 ablations:
- (a) FTS-only vs FTS+RRF (sem semantic)
- (b) FTS+semantic sem RRF (concat scores)
- (c) Hybrid sem salience boost
- (d) Hybrid sem section_boost
**Effort:** ~3h adapter + 2h runs + 2h analysis = **7h**

### Gap #5 — Voyage cut deixa "provider intercambiável" claim untested (MEDIUM)
**Status:** §1.3 disse "plausible but unmeasured".
**Fix:** OPÇÃO A — buy Voyage trial $20 + run = 1h. OPÇÃO B — usar BGE-M3 (já no Gap #3) como proxy alt-provider.
**Recomendação:** OPÇÃO B (zero cost extra, kill 2 birds).

---

## 🤝 Como melhorar semelhanças com prior work (cite corretamente)

| Prior work | Como nox-mem se relaciona | Citation positioning |
|---|---|---|
| **GraphRAG** (Microsoft 2024) | Both use LLM-extracted KG over chunks. Diferencia: nox-mem foca em operational/personal corpus + edge typing closed enum, GraphRAG foca em community detection + multi-level summary | "Following GraphRAG's KG construction approach [Edge et al. 2024], we extend with closed-enum edge typing for operational use cases" |
| **MemGPT/Letta** (Berkeley 2023) | Both target persistent memory pra LLM agents. Diferencia: MemGPT = OS-inspired tiers + agent-paged, nox-mem = SQL-canonical multi-agent shared | "Unlike MemGPT's [Packer et al. 2023] OS-inspired per-agent paging, we adopt a shared-canonical model for trusted multi-agent contexts" |
| **Mem0** (paper 2025) | Both auto-extract memories from conversations. Diferencia: mem0 self-improving via LLM editing, nox-mem manual entity files + shadow-validated changes | "While Mem0 [Chhikara et al. 2025] explores self-improving memory editing, we prioritize human-in-the-loop validation through enforced shadow periods" |
| **A-MEM** (2024) | Both use Zettelkasten-inspired auto-tagging. Diferencia: A-MEM auto-links, nox-mem manual entity files + KG extraction | Cite as influence on §3 (Knowledge Graph Construction) |
| **HiRAG** (2024) | Both layer FTS + dense retrieval. Diferencia: HiRAG hierarchical reasoning chains, nox-mem flat 3-layer + RRF | "Our 3-layer hybrid retrieval (FTS5 + Gemini + RRF) differs from HiRAG's [Liu et al. 2024] hierarchical reasoning by maintaining flat fusion for latency-critical operational use" |
| **Cognee** (2024) | Both KG + hybrid. Diferencia: Cognee é open-source framework genérico, nox-mem é vertical solution + eval-harness gated | Cite as alternative implementation; emphasize eval-harness as differentiator |

**Section dedicada §2 Related Work** vai citar 8-10 papers, posicionar nox-mem como "operational synthesis of multiple research threads, with novel contributions in (a) pain-weighted salience, (b) enforced shadow discipline, (c) shared-canonical multi-agent design".

---

## 📢 Voice / tom pra cada channel

| Channel | Tom | Length | Audience | Goal |
|---|---|---|---|---|
| **arXiv paper** | Acadêmico formal, hedged claims, exhaustive related work | 12 pages | Researchers | Citation handle + permanent registry |
| **Blog post** | Story-driven, "I built this in production for X reason", code snippets, screenshots | 2500 words | Devs/practitioners | Distribution + credibilidade técnica produto |
| **HN submission** | Honest title focusing on counterintuitive finding ("FTS5 is 97.7% useless for natural language" or similar) | Title 80 chars + first comment 500 chars | HN devs | Front page → traffic spike |
| **Twitter/LinkedIn** | Punchy 1-liner + 1 chart screenshot | <280 chars | Mixed dev/business | Reach + product launch tease |
