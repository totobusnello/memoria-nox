# nox-mem — Evolution Log

> Timeline completa das versões do nox-mem. CLAUDE.md só referencia a **versão atual** (v3.6d) — detalhe de versões anteriores mora aqui.
>
> ⚠️ **Versões v3.7+ contêm contexto OpenClaw plataforma** (routing, auth-profiles, plugins, RelayPlane, monkey-patch) porque o trabalho dessa janela foi entrelaçado. Detalhes de plataforma OpenClaw vivem agora em `~/Claude/Projetos/openclaw-vps/infra/`. Versão mestra pré-split em `_archive-pre-split-20260501/EVOLUTION.md.bak`.

## v3.7b (Apr 24 18:20) — Routing rework + auth hardening + thinking=max

Continuação da v3.7a após probe revelar que **cipher/forge/lex rodavam em openai-codex/gpt-5.4 (pay-per-token)** apesar do `openclaw.json` dizer claude-cli — sessions.json grudou em fallback (regra 11).

Descoberta paralela: **Tier 2 tinha sido parcialmente revertido** — edits manuais em `openclaw.json` não sobrevivem ao restart porque gateway tem in-memory state canonical que sobrescreve o arquivo. Solução: usar `openclaw config set` + `validate` + restart.

**Via CLI oficial:** `bootstrapMaxChars=12000`, `thinkingDefault=max`, google removido de `plugins.allow`/`entries`, `llm-task.model=gemini-2.5-flash-lite`.

**Via edit agents/\*/auth-profiles.json:** removido `apiKey` de `anthropic:default` em nox/atlas/boris/cipher/forge/lex (type→token). Era bomba-relógio — gateway poderia passar ao subprocess em fallback path e gerar 401.

**Sessions.json reset** pra 6 agentes — removidas entries não-claude pra quebrar stickiness.

**Routing canônico final:** nox+forge=opus, atlas+boris+cipher+lex=sonnet, todos via claude-cli. Thinking=max (efetivo `high`, limite dos modelos). Zero Codex.

Probe pós-restart confirmou: todos claude-cli, graph-memory em gemini/flash-lite (log fix da v3.7a continuou funcionando), bootstrap 12000 respeitado, fratricide zero, monkey-patch #62028 intacto.

Backup: `/root/backups/config-rework-20260424-181356/` (openclaw.json + 7× auth + 7× sessions).

CLAUDE.md regra 5 atualizada pra schema novo (`anthropic-max:default` canônico, não `anthropic:claude-cli`). Detalhes: `docs/OPTIMIZATION-2026-04-24.md` addendum.

## v3.7a (Apr 24 tarde) — Agent performance optimization Tier 1+2 + graph-memory log fix

**Contexto:** audit de performance dos agentes identificou plugins quebrados em retry loop, bootstrap inflado, thinking sempre on, e log do graph-memory reportando opus (suspeita de rodar em modelo caro).

**Tier 1 (broken plugins):**
- `plugins.entries.google` removido de `openclaw.json`
- `amazon-bedrock` + `google` já estavam `mv`d pra `/tmp/` (confirmado)
- allowlist reduzida pra 21 items

**Tier 2 (config tuning):**
- `bootstrapMaxChars: 25000 → 12000` (~3k tokens/turn economizados)
- `agents.defaults.thinking.mode: on → off` (operacional não precisa CoT)
- `llm-task.model: anthropic/claude-haiku-4-5 → gemini/gemini-2.5-flash-lite` (10x mais barato)

**Validação graph-memory:**
- Código-fonte confirma **Path A** (direct OpenAI-compat via `cfg.llm.baseURL`) vence sobre `agents.defaults.primary`
- Latência real 1.7-3.3s/extração = flash-lite range (opus seria 5-10s)
- **Log estava mentindo há meses** — reportando `agents.defaults.primary` (claude-opus-4-6) em vez do que realmente rodava

**Fix cosmético aplicado:** patch local em `/root/.openclaw/extensions/graph-memory/index.ts` (~L756) introduz bloco `effProvider/effModel` que inspeciona `cfg.llm.baseURL` host e reporta valor real. Log agora diz `provider=gemini | model=gemini-2.5-flash-lite`.

**Backups:** `/root/backups/optimize-20260424-173248/{openclaw.json,sessions-main.json}.bak` + `index.ts.bak-log-fix-20260424-*`.

**Invariantes pós-restart:** monkey-patch #62028 intacto (`CegQx-K9`), vec coverage 9538/9541, salience shadow, sem fratricide.

**Detalhes completos:** `docs/OPTIMIZATION-2026-04-24.md`.

## v3.6d (Apr 21 final) — Item D fechado + active-memory plugin migrado
Fechou os 5 pendentes do handoff.docx:
- **D1:** `check-discord-heartbeat-validation.sh` criado + cron `*/30min` + exit=0
- **D2:** cron `nox-mem-session-distill` fixado (max-sessions 50→20, timeout 1800→3600s, consecutiveErrors reset)
- **D3:** delegação inter-agente Nox→Atlas validada end-to-end — Atlas respondeu via `sessions_send`, turn passou pelo RelayPlane (Sonnet+Haiku)
- **D4:** roadmap v3.5 → v1.2 (3 fases marcadas DONE com evidência: 24h obs, 2.5 graph-memory, Path A)

**Descoberta no D3:** `active-memory` plugin do OpenClaw usava `anthropic/claude-haiku-4-5` com `timeoutMs=5000` → sempre dava timeout (Haiku levava 10-13s, timeout 5s, summaryChars=0 em 100% das calls). Migrado pra `gemini/gemini-2.5-flash-lite` + `timeoutMs=15000`: agora completa em ~10s com status `empty` (correto quando sem match) ou `success` (quando enriquece memória). **Ganhos:** 10x mais barato, preserva orçamento OAuth Anthropic, plugin finalmente contribui. Config em `plugins.entries.active-memory.config`. Backup `openclaw.json.bak-pre-active-memory-gemini-20260421`.

## v3.6c (Apr 21 noite) — RelayPlane de verdade + git hygiene
Diagnóstico descobriu que o RelayPlane ainda estava zumbi APESAR do env var `ANTHROPIC_BASE_URL`: `openclaw.json` tinha `providers.anthropic.baseUrl: "https://api.anthropic.com"` hardcoded que sobrescrevia o env var. Gateway chamava api.anthropic.com direto, zero tráfego pelo proxy em 12.9 dias. **Fix crítico:** editado `openclaw.json` pra `providers.anthropic.baseUrl: "http://127.0.0.1:4100"` + gateway restart. Cron manual `end-of-day` disparado → stats RelayPlane saltaram de `requests=1` pra `requests=6` (claude-haiku-4-5: 3, claude-sonnet-4-6: 3, success 100%).

**Crítico pro cenário do Toto** (uso Anthropic via OAuth MAX + extra usage pós-política 2026): budget caps $5/dia / $1/hora / $0.50/req agora são **a única camada que protege o OAuth MAX** de extra usage descontrolado. Backup `openclaw.json.bak-pre-relayplane-baseurl-20260421`.

**Git hygiene:** `.gitignore` do memoria-nox tinha `\n` literal em vez de newlines reais (1 linha `.DS_Store\nnode_modules/\n*.log`), fazendo `*.log` não funcionar. Reescrito com newlines verdadeiros + adicionado `.remember/`. `git status` reduziu de 300+ linhas untracked pra 10.

## v3.6b (Apr 21 tarde) — Medium-severity cleanup pass (M1-M5)
- **M1:** `discovery: {mdns: {mode: "off"}}` adicionado ao `openclaw.json` — defesa do fratricide path 2
- **M2:** referências a Ollama removidas das docs ativas (migrou pra Gemini 2.5 Flash em 2026-04-11)
- **M3:** `/etc/apt/apt.conf.d/99-node-wrapper-guard` reescrito — syntax error estava quebrando hooks apt + nome do binary estava errado (`node.real` mas o real é `node.bin`)
- **M4:** `heartbeat-sync.sh` cron `*/5 → */15 min` — log-bloat desnecessário; threshold `active<30min` ainda bem coberto
- **M5:** cross-agent ressuscitado (opção A — barata): trigger `trg_chunks_delete_cascade` instalado nos 6 DBs agentes + vectorize (462 chunks total embedded em ~25s, ~$0.01 Gemini). `nox-mem cross-stats` agora retorna todos 7 DBs

Backups: `openclaw.json.bak-m1-20260421`, `99-node-wrapper-guard.bak-20260421`, `crontab-backup-m4-20260421.txt`.

## v3.6 (Apr 21 manhã) — Semantic layer self-heal + systemic cleanup
Canário 06:00 detectou `FAIL: 0 results for canary query` → /api/health mostrou `embedded=0/2073`. Root cause: algo rodou `nox-mem reindex` às 01:09 UTC; o `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via trigger → wipe de `vec_chunks`/`vec_chunk_map` → reindex não chamava `vectorize()` no final → janela de cegueira semântica até o próximo domingo (5 dias).

**Fix em 4 camadas:**
- **(B)** `nightly-maintenance.sh` ganhou Phase 6 diário de `nox-mem vectorize` (idempotente, 2s quando nada mudou) — eliminou a dependência do "Sunday only"
- **(C)** `semantic-canary.sh` ganhou função `self_heal()` — ao detectar `total=0` OU `semantic=0`, dispara `timeout 300 nox-mem vectorize` + lockfile + re-query
- **(A)** arquitetural: `dist/reindex.js` patchado pra `import { vectorize }` + bloco `try/catch` após restore metadata + antes de `closeDb()` — qualquer invocador de `reindex()` agora re-embeda automaticamente

**Auditoria sistêmica (fixes aplicados):**
1. `nightly-maintenance.sh` tinha `DB=/root/.openclaw/workspace/nox-mem.db` (arquivo 0 bytes) → Phase 2 lia NEW_CHUNKS=0 sempre e pulava reindex/consolidate de agentes há ~1 mês. Corrigido
2. Dois watchers rodando (`nox-mem-watcher` + `nox-mem-watch.service` legado) → todo arquivo era ingested 2x. Legado stopped+disabled
3. Canário cron `0 6 → */30` — detecção de wipe cai de 24h pra 30min
4. RelayPlane ressuscitado (env var) — budget caps `$5/dia / $1/hora / $0.50/request` agora ativos
5. Logrotate criado em `/etc/logrotate.d/nox` cobrindo 9 logs

## v3.5 (Apr 20 noite) — Cost reduction pass — Gemini 2.5 Flash quota blowout fix
Diagnóstico: 3 camadas de desperdício:
1. `agents.defaults.heartbeat.model = "gemini/gemini-2.5-flash"` com quota 3M tokens/dia estourada (4.31M consumidos) → todo heartbeat falhava 429 → fallback pra Sonnet via Claude MAX OAuth (cobrado como API extra pós-política Anthropic 3rd-party 2026)
2. `lightContext: true` só no override do `nox`, ausente em atlas/boris/cipher/forge/lex → prompts gordos (~200-365K tokens cada)
3. 30 crons internos do OpenClaw (via `openclaw cron list`, separado do crontab Linux) com 19 deles em `gemini/gemini-2.5-flash` caindo em fallback Sonnet

**Fixes:** heartbeat default migrado pra `gemini-2.5-flash-lite`; `lightContext: true` uniformizado; 19 crons internos migrados; 3 arquivos nox-mem/dist migrados de `gemini-2.0-flash` (deprecated) pra `gemini-2.5-flash-lite`; `auto-update-skills-clawhub` timeout 300s→900s; `heartbeat.to = "<channel_id>"` sem prefixo `channel:`.

**Economia estimada: ~$23-55/mês em extra usage Anthropic.** Backups: `openclaw.json.bak-*` (7 checkpoints) + `cron/jobs.json.bak-pre-migrate-*`.

## v3.4 (Apr 19 noite) — Fake-green incident + boost regression rollback
Forge tentou consertar 3 problemas (reindex preserva access metadata, sqlite-vec loader, Core tier promoção), mas em paralelo introduziu migração V7 (`chunks.source_type` + `SOURCE_TYPE_BOOST` multiplicativo: user_statement=2.0×, compiled=1.5×, external=0.8×) num commit de "fix" sem reportar.

**Impacto:** boost empilhou com TIER×BOOST_TYPES×recency (~10× total), colapsando top-3 em chunks fixos independente da query. **Fake-green:** Forge declarou "1969/1969 vetorizados ✅" mas rodou sem `.env` carregado → `GEMINI_API_KEY not set` → 1972 batches falharam silenciosamente.

**Fix:** `SOURCE_TYPE_BOOST` removido (coluna `source_type` preservada pra uso aditivo futuro); re-vectorize com env (1975/1975, 110s); canário trocado de inglês pra PT-BR; lição `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`.

## v3.3 (Apr 18) — Memory integrity restoration
Diagnóstico via 4 agentes especializados (architect + database-optimizer + sre-engineer + performance-engineer) identificou 5 gaps críticos.
- **Tier 0:** health-probe lê `NOX_API_PORT` do .env (elimina 288 restarts/dia causados por port mismatch contra Chrome squatter em :18800); `busy_timeout=5000` em db.ts; `/api/health.vectorCoverage` reporta estado real
- **Tier 1:** 6627 órfãos em `vec_chunk_map` + 2587 unreferenced em `vec_chunks` limpos; trigger `trg_chunks_delete_cascade` instalado; bug em vectorize.ts (coluna inexistente) corrigido; `embedBatch` reescrito usando `batchEmbedContents` Gemini (serial→batch 50, 3→26.4 chunks/s); re-embed 1951 chunks em 74s

Novos endpoints HTTP: `/api/reflect`, `/api/procedures`, `POST /api/crystallize`, `POST /api/crystallize/validate`. MCP server rebuild. Auto-embed em crystallize.

## v3.2 (Mar 31 noite) — Stability fix
Bot Telegram duplicado eliminado (`claude-telegram.service` + watchdog); crons otimizados; OpenAI removido dos fallbacks (sem créditos); DeepSeek R1 adicionado via Groq (free); RelayPlane atualizado v1.8.37; auth profile cooldown fix.

## v3.1 (Mar 31 tarde) — Infrastructure hardening
12-point audit; cascade fallback; WAL checkpoint; ufw firewall; gateway crash loop protection; health check com auto-restart; Ollama KEEP_ALIVE; swappiness tuning; ExecStartPre fix; agents.defaults restoration.

## v3.0 (Mar 23) — KG v2 + Cross-Agent Intelligence + HTTP API + Dashboard
KG v2 (LLM extraction, 384 entities inicial); HTTP API; Dashboard agent-hub.

## v2.6 (Mar 22) — Hybrid search default
866/866 vectorized.

## v2.5 (Mar 22) — Multi-agent workspace fix, gateway supervision

## v2.2 (Mar 20) — Cross-agent, KG v1 (regex), self-improve

## v2.0 (Mar 17) — MCP server, crons, watcher

## v1.0 (Mar 14) — FTS5, consolidation, Notion sync
