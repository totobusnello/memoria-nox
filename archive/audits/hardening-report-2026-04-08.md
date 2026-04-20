# OpenClaw VPS Hardening Report — 2026-04-08

## Sessão: ~4 horas de debugging e hardening

---

## 1. Problemas Encontrados e Soluções

### P1: Service file corrompido pelo Forge
**Sintoma:** Gateway em crash loop, 2 processos competindo pela porta 18789
**Causa raiz:** Forge reescreveu `/etc/systemd/system/openclaw-gateway.service` via SSH usando heredoc. Incluiu comandos shell (`systemctl daemon-reload && ...`) DENTRO do arquivo .service. Removeu `ExecStartPre=fuser -k 18789/tcp` e `StartLimitBurst`.
**Fix:** Restaurado service file correto.
**Prevenção:** `chattr +i` nos 4 arquivos críticos (gateway.service, relayplane.service, gateway-wrapper, node wrapper). Nenhum agente consegue reescrever.

### P2: Plugin Telegram fantasma
**Sintoma:** Gateway morria com SIGTERM a cada ~90s. Health monitor interno matava o processo.
**Causa raiz:** `plugins.entries.telegram.enabled: true` no openclaw.json, mas o service `claude-telegram.service` estava desabilitado desde Mar 31. O health monitor esperava o Telegram conectar, não conseguia, e matava o gateway após o grace period.
**Fix:** Removidas TODAS as referências ao Telegram do openclaw.json (plugins.entries.telegram + channels.telegram).
**Aprendizado:** Desabilitar um service systemd NÃO é suficiente — o plugin no openclaw.json continua tentando conectar. Remover a seção inteira.

### P3: User service duplicado (v2026.4.5 vs system v2026.4.8)
**Sintoma:** Gateway recebia SIGTERM mesmo após fix do Telegram. "Killing stale gateway processes" nos logs.
**Causa raiz:** `systemctl --user` tinha `openclaw-gateway.service` (v2026.4.5) além do system-level service (v2026.4.8). O user service + restart-guard skill ficavam matando o system gateway como "stale". Dois gateways competindo pela mesma porta 18789.
**Fix:** `systemctl --user stop/disable/mask openclaw-gateway.service`
**Aprendizado:** SEMPRE checar `systemctl --user list-units` além do `systemctl list-units`. User services são invisíveis nos comandos padrão.

### P4: RelayPlane morto sem detecção
**Sintoma:** Agentes respondiam "Rate-limited — ready in ~15s" mesmo com assinaturas pagas.
**Causa raiz:** `relayplane-proxy.service` estava `inactive (dead)`. Gateway tinha `ANTHROPIC_BASE_URL=http://127.0.0.1:4100` mas ninguém escutava. Anthropic falhava → cascata para Gemini (quota esgotada) → OpenAI (sem créditos) → "Rate-limited".
**Fix:** Reiniciado RelayPlane, habilitado para boot. Depois removido `ANTHROPIC_BASE_URL` (direto para Anthropic sem proxy).
**Aprendizado:** Health check não verificava porta 4100. Agora health-probe.sh verifica tudo.

### P5: Delivery queue com 2016 mensagens stale
**Sintoma:** Agentes lentos, falando coisas aleatórias, delay enorme nas respostas.
**Causa raiz:** 70+ restarts geraram boot tasks e cron "missed jobs" que acumularam na delivery queue. Cada restart adicionava mais. Gateway ficava processando backlog em vez de responder mensagens novas.
**Fix:** `mv delivery-queue delivery-queue-backup-stale` + mkdir novo vazio.
**Aprendizado:** Após crash loops prolongados, SEMPRE limpar a delivery queue antes de declarar "fixed".

### P6: Fallback cascade amplificando falhas
**Sintoma:** Cada restart queimava quota em Gemini e OpenAI. 7 agentes × 2 fallbacks × 15 restarts = 200+ API calls desperdiçadas.
**Causa raiz:** Todos os 7 agentes tinham `fallbacks: ["openai-codex/gpt-5.4", "gemini/gemini-2.5-flash"]`. Quando Anthropic falhava (por causa do RelayPlane morto), cascateava para providers com quota esgotada.
**Fix:** Fallbacks limpos (`fallbacks: []`). Só Anthropic Sonnet como primary.
**Status:** Fallbacks podem ser reativados quando necessário, mas com providers que funcionam.

### P7: 42 cron jobs internos com modelo errado
**Sintoma:** Agentes "falando besteira", respostas sem sentido.
**Causa raiz:** Cron jobs internos do OpenClaw (`/root/.openclaw/cron/jobs.json`) usavam `gemini/gemini-2.5-flash` e `openai/gpt-5` — providers que estavam com quota esgotada. Os crons falhavam e corrompiam estado dos agentes.
**Fix:** Todos os 42 jobs alterados para `anthropic/claude-haiku-4-5` (depois confirmamos que Gemini Flash funciona — pode voltar).
**Nota:** O rollback restaurou os crons ao estado original (Gemini Flash) e está funcionando agora que o gateway está estável.

### P8: .env com `export` incompatível com systemd
**Sintoma:** systemd logava "Ignoring invalid environment assignment" para todas as vars.
**Causa raiz:** `/root/.openclaw/.env` usa `export VAR=value`. systemd EnvironmentFile espera `VAR=value`.
**Impacto real:** Baixo. OpenClaw lê o .env internamente (via dotenv). As vars são carregadas pelo gateway, não pelo systemd.
**Decisão:** Manter como está. Documentar o quirk.

### P9: OAuth tokens expostos em `ps aux`
**Sintoma:** 3 processos orphan de 17h com `sk-ant-oat01-*` visíveis nos argumentos do processo.
**Causa raiz:** Processos `claude setup-token` que ficaram pendurados sem morrer.
**Fix:** Processos mortos. Permissões de credentials.json e google_client_secret.json corrigidas para 600.

### P10: OpenClaw fork behavior vs systemd
**Sintoma:** `Type=simple` tratava fork do OpenClaw como crash → restart loop infinito.
**Causa raiz:** `openclaw gateway run` faz fork internamente — parent spawna child e parent recebe SIGKILL. Comportamento intencional do OpenClaw (auto-proteção/daemonização).
**Fix:** `Type=oneshot` + `RemainAfterExit=yes` + `KillMode=none` + `SuccessExitStatus=KILL`. Health probe compensa a falta de auto-restart do systemd.
**Trade-offs aceitos:** systemctl stop não mata o child (precisa fuser -k), status "mente", KillMode=none deprecated (mas anos, não meses).

---

## 2. Mudanças de Configuração (Estado Final)

### OpenClaw
- **Versão:** v2026.4.5 → **v2026.4.8**
- **Telegram:** REMOVIDO completamente (plugins.entries + channels)
- **Gateway bind:** `lan` → `loopback` (127.0.0.1 only)
- **Model fallbacks:** Limpos em todos os 7 agentes (`fallbacks: []`)
- **Cron jobs internos:** 42 jobs com modelos corrigidos

### Systemd
- **openclaw-gateway.service:** Type=oneshot, RemainAfterExit=yes, KillMode=none, SuccessExitStatus=KILL
- **User service:** `systemctl --user` gateway MASCARADO (v2026.4.5 conflitava)
- **RelayPlane:** enabled para boot
- **Ollama:** disabled (não usado)
- **nox-mem-watcher:** disabled (duplicata de nox-mem-watch)
- **billing proxy:** morto e removido

### SOUL.md
- **21,702 bytes → 4,842 bytes** (77% menor)
- Todas as regras mantidas, duplicatas removidas
- Não trunca mais (estava excedendo limite de 20,000 chars)

### Sessions
- Sessões >3 dias arquivadas em `/root/.openclaw/backups/sessions-archive-20260408/`
- Main: 65MB → 42MB

### Skills
- **63 → 11 skills** (83% redução)
- Discord não mostra mais "119 commands exceeds limit"
- Mantidas: deep-research, discord, gemini, github, notion, pdf, restart-guard, session-logs, research, summarize, tmux
- Archive: `/root/.openclaw/workspace/skills-archive-20260408/`

### Crontab
- **30 → 7 entries**
- 3 scripts orquestrados: nightly-maintenance.sh, backup-all.sh, health-probe.sh
- Mantidos: config-drift-monitor, token-refresh-max, forge-cc-token-check, sync-verify

### Segurança
- `chattr +i` em: gateway.service, relayplane.service, gateway-wrapper, node wrapper
- Permissões 600 em: credentials.json, google_client_secret.json, backups/*.json
- APT hook: `/etc/apt/apt.conf.d/99-node-wrapper-guard` (alerta se node.real sumir)
- Orphan processes mortos (3 claude + billing proxy = 674MB liberados)

### Cleanup
- Delivery queue: 2016 mensagens stale removidas
- marker-env: 7.5GB Python venv movido para backups
- 90 sanitized backup duplicatas removidas
- WAL checkpoint: path corrigido para DB produção (87MB)

---

## 3. Aprendizados Chave

### Debugging
1. **Uma mudança por vez, testar entre cada uma.** Batch changes causou rollback.
2. **Sempre checar `systemctl --user`** — user services são invisíveis nos comandos padrão.
3. **Delivery queue acumula durante crash loops** — limpar SEMPRE após outages prolongados.
4. **Desabilitar service ≠ desabilitar plugin** — remover a config inteira do openclaw.json.
5. **Nunca usar sed em JSON** — usar python3 (sed quebrou auth-profiles.json).

### Arquitetura
6. **OpenClaw fork behavior é intencional** — não é bug, é auto-proteção. Aceitar, não contornar.
7. **Health probe > systemd restart** — para processos que fazem fork, probe externo é mais confiável.
8. **Fallback cascade amplifica falhas** — N agentes × M fallbacks × R restarts = desastre exponencial.
9. **SOUL.md < 15KB** — acima de 20K trunca, desperdiça tokens e confunde os agentes.
10. **Menos skills = mais rápido** — 63 skills geravam 119 Discord commands, 11 skills eliminam o bottleneck.

### Operacional
11. **chattr +i protege contra agentes reescrevendo configs** — simples e efetivo.
12. **APT hooks protegem wrappers** — node.real pode sumir em apt upgrade.
13. **Crons orquestrados > crons individuais** — 30 entries com timing frágil vs 3 scripts sequenciais com flock.
14. **Backup antes de cada mudança** — rollback salva quando batch changes quebram.

---

## 4. Rollback Points

| Item | Rollback Command |
|------|-----------------|
| Full pre-hardening | `cp /root/.openclaw/backups/pre-hardening-20260408/* [destinos]` |
| Crontab | `crontab /root/.openclaw/backups/crontab-pre-simplify-20260408.bak` |
| SOUL.md | `cp /root/.openclaw/backups/SOUL.md.bak-20260408 /root/.openclaw/workspace/SOUL.md` |
| Skills | `mv /root/.openclaw/workspace/skills-archive-20260408/* /root/.openclaw/workspace/skills/` |
| Sessions | `mv /root/.openclaw/backups/sessions-archive-20260408/* /root/.openclaw/agents/*/sessions/` |
| Immutable flags | `chattr -i [arquivos]` |
| marker-env | `mv /root/.openclaw/backups/marker-env-20260408 /root/.openclaw/tools/marker-env` |
| OpenClaw version | `npm install -g openclaw@2026.4.5` |

---

## 5. Monitoramento Ativo

| Check | Frequência | Script |
|-------|-----------|--------|
| Gateway porta 18789 | */5 min | health-probe.sh |
| nox-mem API 18800 | */5 min | health-probe.sh |
| SQLite integridade | */5 min | health-probe.sh |
| Node wrapper integridade | */5 min | health-probe.sh |
| Disco >85% | */5 min | health-probe.sh |
| RAM <1GB | */5 min | health-probe.sh |
| Config drift | */30 min | config-drift-monitor.sh |
| Token MAX refresh | */4h | token-refresh-max.sh |
| Circuit breaker | automático | health-probe.sh (3 failures → stop) |

---

## 6. Convenções Atualizadas

- **OpenClaw:** v2026.4.8 (atualizar com `npm update -g openclaw`)
- **Telegram:** REMOVIDO. Não reabilitar.
- **Fallbacks:** Vazios por design. Reativar só com providers funcionais.
- **Crons internos:** 42 jobs, modelos Gemini Flash (verificar quota periodicamente)
- **SOUL.md:** Manter < 15KB. Se precisar adicionar regra, comprimir outra.
- **Skills:** 11 essenciais. Para adicionar: mover de skills-archive, não instalar nova.
- **Imutáveis:** 4 arquivos com chattr +i. Para editar: `chattr -i`, editar, `chattr +i`.
- **Delivery queue:** Após crash loops, limpar com `mv delivery-queue delivery-queue-backup-$(date +%s)`.
- **Gateway Type=oneshot:** Hack estável. Não mudar até OpenClaw ter flag `--foreground`.
