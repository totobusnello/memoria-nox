# Unified Evolution Roadmap — nox-mem Memory System

**Versão:** 1.2 (2026-04-21)
**Status:** v3.6c deployado. Fases 24h, 2.5, Path A aposentadas (evidência produção).
**Fonte estratégica:** `docs/nox-neural-memory.md` (v12)
**Fonte de execução:** este arquivo — **source of truth daqui em diante**
**Última auditoria completa:** 2026-04-21 (sessão audit sistêmica — 17 fixes)

---

## Executive Summary

Objetivo: sistema de memória hyper-eficiente, confiável e persistente para os 6 agentes do Totó acessados via WhatsApp/Discord.

**Estado atual (2026-04-21, v3.6c):**
- 2073 chunks 100% embedded, zero orphans
- Hybrid search + canary */30min com self-heal
- Reindex com auto-vectorize inline (fix arquitetural — raiz do bug Apr 21)
- Cross-agent operacional (7 DBs com trigger+vetores)
- RelayPlane ATIVO, roteando Sonnet+Haiku real, budget caps efetivos
- Delegação inter-agente validada end-to-end (D3 passou)
- 6 serviços active, 0 restarts desde 07:56, logrotate configurado

**Próximos movimentos:** (1) importar repos locais pra nox-mem (plano original, ~45 min), (2) Fase 2 Graphify scale de 3 → 15 repos, (3) Fase 1.7b Memory Quality advanced.

---

## Phase Matrix

| # | Nome | Status | Esforço | Depende de | Exit criteria |
|---|---|---|---|---|---|
| 1 | Quick Wins (wip, feedback, L1) | ✅ DONE | — | — | Concluída 2026-04-11 |
| 1.5 | KG Migration Ollama→Gemini | ✅ DONE | — | 1 | 1489 entities extraídas |
| **0.5** | **Foundation Repair** | ✅ DONE | — | 1.5 | 1951/1951 embedded, canary+morning ativos |
| 24h | Observação pós-Fase 0.5 | ✅ DONE (2026-04-21) | — | 0.5 | Concluída 3d estável — canary 5 OKs consecutivos, nightly limpo, 0 restarts anômalos |
| 1.6 | Search Quality (expansion + dedup) | ✅ DONE | — | 24h | Concluída 2026-04-19 (ver rodapé) |
| 1.7a | Core Memory Quality | ✅ DONE | — | 1.6 | Concluída 2026-04-19 (ver rodapé) |
| 2.5 | graph-memory plugin | ✅ DONE (2026-04-21) | — | 1.7a | Plugin ativo em produção — afterTurn events validados nos logs, provider=anthropic model=claude-sonnet-4-6 ok, vector search ready |
| D1-D4 | Audit sistêmica + pendências | ✅ DONE (2026-04-21) | — | 2.5 | 17 fixes aplicados, check-discord-heartbeat-validation criado, cron session-distill fix, delegação Nox→Atlas validada |
| Path A | Write coordinator | 🟡 REATIVO (não mais PRE-REQ) | 3-5d (fast) se precisar | — | SQLITE_BUSY aparecer em produção = ativar. Trigger busy_timeout=5000 (v3.3) + trg_chunks_delete_cascade tem evitado até agora |
| RP | RelayPlane de verdade | ✅ DONE (2026-04-21 v3.6c) | — | — | `providers.anthropic.baseUrl: "http://127.0.0.1:4100"` + ANTHROPIC_BASE_URL env; requests subiram de 1 (12 dias) pra >6 em 1h; Sonnet+Haiku roteados; budget cap $5/dia/$1/h/$0.50/req efetivo |
| IM | Import repos locais | ⏳ READY | ~45min | RP | Plano em `plans/2026-04-21-session-start.md` — docs-only (*.md) de 10 projetos ~/Claude/Projetos/ + raiz |
| 2 | Graphify + GitHub repos | 🔧 IN PROGRESS (3/~15 repos) | escalando | IM | GRAPH_REPORT.md indexado; query "o que tem no repo X?" responde |
| 1.7b | Memory Quality advanced | 🔒 BLOCKED | 4-6h | 2 | Conflicts detectados; inline entity real-time |
| 3 | HD rsync + enrichment tiered | 🔒 BLOCKED | 1h + tempo rsync | 1.7b | 50+ docs indexados com Tier 1/2/3 |
| 3.5 | Fathom API | 🔒 BLOCKED (opcional) | 3-4h | pré-req API | Reunião indexada <24h |
| 4 | Obsidian view-only | 🔒 BLOCKED | 1h | 3 | Galáxia 3D no Mac |
| Path B-lite | Semantic reflect cache | 🔒 BLOCKED | 2-3h | 1.7a + telemetria | Hit rate ≥40% over 7d |
| Path C | WAL shipping + cold tier | 🔒 BLOCKED | dias | 4 | DB hot <50MB perpetuamente |
| 4b | Obsidian write | 🔒 FUTURO | 2-3h | 4 + 2-4 sem | Zero corrupção em 2 sem |
| 5 | openclaw-memory-sync | 🔒 FUTURO | 1h | 4b | Delay <5min bidirecional |
| SEH | Self-Evolving Hooks | 🔒 INDEPENDENTE | 2h | — | 3+ sessões geram regra aprendida |
| P | Productização nox-supermem | 🔒 HORIZONTE 60d+ | semanas | 4 estável 30d | v3.3 paridade no produto |

Legenda: ✅ done / 🔧 in progress / ⏳ ready / 🟡 reativo (só ativa se sintoma aparecer) / 🔒 blocked

---

## Changelog v1.2 (2026-04-21)

Fases fechadas com evidência da sessão de audit de hoje:
- **24h observação** → ✅ DONE (canary passou 5 vezes consecutivas hoje, 0 restarts desde 07:56, nightly Apr 20 rodou limpo)
- **2.5 graph-memory** → ✅ DONE (validado em logs como ativo processando afterTurn events + provider=anthropic)
- **RelayPlane (novo)** → ✅ DONE (fix crítico do baseUrl no openclaw.json — env var sozinho não basta)
- **D1-D4 (novo)** → ✅ DONE (audit sistêmica do Toto: 17 fixes infra no dia)
- **Import repos (IM, novo)** → ⏳ READY (próxima ação do plano original)

Outras mudanças:
- `dist/reindex.js` patchado pra auto-vectorize inline (fix arquitetural da raiz)
- Canary cron `0 6 → */30` com self-heal automático
- `nightly-maintenance.sh` Phase 6 diário de vectorize (safety net)
- `nox-mem-session-distill` cron corrigido (timeout 3600s, max-sessions 20)
- `discovery.mdns.mode: "off"` explícito no openclaw.json
- Agent DBs (atlas/boris/cipher/forge/lex/nox) ressuscitados com trigger + vetores
- Logrotate ativo em 9 logs nox-*
- `.gitignore` do memoria-nox corrigido (tinha `\n` literal)
- `.claude/CLAUDE.md` espelho deletado, source-of-truth único: `memoria-nox/CLAUDE.md`

Tudo detalhado em `handoffs/2026-04-21-session-handoff.md` + `CLAUDE.md` v3.6c.

---

## Fase 24h — Observação pós-Foundation Repair (ATIVO AGORA)

**Goal:** Validar que os fixes do Tier 0+1 sobreviveram ao stress test do `nightly-maintenance.sh` das 23h.

**Deliverables:**
- [ ] Morning report das 06:30 chega no Discord `#nox-chief-of-staff` sem RED
- [ ] Canary das 06:00 retorna `OK: total=N semantic>0 orphans=0`
- [ ] `nightly-maintenance.log` sem errors novos
- [ ] `vectorCoverage.embedded == total` (watcher pode ter adicionado chunks — OK se ainda 100%)
- [ ] Zero restarts automáticos entre 12:30 e 06:30

**Verificação (rode 1 comando):**
```bash
~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh
```

**Exit criteria:** output do script termina com "All green — safe to proceed to Tier 3".

**Risk:** nightly-maintenance pode expor race condition que `busy_timeout=5000` não cobre.
**Rollback:** restore backup `/root/.openclaw/workspace/backups/nox-mem-pre-nightly-20260418-125019.db` (instruções em `plans/2026-04-18-tier0-tier1-session-log.md`).

---

## Fase 1.6 — Search Quality Upgrade + Telemetria Leve

**Goal:** +30-40% recall em queries ambíguas via query expansion (multi-query rewrite) + diversidade de resultados via dedup 4-layer. Instrumentar telemetria leve para medir impacto.

**Inspiração:** [garrytan/gbrain](https://github.com/garrytan/gbrain) `search/expansion.ts` + `search/dedup.ts` (validado em 14.7K brain files).

**Deliverables:**
- [ ] `src/search-expansion.ts` (~70 LOC) — Gemini 2.5 Flash reescreve query em 3 variantes (original + 2 expansões). Queries <3 palavras pulam expansion
- [ ] Config `expansionEnabled: boolean` no `openclaw.json` — liga/desliga sem deploy. Default `true`
- [ ] Fallback gracioso: se Gemini falhar, usa query original (non-fatal)
- [ ] `src/search-dedup.ts` (~80 LOC) — 4 layers: (1) top 3 por page, (2) similarity >0.85 remove duplicatas, (3) nenhum type >60%, (4) max 2 chunks por page final
- [ ] Wire-up em `src/search.ts` — expansion ANTES do RRF, dedup DEPOIS. Zero mudança no core
- [ ] **Telemetria leve:** tabela `search_telemetry` (query_hash, timestamp, variants_count, results_count, has_semantic, latency_ms) — 1 INSERT por search, sem wrapper complexo
- [ ] Campo em `/api/health.searchTelemetry` reportando last_24h_avg_results, semantic_ratio, p95_latency
- [ ] 15 queries de teste cobrindo: ambígua, específica, muito curta, natural language longa — comparar recall antes/depois

**Depende de:** Fase 24h verde.

**Exit criteria (MEDIDOS):**
- 10 queries de teste mostram ≥3 resultados únicos (era ≤1 em alguns casos com FTS-only)
- Pelo menos 1 query ambígua recupera resultado que BM25 puro não pegava (via match_type=semantic)
- `search_telemetry.has_semantic` true em ≥70% das searches (confirma hybrid real)
- Latência p95 ≤ 1.5s (doc baseline: p95=862ms FTS-only; com expansion vira ~1.2s pela expansion Gemini)

**Risk:** expansion Gemini adiciona ~300ms p95. Mitigação: queries curtas pulam; failover para query original.

**Rollback:** `expansionEnabled: false` no config (sem deploy).

**Estimativa:** 2-3h.

---

## Fase 1.7a — Core Memory Quality

**Goal:** Entidades ricas + economia de API + User Profile carregado no boot dos agentes.

**Inspiração:** [topoteretes/cognee](https://github.com/topoteretes/cognee) (ontology grounding), [garrytan/gbrain](https://github.com/garrytan/gbrain) (source attribution, compiled truth), [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) (user profile).

**Deliverables:**
- [ ] **Ontology Grounding** — prompt de `kg-llm.ts` define campos por tipo: `project` (name, value, status, key_person, ebitda_multiple), `person` (name, role, organization), `document` (name, type, date, parties), `decision` (what, who, date, outcome). Usa `responseSchema` nativo Gemini
- [ ] **Multi-Stage Extraction** (~30 LOC em `kg-llm.ts`) — regex fast-path extrai entidades óbvias antes da chamada LLM: nomes próprios, valores (R$/US$/€), datas, emails, URLs, telefones. Se ≥3 encontradas, pula Gemini (economia 30-40%)
- [ ] **Source Attribution** (gbrain) — campo `source_type` nos chunks: `user_statement` | `compiled` | `timeline` | `external`. RRF fusion aplica boost (user 2x, compiled 1.5x, timeline 1x, external 0.8x)
- [ ] **Compiled Truth Flag** (gbrain) — campo `is_compiled` — consolidados = `true` (síntese), originais = timeline (evidência). Search dá boost para compiled
- [ ] **USER-PROFILE.md** — script `generate-user-profile.ts` que roda semanal (após kg-build) e extrai: top 20 entidades por mention, projetos ativos, decisões últimos 30d, preferências declaradas. Salvo em `shared/USER-PROFILE.md`
- [ ] **Boot injection** — agentes leem `USER-PROFILE.md` no boot (antes de qualquer busca). Economiza re-lookup

**Depende de:** Fase 1.6 concluída (ontology precisa de hybrid search confiável).

**Exit criteria:**
- Query "qual o múltiplo de EBITDA do deal X?" retorna valor específico (não "X é um project")
- kg-build mede redução de ≥30% em chamadas Gemini via fast-path
- USER-PROFILE.md gerado com top 20 entities, projetos ativos, últimas decisões
- Pelo menos 1 agente (Nox) confirma que usa USER-PROFILE.md no boot (log ou resposta explícita)

**Risk:** ontology grounding pode quebrar extrações já feitas. **Mitigação:** rodar em chunks novos apenas; histórico permanece com schema v1.

**Estimativa:** 2-3h.

---

## Fase 2.5 — graph-memory Plugin

**Goal:** Memória de curto prazo em conversas — compressão de contexto (~75%) e recall cross-session automático via [adoresever/graph-memory](https://github.com/adoresever/graph-memory).

**Por que antes da Fase 2:** quando graphify começar a injetar 20K+ entities (Fase 2), o L1 (graph-memory) precisa estar ativo para absorver o volume sem sobrecarregar cada query do WhatsApp.

**Deliverables:**
- [ ] `pnpm openclaw plugins install graph-memory` na VPS
- [ ] Configurar `openclaw.json`: `compactTurnCount: 7`, `recallMaxNodes: 6`, `recallMaxDepth: 2`, LLM via provider padrão, embeddings Gemini endpoint OpenAI-compatible
- [ ] Adicionar `graph-memory.db` ao `backup-all.sh`
- [ ] Teste: conversa no WhatsApp com 10+ turns — verificar compressão efetiva (173K→<30K tokens)
- [ ] Monitorar 1 semana antes de declarar concluída

**Depende de:** Fase 1.7a (USER-PROFILE.md pra contexto inicial rico).

**Exit criteria:**
- Conversa de 7+ rounds cabe em ≤30K tokens de context
- Query "o que conversamos ontem?" retorna recall de sessão anterior
- `graph-memory.db` <50MB após 7 dias de uso

**Risk:** plugin pode conflitar com consolidation do nox-mem. **Mitigação:** DBs e hooks isolados (conforme decisão 6 em nox-neural-memory.md).

**Estimativa:** 30 min setup + 1 semana observação.

---

## Path A — Write Coordinator (🟡 REATIVO, não mais PRE-REQ)

**Decisão 2026-04-19 (reavaliada):** Path A DEIXA DE SER PRE-REQ da Fase 2. Vira **intervenção reativa** — só executamos se evidência de problema aparecer.

### Por que a mudança

Baselines medidos em 2026-04-19 invalidam a premissa original:

| Métrica | Valor atual | Valor que justificaria Path A pre-emptivo |
|---|---|---|
| SQLITE_BUSY 7d | **0** | >50 |
| Writes/dia normal | ~300 | >5000 |
| Writes/dia pós-mesh inbox (estimado) | ~330 | >5000 |
| `/api/health` latência | <10ms | >100ms |
| systemd-run cold start | 40ms | — |

Com volume atual + mesh inbox, estamos **uma ordem de magnitude abaixo** do limite que justificaria Path A preventivo. Fazer 2 semanas de dev pra proteger contra problema não-medido = *premature optimization*.

### Estratégia adotada: rate-limit graphify

Graphify (Fase 2) vai processar em **batches controlados** em vez de dump de 20K entities de uma vez:

- **Batch size:** 500 entities por iteração
- **Pause:** 5min entre batches (dá tempo pro watcher + api respirarem)
- **Horário preferencial:** fora do nightly-maintenance (23:00-01:00 bloqueado)
- **Monitoramento:** canary semântico 06:00 + morning report 07:30 detectam regressão

### Quando ativar Path A (triggers)

Ativar Path A "fast" (3-5 dias de dev, não 2 semanas) **apenas se**:

1. **Canary ou morning-report** reportam SQLITE_BUSY > 0 em 24h consecutivas
2. `/api/health.restartsHour` > 2 em janela rolante de 6h (não causado por deploy manual)
3. Latência p95 de `/api/health` > 100ms (atualmente <10ms)
4. `journalctl -u nox-mem-api | grep -c "database is locked"` > 0 em 7d

Qualquer dos 4 gatilhos ativa Path A como intervenção reativa. Plano fast (não incremental):
- 1 dia: implementar `nox-mem-writer.service` + Unix socket + backpressure queue
- 1-2 dias: migrar todos writers de uma vez (big bang)
- 1 dia: observação + rollback pronto
- Total: 3-5 dias de calendário

### Blueprint detalhado (quando precisar)

`audits/sre-deepening-2026-04-18.md` seção Path A mantém o desenho técnico — só não é mais urgência.

**Exit criteria (quando precisar ativar):**
- Zero SQLITE_BUSY em 48h sob carga pós-graphify
- `/api/health` p95 <10ms durante nightly-maintenance
- Kill do writer durante transação → recovery automático sem perda (integrity_check=ok)

**Rollback:** disable writer service, readers voltam a abrir DB direto.

---

## Fase 2 — Graphify + GitHub Repos (PRIMEIRO GRAFO REAL)

**Goal:** Primeiro grafo real sobre os projetos do Totó. Docs do GitHub viram chunks + entidades consultáveis.

**Fonte:** [safishamsi/graphify](https://github.com/safishamsi/graphify) (71.5x menos tokens via Claude Vision multimodal).

**Deliverables:**
- [ ] `pip install graphifyy` na VPS
- [ ] `graphify install --platform claw` (escreve no AGENTS.md)
- [ ] Criar `/root/vault/projetos/` com symlink `/root/.openclaw/workspace/vault → /root/vault`
- [ ] **Teste piloto**: 1 repo pequeno (ex: `memoria-nox` ou `nox-supermem`) antes de comprometer escopo total — valida output + volume de writes real
- [ ] Definir com Totó: lista priorizada de repos (todos 20+? só Nuvini+FII+Granix? Tier 1 vs Tier 2?)
- [ ] Script: clonar repos priorizados em `/root/vault/projetos/`
- [ ] **Rate-limit (novo — substitui Path A pre-emptivo):**
  - Config graphify `--batch-size 500 --pause 300` (500 entities + 5min pause)
  - **Janela proibida:** 22:30-01:30 BRT (não concorre com nightly-maintenance)
  - Monitorar SQLITE_BUSY em morning-report; se >0 em 24h, pausar graphify + ativar Path A reativo
- [ ] `graphify /root/vault/projetos/ --batch-size 500 --pause 300` — primeiro build rate-limited
- [ ] Analisar `GRAPH_REPORT.md`: god nodes? Conexões surpresa? Volume de writes real
- [ ] Cron horário: `git pull` em todos os repos (com lock para não concorrer com nightly)
- [ ] Cron diário 02:00: `graphify --update /root/vault/` (rebuild incremental, fora da janela do nightly)
- [ ] Agentes leem `GRAPH_REPORT.md` no boot
- [ ] nox-mem ingest `GRAPH_REPORT.md` (ponte graphify → hybrid search)
- [ ] **Semantic Chunking** (gbrain, ~150 LOC em `chunkers/semantic.ts`): embed por frase, cosine adjacentes, Savitzky-Golay filter (5-window, 3rd-order) para topic boundaries. Fallback graceful para recursive chunker. Aplica a chunks novos apenas; existentes ficam com v1

**Depende de:**
- Fase 2.5 (graph-memory) estável 7d — confirma que não há conflito entre context engines
- NÃO depende mais de Path A (ver seção Path A revisada — strategy rate-limit substitui)

**Exit criteria:**
- Piloto em 1 repo pequeno roda sem SQLITE_BUSY
- `graphify query "o que tem no repo sao-thiago-fii?"` retorna resposta com source citada
- ≥80% dos repos priorizados do Totó estão indexados
- Chunks de PPTX/PDF novos usam semantic chunking (verificável via metadata `chunker: "semantic"`)
- SQLITE_BUSY 7d = 0 durante + após o build inicial

**Risk + Mitigação:**
- 21GB de HD rsync + 5-10GB de repos ocupa ~30GB no /root (tem 148GB livre — ok)
- Volume de writes: mitigado por rate-limit acima; se sintoma aparecer → Path A reativo

**Estimativa:** 30min piloto + 2-3h setup pleno + tempo do primeiro build (depende do volume de repos — rate-limited).

---

## Fase 1.7b — Memory Quality Advanced

**Goal:** Detecção de contradições, versionamento de fatos, auto-esquecimento inteligente, entity detection real-time.

**Inspiração:** [kraklabs/mie](https://github.com/kraklabs/mie) (conflict detection, invalidation chains), [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) (smart forgetting), [MemPalace/mempalace](https://github.com/MemPalace/mempalace) (verbatim preservation), [garrytan/gbrain](https://github.com/garrytan/gbrain) (inline entity detection).

**Deliverables:**
- [ ] **Reasoning Traces** — novo chunk_type `reasoning_trace`: (query, fontes consultadas, dados extraídos, resposta). Queries similares futuras encontram via hybrid search
- [ ] **Conflict Detection** (SQL query em `kg-build`, ~20 LOC) — entidades com mesmo nome + atributos conflitantes. Exemplo: "FII 2400m² vs 3200m²". Marca para revisão
- [ ] **Invalidation Chains** — campos `valid_until` + `superseded_by` em `kg_entities`. Atualização marca antiga + referencia nova. **REGRA CRÍTICA: entidades com `superseded_by` são IMUNES a TTL (Smart Forgetting)** — arquivadas, nunca deletadas
- [ ] **Smart Forgetting** (~10 LOC em extractor) — TTL inteligente: fatos temporais ("prova amanhã") = data + 7d; permanentes = 90d atual. Exceto entidades superseded
- [ ] **Source Text Preservation** — campo `source_text` na `kg_entities` guardando verbatim. Fallback quando extração não cobre
- [ ] **Hierarchical Tagging** (mudança de prompt) — 3 campos: `scope` (nuvini/fii-sao-thiago/toto), `category` (decisions/contracts/people), `topic` (pricing/ebitda/terreno). +34% retrieval accuracy (MemPalace)
- [ ] **Inline Entity Detection** — regex fast-path em cada mensagem WhatsApp/Discord. Se ≥3 entities (nomes/valores/datas), gravar direto no KG sem LLM. Se <3, chamar Gemini Flash async. KG real-time

**Depende de:** Fase 2 estável 7d (conflicts só fazem sentido com documentos reais chegando).

**Exit criteria:**
- Query de teste "FII tem 2400m² ou 3200m²?" retorna alerta de conflito
- Zero entidades `superseded_by` deletadas por TTL após 30d
- ≥50% das mensagens no Discord com entities são detectadas e gravadas <500ms

**Risk:** inline entity detection com regex pode gerar falsos positivos poluindo KG. **Mitigação:** confidence score + review threshold.

**Estimativa:** 4-6h + testes.

---

## Fase 3 — HD Mac rsync + Enrichment Tiered

**Goal:** Documentos pessoais (PPTX/PDF/XLSX/DOCX) do Mac indexados. Enrichment classificado por importância.

**Deliverables:**
- [ ] Script `~/sync-vault.sh` no Mac (rsync via Tailscale, filtro por extensão, exclude DS_Store + node_modules)
- [ ] Definir com Totó: pastas prioritárias em `~/Documents/` (21GB total; começar com 1-2 pastas)
- [ ] Primeiro rsync manual
- [ ] `graphify --update` processa
- [ ] launchd Mac: sync diário às 02:00
- [ ] **Enrichment Pipeline Tiered** (gbrain):
  - Tier 1 (≥5 mentions): cross-reference todos chunks + compiled truth + conflict validation
  - Tier 2 (2-4 mentions): cross-reference + timeline
  - Tier 3 (1 mention): raw preservation
  - Classificação automática em kg-build

**Depende de:** Fase 1.7b + disk check VPS (verificado: 148GB livre — ok para 21GB rsync).

**Exit criteria:**
- ≥50 docs do HD indexados
- "Qual a área do terreno de Sorocaba?" responde com XLSX indexado
- Tier 1 entities (ex: Sorensen, Nuvini) têm compiled truth gerado

**Estimativa:** 1h setup + tempo rsync inicial.

---

## Fase 3.5 — Fathom API (opcional, paralela)

**Goal:** Reuniões indexadas automaticamente sem esforço manual. **Não bloqueia Fase 4.**

**Pré-requisito (VALIDAR ANTES):**
- [ ] Fathom tem API REST pública?
- [ ] Auth token disponível? Rate limits?
- [ ] Export de transcrições com speakers identificados?

**Se API existir:**
- [ ] Script Python puxa calls novas → `.md` em `/root/vault/reunioes/`
- [ ] Cron noturno 01:00
- [ ] graphify update processa

**Exit criteria:** reunião de hoje indexada até 24h depois.

**Estimativa:** 3-4h (se API viável).

---

## Fase 4 — Obsidian View-Only

**Goal:** Visualizar segundo cérebro no Mac como galáxia 3D — read-only, zero risco de corrupção.

**Deliverables:**
- [ ] graphify gera `graphify-out/obsidian/` como vault pronto
- [ ] rsync noturno VPS → Mac (`~/ObsidianVault/`)
- [ ] Instalar plugins Obsidian: BRAT + 3D Graph, Dataview, Graph Analysis (20 min)
- [ ] Cron launchd: sync diário

**Depende de:** Fase 3 (precisa de dados volumosos para grafo 3D fazer sentido).

**Exit criteria:** grafo 3D rotacionável mostrando clusters reais (projetos/pessoas/documentos).

**Estimativa:** 1h.

---

## Path B-lite — Semantic Reflect Cache

**Goal:** Upgrade do reflect_cache de exact-hash para semantic-key — cache hit quando query é semanticamente similar (cosine >0.92) a uma anterior. **Skip dep-set invalidation** (perf-engineer provou que é correctness trap: watcher DELETE+INSERT = chunk_ids não estáveis).

**Detalhado:** `audits/perf-baseline-2026-04-18.md` seção Path B critique.

**Deliverables:**
- [ ] Tabela `reflect_cache_vec` com embedding da query + resposta cached
- [ ] On reflect: embed query → semantic search na tabela cache → se cosine >0.92, retornar cached
- [ ] Manter TTL 24h (evita staleness sem dep-set)
- [ ] Métrica `reflectCache.semantic_hit_rate` em `/api/health`

**Depende de:** Fase 1.7a (ontology enriquece queries, melhora probabilidade de hit) + 7 dias de telemetria de reflect.

**Exit criteria:** semantic hit rate ≥15% over 7d (abaixo disso, +300ms query embedding é regressão net).

**Risk:** 0.92 é thumb-sucked. **Mitigação:** log de near-misses (0.85-0.91) para recalibrar threshold.

**Estimativa:** 2-3h.

---

## Path C — WAL Shipping + Cold Tier (HORIZONTE 60d)

**Goal:** Backup contínuo sem perda + DB hot perpetuamente <50MB.

**Deliverables:**
- [ ] WAL shipping automático para volume secundário (ou Tailscale peer)
- [ ] Cold tier DB (chunks com `tier='peripheral' AND access_count=0 AND age>90d` → archive DB comprimido)
- [ ] Query router: chunks não encontrados em hot → fallback cold (async)

**Depende de:** Fase 4 estável 30d (baseline de acesso real para classificar tiers).

**Exit criteria:** hot DB <50MB permanentemente, cold tier mantém histórico completo.

**Estimativa:** dias.

---

## Fase 4b + 5 — Obsidian Write + Bidirectional Sync (FUTURO)

**4b:** Obsidian escreve → reconcilia com nox-mem via agente noturno. Pré-requisito: 2-4 semanas em view-only sentindo falta.

**5:** Plugin [YearsAlso/openclaw-memory-sync](https://github.com/YearsAlso/openclaw-memory-sync) conecta porta 18789, sync bidirecional <5min.

---

## SEH — Self-Evolving Hooks (INDEPENDENTE)

**Goal:** Claude Code local (Mac) aprende com correções do usuário e transforma em regras permanentes.

**Spec:** `specs/2026-04-12-self-evolving-hooks.md`.

**Independente das outras fases** — pode rodar em paralelo. Bridge Local→VPS opcional (dream worker ingere regras no nox-mem via `/api/ingest`).

**Estimativa:** 2h.

---

## Fase P — Productização NOX-Supermem (HORIZONTE 60d+)

**Goal:** Empacotar nox-mem v3.3+ estável como produto comercial Hotmart.

**Repo:** `github.com/totobusnello/nox-supermem` (private). Estado: scaffold v2.1.2, ~10% implementação, stale 33d.

**Regra:** NÃO atacar enquanto evolução interna está ativa. Aguardar Fase 4 estável 30d.

**Deliverables (quando chegar a hora):**
- [ ] Rebase: copiar v3.3+ sanitizada → nox-supermem
- [ ] Generalizar: substituir `OPENCLAW_WORKSPACE` hardcoded por `getConfig()` em todos módulos
- [ ] `install.sh` completo com detecção de ambiente
- [ ] Tiers A/B/C definidos (docs, perfis, suporte)
- [ ] Landing + Hotmart setup

**Depende de:** Fase 4 concluída + 30d estável.

**Estimativa:** semanas.

---

## Cross-Cutting Concerns

### Observabilidade (camadas)

1. **HOJE:** canary 06:00 + morning report 06:30 + `check-nox-mem.sh` local
2. **Fase 1.6:** adicionar `search_telemetry` table + campo em `/api/health`
3. **Fase 1.7a:** telemetria por agente (quem usa USER-PROFILE no boot, frequência)
4. **Fase 2.5:** graph-memory metrics (compression ratio, recall hits)
5. **Path A:** writer queue depth, backpressure events, IPC latency
6. **Fase 2:** graphify build metrics, chunks added per day

### SLOs (de `audits/sre-deepening-2026-04-18.md`)

- Availability ≥ **99.5%** (single VPS, não 99.9%)
- Search p95 ≤ **500ms** (hoje 862ms — meta atingida após Fase 1.6)
- Reflect cache hit rate ≥ **40%** over 7d
- Consolidation staleness < **72h**
- **Zero** partial writes (apenas Path A garante)

### Backup strategy

- Daily: `backup-all.sh` às 02:00 (7d retention)
- Pre-release snapshots: `backups/tier0-*`, `tier1-*`, `gaps-fix-*`, `nox-mem-pre-nightly-*`
- WAL checkpoint: */6h
- Path C introduzirá WAL shipping

### Canário não-negociável

Teste `match_type: "semantic"` em resultado de search é **o** canário de sanidade. Nunca remover. Se sumir, Layer 2 morreu. Canary script em `/root/.openclaw/scripts/semantic-canary.sh`.

---

## Decisões Ainda Válidas (filtradas do nox-neural-memory v12)

| # | Decisão | Motivo |
|---|---|---|
| 1 | Query Strategy — Nox decide pelo tipo | Sem custo duplo, auditável |
| 2 | graphify vs nox-mem KG — complementares | Camadas diferentes (docs vs memória operacional) |
| 3 | Vault separado do workspace (`/root/vault/` + symlink) | Workspace pode crescer sem poluir stats/backups |
| 4 | Cross-Agent via SOUL.md (não algorítmico) | Over-engineering para 6 agentes |
| 5 | Obsidian = painel visual, não memória | Memória vive em nox-mem.db + graph-memory.db + graph.json |
| 6 | KG extraction Gemini 2.5 Flash (não Ollama) | 500 RPM free, thinkingBudget:0, stable |
| 7 | graph-memory plugin complementa (não substitui) | Curto prazo vs longo prazo, DBs isolados |
| 8 | Estratégia de camadas hot/warm/cold | 20K-70K entities: busca direta inviável |
| 9 | Notion = Tarefas & Deals apenas | Memória migra para nox-mem + Obsidian |
| 10 | TTL + Invalidation: `superseded_by` imune a TTL | Sem isso, histórico se perde no Smart Forgetting |
| 11 | **NOVO (0.5)** `/api/health` via JOIN source-of-truth | COUNT isolado mente sobre órfãos |
| 12 | **NOVO (0.5)** Semantic canary diário | Fail-silent é o pior tipo de falha |
| 13 | **NOVO (0.5)** Port via env (`NOX_API_PORT`) | Chrome squatter em :18800 — nunca hardcode |

---

## Explicitamente NÃO FAZEMOS

| Item | Razão |
|---|---|
| Migrar nox-mem para Postgres/PGLite (gbrain engine) | Adicionaria daemon + autovacuum + backup. SQLite WAL atende <5ms para 1.951 chunks. Revisitar se >500K entities |
| Adotar git-as-source-of-truth (gbrain markdown) | Filosofias opostas de storage. Significaria reescrever nox-mem do zero. Features individuais portáveis; arquitetura não |
| 30 MCP tools (gbrain) | Mais tools = mais manutenção. Manter 16 atuais; capabilities via search quality |
| Memgraph / Neo4j | Over-engineering para 371 entities. Revisitar se >500K |
| Atomic hybrid query (CTE única) | Latência atual <100ms. Ganho marginal |
| Dashboard React como roadmap item | Já existe (`agent-hub-dashboard`). Não reverter para roadmap |
| Expertise profiling automático | Over-engineering para 6 agentes com papéis fixos |
| Text2Cypher | Sem graph DB, não há Cypher |
| Productizar nox-supermem em paralelo com evolução interna | Divergência acumulada já é 6 meses. Priorizar paridade antes |

---

## Ritual de Progressão

**Checkpoint por fase:**
1. Executar deliverables (checkboxes)
2. Rodar verificação (comandos listados na fase)
3. Validar exit criteria (medidos, não feelings)
4. Atualizar `docs/nox-neural-memory.md` e este plano marcando fase como ✅
5. Executar canary + morning report = tudo verde
6. Observar 24-48h antes de avançar próxima fase

**Checkpoint semanal:**
- Revisar métricas em `/api/health`
- Checar `morning-report` tendências (restart count, 429 count, hit rate)
- Ajustar prioridades com base em tráfego real

**Checkpoint mensal:**
- Revisar decisões nesta lista — alguma virou obsoleta?
- Reavaliar "NÃO FAZEMOS" — alguma premissa mudou?
- Estimar quando Fase P (productização) fica viável

---

## Links Canônicos

- Visão estratégica: `docs/nox-neural-memory.md` (v12)
- Handoff da sessão 2026-04-18: `plans/2026-04-18-tier0-tier1-session-log.md`
- Audits de hoje: `audits/audit-2026-04-18-db-gaps-remediation.md`, `audits/sre-deepening-2026-04-18.md`, `audits/perf-baseline-2026-04-18.md`
- Paper técnico (stale, refletir v3.0.0): `paper-tecnico-nox-mem.md`
- Ferramenta de check local: `scripts/check-nox-mem.sh`
- VPS canonical: `ssh root@100.87.8.44:/root/.openclaw/workspace/`

---

## Fase 1.6 — Resultado (2026-04-19)

**Status:** ✅ Todos exit criteria atendidos no teste de aceitação com 15 queries.

**Entregas:**
- `src/search-expansion.ts` (multi-perspective via Gemini 2.5 Flash, 2 variantes + original)
- `src/search-dedup.ts` (4 layers: per-file cap 3, Jaccard sim ≥0.85, type saturation 60%, final cap 2/file)
- `src/search.ts` — expansion em paralelo com search original; variantes feed FTS; semantic só na query original (decisão que tirou ~800ms do p95)
- Schema v6: tabela `search_telemetry` + flag `meta.expansion_enabled` (default true; toggle via SQL sem deploy)
- `/api/health.searchTelemetry` (count_24h, avg_results, semantic_ratio, p95_latency_ms, expansion_enabled, skip_reasons)
- Script de aceitação: `test-phase-1.6.sh` (15 queries: ambíguas, específicas, too-short, NL longa)

**Métricas (15 queries):**
- Queries com ≥3 resultados únicos: **15/15** (target ≥10)
- Queries com semantic match: **15/15 = 100%** (target ≥70%)
- p95 latência: **1399ms** (target ≤1500ms)
- Latência média: **965ms**

**Evidência de semantic-only recall:** query "coisa da memória quebrada" → BM25 puro retorna **0 resultados**; hybrid com expansion retorna **3 matches semânticos relevantes** (chunks sobre DB corrompido + WAL stale).

**Decisões de implementação que viraram doutrina:**
1. **FTS para variantes, semantic só para original** — paráfrases de query são near-redundantes no espaço vetorial (mesmo cluster de embeddings). Usar Gemini embed para cada variante gastava 900ms de latência sem ganhar recall. Keyword variedade é onde expansion ajuda; semantic ignora vocabulário.
2. **Expansion em paralelo, não serial** — kickoff de `search(original) + searchSemantic(original)` acontece **antes** do await na expansão. Economiza 500-800ms no caminho comum.
3. **`expansion_enabled` na tabela `meta`, não em `openclaw.json`** — binary v2026.3.31 rejeita chaves root desconhecidas (crash loop 2026-04-01). `meta` é schema-compatible e permite toggle sem deploy (`UPDATE meta SET value='false' WHERE key='expansion_enabled'`).
4. **Telemetria via query_hash sha1** — privacidade: não armazenamos texto cru da query. Hash de 16 chars é suficiente para ver padrões.

**Próximo:** Fase 1.7a (Core Memory Quality — ontology grounding + USER-PROFILE.md + multi-stage extraction).

---

## Fase 1.7a — Resultado (2026-04-19)

**Status:** ✅ Todos exit criteria atendidos.

**Entregas:**
- Schema v7: `kg_entities.attributes` (JSON) + `chunks.source_type` + `chunks.is_compiled` + 2 indexes
- `src/kg-llm.ts`: ontology grounding prompt (campos ricos por tipo) + fast-path regex PT-BR (R$/US$/€, CNPJ/CPF, datas BR, telefones +55, emails, URLs, percentagens, proper nouns) + backfill de attributes em `kg_entities` via merge JSON
- `src/index.ts` (`kg-extract`): merge incremental de attributes + contador fast-path
- `src/search.ts`: boost por `source_type` (user 2.0x · compiled 1.5x · timeline 1.0x · external 0.8x) em FTS e semantic
- `src/generate-user-profile.ts` (novo): gera `shared/USER-PROFILE.md` com top 20 entidades, projects ativos, decisões 30d, preferências
- Cron `generate-user-profile` (Dom 21:00 via openclaw cron)
- Boot injection em 6/6 SOUL.md: Nox, Atlas, Boris, Cipher, Forge, Lex leem USER-PROFILE no start

**Métricas (teste 10 chunks):**
- Fast-path hits: **30% (3/10 chunks)** — meta ≥30% ✅ (Gemini API calls economizados)
- Extraction: 41 entities + 16 relations em 10 chunks
- USER-PROFILE.md: 8KB, 371 entities agregadas
- Backfill source_type: 2290 chunks classificados (timeline 99.7%, external 0.3% — heurísticas conservadoras; calibra em sessão futura)

**Decisões de implementação que viraram doutrina:**
1. **Attributes em JSON (não tabelas normalizadas)** — schema rico sem migrations por campo. Merge preserva dados existentes, overwrites chaves novas. Trade-off: sem indices por campo, mas volumes (<500 entities/type) não pedem.
2. **Fast-path threshold = ≥3 hits estruturados (ignora proper_noun solo)** — evita falsos positivos (capitalizações random viram entidades).
3. **Boost source_type multiplicativo em cima do existing** (tier, type, recency) — ordem de aplicação não matters por serem independentes.
4. **USER-PROFILE.md em `shared/`** (not `agents/<x>/`) — single source, 6 agentes leem mesmo arquivo. Regenerado semanal, não manual.
5. **Boot injection por append em SOUL.md** (não edit pontual) — idempotente (grep USER-PROFILE antes de adicionar), reversível (delete da seção).

**Pendente (melhoria futura, não gating):**
- Calibrar heurística de backfill `source_type` — hoje só 6 chunks external + 2284 timeline; nenhum user_statement/compiled. Revisar patterns em sessão dedicada.
- Validar query "múltiplo EBITDA do deal X" retorna valor específico (precisa rodar `kg-extract` full para popular attributes).

**Próximo:** Fase 2.5 (graph-memory plugin) ou Fase 1.8 (Agent Mesh completo — dispatch_to + 9 security controls), conforme prioridade.

---

## Fase 2.5 — Setup (2026-04-19)

**Status:** 🔧 IN OBSERVATION (1 semana). Setup concluído; exit criteria aguarda conversas reais.

**Entregas:**
- `openclaw plugins install graph-memory` via ClawHub community → v1.5.8 em `/root/.openclaw/extensions/graph-memory/`
- `openclaw.json` configurado:
  - `plugins.slots.contextEngine: "graph-memory"` (CRÍTICO — sem isso plugin não ingeria)
  - `plugins.allow` incluindo `graph-memory` (22 plugins explicitamente trusted)
  - `plugins.entries.graph-memory.enabled: true`
  - `config.embedding: { baseURL: generativelanguage.googleapis.com/v1beta/openai/, model: gemini-embedding-001, dimensions: 3072 }`
  - `config.llm`: default (Anthropic via env)
- Defaults de extração honrados: `compactTurnCount: 7`, `recallMaxNodes: 6`, `recallMaxDepth: 2`
- `graph-memory.db` em `/root/.openclaw/graph-memory.db` (schema: gm_messages, gm_nodes, gm_edges, gm_communities, gm_vectors, gm_nodes_fts)
- Backup daily em `backup-all.sh`: SQLite `.backup` API + keep 7 days (`graph-memory_YYYY-MM-DD.db`)
- Gateway restart com 14 plugins loaded
- `[graph-memory] vector search ready` confirmado nos logs

**Descobertas relevantes:**
1. **Gemini OpenAI-compat embedding**: `text-embedding-004` **não existe** na v1main; o correto é `gemini-embedding-001` com 3072d nativo.
2. **plugins.slots.contextEngine é gating**: sem isso, o plugin registra mas ingest/assemble/compact nunca dispara — seria falha silenciosa.
3. **ClawHub auto-install** populou `plugins.allow` com 22 entries (whatsapp, discord, telegram, slack, anthropic, openai, brave, active-memory, memory-core, memory-wiki, graph-memory, etc.) — não precisou configurar manualmente.

**Exit criteria (a medir em 7 dias):**
- [ ] Conversa 7+ turns mede ≤30K tokens no contexto (README do plugin: R7 com graph-memory = 23.977 vs 95.187 sem — 75% compressão)
- [ ] Query "o que conversamos ontem?" retorna recall de sessão anterior
- [ ] `graph-memory.db` < 50MB após 7 dias de uso
- [ ] Zero conflito com active-memory (plugin bundled que também injeta memória antes de replies)

**Pendências (para sessão futura):**
- Monitorar overlap entre `graph-memory` (context engine slot) e `active-memory` (before_prompt_build hook bundled) — podem estar duplicando
- Dashboard visual do grafo não configurado (plugin tem UI mas não ativa por default)
- Comunidades serão formadas após ~7 turns de conversa — primeira "PageRank + community detection" acontece automaticamente

**Próximo:** Após 7 dias de observação, Fase 2 (Graphify + GitHub) rate-limited. Path A virou reativo (ver decisão 14).

---

## Decisão 14 (2026-04-19) — Path A vira reativo + rate-limit graphify substitui

**Contexto:** Path A era listado como PRE-REQ de Fase 2 com estimativa de 2 semanas. Baselines medidos hoje invalidam a premissa:
- SQLITE_BUSY 7d = 0 (não existe o problema que Path A resolveria)
- Writes/dia atuais = ~300 (uma ordem de magnitude abaixo do limite)
- `/api/health` latência = <10ms (sem contenção visível)

**Nova estratégia:**
1. **Pular Path A preventivo** — não gastar 2 semanas protegendo contra problema não-medido
2. **Graphify rate-limited** — batches 500 + pause 5min + janela proibida 22:30-01:30 BRT substitui proteção arquitetural
3. **Path A vira REATIVO** — plano fast (3-5d big-bang) pronto pra ativar SE aparecer:
   - SQLITE_BUSY > 0 em 24h consecutivas
   - /api/health.restartsHour > 2 em 6h (não-deploy)
   - Latência p95 > 100ms
   - `database is locked` no journalctl em 7d
4. **Monitoramento reforçado:** morning-report 07:30 + canary 06:00 + cipher weekly 10:00 pegariam sintomas cedo

**Nova ordem de execução (após Fase 2.5 em observação 7d):**

| # | Fase | Esforço | Gating |
|---|---|---|---|
| 1 | Observar graph-memory 7d (em curso) | passivo | canary verde · compressão medida |
| 2 | **Fase 2 — Graphify + GitHub (rate-limited)** | 2-3h + build | SQLITE_BUSY 0; piloto OK |
| 3 | 7d observação Fase 2 rodando | passivo | zero regressão |
| 4 | Fase 1.7b (Memory Advanced) | 4-6h | Fase 2 estável |
| 5 | Fase 3 (HD Mac rsync + enrichment tiered) | 1h + rsync | Fase 1.7b concluída |
| 6 | Fase 4 (Obsidian view-only) | 1h | Fase 3 estável |
| 7 | Productização (Fase P) | horizonte 60d+ | Fase 4 estável 30d |

**Timeline revisado: 3-4 semanas pra Fase 4** (era 5-6 semanas com Path A preventivo) — economia de ~2 semanas.

**Se Path A for ativado reativo:** insere 3-5 dias de intervenção entre o sintoma e o próximo passo. Atraso aceitável dado que a probabilidade é baixa.

**Rationale da decisão:**
- Engenharia honesta: hedge contra problema sem evidência empírica = premature optimization
- Observabilidade já coberta (morning-report, canary, cipher) — sintomas seriam vistos em <24h
- Rollback do graphify é trivial (`systemctl stop` + `graphify --clear`); Path A depois seria puro ganho

**Quem aceitou:** Totó, 2026-04-19.

---
