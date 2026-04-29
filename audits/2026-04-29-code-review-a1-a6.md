# Code review sprints A1-A6 — 2026-04-29

> Auditor: code-reviewer. Method: review estática de scripts modificados em A1-A6 + cross-validation contra memórias `feedback_*`.

## CRITICAL (data loss / corruption risk)

### [1] pdf-batch.sh:9 — `set +e` + sem lockfile + 4.494 PDFs concorrentes
**File:** `/root/.openclaw/scripts/pdf-batch.sh:9`
Cron + manual run podem coexistir. `[ -f "$md" ] && [ "$md" -nt "$f" ]` race window de ~60s (timeout markitdown) entre check e write. Duas instâncias na mesma subdir geram MD truncado.
**Fix:** `exec 9>/var/lock/pdf-batch.lock; flock -n 9 || exit 1` no topo.

### [2] convert-office-to-md.sh:6 — `set -e` colide com `2>/dev/null` em fallbacks
**File:** `/root/.openclaw/scripts/convert-office-to-md.sh:6,15-17`
Markitdown grava `.md` antes de exit code chegar; se `set -e` aborta script no meio do loop, fica MD parcial sem cleanup.
**Fix:** `set -uo pipefail` (não `-e`); escrever em tempfile + `mv` atômico.

### [3] convert-office-to-md.sh:42 — mtime idempotency vs rsync preserve-time
**File:** `/root/.openclaw/scripts/convert-office-to-md.sh:42`
`-nt` resolução em segundo. rsync Mac→VPS preserva mtime do source → `.docx` parece "mais novo" que `.md` recém-gerado, reprocessa eternamente. ext4 noatime amplifica.
**Fix:** marker file `.md.done` ou comparar tamanho ≠ 0 + checksum.

### [4] cross-agent-sync.sh:20 — workspace switch 6× sem lock vs watcher concorrente
**File:** `/root/.openclaw/workspace/tools/cross-agent-sync.sh:20`
`OPENCLAW_WORKSPACE=... node $NOX_MEM pull-shared` 6 agentes em loop. Watcher inotify (debounce 15s) pode disparar ingest no mesmo DB → "database is locked" sob WAL pressure. Cron 05:30 confirmado.
**Fix:** `flock` per-agent; validar WAL mode em `nox-mem`.

## HIGH (silent failures / regressões)

### [5] pdf-batch.sh:20-25 — exit codes engolidos, SCANNED não loga path
Memória `feedback_scanned_pdf_heuristic.md`: <100 chars descartado mas script só incrementa contador, nunca loga **qual** PDF foi pra Tier 3. Gate OCR fica cego.
**Fix:** `echo "$f → scanned" >> $LOG`.

### [6] release-watcher.sh:40 — `gh release list` sem auth fallback
**File:** `scripts/release-watcher.sh:40,44`
Token expira → `LATEST_STABLE` vazio → exit 0 silencioso. Watcher fica permanente passive (memória `feedback_token_audit_check_values_not_just_presence.md`).
**Fix:** `gh auth status` no início; `notify` Discord antes de `exit 0`.

### [7] upgrade-zero-downtime.sh:160 — invoca `python3` num arquivo `.sh`
**File:** `scripts/upgrade-zero-downtime.sh:160`
`python3 /root/reapply-monkey-patch.sh "$STAGING_PATCH"` — bash invocado como módulo Python falha SyntaxError. O `||` cai no heredoc embutido por acidente.
**Fix:** `bash /root/reapply-monkey-patch.sh "$STAGING_PATCH"`.

### [8] upgrade-zero-downtime.sh:413-426 — journalctl failure mascarada
**File:** `scripts/upgrade-zero-downtime.sh:413-426`
Quando journalctl falha (perm/serviço), retorna stderr ignorado, `RESTARTS="0"`. Auto-rollback gate cego se journal quebrar durante upgrade.
**Fix:** validar journalctl returncode antes de grep.

### [9] cross-agent-sync.sh:11 — exit code do node não capturado, heartbeat false-positive
**File:** `cross-agent-sync.sh:11,18`
Se `pull-shared` falha runtime, regex `Imported \K[0-9]+` não bate, N=0, heartbeat "sistema vivo" mascara falha. Memória `feedback_validate_features_with_db_not_logs.md` aplicável.
**Fix:** capturar `$?` do node; só log "vivo" se exit==0.

### [10] sync-verify.sh:30 — `TOKEN=$(grep ...)` vaza pra `/proc/PID/environ`
**File:** `/root/.openclaw/workspace/tools/sync-verify.sh:30,38`
`Authorization: Bot $TOKEN` em curl → token aparece em `ps -ef` durante chamada. Memória `feedback_no_secrets_in_git.md` aplicável.
**Fix:** `set -a; source /root/.openclaw/.env; set +a; curl -H "Authorization: Bot ${DISCORD_BOT_TOKEN}"`.

## MEDIUM (edge cases / hardening)

- **[11]** convert-office-to-md.sh:53-56 — `find | while read` quebra em filenames com newline. Use `find -print0 | while IFS= read -r -d ''`.
- **[12]** pdf-batch.sh:15 — diretórios hardcoded `PPR PESSOAL CONTRATOS BANCOS`; novos dirs ignorados silenciosamente. Parametrizar.
- **[13]** DB growth — projeção out-of-disk em ~12-15 meses. `nox-mem.db` = **1015MB hoje** (CLAUDE.md afirma 574MB pós-A1 = +76% em 3 dias). Linear ~440MB/3d → ~3.5GB/mês. Disk 88G/193G usado; com VACUUM 3× headroom = 12-15 meses. Fix: adicionar `du -sh nox-mem.db` em `improvements check`; alerta @ 5GB.
- **[14]** upgrade-zero-downtime.sh:55 — `npm pack openclaw@$TARGET` sem `npm audit signatures`. Supply-chain.
- **[15]** ckpt:55 — `dist_hash` via `find -type f`, captura symlinks; benigno mas inconsistente.
- **[16]** improvements:163 — `plugin_disabled_or_absent` retorna OK em `entries: {}` (config corrompido = passa).

## LOW

- **[17]** oc-upgrade:88 — `notify` failure vai pro log mas user vê como "upgrade falhou"; prefix `[notify]`.
- **[18]** cross-agent-sync.sh:11 — `grep -oP` PCRE só GNU; documentar dependência.
- **[19]** sync-verify.sh:81 — `printf '%s\n'` literal `\n` em shell single-quote vira `\\n` em Discord — verificar render.
- **[20]** release-watcher.sh emoji em var bash; ssh terminais antigos quebram.

## Resumo

**Total findings:** 20 (4 CRITICAL, 6 HIGH, 6 MEDIUM, 4 LOW)

**Recomendação: REQUEST CHANGES antes de G01.**

Bloqueadores G01 (must-fix):
- #1 pdf-batch lockfile — race arquiteturalmente confirmada
- #3 mtime idempotency — corrupção sutil, hard-to-detect
- #4 cross-agent-sync lock — contention prod
- #10 TOKEN /proc leak — secret hygiene

Pós-G01 (não bloqueia):
- HIGH #5-9 (observability gaps)
- MEDIUM #13 (disk projection — adicionar em `improvements`)
- LOW pass

**Memórias confirmadas:**
- `feedback_audit_critical_modules_same_session.md` — happy-path A6 não cobriu 3 race incidents; audit expôs o que viria em semanas. Validado.
- `feedback_serial_pipeline_steps_need_timeout.md` — timeout 60s/markitdown OK em ambos scripts.
- `feedback_no_secrets_in_git.md` — violado em sync-verify.sh:30.
