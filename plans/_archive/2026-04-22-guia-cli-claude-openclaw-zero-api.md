# Guia: Rodar OpenClaw com Claude Code CLI (zero custo de API)

**O que você ganha:** seus agentes do OpenClaw deixam de cobrar por token na API da Anthropic. Tudo passa a rodar via sua assinatura Claude Max/Pro (flat $20 ou $200/mês), usando o CLI local `claude` como backend.

**Pra quem:** quem roda OpenClaw em servidor Linux (VPS) com systemd, rodando como `root`.

**Tempo estimado:** 30 min se nada der errado. Veja "armadilhas" no fim.

---

## Pré-requisitos

- Linux com systemd, Node.js 22+, OpenClaw ≥ 2026.4.15 funcionando
- Assinatura Claude Pro ou Max ativa
- Acesso root ao servidor

---

## Passo 1 — Instalar o Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude --version   # precisa retornar algo (testado com 2.1.88)
which claude       # anota o path (geralmente /usr/bin/claude ou ~/.local/bin/claude)
```

---

## Passo 2 — Autenticar o CLI (modo headless)

Em VPS sem browser, use `setup-token`:

```bash
claude setup-token
```

Ele mostra URL + código. Cola a URL no browser do teu **desktop**, autentica com a conta Max/Pro, cola o código de volta no terminal. O CLI imprime:

```
sk-ant-oat01-...  (valid for 1 year)
Use this token by setting: export CLAUDE_CODE_OAUTH_TOKEN=<token>
```

**IMPORTANTE — entenda os DOIS tokens:**
- O token que aparece na tela é um **long-lived OAuth token** (para API externa ou env var)
- O CLI também salva um **session credential** em `~/.claude/.credentials.json` (usado internamente pelo subprocess)
- **Eles DEVEM ser o mesmo valor** — se divergirem (por exemplo, por editar manualmente `.credentials.json` com token antigo), o CLI autentica via `auth status` mas falha 401 ao chamar a API.

Verifique:
```bash
claude auth status
# esperado: {"loggedIn": true, "authMethod": "claude.ai", "subscriptionType": "max"}
jq -r '.claudeAiOauth.accessToken[0:15]' ~/.claude/.credentials.json
# o prefixo deve bater com os primeiros 15 chars do token impresso pelo setup-token
```

Se **não bater**, grave manualmente no `.credentials.json`:
```bash
TOKEN='sk-ant-oat01-...'  # o que setup-token imprimiu
cat > ~/.claude/.credentials.json <<JSON
{
  "claudeAiOauth": {
    "accessToken": "$TOKEN",
    "refreshToken": "",
    "expiresAt": $(date -d "+1 year" +%s)000,
    "scopes": ["user:inference", "user:profile"],
    "subscriptionType": "max"
  }
}
JSON
chmod 600 ~/.claude/.credentials.json
```

---

## Passo 3 — NÃO salvar token no `.env` do gateway

Esse é um **contra-intuitivo crítico.** Se você põe `CLAUDE_CODE_OAUTH_TOKEN=...` no `.env` do gateway, o OpenClaw propaga pra env do subprocess Claude → Claude CLI prioriza a env var sobre `.credentials.json` → falha 401 se o token da env for diferente do credentials (o caso usual).

**Deixe o `.env` sem `CLAUDE_CODE_OAUTH_TOKEN`.** O subprocess Claude vai ler direto do `.credentials.json`, que é o comportamento correto.

Se você já tem essa variável, comente:
```bash
sed -i 's/^CLAUDE_CODE_OAUTH_TOKEN=/#DISABLED_CLAUDE_CODE_OAUTH_TOKEN=/' /root/.openclaw/.env
```

---

## Passo 4 — Blindar `.credentials.json` contra truncamento

O Claude CLI, quando é spawned como subprocess sem TTY em condições de erro, pode zerar `~/.claude/.credentials.json` (comportamento "self-fix" observado em produção). Resultado: próximo turn falha "Not logged in".

**A ORDEM CORRETA IMPORTA.** Faça o `chattr +i` **DEPOIS** do `setup-token`, nunca antes (senão `setup-token` não consegue gravar e o credentials fica desatualizado):

```bash
# 1. Primeiro o setup-token já rodou (Passo 2) e o .credentials.json está populado
# 2. Backup
cp ~/.claude/.credentials.json ~/.claude/.credentials.json.bak

# 3. Só AGORA aplica imutabilidade
chattr +i ~/.claude/.credentials.json
lsattr ~/.claude/.credentials.json
# saída esperada: ----i---------e------- ... (o "i" é o que importa)
```

Para atualizar no futuro (renovar token em 11 meses): `chattr -i` → `setup-token` → (opcional: escrever manualmente) → `chattr +i`.

---

## Passo 5 — Criar profile OAuth no OpenClaw (sem apiKey!)

Sem isso, o OpenClaw reconhece o modelo `claude-cli/*` mas silenciosamente pula sem tentar invocar o CLI (`providersWithOAuth` não lista `claude-cli`).

Edite `~/.openclaw/agents/main/agent/auth-profiles.json` e adicione a entrada `anthropic:claude-cli`. **CRÍTICO:** não inclua `apiKey` nem `key` — o subprocess Claude deve ler do `.credentials.json` nativo, não receber token via OpenClaw:

```json
{
  "version": 1,
  "profiles": {
    "anthropic:claude-cli": {
      "type": "oauth",
      "provider": "claude-cli"
    }
  }
}
```

(Se já houver outros profiles, só adicione essa chave junto — não apague nada.)

```bash
chmod 600 ~/.openclaw/agents/main/agent/auth-profiles.json
```

Validação:
```bash
openclaw models status --json | jq '.auth.providersWithOAuth'
# deve incluir: "claude-cli (1)"
```

---

## Passo 6 — Permitir que o CLI rode como root

O Claude CLI bloqueia `--permission-mode bypassPermissions` quando detecta UID=0. Workaround oficial: variável de ambiente `IS_SANDBOX=1`.

Crie um systemd drop-in (não edite o unit file original):

```bash
mkdir -p /etc/systemd/system/openclaw-gateway.service.d
cat > /etc/systemd/system/openclaw-gateway.service.d/override.conf <<'EOF'
[Service]
Environment=IS_SANDBOX=1
EOF
systemctl daemon-reload
```

---

## Passo 7 — Editar `openclaw.json`

Primeiro backup:
```bash
cp /root/.openclaw/openclaw.json /root/.openclaw/openclaw.json.bak
```

Mudanças no `openclaw.json`:

**a) `agents.defaults.model.primary`:** mudar para `claude-cli/claude-sonnet-4-6`

**b) `agents.defaults.model.fallbacks`:** remover todos os entries `anthropic/*` (pra não mascarar falhas do CLI com API paga)

**c) `agents.list[*].model.primary`:** trocar todos os `anthropic/*` por `claude-cli/claude-sonnet-4-6` em cada agent

**d) `agents.defaults.cliBackends`:** **NÃO criar esse bloco.** O OpenClaw tem um backend `claude-cli` nativo auto-carregado. Configs customizadas (como as que circulam em tutoriais) quebram o parser.

**e) `agents.defaults.models` (allowlist):** inclua `"claude-cli/claude-sonnet-4-6": {}` e `"claude-cli/claude-opus-4-6": {}`

Jeito rápido com `jq`:

```bash
jq '
  .agents.defaults.model.primary = "claude-cli/claude-sonnet-4-6" |
  .agents.defaults.model.fallbacks = [
    "openai-codex/gpt-5.4",
    "gemini/gemini-2.5-pro"
  ] |
  (.agents.list[] | select(.model.primary | test("^anthropic/"))).model.primary = "claude-cli/claude-sonnet-4-6" |
  .agents.defaults.models = {
    "claude-cli/claude-sonnet-4-6": {},
    "claude-cli/claude-opus-4-6": {},
    "openai-codex/gpt-5.4": {},
    "gemini/gemini-2.5-pro": {}
  } |
  del(.agents.defaults.cliBackends)
' /root/.openclaw/openclaw.json > /tmp/oc.new && \
jq empty /tmp/oc.new && \
mv /tmp/oc.new /root/.openclaw/openclaw.json
```

---

## Passo 8 — Desativar a API paga da Anthropic

Pra garantir que nenhum fallback cobrado seja tentado, comente (não apague) no `.env`:

```bash
sed -i 's/^ANTHROPIC_API_KEY=/#DISABLED_ANTHROPIC_API_KEY=/' /root/.openclaw/.env
sed -i 's/^ANTHROPIC_BASE_URL=/#DISABLED_ANTHROPIC_BASE_URL=/' /root/.openclaw/.env
```

Se você usa RelayPlane, pare também (não precisa mais):
```bash
systemctl stop relayplane-proxy
```

---

## Passo 9 — Limpar sessions antigas (opcional mas recomendado)

O gateway persiste o modelo usado por canal em `sessions.json`. Se já houve fallback, o canal fica "grudado" no modelo errado. Limpe:

```bash
cp ~/.openclaw/agents/main/sessions/sessions.json ~/.openclaw/agents/main/sessions/sessions.json.bak
echo '{}' > ~/.openclaw/agents/main/sessions/sessions.json
chmod 600 ~/.openclaw/agents/main/sessions/sessions.json
```

---

## Passo 10 — Restart e validar

```bash
systemctl restart openclaw-gateway
sleep 15
systemctl show openclaw-gateway -p MainPID -p NRestarts -p ActiveState
# precisa mostrar ActiveState=active, NRestarts=0
```

Mande uma mensagem em qualquer canal/persona. Depois:

```bash
journalctl -u openclaw-gateway --since "2 min ago" | grep "cli-backend"
# espera-se algo tipo:
# [agent/cli-backend] cli exec: provider=claude-cli model=sonnet promptChars=...
```

Se aparecer `cli exec`, **funcionou**. Conversas estão indo pelo teu plano.

---

## Armadilhas comuns (todas encontradas em produção)

| Sintoma no log | Causa real | Fix |
|---|---|---|
| `cannot be used with root/sudo privileges` | Falta `IS_SANDBOX=1` no env do gateway | Passo 6 |
| `Not logged in · Please run /login` | `.credentials.json` foi truncada pelo próprio CLI | Passo 4 (chattr +i **depois** do setup-token) |
| `HTTP 401 authentication_error: Invalid authentication credentials` | Token da env var ≠ token do credentials.json (dois tokens diferentes conflitando) | Passo 3 — remover `CLAUDE_CODE_OAUTH_TOKEN` do `.env` |
| `setup-token` imprime token novo mas `claude auth status` continua retornando auth antigo | `.credentials.json` estava com `chattr +i` — setup-token não conseguiu gravar | `chattr -i` antes, grava, `chattr +i` depois |
| Gateway reconhece modelo `claude-cli/*` mas nunca invoca CLI (zero `cli exec` no log, apenas `candidate_failed reason=unknown`) | Falta profile `anthropic:claude-cli` em `auth-profiles.json` | Passo 5 — criar profile `{type:"oauth", provider:"claude-cli"}` sem apiKey |
| Funciona nos crons mas canal Discord cai em gemini/gpt | `sessions.json` cached com modelo do último fallback bem-sucedido | Passo 9 — wipe `sessions.json` para `{}` |
| Config inválido após restart | Você criou o bloco `cliBackends.claude-cli` no openclaw.json | Passo 7d — **NÃO crie** esse bloco; use built-in |
| Config inválido por `timeoutMs`, `allowRoot`, etc | Field inventado que não está no schema | Só use os 22 fields do `runtime-schema-*.js` do OpenClaw |
| Tudo parece OK mas o CLI subprocess trava / demora >60s e gateway dispara fallback | Primeiro turn do CLI é lento (warming de tools/permissions) | Tolerar latência inicial; aumentar paciência do primeiro turn ou aceitar 1-2 fallbacks enquanto warm-up acontece |
| Credentials expired após 1 ano | Token natural do OAuth expira | Repetir Passos 2 e 4 (chattr -i → setup-token → grava manualmente se necessário → chattr +i) |

---

## Como saber quanto está economizando

1. Confirme que `openclaw models status` mostra o claude-cli como primary:
   ```bash
   openclaw models status | grep -A1 "Default"
   ```
2. Monitore o dashboard do Anthropic Console — a curva de "extra usage" deve ficar plana daqui pra frente.
3. No log do gateway, cada `cli exec: provider=claude-cli` é uma chamada que **não** foi cobrada por token.

---

## Rollback em 30 segundos

Se algo der errado:

```bash
cp /root/.openclaw/openclaw.json.bak /root/.openclaw/openclaw.json
chattr -i ~/.claude/.credentials.json
rm -rf /etc/systemd/system/openclaw-gateway.service.d
systemctl daemon-reload
systemctl restart openclaw-gateway
```

---

## Créditos + histórico de descoberta

Baseado no setup demonstrado por [@ziwenxu_](https://x.com/ziwenxu_/status/2046679352977580437) (Abr/2026) + descobertas durante 6+ horas de debug em VPS Linux root+systemd. Issue relacionado: [openclaw/openclaw#70279](https://github.com/openclaw/openclaw/issues/70279).

### 8 camadas de bloqueio que tivemos de descobrir e destravar

1. Root bypass (`--dangerously-skip-permissions` e `bypassPermissions` são bloqueados quando UID=0) — **fix:** `IS_SANDBOX=1` via systemd drop-in
2. `sessions.json` gruda no modelo de fallback bem-sucedido — **fix:** wipe periódico enquanto transitando
3. Tutoriais mostram bloco `cliBackends` com `output:"json"` + `input:"arg"` que QUEBRA o parser — **fix:** omitir o bloco inteiro (OpenClaw tem built-in correto com `output:"jsonl"` + `input:"stdin"`)
4. Fallback Anthropic mascarava falha do CLI com bill pay-per-token — **fix:** remover `anthropic/*` dos fallbacks + disable `ANTHROPIC_API_KEY`
5. `.credentials.json` trunca ciclicamente quando CLI é spawned sob erro — **fix:** `chattr +i` (mas DEPOIS do setup-token, nunca antes)
6. Profile `anthropic:claude-cli` missing faz gateway silent-skip — **fix:** criar profile `{type:"oauth", provider:"claude-cli"}`
7. Dois tokens distintos (long-lived OAuth do env var vs session do credentials.json) → 401 quando divergentes — **fix:** manter só o do credentials.json, remover `CLAUDE_CODE_OAUTH_TOKEN` do `.env`
8. `claude setup-token` falha silenciosamente se `.credentials.json` está imutável — **fix:** `chattr -i` antes do setup-token

### Regra de ouro aprendida

Quando o gateway silent-skipa o primary e cai pra fallback sem log de erro visível, a causa costuma ser uma das 8 acima. Se nada bate, aumente verbosity com `journalctl -u openclaw-gateway -f` enquanto reproduz + use `openclaw models status --json` pra validar que `providersWithOAuth` inclui `claude-cli`.
