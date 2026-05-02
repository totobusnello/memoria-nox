# nox-mem HANDOFF — estado vivo

> **Atualizado:** 2026-05-01 ~21:30 BRT (**Marathon noite: 15 deliverables + 3 bug fixes**)
> Substitui a sequência `handoffs/MASTER-HANDOFF-<date>.md`. Este arquivo único é mantido vivo a cada sessão.
> Histórico individual em `handoffs/_archive/`. Para "o que vem" → `docs/ROADMAP.md`. Para "por quê" → `docs/DECISIONS.md`.

## Sessão atual (2026-05-01 noite ~20h30→21h30 BRT) — G02 + G03 + 5 specs + 3 bug fixes + F12/F13/F14 DONE

### Resultado: ✅ section_boost ativo + 3 docs/specs novos + retry NUVIVI/CONTRATOS background

**Entregas:**
- **G02 ✅ APLICADO** — section_boost shadow→active após análise 7d (compiled +100% n=1252, frontmatter +49% n=315, timeline -17% n=11). `/root/.openclaw/.env` linha 43 `NOX_SECTION_BOOST_MODE=active`. Backup: `.env.bak-pre-section-boost-active-20260501-203152`. Services restarted.
- **G03 ✅ DONE** — 3 source files arquivados em `/root/.openclaw/workspace/memory/{projects,decisions,lessons}.md.archived-20260502`. 8 chunks órfãos (lessons=4, decisions=2, projects=2) cleanup no consolidate noturno.
- **Spec E03a criada** — `specs/2026-05-01-E03a-spo-injection.md` (`<vault-facts>` block via KG, top-K simples, schema zero-mudança, env-var driven shadow→active, 1.5h impl).
- **Spec E04a criada** — `specs/2026-05-01-E04a-focus-boost.md` (`focus set <topic>` 1.4×/0.75×/1.0, cache `/tmp/nox-mem-focus-<session>.json` TTL 7d, fail-open, 1.5h impl).
- **R01a revisado** — `specs/2026-04-27-R01a-eval-harness.md` ready to execute Maio 2026 (5h estimate, schema v11 ou v12 dependendo da ordem com E05).
- **E02 audit** — gap real é **954 PDFs** (não 2.269): PPR 372 / PESSOAL 250 / CONTRATOS 171 / EMPRESAS Cont 83 / NUVIVI 55 / outros 23. Cobertura A6 = 3.541/4.495 = 79%.
- **E02 retry B-target IN-PROGRESS** — 226 PDFs (NUVIVI 55 + CONTRATOS 171) sincronizados pra `/root/.openclaw/workspace/memory/mac-docs/`. Script `/root/.openclaw/scripts/pdf-retry-target.sh` rodando em tmux session `pdf-retry-e02`. Log `/tmp/pdf-retry-target.log`. ETA ~2-4h.
- **ROADMAP atualizado** — E02 marcado IN-PROGRESS com cobertura 79%; E12 escopo expandido pra incluir gap residual (~728 PDFs PPR+PESSOAL+size-rejected).

**Quick wins extras (mesma sessão noite):**
- ✅ DECISIONS.md update — bloco 2026-05-01 (G02/G03/E02/lições)
- ⚠️ Cleanup 8 chunks órfãos G03 — bloqueado (sqlite3 sem vec0); deferido pro consolidate noturno
- ✅ Triagem op-audit-e2e — root cause identificado em `db.js:7` (DB_PATH ignora NOX_DB_PATH env); fix=1.5-2h
- ✅ **F12 ✅ DONE** — RB-05 Gemini SPOF mitigation playbook (Tier 1/2/3) em `docs/RUNBOOKS.md`
- ✅ **F13 ✅ DONE** — cost projection alt em `runbooks/cost-projection-alt-providers.md` (4 cenários 12mo, switch OpenAI 1h)
- ✅ **F14 initial DR drill executed** — `runbooks/dr-drill-quarterly.md` documentado; RTO real 5s validate; **BUG achado: user_version=0 em prod** (schema v10 features presentes mas pragma não bumped). Cron quarterly pendente.
- ✅ **F10 design spec criada** — `specs/2026-05-01-F10-observability-dashboard.md` (4 painéis no agent-hub-dashboard, 2.5-3h impl)

**Carry-over monitoring:**
- `tmux attach -t pdf-retry-e02` (VPS) ou `tail -f /tmp/pdf-retry-target.log`
- Ao fim: `curl /api/health | jq .chunks.total` deve subir; vectorize follow-up para novos chunks
- Validar focus_mode=shadow não atrapalhou ranking (telemetria search 24h)

### Próxima sessão (após retry NUVIVI/CONTRATOS terminar)
- Pós-retry: ingestar .md gerados (watcher pega automático ou rodar `nox-mem reindex` se gap)
- Implementar E03a (1.5h) + E04a (1.5h) em branches paralelas se janela disponível
- R01a impl Maio (4-6h) — schema v11 (PRAGMA user_version 10→11) + tabelas eval_*
- **F10 dashboard impl** (2.5-3h) — feat branch no `agent-hub-dashboard`
- ~~F14 cron quarterly + script~~ ✅ **DONE 2026-05-01 21:29** — `/root/.openclaw/scripts/dr-drill.sh` deployado, cron `0 9 1 1,4,7,10 1` instalado, smoke test OK (drill log JSON em `/var/log/nox-dr-drill-quarterly.log`), Discord alert configurado. Próxima execução auto: 2026-07-06.

### Bug fixes resolvidos esta sessão (2026-05-01 noite extra)
- ✅ **#3 cleanup 8 chunks órfãos G03** — deletados via better-sqlite3 com vec0 loaded (cascade trigger executou). DB total 62.927 → 62.919.
- ✅ **#2 PRAGMA user_version aligned** — bumpado 0 → 10 pra match com `meta.schema_version`. Backup `/var/backups/nox-mem/pre-bump-pragma-20260501-211006.db`. Achado real: não era bug schema, era inconsistência fonte (`meta.schema_version` vs `PRAGMA user_version`); só `op-audit` usa PRAGMA como sentinel safeRestore. Future ops_audit registrará schema_user_version=10.
- ✅ **#1 op-audit-e2e fix** — `src/db.ts` agora honra `NOX_DB_PATH` env (priority: NOX_DB_PATH > OPENCLAW_WORKSPACE > __dirname). Test setupDb refeito pra delegar schema build ao ensureSchema (em vez de pré-criar tabela com schema v1 minimal que conflictava com migrations v3+). **27/27 tests pass** (retention 20 + op-audit-e2e 7), zero regression. Build redeployado, prod nox-mem-api restarted healthy.

---

## Sessão anterior (2026-05-01 tarde) — Split de repos

### Resultado: ✅ memoria-nox enxuto, conteúdo OpenClaw migrado

- Criado `~/Claude/Projetos/openclaw-vps/` (umbrella) com `infra/` + `nox-secretary/` + `_future/`
- `memoria-nox/CLAUDE.md` slim 193→139 linhas (só memoria-nox core)
- `memoria-nox/docs/INCIDENTS.md` slim — entries OpenClaw migrados pra `openclaw-vps/infra/docs/INCIDENTS.md`
- 2 plans + 6 audits OpenClaw movidos pra `openclaw-vps/infra/{plans,audits}/`
- 9 scripts OpenClaw (upgrade/rollback/monkey-patch) sincronizados da VPS pra `openclaw-vps/infra/scripts/`
- 2 scripts secretário (morning-report, log-bvv-message) sincronizados pra `openclaw-vps/nox-secretary/scripts/`
- Backups de antes do split em `_archive-pre-split-20260501/`
- Routing global em `~/Claude/Projetos/CLAUDE.md` ensina Claude qual repo abrir por tema

### Próxima ação memoria-nox
Foco volta pra evolução pura: sair do schema v10 → v11 (TBD), continuar Fase 1.7 salience activation, refinar entity ingestion.

---

## Sessão anterior (2026-05-01 manhã) — Marathon stability + performance

## Sessão atual (2026-05-01 manhã) — Marathon stability + performance

### Resultado: ✅ sistema 5x mais rápido + 100% schema v.29 canonical

**Métricas pós-sessão:**
- Gateway estável (PID atual, 9 plugins), drift OK contínuo desde 08:50 BRT
- Search p50: 3000ms → **620ms** (FTS5 optimize após Graphify de 04-27)
- Restart loop: 4/h → **0** (drift script bug fix: pgrep regex → systemctl MainPID)
- 300s timeouts/48h: 3 → 0
- nox-mem.db: 62.905 chunks, vectorCoverage 100%, KG 402 entities + 544 relations
- SOUL.md bootstrap chars (6 agents): 88K → 26K (**-70%** via slim per-agent)
- Slack token: rotacionado completo (old HTTP 401 revoked, new xoxp+xoxb live)
- Anthropic Max OAuth zero-cost mantido ($0/30d billing primary)
- Schema v.29: agentRuntime=`pi` (era `claude-cli` morto), anthropic.baseUrl=api.anthropic.com (era :4100), fallback `[gpt-5.5, gemini-2.5-pro]` sem dup primary

**56 tasks completadas** — categorias:
- 8 bugfixes críticos (drift, agentRuntime, baseUrl, version-check cron, vectorize-weekly harness, etc)
- 7 performance (FTS5 optimize, VACUUM, plugins disable, cache resize, bootstrap reduce, graph-memory compact, monthly schedule)
- 6 security (Slack rotation, pre-commit hook local, Gemini key sanitize, gitleaks confirmed, Anthropic stale 401)
- 6 memória cleanup (pending.md 15→10, vestigial archives 5 agents, prepare-briefing 10→15, CLAUDE.md fontes corrigidas)
- 6 SOUL.md slim per-agent
- 8 docs reescritos (CLAUDE.md, ARCHITECTURE, HANDOFF, DECISIONS, RUNBOOKS, OPTIMIZATION-04-24 banner, V25/V26 banner, v29-upgrade)
- 1 incident próprio recovered (DB corruption por sed-i em SQLite, lição salva)
- 1 cron follow-up agendado VPS (5 dias)

**Lições salvas (memory):**
- `feedback_gateway_drift_pgrep_regex_bug.md` — drift watchers usar systemctl MainPID
- `feedback_never_sed_binary_files.md` — sweep secrets sempre filtrar tipo arquivo
- `project_2026_05_01_marathon_session.md` — recap completo

**Audit completo:** `audits/2026-05-01-marathon-session.md` (10.5K chars).
**Lição na VPS nox-mem:** `shared/lessons/2026-05-01-marathon-session.md` (15 chunks ingestados, searchable).

**Carry-over monitoring:**
- Cron VPS `0 9 2-6 5 *` → `/root/.openclaw/scripts/marathon-followup-check.sh` rodando 5 dias
- Reporta Discord channel 1480060616021643336 + WhatsApp Toto no dia 5 ou all-clear

---

## Sessão anterior (2026-04-30 noite) — OpenClaw v.29 upgrade

### Resultado: ✅ rodando v2026.4.29 (a448042)
- 3 services active (gateway/api/watcher)
- vectorCoverage 62816/62861 (99.93% — gap 45 chunks recentes não-vetorizados, normal)
- salience.mode=active preservado
- sectionDistribution preservada (compiled=183, frontmatter=183, timeline=366)
- Phase 4 watch loop: max 3 restarts iniciais (Discord rate-limit slash deploy retries), depois estável em 1
- D5/D6/D7 deltas pós-swap: todos PASS (orphan recovery, port conflict, blank prompts)

### 4 bugs encontrados + fixados (script-level)
1. `reapply-monkey-patch.sh` — `ls | head -1` pegava wrapper alfabético em layout 2-arquivos. Fix: `grep -l "function cleanStaleGatewayProcessesSync(portOverride) {"` filtra impl file.
2. `upgrade-zero-downtime.sh` Phase 0e — `grep -c "..." || echo "0"` gerava `0\n0`. Fix: `2>/dev/null || true; ${VAR:-0}`.
3. `upgrade-zero-downtime.sh` Phase 1d — staging precisa `--port $STAGING_PORT` explícito (.29 lock check global novo, default tenta 18789 prod).
4. `upgrade-zero-downtime.sh` Phase 3b — `mv staging/openclaw → /usr/lib/...` deixa transitive deps (dotenv novo na .29) órfãs causando `ERR_MODULE_NOT_FOUND`. Fix: substituído por `npm install -g openclaw@$TARGET` que gerencia deps native.

### Phase 5 final validation reportou 4 FAILs falsos (script verifica formato pré-.29):
- `primary model == anthropic/claude-sonnet-4-6` → openclaw.json schema OK na real (script ainda procurava `claude-cli/*` deprecado em v.26)
- `commands.restart == false` → idem
- `nox-mem-api healthy` → /api/health responde 200, gap de check no script
- `sessions.json not stuck on non-claude model` → main tem 27 sessions, nox=5, atlas=1, etc — normal

### Backups + rollback
- `/usr/lib/node_modules/openclaw.bak-pre-2026.4.29` (snapshot .26)
- `/root/backups/openclaw-pre-2026.4.29/` (openclaw.json.bak + sessions.json.bak)
- `/root/upgrade-zero-downtime.sh.bak-pre-v29-fix-20260430` (script pré-fixes)
- Rollback: `bash /root/rollback-zero-downtime.sh 2026.4.29 /usr/lib/node_modules/openclaw.bak-pre-2026.4.29 /root/backups/openclaw-pre-2026.4.29`
- **Cleanup pós 24h estável:** `rm -rf /usr/lib/node_modules/openclaw.bak-pre-2026.4.29`

### Próximas ações (24-48h monitoring)
- Verificar fratricide events: `journalctl -u openclaw-gateway --since "6h ago" | grep -cE "fratricide|Gateway already"` deve permanecer 0
- Verificar Discord rate-limit estabilizando (slash command deploy retries esperados no startup)
- Smoke manual cada persona via Discord
- Update `MEMORY.md` com observation v.29 upgrade success

### Bonus: config drift correction pós-upgrade (descoberto durante validação)
`npm install -g openclaw@2026.4.29` reescreveu `openclaw.json` defaults — RelayPlane reativou em :4100 + `models.providers.anthropic.baseUrl` voltou pra `http://127.0.0.1:4100` (proxy redundante). Correção:
- `openclaw config set models.providers.anthropic.baseUrl "https://api.anthropic.com"` → API oficial direto
- `openclaw config set agents.defaults.model.primary "anthropic/claude-sonnet-4-6"` → Max OAuth zero-cost (Forge override = `anthropic/claude-opus-4-7` em `agents.list[forge]`)
- `openclaw config set agents.defaults.model.fallbacks '["openai-codex/gpt-5.5","gemini/gemini-2.5-pro"]'` → 2 paid backups (provider `claude-cli` removido em v.26; `anthropic/*` na primary já é Max OAuth)
- `systemctl stop relayplane-proxy && systemctl disable relayplane-proxy` → permanente (NÃO REATIVAR)
- Sessions reset (regra 11): main 28→10, nox 5→1, atlas 1→0, boris 4→1, cipher 1→0, forge 4→0, lex 1→0 — purgou 24 sessions stuck em Gemini fallback
- Backup pré-correção: `/root/.openclaw/openclaw.json.bak-pre-relayplane-disable-20260430` + `/tmp/sessions-bak-pre-reset-20260430/`

**Auto-prevenção em upgrades futuros:** `upgrade-zero-downtime.sh` Phase 5/6 + `upgrade-v29-deltas.sh --post` agora detectam + auto-remediam esse drift (baseUrl, RelayPlane state, fallback leak, sessions stickiness).

---

## Sessão anterior (2026-04-30 manhã) — G01 + cleanup

### Manutenção infra
- **Ubuntu 25.10 + kernel `6.17.0-22-generic`** (era `6.17.0-20`) — apt upgrade + reboot zero-downtime, 0 fratricide pós, monkey-patch íntegro, creds `chattr +i` preservado
- **`nox-mem-watcher` agora `enabled`** (era `disabled` rodando manual; persiste em próximos reboots)
- "CVE-2026-31431 / Copy Fail" mensagem recebida → confirmado **scam** (sem fonte oficial NVD/distro)

### G01 Salience activation ✅ ATIVO
```
mode: shadow → active
promote_candidates: 191
retain: 63
review_needed: 16608
archive_candidates: 45743
mean: 0.1106 / median: 0.078
```
Comando: `bash /root/.openclaw/scripts/activate-salience.sh --apply`. Pre-snapshot saved. Rollback disponível (`--rollback`). **Monitor 48h** /api/health.salience + telemetria search.

### P1 HIGH cleanup (3 fixes em scripts VPS)
- **CODE-5** `/root/.openclaw/scripts/pdf-batch.sh` — log paths SCANNED/ERR + real exit code (1 se ERR>0)
- **CODE-6** `/root/.openclaw/upgrade-watcher/check.sh` — gh CLI auth/network failure detectado + meta-alert Discord (não mais silent exit 0)
- **CODE-8** `/root/upgrade-zero-downtime.sh` Phase 4 — journalctl 1× por iteração + sentinel pra falha (auto-rollback gate não fica cego se journal quebrar)
- Backups `*.bak-CODE{5,6,8}-20260430-130927`

### Bonus cleanup
- **CODE-18** `cross-agent-sync.sh` — header doc GNU PCRE dependency
- **CODE-19** `sync-verify.sh` — `printf %s\n` real newlines + MSG via `printf` (Discord render multi-line)
- **CODE-17** já fixed em commits anteriores (linhas 61/63 já com `[notify]` prefix)
- **CODE-20** mantido (LOW informativo — emojis OK em Discord/WhatsApp UTF-8; SSH terminal raro)
- **Test invocation fix:** `package.json.scripts.test = "node --test dist/__tests__/*.test.js"` (Node 22 quebra `--test <dir>`); `npm run test:retention` 20/20 pass

### Issue residual identificada (não bloqueia G02)
- **op-audit-e2e tests:** 2/27 fails em `npm test` (success path INSERT row + failure path snapshot preserved). Erro: `'snapshot file on disk' actual: false`. Sintoma: env `NOX_PRE_OP_SNAPSHOT_DIR` honored em `op-audit.ts:43` mas snapshot não cria no path setado. Triagem próxima sessão (não bloqueia G02 amanhã).

## Última sessão (2026-04-28) — Optimization Marathon

| Métrica chave | Antes | Depois |
|---|---|---|
| OpenClaw | 2026.4.25 | **2026.4.26** |
| Turn latency | 39.8s | **10.4s** (-74%) |
| Boot gateway | ~10s | 5.7s |
| `.git` workspace | 11GB | **134MB** (-99%) |
| Skills missing | 39 | **0** |
| Heartbeats/dia | 384 | 144 (-62.5%) |
| Token revogado 6 personas | sim (silent 401) | resolvido |
| Disk free `/` | 114GB | 116GB |

**Documentação completa:** `docs/RUNBOOKS/2026-04-28-optimization-marathon.md` (458 linhas, reproduzível).
**Plan original:** `plans/2026-04-28-openclaw-v2026.4.26-upgrade.md`.

---

## 1. Sanity check (1-cmd)

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  total: .chunks.total,
  embedded: .vectorCoverage.embedded,
  salience: .salience.mode,
  section: .sectionDistribution,
  opsAudit: .opsAudit,
  db: .dbSizeMB
}"'
```

**Última leitura (2026-04-27 ~19:00 BRT pós-A1+A3+A4+A5+A6):**
```
total:    62836 chunks (+42005 vs baseline manhã = +202% / TRIPLICOU)
embedded: 62836 / 62836 (100%, gap=0)
salience: shadow (gate G01 04-30)
section:  compiled=183, frontmatter=183, timeline=366, legacy=62104
opsAudit: 1 op 24h (compact 02:00 ✓)
db:       1.016 GB (era 318MB pré-A1, +220% / >1GB)
search:   smoke OK em Granix-App, Claude skills, biolab-ai, agent-orchestrator, NUVIVI (debenture/PDF), PPR (xlsx/pptx/PDF licitação)
```

## 2. Improvements audit

```bash
ssh root@100.87.8.44 '/root/bin/improvements check'
```

**Última leitura:** **13/13 OK** (7 critical + 6 warn-only, todos pass).

## 3. Onde paramos

Sessões 2026-04-25/26/27 entregaram:
- **F01-F08** ✅ Bloco I hardening completo + B1 Obsidian + B3 backlog
- **F07** ✅ OpenClaw upgrade defense system (commit 3b9e23c, pushed)
- **Consolidação documental** ✅ ROADMAP/DECISIONS/HANDOFF (3 arquivos canônicos) + README + ARCHITECTURE + RUNBOOKS + CONTRIBUTING (4 docs novos via agents)
- **Sistema unificado de IDs** F/E/R/P/G/D (substitui 6+ namespaces antigos)
- **Reorganização repo:** plans/_archive (25), handoffs/_archive (9)
- Review triplo (architect + critic + architect-reviewer): 14 mudanças aplicadas no ROADMAP (capacity recalibrada, R01 split skeleton/curation, E03/E04 split implement/activate, F09-F16 gaps adicionados)
- **R01a Eval Harness design spec** ✅ commit 3d85ffd (424 linhas, schema v12 + CLI + métricas)
- **Sprint A1 ingestão massiva** ✅ +19.070 chunks (graphify-ingest 9 repos + 7 repos pequenos + Claude workspace scope curado)
  - Fase 1: graphify-ingest 9 repos com graphify-out → +1.046 graph_nodes
  - Fase 2a: clone+ingest 7 repos pequenos (biolab-ai, curso-ai, posts-linkedin, grancoffee, superfrio, fake-news-check, claude-project-template) → +304 markdown chunks
  - Fase 2b: Claude workspace scope curado (docs+agents+skills+commands+Projetos, _retired excluído) → +17.714 chunks de 1.356 md
  - Decisão: SKIP powerpoint-templates (114MB visual, gated Tier 3 OCR), SKIP nox-workspace (257MB, scope decision posterior), SKIP A2 ~/Desktop (transitório)
- **Sprint A3 Mac local Claude/Projetos delta** ✅ +863 chunks
  - rsync `~/Claude/Projetos/agent-orchestrator/` → VPS shared/imports/ (143MB, exclude .git/node_modules)
  - 106 md ingestados manualmente (watcher race em rsync rápido)
  - Outros 240 md de ~/Claude/Projetos/* duplicariam shared/imports/<repo>/, scope cut
- **Sprint A4 ~/Documents office files (docx+xlsx+pptx)** ✅ +2.469 chunks
  - rsync seletivo: 536 docx + 976 xlsx + 83 pptx → VPS mac-docs/ (NUVIVI, PPR, PESSOAL, CONTRATOS, BANCOS, EMPRESAS Cont)
  - Conversão pipeline expandido: pandoc (docx) + libreoffice-calc (xlsx→csv) + **markitdown[pptx]** (pptx→md)
  - markitdown novo na stack (Microsoft, 117k stars, MIT, Python) — resolveu pptx que libreoffice-impress sem filtro txt
- **Sprint A5 — pipeline unified script** ✅
  - convert-office-to-md.sh refatorado: markitdown primary + pandoc/libreoffice fallback
  - Idempotente (skip se .md newer than source)
  - /root/.openclaw/scripts/pdf-batch.sh standalone reusável
- **Sprint A6 — PDF batch (Tier 2 antecipado, sem OCR)** ✅ +19.602 chunks
  - 4.494 PDFs no ~/Documents (NUVIVI 546 + PPR 1807 + PESSOAL 1163 + CONTRATOS 689 + BANCOS 142 + 84 não-sync EMPRESAS Cont com espaço)
  - rsync paralelo 5 dirs simultâneos
  - Markitdown[pdf] via tmux session (após 2 falhas: parent-shell death + systemd quoting hell + watchdog buggy 69 procs simultâneos)
  - 1.444 PDFs text-layer convertidos com sucesso → 19.602 chunks
  - 781 PDFs scanned/imagem (NFs, fotos, comprovantes) detectados como output <100 chars e descartados (esperam OCR Tier 3 / E12)
  - Vectorize 100% sucesso (15.693 embedded em 13min, 0 errors no retry sem load alto)
  - Lições: 1) systemd-run com `${var}` precisa script standalone; 2) 69 markitdown simultâneos sufoca VPS (load 22, OOM); 3) tmux é a abordagem mais estável; 4) batch idempotent é safety net

Sistema saudável e mais rico. Em **holding pattern** até G01 (3 dias).

## 4. Próxima ação concreta

Hoje é **2026-04-30** (quinta). **G01 ✅ DONE. G02 amanhã 05-01.**

### 🔴 P0 — G02 amanhã (Section_boost decision)
```bash
bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7
```
Decidir: ativar `section_boost` no ranking ou manter shadow-mode.

### 🟡 Hoje opcional (se houver tempo)
| ID | Trabalho | Esforço | Valor |
|---|---|---|---|
| E03a | Design spec A6 SPO Injection (`<vault-facts>` block via KG) | ~1.5h | Alto — execução rápida pós-G03 |
| E04a | Design spec A7 Session Focus Boost (`focus set <topic>` 1.4×/0.75×) | ~1.5h | Alto |
| E09 | Decisão "Fase 1.7b dormente vs E09 executável" | ~30min | Médio (destrava Maio) |
| op-audit-e2e | Triar 2 fails em snapshot path/env | ~30min | Médio (hygiene) |

### Atividade 2026-04-30 (esta sessão) — RESUMO
- ✅ Manutenção infra: kernel upgrade + reboot zero-downtime
- ✅ **G01 Salience activated** (mode shadow → active)
- ✅ 3 P1 HIGH (CODE-5/6/8) — pdf-batch logging, release-watcher gh-fail, upgrade-zero-downtime journalctl
- ✅ Bonus: CODE-18/19, npm test invocation fix
- ⚠️ 2 op-audit-e2e tests failing (snapshot env override) — flag follow-up

## 5. Eventos agendados (gates + waves)

- ~~**2026-04-30** quinta — **G01** Salience activation~~ ✅ DONE 13:11 BRT (mode=active)
- **2026-05-01** sexta — **G02** Section_boost decision (`analyze-shadow-telemetry.sh 7`)
- **2026-05-02** sábado — **G03** Archive 3 source files + iniciar E02 + E03a + E04a paralelo
- **05-09** quinta — **E03b + E04b activate** (após shadow 7d)
- **Maio 2026** — Wave 1 (E05 → E06/E07/E08) + R01a eval skeleton (antecipado!)
- **Jun-Jul 2026** — R01b curadoria 50 queries + R01c baseline + E10 candidate (gated)
- **Ago 2026** — R02 paper v2
- **Set+ 2026** — E11 reflect cache + F15 SEH + **P01 NOX-Supermem productização**

## 6. Contexto necessário pra retomar

**Mínimo absoluto (3 arquivos):**
1. Este arquivo (`docs/HANDOFF.md`) — estado atual
2. `docs/ROADMAP.md` — o que vem, capacity, gates, IDs unificados
3. `CLAUDE.md` — regras críticas operacionais 1-15

**Quando precisar entender "por quê":**
4. `docs/DECISIONS.md` — NÃO FAZEMOS, decisões arquiteturais, lições

**Quando precisar profundidade:**
5. `docs/ARCHITECTURE.md` — system design + ASCII diagrams
6. `docs/VISION.md` — long-term thesis (nox-neural-memory v14)
7. `docs/RUNBOOKS.md` — incident playbooks (10 cenários)

**Quando precisar referência histórica:**
- `plans/_archive/2026-04-25-integration-roadmap-v1.6.md` — v1.6 original
- `plans/_archive/2026-04-26-clawmem-analysis.md` — Section 9 candidates
- `handoffs/_archive/MASTER-HANDOFF-2026-04-26.md` — última sessão detalhada

**Memory auto-load:**
- `MEMORY.md` (em `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`) — 36+ feedback files

## 7. Comandos úteis quick-ref

```bash
# Sanity check completo
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .'

# Improvements audit (13/13 baseline)
ssh root@100.87.8.44 '/root/bin/improvements check'

# Schema invariants
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'

# Tests (rodar individualmente, race condition em --test dir)
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/retention.test.js dist/__tests__/op-audit-e2e.test.js 2>&1 | tail -5'

# OpenClaw release watcher state
ssh root@100.87.8.44 'cat /root/.openclaw/upgrade-watcher/state.json'

# Latest checkpoint
ssh root@100.87.8.44 'ckpt list | head -3'

# Logs gateway
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "10 min ago" --no-pager | tail -30'

# CLI nox-mem (lembrar source env primeiro)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem --help'

# Salience activation gate (G01 04-30)
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/activate-salience.sh check'

# Section_boost analysis (G02 05-01)
ssh root@100.87.8.44 'bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7'
```

## 8. Convenções obrigatórias (lembrete rápido)

Ver `CLAUDE.md` para detalhes completos das 15 regras. Top 5:

1. **Secrets só via env** (`${VAR_NAME}` em configs, gitleaks pre-commit)
2. **Antes de CLI nox-mem em SSH/cron:** `set -a; source /root/.openclaw/.env; set +a`
3. **Validar features com DB state, não só logs** (`/api/health` JOIN é a fonte)
4. **Modelo Gemini default = `gemini-2.5-flash-lite`** (flash full estoura quota)
5. **Anthropic via Max OAuth = zero-cost** — provider `anthropic` (auth-profile `anthropic-max`) usa subprocess CLI; `chattr +i` em `.credentials.json`; NO `CLAUDE_CODE_OAUTH_TOKEN` em env. Provider `claude-cli/*` foi removido em v.26.

**PT-BR:** "você" não "tu". Registro Brasil/Hotmart.

---

**Próxima atualização deste arquivo:** quando estado mudar (gates passarem, sprint completar, incident).
