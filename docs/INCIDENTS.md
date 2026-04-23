# nox-mem — Incident Log

> Histórico completo de incidents, com causa raiz e aprendizados. CLAUDE.md só menciona os 3 mais recentes/representativos em forma sumária; detalhe mora aqui.

## 2026-04-23 ~10:30-11:05 (~35min recovery) — Double-failure: models auth login overwrite + graph-memory zombie

Incident composto descoberto durante sessão de auditoria rápida. Dois problemas independentes, um deles latente há 4 dias.

### Failure 1 — `openclaw models auth login` disparou fratricide crash loop

**Trigger:** Toto rodou `openclaw models auth login --provider openai-codex` (~10:31) pra re-autenticar o fallback tier 2 (Codex token expirado).

**Causa raiz:** o comando faz DOIS overwrites destrutivos não documentados:
1. Remove 4 entries vazias de `agents.defaults.models` em `openclaw.json` (claude-cli/claude-opus-4-6, claude-cli/claude-sonnet-4-6, gemini/gemini-2.5-flash-lite, gemini/gemini-2.5-pro) — deixando só o openai-codex recém-adicionado
2. **Reinstala `/usr/lib/node_modules/openclaw/dist/`**, sobrescrevendo o monkey-patch da Issue #62028 em `restart-stale-pids-BvLkOxHa.js`

**Timeline:**
- 10:31 UTC — Toto roda `models auth login --provider openai-codex` (69 paths alterados; backup `.bak` gerado automaticamente)
- 10:32 — diagnóstico mostra registry com 4 entries faltando; restauradas via jq antes de restartar (evitou falha do primary Claude CLI)
- 10:33 — `systemctl restart openclaw-gateway` → inicia normalmente, graph-memory ready, fallback chain nova (claude-cli → codex → gemini-pro) ativa
- 10:56-11:00 — segundo restart (pós-patch graph-memory) → crash loop: 17 restarts em 5min, SIGTERM a cada ~20s, "Gateway already running locally" nos logs. Segundo processo de gateway (fratricide) tentando tomar porta 18789
- 11:00 — root cause confirmada: `grep cleanStaleGatewayProcessesSync` mostra função original restaurada, sem `return []`
- 11:01 — drop-in `Restart=no` em `/etc/systemd/system/openclaw-gateway.service.d/no-restart.conf` pra parar o loop; kill -9 em todos gateway procs
- 11:02 — monkey-patch reaplicado via python replace; backup `.bak-prepatch-20260423-1102`
- 11:03 — drop-in removido, `systemctl start` limpo; 30s observation: 0 restarts, 0 SIGTERM, graph-memory ready

**Fix:** monkey-patch reaplicado. Função `cleanStaleGatewayProcessesSync` agora retorna `[]` direto. Backup preservado.

**Aprendizado:**
- CLAUDE.md regra #6 precisa incluir `openclaw models auth *` como trigger de invalidação do patch (até agora só mencionava `npm update -g openclaw`) — **atualizada 2026-04-23**
- Sintoma claro de patch perdido: "Gateway already running locally" + SIGTERM em ~20s + NRestarts subindo rápido
- Emergency stop: drop-in `Restart=no` dá janela pra intervenção sem systemd spawning novos processes

### Failure 2 — Fase 2.5 graph-memory era "zombie DONE" há 4 dias

**Causa raiz:** plugin `graph-memory@1.5.8` espera que OpenClaw core chame hook `ingest()` pra persistir mensagens em `gm_messages`. OpenClaw 2026.4.21 **não chama mais `ingest()`** — mudou a API do contextEngine. O plugin só tem hook `afterTurn`, `assemble`, `compact`, `bootstrap` sendo chamados, mas `afterTurn` assumia que `ingest()` já havia gravado. Comentário revelador no código:
```ts
// Messages are already persisted by ingest() — only slice to
// determine the new-message count for extraction triggering.
const newMessages = messages.slice(prePromptMessageCount ?? 0);
```

**Sintoma observável (ignorado por 4 dias):**
- `gm_messages=0` rows desde instalação (19/Abr)
- `graph-memory.db` mtime congelado em 2026-04-19 12:09
- Logs mostram `afterTurn sid=X newMsgs=N totalMsgs=0` — `totalMsgs=0` é a pista: ninguém incrementou `msgSeq`
- `journalctl | grep "graph-memory.*ingest"` retorna vazio em 7 dias → hook `ingest` nunca disparou

**Por que passou 4 dias:** Fase 2.5 foi marcada ✅ DONE em 2026-04-21 com evidence="afterTurn events validados nos logs". Validação olhou só linha de log, não contou rows no DB. Classic false-positive de log-only validation.

**Fix:** patch local em `/root/.openclaw/extensions/graph-memory/index.ts` dentro de `afterTurn`:
```ts
// PATCH 2026-04-23: OpenClaw 2026.4.21+ does not call hooks.ingest() —
// persist messages here so gm_messages actually populates.
const newMessages = messages.slice(prePromptMessageCount ?? 0);
for (const m of newMessages) ingestMessage(sessionId, m);
```
Backup: `index.ts.bak-pre-ingest-fix-20260423`.

**Validação pós-patch:** `gm_messages` foi de 0 → 3 → 25 em poucos minutos de tráfego natural. DB file mtime updated, WAL ativo.

**Aprendizado:**
- Nunca marcar feature como DONE só com base em logs — sempre validar com query direta ao DB ou endpoint com rowcount
- Plugin upstream v1.5.8 está incompatível com core 2026.4.21 (API mudou). Registrar issue upstream quando houver janela.
- Observação 7d da Fase 2.5 rodou no vácuo — exit criteria (R7 ≤30K tokens, compressão 75%) nunca mediriam nada pois não havia dados pra comprimir
- Roadmap precisa marcar Fase 2.5 como `✅ DONE (patched 2026-04-23, vendor v1.5.8 incompatible with core 2026.4.21)`

### Escopo combinado das ações tomadas
1. `chmod 600 openclaw.json` (perms regridiam após overwrite)
2. `delivery-queue-cleanup.sh` (0 órfãos)
3. `sessions cleanup --fix-missing` (52 → 30 sessions)
4. `openclaw doctor --fix`
5. Registry restore via jq (4 entries)
6. Monkey-patch #62028 reaplicado
7. graph-memory `afterTurn` patch aplicado
8. Gateway restart limpo

Duração total: ~35 min de diagnóstico + fix.

---

## 2026-04-21 ~15:30-18:00 — Gemini + Perplexity keys exposed/revoked
**Causa raiz:** chave Gemini `AIzaSyBh...SppQCA` revogada pelo Google (scanner detectou exposição). Chave estava hardcoded em `openclaw.json:120,338` + 6 `agents/*/agent/models.json` + em chunks ingested do nox-mem (dados) + backups nightly. Mesmo vetor comprometeu chave Perplexity `pplx-cwAGwoJ0...`.

**Timeline:**
- ~15:30 Google revoga key Gemini
- 15:34 Toto atualiza `.env` com key nova → mas JSONs ainda têm key antiga hardcoded
- 15:30-17:30 vectorize/KG extraction falham silenciosamente; nox-mem-api rodando desde 20-Abr com key antiga em memória
- 17:20 gateway mostra `API_KEY_INVALID` no log
- 17:29 fix aplicado: swap em 7 JSONs + restart gateway + nox-mem-api + watcher
- 17:30 canary OK, 2443/2443 embedded
- 18:00 rotação Perplexity + migração completa pra envsub (`${VAR_NAME}`)

**Fix final:** todas as `apiKey` em configs ativos movidas pra envsub (`${GEMINI_API_KEY}`, `${PPLX_API_KEY}`, etc.). Zero literais de secret em configs ativos. Instalado `gitleaks` global via Homebrew + hook `~/.git-hooks-global/pre-commit` + `git config --global core.hooksPath` — cobre todos os repos do Mac do Toto.

**Aprendizado:**
- Repo privado **não é proteção** contra scanners (keys vazam via snapshots, backups, memory chunks)
- `apiKey` em JSON é anti-padrão — sempre envsub
- Rotação = só `.env` + restart dos 3 serviços (gateway + api + watcher). API em memória tem cache do env do boot
- Pre-commit secret scan é obrigatório (mecânica > disciplina)

---

## 2026-04-21 06:30-07:50 (~1h20 recovery) — Semantic layer wipe + systemic audit
Alert Discord `nox-mem alerts` 06:30 UTC: `🔴 vectorCoverage: 0/2073 embedded` + `🔴 Canary: FAIL`.

**Root cause:** reindex rodado às 01:09 UTC (1884 chunks recriados em 1min) — `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via `trg_chunks_delete_cascade` → `vec_chunks`/`vec_chunk_map` zerados → reindex terminou sem chamar `vectorize()` → semantic layer morto até próximo Sunday (5 dias).

**Fix imediato:** `set -a; . /root/.openclaw/.env; set +a; nox-mem vectorize` → 2073/2073 embedded em 114s.

**Auditoria sistêmica (mesmo turno, 6 fixes):**
1. DB path errado em `nightly-maintenance.sh` (Phase 2 pulava silenciosamente há 1 mês)
2. Watcher duplicado (`nox-mem-watch.service` legado) stopped+disabled
3. Canary cron `0 6 → */30`
4. RelayPlane ressuscitado (`ANTHROPIC_BASE_URL` no .env)
5. Logrotate `/etc/logrotate.d/nox` pra 9 logs nox-*
6. `dist/reindex.js` patchado pra auto-vectorize inline

**Aprendizado:**
- cascade trigger é correto mas incompleto sem contrapartida no escritor
- single point of truth pra ranking/embeddings é o caller (reindex/ingest/consolidate)
- canary 1×/dia é insuficiente — */30min é o mínimo viável
- duplo-watcher em produção passou meses despercebido — `systemctl list-units | grep -i watch` deve ser parte do audit mensal

---

## 2026-04-20 (silent, multi-week) — Gemini 2.5 Flash quota blowout + burn oculto de Anthropic
**Causa raiz compounded:**
1. Heartbeat default + 19 de 30 crons internos OpenClaw apontavam pra `gemini/gemini-2.5-flash`; quota diária (3M tokens) estourada há semanas
2. Toda chamada 429 no Gemini → fallback pra `anthropic/claude-sonnet-4-6` via OAuth Claude MAX; pós-política Anthropic 3rd-party 2026, OAuth MAX de gateway externo é **cobrado como extra usage**
3. `lightContext: true` só no override do `nox`, outros 5 agentes herdavam shallow → prompts gordos
4. RelayPlane zumbi (config vazia, `ANTHROPIC_BASE_URL` não no env) — nenhum budget cap aplicado
5. Discord heartbeat config com `channelId` (chave inválida) → 323 `failed: Unknown Channel` em 14d

**Fix:** heartbeat model + 19 crons + 3 arquivos nox-mem/dist migrados pra `gemini-2.5-flash-lite`; `lightContext: true` uniformizado; `heartbeat.to = "<channel_id>"` correto.

**Aprendizado:**
- `crontab -l` não é fonte de verdade — OpenClaw tem `cron/jobs.json` paralelo com 30+ jobs; sempre checar `openclaw cron list`
- `[cron] payload.model 'X' not allowed, falling back to agent defaults` no log = alerta de cron com modelo morto queimando fallback
- OAuth Claude MAX **não é grátis** em 3rd-party gateway — RelayPlane ou outra camada de budget é obrigatória
- Schema do `heartbeat` não tem `channelId` — chave correta é `to` (genérico, plugin normaliza)

Lição: `shared/lessons/2026-04-20-gemini-quota-blowout-and-cron-hidden-burn.md`.

---

## 2026-04-20 09:07-14:39 (6h downtime) — Gateway fratricide — Issue #62028
Regressão v2026.4.5. Binary v2026.4.14 entra em crash loop via `cleanStaleGatewayProcessesSync()` matando próprio parent. Dois paths:
1. service-mode marker em `gateway-cli-DhgfjzZ0.js:1338` controlado por `OPENCLAW_SERVICE_MARKER`
2. restart subsystem em `restart-CjpAouST.js` chamado por `emitGatewayRestart` — incondicional

Child orphan sobrevive na porta 18789 (PPID=1, `systemd --user`), systemd vê parent morto → restart → fuser kills orphan → loop até StartLimitBurst.

**Fix (4 camadas):**
1. Wrapper `/usr/local/bin/openclaw-gateway-wrapper` com `unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND` + `export OPENCLAW_NO_RESPAWN=1` mas mantendo INVOCATION_ID
2. Config `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off`
3. **Monkey-patch em `dist/restart-stale-pids-*.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]` imediatamente** (chave)
4. health-probe com `reset-failed + start` no crash

Resultado: 4min+ uptime estável, 0 restarts.

**Aprendizado:** dois paths destrutivos precisam dois bloqueios; monkey-patch em dist/ é legítimo quando upstream não tem fix; pesquisar issue tracker ANTES de debug local teria economizado 2h.

Lição: `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`.

---

## 2026-04-19 19:13-22:41 (3h28 silent) — Fake-green incident pós-Forge fix
Forge declarou sucesso ao Toto ("sistema 100% ✅, 1969/1969 vetorizados, 0 órfãos") mas três coisas estavam erradas:
1. `nox-mem vectorize` rodou sem `.env` carregado → 1972 batches falharam silenciosamente
2. Mesmo commit (`d764009`) introduziu `SOURCE_TYPE_BOOST` multiplicativo empilhado em cima de TIER×BOOST_TYPES×recency (~10× stacking)
3. Canário diário em inglês contra corpus PT-BR passou por sorte

**Detecção:** canário falhou exit=3 + api logs `Vector index empty — Falling back to FTS5` + `/api/health.vectorCoverage.embedded=0`.

**Fix:** `SOURCE_TYPE_BOOST` desativado em `search.ts`; `set -a; source /root/.openclaw/.env; set +a` antes de `nox-mem vectorize`; canário trocado pra PT-BR.

**Aprendizado:** Forge reincidiu em "declarar sucesso sem verificar". Regras adicionadas:
- Sempre `curl /api/health` pós-operação
- Separar commits de ranking de commits de fix
- Boost multiplicativo é veneno quando empilhável — usar aditivo

Lição: `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`.

---

## 2026-04-18 (silent, multi-week) — Semantic search silenciosamente morta
**Causa raiz compounded:**
1. Chrome com `--remote-debugging-port=18800` ocupou a porta; `nox-mem-api` migrou pra :18802; `health-probe.sh` continuou batendo em :18800 hardcoded → 12 restarts/hora (288/dia) matando writes mid-flight
2. `vectorize.ts:39` consultava `SELECT chunk_id FROM vec_chunks` mas coluna não existe (chunk_id mora em `vec_chunk_map`) → "already embedded" check sempre vazio
3. Sem FK CASCADE nem trigger, cada `DELETE chunks` por consolidation/dedup deixava órfãos
4. `busy_timeout=0` causava SQLITE_BUSY silencioso sob contenção

Acumulado: 6,627 linhas em `vec_chunk_map` 100% órfãs, 2,587 vetores unreferenced, 0 chunks vivos embedded. `/api/health` mentia `embedded: 6627`. Hybrid search era FTS-only disfarçado.

**Fix (Tier 0+1):** probe port via env; `busy_timeout=5000`; DELETE órfãos + trigger `trg_chunks_delete_cascade`; `vectorize.ts` corrigido (INNER JOIN); `embedBatchAPI` usando `batchEmbedContents` (3→26.4 chunks/s); re-embed full em 74s.

**Aprendizado:** `/api/health` nunca deve derivar de tabela — sempre JOIN com source-of-truth (chunks). Embedding layer precisa de teste canário diário.

---

## 2026-04-01 12:00-15:30 — Gateway crash loop contínuo (~75 restarts)
**Causa raiz:** Node.js 22 emite `DEP0040 DeprecationWarning` (punycode) no stderr; OpenClaw v2026.3.31 interpreta qualquer stderr ERROR como falha e auto-reinicia. Ciclo: gateway inicia → punycode warning 2s depois → restart subsystem mata child → systemd reinicia → loop infinito.

**Amplificadores:** (1) health check cron `/5min não resetava contador; (2) agente `main` com `openai/gpt-5.1-codex` (sem créditos) → boot task falhava; (3) `anthropic-overload-monitor` com prompt 33K tokens > limite 6K TPM Groq.

**Fix:** wrapper `/usr/bin/node` → `/usr/bin/node.bin --no-warnings` suprime DEP0040. Main agent model OpenAI→Sonnet. `anthropic-overload-monitor` desabilitado. Health check com grace period.

---

## 2026-04-01 07:15 — Gateway crash loop (restart counter 4/5)
Chave `"providers"` no root do `openclaw.json` não reconhecida pela versão 2026.3.2 (config foi escrito por versão 2026.3.31 que suporta). Fix: chave removida.

Também: `session-context.json` e `active-tasks.md` stale → deprecated em favor de SESSION-STATE.md.

---

## 2026-03-31 22:00-23:05 — Agentes lentos (Discord/WhatsApp/Telegram)
`claude-telegram.service` + `claude-tg-watchdog.sh` criavam bot Telegram duplicado → conflito 409 + dobro de API requests. Compaction usava OpenAI (sem créditos) em loop infinito.

**Fix:** service desabilitado; watchdog removido; OpenAI removido dos fallbacks; crons espaçados; auth cooldowns limpos; DeepSeek R1 (Groq free) adicionado.

---

## 2026-03-31 ~21:30 — Gateway crash loop (18+)
`ExecStartPre=pkill openclaw-gateway` truncava a 15 chars e não matava nada. Fix: `fuser -k 18789/tcp`.

---

## 2026-03-31 19:43-20:02 — Gateway crash
`openclaw.json` tinha agent keys em formato antigo (flat) + novo (list). Nova versão rejeitou flat como "Unrecognized keys". Processo orphan queimou 105% CPU. Fix: removidas chaves flat.

---

## 2026-03-31 — RelayPlane cascade desligado
`cascade.enabled: false`, `models: []`. Causa raiz do fallback não funcionar durante instabilidade Anthropic. Fix: cascade ativado com 6 modelos e 4 max escalations.

## 2026-03-31 — `agents.defaults` acidentalmente removido
Durante cleanup do config. Fix: seção inteira restaurada com model fallback chain, heartbeat, compaction, memory search.
