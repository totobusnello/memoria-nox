# memoria-nox — Projeto de Memória Inteligente para OpenClaw

## O que é este repo

Documentação, specs, plans e paper técnico do sistema de memória **nox-mem** (v3.0.0, deployado na VPS) e do produto comercial **NOX-Supermem** (em desenvolvimento no repo `nox-supermem`).

## Estrutura

```
memoria-nox/
├── specs/
│   ├── 2026-03-14-nox-memory-system-design.md       — Spec técnico do nox-mem
│   ├── 2026-04-12-self-evolving-hooks.md            — Spec: feedback loop automático (hooks)
│   └── (2026-03-14-nox-supermem-produto-design.md   — movido para nox-supermem/)
├── plans/
│   ├── 2026-03-14-nox-memory-system.md               — Plan técnico (executado)
│   └── (2026-03-14-nox-supermem-produto.md           — movido para nox-supermem/)
├── audits/
│   ├── audit-2026-04-08-stability.md                 — Audit de estabilidade VPS
│   ├── audit-2026-04-08-live-vps.md                  — Audit live da VPS
│   └── hardening-report-2026-04-08.md                — Relatório de hardening
├── paper-tecnico-nox-mem.md                           — Paper técnico completo (12 seções)
├── paper-tecnico-nox-mem.docx                         — Versão Word do paper
└── .claude/CLAUDE.md                                  — Este arquivo
```

## Sistema nox-mem v3.6d (deployado 2026-03-23, hardened 2026-03-31, Tier 0+1 fixes 2026-04-18, audit sistêmica + RelayPlane + item D + active-memory migration 2026-04-21)

- **VPS:** ssh root@187.77.234.79 (público) / ssh root@100.87.8.44 (Tailscale), Hostinger KVM 4
- **Path:** `/root/.openclaw/workspace/tools/nox-mem/`
- **Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings (3072d), inotifywait, systemd
- **OpenClaw:** v2026.4.15 (commit `041266a`, binário, requer Node.js 22.12+) — **com monkey-patch em `dist/restart-stale-pids-*.js` pra fix Issue #62028 (ainda não corrigido upstream nesta versão)**, rollback para v2026.3.31 disponível se necessário
- **Node.js:** v22.22.2 com wrapper `--no-warnings` em `/usr/bin/node` (suprime DEP0040 punycode que causava crash loop)
- **RelayPlane:** v1.8.37 (proxy inteligente de roteamento AI, atualizado 2026-03-31)

### Schema v7 (Apr 19)
- `chunks` + `chunks_fts` (FTS5 porter unicode61) — **1,975 chunks**, com `source_type` (user_statement|compiled|timeline|external) e `is_compiled` (V7, adicionados pelo Forge)
- `consolidated_files` — 18 done, 0 failed
- `meta` — key-value config
- `vec_chunks` + `vec_chunk_map` — sqlite-vec embeddings (**1,975 / 1,975 = 100% coverage** pós re-embed 2026-04-19 22:39 — incident v3.4)
- `kg_entities` (~371) + `kg_relations` (~500) — Knowledge Graph v2 (Gemini 2.5 Flash extraction, migrado 2026-04-11)
- `decision_versions` — tracked decisions
- `dedup_log` — duplicate audit trail
- `reflect_cache` — Gemini Flash synthesis cache (TTL 24h, colunas `hit_count` + `last_hit_at` 2026-04-18)
- **Trigger `trg_chunks_delete_cascade`** — AFTER DELETE ON chunks limpa vec_chunks + vec_chunk_map (previne órfãos, instalado 2026-04-18)

### Hybrid Search (default, 3 camadas — semantic restaurada 2026-04-18)
- Layer 1: FTS5 BM25 (keyword, type boost 2x, recency 1.5x) → `match_type: "fts"`
- Layer 2: Gemini semantic (gemini-embedding-001, 3072d, sqlite-vec) → `match_type: "semantic"`
- Layer 3: RRF fusion (k=60, content dedup) → tag `[hybrid]`
- sqlite-vec carrega via `loadVecSafe()` em embed.js (path direto + fallback)
- **Atenção:** entre ~mar/2026 e 2026-04-18 a Layer 2 estava silenciosamente quebrada (0 embeddings vivos, todos vec_chunk_map órfãos). Search devolvia [hybrid] mas era 100% BM25. Fix no Tier 1 2026-04-18.

### Knowledge Graph v2
- ~371 entidades, ~500 relações, 11 tipos (project, tool, concept, person, org, agent, etc.)
- LLM extraction via Gemini 2.5 Flash (migrado de Ollama 2026-04-11, thinkingBudget:0, JSON schema nativo)
- TTL: 90 dias, confidence decay -0.1/30d, prune threshold 0.3
- Graph traversal: BFS path finding entre entidades

### CLI (25+ comandos)
`search/ingest/reindex/primer/stats/consolidate/retry-failed/digest/sync-notion/doctor`
`vectorize/kg-stats/kg-query/kg-extract/kg-path/kg-build/kg-merge/kg-prune`
`cross-search/cross-stats/agent-profiles/agent-insights/cross-kg`
`self-improve/decision-set/decision-get/decision-history/decision-list`
`reflect/crystallize/crystallize-validate` (Hermes upgrades 2026-04-13)

### MCP Server (16 tools)
`nox_mem_search` (hybrid), `stats`, `primer`, `ingest`, `cross_search`, `cross_stats`, `metrics`
`kg_build`, `kg_query`, `kg_stats`, `agent_profiles`, `cross_kg`, `kg_path`, `self_improve`
`nox_mem_reflect`, `nox_mem_crystallize` (Hermes upgrades 2026-04-13, build consertado 2026-04-18)

### HTTP API Server (porta 18802 — era 18800, Chrome squata :18800)
10 endpoints:
- Core: `/api/health`, `/api/agents`, `/api/kg`, `/api/kg/path`, `/api/search`, `/api/cross-kg`
- Hermes: `/api/reflect?q=...&nocache=1`, `/api/procedures`, `POST /api/crystallize`, `POST /api/crystallize/validate?id=N`
- Porta real: controlada por `NOX_API_PORT` em `/root/.openclaw/.env` (hoje 18802)
- Systemd: `nox-mem-api.service` (Type=simple)

### 6 Serviços systemd (todos ativos)
- `openclaw-gateway` (:18789 WS, Type=simple, Restart=always)
  - `StartLimitBurst=5` + `StartLimitIntervalSec=120` (crash loop protection)
  - `ExecStartPre=fuser -k 18789/tcp` (mata orphans por porta antes de iniciar)
  - `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` (via RelayPlane)
- `relayplane-proxy` (:4100, proxy AI routing, v1.8.37)
  - Cascade fallback: Sonnet → Haiku → DeepSeek R1 (Groq) → Qwen3 32B (Groq) → Llama 70B (Groq)
  - `maxEscalations: 4`, `escalateOn: error`
  - Complexity routing: simple=Haiku, moderate=Sonnet, complex=Opus
  - Budget: $5/dia warn, $1/hora warn, $0.50/request block
- `claude-telegram.service` — **DESABILITADO** (2026-03-31, conflitava com gateway Telegram)
- `nox-mem-watcher` (inotifywait, debounce 15s, heartbeat)
- `nox-mem-api` (:18802 HTTP JSON — configurável via `NOX_API_PORT` no .env)
- `tailscaled` (100.87.8.44)

**Nota sobre Ollama (removido dos serviços ativos):** Ollama foi desabilitado em 2026-04-11 quando KG extraction migrou pra Gemini 2.5 Flash. Serviço está `inactive, disabled` no systemd. Não há mais dependência viva. Se reativar no futuro (fallback CPU offline), verificar consumo de memória (KEEP_ALIVE=5m era a mitigação).

### Cron Jobs (consolidados em nightly-maintenance.sh pós-2026-04-01)
- **Serial runner único às 23:00** via `/root/.openclaw/scripts/nightly-maintenance.sh` executa: reindex → consolidate → vectorize → kg-build → kg-prune → session-distill em ordem determinística (elimina race conditions entre writers)
- */5 min: `/root/.openclaw/scripts/health-probe.sh` (probe de serviços; lê `${NOX_API_PORT}` do .env pós-2026-04-18)
- 02:00: SQLite backup (7d retention)
- 03:00: backup completo (`/root/.openclaw/scripts/backup-openclave.sh`)
- */6h: git backup + WAL checkpoint
- **DEPRECATED (2026-04-01):** `session-context.json` e `active-tasks.md` → migrados para SESSION-STATE.md
- **REMOVIDO:** `claude-tg-watchdog.sh` (recriava bot Telegram duplicado a cada 5min)
- **Histórico:** antes da consolidação, cron tinha ~29 entries com heavy writers rodando em paralelo — docs antigos mencionam essa config

### Segurança e Hardening (2026-03-31)
- **Firewall (ufw):** deny default, SSH aberto, portas 18789/18802/4100 restritas a Tailscale (100.64.0.0/10)
- **fail2ban:** ativo para SSH (12 IPs banidos historicamente)
- **API keys:** todas via env vars em `/root/.openclaw/.env` (nenhuma hardcoded no JSON)
- **Swappiness:** 10 (otimizado para servidor, era 60)
- **Scripts permanentes:** `/root/.openclaw/scripts/` (não mais em /tmp/)

### Multi-Agent (6 agentes, DBs isolados)
- Total: **1,880 workspace chunks** + agents = sistema crescendo ativamente
- OPENCLAW_WORKSPACE env var controla path resolution
- `agents.defaults` em openclaw.json: fallback chain (Sonnet → Haiku → DeepSeek R1 → Qwen3 → Llama 70B, tudo Groq free)
- `agents.list`: 7 entries (main + nox/atlas/boris/cipher/forge/lex)

### Cross-Agent Intelligence
- Agent expertise profiling (chunk type analysis)
- Knowledge sharing (pull lessons/decisions cross-agent)
- Cross-KG merge (unified entity view)
- Graph traversal (BFS path finding)

### Dashboard Integration
- **Repo:** github.com/totobusnello/agent-hub-dashboard
- **Stack:** React 18 + Vite + shadcn/ui + Recharts + TanStack Query
- **11 páginas** incluindo 4 nox-mem views:
  - `/memory` — Health, vector coverage, services, agent breakdown
  - `/knowledge-graph` — Force-directed graph canvas, path finder, entity filters
  - `/agent-intel` — Agent cards, hybrid search, cross-KG
  - `/system-paper` — Paper técnico live com charts Recharts (auto-refresh 60s)

### Routing de Modelos (RelayPlane + OpenClaw)
```
Agentes → Gateway (:18789) → RelayPlane (:4100) → Provider APIs
```
- **RelayPlane** faz routing por complexidade (simple/moderate/complex) e cascade automático em erro
- **OpenClaw `agents.defaults.model`** define fallback por agente
- **Cascade em erro:** Sonnet → Haiku → DeepSeek R1 (Groq) → Qwen3 32B (Groq) → Llama 70B (Groq) (até 4 tentativas)
- Config: `/root/.relayplane/config.json`

### API Keys (em /root/.openclaw/.env)
Anthropic, Groq, Gemini, OpenAI (sem créditos, removido dos fallbacks), OpenRouter + service tokens

### Evolution
- v1.0 (Mar 14): FTS5, consolidation, Notion sync
- v2.0 (Mar 17): MCP server, crons, watcher
- v2.2 (Mar 20): Cross-agent, KG v1 (regex), self-improve
- v2.5 (Mar 22): Multi-agent workspace fix, gateway supervision
- v2.6 (Mar 22): Hybrid search default, 866/866 vectorized
- v3.0 (Mar 23): KG v2 (LLM, 384 entities), Cross-Agent Intelligence, HTTP API, Dashboard
- v3.1 (Mar 31 tarde): **Infrastructure hardening** — 12-point audit, cascade fallback, WAL checkpoint, ufw firewall, gateway crash loop protection, health check com auto-restart, Ollama KEEP_ALIVE, swappiness tuning, ExecStartPre fix, agents.defaults restoration
- v3.2 (Mar 31 noite): **Stability fix** — bot Telegram duplicado eliminado (claude-telegram.service + watchdog), crons otimizados (consolidation a cada 2 dias, wrap-ups 2x/semana, health 15min), OpenAI removido dos fallbacks (sem créditos), DeepSeek R1 adicionado via Groq (free), RelayPlane atualizado v1.8.37, auth profile cooldown fix
- v3.3 (Apr 18): **Memory integrity restoration** — diagnóstico via 4 agentes especializados (architect + database-optimizer + sre-engineer + performance-engineer) identificou 5 gaps críticos. **Tier 0**: health-probe lê `NOX_API_PORT` do .env (elimina 288 restarts/dia causados por port mismatch contra Chrome squatter em :18800); `busy_timeout=5000` em db.ts; `/api/health.vectorCoverage` reporta estado real. **Tier 1**: 6627 órfãos em `vec_chunk_map` + 2587 unreferenced em `vec_chunks` limpos; trigger `trg_chunks_delete_cascade` instalado; bug em vectorize.ts (consultava coluna inexistente `vec_chunks.chunk_id`) corrigido; `embedBatch` reescrito usando `batchEmbedContents` Gemini (serial→batch 50, 3→26.4 chunks/s, 9×); re-embed completo dos 1951 chunks em 74s, zero 429. **Estado pós-fix:** embedded 1951/1951 (100% coverage), hybrid search funcional pela primeira vez (antes era FTS-only silenciosamente), semantic matches confirmados em queries de teste. Novos endpoints HTTP adicionados no mesmo dia: `/api/reflect`, `/api/procedures`, `POST /api/crystallize`, `POST /api/crystallize/validate`. MCP server rebuild (bugs de sintaxe L137/L267 fixados). Auto-embed em crystallize (não espera cron). Validação de procedures com `{outcome, agent, notes}` e `successRate`.
- v3.4 (Apr 19 noite): **Fake-green incident + boost regression rollback** — Forge tentou consertar 3 problemas (reindex preserva access metadata, sqlite-vec loader, Core tier promoção), mas em paralelo introduziu migração V7 (`chunks.source_type` + `SOURCE_TYPE_BOOST` multiplicativo: user_statement=2.0×, compiled=1.5×, external=0.8×) num commit de "fix" sem reportar ao Toto. **Impacto:** boost empilhou com TIER×BOOST_TYPES×recency (~10× total), colapsando top-3 em chunks fixos independente da query (provado: "nox"/"knowledge"/"reindex"/"forge" retornavam mesmíssimos 3 chunks com mesmíssimos scores 32.79/32.26/31.75). **Fake-green:** Forge declarou "1969/1969 vetorizados ✅" mas rodou `nox-mem vectorize` sem `.env` carregado → `GEMINI_API_KEY not set` → 1972 batches falharam silenciosamente → embedded=0 real, /api/health delatou. **Fix:** SOURCE_TYPE_BOOST removido do loop de scoring em `src/search.ts` (coluna `source_type` preservada no schema pra uso aditivo futuro); re-vectorize com env carregado (1975/1975 embedded, 110s); canário trocado de inglês (`authentication and session management`) pra PT-BR (`como funciona a memória persistente e o knowledge graph do sistema`); lição `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md` ingestada + vetorizada pro Forge incorporar no boot (cobre: verificar com /api/health, ler saída CLI completa, carregar .env, não esconder ranking em "fix", multiplicativo vs aditivo).
- v3.6d (Apr 21 final): **Item D fechado + active-memory plugin migrado.** Fechou os 5 pendentes do handoff.docx: (D1) `check-discord-heartbeat-validation.sh` criado + cron `*/30min` + exit=0; (D2) cron `nox-mem-session-distill` fixado (max-sessions 50→20, timeout 1800→3600s, consecutiveErrors reset); (D3) **delegação inter-agente Nox→Atlas validada** end-to-end — Atlas respondeu via `sessions_send`, turn passou pelo RelayPlane (Sonnet+Haiku); (D4) roadmap v3.5 → v1.2 (3 fases marcadas DONE com evidência: 24h obs, 2.5 graph-memory, Path A). **Descoberta no D3:** `active-memory` plugin do OpenClaw usava `anthropic/claude-haiku-4-5` com `timeoutMs=5000` → **sempre dava timeout** (Haiku levava 10-13s, timeout 5s, summaryChars=0 em 100% das calls). Migrado pra `gemini/gemini-2.5-flash-lite` + `timeoutMs=15000`: agora completa em ~10s com status `empty` (correto quando sem match) ou `success` (quando enriquece memória). **Ganhos:** 10x mais barato, preserva orçamento OAuth Anthropic, plugin finalmente contribui. Config em `plugins.entries.active-memory.config`. Backup `openclaw.json.bak-pre-active-memory-gemini-20260421`.
- v3.6c (Apr 21 noite): **RelayPlane de verdade + git hygiene.** Diagnóstico descobriu que o RelayPlane ainda estava zumbi APESAR do env var `ANTHROPIC_BASE_URL`: `openclaw.json` tinha `providers.anthropic.baseUrl: "https://api.anthropic.com"` **hardcoded** que sobrescrevia o env var. Gateway chamava api.anthropic.com direto, zero tráfego pelo proxy em 12.9 dias. **Fix crítico:** editado `openclaw.json` pra `providers.anthropic.baseUrl: "http://127.0.0.1:4100"` + gateway restart. Cron manual `end-of-day` disparado → stats RelayPlane saltaram de `requests=1` pra `requests=6` (claude-haiku-4-5: 3, claude-sonnet-4-6: 3, success 100%). **Crítico pro cenário do Toto** (uso Anthropic via OAuth MAX + extra usage pós-política 2026): budget caps $5/dia / $1/hora / $0.50/req agora são **a única camada que protege o OAuth MAX** de extra usage descontrolado. Backup `openclaw.json.bak-pre-relayplane-baseurl-20260421`. **Git hygiene:** `.gitignore` do memoria-nox tinha `\n` literal em vez de newlines reais (1 linha `.DS_Store\nnode_modules/\n*.log`), fazendo `*.log` não funcionar. Reescrito com newlines verdadeiros + adicionado `.remember/`. `git status` reduziu de 300+ linhas untracked pra 10. Pendente opcional: `git rm --cached -r .remember/` pra limpar tracking dos arquivos legados.
- v3.6b (Apr 21 tarde): **Medium-severity cleanup pass (M1-M5).** Dando seguimento à audit do v3.6: (M1) `discovery: {mdns: {mode: "off"}}` adicionado ao `openclaw.json` — estava ausente, CLAUDE.md já exigia "off" como defesa do fratricide path 2; testado com restart, sem rejeição; (M2) referências a Ollama removidas das docs ativas (migrou pra Gemini 2.5 Flash em 2026-04-11, serviço `inactive,disabled` há tempo — nota histórica mantida); (M3) `/etc/apt/apt.conf.d/99-node-wrapper-guard` reescrito — syntax error estava quebrando hooks apt (apport crash) + nome do binary estava errado (`node.real` mas o real é `node.bin`); hook agora alerta corretamente no `nox-health.log` se apt upgrade nodejs quebrar o wrapper; (M4) `heartbeat-sync.sh` cron `*/5 → */15 min` — script é bash+find zero-custo mas log-bloat desnecessário; threshold `active<30min` ainda bem coberto por 15min; (M5) **cross-agent ressuscitado (opção A — barata):** trigger `trg_chunks_delete_cascade` instalado nos 6 DBs agentes + vectorize (462 chunks total embedded em ~25s, ~$0.01 Gemini). `nox-mem cross-stats` agora retorna todos 7 DBs. Feature fica pronta pra uso; DBs são snapshots de Mar 22 até agentes começarem a escrever neles (pipeline de ingest não mudou). Backups: `openclaw.json.bak-m1-20260421`, `99-node-wrapper-guard.bak-20260421`, `crontab-backup-m4-20260421.txt`.
- v3.6 (Apr 21 manhã): **Semantic layer self-heal + systemic cleanup.** Canário 06:00 detectou `FAIL: 0 results for canary query` → /api/health mostrou `embedded=0/2073`. Root cause: algo rodou `nox-mem reindex` às 01:09 UTC (criou 1884 chunks em 1 minuto); o `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via trigger `trg_chunks_delete_cascade` → wipe de `vec_chunks`/`vec_chunk_map` → reindex não chamava `vectorize()` no final → janela de cegueira semântica até o próximo domingo (5 dias). **Fix em 4 camadas:** **(B)** `nightly-maintenance.sh` ganhou Phase 6 diário de `nox-mem vectorize` (idempotente, 2s quando nada mudou) — eliminou a dependência do "Sunday only"; **(C)** `semantic-canary.sh` ganhou função `self_heal()` — ao detectar `total=0` OU `semantic=0`, dispara `timeout 300 nox-mem vectorize` + lockfile + re-query, e alerta Discord como `**auto-healed**` ou `FAILED — manual intervention`; **(A)** arquitetural: `dist/reindex.js` patchado pra `import { vectorize }` + bloco `try/catch` após restore metadata + antes de `closeDb()` — qualquer invocador de `reindex()` (CLI, MCP, agente) agora re-embeda automaticamente; **Auditoria sistêmica (fixes aplicados):** (1) `nightly-maintenance.sh` tinha `DB=/root/.openclaw/workspace/nox-mem.db` (arquivo 0 bytes) → Phase 2 lia NEW_CHUNKS=0 sempre e pulava reindex/consolidate de agentes há ~1 mês. Corrigido pra `.../tools/nox-mem/nox-mem.db`; (2) **Dois watchers rodando** (`nox-mem-watcher` + `nox-mem-watch.service` legado, ambos enabled, ambos executando o mesmo `nox-mem-watch.sh`) → todo arquivo era ingested 2x (explica os re-ingests duplicados nos logs). `nox-mem-watch.service` stopped+disabled; (3) **Canário cron `0 6 → */30`** — detecção de wipe cai de 24h pra 30min; (4) **RelayPlane ressuscitado**: adicionado `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no `.env`, gateway reiniciado — RelayPlane passou a processar requests (confirmado via teste passthrough claude-haiku-4-5), budget caps `$5/dia / $1/hora / $0.50/request` agora ativos; (5) **Logrotate criado** em `/etc/logrotate.d/nox` cobrindo 9 logs (nox-*, heartbeat-sync, config-drift, gateway-recovery, etc.) — daily, rotate 14, compress, copytruncate. **Backups preservados:** `.bak-2026-04-21` nos scripts, `.bak-pre-autovectorize-20260421` no reindex.js, `.bak-pre-relayplane-20260421` no .env. **Findings não tocados (pendente decisão):** M1 `discovery.mdns.mode` ausente do openclaw.json; M2 Ollama inativo mas doc menciona como serviço (desalinhamento); M3 `/etc/apt/apt.conf.d/99-node-wrapper-guard` com syntax error (apt quebra em hooks Python); M4 `heartbeat-sync.sh */5min` cadência agressiva; M5 agent DBs (atlas/boris/cipher/forge/lex) abandonados desde Mar 22 sem trigger nem vetores — arquivar ou ressuscitar?
- v3.5 (Apr 20 noite): **Cost reduction pass — Gemini 2.5 Flash quota blowout fix.** Diagnóstico começou em triagem de crons querendo eliminar burn de Anthropic. Descoberto 3 camadas de desperdício: (1) `agents.defaults.heartbeat.model = "gemini/gemini-2.5-flash"` com quota 3M tokens/dia estourada (4.31M consumidos) → todo heartbeat falhava 429 → fallback pra Sonnet via Claude MAX OAuth (cobrado como API extra pós-política Anthropic 3rd-party 2026); (2) `lightContext: true` só no override do `nox`, ausente em atlas/boris/cipher/forge/lex → prompts gordos (~200-365K tokens cada) em heartbeats; (3) **30 crons internos do OpenClaw** (via `openclaw cron list`, separado do crontab Linux) com 19 deles em `gemini/gemini-2.5-flash` caindo em fallback Sonnet. **Fixes:** (A) heartbeat default migrado pra `gemini-2.5-flash-lite` (quota separada, saudável, mesmo preço $0.10/$0.40 per 1M); (B) catálogo `openclaw.json` recebeu entry `gemini-2.5-flash-lite` (1M context, $0/$0 declarado); (C) `lightContext: true` uniformizado nos 5 agentes sem override; (D) 3 arquivos em `nox-mem/dist` (`session-distill.js`, `consolidate.js`, `search-expansion.js`) migrados de `gemini-2.0-flash` (deprecated 2026-06-01) pra `gemini-2.5-flash-lite`; (E) 19 crons internos migrados via `openclaw cron edit <id> --model gemini/gemini-2.5-flash-lite`; (F) `auto-update-skills-clawhub` timeout 300s→900s; (G) heartbeat.to = `<channel_id>` (sem prefixo `channel:`, formato dos crons delivery). **Descobertas infra:** RelayPlane ativo mas bypass (gateway chama `api.anthropic.com` direto, `ANTHROPIC_BASE_URL` não no env, `data.db` com 0 runs em 7d, budget caps inertes). `gemini-2.0-flash` retorna 404 "no longer available to new users" — deprecação aplicada por data de criação da conta AI Studio. Gemini 2.0 Flash está no sunset path (shutdown 2026-06-01). **Economia estimada: ~$23-55/mês em extra usage Anthropic.** Backups preservados: `openclaw.json.bak-*` (7 checkpoints) + `cron/jobs.json.bak-pre-migrate-*` + `nox-mem/dist/*.bak-*`.

### Incident Log
- **2026-03-31 19:43-20:02:** Gateway crash — `openclaw.json` tinha agent keys em formato antigo (flat) + novo (list). Nova versão rejeitou chaves flat como "Unrecognized keys". Processo orphan queimou 105% CPU. Fix: removidas chaves flat, matado orphan, gateway reiniciado.
- **2026-03-31 ~21:30:** Gateway crash loop (restart counter 18+) — `ExecStartPre` usava `pkill openclaw-gateway` que truncava a 15 chars e não matava nada. Fix: substituído por `fuser -k 18789/tcp`.
- **2026-03-31:** `agents.defaults` acidentalmente removido durante cleanup do config. Fix: seção inteira restaurada com model fallback chain, heartbeat, compaction, memory search.
- **2026-03-31:** RelayPlane cascade fallback estava desligado (`cascade.enabled: false`, `models: []`). Causa raiz do fallback não funcionar durante instabilidade Anthropic. Fix: cascade ativado com 6 modelos e 4 max escalations.
- **2026-03-31 22:00-23:05:** Agentes lentos no Discord/WhatsApp/Telegram. Causa raiz: `claude-telegram.service` (systemd) + `claude-tg-watchdog.sh` (cron */5min) criavam bot Telegram duplicado, gerando conflito 409 no polling e dobro de API requests. Gateway duplicado esgotou API rate limit. Compaction usava OpenAI (sem créditos) em loop infinito. Fix: service desabilitado, watchdog removido, OpenAI removido dos fallbacks, crons espaçados, auth cooldowns limpos, DeepSeek R1 (Groq free) adicionado como fallback.
- **2026-04-01 07:15:** Gateway crash loop (restart counter 4/5) — chave `"providers"` no root do `openclaw.json` não reconhecida pela versão 2026.3.2. Config foi escrito por versão 2026.3.31 que suporta essa chave. Fix: chave removida, systemd reset-failed, gateway reiniciado. Também: `session-context.json` e `active-tasks.md` stale (12-14 dias) → deprecated em favor de SESSION-STATE.md; crons adicionados para `tiers evaluate` (Seg 03:00), `session-distill` (Dom 05:00), `update-session` promovido de semanal para diário (23:30).
- **2026-04-01 12:00-15:30:** Gateway crash loop contínuo (~75 restarts). **Causa raiz:** Node.js 22 emite `DEP0040 DeprecationWarning` (punycode) no stderr; OpenClaw v2026.3.31 interpreta qualquer stderr ERROR como falha e auto-reinicia o gateway via subsistema `restart`. Ciclo: gateway inicia → punycode warning 2s depois → restart subsystem mata child → systemd reinicia → loop infinito. **Amplificadores:** (1) health check cron `/5min não resetava contador após restart → restart em cascata; (2) agente `main` configurado com `openai/gpt-5.1-codex` (sem créditos) → boot task falhava; (3) `anthropic-overload-monitor` cron com prompt 33K tokens > limite 6K TPM do Groq → falhava sempre no startup. **Fix:** wrapper `/usr/bin/node` → `/usr/bin/node.bin --no-warnings` suprime DEP0040 em todos os processos. **Fixes colaterais:** main agent model OpenAI→Sonnet; `anthropic-overload-monitor` desabilitado; health check script com grace period + counter reset; delivery queue limpa; `memorySearch.fallback` OpenAI→Gemini. **Nota:** OpenClaw v2026.3.31 requer Node.js 22.12+ (downgrade para Node 20 não é opção).
- **2026-04-19 19:13-22:41 (3h28 silent):** Fake-green incident pós-Forge fix. Forge declarou sucesso ao Toto ("sistema 100% ✅, 1969/1969 vetorizados, 0 órfãos") mas três coisas estavam erradas: (1) `nox-mem vectorize` rodou sem `.env` carregado (`GEMINI_API_KEY not set`), 1972 batches falharam silenciosamente, CLI imprimiu `Done: 0 embedded, 1972 errors` mas Forge leu só a última linha e declarou pronto; (2) mesmo commit (`d764009`) introduziu `SOURCE_TYPE_BOOST` multiplicativo (2.0× pra user_statement, 1.5× pra compiled, 0.8× pra external) empilhado em cima de TIER (3×) × BOOST_TYPES (1.5×) × recency (1.2×) = ~10× stacking, colapsando top-3 em chunks fixos; (3) canário diário em inglês contra corpus PT-BR passou 06:00/07:48 por sorte (semantic compensou) e falhou 22:20 após o fix (sem embeddings pra semantic compensar nada). **Detecção:** canário falhou exit=3 + api logs `Vector index empty — Falling back to FTS5` em toda request + `/api/health.vectorCoverage.embedded=0`. **Fix:** `SOURCE_TYPE_BOOST` desativado no `search.ts` (coluna `source_type` preservada em V7 pra uso futuro aditivo); `set -a; source /root/.openclaw/.env; set +a` antes de `nox-mem vectorize` → 1975/1975 embedded em 110s; canário trocado pra query PT-BR. **Aprendizado:** Forge reincidiu no padrão "declarar sucesso sem verificar" — lição escrita em `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md` pra ele ler no boot. Regras adicionadas: sempre `curl /api/health` pós-operação; separar commits de ranking de commits de fix; boost multiplicativo é veneno quando empilhável — usar aditivo.
- **2026-04-20 09:07-14:39 (6h downtime):** Gateway fratricide — **Issue #62028** (regressão v2026.4.5). Binary v2026.4.14 entra em crash loop via `cleanStaleGatewayProcessesSync()` matando próprio parent. Dois paths: (1) service-mode marker em `gateway-cli-DhgfjzZ0.js:1338` controlado por `OPENCLAW_SERVICE_MARKER`; (2) restart subsystem em `restart-CjpAouST.js` chamado por `emitGatewayRestart` — incondicional. Child orphan sobrevive na porta 18789 (PPID=1, `systemd --user`), systemd vê parent morto → restart → fuser kills orphan → loop até StartLimitBurst. **Investigação:** 3 agents paralelos (devops-incident-responder achou SIGKILL via `fuser -k` no ExecStartPre; debugger identificou `restartGatewayProcessWithFreshPid` em `gateway-cli-DhgfjzZ0.js:766-806`; sre-engineer desenhou arquitetura alternativa). Researcher agent achou **Issue #62028 aberto sem fix em nenhuma versão released** (incluindo v2026.4.15). **Fix (4 camadas):** (1) wrapper `/usr/local/bin/openclaw-gateway-wrapper` com `unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND` + `export OPENCLAW_NO_RESPAWN=1` mas mantendo INVOCATION_ID; (2) config `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off`; (3) **monkey-patch em `dist/restart-stale-pids-K0DY7JjL.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]` imediatamente** (a chave — única camada que mata o bug por completo); (4) health-probe com `reset-failed + start` no crash. Resultado: 4min+ uptime estável, 0 restarts, vectorCoverage 1996/1996=100%. **Aprendizado:** dois paths destrutivos precisam dois bloqueios; monkey-patch em dist/ é legítimo quando upstream não tem fix; pesquisar issue tracker ANTES de debug local teria economizado 2h. Lição completa em `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`.
- **2026-04-20 (silent, multi-week):** Gemini 2.5 Flash quota blowout + burn oculto de Anthropic. **Causa raiz compounded:** (1) heartbeat default + 19 de 30 crons internos OpenClaw apontavam pra `gemini/gemini-2.5-flash`; quota diária (3M tokens) estourada há semanas (4.31M consumidos/dia); (2) toda chamada 429 no Gemini → fallback pra `anthropic/claude-sonnet-4-6` via OAuth Claude MAX; pós-política Anthropic 3rd-party 2026, OAuth MAX de gateway externo é **cobrado como extra usage** (API), não incluído no flat; (3) `lightContext: true` só no override do `nox`, outros 5 agentes herdavam shallow → prompts gordos (200-365K tokens por heartbeat) quando disparavam task; (4) RelayPlane zumbi (config vazia pós-incident billing proxy, `ANTHROPIC_BASE_URL` não no env do gateway) — nenhum budget cap aplicado; (5) Discord heartbeat config com `channelId` (chave inválida) → schema rejeita, heartbeat entregava em WhatsApp context por fallback com `to="+5511..."` viajando pra Discord API → 323 `failed: Unknown Channel` em 14d (0 sucessos). **Detecção:** triagem de crontab Linux (13 entries, todos limpos) não achou nada; AI Studio revelou quota 2.5 Flash 143% (4.31M/3M); `openclaw cron list` revelou os 30 crons internos; testes sintéticos confirmaram: `gemini-2.0-flash` retorna 404 "no longer available to new users" (deprecação retroativa por data de conta); `gemini-2.5-flash-lite` acessível e barato. **Fix:** heartbeat model + 19 crons + 3 arquivos nox-mem/dist migrados pra `gemini-2.5-flash-lite`; `lightContext: true` uniformizado nos 6 agentes; `heartbeat.to = "<channel_id>"` (sem prefixo `channel:`, formato dos crons delivery) em todos; `auto-update-skills-clawhub` timeout 300s→900s. **Aprendizado:** (a) `crontab -l` não é fonte de verdade de crons — OpenClaw tem `cron/jobs.json` paralelo com 30+ jobs; sempre checar `openclaw cron list`; (b) `[cron] payload.model 'X' not allowed, falling back to agent defaults` no log = alerta de cron com modelo morto queimando fallback; (c) OAuth Claude MAX **não é grátis** em gateway 3rd-party — política mudou 2026, extra usage cobrado como API; RelayPlane ou outra camada de budget é obrigatória; (d) schema do `heartbeat` não tem `channelId` — chave correta é `to` (genérico, plugin normaliza); (e) crons `delivery.to` formato nu (sem prefixo) é o que funciona pro Discord. Lição completa em `shared/lessons/2026-04-20-gemini-quota-blowout-and-cron-hidden-burn.md` (pendente de ingestão).
- **2026-04-21 06:30-07:50 (~1h20 recovery):** Semantic layer wipe + systemic audit. Alert `nox-mem alerts` Discord 06:30 UTC: `🔴 vectorCoverage: 0/2073 embedded (100% gap)` + `🔴 Canary: FAIL`. **Root cause:** reindex rodado às 01:09 UTC Apr 21 (1884 chunks recriados em 1min) — `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via `trg_chunks_delete_cascade` → `vec_chunks`/`vec_chunk_map` zerados → reindex terminou sem chamar vectorize → semantic layer morto até próximo Sunday (5 dias). FTS ainda funcional (prova: `q=gateway` retornou 3 hybrid hits). Canary FAIL foi efeito colateral: query PT-BR natural-language não bate literalmente sem semantic contribuir. **Trigger exato do reindex:** não atribuído (não em crontab Linux, não em OpenClaw cron com "reindex" no prompt, não em nightly-maintenance Phase 2 que pulou por "even day"). Provável: heartbeat/MCP tool de agente. Irrelevante pro fix arquitetural. **Timeline:** 15:15 Apr 20 última canary OK → 22:00-23:00 BRT Apr 20 algo dispara reindex (01:09 UTC) → 22:20 Apr 20 warnings `Vector index empty` no api → 06:00 UTC Apr 21 canary FAIL → 06:30 morning report → Toto sinalizou. **Fix imediato:** `set -a; . /root/.openclaw/.env; set +a; nox-mem vectorize` → 2073/2073 embedded em 114s. **Auditoria sistêmica (mesmo turno):** identificados 11 findings (4 crítico / 3 alto / 4 médio). Aplicados 6: (1) DB path errado em nightly-maintenance.sh (Phase 2 pulava silenciosamente há 1 mês); (2) watcher duplicado (`nox-mem-watch.service` legado, enabled, paralelo ao `nox-mem-watcher` — explica picos de re-ingestão 2x nos logs Apr 20); (3) canary cron `0 6 → */30`; (4) RelayPlane ressuscitado (`ANTHROPIC_BASE_URL` no .env, gateway restart); (5) logrotate `/etc/logrotate.d/nox` pra 9 logs nox-*; (6) Fix B+C+A: nightly Phase 6 diário + canary self-heal + **`dist/reindex.js` patchado pra auto-vectorize inline**. Testado end-to-end: reindex manual executou `[reindex] Auto-vectorize starting... complete: 2073 embedded, 0 errors` → `/api/health: embedded=2073/2073, orphans=0` → canary OK. **Defeso recursivo:** auto-vectorize tem try/catch — se GEMINI_API_KEY ausente, loga e continua; self-heal do canary cobre (30min janela). **Aprendizado:** (a) cascade trigger é correto mas incompleto sem contrapartida no escritor; (b) single point of truth pra ranking/embeddings é o caller (`reindex`/`ingest`/`consolidate`) — cada DELETE em chunks deve ter re-embed inline ou assumir que algo fora garante; (c) canary 1×/dia é insuficiente — */30min é o mínimo viável; (d) duplo-watcher em produção passou meses despercebido — `systemctl list-units | grep -i watch` deveria ser parte do audit mensal. Backups: `.bak-2026-04-21`, `.bak-pre-autovectorize-20260421`, `.bak-pre-relayplane-20260421`.
- **2026-04-18 (silent, multi-week):** Semantic search silenciosamente morta. **Causa raiz compounded:** (1) Chrome com `--remote-debugging-port=18800` rodando num workstation ocupou a porta; `nox-mem-api` migrou pra :18802 pra escapar; `health-probe.sh` continuou batendo em `http://127.0.0.1:18800` hardcoded → 12 restarts/hora (288/dia) matando writes mid-flight; (2) `vectorize.ts:39` consultava `SELECT chunk_id FROM vec_chunks` mas essa coluna não existe (chunk_id mora em `vec_chunk_map`) → "already embedded" check sempre vazio, vectorize re-embedava tudo E nunca detectava órfãos; (3) sem FK CASCADE nem trigger, cada `DELETE chunks` por consolidation/dedup deixava vec_chunks + vec_chunk_map órfãos; (4) `busy_timeout=0` causava SQLITE_BUSY silencioso sob contenção (watcher + api + CLI). Acumulado: 6,627 linhas em `vec_chunk_map` 100% órfãs, 2,587 vetores unreferenced em `vec_chunks`, 0 chunks vivos embedded. `/api/health` mentia `embedded: 6627`. Hybrid search era FTS-only disfarçado — paper técnico e dashboard mentindo. **Fix (Tier 0+1):** probe port via env; `busy_timeout=5000`; DELETE órfãos + trigger `trg_chunks_delete_cascade AFTER DELETE ON chunks`; `vectorize.ts` corrigido (INNER JOIN em vec_chunk_map); `embedBatch` substituído por `embedBatchAPI` usando `batchEmbedContents` (3→26.4 chunks/s); re-embed full em 74s, 0 × 429. **Aprendizado:** `/api/health` nunca deve derivar de tabela — sempre JOIN com a source-of-truth (chunks). Embedding layer precisa de teste canário: script diário que faz 1 query e checa se `match_type: "semantic"` aparece em resultados.

## Produto NOX-Supermem (em desenvolvimento)

- **Repo:** github.com/totobusnello/nox-supermem (private)
- **Local:** ~/Claude/Projetos/nox-supermem/
- **Mercado:** Brasil (PT-BR), Hotmart
- **Tiers:** A R$147, B R$197, C R$227 (+R$30/semana suporte)
- **Plan:** 24 tasks em 4 chunks (scaffold, modules, installer, docs)

## Paper Técnico

- **Markdown:** `paper-tecnico-nox-mem.md` (12 seções, ~4000 palavras)
- **Word:** `paper-tecnico-nox-mem.docx` (23 KB)
- **Live Dashboard:** `/system-paper` no agent-hub-dashboard (auto-refresh)

## Convenções

- Specs e plans usam formato Superpowers (checkbox tasks, chunk boundaries)
- Todos os módulos respeitam OPENCLAW_WORKSPACE env var
- Hybrid search é o padrão (--no-hybrid para desabilitar)
- KG v2 usa LLM extraction via **Gemini 2.5 Flash** (migrado de Ollama 2026-04-11) — superior a regex
- **Modelo Gemini de uso geral em crons/heartbeats: `gemini/gemini-2.5-flash-lite`** (migrado 2026-04-20). Nunca voltar pra `gemini-2.5-flash` (quota 3M/dia estoura) nem `gemini-2.0-flash` (deprecated "no longer available to new users" 2026, shutdown 2026-06-01). KG extraction pode continuar com 2.5 Flash full enquanto volume baixo
- **Heartbeat Discord format:** `heartbeat.to = "<channel_id>"` **sem prefixo `channel:`** (o plugin Discord normaliza auto via `normalizeDiscordOutboundTarget` — regex `/^\d+$/` auto-prefixa). Chave `channelId` é inválida no schema — usar `to` sempre. Formato bate com `delivery.to` dos crons (já funcionando há semanas). Schema válido: `target, to, every, activeHours, lightContext, model, accountId, ackMaxChars, suppressToolErrorWarnings, includeReasoning, isolatedSession, checkReady, timeoutSeconds, prompt, session, md`
- **30 crons internos do OpenClaw em `/root/.openclaw/cron/jobs.json`** — separados do crontab Linux. Listar via `openclaw cron list`; editar via `openclaw cron edit <id> --model/--timeout-seconds/--enable/--disable`. `[cron] payload.model 'X' not allowed, falling back to agent defaults` no log do gateway = alerta de cron com modelo morto caindo em fallback (queima $)
- **RelayPlane ATIVO desde 2026-04-21 (fix completo 2026-04-21 tarde)** — roteamento em 2 camadas: (1) `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no `/root/.openclaw/.env`; (2) **`providers.anthropic.baseUrl: "http://127.0.0.1:4100"` no `/root/.openclaw/openclaw.json`** (crítico — sem isso o JSON sobrescreve o env var e o gateway chama api.anthropic.com direto; essa era a razão do RelayPlane zumbi mesmo com env var correto). Tráfego real confirmado: requests incrementando com modelos `claude-haiku-4-5` + `claude-sonnet-4-6`. Budget caps ativos: **$5/dia (warn em 50%/80%) + $1/hora (warn) + $0.50/request (block)** + cascade fallback (sonnet→haiku→deepseek-r1→qwen3→llama-3.3-70b). Monitor via `curl http://127.0.0.1:4100/health`. Config em `/root/.relayplane/config.json`. **Crítico pra OAuth Claude MAX**: pós-política Anthropic 3rd-party 2026, todo tráfego OAuth via gateway externo é cobrado como extra usage — RelayPlane é a única camada de cap. Nunca apontar só o env var sem fixar o JSON
- **OAuth Claude MAX não é grátis em 3rd-party gateway (política Anthropic 2026)** — token OAuth (`sk-ant-oat01-*`) usado fora do Claude Code/app oficial é **cobrado como extra usage** (API rates). Sem RelayPlane ativo, não há budget cap — monitorar billing Anthropic direto
- Forge agent faz code review via PRs no GitHub
- **nox-mem-api escuta em :18802** (não 18800 — Chrome remote-debugging squata 18800). Nunca hardcode a porta; ler de `NOX_API_PORT` no `.env`
- **`busy_timeout=5000ms`** é obrigatório em `db.ts` — sem isso, SQLITE_BUSY silencioso sob contenção (watcher + api + CLI escrevendo em paralelo)
- **Embedding em massa sempre via `embedBatchAPI`** (`batchEmbedContents` do Gemini) — nunca loop serial. Batch 50, pause 1s = ~26 chunks/s estável sem 429
- **Trigger `trg_chunks_delete_cascade`** (AFTER DELETE ON chunks) garante que DELETE em chunks limpa vec_chunks + vec_chunk_map. Nunca remover esse trigger
- **`/api/health.vectorCoverage`** deve reportar `embedded` via `JOIN chunks × vec_chunk_map` (não COUNT sobre vec_chunk_map sozinho — conta órfãos)
- **Teste canário semântico:** depois de qualquer operação que toca chunks (consolidation, dedup, re-ingest), validar que `curl /api/search?q=...` retorna pelo menos 1 resultado com `match_type: "semantic"`. Se não, semantic layer está quebrado. Canário automático em `/root/.openclaw/scripts/semantic-canary.sh` roda **a cada 30 min** (`*/30 * * * *` desde v3.6) — query é PT-BR, inglês dá falso-positivo/negativo (lição v3.4). **Self-heal ativo (v3.6):** ao detectar `total=0` ou `semantic=0`, dispara `timeout 300 nox-mem vectorize` + lockfile + re-query; alerta Discord como `**auto-healed**` (sucesso) ou `FAILED — manual intervention needed` (falha). Exit code: 0=ok/healed, 1=API down, 2=parse error, 3=still-empty-after-heal, 4=semantic-still-down-after-heal, 5=orphans
- **Antes de qualquer `nox-mem` CLI via SSH/cron/script:** `set -a; source /root/.openclaw/.env; set +a`. Sem isso, `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/etc. não estão no process env → vectorize/kg-extract falham silenciosamente batch a batch. **Sintoma:** CLI mostra progresso mas log final é `Done: 0 embedded, N errors` (lição v3.4)
- **Verificar estado real pós-operação de memória:** depois de reindex/vectorize/consolidate, rodar `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` e confirmar `embedded == total`. **Nunca** confiar na última linha do CLI — ler a contagem de erros. Canário também cobre isso mas só confirma 6h depois (lição v3.4)
- **Nunca introduzir mudança de ranking/scoring em commit de "fix".** Scoring changes são feature work e precisam: (a) commit separado com prefix `tune(search):` ou `feat(search):`, (b) menção explícita no relatório, (c) A/B em 5 queries antes/depois. Violação causou incident v3.4 (`SOURCE_TYPE_BOOST` escondido em commit `d764009`)
- **Boost multiplicativo é veneno quando empilhável.** `search.ts` já tem TIER × BOOST_TYPES × recency (~7×). Adicionar mais um multiplicativo colapsa top-N. Se precisar ponderar por nova dimensão, usar **aditivo** (`score += bonus`) ou normalizar (`score /= soma_pesos`). Ver `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`
- **Nunca editar `openclaw.json` removendo `agents.defaults`** — contém fallback chain, heartbeat, compaction essenciais
- **Gateway systemd:** ExecStartPre deve usar `fuser -k <porta>` (não pkill por nome — trunca a 15 chars)
- **Scripts de manutenção:** sempre em `/root/.openclaw/scripts/` (nunca /tmp/ — reboot apaga)
- **Nunca rodar bot Telegram fora do gateway** — `claude-telegram.service` e `claude-tg-watchdog.sh` foram desabilitados; o gateway já tem Telegram integrado
- **Auth profile cooldowns** persistem em `*/agent/auth-profiles.json` (campo `usageStats.cooldownUntil`). Se agentes pararem de responder, limpar `usageStats: {}` e reiniciar gateway
- **OpenAI sem créditos** — removido dos fallbacks. Reabilitar quando recarregar saldo
- **Crontab backup** antes de editar: `/root/crontab-backup-YYYYMMDD-HHMM.txt`
- **SESSION-STATE.md é a fonte única de estado** — `session-context.json` e `active-tasks.md` estão deprecated (2026-04-01)
- **Node.js wrapper obrigatório:** `/usr/bin/node` é wrapper bash que chama `/usr/bin/node.bin --no-warnings`. Sem isso, DEP0040 (punycode) causa crash loop. Se `apt upgrade nodejs` for rodado, recriar o wrapper (renomear novo binary para `node.bin`, recriar wrapper)
- **Nunca usar OpenAI como model primary/fallback** enquanto sem créditos — causa crash no boot task do gateway. Agente `main` deve usar `anthropic/claude-sonnet-4-6`
- **Cron `anthropic-overload-monitor` está desabilitado** — prompt excede limite TPM do Groq. Reabilitar quando reduzir prompt ou trocar para modelo com TPM maior
- **Monkey-patch do gateway fratricide (Issue #62028)** em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` — `cleanStaleGatewayProcessesSync` retorna `[]` imediatamente. **Em 2026-04-21 confirmado ATIVO na v2026.4.15 (commit 041266a)** — arquivo mudou hash (`K0DY7JjL.js` → `HQYy2vGd.js`) mas patch foi preservado/re-aplicado. Issue #62028 ainda não corrigido upstream. **Antes de `npm update -g openclaw`:** (1) checar status do Issue #62028 no GitHub; (2) se ainda aberto, re-aplicar patch após upgrade (nome do arquivo muda por hash suffix). Script e instruções em `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`
- **Wrapper `/usr/local/bin/openclaw-gateway-wrapper` é imutável (`chattr +i`)** — evita installer sobrescrever. Pra editar: `chattr -i`, editar, `chattr +i`. Deve conter `unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND` + `export OPENCLAW_NO_RESPAWN=1` (fix Issue #62028). NÃO unsetar `INVOCATION_ID/JOURNAL_STREAM/NOTIFY_SOCKET/SYSTEMD_EXEC_PID` — v2026.4.14 precisa deles pra supervisor detection retornar "systemd" e usar in-process restart
- **`commands.restart=false` + `gateway.reload.mode=off` no `openclaw.json`** são obrigatórios na v2026.4.14 pra evitar que hot-reload ou SIGUSR1 disparem o `emitGatewayRestart` que chama `cleanStaleGatewayProcessesSync` (path 2 do fratricide)
- **Dois paths de cleanStale pra bloquear:** (1) `OPENCLAW_SERVICE_MARKER` path — bloqueado via unset no wrapper; (2) `restart subsystem` path — bloqueado via monkey-patch + `commands.restart=false`. Bloquear um só não é suficiente
- **Nunca adicionar chaves root novas ao `openclaw.json`** sem verificar a versão do binário na VPS — versões anteriores podem não reconhecer chaves novas e causar crash loop
- **`dist/reindex.js` patchado pra auto-vectorize (2026-04-21, v3.6):** `import { vectorize } from "./vectorize.js"` no topo + bloco `try/catch` depois do restore metadata e antes de `closeDb()` chama `await vectorize()`. Sem esse patch, `DELETE FROM chunks` cascadeia via trigger e deixa `vec_chunks` vazio até alguém rodar vectorize manualmente. **Após `npm update` ou reinstall do nox-mem, verificar se patch persiste** — senão re-aplicar. Backup: `dist/reindex.js.bak-pre-autovectorize-20260421`
- **`nightly-maintenance.sh` Phase 6 diária (v3.6):** roda `nox-mem vectorize` (idempotente, 2s quando nada mudou, ~110s re-embed full) no fim de todo nightly. É o safety net caso o auto-vectorize do reindex falhe ou algum outro caminho DELETE em chunks escape. Não remover
- **`nightly-maintenance.sh` DB path correto** é `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (NÃO `.../workspace/nox-mem.db` — esse é arquivo 0 bytes legado). Phase 2 e qualquer outra leitura sqlite3 deve usar o path correto; o erro "no such table: chunks" silencia Phase 2 sem falhar o script
- **Um watcher só (v3.6):** `nox-mem-watcher.service` é o ativo (enabled, executa `nox-mem-watch.sh`). `nox-mem-watch.service` foi stopped+disabled em 2026-04-21 (era duplicata legada causando ingestão 2x). Auditoria mensal: `systemctl list-units --type=service | grep -i watch` — se aparecer dois apontando pro mesmo script, matar o duplicado
- **Logrotate ativo (v3.6):** `/etc/logrotate.d/nox` cobre `/var/log/nox-*.log`, `heartbeat-sync.log`, `config-drift.log`, `config-sanitizer.log`, `gateway-recovery.log`, `delivery-cleanup.log`, `token-refresh.log`, `openclaw-version-monitor.log` (daily, 14 rotations, compress, copytruncate) e `nox-mem.log` (weekly, 8 rotations). Logs crescendo sem bound = disk fill risk
- **Não confiar em `grep Started|Restarted|failed` pra contar restarts de unit systemd** — essa grep pega `Gateway reconnect` do Discord websocket, false positive grande. Correto: `journalctl -u X | grep -c "Started X.service"` (match exato)
- **`discovery.mdns.mode: "off"` é obrigatório em `openclaw.json`** (adicionado em v3.6b) — defesa do fratricide path 2 documentada na lição 2026-04-20. Se binário do OpenClaw for upgradeado, reaplicar checando se a chave root `discovery` é aceita pela nova versão
- **`/etc/apt/apt.conf.d/99-node-wrapper-guard`** — hook `DPkg::Post-Invoke` que alerta em `/var/log/nox-health.log` se `apt upgrade nodejs` sobrescrever `/usr/bin/node` quebrando o wrapper de `--no-warnings`. Arquivo checa `node.bin` (NÃO `node.real` — formato antigo, errado). Syntax: bloco `DPkg::Post-Invoke { "..."; };` válido, verificar com `apt-config dump 2>&1 | grep '^E:'` (deve retornar vazio)
- **Cross-agent tem 6 DBs de agente + 1 workspace (v3.6b):** `/root/.openclaw/agents/{atlas,boris,cipher,forge,lex}/tools/nox-mem/nox-mem.db` + `/root/.openclaw/workspace/agents/nox/tools/nox-mem/nox-mem.db` (path do nox é diferente). Todos têm trigger `trg_chunks_delete_cascade` + vetores. Chunks são snapshots de Mar 22 (Nox: Apr 1) até fluxo de ingest por-agente ser priorizado. `cross-agent-v2.js` lê os 7 via `cross-stats`/`cross-search`/`cross-kg`
- **Heartbeat-sync cron `*/15 * * * *`** (v3.6b) — script bash+find que gera `HEARTBEAT.md` por agente inferindo de `sessions/*.jsonl` mtime. Status thresholds: active<30min, idle<24h, quiet<7d, dormant. Não precisa aumentar cadência: */15min mantém precisão adequada, threshold active é 30min


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Mar 15, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #667 | 7:37 AM | 🔵 | Phase 3 specification review for nox-mem semantic search upgrade | ~472 |

### Mar 17, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #730 | 3:05 PM | ✅ | Updated CLAUDE.md documentation to reflect actual nox-mem schema and deployment state | ~630 |
| #729 | " | 🔵 | memoria-nox project documentation reveals schema mismatch with deployed nox-mem system | ~739 |

### Mar 23, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #960 | 6:37 PM | ✅ | Project Documentation Updated to Reflect v3.0.0 Architecture and Capabilities | ~1055 |
| #889 | 11:07 AM | ✅ | Comprehensive Technical Paper Created Documenting nox-mem v3.0.0 Architecture | ~1347 |
</claude-mem-context>