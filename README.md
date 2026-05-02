# memoria-nox

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/totobusnello/memoria-nox)](https://github.com/totobusnello/memoria-nox/commits/main)
[![Tests](https://img.shields.io/badge/tests-27%20passing-brightgreen)](docs/HANDOFF.md)
[![Schema](https://img.shields.io/badge/schema-v10-blue)](CLAUDE.md)
[![Improvements](https://img.shields.io/badge/improvements-13%2F13%20OK-brightgreen)](docs/HANDOFF.md)

> Sistema de memória inteligente multi-agent com hybrid search, knowledge graph e backend claude-cli zero-cost.

---

## Por que isso existe

Agentes AI sem memória persistente repetem erros, perdem contexto entre sessões e tratam cada conversa como se fosse a primeira. Quando você escala pra 7 agentes com papéis distintos, o problema multiplica: memórias fragmentadas por agente, rankings de busca frágeis que quebram sem aviso, drift de schema em ops destrutivas.

**nox-mem** resolve isso com uma camada de memória canônica compartilhada: a tabela `chunks` é a fonte única de verdade. O knowledge graph (`kg_entities` + `kg_relations`) é derivado via extração Gemini — não um silo separado. Qualquer mudança de ranking passa por shadow-mode obrigatório de 7 dias antes de ativar. Ops destrutivas criam snapshot atômico pré-execução via `withOpAudit()`.

O resultado é um sistema que, na prática, resiste a upgrades de infra, patches de segurança, incidents reais e mudanças de equipe sem perder memória acumulada — 20.831 chunks, 99,2% embedded, 318MB de DB em produção na VPS desde v1.0.

---

## Arquitetura

```
INPUTS
─────────────────────────────────────────────────────────────────────
  graphify CLI          nox-mem-watcher           nox-mem ingest
  (knowledge graph      (inotifywait,              (CLI manual,
   extraction)          debounce 15s)              MCP tools)
        │                     │                          │
        └──────────────────── routeIngest() ─────────────┘
                               (ingest-router unified)
                                       │
                           ┌───────────▼───────────┐
STORAGE                    │  chunks (FTS5 + BM25)  │◄─── ops_audit
─────────────────────────  │  vec_chunks (3072d)    │     (append-only,
                           │  kg_entities  (~402)   │     SQL triggers,
                           │  kg_relations (~544)   │     CWE-693)
                           └───────────┬───────────┘
                                       │
                             hybrid search pipeline
SEARCH                    ┌────────────▼────────────┐
──────────────────────    │  FTS5 BM25               │
                          │    + Gemini semantic      │
                          │    + RRF (k=60)           │
                          │    + MMR (λ=0.7)          │
                          │    + temporal decay       │
                          │    + salience weight      │
                          │      (recency×pain×imp)   │
                          └────────────┬────────────┘
                                       │
OUTPUTS                  ┌─────────────┼─────────────┐
──────────────────────   │             │              │
                    16 MCP tools  HTTP API       CLI (26+ cmds)
                    (nox_mem_search  :18802       search / ingest /
                     kg_build        /api/        reindex / reflect /
                     reflect         health       crystallize /
                     cross_search    search       kg-build / cross-* ...)
                     ...)            kg/path
                                     agents)
                                       │
                               ┌───────▼───────┐
AGENTS                         │  main (Maestro) │
──────────────────             │  nox  | atlas   │  cross-agent
                               │  boris| cipher  │  search/stats/KG
                               │  forge| lex      │  ativo
                               └───────────────┘
```

---

## Quick start

```bash
# Verificar estado do sistema
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq'

# Audit de improvements (13/13 baseline)
ssh root@100.87.8.44 '/root/bin/improvements check'

# Buscar na memória
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem search "sua query" --hybrid'
```

---

## Funcionalidades principais

- **Hybrid search** — FTS5 BM25 + Gemini semantic (gemini-embedding-001, 3072d) + RRF fusion (k=60); pure-vector e lexical-only falham silenciosamente em casos opostos
- **Cross-agent search** — 7 agentes com DBs isolados, busca/stats/KG compartilhados via `nox-mem cross-*`
- **Knowledge graph** — Gemini 2.5 Flash extraction, ~402 entidades, ~544 relações, enum fechado de 7 tipos de relação
- **Salience-weighted retrieval** — fórmula multiplicativa `recency × pain × importance`; shadow-mode 7d antes de ativar (gate 2026-04-30)
- **Section boost** — entity files com seções `compiled` (2.0×) / `frontmatter` (1.5×) / `timeline` (0.8×)
- **Shadow-mode safety** — qualquer mudança de ranking requer `NOX_*_MODE=shadow` + baseline 7d em `/api/health` antes de ativar
- **Append-only audit log** — `ops_audit` com SQL triggers CWE-693: DELETE e UPDATE em rows terminais bloqueados
- **Atomic snapshot pre-op** — `withOpAudit()` wrapper cria `VACUUM INTO snapshot` em `/var/backups/nox-mem/pre-op/` antes de qualquer op destrutiva
- **Dry-run em ops destrutivas** — `nox-mem reindex --dry-run` e `consolidate --dry-run` produzem JSON preview sem mutar o DB
- **Canary invariants** — 13 invariantes verificados `*/15min` com alert Discord; schema canary semantic `*/30min`

---

## Estado atual

Para estado vivo e proxima acao: [docs/HANDOFF.md](docs/HANDOFF.md). Para roadmap completo + capacity tracker: [docs/ROADMAP.md](docs/ROADMAP.md).

## Fases do projeto

Linha do tempo com descritivo do que foi feito e do que ainda sera feito, agrupado por fases historicas (v1.0 → v3.7+) e fases futuras (Wave 1-3 + Productizacao).

### Fase 1.0-1.5 — Foundation (v1.0 → v3.3, Mar/Abr 2026) ✅ DONE

**Goal:** Sistema de memoria minimo viavel pros 6 agentes da VPS — chunks indexados, hybrid search funcional, autodefesa diaria.

**Foi feito:**
- Schema v1-v7: tabelas `chunks`, `chunks_fts` (FTS5/BM25), `vec_chunks` (sqlite-vec 3072d), `kg_entities`, `kg_relations`
- Hybrid search (FTS5 BM25 + Gemini semantic + RRF k=60) integrado e validado
- 26+ comandos CLI (`search`, `ingest`, `reindex`, `vectorize`, `kg-build`, `cross-search`, `reflect`)
- 16 MCP tools + HTTP API porta 18802 (`/api/health`, `/api/search`, `/api/kg`, `/api/cross-kg`)
- Multi-agent rollout: 6 personas (nox/atlas/boris/cipher/forge/lex) com DBs isolados
- Cron nightly 23:00 (reindex + consolidate + vectorize + kg-build + kg-prune + session-distill)
- Canary semantic */30min + health probe */5min + backup diario 02:00
- Foundation Repair Tier 0+1 (1.951 chunks 100% embedded baseline)

### Fase 1.6 — Search Quality Upgrade (Abr 2026) ✅ DONE

**Goal:** +30-40% recall em queries ambiguas via query expansion + dedup 4-layer + telemetria.

**Foi feito:**
- Query expansion multi-query rewrite (inspirado em [garrytan/gbrain](https://github.com/garrytan/gbrain))
- Dedup 4-layer (exact / near-dup / cosine / MMR λ=0.7)
- Search telemetry baseline (`search_telemetry` table)
- Validacao com 15 queries de aceitacao

### Fase 1.7a — Core Memory Quality (Abr 2026) ✅ DONE

**Goal:** Entidades ricas + economia de API + User Profile carregado no boot dos agentes.

**Foi feito:**
- KG extraction Gemini 2.5 Flash com schema fechado de 7 tipos de relacao
- ~402 entidades + ~544 relacoes acumuladas
- Compiled truth + source attribution per entity (inspirado em [topoteretes/cognee](https://github.com/topoteretes/cognee), [garrytan/gbrain](https://github.com/garrytan/gbrain))
- User profile injection no boot dos agents
- Reflective loops (consolidacao + crystallize)

### Fase 1.7b — Memory Quality Advanced 🛑 DORMENTE → migrou para E09

**Goal original:** Deteccao de contradicoes + versionamento de fatos + auto-esquecimento + entity detection real-time.

**Status:** Dormente apos analise ClawMem (2026-04-26). Funcionalidade reabsorvida em **E09 A-MEM auto-keywords/links no ingest** (5-6h, gated em E05 active obrigatorio + shadow 7d). Trigger pra resurrect: enum CLOSED estavel via E05 ranking-active.

### Fase 2 — Graphify + GitHub Repos (Abr 2026) ✅ DONE

**Goal:** Primeiro grafo real sobre os projetos do Toto via [safishamsi/graphify](https://github.com/safishamsi/graphify) (71.5x menos tokens via Claude Vision).

**Foi feito:**
- 9 repos GitHub processados via graphify
- 147 docs + 2 entities piloto ingestados
- 7.300+ chunks ativos pos-IM + Fase 2 Graphify
- Router `routeIngest` unificado (graphify + entity + markdown)

### Fase 2.5 — graph-memory Plugin (Abr 2026) ✅ DONE

**Goal:** Memoria de curto prazo + compressao de contexto (~75%) + recall cross-session via [adoresever/graph-memory](https://github.com/adoresever/graph-memory).

**Foi feito:** Plugin instalado, validado em producao, log startup patchado para mostrar gemini/flash-lite real (vs default mascarado).

### Fase 3 — HD Mac rsync + Enrichment Tiered (Abr 2026) ✅ DONE (parcial)

**Goal:** Documentos pessoais (PPTX/PDF/XLSX/DOCX) do Mac indexados.

**Foi feito:**
- Script `~/sync-vault.sh` no Mac (rsync via Tailscale, filtro por extensao)
- Tier 1 (markdown/text) ingest funcional
- Pipeline de enrichment classificado por importancia

**Em progresso (E02 🔄):** Tier 2 PDFs — gap real 954 (não 2.269 estimados); cobertura A6 = 79% (3.541/4.495); retry NUVIVI+CONTRATOS rodando background (+1.236 chunks ingestados). Gap residual ~728 PDFs → E12 Tier 3 OCR (escopo expandido).

### Fase 4 — Obsidian View-Only (Abr 2026) ✅ DONE

**Goal:** Visualizar segundo cerebro no Mac como galaxia 3D — read-only, zero risco de corrupcao.

**Foi feito:**
- Python gen 430 LOC produz `graphify-out/obsidian/` como vault pronto
- Cron + launchd ativo
- Vault Obsidian sincronizado com chunks + entities + KG
- 30 dias de estabilidade exigidos antes de habilitar Fase 4b

### Hardening Triplo (Abr 25-27 2026) ✅ DONE

**Goal:** Sistema resistente a upgrades de infra, ops destrutivas, drift de schema, incidents.

**Foi feito:**
- 47 findings de audit → 11 HIGH fechados
- Audit log `ops_audit` append-only com SQL triggers (CWE-693)
- `withOpAudit()` wrapper cria snapshot atomico VACUUM INTO antes de op destrutiva
- Dry-run mode em `reindex` e `consolidate`
- Canary invariants */15min com alert Discord
- E2E test suite (27 tests passando)
- Schema v10 (retention_days + pain + section + section_boost)

### Upgrade Defense System (Abr 27 2026) ✅ DONE

**Goal:** Aplicar upgrades OpenClaw sem destruir monkey-patch Issue #62028 ou improvements deployados.

**Foi feito:**
- `ckpt` script (492 LOC) com save/list/show/diff/restore/pin/unpin/prune
- `improvements` Python runner com 13 invariantes (7 critical + 6 warn)
- `release-watcher.sh` cron diario 12:00 BRT (notifica WhatsApp + Discord)
- `oc-upgrade` orchestrator com auto-rollback em violacao critical
- `upgrade-zero-downtime.sh` 5-fase pipeline (pre-flight → staging port 18790 → smoke → swap → 5min watch)

### Consolidacao Documental (Abr 27 2026) ✅ DONE

**Goal:** Repo profissional com single source of truth, sem sprawl de 25 plans + 9 handoffs.

**Foi feito:**
- 3 docs canonicos vivos: `HANDOFF.md` + `ROADMAP.md` + `DECISIONS.md`
- 4 docs novos via agents: `ARCHITECTURE.md` + `RUNBOOKS.md` + `CONTRIBUTING.md` + `README.md` profissional
- Sistema unificado de IDs F/E/R/P/G/D substitui 6+ namespaces antigos (A/B/W/Q/Fase/Phase)
- 25 plans + 9 handoffs antigos arquivados em `plans/_archive/` e `handoffs/_archive/`
- Review triplo (architect + critic + architect-reviewer) com 14 correcoes aplicadas
- Cross-ref VISION.md em todos os items do roadmap

---

### ✅ Fase concluída — Pre-Gate + Gates G01-G03 (04-27 → 05-01)

**Resultado:** Sistema healthy + 3 gates fechados + 4 foundation items DONE + 5 design specs criadas.

**Entregue:**
- ✅ **G01 Salience activation** (04-30) — `recency × pain × importance` ativa em `/api/health.salience`
- ✅ **G02 Section_boost** (05-01) — shadow→active após análise 7d (compiled +100% / frontmatter +49% / timeline -17%)
- ✅ **G03 Archive 3 source files** (05-01) — `memory/{projects,decisions,lessons}.md → .archived-20260502` + 8 chunks órfãos cleanup
- ✅ **F12 Gemini SPOF playbook** (05-01) — Tier 1/2/3 mitigation em `docs/RUNBOOKS.md`
- ✅ **F13 Cost projection alt** (05-01) — 4 cenários 12mo + switch OpenAI 1h
- ✅ **F14 DR drill** (05-01) — script + cron quarterly instalado, próxima execução auto 2026-07-06
- ✅ **3 bug fixes** — `db.ts` honra `NOX_DB_PATH`, PRAGMA `user_version` aligned 10/10, 27/27 tests pass
- 🤔 **5 design specs** — E03a / E04a / F10 / R01a revalidated / F14 quarterly (prontas pra impl Maio)
- ❌ **F09 off-site backup CUT (D22)** — user rejected 2x (VPS Hostinger native suffices)

### 🔄 Fase atual — Implementation Maio (post-gates)

**Goal:** Implementar specs já validadas + finalizar E02 retry + Wave 1 core.

### 📋 Wave 1 — Memory Graph Maturity (Maio-Jun 2026)

**Goal:** Edge typing rico + impact analysis + change detection sobre KG existente.

**Sera feito:**
- **E02 Tier 2 PDFs ingest** (15-25h I/O paralelo) — 4.432 PDFs do HD Mac
- **E03a/b A6 Entity-Facts SPO Injection** (1.7h) — `<vault-facts>` block via KG, shadow 7d
- **E04a/b A7 Session Focus Topic Boost** (1.8h) — `focus set <topic>` 1.4×/0.75×, shadow 7d
- **E05 Edge typing FULL** (8-10h) — `relation_reason` enum 7 + `confidence REAL`, kg_relations v11
- **R01a Eval harness skeleton** (4-6h) — schema v12 + tabela `eval_queries` + nDCG@10/MRR + CLI

### 📋 Wave 2 — Eval + Impact CLI (Jun-Jul 2026)

**Goal:** Baseline cientifico de busca + ferramentas de impact analysis.

**Sera feito:**
- **E06 detect-changes** (2-3h) — `nox-mem detect-changes --since=<commit>` read-only git diff→entities
- **E07 impact** (2.5h) — `nox-mem impact <entity>` 1-hop blast radius via kg_relations
- **E08 api_impact** (1.5h) — multi-arquivo grep + import graph (nice-to-have)
- **R01b Curadoria 50 golden queries** (8-10h cognitive floor, spread Jun-Jul)
- **R01c Baseline FTS-only vs hybrid** + publish nDCG@10 em `/api/health.evalMetrics`
- **E10 Consolidation merge candidate** (3-4h, gated nDCG≥0.6)

### 📋 Wave 3 — Paper + Fase Cognitiva (Ago 2026)

**Goal:** Documentar evolucao via paper academico + features cognitivas avancadas.

**Sera feito:**
- **R02 Paper v2** (5-6h) — Affective Ranking + Multi-Agent Federation + Bridge Mode
- **E09 A-MEM auto-keywords/links** (5-6h, candidate, gated em E05 active)

### 🚀 Productizacao + Bloco V (Set+ 2026)

**Goal:** Empacotar nox-mem como produto comercial Hotmart + features finais.

**Sera feito:**
- **E11 Reflect cache** (1.5h) — semantic key cache pra reflect operations
- **F15 SEH Self-Evolving Hooks** (1h) — auto-evolution de regras operacionais
- **E12 Tier 3 OCR + Fathom + Path C** (dias, opcional) — PDFs scaneados + reunioes
- **P01 NOX-Supermem productizacao** (semanas) — Fase 4b → 5 → P, mercado Brasil/Hotmart, tiers A/B/C R$147/197/227 + R$30/sem suporte

> **Fase 4b/5 (futuro):** Obsidian Write + Bidirectional Sync via [YearsAlso/openclaw-memory-sync](https://github.com/YearsAlso/openclaw-memory-sync). Pre-requisito: 30 dias estavel em view-only sentindo falta.

---

## Phase Matrix (status canonico embedded — v3.7+)

> Tabela autossuficiente para entender o estado real sem abrir o plano. Detalhes operacionais (sequencia, esforcos, gates, dependencias) em [`docs/ROADMAP.md`](docs/ROADMAP.md).

| # | Fase | Status | Conclusao | Notas |
|---|---|---|---|---|
| 1 | Quick Wins (wip, feedback, L1) | ✅ DONE | 2026-04-11 | — |
| 1.5 | KG Migration Ollama→Gemini | ✅ DONE | 2026-04-11 | 1.489 entities |
| 0.5 | Foundation Repair | ✅ DONE | 2026-04-18 | 1.951/1.951 embedded |
| 24h | Observacao pos-Foundation | ✅ DONE | 2026-04-21 | 3d estavel |
| 1.6 | Search Quality (expansion + dedup) | ✅ DONE | 2026-04-19 | wrapper puro |
| 1.7a | Core Memory Quality | ✅ DONE | 2026-04-19 | ontology, USER-PROFILE |
| 2.5 | graph-memory plugin | ✅ DONE (patched) | 2026-04-23 | log misleading 04-24 |
| D1-D4 | Audit sistemica | ✅ DONE | 2026-04-21 | 17 fixes |
| RP | RelayPlane | ✅ DONE | 2026-04-21 | INATIVO desde 04-22 (substituido pelo Claude CLI) |
| IM | Import repos locais | ✅ DONE | 2026-04-23 | 147 docs + 9 repos |
| 1.7b-a | Typed retention matrix | ✅ DONE | 2026-04-23 | schema v8 |
| Stab | 5-agent audit + 10 fixes | ✅ DONE | 2026-04-23 | APPROVE WITH MINOR |
| 2 | Graphify scale | ✅ DONE (9 repos) | 2026-04-23 | 1.046 graph_node chunks |
| 1.7b-b | Salience formula formal | ✅ DONE shadow | 2026-04-23 | schema v9, pain REAL |
| 1.7b-c | Compiled truth + timeline | ✅ DONE | 2026-04-24 | schema v10, 181 entities |
| 3 Tier 1 | HD Mac md+docx | ✅ DONE | 2026-04-24 | 2.697 chunks via pandoc + watcher |
| **Sprint A1** | **GitHub repos + Claude workspace ingest** (graphify-ingest 9 repos + 7 repos pequenos + Claude scope curado docs/agents/skills/commands/Projetos) | ✅ **DONE** | **2026-04-27** | **+19.070 chunks** (1.046 graph_nodes + 304 small repos md + 17.714 Claude workspace md). Scope cut: _retired/, prompts/, powerpoint-templates, nox-workspace |
| **Sprint A3** | **Mac local ~/Claude/Projetos delta** (rsync agent-orchestrator local-only, 143MB → VPS) | ✅ **DONE** | **2026-04-27** | **+863 chunks** (106 md). Outros ~/Claude/Projetos/* duplicariam shared/imports, scope cut. Skip A2 (~/Desktop transitório) |
| **Sprint A4** | **~/Documents office files docx+xlsx+pptx** (NUVIVI, PPR, PESSOAL, CONTRATOS, BANCOS, EMPRESAS Cont — sem PDFs/fotos/videos) | ✅ **DONE** | **2026-04-27** | **+2.469 chunks** (972 xlsx + 81 pptx + 2 docx novos). Stack expandido: pandoc + libreoffice-calc + **markitdown[pptx]** (Microsoft 117k stars MIT, novo na stack). Erros mínimos: 6 docx + 2 pptx |
| **Sprint A5** | **Pipeline unified script** (markitdown primary + pandoc/libreoffice fallback, idempotent) | ✅ **DONE** | **2026-04-27** | `convert-office-to-md.sh` + `pdf-batch.sh` standalone reusáveis em `/root/.openclaw/scripts/` |
| **Sprint A6** | **PDF batch Tier 2 antecipado** (4.494 PDFs ~/Documents NUVIVI/PPR/PESSOAL/CONTRATOS/BANCOS, sem OCR) | ✅ **DONE** | **2026-04-27** | **+19.602 chunks** (1.444 text-layer PDFs convertidos). 781 scanned descartados (esperam OCR E12). 3 tentativas de batch (parent-shell death, systemd quoting hell, watchdog 69 procs OOM) → tmux session estável. 0 errors no retry vectorize 13min |
| **F01** | Query logging + golden-tag (search_telemetry +4 cols) | ✅ DONE | 2026-04-25 | extends search_telemetry, opt-in NOX_SEARCH_LOG_TEXT=1 |
| **F02** | Audit log + `withOpAudit` snapshot pre-op atomico | ✅ DONE | 2026-04-26 | cura incident 04-25, ops_audit append-only triggers |
| **F03** | Ingest-router unified (single dispatch `routeIngest`) | ✅ DONE | 2026-04-26 | debito arquitetural cleared |
| **F04** | Unit tests parseRetentionOverride (20 cases) | ✅ DONE | 2026-04-26 | backlog #1, teria pego incident |
| **F05** | Canary invariants extension (5 invariants */15min Discord) | ✅ DONE | 2026-04-26 | +section/retention NOT NULL |
| **F06** | Dry-run mode em ops destrutivas (reindex/consolidate) | ✅ DONE | 2026-04-26 | antes migration v11+ |
| **F07** | OpenClaw upgrade defense (ckpt + improvements + watcher + orchestrator) | ✅ DONE | 2026-04-27 | destrava upgrades futuros |
| **F08** | B3 backlog sprint 7/8 (issue + CONVENTIONS + alerts + playbooks) | ✅ DONE | 2026-04-27 | 1h45m total |
| **F11** | RUNBOOKS.md formalizado (RB-01 a RB-10 incident playbooks) | ✅ DONE | 2026-04-27 | 902 LOC, 10 cenarios |
| **E01 / 4** | Obsidian view-only (Python gen 430 LOC + cron+launchd) | ✅ DONE | 2026-04-26 | destrava Fase P em 30d |
| **F09** ⭐ | ~~Off-site backup rclone → B2/R2~~ → **D22 ❌ CUT** (user rejected 2x — VPS Hostinger native backup suffices) | ❌ CUT | 2026-04-29 | ver `docs/DECISIONS.md` linha 246 |
| **G01** | Salience activation `recency × pain × importance` em `/api/health.salience` | ✅ DONE | **2026-04-30** | `NOX_SALIENCE_MODE=active` aplicado pós-baseline 7d OK |
| **G02** | Section_boost shadow→active (compiled +100% n=1252, frontmatter +49% n=315, timeline -17% n=11) | ✅ DONE | **2026-05-01** | `.env NOX_SECTION_BOOST_MODE=active` + services restarted |
| **G03** | Archive 3 source files `memory/{projects,decisions,lessons}.md → .archived-20260502` + cleanup 8 chunks órfãos | ✅ DONE | **2026-05-01** | DB 62.927 → 62.919 via better-sqlite3 cascade |
| **F12** | Embedding model migration playbook — Gemini SPOF mitigation Tier 1/2/3 | ✅ DONE | **2026-05-01** | RB-05 em `docs/RUNBOOKS.md` |
| **F13** | Cost projection pay-per-token alternative (4 cenários 12mo + switch OpenAI 1h + 7 providers) | ✅ DONE | **2026-05-01** | `runbooks/cost-projection-alt-providers.md` |
| **F14** | DR drill trimestral — script `dr-drill.sh` + cron `0 9 1 1,4,7,10 1` instalado, RTO 3s validado | ✅ DONE | **2026-05-01** | próxima execução auto 2026-07-06 |
| **E02 / 3 Tier 2** | Tier 2 PDFs (gap real 954, cobertura A6 = 79% / 3.541 ingested + retry NUVIVI/CONTRATOS +1.236 chunks) | 🔄 IN-PROGRESS | 2026-05-01 | gap residual ~728 → E12 OCR; E12 escopo expandido |
| **F10** | Observability dashboard (4 painéis IndexedDB ring buffer 7d no agent-hub-dashboard) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-F10-observability-dashboard.md`, impl 2.5-3h Maio |
| **E03a** | A6 Entity-Facts SPO Injection (`<vault-facts>` block via KG, top-K simples, schema zero-mudança) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-E03a-spo-injection.md`, impl 1.5h |
| **E03b** | A6 activate após 7d subjective utility report | 📋 QUEUED | post-E03a + 7d wall | 0.2h |
| **E04a** | A7 Session Focus Topic Boost (`focus set <topic>` 1.4×/0.75×, cache TTL 7d) | 🤔 SPEC READY | 2026-05-01 | spec `specs/2026-05-01-E04a-focus-boost.md`, impl 1.5h |
| **E04b** | A7 activate após 7d shadow + delta recall ≥3% | 📋 QUEUED | post-E04a + 7d shadow | 0.3h |
| **E05 / W1.1** | Edge typing FULL (relation_reason enum 7 + confidence REAL, kg_relations v11) | 🟣 WAVE 1 Maio-Jun | gated por metricas | 8-10h, shadow 7d antes ranking |
| **E06 / W1.2** | `nox-mem detect-changes --since=<commit>` read-only git diff→entities | 🟣 WAVE 1 Jun | depende E05 | 2-3h |
| **E07 / W1.3** | `nox-mem impact <entity>` 1-hop blast radius via kg_relations | 🟣 WAVE 1 Jun-Jul | E05 active (nao shadow) | 2.5h |
| **E08 / W1.4** | `nox-mem api_impact <signature-change>` multi-arquivo grep + import graph | 🟣 WAVE 1 Jul | nice-to-have | 1.5h |
| **R01a / W2.1** | Eval harness skeleton (schema v12 + `eval_queries` + nDCG@10/MRR + CLI) | 🟣 WAVE 2 Maio | F01 corpus ready | 4-6h, MOVED earlier baseline-first |
| **R01b** | Curadoria 50 golden queries (cognitive floor, nao comprime) | 🟣 WAVE 2 Jun-Jul | spread Jun-Jul | 8-10h humano |
| **R01c** | Baseline FTS-only vs hybrid + publish nDCG@10 em /api/health.evalMetrics | 🟣 WAVE 2 Jul | R01a + R01b | 1-2h |
| **E09 / W1.5** | A-MEM auto-keywords/links no ingest (funde Fase 1.7b dormente) | 🤔 CANDIDATE Ago | E05 active obrigatorio | 5-6h |
| **E10 / W2.2** | Consolidation merge + contradiction detection (entity-anchor val) | 🤔 CANDIDATE Jul | gated nDCG≥0.6 + dry-run zero FP | 3-4h |
| **R02 / W3.1** | Paper v2 (Affective Ranking + Multi-Agent Federation + Bridge Mode) | 🟣 WAVE 3 Ago | depende R01c baseline | 5-6h cognitive floor |
| **E12 / 3 Tier 3** | Tier 3 OCR — escopo expandido inclui ~728 PDFs gap E02 (PPR 372 + PESSOAL 250 + size-rejected ~106) + Fathom + Path C | 📋 QUEUED | post-E02 | dias |
| **3 Tier 3** | OCR Gemini PDFs scaneados (opcional) | 🔒 OPCIONAL | — | dias |
| **3.5** | Fathom API (opcional, paralela) | 🔒 OPCIONAL | — | 3-4h |
| **E11 / Path B-lite** | Reflect cache (semantic key) | 🔒 BLOCKED Set+ | depende telemetria reflect | 1.5-3h |
| **Path C** | WAL shipping + cold tier | 🔒 BLOCKED | depende Fase 4 estavel 30d | dias |
| **4b/5** | Obsidian write + bidirectional | 🔒 FUTURO | depende Fase 4 + 2-4 sem | semanas |
| **F15 / SEH** | Self-Evolving Hooks | 🔒 INDEPENDENTE Set+ | — | 1-2h |
| **F16** | Telegram bot rollback automatico (health-check 30min) | 🔒 BACKLOG | fora orcamento atual | 4h |
| **P01 / Fase P** | Productizacao NOX-Supermem (Fase 4b → 5 → P) | 🔒 HORIZONTE 60d+ | depende Fase 4 estavel 30d (>= 05-26) | semanas |

**Legenda:** ✅ DONE / 🔄 IN-PROGRESS / 🤔 SPEC READY (impl pendente) / 📋 QUEUED / 🟣 WAVE FUTURA (gated por metricas) / 🤔 CANDIDATE (POC + 7d shadow) / 🔒 BLOCKED ou FUTURO / ❌ CUT

**Sistema unificado de IDs F/E/R/P/G/D** substitui 6+ namespaces antigos (A/B/W/Q/Fase/Phase). Cross-ref completo em [`docs/ROADMAP.md §8`](docs/ROADMAP.md). Items DEFERRED/CUT (D01-D21) em [`docs/ROADMAP.md §4`](docs/ROADMAP.md#4-tabela-mestre-cronologica).

### Capacity overview

```
Disponivel 04-27 → 09-30:    ~22 semanas × 6h/sem = 132h
Margem incident:             -20h reservadas (4 incidents em 2 dias 04-25/26)
Capacity liquida:            ~112h
Compromissado nucleo:         53-72h
Candidates (E03a/b, E04a/b, E09, E10):  11.5-13.5h
Bloco V (Set+):               2.5h pequeno + dias-semanas E12/P01
Sobra realista:               +23 a +45h
```

---

## Mapa de documentacao

| Para... | Leia... |
|---|---|
| Proxima acao imediata + estado vivo | [docs/HANDOFF.md](docs/HANDOFF.md) |
| Roadmap completo + capacity + gates | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Decisoes arquiteturais + NAO FAZEMOS | [docs/DECISIONS.md](docs/DECISIONS.md) |
| System design overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Visao estrategica long-term | [docs/VISION.md](docs/VISION.md) |
| Regras criticas pra AI assistants (1-15) | [CLAUDE.md](CLAUDE.md) |
| Incident playbooks | [docs/RUNBOOKS.md](docs/RUNBOOKS.md) |
| Convencoes de codigo e docs | [docs/CONVENTIONS.md](docs/CONVENTIONS.md) |
| Historico de versoes v1.0 → v3.7 | [docs/EVOLUTION.md](docs/EVOLUTION.md) |
| Incident log completo | [docs/INCIDENTS.md](docs/INCIDENTS.md) |
| Como trabalhar neste repo | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Audit trail (13+ docs) | [audits/](audits/) |
| Paper tecnico | [paper/paper-tecnico-nox-mem.md](paper/paper-tecnico-nox-mem.md) |

---

## Estrutura do repositorio

```
memoria-nox/
├── README.md                   <- este arquivo
├── CLAUDE.md                   <- regras operacionais 1-15 para AI assistants
├── docs/
│   ├── HANDOFF.md              <- estado vivo (single source of truth "agora")
│   ├── ROADMAP.md              <- timeline + capacity + gates ("o que vem")
│   ├── DECISIONS.md            <- append-only (NAO FAZEMOS + razoes + licoes)
│   ├── ARCHITECTURE.md         <- system design overview
│   ├── VISION.md               <- long-term thesis
│   ├── CONVENTIONS.md          <- convencoes detalhadas
│   ├── EVOLUTION.md            <- historico v1.0→v3.7
│   ├── INCIDENTS.md            <- incident log
│   ├── RUNBOOKS.md             <- incident playbooks
│   ├── CONTRIBUTING.md         <- como trabalhar no repo
│   └── _archive/               <- handoffs e plans antigos (referencia historica)
├── specs/                      <- especificacoes tecnicas
├── audits/                     <- audit trail (13+ docs)
├── scripts/                    <- ops scripts (ckpt, improvements, oc-upgrade, release-watcher)
├── paper/                      <- paper tecnico (.md + .docx)
├── plans/_archive/             <- roadmaps anteriores (v1.5, v1.6)
├── handoffs/_archive/          <- handoffs de sessoes anteriores
└── .github/
```

---

## Stack tecnico

- **Runtime:** TypeScript / Node.js 22 (wrapper `--no-warnings` obrigatorio)
- **Storage:** better-sqlite3 + FTS5 (BM25) + sqlite-vec (3072d vectors)
- **Embeddings:** Gemini gemini-embedding-001 via `gemini-2.5-flash-lite` default
- **Backend agents:** Claude CLI (`/usr/bin/claude`) via OAuth Max — zero cobrança de API
- **Orchestration:** OpenClaw v2026.4.23 (monkey-patched para Issue #62028)
- **Watcher:** inotifywait + debounce 15s
- **Process management:** systemd (3 servicos ativos: openclaw-gateway + nox-mem-api + nox-mem-watcher)
- **Dashboard:** [agent-hub-dashboard](https://github.com/totobusnello/agent-hub-dashboard) (4 paginas nox-mem)

---

## Operacoes e seguranca

O sistema opera com 5 camadas de defesa sobrepostas: (1) `withOpAudit()` cria snapshot atomico antes de qualquer op destrutiva; (2) dry-run obrigatorio antes de operacoes em prod; (3) `ops_audit` append-only com SQL triggers CWE-693; (4) canary de invariantes `*/15min` com alert Discord; (5) improvements audit com 13 checks (7 critical + 6 warn-only) que cobrem permissoes, cron, env vars, monkey-patch e session drift.

O script `ckpt` cria checkpoints git com snapshot de estado de sistema. O release-watcher monitora novas versoes do OpenClaw antes que upgrades automaticos destruam o monkey-patch do Issue #62028. O orchestrator de upgrade (`oc-upgrade`) aplica versoes novas com auto-rollback em caso de fratricide detectado.

Baseline de saude: `ssh root@100.87.8.44 '/root/bin/improvements check'` deve retornar **13/13 OK**.

---

## Projetos relacionados

- **[nox-supermem](https://github.com/totobusnello/nox-supermem)** (privado) — produto comercial PT-BR baseado no nox-mem. Mercado Brasil, distribuicao Hotmart, tiers A/B/C. Em desenvolvimento apos Fase 4 estavel 30 dias.
- **[agent-hub-dashboard](https://github.com/totobusnello/agent-hub-dashboard)** — dashboard UI com 4 paginas nox-mem (chunks, KG, search telemetry, health).

---

## Licenca

MIT — veja [LICENSE](LICENSE).

---

## Agradecimentos

Construido por [Toto Busnello](https://github.com/totobusnello). Powered by [Claude](https://anthropic.com) (Anthropic). Usa [OpenClaw](https://openclaw.dev), [sqlite-vec](https://github.com/asg017/sqlite-vec) e Gemini (Google DeepMind).
