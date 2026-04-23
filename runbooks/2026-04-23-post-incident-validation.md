# Post-Incident Validation Runbook — 2026-04-23

Fixes: A (registry restore) / B (monkey-patch reapply) / C (graph-memory afterTurn).
Severity: **MUST** = apply today. **SHOULD** = within 7d. **NICE** = backlog.

---

## 1. Stability Monitoring (1–7d)

### MUST — daily gateway health (cron 06:00)
```bash
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "24h ago" | \
  grep -cE "Gateway already running locally|SIGTERM|restart-stale|EADDRINUSE"'
# Expected: 0. Anything >0 = investigate.
```

### MUST — monkey-patch integrity check (cron hourly)
```bash
ssh root@100.87.8.44 'grep -l "MONKEY-PATCH 2026-04-23" \
  /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js || \
  curl -X POST https://nox-alert/... -d "patch_lost"'
```

### SHOULD — SIGTERM baseline
Normal: 0–2/day (systemd stop/reload, daily backup). Problematic: >5/day OR clustered <60s apart = fratricide suspected.
```bash
journalctl -u openclaw-gateway --since "24h ago" | \
  awk '/SIGTERM/ {print $1,$2,$3}' | uniq -c
```

### MUST — graph-memory ingest canary (cron */30min)
```bash
sqlite3 /root/.openclaw/workspace/tools/graph-memory/data.db \
  "SELECT COUNT(*) FROM gm_messages WHERE created_at > strftime('%s','now','-30 minutes')"
# Expected: >0 during active hours. 0 for 2h = patch regressed.
```

---

## 2. Runbook: pós `openclaw models auth <cmd>`

1. `cp /root/.openclaw/openclaw.json{,.pre-auth-$(date +%s)}`
2. Rodar o comando.
3. `diff openclaw.json.pre-auth-* openclaw.json | grep -E "claude-cli|gemini"` — se entries sumiram, restaurar via jq.
4. `ls -la /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` — se mtime mudou, reaplicar patch.
5. `grep "MONKEY-PATCH 2026-04-23" .../restart-stale-pids-*.js` — confirmar string.
6. `systemctl status openclaw-gateway --no-pager | head -5`
7. `journalctl -u openclaw-gateway -n 20 | grep -c "Gateway already"` — deve ser 0.
8. Canary turn via curl ao gateway; confirmar resposta.

---

## 3. Crash-loop Auto-Containment

### MUST — systemd StartLimitBurst circuit breaker
```ini
# /etc/systemd/system/openclaw-gateway.service.d/circuit-breaker.conf
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5
[Service]
Restart=on-failure
RestartSec=10s
```
Após 5 restarts/5min, systemd para sozinho → alerta via `systemctl is-failed`.

---

## 4. Alerting Gaps

| Canário | Trigger | Ferramenta |
|---|---|---|
| monkey-patch-lost | MUST | grep hourly no `.js` |
| models-registry-drift | MUST | `jq '.agents.defaults.models | length < 4'` |
| gm_messages-stall | MUST | SQL query 2h sem inserts |
| claude-cli-401 | MUST | `journalctl \| grep "Invalid authentication"` |
| session-sticky-fallback | SHOULD | `jq` em sessions.json procurando model não-claude |

### Heartbeat refactor (SHOULD)
Substituir janela 24h por **edge-triggered**: alerta só quando count muda 0→N ou N→0 em 1h. Código:
```bash
current=$(grep -c "Unknown Channel" /var/log/openclaw.log | tail -1h)
prev=$(cat /var/lib/nox/hb-state)
[[ "$current" != "$prev" ]] && alert "channel drift: $prev → $current"
echo "$current" > /var/lib/nox/hb-state
```

---

## 5. Backup Additions (MUST)

Já tem. Adicionar:
- `/etc/systemd/system/openclaw-gateway.service.d/*.conf` (drop-ins)
- `/usr/local/bin/openclaw-gateway-wrapper` + atributo `chattr`
- `/root/.claude/.credentials.json` (encrypted — age/sops) — anual renewal
- `agents/main/sessions/sessions.json` (pré-reset sticky fallback)

Rollback steps por fix: arquivo + `.bak-*` → `cp` reverso → `systemctl restart <unit>` → canary.

---

## 6. Antifragile — Permanent Canaries

1. **patch-integrity** (MUST): hourly hash check de `restart-stale-pids-*.js` contra known-good SHA256.
2. **gm_messages-growth** (MUST): SLO `>0 msgs/h` durante 09h–22h.
3. **registry-completeness** (MUST): `models | length >= 4`.
4. **credentials-immutable** (SHOULD): `lsattr ~/.claude/.credentials.json | grep -q '\-\-i\-'`.
5. **fallback-chain-purity** (SHOULD): `jq` confirma zero entries `anthropic/*` em fallbacks.

Integrar como tools MCP em `nox-mem` para Claude poder autodiagnosticar.
