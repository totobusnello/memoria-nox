# Post-Mortem — Upgrade OpenClaw v2026.4.23 → v2026.4.25

> **Data:** 2026-04-27 BRT (~9h de sessão, ~5h de execução real)
> **Resultado:** ✅ Estável, claude-cli routing primary, zero pay-per-token, 12 plugins enabled (de 113), latency p50 12s
> **Cronograma real:** Phase 0 (12:30-13:00) → Phase 1-4 + token sync + wizard + Gemini key (21:00-22:30) → Auditoria (22:30+)

---

## 1. Sumário Executivo

Upgrade bem-sucedido com **3 surpresas significativas** que custaram tempo:
1. Token Anthropic divergente em 5 lugares (não detectado em Phase 0)
2. `chattr -i` preventivo causou self-truncation de credentials.json
3. Wizard `openclaw config` foi descoberto LATE — era a peça canonical missing

**Tempo perdido por cada surpresa:** ~30min cada = ~1h30 economizável em próxima rodada.

---

## 2. Onde Erramos

### 2.1 ❌ Removemos `chattr +i` preventivamente — backfired

**O que fizemos (Phase 0.B.3):** `chattr -i .credentials.json` "preventivo pra evitar conflito com #70902 OAuth sync da v.25".

**O que aconteceu:** Em ~8h, o claude CLI subprocess auto-truncou `.credentials.json` para 0 bytes (rule 12: self-fix em condições de erro sem TTY). Ao boot do gateway pós-install, `claude auth status` retornou `loggedIn:false`. Phase 4 quebrou com `FailoverError: Not logged in · Please run /login`.

**Lição:** **Manter `chattr +i` SEMPRE.** O #70902 da release notes só escreve em refresh REAL (raro). Se a escrita falhar, é warn — não fatal. A defesa contra self-truncation é mais importante que tolerância ao OAuth refresh.

**Ação correta:**
- NÃO toggle chattr antes do upgrade
- Se v.25 reclamar de não conseguir escrever credentials, AÍ resolver case-by-case
- Validar pós-upgrade: `claude auth status` deve continuar `loggedIn:true`

### 2.2 ❌ Phase 0 audit não checou VALORES de tokens, só presença de profiles

**O que fizemos:** Audit verificou que `anthropic-max:default` tinha `apiKey` (rule 5) e `anthropic:default` não tinha. Marcou como ✅.

**O que NÃO checamos:** Os VALORES dos tokens em 5 lugares:
- `.credentials.json` (claude-cli usa)
- `ANTHROPIC_MAX_API_KEY` env var
- `auth-profiles.json` profiles[anthropic-max:default].apiKey
- profiles[anthropic:default].token
- profiles[anthropic:claude-cli].token (existia em main, não em 6 agents)

**Estado real descoberto na Phase 4:** 3 tokens distintos rodando:
- `Ry9UjsX...` (válido em credentials.json + main:claude-cli profile)
- `4S1jClmz...` (env + max:default profile — REVOGADO, retornava 401)
- `IlluB97L...` (anthropic:default profile — stale)

**Sintoma escondido:** rule 13 violada silenciosamente — `claude auth status` retornava `loggedIn:true` (env var inválida não bloqueava status), mas chamadas reais via auth-profile pay path eram 401.

**Lição:** Em audit pré-upgrade, validar **valor** (não só presença) de cada token via API direct test. HTTP 401 = revoked, HTTP 429 = valid+rate-limited, HTTP 200 = perfect.

### 2.3 ❌ Wizard `openclaw config` foi descoberto MUITO TARDE

**O que fizemos:** Plano original tinha `doctor --fix` em Phase 3. Recusamos rodar `--fix` por medo de strippar config (signal #65035 community). Pulamos pra Phase 4 sem rodar wizard.

**Resultado:** Phase 4 funcionava via fallback dance (gemini → claude-cli após FailoverError) com latency 30+s. Toto teve que insistir 2x ("ainda não estamos pelo CLI") pra fazer eu rodar `openclaw config` interactive.

**O que o wizard fez (que `doctor --fix` NÃO faria):**
- Adicionou provider entry `anthropic:claude-cli` no config (registry binding explícito)
- Registrou modelos novos no catálogo (claude-opus-4-7, 4-5, sonnet-4-5, haiku-4-5)
- Atualizou `lastRunVersion` pra 2026.4.25 (registry refresh)

**Após wizard:** latency p50 caiu de 33s → 12s (claude-cli é o caminho primary direto, não via fallback).

**Lição:** `openclaw config` (sem subcommand = guided wizard) é a ferramenta canonical v.25. Roda **sempre** pós-install antes de declarar Phase 3 complete. `doctor` é diagnostic-only; wizard é o único que adiciona registry entries necessárias.

### 2.4 ❌ Sub-agent reportou false positives por permission error

**Agent 3 (invariants audit)** reportou:
- "I4 monkey-patch FAIL — permission denied" → era apenas seu read perm
- "Plugin count: 3" → real era 12
- "Auth profiles per agent: 0" → real era 2
- "Token consistency FAIL — 2 tokens" → real era 1 (sincronizado)

Causou ansiedade desnecessária e gastou tempo validando.

**Lição:** Sub-agents fazendo SSH read em VPS podem ter quirks de perm/path. **Sempre validar findings críticos via primary session** (eu) antes de reagir. Sub-agent reports = hipótese, não fato.

### 2.5 ❌ Sessions sticky filter foi over-correction

**Phase 0.B.1 filtrou** todas sessions não-claude. Resetamos `gemini-flash-lite` entries em 6 agents. Pareceu correto pela rule 11.

**Realidade:** `agents.defaults.heartbeat.model = "gemini/gemini-2.5-flash-lite"` é config explícito (cost optimization, memory `feedback_model_selection_for_agent_infra`). Heartbeat fluxo cria sessions com gemini intencionalmente.

**Pós-filter:** heartbeats voltaram a criar gemini sessions em <30min, parecendo "stuck again". Investigamos como bug, era feature.

**Lição:** Distinguir:
- `:main` session com `gemini-flash-lite` após heartbeat → **DESIGN** (não filtrar)
- `:main` session com `gemini-flash-lite` após user msg conversational → **STUCK** (filtrar)

Filter precisa de timestamp + lane analysis pra ser correto. Ou simplesmente: deixar quieto, validar smoke test ativo.

### 2.6 ❌ Latency mid-rotation Gemini parecia regressão

**Agent 4 reportou:** p50 33s, max 69s. Vermelho.

**Causa real:** Gemini billing cap exhausted em primary heartbeat → cada turn pagava 30s de gemini-fail antes do claude-cli pegar via fallback. Não era regressão de código v.25.

**Pós-rotação Gemini key:** p50 caiu pra 12s (esperado).

**Lição:** Performance benchmarks pré-fix-completo são enganosos. Medir DEPOIS de todos os fixes em pipeline (rotação Gemini, wizard, token sync). Cada métrica de transição é ruído.

---

## 3. O Que Funcionou Bem

### 3.1 ✅ Pre-flight reconnaissance via 4 agents paralelos
Antes de tocar prod, 4 agents (Explore + researcher) mapearam:
- VPS state atual + invariants
- v.25 release notes correlation com nossas rules
- Community regression signals (24-48h pós-release)
- Binary diff prediction

**Achados úteis:** #72042 fix elimina risco postinstall pruning; monkey-patch regex casa em v.25; bedrock-mantle escondido pré-existente.

### 3.2 ✅ Backups completos (audit trail, não rollback)
Phase 0.A criou tar de configs + VACUUM INTO snapshot DB + dump completo. Quando Phase 4 quebrou com credentials zerada, **restore foi imediato** do `.credentials.json.pre-v25`.

### 3.3 ✅ Monkey-patch reapply foi trivial
Hash mudou (`CegQx-K9` → `CSJWMprl`), mas:
- Glob `restart-stale-pids-*.js` continuou funcionando
- Função `cleanStaleGatewayProcessesSync` ficou idêntica em v.25 (linha 531, mesma signature)
- Regex pattern do reapply script casou primeira tentativa
- Marker comment validation funcional

### 3.4 ✅ Forward-fix > rollback (filosofia validada)
Quando Phase 4 quebrou (credentials empty + tokens divergentes), **NÃO revertemos pro v.23**. Diagnosticamos, corrigimos forward (restore credentials, sync tokens, run wizard). Sistema saiu funcional + simplificado.

### 3.5 ✅ Plugin slim (54 → 12) preservou através install
Cold persisted registry da v.25 manteve nossos 40 plugins disabled através do `npm install`. Não voltaram default-on.

### 3.6 ✅ `OPENCLAW_SERVICE_REPAIR_POLICY=external`
Doctor não tentou auto-restart/repair nosso wrapper imutável. Drop-in funcionou como pretendido.

### 3.7 ✅ Subprocess `/usr/bin/claude` confirmado spawning
Validamos via `ps -ef`: claude subprocesses como child do gateway, ~1s CPU each, OAuth via `.credentials.json`. Plan-flat zero pay-per-token confirmed.

---

## 4. Pegadinhas Específicas v.25 (não óbvias do release)

### 4.1 `claude-cli/` prefix removido em model.primary
- v.23: `model.primary = "claude-cli/claude-opus-4-6"` (prefixo controla roteamento)
- v.25: `model.primary = "anthropic/claude-opus-4-6"` (sem prefixo); roteamento via `agentRuntime.id: "claude-cli"`

Se você tem old config com `claude-cli/...`, v.25 pode renormalizar silenciosamente.

### 4.2 Provider entry `anthropic:claude-cli` é load-bearing
Em v.23 isso era implícito. Em v.25 precisa estar EXPLÍCITO em `models.providers`:
```json
"anthropic:claude-cli": {
  "mode": "token",
  "provider": "claude-cli"
}
```
Sem isso, fallback dance ativo (claude-cli só pega via FailoverError).

### 4.3 Bedrock vem em DUAS variantes
- `amazon-bedrock`
- `amazon-bedrock-mantle` (OpenAI-compatible variant — escapa do disable do `amazon-bedrock` se você só desabilitar o primeiro)

Disable AMBOS no plugins.entries.

### 4.4 `vectorize --limit` removido
v.25 nox-mem aceita só `--force`. Default já é idempotente. Scripts antigos com `--limit` quebram.

### 4.5 doctor mostra `anthropic:claude-cli (provider claude-cli)` mesmo se não houver no config
Reporta a INTENÇÃO baseada em `agentRuntime.id`, não o estado real. Validar via `jq '.profiles' auth-profiles.json` direto.

### 4.6 `openclaw plugins list` tabela trunca IDs em 8 chars
`amazon-bedrock-mantle` aparece como `amazon-` na coluna ID. Usar `--json` pra IDs completos.

### 4.7 graph-memory probe error é stale
Probe roda em processo separado e cacheia 8h. Mesmo com Gemini key válida, probe error pode persistir nos logs por horas. **Não é fonte de verdade** — validar via runtime direto (vectorize real).

### 4.8 Cron canary em `*/30` cai em windows de restart
Se você restarta gateway nas xx:00 ou xx:30, o cron canary roda nesse window e reporta RED (search degraded). Ignorável; recupera no próximo cycle.

### 4.9 Heartbeat sessions são gemini by-design
`agents.defaults.heartbeat.model: "gemini/gemini-2.5-flash-lite"` é cost optimization. Sessions :main com gemini POSTo heartbeat NÃO são bug.

### 4.10 4 modelos novos no catálogo da v.25
Wizard adiciona: `claude-opus-4-7`, `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`. Roteados via cli-backend = zero pay-per-token quando Max plan cobre.

---

## 5. Métricas Antes/Depois

| Métrica | v.23 baseline | v.25 final |
|---|---|---|
| Plugins loaded | 54/101 | 12/113 (39 disabled by us) |
| Boot time | ~10s | 11.4s |
| Latency p50 (turns) | ~15s | 12s |
| Latency p99 | ~40s | ~25s |
| FailoverErrors / 5min | ~10 | 0 |
| Claude-cli routing path | fallback dance | primary direct |
| Plan-flat zero-cost | ✅ | ✅ |
| Token consistency | 3 tokens divergentes 🔴 | 1 token Ry... ✅ |
| credentials.json immutable | ✅ | ✅ |
| Monkey-patch active | ✅ | ✅ |
| 6 agents auth-profiles | 7 + 2 + 7 + 2 + 2 + 2 = 22 profiles | 6 × 2 = 12 profiles |

---

## 6. Tempo Realmente Gasto

| Phase | Tempo planejado | Real | Causa atraso |
|---|---|---|---|
| 0 — Pre-flight | 1h | 30min | mais rápido |
| 1 — Install | 15min | 5min | trivial |
| 2 — Reapply patches | 20min | 15min | regex casou primeira |
| 3 — Doctor migration | 30min | 5min | doctor `--non-interactive` foi noop |
| 4 — Bring-up | 30min | **2h** | credentials empty + token divergente |
| 5 — Smoke test 6 agents | 30min | (não rodado, validado via heartbeats) | - |
| 6 — Re-immutabilize | 10min | 2min | trivial |
| **Crisis fix:** | (não previsto) | **1h** | wizard descoberto via insistência |
| **Crisis fix Gemini:** | (não previsto) | **20min** | API key rotation |
| Auditoria + post-mortem | (não previsto) | **1h** | 4 agents + síntese |

**Total real:** ~5h vs 4h planejados = +25% overrun. Causa principal: surpresas em Phase 4 (chattr backfire + tokens divergentes).

---

## 7. Plan Phase 8/9 (Pós-Estável)

### 7.1 Phase 8 — Simplificações já validadas (próximas semanas)
- ✅ Bedrock disabled via CLI (não mais `mv pra /tmp`)
- ✅ Plugin disable via `openclaw plugins disable` (não jq)
- 🔄 Após 7 dias estáveis: aposentar nosso filtro `extractMessages` em `session-distill.ts` se v.25 transient heartbeats funcionarem
- 🔄 Após 14 dias estáveis: validar se `chattr +i` ainda necessário ou se `#70902` OAuth sync graceful o suficiente

### 7.2 Phase 9 — Runbook reutilizável (deliverable)
Ver: `docs/RUNBOOKS/openclaw-upgrade-runbook.md` (próximos updates v.26+)
Ver: `docs/RUNBOOKS/openclaw-v25-upgrade-paper.md` (público)

---

## 8. Memorias a atualizar (post-fix)

Itens pra adicionar/atualizar em `~/.claude/projects/.../memory/`:

1. **`feedback_v25_native_cli_via_wizard.md`** (novo) — `openclaw config` wizard é canonical pra v.25, adiciona registry entries que doctor não fixaria
2. **`feedback_chattr_keep_immutable.md`** (novo) — NUNCA remover preventivamente; #70902 OAuth sync é não-fatal
3. **`feedback_token_audit_check_values_not_just_presence.md`** (novo) — Token audit deve incluir HTTP test (200/401/429), não só "tem apiKey?"
4. **`feedback_subagent_findings_validate_critical.md`** (novo) — Sub-agent reports são hipótese; permission errors silenciosos
5. **`reference_v25_canonical_paths.md`** (novo) — `agentRuntime.id`, `anthropic:claude-cli` provider entry, `claude-cli/` prefix removido
6. **Atualizar `feedback_openclaw_24_breaks_claude_cli_harness.md`** → resolved em v.25 #71957
7. **`feedback_heartbeat_design_uses_gemini.md`** (novo) — sessions :main com gemini-flash-lite após heartbeat são DESIGN, não bug
