---
chunk_type: lesson
source: internal
date: 2026-04-20
severity: critical
downtime_minutes: 360
tags: [openclaw, gateway, systemd, fratricide, monkey-patch, issue-62028]
related_lessons: [2026-04-01-dep0040-punycode, 2026-04-19-boost-stacking-and-fake-green]
---

# OpenClaw Gateway Fratricide Bug — Issue #62028 (v2026.4.14)

## TL;DR

**Bug:** OpenClaw v2026.4.14 entra em crash loop infinito em systemd porque a função `cleanStaleGatewayProcessesSync()` — chamada durante startup e durante `emitGatewayRestart()` — mata o próprio processo parent achando que é "stale", deixando um child orphan na porta 18789. Systemd vê parent morto, reinicia, novo parent mata o orphan anterior, novo orphan sobrevive, loop infinito até `StartLimitBurst`.

**Impacto:** 6h+ de downtime (09:07 → 14:39 em 2026-04-20). Agentes Discord/Telegram/WhatsApp respondiam intermitentemente (via child orphan antes dele ser morto).

**Root cause:** Regressão introduzida em v2026.4.5. Função `cleanStaleGatewayProcessesSync` em `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-K0DY7JjL.js:509-527` tem filtro de `process.pid` em `findGatewayPidsOnPortSync` (linhas 280/287/295) MAS só exclui o pid do caller — não exclui o child orphan do restart anterior, que o kernel listagem mostra escutando na porta.

**Fix definitivo:** Monkey-patch em `restart-stale-pids-K0DY7JjL.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]` imediatamente. Complementado com unset `OPENCLAW_SERVICE_MARKER` no wrapper + `commands.restart=false` + `gateway.reload.mode=off` + `discovery.mdns.mode=off` no config.

**Não resolve:** v2026.4.15 (última released), `OPENCLAW_NO_RESPAWN=1` sozinho, `commands.restart=false` sozinho (Issue #5533 mostra que é ignorado).

## ⚠️ Nuance crítica: Issue #62028 está CLOSED mas o bug persiste (verificado 2026-04-20 pós-fix)

**Não confie no status do GitHub Issue pra decidir upgrade.** Forge validou:
- Issue #62028 foi fechado em 2026-04-06 no GitHub (antes mesmo da v2026.4.5 ser released — suspeito)
- Issue está **LOCKED** (não aceita mais comentários)
- v2026.4.15 changelog menciona fix pra **Issue #67436 (SIGUSR1 loop)** — **bug diferente**, não o fratricide
- O comportamento real (`cleanStaleGatewayProcessesSync` self-kill) **persiste em v2026.4.15**
- Comentário pra upstream salvo em `shared/github-comments/issue-62028-comment-draft.md` pra quando a issue reabrir ou criarem nova

**Isso significa que o monitor deve checar o CÓDIGO, não o STATUS:**
```bash
# Check se o fix está no binary (sinaliza que monkey-patch não é necessário):
FILE=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | head -1)
grep -q 'return \[\]; // monkey-patch' "$FILE" && echo "MONKEY-PATCHED (nosso fix ativo)"
# OU procurar assinatura que indique que upstream corrigiu:
grep -q 'if (pid === process.pid.*skip)\|selfPid.*exclude' "$FILE" && echo "UPSTREAM FIX DETECTED"
```

**Rollback alternativo:** v2026.3.31 é pré-regression, estável, mas tem config drift.

## Timeline do incident (2026-04-20)

| Hora | Evento |
|---|---|
| 09:07 | Gateway entra em crash loop (StartLimitBurst=5 hit) → systemd=failed. Detectado via ausência de respostas dos agentes |
| 12:30-13:00 | Primeiras tentativas: mDNS off, delivery-queue cleanup (225→0), config restore — sem efeito estrutural |
| 13:00-13:30 | Spawn 3 agents paralelos (devops-incident-responder, debugger, sre-engineer). Debugger encontra código-fonte em `dist/gateway-cli-DhgfjzZ0.js:766-806` (`restartGatewayProcessWithFreshPid`) e identifica wrapper incompatível com v2026.4.14 |
| 13:30 | Wrapper fix v1: adiciona `OPENCLAW_NO_RESPAWN=1`, para de unsettar INVOCATION_ID. Não resolve — kill persiste |
| 13:45 | Descoberta do segundo chamador via log `[restart] killing 1 stale gateway process(es) before restart: <pid>` em `/tmp/openclaw/openclaw-2026-04-20.log` |
| 14:00 | Researcher agent encontra Issue #62028 no GitHub — bug conhecido desde v2026.4.5, nenhuma versão released tem fix |
| 14:30 | Wrapper fix v2: unset `OPENCLAW_SERVICE_MARKER` elimina o path 1 de cleanStale. Bug persiste via path 2 (restart subsystem) |
| 14:35 | **Monkey-patch aplicado** em `restart-stale-pids-K0DY7JjL.js` fazendo `cleanStaleGatewayProcessesSync` retornar `[]` direto |
| 14:39 | Gateway estável, 0 restarts, port listening. **Bug resolvido** |

## Fluxo do bug (explicado)

### Startup normal (o que deveria acontecer)

```
systemd → openclaw-gateway-wrapper → openclaw gateway run
  → bind port 18789
  → load plugins
  → ready
  → serve indefinidamente
```

### Startup com bug v2026.4.14

```
systemd → openclaw-gateway-wrapper → openclaw gateway run
  → bind port 18789
  → load plugins
  → ready (T+4s)
  → hooks loaded (T+5s)
  → acpx/graph-memory/discord/whatsapp started (T+10-15s)
  → cleanStaleGatewayProcessesSync() chamado (path 1: OPENCLAW_SERVICE_MARKER set, OU path 2: emitGatewayRestart)
    → findGatewayPidsOnPortSync(18789)
    → encontra próprio PID (filtro process.pid está lá MAS há child fork interno que o filtro não pega)
    → OU encontra PID do ciclo anterior (orphan sobrevivendo)
  → SIGTERM + SIGKILL → parent morre
  → child orphan continua servindo port 18789 (PPID=1, systemd --user)
  → systemd vê MainPID morto → restart
  → próximo ExecStartPre roda fuser -k 18789/tcp → mata child orphan
  → novo parent starts → bind port → repeat loop
```

## Dois paths de cleanStale (os dois precisam ser bloqueados)

**Path 1 — Service-mode marker** em `gateway-cli-DhgfjzZ0.js:1338`:
```javascript
if (process.env.OPENCLAW_SERVICE_MARKER?.trim()) {
    const stale = cleanStaleGatewayProcessesSync(port);
    if (stale.length > 0) gatewayLog.info(`service-mode: cleared ${stale.length} stale gateway pid(s) before bind on port ${port}`);
}
```
Bloqueado por: `unset OPENCLAW_SERVICE_MARKER` no wrapper.

**Path 2 — Restart subsystem** em `restart-CjpAouST.js`:
- Chamado via `emitGatewayRestart()` (SIGUSR1-triggered OU config-change-triggered OU plugin-triggered)
- Aparece no log com subsystem="restart": `[restart] killing 1 stale gateway process(es) before restart: <pid>`
- NÃO é bloqueado por nenhum env var ou config key — chamada incondicional
- Bloqueado por: monkey-patch no `restart-stale-pids-K0DY7JjL.js`

## Solução aplicada (4 camadas)

### Camada 1: Wrapper

`/usr/local/bin/openclaw-gateway-wrapper`:
```bash
#!/bin/bash
# v2026.4.14 fratricide fix (GitHub Issue #62028):
# - cleanStaleGatewayProcessesSync() roda se OPENCLAW_SERVICE_MARKER esta set, mata parent.
# - MANTER INVOCATION_ID/JOURNAL_STREAM/NOTIFY_SOCKET/SYSTEMD_EXEC_PID pro detector
#   de supervisor retornar "systemd" e usar in-process restart (sem fork-detach).
unset OPENCLAW_SERVICE_MARKER OPENCLAW_SERVICE_KIND
export OPENCLAW_NO_RESPAWN=1
exec /usr/local/bin/openclaw gateway run --bind loopback
```

Atributo `chattr +i` mantido (imutabilidade protege contra reescrita acidental por installer OpenClaw).

### Camada 2: Config `openclaw.json`

- `commands.restart = false` — desativa restart subsystem que chama `emitGatewayRestart()`
- `gateway.reload.mode = "off"` — desativa hot-reload de config que também dispara restart
- `discovery.mdns.mode = "off"` — silencia bonjour watchdog (ruído, não é causa raiz mas gerava warnings no restart subsystem)

### Camada 3: Monkey-patch no binary (A CHAVE)

`/usr/lib/node_modules/openclaw/dist/restart-stale-pids-K0DY7JjL.js`, função `cleanStaleGatewayProcessesSync`:

```javascript
function cleanStaleGatewayProcessesSync(portOverride) {
    // MONKEY-PATCHED 2026-04-20 fix Issue #62028: skip stale cleanup (was killing self)
    return [];
    try {
        // ... original code preserved below (unreachable)
```

Essa é a camada que efetivamente mata o bug. A função vira no-op. Nada de stale cleanup.

### Camada 4: health-probe resiliente

`/root/.openclaw/scripts/health-probe.sh` (cron */5min):
- Se port 18789 não está listening → `systemctl reset-failed openclaw-gateway && systemctl start openclaw-gateway`
- Circuit breaker em `/tmp/openclaw-circuit-open` para após 3 restarts consecutivos (evita flapping)

## Backups preservados

- `/usr/local/bin/openclaw-gateway-wrapper.bak-20260420-1320` — wrapper original
- `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-K0DY7JjL.js.bak-20260420` — binary original
- `/root/.openclaw/openclaw.json.bak-20260420-1235` — config original
- `/root/.openclaw/scripts/health-probe.sh.bak-20260420` — script original

Para reverter TUDO: `cp <arquivo>.bak-20260420* <arquivo>` nos 4 arquivos acima, então `systemctl daemon-reload && systemctl restart openclaw-gateway`.

## ⚠️ CRÍTICO — Fragilidade do monkey-patch

**O patch no `restart-stale-pids-K0DY7JjL.js` será PERDIDO se:**
- `npm update -g openclaw` rodar
- `npm install -g openclaw@<qualquer versão>` rodar
- OpenClaw installer fizer auto-update
- Sistema operacional fizer upgrade de Node.js que toca em node_modules global

**Antes de qualquer upgrade do OpenClaw:**

1. Checar status do Issue #62028: https://github.com/openclaw/openclaw/issues/62028
2. Se fixed em versão nova → upgrade limpo, remover monkey-patch
3. Se ainda aberto → após upgrade, re-aplicar monkey-patch:

```bash
ssh root@100.87.8.44
FILE=/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js
# Nome do arquivo pode mudar após upgrade (hash suffix) — ajustar
python3 <<'PYEOF'
import glob
files = glob.glob('/usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js')
for path in files:
    src = open(path).read()
    old = 'function cleanStaleGatewayProcessesSync(portOverride) {\n\ttry {'
    new = 'function cleanStaleGatewayProcessesSync(portOverride) {\n\treturn [];\n\ttry {'
    if old in src and 'return [];' not in src[:src.index('try {')]:
        open(path,'w').write(src.replace(old, new))
        print(f'PATCHED {path}')
PYEOF
systemctl restart openclaw-gateway
```

## Lições aprendidas

1. **Produtos Node.js distribuídos via npm podem ter bugs específicos de plataforma** — mesmo projetos maduros. v2026.4.14 funciona em macOS/launchd mas quebra Linux/systemd. Testar na target platform antes de upgrade.

2. **Monkey-patch em dist/ é ferramenta legítima** quando upstream não tem fix e rollback tem custos. Documentar bem (comentário no código + lesson) e ter script pra re-aplicar.

3. **Wrapper patterns que "unsetavam env vars pra evitar daemonization" podem virar incompatíveis** em versões novas do binary. Validar supervisor detection via `cat /proc/<pid>/environ` antes de declarar vitória.

4. **Dois caminhos de código podem chamar a mesma função destrutiva** — bloquear UM path (via env var) não é suficiente se OUTRO path é incondicional. Monkey-patch na função destino é mais robusto que bloquear cada chamador.

5. **Sintomas "SIGKILL externo" nem sempre vêm de OOM ou de outro processo** — podem ser auto-envio via `process.kill(process.pid, 'SIGTERM')` que é catcheado pelo handler e logado como "SIGTERM received". Depois systemd manda SIGKILL porque processo demora pra sair.

6. **Logs do próprio processo (`/tmp/openclaw/*.log`) revelam mais que journalctl** — especialmente quando o processo tem subsystem="restart" distinct dos logs do systemd unit.

7. **Spawning 3 agents paralelos com ângulos complementares (kernel tracing, binary analysis, architectural) colapsa tempo de debug** — o que levaria dias sequencial foi feito em ~40min de wall-clock.

8. **Issue tracking upstream é investigação obrigatória antes de debug profundo local** — Issue #62028 descreve o exato mesmo bug desde 2026-04-07. Ter pesquisado PRIMEIRO teria economizado ~2 horas de investigação redundante.

## Convenções institucionais derivadas

Adicionar ao CLAUDE.md do memoria-nox na seção Convenções:

- **Antes de `npm update -g openclaw`:** verificar Issue #62028 status. Se aberto, re-aplicar monkey-patch em `restart-stale-pids-*.js`. Script em `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`.
- **Wrapper `/usr/local/bin/openclaw-gateway-wrapper` deve ser imutável (`chattr +i`)** — evita que installer sobrescreva. Para editar: `chattr -i`, editar, `chattr +i`.
- **Antes de setar config via `openclaw config set`:** lembrar que reformat pode disparar reload — se gateway está rodando, parar primeiro.
- **Os 2 paths de cleanStale são:** (1) via `OPENCLAW_SERVICE_MARKER` → bloquear com unset no wrapper; (2) via `emitGatewayRestart` → bloquear com monkey-patch.

## Referências

- **GitHub Issue #62028**: https://github.com/openclaw/openclaw/issues/62028 (bug principal, aberto)
- **GitHub Issue #5533**: https://github.com/openclaw/openclaw/issues/5533 (commands.restart=false broken)
- **GitHub Issue #25443**: https://github.com/openclaw/openclaw/issues/25443 (OPENCLAW_NO_RESPAWN docs)
- **GitHub Issue #52922**: https://github.com/openclaw/openclaw/issues/52922 (gateway lock conflict restart loop)
- **PR #42544**: https://github.com/openclaw/openclaw/pull/42544 (fix anterior, insuficiente)
- **OpenClaw CHANGELOG**: https://github.com/openclaw/openclaw/blob/main/CHANGELOG.md
- **Versão estável pré-regression**: 2026.3.31
- **Versão atual com monkey-patch**: 2026.4.14 + patches

### Arquivos do código (file:line)

- `dist/restart-stale-pids-K0DY7JjL.js:509-527` — `cleanStaleGatewayProcessesSync` (FUNÇÃO MONKEY-PATCHED)
- `dist/restart-stale-pids-K0DY7JjL.js:280,287,295` — filtros `process.pid` (existem mas insuficientes)
- `dist/gateway-cli-DhgfjzZ0.js:640-676` — `detectRespawnSupervisor` (lookup de INVOCATION_ID etc)
- `dist/gateway-cli-DhgfjzZ0.js:766-806` — `restartGatewayProcessWithFreshPid`
- `dist/gateway-cli-DhgfjzZ0.js:1338` — chamada de cleanStale path 1 (service marker)
- `dist/restart-CjpAouST.js:139-162` — `emitGatewayRestart` (chamada path 2)
- `dist/server.impl-BbJvXoPb.js:18638` — config-change reload trigger (pode chamar emitGatewayRestart)
- `/usr/local/bin/openclaw-gateway-wrapper` — script bash (imutável, chattr +i)
- `/etc/systemd/system/openclaw-gateway.service` — service unit

## Entidades identificadas (para KG)

- **Projetos**: OpenClaw (gateway distribuído), nox-mem v3.4
- **Componentes**: openclaw-gateway (systemd service), openclaw binary, cleanStaleGatewayProcessesSync (função), restart subsystem, emitGatewayRestart (função), health-probe.sh, restartGatewayProcessWithFreshPid
- **Conceitos**: fratricide bug, monkey-patch, systemd Type=simple, fork-and-die pattern, orphan child, supervisor detection, StartLimitBurst, config hot-reload, service-mode marker
- **Versões**: 2026.3.31 (last stable), 2026.4.5 (regression introduced), 2026.4.14 (current, bugged), 2026.4.15 (latest released, no fix)
- **Issues**: #62028 (main), #5533 (commands.restart), #25443 (NO_RESPAWN), #52922 (lock conflict), #20536 (supervisor detection), PR #42544
- **Agentes usados**: devops-incident-responder, debugger, sre-engineer, researcher
- **Pessoas**: Toto (owner), Forge (code review após fix)
- **Arquivos**: wrapper, restart-stale-pids-*.js, openclaw.json, health-probe.sh, restart-CjpAouST.js, gateway-cli-DhgfjzZ0.js

## Pendências pós-fix

1. [ ] Abrir comentário no Issue #62028 do GitHub reportando a reprodução em VPS/systemd Type=simple com OPENCLAW_SERVICE_MARKER set + detalhes do monkey-patch
2. [ ] Adicionar monitor de versão npm do openclaw — se sair 2026.4.16+ verificar se Issue #62028 foi fechado
3. [ ] Forge review do monkey-patch (code review da mudança no dist/)
4. [ ] Incluir script de re-aplicação do monkey-patch em `/root/.openclaw/scripts/reapply-gateway-fix.sh` pra facilitar após npm updates
5. [ ] Considerar pin da versão openclaw no package-lock se houver (ou equivalente) pra evitar auto-update
