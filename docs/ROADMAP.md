# nox-mem ROADMAP — single source of truth

> **Canônico desde 2026-04-27.** Sistema unificado de IDs (F/E/R/P/G/D) substitui os 6+ namespaces antigos (A/B/W/Q/Fase/Phase). Cross-ref em §8.
> **Última atualização:** 2026-04-27 manhã, pós-review por architect + critic + architect-reviewer (correções aplicadas).
> Para "por quê" de qualquer decisão → `docs/DECISIONS.md`. Para estado atual → `docs/HANDOFF.md`.

---

## 1. Estado atual

```
Sistema:        nox-mem v3.7+, schema v10, ops_audit append-only
Chunks:         39901 (pós-Sprint A1 GitHub+Claude ingest, target 100% embedded)
DB size:        ~440MB (era 318MB pré-A1, +38%)
Agentes:        7 (1 main Maestro + 6 personas: nox/atlas/boris/cipher/forge/lex)
OpenClaw:       v2026.4.23 (.24 quebrado, .25-stable aguardada)
Improvements:   13/13 OK (audit baseline)
Capacity:       ~6h/semana realista até Set/2026 (CEO em 5 frentes)
Margem incident: 20h reservadas (histórico: 4 incidents em 2 dias 04-25/26)
```

### Sprint A1 delivered (2026-04-27)

Ingestão massiva GitHub repos + Claude workspace, **pré-R01a (baseline-first em corpus completo)**:
- **+1.046 graph_nodes** via `graphify-ingest` em 9 repos com graphify-out já gerados (Future-Farm, GalapagosApp, Granix-App, agent-hub-dashboard, daily-tech-digest, memoria-nox, nox-supermem, projeto-ai-galapagos, sao-thiago-fii)
- **+304 markdown chunks** via clone+ingest de 7 repos pequenos (biolab-ai, curso-ai, posts-linkedin, grancoffee, superfrio, fake-news-check, claude-project-template)
- **+17.714 chunks** via Claude workspace scope curado (1.356 md de docs+agents+skills+commands+Projetos)
- **Scope cut:** _retired/, prompts/, powerpoint-templates (Tier 3 OCR), nox-workspace (257MB scope decision posterior)
- **Total:** +19.070 chunks (DB +38%)
- Implicação: F09 off-site backup vira **mais crítico** (mais dados = exposição maior em disk failure)
- Implicação: G01 baseline 7d pode shift 2-3 dias se distribuição salience mudar significativamente

## 2. Sistema unificado de IDs

| Prefix | Categoria | Exemplos |
|---|---|---|
| **F** | Foundation — infra, hardening, ops, security | F01 Query logging, F02 Audit log, F11 Off-site backup |
| **E** | Evolution — features, capabilities, search/ranking | E01 Obsidian, E03 SPO Injection, E05 Edge typing |
| **R** | Research — eval, paper, benchmarks | R01 Eval harness, R02 Paper v2 |
| **P** | Product — NOX-Supermem productization path | P01 Supermem Wave 1 |
| **G** | Gates — decision points (data-fixed) | G01 Salience, G02 Section_boost |
| **D** | Deferred / Cut — com trigger pra revisitar | D01 Q5 reranker, D03 Group routing |

## 3. Status enum

- ✅ `DONE` — entregue, validado em produção
- ⏳ `GATED` — esperando trigger explícito
- 📋 `QUEUED` — pronto pra executar quando bloco abrir
- 🔄 `IN-PROGRESS` — execução ativa
- 🤔 `CANDIDATE` — em validation, precisa POC antes de committed scope
- 🛑 `DEFERRED` — adiado com trigger explícito
- ❌ `CUT` — não fazemos (ver DECISIONS.md)

---

## 4. Tabela mestre cronológica

Velocity buckets aplicados (corrigidos pós-review crítico):
- **Hardening de código existente:** ~0.4× estimates conservadores (validated Bloco I)
- **Greenfield feature** (schema novo, código zero-existente): ~0.7×
- **Cognitive floor** (curadoria humana, paper writing): NÃO comprime — usar estimates honestos

### Foundation (Maio-Set sprints intercalados)

| ID | Vision § | Item | Status | h | Trigger |
|---|---|---|---|---|---|
| **F01** | §0,7 | Query logging + golden-tag (search_telemetry +4 cols) | ✅ DONE | 1 | — |
| **F02** | §15 (audit) | Audit log + `withOpAudit` snapshot pré-op atômico | ✅ DONE | 6 | incident 04-25 |
| **F03** | §1,2 | Ingest-router unified (`routeIngest`) | ✅ DONE | 1 | incident 04-25 |
| **F04** | (tests) | Unit tests `parseRetentionOverride` (20 cases) | ✅ DONE | 0.4 | — |
| **F05** | §10 (canary) | Canary invariants extension (5 invariants */15min Discord) | ✅ DONE | 0.5 | — |
| **F06** | §15 | Dry-run mode reindex/consolidate | ✅ DONE | 1 | — |
| **F07** | (ops) | OpenClaw upgrade defense system (ckpt + improvements + watcher + orchestrator) | ✅ DONE | 4 | OpenClaw .24 break |
| **F08** | (backlog) | B3 backlog sprint 7/8 (issue + CONVENTIONS + alert + playbooks) | ✅ DONE | 1.5 | — |
| **F09** ⭐ | §3,resilience | **Off-site backup rclone → B2/R2** (retention 30d remoto + alerta upload fail) | 📋 QUEUED P0 | 1 | **antes G01 04-30** |
| **F10** | §10 | Observability dashboard (Grafana + SQLite plugin OR `/api/health` time-series no agent-hub-dashboard) | 📋 QUEUED | 2-3 | Maio |
| **F11** | (incident) | RUNBOOKS.md formalizado (cobre RB-01 a RB-10 — incident playbooks) | ✅ DONE | 2 | — |
| **F12** | (resilience) | Embedding model migration playbook (Gemini SPOF mitigation, shadow-index trimestral com Voyage/OpenAI) | 📋 QUEUED | 1 | Maio |
| **F13** | (cost) | Cost projection pay-per-token alternative (Max OAuth backup plan) | 📋 QUEUED | 1 | Maio |
| **F14** | §10 | DR drill trimestral (restore snapshot `/tmp/nox-mem-drill.db` + smoke check) | 📋 QUEUED | 1 × 3 | Jul/Out/Jan |
| **F15** | §11 | SEH Self-Evolving Hooks | 📋 QUEUED | 1 | Set+ |
| **F16** | (bus factor) | Telegram bot rollback automático se health-check falha 30min | 📋 BACKLOG | 4 | gap urgente; fora orçamento atual |

### Gates (data-fixed)

| ID | Data | Item | Status | h | Comando |
|---|---|---|---|---|---|
| **G01** | **2026-04-30** | Salience activation (`activate-salience.sh --apply` se baseline 7d OK) | ⏳ GATED | 0.1 | `bash /root/.openclaw/scripts/activate-salience.sh check` |
| **G02** | **2026-05-01** | Section_boost decision | ⏳ GATED | 0.3 | `bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7` |
| **G03** | **2026-05-02** | Archive 3 source files `.archived-20260502` (projects/decisions/lessons.md) | ⏳ GATED | 0.1 | manual `mv` |

### Evolution (Maio-Set)

A6/A7 (E03/E04) **separados em implement vs activate** após review crítico (shadow-mode 7d obrigatório per regra existente):

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **E01** | §11 (Fase 4) | Obsidian view-only (Python gen 430 LOC + cron+launchd) | ✅ DONE | 1 | F01-F08 done |
| **E02** | §11 (Fase 3) | Tier 2 PDFs ingest (4432 PDFs HD Mac) | 📋 QUEUED | 15-25 (I/O) | G03; rate-limit Gemini risk |
| **E03a** | (ClawMem Q1) | **A6 implement** Entity-Facts SPO Injection (`<vault-facts>` block via KG) | 🤔 CANDIDATE | 1.5 | ≥G03; v1 sem confidence filter (top-K simples) |
| **E03b** | — | **A6 activate** após 7d subjective utility report | 🤔 CANDIDATE | 0.2 | ≥E03a + 7d wall |
| **E04a** | (ClawMem Q2) | **A7 implement** Session Focus Topic Boost (`focus set <topic>` 1.4×/0.75×) | 🤔 CANDIDATE | 1.5 | ≥G03 |
| **E04b** | — | **A7 activate** após 7d shadow + delta recall ≥3% | 🤔 CANDIDATE | 0.3 | ≥E04a + 7d shadow |
| **E05** | §11 Wave 1 | Edge typing FULL — `relation_reason` enum 7 + `confidence REAL` (kg_relations v11) | 📋 QUEUED | **8-10** (greenfield 0.7×) | shadow 7d antes ranking |
| **E06** | §11 | `nox-mem detect-changes --since=<commit>` (read-only git diff→entities) | 📋 QUEUED | 2-3 | — |
| **E07** | §11 | `nox-mem impact <entity>` 1-hop blast radius via kg_relations | 📋 QUEUED | 2.5 | E05 active (não shadow) |
| **E08** | §11 | `nox-mem api_impact <signature-change>` multi-arquivo grep + import graph | 📋 QUEUED | 1.5 | nice-to-have |
| **E09** | (ClawMem Q3 + §1.7b dormente) | A-MEM auto-keywords/links no ingest (funde §1.7b Hierarchical Tagging) | 🤔 CANDIDATE | 5-6 | E05 active obrigatório (enum CLOSED); shadow obrigatório |
| **E10** | (ClawMem Q4 + W2.2) | Consolidation merge + contradiction detection (entity-anchor val) | 🤔 CANDIDATE | 3-4 | R01 nDCG≥0.6 + dry-run zero FP |
| **E11** | §11 | Reflect cache (semantic key) | 📋 QUEUED | 1.5 | 7d telemetria reflect (Fase 1.7a ✅ DONE 04-19) |
| **E12** | §11 (Tier 3) | Tier 3 OCR + Fathom + Path C (opcional, não bloqueia Fase 4) | 📋 QUEUED | dias | — |

### Research (eval + paper)

⚠️ **Mudança crítica pós-review:** R01 dividido em skeleton (Maio) + curation (Jun-Jul) — baseline-first é precondição arquitetural pra E05/E10 mudarem ranking.

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **R01a** | §11 Wave 2 | **Eval harness skeleton** (schema v12 + tabela `eval_queries` + nDCG@10/MRR + CLI + JSONL out + 5 golden seed queries) | 📋 QUEUED | 4-6 (greenfield 0.7×) | F01 corpus ready |
| **R01b** | — | **Curadoria 50 golden queries** (cognitive floor, não comprime) | 📋 QUEUED | **8-10** (humano) | spread Jun-Jul |
| **R01c** | — | Baseline FTS-only vs hybrid run + publish nDCG@10 em `/api/health.evalMetrics` | 📋 QUEUED | 1-2 | R01a + R01b |
| **R02** | §11 Wave 3 | Paper v2 update — Affective Ranking + Multi-Agent Federation + Bridge Mode | 📋 QUEUED | **5-6** (writing tem floor cognitivo) | R01c published |

### Product (NOX-Supermem)

| ID | Vision § | Item | Status | h | Dependências |
|---|---|---|---|---|---|
| **P01** | §11 (Fase 4b/5/P) | NOX-Supermem productização — Fase 4b → 5 → P | 📋 QUEUED | semanas | E01 estável 30d (= 2026-05-26 elegível) |

**Short-circuit identificado pelo architect-reviewer:** P01 depende **apenas** de E01 estável 30d. Wave 1-3 (E05-E10, R01-R02) são **enrichments**, não bloqueadores. Toto pode iniciar **P01 design** em **05-26** sem aguardar Wave 2.

### Deferred / Cut

| ID | Item | Decisão | Trigger pra reavaliar |
|---|---|---|---|
| **D01** | Q5 Cross-encoder reranker (Qwen3 local) | 🛑 DEFERRED | R01c nDCG≥0.6 OR 2 PRs com query mal-rankeada documentadas (early trigger antecipado) |
| **D02** | W3.2 Plugin hooks (`onIngest`, `onRelation`) | 🛑 DEFERRED (não CUT) | Multi-tenancy P01 design — se >2 tenants pediram custom ingest, design hooks ANTES de implementar |
| **D03** | Group routing (`@group`, `groups.yaml`) | ❌ CUT | Açúcar de `cross-search --agents` se aparecer dor real |
| **D04** | W3.3 Group routing v2 (frontmatter tag) | ❌ CUT | — (mesma razão D03) |
| **D05** | Phase 3 deductive synthesis cross-session | ❌ CUT | LLM confabula sem citation chain |
| **D06** | Phase 4 recall stats worker dedicado | 🛑 DEFER | F10 dashboard cobre? Revisitar Jul antes de R01a |
| **D07** | Heavy-lane quiet-window worker | ❌ CUT | Cron 23:00 + canary já cobrem |
| **D08** | Silos schema separados (docs+observations+KG) | ❌ CUT | chunks canônico evita drift |
| **D09** | 30 MCP tools (gbrain pattern) | ❌ CUT | Cap em 16 |
| **D10** | Memgraph / Neo4j | ❌ CUT | >500K entities |
| **D11** | Postgres / PGLite | ❌ CUT | >500K entities |
| **D12** | Text2Cypher / query DSL | ❌ CUT | — (estrutural) |
| **D13** | Free-form `relation_reason` vocabulary | ❌ CUT | — (estrutural) |
| **D14** | Atomic hybrid query (CTE única) | ❌ CUT | p95 >500ms persistente |
| **D15** | Dashboard React como roadmap item | ❌ CUT | Já existe (`agent-hub-dashboard`) |
| **D16** | Expertise profiling automático | ❌ CUT | >20 agentes |
| **D17** | Productizar nox-supermem em paralelo | 🛑 DEFER | E01 estável 30d |
| **D18** | Bump v1.6→v1.7 / v14→v15 (ClawMem-driven) | ❌ CUT | POC + 7d shadow validados |
| **D19** | Tier 3 OCR no critical path Fase 4 | 🛑 OPCIONAL | Volume PDF scaneado >50 docs |
| **D20** | git-as-source-of-truth | ❌ CUT | Nunca (incompatível) |
| **D21** | W2.3 Tool/Skill map | 🛑 DEFER ≥6mo | Caso de uso concreto aparecer |

---

## 5. Capacity tracker (recalibrado pós-review)

```
Disponível 04-27 → 09-30:        ~22 semanas × 6h/sem realista = 132h
Margem incident:                 -20h reservadas (histórico: 4 incidents 2 dias)
Capacity líquida:                ~112h

Compromissado núcleo (estimates honestos pós-review):
  F09 off-site backup:           1h     ← P0 antes G01
  F10 observability dashboard:   2-3h
  F12 Gemini SPOF playbook:      1h
  F13 cost projection alt:       1h
  F14 DR drill (1 inicial):      1h
  E02 Tier 2 PDFs (I/O):         15-25h ← paralelo possível
  E05 Edge typing FULL:          8-10h  ← greenfield 0.7×
  E06 detect-changes:            2-3h
  E07 impact:                    2.5h
  E08 api_impact (defer 1º):     1.5h
  R01a eval skeleton (Maio!):    4-6h   ← MOVED earlier
  R01b curadoria 50 queries:     8-10h  ← cognitive floor
  R01c baseline + publish:       1-2h
  R02 paper v2:                  5-6h   ← writing tem floor
                                 ───────
Subtotal núcleo:                 53-72h

Candidates Section 9:
  E03a/b A6 implement+activate:  1.7h
  E04a/b A7 implement+activate:  1.8h + 7d wall
  E09 A-MEM keywords:            5-6h
  E10 consolidation merge:       3-4h
                                 ───────
Subtotal candidates:             11.5-13.5h

Bloco V (Set+):
  E11 reflect cache:             1.5h
  F15 SEH:                       1h
  E12/P01 dias-semanas:          out-of-budget Maio-Ago
                                 ───────

TOTAL núcleo + candidates + small Set+:  67-89h vs 112h capacity líquida

Sobra realista:                  +23 a +45h (margem confortável)
```

**Diferença vs estimate ingênuo anterior:**
- Antes: 36-41h vs 45h (4-9h sobra)
- **Agora honesto:** 67-89h vs 112h (23-45h sobra)
- **Capacity ampliada** (10h/sem fantasia → 6h/sem realista × mais semanas) **bate com cognitive floor honesto**

**Decisões de ajuste obrigatórias:**
- ✅ **Defer E08** (api_impact, 1.5h) — primeiro corte se apertar
- ✅ **Recompactar R02** pra 4-5h se sem dados eval completos
- ✅ **Promover E03/E04 (A6/A7) candidates** post-G03 — 3.5h total, additive, baixo risco
- 🤔 **E09/E10 candidates entram se sobrar tempo pós-Wave 1 core** (60-70% likely com capacity nova)
- ✅ **F09 off-site backup ANTES de G01 04-30** — risco catastrófico vs custo trivial

## 6. Wave gating métrico (não calendário)

**Wave 1 → Wave 2 (E05 → R01/E10):**
- E05 atinge ≥80% das ~544 rels classificadas com confidence ≥0.7 em shadow-mode por ≥7d
- E06 + E07 + E08 rodaram ≥3x em uso real sem falso-positivo
- 50 golden queries (R01b) curadas e validadas

**Wave 2 → Wave 3 (R01c → R02 + D01 trigger):**
- nDCG@10 baseline publicado em `/api/health.evalMetrics`
- 1 incident-free month pós-Wave 1
- Affective Ranking validado com salience ativa (G01 OK)

**Kill switches:**
- E07/E08 não usados ≥3x/semana após 30d → archive feature
- R01b não conseguir 50 queries em 2 semanas → reduzir pra 20 + accept lower power
- Health: salience delta ≥5%, vectorCoverage <99%, ou confidence distribution bimodal extrema → PAUSE wave + investigar

---

## 7. Critical path & ordering (revisado)

```
HOJE 04-27 ──┐
             │ F09 off-site backup (1h) ◀── P0 NOVO antes G01
             ▼
[G01 salience activation 04-30] ──→ [G02 section_boost 05-01] ──→ [G03 archive 05-02]   0.5h serial / 5d wall
             │
             ▼
[E02 Tier 2 PDFs 15-25h I/O paralelo] ════════════════════════════════════════════│
             │                                                                    │
             ├──→ [E03a A6 implement 05-02] ──→ shadow 7d ──→ [E03b activate 05-09]
             ├──→ [E04a A7 implement 05-02] ──→ shadow 7d ──→ [E04b activate 05-09]
             │
             ▼
[R01a eval skeleton 4-6h MAIO] ◀── MOVED earlier pra baseline-first      │
             │                                                            │
             ▼                                                            │
[E05 edge typing 8-10h] ──→ shadow 7d ──→ E05 active                     │
             │                                                            │
             ▼                                                            │
[E06 detect-changes 2-3h] + [E07 impact 2.5h] + [E08 api_impact 1.5h]    │
             │                                                            │
             ▼                                                            │
[R01b curadoria 8-10h spread Jun-Jul] ──→ [R01c baseline publish]        │
             │                                                            │
             ▼                                                            │
[E10 consolidation merge 3-4h candidate] (gated nDCG≥0.6)                │
             │                                                            │
             ▼                                                            │
[R02 paper v2 5-6h Ago]                                                   │
             │                                                            │
             ▼                                                            │
[E01 Fase 4 estabiliza 30d wall-clock] ◀── DONE 04-26 conta from there  │
             │                                                            │
             ▼                                                            │
[P01 NOX-Supermem productização] semanas (≥05-26 elegível)                │
                                                                          │
                                                                          ▼
                                                              SHORT-CIRCUIT POSSÍVEL:
                                                              P01 design pode iniciar 05-26
                                                              SEM aguardar Wave 2/3
                                                              (E05-R02 = enrichments, não bloqueadores)
```

---

## 8. Cross-ref ID systems (decoder de namespaces antigos)

Nomenclatura antiga (v1.5/v1.6/ClawMem/Wave/Bloco) → nova:

| Antigo | Novo | Item |
|---|---|---|
| A0 | F01 | Query logging |
| A1 | F02 | Audit log + snapshot |
| A2 | F03 | Ingest-router |
| A3 | F04 | Tests parseRetentionOverride |
| A4 | F05 | Canary invariants |
| A5 | F06 | Dry-run mode |
| upgrade-defense | F07 | OpenClaw upgrade defense |
| B3 | F08 | Backlog sprint |
| (novo) | F09 | Off-site backup ⭐ |
| (novo) | F10 | Observability dashboard ⭐ |
| (novo) | F11 | RUNBOOKS.md |
| (novo) | F12 | Gemini SPOF playbook ⭐ |
| (novo) | F13 | Cost projection alt ⭐ |
| (novo) | F14 | DR drill ⭐ |
| C2 | F15 | SEH Self-Evolving Hooks |
| (novo) | F16 | Telegram rollback bot ⭐ |
| gate.salience | G01 | — |
| gate.section_boost | G02 | — |
| gate.archive_3files | G03 | — |
| B1 | E01 | Obsidian view-only |
| B2 | E02 | Tier 2 PDFs |
| A6 (Q1) | E03a + E03b | SPO Injection (split implement/activate) |
| A7 (Q2) | E04a + E04b | Focus Boost (split implement/activate) |
| W1.1 | E05 | Edge typing FULL |
| W1.2 | E06 | detect-changes |
| W1.3 | E07 | impact |
| W1.4 | E08 | api_impact |
| W1.5 (Q3, §1.7b) | E09 | A-MEM keywords |
| W2.2 (Q4) | E10 | Consolidation merge |
| C1 | E11 | Reflect cache |
| C3 | E12 | Tier 3 OCR |
| W2.1 | R01a + R01b + R01c | Eval harness (split skeleton/curation/baseline) |
| W3.1 | R02 | Paper v2 |
| C4 | P01 | NOX-Supermem productização |
| Q5 | D01 | Cross-encoder reranker |
| W3.2 | D02 | Plugin hooks |
| (group routing) | D03/D04 | Group routing v1/v2 |
| (Phase 3 ClawMem) | D05 | Deductive synthesis |
| (Phase 4 ClawMem) | D06 | Recall stats worker |
| (heavy-lane ClawMem) | D07 | Quiet-window worker |
| (silos ClawMem) | D08 | Schema separados |
| (gbrain) | D09 | 30 MCP tools |
| — | D10 | Memgraph/Neo4j |
| — | D11 | Postgres/PGLite |
| — | D12 | Text2Cypher |
| — | D13 | Free-form relation_reason |
| — | D14 | Atomic hybrid query |
| — | D15 | Dashboard React (existe) |
| — | D16 | Expertise profiling |
| — | D17 | Productizar paralelo |
| — | D18 | Bump v1.6→v1.7 |
| — | D19 | Tier 3 OCR critical-path |
| — | D20 | git-as-source-of-truth |
| W2.3 | D21 | Tool/Skill map |

⭐ = item **NOVO** identificado pelos agents review (não estava no roadmap original).

---

## 9. Cruzamento com VISION.md (nox-neural-memory v14)

A coluna `Vision §` em §4 referencia seções da visão estratégica. Mapping resumido:

| Conceito Vision | Implementado por |
|---|---|
| §0 Query Strategy | F01 (telemetry corpus) |
| §1 graphify vs nox-mem KG | F03 (router) |
| §3 Cross-Agent Intelligence | (existing `cross-search`) |
| §4 Obsidian painel visual | E01 ✅ |
| §5 KG extraction Gemini 2.5 Flash | (existing — kg-build) |
| §6 graph-memory plugin | (existing) |
| §7 Estratégia camadas hot/warm/cold | F01, F05 |
| §8 Affective Ranking pain-weighted | (salience formula ativa post-G01) |
| §9 Compiled Truth + Timeline 3-section | F03 (entity ingest) ✅ |
| §10 Bridge Mode | (R02 paper v2 documenta) |
| §11 Memory Graph Maturity Waves | E05, E06, E07, E08, E09, E10, R01a-c, R02 |
| Fase 1.7b dormente | E09 (resurrected as candidate) |
| Fase 1.7a Reflective Loops | ✅ DONE 04-19 — destrava E11 |
| Fase 4 Obsidian | E01 ✅ |
| Fase 5 openclaw-memory-sync | (parte de P01) |
| Fase P NOX-Supermem | P01 |

Próximo update VISION.md: pós-G01/G02/G03 (capturar resultado dos gates).

---

## 10. Próxima ação concreta (referência rápida)

Hoje é **2026-04-27** (segunda).

### Antes de G01 (próximos 3 dias)
- **F09 off-site backup** (1h) — **P0** antes do gate; risco catastrófico vs custo trivial
- Opcional: design specs E03a + E04a (A6/A7 implementation, ~1h cada)
- Opcional: investigar 1.7b dormente vs E09 (1h)

### G01-G03 window (04-30 → 05-02)
- 04-30 manhã: `bash /root/.openclaw/scripts/activate-salience.sh check`
- 05-01 manhã: `bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7`
- 05-02: archive 3 source files + iniciar E03a + E04a + E02

### Post-gate Maio (parallel-friendly)
- E02 Tier 2 PDFs (I/O bound — fire-and-forget background)
- R01a eval skeleton (4-6h, antecipado per architect-reviewer)
- E05 edge typing (após R01a skeleton pra baseline-first)
- E03b/E04b activate após shadow 7d

### Jun-Jul
- E06/E07 (post-E05 active)
- R01b curadoria 50 queries (cognitive floor, spread)
- R01c baseline publish
- E10 candidate (gated nDCG≥0.6)

### Ago
- R02 paper v2

### Set+
- E11 reflect cache
- F15 SEH
- **P01 NOX-Supermem productização** (elegível desde 05-26 + Wave 2 delivered)

---

## 11. Mudanças vs versão anterior do ROADMAP (2026-04-27 manhã)

Pós-review por 3 agents (architect, critic, architect-reviewer):

1. ✅ **Sistema unificado de IDs** F/E/R/P/G/D substitui 6+ namespaces
2. ✅ **F09 off-site backup adicionado** como P0 (antes G01) — gap crítico
3. ✅ **F10/F12/F13/F14/F16 adicionados** (observability + DR + cost + bus factor)
4. ✅ **R01 dividido em R01a/R01b/R01c** — skeleton em Maio (era Jun-Jul) pra baseline-first
5. ✅ **E03/E04 dividido em implement/activate** — captura latência shadow 7d wall-clock
6. ✅ **Velocity bucketada** (greenfield 0.7×, hardening 0.4×, cognitive floor não comprime)
7. ✅ **Capacity recalibrada** (6h/sem × 22 sem = 132h, vs 10h/sem × 5 meses = 50h fantasia)
8. ✅ **Margem incident ampliada** (5h → 20h baseado em histórico real)
9. ✅ **D02 promovido de CUT → DEFERRED** (Plugin hooks, gatilho multi-tenancy)
10. ✅ **D01 trigger antecipado** (Q5 reranker; 2 PRs mal-rankeadas OR R01c)
11. ✅ **Cross-ref VISION.md adicionado** (coluna `Vision §`)
12. ✅ **Critical path & short-circuit explicitados** (P01 elegível 05-26 sem aguardar Wave 2)
13. ✅ **E05 → E07 dependência explícita** (edge typing active antes de impact CLI)
14. ✅ **E09 → E05 active dependência explícita** (auto-keywords não pode poluir enum closed)

Este arquivo é a **fonte mestre**. Cross-refs:
- **`docs/HANDOFF.md`** — estado vivo + próxima ação imediata
- **`docs/DECISIONS.md`** — porquê + NÃO FAZEMOS + lições
- **`docs/VISION.md`** — long-term thesis (nox-neural-memory v14)
- **`docs/ARCHITECTURE.md`** — system design overview
- **`docs/RUNBOOKS.md`** — incident playbooks
- **`CLAUDE.md`** — regras críticas operacionais 1-15
- **`plans/_archive/`** — v1.6, v1.5, ClawMem analysis (referência histórica)
