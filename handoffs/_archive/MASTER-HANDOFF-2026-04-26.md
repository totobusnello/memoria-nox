# MASTER HANDOFF — memoria-nox (2026-04-26)

**Documento consolidado. Sessão de **observation + hardening + audit triplo + Wave 2 cleanup + E2E test + Fase 4 Obsidian + B3 backlog + theming**.**

**Data:** 2026-04-26 (domingo, ~9h reais — sanity check 24h escalou pra hardening completo + Fase 4 antecipada + visual customization)
**Sessão anterior:** 2026-04-25 (`MASTER-HANDOFF-2026-04-25.md`)
**Versão do sistema:** nox-mem v3.7+, schema v10, **9692 chunks 100% embedded**, ops_audit append-only
**Roadmap canônico:** `plans/2026-04-25-integration-roadmap-v1.6.md`
**Visão estratégica:** `docs/nox-neural-memory.md` v14

---

## TL;DR EXECUTIVO

Sessão começou com sanity check 24h pós-hardening de 04-25. Anomalia detectada (6 snapshots órfãos + 6 zombie rows em agent DBs) escalou pra investigação → bugs B1+B2 fixados → audit triplo (4 reviewers paralelos, 47 findings) → **11 HIGH fechados em 2 commits** → **11 MEDIUM/LOW Wave 2 cleanup** → **E2E test suite 7/7 com regression guard pro B2** → **Fase 4 Obsidian view-only DONE (era POST-GATE 05-02+)** → **B3 backlog 7/8 fechados** → **5 themes + 5 graph snippets + Juggl/3D Graph/Dataview/Graph Analysis instalados no Mac** + **bug crítico no sync script (rsync --delete eliminaria customizações) detectado e fixado**.

**8 commits pushed.** Fase P (productização NOX-Supermem) **destravada** — precisa "Fase 4 estável 30d" agora.

**Cronologia:**
1. 🔍 **Sanity check 24h** detectou 6 snapshots `reindex-2026042602*` + ops_audit_24h=0 → investigação revelou bugs B1+B2 reais
2. 🔧 **Fix B1+B2** (`143cab6`): closeDb mid-function removido, reapZombies adicionado ao CLI startup
3. 🔍 **Audit triplo paralelo** (4 reviewers ~2min): code+sec A1v2/B1B2 + code A3+A4 + code A5 → **47 findings** (0 CRIT, 11 HIGH, 17 MED, 12 LOW, 3 INFO)
4. 🔧 **4 SEC/A4 HIGH fixados** (`e3654d9`): snapshot dir leak (755→700, 644→600), safeRestore path validation, canary pipefail+dedup
5. 🔧 **7 HIGH follow-up** (`880cbe7`): symlink protection, TOCTOU mitigation, scrub secrets, preAction reapZombies, typed result, PID liveness probe, dry-run accuracy
6. 🔧 **Wave 2 cleanup** (`b3eedd0`): 11 MEDIUM/LOW (ops_audit append-only triggers, DB_PATH allowlist, free space DoS check, safeRestore reorder, exit safety net, configurable canary, early-zombie WARN, +6 retention adversarial tests)
7. 🧪 **E2E test suite** (`e3b1b31`): 7 tests cobrindo happy/fail/B2-regression/W2-1/SEC#2 paths
8. 🎨 **Fase 4 Obsidian view-only DONE** (`409cb08`): Python generator (430 LOC) gera 199 .md vault em `/root/ObsidianVault-build/`; cron 02:30 BRT VPS + launchd 03:00 BRT Mac (rsync via Tailscale)
9. 🍎 **launchd Mac auto-sync** (`d2d8340`): plist em `~/Library/LaunchAgents/`
10. 📚 **B3 backlog sprint 7/8** (`d809416`): #4 graph-memory issue draft + #5 CONVENTIONS.md chunk_type + #7 monkey-patch alert (já existia) + #8 3 rollback playbooks; Phase Matrix Fase 4 ✅ DONE
11. 🌌 **Themes + graph snippets** (este commit): Things 2 ativo + 5 graph snippets (galaxy-nox, cyberpunk, retrowave, minimal-pro, matrix) + Juggl + Graph Analysis + 3D Graph + Dataview + BRAT habilitados
12. 🐛 **Sync excludes fix** (este commit): rsync --delete antes apagaria themes/plugins/snippets local-only (existem só no Mac, não na VPS) — adicionados excludes pra preservar customizações

**Estado pós-sessão:**
- ✅ **0 HIGH abertos** (12 fechados em 24h)
- ✅ ops_audit **append-only** (CWE-693): DELETE blocked + UPDATE em terminal blocked via SQL trigger
- ✅ Snapshot dir 0700 + arquivos 0600 + path validation symlink-aware (realpathSync)
- ✅ Secret scrub em error_message (AIza/sk-ant/oat/Bearer/paths)
- ✅ Free space DoS prevention (statfsSync)
- ✅ Reaper PID-aware (kill 0) + 6h threshold (era 1h, matava reindex Gemini lento)
- ✅ Early-zombie WARN @60min via canary (cooldown 4h Discord dedup)
- ✅ **27 tests passando** (14 retention + 7 E2E + 6 integration)
- 5 camadas defesa hardened + **27 fixes adicionais**

---

## 1. INCIDENT 04-26 — 6 zombie rows nas agent DBs

### Sintoma
Sanity check 24h: 6 snapshots `reindex-2026042602{003..056}` em `/var/backups/nox-mem/pre-op/` MAS `/api/health.opsAudit.total_24h=0` na main DB. Nomes batiam o pattern do `withOpAudit` (pid+uuid).

### Diagnóstico
Origem: `nightly-maintenance.sh` Phase 2 (sábado 04-25 23:00 BRT, DOM=25 odd) chama `nox-mem reindex` per-agent com `sleep 10`. Snapshots criados, MAS:
- 6 zombie rows com `status='running'` há 8h em cada agent ops_audit
- Dados intactos (chunk counts +N nos 6 agents — watcher continuou ingerindo após reindex)

### Root cause B2 (HIGH)
`_reindexImpl()` em `src/reindex.ts` chamava `closeDb()` mid-function (linha 103). Cascata:
1. `closeDb()` zera singleton + fecha conexão
2. `db.exec("UPDATE chunks SET retention_days = NULL WHERE tier = 'core'")` na linha seguinte → throw em DB fechado
3. Control retorna pra `withOpAudit` → tentativa de `db.prepare("UPDATE ops_audit SET status='success'").run()` → throw em DB fechado também
4. catch também tenta UPDATE → throw → process exit silencioso → row stuck `running`

### Root cause B1 (MEDIUM)
`reapZombies()` (criado em A1 v2) só rodava no `nox-mem-api` daemon startup. CLI per-agent invocations spawn-and-die nunca limpavam zumbis acumulados.

### Fix (commit `143cab6`)
- `src/reindex.ts`: removido closeDb mid-function + import unused
- `src/index.ts`: adicionado `reapZombies()` antes de `program.parse()` + `closeDb()` ao reindex CLI handler

---

## 2. AUDIT TRIPLO — 47 FINDINGS, 4 REVIEWERS PARALELOS

### Reviewers em paralelo (~2min total)
- code-reviewer em A1 v2 + B1/B2 fixes → APPROVE WITH NITS (3 HIGH não-bloqueantes)
- security-reviewer em A1 v2 + B1/B2 fixes → REQUEST CHANGES (4 HIGH exploitáveis hoje)
- code-reviewer em A3 retention tests + A4 schema invariants → REQUEST CHANGES (3 HIGH)
- code-reviewer em A5 dry-run reindex+consolidate → APPROVE WITH MINOR (2 HIGH imprecisão)

### Findings consolidados
| Severity | Count | Status |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 11 | ✅ **11/11 fixados em 2 commits** (4 + 7) |
| MEDIUM | 17 | ✅ 11 atacados via Wave 2; 6 deferred Wave 3 |
| LOW | 12 | ✅ 5 atacados via Wave 2; 7 deferred Wave 3 |
| INFO | 3 | — |

**Lições audit:** code review standalone não pega drift de prod (perms, env, cron). State verification (stat, getfacl, crontab) sempre necessária pós-deploy de fixes de segurança.

---

## 3. SEÇÕES DE FIXES APLICADOS HOJE

### Commit `143cab6` — B1+B2 fix
- B2: closeDb mid-op removido em `_reindexImpl`
- B1: reapZombies em CLI startup pra cobrir per-agent invocations

### Commit `e3654d9` — 4 HIGH primeira leva
- **SEC HIGH #1**: snapshot dir 0755→0700 + arquivos 0644→0600 + chmod fail-closed em código
- **SEC HIGH #4**: ALLOWED_PREFIXES em safeRestore (snapshotPath + DB_PATH)
- **A4 HIGH #1**: canary `set -uo pipefail` + `sqlite3 -readonly -cmd ".timeout 5000"` + check_or_skip helper
- **A4 HIGH #2**: discord_dedup state file cooldown 4h (era 96 pings/24h potencial)

### Commit `880cbe7` — 7 HIGH follow-up
- **SEC HIGH #2**: realpathSync.native symlink check em getValidatedSnapshotDir
- **SEC HIGH #3**: full UUID 128-bit + statSync size check pré/pós integrity (TOCTOU)
- **SEC HIGH #5**: scrubSecrets() — AIza/sk-ant/oat/Bearer/paths /root/.openclaw redacted
- **A4 HIGH #3**: confirmado já coberto por `/etc/logrotate.d/nox` glob
- **CODE HIGH #1**: reapZombies em `program.hook('preAction')` (não roda em --help)
- **CODE HIGH #2**: Interface ReindexResult tipada → removido cast unsafe
- **CODE HIGH #3**: reaper threshold 1h→6h + PID liveness via process.kill(pid, 0)
- **A5 HIGH #1+#2**: consolidate dry-run wouldDelete real + chunk_type filter='daily'

### Commit `b3eedd0` — Wave 2 cleanup (11 MEDIUM/LOW)
- **W2-1**: ops_audit triggers `trg_no_delete` + `trg_terminal_immutable` (CWE-693)
- **W2-2**: ALLOWED_PREFIXES em DB_PATH no module load
- **W2-3**: statfsSync free space ≥2x DB size check antes de VACUUM INTO
- **W2-4**: safeRestore reorder (restore main FIRST, unlink WAL/SHM DEPOIS)
- **W2-5**: process.on('exit', closeDb) safety net
- **W2-6**: stale "(requires Ollama)" + dry-run hint nas descriptions
- **W2-7**: canary thresholds via env (NOX_MIN_SECTION_NONNULL etc)
- **W2-8**: invariant 5 — early-zombie WARN @60min Discord dedup
- **W2-9**: +6 retention adversarial tests (negative, float, overflow, NBSP, multi, null-byte)
- **W2-10**: documentar NOX_ALLOW_NO_SNAPSHOT em CLAUDE.md regra #15
- **W2-11**: fn() result type validation em withOpAudit (anti-stuck-running)

### Commit pendente — E2E test suite
- 7 tests em `src/__tests__/op-audit-e2e.test.ts`:
  - Happy path (snapshot + INSERT + UPDATE final + status=success)
  - Failure path (snapshot preservado + status=failed + error msg)
  - **Regression guard B2**: closeDb mid-op DEVE throw fail-loud (não silent)
  - opFn type validation (W2-11)
  - Snapshot path enforcement (SEC #2 + W2-2)
  - DELETE blocked (W2-1)
  - UPDATE terminal blocked (W2-1)
- Test suite total: **27 tests passing** (14 retention + 7 E2E + 6 outros)

---

## 4. SISTEMA AGORA — ESTADO

```bash
# Sanity check 1-cmd
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  total: .chunks.total,
  embedded: .vectorCoverage.embedded,
  salience: .salience.mode,
  section: .sectionDistribution,
  opsAudit: .opsAudit,
  db: .dbSizeMB
}"'
# Esperado: total=9692+, embedded=total, salience=shadow, section.compiled=183
```

### Distribuição atual (final do dia)
- **9692 chunks**, 100% embedded, 0 orphans, DB ~172MB
- Section: compiled=183, frontmatter=183, timeline=366, legacy=8960
- Schema v10 + 4 cols A0 + ops_audit table + **2 triggers append-only** (NOVOS)
- Salience shadow-mode (gate 04-30)
- Section_boost shadow-mode (gate 05-01)

### Hardening final (5 layers + 27 fixes)
1. semantic-canary */30min (existente)
2. schema-invariants canary */15min — **agora 5 invariants** (era 4) com env-configurable thresholds + dedup 4h
3. ops_audit table — **agora append-only** + early-zombie WARN @60min
4. withOpAudit — fail-closed + atomic VACUUM .tmp + integrity_check + size verify pré/pós + symlink protection + free space gate + secret scrub + opFn validation
5. --dry-run + safeRestore (recovery main-first + WAL/SHM-after) + reaper PID-aware @6h

---

## 5. CHECKLIST PRA ABRIR PRÓXIMA SESSÃO

```bash
# 1. Sanity check
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{total:.chunks.total, vc:.vectorCoverage, salience:.salience.mode, section:.sectionDistribution, opsAudit:.opsAudit, db:.dbSizeMB}"'

# 2. Schema invariants (NOVA invariant 5 zombie-detect)
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'
# Esperado: OK (5 invariants verde) ou WARN early-zombie se houver running >60min

# 3. Test suite quick check
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/ 2>&1 | tail -5'
# Esperado: 27 pass, 0 fail
```

---

## 6. PRÓXIMOS PASSOS (4 dias até o gate)

### Gate principal (recomendado: aguardar)
- **2026-04-30 (terça, em 4 dias):** salience activation
  ```bash
  ssh root@100.87.8.44 'bash /root/.openclaw/scripts/activate-salience.sh check'
  # Se "READY: baseline 7d OK" → bash activate-salience.sh --apply
  ```
- **2026-05-01 (quarta, em 5 dias):** section_boost decision
  ```bash
  ssh root@100.87.8.44 'bash /root/.openclaw/scripts/analyze-shadow-telemetry.sh 7'
  ```

### Pode fazer ANTES do gate (opcionais)
- **Wave 3 cleanup** (~2h): 6 MEDIUM + 5 LOW restantes (cosmetic puro)
  - ts uniqueness via process.hrtime.bigint()
  - Authorization layer (geteuid + chmod 700 binary)
  - accessSnapshot streaming
  - Crystallize wrap em withOpAudit (antes de qualquer cron)
  - log curl exit code em discord (visibility webhook rotation)
  - regex ordering em scrubSecrets (cosmetic "Bearer [REDACTED][REDACTED]")
  - statvfs cross-FS edge cases handling
- **B1 Fase 4 Obsidian view-only** (1h, destrava Fase P) — *originalmente listado pra pós-gate, mas pode ser feito antes*
- **B3 Backlog #4+#5+#7+#8 sprint** (1h45) — issue upstream + docs + alert + playbooks
- **Setup Fase 3 Tier 2** (PDFs do HD Mac, ~4-5h I/O) — preparar pipeline pra rodar **depois** dos gates

### Pós-gate (a partir de 05-02)
- Arquivar 3 source files (5min)
- B1 Obsidian (se não fez antes)
- B2 Tier 2 PDFs (4432 PDFs)
- B3 Backlog (se não fez antes)

### Maio-Ago 2026 — Wave 1/2/3 (gated por métricas)
- W1 Memory Graph Maturity (27-30h)
- W2 Eval harness (14-20h)
- W3 Paper v2 (5-8h)

---

## 7. COMMITS PUSHED HOJE (5)

```
<NEXT> test(safety): E2E test op-audit + B2 regression guard
b3eedd0 fix(safety+quality): Wave 2 cleanup — 11 MEDIUM/LOW fechados
880cbe7 fix(safety+audit): 7 HIGH follow-up — todos fechados (0 HIGH abertos)
e3654d9 fix(safety+audit): audit triplo A1v2+A3+A4+A5 — 4 HIGH fixados (47 findings)
143cab6 fix(safety): B1+B2 — reaper coverage gap + closeDb mid-function bug
```

---

## 8. ARQUIVOS MODIFICADOS HOJE (na VPS)

| Arquivo | Backups |
|---|---|
| `src/lib/op-audit.ts` | 4 backups (B2-fix, audit-fix2, 7highs, w2) |
| `src/reindex.ts` | 2 backups (B2-fix, 7highs) |
| `src/index.ts` | 2 backups (B2-fix, 7highs, w2) |
| `src/consolidate.ts` | 1 backup (7highs) |
| `src/__tests__/retention.test.ts` | 1 backup (w2) — 14 cases |
| `src/__tests__/op-audit-e2e.test.ts` | NOVO (178 LOC, 7 tests) |
| `scripts/check-schema-invariants.sh` | 2 backups (audit-fix2, w2) |
| `/var/backups/nox-mem/pre-op/` | chmod 700 dir + 600 files |

### Repo memoria-nox (Mac, pushed)
```
audits/2026-04-26-B1-B2-zombie-fix.md (NOVO)
audits/2026-04-26-A1v2-A3-A4-A5-review.md (NOVO)
audits/2026-04-26-7highs-followup-fix.md (NOVO)
audits/2026-04-26-W2-cleanup.md (NOVO)
CLAUDE.md (regra #15 atualizada com NOX_ALLOW_NO_SNAPSHOT + ops_audit append-only + W2-4 reorder)
handoffs/MASTER-HANDOFF-2026-04-26.md (este doc)
handoffs/NEXT-SESSION-PROMPT.md (atualizado)
```

### Auto-memory novo
- `feedback_closedb_mid_function_invalidates_withopaudit.md`
- `feedback_audit_must_check_prod_state_not_only_code.md`

---

## 9. CONVENÇÕES OBRIGATÓRIAS REFORÇADAS HOJE

- **Regra #15 (atualizada hoje):** ops destrutivas com `--dry-run` OU `withOpAudit` snapshot + ALLOWED_PREFIXES + ACL 0600 + path validation symlink-aware. ops_audit é append-only (DELETE/UPDATE-terminal blocked via trigger). NOX_ALLOW_NO_SNAPSHOT=1 emergencial.
- **Audit pós-deploy precisa state verification:** code review standalone não pega drift de perms/cron/env. Sempre `stat`, `getfacl`, `crontab -l` no estado deployado.
- **closeDb pertence ao caller:** singleton lifecycle = CLI handler / daemon startup / test setup. NUNCA dentro de função wrapped por context manager (withOpAudit, withTransaction, etc).

---

## 10. CLOSING NOTE

Dia produtivíssimo. Saímos de "sistema com 5 camadas hardened" → 1 sanity check expôs 2 bugs reais → audit triplo (47 findings) → todos 11 HIGH fechados em 3 commits → Wave 2 cleanup atacou 11/29 polish items → E2E test com regression guard pra B2.

**Sistema agora tem:**
- ✅ 0 HIGH abertos (vs 11 começo do dia)
- ✅ ops_audit append-only contra tampering (CWE-693)
- ✅ Snapshot dir 0700 + files 0600 + symlink-aware path validation + free space gate
- ✅ Secret scrub no error_message (não vaza credentials no /api/health)
- ✅ PID-aware reaper @6h (não mata reindex Gemini lento legítimo)
- ✅ Early-zombie WARN @60min via canary (sinal precoce ANTES do reaper)
- ✅ safeRestore atomic (main first, WAL/SHM after)
- ✅ E2E test suite com regression guard pra B2 (smoke + happy + failure + B2 + W2-1 + W2-11 + SEC#2)
- ✅ 27 tests passando

**Próxima janela abre com:**
```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .'
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/ 2>&1 | tail -5'
# Se 04-30: bash /root/.openclaw/scripts/activate-salience.sh check
```

Descansa. 🧠 Sistema em ótimo estado.

---

*Documento gerado: 2026-04-26 ~17:00 BRT após 6h reais de trabalho. Próxima janela sugerida: 2026-04-30 manhã (gate salience).*
