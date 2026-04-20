# Próxima Sessão — Checklist (2026-04-20)

Continuação da sessão monstro de 2026-04-19. Ordem aprovada pelo Totó.

---

## ⚠️ Nota do Totó (2026-04-19 fim-de-dia)

> "Tem algumas coisas soltas mas processamos na próxima sessão."

**Ou seja:** abrir a sessão consciente que existem pontos não fechados nos grafos piloto ou em decisões tomadas. Sessão de amanhã deve **abrir espaço** pra Totó trazer essas observações antes de executar — não ignorar por estar focado em auditoria/escalar.

**Primeira ação:** perguntar ao Totó "quais coisas soltas você anotou?" antes de seguir pro item 1.

---

## Ordem aprovada pelo Totó

### 1. Auditoria + melhorias do que já fizemos hoje

Sessão de hoje entregou muito. Auditar tudo antes de escalar pra mais repos.

**Escopo da auditoria:**

**Fase 1.6 — Search Quality (search expansion + dedup)**
- [ ] Rodar `test-phase-1.6.sh` de novo na VPS (validar 15 queries ainda verde)
- [ ] Conferir `search_telemetry` dos últimos 24h — has_semantic ratio, p95 latency, skip_reasons
- [ ] Ver se `expansion_enabled=true` sigue default. Algum caso onde desligar faria sentido?

**Fase 1.7a — Core Memory Quality**
- [ ] Fast-path hit rate em produção (últimos kg-build runs)
- [ ] USER-PROFILE.md regenerado domingo 21:00? Conferir quando cron rodou
- [ ] 6 SOULs têm a seção "Boot reading" (sanity check)
- [ ] Backfill `source_type` heurística — calibragem: 99.7% timeline é conservador demais. Totó lembrou alguma exceção?
- [ ] Query de teste ontology: "qual o múltiplo de EBITDA do deal X?" retorna valor específico? (precisa primeiro rodar `kg-extract` full sobre os 2290 chunks)

**Fase 1.8-lite parcial (daily briefing + heartbeat + cipher)**
- [ ] Daily briefing 07:30 chegou WhatsApp + Discord limpo?
- [ ] Heartbeat /5min continua 6/6 active?
- [ ] Cipher weekly cron — ainda não rodou (primeiro Dom 04:30 é amanhã 2026-04-26)
- [ ] Telemetria restart count — zero anomalias?

**Fase 2.5 — graph-memory plugin**
- [ ] `graph-memory.db` tamanho (esperado crescer com cada conversa)
- [ ] `gm_messages` / `gm_nodes` / `gm_communities` counts
- [ ] Vector search ready mantém?
- [ ] Teste real: uma conversa >7 turns comprime contexto?
- [ ] Conflito com `active-memory` (plugin bundled)? Ambos injetam before_prompt_build

**Fase 2 — Graphify (3 repos piloto)**
- [ ] Validar boost `source_type=external` (0.8x) aplicado aos graph_node chunks
- [ ] Query cross-repo: "qual a conexão entre Granix e sao-thiago-fii?" — deve misturar chunks
- [ ] Comparar qualidade dos 3 grafos (Granix mais denso 8 comunidades vs Galapagos 7 vs SaoThiago 9)
- [ ] **Ruído residual:** god nodes ainda têm helpers AST? Ajustar `.graphifyignore`?
- [ ] Ingest dos 404 chunks mexeu em algo (SQLITE_BUSY? latency?)

**Infra geral**
- [ ] `check-nox-mem.sh` verde?
- [ ] morning-report anomalias?
- [ ] Restarts 24h normais?
- [ ] Cipher weekly audit consolidado rodou primeira vez?

**Deliverable da auditoria:**
- `audits/audit-2026-04-20-fase-1-2.md` consolidando achados + recomendações de melhoria

---

### 2. Melhorias identificadas (pós-auditoria)

Lista pra confirmar com Totó:

**Já mapeadas como pendências:**
- Calibrar heurística `source_type` (WhatsApp Totó → user_statement patterns)
- Rodar `kg-extract` full sobre 2290 chunks pra popular attributes completos
- Validar query "múltiplo EBITDA" retornar valor específico
- Overlap `active-memory` vs `graph-memory` — decidir se mantém ambos ou desliga active-memory

**Podem surgir na auditoria:**
- Novos `.graphifyignore` patterns a padronizar
- Tuning do rate-limit (batch size, pause duration)
- Ajustes no prompt do `graphify-ingest` (inclui ou não community name no chunk_text?)

---

### 3. Escalar Fase 2 pros repos restantes

**Ordem definida com Totó:** comerciais → áreas → infra.

**Tier 1 — Comerciais restantes (8 repos):**
- [ ] **Future-Farm** (JavaScript, 2026-04-13 push)
- [ ] **GalapagosApp** (JavaScript — app mobile, diferente do projeto-ai-galapagos)
- [ ] **Frooty**
- [ ] **superfrio**
- [ ] **grancoffee**
- [ ] **biolab-ai**
- [ ] **curso-ai**
- [ ] **fake-news-check**

**Tier 2 — Áreas (2 repos):**
- [ ] **Area-Manuel-Nobrega**
- [ ] **Area-Campolim-Sorocaba**

**Tier 3 — Infra (4 repos):**
- [ ] **nox-supermem** (TypeScript, v2.1.2 stale 33d)
- [ ] **agent-hub-dashboard** (TypeScript — dashboard React)
- [ ] **daily-tech-digest**
- [ ] **memoria-nox** (self-graph — interessante: indexar o próprio projeto de memória)

**Fora de escopo pra esta fase:**
- `Claude` (workspace monorepo — muito grande, ~500MB+, melhor pós Path A se necessário)
- `nox-workspace` (similar ao Claude)
- `powerpoint-templates` (templates, não conteúdo)
- `claude-project-template` (skeleton)
- `posts-linkedin` (conteúdo ocasional)

**Processamento em batches de 2-4 em paralelo** pra acelerar. Cada repo:
1. Clone local se ainda não tem
2. Criar `.graphifyignore` padrão
3. Detect + AST + subagents DEEP mode em paralelo
4. Merge + cluster + labels + HTML
5. rsync pro VPS
6. Ingest via `graphify-ingest.js` com rate-limit

**Estimativa:** 14 repos × 10-15min cada = 3-4h total. Pode fazer em 2 sessões se preferir.

---

### 4. Fase 1.7b — Memory Quality Advanced (opcional pós-Fase 2)

Se tempo sobrar na sessão, começar 1.7b que depende de Fase 2 estável:
- Reasoning traces (chunk_type=`reasoning_trace`)
- Conflict detection (SQL query em kg-build)
- Invalidation chains (`valid_until` + `superseded_by`)
- Smart forgetting (TTL inteligente)
- Source text preservation (verbatim em kg_entities.source_text)
- Hierarchical tagging (scope/category/topic)
- Inline entity detection (regex fast-path em mensagens WhatsApp/Discord)

Estimativa: 4-6h. Provavelmente fica pra sessão seguinte.

---

### 5. Fase 3 — HD Mac rsync (muito depois)

Depende de 1.7b concluída. 21GB de Documents do Mac → graphify → ingest. Rate-limit crítico aqui (pode gerar 5000+ nodes).

---

## Status do sistema ao fim da sessão 2026-04-19

**Nox-mem (VPS):**
- Schema v7 (attributes + source_type + is_compiled)
- 2290 chunks base + 404 graph_node chunks = **~2694 chunks**
- 371 entities no KG (stale — precisa `kg-extract` full pra popular attributes)
- Hybrid search: FTS + semantic (Gemini 3072d) + source_type boost
- Search telemetry ativa
- **SQLITE_BUSY 7d = 0** (sistema saudável)

**Graph-memory plugin (VPS):**
- Instalado, contextEngine slot, vector search ready
- DB vazio (popula conforme conversas)
- Observação 7d iniciada 2026-04-19

**Daily briefing (WhatsApp + Discord):**
- 07:30 BRT automatizado
- System health + clima min/max + aniversários + agenda 3 contas + emails urgentes + MPDM Slack + tarefas numeradas globais + Slack 20-F + BVV + comentário humano
- Thinking OFF (sem verbosidade)

**Automações:**
- Heartbeat /5min (6/6 agentes active)
- Cipher weekly Dom 04:30 (consolidado com openclaw security audit)
- generate-user-profile Dom 21:00
- Morning-report health técnico (Discord) — mantém

**Graphify pipeline:**
- Local no Mac + rsync + ingest funcionando
- 3 repos piloto com 404 chunks + 3 HTMLs
- Rate-limit ready (não exercitado ainda)

**Plano unificado:**
- Fase 0.5 ✅ Foundation Repair
- Fase 1.6 ✅ Search Quality
- Fase 1.7a ✅ Core Memory Quality
- Fase 1.8-lite ✅ parcial (daily briefing + heartbeat + Cipher)
- Fase 2.5 🔧 graph-memory (em observação 7d)
- Fase 2 🔧 Graphify (3/~15 repos)
- Path A 🟡 REATIVO (não mais pre-req)

---

## Abrir sessão amanhã assim:

```
1. "O que você achou dos grafos ontem? Lembrou das coisas soltas que queria levantar?"
2. Rodar: ~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh
3. Abrir: plans/2026-04-20-next-session-checklist.md (este arquivo)
4. Começar auditoria (item 1) na ordem proposta
```

---

**Arquivos principais pra consultar:**
- `plans/2026-04-19-unified-evolution-roadmap.md` — roadmap mestre
- `plans/2026-04-19-session-log.md` — log completo de hoje (6 partes)
- `plans/2026-04-19-fase-2-graphify-log.md` — detalhes Fase 2
- `audits/reviews-phase-1.8/` — 4 reviews + baselines
- `audits/spot-check-souls-2026-04-19.md`
- `staged-*/` — código stage da sessão (1.6, 1.7a, 1.8, graphify-ingest)
