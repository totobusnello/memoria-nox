# Post-Marathon Audit — 2026-04-29 (CONSOLIDADO)

> Audit triplo (architect-reviewer + security-reviewer + code-reviewer) pós optimization marathon (04-28) + Sprints A1-A6 (04-27).
> Driver: memória `feedback_audit_critical_modules_same_session.md` — smoke tests happy-path não cobrem adversarial.
> Audits individuais: `2026-04-29-architect-drift.md`, `2026-04-29-security-pos-marathon.md`, `2026-04-29-code-review-a1-a6.md`.

---

## Sumário executivo

**Recomendação G01 (amanhã 04-30): ⛔ NO-GO até CRITICAL fixed.**

| Severity | Architect | Security | Code | Total |
|---|---|---|---|---|
| **CRITICAL** | 0 | 3 | 4 | **7** |
| **HIGH** | 3 | 2 | 6 | 11 |
| **MEDIUM** | 4 | 2 | 6 | 12 |
| **LOW** | 4 | 7 (OK) | 4 | 15 |
| **Total** | 11 | 14 | 20 | **45** |

**Tempo estimado pra fix CRITICAL:** ~2-3h.
**Janela disponível antes G01:** ~24h.
**Decisão proposta:** corrigir CRITICAL hoje + HIGH amanhã manhã, executar G01 04-30 à tarde com sistema validado.

---

## 7 CRITICAL bloqueando G01

### 🔴 SEC-C1 — 14 apiKeys literais em configs de agents (regra 1 violada)
- **Validado** via `ssh + grep`: 7 anthropic OAuth tokens (`sk-ant-oat01-Ry…`) + 6 Gemini keys (`AIzaSyBnyA1s81…`) + 1 main Gemini diferente.
- **Risco:** revogação Gemini incident 04-21 pode repetir; combo com SEC-C2 ausência gitleaks → leak imediato em qualquer `git add`.
- **Files:** `/root/.openclaw/agents/{atlas,boris,cipher,forge,lex,main,nox}/agent/{auth-profiles,models}.json`
- **Fix:** envsub refactor (`${GEMINI_API_KEY}`, `${ANTHROPIC_OAUTH_TOKEN}`) + restart cascata. ~1h.

### 🔴 SEC-C2 — gitleaks pre-commit hook ausente
- **Validado:** `/root/.openclaw/workspace/.git/hooks/pre-commit` não existe. Só `.sample` files.
- **Risco:** combo com SEC-C1 = bomba ativa.
- **Fix:** instalar `pre-commit` framework + `gitleaks protect --staged`. ~15min.

### 🔴 SEC-C3 — `nox-mem.db` perms 0644 (regressão pós-upgrade)
- **Validado:** `stat` retorna `644 root:root` no DB, WAL e SHM. Regra 15 manda 0600.
- **Causa:** v.26 reindex/vectorize ou cron novo regrediu perms.
- **Fix:** `chmod 600 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db*`. **30s.**

### 🔴 CODE-1 — `pdf-batch.sh` sem lockfile (race em 4.494 PDFs)
- Cron + manual run podem coexistir; race window 60s entre check e write → MD truncado.
- **Fix:** `flock -n 9` no topo. ~5min.

### 🔴 CODE-3 — `convert-office-to-md.sh` mtime idempotency vs rsync preserve-time
- rsync Mac→VPS preserva mtime → `.docx` parece "mais novo" que `.md` recém-gerado → reprocessa eternamente.
- **Fix:** marker file `.md.done`. ~10min.

### 🔴 CODE-4 — `cross-agent-sync.sh` workspace switch 6× sem lock vs watcher
- Loop 6 agentes sem flock → "database is locked" sob WAL pressure quando watcher dispara concorrente.
- **Fix:** `flock` per-agent. ~10min.

### 🔴 CODE-10 — `sync-verify.sh` `TOKEN=$(grep)` vaza pra `/proc/PID/environ`
- `Authorization: Bot $TOKEN` em curl → token visível em `ps -ef` durante chamada.
- **Fix:** `set -a; source .env; set +a; curl -H "Authorization: Bot ${DISCORD_BOT_TOKEN}"`. ~5min.

---

## 11 HIGH (corrigir antes Wave 1 Maio)

### Architect drift
- **ARCH-H1** ✅ F09 contradição ROADMAP/DECISIONS — **JÁ APLICADO** nesta sessão (F09→D22 CUT)
- **ARCH-H2** CLAUDE.md regra 6 cita hashes monkey-patch v.22/v.23 desatualizados; atual v.26 = `BQxFGeFd`
- **ARCH-H3** OpenClaw v2026.4.23 desatualizado em CLAUDE.md:41 + ROADMAP.md:18 → real **v2026.4.26**

### Security
- **SEC-H1** Cron 5:30 cross-agent-sync sem `timeout N` per-step (memória `feedback_serial_pipeline_steps_need_timeout.md`)
- **SEC-H2** CLAUDE.md regra 15 cita status `('started','completed','failed','rolled_back')` mas trigger DB usa `('success','failed','crashed')` — drift docs

### Code
- **CODE-5** pdf-batch.sh exit codes engolidos, SCANNED não loga path
- **CODE-6** release-watcher.sh `gh release list` sem auth fallback
- **CODE-7** upgrade-zero-downtime.sh:160 invoca `python3` num `.sh` (BUG — falha SyntaxError)
- **CODE-8** upgrade-zero-downtime.sh:413-426 journalctl failure mascarada
- **CODE-9** cross-agent-sync.sh exit code não capturado, heartbeat false-positive

---

## 12 MEDIUM (próxima sessão)

- **ARCH-M1** HANDOFF datado 04-27 (já corrigi pra 04-29 nesta sessão) ✅
- **ARCH-M2** improvements check real = 12 OK + 1 warn-only (HANDOFF dizia 13/13)
- **ARCH-M3** 8 cron entries novas não documentadas em CLAUDE.md regra 22
- **ARCH-M4** OpsAudit 0 ops/24h apesar de cron destrutivo rodar — investigar withOpAudit em consolidate
- **SEC-M1** ops_audit triggers cobrem UPDATE/DELETE mas não INSERT (forjável)
- **SEC-M2** 3 rows `crashed` em ops_audit sem evidência safeRestore
- **CODE-11** find|while read quebra em filenames com newline
- **CODE-12** pdf-batch hardcoded dirs PPR/PESSOAL/CONTRATOS/BANCOS
- **CODE-13** DB growth ~3.5GB/mês — out-of-disk em 12-15 meses sem VACUUM regular
- **CODE-14** upgrade-zero-downtime.sh `npm pack` sem audit signatures (supply-chain)
- **CODE-15** ckpt dist_hash captura symlinks
- **CODE-16** improvements `entries: {}` retorna OK (config corrompido passa)

---

## 15 LOW (polish + 7 informativos OK)

- **ARCH-L1** `.git` workspace 9.3GB pós-shrink prometido 134MB (backup auto-commit re-empurrou)
- **ARCH-L2** HEARTBEAT 04-29 confirmado ✅
- **ARCH-L3** section_boost distribution match ✅
- **ARCH-L4** Agent routing OK (nox+forge=opus, atlas+boris+cipher+lex=sonnet) ✅
- **SEC-L1** monkey-patch #62028 OK (BQxFGeFd v.26)
- **SEC-L2** chattr +i íntegro em credentials.json + wrapper
- **SEC-L3** token consistency OK
- **SEC-L4** drop-in IS_SANDBOX=1 OK
- **SEC-L5** snapshot dir 700, files 600
- **SEC-L6** delivery-queue limpa
- **SEC-L7** trg_chunks_delete_cascade presente
- **CODE-17/18/19/20** notify prefix, GNU PCRE, printf escape, emoji ssh

---

## Plano de execução proposto

### Fase 1 — Quick wins (~30min, hoje)
1. `chmod 600 nox-mem.db*` (SEC-C3) — 30s
2. `flock` em pdf-batch.sh, convert-office-to-md.sh, cross-agent-sync.sh (CODE-1, CODE-3, CODE-4) — 30min
3. Fix sync-verify.sh `Authorization` env var (CODE-10) — 5min

### Fase 2 — Hardening (~1.5h, hoje)
4. Setup gitleaks pre-commit (SEC-C2) — 15min
5. Envsub refactor 14 apiKeys + restart cascata (SEC-C1) — 1h
6. Validar tudo via `improvements check` + smoke test G01 dry-run

### Fase 3 — Drift fixes (~30min, amanhã manhã)
7. CLAUDE.md atualizar regra 6 hashes + regra 15 status enum (ARCH-H2, SEC-H2)
8. CLAUDE.md/ROADMAP bump versão v.23 → v.26 (ARCH-H3)
9. CLAUDE.md regra 22 atualizar inventário cron (ARCH-M3)

### Fase 4 — G01 amanhã 04-30 tarde
10. `bash /root/.openclaw/scripts/activate-salience.sh check` → `--apply` se READY

### Pós-G01 (Maio sprint)
11. HIGH #5-9 (observability gaps)
12. MEDIUM #11-16 (edge cases)
13. CODE-13 disk monitoring → adicionar em `improvements check`

---

## Decisão pendente do user

1. **Aprovar fase 1+2 hoje?** Custo ~2h, blast radius mínimo (SSH + chmod + flock + envsub).
2. **Adiar G01 pra 04-30 tarde** (após fixes) **vs** 05-01 (margem segurança extra)?
3. **Code-review #13 disk projection** — quer que adicione watchdog em `improvements check` agora?
