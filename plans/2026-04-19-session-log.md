# Session Log — 2026-04-19 (Domingo)

Sessão longa cobrindo **Fase 1.6**, **Fase 1.8-lite (parcial)** e **Fase 1.7a** completa.

---

## Timeline das entregas

### Parte 1 — Fase 1.6: Search Quality Upgrade ✅
**Duração:** ~2h (manhã)

Query expansion multi-perspective via Gemini 2.5 Flash + dedup 4-layer + search_telemetry.

**Entregas:**
- `src/search-expansion.ts` — Gemini rewrite em 2 variantes (técnica + paráfrase), fallback gracioso, toggle `meta.expansion_enabled`
- `src/search-dedup.ts` — 4 layers: cap 3/file · Jaccard sim ≥0.85 · type saturation 60% · final cap 2/file
- `src/search.ts` — expansion paralelo com original search, semantic só na query original (economia 800ms no p95)
- Schema v6: tabela `search_telemetry` (query_hash sha1, variants_count, results_count, has_semantic, latency_ms)
- `/api/health.searchTelemetry` — reportando count_24h, avg_results, semantic_ratio, p95_latency_ms, skip_reasons
- Script de aceitação `test-phase-1.6.sh` (15 queries)

**Métricas (15 queries):**
- ≥3 resultados únicos: **15/15** (target 10)
- Semantic hit: **100%** (target 70%)
- p95 latência: **1399ms** (target ≤1500ms)
- Média: 965ms
- Evidência killer: query "coisa da memória quebrada" → BM25 0 results · hybrid 3 matches semânticos

**Doctrina herdada:**
1. FTS para variantes · semantic só para original (paráfrases são near-redundantes no espaço vetorial)
2. Expansion kickoff em paralelo, não serial
3. `meta` table para config runtime (não `openclaw.json` — binary v2026.3.31 rejeita chaves root desconhecidas)
4. Telemetria via sha1 16-char hash (privacidade do conteúdo da query)

---

### Parte 2 — Fase 1.8-lite Track A/C/D (parcial) ✅
**Duração:** ~2-3h (tarde)

**Pré-work — método:**
- 4 reviews paralelos (architect, sre-engineer, security-auditor, product-manager) sobre draft inicial → `audits/reviews-phase-1.8/`
- 7 baselines SRE medidos → `audits/reviews-phase-1.8/05-baselines-sre.md`
- Plano calibrado v2 → `plans/2026-04-19-phase-1.8-lite-v2.md`

**Achados-chave dos reviews:**
- SEV-1 architectural: inbox-em-DB violaria Path A pre-req → adotado inbox.jsonl append-only
- Critical security: cross-agent prompt injection = worm vector → 9 security controls obrigatórios
- PM: matcher reativo resolve 20% · event triggers 80% → redesign Track D para Slack/Calendar/Gmail/WhatsApp BVV
- Architect: matcher em `meta` table (não TEAM.md — drift provado: 6/6 SOULs têm TEAM.md idêntico)

**Entregas efetivas (tracks A + C + D4):**

**Track A — Mesh Foundation:**
- Spot-check audit dos 6 SOULs → `audits/spot-check-souls-2026-04-19.md`
  - TEAM.md idêntico em 6/6 (stub nunca customizado)
  - CHANNELS.md stale Apr 5 (drift do openclaw.json que evolui daily)
  - Forge sem BOOTSTRAP.md (correto — arquivo é "delete-after-init")
- `scripts/heartbeat-sync.sh` — cron /5min infere atividade por mtime de session files · 6/6 agentes **active** (gap "stale 6-14d" resolvido)

**Track C — Cipher Security:**
- `scripts/cipher-weekly-audit.sh` — bash: disco, ufw, fail2ban, SSH failures, Tailscale, backups age, nox-mem integrity, auth cooldowns, secrets age
- Consolidado com cron `security-audit` existente num só: `cipher-weekly-audit` Dom 10:00, agent=cipher, thinking off, timeout 600s
  - Executa `openclaw security audit` nativo + `bash cipher-weekly-audit.sh` + consolidates
  - Post estruturado no Discord #agents-hub + escalate WhatsApp em red flag

**Track D4 — Daily Briefing 07:30 WhatsApp:**
- **Descoberta importante:** daily-briefing já existia como cron openclaw mas estava em error state há 2 dias (timeout 04-17 intermitente)
- Schedule unificado:
  - `slack-20f-daily-summary` → 07:15 todos os dias (era Seg-Sex 07:45)
  - `obra-bvv-resumo-manha` → 07:20 (era 07:55 Seg-Sáb)
  - `prepare-briefing-context` → 07:20 (era 07:55 Seg-Sex)
  - `daily-briefing` → **07:30 todos dias** (era 08:00 Seg-Sex)
- Timeouts generosos (15min briefing, 5min outros)
- **Thinking OFF** no daily-briefing (eliminou "I'll start generating..." streaming)
- Prompt estrito: "Sua resposta final é UNICA E EXCLUSIVAMENTE o briefing" (eliminou meta-resumos)
- `scripts/weather-sp.sh` — wttr.in j1 parse JSON → min/max temp ("São Paulo: Partly cloudy +23°C · min 19°C / max 27°C")
- Delivery: WhatsApp `+55 11 98202-2121` primary + Discord `#agents-hub` cópia archive
- Briefing reusa infra existente: skill `briefing` · `prepare-briefing-context.sh` · cron `slack-20f-daily-summary` · `gog` CLI (Gmail/Calendar 3 contas: generantis + nuvini + ppr)
- **Validado** — Totó confirmou entregue limpo

**Pendente do plano 1.8-lite:**
- Track A3 discovery primer Nox (satisfeito via boot injection do USER-PROFILE na 1.7a)
- Track B — dispatch_to tool + 9 security controls
- Track D1 — Slack @mentions fora do canal 20-F
- Track D2 — Calendar briefings dedicados pelo Atlas (antes de reuniões externas)
- Track D3 — Gmail → Lex contratos dedicado

---

### Parte 3 — Fase 1.7a: Core Memory Quality ✅
**Duração:** ~1h (tarde/noite)

**Entregas:**
- Schema v7 (`kg_entities.attributes` JSON + `chunks.source_type` + `chunks.is_compiled` + 2 indexes)
- `src/kg-llm.ts` — ontology grounding prompt + fast-path regex PT-BR:
  - Valores R$/US$/€
  - CNPJ (`\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`) · CPF
  - Datas DD/MM/YYYY · telefones +55
  - Emails · URLs · percentagens
  - Proper nouns (capitalizadas compostas em PT-BR)
  - Threshold ≥3 hits estruturados (ignora proper_noun solo para evitar falsos positivos)
- `src/index.ts` (`kg-extract`) — merge JSON incremental de attributes + contador fast-path vs llm
- `src/search.ts` — `SOURCE_TYPE_BOOST`: user 2.0x · compiled 1.5x · timeline 1.0x · external 0.8x (aplicado em FTS + semantic)
- `src/generate-user-profile.ts` (novo) — gera `shared/USER-PROFILE.md`:
  - Top 20 entidades por mention (agrupadas por tipo: person, project, organization, agent)
  - Projects ativos (status ≠ closed)
  - Decisões últimos 30 dias
  - Preferências declaradas (chunks tipo lesson/preference/pattern)
- Cron openclaw `generate-user-profile` Dom 21:00 BRT
- Boot injection em 6/6 SOULs (Nox, Atlas, Boris, Cipher, Forge, Lex) — seção "📋 Boot reading" referenciando `shared/USER-PROFILE.md`

**Métricas de aceitação (teste 10 chunks):**
- Fast-path hits: **30%** (3/10 chunks, meta ≥30% ✅) — Gemini API calls economizados
- Extraction: 41 entities + 16 relations em 10 chunks
- USER-PROFILE.md: 8019 bytes, 371 entities agregadas
- Backfill source_type: 2290 chunks classificados (99.7% timeline, 0.3% external — heurísticas conservadoras)

**Doctrina herdada:**
1. Attributes em JSON (não tabelas normalizadas) — schema rico sem migrations por campo
2. Merge incremental no upsert (preserva dados existentes, overwrites chaves novas)
3. Fast-path exclui proper_noun solo do threshold (evita falso positivo)
4. Boost multiplicativo sobre tier/type/recency (ordem não importa, independentes)
5. USER-PROFILE em `shared/` (single source pra 6 agentes), não em `agents/<x>/`
6. Boot injection idempotente via grep antes de append

**Pendências (não gating):**
- Calibrar heurística de backfill `source_type` (WhatsApp/Notion patterns hoje não batem)
- Rodar `kg-extract` full sobre 2290 chunks para popular attributes completos (~20-40min com fast-path)
- Validar query "múltiplo EBITDA do deal X" retorna valor específico (precisa attributes populados)

---

## Infraestrutura tocada hoje

### Novos arquivos criados na VPS:
- `/root/.openclaw/scripts/heartbeat-sync.sh`
- `/root/.openclaw/scripts/cipher-weekly-audit.sh`
- `/root/.openclaw/scripts/weather-sp.sh`
- `/root/.openclaw/workspace/tools/nox-mem/src/search-expansion.ts`
- `/root/.openclaw/workspace/tools/nox-mem/src/search-dedup.ts`
- `/root/.openclaw/workspace/tools/nox-mem/src/generate-user-profile.ts`
- `/root/.openclaw/workspace/shared/USER-PROFILE.md`

### Arquivos modificados:
- `/root/.openclaw/workspace/tools/nox-mem/src/db.ts` (schema v6 → v7)
- `/root/.openclaw/workspace/tools/nox-mem/src/kg-llm.ts` (ontology + fast-path)
- `/root/.openclaw/workspace/tools/nox-mem/src/search.ts` (expansion + dedup + source_type boost)
- `/root/.openclaw/workspace/tools/nox-mem/src/index.ts` (kg-extract merge attributes)
- `/root/.openclaw/workspace/tools/nox-mem/src/api-server.ts` (searchTelemetry field)
- Todos os 6 `/root/.openclaw/workspace/agents/*/SOUL.md` (boot reading injection)

### Crons novos ou alterados:
| Cron | Antes | Depois |
|---|---|---|
| slack-20f-daily-summary | `45 7 * * 1-5` 60s | `15 7 * * *` 300s |
| obra-bvv-resumo-manha | `55 7 * * 1-6` 60s | `20 7 * * *` 300s |
| prepare-briefing-context | `55 7 * * 1-5` 60s | `20 7 * * *` 300s |
| daily-briefing | `0 8 * * 1-5` noTimeout | `30 7 * * *` 900s · thinking off · novo prompt |
| security-audit | Dom 10:00 agent=None | **`cipher-weekly-audit`** Dom 10:00 agent=cipher |
| generate-user-profile | (não existia) | **Dom 21:00** 120s |
| heartbeat-sync.sh | (não existia) | crontab sistema `*/5 * * * *` |

### Agentes 1:1 ainda on crontab sistema (não openclaw cron):
- `*/5 * * * * /root/.openclaw/scripts/heartbeat-sync.sh`

### Backups pré-mudança:
- `/root/.openclaw/workspace/tools/nox-mem/backups-src/pre-1.7a-20260419/` (db.ts, kg-llm.ts, index.ts, search.ts originais)
- `/root/.openclaw/workspace/tools/nox-mem/backups-src/backup-pre-1.6-20260419/` (originais Fase 1.6)

---

## Documentos escritos

- `audits/reviews-phase-1.8/01-architect.md`
- `audits/reviews-phase-1.8/02-sre.md`
- `audits/reviews-phase-1.8/03-security.md`
- `audits/reviews-phase-1.8/04-product.md`
- `audits/reviews-phase-1.8/05-baselines-sre.md`
- `audits/spot-check-souls-2026-04-19.md`
- `plans/2026-04-19-phase-1.8-lite-v2.md` (FINAL)
- `plans/2026-04-19-session-log.md` (este arquivo)

E no roadmap unificado (`plans/2026-04-19-unified-evolution-roadmap.md`):
- Fase 1.6 marcada ✅ com resultado detalhado
- Fase 1.7a marcada ✅ com resultado detalhado

---

## O que chega amanhã (automatizado)

1. **Daily briefing 07:30 BRT** — WhatsApp + Discord #agents-hub
   - System health · clima SP min/max · aniversários (calendar) · agenda 3 contas · emails urgentes · MPDM Slack · tarefas+Slack+BVV numerados globalmente · comentário humano
2. **Heartbeat sync /5min** — HEARTBEAT.md de cada agente atualizado
3. **Semantic canary 06:00** — valida Layer 2 (vector search) ativa
4. **Morning report 06:30** — health técnico do nox-mem (Discord)
5. **Nightly maintenance 23:00** — reindex + consolidate + vectorize + kg-build

**Dom 21:00:** `generate-user-profile` → regenera `shared/USER-PROFILE.md`
**Dom 10:00:** `cipher-weekly-audit` → relatório consolidado no Discord

---

## Próximas opções

| Fase | Esforço | Valor imediato | Recomendação |
|---|---|---|---|
| **2.5 graph-memory plugin** | 30min + 1sem | Alto (compressão WhatsApp 173K→<30K) | **✅ FEITA** 2026-04-19 — em observação 7d |
| **1.8 completa** (dispatch_to + 9 controls) | 3-4h | Médio (infra agent mesh) | Se priorizar A2A agora |
| ~~**Path A Write Coordinator**~~ | ~~2 semanas~~ | ~~Baixo (higiene arquitetural)~~ | **Virou reativo** — ver Decisão 14 |
| **Fase 2 — Graphify + GitHub (rate-limited)** | 2-3h + build | Alto (mapa completo de conhecimento) | **Próxima após 7d de obs** |
| **1.8 Track D1/D2/D3** | 1h cada | Médio (Slack/Calendar/Gmail triggers dedicados) | Incremental ao daily briefing |
| **Calibrar backfill `source_type`** | 30min | Baixo (melhora boost atual) | Nice-to-have |

---

## Parte 5 — Decisão de arquitetura (17h) ✅

### Fase 2.5 graph-memory plugin — setup concluído (em observação 7d)
- `openclaw plugins install graph-memory` via ClawHub community (v1.5.8)
- `plugins.slots.contextEngine: "graph-memory"` (crítico — sem isso não ingere)
- `plugins.allow` com 22 plugins (populado automaticamente pelo install)
- Embedding: Gemini `gemini-embedding-001` via OpenAI-compat endpoint (3072d)
  - **Descoberta:** `text-embedding-004` não existe na Gemini v1main; correto é `gemini-embedding-001`
- `graph-memory.db` em `/root/.openclaw/` (FTS5 + vectors + communities)
- Backup daily no `backup-all.sh` (keep 7d)
- `[graph-memory] vector search ready` confirmado nos logs
- Exit criteria a medir em 7d: conversa 7+ turns ≤30K tokens; DB <50MB

### Decisão 14 — Path A vira reativo, não pre-req

**Contexto levantado pelo Totó:** "por que Path A leva 2 semanas?"

**Análise honesta:**
- Baselines de hoje mostram SQLITE_BUSY=0 em 7d, /api/health <10ms, writes/dia ~300
- Volume está uma ordem de magnitude abaixo do limite que justificaria Path A preventivo
- 2 semanas de dev pra proteger contra problema não-medido = premature optimization

**Nova estratégia adotada (Totó aprovou):**
1. **Path A vira REATIVO** — plano fast 3-5 dias pronto, ativa só se triggers concretos aparecerem
2. **Graphify rate-limited** — batches 500 + pause 5min + janela proibida 22:30-01:30 BRT substitui Path A preventivo
3. **Triggers explícitos pra ativação:** SQLITE_BUSY>0 em 24h, restartsHour>2 em 6h, p95>100ms, `database is locked` em journalctl
4. **Monitoramento reforçado já coberto:** morning-report 07:30 + canary 06:00 + cipher weekly Dom 10:00

**Impacto no cronograma:**
- Timeline revisado pra Fase 4 (Obsidian): **3-4 semanas** (era 5-6 semanas com Path A preventivo)
- Economia: ~2 semanas de calendário
- Risco: +3-5 dias de calendário SE um dos 4 triggers aparecer (probabilidade baixa)

### Nova ordem de execução documentada no roadmap

1. Observar graph-memory 7d (em curso)
2. **Fase 2 — Graphify + GitHub (rate-limited)** 2-3h
3. 7d observação Fase 2
4. Fase 1.7b — Memory Advanced 4-6h
5. Fase 3 — HD Mac rsync + enrichment tiered 1h + rsync
6. Fase 4 — Obsidian view-only 1h
7. Productização (Fase P) horizonte 60d+

### Tracks 1.8 pendentes (decisão independente)

Tracks B, D1, D2, D3 do plano Fase 1.8 ainda fazem sentido mas não são gating de nada. Fica decisão do Totó: fazer incremental ao daily briefing, ou deixar pra depois. Atualmente **todos paused**:
- B — dispatch_to + 9 security controls (3-4h)
- D1 — Slack @mentions fora canal 20-F (1h)
- D2 — Calendar briefings dedicados Atlas (1h)
- D3 — Gmail → Lex contratos dedicado (1h)

---

## Parte 6 — Fase 2 Graphify + GitHub repos (noite) ✅ piloto

**Duração:** ~2h · **Output:** 404 chunks em nox-mem + 3 HTMLs visuais aprovados

### Instalação
- `graphify` CLI local no Mac: `pipx install graphifyy` (v0.4.23)
- Skill `/graphify` em `~/.claude/skills/graphify/SKILL.md`
- Skill também na VPS (`/root/.openclaw/skills/graphify/` + venv `/root/.openclaw/venv-graphify/`) — porém OpenClaw é sequential-only, então execução real roda **local no Mac** (Claude Code parallel subagents)

### Workflow estabelecido
```
Mac (repos locais) → /graphify skill (parallel Claude subagents) →
graphify-out/{graph.html, graph.json, GRAPH_REPORT.md} →
rsync → VPS /root/vault/projetos/<repo>/graphify-out/ →
graphify-ingest.ts (rate-limited) → nox-mem chunks (graph_node type)
```

### Script de ingest criado
- `src/graphify-ingest.ts` + deployed `dist/graphify-ingest.js` no VPS
- CLI: `node dist/graphify-ingest.js <graph.json> <repo-name>`
- Rate-limit: batch 500 + pause 5min (default) + janela proibida 22:30-01:30 BRT
- Idempotente: `DELETE WHERE source_file LIKE 'graphify:<repo>:%'` antes de inserir
- Load `sqlite-vec` antes de abrir DB (fix "no such module: vec0" com virtual tables)
- Cada node → 1 chunk com source_file=`graphify:<repo>:<node_id>`, source_type=`external`, is_compiled=1, chunk_type=`graph_node`, metadata JSON completo

### Repos processados

| Repo | Files | Words | Nodes | Edges | Communities | Isolated | Chunks ingeridos |
|---|---|---|---|---|---|---|---|
| **Granix-App** (piloto) | 68 | 394K | 163 | 258 | 8 | 33 | 163 |
| **sao-thiago-fii** | 13 | 24.8K | 94 | 146 | 9 | 36 | 94 |
| **projeto-ai-galapagos** | 22 | 203K | 147 | 205 | 7 | 44 | 147 |
| **TOTAL** | 103 | 622K | 404 | 609 | 24 | 113 | **404** |

### Insights descobertos (cross-document surprises dos grafos)

**Granix-App:**
- Greenlight (US fintech) é bridge entre v1-archive e v2-current (betweenness 0.084 — maior do grafo)
- 4 Buckets Greenlight ↔ 4 Pots GRANIX (inspiração documentada)
- Wireframe Gamificação → Component Library (implements link não óbvio)
- PRD Pre-Pivot ≈ PRD v1 (semantic duplicate — duas versões do mesmo doc)

**sao-thiago-fii:**
- Tese R$ 8MM/laje triangulada por 3 pilares (mark-to-market, block premium, market optionality)
- CECB building = hub central (pesquisa, justificativa, plano-torre, apresentação)
- 59.200 m² residual no plano-torre (material case extra identificado)
- Benchmarks FIIs comparáveis: RBRP11, PVBI11, ONEF11

**projeto-ai-galapagos:**
- Darwin AI = hub (11 produtos, 63 agentes, 22 áreas)
- Stack triad: HubSpot + Claude API + Supabase
- Compliance chain: CVM 30/2021 + LGPD → Data Gateway → Audit Trail → Claude Zero-Retention
- Cross-Sell Intelligence (#0) rationale para Lovable.dev prototype
- Blueprint (sales) ≈ Darwin AI (technical) — sibling docs via semantic_similar_to

### `.graphifyignore` pattern validado
```
docs/scripts/
docs/scripts/*.py
**/build_*.py
branding/CLAUDE.md
wireframes/CLAUDE.md
.claude/
graphify-out/
**/node_modules/
**/.git/
```
Aplicar em todo repo novo antes do graphify. Reduziu 89→33 isolated no Granix (-63%).

### Decisões de implementação que viraram doutrina

1. **Graphify roda SEMPRE local no Mac**, nunca na VPS — Claude Code parallel subagents vs OpenClaw sequential.
2. **`.graphifyignore` obrigatório** por repo antes do primeiro run (remove scripts Python de deck + folder memory contexts).
3. **Deep mode (`--mode deep`) default** — triplica INFERRED edges, reduz isolated em ~60%.
4. **Ingest rate-limit não foi exercitado** nos pilotos (<500 nodes cada). Será crítico com HD rsync (Fase 3) que pode gerar 5000+ nodes.
5. **Chunks graphify não replicam em kg_entities** — ficam só em `chunks` table. Evita duplicação com KG v2 que já tem 371 entities próprias. Future work: decidir se enriquece kg_entities com attributes do graphify.

### Search cross-repo validado
Query `"Ciclo Virtuoso Granix"` via hybrid search retornou:
- `graphify:Granix-App:estrategia_ciclo_virtuoso_design` [fts] — top result
- `shared/SYSTEM-STATE.md` [semantic] — contextual match
- `graphify:Granix-App:estrategia_ciclo_virtuoso_loop` [fts]

Pipeline fim-a-fim funcionando.

---

## Atualizações no roadmap

- Fase 2: ⏳ READY → 🔧 **IN PROGRESS (3/~15 repos)**
- Fase 2.5: 🔧 IN OBSERVATION (graph-memory plugin, 7d iniciados)
- Fase 1.7a: ✅ DONE
- Fase 1.6: ✅ DONE
- Path A: 🟡 REATIVO (não mais PRE-REQ)
