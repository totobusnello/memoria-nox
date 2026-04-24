# Briefing para agentes — mudanças 2026-04-24 tarde

> Cole isso no kickoff de qualquer sessão nova (main, nox, atlas, boris, cipher, forge, lex) que vai tocar em performance, KG extraction, graph-memory, ou validação de modelo.

---

## TL;DR (cole isso)

```
Atualizações 2026-04-24 na VPS (root@100.87.8.44):

1. openclaw.json otimizado:
   - bootstrapMaxChars: 25000 → 12000
   - agents.defaults.thinking.mode: on → off
   - llm-task.model: claude-haiku-4-5 → gemini-2.5-flash-lite
   - plugins.entries.google removido

2. graph-memory CONFIRMADO rodando em gemini-2.5-flash-lite
   (Path A via cfg.llm.baseURL, não opus como o log antigo sugeria).
   Latência medida: 1.7-3.3s/extração.

3. Log do graph-memory PATCHED localmente em
   /root/.openclaw/extensions/graph-memory/index.ts (~L756).
   Agora reporta provider=gemini | model=gemini-2.5-flash-lite.
   Patch wipa em npm reinstall ou restore do .bak — reaplicar de
   index.ts.bak-log-fix-20260424-*.

4. Backups em /root/backups/optimize-20260424-173248/.

5. Invariantes OK: monkey-patch #62028 intacto (CegQx-K9),
   vectorCoverage 9538/9541, salience shadow, sem fratricide.

Ver docs/OPTIMIZATION-2026-04-24.md pra detalhes.
```

---

## Regras novas/atualizadas que agentes precisam saber

### Se o agente vai mexer em `openclaw.json`:

- `bootstrapMaxChars` agora é 12000 — **não** mexer sem motivo
- `thinking.mode` é `off` — só ligar se a tarefa exigir reasoning (search/ranking changes, etc)
- `llm-task.model` é `gemini/gemini-2.5-flash-lite` — **não** voltar pra claude-haiku sem razão clara (custo 10x)
- Plugins `amazon-bedrock` e `google` **não devem voltar** — quebrados, causam retry loops

### Se o agente vai diagnosticar graph-memory:

- Log `[graph-memory] ready | provider=gemini | model=gemini-2.5-flash-lite` é a **verdade nova**
- Se aparecer `provider=claude-cli | model=claude-opus-*` → **patch foi perdido**, reaplicar de `index.ts.bak-log-fix-*`
- Latência real é a ground truth: 1-3s = flash-lite, >5s = investigar
- `cfg.llm.baseURL` presente = Path A vence, `provider/model` de `agents.defaults` são cosméticos

### Se o agente vai rodar upgrade do OpenClaw:

- Além do monkey-patch #62028, agora também precisa verificar se o log-fix do graph-memory sobreviveu
- Checklist: `grep -q "effProvider" /root/.openclaw/extensions/graph-memory/index.ts` → se vazio, reaplicar backup
- Script `/root/upgrade-<V>.sh` **ainda não cobre** o log-fix do graph-memory — adicionar na próxima iteração

---

## Arquivos pra agente ler (prioridade alta → baixa)

1. `docs/OPTIMIZATION-2026-04-24.md` — changelog completo + rollback
2. `memory/feedback_graph_memory_startup_log_is_misleading.md` — contexto histórico + patch details
3. `docs/EVOLUTION.md` entry v3.7a — resumo executivo
4. `CLAUDE.md` regra 6 — monkey-patch invariants (não atualizada ainda pra log-fix — TODO)

---

## Perguntas frequentes (respostas rápidas)

**"Por que o log dizia opus mas rodava flash-lite?"**
`readProviderModel()` lia `agents.defaults.model.primary`, mas `createCompleteFn()` prioriza `pluginConfig.llm` quando `apiKey + baseURL` estão set. Log e execução desacoplados.

**"O patch cosmético vai sobreviver a um `npm update graph-memory`?"**
Não. Gets wiped. Backup: `index.ts.bak-log-fix-20260424-*`. Reapply pattern: mesmo bloco `effProvider/effModel` após o novo `api.logger.info("[graph-memory] ready")`.

**"Podemos usar modelo ainda mais barato pra KG extraction?"**
`gemini-2.5-flash-lite` já é o ponto ótimo — $0.10/$0.40 per 1M tokens. Próxima opção (`gemini-2.0-flash-lite`) está deprecated (shutdown 2026-06-01), não compensa migrar.

**"E se o KG extraction começar a falhar?"**
Check sequence:
1. `journalctl -u openclaw-gateway --since "10 min" | grep graph-memory` — procurar stack traces
2. `curl -sf http://127.0.0.1:18802/api/health | jq .graphMemory` — stats
3. `echo $GEMINI_API_KEY` (após `set -a; source /root/.openclaw/.env; set +a`) — key ainda válida?
4. Teste direto: `curl https://generativelanguage.googleapis.com/v1beta/openai/chat/completions -H "Authorization: Bearer $GEMINI_API_KEY" -d '{"model":"gemini-2.5-flash-lite","messages":[{"role":"user","content":"hi"}]}'`
