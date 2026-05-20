# nox-mem — Incident Log

> Histórico de incidents do **nox-mem core** (chunks, vectorize, reindex, schema migration, semantic layer) e **graph-memory plugin** (KG extract/recall, plugin custom v1.5.8). Incidents de plataforma OpenClaw (gateway, fratricide, RelayPlane, credentials) ficam em `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`.

## 2026-05-20 ~10h BRT (~30min recovery) — VPS IP swap silencioso (false alarm offline)

**Sintoma:** durante deploy Wave A novo (PRs #154/#158), ping em `45.43.85.86` retornou 100% packet loss + curl HTTP 000 em portas 22/2222/2200/18802. Agent VPS-cleanup retornou "host inacessível"; verificação direta da main session confirmou.

**Hipóteses iniciais:** (1) maintenance window, (2) bloqueio por uso CPU/network, (3) firewall mudou, (4) disk full, (5) hardware failure.

**Realidade:** Hostinger fez floating IP swap silencioso. Toto deu novo IP `187.77.234.79`. SSH funcionou de primeira (mesma chave ed25519). Hostname `srv1465941`, uptime **20 days, 50 min** intacto — sem reboot, sem maintenance, sem downtime. Apenas redirecionamento de rota.

**Impact:** ~30min de incerteza, deploy Wave A novo atrasado mas executado com sucesso após IP atualizado. Zero dados perdidos. Service `nox-mem-api` continuou rodando o tempo todo.

**Root cause:** Hostinger floating IP rebalance silencioso (sem notif). Cronograma típico de prov cloud sem mensagem ao tenant.

**Recovery time:** ~30min (ping fail → user verification → SSH retry com novo IP).

**Action items:**
- Adicionar healthcheck script com IP atual em cron (`ssh -o ConnectTimeout=3 root@$VPS_IP 'hostname' || alert`)
- Atualizar `~/.ssh/config` se houver Host alias com IP antigo
- Memory `[[vps-ip-change-2026-05-20]]` cravada como reference
- Memory anterior `[[vps-down-2026-05-20]]` ficou desatualizada — não era outage real

**Cross-links:** PR #158 (api-server fix doc), deploy Wave A novo (sed+scp+build em 187.77.234.79), HANDOFF morning + midday 2026-05-20.

## 2026-05-20 ~09h30 BRT (~15min recovery) — Multi-agent branch checkout race condition

**Sintoma:** PR #154 polish commit landed em `feat/visual-identity-g5-v3-canonical` em vez de `feat/source-type-boost-map-2026-05-20`. `git push` complained sobre upstream errado.

**Root cause:** main session estava trabalhando em `feat/source-type-boost-map-2026-05-20` (PR #154 polish). Spawned designer agent em paralelo pra atualizar README/SVGs em NOVO branch `feat/visual-identity-g5-v3-canonical`. Agent fez `git checkout -b feat/visual-identity-g5-v3-canonical` dentro do MESMO working tree. Quando main thread fez `git commit` em seguida, commit landed na DESIGNER's branch, não na intended.

**Mecânica do bug:** git checkout em same working directory é process-global state — não há per-thread/per-agent HEAD isolation. Ambos main session E spawned agent compartilham mesmo `.git/HEAD`. Quem rodar `git checkout` por último ganha para subsequent operations no working tree.

**Recovery:**
1. `git reset --hard f49660e` na branch errada (remove design commit vazado)
2. `git checkout feat/source-type-boost-map-2026-05-20`
3. `git cherry-pick f49660e` (mesmo SHA, branch certa)
4. `git rebase --onto main f49660e feat/visual-identity-g5-v3-canonical` (descross dos commits)
5. `git push --force-with-lease` em ambas branches

Total: ~15min de git surgery + recovery completa, 0 perdido.

**Fix protocol (cravado):**
- Parallel agents que tocam git devem usar `isolation: "worktree"` na chamada Agent tool
- OR serializar (esperar agent terminar antes de main session continuar)
- Defaulting `isolation: "worktree"` pra qualquer agent que toca git remove entire class de bug
- Sanity check before commit em multi-agent sessions: `git branch --show-current` ANTES de `git add`/`git commit`

**Cross-links:** PRs #154/#155 (recuperados com sucesso após surgery), memory `[[multi-agent-branch-checkout-race]]`, CLAUDE.md `[[worktree-branch-leak-to-main]]` (pattern relacionado).

## 2026-05-18 16:23 BRT (~10min fix) — Deploy Validator CI 100% fail por stderr→JSON contamination

**Sintoma:** 5 PRs consecutivos (#92, #95, #98, #99 e mais um) com Deploy Validator falhando em ~25s. Email do GitHub: "Deploy Validator: All jobs have failed". Run logs mostravam `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` na step "Parse validator output", mas o validator em si passava (summary.fail=0).

**Workflow:** `.github/workflows/deploy-validator.yml`. Trigger: pull_request paths que incluem `docs/DEPLOY-WAVE-B.md`, `staged-*/**`, `scripts/deploy-validator/**`.

**Root cause:** linha 50 invocava `node --loader ts-node/esm src/cli.ts ... > /tmp/validator-report.json 2>&1`. O flag `--loader` é experimental em Node, e emite `(node:XXXX) ExperimentalWarning: --loader is an experimental feature` em stderr. O `2>&1` mergia stderr no stdout antes do redirect, então o warning entrava no JSON file ANTES do `{`. A step seguinte rodava `python3 -c "import json; json.load(sys.stdin)"` → choke em char 0 → exit 1 sempre.

**Fix (commit `62be1f6`):**
1. `node dist/cli.js` em vez de `node --loader ts-node/esm src/cli.ts` — `npm test` (step anterior) já roda `npm run build` per `package.json:7`, então dist/cli.js existe.
2. `2> /tmp/validator-stderr.log` em vez de `2>&1` — stderr separado do JSON.
3. Print de ambos com headers + upload de stderr.log como artifact pra debug futuro.

**Validação:** workflow só dispara em PR (linha 4-5), não em push. Próximo PR aberto valida o fix end-to-end. Fix testado mentalmente: validator escreve JSON via `console.log` (stdout) e errors via `console.error` (stderr) — separação por design.

**Lesson:** [[feedback_stderr_redirect_breaks_json_capture]] — JSON capture via shell redirect deve usar `>` SEM `2>&1`. Pra debug, redirecionar stderr a outro arquivo, nunca mergir.

**Affected runs:** 26055289735, 26055156560, 26054093674, 26053675928, 26053179030.

---

## 2026-05-17 17:03 BRT (~45min trabalho) — graph-memory turn extract parse failure 19.7% → 0%

**Sintoma:** logs do gateway mostravam ~73 falhas/dia (sobre 297 sucessos = **19.7% rate**) com `[graph-memory] extraction parse failed: SyntaxError`. 1 em cada 5 turns NÃO entrava no Knowledge Graph → cross-session recall degradado.

**Plugin:** `graph-memory v1.5.8` (custom mods sobre `adoresever/graph-memory`) em `/root/.openclaw/extensions/graph-memory/`. Extrai triplets `{nodes: [TASK/SKILL/EVENT], edges: [USED_SKILL/SOLVED_BY/REQUIRES/PATCHES/CONFLICTS_WITH]}` de cada turn via LLM (gemini-2.5-flash-lite).

**Root cause:** `src/extractor/extract.ts:365` usava `s.slice(s.indexOf("{"), s.lastIndexOf("}")+1)` — quando LLM gerava `{json válido} ... texto extra/exemplo ... {json2}` (~20% dos casos mesmo com system prompt "禁止解释文字"), o slice englobava lixo no meio → `JSON.parse` quebrava.

**Fix:** substituído `extractJson` por **bracket-balance matcher** depth-counting que respeita strings e escapes (para no primeiro JSON object completo). Build via `bun build` (não tsc — tem `noEmit: true`), restart gateway.

**Validação prod:** 6 extracts seguidos pós-restart, **0 falhas** (100% sucesso). Nodes capturados úteis: `TASK:monitor-context-usage`, `SKILL:execute-script`, `EVENT:script-still-running`, etc.

**Lesson completa:** `lessons/2026-05-17-graph-memory-parse-failure-fix.md` (causa raiz + diff + bracket-matcher code + pegadinhas tsc/bun + rollback procedure).

**Backups:** `dist/index.js.bak-pre-extractjson-fix-20260517` + idem para extract.ts.

---

## 2026-04-27 06:48 BRT (~15min recovery) — Vector coverage 54% gap por session-distill hung 8h (N² em checkpoints HEARTBEAT)

**Sintoma:** morning report às 06:30 BRT alertou `🔴 vectorCoverage: 9390/20201 embedded (54% gap — vectorize not running)`. Health endpoint confirmou `{embedded: 9390, total: 20548, orphans: 0}` — sem corrupção, mas embedded congelado enquanto total cresceu via watcher.

**Root cause:** Phase 4 do `nightly-maintenance.sh` (Sunday tasks, DOW=7) roda `nox-mem session-distill` ANTES do Phase 6 Daily Vectorize. Domingo 26/04 23:00 BRT, session-distill iniciou e ficou pendurado 7h48min (PID 1799773 + 1800385) segurando `/tmp/nox-maintenance.lock`. Phases 5/6/7 nunca executaram. Watcher continuou ingestando chunks normais (digests, USER-PROFILE, sessions wrap-ups) — total foi de 9390 → 20548 sem nenhum embedding novo.

**Causa do hang em session-distill:** algoritmo é O(N²) — para cada candidato extraído pelo LLM Gemini, roda cosine similarity contra todos os chunks distilled existentes. Sessões `cipher:650b0642` (27 checkpoints, 4.5-6MB cada, voltando até 8/abr) e `atlas:cd72e874` (30 checkpoints) acumularam meses de heartbeats redundantes. Filtro de noise em `extractMessages()` cobria SOMENTE `role === "user"` (linha 148, `text.startsWith("HEARTBEAT")`) — respostas do assistant paraphrasing HEARTBEAT.md (`"The user wants the agent to read the file..."`, `"A pending task for Cipher in Notion is..."`, `"HEARTBEAT_OK"`) passavam pelo filtro, eram enviadas ao LLM, viravam memórias candidatas, e cada uma rodava cosine contra o pool inteiro. Log da maintenance virou 2.1MB de `[DEDUP] Suppressed (cosine=9X%)` — dedup funcionando, mas custo CPU explosivo. 4576 dedup events vieram só de `cipher:650b0642`, 1966 de `atlas:cd72e874`.

**Trigger temporal:** primeira execução pós-acúmulo crítico de checkpoints. Não havia timeout no `session-distill` invocation — `|| true` capturava erros mas não duração. Cada checkpoint adicional aumentava N² quadraticamente; o 27º checkpoint do cipher (combinado com o 30º do atlas) cruzou o limite onde a run não termina em 24h.

**Recovery (07:00-07:15 BRT 27/04):**
1. `kill 1799772 1799773 1800385` → script + session-distill mortos sem corromper DB (idempotente)
2. `rm /tmp/nox-maintenance.lock` → libera próximo nightly
3. `nox-mem vectorize` foreground → 11272 embedded, 0 erros, 518s; vectorCoverage 20662/20662 (100%) confirmado via `/api/health`

**Fixes preventivos (mesma sessão):**
1. **Prune de checkpoints velhos:** mtime>14d em cipher+atlas → `/var/backups/checkpoints-pruned/{cipher,atlas}/` (115MB total, restore via `mv`). Cipher 27→18, Atlas 30→23. Reduz ~60% do trabalho do próximo session-distill.
2. **Hard timeout 30min em session-distill:** `nightly-maintenance.sh:75` agora `timeout 1800 nox-mem session-distill ... || log "TIMEOUT/ERROR — continuing"`. Soft-fail garante Phases 5/6/7 sempre rodam mesmo se distill estourar tempo. Backup do script em `.bak-20260427`.
3. **Filtro HEARTBEAT extendido:** `src/session-distill.ts:147-160` — `extractMessages()` filtra agora **user E assistant** (era só user). Cobre `[cron:`, `HEARTBEAT*`, regex `/^heartbeat[_ ]ok\b/i`, conversation history, text<5chars. Build TypeScript OK. Backup em `.bak-pre-heartbeat-filter-20260427`.

**Aprendizados:**
- Pipelines seriais **sem timeout por step** = uma fase travada congela tudo downstream. Cada `>> "$LOG" 2>&1 || true` precisa ser `timeout N ... || log_fallback`.
- Filtros de noise devem cobrir TODOS os roles, não só `user`. LLM extrai memórias de respostas do assistant também — heartbeat-loops paraphrasados pelo LLM são tóxicos pro dedup downstream.
- Algoritmos O(N²) em nightlies acumulam tech debt invisível — um threshold de "max candidates per run" é defesa em profundidade que precisa entrar em V1.7.
- Morning-report deveria expor não só `vectorCoverage` mas TAMBÉM "última nightly completou? duração? Phases pendentes?" — ausência dessa visibilidade atrasou detecção em ~7h.

## 2026-04-25 ~07:00 BRT (~12min recovery) — Section/retention metadata wipe via reindex (não-nightly)

**Sintoma:** sanity check matinal mostrou `sectionDistribution.compiled=0, frontmatter=0, timeline=0` (esperado 183/183/366), `retention.never_decay=25` (esperado 104), total 9173 vs 9541. Shadow telemetry às 23:45 BRT 24/04 ainda mostrava sections populadas — regressão entre 23:45 e o próximo sanity check.

**Root cause arquitetural:** `reindex.ts` (callable manualmente OU via `nightly-maintenance.sh`) faz `DELETE FROM chunks` + loop chamando `ingestFile()` (genérico) sobre **todos** os `.md` do workspace, incluindo os 183 arquivos `memory/entities/<type>/*.md`. `ingestFile()` não conhece o formato 3-section (compiled/frontmatter/timeline) — gera 1-2 chunks genéricos por arquivo com `section=NULL`, ignorando o N+2 split que `ingestEntityFile()` produz. `accessSnapshot` em reindex.ts só preserva `tier/access_count/importance/last_accessed_at`, não `section` nem `retention_days` — metadados nukados sem aviso. Mesmo padrão arquitetural que watcher (`watch.ts:71` chama `ingestFile`).

**Trigger temporal (forensic post-recovery):** investigação dos timestamps no DB mostrou que TODOS os 8808 chunks não-entity foram criados num **único minuto às 01:03 UTC 25/04 = 22:03 BRT 24/04** (assinatura clássica de reindex full). NÃO foi o nightly cron OS (esse rodou 23:00 BRT, 1h depois — e Phase 2/agent-reindex foi skipped por ser DOM par dia 24). **Foi a OpenClaw cron `end-of-day`** (id `ee15b430-ec10-4698-b25f-7fc4e1169417`, schedule `0 22 * * *`) — cron interno da plataforma OpenClaw que dispara um agent turn diariamente às 22:00 BRT. O prompt do agent tem 14 steps; **step 11 é literalmente `Execute: nox-mem reindex`**.

**Timeline:**
- 22:03 BRT 24/04 — reindex full disparado; 8808 chunks recriados via `ingestFile()` genérico, sections nukadas
- 23:00 BRT 24/04 — nightly cron dispara `nightly-maintenance.sh` mas Phase 2 skipped (DOM par); só Phase 6 vectorize roda + Phase 7 WAL
- 23:03 BRT — vectorize embed 3923 chunks; total 9173, vc 100%
- 23:45 BRT — section-shadow-telemetry roda mas mede events da janela 24h ANTES — não detecta a regressão
- 06:50 BRT — sanity check matinal expõe regressão
- 07:05 — backups: `ingest.ts.bak-pre-section-fix-20260425`, `reindex.ts.bak-pre-section-fix-20260425`
- 07:06 — patch em `ingest.ts`: guard no topo de `ingestFile()` rotando `memory/entities/*.md` → `ingestEntityFile()`. Cobre reindex AND watcher num só lugar.
- 07:07 — `npx tsc` build OK; `systemctl restart nox-mem-watcher`
- 07:09-07:10 — loop `nox-mem ingest-entity` × 183 files (100% sucesso, 0 fail)
- 07:11 — `nox-mem vectorize`: 732 novos chunks embedded em 40s
- 07:12 — `/api/health`: `compiled=183, frontmatter=183, timeline=366, embedded=9540/9540, orphans=0` ✅

**Fix permanente:** routing fica em `ingestFile()`, não em caller — qualquer entry point (reindex, watcher, future bulk imports) automaticamente roteia entity files corretos. Próximo nightly 23:00 BRT (25/04) deve mostrar zero regressão. Validação canônica = `/api/health.sectionDistribution.compiled == 183`.

**Fix #2 (paralelo):** patch no end-of-day cron via `openclaw cron edit ee15b430-... --message "..."` — step 11 mudado de `nox-mem reindex` → `nox-mem consolidate`. Consolidate é leve (não DELETE chunks).

**Aprendizado:**
- **Validar com section data, não só logs** — shadow telemetry às 23:45 capturou estado bom porque agrega events de search 24h ANTES; o reindex de 22:03 já tinha quebrado tudo. Section count + recently-modified file timestamps são canaries melhores
- **Routing por path → handler especializado pertence ao entry point comum** (ingestFile), não ao caller — senão cada novo caller (reindex.ts E watch.ts) duplica o erro
- **Cron interno do OpenClaw é separado de cron OS** — investigação precisa cobrir AMBOS: `crontab -l` (OS) E `openclaw cron list` (internal)

> NOTA: Eventos paralelos da mesma janela (gateway crash loop user-systemd v4.15, logrotate copytruncate) migrados pra `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`.

---

## 2026-04-21 06:30-07:50 (~1h20 recovery) — Semantic layer wipe + systemic audit

Alert Discord `nox-mem alerts` 06:30 UTC: `🔴 vectorCoverage: 0/2073 embedded` + `🔴 Canary: FAIL`.

**Root cause:** reindex rodado às 01:09 UTC (1884 chunks recriados em 1min) — `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via `trg_chunks_delete_cascade` → `vec_chunks`/`vec_chunk_map` zerados → reindex terminou sem chamar `vectorize()` → semantic layer morto até próximo Sunday (5 dias).

**Fix imediato:** `set -a; . /root/.openclaw/.env; set +a; nox-mem vectorize` → 2073/2073 embedded em 114s.

**Auditoria sistêmica (mesmo turno, 6 fixes — itens nox-mem):**
1. DB path errado em `nightly-maintenance.sh` (Phase 2 pulava silenciosamente há 1 mês)
2. Watcher duplicado (`nox-mem-watch.service` legado) stopped+disabled
3. Canary cron `0 6 → */30`
4. `dist/reindex.js` patchado pra auto-vectorize inline

> Itens OpenClaw (RelayPlane ressuscitado, logrotate /etc/logrotate.d/nox) migrados pra `openclaw-vps/infra/docs/INCIDENTS.md`.

**Aprendizado:**
- cascade trigger é correto mas incompleto sem contrapartida no escritor
- single point of truth pra ranking/embeddings é o caller (reindex/ingest/consolidate)
- canary 1×/dia é insuficiente — */30min é o mínimo viável
- duplo-watcher em produção passou meses despercebido — `systemctl list-units | grep -i watch` deve ser parte do audit mensal

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

> **Incidents OpenClaw plataforma migrados em 2026-05-01 pra `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`:**
> - 2026-04-23 models auth login overwrite + graph-memory zombie
> - 2026-04-21 ~15:30 Gemini + Perplexity keys exposed/revoked
> - 2026-04-20 Gemini quota blowout + Anthropic burn oculto
> - 2026-04-20 09:07 Gateway fratricide #62028
> - 2026-04-01 12:00 Gateway crash punycode
> - 2026-04-01 07:15 Gateway crash providers key
> - 2026-03-31 todos (gateway crashes, agentes lentos, RelayPlane cascade, agents.defaults removido)
