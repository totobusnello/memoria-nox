# nox-mem — Convenções Detalhadas

> Regras expandidas com contexto + razão + exemplos. CLAUDE.md mantém as 10 críticas inline; as demais ficam aqui como referência via `Read docs/CONVENTIONS.md`.

## Ranking / Scoring / Busca

### Nunca introduzir mudança de ranking/scoring em commit de "fix"
Scoring changes são feature work e precisam: (a) commit separado com prefix `tune(search):` ou `feat(search):`, (b) menção explícita no relatório, (c) A/B em 5 queries antes/depois. Violação causou incident v3.4 (`SOURCE_TYPE_BOOST` escondido em commit `d764009`).

### Boost multiplicativo é veneno quando empilhável
`search.ts` já tem TIER × BOOST_TYPES × recency (~7×). Adicionar mais um multiplicativo colapsa top-N. Se precisar ponderar por nova dimensão:
- **Aditivo:** `score += bonus`
- **Normalizar:** `score /= soma_pesos`

Ver `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`.

### Hybrid search é o padrão
`--no-hybrid` para desabilitar.

### Teste canário semântico obrigatório pós-operação
Depois de qualquer operação que toca chunks (consolidation, dedup, re-ingest), validar que `curl /api/search?q=...` retorna pelo menos 1 resultado com `match_type: "semantic"`. Canário automático em `/root/.openclaw/scripts/semantic-canary.sh` roda `*/30 * * * *`. Query PT-BR, não inglês (lição v3.4).

**Self-heal ativo (v3.6):** ao detectar `total=0` ou `semantic=0`, dispara `timeout 300 nox-mem vectorize` + lockfile + re-query; alerta Discord como `**auto-healed**` (sucesso) ou `FAILED — manual intervention needed` (falha). Exit codes: 0=ok/healed, 1=API down, 2=parse error, 3=still-empty, 4=semantic-still-down, 5=orphans.

## Embeddings / Database

### Embedding em massa sempre via `embedBatchAPI`
`batchEmbedContents` do Gemini. Nunca loop serial. Batch 50, pause 1s = ~26 chunks/s estável sem 429.

### Trigger `trg_chunks_delete_cascade` nunca remover
`AFTER DELETE ON chunks` garante que DELETE limpa `vec_chunks` + `vec_chunk_map`.

### `/api/health.vectorCoverage` embedded via JOIN
Deve reportar `embedded` via `JOIN chunks × vec_chunk_map` (não COUNT sobre vec_chunk_map sozinho — conta órfãos).

### `busy_timeout=5000ms` obrigatório em `db.ts`
Sem isso, SQLITE_BUSY silencioso sob contenção (watcher + api + CLI escrevendo em paralelo).

### KG v2 LLM extraction
Via **Gemini 2.5 Flash** (migrado de Ollama 2026-04-11) — superior a regex.

### `dist/reindex.js` patchado pra auto-vectorize (2026-04-21, v3.6)
`import { vectorize } from "./vectorize.js"` no topo + bloco `try/catch` depois do restore metadata e antes de `closeDb()` chama `await vectorize()`. Sem esse patch, `DELETE FROM chunks` cascadeia via trigger e deixa `vec_chunks` vazio até alguém rodar vectorize manualmente. **Após `npm update` ou reinstall do nox-mem, verificar se patch persiste** — senão re-aplicar. Backup: `dist/reindex.js.bak-pre-autovectorize-20260421`.

### `nightly-maintenance.sh` Phase 6 diária (v3.6)
Roda `nox-mem vectorize` (idempotente) no fim de todo nightly. Safety net caso o auto-vectorize do reindex falhe. Não remover.

### `nightly-maintenance.sh` DB path correto
`/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (NÃO `.../workspace/nox-mem.db` — esse é arquivo 0 bytes legado).

## Ambiente / Env Vars

### Antes de qualquer `nox-mem` CLI via SSH/cron/script
`set -a; source /root/.openclaw/.env; set +a`. Sem isso, `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/etc. não estão no process env → vectorize/kg-extract falham silenciosamente batch a batch. **Sintoma:** CLI mostra progresso mas log final é `Done: 0 embedded, N errors` (lição v3.4).

### Verificar estado real pós-operação de memória
Depois de reindex/vectorize/consolidate, rodar `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` e confirmar `embedded == total`. **Nunca** confiar na última linha do CLI — ler a contagem de erros.

### OpenClaw API keys via env vars em `/root/.openclaw/.env`
**Nenhuma hardcoded no JSON.** Usar `${VAR_NAME}` em todos os `apiKey` de providers. Pós-incident 2026-04-21, todos os 8 apiKey (Gemini×2 + 6 agents/*/models.json + Perplexity) usam envsub. Rotação = só `.env` + restart dos 3 serviços.

## Modelos / Routing

### Modelo Gemini de uso geral em crons/heartbeats
`gemini/gemini-2.5-flash-lite` (migrado 2026-04-20). **Nunca** voltar pra:
- `gemini-2.5-flash` (quota 3M/dia estoura) 
- `gemini-2.0-flash` (deprecated "no longer available to new users" 2026, shutdown 2026-06-01)

KG extraction pode continuar com 2.5 Flash full enquanto volume baixo.

### Heartbeat Discord format
`heartbeat.to = "<channel_id>"` **sem prefixo `channel:`** (plugin Discord normaliza auto via regex `/^\d+$/`). Chave `channelId` é inválida no schema — usar `to` sempre. Schema válido: `target, to, every, activeHours, lightContext, model, accountId, ackMaxChars, suppressToolErrorWarnings, includeReasoning, isolatedSession, checkReady, timeoutSeconds, prompt, session, md`.

### 30 crons internos do OpenClaw em `/root/.openclaw/cron/jobs.json`
Separados do crontab Linux. 
- Listar: `openclaw cron list`
- Editar: `openclaw cron edit <id> --model/--timeout-seconds/--enable/--disable`
- Alerta: `[cron] payload.model 'X' not allowed, falling back to agent defaults` no log do gateway = cron com modelo morto caindo em fallback (queima $).

### RelayPlane ATIVO desde 2026-04-21 (fix completo v3.6c)
Roteamento em 2 camadas:
1. `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no `/root/.openclaw/.env`
2. `providers.anthropic.baseUrl: "http://127.0.0.1:4100"` no `/root/.openclaw/openclaw.json` (**crítico** — sem isso o JSON sobrescreve o env var; essa era a razão do RelayPlane zumbi mesmo com env var correto)

Budget caps ativos: **$5/dia (warn em 50%/80%) + $1/hora (warn) + $0.50/request (block)** + cascade fallback (sonnet→haiku→deepseek-r1→qwen3→llama-3.3-70b). Monitor: `curl http://127.0.0.1:4100/health`. Config: `/root/.relayplane/config.json`.

**Crítico pra OAuth Claude MAX**: pós-política Anthropic 3rd-party 2026, todo tráfego OAuth via gateway externo é cobrado como extra usage — RelayPlane é a única camada de cap.

### OAuth Claude MAX não é grátis em 3rd-party gateway (política Anthropic 2026)
Token OAuth (`sk-ant-oat01-*`) usado fora do Claude Code/app oficial é **cobrado como extra usage** (API rates). Sem RelayPlane ativo, não há budget cap — monitorar billing Anthropic direto.

### Nunca usar OpenAI como model primary/fallback
Enquanto sem créditos — causa crash no boot task do gateway. Agente `main` deve usar `anthropic/claude-sonnet-4-6`.

### OpenAI sem créditos
Removido dos fallbacks. Reabilitar quando recarregar saldo.

## Gateway / Systemd

### Gateway systemd ExecStartPre
Usar `fuser -k <porta>` (não `pkill` por nome — trunca a 15 chars).

### Nunca editar `openclaw.json` removendo `agents.defaults`
Contém fallback chain, heartbeat, compaction essenciais.

### Nunca adicionar chaves root novas ao `openclaw.json`
Sem verificar a versão do binário na VPS — versões anteriores podem não reconhecer chaves novas e causar crash loop.

### `commands.restart=false` + `gateway.reload.mode=off`
Obrigatórios na v2026.4.14 pra evitar que hot-reload ou SIGUSR1 disparem `emitGatewayRestart` que chama `cleanStaleGatewayProcessesSync` (path 2 do fratricide).

### `discovery.mdns.mode: "off"` obrigatório em `openclaw.json`
Defesa do fratricide path 2 (lição 2026-04-20). Se binário do OpenClaw for upgradeado, reaplicar.

### Monkey-patch do gateway fratricide (Issue #62028)
Em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` — `cleanStaleGatewayProcessesSync` retorna `[]` imediatamente. Em 2026-04-21 confirmado ATIVO na v2026.4.15.

**Antes de `npm update -g openclaw`:** (1) checar status do Issue #62028 no GitHub; (2) se ainda aberto, re-aplicar patch após upgrade (nome do arquivo muda por hash suffix). Script em `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`.

### Wrapper `/usr/local/bin/openclaw-gateway-wrapper` é imutável (`chattr +i`)
Evita installer sobrescrever. Pra editar: `chattr -i`, editar, `chattr +i`. Deve conter `unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND` + `export OPENCLAW_NO_RESPAWN=1`. **NÃO unsetar** `INVOCATION_ID/JOURNAL_STREAM/NOTIFY_SOCKET/SYSTEMD_EXEC_PID` — v2026.4.14 precisa deles pra supervisor detection.

### Dois paths de cleanStale pra bloquear
1. `OPENCLAW_SERVICE_MARKER` path — bloqueado via unset no wrapper
2. `restart subsystem` path — bloqueado via monkey-patch + `commands.restart=false`

Bloquear um só não é suficiente.

### Node.js wrapper obrigatório
`/usr/bin/node` é wrapper bash que chama `/usr/bin/node.bin --no-warnings`. Sem isso, DEP0040 (punycode) causa crash loop. Se `apt upgrade nodejs` for rodado, recriar (renomear novo binary para `node.bin`, recriar wrapper).

### `/etc/apt/apt.conf.d/99-node-wrapper-guard`
Hook `DPkg::Post-Invoke` que alerta em `/var/log/nox-health.log` se `apt upgrade nodejs` sobrescrever `/usr/bin/node`. Checa `node.bin` (NÃO `node.real` — formato antigo). Verificar syntax com `apt-config dump 2>&1 | grep '^E:'` (deve retornar vazio).

## Serviços / Portas

### nox-mem-api escuta em :18802
Não 18800 — Chrome remote-debugging squata 18800. **Nunca hardcode a porta; ler de `NOX_API_PORT` no `.env`.**

### Um watcher só (v3.6)
`nox-mem-watcher.service` é o ativo (enabled, executa `nox-mem-watch.sh`). `nox-mem-watch.service` foi stopped+disabled (era duplicata). Auditoria mensal: `systemctl list-units --type=service | grep -i watch`.

### Nunca rodar bot Telegram fora do gateway
`claude-telegram.service` e `claude-tg-watchdog.sh` foram desabilitados; o gateway já tem Telegram integrado.

## Logs / Backups / Manutenção

### Scripts de manutenção sempre em `/root/.openclaw/scripts/`
Nunca /tmp/ — reboot apaga.

### Crontab backup antes de editar
`/root/crontab-backup-YYYYMMDD-HHMM.txt`.

### Logrotate ativo (v3.6)
`/etc/logrotate.d/nox` cobre `/var/log/nox-*.log`, `heartbeat-sync.log`, `config-drift.log`, `config-sanitizer.log`, `gateway-recovery.log`, `delivery-cleanup.log`, `token-refresh.log`, `openclaw-version-monitor.log` (daily, 14 rotations, compress, copytruncate) e `nox-mem.log` (weekly, 8 rotations).

### Auth profile cooldowns em `*/agent/auth-profiles.json`
Campo `usageStats.cooldownUntil`. Se agentes pararem de responder, limpar `usageStats: {}` e reiniciar gateway.

### SESSION-STATE.md é a fonte única de estado
`session-context.json` e `active-tasks.md` estão deprecated (2026-04-01).

### Não confiar em `grep Started|Restarted|failed` pra contar restarts
Pega `Gateway reconnect` do Discord websocket (false positive). Correto: `journalctl -u X | grep -c "Started X.service"` (match exato).

### Heartbeat-sync cron `*/15 * * * *` (v3.6b)
Script bash+find que gera `HEARTBEAT.md` por agente inferindo de `sessions/*.jsonl` mtime. Status thresholds: active<30min, idle<24h, quiet<7d, dormant. Não aumentar cadência.

## Multi-Agent

### Cross-agent tem 6 DBs de agente + 1 workspace (v3.6b)
- `/root/.openclaw/agents/{atlas,boris,cipher,forge,lex}/tools/nox-mem/nox-mem.db`
- `/root/.openclaw/workspace/agents/nox/tools/nox-mem/nox-mem.db` (path do nox é diferente)

Todos têm trigger `trg_chunks_delete_cascade` + vetores. Chunks são snapshots de Mar 22 (Nox: Apr 1) até fluxo de ingest por-agente ser priorizado. `cross-agent-v2.js` lê os 7 via `cross-stats`/`cross-search`/`cross-kg`.

### Cron `anthropic-overload-monitor` está desabilitado
Prompt excede limite TPM do Groq. Reabilitar quando reduzir prompt ou trocar para modelo com TPM maior.

## Git / Secrets

### Nunca committar secrets (regra dura pós-incident 2026-04-21)
Defesa instalada: **gitleaks 8.30.1** global via Homebrew + hook `~/.git-hooks-global/pre-commit` + `git config --global core.hooksPath`. Cobre todos os repos do Mac automaticamente. Bypass emergencial: `git commit --no-verify` (documentar).

### Specs e plans usam formato Superpowers
Checkbox tasks, chunk boundaries.

### Todos os módulos respeitam `OPENCLAW_WORKSPACE` env var

### Forge agent faz code review via PRs no GitHub

## chunk_type — enum canônico (B3-5, 2026-04-26)

> Tipos de chunk são uma **decisão de design**: cada tipo carrega retention default + behavior de ingest + relevância pra crons (consolidate filtra `daily`, etc). Não criar tipo novo sem atualizar matriz aqui + `src/retention.ts:RETENTION_BY_TYPE` + `migrateToV8` no `db.ts`.

### Tipos canônicos (schema v10)

| `chunk_type` | retention default | Origem (ingest) | Notes |
|---|---|---|---|
| `feedback` | NULL (never-decay) | `memory/feedback.md` ou via `--type=feedback` no ingest | Evidência preservada — user feedback, lições críticas |
| `person` | NULL (never-decay) | `memory/people.md`, entity files type=person | Ontologia estável de pessoas |
| `lesson` | 180d | `memory/lessons.md`, entity files type=lesson | Mistakes caros merecem 6 meses |
| `decision` | 365d | `memory/decisions.md`, entity files type=decision | Decisões têm lifespan longo |
| `project` | 365d | `memory/projects.md`, entity files type=project | Projetos ativos |
| `daily` | 90d | session daily notes (`memory/2026-MM-DD.md`) | Único iterado pelo `consolidate` loop real |
| `team` | 120d | shared/notes per-team | Estado de time evolui |
| `digest` | 180d | output do `nox-mem digest` (weekly) | Consolidação semanal |
| `pending` | 30d | `memory/pending.md`, entity files type=pending | Se 30d sem resolver, escala pra review |
| `graph_node` | 60d | `graphify-ingest` em repos externos | Research-like, decay rápido |
| `other` | 90d (default) | Qualquer file não classificável | Fallback do `RETENTION_BY_TYPE` |

### Adicionar tipo novo (workflow)

1. Adicionar entry em `src/retention.ts:RETENTION_BY_TYPE` com retention apropriada
2. Atualizar `migrateToV8` em `src/db.ts` se houver backfill heurístico (UPDATE por `source_file LIKE`)
3. Atualizar tabela acima neste arquivo
4. Se o ingest precisa de path-based dispatch: adicionar handler em `src/lib/ingest-router.ts:routeIngest()` (Fase A2 v1.6)
5. Atualizar canary `check-schema-invariants.sh` se houver invariant pra esse tipo (ex: feedback NULL sempre)
6. Bumpar `SCHEMA_VERSION` em `db.ts` SE estiver mudando schema (não só seed)

### Ingest-router unified (Fase A2 v1.6, 2026-04-25)

Single dispatch point: `src/lib/ingest-router.ts:routeIngest(file, opts)` rota automaticamente:
- `memory/entities/<type>/*.md` → `ingestEntityFile()` (3-section format: frontmatter + compiled + timeline)
- `*.md` (genérico) → `ingestFile()` com chunk_type inferido por path/frontmatter
- `*.json` → `ingestFile()` com chunk_type=`other`
- `--force-kind=graphify` (futuro) → `graphifyIngest()` (não wrapped ainda — Wave 2)

Callers: watch.ts (file events), reindex.ts (loop), index.ts CLI `ingest`/`ingest-entity`, mcp-server.ts.
**Nunca** chamar `ingestFile()` diretamente em loop sem passar pelo router — A2 fix do incident 2026-04-25 expôs isso.
