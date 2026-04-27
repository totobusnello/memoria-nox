# Section 7 Wave Roadmap — Validation Round

**Data:** 2026-04-25
**Contexto:** validação técnica + crítica das 9 ideias inspiradas em precedentes externos de code-intelligence antes de incorporar como Section 7 do v1.6
**Agents:** architect (read-only validation contra codebase) + critic (feature creep + capacity reality)
**Resultado:** Section 7 promovida ao v1.6 com 4 cortes + 1 adição + esforços corrigidos

---

## Convergências (architect + critic concordaram)

### CORTAR (4 itens, ~15h fantasia eliminados)

| Item | Razão |
|---|---|
| G3.3 Group routing v2 (frontmatter) | Viola Decisão #4 SOUL.md + contradiz Seção 1 do próprio v1.6 |
| G2.3 Tool/Skill map | Sem consumer real, premature polish, vira Dashboard React risk |
| G2.2 Bridge mode docs | Não é wave standalone — fundir em G3.2 paper |
| G3.1 Plugin hooks | YAGNI clássico (n=1 = graphify), aproxima "30 MCP tools" proibidos |

### ADICIONAR (1 item, +4h valor real)

**G1.4 api_impact CLI** — paga débito do incident de hoje melhor que G1.3 sozinho. O argumento "G1.3 teria pego o bug" é FALSO (foi DELETE+rewrite no DB, não relação faltante). api_impact (multi-arquivo via grep + import graph) cobre essa classe.

### Esforços corrigidos (subestimados ~2x)

| Item | Original | Realista | Justificativa |
|---|---|---|---|
| G1.1 Edge typing | 6h | 12-14h | Migration v11 + amostragem 544 rels + backfill heurístico + shadow 7d |
| G1.2 Detect-changes | 4h | 5-6h | Path→chunk→entity join novo |
| G1.3 Impact analysis | 5h | 6h | OK como estava, scope-cap 1-hop |
| G2.1 Eval harness | 10h | 14-20h | Curadoria 50 queries 6h + ground-truth + nDCG/MRR + CI gate |
| G3.2 Paper v2 | 3h | 5-6h | 3 seções + diagramas |

---

## Veracity scoreboard — 6 alegações do critic da rodada anterior

Architect verificou cada alegação contra o codebase:

| # | Alegação | Veredict | Evidência |
|---|---|---|---|
| 1 | "backup-all.sh = snapshot pré-op" | **FALSO** | backup-all é cron 02:00 diário, não atômico; tier0-* são manuais pré-release |
| 2 | "semantic-canary é invariant gate" | **FALSO** | Só testa match=semantic ≥1 + orphans=0; zero check de section/pain/retention |
| 3 | "search_telemetry = eval harness" | **PARCIAL** | Schema tem query_hash sha1, latency, count; falta query_id/expected_chunk_ids/precision@k |
| 4 | "consolidated_files+graphify+watcher = incremental indexing" | **PARCIAL** | 3 sistemas isolados, sem chunks.last_seen_at unificado |
| 5 | "NOX_*_MODE = framework de feature flags" | **PARCIAL** | Convenção (3 flags), sem registry/validação/listing |
| 6 | "relation_reason vocabulary viola Text2Cypher" | **FALSO com ressalva** | Proibição é sobre query DSL + graph engine, não tipagem; enum fechado mitiga |

**Conclusão:** o critic da rodada anterior errou em 4 das 6 alegações ao colapsar fases novas em "duplicatas" superficiais. Hardening genuíno (A1 audit/snapshot, A2 ingest-router) confirmado como necessário.

---

## Wave Gating Métrico (não-calendário)

### W1 → W2
- G1.1 atinge ≥80% das ~544 rels classificadas com confidence ≥0.7 em shadow-mode por ≥7d
- G1.2/G1.3/G1.4 rodaram ≥3x em uso real sem falso-positivo
- 50 golden queries curadas e validadas

### W2 → W3
- nDCG@10 baseline publicado em `/api/health.evalMetrics`
- 1 incident-free month pós-W1
- Affective Ranking validado com salience ativa (gate 04-30)

### Kill switches
- G1.3/G1.4 não usados ≥3x/semana após 30d → archive feature
- G2.1 não conseguir 50 queries em 2 semanas → reduzir pra 20 + accept lower power
- Health: salience delta ≥5%, vectorCoverage <99%, ou confidence distribution bimodal extrema → PAUSE wave + investigar

---

## Capacity Reality (validada por critic)

- 4 meses ≈ **150h disponíveis** (10h/semana focado, otimista)
- Compromisso pré-existente: ~95h
  - Hardening 7h (A0+A1+A2)
  - Tier 2 PDFs ~25h
  - Fase 4 Obsidian 1h
  - Backlog #4-#5-#7-#8 ~1h45
  - Fase P early ~12h
  - Buffer 30h
- Sobra para Waves: **~50h em 4 meses**
- Margem incident: **~5h** (apertado!)
- Hoje (2026-04-25) foi incident de 12min recovery; um único de 4-6h queima 80% da margem

**Defer-first se margem apertar:** G1.4 api_impact (4h) é nice-to-have. G1.1/G1.2/G1.3/G2.1/G3.2 são core.

---

## Roadmap pós-Wave 3 (~Set 2026 em diante)

Conforme v1.5 mantido como referência:
- Path B-lite reflect cache
- SEH Self-Evolving Hooks
- Tier 3 OCR + Fathom + Path C
- Fase 4b → 5 → P (productização NOX-Supermem)

Detalhes em `2026-04-19-unified-evolution-roadmap.md` (referência histórica).
