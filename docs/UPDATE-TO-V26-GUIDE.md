# Update to OpenClaw v.26 — Guia Incremental

> Status: pendente validação em produção (target 2026-04-28 22h BRT)
> Versão alvo: 2026.4.26
> Versão de origem: 2026.4.25
> Tempo: **30-45min** com este guia (vs 2-3h da v.25)
> Dependência: `docs/UPDATE-TO-V25-GUIDE.md` (referência primária — este guia é só o delta)

---

## TL;DR

| | |
|---|---|
| **Vale upgrade?** | SIM — incremento puro |
| **Tempo necessário** | 30-45min (sem wizard, sem token audit completo, sem schema migration grande) |
| **Maior risco** | Cerebras bundled default-on (mesmo padrão bedrock) |
| **Maior win opt-in** | Compaction preflight (`maxActiveTranscriptBytes`) — só ativar se transcripts crescem |
| **Rollback necessário?** | Improvável — fn `cleanStaleGatewayProcessesSync` body idêntica à v.25, deps inalteradas |

Resumo de uma linha: v.26 é **patch incremento sobre canonical da v.25**. Sem novo wizard, sem mudanças em `agentRuntime.id`, sem mudanças em `.credentials.json` flow. Tarball diff confirmou fn crítica byte-for-byte igual.

---

## O que muda em v.26 (e por que importa pra nós)

### Mudanças que afetam nossa stack

#### 1. **Cerebras** como bundled plugin novo (extensions/cerebras/)
Adiciona Cerebras como provider primeiro-class via plugin manifest. Mesma estratégia do bedrock — vem default-on no manifesto. Não usamos. **Disable preventivo em Phase 2.**

#### 2. **Compaction preflight** opt-in
Novo `agents.defaults.compaction.maxActiveTranscriptBytes` faz preflight check antes de cada turn — se JSONL ativo passou o limit, força compaction local antes do turn novo. Successor file recebe transições futuras. **Win pra agents que têm transcripts crescendo (forge, nox).** Opt-in — não ativa sozinho.

#### 3. **Memory asymmetric embeddings** opt-in
`memorySearch.inputType`, `queryInputType`, `documentInputType` permitem query embedding ≠ document embedding. Gemini suporta nativamente (`task_type=RETRIEVAL_QUERY` vs `RETRIEVAL_DOCUMENT`). **Relevante pro nox-mem** — hoje usamos simétrico, asymmetric pode melhorar ranking. Phase 8.

#### 4. **Plugin config helpers deprecation**
Helpers antigos `loadPluginConfig`/`writePluginConfig` deprecated em favor de runtime snapshots + transactional mutation. **Warnings esperados** em logs durante boot e durante `openclaw config set`. Não-fatal.

#### 5. **Plugins manifest model-id normalization**
Provider routing tables movidas pra plugin manifests. **Risco baixo:** se algum config legacy nosso ainda tem `claude-cli/...` prefix, renormalizar pra `anthropic/...` automaticamente. Phase 4 valida.

#### 6. **Gateway device-token fix #66773**
Stop echoing rotated bearer tokens em respostas admin/shared. **Security improvement** — sem ação nossa.

### Não muda (boas notícias confirmadas pelo diff offline)

- Fn `cleanStaleGatewayProcessesSync` body **byte-for-byte idêntica** à v.25 → monkey-patch reapply zero-risco
- `package.json` deps **sem diff** → zero risco peer-deps
- `agentRuntime.id` continua canonical → I13 + I14 da v.25 preservadas
- `.credentials.json` flow inalterado → chattr +i continua válido
- Sem novo wizard `openclaw config` interativo

### O que NÃO usamos (ignorar)

- TTS/Voice/Talk realtime (Google Live, Azure Speech, ElevenLabs) — usamos texto
- Matrix E2EE setup — não usamos Matrix
- Control UI (PWA, pending-changes panel, dashboard polish) — operamos via CLI
- migrate-claude/migrate-hermes — não estamos importando outras configs
- Browser automation — não relevante pra agents conversacionais

---

## Pré-requisitos (CHECK ANTES DE COMEÇAR)

> v.25 já fez todo o setup canonical. Este check só confirma que nada drift.

```bash
# Sentinela única (1 comando que valida 5 invariantes)
ssh root@100.87.8.44 'echo "=== Pre-flight v.26 ===" && \
  echo "1. Versao atual: $(openclaw --version)" && \
  echo "2. agentRuntime: $(openclaw config get agentRuntime.id 2>&1)" && \
  echo "3. credentials immutable: $(lsattr /root/.claude/.credentials.json | awk "{print \$1}")" && \
  echo "4. wrapper immutable: $(lsattr /usr/local/bin/openclaw-gateway-wrapper | awk "{print \$1}")" && \
  echo "5. drop-in: $(grep -c "Environment=" /etc/systemd/system/openclaw-gateway.service.d/override.conf)"'

# Esperado:
# 1. Versao atual: 2026.4.25
# 2. agentRuntime: claude-cli
# 3. credentials immutable: ----i---
# 4. wrapper immutable: ----i---
# 5. drop-in: 2 (IS_SANDBOX=1 + REPAIR_POLICY=external)

# Token HTTP sentinela (não repetir audit completo da v.25)
ssh root@100.87.8.44 'T=$(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json); \
  curl -sw "\nHTTP: %{http_code}\n" -o /dev/null -X POST https://api.anthropic.com/v1/messages \
    -H "anthropic-version: 2023-06-01" \
    -H "x-api-key: $T" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"claude-opus-4-5\",\"max_tokens\":5,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"'
# Esperado: 200 ou 429 (revogado=401 → ROTACIONAR antes)
```

Se algum FAIL: ler `docs/UPDATE-TO-V25-GUIDE.md` Phase 0 completo, resolver, depois voltar pra v.26.

---

## As 3 Pegadinhas Específicas v.26

### Pegadinha 1 — Cerebras vem default-on (mesma lição bedrock)

Novo bundled plugin em `extensions/cerebras/`. Como bedrock-mantle (v.25), provavelmente vem `enabled:true` no manifesto.

```bash
# Ler manifest pre-install (sem instalar)
ssh root@100.87.8.44 'mkdir -p /var/cache/openclaw-v26 && \
  npm pack openclaw@2026.4.26 --pack-destination /var/cache/openclaw-v26/ && \
  tar xOf /var/cache/openclaw-v26/openclaw-2026.4.26.tgz \
    package/dist/extensions/cerebras/openclaw.plugin.json | \
    jq "{id, enabled, default}"'
# Se enabled:true → preparar `openclaw plugins disable cerebras` em Phase 2
```

### Pegadinha 2 — Plugin config deprecation warnings inflam o log

`loadPluginConfig`/`writePluginConfig` agora warn em cada uso. Esperado em boot e em qualquer `openclaw config set`. **Não é erro** — não abort por causa disso. Filtrar com `grep -v "DEPRECATION"` se atrapalhar análise.

### Pegadinha 3 — Manifest model-id normalization pode "consertar" config legacy

Se algum agent ainda tem `claude-cli/claude-opus-4-6` no `model.primary` (legacy v.23), v.26 normaliza pra `anthropic/claude-opus-4-6`. **Não é regression** — é o canonical certo. Phase 4 valida via `openclaw config get agents.defaults.model.primary` — se mudou, OK desde que `agentRuntime.id == claude-cli` continue intacto.

---

## ROTEIRO COMPLETO (incremento puro)

> Comandos assumem execução da máquina local via SSH.

### Phase 0 — Pre-flight (zero risco, ~5min)

```bash
NEW="2026.4.26"
DATE=$(date +%Y%m%d-%H%M)

# 0.A Backup
ssh root@100.87.8.44 "tar czf /var/backups/preupgrade-v${NEW}-${DATE}.tar.gz \
  /root/.openclaw/openclaw.json \
  /root/.openclaw/agents/*/agent/auth-profiles.json \
  /root/.openclaw/agents/*/sessions/sessions.json \
  /etc/systemd/system/openclaw-gateway.service.d/ \
  /usr/local/bin/openclaw-gateway-wrapper \
  /usr/bin/node \
  /root/.claude/.credentials.json"

ssh root@100.87.8.44 "sqlite3 /root/.openclaw/workspace/tools/nox-mem/data/nox-mem.db \
  \"VACUUM INTO '/var/backups/nox-mem-pre-v${NEW}-${DATE}.db';\""

# 0.B Sentinela única (token HTTP + invariantes I1-I12 do v.25)
# (rodar bloco da seção "Pré-requisitos" acima)

# 0.C Pre-stage tarball + ler manifest cerebras
ssh root@100.87.8.44 'tar xOf /var/cache/openclaw-v26/openclaw-2026.4.26.tgz \
  package/dist/extensions/cerebras/openclaw.plugin.json | jq .'

# 0.D Health snapshot
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health > /var/backups/health-pre-v26.json'
```

**Gate Phase 0:** backups feitos, sentinela verde, manifest lido. Aprovação.

---

### Phase 1 — Install Pinned (~5min)

```bash
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher nox-mem-api openclaw-gateway && \
  ps -ef | grep -E "openclaw|nox-mem" | grep -v grep | wc -l'
# Esperado: 0

ssh root@100.87.8.44 'npm install -g openclaw@2026.4.26 2>&1 | tail -3'
ssh root@100.87.8.44 'openclaw --version'
# Esperado: 2026.4.26

ssh root@100.87.8.44 'ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js'
# Esperado: restart-stale-pids-BQxFGeFd.js (ou hash similar — glob casa)
```

**Gate Phase 1:** versão exata, novo arquivo localizado.

---

### Phase 2 — Reapply Customizations + Disable Cerebras (~10min)

```bash
# 2.1 Monkey-patch (zero risco — fn idêntica à v.25)
ssh root@100.87.8.44 'bash /root/reapply-monkey-patch.sh 2>&1'
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A8 cleanStaleGatewayProcessesSync | head -10'
# Esperado: marker MONKEY_PATCH_62028 + "return [];" como primeira linha do corpo

# 2.2 Disable Cerebras (novo bundled v.26)
ssh root@100.87.8.44 'openclaw plugins list --json | \
  jq ".[] | select(.id | test(\"cerebras\"))"'
ssh root@100.87.8.44 'openclaw plugins disable cerebras 2>&1'
ssh root@100.87.8.44 'openclaw plugins list --json | \
  jq "[.[] | select(.id | test(\"cerebras\")) | .enabled] | any"'
# Esperado: false

# 2.3 Re-validar bedrock disabled (cold registry deve preservar)
ssh root@100.87.8.44 'openclaw plugins list --json | \
  jq "[.[] | select(.id | test(\"bedrock\")) | .enabled] | any"'
# Esperado: false

# 2.4 Imutáveis intactos
ssh root@100.87.8.44 'lsattr /usr/local/bin/openclaw-gateway-wrapper /root/.claude/.credentials.json'
# Esperado: ----i--- em ambos

# 2.5 Daemon reload
ssh root@100.87.8.44 'systemctl daemon-reload'
```

**Gate Phase 2:** monkey-patch validado (body + marker), Cerebras + bedrock disabled, imutáveis intactos.

---

### Phase 3 — Schema Validation (~5min — sem wizard)

> v.26 não tem wizard novo. Só validamos doctor + canonical preservado.

```bash
ssh root@100.87.8.44 'cp /root/.openclaw/openclaw.json /var/backups/openclaw-pre-doctor-v26.json'

ssh root@100.87.8.44 'OPENCLAW_SERVICE_REPAIR_POLICY=external openclaw doctor --non-interactive 2>&1 | \
  tee /var/backups/doctor-check-v26.log | tail -30'

# Aceitável: warnings DEPRECATION sobre plugin config helpers
# Abort se: stripping de agents.defaults, removing model.primary, removing channels.*

# Validar I13 + I14 (canonical da v.25 preservado)
ssh root@100.87.8.44 'openclaw config get agentRuntime.id'  # claude-cli
ssh root@100.87.8.44 'jq ".profiles[\"anthropic:claude-cli\"]" \
  /root/.openclaw/agents/nox/agent/auth-profiles.json'
# Esperado: { "mode": "token", "provider": "claude-cli" }

# Diff config (deve ser mínimo ou só normalizações esperadas)
ssh root@100.87.8.44 'diff /var/backups/openclaw-pre-doctor-v26.json \
  /root/.openclaw/openclaw.json | head -30'
```

**Gate Phase 3:** doctor sem reds, I13+I14 intactos, diff só com normalizações esperadas (ou vazio).

---

### Phase 4 — Bring-up Sequencial (~10min)

```bash
ssh root@100.87.8.44 'systemctl start openclaw-gateway'
ssh root@100.87.8.44 'journalctl -fu openclaw-gateway --since "5s ago" 2>&1 | head -60'
```

**Checklist primeiros 60s:**

| Sinal | OK | Alerta |
|---|---|---|
| Versão reportada | `2026.4.26` | abort se diferente |
| Tempo até "ready" | < 15s | > 30s → F5 (mas sem wizard pra rodar — investigar) |
| Restart counter | 0 | > 0 → F6 (monkey-patch perdido) |
| 401/Not logged in | ausente | F1/F2 |
| `[plugins] [claude-cli] ready` | presente | registry regrediu → F7 |
| `[plugins] [cerebras] ready` | **ausente** | re-disable não pegou → 2.2 de novo |
| Plugin count | ~12 (mesmo da v.25) | > 50 → registry reset |
| Warnings DEPRECATION plugin config | OK (esperado v.26) | filtrar do log |

```bash
ssh root@100.87.8.44 'systemctl start nox-mem-api && sleep 3 && \
  curl -s http://127.0.0.1:18802/api/health | jq .status'
# Esperado: "ok"

ssh root@100.87.8.44 'systemctl start nox-mem-watcher && sleep 2 && \
  systemctl is-active nox-mem-watcher'
# Esperado: active
```

**Gate Phase 4:** 3 services active, claude-cli loaded, cerebras NOT loaded, restart counter 0.

---

### Phase 5 — Smoke Test 6 Agents (~10min)

Sequencial: **nox → forge → atlas → boris → cipher → lex**.

Para cada agent:
1. 1 mensagem trivial via canal
2. Confirma `sessions.json` :main lane com `claude-*`
3. journalctl sem 401 nos últimos 2min

Se falhar: forward-fix (F1/F2), não pular.

---

### Phase 6 — Re-validação rápida (~3min)

```bash
ssh root@100.87.8.44 'lsattr /root/.claude/.credentials.json | grep -o "\-i-" && \
  echo "OK imutavel" || (chattr +i /root/.claude/.credentials.json && echo "Reimut")'

# Diff rápido pré vs pós upgrade
ssh root@100.87.8.44 'diff /var/backups/health-pre-v26.json \
  <(curl -s http://127.0.0.1:18802/api/health) | head -20'
```

---

### Phase 7 — Observação 30min

Mesmo loop da v.25. 6 checkpoints a cada 5min validando:
- 3 services active
- 0 401 errors em 5min
- vectorCoverage estável
- Heartbeats no Discord normais
- Cron canary verde

---

## Forward-fix Decision Tree

> Mesmas referências (F1-F7) do guia v.25. Tudo aplicável idêntico.
>
> Adicionado novo cenário **F8** abaixo.

### F8 — Cerebras carregando após disable

```bash
# Causa provável: disable não persistiu no cold registry
ssh root@100.87.8.44 'openclaw plugins disable cerebras --persist 2>&1 || \
  openclaw plugins disable cerebras'
ssh root@100.87.8.44 'systemctl restart openclaw-gateway'

# Se persistir como enabled após restart: physical mv (lição bedrock-mantle)
ssh root@100.87.8.44 'mv /root/.openclaw/extensions/cerebras /tmp/cerebras-disabled-$(date +%Y%m%d)'
```

---

## Métricas Reais Esperadas Após v.26

| Métrica | v.25 final | v.26 esperada |
|---|---|---|
| Plugins carregados | 12/113 | 12/114 (cerebras disabled) |
| Boot time | 11.4s | ≤ 13s (DEPRECATION warnings adicionam ~1s log) |
| Latency p50 | 12s | 12s (mesmo path claude-cli direto) |
| FailoverErrors / 5min | 0 | 0 |
| Pay-per-token | zero | zero |
| Monkey-patch hash | CSJWMprl | **BQxFGeFd** (validado offline) |
| Compaction preflight ativo | não | não (Phase 8 opcional) |

---

## Wins Opt-in da v.26 (Phase 8 — após 7d estável)

### Compaction preflight (`maxActiveTranscriptBytes`)

**Decisão:** ativar SE algum agent tem JSONL :main > 30MB.

```bash
# Medir antes de decidir
ssh root@100.87.8.44 'for a in nox forge atlas boris cipher lex; do
  echo -n "$a: "
  ls -la /root/.openclaw/agents/$a/sessions/*.jsonl 2>/dev/null | \
    awk "{print \$5}" | sort -rn | head -1
done'
```

Se threshold passar:
```bash
ssh root@100.87.8.44 'openclaw config set agents.defaults.compaction.maxActiveTranscriptBytes 31457280 && \
  openclaw config validate && \
  systemctl reload openclaw-gateway'
```

### Asymmetric memory embeddings (nox-mem)

Avaliação técnica antes — não ativar direto. Hoje nox-mem chama Gemini com `task_type=RETRIEVAL_DOCUMENT` em queries E documentos. Asymmetric mode usaria `RETRIEVAL_QUERY` pra queries. Shadow-mode 7d comparando precisão antes de ativar.

---

## Quando NÃO Fazer Este Upgrade

| Condição | Por que |
|---|---|
| Token HTTP test retornou 401 agora | Resolver antes — upgrade não conserta |
| `openclaw --version` ainda diferente de 2026.4.25 | Pular pra UPDATE-TO-V25-GUIDE.md primeiro |
| Sistema 24/7 sem janela de 45min disponível | Phase 1-4 derruba serviços |
| Comunidade reportou regressão grave nas últimas 12h | Aguardar |

---

## Quando ABORTAR Mid-Upgrade (Rollback)

Mesmas condições do v.25. Rollback procedure:

```bash
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher nox-mem-api openclaw-gateway && \
  npm install -g openclaw@2026.4.25 && \
  bash /root/reapply-monkey-patch.sh && \
  systemctl start openclaw-gateway nox-mem-api nox-mem-watcher && \
  openclaw --version'
# Esperado: 2026.4.25
```

Considerar criar `/root/upgrade-2026.4.26.sh` + `/root/rollback-2026.4.26.sh` seguindo padrão `/root/upgrade-4.24.sh` existente.

---

## Lições para Futuros Upgrades (v.27+)

### L7 — Tarball diff offline antes de tocar VPS

`npm pack` ambas versões + `tar tzf | comm` + `tar xOf | diff` na fn crítica.
Cinco minutos local que evitam descoberta de breaking change em Phase 4.

### L8 — Distinguir patch incremento vs big-bang antes de planejar

Sinais de incremento puro:
- `package.json` deps sem diff
- `agentRuntime.id` canonical inalterado
- Fn `cleanStaleGatewayProcessesSync` body idêntica
- Sem novo wizard

Patch incremento → 30-45min Phase compactada.
Big-bang (como v.25) → 2-3h Phase completa + wizard.

### L9 — Novo bundled plugin = default-on por padrão

Toda nova versão pode trazer plugin novo em `extensions/<name>/`. Verificar manifest pre-install. Disable preventivo segue o pattern bedrock/cerebras. Adicionar à pre-flight checklist.

---

## Referências

- Release notes v.26: https://github.com/openclaw/openclaw/releases/tag/v2026.4.26
- Guia v.25 completo: `docs/UPDATE-TO-V25-GUIDE.md` (referência primária — este guia é só o delta)
- Plan v.26: `plans/2026-04-28-openclaw-v2026.4.26-upgrade.md`
- Runbook genérico: `docs/RUNBOOKS/openclaw-upgrade-runbook.md`
- `CLAUDE.md` rules 5, 6, 9, 11, 12, 13 — operacionais
