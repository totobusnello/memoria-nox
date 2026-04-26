# ClawMem Analysis — Investigation Note (não plan)

**Data:** 2026-04-26
**Status:** INVESTIGATION — pending POC validation
**Tipo:** análise comparativa de repo externo, **não** spec executável
**License upstream:** **MIT** (verified via `gh api repos/yoloshii/ClawMem/license` — clean-room reimplementation OK; copy direto de código exige preservar copyright)
**Repo analisado:** github.com/yoloshii/ClawMem (TypeScript + Bun + sqlite-vec, mesmo nicho OpenClaw)

---

## Por que esta nota existe

Analisamos `ClawMem` (concorrente direto pra OpenClaw) buscando ideias aproveitáveis pro nox-mem. Análise inicial sugeriu criar "Fase Q" com 5 features novas + bumpar roadmap v1.6→v1.7 e visão v14→v15.

**Após validação paralela** (researcher fact-check + architect review + critic review), o plano original foi **rejeitado por unanimidade**. Esta nota documenta os achados, decisões e o caminho escolhido. **Não bumpa canônicos.** Substitui spec detalhado por candidate-list pending POC.

---

## TL;DR

- **3 das 5 ideias têm overlap forte com fases já planejadas** que estão dormentes — adicionar como "fase nova" criaria roadmap paralelo redundante. Solução: re-mapear pra IDs existentes.
- **2 ideias são genuinamente novas e quick-wins** (S effort, sem overlap) — promover a candidates pós-gate (A6, A7).
- **1 ideia (cross-encoder reranker)** muda ranking permanente sem shadow + viola SLA L2 + ROI claim sem baseline → **DEFER** até W2.1 publicar nDCG.
- **Capacity check estoura**: W1+W2+W3 já = 46-58h pra ~50h disponíveis até Set/2026; adicionar 5 items novos = +18-30h sem cortar outros é fantasia.
- **Validação de alegações**: 5/7 confirmadas (3 totais, 2 parciais), 2 erros materiais corrigidos abaixo.

---

## 1. Validação de alegações (researcher)

| # | Alegação | Status | Correção/observação |
|---|---|---|---|
| 1 | A-MEM auto-keywords/links no ingest | **PARCIAL** | Confirmado nominalmente; "LLM lightweight" é impreciso — usa stack GGUF local (node-llama-cpp), não modelo cloud especializado. Schema das tags persistidas não verificável sem clone. |
| 2 | Multi-stage consolidation (Phase 1-4) + heavy-lane quiet-window | **CONFIRMADO** | Heavy-lane (`CLAWMEM_HEAVY_LANE`) é **disabled by default** desde v0.8.0 — não default-on. `worker_leases` + `maintenance_runs` confirmados como tabelas. |
| 3 | Query expansion + cross-encoder reranking | **PARCIAL** | **Erro material corrigido:** Qwen3-Reranker-0.6B e zembed-1/zerank-2 **não são alternativas** — são componentes complementares (zembed-1 = embedding distillado de zerank-2, Qwen3-Reranker = reranking pós-RRF). Top-k pro reranker não verificável. |
| 4 | Session focus topic boost (1.4×) | **CONFIRMADO** | **Erro material corrigido:** existe `1.4× match` **+ `0.75× demote`** (omitido na análise inicial). Path do cache e fail-open não verificáveis sem clone. |
| 5 | Entity-facts SPO injection (`<vault-facts>`) | **CONFIRMADO** | Token budget é bimodal (200 balanced / 250 deep), não single value. "3-path extraction" é terminologia inventada — texto real fala em SPO triples. |
| 6 | Intent classification (WHY/WHEN/ENTITY/WHAT) + multi-graph traversal | **CONFIRMADO** | Estratégia é **adaptive beam search**, não beam puro. Tool `intent_search` confirmada como MCP tool. |
| 7 | Contradiction detection + entity anchor validation | **CONFIRMADO** | `CLAWMEM_CONTRADICTION_MIN_CONFIDENCE=0.5` env var confirmada. Edge `contradicts` mencionado mas DDL não vista. |

**Não verificável sem clone do repo:**
- Versão atual (claim v0.10.1 — fontes públicas chegam até v0.9.0)
- Test count (claim ~1200 — sem evidência)
- Schema DDL exato de tags (#1) e edge contradicts (#7)
- Cache path do session focus (#4)

---

## 2. Mapeamento overlap com fases existentes (architect)

| Item ClawMem | Overlap interno | Veredito |
|---|---|---|
| **Q1 Entity-Facts SPO Injection** (read-only KG → context) | **Sem overlap** — genuinamente novo | Promover a **A6 candidate** (post-gate, ~3h) |
| **Q2 Session Focus Topic Boost** (cache file + boost/demote) | **Sem overlap** — genuinamente novo | Promover a **A7 candidate** (post-gate, ~3h + 7d shadow obrigatório) |
| **Q3 A-MEM Auto-Keywords/Links** (LLM enrich no ingest) | **Forte overlap com Fase 1.7b** "Hierarchical Tagging — scope/category/topic" + "Multi-Stage Extraction" + "Inline Entity Detection" (`docs/nox-neural-memory.md:660-694`, dormente) | **Fundir com 1.7b ressuscitada como W1.5 candidate** (Maio 2026, paralelo a Tier 2) |
| **Q4 Consolidation Merge + Contradiction Detection** | **Triplo overlap**: W1.1 enum já inclui `contradicts` + Fase 1.7b "Conflict Detection" + "Invalidation Chains" | **Fundir com W1.1 expandida como W2.2 candidate** (Jun-Jul 2026, mandatory `withOpAudit()`) |
| **Q5 Cross-Encoder Reranker** (Qwen3-Reranker-0.6B local) | Sem overlap direto, mas viola constraints | **DEFER** até W2.1 nDCG publicado; reavaliar como Wave 4 hipotética (Set+) |

---

## 3. Por que Q5 está deferred (não cortado)

Cinco razões cumulativas:
1. **ROI claim "+15% recall" sem baseline** — W2.1 (eval harness) ainda não rodou; nDCG@10 inexistente; comparação é vibe-check
2. **Latência +200ms quebra SLA L2** (`<2s` definido em `docs/nox-neural-memory.md:282`)
3. **Infra nova heavy** — llama-server + Qwen3-Reranker-0.6B comendo 2-3GB RAM na VPS Hostinger KVM 4 (compete com OpenClaw + nox-mem-api + nightly)
4. **Ranking change permanente sem shadow-mode** — viola precedente salience/section_boost + regra `feedback_shadow_mode_for_ranking_changes.md`
5. **Stack lean violation** — adiciona dep heavy (CPU/GPU inference) ao stack TS+SQLite+Gemini API atual

**Reavaliação trigger:** se W2.1 publicar nDCG@10 baseline ≥0.6 e houver caso concreto de query ambígua mal-rankeada, retomar como design-doc com shadow obrigatório 14d.

---

## 4. Capacity reality check

```
Disponível 04-26 → 09-30:  ~50h (já apertado, margem incident ~5h)
Compromisso atual:          W1 (27-30h) + W2 (14-20h) + W3 (5-8h) = 46-58h
Sobra real:                 -8 a +4h (negativo no pior caso)

Adicionar como nova fase:   A6+A7 (~6h) + W1.5 funde 1.7b (~6-8h líquidos) + W2.2 funde W1.1 (~+3-4h)
                            ≈ +15-18h líquidos vs +18-30h fantasia
```

**Conclusão:** mesmo após fusões com fases dormentes, capacity continua negativa. Decisão de cortar/adiar deve ser explícita:
- **Candidato a defer**: W1.4 (`api_impact`, 4h, nice-to-have) — já flaggado pelos agents originais
- **Candidato a corte**: nenhum dos itens core (W1.1/1.2/1.3, W2.1, W3.1)
- **Candidato a recompactar**: W3.1 (paper v2) pode ficar 3-4h se sem dados eval

---

## 5. NÃO FAZEMOS — adicionar a v1.5

4 padrões observados no ClawMem que rejeitamos explicitamente:

| Item | Razão |
|---|---|
| **Phase 3 deductive synthesis cross-session** (LLM gera "insights sintéticos" a partir de N observações) | Risco de LLM confabular insights que poluem KG; sem citation chain rastreável; preferimos crystallize manual gated |
| **Phase 4 recall stats como worker dedicado** | Já temos `search_telemetry` + `/api/health.searchTelemetry`; worker separado adiciona overhead op sem ganho |
| **Heavy-lane quiet-window worker** (`worker_leases` DB + `context_usage` query-rate gate + hour windows) | Overhead operacional alto; nosso cron 23:00 unificado + canary `*/15min` cobre o caso com 10% da complexidade |
| **Silos schema separados** (docs + observations + KG em 3 tabelas independentes) | Nosso `chunks` canônico com `kg_entities`/`kg_relations` derivados é mais normalizado e evita 3-way drift |

---

## 6. Decisão final

### Mantém em v1.6 inalterado
- Phase Matrix
- Wave Roadmap (W1/W2/W3)
- Bloco I/II/III/IV/V
- Cortes existentes

### Adiciona em v1.6 (Section 9 nova, ~15 linhas)
- Lista candidate items (A6, A7, W1.5, W2.2, Q5-deferred) apontando para esta nota
- Status explícito: "candidate, pending POC validation, not committed scope"

### Adiciona em v1.5 (NÃO FAZEMOS table)
- 4 entries acima

### NÃO faz
- ❌ Bump v1.6 → v1.7
- ❌ Bump v14 → v15
- ❌ Cria spec detalhado tipo `borrow-plan.md`
- ❌ Atualiza CLAUDE.md (subagents leriam Q1-Q5 como decididos)
- ❌ Atualiza handoffs (não há handoff novo necessário)

---

## 7. Trigger de promoção (quando re-visitar)

Cada candidate vira committed scope se:

| Item | Trigger |
|---|---|
| **A6 (Entity-Facts SPO Injection)** | Pós-gate 04-30 + 05-01 (≥05-02). POC isolado de 3h. Métrica: subjective utility report do Toto após 7d uso. Promove a v1.7. |
| **A7 (Session Focus Topic Boost)** | Mesma janela A6. POC + 7d shadow telemetry obrigatório (regra existente). Promove se delta recall ≥3% positivo OU subjective improvement claro. |
| **W1.5 (A-MEM keywords ressuscitando 1.7b)** | Maio 2026, paralelo a Tier 2. Decisão prévia: 1.7b está MORTA ou W1.5 é versão executável dela? Documentar antes. |
| **W2.2 (consolidation merge + contradiction)** | Jun-Jul 2026, depois W2.1 publicar nDCG. Mandatory `withOpAudit()` + dry-run + canary invariants extension (regra #15). |
| **Q5 (cross-encoder reranker)** | Wave 4 hipotética (Set+). Trigger: W2.1 baseline ≥0.6 + caso concreto de query ambígua mal-rankeada + decisão arquitetural sobre llama-server local vs cloud API. |

---

## 8. Red flags reconhecidas (não acionáveis aqui, mas registradas)

1. **Fase 4 Obsidian acabou hoje** — recomenda 30d estabilização antes de Fase P; abrir frente nova grande dilui atenção operacional
2. **Análise inicial confiou em line numbers chutados** — researcher confirmou 2 erros materiais (#3 reranker, #4 demote omission); validar cada citação antes de implementar
3. **Plano original era 5 arquivos em commit único** — rejeitado pelo critic por quebrar atomicidade; commits separados é a convenção correta
4. **Sleep-on-it foi sugerido pelo critic** — ignorado neste caso porque a nota investigativa não muda canônicos, só registra estado de pensamento; risco baixo

---

## 9. Citações (raw URLs, validar antes de implementar)

- README: `https://raw.githubusercontent.com/yoloshii/ClawMem/main/README.md`
- SKILL.md: `https://raw.githubusercontent.com/yoloshii/ClawMem/main/SKILL.md`
- RELEASE_NOTES.md: `https://raw.githubusercontent.com/yoloshii/ClawMem/main/RELEASE_NOTES.md`
- LICENSE: MIT (`https://raw.githubusercontent.com/yoloshii/ClawMem/main/LICENSE`)

**Antes de implementar qualquer candidate**, clonar repo e ler módulo correspondente — não confiar em descrições do README.

---

## 10. Predecessores e contexto

- Roadmap canônico atual: `plans/2026-04-25-integration-roadmap-v1.6.md` (v1.6 — não bumpado por esta nota)
- Cross-cutting + NÃO FAZEMOS: `plans/2026-04-19-unified-evolution-roadmap.md` (v1.5 — patch aditivo aqui adiciona 4 entries em NÃO FAZEMOS)
- Visão estratégica: `docs/nox-neural-memory.md` v14 — não bumpada
- Análise comparativa fonte: descartado (era spec prematuro escrito antes de validation)
