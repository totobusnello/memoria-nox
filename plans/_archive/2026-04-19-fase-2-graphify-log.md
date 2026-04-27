# Session Log — Fase 2 Graphify + GitHub repos (2026-04-19)

Executada mesma sessão de Fase 1.6, 1.8-lite parcial, 1.7a e 2.5. Continuação natural.

---

## Decisão 14 (anterior) aplicada

Path A virou reativo, não pre-req. Rate-limit graphify (batch 500 + pause 5min + janela proibida 22:30-01:30 BRT) substitui. Ver `plans/2026-04-19-unified-evolution-roadmap.md` para racional.

---

## Entregas desta fase

### Infraestrutura
- **`graphify` CLI** instalada local no Mac via `pipx install graphifyy` (v0.4.23)
- Skill `/graphify` disponível em `~/.claude/skills/graphify/SKILL.md`
- Skill `graphify` também instalada na VPS (`/root/.openclaw/skills/graphify/` via venv `/root/.openclaw/venv-graphify/`), mas execução dispara Claude subagents via OpenClaw, que é sequential-only — piloto validou que **rodar local no Mac (parallel Claude Code) + rsync pro VPS + ingest via script** é o workflow correto.

### Workflow adotado
```
Mac (repos locais) → graphify pipeline (parallel Claude subagents) →
graphify-out/{graph.html, graph.json, GRAPH_REPORT.md} →
rsync → VPS /root/vault/projetos/<repo>/graphify-out/ →
graphify-ingest.ts (rate-limited) → nox-mem chunks (graph_node type)
```

### Script de ingest
- Arquivo: `src/graphify-ingest.ts` (localmente em `staged-graphify-ingest/`, deployed em VPS)
- CLI: `node dist/graphify-ingest.js <graph.json> <repo-name> [--dry-run] [--batch-size N] [--pause-ms MS]`
- Default: batch=500, pause=300s (5min)
- Janela proibida: 22:30-01:30 BRT (abort se executado nela)
- Idempotente: `DELETE ... WHERE source_file LIKE 'graphify:<repo>:%'` antes de inserir
- Carrega `sqlite-vec` antes de abrir DB (evita "no such module: vec0" com virtual tables)
- Cada node graphify vira 1 chunk:
  - `source_file = graphify:<repo>:<node_id>`
  - `chunk_type = 'graph_node'`
  - `source_type = 'external'` (graphify é síntese externa)
  - `is_compiled = 1`
  - `chunk_text` = label + type + origem + até 8 conexões ("relação → target")
  - `metadata` JSON = graphify_id, community, file_type, source_original, author

---

## Repos processados (total ingeridos no nox-mem: 404 chunks)

| Repo | Files | Words | Graph nodes | Edges | Hyperedges | Communities | Isolated | Chunks em nox-mem |
|---|---|---|---|---|---|---|---|---|
| **Granix-App** (piloto) | 68 | 394K | 163 | 258 | 20 | 8 | 33 | 163 |
| **sao-thiago-fii** | 13 | 24.8K | 94 | 146 | 5 | 9 | 36 | 94 |
| **projeto-ai-galapagos** | 22 | 203K | 147 | 205 | 10 | 7 | 44 | 147 |

### Insights de cada grafo

**Granix-App**
- 8 comunidades: v1 Pre-Pivot Archive · Brand Identity · Competitive Landscape BR · Architecture Flows C4 · API v2 Multi-tenant · Compliance + Project Rules · Logo Concepts · Financial Models
- God nodes (betweenness): Greenlight (0.084), PRD Greenlight-inspired (0.071), PRD Family Financial Education (0.068)
- Surprising connections: PRD Pre-Pivot ↔ PRD v1 (semantic duplicate), 4 Buckets Greenlight ↔ 4 Pots GRANIX (inspiração explícita), Wireframe Gamificação → Component Library (implements)

**sao-thiago-fii**
- Tese de R$ 8MM/laje triangulada por 3 pilares (mark-to-market, block premium, market optionality) + benchmarks FIIs comparáveis (RBRP11, PVBI11, ONEF11)
- CECB building = hub central (pesquisa, justificativa, plano-torre, apresentação)
- 59.200 m² residual identificado no plano-torre (material para o caso)
- Locatários triangulados: B3, FAPES, Caixa, CAU/RJ

**projeto-ai-galapagos**
- Darwin AI platform = hub (11 produtos, 63 agentes, 22 áreas)
- Stack integration triad: HubSpot + Claude API + Supabase (pgvector/Edge Functions)
- Compliance rationale chain: CVM 30/2021 + LGPD → Data Gateway → Audit Trail → Claude Zero-Retention
- Cross-Sell Intelligence (#0) rationale para Lovable.dev prototype
- Blueprint (strategy/sales deck) e Darwin AI (technical spec) linked via semantically_similar_to edges

---

## Workflow validated — `.graphifyignore` pattern

Pattern que removeu ruído efetivamente:
```
# Python scripts geradores de slides/decks (helpers, não conteúdo)
docs/scripts/
docs/scripts/*.py
**/build_*.py

# CLAUDE.md de folders (1-node memory context stubs)
branding/CLAUDE.md
wireframes/CLAUDE.md
.claude/

# Cache + outputs
graphify-out/
.remember/
**/node_modules/
**/.git/
```

Aplicar em cada novo repo antes de rodar graphify.

---

## Rate-limit na prática

Repositórios piloto são pequenos (163, 94, 147 nodes cada) — todos coubessem em 1 batch single (default 500). **Rate-limit não foi exercitado** nessa sessão, mas a infra está pronta. Será necessário quando:
- Repos maiores (>500 nodes) no futuro
- Mac Documents rsync (~21GB, pode gerar 5000+ nodes)

---

## Pendências (para próxima sessão)

### Curto prazo (1-2h)
- **Auditoria da Fase 2 + melhorias** (Totó pediu explícito):
  - Rodar query de teste cross-repo: "qual a conexão entre Granix e sao-thiago-fii?" → valida hybrid search retornando chunks de múltiplos repos
  - Validar boost `source_type=external` (Fase 1.7a) aplicado corretamente em graph_node chunks (0.8x multiplier)
  - Ver se há ruído nos god nodes filtráveis via `.graphifyignore` melhorado
  - Calibrar heurística: graph_node chunks devem ou não fazer parte do kg_entities (attributes enrichment)?

### Médio prazo (esta semana)
- **Escalar pros repos comerciais restantes:**
  - Future-Farm
  - GalapagosApp (diferente do projeto-ai-galapagos — app mobile)
  - Frooty
  - superfrio
  - grancoffee
  - biolab-ai (mencionado no gh list, verificar escopo)
  - curso-ai
  - fake-news-check
- **Áreas:**
  - Area-Manuel-Nobrega
  - Area-Campolim-Sorocaba
- **Infra (Tier 3):**
  - nox-supermem
  - agent-hub-dashboard
  - daily-tech-digest
  - memoria-nox (self-graph)

### Longo prazo (Fase 3)
- HD Mac rsync (21GB Documents) → graphify → ingest
- Enrichment tiered (Tier 1/2/3 por mention count)
- Depende de Fase 1.7b (conflict detection) antes

---

## Status consolidado pós Fase 2 (piloto)

- **404 graph_node chunks** no nox-mem (Granix 163 + SaoThiago 94 + Galapagos 147)
- **3 HTML interativos** gerados (Mac) + ingestão validada no VPS
- **Infra de ingest funcionando** com idempotência + rate-limit ready
- **Search cross-repo funcional** (query "Ciclo Virtuoso" retorna nós do Granix via FTS)

Roadmap unificado atualizado na Fase 2 seção.
