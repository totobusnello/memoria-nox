# Architect drift audit — 2026-04-29

> Pós-optimization-marathon (corpus tripled, OpenClaw v.25→v.26, latency 39.8s→10.4s, .git 11GB→134MB).
> Auditor: architect-reviewer. Method: docs vs VPS reality (`ssh root@100.87.8.44`).

---

## Findings (severity-rated)

### CRITICAL (bloqueia G01 04-30)

**Nenhum.** Sistema está READY para G01 amanhã. Todos os pré-requisitos operacionais (gateway active, monkey-patch aplicado, schema invariants honrados, vector coverage 100%, salience shadow rodando há ≥5 dias) estão presentes.

### HIGH (corrigir antes Wave 1 Maio)

1. **F09 contradição direta entre ROADMAP e DECISIONS** (já flag do user)
   - `ROADMAP.md:76` diz `F09 📋 QUEUED P0 — antes G01 04-30`
   - `ROADMAP.md:169,215,240,297,380,416` reforçam F09 como P0 (7 mentions ativas)
   - `DECISIONS.md:246` diz `F09 off-site backup REJEITADO permanentemente — VPS Hostinger nativo basta. User declarou 2x. Não sugerir mais como next action mesmo quando DB cresce.`
   - Memory entry `feedback_no_f09_offsite_backup.md` confirma rejeição
   - `HANDOFF.md:103` ainda lista F09 como P0 hoje
   - **Fix:** sed-replace F09 status `📋 QUEUED P0 → ❌ CUT` em `ROADMAP.md`, mover de §4 Foundation pra §6 Deferred/Cut com nota link pra `DECISIONS.md:246`. Remover F09 do "Próxima ação concreta" §4 do `HANDOFF.md`. Remover de §"Combo recomendado pré-G01".

2. **CLAUDE.md regra 6 cita hashes monkey-patch desatualizados**
   - Linha 104 diz `v4.22=BUk5aJLm, v4.23=CegQx-K9`
   - Realidade: `ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` → `BQxFGeFd` (v.26)
   - Patch confirmado idempotente (`grep MONKEY-PATCH` retorna marker; `return []` antes de `const port`)
   - **Fix:** adicionar `v4.26=BQxFGeFd` na regra 6 ou remover hashes específicos (princípio: glob é a fonte, não hash)

3. **CLAUDE.md header diz OpenClaw v2026.4.23, realidade é v2026.4.26**
   - `CLAUDE.md:41` diz `OpenClaw: v2026.4.23 (binário; requer Node.js 22.12+...)`
   - `openclaw --version` → `OpenClaw 2026.4.26 (be8c246)`
   - Mismatch de 3 versões (v.24 broken, v.25 wizard, v.26 atual)
   - `ROADMAP.md:18` também diz `OpenClaw: v2026.4.23 (.24 quebrado, .25-stable aguardada)` — desatualizado
   - **Fix:** bump pra `v2026.4.26` em CLAUDE.md:41 + ROADMAP.md:18; mencionar `.24 quebrado` e `.25 wizard adoption` como histórico em DECISIONS.md

### MEDIUM (next sprint)

4. **HANDOFF.md datado 2026-04-27 mas hoje é 2026-04-29**
   - `HANDOFF.md:3` diz "Atualizado: 2026-04-28 12:20 BRT"
   - `HANDOFF.md:97` diz "Hoje é 2026-04-27 (segunda). 3 dias até G01"
   - Realidade: hoje é 2026-04-29 (quarta). 1 dia até G01.
   - Numbers em §1 Sanity check ainda citam baseline 04-27 (62.836 chunks); realidade 04-29: **62.844 chunks** (+8 do dia, normal nightly)
   - **Fix:** bump header data, atualizar §1 com leitura atual (62.844, db ainda ~1.014GB, salience shadow 191/62/16607/45739 com mean=0.1119/median=0.0787)

5. **HANDOFF cita "13/13 OK" mas realidade tem 1 warn-only**
   - `HANDOFF.md:55` diz `13/13 OK (7 critical + 6 warn-only, todos pass)`
   - `improvements check` na VPS retorna `1 warn-only violation(s) — informational, not blocking`
   - Não bloqueia G01, mas fade da accuracy (provavelmente um dos 6 warn já era esse)
   - **Fix:** atualizar pra "12 OK + 1 warn-only informacional" ou rodar `improvements check` agora e reflair

6. **Cron tem 8 entradas novas pós-04-27 não documentadas em RUNBOOKS/CLAUDE.md regra 22**
   - Adicionados desde HANDOFF 04-27: `5 2 * * * ckpt save daily-passive`, `0 12 * * * upgrade-watcher/check.sh`, `*/15 canary-bundle-15min.sh`, `30 2 export-obsidian-vault.py`, `*/15 bvv-extract.py`, `30 3 prune-pre-op-snapshots.sh`, `15 * check-gm-messages.sh`
   - `CLAUDE.md` §Cron parágrafo só menciona "Runner único 23:00 + canary 30min + health 5min + backup 02:00"
   - **Fix:** atualizar §Cron de CLAUDE.md OU criar `docs/RUNBOOKS/cron-inventory.md` referenciado de CLAUDE.md
   - **NB:** "5:30 cross-agent-sync hoje" mencionado pelo user **NÃO existe** em `crontab -l`. Verificar se foi adicionado ao SystemD timer ou se foi cancelado.

7. **OpsAudit metrics zeradas em 24h apesar de cron destrutivo rodar**
   - `/api/health.opsAudit` → `total_24h: 0, success_24h: 0, last_op: test-bad-fn (failed) 2026-04-27 10:32:40`
   - `ops_audit` table tem 13 rows totais, último em 04-27
   - Cron 23:00 nightly-maintenance.sh roda `consolidate` (não `reindex`, conforme patch 04-25) — **deveria** wrappar com withOpAudit
   - Possíveis causas: (a) consolidate não está dentro de withOpAudit; (b) op_audit não está sendo persistido; (c) no-op (nada pra consolidar 2 dias seguidos)
   - **Fix:** verificar `nightly-maintenance.sh` chama `nox-mem consolidate` com wrapper; rodar smoke `consolidate --dry-run` e validar telemetria

### LOW (polish)

8. **Workspace `.git` 9.3GB pós-shrink prometido 134MB**
   - HANDOFF tabela diz `.git workspace: 11GB → 134MB (-99%)`
   - Realidade: `du -sh /root/.openclaw/workspace/.git` → **9.3G**
   - Possíveis causas: backup-all.sh diário re-empurrou objects; pack rebuild revertido; commit `0227816e backup: auto-commit 2026-04-29 02:01` rolou pesado
   - Não-bloqueante mas drift de fato substantivo
   - **Fix:** rodar `git gc --aggressive` no workspace + investigar se backup auto-commit está duplicando blobs grandes; documentar que shrink é one-shot, não persistent

9. **HEARTBEAT 04-29 confirmado** — `agent-activity.log` mostra `2026-04-29T10:20:03Z [SYSTEM] HEARTBEAT: cross-agent memory sync` + boris matinal 11:17. OK.

10. **section_boost distribution match** — `compiled=183, frontmatter=183, timeline=366, legacy=62112` ≈ HANDOFF claim (183/183/366/62104). Delta legacy +8 explicado pelo +8 chunks normal.

11. **Agent routing OK** — config tem nox+forge=opus, atlas+boris+cipher+lex=sonnet (regra 5 honrada). Nenhuma regressão pós upgrade v.26.

---

## Resumo executivo

- **Total findings:** 11 (0 CRITICAL, 3 HIGH, 4 MEDIUM, 4 LOW)
- **Bloqueia G01?** **NÃO.** Sistema operacional saudável: gateway active, vectorCoverage 100%, salience shadow desde ≥04-23 (>5 dias baseline cumprido), monkey-patch aplicado, schema v10 íntegro, agent routing correto.
- **Recomendação G01 04-30:** **GO.** Rodar `activate-salience.sh check` na manhã de amanhã; se output `READY`, executar `--apply`. Salience shadow tem mean=0.1119/median=0.0787 com 191 promote_candidates e 45739 archive_candidates — distribuição saudável pra ativação.
- **Antes de G01:** corrigir HIGH #1 (F09 contradição) — não bloqueante operacional, mas docs canônicos contraditórios geram retrabalho mental e risco de re-suggestão. 5 minutos de sed.
- **Pós-G01 (Wave 1 Maio):** corrigir HIGH #2 e #3 (versions/hashes) + MEDIUM #4 e #6 (HANDOFF date drift + cron inventory) na primeira sessão Maio.

**Outstanding question pro user:** entry de "5:30 cross-agent-sync adicionada hoje" não está em `crontab -l` — está em outro mecanismo (systemd timer, agent-orchestrator scheduler) ou foi rolled back?

---

**File saved:** `/Users/lab/Claude/Projetos/memoria-nox/audits/2026-04-29-architect-drift.md`
