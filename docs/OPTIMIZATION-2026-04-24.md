# Agent Performance Optimization — 2026-04-24

> **TL;DR:** Tier 1+2 aplicado na VPS. Gateway mais leve (~3k tokens/turn a menos), plugins quebrados removidos, KG extraction confirmada em `gemini-2.5-flash-lite`, log do graph-memory patched pra refletir realidade.
>
> Status: **produção estável** — 9541 chunks, 99.97% vec coverage, monkey-patch #62028 intacto, 0 fratricides.

---

## Contexto

Audit 2026-04-24 identificou:
1. Plugins quebrados (`amazon-bedrock`, `google`) causando retry loops a cada turn
2. Bootstrap context de 25k chars (inflando todo turn)
3. `agents.defaults.thinking.mode = on` (overhead em tarefas operacionais)
4. `llm-task` usando claude-haiku (poderia ser gemini-flash-lite, mais barato)
5. Log do graph-memory reportando `claude-opus-4-6` — suspeita de rodar em modelo caro/lento

---

## O que foi feito

### Tier 1 — remoção de broken plugins

Script: `/root/optimize-agents.sh` (executado 2026-04-24T17:32:48-03:00)

**Removido fisicamente:**
- `/usr/lib/node_modules/openclaw/dist/extensions/amazon-bedrock/` → `/tmp/` (já estava ausente, rollback anterior)
- `/usr/lib/node_modules/openclaw/dist/extensions/google/` → `/tmp/` (já estava ausente)

**Limpo de `openclaw.json`:**
- `plugins.entries.google` deletado
- `plugins.allow` enxuto (21 items restantes)

**Por quê removemos fisicamente:** schema do OpenClaw **rejeita** `plugins.disabled: true` — a única forma de desabilitar é `mv` do dir. Ver `memory/feedback_amazon_bedrock_plugin_broken_remove_physically.md`.

### Tier 2 — config tuning

```diff
-  "bootstrapMaxChars": 25000
+  "bootstrapMaxChars": 12000

-  "thinking": { "mode": "on" }
+  "thinking": { "mode": "off" }

-  "llm-task.model": "anthropic/claude-haiku-4-5"
+  "llm-task.model": "gemini/gemini-2.5-flash-lite"
```

**Impacto esperado:**
- Bootstrap: **~3k tokens/turn economizados** em todas as conversas
- Thinking off: elimina reasoning chain em tasks operacionais (heartbeats, routing, summaries)
- llm-task: **~10x mais barato** ($1/5 → $0.10/0.40 per 1M tokens) mantendo qualidade pra pattern matching

### Validação empírica: graph-memory roda flash-lite

**Dúvida:** log dizia `model=claude-opus-4-6`. Verdade?

**Evidência 1 — código-fonte do plugin** (`index.ts` + `src/engine/llm.ts`):
```typescript
// createCompleteFn() em llm.ts:
if (llmConfig?.apiKey && llmConfig?.baseURL) {
  // Path A: POST direto pro baseURL (Gemini OpenAI-compatible)
  // O 'model' e 'provider' args são IGNORADOS aqui
  return await fetchRetry(`${baseURL}/chat/completions`, {
    body: { model: llmConfig.model ?? model, ... }
  });
}
// Path B: só executa se llmConfig.apiKey && !llmConfig.baseURL
```

**Config atual:**
```json
"llm": {
  "apiKey": "${GEMINI_API_KEY}",
  "baseURL": "https://generativelanguage.googleapis.com/v1beta/openai/",
  "model": "gemini-2.5-flash-lite"
}
```

→ **Path A vence silenciosamente.** `provider/model` de `agents.defaults.primary` nunca são chamados.

**Evidência 2 — latência real:**
```
17:30:17.381 → 17:30:19.085 = 1.7s (2 nodes, 1 edge)
17:30:18.576 → 17:30:21.870 = 3.3s (3 nodes, 1 edge)
```
Opus: 5-10s típico. Flash-lite: 1-3s. **Confirmado.**

### Fix cosmético do log

**Arquivo:** `/root/.openclaw/extensions/graph-memory/index.ts` (~linha 756)
**Backup:** `index.ts.bak-log-fix-20260424-HHMMSS`

**Patch aplicado:**
```typescript
// Antes:
api.logger.info(
  `[graph-memory] ready | db=${cfg.dbPath} | provider=${provider} | model=${model}`,
);

// Depois:
let effProvider = provider;
let effModel = model;
if (cfg.llm?.apiKey && cfg.llm?.baseURL) {
  const host = cfg.llm.baseURL.toLowerCase();
  if (host.includes("googleapis") || host.includes("generativelanguage")) effProvider = "gemini";
  else if (host.includes("openai.com")) effProvider = "openai";
  else if (host.includes("anthropic.com")) effProvider = "anthropic";
  else effProvider = "openai-compatible";
  effModel = cfg.llm.model ?? model;
} else if (cfg.llm?.apiKey && !cfg.llm?.baseURL) {
  effProvider = "anthropic";
  effModel = cfg.llm.model ?? model;
}
api.logger.info(
  `[graph-memory] ready | db=${cfg.dbPath} | provider=${effProvider} | model=${effModel}`,
);
```

**Log pós-fix:**
```
[plugins] [graph-memory] ready | db=/root/.openclaw/graph-memory.db | provider=gemini | model=gemini-2.5-flash-lite
```

**⚠️ Patch é local.** Gets wiped em:
- `npm install/update graph-memory` (se for publicado)
- Restore de `.bak` antigo do `index.ts`

**Reaplicação:** `cp index.ts.bak-log-fix-20260424-* /root/.openclaw/extensions/graph-memory/index.ts` — OU refazer o bloco `effProvider/effModel` manualmente na nova versão.

**TODO longo prazo:** PR upstream pra `github.com/adoresever/graph-memory` com o bloco.

---

## Invariantes pós-restart (verificados)

| Check | Status | Evidência |
|---|---|---|
| Monkey-patch #62028 intacto | ✅ | `restart-stale-pids-CegQx-K9.js` existe (v4.23) |
| Sem fratricide loop | ✅ | 4 restarts em 5min (optimize + log-fix + bootstraps), sem SIGTERM spam |
| vectorCoverage estável | ✅ | 9538/9541 (99.97%) |
| Salience mode | ✅ | `shadow` (não aplica no ranking até 2026-04-30) |
| graph-memory runtime | ✅ | extração em 1.7-3.3s = flash-lite range |

---

## Backups & rollback

**Script optimize-agents:**
```bash
cp /root/backups/optimize-20260424-173248/openclaw.json.bak /root/.openclaw/openclaw.json
cp /root/backups/optimize-20260424-173248/sessions-main.json.bak /root/.openclaw/agents/main/sessions/sessions.json
systemctl restart openclaw-gateway
```

**Log patch graph-memory:**
```bash
cp /root/.openclaw/extensions/graph-memory/index.ts.bak-log-fix-20260424-* \
   /root/.openclaw/extensions/graph-memory/index.ts
systemctl restart openclaw-gateway
```

---

## Regras atualizadas (CLAUDE.md)

Adicionar à lista de "comandos que invalidam patches" na regra 6:
- `npm install -g graph-memory` (se algum dia for publicado) → invalida log patch
- Restore manual do `index.ts.bak` → invalida log patch

Novo item de memory: `feedback_graph_memory_startup_log_is_misleading.md` atualizado pra "patched 2026-04-24".

---

## Arquivos tocados

**VPS (root@100.87.8.44):**
- `/root/.openclaw/openclaw.json` (bootstrap, thinking, llm-task, plugin entries)
- `/root/.openclaw/extensions/graph-memory/index.ts` (log fix)
- `/usr/lib/node_modules/openclaw/dist/extensions/google/` (removido; já estava no /tmp)

**Local (repo memoria-nox):**
- `docs/OPTIMIZATION-2026-04-24.md` (este arquivo)

**Memory:**
- `/Users/lab/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/feedback_graph_memory_startup_log_is_misleading.md` (atualizado)
- `/Users/lab/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/MEMORY.md` (entry atualizada)

---

## Addendum tarde — rework completo de routing + auth + thinking (18:20 GMT-3)

Depois do Tier 1+2 inicial, audit via `openclaw agent --json --agent <id>` nos 6 agentes revelou:
- **cipher/forge/lex rodavam em `openai-codex/gpt-5.4`** (pay-per-token) apesar de `openclaw.json` dizer claude-cli. Causa: `sessions.json` grudou em codex após falha antiga (regra 11).
- **Tier 2 parcialmente reverteu:** `bootstrapMaxChars` voltou pra 25000 porque o gateway sobrescreve `openclaw.json` no startup via in-memory state. Edits manuais (`jq`+`mv`) NÃO persistem; só `openclaw config set` sobrevive.

### Mudanças aplicadas

**Via `openclaw config set`:**
```
agents.defaults.bootstrapMaxChars = 12000
agents.defaults.thinkingDefault = max        # antes: não existia
plugins.allow -= "google"
plugins.entries.google removido
plugins.entries."llm-task".config.model = "gemini/gemini-2.5-flash-lite"
```

**Via edit direto em `auth-profiles.json`** de nox/atlas/boris/cipher/forge/lex:
```
profiles["anthropic:default"].apiKey removido
profiles["anthropic:default"].type = "token"  (era "api_key" com sk-ant-oat…)
```
Motivo: apiKey em `anthropic:default` era passada ao subprocess claude-cli gerando conflito latente.

**Sessions.json reset** pra 6 agentes — removidas entries com `model != claude-*` pra quebrar stickiness em codex/gemini/outros fallbacks.

### Routing final (canônico)

| Agente | Model primary | Thinking |
|---|---|---|
| main | claude-cli/claude-opus-4-6 | max |
| nox | claude-cli/claude-opus-4-6 | max |
| forge | claude-cli/claude-opus-4-6 | max (efetivo: high) |
| atlas | claude-cli/claude-sonnet-4-6 | max (efetivo: high) |
| boris | claude-cli/claude-sonnet-4-6 | max (efetivo: high) |
| cipher | claude-cli/claude-sonnet-4-6 | max (efetivo: high) |
| lex | claude-cli/claude-sonnet-4-6 | max (efetivo: high) |

Thinking=max resulta em `high` efetivo nos probes (limite dos modelos atuais). Fallback chain default: `[claude-cli/sonnet, openai-codex/gpt-5.5, gemini/2.5-pro]`.

### Validação pós-restart

Probe nos 6 agentes após restart do gateway:
```
nox     provider=claude-cli  model=claude-opus-4-6     bootstrapMaxChars=12000
cipher  provider=claude-cli  model=claude-sonnet-4-6   thinking=high
forge   provider=claude-cli  model=claude-opus-4-6     thinking=high
lex     provider=claude-cli  model=claude-sonnet-4-6   thinking=high
```

**Zero codex. Zero pay-per-token. Zero 401.** graph-memory log continua correto: `provider=gemini | model=gemini-2.5-flash-lite`.

### Backup

`/root/backups/config-rework-20260424-181356/` contém:
- `openclaw.json.bak` + 7x `<agent>-auth-profiles.json.bak` + 7x `<agent>-sessions.json.bak`

### Rollback emergencial

```bash
BK=/root/backups/config-rework-20260424-181356
cp $BK/openclaw.json.bak /root/.openclaw/openclaw.json
for a in main nox atlas boris cipher forge lex; do
  cp $BK/${a}-auth-profiles.json.bak /root/.openclaw/agents/$a/agent/auth-profiles.json
  cp $BK/${a}-sessions.json.bak /root/.openclaw/agents/$a/sessions/sessions.json
done
systemctl restart openclaw-gateway
```

### Regras novas descobertas nesta sessão

1. **Gateway sobrescreve openclaw.json no restart** — usar `openclaw config set` + `openclaw config validate`, nunca edit direto+restart.
2. **Schema auth profile mudou** — `anthropic-max:default` com apiKey é o canônico (não `anthropic:claude-cli` como CLAUDE.md regra 5 antiga descrevia).
3. **`anthropic:default.apiKey` é bomba-relógio** — mesmo sem CLI falhar agora, gateway pode passar a key ao subprocess em fallback path e quebrar 401. Manter sempre vazio (`type=token`, sem `apiKey`).
4. **Sessions stickiness obriga reset** após qualquer mudança de `model.primary` ou credencial.

CLAUDE.md regra 5 atualizada pra refletir schema atual.
