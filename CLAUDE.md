# memoria-nox — Projeto de Memória Inteligente para OpenClaw

## O que é este repo
Documentação, specs, plans e paper técnico do sistema **nox-mem** (deployado na VPS) e do produto comercial **NOX-Supermem** (em desenvolvimento no repo `nox-supermem`).

## Onde fica cada coisa

**Canônicos (ler nessa ordem pra retomar):**

| Conteúdo | Arquivo |
|---|---|
| Estado vivo + próxima ação | **`docs/HANDOFF.md`** ← começar aqui |
| Roadmap (o que vem, capacity, gates) | **`docs/ROADMAP.md`** ← single source of truth |
| Decisões + NÃO FAZEMOS + razões | **`docs/DECISIONS.md`** |
| Regras críticas operacionais 1-15 | **este arquivo** |
| Visão estratégica (longo prazo) | `docs/VISION.md` (v14) |

**Referência:**

| Conteúdo | Arquivo |
|---|---|
| Histórico de versões (v1.0 → v3.6d) | `docs/EVOLUTION.md` |
| Incident log completo | `docs/INCIDENTS.md` |
| Convenções detalhadas | `docs/CONVENTIONS.md` |
| Specs técnicos | `specs/*.md` |
| Audits de infra | `audits/*.md` |
| Paper técnico | `paper/paper-tecnico-nox-mem.md` / `.docx` |

**Histórico arquivado (referência só, não operacional):**

| Conteúdo | Arquivo |
|---|---|
| Plans antigos (25 arquivos, v1.5/v1.6/ClawMem/sessões) | `plans/_archive/` |
| Handoffs antigos (9 arquivos MASTER-HANDOFF-<date>) | `handoffs/_archive/` |

## Infraestrutura (estado atual — v3.7, Abr 22)

- **VPS:** `ssh root@100.87.8.44` (Tailscale) ou `187.77.234.79` (público); Hostinger KVM 4
- **Path:** `/root/.openclaw/workspace/tools/nox-mem/`
- **Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings (3072d), inotifywait, systemd
- **OpenClaw:** v2026.4.29 (binário; requer Node.js 22.12+; **monkey-patched** em `dist/restart-stale-pids-DNoLLjzi.js` (impl) pra Issue #62028 — desde v.27 bundle ships 2 arquivos: `BxD39Nsb.js` (re-export wrapper, 2 linhas) + `DNoLLjzi.js` (impl, 510 linhas). Patch via `grep -l` filtra impl file (não confiar em `ls | head -1` que pega wrapper alfabeticamente). Patch idempotente em `/root/reapply-monkey-patch.sh`. Histórico: v.24 quebrado, v.25 wizard, v.26 marathon, v.27/v.29 multi-file restart-stale-pids.)
- **Node.js:** v22.22.2 com wrapper `--no-warnings` em `/usr/bin/node`
- **Claude Code CLI:** v2.1.88 em `/usr/bin/claude` — **backend primário dos agents via OAuth Max** (zero cobrança de API). Em v.29+ schema: provider canônico é `anthropic/*` via `https://api.anthropic.com` (NÃO RelayPlane). Token Max em `ANTHROPIC_MAX_API_KEY` no `.env` (sk-ant-oat01-…) + credenciais em `~/.claude/.credentials.json` (chattr +i). Subprocess CLI roda em background como child do gateway.
- **RelayPlane:** v1.8.37 **INATIVO + DISABLED** (parado 2026-04-30 — confirmado redundante com anthropic provider direto). NÃO REATIVAR — não tem uso operacional. Mantido instalado só como referência histórica.

### Serviços ativos (3 + tailscale)
- `openclaw-gateway` :18789 WS → claude CLI subprocess (Max OAuth) → `https://api.anthropic.com` (zero cobrança)
- `nox-mem-api` :18802 HTTP (porta via `NOX_API_PORT` no .env)
- `nox-mem-watcher` (inotifywait, debounce 15s) — **único**, watcher legado disabled
- `tailscaled` 100.87.8.44

### Inativos (mas instalados)
- `relayplane-proxy` :4100 — DESATIVADO + DISABLED 2026-04-30. Não reativar.

### Schema (V7)
- `chunks` + `chunks_fts` (FTS5) — **7.3k+ chunks** ativos (pós-IM + Fase 2 Graphify 2026-04-23: 147 docs + 9 repos com código via graphify + 2 entities piloto)
- `vec_chunks` + `vec_chunk_map` (sqlite-vec, 3072d) — ~100% coverage (9538/9541 2026-04-24)
- `kg_entities` (~402) + `kg_relations` (~544) — Gemini 2.5 Flash extraction (processando incrementalmente via nightly)
- **Schema v10** (2026-04-23): `retention_days` v8 + `pain` v9 + `section` v10
  - `retention_days` — typed retention (feedback/person=NULL never-decay, lesson 180d, decision/project 365d, team 120d, daily 90d, pending 30d, graph_node 60d, default 90d). Distribuição: 92 never-decay, 9 em 30d, 1954 em 90d, 5312 em 365d. `<!-- retention: X -->` override via frontmatter em linha isolada.
  - `pain` REAL DEFAULT 0.2 — severity 0.1 trivial → 1.0 prod-outage. Backfill heurístico: 256 chunks pain=1.0 (crash/outage/rollback), 43 pain=0.8 (lesson), 469 pain=0.5 (bug/error), 105 pain=0.3 (warn/deprec), 6474 pain=0.2 default.
  - `section` TEXT + `section_boost` REAL — entity file format (compiled/frontmatter/timeline/NULL). SECTION_BOOST={compiled:2.0, frontmatter:1.5, timeline:0.8, legacy:1.0}. 2 entities piloto ingestadas: `memory/entities/agents/nox.md` + `memory/entities/systems/nox-mem.md`.
- **Salience formula (Fase 1.7b-b, shadow-mode)**: `salience = recency × pain × importance` exposta em /api/health.salience. NOX_SALIENCE_MODE=shadow default (não aplica no ranking). Baseline 2026-04-23: 207 promote_candidates, 1886 archive_candidates, median=0.16. Ativação após ≥7d observação.
- **Trigger `trg_chunks_delete_cascade`** — DELETE em chunks limpa vetores (não remover)

### Hybrid Search (3 camadas)
FTS5 BM25 → Gemini semantic (gemini-embedding-001) → RRF fusion (k=60)

### Interfaces
- **CLI (26+ cmds):** search/ingest/**ingest-entity**/reindex/vectorize/kg-*/cross-*/reflect/crystallize... (`nox-mem --help`). **Entry point é `dist/index.js`** (package.json.bin), não cli.js — confusão comum. `ingest-entity <file>` adicionado 2026-04-24 pra ingestar memory/entities/<type>/<slug>.md (3-section format).
- **MCP Server (16 tools):** `nox_mem_search`, `stats`, `kg_build`, `cross_search`, `reflect`, etc.
- **HTTP API (porta 18802):** `/api/{health,search,kg,kg/path,agents,cross-kg,reflect,procedures}` + `POST /api/crystallize{,/validate}`
- **Dashboard:** github.com/totobusnello/agent-hub-dashboard (4 páginas nox-mem)

### Cron (inventário 2026-04-29)

**Diários:**
- `02:00` backup-all.sh (7d retention)
- `02:01` workspace auto-commit + push (gera commits `backup: auto-commit YYYY-MM-DD`)
- `02:30` export-obsidian-vault.py
- `03:30` prune-pre-op-snapshots.sh (ops_audit retention 7d)
- `05:00` ckpt save daily-passive
- `05:30` cross-agent-sync.sh (heartbeat sempre, mesmo TOTAL=0 — ver `reference_sync_verify_activity_log.md`)
- `06:00` sync-verify.sh (alerta Discord se diverg)
- `12:00` upgrade-watcher/check.sh (release-watcher passive)
- `22:00` end-of-day OpenClaw cron (consolidate, NÃO reindex desde patch 2026-04-25)
- `23:00` nightly-maintenance.sh (serializa reindex → consolidate → vectorize → kg-build → kg-prune → session-distill)

**Periódicos:**
- `*/5min` health-probe.sh
- `*/15min` canary-bundle-15min.sh + bvv-extract.py + check-gm-messages.sh + check-schema-invariants.sh + check-discord-heartbeat-validation.sh + heartbeat-sync.sh
- `*/30min` canary semantic + check-discord-heartbeat-validation

**Semanais:**
- `Dom 04:00` weekly vectorize
- `Dom 05:00` session-distill
- `Seg 03:00` tiers evaluate
- `Seg 09:00` forge-cc-token-check

Logrotate em `/etc/logrotate.d/nox`. Crontab rebuilder: `/root/.openclaw/scripts/crontab-rebuild.sh` (idempotente).

### Multi-agent (6 agentes, DBs isolados)
main + nox/atlas/boris/cipher/forge/lex. Cross-agent search/stats/KG disponível via `nox-mem cross-*`.

## Regras críticas (violação = produção quebra)

> As 10 mais sensíveis ficam aqui. Regras completas em `docs/CONVENTIONS.md`.

1. **Secrets só via env.** Todo `apiKey` em `openclaw.json` / `agents/*/agent/models.json` usa `${VAR_NAME}`. Valores literais estão bloqueados globalmente por gitleaks pre-commit hook. Rotação = `.env` + `systemctl restart openclaw-gateway nox-mem-api nox-mem-watcher`.

2. **Antes de rodar `nox-mem` CLI em SSH/cron/script:** `set -a; source /root/.openclaw/.env; set +a`. Sem isso, vectorize/kg-extract falham silenciosamente ("Done: 0 embedded, N errors" na última linha).

3. **Verificar estado real pós-operação de memória:** `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — confirmar `embedded == total`. Nunca confiar na última linha do CLI.

4. **Modelo Gemini padrão: `gemini/gemini-2.5-flash-lite`.** NUNCA voltar pra `gemini-2.5-flash` (quota 3M/d estoura) nem `gemini-2.0-flash` (deprecated, shutdown 2026-06-01). KG extraction pode usar `gemini-2.5-flash` full enquanto volume baixo.

5. **Modelos via Max OAuth (zero billing) — schema canônico v.29 pós-2026-05-01.** `agents.defaults.model.primary = "anthropic/claude-sonnet-4-6"` aponta pro provider `anthropic` em `models.providers.anthropic` (`baseUrl: "https://api.anthropic.com"`, `api: "anthropic-messages"`). Auth via `auth-profiles.json` profile `anthropic-max` (apiKey = token Max OAuth `sk-ant-oat01-…`). Subprocess CLI Claude roda como child do gateway, billing = $0. **Provider `claude-cli/*` foi REMOVIDO em v.26** — não existe no schema atual; usar `anthropic/<model>` (mesmo path funcional, nomenclatura nova). Per-agent override fica em `agents.list[].model` (array), não `agents.<id>.model` (object não existe).

   **Fallback chain canônica (validada 2026-05-01):**
   ```yaml
   primary: anthropic/claude-sonnet-4-6      # Max OAuth, $0
   fallbacks:
     - openai-codex/gpt-5.5                  # paid, runtime catalog (não em config registry)
     - gemini/gemini-2.5-pro                 # paid, último recurso
   ```
   **Forge override:** `agents.list[forge].model.primary = anthropic/claude-opus-4-7` (o único agent que precisa raciocínio profundo).

   **Pré-requisitos críticos pra Max OAuth funcionar — ordem importa:**
   - `/root/.claude/.credentials.json` populado pelo `claude setup-token` (token Max válido, expira anualmente — atual válido até 2027-04-21)
   - Só DEPOIS `chattr +i ~/.claude/.credentials.json` (ordem importa — antes, setup-token não consegue gravar)
   - `CLAUDE_CODE_OAUTH_TOKEN` **NÃO pode** estar no `.env` (comentar `#DISABLED_...`). Subprocess Claude DEVE ler só do credentials.json; env var conflita e gera 401.
   - `models.providers.anthropic.baseUrl == https://api.anthropic.com` (NÃO `:4100`). `npm install -g openclaw@<version>` pode reescrever pra `http://127.0.0.1:4100` ativando RelayPlane redundante. Validar pós-upgrade: `openclaw config get models.providers.anthropic.baseUrl`.
   - **RelayPlane (`relayplane-proxy` :4100) DESATIVADO + DISABLED desde 2026-04-30.** Não reativar. Se aparecer `active`, `systemctl stop relayplane-proxy && systemctl disable relayplane-proxy`.
   - Systemd drop-in `/etc/systemd/system/openclaw-gateway.service.d/override.conf` com `Environment=IS_SANDBOX=1` (gateway roda como root; sem essa var o CLI bloqueia `bypassPermissions`)
   - **NUNCA** incluir `anthropic/*` na fallback chain DUPLICANDO o primary (mascara falha real). Tudo bem ter `anthropic/*` como primary; só não duplicar em fallbacks[0].

   **`gpt-5.5` está no runtime catalog mas NÃO em `models.providers.openai-codex.models` (config registry estático).** O gateway expõe gpt-5.5 dinamicamente via Max OAuth Codex catalog. Validar com `openclaw models list | grep gpt-5.5` (deve mostrar `configured`), não com `openclaw config get models.providers.openai-codex.models` (só mostra gpt-5.4).

   **Sessions stickiness:** se um agente cair em fallback (gemini/codex), `sessions.json` gruda nesse model. Reset: `jq 'with_entries(select(.value.model | test("^claude-")))' agents/<id>/sessions/sessions.json`. Crons em haiku-4-5 são DESIGN (heartbeat barato), não tocar.

   **Editar config via CLI oficial, NÃO `jq` + `mv`:** o gateway tem in-memory canonical state que sobrescreve `openclaw.json` no startup. Usar `openclaw config set <path> <val>` + `openclaw config validate` antes de restart.

   **Pós upgrade (Phase 6 mandatório):** validar 5 invariants — `(a)` `model.primary` = `anthropic/<model>`, `(b)` `models.providers.anthropic.baseUrl == https://api.anthropic.com`, `(c)` `relayplane-proxy` inactive+disabled, `(d)` fallback chain = `[openai-codex/gpt-5.5, gemini/gemini-2.5-pro]` (sem duplicar primary), `(e)` sessions sem fallback grudado. Se qualquer uma drift: corrigir + restart gateway uma vez.

6. **Gateway fratricide (Issue #62028, v2026.4.14+):** monkey-patch em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]`. **O hash do nome do arquivo muda a cada versão** (ex: v4.22=`BUk5aJLm`, v4.23=`CegQx-K9`, v4.26=`BQxFGeFd`) — usar glob `restart-stale-pids-*.js` e nunca confiar no hash hardcoded. Wrapper em `/usr/local/bin/openclaw-gateway-wrapper` (imutável com `chattr +i`) unset `OPENCLAW_SERVICE_MARKER/KIND`. Config `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off`. **Comandos que invalidam o patch** (precisam checar + reaplicar ANTES do próximo restart): `npm install/update -g openclaw`, `openclaw models auth {add,login,paste-token,setup-token}` (confirmado 2026-04-23 — reinstala node_modules/dist/). **Reapplicação automática:** `bash /root/reapply-monkey-patch.sh` (idempotente, Python regex). Upgrade completo: `bash /root/upgrade-<VERSION>.sh` + rollback: `bash /root/rollback-<VERSION>.sh`. Sintoma de patch perdido: 15+ restarts/5min, SIGTERM loop, "Gateway already running locally" nos logs. Fix emergencial em memory `feedback_models_auth_login_reinstalls_node_modules.md`.

7. **`nox-mem-api` escuta em :18802** (não 18800 — Chrome squata). Nunca hardcode; ler `NOX_API_PORT` do .env.

8. **Nunca introduzir ranking/scoring change em commit de "fix".** Scoring é feature work (prefix `tune(search):` ou `feat(search):`). Boost multiplicativo empilhável é veneno — usar aditivo. Violação causou incident v3.4.

9. **Nunca editar `openclaw.json` removendo `agents.defaults`** (fallback chain, heartbeat, compaction). Nunca adicionar chaves root novas sem verificar versão do binário na VPS.

10. **Node.js wrapper obrigatório:** `/usr/bin/node` é wrapper bash → `/usr/bin/node.bin --no-warnings`. Sem isso, DEP0040 (punycode) causa crash loop. Se `apt upgrade nodejs` rodar, recriar wrapper (renomear binary para `node.bin`).

11. **Sessions.json pode grudar em fallback model.** O gateway persiste em `agents/main/sessions/sessions.json` o model do último turn bem-sucedido por canal/session. Se o CLI falha uma vez e cai em gemini/gpt, o canal fica grudado. Fix: `jq 'with_entries(select(.value.model | startswith("claude-")))'` filtra só as sessions válidas; ou `echo '{}' > sessions.json` pra resetar tudo. Sempre que mudar `model.primary`, considerar reset.

12. **`.credentials.json` do Claude CLI trunca ciclicamente (~8h).** O CLI, quando spawned como subprocess sem TTY em condições de erro, faz "self-fix" zerando `~/.claude/.credentials.json`. Consequência: próximo turn falha "Not logged in". Mitigação obrigatória: `chattr +i ~/.claude/.credentials.json` após popular do `.credentials.json.bak`. Pra atualizar legitimamente no futuro: `chattr -i` → edit → `chattr +i`.

13. **Dois tokens distintos no fluxo do Claude CLI.** `setup-token` imprime na tela um **long-lived OAuth token** (pra uso em env vars/API externa). Ao mesmo tempo ele persiste um **session credential** em `.credentials.json` pro uso local do subprocess. **DEVEM ser o mesmo valor.** Se divergirem (por restore do .bak antigo, edit manual inconsistente, etc), `claude auth status` retorna `loggedIn:true` (usando env var) mas chamadas reais falham HTTP 401 "Invalid authentication credentials" (porque subprocess usa credentials.json). Validação: `jq -r '.claudeAiOauth.accessToken[0:15]' ~/.claude/.credentials.json` deve bater com os primeiros 15 chars do token que setup-token imprimiu. Token tem validade de 1 ano — adicionar reminder no calendário pra renovação anual.

14. **Delivery-queue órfã pode gerar 15+ "Unknown Channel" por restart.** Canais Discord/Telegram removidos do teu servidor deixam mensagens travadas em `/root/.openclaw/delivery-queue/*.json` que o `[delivery-recovery]` re-tenta a cada restart do gateway. Script `/root/.openclaw/workspace/tools/delivery-queue-cleanup.sh` limpa automaticamente (detecta "Unknown Channel" + "recovery time budget exceeded" + >7 dias). Rodar após qualquer série de restarts anômalos ou mudança de canais Discord. Main agent **não deve ter heartbeat configurado** (target=discord sem `to` gera "Unknown Channel" persistente) — só as 6 personas (nox/atlas/boris/cipher/forge/lex) têm heartbeat válido.

15. **Operações destrutivas em chunks só com `--dry-run` ou snapshot atômico.** Lição do incident 2026-04-25 (reindex.ts wipou section/retention de 183 entities; root cause = end-of-day cron diário rodava `nox-mem reindex` sem rede de proteção). Antes de `reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune` em prod: ou rodar com `--dry-run` (preview JSON, não muta) OU usar `withOpAudit()` wrapper que cria snapshot atômico em `/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db` (retention 7d, ACL 0600, dir 0700, snapshot path validation symlink-aware via realpathSync). Backup-all.sh 02:00 NÃO conta — é diário, não pré-op. Ingest-router unified (Fase A2 v1.6) rota entity files via `ingestEntityFile()` automaticamente; sem ele, `ingestFile()` genérico zera section/retention. Validar pós-op com `/api/health.sectionDistribution.compiled == 183`. **Recovery via `safeRestore()`** em `src/lib/op-audit.ts` — valida `user_version` match + restaura main DB primeiro + remove WAL/SHM órfãos depois (W2-4 fix 04-26: ordem importa). NÃO fazer `cp snapshot.db nox-mem.db` direto (corrompe se WAL stale). **Override emergencial:** `NOX_ALLOW_NO_SNAPSHOT=1` no env permite rodar op destrutiva mesmo se snapshot falhar (ex: disk full + emergency reindex) — usar SÓ se snapshot falhou por motivo legítimo conhecido, nunca como atalho. Audit log `ops_audit` é **append-only** (W2-1 trigger CWE-693): DELETE bloqueado, UPDATE bloqueado em rows com status terminal. **Status enum válido (validado via DB triggers 2026-04-29):** `'started'` (inicial), `'success'` (terminal OK), `'failed'` (terminal erro app), `'crashed'` (terminal erro sistema). `'completed'` e `'rolled_back'` NÃO são status válidos apesar de docs antigas mencionarem. Detalhes incident: `docs/INCIDENTS.md#2026-04-25`. Audits pós-fix: `audits/2026-04-25-A1-A2-review.md` + `audits/2026-04-26-{A1v2-A3-A4-A5-review,7highs-followup-fix,W2-cleanup}.md`.

## Roadmap canônico

**Single source of truth:** `docs/ROADMAP.md` (canônico desde 2026-04-27 — substitui v1.6 + ClawMem analysis como referência operacional).
- "O que vem, ordem cronológica, capacity, gates" → `docs/ROADMAP.md`
- "Por quê / NÃO FAZEMOS / decisões arquiteturais" → `docs/DECISIONS.md`
- "Estado vivo + próxima ação" → `docs/HANDOFF.md`
- "Visão estratégica longo prazo" → `docs/VISION.md` (v14)

Histórico de pensamento (não operacional) em `plans/_archive/`: v1.6, v1.5, ClawMem analysis, session handoffs antigos.

## Produto NOX-Supermem

Repo `github.com/totobusnello/nox-supermem` (private), local `~/Claude/Projetos/nox-supermem/`. Mercado Brasil (PT-BR, Hotmart). Tiers A/B/C R$147/197/227 + R$30/sem suporte. Plan de 24 tasks em 4 chunks.

## Convenções de workflow

- Specs e plans usam formato **Superpowers** (checkbox tasks, chunk boundaries)
- Todos os módulos respeitam `OPENCLAW_WORKSPACE` env var
- Hybrid search é o padrão (`--no-hybrid` para desabilitar)
- Forge faz code review via PRs no GitHub
- **Fontes de verdade da memória dos agentes (validado 2026-05-01):**
  - `agents/<id>/memory/active-tasks.md` — pendências Toto + crons + bloqueios + concluídos. Atualizado quase diário pelo agente. **É a lista que o daily-briefing deve ler** (regra anterior "deprecated" estava errada — esse arquivo está vivo).
  - `agents/<id>/memory/session-context.json` — state operacional: `currentFocus`, `carryOver[]`, `nextActions[]`, `openIssues[]`, `systemState`. Atualizado pelo cron 05:00 BRT diário. **NÃO é deprecated**.
  - `agents/<id>/memory/core-memory.json` — config estável (perfil Toto, integrações Notion/Slack, IDs). Update raro.
  - `agents/<id>/memory/pending.md` — lista informal de pendências mistas (ele + Toto + Forge etc). Pode divergir de active-tasks.md; consolidar via cron quando estável.
  - `workspace/memory/SESSION-STATE.md` — **fonte VIVA** (auto-update via `nox-mem update-session` no end-of-day/consolidate). Tem `Tarefa Ativa`, `Decisões Recentes`, `Pendências` (mirrored). Compartilhado entre agents.
  - `agents/<id>/memory/SESSION-STATE.md` — **VESTIGIAL** (versão privada por agente que ficava stale; archived 2026-05-01 em `_archive/legacy-state-files/`). Usar `workspace/memory/SESSION-STATE.md` em vez.
  - `agents/<id>/memory/2026-MM-DD.md` — daily notes. Retention sugerida: archive >30d em `_archive/daily/`.
- Scripts permanentes em `/root/.openclaw/scripts/` (nunca /tmp/)
