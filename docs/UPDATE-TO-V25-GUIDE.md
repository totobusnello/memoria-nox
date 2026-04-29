# Update to OpenClaw v.25 — Guia Definitivo

> Status: validado em produção 2026-04-27
> Versão alvo: 2026.4.25
> Versão de origem: 2026.4.23
> Tempo: 2-3h se seguir este guia (vs 5h+ improvisado)

---

## TL;DR

| | |
|---|---|
| **Vale upgrade?** | SIM |
| **Tempo necessário** | 2-3h com este guia; ~1h Phase 0 pode ser feita separada antes |
| **Maior risco** | Token Anthropic divergente em até 5 lugares — invisível até Phase 4 se não auditado em Phase 0 |
| **Maior win** | claude-cli routing primary direto: latency p50 33s → 12s pós-wizard + Gemini key válida |
| **Rollback necessário?** | Não. Forward-fix funcionou. |

Resumo de uma linha: v.25 torna o claude-cli backend **oficial** (não fallback), mas exige um wizard interativo pós-install que a maioria dos guides não menciona. Sem ele, você fica em fallback dance com 30+s/turn.

---

## O que muda em v.25 (e por que importa)

### Fix #71957 — claude-cli routing via `agentRuntime.id`

A maior mudança. Em v.23, `claude-cli/` era um prefixo no `model.primary` que controlava o roteamento:

```json
// v.23
"model": { "primary": "claude-cli/claude-opus-4-6" }
```

Em v.25, o roteamento é via `agentRuntime.id` canonical. O prefixo `claude-cli/` foi removido — o provider é vinculado via registry:

```json
// v.25
"model": { "primary": "anthropic/claude-opus-4-6" },
"agentRuntime": { "id": "claude-cli" }
```

Se você tinha configs com `claude-cli/...`, v.25 pode renormalizar silenciosamente. Verifique os logs de boot após upgrade.

### Fix #70902 — OAuth credential sync

Melhoria no fluxo de refresh do `.credentials.json`. O CLI agora tenta sync graceful antes de truncar. **Mas não muda a regra de ouro**: `chattr +i` continua obrigatório. Ver "As 5 Surpresas" abaixo.

### Fix #71284 — Silent auth failures isolated

Melhora isolamento de 401s silenciosos. Em v.23, tokens divergentes podiam fazer `claude auth status` reportar `loggedIn:true` enquanto chamadas reais falhavam. v.25 expõe melhor esse estado. Ainda assim, o token audit em Phase 0 é obrigatório.

### Cold persisted plugin registry (Fix #72042)

Plugins disabled agora são persistidos em cold storage. Um `npm install -g openclaw` não volta os 100+ plugins para on. Em v.23, qualquer install global resetava a lista — você tinha que re-disable manualmente.

Resultado prático: fomos de 54 plugins carregados para 12 (só o necessário), e sobreviveu ao install.

### `OPENCLAW_SERVICE_REPAIR_POLICY=external`

Nova variável de ambiente. Com ela, o `doctor` não tenta auto-repair wrappers customizados (como o `openclaw-gateway-wrapper` imutável do Issue #62028). Essencial se você usa `chattr +i` em executáveis customizados. Adicionar no drop-in do systemd **antes** do upgrade.

---

## Pré-requisitos (CHECK ANTES DE COMEÇAR)

- [ ] Acesso SSH confirmado: `ssh root@100.87.8.44` (Tailscale) ou `root@187.77.234.79` (público)
- [ ] Janela de 2-3h sem interrupção (Phase 1-5 derruba os 3 serviços)
- [ ] Espaço em disco: mínimo 2GB livre em `/root` e `/var`
  ```bash
  ssh root@100.87.8.44 'df -h /root /var'
  ```
- [ ] `claude auth status` retornando `loggedIn:true` agora (não resolva isso durante o upgrade)
- [ ] `chattr +i` ativo em `/root/.claude/.credentials.json` (aplicar se ausente, monitorar 24h antes de upgrade)
- [ ] `/root/reapply-monkey-patch.sh` existente e testado
- [ ] Scripts de cron sem `vectorize --limit` (flag removido em v.25 — ver Surpresa 5)
- [ ] Gemini billing cap não esgotado (diagnosticar latency com Gemini falhando é confuso)

```bash
# Checagem rápida de pré-requisitos
ssh root@100.87.8.44 'openclaw --version && \
  claude auth status 2>&1 | grep -E "loggedIn|Logged" && \
  lsattr /root/.claude/.credentials.json && \
  df -h /root | tail -1 && \
  ls /root/reapply-monkey-patch.sh'
```

---

## As 5 Surpresas que Vão Custar Tempo se Você Não Souber

Cada uma custou ~30min em produção.

---

### Surpresa 1 — Token Anthropic divergente em até 5 lugares

**Root cause:** A maioria dos pre-flight audits verifica se o campo `apiKey` existe nos auth-profiles. Isso é insuficiente. Em produção, encontramos 3 tokens distintos rodando simultaneamente — e `claude auth status` retornava `loggedIn:true` para todos (porque verifica a env var, não o credentials.json em uso real pelo subprocess).

**A regra 13 violada silenciosamente:** `claude auth status` usa a env var pra reportar status. Se a env var diverge do `.credentials.json`, você vê `loggedIn:true` mas subprocess calls reais falham com HTTP 401.

Os 5 lugares onde um token Anthropic pode estar, potencialmente divergente:

| # | Lugar | Como verificar os primeiros 20 chars |
|---|---|---|
| 1 | `~/.claude/.credentials.json` | `jq -r '.claudeAiOauth.accessToken[0:20]' ~/.claude/.credentials.json` |
| 2 | Env var `ANTHROPIC_MAX_API_KEY` | `grep ANTHROPIC_MAX_API_KEY /root/.openclaw/.env \| cut -d= -f2 \| head -c 20` |
| 3 | `auth-profiles.json` → `anthropic-max:default.apiKey` | `jq -r '.profiles["anthropic-max:default"].apiKey[0:20]' /root/.openclaw/agents/nox/agent/auth-profiles.json` |
| 4 | `auth-profiles.json` → `anthropic:default.token` | `jq -r '.profiles["anthropic:default"].token[0:20]' /root/.openclaw/agents/nox/agent/auth-profiles.json` |
| 5 | `auth-profiles.json` → `anthropic:claude-cli.token` | `jq -r '.profiles["anthropic:claude-cli"].token[0:20]' /root/.openclaw/agents/main/agent/auth-profiles.json` |

**Ação correta:** HTTP test no token real. Cinco minutos que evitam 2h de troubleshooting em Phase 4.

```bash
# Interpretação: 200=válido, 429=válido+rate-limited, 401=REVOGADO (pare aqui)
REAL_TOKEN=$(ssh root@100.87.8.44 'jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json')
HTTP_CODE=$(curl -sw "%{http_code}" -o /dev/null -X POST \
  https://api.anthropic.com/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: $REAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-opus-4-5","max_tokens":5,"messages":[{"role":"user","content":"hi"}]}')
echo "API HTTP test: $HTTP_CODE"
```

---

### Surpresa 2 — Nunca remova `chattr +i` preventivamente

**Root cause:** "v.25 tem Fix #70902 que melhora OAuth sync. Vou remover `chattr +i` preventivamente pra não conflitar." Parece razoável. É errado.

O claude CLI subprocess, quando spawned sem TTY em condições de erro (comum durante installs e restarts), faz "self-fix" zerando `.credentials.json` para 0 bytes — documentado em rule 12.

Em produção: removemos `chattr -i` em Phase 0. Em Phase 4 (~8h depois), `claude auth status` retornou `loggedIn:false`. Phase 4 quebrou com:
```
FailoverError: Not logged in · Please run /login
```

**Ação correta:** O Fix #70902 escreve em refresh REAL (raro). Se falhar por chattr, é warn — não fatal. A proteção contra self-truncation (rule 12) vale mais que a conveniência. Se a nova versão reclamar de não conseguir escrever credentials, avalie case-by-case depois do upgrade.

```bash
# Verificar — deve conter -i-
ssh root@100.87.8.44 'lsattr /root/.claude/.credentials.json'
# Se ausente: chattr +i /root/.claude/.credentials.json
```

---

### Surpresa 3 — O wizard `openclaw config` é a peça canonical (não o `doctor`)

**Root cause:** Plano original tinha `doctor --fix` em Phase 3. `doctor --fix` é diagnostic com fixes pontuais. Ele **não adiciona** provider entries novas no config registry.

Sem a entrada `anthropic:claude-cli` no registry, o claude-cli só pega via fallback dance — FailoverError → retry → pega o segundo da fila. Result: Phase 4 "funcionava" mas com latency 30+s por turn.

**O que o wizard faz que `doctor --fix` não faz:**
1. Adiciona provider entry `anthropic:claude-cli` no config registry (binding explícito)
2. Registra modelos novos: `claude-opus-4-7`, `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
3. Atualiza `lastRunVersion` para 2026.4.25 (forçando registry refresh)

**Após wizard:** latency p50 caiu de 33s para 12s.

**Ação correta:** `openclaw config` (sem subcommand = guided wizard) é **obrigatório** em Phase 3. Roda sempre antes de declarar Phase 3 completa. `doctor` é diagnostic-only, não substituto.

---

### Surpresa 4 — Bedrock vem em DUAS variantes em v.25

v.24 tinha `amazon-bedrock`. v.25 adicionou silenciosamente `amazon-bedrock-mantle` (variante OpenAI-compatible). Se você só disabilitar `amazon-bedrock`, o mantle fica ativo.

Adicionalmente: `openclaw plugins list` (tabela) trunca IDs em 8 chars. `amazon-bedrock-mantle` aparece como `amazon-b`. Use sempre `--json` pra IDs completos.

**Ação correta:**
```bash
ssh root@100.87.8.44 'openclaw plugins list --json | \
  jq ".[] | select(.id | startswith(\"amazon\")) | {id, enabled}"'
# Disable ambos:
ssh root@100.87.8.44 'openclaw plugins disable amazon-bedrock && \
  openclaw plugins disable amazon-bedrock-mantle'
```

---

### Surpresa 5 — `vectorize --limit` foi removido em v.25

Scripts antigos com `nox-mem vectorize --limit N` quebram silenciosamente. O comportamento padrão do vectorize agora é idempotente (só re-vectoriza chunks sem embedding).

**Migração:**
```bash
# v.23 — QUEBRA em v.25
nox-mem vectorize --limit 500

# v.25 — correto
nox-mem vectorize          # idempotente, só chunks sem embedding
nox-mem vectorize --force  # re-vectoriza tudo
```

Atualize todos os scripts e crons antes do upgrade.

---

## ROTEIRO COMPLETO (copy-paste safe)

> Todos os comandos assumem execução da sua máquina local via SSH. Adapte se já estiver na VPS.

---

### Phase 0 — Pre-flight (zero risco, pode rodar antes da janela)

Phase 0 não derruba serviços. Pode ser feita dias antes.

#### 0.A — Backup completo

```bash
# Substitua <NEW> pela versão alvo: 2026.4.25
NEW="2026.4.25"
DATE=$(date +%Y%m%d-%H%M)

ssh root@100.87.8.44 "tar czf /var/backups/preupgrade-v${NEW}-${DATE}.tar.gz \
  /root/.openclaw/openclaw.json \
  /root/.openclaw/agents/*/agent/auth-profiles.json \
  /root/.openclaw/agents/*/sessions/sessions.json \
  /etc/systemd/system/openclaw-gateway.service.d/ \
  /usr/local/bin/openclaw-gateway-wrapper \
  /usr/bin/node \
  /root/.claude/.credentials.json"

# Snapshot DB (VACUUM INTO = consistente, não hot-copy)
ssh root@100.87.8.44 "sqlite3 /root/.openclaw/workspace/tools/nox-mem/data/nox-mem.db \
  \"VACUUM INTO '/var/backups/nox-mem-pre-v${NEW}-${DATE}.db';\""

# Capturar hash atual do monkey-patch
ssh root@100.87.8.44 'ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js' \
  > /tmp/preupgrade-monkey-patch-path.txt

# Dump estado de plugins + config + health baseline
ssh root@100.87.8.44 'openclaw plugins list --json' > /var/backups/preupgrade-v${NEW}-plugins.json 2>/dev/null
ssh root@100.87.8.44 'openclaw config dump' > /var/backups/preupgrade-v${NEW}-config.json 2>/dev/null
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{status,chunks:.chunks.total,embedded:.vectorCoverage.embedded,total:.vectorCoverage.total,compiled:.sectionDistribution.compiled,neverDecay:.retention.never_decay,dbSizeMB}"' \
  > /var/backups/health-pre-v${NEW}.json

echo "Backups criados:"
ssh root@100.87.8.44 "ls -lh /var/backups/preupgrade-v${NEW}* /var/backups/nox-mem-pre-v${NEW}*"
```

#### 0.B — Token audit completo (valores, não só presença)

> AVISO baseado em incident real: Phase 0 do upgrade real verificou presença de `apiKey` nos profiles e marcou como OK. Não checou os VALORES. Resultado: 3 tokens distintos, 2 revogados, descobertos só na Phase 4 após 2h de troubleshooting.

```bash
# Pegar primeiros 20 chars de cada lugar (devem ser idênticos)
ssh root@100.87.8.44 'echo "=== Token Audit (primeiros 20 chars) ===" && \
  echo "1. credentials.json:    $(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json | head -c 20)" && \
  echo "2. ANTHROPIC_MAX_API_KEY: $(grep "^ANTHROPIC_MAX_API_KEY" /root/.openclaw/.env | cut -d= -f2 | head -c 20)" && \
  echo "3. auth-profile nox:    $(jq -r ".profiles[\"anthropic-max:default\"].apiKey" /root/.openclaw/agents/nox/agent/auth-profiles.json 2>/dev/null | head -c 20)"'

# HTTP test no token do credentials.json (fonte da verdade para subprocesso claude)
ssh root@100.87.8.44 'T=$(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json); \
  R=$(curl -sw "%{http_code}" -o /dev/null -X POST https://api.anthropic.com/v1/messages \
    -H "anthropic-version: 2023-06-01" \
    -H "x-api-key: $T" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"claude-opus-4-5\",\"max_tokens\":5,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" 2>/dev/null); \
  echo "credentials.json HTTP test: $R  (200=OK, 429=OK rate-limited, 401=REVOGADO — pare aqui)"'
```

Se tokens divergirem: sincronize TODOS para o token do `credentials.json` via `openclaw config set` antes de continuar.
Se HTTP 401: rotacione o token antes do upgrade (ver RB-05).

#### 0.C — Validar `chattr +i` e `claude auth status`

```bash
ssh root@100.87.8.44 'claude auth status 2>&1'
# Esperado: "Logged in" com email

ssh root@100.87.8.44 'lsattr /root/.claude/.credentials.json'
# Esperado: ----i--- (bit i presente)

# Se NÃO imutável: imutabilizar AGORA
# ssh root@100.87.8.44 'chattr +i /root/.claude/.credentials.json'

# CRITICO: NÃO remover chattr +i antes do upgrade (ver Surpresa 2)
```

#### 0.D — Verificar e adicionar `OPENCLAW_SERVICE_REPAIR_POLICY=external`

```bash
ssh root@100.87.8.44 'cat /etc/systemd/system/openclaw-gateway.service.d/override.conf'
# Deve conter AMBAS as linhas:
# Environment=IS_SANDBOX=1
# Environment=OPENCLAW_SERVICE_REPAIR_POLICY=external

# Se REPAIR_POLICY estiver ausente, adicionar:
ssh root@100.87.8.44 'echo "Environment=OPENCLAW_SERVICE_REPAIR_POLICY=external" >> \
  /etc/systemd/system/openclaw-gateway.service.d/override.conf && \
  systemctl daemon-reload && \
  echo "Drop-in atualizado"'
```

#### 0.E — Verificar 12 invariantes I1-I12

> Tabela completa em Apêndice B. Checar pelo menos I1, I4, I5, I6, I7, I12 antes de prosseguir.

```bash
# I1 — model.primary aponta para claude
ssh root@100.87.8.44 'openclaw config get agents.defaults.model.primary'
# Esperado: contém "claude-" e "opus" ou "sonnet"

# I4 — Monkey-patch ativo (corpo da função, não grep -c)
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A8 "cleanStaleGatewayProcessesSync" | head -10'
# Esperado: marker comment + primeira linha do corpo = "return [];"

# I5 — Wrapper imutável
ssh root@100.87.8.44 'lsattr /usr/local/bin/openclaw-gateway-wrapper'
# Esperado: ----i---

# I6 — IS_SANDBOX drop-in
ssh root@100.87.8.44 'grep "IS_SANDBOX=1" /etc/systemd/system/openclaw-gateway.service.d/override.conf'

# I7 — CLAUDE_CODE_OAUTH_TOKEN ausente ou comentado
ssh root@100.87.8.44 'grep "CLAUDE_CODE_OAUTH_TOKEN" /root/.openclaw/.env'
# Deve começar com #DISABLED_ ou estar ausente

# I12 — Node.js wrapper
ssh root@100.87.8.44 'head -3 /usr/bin/node'
# Esperado: bash shebang + exec /usr/bin/node.bin --no-warnings
```

#### 0.F — Pre-stage tarball (inspeção sem instalar)

```bash
# Confirmar que v.25 existe no registry
ssh root@100.87.8.44 'npm view openclaw@2026.4.25 version 2>/dev/null'
# Esperado: 2026.4.25

# Baixar tarball para inspeção (não instala ainda)
ssh root@100.87.8.44 'mkdir -p /var/cache/openclaw-v25 && \
  npm pack openclaw@2026.4.25 --pack-destination /var/cache/openclaw-v25/ 2>&1 | tail -3'

# Verificar se cleanStaleGatewayProcessesSync ainda existe (patchable?)
ssh root@100.87.8.44 'tar xOf /var/cache/openclaw-v25/openclaw-*.tgz \
  $(tar tzf /var/cache/openclaw-v25/openclaw-*.tgz | grep restart-stale-pids) | \
  grep -A10 "cleanStaleGatewayProcessesSync" | head -12'
# Se função não existe: PARAR, ver seção "Quando NÃO fazer este upgrade"
```

#### 0.G — Atualizar scripts com `vectorize --limit`

```bash
ssh root@100.87.8.44 'grep -r "vectorize --limit" /root/.openclaw/scripts/ 2>/dev/null'
# Se encontrar: atualizar ANTES de continuar (ver Surpresa 5)
```

#### 0.H — Verificar sessions (atenção ao contexto heartbeat)

> AVISO: Filtrar sessions gemini-flash-lite indiscriminadamente é erro comum. Heartbeat sessions com gemini são DESIGN (ver Pitfall 9). Filtrar só sessions :main após mensagem conversacional do usuário.

```bash
ssh root@100.87.8.44 'for a in nox atlas boris cipher forge lex; do
  MODEL=$(jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null)
  echo "$a main-lane: $MODEL"
done'
# claude-* ou empty = OK
# gemini-flash-lite após heartbeat = OK (design)
# gemini-flash-lite após user msg conversacional = STUCK (resetar esse agent específico)
```

**Gate Phase 0:** Backups criados, tokens validados por HTTP test (200/429), `claude auth status` = Logged in, `chattr +i` ativo, REPAIR_POLICY no drop-in. Aprovação antes de Phase 1.

---

### Phase 1 — Install Pinned (5-10min)

> Serviços param aqui. Janela de manutenção começa.

```bash
# Passo 1: Stop em ORDEM REVERSA de dependência (nunca paralelo)
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher'
ssh root@100.87.8.44 'systemctl stop nox-mem-api'
ssh root@100.87.8.44 'systemctl stop openclaw-gateway'

# Passo 2: Confirmar todos parados
ssh root@100.87.8.44 'ps -ef | grep -E "openclaw|nox-mem" | grep -v grep'
# Esperado: output vazio (ou só grep em si)

# Passo 3: Install PINNED — nunca sem versão explícita
ssh root@100.87.8.44 'npm install -g openclaw@2026.4.25 2>&1 | tail -5'

# Passo 4: Validar versão exata
ssh root@100.87.8.44 'openclaw --version'
# Esperado: exatamente 2026.4.25

# Passo 5: Capturar novo hash do arquivo monkey-patchado (muda a cada versão)
ssh root@100.87.8.44 'ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js'
# Hash v.25 confirmado em produção: CSJWMprl (era CegQx-K9 em v.23)
# Registrar o seu aqui: ________________
```

**Gate Phase 1:** `openclaw --version` == `2026.4.25` exato. Novo arquivo `restart-stale-pids-*.js` localizado.

---

### Phase 2 — Reapply Customizations (10-15min)

> `npm install -g` reinstala `node_modules/dist/` — apaga todos os patches. Tudo aqui deve ser reaplicado.

#### 2.1 — Monkey-patch #62028

> AVISO baseado em incident real: hash mudou de `CegQx-K9` (v.23) para `CSJWMprl` (v.25), mas o glob `restart-stale-pids-*.js` continuou funcionando. A função `cleanStaleGatewayProcessesSync` ficou idêntica (linha 531, mesma signature). Regex do reapply-script casou primeira tentativa.

```bash
# Reaplicar (script é idempotente)
ssh root@100.87.8.44 'bash /root/reapply-monkey-patch.sh 2>&1'

# Validar via CORPO DA FUNÇÃO — nunca use grep -c (false positive conhecido)
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A8 "cleanStaleGatewayProcessesSync" | head -10'
# Esperado:
# 1. Marker comment "MONKEY_PATCH_62028" (ou similar)
# 2. PRIMEIRA linha do corpo = "return [];"

# Validar marker explicitamente
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep "MONKEY_PATCH_62028"'
# Se ausente: regex do script não casou — parar, mostrar diff, ajustar manualmente
```

#### 2.2 — Verificar wrapper e credentials ainda imutáveis

```bash
ssh root@100.87.8.44 'lsattr /usr/local/bin/openclaw-gateway-wrapper /root/.claude/.credentials.json'
# Esperado: ----i--- em AMBOS
# Se credentials perdeu o bit (npm install pode ter tocado): reimutabilizar
# ssh root@100.87.8.44 'chattr +i /root/.claude/.credentials.json'
```

#### 2.3 — Graph-memory log patch

```bash
# Verificar se backup do log patch existe (patch é local, perde com reinstall do plugin)
ssh root@100.87.8.44 'ls /root/.openclaw/extensions/graph-memory/index.ts.bak-log-fix-* 2>/dev/null'
# Se backup existe e log patch foi perdido: reaplicar do bak
```

#### 2.4 — Systemd daemon reload

```bash
ssh root@100.87.8.44 'systemctl daemon-reload'
```

#### 2.5 — Node.js wrapper intacto?

```bash
ssh root@100.87.8.44 'head -3 /usr/bin/node'
# Esperado: #!/bin/bash + exec /usr/bin/node.bin --no-warnings "$@"
# Se apt upgrade nodejs rodou entre upgrades: recriar wrapper (renomear binary para node.bin)
```

**Gate Phase 2:** Monkey-patch validado (body + marker), credentials imutável, wrapper imutável, daemon reloaded.

---

### Phase 3 — Schema Migration + Wizard (20-30min)

#### 3.1 — Backup imediato pré-doctor

```bash
ssh root@100.87.8.44 'cp /root/.openclaw/openclaw.json /var/backups/openclaw-pre-doctor-v25.json'
```

#### 3.2 — Doctor diagnostic (não-destrutivo)

```bash
# --non-interactive: informa problemas sem alterar nada
ssh root@100.87.8.44 'OPENCLAW_SERVICE_REPAIR_POLICY=external openclaw doctor --non-interactive 2>&1 | \
  tee /var/backups/doctor-check-v25.log'

# LEITURA CUIDADOSA:
# OK para ignorar: "anthropic:claude-cli (provider claude-cli)" — doctor reporta INTENÇÃO, não estado real
# OK para ignorar: probe errors de graph-memory — stale por 8h (Pitfall 5)
# ABORT se mencionar: stripping agents.defaults, removing model.primary, channels.discord
```

#### 3.3 — Disable bedrock AMBAS variantes

```bash
ssh root@100.87.8.44 'openclaw plugins disable amazon-bedrock && \
  openclaw plugins disable amazon-bedrock-mantle'

# Verificar com --json (tabela trunca IDs em 8 chars)
ssh root@100.87.8.44 'openclaw plugins list --json | \
  jq ".[] | select(.id | startswith(\"amazon\")) | {id, enabled}"'
# Ambos devem ter "enabled": false
```

#### 3.4 — Wizard `openclaw config` (OBRIGATÓRIO — não pular)

> AVISO baseado em incident real: pulamos o wizard em Phase 3 por medo de stripping de config. Resultado: 1h a mais de fallback dance com latency 33s. O wizard é a única ferramenta que adiciona o registry entry `anthropic:claude-cli`. Doctor não faz isso.

```bash
ssh root@100.87.8.44 'openclaw config'
# Wizard interativo. Seguir:
# - "Upgrade migration detected?" → YES
# - "Add claude-cli as primary auth provider?" → YES
# - "Register new model catalog?" → YES (ou Enter pra default)
# - "Preserve plugin state?" → YES
# NÃO aceitar mudanças que toquem em agents.defaults.model.primary
```

#### 3.5 — Verificar resultado do wizard

```bash
# Diff de config (deve ter só adições esperadas)
ssh root@100.87.8.44 'diff /var/backups/openclaw-pre-doctor-v25.json /root/.openclaw/openclaw.json | head -60'
# Verde (adições esperadas): agentRuntime.id, anthropic:claude-cli provider, model catalog entries
# ABORT + restore se: agents.defaults.model.primary mudou, fallbacks foi limpo, discord/telegram sumiu

# Verificar que anthropic:claude-cli está no registry
ssh root@100.87.8.44 'jq ".profiles[\"anthropic:claude-cli\"]" \
  /root/.openclaw/agents/nox/agent/auth-profiles.json'
# Esperado: { "mode": "token", "provider": "claude-cli" }

# Invariantes I1 e I3 ainda passando?
ssh root@100.87.8.44 'openclaw config get agents.defaults.model.primary'
ssh root@100.87.8.44 'openclaw config get agents.defaults.model.fallbacks'
```

Se o config diff mostrar mudanças indesejadas:
```bash
ssh root@100.87.8.44 'cp /var/backups/openclaw-pre-doctor-v25.json /root/.openclaw/openclaw.json'
# Depois rodar o wizard novamente recusando as mudanças problemáticas
```

**Gate Phase 3:** Schema migrado, wizard rodou, `anthropic:claude-cli` presente no registry, config diff só tem adições esperadas, I1+I3 passando.

---

### Phase 4 — Bring-up Sequencial (15-30min)

> Subir um de cada vez. Nunca todos em paralelo.

#### 4.1 — Gateway primeiro

```bash
ssh root@100.87.8.44 'systemctl start openclaw-gateway'

# Watch primeiros 60 segundos:
ssh root@100.87.8.44 'journalctl -fu openclaw-gateway --since "5s ago" 2>&1 | head -60'
```

**Checklist nos primeiros 60s:**

| O que observar | OK | PROBLEMA → ação |
|---|---|---|
| Tempo até "ready" | < 15s | > 30s → ver Forward-fix F5 |
| Versão reportada no log | == 2026.4.25 | Versão errada → abort |
| Restart counter | = 0 em 60s | > 0 → monkey-patch perdido (F6) |
| "401" ou "Not logged in" | Ausente | Presente → F1 ou F2 |
| "claude-cli" ou "agentRuntime: claude-cli" | Presente | Ausente → wizard Phase 3 (F5) |
| "harness not registered" | Ausente | Presente → rollback |
| Plugin count | ~12 | > 50 → registry reset |
| `IS_SANDBOX=1` respeitado | Sem block | "permission denied" → checar drop-in |

```bash
# Validar agentRuntime carregado
ssh root@100.87.8.44 'openclaw config get agentRuntime 2>/dev/null'
# Esperado: JSON com id="claude-cli"

# Checar restart counter
ssh root@100.87.8.44 'systemctl status openclaw-gateway --no-pager | grep -E "Active:|restart"'
```

#### 4.2 — nox-mem-api

```bash
ssh root@100.87.8.44 'systemctl start nox-mem-api && sleep 3 && \
  curl -s http://127.0.0.1:18802/api/health | jq .status'
# Esperado: "ok"
```

#### 4.3 — nox-mem-watcher

```bash
ssh root@100.87.8.44 'systemctl start nox-mem-watcher && sleep 2 && \
  systemctl is-active nox-mem-watcher'
# Esperado: "active"
```

**Gate Phase 4 inicial:** 3 serviços ativos, gateway ready < 15s, restart counter = 0.

---

### Phase 5 — Smoke Test 6 Agents (15-20min)

Enviar 1 mensagem trivial para cada agent na ordem: **nox → forge → atlas → boris → cipher → lex**

Para cada agent após resposta:

```bash
# Verificar que sessions.json gravou model claude-* (não fallback)
ssh root@100.87.8.44 'jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
  /root/.openclaw/agents/<AGENT>/sessions/sessions.json'
# Esperado: começa com "claude-"

# Verificar ausência de 401 no log
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "2 min ago" --no-pager | \
  grep -c "401" && echo "401 errors" || echo "0 auth errors"'
```

Se agent falhar: parar, investigar, fix forward. Não pular para o próximo.

---

### Phase 6 — Re-imutabilize + Token Sync Validation (5min)

```bash
# Confirmar chattr +i ainda ativo
ssh root@100.87.8.44 'lsattr /root/.claude/.credentials.json | grep -o "\-i-" && \
  echo "Imutavel: OK" || \
  (chattr +i /root/.claude/.credentials.json && echo "Re-imutabilizado")'

# Re-validar token consistency (rodar token audit completo do 0.B)
# Os 5 lugares devem mostrar os mesmos 20 chars
ssh root@100.87.8.44 'echo "1. creds: $(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json | head -c 20)" && \
  echo "2. env:   $(grep "^ANTHROPIC_MAX_API_KEY" /root/.openclaw/.env | cut -d= -f2 | head -c 20)" && \
  echo "3. prof:  $(jq -r ".profiles[\"anthropic-max:default\"].apiKey" /root/.openclaw/agents/nox/agent/auth-profiles.json 2>/dev/null | head -c 20)"'
```

---

### Phase 7 — Observação 30min

```bash
# Monitor a cada 5min durante 30min
ssh root@100.87.8.44 'for i in 1 2 3 4 5 6; do \
  echo "=== Check $i ===" && \
  systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher && \
  journalctl -u openclaw-gateway --since "5 min ago" --no-pager | grep -c "401" 2>/dev/null && \
  curl -s http://127.0.0.1:18802/api/health | jq "{status,embedded:.vectorCoverage.embedded,total:.vectorCoverage.total}" && \
  sleep 300; \
done'
```

**Checkpoints a cada 5min:**

| Métrica | Gate |
|---|---|
| `systemctl is-active` todos 3 | active |
| Restart counter gateway | 0 novos |
| Erros 401 em journalctl | 0 |
| `/api/health.status` | ok |
| Heartbeats no Discord (6 personas) | aparecendo normalmente |
| vectorCoverage | >= baseline pré-upgrade |

> Cron canary `*/30min`: se cair durante window de restart (xx:00 ou xx:30) é falso positivo — ignorar, aguardar próximo ciclo.

**Gate Phase 7:** 30min contínuos sem regressões. Upgrade concluído.

---

## Forward-fix Decision Tree

**Filosofia:** Forward-fix > rollback. Rollback real só se binário corrompido ou config irrecuperável. Quando Phase 4 quebrou em produção com credentials zerada e tokens divergentes, a abordagem correta foi diagnosticar e corrigir forward. Resultado: sistema saiu funcional **e** simplificado (3 tokens → 1, 22 profiles → 12).

---

### F1 — "Not logged in · Please run /login"

Diagnóstico: `credentials.json` foi truncado (chattr não estava ativo ou foi removido preventivamente).

```bash
ssh root@100.87.8.44 'wc -c /root/.claude/.credentials.json'
# < 100 bytes = truncado

# Fix: restaurar do backup pré-upgrade
ssh root@100.87.8.44 'chattr -i /root/.claude/.credentials.json && \
  cp /root/.claude/.credentials.json.pre-v25 /root/.claude/.credentials.json && \
  chattr +i /root/.claude/.credentials.json && \
  claude auth status 2>&1'
# Esperado: "Logged in"

ssh root@100.87.8.44 'systemctl restart openclaw-gateway'
```

### F2 — HTTP 401 silencioso (agent responde mas via fallback caro)

Diagnóstico: tokens divergentes em múltiplos lugares.

```bash
# Validar os 5 locais (primeiros 20 chars devem ser idênticos)
ssh root@100.87.8.44 'echo "1: $(jq -r ".claudeAiOauth.accessToken[0:20]" /root/.claude/.credentials.json)" && \
  echo "2: $(grep ANTHROPIC_MAX_API_KEY /root/.openclaw/.env | cut -d= -f2 | head -c 20)" && \
  echo "3: $(jq -r ".profiles[\"anthropic-max:default\"].apiKey" /root/.openclaw/agents/nox/agent/auth-profiles.json | head -c 20)" && \
  echo "4: $(jq -r ".profiles[\"anthropic:default\"].token" /root/.openclaw/agents/nox/agent/auth-profiles.json | head -c 20)" && \
  echo "5: $(jq -r ".profiles[\"anthropic:claude-cli\"].token" /root/.openclaw/agents/main/agent/auth-profiles.json 2>/dev/null | head -c 20)"'

# Token canônico é o que está em credentials.json
# Sincronizar os demais via: openclaw config set <path> <value>
```

### F3 — FailoverError: rate limit (Gemini billing esgotado)

```bash
# Não é problema do upgrade — é quota Gemini
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a && \
  nox-mem vectorize 2>&1 | tail -3'
# Se "0 embedded, N errors": chave Gemini expirou ou quota esgotou
# Fix: atualizar GEMINI_API_KEY em .env + systemctl restart nox-mem-api nox-mem-watcher
```

### F4 — Sessions de agents grudadas em gemini/codex

```bash
# Distinguir heartbeat session (design) de user session (bug)
ssh root@100.87.8.44 'for a in nox atlas boris cipher forge lex; do
  jq "to_entries | map({k:.key, model:.value.model, lane:.value.lane}) | .[]" \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null
done'
# lane == ":heartbeat" com gemini → DESIGN, não filtrar
# lane == ":main" com gemini após user message → STUCK
# Fix só o agent stuck:
# ssh root@100.87.8.44 'echo "{}" > /root/.openclaw/agents/<AGENT>/sessions/sessions.json'
```

### F5 — Latency p50 > 20s após upgrade

```bash
# Causa provável: fallback dance ativo
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "10 min ago" --no-pager | \
  grep -i "fallback\|failover\|FailoverError" | tail -20'

# Se FailoverErrors presentes:
# 1. Wizard foi rodado (Phase 3.4)? anthropic:claude-cli provider no config?
# 2. credentials.json íntegro (0.C)?
# 3. agentRuntime.id = "claude-cli": openclaw config get agentRuntime
# 4. Se tudo OK: resetar sessions + restart gateway

# IMPORTANTE: Medir latência APENAS após todos os fixes completos
# Métricas de transição (Gemini falhando, tokens divergentes) são ruído
```

### F6 — Gateway restarta em loop (> 3x em 5min)

```bash
# Monkey-patch #62028 perdido
cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A5 "cleanStaleGatewayProcessesSync" | head -7

# Fix emergencial:
ssh root@100.87.8.44 'mkdir -p /etc/systemd/system/openclaw-gateway.service.d/ && \
  echo -e "[Service]\nRestart=no" > \
  /etc/systemd/system/openclaw-gateway.service.d/no-restart.conf && \
  systemctl daemon-reload && \
  pkill -9 -f openclaw-gateway && \
  bash /root/reapply-monkey-patch.sh && \
  rm /etc/systemd/system/openclaw-gateway.service.d/no-restart.conf && \
  systemctl daemon-reload && \
  systemctl start openclaw-gateway'
```

### F7 — `agents.defaults.model.primary` mudou após wizard

```bash
# Restaurar valor correto
ssh root@100.87.8.44 'openclaw config set agents.defaults.model.primary "<VALOR_ORIGINAL>" && \
  openclaw config validate'

# Se validate falha: restaurar do backup
ssh root@100.87.8.44 'cp /var/backups/openclaw-pre-doctor-v25.json /root/.openclaw/openclaw.json && \
  systemctl restart openclaw-gateway'
```

---

## 10 Pegadinhas Específicas v.25

### 1. `claude-cli/` prefix removido em model.primary

v.23 usava `"claude-cli/claude-opus-4-6"`, v.25 usa `"anthropic/claude-opus-4-6"` com roteamento via `agentRuntime.id`. Config com `claude-cli/` pode ser renormalizado silenciosamente — verificar via `openclaw config get agents.defaults.model.primary` pós-wizard.

### 2. Provider entry `anthropic:claude-cli` é load-bearing em v.25

Em v.23 era implícito pelo prefixo. Em v.25 precisa estar **explícito** em `auth-profiles.json`. Sem ele, claude-cli só pega via FailoverError (fallback dance, latency ~30s). Wizard adiciona. `doctor --fix` não adiciona.

```json
"anthropic:claude-cli": {
  "mode": "token",
  "provider": "claude-cli"
}
```

### 3. Bedrock em duas variantes (`amazon-bedrock` + `amazon-bedrock-mantle`)

Disable AMBOS ou o mantle fica ativo e aumenta boot time + polui health logs.

### 4. `vectorize --limit` removido — scripts antigos quebram silenciosamente

Usar `nox-mem vectorize` (idempotente) ou `nox-mem vectorize --force` (tudo).

### 5. `doctor` reporta `anthropic:claude-cli` mesmo se não houver no config

Reporta a INTENÇÃO baseada em `agentRuntime.id`, não o estado real. Validar via `jq '.profiles' auth-profiles.json` direto.

### 6. `openclaw plugins list` trunca IDs em 8 chars

`amazon-bedrock-mantle` → `amazon-b` na tabela. Usar `--json` pra IDs completos.

### 7. graph-memory probe errors são stale por 8h

Probe roda em processo separado e cacheia. Mesmo com Gemini key válida, probe error persiste nos logs. Não é fonte de verdade — validar via `nox-mem vectorize` real ou `/api/health`.

### 8. Cron canary `*/30min` cai em windows de restart

Falso positivo se gateway restartou exatamente em xx:00 ou xx:30. Ignorar, recupera no próximo ciclo.

### 9. Heartbeat sessions com gemini-flash-lite são DESIGN

`agents.defaults.heartbeat.model: "gemini/gemini-2.5-flash-lite"` é custo intencional. Sessions `:heartbeat` com gemini = normal. Filtrar pensando que estão "stuck" causa confusão (voltam em < 30min via cron).

### 10. 4 modelos novos no catálogo

Wizard adiciona: `claude-opus-4-7`, `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`. Zero pay-per-token quando Max plan cobre. Atualizar configs de roteamento por agent se quiser usar.

---

## Checklist de Validação Pós-Upgrade

```bash
# Script de validação automática
echo "=== Validação pós-upgrade v.25 ===" && \
VER=$(ssh root@100.87.8.44 'openclaw --version') && \
[[ "$VER" == "2026.4.25" ]] && echo "OK Versao: $VER" || echo "FAIL Versao: $VER"

ssh root@100.87.8.44 '
# 1. agentRuntime.id
RUNTIME=$(openclaw config get agentRuntime.id 2>/dev/null)
[[ "$RUNTIME" == "claude-cli" ]] && echo "OK agentRuntime.id: claude-cli" || echo "FAIL agentRuntime.id: $RUNTIME"

# 2. Provider anthropic:claude-cli
PROVIDER=$(jq -r ".profiles[\"anthropic:claude-cli\"].provider // \"MISSING\"" \
  /root/.openclaw/agents/nox/agent/auth-profiles.json 2>/dev/null)
[[ "$PROVIDER" == "claude-cli" ]] && echo "OK anthropic:claude-cli provider" || echo "FAIL Provider: $PROVIDER"

# 3. Monkey-patch marker
PATCH_FILE=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js)
grep -q "MONKEY_PATCH_62028" $PATCH_FILE && \
  echo "OK Monkey-patch #62028 marker" || echo "FAIL Monkey-patch ausente"

# 4. credentials.json imutavel
lsattr /root/.claude/.credentials.json | grep -q "\-i-" && \
  echo "OK credentials.json imutavel" || echo "FAIL credentials.json NAO imutavel"

# 5. 3 servicos ativos
systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher | \
  paste - - - | grep -q "active	active	active" && \
  echo "OK 3 servicos ativos" || echo "FAIL algum servico inativo"

# 6. VectorCoverage
set -a; source /root/.openclaw/.env; set +a
COVERAGE=$(curl -s http://127.0.0.1:${NOX_API_PORT}/api/health | \
  jq -r ".vectorCoverage | \"\(.embedded)/\(.total)\"")
echo "INFO VectorCoverage: $COVERAGE"

# 7. Bedrock disabled
BEDROCK=$(openclaw plugins list --json | \
  jq "[.[] | select(.id | startswith(\"amazon\")) | .enabled] | any")
[[ "$BEDROCK" == "false" ]] && echo "OK Bedrock disabled" || echo "FAIL Bedrock ativo"

# 8. credentials.json nao truncado
SIZE=$(wc -c < /root/.claude/.credentials.json)
[[ $SIZE -gt 200 ]] && echo "OK credentials.json size: ${SIZE}b" || echo "FAIL credentials.json truncado: ${SIZE}b"
'
```

Itens adicionais (observação manual nos logs):

- [ ] `[agent/cli-backend]` aparece nos logs durante turns
- [ ] `/usr/bin/claude` subprocess spawning: `ps -ef | grep claude` durante turn ativo
- [ ] Zero `FailoverError` em janela de 5min de uso normal
- [ ] Latency p50 < 15s (medir com `time` em alguns turns manuais)
- [ ] Cron canary `*/30min` verde na próxima janela (pode estar RED se restart coincidir — aguardar 1h)

---

## Métricas Reais Antes/Depois (produção 2026-04-27)

| Métrica | v.23 baseline | v.25 final |
|---|---|---|
| Plugins carregados | 54/101 | 12/113 (39 disabled por nós) |
| Boot time | ~10s | 11.4s |
| **Latency p50** | ~15s (com fallback esporádico) | **12s (primary direto)** |
| Latency p99 | ~40s | ~25s |
| FailoverErrors / 5min | ~10 | **0** |
| claude-cli routing path | fallback dance | **primary direct** |
| Pay-per-token | zero | zero |
| Token consistency | 3 tokens divergentes | 1 token sincronizado |
| credentials.json imutável | sim | sim |
| Monkey-patch #62028 | ativo (hash CegQx-K9) | ativo (hash CSJWMprl) |
| Auth profiles (6 agents) | 22 profiles (inconsistente) | 12 profiles (6 x 2) |

A melhoria real de latência foi de 33s (pico durante troubleshooting) para 12s estável. O baseline v.23 era ~15s por causa de fallback esporádico.

---

## Quando NÃO Fazer Este Upgrade

Aguarde se:

| Condição | Por que |
|---|---|
| Sistema 24/7 sem janela de 2-3h disponível | Phase 4 pode precisar de troubleshooting ativo; Phase 1-4 derruba serviços |
| `claude auth status` retorna `loggedIn:false` agora | Resolva antes — o upgrade não vai consertar isso |
| `.credentials.json` nunca teve `chattr +i` | Aplique o chattr e monitore 24h antes de upgrade |
| Gemini billing cap esgotado | Rotacione a key antes — diagnosticar latency com Gemini falhando é confuso |
| Scripts de cron com `vectorize --limit` não atualizados | Atualize antes — quebra silenciosamente |
| Você está a < 24h do release da versão alvo | Aguardar comunidade reportar regressões críticas |

---

## Quando ABORTAR Mid-Upgrade (Rollback Real)

**Rollback é caro** (perde wizard config, registry, migrations). Forward-fix resolve 95% dos casos.

| Condição | Rollback? |
|---|---|
| Gateway não sobe + `ERR_MODULE_NOT_FOUND` + `ls dist/` confirma arquivo deletado | SIM |
| `openclaw.json` corrompido além de restauração de backup | SIM |
| Fratricide loop persiste depois de monkey-patch reaplicado + cache limpo | SIM |
| Credentials restaurado mas `claude auth status` ainda falha após 3 tentativas + `claude setup-token` novo | SIM |
| Latência alta ou fallback dance | NÃO — forward-fix F5 |
| Agent não responde | NÃO — forward-fix |
| Erros 401 | NÃO — forward-fix F2 (token sync) |
| Plugin não carrega | NÃO — forward-fix |

**Procedimento de rollback:**

```bash
# Opção 1: Script dedicado (preferido — inclui monkey-patch automático)
ssh root@100.87.8.44 'ls /root/rollback-*.sh'
ssh root@100.87.8.44 'bash /root/rollback-2026.4.23.sh'

# Opção 2: npm install versão anterior (só se sem rollback script)
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher nox-mem-api openclaw-gateway && \
  npm install -g openclaw@2026.4.23 && \
  bash /root/reapply-monkey-patch.sh && \
  cp /var/backups/openclaw-pre-doctor-v25.json /root/.openclaw/openclaw.json && \
  systemctl start openclaw-gateway nox-mem-api nox-mem-watcher && \
  openclaw --version'
# Esperado: 2026.4.23

# Após rollback: validar todos I1-I12 + smoke test 1 agent
```

---

## Lições para Futuros Upgrades (v.26+)

### L1 — Token audit = verificar VALORES, não presença

Verificar que o campo `apiKey` existe não é suficiente. O HTTP test (`curl -sw "%{http_code}"`) é obrigatório em Phase 0. Cinco minutos que evitam 2h de troubleshooting em Phase 4.

### L2 — Wizard é Phase 3, não opcional

Qualquer upgrade que mude o registry de providers requer o wizard interativo. `doctor` é diagnostic. Wizard é migration. São ferramentas diferentes com propósitos diferentes.

### L3 — Forward-fix > rollback

Rollback preserva o problema que levou ao upgrade. Forward-fix resolve o root cause. Quando Phase 4 quebrou com credentials zerada e tokens divergentes, diagnose + fix forward saiu com sistema funcional **e** simplificado.

### L4 — Não toggle imutabilidade preventivamente

`chattr +i` é uma defesa de última linha. Qualquer release que promete "melhorar o OAuth sync" ainda pode ter edge cases. Se o upgrade realmente exigir remover o chattr, você vai saber — o comando vai reclamar explicitamente.

### L5 — Medir performance DEPOIS de todos os fixes

Métricas durante troubleshooting (Gemini falhando, tokens divergentes, fallback dance ativo) são ruído. O número relevante é pós-estabilização completa. Bench intermediário gera ansiedade sem informação útil.

### L6 — Separar heartbeat sessions de user sessions ao diagnosticar stickiness

Antes de filtrar `sessions.json` por model, verificar se a session foi criada por heartbeat. Heartbeats com gemini são design. Filtrar indiscriminadamente causa confusão de diagnóstico — as sessions voltam em < 30min.

---

## Apêndice A — Os 5 Lugares do Token Anthropic (deep dive)

Explicação de por que cada lugar existe e qual o método de validação:

| # | Lugar | Quem usa | Formato esperado | Teste definitivo |
|---|---|---|---|---|
| 1 | `/root/.claude/.credentials.json` → `.claudeAiOauth.accessToken` | Subprocess `/usr/bin/claude` spawned pelo gateway | `sk-ant-oat...` longo (OAuth token) | HTTP 200/429 via curl direto |
| 2 | `ANTHROPIC_MAX_API_KEY` em `.env` | Código que usa a env var explicitamente | `sk-ant-...` | HTTP 200/429 via curl |
| 3 | `auth-profiles.json` → `anthropic-max:default.apiKey` | Gateway quando roteando via perfil max | Mesmo token do credentials.json | Comparar primeiros 20 chars com #1 |
| 4 | `auth-profiles.json` → `anthropic:default.token` | Fallback path genérico | Pode ser stale | Comparar com #1; se divergir, atualizar |
| 5 | `auth-profiles.json` → `anthropic:claude-cli.token` (main agent) | Path específico do cli-backend | Mesmo token | Comparar com #1 |

**Regras:**
- O token canônico é o que está em `credentials.json` — é o que o subprocess usa diretamente
- `claude auth status` verifica env var, não credentials.json — `loggedIn:true` não garante que o subprocess vai funcionar
- Todos os 5 lugares devem mostrar o mesmo token (primeiros 20+ chars idênticos)
- Validação real = HTTP test, não inspeção de campo

**Script de sync (se tokens divergirem):**
```bash
# Pegar token canônico do credentials.json
CANON_TOKEN=$(ssh root@100.87.8.44 'jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json')

# Atualizar env var no .env (se divergir)
ssh root@100.87.8.44 "sed -i 's/^ANTHROPIC_MAX_API_KEY=.*/ANTHROPIC_MAX_API_KEY=${CANON_TOKEN}/' /root/.openclaw/.env"

# Atualizar auth-profiles via openclaw config set (nunca jq+mv direto)
ssh root@100.87.8.44 "openclaw config set 'agents.nox.auth.anthropic-max:default.apiKey' '${CANON_TOKEN}'"
```

---

## Apêndice B — 12 Invariantes I1-I12

Estas invariantes NUNCA podem regredir. Validar antes e depois do upgrade.

| # | Invariante | Comando de validação | Esperado |
|---|---|---|---|
| I1 | `model.primary` aponta para claude | `openclaw config get agents.defaults.model.primary` | Contém `claude-` e `opus` ou `sonnet` |
| I2 | `cliBackends.claude-cli` NÃO existe | `openclaw config get agents.defaults.cliBackends 2>&1` | `null`, erro, ou ausente |
| I3 | Fallback chain SEM `anthropic/*` direto | `openclaw config get agents.defaults.model.fallbacks` | Contém `claude-cli/sonnet*`, `openai-codex/*`, `gemini/*` — sem `anthropic/claude-*` direto |
| I4 | Monkey-patch #62028 ativo | Ver comando abaixo | Marker comment + corpo retorna `[]` imediatamente |
| I5 | Wrapper imutável | `lsattr /usr/local/bin/openclaw-gateway-wrapper` | `----i---` |
| I6 | Drop-in `IS_SANDBOX=1` | `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf` | Linha `Environment=IS_SANDBOX=1` presente |
| I7 | `CLAUDE_CODE_OAUTH_TOKEN` ausente/comentado | `grep "CLAUDE_CODE_OAUTH_TOKEN" /root/.openclaw/.env` | Começa com `#DISABLED_` ou ausente |
| I8 | Bedrock ausente (ambas variantes) | `openclaw plugins list --json \| jq "[.[] \| select(.id \| test(\"bedrock\")) \| .enabled] \| any"` | `false` |
| I9 | 3 serviços nox-mem ativos | `systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher` | `active` em todos 3 |
| I10 | vectorCoverage >= 95% | `curl -s http://127.0.0.1:18802/api/health \| jq ".vectorCoverage"` | `embedded / total >= 0.95` |
| I11 | Sessions não grudadas em fallback não-claude | Ver comando abaixo | claude-* OU empty (gemini em heartbeat = OK) |
| I12 | Node.js wrapper ativo | `head -3 /usr/bin/node` | Bash shebang + `exec /usr/bin/node.bin --no-warnings` |

**Validação I4 completa (não usar grep -c — false positive conhecido):**
```bash
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A8 "cleanStaleGatewayProcessesSync" | head -10'
# Validar: marker comment presente + primeira linha do corpo = "return [];"
```

**Validação I11:**
```bash
ssh root@100.87.8.44 'for a in nox atlas boris cipher forge lex; do
  echo -n "$a: "
  jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null
done'
```

---

## Apêndice C — Os 7 Prompts dos Reconnaissance Agents

Dispatchar em **paralelo** antes de tocar prod. Cada um é independente. Retornam insights que economizam horas de surpresa em Phase 4.

### Agent 1 — VPS State Audit

```
Você é um auditor de infraestrutura. Conecte via SSH em root@100.87.8.44 e capture:

1. `openclaw --version` (versão atual)
2. `systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher`
3. `claude auth status 2>&1`
4. `lsattr /root/.claude/.credentials.json /usr/local/bin/openclaw-gateway-wrapper`
5. `wc -c /root/.claude/.credentials.json` (deve ser >200 bytes)
6. `ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` (captura hash atual)
7. `cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | grep -A5 "cleanStaleGatewayProcessesSync" | head -10` (valida patch body)
8. `grep -v "^#" /root/.openclaw/.env | grep -E "CLAUDE_CODE_OAUTH|ANTHROPIC_API_KEY|ANTHROPIC_BASE_URL"` (devem estar comentados/ausentes)
9. `curl -s http://127.0.0.1:18802/api/health | jq "{status,vectorCoverage,chunks}"`
10. `for a in main nox atlas boris cipher forge lex; do echo -n "$a: "; jq -r "to_entries[0].value.model // \"empty\"" /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null || echo "no file"; done`
11. `openclaw plugins list --json 2>/dev/null | jq "[.[] | {id,enabled,loaded}]"`
12. `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf`

Reportar: quais invariantes I1-I12 passam/falham, blockers que precisam ser resolvidos antes do upgrade.
```

### Agent 2 — Binary Diff Prediction

```
Você é um engenheiro de upgrade. Para openclaw@2026.4.25:

1. `npm view openclaw@2026.4.25 --json | jq "{version,dependencies,peerDependencies,dist}"`
2. `npm pack openclaw@2026.4.25 --pack-destination /tmp/openclaw-pack/ --dry-run 2>&1 | head -30`
3. Baixe o tarball: `npm pack openclaw@2026.4.25 --pack-destination /tmp/`
4. Liste arquivos relevantes: `tar tzf /tmp/openclaw-*.tgz | grep -E "restart-stale-pids|cliBackends|agentRuntime|plugins|harness|claude-cli" | head -30`
5. Inspecione o arquivo restart-stale-pids: `tar xOf /tmp/openclaw-*.tgz $(tar tzf /tmp/openclaw-*.tgz | grep restart-stale-pids) | head -40`
6. Verifique se cleanStaleGatewayProcessesSync ainda existe com mesma signature

Reportar: novo hash do arquivo restart-stale-pids, se função existe e é patchable, mudanças de schema esperadas.
```

### Agent 3 — Community Regression Scan

```
Você é um pesquisador de signals de comunidade. Pesquise:

1. GitHub issues do repositório openclaw abertas/fechadas nos últimos 3 dias com labels "bug", "regression"
2. Changelog/release notes de openclaw@2026.4.25 completo
3. Issues mencionando: "credentials", "auth", "claude-cli", "harness", "fratricide", "plugins", "schema"
4. Posts em Discord/forum da comunidade openclaw (últimas 48h se acessível)

Reportar: lista de regressões conhecidas, workarounds documentados, issues que afetam nossa stack. Classificar por severidade.
```

### Agent 4 — Release Notes Correlation

```
Você é um analista de compatibilidade. Leia as release notes de openclaw@2026.4.25 e correlacione com estas regras críticas:

- Rule 5: claude-cli como backend primário via OAuth. Mudança em agentRuntime, cliBackends, anthropic:claude-cli provider?
- Rule 6: monkey-patch #62028 em restart-stale-pids-*.js. Menciona Issue #62028? cleanStaleGatewayProcessesSync mudou?
- Rule 12: chattr +i .credentials.json. Menciona Issue #70902 OAuth sync? Altera comportamento de escrita?
- Rule 9: openclaw.json schema. Novas chaves obrigatórias? Chaves removidas? doctor auto-migration?
- Plugin registry: bedrock mudou? amazon-bedrock-mantle ainda existe? Novos plugins default-on?
- Deprecações: vectorize --limit? Outros flags nox-mem?

Reportar: itens que requerem ação nossa, itens que simplificam nossa stack (hacks a aposentar), itens de risco alto.
```

---

## Referências

- Release notes v.25: https://github.com/openclaw/openclaw/releases/tag/v2026.4.25
- Issue #71957 — claude-cli routing via `agentRuntime.id` (canonical fix)
- Issue #70902 — OAuth credential sync (credentials.json graceful refresh)
- Issue #71284 — Silent auth failures isolated
- Issue #62028 — Gateway fratricide (monkey-patch ainda necessário em v.25)
- Issue #72042 — Postinstall pruning fix (elimina risco de plugin wipe em npm install)
- `docs/RUNBOOKS/openclaw-upgrade-runbook.md` — RB-11 (runbook completo, genérico pra v.26+)
- `docs/RUNBOOKS/openclaw-v25-upgrade-postmortem.md` — post-mortem com métricas e timeline real
- `docs/RUNBOOKS/openclaw-v25-upgrade-paper.md` — paper público com contexto expandido
- `CLAUDE.md` rules 5, 6, 9, 11, 12, 13 — regras operacionais que este guia referencia
