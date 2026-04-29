# Upgrade OpenClaw 2026.4.25: Lições de uma Sessão Real de Produção

> **Publicado:** 2026-04-27 | **Autor:** operador (VPS Hostinger KVM 4, multi-agent, claude-cli backend)
> **Setup:** 6 agents (main + nox/atlas/boris/cipher/forge/lex), TypeScript, nox-mem (SQLite + FTS5 + sqlite-vec), claude-cli via Max plan (zero pay-per-token)

---

## TL;DR

| | |
|---|---|
| **Vale upgrade?** | SIM |
| **Tempo necessário** | 3-5h pra setup conservador; ~1h com este guia |
| **Maior risco** | Token Anthropic divergente em até 5 lugares — invisível até Phase 4 se não auditado em Phase 0 |
| **Maior win** | claude-cli routing primary direto (latency p50 33s → 12s pós-wizard + rotação Gemini) |
| **Rollback necessário?** | Não. Forward-fix funcionou. |

Resumo de uma linha: v.25 torna o claude-cli backend **oficial** (não fallback), mas exige um wizard interativo pós-install que a maioria dos guides não menciona. Sem ele, você fica em fallback dance com 30+s/turn.

---

## Por que v.25 é importante

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

Se você tinha configs com `claude-cli/...`, v.25 pode renormalizar silenciosamente. Verifique os logs de boot.

### Fix #70902 — OAuth credential sync

Melhoria no fluxo de refresh do `.credentials.json`. O CLI agora tenta sync graceful antes de truncar. Mas **não muda a regra de ouro**: `chattr +i` continua obrigatório. Ver Surpresa 2 abaixo.

### Cold persisted plugin registry

Plugins disabled agora são persistidos em cold storage. Um `npm install -g openclaw` não volta os 100+ plugins para on. Em v.23, qualquer install global resetava a lista — você tinha que re-disable manualmente.

**Resultado prático:** fomos de 54 plugins carregados → 12 (só o necessário), e isso sobreviveu ao install.

### `OPENCLAW_SERVICE_REPAIR_POLICY=external`

Variável de ambiente nova. Com ela, o `doctor` não tenta auto-repair wrappers customizados (como o `openclaw-gateway-wrapper` imutável do Issue #62028). Essencial se você usa `chattr +i` em executáveis customizados.

Adicionar no drop-in do systemd:

```ini
# /etc/systemd/system/openclaw-gateway.service.d/override.conf
[Service]
Environment=IS_SANDBOX=1
Environment=OPENCLAW_SERVICE_REPAIR_POLICY=external
```

### `--method cli` em models auth login

Novo flag. Faz o `models auth login` bindar explicitamente o claude-cli como primary auth. Sem ele, o comando usa o caminho legado (que em v.23 apagava registry entries — Issue ainda relevante, verificar).

---

## Pré-requisitos

Antes de iniciar, confirme:

- Acesso SSH à VPS
- Janela de **3-5h** sem produção-crítica
- Espaço em disco: **1-2 GB** para VACUUM INTO snapshot (DB atual + backup)
- `claude auth status` retornando `loggedIn:true` no momento do pre-flight
- `/root/reapply-monkey-patch.sh` existente e funcionando (Issue #62028)

```bash
# Checagem rápida de pré-requisitos
ssh root@<VPS>
claude auth status | grep -E 'loggedIn|token'
df -h /root | tail -1
cat /root/reapply-monkey-patch.sh | head -3   # deve existir
```

---

## As 5 Surpresas que Custaram Tempo (e Como Evitar)

Esta seção é o coração do paper. Em produção, cada surpresa custou ~30min.

---

### Surpresa 1 — Token Anthropic divergente em até 5 lugares

**O problema:**

A maioria dos pre-flight audits verifica se o campo `apiKey` existe nos auth-profiles. Isso é insuficiente. Em produção, encontramos **3 tokens distintos rodando simultaneamente** — e `claude auth status` retornava `loggedIn:true` para todos (porque verifica a env var, não o credentials.json em uso real).

Os 5 lugares onde um token Anthropic pode estar, potencialmente divergente:

| # | Lugar | Como acessar |
|---|---|---|
| 1 | `~/.claude/.credentials.json` | `jq -r '.claudeAiOauth.accessToken[0:15]' ~/.claude/.credentials.json` |
| 2 | Env var `ANTHROPIC_MAX_API_KEY` | `echo ${ANTHROPIC_MAX_API_KEY:0:15}` |
| 3 | `auth-profiles.json` → `anthropic-max:default.apiKey` | `jq -r '.profiles["anthropic-max:default"].apiKey[0:15]' auth-profiles.json` |
| 4 | `auth-profiles.json` → `anthropic:default.token` | `jq -r '.profiles["anthropic:default"].token[0:15]' auth-profiles.json` |
| 5 | `auth-profiles.json` → `anthropic:claude-cli.token` | `jq -r '.profiles["anthropic:claude-cli"].token[0:15]' auth-profiles.json` |

**A regra 13 violada silenciosamente:** `claude auth status` usa a env var pra reportar status. Se a env var diverge do `.credentials.json`, você vê `loggedIn:true` mas subprocess calls reais falham com HTTP 401.

**Validação correta — teste direto na API:**

```bash
# Substitua TOKEN pelo valor real de cada local
TOKEN="sk-ant-..."

curl -sw "%{http_code}" -o /dev/null -X POST https://api.anthropic.com/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-opus-4-5","max_tokens":5,"messages":[{"role":"user","content":"hi"}]}'
```

Interpretação:
- `200` → token perfeito
- `429` → token válido, rate-limited (Max plan OK)
- `401` → token **revogado** — precisa rotacionar antes do upgrade

**Ação em Phase 0:** Extraia os 15 primeiros caracteres de cada lugar, confirme que são o mesmo token, e faça o curl test no token real. Se divergirem: sincronize TODOS para o token válido antes de continuar.

```bash
# Script de audit rápido
CREDS=$(jq -r '.claudeAiOauth.accessToken[0:15]' ~/.claude/.credentials.json)
ENV_T=${ANTHROPIC_MAX_API_KEY:0:15}
PROFILES=$(jq -r '.profiles["anthropic-max:default"].apiKey[0:15]' \
  /root/.openclaw/agents/main/agent/auth-profiles.json)

echo "credentials.json: $CREDS"
echo "env var:          $ENV_T"
echo "auth-profiles:    $PROFILES"

# Todos devem ser idênticos
[[ "$CREDS" == "$ENV_T" && "$ENV_T" == "$PROFILES" ]] && echo "OK: tokens consistentes" || echo "ATENCAO: tokens divergentes"
```

---

### Surpresa 2 — NÃO remova `chattr +i` preventivamente

**O que parece razoável:** "v.25 tem o Fix #70902 que melhora o OAuth credential sync. Vou remover o `chattr +i` preventivamente pra não conflitar."

**O que acontece de verdade:** O claude CLI subprocess, quando spawned sem TTY em condições de erro (comum durante installs e restarts), faz "self-fix" zerando `.credentials.json` para 0 bytes. Documentado no nosso rule 12.

Em produção: removemos o `chattr -i` em Phase 0.B.3. Em Phase 4 (~8h depois), `claude auth status` retornou `loggedIn:false`. Phase 4 quebrou com:

```
FailoverError: Not logged in · Please run /login
```

**Ação correta:**

- **Não toque no `chattr +i`** antes, durante ou depois do upgrade
- Se v.25 reclamar que não consegue escrever credentials: avalie case-by-case, mas o default é deixar imutável
- O Fix #70902 escreve em refresh REAL (raro). Se falhar por chattr, é warn — não fatal

```bash
# Verificar estado atual do imutável
lsattr ~/.claude/.credentials.json | grep -o '\-i-'
# Deve mostrar: -i-

# Se não estiver imutável (deveria estar):
chattr +i ~/.claude/.credentials.json
```

---

### Surpresa 3 — O wizard `openclaw config` é a peça canonical

**O que parece razoável:** "Vou rodar `doctor --fix` em Phase 3 pra migrar configs v.23 → v.25."

**O que acontece:** `doctor --fix` é diagnostic com fixes pontuais. Ele **não adiciona** provider entries novas no config registry. Sem a entrada `anthropic:claude-cli` no registry, o claude-cli só pega via fallback dance — FailoverError → retry → pega o segundo da fila.

Resultado: Phase 4 "funcionava" mas com latency 30+s por turn. Sintoma: logs mostrando fallback antes de cada claude-cli turn.

**O que o wizard faz (que `doctor --fix` não faz):**

1. Adiciona provider entry `anthropic:claude-cli` no config registry (binding explícito)
2. Registra modelos novos: `claude-opus-4-7`, `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
3. Atualiza `lastRunVersion` para 2026.4.25 (forçando registry refresh)

**Como rodar:**

```bash
# Wizard interativo — obrigatório pós-install em v.25
openclaw config

# Seguir prompts:
# - Confirm upgrade detection: YES
# - Add claude-cli as primary provider: YES
# - Register new models: YES (ou press Enter pra default)
# - Preserve existing plugin state: YES
```

**Após wizard:** latency p50 caiu de 33s → 12s.

**Regra:** `openclaw config` (sem subcommand = guided wizard) é **obrigatório** em Phase 3 de qualquer upgrade para v.25+. Roda sempre antes de declarar Phase 3 completa.

---

### Surpresa 4 — Bedrock vem em DUAS variantes em v.25

v.24 tinha `amazon-bedrock`. v.25 adicionou silenciosamente:

- `amazon-bedrock` — variant original
- `amazon-bedrock-mantle` — variante OpenAI-compatible (nova)

Se você só disabilitar `amazon-bedrock`, o `amazon-bedrock-mantle` fica ativo. Ele não quebra nada se você não tem creds de Bedrock, mas aumenta boot time e polui logs de health check.

**Verificação:**

```bash
# Listar com --json pra ver IDs completos (tabela trunca em 8 chars)
openclaw plugins list --json | jq '.[] | select(.id | startswith("amazon")) | {id, enabled}'
```

**Disable ambos:**

```bash
openclaw plugins disable amazon-bedrock
openclaw plugins disable amazon-bedrock-mantle
```

**Validar:**

```bash
openclaw plugins list --json | jq '.[] | select(.id | startswith("amazon")) | {id, enabled}'
# Ambos devem ter: "enabled": false
```

---

### Surpresa 5 — `vectorize --limit` foi removido

Se você tem scripts com `nox-mem vectorize --limit 500`, eles vão quebrar silenciosamente em v.25.

O comportamento padrão do vectorize agora é idempotente (só re-vectoriza chunks sem embedding), então `--limit` foi considerado desnecessário pela equipe.

**Flags disponíveis em v.25:**

```bash
nox-mem vectorize --help
# --force    Re-vectoriza TUDO (ignora existing embeddings)
# --dry-run  Preview sem mutar
# (sem --limit)
```

**Migração:**

```bash
# v.23 — QUEBRA em v.25
nox-mem vectorize --limit 500

# v.25 — correto
nox-mem vectorize          # idempotente, só chunks sem embedding
nox-mem vectorize --force  # re-vectoriza tudo (para limpeza)
```

Atualize todos os scripts e crons antes do upgrade.

---

## Roteiro Mínimo (copy-paste safe)

Este roteiro assume que você já tem o setup básico funcionando em v.23. Adapte paths conforme seu setup.

### Phase 0 — Pre-flight (30min)

```bash
# 0.A — Backup completo
DATE=$(date +%Y%m%d-%H%M)
BACKUP_DIR="/root/backups/pre-v25-$DATE"
mkdir -p $BACKUP_DIR

# Config backup
tar czf $BACKUP_DIR/openclaw-config.tar.gz \
  /root/.openclaw/openclaw.json \
  /root/.openclaw/agents/*/agent/auth-profiles.json \
  /root/.openclaw/agents/*/agent/models.json \
  /root/.openclaw/.env

# Credentials backup
cp ~/.claude/.credentials.json $BACKUP_DIR/credentials.json.pre-v25

# DB snapshot
set -a; source /root/.openclaw/.env; set +a
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "VACUUM INTO '$BACKUP_DIR/nox-mem.db'"

echo "Backup: $BACKUP_DIR"
ls -lh $BACKUP_DIR/
```

```bash
# 0.B — Token audit (crítico — ver Surpresa 1)
CREDS_TOKEN=$(jq -r '.claudeAiOauth.accessToken[0:20]' ~/.claude/.credentials.json)
ENV_TOKEN=${ANTHROPIC_MAX_API_KEY:0:20}
PROFILE_TOKEN=$(jq -r '.profiles["anthropic-max:default"].apiKey[0:20]' \
  /root/.openclaw/agents/main/agent/auth-profiles.json 2>/dev/null || echo "NOT_FOUND")

echo "=== Token Audit ==="
echo "credentials.json: $CREDS_TOKEN"
echo "env ANTHROPIC_MAX_API_KEY: $ENV_TOKEN"
echo "auth-profiles main: $PROFILE_TOKEN"

# HTTP test no token real (pega do credentials.json)
REAL_TOKEN=$(jq -r '.claudeAiOauth.accessToken' ~/.claude/.credentials.json)
HTTP_CODE=$(curl -sw "%{http_code}" -o /dev/null -X POST \
  https://api.anthropic.com/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: $REAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-opus-4-5","max_tokens":5,"messages":[{"role":"user","content":"hi"}]}')

echo "API HTTP test: $HTTP_CODE  (200=valid, 429=valid+ratelimit, 401=REVOKED)"
[[ "$HTTP_CODE" == "401" ]] && echo "PARE: rotacione o token antes de continuar" && exit 1
```

```bash
# 0.C — Verificar chattr
lsattr ~/.claude/.credentials.json
# Deve conter: -i-   (i = imutável)
# NÃO remova o chattr +i
```

```bash
# 0.D — Verificar monkey-patch atual (pra comparar depois)
PATCH_FILE=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js 2>/dev/null)
echo "Patch file: $PATCH_FILE"
grep -l "return \[\];" $PATCH_FILE && echo "Patch ATIVO" || echo "Patch AUSENTE"
```

```bash
# 0.E — Atualizar scripts com --limit (ver Surpresa 5)
grep -r "vectorize --limit" /root/.openclaw/scripts/ && \
  echo "ATENCAO: scripts precisam ser atualizados (--limit removido em v.25)"
```

### Phase 1 — Install (5-10min)

```bash
# Salvar versão atual
CURRENT_VER=$(openclaw --version)
echo "Versão atual: $CURRENT_VER"

# Install pinned (substitua VERSION pela versão desejada)
npm install -g openclaw@2026.4.25

# Confirmar
openclaw --version  # deve mostrar 2026.4.25
```

### Phase 2 — Reapply Monkey-Patch (10-15min)

```bash
# Reapply imediato pós-install (npm install troca o dist/)
bash /root/reapply-monkey-patch.sh

# Validar (não use grep -c — falso positivo conhecido)
PATCH_FILE=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js)
echo "Novo arquivo: $PATCH_FILE"

# Validar via conteúdo real da função
grep -A5 "cleanStaleGatewayProcessesSync" $PATCH_FILE | grep "return \[\];" && \
  echo "Patch ATIVO" || echo "ATENCAO: patch ausente"

# Validar marker
grep "MONKEY_PATCH_62028" $PATCH_FILE && echo "Marker OK" || echo "Marker ausente"
```

### Phase 3 — Config Migration (20-30min)

```bash
# 3.A — Disable bedrock AMBAS variantes (ver Surpresa 4)
openclaw plugins disable amazon-bedrock
openclaw plugins disable amazon-bedrock-mantle

# Verificar
openclaw plugins list --json | \
  jq '.[] | select(.id | startswith("amazon")) | {id, enabled}'
```

```bash
# 3.B — Wizard interativo (OBRIGATÓRIO — ver Surpresa 3)
# Este passo adiciona anthropic:claude-cli no registry
openclaw config

# Nos prompts:
# - Upgrade migration detected? → confirm YES
# - Add claude-cli as primary auth provider? → YES
# - Register new model catalog? → YES (ou Enter pra default)
# - Preserve plugin state? → YES
```

```bash
# 3.C — Verificar que anthropic:claude-cli está no registry pós-wizard
jq '.profiles["anthropic:claude-cli"]' \
  /root/.openclaw/agents/main/agent/auth-profiles.json

# Esperado:
# {
#   "mode": "token",
#   "provider": "claude-cli"
# }
```

```bash
# 3.D — Doctor (diagnostic-only, não como substitute do wizard)
OPENCLAW_SERVICE_REPAIR_POLICY=external openclaw doctor

# Ignorar:
# - "anthropic:claude-cli (provider claude-cli)" mesmo sem estar no config
#   (doctor reporta INTENÇÃO, não estado real — ver Surpresa 4.5 do postmortem)
# - Probe errors de graph-memory (stale, cacheia 8h — ver Surpresa 4.7)
```

### Phase 4 — Restart Sequencial e Bring-up (15-30min)

```bash
# Restart sequencial (não todos de uma vez)
systemctl restart nox-mem-watcher
sleep 3
systemctl restart nox-mem-api
sleep 5
systemctl restart openclaw-gateway

# Aguardar boot completo
sleep 15
systemctl status openclaw-gateway | grep -E 'Active|running'
```

```bash
# Smoke test básico
set -a; source /root/.openclaw/.env; set +a

# Health check
curl -s http://127.0.0.1:${NOX_API_PORT}/api/health | \
  jq '{vectorCoverage: .vectorCoverage, status: .status}'

# Teste de turn (deve roteiar via claude-cli)
# Observar logs em paralelo:
# journalctl -u openclaw-gateway -f | grep -E 'cli-backend|FailoverError|anthropic'
```

### Phase 5 — Validação Completa

Ver checklist na próxima seção.

### Phase 6 — Re-imutabilizar e Fechar

```bash
# Confirmar chattr +i ainda ativo (pode ter sido removido por bug)
lsattr ~/.claude/.credentials.json | grep '\-i-' && \
  echo "Imutavel: OK" || \
  (chattr +i ~/.claude/.credentials.json && echo "Re-imutabilizado")

# Commit de qualquer config persistida
# (se usa git pra track configs)
```

---

## Checklist de Validação Pós-Upgrade

Execute cada item. Todos devem estar ✅ antes de declarar upgrade completo.

```bash
# Automatizar o máximo possível
echo "=== Validação pós-upgrade v.25 ==="

# 1. Versão
VER=$(openclaw --version)
[[ "$VER" == "2026.4.25" ]] && echo "✅ Versão: $VER" || echo "❌ Versão: $VER"

# 2. agentRuntime.id
RUNTIME=$(openclaw config get agentRuntime.id 2>/dev/null)
[[ "$RUNTIME" == "claude-cli" ]] && echo "✅ agentRuntime.id: claude-cli" || echo "❌ agentRuntime.id: $RUNTIME"

# 3. Provider entry anthropic:claude-cli
PROVIDER=$(jq -r '.profiles["anthropic:claude-cli"].provider // "MISSING"' \
  /root/.openclaw/agents/main/agent/auth-profiles.json)
[[ "$PROVIDER" == "claude-cli" ]] && echo "✅ anthropic:claude-cli provider" || echo "❌ Provider: $PROVIDER"

# 4. Monkey-patch ativo
PATCH_FILE=$(ls /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js)
grep -q "MONKEY_PATCH_62028" $PATCH_FILE && \
  echo "✅ Monkey-patch #62028 marker" || echo "❌ Monkey-patch ausente"

# 5. credentials.json imutável
lsattr ~/.claude/.credentials.json | grep -q '\-i-' && \
  echo "✅ credentials.json imutável" || echo "❌ credentials.json NÃO imutável"

# 6. VectorCoverage
set -a; source /root/.openclaw/.env; set +a
COVERAGE=$(curl -s http://127.0.0.1:${NOX_API_PORT}/api/health | \
  jq -r '.vectorCoverage | "\(.embedded)/\(.total)"')
echo "📊 VectorCoverage: $COVERAGE"

# 7. Bedrock disabled
BEDROCK=$(openclaw plugins list --json | \
  jq '[.[] | select(.id | startswith("amazon")) | .enabled] | any')
[[ "$BEDROCK" == "false" ]] && echo "✅ Bedrock disabled" || echo "❌ Bedrock ainda ativo"
```

Itens adicionais que requerem observação nos logs:

- [ ] `[agent/cli-backend]` aparece nos logs durante turns de agente
- [ ] `/usr/bin/claude` subprocess spawning: `ps -ef | grep claude` durante turn ativo
- [ ] Zero `FailoverError` em janela de 5min de uso normal
- [ ] Latency p50 < 15s (medir com `time` em alguns turns manuais)
- [ ] Cron canary `*/30min` verde na próxima janela (pode estar RED se restart coincidir — aguardar 1h)

---

## Pegadinhas v.25 (TIL)

Lista completa de comportamentos não-óbvios específicos desta versão:

### 1. `claude-cli/` prefix removido em model.primary

```json
// v.23 — ainda aceito, mas pode renormalizar silenciosamente
{ "model": { "primary": "claude-cli/claude-opus-4-6" } }

// v.25 — canônico
{ "model": { "primary": "anthropic/claude-opus-4-6" } }
```

Se você vê logs com `Renormalizing model primary: claude-cli/...`, é esperado — verifique o resultado.

### 2. Provider entry `anthropic:claude-cli` é load-bearing (v.25)

Em v.23, o roteamento claude-cli era implícito pelo prefixo. Em v.25, a entry precisa estar **explícita** no registry. Sem ela, claude-cli só pega via FailoverError (fallback dance, latency ~30s).

O wizard adiciona. `doctor --fix` não adiciona.

### 3. `openclaw plugins list` trunca IDs em 8 chars

`amazon-bedrock-mantle` aparece como `amazon-b` na coluna ID. Sempre use `--json` para IDs completos quando filtrando por nome.

### 4. `doctor` reporta intenção, não estado real

`doctor` mostra `anthropic:claude-cli (provider claude-cli)` mesmo que não exista no config — ele reporta o que `agentRuntime.id` implica, não o que está em `auth-profiles.json`. Validar via `jq` direto.

### 5. Probe errors de graph-memory são stale por 8h

O probe process do doctor roda separado e cacheia. Mesmo com Gemini key válida, erros do probe podem persistir nas saídas do doctor por horas. Não é fonte de verdade — validar via `nox-mem vectorize` real ou `/api/health`.

### 6. Cron canary RED em windows de restart é normal

O cron `*/30` de health check que dispara exatamente nos xx:00 ou xx:30 vai reportar RED se você restartou o gateway nesse intervalo. Recupera automaticamente no próximo cycle. Não é regressão.

### 7. Heartbeat sessions com gemini-flash-lite são design, não bug

`agents.defaults.heartbeat.model: "gemini/gemini-2.5-flash-lite"` é otimização de custo para heartbeats. Sessions `:main` com gemini após um heartbeat são NORMAIS. Filtrar essas sessions pensando que estão "stuck" causa confusão (elas voltam em < 30min, parece regressão).

Distinguir:
- `:main` com `gemini-flash-lite` após heartbeat → **design** (não filtrar)
- `:main` com `gemini-flash-lite` após mensagem conversacional do usuário → **stuck** (filtrar)

### 8. 4 modelos novos no catálogo

Wizard adiciona: `claude-opus-4-7`, `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`. Todos roteáveis via claude-cli = zero pay-per-token quando Max plan cobre. Atualizar configs de roteamento por agente se quiser usar os novos.

### 9. Sessions sticky após filtro over-aggressive

Se você filtrar sessions com `jq 'with_entries(select(.value.model | startswith("claude-")))'` durante troubleshooting, heartbeats vão recriar sessões gemini em < 30min. Não interprete isso como "ainda stuck" — é o cron de heartbeat funcionando.

### 10. Sub-agent audits em SSH podem ter falsos positivos

Sub-agents com permissões SSH limitadas reportam:
- "Permission denied" em arquivos que existem
- Counts incorretos de plugins, profiles, tokens

Sempre validar findings críticos via sessão primária (você mesmo) antes de reagir.

---

## Quando NÃO Fazer o Upgrade (Ainda)

Aguarde se:

| Condição | Por que |
|---|---|
| Sistema 24/7 sem janela de 3-5h disponível | Phase 4 pode precisar de troubleshooting ativo |
| `claude auth status` retorna `loggedIn:false` agora | Resolva antes — o upgrade não vai consertar isso |
| `.credentials.json` nunca teve `chattr +i` | Aplique o chattr e monitore 24h antes de upgrade |
| Gemini billing cap esgotado | Rotacione a key antes — diagnosticar latency durante upgrade com Gemini falhando é confuso |
| Scripts de cron com `vectorize --limit` não atualizados | Atualize antes — quebra silenciosamente |
| Você nunca rodou o `/root/reapply-monkey-patch.sh` | Crie e teste o script com v.23 primeiro |

---

## Métricas Antes/Depois (nossa produção)

| Métrica | v.23 baseline | v.25 estável |
|---|---|---|
| Plugins carregados | 54/101 | 12/113 |
| Boot time | ~10s | 11.4s |
| **Latency p50** | ~15s | **12s** |
| Latency p99 | ~40s | ~25s |
| FailoverErrors / 5min | ~10 | **0** |
| claude-cli routing path | fallback dance | **primary direct** |
| Pay-per-token | zero | zero |
| Token consistency | 3 tokens divergentes | 1 token sincronizado |
| credentials.json imutável | sim | sim |
| Monkey-patch #62028 | ativo | ativo |
| Auth profiles (6 agents) | 22 profiles (inconsistente) | 12 profiles (6 × 2) |

A melhoria real de latency foi de **33s → 12s** (pico durante troubleshooting) para **12s estável** pós-wizard + rotação Gemini. O baseline v.23 era ~15s porque já tínhamos algum fallback.

---

## Lições para a Próxima Upgrade (v.26+)

### L1 — Token audit = verificar VALORES, não presença

Verificar que o campo `apiKey` existe não é suficiente. O HTTP test (`curl -sw "%{http_code}"`) é obrigatório em Phase 0. Cinco minutos que evitam 2h de troubleshooting em Phase 4.

### L2 — Wizard é Phase 3, não opcional

Qualquer upgrade que mude o registry de providers requer o wizard interativo. `doctor` é diagnostic. Wizard é migration. São ferramentas diferentes.

### L3 — Forward-fix > rollback

Quando Phase 4 quebrou com credentials zerada e tokens divergentes, a tentação era reverter para v.23. A abordagem correta foi diagnosticar e corrigir forward. Resultado: sistema saiu funcional **e** simplificado (3 tokens → 1, 22 profiles → 12).

Rollback preserva o problema que levou ao upgrade. Forward-fix resolve o root cause.

### L4 — Não toggle imutabilidade preventivamente

`chattr +i` é uma defesa de última linha, não um obstáculo de conveniência. Qualquer release que promete "melhorar o OAuth sync" ainda pode ter edge cases. A defesa vale mais que a conveniência.

Se o upgrade realmente exigir remover o `chattr`, você vai saber — o comando vai reclamar explicitamente. Até lá, deixe imutável.

### L5 — Medir performance DEPOIS de todos os fixes

Métricas de latency medidas durante troubleshooting (Gemini falhando, tokens divergentes, fallback dance ativo) são ruído. O número relevante é pós-estabilização completa. Bench intermediário gera ansiedade sem informação útil.

### L6 — Separar heartbeat sessions de user sessions ao diagnosticar stickiness

Antes de filtrar `sessions.json` por model, verificar se a session com "model errado" foi criada por um heartbeat. Heartbeats com gemini são design, não bug. Filtrar indiscriminadamente causa confusão de diagnóstico.

---

## Referências

- Release notes v.25: https://github.com/openclaw/openclaw/releases/tag/v2026.4.25
- Issue #71957 — claude-cli routing via `agentRuntime.id` (canonical fix)
- Issue #70902 — OAuth credential sync (credentials.json graceful refresh)
- Issue #71284 — Silent auth failures isolated (diagnóstico de 401s silenciosos)
- Issue #62028 — Gateway fratricide (monkey-patch ainda necessário em v.25)
- Issue #72042 — Postinstall pruning fix (elimina risco de plugin wipe em npm install)

---

## Créditos e Contexto

Este paper é baseado em uma sessão real de produção de ~9h em 2026-04-27, documentada no post-mortem interno `docs/RUNBOOKS/openclaw-v25-upgrade-postmortem.md`. Setup: VPS Hostinger KVM 4 com 6 agents, nox-mem com 9.5k+ chunks, claude-cli backend via Max plan.

Todas as métricas são reais. Os erros também.

---

*Última atualização: 2026-04-27 | Versão documentada: OpenClaw 2026.4.25*
