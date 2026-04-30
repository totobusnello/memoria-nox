# RB-12: OpenClaw v2026.4.29 Upgrade Runbook

> **Versão:** 1.0 — 2026-04-30
> **Salto:** `2026.4.26` → `2026.4.29` (.27 release intermediária + .28 yanked)
> **Tempo total:** ~1h (Phase 0 pode rodar dias antes; janela real ~30min)
> **Severity:** P1 — gateway offline ~30s durante atomic swap, 5min watch loop
> **Companion script:** `scripts/upgrade-v29-deltas.sh` (deltas .29-específicos)
> **Generic runbook:** `docs/RUNBOOKS/openclaw-upgrade-runbook.md` (RB-11)

---

## 0. TL;DR

```bash
ssh root@100.87.8.44

# Phase 0: dry-run pre-flight (zero risco — pode rodar agora)
bash /root/upgrade-v29-deltas.sh --pre

# Phase 1-4: atomic swap com auto-rollback (janela ~30min)
DRY_RUN=1 bash /root/upgrade-zero-downtime.sh 2026.4.29   # staging only, no swap
bash /root/upgrade-zero-downtime.sh 2026.4.29              # real swap

# Phase 5: post-swap delta validation
bash /root/upgrade-v29-deltas.sh --post

# Phase 6: rollback (se algo der errado)
bash /root/rollback-zero-downtime.sh 2026.4.29 \
  /usr/lib/node_modules/openclaw.bak-pre-2026.4.29 \
  /root/backups/openclaw-pre-2026.4.29
```

---

## 1. Por que upgradar

**Win direto pra gente (vale o risco):**

| # | Issue | Impacto |
|---|---|---|
| 🟢 | `#74864` orphan recovery bounded | Acaba com `sessions.json` surgery manual (regra 11 do `CLAUDE.md`) |
| 🟢 | `#75115` EADDRINUSE → exit 78 | Para restart loop quando :18802 zumbi |
| 🟢 | `#74137` skip blank user prompts | Telegram/group sessions param de vazar erro |
| 🟢 | `#74868` auto-reply group fallback | Discord group turns não silenciam mais sem reply |
| 🟢 | `#75087` browser shared runtime | CLI honra `browser.executablePath`/`headless` |

**Não-fix conhecidos (continuam manuais):**
- ❌ Fratricide `#62028` — monkey-patch ainda mandatório
- ❌ `models auth login` ainda reinstala `node_modules` (regra do MEMORY)
- ❌ `.credentials.json` ainda trunca em ~8h sem `chattr +i`

**Skip (não usamos):** DeepInfra/NVIDIA/Tencent providers, Codex Computer Use, people-aware memory wiki.

---

## 2. Mudanças de comportamento — atenção

| Delta | Default novo | Mitigação |
|---|---|---|
| **D1** restart-stale-pids pode vir em 2 arquivos | impl + wrapper | Script `--pre` valida qual contém função real |
| **D2** `messages.visibleReplies` global | falsy esperado | Validar via `--pre` (se true, força replies via `message` tool) |
| **D3** `agents.defaults.queueing.mode` = `steer` | era 1-at-a-time | Concurrent inputs agora drenam todos no boundary; `queue` se incompatível |
| **D4** `commitments.enabled` | opt-in (off) | Confirmar default; ativar manualmente se quiser heartbeat reminders |
| **D5** subagent orphan recovery bounded | NEW | Telemetria pós-swap: sem restart loop |
| **D6** `RestartPreventExitStatus=78` | recomendado | Add no systemd drop-in se EADDRINUSE aparecer |
| **D7** restrictive profiles (`messaging`/`minimal`) | sem auto-include | Não usamos profiles restritivos, sem impacto |

---

## 3. Pré-requisitos

- [ ] VPS rodando v2026.4.26 confirmado: `openclaw --version`
- [ ] 3 services `active`: `systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher`
- [ ] Disco livre ≥2GB em `/root` e `/var`: `df -h /root /var`
- [ ] Backup-all 02:00 rodou nas últimas 24h: `ls -la /var/backups/nox-mem/ | head`
- [ ] Sem heartbeats stuck nem fratricide nas últimas 6h: `journalctl -u openclaw-gateway --since "6h ago" | grep -cE "Gateway already|fratricide" — deve ser 0`
- [ ] `.credentials.json` íntegro e immutable: `lsattr ~/.claude/.credentials.json | grep -- '----i'`
- [ ] Toto disponível pra supervisionar (smoke tests via Discord)
- [ ] Janela ≥45min sem competing crons (evitar 22:00 BRT end-of-day, 23:00 nightly-maintenance, 02:00 backup)

---

## 4. Phase 0 — Pre-flight (zero risco)

Roda sem janela. Pode ser feita agora.

```bash
ssh root@100.87.8.44

# Snapshot estado atual
curl -s http://127.0.0.1:18802/api/health > /var/backups/health-pre-v29.json
md5sum /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js > /var/backups/monkey-patch-pre-v29.md5

# Pull v29 tarball + run delta checks (validação pura)
bash /root/upgrade-v29-deltas.sh --pre
```

**Saída esperada:** `━━━ PRE-SWAP DELTAS: ALL PASS ━━━`

Se D1 falhar (regex pattern não bate na .29):
1. Inspecionar `/tmp/openclaw-v29-tarball/extract/package/dist/restart-stale-pids-*.js`
2. Atualizar regex em `/root/reapply-monkey-patch.sh`
3. Rerun `--pre` até passar

Se D2 ou D4 warn (defaults não claros):
- Setar explicitamente em `openclaw.json` antes do swap:
  ```bash
  openclaw config set messages.visibleReplies false
  openclaw config set agents.defaults.commitments.enabled false
  ```

---

## 5. Phase 1-4 — Atomic swap (janela)

### 5.1 Dry-run (staging, sem swap)

```bash
DRY_RUN=1 bash /root/upgrade-zero-downtime.sh 2026.4.29
```

Isso instala em `/opt/openclaw-staging`, sobe gateway em :18790, roda smoke tests, e **para antes do swap**. Tempo: ~3-5min.

Validar saída:
- `[2a] health endpoint` PASS
- `[2c] harness registration is live` PASS
- `[2e] Monkey-patch marker confirmed` PASS
- `[2f] IS_SANDBOX env reaches staging` PASS
- `[2g] staging did NOT kill production gateway` PASS

### 5.2 Real swap

```bash
bash /root/upgrade-zero-downtime.sh 2026.4.29
```

**Fases automáticas:**
1. Snapshot prod em `/usr/lib/node_modules/openclaw.bak-pre-2026.4.29`
2. Backup config em `/root/backups/openclaw-pre-2026.4.29/`
3. Staging install + monkey-patch + smoke (mesmo do dry-run)
4. **Atomic swap:** stop gateway → `mv` node_modules → fix npm symlink → start
5. **Watch loop 5min:** monitora restart count, harness errors, fratricide events. Auto-rollback se threshold disparar.

**Tempo:** ~15-20min total. Gateway offline ~30s durante swap.

### 5.3 Se auto-rollback disparar

Script já restaura node_modules + config + sessions automaticamente. Verificar:
```bash
openclaw --version          # deve ser 2026.4.26
systemctl status openclaw-gateway
```

Investigar causa via `/var/log/openclaw-upgrade-*.log`.

---

## 6. Phase 5 — Post-swap delta validation

```bash
bash /root/upgrade-v29-deltas.sh --post
```

**Checks (D5-D7 + invariantes):**
- D5: orphan recovery telemetry — sem loop de session restarts
- D6: gateway port handling — sem EADDRINUSE descontrolado
- D7: embedded-runner — sem `MessageContentEmpty` errors
- Health: vectorCoverage 100%, salience mode preservado
- Patch: monkey-patch marker presente
- Fratricide: 0 eventos em 5min
- Auth: 0 401 Anthropic
- Channels: 0 "Unknown Channel" loops

**Saída esperada:** `━━━ POST-SWAP DELTAS: ALL PASS ━━━`

---

## 7. Phase 6 — Smoke manual (10min)

Discord → mandar 1 mensagem pra cada persona:

| Persona | Canal | Comando teste |
|---|---|---|
| nox | DM ou #nox | `oi nox, status` |
| atlas | #atlas | `atlas, ping` |
| boris | #boris | `boris, ping` |
| cipher | #cipher | `cipher, ping` |
| forge | #forge | `forge, ping` |
| lex | #lex | `lex, ping` |

Cada um deve responder em <30s usando claude-cli (ver model no log: `opus-4-6` pra nox/forge, `sonnet-4-6` pros outros).

Verificar no `/api/health`:
```bash
curl -s http://127.0.0.1:18802/api/health | jq '.salience.mode'   # active (G01)
curl -s http://127.0.0.1:18802/api/health | jq '.chunks.total'    # ~62.836+
```

Smoke search nox-mem:
```bash
nox-mem search "graphify" --limit 5
nox-mem search "monkey-patch" --limit 3
```

---

## 8. Phase 7 — Update docs + memory

### CLAUDE.md
Bump version reference + monkey-patch hash:
```bash
# Em /Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md
# Linha "**OpenClaw:** v2026.4.26" → "v2026.4.29"
# Linha hash exemplo "v.26=BQxFGeFd" → adicionar "v.29=<NOVO_HASH>"
```

### HANDOFF.md
Adicionar sessão 2026-04-30 ou 05-01 com:
- Versão antiga → nova
- Deltas comportamentais observados (queueing.mode, visibleReplies)
- Wins concretos (#74864 etc)

### Memory
```
Save observation: "OpenClaw v2026.4.29 upgrade completed"
Type: discovery / change
Facts: target version, monkey-patch hash, atomic swap duration, any deltas behavior, fratricide-free 5min
```

---

## 9. Monitoring 24-48h

Verificações recorrentes (até 48h pós-swap):

```bash
# A cada 6h
journalctl -u openclaw-gateway --since "6h ago" | grep -cE "fratricide|Unknown Channel|EADDRINUSE|401" 

# Daily
curl -s http://127.0.0.1:18802/api/health | jq '.opsAudit, .salience'

# Verificar nightly-maintenance 23:00 sem erro
tail -50 /var/log/nightly-maintenance.log
```

**Sinais de regressão:**
- Restart loop >10/h → fratricide patch perdido
- Sessions.json grudou em fallback → reset com `jq` (regra 11)
- vectorCoverage caiu — reindex ou re-vectorize manual
- ops_audit não está logando — verificar trigger `trg_ops_audit_*`

---

## 10. Quando NÃO upgradar

- Janela conflitante: 22:00-23:30 BRT (end-of-day + nightly-maintenance) ou 02:00-03:30 BRT (backup + prune)
- Canary alerts ativos nas últimas 2h
- < 2GB livre em `/var` (snapshot precisa de espaço)
- Token Anthropic perto de expirar (validade 1 ano — ver memory `feedback_token_audit_check_values_not_just_presence`)
- **Nunca** upgradar se nightly cron está rodando (concurrent reindex pode corromper schema)

---

## 11. Rollback completo

Se 24h pós-swap aparecer regressão grave:

```bash
bash /root/rollback-zero-downtime.sh 2026.4.29 \
  /usr/lib/node_modules/openclaw.bak-pre-2026.4.29 \
  /root/backups/openclaw-pre-2026.4.29
```

Restaura: `node_modules/openclaw`, `openclaw.json`, `sessions.json`. Patch automático sobrevive (estava no snapshot pré-upgrade).

Pós-rollback:
- Sessions reset preventivo: `for a in main nox atlas boris cipher forge lex; do echo '{}' > /root/.openclaw/agents/$a/sessions/sessions.json; done`
- Documentar incident em `docs/INCIDENTS.md`
- Memory observation com root cause

---

## 12. Referências

- Generic upgrade runbook: `docs/RUNBOOKS/openclaw-upgrade-runbook.md`
- v.25 paper (lições): `docs/oc-upgrade/openclaw-v25-upgrade-paper.md`
- v.25 postmortem: `docs/oc-upgrade/openclaw-v25-upgrade-postmortem.md`
- Memory observations:
  - `feedback_models_auth_login_reinstalls_node_modules.md`
  - `feedback_chattr_keep_immutable.md`
  - `feedback_subagent_findings_validate_critical.md`
  - `reference_openclaw_upgrade_scripts.md`
- CLAUDE.md regras críticas: 5, 6, 10, 11, 12, 13, 14, 15
