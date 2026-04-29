# RB-11: OpenClaw Version Upgrade Runbook

> **Versão:** 1.0 (baseado em v.23→v.25 upgrade, 2026-04-27)
> **Severity:** P0 operação planejada — prod offline durante Phase 1-2
> **Tempo total estimado:** 2-3h (Phase 0 pode ser feita separado, sem janela)
> **Aplica a:** qualquer bump de versão OpenClaw (v.25 → v.26, v.26 → v.27, etc.)

---

## Índice

1. [Quando usar este runbook](#1-quando-usar-este-runbook)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Filosofia](#3-filosofia)
4. [4 Reconnaissance Agents — dispatchar antes de tocar prod](#4-reconnaissance-agents)
5. [12 Invariantes I1-I12](#5-12-invariantes-i1-i12)
6. [Phase 0 — Pre-flight Hygiene (zero risco)](#phase-0--pre-flight-hygiene-zero-risco)
7. [Phase 1 — Install pinned version](#phase-1--install-pinned-version)
8. [Phase 2 — Reapply customizations](#phase-2--reapply-customizations)
9. [Phase 3 — Schema migration](#phase-3--schema-migration)
10. [Phase 4 — Bring-up sequencial](#phase-4--bring-up-sequencial)
11. [Phase 5 — Live observation 30min](#phase-5--live-observation-30min)
12. [Forward-fix decision tree](#12-forward-fix-decision-tree)
13. [Pitfalls e armadilhas conhecidas](#13-pitfalls-e-armadilhas-conhecidas)
14. [Post-upgrade hygiene (24-48h)](#14-post-upgrade-hygiene-24-48h)
15. [Quando abortar e fazer rollback real](#15-quando-abortar-e-fazer-rollback-real)

---

## 1. Quando usar este runbook

Disparar este runbook em qualquer um dos cenários:

| Gatilho | Ação |
|---|---|
| Nova versão OpenClaw disponível no npm | Esperar 24-48h, depois iniciar Phase 0 |
| `openclaw --version` difere da versão esperada após npm install acidental | Iniciar a partir da Phase 2 |
| Rollback de versão (dowgrade) necessário | Ir direto para [Seção 15](#15-quando-abortar-e-fazer-rollback-real) |
| `harness 'claude-cli' not registered` pós-restart inesperado | Ver RB-07 primeiro; se causa foi upgrade parcial, usar este runbook |

**Nunca upgradear sem janela de manutenção.** Phase 1-4 derruba os 3 serviços.

---

## 2. Pré-requisitos

- [ ] Acesso SSH confirmado: `ssh root@100.87.8.44` (Tailscale) ou `root@187.77.234.79` (público)
- [ ] Toto disponível pra supervisionar Phase 4-5 (smoke tests via Discord)
- [ ] Espaço em disco: mínimo 2GB livre em `/root` e `/var` para snapshots + tarball
  ```bash
  ssh root@100.87.8.44 'df -h /root /var'
  ```
- [ ] Tempo: ~1h para Phase 0 (pode ser feita dias antes) + ~2h para Phase 1-5
- [ ] Reconnaissance completa (ver Seção 4) — **não pule isso**
- [ ] Esperar ≥24h após release pra comunidade reportar regressões críticas

---

## 3. Filosofia

**Forward-fix > rollback.** Rollback real só se binário corrompido ou config irrecuperável.

**Slow + observable > fast.** Cada phase tem gate de aprovação. Não corra.

**Backups são audit trail, não gatilho de reversão.** O backup existe pra restaurar peças específicas (ex: credentials.json), não para desfazer o upgrade inteiro.

**Reconnaissance antes de qualquer ação destrutiva.** Os 4 agents paralelos economizam horas de surpresa em Phase 4.

**Simplificações depois de estável.** Se a nova versão remove a necessidade de um hack, aposentar o hack 7 dias após upgrade confirmado — nunca no mesmo dia.

---

## 4. Reconnaissance Agents

Dispatchar em **paralelo** antes de tocar prod. Cada um é independente.

### Agent 1 — VPS State Audit

```
Você é um auditor de infraestrutura. Conecte via SSH em root@100.87.8.44 e capture:

1. `openclaw --version` (versão atual)
2. `systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher`
3. `claude auth status 2>&1`
4. `lsattr /root/.claude/.credentials.json /usr/local/bin/openclaw-gateway-wrapper`
5. `wc -c /root/.claude/.credentials.json` (deve ser >200 bytes)
6. `ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js` (captura o hash atual)
7. `cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | grep -A5 "cleanStaleGatewayProcessesSync" | head -10` (valida patch body)
8. `grep -v "^#" /root/.openclaw/.env | grep -E "CLAUDE_CODE_OAUTH|ANTHROPIC_API_KEY|ANTHROPIC_BASE_URL"` (devem estar comentados/ausentes)
9. `curl -s http://127.0.0.1:18802/api/health | jq "{status,vectorCoverage,chunks}"` 
10. `for a in main nox atlas boris cipher forge lex; do echo -n "$a: "; jq -r 'to_entries[0].value.model // "empty"' /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null || echo "no file"; done`
11. `openclaw plugins list --json 2>/dev/null | jq '[.[] | {id,enabled,loaded}]'`
12. `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf`

Reportar: quais invariantes I1-I12 passam/falham, blockers que precisam ser resolvidos antes do upgrade.
```

### Agent 2 — Binary Diff Prediction

```
Você é um engenheiro de upgrade. Para a versão alvo <VERSION>:

1. `npm view openclaw@<VERSION> --json | jq "{version,dependencies,peerDependencies,dist}"` 
2. `npm pack openclaw@<VERSION> --pack-destination /tmp/openclaw-pack/ --dry-run 2>&1 | head -30`
3. Baixe o tarball: `npm pack openclaw@<VERSION> --pack-destination /tmp/`
4. Liste arquivos relevantes: `tar tzf /tmp/openclaw-*.tgz | grep -E "restart-stale-pids|cliBackends|agentRuntime|plugins|harness|claude-cli" | head -30`
5. Inspecione o arquivo restart-stale-pids: `tar xOf /tmp/openclaw-*.tgz $(tar tzf /tmp/openclaw-*.tgz | grep restart-stale-pids) | head -40`
6. Verifique se cleanStaleGatewayProcessesSync ainda existe com mesma signature

Reportar: novo hash do arquivo restart-stale-pids, se função existe e é patchable, mudanças de schema esperadas, novos arquivos/módulos que podem afetar nossa config.
```

### Agent 3 — Community Regression Scan

```
Você é um pesquisador de signals de comunidade. Pesquise:

1. GitHub issues do repositório openclaw abertas/fechadas nos últimos 3 dias com labels "bug", "regression"
2. Changelog/release notes de openclaw@<VERSION> completo
3. Issues mencionando: "credentials", "auth", "claude-cli", "harness", "fratricide", "plugins", "schema"
4. Posts em Discord/forum da comunidade openclaw (últimas 48h se acessível)
5. npm downloads: qualquer anomalia de downgrade pós-release?

Reportar: lista de regressões conhecidas, workarounds documentados, issues que afetam nossa stack (claude-cli backend, monkey-patch, plugin registry). Classificar por severidade.
```

### Agent 4 — Release Notes Correlation

```
Você é um analista de compatibilidade. Leia as release notes de openclaw@<VERSION> e correlacione com estas regras críticas da nossa stack:

Regras para verificar:
- Rule 5: claude-cli como backend primário via OAuth. Qualquer mudança em agentRuntime, cliBackends, anthropic:claude-cli provider?
- Rule 6: monkey-patch #62028 em restart-stale-pids-*.js. Menciona Issue #62028? Mudança na função cleanStaleGatewayProcessesSync?
- Rule 12: chattr +i .credentials.json. Menciona Issue #70902 OAuth sync? Altera comportamento de escrita em credentials.json?
- Rule 9: openclaw.json schema. Novas chaves obrigatórias? Chaves removidas? doctor auto-migration?
- Plugin registry: bedrock mudou? amazon-bedrock-mantle ainda existe? Novos plugins default-on?
- Node.js version req: mudou de 22.12+?
- Deprecações: vectorize --limit? Outros flags nox-mem?

Reportar: lista de itens que requerem ação nossa, itens que simplificam nossa stack (hacks a aposentar), itens de risco alto.
```

**Gate reconnaissance:** Só avançar para Phase 0 após ler todos os 4 relatórios.

---

## 5. 12 Invariantes I1-I12

Estas invariantes NUNCA podem regredir. Validar antes e depois do upgrade.

| # | Invariante | Comando de validação | Esperado |
|---|---|---|---|
| I1 | `agents.defaults.model.primary` apontando para claude-cli | `openclaw config get agents.defaults.model.primary` | Contém `claude-` e `opus` ou `sonnet` (sem prefixo `claude-cli/` em v.25+; via `agentRuntime.id`) |
| I2 | `agents.defaults.cliBackends.claude-cli` NÃO existe | `openclaw config get agents.defaults.cliBackends 2>&1` | `null`, erro, ou ausente |
| I3 | Fallback chain SEM `anthropic/*` direto (pay-per-token) | `openclaw config get agents.defaults.model.fallbacks` | Contém só `claude-cli/sonnet*`, `openai-codex/*`, `gemini/*` — sem `anthropic/claude-*` diretamente |
| I4 | Monkey-patch #62028 ativo em `dist/restart-stale-pids-*.js` | Ver abaixo | Marker comment presente + corpo da função retorna `[]` imediatamente |
| I5 | Wrapper `/usr/local/bin/openclaw-gateway-wrapper` imutável | `lsattr /usr/local/bin/openclaw-gateway-wrapper` | `----i---` na saída |
| I6 | systemd drop-in `IS_SANDBOX=1` | `cat /etc/systemd/system/openclaw-gateway.service.d/override.conf` | Linha `Environment=IS_SANDBOX=1` presente |
| I7 | `CLAUDE_CODE_OAUTH_TOKEN` comentado no `.env` | `grep "CLAUDE_CODE_OAUTH_TOKEN" /root/.openclaw/.env` | Linha começa com `#DISABLED_` ou ausente |
| I8 | bedrock plugin ausente (ambas variantes) | `ls /usr/lib/node_modules/openclaw/node_modules/ 2>/dev/null \| grep -i bedrock` | Vazio |
| I9 | 3 serviços nox-mem ativos | `systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher` | `active` em todos 3 |
| I10 | vectorCoverage ≥95% (tracking de regressão) | `curl -s http://127.0.0.1:18802/api/health \| jq '.vectorCoverage'` | `embedded / total ≥ 0.95` |
| I11 | sessions.json não grudado em fallback não-claude | `for a in nox atlas boris cipher forge lex; do jq -r 'to_entries[0].value.model // "empty"' /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null; done` | Todos mostram `claude-*` OU `empty` (gemini só em heartbeat sessions é OK — ver pitfall #9) |
| I12 | Node.js wrapper ativo | `head -3 /usr/bin/node` | Bash shebang + `exec /usr/bin/node.bin --no-warnings "$@"` |

**Validação de I4 (completa — NÃO usar `grep -c`):**
```bash
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | grep -A8 "cleanStaleGatewayProcessesSync" | head -10'
# Esperado: marker comment "# MONKEY-PATCH #62028" + primeira linha do corpo = "return [];"
# NUNCA validar só com: grep -c "return \[\]" — false positive (pode estar em outro contexto)
```

---

## Phase 0 — Pre-flight Hygiene (zero risco)

> Pode rodar dias antes do upgrade. Nenhuma mudança destrutiva. Não derruba serviços.

### 0.A — Backup completo

```bash
# Todos os comandos a partir de /root/.openclaw/

# 1. Config + auth + wrapper + systemd
tar czf /var/backups/preupgrade-v<NEW>-$(date +%Y%m%d-%H%M).tar.gz \
  openclaw.json \
  agents/*/agent/auth-profiles.json \
  agents/*/sessions/sessions.json \
  /etc/systemd/system/openclaw-gateway.service.d/ \
  /usr/local/bin/openclaw-gateway-wrapper \
  /usr/bin/node \
  /root/.claude/.credentials.json

# 2. Snapshot DB nox-mem (VACUUM INTO = consistente, não hot-copy)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/data/nox-mem.db \
  "VACUUM INTO '/var/backups/nox-mem-pre-v<NEW>-$(date +%Y%m%d).db';"

# 3. Capturar hash atual do monkey-patch
ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js \
  > /var/backups/preupgrade-v<NEW>-monkey-patch-path.txt

# 4. Dump estado de plugins + config
openclaw plugins list --json > /var/backups/preupgrade-v<NEW>-plugins.json 2>/dev/null
openclaw config dump > /var/backups/preupgrade-v<NEW>-config.json 2>/dev/null
curl -s http://127.0.0.1:18802/api/health > /var/backups/health-pre-v<NEW>.json

# Verificar backups criados:
ls -lh /var/backups/preupgrade-v<NEW>* /var/backups/nox-mem-pre-v<NEW>*
```

### 0.B — Validar TOKEN VALUES (não só presença)

> Lição do v.25: audit verificou presença de `apiKey`, não detectou 3 tokens distintos divergentes. HTTP test é a única validação confiável.

```bash
# 1. Token em credentials.json (usado pelo subprocess claude-cli)
TOKEN_CREDS=$(ssh root@100.87.8.44 'jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json 2>/dev/null | head -c 20')
echo "Token credentials.json (primeiros 20): $TOKEN_CREDS"

# 2. Token em ANTHROPIC_MAX_API_KEY env var
TOKEN_ENV=$(ssh root@100.87.8.44 'grep "^ANTHROPIC_MAX_API_KEY" /root/.openclaw/.env | cut -d= -f2 | head -c 20')
echo "Token env var (primeiros 20): $TOKEN_ENV"

# 3. Token em auth-profiles.json anthropic-max:default (qualquer agent, e.g. nox)
TOKEN_PROF=$(ssh root@100.87.8.44 'jq -r ".profiles[\"anthropic-max:default\"].apiKey" /root/.openclaw/agents/nox/agent/auth-profiles.json 2>/dev/null | head -c 20')
echo "Token auth-profile nox (primeiros 20): $TOKEN_PROF"

# 4. Testar cada token via HTTP direto (200=válido, 401=revogado, 429=válido+rate-limit)
# Pegar token completo do credentials.json:
ssh root@100.87.8.44 'T=$(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json); \
  R=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $T" \
    "https://api.anthropic.com/v1/models" 2>/dev/null); \
  echo "credentials.json token HTTP: $R (200=OK, 401=revogado, 429=OK rate-limited)"'

# Todos devem começar com os mesmos caracteres E retornar 200 ou 429 (não 401)
# Se divergirem: sincronizar ANTES do upgrade (ver RB-05)
```

### 0.C — Validar `claude auth status` pre-upgrade

```bash
ssh root@100.87.8.44 'claude auth status 2>&1'
# Esperado: "Logged in" com email

ssh root@100.87.8.44 'lsattr /root/.claude/.credentials.json'
# Esperado: ----i--- (imutável)

# SE não imutável: imutabilizar AGORA (antes de qualquer outra coisa)
# ssh root@100.87.8.44 'chattr +i /root/.claude/.credentials.json'

# CRÍTICO: NÃO remover chattr +i preventivamente.
# Lição do v.25: remover "preventivo" causou self-truncation em 8h.
# Se a nova versão reclamar de não conseguir escrever credentials → resolver case-by-case DEPOIS.
# A proteção contra truncação cíclica (rule 12) é mais importante.
```

### 0.D — Snapshot `/api/health` baseline

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  status,
  chunks: .chunks.total,
  embedded: .vectorCoverage.embedded,
  total: .vectorCoverage.total,
  compiled: .sectionDistribution.compiled,
  neverDecay: .retention.never_decay,
  dbSizeMB
}"'
# Salvar esses números — comparar pós-upgrade para detectar regressão
```

### 0.E — Verificar `OPENCLAW_SERVICE_REPAIR_POLICY=external` no drop-in

```bash
ssh root@100.87.8.44 'cat /etc/systemd/system/openclaw-gateway.service.d/override.conf'
# Deve conter AMBAS as linhas:
# Environment=IS_SANDBOX=1
# Environment=OPENCLAW_SERVICE_REPAIR_POLICY=external

# Se OPENCLAW_SERVICE_REPAIR_POLICY=external estiver ausente:
ssh root@100.87.8.44 'cat >> /etc/systemd/system/openclaw-gateway.service.d/override.conf << EOF
Environment=OPENCLAW_SERVICE_REPAIR_POLICY=external
EOF
systemctl daemon-reload'
```

### 0.F — Resolver sessions stickiness (se necessário)

```bash
# Verificar estado das sessions (gemini após heartbeat é NORMAL — não filtrar isso):
ssh root@100.87.8.44 'for a in nox atlas boris cipher forge lex; do
  MODEL=$(jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null)
  echo "$a main-lane: $MODEL"
done'

# Se algum agent tem model não-claude em lane :main E a entrada tem timestamp de USER message
# (não heartbeat), resetar só esse agent:
# ssh root@100.87.8.44 'echo "{}" > /root/.openclaw/agents/<AGENT>/sessions/sessions.json'
#
# NÃO filtrar entradas gemini-flash-lite — heartbeat usa gemini por design (rule heartbeat.model)
```

### 0.G — Plugins disabled list (39 plugins)

O cold registry persiste através do `npm install`. Confirmar que nossa lista está preservada:

```bash
ssh root@100.87.8.44 'openclaw plugins list --json | jq "[.[] | select(.enabled == false) | .id] | length"'
# Esperado: ~39 (nossa lista de disabled do v.23/v.25)

# Se novo upgrade adicionar plugins default-on que não queremos:
# openclaw plugins disable <id>  ← SEMPRE via CLI, nunca via jq+mv
```

**Lista dos 39 disabled (referenciar pré-upgrade):**
```bash
ssh root@100.87.8.44 'openclaw plugins list --json 2>/dev/null | jq -r "[.[] | select(.enabled == false) | .id] | .[]"'
```

### 0.H — Pre-stage tarball (não instala)

```bash
# Confirmar que versão alvo existe:
npm view openclaw@<NEW_VERSION> version 2>/dev/null
# Deve retornar: <NEW_VERSION>

# Baixar tarball para inspeção (não instala ainda):
ssh root@100.87.8.44 'npm pack openclaw@<NEW_VERSION> --pack-destination /var/cache/openclaw-v<NEW>/ 2>&1'

# Inspecionar arquivos críticos:
ssh root@100.87.8.44 'tar tzf /var/cache/openclaw-v<NEW>/openclaw-*.tgz | \
  grep -E "restart-stale-pids|cliBackends|agentRuntime|plugins/installs|claude-cli" | head -20'

# Verificar se função monkey-patchada ainda existe com mesma signature:
ssh root@100.87.8.44 'tar xOf /var/cache/openclaw-v<NEW>/openclaw-*.tgz \
  $(tar tzf /var/cache/openclaw-v<NEW>/openclaw-*.tgz | grep restart-stale-pids) | \
  grep -A10 "cleanStaleGatewayProcessesSync" | head -12'
# Esperado: função presente, mesma assinatura, patchable
```

**Gate Phase 0:** Todos os backups criados, tokens validados por HTTP test, `claude auth status` = loggedIn, `chattr +i` ativo, drop-in com REPAIR_POLICY. Toto aprova antes de Phase 1.

---

## Phase 1 — Install Pinned Version

> Serviços param aqui. Janela de manutenção começa.

```bash
# Passo 1: Stop em ORDEM REVERSA de dependência (NÃO paralelo)
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher'
ssh root@100.87.8.44 'systemctl stop nox-mem-api'
ssh root@100.87.8.44 'systemctl stop openclaw-gateway'

# Passo 2: Confirmar todos parados
ssh root@100.87.8.44 'ps -ef | grep -E "openclaw|nox-mem" | grep -v grep'
# Esperado: output vazio (ou só grep em si)

# Passo 3: Install PINNED (nunca npm update -g ou npm install -g openclaw sem versão)
ssh root@100.87.8.44 'npm install -g openclaw@<NEW_VERSION> 2>&1 | tail -5'

# Passo 4: Validar versão exata instalada
ssh root@100.87.8.44 'openclaw --version'
# Esperado: exatamente <NEW_VERSION>

# Passo 5: Capturar novo hash do arquivo monkey-patchado
ssh root@100.87.8.44 'ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js'
# Hash muda a cada versão — registrar aqui: ________________
```

**Gate Phase 1:** `openclaw --version` == `<NEW_VERSION>` exato. Novo arquivo `restart-stale-pids-*.js` localizado.

---

## Phase 2 — Reapply Customizations

> `npm install -g` reinstala `node_modules/dist/` — apaga patches. Tudo aqui deve ser reaplicado.

### 2.1 — Monkey-patch #62028

```bash
# Reaplicar (script é idempotente):
ssh root@100.87.8.44 'bash /root/reapply-monkey-patch.sh 2>&1'

# Validar — CORPO DA FUNÇÃO, não grep -c:
ssh root@100.87.8.44 'cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | \
  grep -A8 "cleanStaleGatewayProcessesSync" | head -10'
# Esperado:
# 1. Marker comment "# MONKEY-PATCH #62028" (ou similar)
# 2. PRIMEIRA linha do corpo da função = "return [];"
# Se regex do reapply-script não casou (whitespace change na nova versão):
# → PARAR, mostrar diff, ajustar regex manualmente antes de continuar
```

### 2.2 — Graph-memory log patch

```bash
# Verificar se plugin foi reinstalado (perde log patch):
ssh root@100.87.8.44 'ls /root/.openclaw/extensions/graph-memory/index.ts.bak-log-fix-* 2>/dev/null'
# Se backup existe: patch ainda pode estar presente; verificar:
ssh root@100.87.8.44 'grep "gemini.*flash" /root/.openclaw/extensions/graph-memory/index.js 2>/dev/null | head -3'
# Se ausente e backup existe: reaplicar do bak
```

### 2.3 — Verificar wrapper e credentials imutáveis

```bash
ssh root@100.87.8.44 'lsattr /usr/local/bin/openclaw-gateway-wrapper /root/.claude/.credentials.json'
# Esperado: ----i--- em ambos
# Se credentials perdeu o bit: imutabilizar novamente
# ssh root@100.87.8.44 'chattr +i /root/.claude/.credentials.json'
```

### 2.4 — Systemd daemon reload

```bash
ssh root@100.87.8.44 'systemctl daemon-reload'
# (captura qualquer mudança no drop-in da Phase 0.E)
```

### 2.5 — Verificar Node.js wrapper ainda intacto

```bash
ssh root@100.87.8.44 'head -3 /usr/bin/node'
# Esperado: #!/bin/bash + exec /usr/bin/node.bin --no-warnings "$@"
# Se apt upgrade nodejs rodou entre upgrades: recriar wrapper
```

**Gate Phase 2:** Monkey-patch validado (body, não grep-c), wrapper imutável, credentials imutável, daemon reloaded.

---

## Phase 3 — Schema Migration

> `openclaw.json` pode precisar de migração. Backup ANTES, diff DEPOIS.

### 3.1 — Backup imediato pré-doctor

```bash
ssh root@100.87.8.44 'cp /root/.openclaw/openclaw.json /var/backups/openclaw-pre-doctor-v<NEW>.json'
```

### 3.2 — Doctor diagnostic (não-destrutivo)

```bash
ssh root@100.87.8.44 'openclaw doctor --non-interactive 2>&1 | tee /var/backups/doctor-check-v<NEW>.log'
# LEITURA CUIDADOSA DO OUTPUT:
# OK: relatos de agentRuntime.id, plugin registry updates, version bump
# ABORT se mencionar: stripping agents.defaults, removing model.primary, channels.discord
```

### 3.3 — Wizard `openclaw config` (OBRIGATÓRIO em v.25+)

> Esta é a peça canonical que `doctor` não faz. Adiciona provider entries e atualiza registry.
> Descoberto tarde no v.25 — custeou 1h de fallback dance desnecessário.

```bash
ssh root@100.87.8.44 'openclaw config'
# Wizard interativo. Seguir o fluxo:
# - Confirmar agentRuntime.id = "claude-cli"
# - Confirmar provider anthropic:claude-cli está registrado
# - Confirmar novos modelos adicionados ao catálogo
# - NÃO aceitar mudanças que toquem em agents.defaults.model.primary
```

### 3.4 — Diff de config pós-wizard

```bash
ssh root@100.87.8.44 'diff /var/backups/openclaw-pre-doctor-v<NEW>.json /root/.openclaw/openclaw.json | head -60'
# Verde: adições de agentRuntime.id, provider entries, model catalog entries
# ABORT + restore se:
#   - agents.defaults.model.primary mudou
#   - agents.defaults.model.fallbacks foi limpo
#   - channels.discord ou .telegram desapareceram
#   - heartbeat config foi removido dos 6 agentes

# Se ABORT necessário:
# ssh root@100.87.8.44 'cp /var/backups/openclaw-pre-doctor-v<NEW>.json /root/.openclaw/openclaw.json'
```

### 3.5 — Verificar invariantes após config

```bash
ssh root@100.87.8.44 'openclaw config get agents.defaults.model.primary'
ssh root@100.87.8.44 'openclaw config get agents.defaults.model.fallbacks'
# Validar I1 e I3 ainda passando
```

**Gate Phase 3:** Schema migrado, wizard rodou, config diff só tem adições esperadas, I1+I3 passando.

---

## Phase 4 — Bring-up Sequencial

> Subir um de cada vez. Não subir todos em paralelo.

### 4.1 — Gateway primeiro

```bash
ssh root@100.87.8.44 'systemctl start openclaw-gateway'

# Watch primeiros 60 segundos:
ssh root@100.87.8.44 'journalctl -fu openclaw-gateway --since "5s ago" 2>&1 | head -50'
```

**Checklist nos primeiros 60s:**

| O que observar | OK | PROBLEMA |
|---|---|---|
| Tempo até "ready" | < 15s | > 30s → ver decision tree |
| Versão reportada no log | == `<NEW_VERSION>` | Versão errada → abort |
| Restart counter | = 0 em 60s | > 0 → monkey-patch perdido (RB-06) |
| "401" ou "Not logged in" | Ausente | Presente → ver decision tree |
| "claude-cli" ou "agentRuntime: claude-cli" | Presente | Ausente → wizard necessário |
| "harness not registered" | Ausente | Presente → rollback (RB-07) |
| Plugin count | ~12 (nossa lista slim) | > 50 → registry reset |
| `IS_SANDBOX=1` respeitado | Sem mensagem de block | "permission denied" → checar drop-in |

```bash
# Validar agentRuntime carregado:
ssh root@100.87.8.44 'openclaw config get agentRuntime 2>/dev/null'
# Esperado: JSON com id="claude-cli"

# Checar restart counter:
ssh root@100.87.8.44 'systemctl status openclaw-gateway --no-pager | grep -E "Active:|restarts"'
```

### 4.2 — nox-mem-api

```bash
ssh root@100.87.8.44 'systemctl start nox-mem-api && sleep 3'
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .status'
# Esperado: "ok"
```

### 4.3 — nox-mem-watcher

```bash
ssh root@100.87.8.44 'systemctl start nox-mem-watcher && sleep 2'
ssh root@100.87.8.44 'systemctl is-active nox-mem-watcher'
# Esperado: "active"
```

### 4.4 — Smoke test 6 agents (sequencial, não paralelo)

Enviar 1 mensagem trivial para cada agent na ordem: **nox → forge → atlas → boris → cipher → lex**

Para cada agent após resposta:

```bash
# Verificar que sessions.json gravou model claude-* (não fallback):
ssh root@100.87.8.44 'jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
  /root/.openclaw/agents/<AGENT>/sessions/sessions.json'
# Esperado: começa com "claude-"

# Verificar ausência de 401 no log:
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "2 min ago" --no-pager | grep -c "401" && echo "401 errors" || echo "0 auth errors"'
```

Se agent falhar: parar, investigar, fix forward. Não pular para o próximo.

**Gate Phase 4:** 3 serviços ativos, gateway ready < 15s, restart counter = 0, 0 erros 401, todos 6 agents responderam via claude-cli.

---

## Phase 5 — Live Observation 30min

```bash
# Monitor loop a cada 5min durante 30min:
ssh root@100.87.8.44 'watch -n 300 "systemctl is-active openclaw-gateway nox-mem-api nox-mem-watcher; \
  journalctl -u openclaw-gateway --since \"5 min ago\" --no-pager | grep -c \"401\"; \
  curl -s http://127.0.0.1:18802/api/health | jq \"{status,embedded:.vectorCoverage.embedded,total:.vectorCoverage.total}\""'
```

**Checkpoints a cada 5min:**

| Métrica | Gate |
|---|---|
| `systemctl is-active` todos 3 | active |
| Restart counter gateway | 0 novos |
| Erros 401 em journalctl | 0 |
| `/api/health.status` | ok |
| Heartbeats no Discord (nox/atlas/boris/cipher/forge/lex) | aparecendo normalmente |
| "Unknown Channel" errors | 0 novos (stale queue < 10min é OK) |
| vectorCoverage | igual ou melhor que baseline pré-upgrade |

**Cron canary:** Se canário `*/30min` cair durante window de restart (xx:00 ou xx:30), é falso positivo — ignorar, aguardar próximo ciclo.

**Gate Phase 5:** 30min contínuos sem regressões. Upgrade concluído.

---

## 12. Forward-fix Decision Tree

### F1 — "Not logged in · Please run /login"

```
credentials.json foi truncado (chattr não estava ativo ou foi removido preventivamente)

Diagnóstico:
  ssh root@100.87.8.44 'wc -c /root/.claude/.credentials.json'
  # < 100 bytes = truncado

Fix:
  ssh root@100.87.8.44 'chattr -i /root/.claude/.credentials.json && \
    cp /root/.claude/.credentials.json.pre-v<OLD_VERSION> /root/.claude/.credentials.json && \
    chattr +i /root/.claude/.credentials.json && \
    claude auth status 2>&1'
  # Esperado: "Logged in"
  systemctl restart openclaw-gateway
```

### F2 — HTTP 401 silencioso (agent responde mas via fallback caro)

```
Tokens divergentes em múltiplos lugares. Validar todos os 5 locais:

1. jq -r '.claudeAiOauth.accessToken[0:20]' /root/.claude/.credentials.json
2. grep ANTHROPIC_MAX_API_KEY /root/.openclaw/.env | cut -d= -f2 | head -c 20
3. jq -r '.profiles["anthropic-max:default"].apiKey' /root/.openclaw/agents/nox/agent/auth-profiles.json | head -c 20
4. jq -r '.profiles["anthropic:default"].token' /root/.openclaw/agents/nox/agent/auth-profiles.json | head -c 20
5. jq -r '.profiles["anthropic:claude-cli"].token' /root/.openclaw/agents/main/agent/auth-profiles.json | head -c 20

Todos devem mostrar os mesmos primeiros 20 chars.
O token canônico é o que está em credentials.json (usado pelo subprocess direto).
Sincronizar os demais para o mesmo valor via `openclaw config set`.
```

### F3 — `FailoverError: rate limit` no primary claude-cli

```
NÃO é problema do upgrade. É problema de quota Gemini ou chave revogada.

Verificar:
  grep GEMINI_API_KEY /root/.openclaw/.env | head -1
  set -a; source /root/.openclaw/.env; set +a
  nox-mem vectorize --limit 1 2>&1 | tail -3

Se "0 embedded, N errors": chave Gemini expirou ou quota esgotou.
Fix: atualizar GEMINI_API_KEY em .env → systemctl restart nox-mem-api nox-mem-watcher
Ver RB-09 para procedimento completo.
```

### F4 — Sessions de todos 6 agents grudadas em gemini/codex após restart

```
Verificar se é heartbeat session (design) ou user session (bug):

for a in nox atlas boris cipher forge lex; do
  jq 'to_entries | map({k:.key, model:.value.model, lane:.value.lane}) | .[]' \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null
done

Se lane == ":heartbeat" com gemini → DESIGN, não filtrar
Se lane == ":main" com gemini após user message → STUCK, filtrar esse agent:
  echo "{}" > /root/.openclaw/agents/<AGENT>/sessions/sessions.json

Após reset de sessions, verificar agents.defaults.heartbeat.model ainda aponta pra gemini-flash-lite.
```

### F5 — Latency p50 > 20s após upgrade

```
Provável causa: fallback dance ativo (primary claude-cli falhando, gemini/codex sendo chamado).

Diagnóstico:
  journalctl -u openclaw-gateway --since "10 min ago" --no-pager | grep -i "fallback\|failover\|FailoverError" | tail -20

Se FailoverErrors presentes:
  1. Verificar wizard foi rodado (Phase 3.3) — anthropic:claude-cli provider entry no config
  2. Verificar credentials.json íntegro (Phase 0.C)
  3. Verificar agentRuntime.id = "claude-cli": openclaw config get agentRuntime
  4. Se tudo OK mas ainda fallback: resetar sessions de todos os agents + restart gateway

Medir latency APENAS após todos os fixes estarem completos — métricas de transição são ruído.
```

### F6 — Gateway restarta em loop (> 3x em 5min)

```
Monkey-patch #62028 perdido. Ir para RB-06.

Diagnóstico rápido:
  cat /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | grep -A5 "cleanStaleGatewayProcessesSync" | head -7

Fix emergencial (dá janela):
  mkdir -p /etc/systemd/system/openclaw-gateway.service.d/
  echo -e "[Service]\nRestart=no" > /etc/systemd/system/openclaw-gateway.service.d/no-restart.conf
  systemctl daemon-reload
  pkill -9 -f openclaw-gateway
  bash /root/reapply-monkey-patch.sh
  rm /etc/systemd/system/openclaw-gateway.service.d/no-restart.conf
  systemctl daemon-reload
  systemctl start openclaw-gateway
```

### F7 — `agents.defaults.model.primary` mudou após wizard

```
Wizard ou doctor alterou config. Restaurar do backup.

openclaw config set agents.defaults.model.primary "<VALOR_ORIGINAL>"
openclaw config validate

Se config validate falha: restaurar openclaw.json do backup:
  cp /var/backups/openclaw-pre-doctor-v<NEW>.json /root/.openclaw/openclaw.json
  systemctl restart openclaw-gateway
```

---

## 13. Pitfalls e Armadilhas Conhecidas

### P1 — `claude-cli/` prefix no model name

- **v.23:** `model.primary = "claude-cli/claude-opus-4-6"` (prefixo controlava roteamento)
- **v.25+:** `model.primary = "anthropic/claude-opus-4-6"` sem prefixo; roteamento via `agentRuntime.id: "claude-cli"`
- Reconhecer que a string `claude-cli/` pode ser normalizada silenciosamente no upgrade. Verificar via `openclaw config get agents.defaults.model.primary` pós-wizard.

### P2 — Provider entry `anthropic:claude-cli` é load-bearing

Em v.25+ precisa estar explícito em `models.providers`. Sem ele, claude-cli só pega via FailoverError (fallback dance, latência +20s). Wizard adiciona isso — é o motivo de rodar o wizard, não o doctor.

```json
"anthropic:claude-cli": {
  "mode": "token",
  "provider": "claude-cli"
}
```

### P3 — Bedrock vem em DUAS variantes

- `amazon-bedrock`
- `amazon-bedrock-mantle` (variante OpenAI-compatible — escapa do disable do primeiro)

Verificar ambos:
```bash
ssh root@100.87.8.44 'openclaw plugins list --json | jq -r "[.[] | select(.id | test(\"bedrock\")) | {id,enabled}]"'
# Se qualquer um aparecer como enabled: openclaw plugins disable <id>
```

### P4 — `vectorize --limit` removido em v.25

Scripts antigos com `nox-mem vectorize --limit N` quebram silenciosamente. Default já é idempotente. Usar `nox-mem vectorize --force` ou sem flags.

### P5 — `openclaw plugins list` trunca IDs

A tabela trunca IDs longos a 8 chars. `amazon-bedrock-mantle` aparece como `amazon-b`. Sempre usar `--json` para IDs completos quando desabilitando.

### P6 — doctor reporta `anthropic:claude-cli` mas não cria entrada real

Doctor v.25 reporta a INTENÇÃO baseada em `agentRuntime.id`, não o estado real do config. Validar via:
```bash
ssh root@100.87.8.44 'jq ".profiles" /root/.openclaw/agents/nox/agent/auth-profiles.json | jq keys'
```

### P7 — graph-memory probe error é stale

Probe roda em processo separado, cacheia 8h. Mesmo com Gemini key válida, probe error persiste no log. Não é fonte de verdade. Sempre validar com `nox-mem vectorize --limit 1` real.

### P8 — Cron canary em `*/30` durante window de restart

Canário semântico (`*/30min`) cai se gateway estiver restartando no exato minuto xx:00 ou xx:30. Falso positivo. Ignorar, aguardar próximo ciclo.

### P9 — Heartbeat sessions em gemini-flash-lite são DESIGN

`agents.defaults.heartbeat.model = "gemini/gemini-2.5-flash-lite"` é custo intencional (memory `feedback_model_selection_for_agent_infra`). Sessions `:heartbeat` com gemini NÃO são regressão. Filtrar só sessions `:main` com gemini após user message conversacional.

### P10 — Sub-agent reports de VPS podem ter false positives

Sub-agents fazendo SSH têm quirks de permissão e path. Nunca reagir a um finding crítico (ex: "I4 FAIL — patch perdido") sem validar via sessão primária. Reports de sub-agents são hipótese, não fato.

### P11 — Performance benchmarks pré-fix-completo são ruído

Medir latência p50 apenas após: tokens sincronizados + wizard rodado + Gemini key válida. Qualquer métrica durante o pipeline de fix reflete estado transitório, não o baseline real da nova versão.

---

## 14. Post-upgrade Hygiene (24-48h)

### Verificar em D+1

```bash
# Nightly maintenance rodou OK?
ssh root@100.87.8.44 'tail -20 /var/log/nox-maintenance.log'
# Esperado: todas phases OK, duração total < 30min

# vectorCoverage após nightly:
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage'
# Esperado: embedded == total (ou gap < 50)

# Schema invariants canary:
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'
# Esperado: "All invariants OK"

# Sessions drift:
ssh root@100.87.8.44 'for a in nox atlas boris cipher forge lex; do
  echo -n "$a: "
  jq -r "to_entries | map(select(.value.lane == \":main\")) | .[0].value.model // \"empty\"" \
    /root/.openclaw/agents/$a/sessions/sessions.json 2>/dev/null
done'
# Esperado: claude-* em todos ou empty
```

### Verificar em D+7 (antes de qualquer Phase 8 simplificação)

```bash
# Zero crashes ou rollbacks em 7 dias?
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "7 days ago" --no-pager | grep -c "Started openclaw-gateway"'
# Esperado: 1 (só o start inicial do upgrade) ou alguns poucos (reboots planejados)

# Latência estabilizou?
# Verificar via /api/health.searchTelemetry ou Discord logs de latência

# Só após 7 dias estáveis: considerar Phase 8 (aposentar hacks)
```

### Atualizar CLAUDE.md

Após confirmação estável:
- Atualizar versão OpenClaw em "Infraestrutura (estado atual)"
- Atualizar hash do monkey-patch se mudou (ou remover referência ao hash específico)
- Documentar qualquer nova pitfall descoberta neste upgrade

### Backup pós-estável

```bash
ssh root@100.87.8.44 'tar czf /var/backups/stable-v<NEW>-$(date +%Y%m%d).tar.gz \
  /root/.openclaw/openclaw.json \
  /root/.openclaw/agents/*/agent/auth-profiles.json \
  /etc/systemd/system/openclaw-gateway.service.d/'
# Este é o ponto de restauração de referência pra próximo upgrade
```

---

## 15. Quando Abortar e Fazer Rollback Real

**Filosofia:** Rollback é caro (perde wizard config, registry, migrations). Forward-fix resolve 95% dos casos. Rollback APENAS em:

| Condição | Rollback? |
|---|---|
| Gateway não sobe + `ERR_MODULE_NOT_FOUND` + `ls dist/` confirma arquivo deletado | SIM |
| openclaw.json corrompido além de restauração de backup | SIM |
| Fratricide loop persiste depois de monkey-patch reaplicado + cache limpo | SIM |
| Credentials.json restaurado mas `claude auth status` ainda falha após 3 tentativas | SIM — antes de rollback, tentar `claude setup-token` novo |
| Latência alta ou fallback dance | NÃO — forward-fix |
| Agent não responde | NÃO — forward-fix |
| Erros 401 | NÃO — forward-fix (token sync) |
| Plugin não carrega | NÃO — forward-fix |

**Procedimento de rollback:**

```bash
# Opção 1: Script dedicado (preferido — inclui monkey-patch automático)
ssh root@100.87.8.44 'ls /root/rollback-*.sh'
ssh root@100.87.8.44 'bash /root/rollback-<PREVIOUS_VERSION>.sh'

# Opção 2: npm install versão anterior (só se sem rollback script)
ssh root@100.87.8.44 'systemctl stop nox-mem-watcher nox-mem-api openclaw-gateway'
ssh root@100.87.8.44 'npm install -g openclaw@<PREVIOUS_VERSION>'
ssh root@100.87.8.44 'bash /root/reapply-monkey-patch.sh'
ssh root@100.87.8.44 'cp /var/backups/openclaw-pre-doctor-v<NEW>.json /root/.openclaw/openclaw.json'
ssh root@100.87.8.44 'systemctl start openclaw-gateway nox-mem-api nox-mem-watcher'
ssh root@100.87.8.44 'openclaw --version'
# Esperado: <PREVIOUS_VERSION>

# Após rollback: validar todos I1-I12 + smoke test 1 agent
```

---

## Métricas de Sucesso do Upgrade

| Métrica | v.25 real | Target v.26+ |
|---|---|---|
| Tempo total (incluindo Phase 0 separado) | ~5h | < 3h |
| Surpresas em Phase 4 | 3 | 0 |
| FailoverErrors/5min pós-upgrade | 0 | 0 |
| Latência p50 | 12s | ≤ 15s |
| Plugins loaded | 12/113 | ≤ 15/total |
| Rollbacks | 0 | 0 |
| Pay-per-token | 0 | 0 |

---

*Runbook criado 2026-04-27 baseado em post-mortem `docs/RUNBOOKS/openclaw-v25-upgrade-postmortem.md`. Próxima revisão: pós-upgrade v.26. Regras operacionais em `CLAUDE.md` (rules 1-15).*
