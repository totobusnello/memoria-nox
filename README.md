# memoria-nox

> Sistema de memória inteligente multi-agent com hybrid search, knowledge graph com edge typing, eval harness, semantic cache, blast radius analysis e backend claude-cli zero-cost.

**Status & quality**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/totobusnello/memoria-nox)](https://github.com/totobusnello/memoria-nox/commits/main)
[![Tests](https://img.shields.io/badge/tests-69%2F69%20passing-brightgreen)](docs/HANDOFF.md)
[![Schema](https://img.shields.io/badge/schema-v12-blue)](CLAUDE.md)
[![Chunks](https://img.shields.io/badge/chunks-64.180-blue)](docs/HANDOFF.md)
[![KG](https://img.shields.io/badge/KG-914_entities_%2F_1109_relations-blue)](docs/HANDOFF.md)
[![Eval nDCG](https://img.shields.io/badge/eval__nDCG@10-0.519_(n%3D50)-blue)](docs/HANDOFF.md)
[![R01b Cure](https://img.shields.io/badge/R01b__cured-50%2F50_✅-brightgreen)](docs/HANDOFF.md)

**Features ativas**

[![Salience](https://img.shields.io/badge/salience-active-brightgreen)](docs/DECISIONS.md)
[![Section Boost](https://img.shields.io/badge/section__boost-active-brightgreen)](docs/DECISIONS.md)
[![Edge Typing](https://img.shields.io/badge/edge__typing-active-brightgreen)](docs/ROADMAP.md)
[![Reflect Cache](https://img.shields.io/badge/reflect__cache-semantic-brightgreen)](docs/ROADMAP.md)
[![CLI Telemetry](https://img.shields.io/badge/CLI__telemetry-active-brightgreen)](docs/ROADMAP.md)
[![SEH](https://img.shields.io/badge/SEH-detector_active-brightgreen)](docs/ROADMAP.md)
[![SPO Injection](https://img.shields.io/badge/SPO__injection-shadow-yellow)](specs/2026-05-01-E03a-spo-injection.md)
[![Focus Boost](https://img.shields.io/badge/focus__boost-shadow-yellow)](specs/2026-05-01-E04a-focus-boost.md)
[![FTS Gap](https://img.shields.io/badge/FTS__vs__hybrid__gap-97.7%25_loss-red)](paper/paper-v2-draft-evidence.md)

---

## 📑 Índice

- [Por que isso existe](#por-que-isso-existe)
- [Demo / Use cases](#demo--use-cases) ⭐ comandos com sample output
- [Arquitetura](#arquitetura)
- [Quick start](#quick-start)
- [Comparison vs alternativas](#comparison-vs-alternativas) (mem0 / MemGPT / A-MEM / LangChain Memory)
- [Funcionalidades principais](#funcionalidades-principais)
- [Estado atual](#estado-atual)
- [Fases do projeto](#fases-do-projeto)
- [Phase Matrix](#phase-matrix-status-canonico-embedded--v37)
- [Mapa de documentação](#mapa-de-documentacao)
- [Estrutura do repositório](#estrutura-do-repositorio)
- [Stack técnico](#stack-tecnico)
- [Operações e segurança](#operacoes-e-seguranca)
- [Projetos relacionados](#projetos-relacionados)

---

## Demo / Use cases

Sample outputs reais da CLI em produção (VPS, 2026-05-03 noite). Cada comando é read-only e idempotente.

### 🔍 Hybrid search (FTS5 + Gemini semantic + RRF)
```bash
$ nox-mem search "como ativar salience em produção" 3
#1 [16.39 [semantic]] memory/entities/decisions/2026-04-30-salience-activation.md
   "Salience ativado via NOX_SALIENCE_MODE=active após baseline 7d (G01 gate)..."

#2 [15.87 [semantic]] memory/2026-04-30.md
   "G01 ✅ DONE: salience formula `recency × pain × importance` exposta em /api/health.salience"

#3 [12.66 [fts]] shared/lessons/2026-04-30-marathon.md
   "Mode shadow → active após análise distribuição: 16608 review_needed, 45743 archive_candidates"
```

### 🎯 Impact analysis (E07 — 1-hop blast radius)
```bash
$ nox-mem impact "Forge"
## impact: "Forge" [agent, 1306 mentions]
Total neighbors: 54 | Unique entities: 39 | Blast radius score: 13251.4 | Duration: 1ms

### 🔴 depends_on (12, priority=5)
   ← [agent] Nox (1366 m, conf=0.7, via=depends_on)
   → [project] nox-mem (1269 m, conf=0.7, via=uses)
   → [tool] Discord (89 m, conf=0.8, via=depends_on)
   ...

### 🟡 mentions (29, priority=1)
   → [project] OpenClaw (1943 m, conf=0.6, via=mentioned_with)
   ...
```

### 🔄 Detect changes (E06 — git diff → KG entities)
```bash
$ nox-mem detect-changes --since=HEAD~30
## detect-changes (4e0aeb98...eabe0c47)
Files changed: 1498 | Chunks scanned: 1747 | Duration: 268ms

### Entity files (182)
  A memory/entities/decisions/2026-03-09-brave-search-como-provider-padrao.md → decisions/...
  M memory/entities/projects/nox-mem.md → projects/...
  ...

### Affected entities (182)
  [project] nox-mem (1269 mentions, via=entity_file)
  [project] Nuvini (351 mentions, via=entity_file)
  ...
```

### 🔬 API impact (E08 — multi-arquivo grep + classification)
```bash
$ nox-mem api-impact "getDb" --scope ./src
## api-impact: "getDb"
Files scanned: 58 | Files affected: 39
Total refs: 157 (imports=32, usages=121, definitions=4)
Duration: 11ms

### 📍 Definition site(s) (4)
   db.ts  (1 refs)
   __tests__/edge-typing.test.ts  (8 refs)
   ...

### 📥 Importers (32)
   knowledge-graph.ts  (imports=1, usages=15)
   index.ts  (imports=1, usages=9)
   ...
```

### 🧠 Reflect (KG synthesis com semantic cache)
```bash
$ nox-mem reflect "qual a regra sobre commitar secrets no git"
Não comite secrets no Git. Se um secret for committado acidentalmente, rode-o
imediatamente, remova-o do histórico do Git e adicione o padrão ao .gitignore
ou use variáveis de ambiente / gerenciadores de secrets.

Sources: shared/imports/agent-orchestrator/SECURITY.md, shared/lessons/security-audit.md, ...
[fresh, 11 evidence items]

# segunda chamada (paraphrase semantic):
$ nox-mem reflect "qual a politica sobre commits com secrets"
[cached:semantic, 0 evidence items]   # ← 4× speedup via cosine ≥ 0.88
```

### 📊 Eval harness (R01a — nDCG/MRR/Recall/Precision)
```bash
$ nox-mem eval run-batch --variant=hybrid --runs=3
## Eval Batch (variant=hybrid) — 3 runs over 50 queries
| Run | nDCG@10 | MRR    | Recall@10 | Prec@5 |
| #10 | 0.5215  | 0.4900 | 0.6767    | 0.2640 |
| #11 | 0.5207  | 0.4917 | 0.6767    | 0.2640 |
| #12 | 0.5215  | 0.4850 | 0.6867    | 0.2640 |

### Aggregate (mean ± std)
| nDCG     | 0.5213 ± 0.0004 |  ← system é deterministic (RRF tie-breaking only)
| MRR      | 0.4889 ± 0.0028 |
| Recall   | 0.6800 ± 0.0047 |
```

### 🔧 Self-Evolving Hooks (F15a + F15b)
```bash
$ nox-mem cli-stats              # F15a — telemetry insights
## CLI Telemetry Insights
Total runs 7d: 24 | Unique commands: 8

### 📊 Top commands
   reflect              runs=  6 sr=100.0% avg=2516ms p95=3540ms
   search               runs= 12 sr=100.0% avg=621ms  p95=890ms
   ...

$ nox-mem seh-report             # F15b — WoW comparison + alert
## SEH Report
Comparing last 7d vs prior 7d. Proposals: 2.
🟡 [perf_regression] reflect: p95_ms 1200 → 3540 (Δ +195%)
   ▶ p95 saltou 195% WoW. Investigar profile / quota / rede.
   📋 Config patch sugerido: NOX_REFLECT_TIMEOUT_MS=5500 (current: unset)
```

[**→ CLI reference completa em `docs/HANDOFF.md`**](docs/HANDOFF.md)

---

## Comparison vs alternativas

Por que nox-mem em vez de soluções existentes? Cada uma resolve parte do problema, mas falha em pelo menos 1 dos 5 requisitos da [seção "Por que isso existe"](#por-que-isso-existe):

| Solução | Hybrid search | KG nativo | Eval baseline | Multi-agent isolation | Custom shadow-mode | Operacional self-host |
|---|---|---|---|---|---|---|
| **nox-mem** | ✅ FTS5+Gemini+RRF | ✅ kg_entities/relations + edge typing E05 | ✅ R01a harness com nDCG/MRR | ✅ chunks compartilhada | ✅ todas mudanças ranking | ✅ SQLite + Tailscale |
| [mem0](https://github.com/mem0ai/mem0) | ❌ vector-only | ⚠️ Mem0 v2 introduz, mas nasce vector | ❌ sem harness oficial | ⚠️ via user_id | ❌ | ⚠️ paid SaaS preferred |
| [MemGPT/Letta](https://github.com/letta-ai/letta) | ❌ embedding-first | ❌ sem KG | ❌ | ✅ multi-agent core feature | ❌ | ✅ self-host |
| [A-MEM](https://github.com/agi-arena/AgentMemoryEngine) | ⚠️ semantic-first | ⚠️ optional | ❌ | ❌ single-agent design | ❌ | ✅ |
| [LangChain Memory](https://python.langchain.com/docs/concepts/memory) | ❌ key-value/buffer | ❌ | ❌ | ⚠️ via session_id | ❌ | ✅ |
| [Cognee](https://github.com/topoteretes/cognee) | ✅ hybrid | ✅ KG nativo | ⚠️ ad-hoc | ❌ | ❌ | ✅ |

**Quando usar nox-mem:** workspace pessoal/operacional onde tu controla todos os agents (é tu mesmo + assistentes), corpus é misto (código + decisões + memórias longa-prazo), tu valoriza testar cada mudança de ranking antes de ativar (shadow-mode obrigatório) e quer baseline objetivo nDCG pra detectar regressão silenciosa.

**Quando NÃO usar:** SaaS multi-tenant produção (use mem0 paid), agentes de chat consumer-facing puros (use Letta), single-agent assistant simples (use LangChain BufferMemory).

---

## Por que isso existe

Agentes AI sem memória persistente repetem erros, perdem contexto entre sessões e tratam cada conversa como se fosse a primeira. Quando você escala pra **7 agentes** com papéis distintos (Maestro + nox/atlas/boris/cipher/forge/lex), o problema multiplica em três dimensões:

1. **Memórias fragmentadas** — cada agente "vê" só sua história, não a coletiva
2. **Rankings frágeis** — qualquer ajuste de busca pode quebrar resultados sem aviso, e sem baseline objetivo é impossível detectar regressão
3. **Drift de schema** — operações destrutivas (reindex, consolidate, kg-prune) sem snapshot atômico levam a perda silenciosa de campos importantes (incident 2026-04-25 wipou `section`/`retention` de 183 entities)

**nox-mem** resolve com 5 escolhas arquiteturais não-negociáveis:

- **Camada canônica compartilhada** — a tabela `chunks` é fonte única de verdade pros 7 agentes; nada de silos por agente
- **KG derivado, não paralelo** — `kg_entities` + `kg_relations` extraídos via Gemini 2.5 Flash sobre os chunks; quando chunks mudam, KG re-deriva (não vira drift independente)
- **Shadow-mode obrigatório 7d** — qualquer mudança que afete ranking (salience, section_boost, focus, edge typing) roda em paralelo computando+logando antes de surgir nos resultados; ativação só após análise de telemetria real
- **Snapshot atômico pré-op** — `withOpAudit()` cria backup VACUUM INTO antes de qualquer destructive op; recovery em segundos via `safeRestore()` com PRAGMA sentinel
- **Baseline-first em qualquer ranking change** — antes de ativar E05/E10/D01 reranker, mede nDCG@10 vs baseline atual via eval harness (R01a) com golden queries curadas; sem baseline, não merge

O sistema é construído pra **resistir a upgrades de infra** (já sobreviveu OpenClaw v.24→v.25→v.26→v.29 sem perda de dados), **patches de segurança** (24+ feedback files documentando incidents resolvidos), e **mudanças de modelo** (Gemini Flash → Flash-Lite default por custo, com playbook RB-05 pra trocar provider em 1h se necessário).

**Estado atual em produção** (VPS Hostinger, Tailscale-only, 2026-05-03 20:30 BRT):
- **64.180 chunks** indexados / **100% embedded** (Gemini 3072d sqlite-vec) / **1.036 GB** DB
- **914 entities + 1109 relations** no KG (+128% / +104% nesta sessão pós kg-extract n=100); reasons classified: depends_on=260, mentions=213, derived_from=35, extends=3, replaces=2, opposes=1, unknown=595 (46% classified, +29pp vs baseline 17%)
- **Schema v12** (PRAGMA aligned 12/12, drift-recovery proof, relation_reason enum 7 fechado, +cli_telemetry table 2026-05-03)
- **Gates fechados:** G01 salience + G02 section_boost + G03 archive ✅
- **Features em shadow** (gate activate 2026-05-09 via routine automática):
  - **SPO injection** (E03a) — `<vault-facts>` block via KG, top-K 8, sanitize anti-injection
  - **Focus boost** (E04a) — `nox-mem focus set <topic>` 1.4×/0.75×, cache hardened sha256+0600
- **Features active (Wave 1 sprint 2026-05-03):**
  - **Edge typing FULL** (E05+B1+B2+B3) — relation_reason enum 7 com 3-path normalize + RELATION_TYPE_TO_REASON map + `kg-reclassify` backfill subcomando; classification rate 14%→56%
  - **detect-changes** (E06) — `nox-mem detect-changes --since=<commit>` git diff → entidades KG afetadas (1498 files → 182 entities em 268ms)
  - **impact** (E07) — `nox-mem impact <entity>` 1-hop blast radius via reason-weighted scoring (Toto blast=29152.1)
  - **api-impact** (E08) — `nox-mem api-impact <signature>` multi-arquivo grep + import/definition/usage classification (getDb: 39 files em 11ms)
  - **consolidate-merge** (E10 dry-run) — entity merge candidate detection com FP risk + protected names (914 entities → 52 pairs em 134ms; --apply gated R01≥0.6)
  - **reflect cache semantic** (E11) — Gemini embed + cosine ≥ 0.88; exact hit 30× / semantic hit 4× speedup
  - **CLI Observability** (F15a) — `cli_telemetry` + `cli-stats` insights (top usage / slow / error-prone / dormant); secret redaction defensiva
- **Eval harness** (R01a) — schema v12, 6 CLI subcomandos, endpoint `/api/eval-metrics`, JSONL export
- **Eval baseline definitivo R01c (Run #9, n=50 com R01b 50/50 cured):** hybrid **nDCG@10=0.519** / MRR=0.482 / Recall@10=0.687 / Prec@5=0.268. Drag de balanceamento: 6 negative cases (12% sample). FTS-only n=50 = nDCG=0.015 → **gap 97.7% loss vs hybrid** (sample 10× maior que prelim) confirma necessidade arquitetural pipeline 3-camada. Trigger D01 cross-encoder NÃO dispara (0.519 < 0.6). Pontos fracos: temporal=0.233, cross-agent=0.369, entity=0.459 (alvos E07/E08/E10).
- **Hardening:** 69/69 baseline tests pass, 13/13 improvements OK pós ajuste threshold 12→55, audit log append-only com triggers DB, op-audit + dry-run + canary invariants */15min Discord, **2 audits CRITICAL + security HIGH (4+7) fixed mesma sessão** (execFileSync arrays + scope allowlist + Buffer pool aliasing copy + N+1 → in-memory)

**Origem e endereço:** projeto pessoal de [@totobusnello](https://github.com/totobusnello) (Toto), construído solo. Capacity realista ~6h/sem; arquitetura calibrada pra essa restrição — escolhe simples sobre clever, prefere defer feature sobre tech debt.

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

### ✅ Fase concluída — Triple deploy (2026-05-02)

**Resultado:** 3 features novas em produção + schema v11 + R01b 5/50 cured + 1ª eval baseline.

**Entregue:**
- ✅ **E03a SPO injection** (shadow) — `<vault-facts>` block via KG, top-K 8, sanitize anti-prompt-injection; smoke 1 entity / 7 triples / 55 tokens
- ✅ **E04a Focus boost** (shadow) — CLI `focus set/get/clear`, cache hardened `${WORKSPACE}/focus/<sha256>.json` mode 0600/0700, zod-style validation, `NOX_FOCUS_SESSION` env override pra CLI+API sync; smoke on=2 / off=28 / delta±0.110
- ✅ **R01a Eval harness** (live) — schema v11 (3 tabelas), 5 CLI subcomandos (`eval init/golden import/list/run/compare`), métricas nDCG@10/MRR/Recall@10/Precision@5, `/api/eval-metrics` endpoint, JSONL export
- ✅ **R01b 5/50 cured** — 4 queries com chunks + 1 negative case (withOpAudit gap código TS); baseline hybrid nDCG=0.699 vs FTS=0.000
- ✅ **3 fixes residuais** — F14 RTO breakdown (5s) / F10 stack canônica / cost projection escrito por extenso
- ✅ **PRAGMA v2 patch** — ensureSchema realign antes early return (drift recovery proof)

### ✅ Fase concluída — E05 Edge Typing Phase 1 (2026-05-02 noite)

**Resultado:** Schema v12 ativo + relation_reason enum 7 fechado + SPO surface annotation.

- ✅ **Schema v12 migration** com defensive lazy-init + ALTER TABLE + index `idx_kg_relations_reason`
- ✅ **544 backfill** existentes recebem `'unknown'` (zero data loss)
- ✅ **Gemini extraction enrichment** — RelationReason CLOSED 7 + responseSchema enum guard
- ✅ **SPO surface** — `<vault-facts>` agora anota `[reason]` quando classified
- ✅ Tests: 10/10 edge-typing pass + 109/110 suite total

### ✅ Wave 1 sprint completo (2026-05-03) — 8 features + audit triplo + 11 fixes

**Resultado:** Wave 1 inteira fechada em ~5h (vs ~10h estimate); 4 CRITICAL + 7 HIGH security/perf bugs flagged e fixed mesma sessão.

**Entregue:**
- ✅ **B1+B2+B3 fix E05 reason undercoverage** — RELATION_TYPE_TO_REASON map (24 entradas PT-BR + EN) + 3-path normalize + prompt revisado + novo `kg-reclassify` subcomando (137 backfill em <50ms zero Gemini); classification rate **14% → 56%** (4× melhora) em sample n=100
- ✅ **R01b 50/50 milestone** — 6 NEGATIVE/GAP cases + 4 cured via search prod top-10 análise; libera R01c definitivo
- ✅ **R01c Run #9 hybrid n=50** — nDCG=0.519 / Recall=0.687 (drag de balanceamento 12% negatives); FTS-only n=50 = 0.015 → **gap 97.7% loss confirma necessidade arquitetural pipeline 3-camada**
- ✅ **E06 detect-changes** — `--since=<commit>` git diff → entities (1498 files → 182 entities em 268ms); `src/detect-changes.ts` ~210 LOC
- ✅ **E07 impact** — `<entity>` 1-hop blast radius com REASON_PRIORITY weights (E05) + blast_radius_score (Toto blast=29152.1 em 1ms); `src/impact.ts` ~165 LOC
- ✅ **E08 api-impact** — `<signature>` multi-arquivo grep + import/definition/usage classification (getDb: 39 files / 157 refs em 11ms); `src/api-impact.ts` ~150 LOC
- ✅ **E10 consolidate-merge dry-run** — entity merge candidate detection (914 entities → 52 pairs em 134ms; 39 LOW FP / 9 MEDIUM / 4 HIGH protected); apply gated R01≥0.6
- ✅ **E11 reflect cache semantic** — Gemini embed + cosine ≥ 0.88; **exact hit 30× / semantic hit 4× speedup**; `src/reflect.ts` extension
- ✅ **F15a CLI Observability** — `cli_telemetry` + `cli-stats` (renomeado pós-critic; F15b SEH proper queued); secret redaction defensiva
- ✅ **R02 paper v2 draft** — 7 sections com 6 quantitative tables + 4 open questions em `paper/paper-v2-draft-evidence.md`
- ✅ **Audit triplo** code-reviewer + security-reviewer + critic em paralelo → **11 fixes (4 CRITICAL + 7 HIGH)** aplicados mesma sessão (execFileSync arrays vs command injection, Buffer pool aliasing copy, scope realpath allowlist, N+1 → in-memory intersect, SQL placeholder cap 500, secret redaction)

### 🔄 Fase atual — Shadow validation + Wave 2 prep (Maio-Jul 2026)

**Goal:** Validar SPO + Focus 7d shadow → activate gates 2026-05-09 (routine automática); R02 paper v2 finalize.

### ✅ Wave 2 — Eval + Impact CLI (~~Jun-Jul 2026~~ ANTECIPADA 2026-05-03)

**Goal antigo:** Baseline cientifico de busca + ferramentas de impact analysis.
**Status:** ✅ DONE inteira em 2026-05-03 (E06+E07+E08+E10 dry-run+R01b 50/50+R01c definitivo)

### 📋 Wave 3 — Paper + Fase Cognitiva (Ago 2026)

**Goal:** Documentar evolucao via paper academico + features cognitivas avancadas.

**Sera feito:**
- **R02 Paper v2 finalize** (~3h restantes) — draft inicial em `paper/paper-v2-draft-evidence.md` (7 sections, 6 quantitative tables, 4 open questions); precisa caveats n=1 + golden bias acknowledgment per critic
- **E09 A-MEM auto-keywords/links** (5-6h, candidate, gated em E05 active)

### 🚀 Productizacao + Bloco V (Set+ 2026)

**Goal:** Empacotar nox-mem como produto + features finais.

**Sera feito:**
- ✅ ~~**E11 Reflect cache** (1.5h)~~ — DONE 2026-05-03 (E11 active, exact 30× / semantic 4× speedup)
- ✅ ~~**F15b SEH proper** (2-3h)~~ — DONE 2026-05-03 (`seh-report` subcomando: 6 detector kinds + PERF_PATCH_HINTS map; não auto-aplica)
- **E10 --apply path** (1-2h) — gated R01≥0.6 + per-pair human approval pra HIGH FP names (Toto/Nox/etc protected)
- **R01c replication** (3-run mean±std + held-out subset 10 queries + Voyage comparison) — pré-requisito pra paper R02 submit
- **F15 SEH Self-Evolving Hooks** (1h) — auto-evolution de regras operacionais
- **E12 Tier 3 OCR + Fathom + Path C** (dias, opcional) — PDFs scaneados + reunioes
- **P01 NOX-Supermem productizacao** (semanas) — Fase 4b → 5 → P

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
| **F14** | DR drill trimestral — script `dr-drill.sh` + cron `0 9 1 1,4,7,10 1` instalado, RTO 5s (1+2+<1+<1) | ✅ DONE | **2026-05-01** | próxima execução auto 2026-07-06 |
| **E02 / 3 Tier 2** | Tier 2 PDFs (gap real 954, cobertura A6 = 79% / 3.541 + retry NUVIVI/CONTRATOS 23 .md +1.246 chunks) | 🔄 IN-PROGRESS | 2026-05-02 | gap residual ~728 → E12 OCR; E12 escopo expandido |
| **F10** | Observability dashboard (4 painéis IndexedDB ring buffer 7d no agent-hub-dashboard) | 🛑 DEFERRED | — | trigger: ≥2 features shadow rodando OR R01a publicar evalMetrics; user não usa agora |
| **E03a** | SPO Injection shadow (`<vault-facts>` block via KG, top-K 8) | ✅ DONE shadow | **2026-05-02** | activate gate 2026-05-09 routine automática |
| **E03b** | SPO surface activate após 7d shadow | 📋 QUEUED (auto 2026-05-09) | routine `trig_012nuCN14VwcxGLq8ERaLPCK` | 0.2h |
| **E04a** | Session Focus Boost shadow (`focus set <topic>` 1.4×/0.75×) | ✅ DONE shadow | **2026-05-02** | activate gate 2026-05-09 |
| **E04b** | Focus apply activate após 7d + delta recall ≥3% | 📋 QUEUED (auto 2026-05-09) | routine `trig_012nuCN14VwcxGLq8ERaLPCK` | 0.3h |
| **E05** | Edge typing FULL Phase 1 — relation_reason enum 7 + SPO `[reason]` annotation (schema v12) | ✅ DONE | **2026-05-02** | 544 backfilled; surface only (não ranking) |
| **B1+B2+B3** | E05 reason undercoverage fix — RELATION_TYPE_TO_REASON map + 3-path normalize + `kg-reclassify` subcomando; classification 14% → 56% | ✅ DONE | **2026-05-03** | +137 backfill zero Gemini cost |
| **E06** | `nox-mem detect-changes --since=<commit>` read-only git diff→entities (Path 1: frontmatter + Path 2: chunk evidence) | ✅ DONE | **2026-05-03** | 1498 files → 182 entities em 268ms |
| **E07** | `nox-mem impact <entity>` 1-hop blast radius com REASON_PRIORITY weights (E05) + blast_radius_score | ✅ DONE | **2026-05-03** | Toto blast=29152.1 em 1ms |
| **E08** | `nox-mem api-impact <signature>` multi-arquivo grep + import/definition/usage classification | ✅ DONE | **2026-05-03** | getDb 39 files / 157 refs em 11ms |
| **E10** | Consolidation merge candidate detection — DRY-RUN ONLY (gate D01 R01≥0.6 not yet) | 🟡 PARTIAL DONE (dry-run) | **2026-05-03** | 914 entities → 52 pairs em 134ms; 4 HIGH FP protected |
| **E11** | Reflect cache semantic — Gemini embed + cosine ≥ 0.88; exact hit 30× / semantic hit 4× speedup | ✅ DONE | **2026-05-03** | env vars `NOX_REFLECT_SEMANTIC_*` |
| **F15a** | CLI Observability — `cli_telemetry` table + Commander hooks + `cli-stats` insights (top usage / slow / dormant / errors) | ✅ DONE | **2026-05-03** | secret redaction defensiva |
| **F15b** | SEH proper — `seh-report` WoW comparison: perf_regression / error_spike / dormant / capacity / first_use / recovery + PERF_PATCH_HINTS | ✅ DONE | **2026-05-03** | cron daily 09:00 BRT + Discord alert |
| **R01a** | Eval harness skeleton (schema v11 + 3 tabelas + 6 CLI subcomandos + nDCG/MRR/Recall/Prec + endpoint /api/eval-metrics) | ✅ DONE | **2026-05-02** | run #2 baseline n=5 |
| **R01b** | Curadoria 50 golden queries — milestone fechado | ✅ DONE 50/50 | **2026-05-03** | 8 categorias mistas, 12% negative cases |
| **R01c** | Baseline FTS vs Hybrid n=50 — Run #9 hybrid 0.519 / FTS 0.012; gap 97.7% loss confirma necessidade arquitetural | ✅ DONE | **2026-05-03** | trigger D01 reranker NÃO dispara (<0.6) |
| **R01c-rep** | R01c replication 3-run mean±std + held-out 10 queries | ✅ DONE Steps 1+2 | **2026-05-03** | system deterministic; 5/5 negatives zero hallucination |
| **R02** | Paper v2 draft 7 sections + 6 quantitative tables + 4 caveats critic (n=1, golden bias, baseline, no alt providers) | ✅ DONE draft | **2026-05-03** | `paper/paper-v2-draft-evidence.md`; Voyage Step 3 CUT |
| **E09** | A-MEM auto-keywords/links no ingest (funde Fase 1.7b dormente) | 🤔 CANDIDATE Ago | E05 active obrigatorio | 5-6h |
| **E10b** | Consolidation `--apply` path — gated R01≥0.6 + per-pair human approval pra HIGH FP | 🟣 BLOCKED | aguarda R01c ≥ 0.6 | 1-2h |
| **E12 / 3 Tier 3** | Tier 3 OCR — escopo expandido inclui ~728 PDFs gap E02 + Fathom + Path C | 📋 QUEUED | post-E02 | dias |
| **3 Tier 3** | OCR Gemini PDFs scaneados (opcional) | 🔒 OPCIONAL | — | dias |
| **3.5** | Fathom API (opcional, paralela) | 🔒 OPCIONAL | — | 3-4h |
| **Path C** | WAL shipping + cold tier | 🔒 BLOCKED | depende Fase 4 estavel 30d | dias |
| **4b/5** | Obsidian write + bidirectional | 🔒 FUTURO | depende Fase 4 + 2-4 sem | semanas |
| **P01 / Fase P** | Productizacao NOX-Supermem (Fase 4b → 5 → P) | 🔒 HORIZONTE 60d+ | depende Fase 4 estavel 30d (>= 05-26) | semanas |

**Legenda:** ✅ DONE / 🔄 IN-PROGRESS / 🤔 SPEC READY (impl pendente) / 📋 QUEUED / 🟣 WAVE FUTURA (gated por metricas) / 🤔 CANDIDATE (POC + 7d shadow) / 🔒 BLOCKED ou FUTURO / ❌ CUT

**Sistema unificado de IDs F/E/R/P/G/D** substitui 6+ namespaces antigos (A/B/W/Q/Fase/Phase). Cross-ref completo em [`docs/ROADMAP.md §8`](docs/ROADMAP.md). Items DEFERRED/CUT (D01-D21) em [`docs/ROADMAP.md §4`](docs/ROADMAP.md#4-tabela-mestre-cronologica).

### Capacity overview (atualizado 2026-05-03)

```
Disponivel 04-27 → 09-30:    ~22 semanas × 6h/sem = 132h
Margem incident:             -20h reservadas (4 incidents em 2 dias 04-25/26)
Capacity liquida:            ~112h
Consumido até 2026-05-03:    ~31h (Wave 1+2 + R02 paper drafts + 4 sessões intensas)
Wave 1+2 estimado:            22h estimado → 7h real (3.5× faster — sprint Maio 03)
Wave 3 (paper R02 publish):    ~3h restantes (caveats já aplicados)
Candidates (E09, E10b apply): 8-10h (gated)
Bloco V (Set+):               dias-semanas E12/P01
Sobra realista:               ~70h (4× margin original) — folga pra incidents Maio-Set
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

- **[nox-supermem](https://github.com/totobusnello/nox-supermem)** (privado) — produto PT-BR baseado no nox-mem. Em desenvolvimento apos Fase 4 estavel 30 dias.
- **[agent-hub-dashboard](https://github.com/totobusnello/agent-hub-dashboard)** — dashboard UI com 4 paginas nox-mem (chunks, KG, search telemetry, health).

---

## Licenca

MIT — veja [LICENSE](LICENSE).

---

## Agradecimentos

Construido por [Toto Busnello](https://github.com/totobusnello). Powered by [Claude](https://anthropic.com) (Anthropic). Usa [OpenClaw](https://openclaw.dev), [sqlite-vec](https://github.com/asg017/sqlite-vec) e Gemini (Google DeepMind).
