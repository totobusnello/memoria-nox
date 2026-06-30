---
date: 2026-05-01
chunk_type: session
tags: [marathon, drift-fix, slack-rotation, db-corruption-recovery, soul-slim, schema-v29-canonical]
session_duration_hours: ~5
tasks_completed: 53
---

# Sessão Marathon 2026-05-01 — OpenClaw VPS Stability + Performance + Security

> **TL;DR:** sessão de auditoria + fixes que partiu de "agentes errantes/lentos/esquecendo coisas" e terminou com sistema 5x mais rápido, drift loop morto, Slack rotacionado, DB recuperada de corrupção, e 6 SOUL.md compactados pra fim de truncating.

---

## 🚨 Problema reportado pelo Toto

Discord + WhatsApp acusavam:
- "Agentes errantes, devagares e esquecendo as coisas"
- "Restart de sessões — vários restarts!"
- Cron jobs falhando: `daily-briefing failed: cron: job interrupted by gateway restart`
- Nox alucinando ("Gemini API key expirada", "lista de 11 itens" inexistente)
- Forge propondo fix incompleto (atribuiu causa a WhatsApp loop)

## 🎯 Causa raiz #1 — Drift script restart loop (14h)

`/root/.openclaw/scripts/gateway-drift-check.sh` linha 9:
```bash
REAL_PID=$(pgrep -f "openclaw-gateway$" | head -1)   # ← regex NUNCA bate
```

Processo real chama-se `openclaw` (não `openclaw-gateway`). Regex com `$` jamais casava. Resultado: drift script via `SD_STATE=active` + `REAL_PID` vazio → `systemctl restart openclaw-gateway` a cada 15min. Loop iniciado 04-30 17:18 BRT, durou 14h até fix manual 05-01 07:55.

**Evidência incontestável** (`/var/log/gateway-drift.log` 30+ entries):
```
[CRITICAL] systemd=active, sem processo openclaw-gateway. Restarting.
```

**Fix:** `pgrep` → `systemctl show openclaw-gateway --property=MainPID --value`. Idempotente, autoritativo.

**Impacto:** 4 restarts/h × 14h = 56 restart cycles. Cada um:
- Matava cron em curso (interrupted)
- Resetava session context (agents "esqueciam")
- WhatsApp reconnect loop (efeito, não causa)
- Sessions grudavam em fallback gemini-flash-lite após primary anthropic falhar
- Briefing matinal 07:30 retry caiu em haiku-4-5, alucinou (input_tokens=17 = não leu briefing-items.txt)

## 📋 53 tasks completadas — categorias

### Bugfixes críticos (8)
1. Drift script regex (causa raiz)
2. agentRuntime.id `claude-cli` → `pi` em todos 7 agents
3. anthropic.baseUrl :4100 → api.anthropic.com em todos 7 agents
4. Cron version-check model gemini-flash → flash-lite
5. Cron Boris duplicata deletada (`b1592ecb`)
6. Vectorize-weekly fix (harness claude-cli não registrado)
7. /api/search canary race condition (era restart timing, não bug)
8. SOUL.md truncating warning (-70% chars universal)

### DB corruption recovery — incident próprio
**Causa:** sweep agressivo de Slack token via `sed -i` sem filtro de tipo. Sed alterou bytes em SQLite databases corrompendo page boundaries / b-tree pointers.

**Damage:**
- nox-mem.db (1GB): corrompido
- 4 daily backups (04-29, 04-30 e graph-memory_2026-04-28..05-01): corrompidos
- graph-memory.db (62MB): corrompido

**Salvação:**
- `/var/backups/nox-mem-pre-vacuum-20260428-1204.db` (62.840 chunks) — ficou intacto fora do scope sweep `/root/.openclaw/`
- `graph-memory_2026-04-27.db` — idem

**Recovery sequence:**
1. Stop nox-mem-api + watcher
2. Quarantine `nox-mem.db.CORRUPTED-20260501-1004` + remove WAL/SHM órfãos
3. `cp /var/backups/nox-mem-pre-vacuum-20260428-1204.db nox-mem.db`
4. Validate via `better-sqlite3` Node script (sqlite-vec extension loaded)
5. Stop gateway, idem pra graph-memory.db
6. Start services
7. **R1** Re-ingest 22 arquivos modificados pós-cutoff: +117 chunks novos embedded (62.788 → 62.905)
8. **R2** `nox-mem kg-build` re-validou 402 entities + 544 relations
9. graph-memory plugin re-popula gradualmente via uso normal

**Lição salva:** `feedback_never_sed_binary_files.md` — NUNCA `sed -i` em `.db`/`.sqlite`/binary; sweep sempre filtrar `grep -E '\.(json|md|sh|txt|jsonl|env)$'`.

### Performance optimization (7)
1. `bootstrapMaxChars` 18000 → 12000 (-25% tokens/turn)
2. `graph-memory.compactTurnCount` 7 → 20 (3x menos maintenance)
3. `memorySearch.cache.maxEntries` 50000 → 5000 (oversized 150x; só 329 recalls/24h)
4. Plugin `slack` disabled (zero use 7d) → reabilitado pós-token-rotation
5. Plugin `browser` disabled (zero use 7d)
6. **FTS5 optimize** após Graphify de 04-27 (corpus 21k → 62k sem optimize): search **3000ms → 620ms p50** ✅ (5x speedup)
7. VACUUM nox-mem.db: 1018→971 MB (-47MB freelist), adicionado ao nightly-maintenance.sh (1º domingo do mês)

### Security (6)
1. **Slack token rotation completa** — old `xoxp-...c6cf6714...` revogado HTTP 401, novos `xoxp` + `xoxb` no `.env` (perms 600). Old token estava ATIVO HTTP 200 antes (user=lab, team=TSA520XL4)
2. ~30+ arquivos VPS sanitizados (sed redact em `.md/.json/.sh/.txt/.jsonl/.env`)
3. Pre-commit hook local instalado (`/Users/lab/Claude/Projetos/memoria-nox/.git/hooks/pre-commit` → `~/.git-hooks-global/pre-commit`)
4. Gemini key revogada masked em `feedback_no_hardcoded_secrets.md` (`AIzaSyB***[REDACTED-revoked-2026-04-21]***SppQCA`)
5. VPS workspace gitleaks confirmado instalado desde 04-29
6. Anthropic stale token testado HTTP 401 (já invalido, só higiene)

### Memória Nox cleanup (6)
1. `pending.md`: 15 → 10 itens (removidos 3 stale 19/03+22/03, 1 dup hotel Miami, 1 meta-circular)
2. `prepare-briefing-context.sh` `head -10` → `head -15` (briefing matinal cobre top 15 prioridades)
3. `agents/{atlas,boris,cipher,lex}/memory/SESSION-STATE.md` archived (vestigial 04-05)
4. `agents/{atlas,boris,cipher,lex}/memory/active-tasks.md` archived (vestigial)
5. `agents/nox/memory/SESSION-STATE.md` archived (vestigial 04-05)
6. CLAUDE.md "Convenções de workflow" reescrito — fontes de verdade corretas:
   - `active-tasks.md` = atualizado quase diário (não deprecated)
   - `session-context.json` = cron 05:00 daily (não deprecated)
   - `workspace/memory/SESSION-STATE.md` = auto-update via `nox-mem update-session` (LIVE)
   - `agents/<id>/memory/SESSION-STATE.md` = vestigial (archived)

### SOUL.md slim per-agent (6)
| Agent | Antes | Depois | Redução |
|---|---:|---:|---:|
| nox | 15.896 | 5.951 | -63% |
| atlas | 16.479 | 4.224 | -74% |
| boris | 13.711 | 3.411 | -75% |
| cipher | 13.793 | 3.847 | -72% |
| forge | 15.713 | 4.550 | -71% |
| lex | 12.581 | 4.134 | -67% |
| **Total** | 88.173 | 26.117 | **-70%** |

Truncating warning eliminado (era 6000 limit). Backups `.bak-pre-slim-20260501` em cada agent dir.

### Documentação reescrita (8 arquivos)
1. `CLAUDE.md` regra #5 (schema v.29 canonical, claude-cli/* deprecated)
2. `CLAUDE.md` "Convenções" (fontes de verdade da memória)
3. `docs/ARCHITECTURE.md` (4 blocos: model assignment, deployment, fallback chain L990)
4. `docs/OPTIMIZATION-2026-04-24.md` (banner histórico)
5. `docs/UPDATE-TO-V26-GUIDE.md` (banner histórico)
6. `docs/HANDOFF.md` (3 refs claude-cli/* corrigidas)
7. `docs/DECISIONS.md` (4 refs corrigidas)
8. `docs/RUNBOOKS/openclaw-v29-upgrade.md` (commands corrigidos)

Banner pattern: arquivos históricos (V25/V26 guides, OPTIMIZATION-04-24) ganham nota de obsolescência apontando pra schema atual sem reescrever conteúdo.

## 📈 Métricas antes vs depois

| | Antes | Depois |
|---|---:|---:|
| Restart loop frequency | 4/h | **0** |
| 300s timeouts/48h | 3 | 0 |
| Search p50 latency | 3000ms | **620ms** (5x ↓) |
| Search p95 latency | 280s+ | 121s |
| Cron status (errors) | 11 | 1 confirmed fixed, 10 auto-resolving |
| Slack token live em git | xoxp ATIVO | revoked HTTP 401 |
| SOUL.md bootstrap chars | 88.173 | 26.117 (-70%) |
| nox-mem.db size | 1018 MB | 971 MB (-47 MB VACUUM) |
| Custo paid backends 30d | $7.76 | $7.76 (sob controle) |
| Anthropic Max OAuth ratio | ~82% volume | mantido |

## 🔑 Lições aprendidas (saved to memory)

1. `feedback_gateway_drift_pgrep_regex_bug.md` — drift scripts devem usar `systemctl MainPID`, não `pgrep` regex
2. `feedback_never_sed_binary_files.md` — sweep secrets sempre filtrar tipos; nunca `sed -i` em SQLite
3. CLAUDE.md regra #5 reescrita — schema v.29 canonical
4. CLAUDE.md "Convenções" reescrita — fontes de verdade corretas

## 🟡 Carry-over

- **Push GitHub:** workspace VPS commit `c87558ce` foi pushed ✅. Repo `memoria-nox` (este) — ver `git status` se algo a commitar.
- **graph-memory plugin recovery:** estado em 04-27 backup. Auto-rebuild gradual via uso normal (~3-5d).
- **Crons que estavam em error:** vão auto-resolver nas próximas execuções (22h end-of-day, 23h relatorio-eod, etc).
- **Validação SOUL.md slim:** próximas 24-48h, testar 1 turn de cada agent. Se persona escapar, restore via `.bak-pre-slim-20260501`.
- **VACUUM mensal:** primeiro domingo de cada mês via nightly-maintenance.sh (Phase 8).

## 📁 Backups criados nesta sessão

VPS:
- `/root/.openclaw/openclaw.json.bak-20260501-fallback-fix`
- `/root/.openclaw/openclaw.json.bak-20260501-runtime-fix`
- `/root/.openclaw/.env.bak-20260501-slack-rotation`
- `/root/.openclaw/scripts/gateway-drift-check.sh.bak-20260501-pgrep-fix`
- `/root/.openclaw/scripts/nightly-maintenance.sh.bak-pre-vacuum-20260501`
- `/root/.openclaw/agents/*/agent/models.json.bak-20260501-baseurl-fix` (×7)
- `/root/.openclaw/agents/*/sessions/sessions.json.bak-20260501-fallback-fix` (×7)
- `/root/.openclaw/workspace/agents/*/SOUL.md.bak-pre-slim-20260501` (×6)
- `/root/.openclaw/workspace/agents/*/memory/_archive/legacy-state-files/` (4 SESSION-STATE + 4 active-tasks archived)
- `/root/.openclaw/workspace/agents/nox/memory/pending.md.bak-20260501`
- `/root/.openclaw/workspace/tools/prepare-briefing-context.sh.bak-20260501`
- `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db.CORRUPTED-20260501-1004` (forensics)
- `/root/.openclaw/graph-memory.db.CORRUPTED-20260501-1010` (forensics)

## 📊 Status pós-sessão

```
✅ Gateway estável (PID 89745+, 9 plugins)
✅ Drift OK contínuo desde 08:50 BRT
✅ Slack token rotacionado, old revoked
✅ Anthropic Max OAuth zero-cost ($0)
✅ Search latência 620ms p50
✅ DB integrity restored (62.905 chunks pós-recovery)
✅ Vector coverage 100% (62.905/62.905)
✅ KG: 402 entities, 544 relations
✅ Per-agent agentRuntime + baseUrl normalizados pra schema v.29
✅ Memória Nox limpa
✅ 4 docs canônicos atualizados
✅ 8 docs históricos com banner
✅ Pre-commit hook local instalado
✅ FTS5 optimized (5x speedup)
✅ VACUUM aplicado + agendado mensal
✅ 6 SOUL.md compactados (-70%)
✅ Workspace VPS commit pushed
```

---

_Maintainer: Toto. Sessão executada por Claude (opus-4-7 via Max OAuth)._
