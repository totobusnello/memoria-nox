# Runbook — Rollback OpenClaw version

**Quando usar:** após `npm install -g openclaw@<version>` ou `openclaw models auth *` introduzir gateway crash loop / fratricide / schema reject / agents 401.

**Sintomas comuns:**
- `journalctl -u openclaw-gateway` mostra >15 restarts/5min
- Logs com "Gateway already running locally" (Issue #62028 patch perdido)
- HTTP 401 em todos agents (sessions stuck em fallback model)
- "Unrecognized keys" no openclaw.json schema

## Pré-requisitos

- SSH root VPS (`ssh root@100.87.8.44`)
- Script `/root/upgrade-<VERSION>.sh` + `/root/rollback-<VERSION>.sh` foram gerados (convenção desde 04-23)
- Backups em `/root/backups/openclaw-pre-<VERSION>/`
- Versão estável conhecida (atual prod 2026.4.23)

## Procedure (10min)

### 1. Identificar versão estável + backup mais recente
```bash
ssh root@100.87.8.44 '
ls -la /root/rollback-*.sh | tail -5
ls -la /root/backups/openclaw-pre-* | tail -3
'
```

### 2. Stop services + executar rollback script
```bash
ssh root@100.87.8.44 '
# Stop services pra evitar lock contention
systemctl stop openclaw-gateway

# Run rollback (script gerado pelo upgrade)
bash /root/rollback-<VERSION>.sh 2>&1 | tail -20

# rollback script faz:
#   1. npm install -g openclaw@<previous-version>
#   2. cp /root/backups/openclaw-pre-<VERSION>/openclaw.json /root/.openclaw/
#   3. cp /root/backups/openclaw-pre-<VERSION>/sessions-main.json.bak /root/.openclaw/agents/main/sessions/sessions.json
#   4. bash /root/reapply-monkey-patch.sh (Issue #62028)
'
```

### 3. Reapply monkey-patch (caso script automático falhe)
```bash
ssh root@100.87.8.44 'bash /root/reapply-monkey-patch.sh 2>&1 | tail -10'
# Esperado: "Patch applied to /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js"
```

### 4. Restart + validate
```bash
ssh root@100.87.8.44 '
systemctl start openclaw-gateway
sleep 5
systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher
journalctl -u openclaw-gateway --since "1 minute ago" --no-pager | tail -10
'
```

Esperado:
- 4 services `active`
- Logs sem `SIGTERM` ou `Gateway already running`
- `/var/log/syslog` sem `nox-canary CRITICAL`

### 5. Canary check
```bash
ssh root@100.87.8.44 '
bash /root/.openclaw/scripts/check-monkey-patch.sh && echo "OK monkey-patch"
tail -3 /var/log/nox-schema-invariants.log
curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage
'
```

### 6. Sessions cleanup (se necessário)
Se agents continuam em fallback model após rollback, sessions podem estar grudadas:
```bash
ssh root@100.87.8.44 '
# Filtrar só sessions Claude válidas
for d in main nox atlas boris cipher forge lex; do
  jq "with_entries(select(.value.model | startswith(\"claude-\")))" \
    /root/.openclaw/agents/$d/sessions/sessions.json > /tmp/cleaned.json
  mv /tmp/cleaned.json /root/.openclaw/agents/$d/sessions/sessions.json 2>/dev/null
done
systemctl restart openclaw-gateway
'
```

## Pós-rollback

1. Documentar em `docs/INCIDENTS.md` (timestamp + versão buggy + rollback feito)
2. NÃO re-fazer upgrade até identificar root cause + teste em isolado
3. Validar 24h estável antes de retry

## Comandos que invalidam o monkey-patch (CLAUDE.md regra #6)

- `npm install/update -g openclaw`
- `openclaw models auth {add,login,paste-token,setup-token}`
- `apt upgrade nodejs`

Após qualquer um destes: rodar `bash /root/reapply-monkey-patch.sh` ANTES do próximo restart.

## Tokens cleanup pré-rollback

Se rollback é por 401 em agents, validar tokens antes:
```bash
ssh root@100.87.8.44 '
# claude-cli token check
jq -r ".claudeAiOauth.accessToken[0:15]" ~/.claude/.credentials.json
claude auth status

# Anthropic API key (não deveria estar setado se claude-cli ativo)
grep -E "^ANTHROPIC|^CLAUDE" /root/.openclaw/.env | grep -v "^#"
'
```

Se token Claude expirou (1y validade): renovar via `claude setup-token` ANTES do rollback (caso contrário rollback não resolve).
