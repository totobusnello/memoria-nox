# Security audit pós-marathon — 2026-04-29

> Pós OpenClaw v.25→v.26 (`2026.4.26`), monkey-patch reaplicado (hash `BQxFGeFd`), cron `cross-agent-sync` adicionado 5:30 BRT hoje. Verificação prod-state via SSH (regra mem `feedback_audit_must_check_prod_state_not_only_code.md`).
> Auditor: security-reviewer.

## CRITICAL (bloqueia operação)

### C1 — 14 apiKeys literais em configs de agents (regra 1)
**Cmd:** `grep -rE "apiKey.*[\"']sk-|apiKey.*[\"']AIzaS|apiKey.*[\"']gsk_" /root/.openclaw/agents/*/agent/*.json`
**Output:** 14 hits em 14 arquivos (auth-profiles.json + models.json) pra **todos os 7 agents** (atlas/boris/cipher/forge/lex/main/nox). Inclui `agents/atlas/agent/models.json: "apiKey": "AIzaSy…[REDACTED]"` — mesma chave Gemini literal nos 7 agents. 7 ocorrências `sk-…` em `auth-profiles.json` (anthropic-max OAuth tokens persistidos literais).
**Risco:** mesma chave Gemini foi revogada antes (incident 2026-04-21). Literal `sk-ant-oat` tokens em disk burlam regra "tudo via `${VAR}`". Se gitleaks ausente (C2) + git-add → leak imediato.
**Fix:** rotação `.env` + envsub workflow (mem `project_openclaw_key_rotation_workflow.md`); `openclaw config set` per-agent referenciando `${GEMINI_API_KEY}` e `${ANTHROPIC_OAUTH_TOKEN}`.

### C2 — Ausência de gitleaks pre-commit hook em `/root/.openclaw/workspace/.git/`
**Cmd:** `ls -la /root/.openclaw/workspace/.git/hooks/pre-commit`
**Output:** vazio. Hook prometido pela regra 1 ("bloqueado globalmente por gitleaks pre-commit hook") **não está instalado** nesse repo.
**Risco:** combinado com C1, qualquer `git add agents/*/agent/*.json` vaza 14 secrets.
**Fix:** instalar via `pre-commit` framework + testar com `gitleaks protect --staged`.

### C3 — `nox-mem.db` com perms 0644 (world-readable) — REGRESSÃO PÓS-UPGRADE
**Cmd:** `stat -c "%a %U:%G %n" /root/.openclaw/workspace/tools/nox-mem/nox-mem.db`
**Output:** `644 root:root … nox-mem.db` (1.0 GB com embeddings, golden queries, telemetria `query_text` opt-in).
**Risco:** regra 15 manda 0600 (paralelo aos snapshots, que continuam 0600 OK). Drift introduzido pelo upgrade v.26 ou cron novo. Qualquer user não-root no host lê PII de queries + chunks.
**Fix:** `chmod 600 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db*` (incluir `-wal` `-shm`).

## HIGH (corrigir hoje)

### H1 — Cron `cross-agent-sync` 5:30 sem timeout per-step
**Cmd:** `crontab -l | grep cross-agent-sync`
**Output:** `30 5 * * * set -a && source /root/.openclaw/.env … && bash …/cross-agent-sync.sh >> nox-mem.log 2>&1`
**Risco:** memória `feedback_serial_pipeline_steps_need_timeout.md` (incident 04-27 vectorize gap). Script novo, perms 0755 OK, owner root OK — mas sem `timeout N` interno. Se travar, downstream `sync-verify.sh` 6:00 trava também.
**Fix:** wrap cada step com `timeout 600 … || log_fallback`.

### H2 — Memória CLAUDE.md desatualizada sobre status canônicos `ops_audit`
**Cmd:** `sqlite3 nox-mem.db "SELECT sql FROM sqlite_master WHERE name='trg_ops_audit_terminal_immutable';"`
**Output:** trigger usa `('success','failed','crashed')` como terminal. CLAUDE.md regra 15 + prompt diziam `('started','completed','failed','rolled_back')`. **Trigger é a verdade**; docs/memória estão drift.
**Risco:** auditor futuro reage a falso-positivo.
**Fix:** atualizar `docs/CONVENTIONS.md` + memória → `('started','running','success','failed','crashed')`.

## MEDIUM (próxima sessão)

### M1 — Triggers ops_audit cobrem UPDATE+DELETE; INSERT direto não é bloqueado
**Risco:** atacante com SQL access pode `INSERT … (status='success', …)` forjando audit completo fora de `withOpAudit`. Surface pequena (root-only DB) mas spec append-only idealmente bloqueia INSERT ad-hoc.
**Fix:** trigger BEFORE INSERT validando `status='started'` na criação.

### M2 — 3 rows `crashed` em `ops_audit` sem evidência de safeRestore correlato
**Cmd:** `SELECT status, COUNT(*) FROM ops_audit GROUP BY status` → `crashed|3, failed|6, success|4`.
**Risco:** crashes sem rollback automático evidenciado. Validar se `safeRestore()` foi acionado.
**Fix:** correlacionar `id, op, started_at, snapshot_path` com `pre-op/*.db` retidos.

## LOW (OK — informativo)

- L1: monkey-patch #62028 OK — `restart-stale-pids-BQxFGeFd.js` (v.26 hash), 7x `return [];`, marker `MONKEY_PATCH_62028` presente.
- L2: `chattr +i` íntegro em `/root/.claude/.credentials.json` + `/usr/local/bin/openclaw-gateway-wrapper`.
- L3: token consistency OK — `ENV_LIVE=EMPTY`, `#DISABLED_CLAUDE_CODE_OAUTH_TOKEN=` presente, credentials.json válido `sk-ant-oat01-Ry…`.
- L4: drop-in `IS_SANDBOX=1` + `OPENCLAW_SERVICE_REPAIR_POLICY=external`.
- L5: snapshot dir `700`, snapshot files `600`.
- L6: delivery-queue limpa (0 items).
- L7: `trg_chunks_delete_cascade` presente.

## Resumo

- **Findings totais:** 12 (3 CRITICAL, 2 HIGH, 2 MEDIUM, 7 LOW OK).
- **Regressões pós-upgrade detectadas:**
  - **C3** — perms DB 0600→0644 durante v.26 reindex/vectorize ou cron novo
  - **C1** — escopo expandido (forge agora também)
  - monkey-patch hash trocou corretamente (não é regressão)
- **Recomendação G01 amanhã 2026-04-30:** ⛔ **NO-GO** até C1+C2+C3 corrigidos.
  - C3 = `chmod 600` (30s)
  - C2 = setup gitleaks (15min)
  - C1 = envsub refactor + restart cascata (~1h)
  - H1+H2 mesma janela

## File paths (absolutos)
- `/root/.openclaw/agents/{atlas,boris,cipher,forge,lex,main,nox}/agent/{auth-profiles,models}.json` — C1
- `/root/.openclaw/workspace/.git/hooks/pre-commit` — C2 (ausente)
- `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` — C3
- `/root/.openclaw/workspace/tools/cross-agent-sync.sh` — H1
- `/Users/lab/Claude/Projetos/memoria-nox/CLAUDE.md` — H2 (regra 15 desatualizada)
- `/usr/lib/node_modules/openclaw/dist/restart-stale-pids-BQxFGeFd.js` — L1 (OK)
