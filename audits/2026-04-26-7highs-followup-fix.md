# 7 HIGH Follow-up Fix (2026-04-26)

**Trigger:** Audit triplo (`audits/2026-04-26-A1v2-A3-A4-A5-review.md`) achou 11 HIGH; 4 fixados na sessão original; 7 deferidos pra este commit.

**Resultado:** 6 patches em 4 arquivos (op-audit, reindex, index, consolidate) + 1 confirmado coberto = **7/7 HIGH fechados**. 7 smoke tests passaram. Build limpo.

---

## Fixes aplicados

| # | Severity | Origem | Arquivo | Fix |
|---|---|---|---|---|
| 1 | SEC HIGH #2 | security A1v2 | `op-audit.ts:getValidatedSnapshotDir` | `realpathSync.native()` após `resolve()`; rejeita se path resolvido difere do real ou cai fora ALLOWED_PREFIXES após follow-symlinks. Bypass via `ln -s /etc /var/backups/nox-mem/pre-op-link` agora detectado. |
| 2 | SEC HIGH #3 | security A1v2 | `op-audit.ts:snapshot` | (a) full UUID 128-bit (era slice 8 = 32-bit); (b) `statSync` size pré-integrity_check + pós, refuse rename se mudou (TOCTOU swap detection). |
| 3 | SEC HIGH #5 | security A1v2 | `op-audit.ts:scrubSecrets + withOpAudit catch` | Helper `scrubSecrets()` redacta `AIza...{35}`, `sk-ant-(oat\|api)...`, `sk-...{20+}`, `oat_...{20+}`, `Bearer ...`, paths `/root/.openclaw/.../.env`, `/home/USER/.dotfiles`. Aplicado no catch antes do INSERT em ops_audit (exposto via `/api/health.opsAudit`). Truncate agora preserva 1980 chars + `…[truncated]` marker. |
| 4 | A4 HIGH #3 | code A3+A4 | `/etc/logrotate.d/nox` | **Já coberto** — glob `/var/log/nox-*.log` pega `nox-schema-invariants.log`, `nox-snapshot-prune.log`, `nox-canary.log`, etc. Daily, rotate 14, compress, copytruncate. Sem mudança necessária. |
| 5 | CODE HIGH #1 | code A1v2 | `index.ts:end` | `try { reapZombies() } catch {}` movido pra `program.hook('preAction', ...)` — só roda quando subcomando real é dispatched, não em `--help/--version/no-args`. Reduz WAL/SHM churn. Validado via smoke (--help mantém zombie running, stats reapeia). |
| 6 | CODE HIGH #2 | code A1v2 | `reindex.ts:reindex` | Interface `ReindexResult extends OpResult`; `withOpAudit<ReindexResult>(...)` tipado; removido `as unknown as Promise<...>` cast. Compiler agora pega drift de campos. |
| 7 | CODE HIGH #3 | code A1v2 | `op-audit.ts:reapZombies` | (a) Threshold 1h → 6h (reindex em DB grande pode rodar legitimamente >1h via Gemini API); (b) PID liveness check via `process.kill(pid, 0)` em JS — só marca crashed se pid não responder. Reindex legítimo lento não é mais reaped. |
| 8 | A5 HIGH #1+#2 | code A5 | `consolidate.ts:dryRun` | (a) `wouldDelete.rows` agora reflete cenário real (só `failedToReset` se `--retry-failed`, senão 0 com texto explicativo); (b) `newFilesEstimate` usa MESMO filtro do real loop (`chunk_type='daily'` DISTINCT source_file, sem `IN (decision/lesson/...)` 6-types overestimating 5x); (c) novo campo `wouldInsert` mostra escopo de INSERT em `consolidated_files` capped por MAX_FILES_PER_RUN. |

---

## Smoke tests (7/7 passaram)

| Teste | Resultado |
|---|---|
| Build TypeScript pós-7-patches | ✅ tsc clean |
| reindex normal (CODE #2 tipos novos) | ✅ success in 70ms (affected=46) |
| `--help` NÃO dispara reapZombies (CODE #1 hook gate) | ✅ zombie permanece `running` |
| Subcomando real dispara reaper (CODE #1+#3) | ✅ pid morto marcado crashed |
| reaper PRESERVA pid alive (CODE #3 negative) | ✅ pid `$$` mantido `running` |
| Symlink no snapshot dir (SEC #2) | ✅ "resolves via symlink to '/etc' — refusing" |
| scrubSecrets redacts API keys (SEC #5) | ✅ AIza/sk-ant/oat_/Bearer todos `[REDACTED]` |
| consolidate dry-run accuracy (A5 #1+#2) | ✅ wouldInsert + wouldProcess + capPerRun corretos |

---

## Backups na VPS
- `src/lib/op-audit.ts.bak-pre-20260426-7highs`
- `src/reindex.ts.bak-pre-20260426-7highs`
- `src/index.ts.bak-pre-20260426-7highs`
- `src/consolidate.ts.bak-pre-20260426-7highs`

## Estado pós-fix
- **0 HIGH abertos** (11 originais → 11 fechados em 24h)
- 17 MEDIUM + 12 LOW deferidos pra Wave 2 cleanup
- 5 camadas de defesa hardened + 7 fixes adicionais (B1+B2+SEC#1+SEC#4+A4#1+A4#2+SEC#2+SEC#3+SEC#5+CODE#1+#2+#3+A5#1+#2)
- 100% A1 op-audit cobertura crítica (path validation completa, secret scrub, PID-aware reaper, TOCTOU mitigation)

## Observação técnica

scrubSecrets dual-match em `Bearer sk-ant-oat...`:
- Regex 1 (`Bearer\s+...`) substitui por `Bearer [REDACTED]`
- Regex 2 (`sk-ant-oat...`) substitui token original (já consumido por #1)
- Output: `Bearer [REDACTED][REDACTED]` — visualmente feio mas zero leak. Aceitável; refinar regex ordering em Wave 2 se incomodar.

## Próximos passos sugeridos

- **04-30 (4d):** salience activation gate (`activate-salience.sh check` → `--apply`)
- **05-01 (5d):** section_boost decision gate
- **Wave 2 (Maio):** sprint dedicado nas 17 MEDIUM (ops_audit append-only, statvfs check, authorization layer, etc) + 12 LOW
- **Pre-NOX-Supermem productização:** validar threat model multi-tenant antes de qualquer customer
