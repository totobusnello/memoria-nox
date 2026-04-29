# nox-mem — Architecture Reference

> **Versão:** 2026-04-27  
> **Sistema:** nox-mem v3.7+ | Schema v10 | OpenClaw v2026.4.23  
> **Status prod:** 20.831 chunks, 99.2% embedded, 318 MB, 6 personas + main

---

## Índice

1. [Overview](#1-overview)
2. [Data Model](#2-data-model)
3. [Ingest Pipeline](#3-ingest-pipeline)
4. [Search Pipeline](#4-search-pipeline)
5. [Knowledge Graph Layer](#5-knowledge-graph-layer)
6. [API Surfaces](#6-api-surfaces)
7. [Operational Architecture](#7-operational-architecture)
8. [Performance Characteristics](#8-performance-characteristics)
9. [External Integrations](#9-external-integrations)
10. [Future Architecture](#10-future-architecture)

---

## 1. Overview

nox-mem é o sistema de memória persistente do segundo cérebro do Toto Busnello. Qualquer documento, decisão, lição ou conversa produzida por qualquer agente OpenClaw vira conhecimento consultável em segundos. O sistema combina busca textual (FTS5 BM25), busca semântica vetorial (Gemini embeddings 3072d) e um grafo de conhecimento derivado (KG extraído por Gemini 2.5 Flash) sobre um único banco SQLite por agente. A camada de segurança protege operações destrutivas com snapshot atômico, audit log append-only e cinco camadas de invariants.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          nox-mem — visão geral                           │
│                                                                          │
│   FONTES DE INGEST                                                       │
│   ─────────────────                                                      │
│   Obsidian vault ──┐                                                     │
│   HD Mac (rsync)   ├──► nox-mem-watcher ──┐                             │
│   Repos GitHub  ───┘    (inotifywait 15s) │                             │
│                                           │                             │
│   graphify AST ─────────────────────────┐ │                             │
│   CLI manual    ─────────────────────── ┴─┴──► routeIngest()            │
│   MCP ingest    ──────────────────────────────► (ingest-router.ts)      │
│                                                      │                  │
│                                    ┌─────────────────┤                  │
│                                    │                 │                  │
│                             ingestFile()     ingestEntityFile()         │
│                             (markdown)       (3-section: compiled       │
│                                              frontmatter + timeline)    │
│                                    │                 │                  │
│                                    └────────┬────────┘                  │
│                                             ▼                           │
│                              ┌──────────────────────────┐               │
│                              │   SQLite — nox-mem.db    │               │
│                              │                          │               │
│                              │  chunks (canônico)       │               │
│                              │  chunks_fts  (FTS5)      │               │
│                              │  vec_chunks  (3072d)     │               │
│                              │  vec_chunk_map           │               │
│                              │  kg_entities             │               │
│                              │  kg_relations            │               │
│                              │  ops_audit  (append-only)│               │
│                              │  search_telemetry        │               │
│                              └──────────┬───────────────┘               │
│                                         │                               │
│   QUERY SURFACES                        │                               │
│   ──────────────                        ▼                               │
│                              ┌──────────────────────────┐               │
│   CLI (26+ cmds) ──────────► │   Hybrid Search Engine   │               │
│   MCP (16 tools) ──────────► │   FTS5 BM25              │               │
│   HTTP API :18802 ─────────► │   Gemini semantic        │               │
│   Dashboard ───────────────► │   RRF fusion (k=60)      │               │
│                              │   MMR + decay + salience │               │
│                              └──────────────────────────┘               │
│                                                                          │
│   MANUTENÇÃO                                                             │
│   ──────────                                                             │
│   nightly cron 23:00 BRT ──► reindex → consolidate → vectorize          │
│                                       → kg-build → kg-prune             │
│                                       → session-distill                 │
│   canary */30min  ──────────► semantic smoke test → Discord             │
│   invariants */15min  ──────► 5 invariants → Discord se falhar          │
│   health-probe */5min ──────► /api/health endpoint                      │
│   backup 02:00 BRT    ──────► VACUUM INTO 7d retention                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Model

### 2.1 Schema geral

A tabela `chunks` é a única fonte canônica de verdade. Todas as outras tabelas são satélites derivados ou auxiliares — nenhuma é fonte primária independente.

```
┌───────────────────────────────────────────────────────────────────┐
│                         nox-mem.db schema v10                     │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ chunks  (tabela canônica)                                │     │
│  │──────────────────────────────────────────────────────────│     │
│  │ id            INTEGER  PRIMARY KEY                       │     │
│  │ source_file   TEXT                                       │     │
│  │ chunk_index   INTEGER                                    │     │
│  │ content       TEXT                                       │     │
│  │ chunk_type    TEXT                                       │     │
│  │ metadata_json TEXT                                       │     │
│  │ created_at    DATETIME                                   │     │
│  │ updated_at    DATETIME                                   │     │
│  │ retention_days INTEGER   (v8 — NULL = never-decay)       │     │
│  │ pain          REAL       (v9 — 0.1 trivial..1.0 outage)  │     │
│  │ section       TEXT       (v10 — compiled/frontmatter/    │     │
│  │                                  timeline/NULL)          │     │
│  │ section_boost REAL       (v10 — 2.0/1.5/0.8/1.0)        │     │
│  └─────────────────┬────────────────────────────────────────┘     │
│                    │ mirrors                                       │
│           ┌────────┴─────────────────────────┐                    │
│           │                                  │                    │
│  ┌────────▼──────────┐           ┌───────────▼────────────┐       │
│  │ chunks_fts (FTS5) │           │ vec_chunks (sqlite-vec)│       │
│  │───────────────────│           │────────────────────────│       │
│  │ content           │           │ chunk_id  → chunks.id  │       │
│  │ chunk_type        │           │ embedding FLOAT[3072]  │       │
│  │ source_file       │           └────────────────────────┘       │
│  └───────────────────┘                       │                    │
│                                   ┌──────────▼──────────┐         │
│                                   │ vec_chunk_map        │         │
│                                   │─────────────────────│         │
│                                   │ chunk_id  → chunks  │         │
│                                   │ vec_id    → vec_row │         │
│                                   └─────────────────────┘         │
│                                                                   │
│  ┌──────────────────────────┐     ┌───────────────────────────┐   │
│  │ kg_entities (derivado)   │     │ kg_relations (derivado)   │   │
│  │──────────────────────────│     │───────────────────────────│   │
│  │ id, name, type           │◄────┤ from_entity_id            │   │
│  │ description              │     │ to_entity_id              │   │
│  │ properties_json          │     │ relation_type             │   │
│  │ confidence               │ ────► relation_reason (enum 7) │   │
│  └──────────────────────────┘     │ confidence, evidence_text │   │
│                                   └───────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │ ops_audit  (append-only via 2 triggers SQL)               │    │
│  │───────────────────────────────────────────────────────────│    │
│  │ id, op_type, status, started_at, finished_at              │    │
│  │ snapshot_path, affected_rows, error_msg                   │    │
│  │ trg_no_delete: DELETE → ABORT                             │    │
│  │ trg_terminal_immutable: UPDATE status terminal → ABORT    │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │ search_telemetry  (A0 — query logging)                    │    │
│  │───────────────────────────────────────────────────────────│    │
│  │ id, query_text*, golden_id*, top_chunk_ids*, top_scores*  │    │
│  │ (* opt-in via NOX_SEARCH_LOG_TEXT=1)                      │    │
│  │ search_type, latency_ms, result_count, created_at         │    │
│  └───────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 Trigger cascade

```
DELETE em chunks
    │
    ├──► trg_chunks_delete_cascade
    │    ├── DELETE vec_chunks WHERE chunk_id = OLD.id
    │    └── DELETE vec_chunk_map WHERE chunk_id = OLD.id
    │
    └──► (FTS5 atualiza automaticamente via tabela virtual)
```

### 2.3 Tipagem de retention

| chunk_type | retention_days | Razão |
|---|---|---|
| `feedback`, `person` | NULL (never-decay) | Conhecimento permanente |
| `lesson` | 180d | Lições aprendidas |
| `decision`, `project` | 365d | Decisões e projetos ativos |
| `team` | 120d | Contexto de time |
| `daily`, `default` | 90d | Notas diárias |
| `pending` | 30d | Items temporários |
| `graph_node` | 60d | Nós de grafo derivados |

Override via HTML comment isolado no frontmatter: `<!-- retention: 365 -->`

### 2.4 Distribuição de pain (backfill heurístico)

| Valor | Semântica | Chunks |
|---|---|---|
| 1.0 | crash/outage/rollback | 256 |
| 0.8 | lesson explícita | 43 |
| 0.5 | bug/error | 469 |
| 0.3 | warn/deprecation | 105 |
| 0.2 | default | 6.474 |

### 2.5 Section boost multipliers

| section | section_boost | Semântica |
|---|---|---|
| `compiled` | 2.0 | Verdade destilada (entity format) |
| `frontmatter` | 1.5 | Metadados estruturados |
| `timeline` | 0.8 | Histórico temporal |
| NULL / `legacy` | 1.0 | Chunks genéricos |

### 2.6 Histórico de migrations (v1 → v10)

As migrations seguem padrão aditivo: `ALTER TABLE ADD COLUMN` + backfill heurístico. DROP/recreate nunca foi usado.

| Versão | Mudança principal |
|---|---|
| v1–v3 | Schema inicial (chunks + FTS5) |
| v4 | Embeddings SQLite-vec (vec_chunks + vec_chunk_map) |
| v5 | Knowledge graph (kg_entities + kg_relations) |
| v6 | search_telemetry (logging básico) |
| v7 | Trigger trg_chunks_delete_cascade |
| **v8** | `retention_days` INTEGER nullable (never-decay para feedback/person) |
| **v9** | `pain` REAL DEFAULT 0.2 (Affective Ranking) |
| **v10** | `section` TEXT + `section_boost` REAL (entity 3-section format) |

Detalhes de cada versão: `docs/EVOLUTION.md`.

### 2.7 Schema invariants ativos (canary */15min)

1. `chunks.section NOT NULL` nas 183 entity files (compiled/frontmatter/timeline)
2. Todos os chunks `chunk_type IN ('feedback','person')` têm `retention_days IS NULL`
3. Nenhuma row em `ops_audit` com status terminal foi editada (trigger integrity)
4. `section_boost` consistente com `section` (compiled=2.0, frontmatter=1.5, timeline=0.8)
5. `vec_chunks` count ≥ 99% de `chunks` count (cobertura vetorial)

Violação de qualquer invariant dispara alerta no Discord imediatamente.

---

## 3. Ingest Pipeline

### 3.1 Fontes de ingest

```
┌─────────────────────────────────────────────────────────────────┐
│                      fontes de ingest                           │
│                                                                 │
│  ┌──────────────────┐   rsync Tailscale     ┌────────────────┐  │
│  │   HD Mac local   │ ──────────────────►   │  /root/vault/  │  │
│  │  .md / .docx     │                       │  documentos/   │  │
│  └──────────────────┘                       └───────┬────────┘  │
│                                                     │           │
│  ┌──────────────────┐   git pull            ┌───────▼────────┐  │
│  │  Repos GitHub    │ ──────────────────►   │  /root/vault/  │  │
│  │  (9 repos code)  │                       │  projetos/     │  │
│  └──────────────────┘                       └───────┬────────┘  │
│                                                     │           │
│  ┌──────────────────┐                       ┌───────▼────────┐  │
│  │  Obsidian vault  │ ──── view-only ────►  │  exportada     │  │
│  │  (Mac local)     │      (Fase 4)         │  cron 02:30    │  │
│  └──────────────────┘                       └───────┬────────┘  │
│                                                     │           │
│  ┌────────────────────────────────────────────────┐ │           │
│  │ nox-mem-watcher (inotifywait, debounce 15s)    │◄┘           │
│  │ monitora /root/.openclaw/workspace/memory/      │            │
│  └──────────────────────────┬───────────────────┬─┘            │
│                             │                   │              │
│  ┌──────────────────┐       │     ┌─────────────▼────────────┐ │
│  │ graphify AST     │       │     │   routeIngest()           │ │
│  │ (cache JSON)     │───────┼────►│   src/lib/ingest-router.ts│ │
│  └──────────────────┘       │     └─────────────┬────────────┘ │
│                             │                   │              │
│  ┌──────────────────┐       │                   │              │
│  │ CLI manual       │───────┘                   │              │
│  │ MCP ingest call  │                           │              │
│  └──────────────────┘                           │              │
└────────────────────────────────────────────────┼──────────────┘
                                                  │
                          ┌───────────────────────┤
                          │                       │
              ┌───────────▼───────┐  ┌────────────▼──────────────┐
              │  ingestFile()     │  │  ingestEntityFile()        │
              │  (markdown genérico│  │  (entity 3-section format) │
              │   + graphify nodes│  │  produz N+2 chunks com     │
              │   + daily notes)  │  │  section_boost aplicado)   │
              └───────────┬───────┘  └────────────┬──────────────┘
                          │                       │
                          └──────────┬────────────┘
                                     │
                         ┌───────────▼────────────────────────┐
                         │ auto-vectorize (Gemini API inline)  │
                         │ auto-KG-extract (Gemini 2.5 Flash)  │
                         └────────────────────────────────────┘
```

### 3.2 routeIngest() — lógica de dispatch

`src/lib/ingest-router.ts` é o único ponto de entrada para qualquer operação de ingest. A lógica de roteamento é:

```
routeIngest(filePath, options)
    │
    ├── filePath matches memory/entities/<type>/<slug>.md ?
    │       └── YES → ingestEntityFile() [3-section parse]
    │
    ├── filePath has graphify marker in content ?
    │       └── YES → ingestGraphifyNode() [graph_node chunks]
    │
    └── DEFAULT → ingestFile() [markdown chunks]
              │
              └── guard no topo: se filePath bater com entity pattern
                  → redireciona para ingestEntityFile() (defesa em camadas)
```

Todos os callers (watcher, reindex, CLI, MCP) usam `routeIngest()`. O guard interno em `ingestFile()` é defesa secundária, não ponto de entrada.

### 3.3 Entity 3-section format

Arquivos em `memory/entities/<type>/<slug>.md` seguem um formato de 3 seções que produz chunks diferenciados:

```
memory/entities/<type>/<slug>.md
─────────────────────────────────────────

## Frontmatter (section=frontmatter, boost=1.5)
---
name: <Nome da entidade>
type: <agent|system|project|decision|lesson>
tags: [...]
<!-- retention: 365 -->
---

## Compiled Truth (section=compiled, boost=2.0)
> Seção destilada — verdade atual, sem histórico
> Produz 1+ chunk(s) com máximo boost de ranking

<conteúdo destilado>

## Timeline (section=timeline, boost=0.8)
> Histórico cronológico de eventos
> Produz N chunks com boost reduzido (passado, não presente)

- 2026-04-01: evento
- 2026-04-15: outro evento
```

`ingestEntityFile()` produz exatamente N+2 chunks por entidade: 1 frontmatter + N compiled chunks + M timeline chunks.

### 3.4 Sequência de ingest (diagrama)

```
CLI: nox-mem ingest-entity memory/entities/systems/nox-mem.md
            │
            ▼
    dist/index.js  (entry point — não cli.js)
            │
            ▼
    routeIngest(filePath)
            │ detecta padrão entity
            ▼
    ingestEntityFile(filePath)
            │
            ├── parse frontmatter → chunk (section=frontmatter)
            ├── parse ## Compiled Truth → chunk(s) (section=compiled)
            └── parse ## Timeline → chunk(s) (section=timeline)
                    │
                    ▼
            INSERT OR REPLACE INTO chunks
                    │
                    ├──► chunks_fts (FTS5 virtual table — automático)
                    │
                    └──► auto-vectorize inline
                              │
                              ├── Gemini API: embedContent(content)
                              │   model: gemini-embedding-001
                              │   output: Float32Array[3072]
                              │
                              └── INSERT INTO vec_chunks
                                  INSERT INTO vec_chunk_map
                                          │
                                          ▼
                                  ops_audit: status=success
                                  (se wrapped por withOpAudit)
```

---

## 4. Search Pipeline

### 4.1 Arquitetura híbrida em camadas

O search pipeline tem 7 estágios sequenciais. Cada estágio recebe a lista de candidatos do anterior e a refina.

```
query string
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ESTÁGIO 1 — FTS5 BM25 (lexical)                                │
│  Input:  query string                                           │
│  Engine: SQLite FTS5 + BM25 ranking                             │
│  Output: top-K chunks por score textual + rank BM25             │
│  Quando falha silenciosamente: never (determinístico)           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 2 — Gemini Semantic (vetorial)                         │
│  Input:  query string                                           │
│  Engine: Gemini embedContent (3072d) → cosine similarity        │
│          sqlite-vec KNN search                                  │
│  Output: top-K chunks por score semântico + cosine distance     │
│  Canário */30min verifica que este estágio retorna resultados   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 3 — RRF Fusion (Reciprocal Rank Fusion)                │
│  Input:  rank lists de FTS5 + rank list de semantic             │
│  Engine: RRF(k=60): score = Σ 1/(k + rank_i)                   │
│  Output: lista unificada com score RRF                          │
│  Por que RRF: não requer calibração de escala entre BM25/cosine │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 4 — MMR (Maximal Marginal Relevance)                   │
│  Input:  lista RRF                                              │
│  Engine: λ=0.7 — balancea relevância vs diversidade            │
│  Output: lista re-rankeada com diversidade temática             │
│  Objetivo: evitar top-K repetindo o mesmo chunk em variações   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 5 — Temporal Decay                                     │
│  Input:  lista MMR                                              │
│  Engine: half-life 30d: decay = exp(-age_days / 30)            │
│  Output: scores ajustados por freshness                         │
│  Objetivo: chunks recentes recebem boost relativo              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 6 — Salience Boost (shadow-mode até 2026-04-30)        │
│  Input:  lista pós-decay                                        │
│  Engine: salience = recency × pain × importance                 │
│          NOX_SALIENCE_MODE=shadow: calcula mas NÃO aplica       │
│          NOX_SALIENCE_MODE=active: aplica multiplicador         │
│  Output: scores com salience (shadow: apenas telemetria)        │
│  Gate:   04-30 — ativação se baseline 7d OK                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ESTÁGIO 7 — Section Boost (shadow-mode até 2026-05-01)         │
│  Input:  lista pós-salience                                     │
│  Engine: score × section_boost                                  │
│          compiled=2.0, frontmatter=1.5, timeline=0.8, rest=1.0  │
│          NOX_SECTION_BOOST_MODE=shadow: calcula mas NÃO aplica  │
│  Output: lista final rankeada                                   │
│  Gate:   05-01 — ativação após analyze-shadow-telemetry.sh      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
              resultados finais com scores + metadata
```

### 4.2 Shadow-mode mechanics

Ambos salience e section_boost seguem o mesmo padrão antes de ativação em produção:

1. Feature computada a cada query (sem custo adicional de runtime)
2. Resultado armazenado em `search_telemetry` para análise
3. Ranking efetivo NÃO modificado (usuário não sente mudança)
4. Telemetria acumula por ≥7d para baseline estatístico
5. Script de análise (`analyze-shadow-telemetry.sh`) avalia impacto
6. Gate manual: operador decide ativar com `--apply`

Nenhuma mudança de ranking entra em produção sem shadow-mode de pelo menos 7 dias. Violação desta regra causou o incident v3.4.

### 4.3 Cross-agent search

O cross-agent search une os resultados de múltiplos bancos de agentes via RRF adicional:

```
nox-mem cross-search "query" --agents nox,atlas,forge
    │
    ├── search(nox-mem.db)     → results_nox
    ├── search(atlas-mem.db)   → results_atlas
    └── search(forge-mem.db)   → results_forge
              │
              ▼
        RRF merge (k=60) dos 3 rank lists
              │
              ▼
        resultados cross-agent rankeados com agent_id annotated
```

Cada agente tem DB isolado em `/root/.openclaw/workspace/agents/<X>/data/nox-mem.db`. O workspace DB (main) é o mais completo — todos os agentes leem ele. Os DBs de agente congelaram em 2026-04-21 para suportar a feature `cross-*`.

### 4.4 Canário semântico

Um job `*/30min` executa uma query sintética conhecida e valida que:
- Pelo menos 1 resultado com `match_type = "semantic"` retorna
- Score cosine acima de threshold mínimo

Se falhar, `semantic-canary.sh` tenta auto-recovery (re-vectorize do chunk canário) e notifica Discord.

---

## 5. Knowledge Graph Layer

### 5.1 Extração via Gemini

O KG é derivado do corpus de chunks via Gemini 2.5 Flash. Não é uma fonte primária — é um índice de relacionamentos extraídos.

```
corpus chunks
    │
    ▼
nox-mem kg-build
    │
    ├── seleciona chunks sem KG coverage (ou desatualizados)
    │
    ├── agrupa por source_file (contexto)
    │
    └── Gemini 2.5 Flash
            input: chunk content + system prompt (extraction schema)
            output: [{entity, type, description}, ...],
                    [{from, to, relation_type, relation_reason,
                      confidence, evidence_text}, ...]
                │
                ▼
        UPSERT kg_entities
        UPSERT kg_relations
            │
            ▼
        nox-mem kg-prune (nightly)
            remove entidades com confidence < threshold
            remove relações órfãs
```

### 5.2 Vocabulário relation_reason (enum fechado — 7 valores)

O vocabulário é intencionalmente fechado e nunca extendido via free-form. Extensão ad-hoc criaria indexação não-estruturada equivalente a Text2Cypher, que foi explicitamente rejeitado (DECISIONS.md §1 item 11).

| relation_reason | Semântica |
|---|---|
| `mentions` | Referência simples |
| `owns` | Posse / responsabilidade |
| `decides` | Decisão tomada sobre |
| `depends` | Dependência funcional |
| `derives_from` | Derivado de / baseado em |
| `contradicts` | Contradiz / invalida |
| `supersedes` | Substitui / depreca |

A coluna `confidence` (REAL 0.0-1.0) e o gate de threshold para kg-prune são implementados — o threshold específico de pruning é configurável.

### 5.3 Por que SQLite, não graph database

A decisão de usar SQLite em vez de Memgraph/Neo4j é documentada em `docs/DECISIONS.md §1 item 9`. Resumo:

- **Volume atual**: ~402 entities, ~544 relations — trivial para SQLite
- **Threshold**: graph DB se justifica em >500K entities
- **Overhead**: Memgraph/Neo4j adicionariam daemon + backup complexo + curva de manutenção
- **Query pattern**: BFS (`kg-path`) implementado em SQLite CTE recursivo com performance adequada (<100ms p95)
- **Stack lean**: TypeScript + SQLite + Gemini API é o princípio arquitetural

### 5.4 KG paths e queries

```bash
# BFS entre duas entidades
nox-mem kg-path "nox-mem" "OpenClaw"

# Query por entidade
nox-mem kg-query "entity:nox-mem"

# HTTP API equivalente
GET /api/kg?entity=nox-mem
GET /api/kg/path?from=nox-mem&to=OpenClaw
```

---

## 6. API Surfaces

### 6.1 CLI — commander.js

Entry point canônico: `dist/index.js` (via `package.json#bin`). Confusão comum: `cli.js` existe mas não é o entry point.

```
nox-mem <command> [options]

Ingest:
  ingest <file>              ingesta arquivo markdown genérico
  ingest-entity <file>       ingesta entity 3-section format
  reindex [--dry-run]        re-processa todos os chunks
  consolidate [--dry-run]    dedup + cleanup

Search:
  search <query>             hybrid search (FTS5 + semantic + RRF)
  cross-search <query>       search em múltiplos DBs de agentes

Vectorize:
  vectorize [--all]          gera/atualiza embeddings

Knowledge Graph:
  kg-build                   extrai entities + relations via Gemini
  kg-prune                   remove KG com confidence baixa
  kg-query <entity>          busca no grafo
  kg-path <from> <to>        caminho BFS entre entidades

Memory operations:
  reflect                    síntese KG via Gemini
  crystallize                procedures → chunks pesquisáveis
  compact [--dry-run]        compacta DB (VACUUM)

Cross-agent:
  cross-search <query>       busca cross-agente
  cross-stats                stats de todos os agentes
  cross-kg                   KG unificado cross-agente

Admin:
  stats                      estatísticas do banco
  health                     validação de integridade
  session-distill            destila sessões para memória permanente
```

Opções globais relevantes:
- `--dry-run`: produz JSON preview sem mutar o DB (obrigatório em ops destrutivas)
- `--no-hybrid`: força FTS5-only (sem chamadas à API Gemini)
- `--agents <list>`: especifica agentes para operações cross-*

### 6.2 MCP Server — JSON-RPC 2.0 stdio

16 tools expostos via protocolo MCP (stdio transport). O limite de 16 é uma decisão arquitetural explícita — capabilities crescem via qualidade de search, não via proliferação de tools.

```
Tool list (16):

nox_mem_search          busca híbrida
nox_mem_ingest          ingesta content inline
nox_mem_ingest_entity   ingesta entity 3-section
nox_mem_reindex         re-indexa (dry-run por default via MCP)
nox_mem_stats           estatísticas
nox_mem_health          health check
nox_mem_kg_build        constrói KG
nox_mem_kg_query        busca no KG
nox_mem_kg_path         BFS path
nox_mem_cross_search    cross-agente search
nox_mem_cross_stats     cross-agente stats
nox_mem_cross_kg        cross-agente KG
nox_mem_reflect         síntese KG
nox_mem_crystallize     procedures → memória
nox_mem_session_distill destila sessão atual
nox_mem_vectorize       força re-vectorize
```

O MCP server roda como processo separado comunicando via stdin/stdout JSON-RPC 2.0. É o canal primário pelos agentes OpenClaw.

### 6.3 HTTP API — Express.js

Porta `18802` (via env `NOX_API_PORT` — nunca hardcoded). Outputs formatados para consumo via `jq`.

```
GET  /api/health               estado completo (chunks, vectors, KG, ops_audit)
GET  /api/search?q=<query>     hybrid search
GET  /api/kg?entity=<name>     knowledge graph por entidade
GET  /api/kg/path?from=&to=    BFS path no KG
GET  /api/agents               lista de agentes e DBs
GET  /api/cross-kg             KG unificado cross-agente
GET  /api/reflect              síntese KG recente
GET  /api/procedures           crystallized procedures pesquisáveis

POST /api/crystallize          converte procedure para chunks pesquisáveis
POST /api/crystallize/validate validação sem persistência (dry-run HTTP)
```

`/api/health` é o endpoint mais importante operacionalmente:

```json
{
  "chunks": { "total": 20831, "byType": {...} },
  "vectorCoverage": { "embedded": 20662, "total": 20831 },
  "sectionDistribution": { "compiled": 183, "frontmatter": 183, "timeline": 366 },
  "salience": { "mode": "shadow", "promoteCount": 207, "archiveCount": 1886 },
  "opsAudit": { "last24h": 1, "pendingOps": 0 },
  "dbSizeMB": 318,
  "kgStats": { "entities": 402, "relations": 544 }
}
```

### 6.4 Dashboard

`github.com/totobusnello/agent-hub-dashboard` (repositório separado). 4 páginas dedicadas ao nox-mem:

- **Overview**: chunks totais, coverage vetorial, KG stats
- **Search**: interface de busca com highlight
- **Knowledge Graph**: visualização das entities/relations
- **Agents**: cross-agent stats e health por agente

O dashboard consome exclusivamente a HTTP API do nox-mem. Não acessa o SQLite diretamente.

---

## 7. Operational Architecture

### 7.1 As 5 camadas de segurança

```
┌──────────────────────────────────────────────────────────────────────┐
│                     5 safety layers (defesa em profundidade)         │
│                                                                      │
│  L5 ┌────────────────────────────────────────────────────────────┐  │
│     │ safeRestore() + reaper PID-aware @6h + early-zombie @60min │  │
│     │ Recovery de snapshot: valida user_version match, restaura  │  │
│     │ main DB, remove WAL/SHM órfãos. NUNCA cp direto.          │  │
│     └────────────────────────────────────────────────────────────┘  │
│  L4 ┌────────────────────────────────────────────────────────────┐  │
│     │ --dry-run mode em ops destrutivas                          │  │
│     │ reindex/consolidate: produz JSON preview com               │  │
│     │ wouldDelete/wouldProcess/protected/estimatedDuration       │  │
│     │ sem mutar o DB.                                            │  │
│     └────────────────────────────────────────────────────────────┘  │
│  L3 ┌────────────────────────────────────────────────────────────┐  │
│     │ withOpAudit() wrapper (src/lib/op-audit.ts)                │  │
│     │ 1. VACUUM INTO snapshot atômico                            │  │
│     │    path: /var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>│  │
│     │    ACL: 0600 arquivo, 0700 diretório                       │  │
│     │    validation: realpathSync (symlink-aware, TOCTOU)        │  │
│     │    free space: statfsSync ≥ 2× DB antes de VACUUM         │  │
│     │ 2. Registra início em ops_audit (status=started)           │  │
│     │ 3. Executa operação                                        │  │
│     │ 4. Atualiza ops_audit (status=success/failed/crashed)      │  │
│     │ 5. reapZombies() no preAction hook                         │  │
│     └────────────────────────────────────────────────────────────┘  │
│  L2 ┌────────────────────────────────────────────────────────────┐  │
│     │ ops_audit append-only (SQL triggers — CWE-693)             │  │
│     │ trg_ops_audit_no_delete: DELETE → ABORT                    │  │
│     │ trg_ops_audit_terminal_immutable: UPDATE em success/       │  │
│     │   failed/crashed → ABORT                                   │  │
│     └────────────────────────────────────────────────────────────┘  │
│  L1 ┌────────────────────────────────────────────────────────────┐  │
│     │ Schema invariants canary */15min                           │  │
│     │ check-schema-invariants.sh: 5 invariants (ver §2.7)        │  │
│     │ Alerta Discord imediato se qualquer invariant falhar       │  │
│     └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 ops_audit triggers (detalhado)

```sql
-- L2: impede DELETE em qualquer row do audit log
CREATE TRIGGER trg_ops_audit_no_delete
BEFORE DELETE ON ops_audit
BEGIN
    SELECT RAISE(ABORT, 'ops_audit is append-only: DELETE blocked');
END;

-- L2: impede UPDATE de status terminal (imutabilidade de conclusões)
CREATE TRIGGER trg_ops_audit_terminal_immutable
BEFORE UPDATE OF status ON ops_audit
WHEN OLD.status IN ('success', 'failed', 'crashed')
BEGIN
    SELECT RAISE(ABORT, 'ops_audit terminal status is immutable');
END;
-- Status enum válido: 'started' (inicial), 'success' (terminal OK), 'failed' (terminal erro app), 'crashed' (terminal erro sistema)
```

Ops destrutivas sem wrapper: usar `NOX_ALLOW_NO_SNAPSHOT=1` **somente** em emergência com motivo legítimo documentado (ex: disk full + reindex urgente). Nunca como atalho rotineiro.

### 7.3 Loop de manutenção noturna

```
23:00 BRT — nightly-maintenance.sh
│
├── Phase 1: reindex (via routeIngest — entity files roteadas corretamente)
├── Phase 2: consolidate (dedup + cleanup)
├── Phase 3: vectorize (preenche gaps de embedding)
├── Phase 4: kg-build (extração incremental de entities/relations)
├── Phase 5: kg-prune (remove KG de baixa confiança)
├── Phase 6: session-distill (transforma sessões em memória permanente)
└── Phase 7: WAL checkpoint TRUNCATE (libera espaço)

02:00 BRT — backup-all.sh
└── VACUUM INTO /var/backups/nox-mem/daily/<date>.db (retention 7d)

02:30 BRT — export-obsidian-vault.py (VPS)
└── gera /root/ObsidianVault-build/ (199 .md files)

03:00 BRT — launchd Mac
└── rsync Tailscale: VPS → Mac vault (com excludes de customizações locais)

*/5min — health-probe
└── curl /api/health → verifica que serviço responde

*/15min — check-schema-invariants.sh
└── 5 invariants → Discord se falhar

*/30min — semantic-canary.sh
└── query sintética → valida match_type=semantic → Discord se falhar

06:30 BRT — morning-report.sh
└── resumo diário via Discord (chunks, vectors, KG stats)
```

Nota: `nightly-maintenance.sh` usa `withOpAudit()` em operações destrutivas. O cron OpenClaw `end-of-day` (22:00 BRT) foi editado em 2026-04-25 para usar `consolidate` em vez de `reindex` — patch pós-incident para evitar wipe de section/retention.

### 7.4 Sistema de upgrade defense (2026-04-26)

Construído após o incident OpenClaw .24 (bug #71957):

```
/root/bin/ckpt        — checkpoint de estado pré-upgrade
/root/bin/improvements — 13 invariants de produção (check/audit)
/root/.openclaw/upgrade-watcher/  — monitora releases OpenClaw
/root/oc-upgrade <version>        — orchestrator completo com:
    ├── pre-flight: improvements check (todos 13 OK)
    ├── ckpt save pré-upgrade
    ├── backup do DB
    ├── instala nova versão
    ├── reapply monkey-patch #62028
    ├── restart + health-check
    └── auto-rollback se gateway não estabilizar em 30s
```

Invariants do `improvements check` (13 total):
- 7 critical: gateway ativo, nox-mem-api ativo, monkey-patch aplicado, credentials imutáveis, env vars presentes, watcher ativo, backup recente
- 6 warn-only: KG coverage, vector coverage, ops_audit clean, log rotation, disk space, cron jobs ativos

### 7.5 Multi-agent isolation strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    topologia multi-agent                            │
│                                                                     │
│  workspace DB (main)          /root/.openclaw/workspace/data/       │
│  ─────────────────────        nox-mem.db — 20.831 chunks            │
│  LIDO POR TODOS OS 6 AGENTES  Atualizado pelo watcher + nightly     │
│                                                                     │
│  DBs isolados por agente      /root/.openclaw/workspace/agents/     │
│  ──────────────────────────── <X>/data/nox-mem.db                   │
│                                                                     │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────┐│
│  │  nox   │  │  atlas │  │  boris │  │ cipher │  │  forge │  │lex ││
│  │ opus   │  │ sonnet │  │ sonnet │  │ sonnet │  │  opus  │  │son ││
│  └────┬───┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └──┬─┘│
│       │          │           │            │            │          │  │
│       └──────────┴───────────┴────────────┴────────────┴──────────┘  │
│                                     │                               │
│                               cross-search/stats/kg                │
│                               (RRF merge dos N DBs)                 │
│                                                                     │
│  Roteamento inter-agente:                                           │
│  ─────────────────────────                                          │
│  - Via SOUL.md de cada persona (filosofia + expertise)              │
│  - sessions_send("agent:X:discord:channel:ID", "msg")              │
│  - NÃO há routing algorítmico (over-engineering pra 6 agentes)     │
│                                                                     │
│  nox + forge = claude-opus-4-6   (raciocínio complexo)             │
│  atlas + boris + cipher + lex = claude-sonnet-4-6  (operacional)   │
│  todos via claude-cli (zero custo API, OAuth Max/Pro)              │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.6 Deployment topology

```
Hostinger KVM 4 VPS — 187.77.234.79 (público) / 100.87.8.44 (Tailscale)
Ubuntu Linux — /root/.openclaw/

Serviços ativos (systemd):
┌──────────────────────────────────────────────────────────────┐
│ openclaw-gateway  :18789 WebSocket                           │
│   └── claude-cli subprocess (via anthropic-max OAuth)        │
│   └── monkey-patch Issue #62028 aplicado                     │
│   └── drop-in: Environment=IS_SANDBOX=1                      │
│                                                              │
│ nox-mem-api       :18802 HTTP                                │
│   └── Express.js + better-sqlite3                            │
│   └── porta via NOX_API_PORT (.env)                          │
│                                                              │
│ nox-mem-watcher   (inotifywait, debounce 15s)                │
│   └── monitora /root/.openclaw/workspace/memory/            │
│   └── dispara routeIngest() em mudanças                     │
│                                                              │
│ tailscaled        100.87.8.44                                │
│   └── Tailscale para acesso seguro Mac ↔ VPS                │
└──────────────────────────────────────────────────────────────┘

Serviços inativos (instalados como fallback):
│ relayplane-proxy  :4100  — substituído pelo claude-cli direto
```

Toda configuração de segredos via `/root/.openclaw/.env` (perms 0600). Nenhuma chave em hardcode — gitleaks pre-commit global bloqueia.

---

## 8. Performance Characteristics

### 8.1 Latências típicas (hot path)

| Operação | P50 | P95 | Notas |
|---|---|---|---|
| FTS5 BM25 search | <5ms | <15ms | Determinístico, sem API externa |
| Gemini embed (query) | 80-150ms | 200ms | Latência de rede + API |
| RRF fusion | <1ms | <5ms | In-process, sem I/O |
| Full hybrid search | 100-200ms | 400ms | Dominado pelo Gemini embed |
| Cross-agent search (3 DBs) | 200-400ms | 600ms | 3× overhead de query |
| KG BFS path | <10ms | 50ms | SQLite CTE recursivo |
| Ingest single file | 200-500ms | 1s | Inclui auto-vectorize inline |

SLA definido: hybrid search <2s (inclui rede VPS→Mac quando necessário). Atomic hybrid query (CTE única) foi rejeitada como otimização — p95 atual não justifica a complexidade adicionada (DECISIONS.md §1 item 13).

### 8.2 Cold start

| Componente | Tempo |
|---|---|
| nox-mem-api (Express startup) | ~800ms |
| DB open + WAL recovery | ~200ms |
| sqlite-vec extension load | ~100ms |
| Total cold start (ready to serve) | ~1.1s |

O watcher e a API são serviços long-running via systemd — cold start acontece apenas em restart.

### 8.3 Storage scaling

```
Estado atual (2026-04-27):
  DB:           318 MB
  Chunks:       20.831
  Avg chunk:    ~15 KB equivalent (texto + metadata + embedding Float32[3072])

Breakdown:
  chunks table: ~40 MB (texto puro)
  vec_chunks:   ~250 MB (20.831 × 3072 × 4 bytes = ~256 MB)
  kg + meta:    ~28 MB

Modelo de crescimento:
  Cada 1.000 novos chunks ≈ +12 MB DB
  Ponto crítico de backup: >1 GB (monitor disk space no improvements check)
  Tier 2 (4.432 PDFs): estimado +53 MB vetores ≈ 370 MB total
```

### 8.4 API rate limits (Gemini)

| Modelo | Quota | Uso atual |
|---|---|---|
| `gemini-embedding-001` | 1.500 req/min, 1M tokens/day | ~200 req/min no nightly (vectorize) |
| `gemini-2.5-flash-lite` | 3M tokens/day | Usado para heartbeats + summaries |
| `gemini-2.5-flash` | 3M tokens/day | KG extraction (leve, uso baixo atual) |

Regra crítica: NUNCA usar `gemini-2.5-flash` como default de infra — quota estoura. `gemini-2.0-flash` está deprecated (shutdown 2026-06-01). Default mandatório: `gemini-2.5-flash-lite`.

O nightly vectorize é o maior consumidor. Processamento incremental (só novos chunks) mantém o uso dentro da quota mesmo com crescimento de corpus.

---

## 9. External Integrations

### 9.1 Gemini API (Google)

Dois usos distintos com modelos diferentes:

```
Embeddings:
  model: gemini-embedding-001
  usage: ingest (inline) + query (hybrid search)
  output: Float32[3072]
  cost: gratuito até quota diária

KG Extraction:
  model: gemini-2.5-flash (enquanto volume baixo)
  usage: kg-build nightly
  input: chunk content (batched por source_file)
  output: entities[] + relations[] (JSON estruturado)
```

Configuração via env: `GEMINI_API_KEY` em `/root/.openclaw/.env`. Rotação: editar `.env` + `systemctl restart nox-mem-api nox-mem-watcher`.

### 9.2 Claude CLI subprocess (Anthropic)

O backend primário de todos os agentes OpenClaw. Zero custo de API — usa OAuth da subscription Max/Pro.

```
openclaw-gateway
    │
    └── spawn: /usr/bin/claude --print ...
                    │
                    ├── lê ~/.claude/.credentials.json
                    │   (NUNCA env var CLAUDE_CODE_OAUTH_TOKEN — conflita)
                    │   chattr +i aplicado pós-setup-token (auto-trunca sem)
                    │
                    └── anthropic-max:default profile
                        (sk-ant-oat… OAuth token, não API key paga)
```

Fallback chain por agente: `claude-cli/sonnet-4-6` → `openai-codex/gpt-5.5` → `gemini/2.5-pro`. Sem `anthropic/*` direto na chain (mascararia falha CLI e geraria cobrança pay-per-token).

### 9.3 OpenClaw gateway

OpenClaw v2026.4.23 (binário Node.js) hospeda os 6 agentes + main e expõe WebSocket em `:18789`.

```
Monkey-patch ativo (Issue #62028):
  arquivo: /usr/lib/node_modules/openclaw/dist/restart-stale-pids-<hash>.js
  patch: cleanStaleGatewayProcessesSync → return []
  motivo: versão 2026.4.14+ mata o próprio gateway (fratricide)
  manutenção: hash muda a cada versão → usar glob; /root/reapply-monkey-patch.sh
  idempotente: sim (Python regex, safe re-apply)

Configs críticas em openclaw.json:
  commands.restart = false
  gateway.reload.mode = off
  discovery.mdns.mode = off

NUNCA editar openclaw.json via jq+mv:
  gateway tem in-memory canonical state que sobrescreve no startup
  usar: openclaw config set <path> <val> + openclaw config validate
```

### 9.4 graphify (AST extraction)

graphify é uma ferramenta separada que indexa documentos estáticos (repos, PDFs, PPTX, XLSX). A integração com nox-mem é via ingest do `GRAPH_REPORT.md` gerado.

```
Camada de separação de responsabilidades:

  graphify                     nox-mem
  ────────                     ───────
  Indexa DOCUMENTOS            Indexa MEMÓRIA OPERACIONAL
  (repos, PDFs, slides)        (conversas, decisions, lessons)
  Output: graph.json +         Input: graphify/graph.json +
          GRAPH_REPORT.md              GRAPH_REPORT.md (via ingest)
  Storage: graph.json           Storage: chunks table
  Query: graphify query         Query: hybrid search

A ponte: nox-mem ingest GRAPH_REPORT.md → chunks consultáveis
Agentes leem GRAPH_REPORT.md no boot → contexto completo
```

Query strategy: Nox decide qual sistema consultar pelo tipo de pergunta. Decisão/conversa/lessons → nox-mem. Documento/contrato/repo → graphify. Ambíguo → nox-mem primeiro, graphify se não achar.

### 9.5 Obsidian vault (Fase 4 — view-only)

```
VPS (02:30 BRT)
export-obsidian-vault.py (430 LOC Python)
    ├── lê DB: kg_entities + kg_relations + chunks (section=compiled)
    ├── gera /root/ObsidianVault-build/
    │   ├── 183 entity files (.md com frontmatter Obsidian)
    │   ├── KG index (Dataview table)
    │   └── by-type breakdowns (agents, systems, projects, decisions, lessons)
    └── total: 199 arquivos .md

Mac (03:00 BRT via launchd)
rsync Tailscale: 100.87.8.44:/root/ObsidianVault-build/ → ~/ObsidianVault/
    └── excludes obrigatórios (customizações local-only que NÃO sobrescrever):
        .obsidian/themes/
        .obsidian/plugins/
        .obsidian/snippets/
        .obsidian/community-plugins.json
        .obsidian/appearance.json
        .obsidian/hotkeys.json
        .obsidian/types.json
        .obsidian/graph.json
```

O Obsidian é **janela**, não memória. A memória real vive no SQLite. O sistema funciona igual com ou sem Obsidian aberto.

---

## 10. Future Architecture

### 10.1 Wave 1 — Maio 2026 (Memory Graph Maturity)

**W1.1 — Edge typing FULL** (5-6h):
- `relation_reason` enum 7 valores aplicado a todas as ~544 relations existentes
- Campo `confidence` REAL (0.0-1.0) populado por Gemini na extração
- Shadow-mode 7d antes de usar confidence para kg-prune
- Gate: ≥80% das relations classificadas com confidence ≥0.7

**W1.2 — detect-changes** (2-3h):
- `nox-mem detect-changes --since=<commit>` compara estado do DB contra commit Git
- Identifica chunks que mudaram/foram adicionados/removidos
- Base para alertas de mudança de contexto crítico

**W1.3 — impact CLI** (2.5h):
- `nox-mem impact <entity>` — blast radius 1-hop no KG
- "Se nox-mem mudar, o que mais é afetado?"
- Depende de W1.1 para ter relations tipadas confiáveis

**W1.4 — api_impact** (1.5h, candidato a defer):
- `nox-mem api_impact` — análise multi-arquivo de impacto de mudança de API
- Nice-to-have; primeiro corte de capacity se apertar

**W1.5 — A-MEM auto-keywords/links** (3-4h, candidate):
- Auto-geração de keywords e links durante ingest (inspirado em A-MEM)
- Candidato: aguarda POC + 7d shadow validado
- Pode ser fundido com Fase 1.7b dormente

### 10.2 Wave 2 — Jun-Jul 2026 (Eval Harness)

**W2.1 — Eval harness completo** (7-9h):
- 50 golden queries curadas manualmente
- Métricas: nDCG@10, MRR (Mean Reciprocal Rank)
- Base para qualquer decisão futura de ranking (shadow-mode mandatory)
- Consome corpus `search_telemetry` já acumulado desde A0

**W2.2 — Consolidation merge + contradiction detection** (1.5-2h, candidate):
- Detecta chunks contraditórios via KG (`relation_reason=contradicts`)
- Sugere merge ou supersedure
- Depende de W2.1 nDCG ≥0.6 + dry-run com zero falsos positivos

Gate Wave 1 → Wave 2: ≥80% relations classificadas + W1.2/W1.3 rodaram ≥3× sem falso positivo + 50 golden queries curadas.

### 10.3 Wave 3 — Ago 2026 (Paper v2)

**W3.1 — Paper técnico v2** (2.5-3h):
- Atualiza `paper-tecnico-nox-mem.md` com resultados medidos
- Seções novas: Affective Ranking quantificado (pain × recency × importance)
- Federation model (cross-agent search em produção)
- Bridge Mode formalizado (CLI + MCP + HTTP sobre mesma SQLite)
- Depende de W2.1 publicar nDCG@10 baseline

Gate Wave 2 → Wave 3: nDCG@10 baseline publicado + W2.1 validado em produção ≥30d.

### 10.4 NOX-Supermem — Set+ 2026 (productização)

```
Repo: github.com/totobusnello/nox-supermem (private)
Local: ~/Claude/Projetos/nox-supermem/

Mercado: Brasil (PT-BR, Hotmart)
Tiers: A/B/C — R$ 147 / 197 / 227
       + R$ 30/sem suporte premium

Arquitetura planejada (design pendente):
  - Multi-tenancy: 1 nox-mem DB por cliente (isolamento total)
  - Auth: JWT por tenant
  - Billing: Hotmart webhook → activation
  - Infra: mesma stack (SQLite + Gemini API), escalada por instância

Gate de entrada: "Fase 4 Obsidian estável 30d" (≥2026-05-26)
```

Productização de nox-mem em paralelo com o desenvolvimento pessoal foi explicitamente rejeitada (DECISIONS.md §1 item 16) — risco de divergência de 6 meses. Horizonte realista: Set+ 2026.

### 10.5 Candidatos deferred com trigger de revisão

| ID | Item | Trigger para reavaliar |
|---|---|---|
| Q5 | Cross-encoder reranker (Qwen3-0.6B local) | W2.1 nDCG ≥0.6 + caso real de query ambígua mal-rankeada + decisão local-vs-cloud |
| C1 | Reflect cache (semantic key) | 7d telemetria reflect acumulada |
| C2 | Self-Evolving Hooks | Caso de uso concreto aparecer |
| C3 | OCR PDFs scaneados (Tier 3) | Volume PDF scaneado >50 docs |

Nenhum destes entra em desenvolvimento sem trigger explícito documentado e POC de shadow-mode.

---

## Referências cruzadas

| Documento | Conteúdo |
|---|---|
| `CLAUDE.md` | Regras críticas operacionais 1-15 (violação = produção quebra) |
| `docs/HANDOFF.md` | Estado atual + próxima ação |
| `docs/ROADMAP.md` | Calendário cronológico + capacity tracker |
| `docs/DECISIONS.md` | NÃO FAZEMOS + decisões arquiteturais com razões |
| `docs/EVOLUTION.md` | Histórico detalhado de versões v1.0 → v3.7 |
| `docs/INCIDENTS.md` | Log completo de incidents com root cause + mitigação |
| `docs/CONVENTIONS.md` | Convenções de código + nomenclatura |
| `docs/nox-neural-memory.md` | Visão estratégica (v14) + Phase Matrix completa |
| `specs/*.md` | Specs técnicas por feature |
| `audits/*.md` | Audits de segurança e código |
| `plans/_archive/` | Plans históricos (v1.5, v1.6, ClawMem analysis, handoffs) |
