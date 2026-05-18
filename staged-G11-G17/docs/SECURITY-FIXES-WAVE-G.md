# Security Fixes — Wave G (G11–G17)

> Bundle de 7 fixes endereçando os gaps abertos no THREAT-MODEL v1.1
> (PR #58 / Wave-E.1 follow-up). 2 High, 5 Medium. Todos backward-compatible
> (env-opt-in).

| Gap | Severity | Sprint | Fix module | Env vars introduzidos |
|---|---|---|---|---|
| G11 | 🔴 High | P5.1 | `staged-G11/edits/src/api/events-stream-limited.ts` | `NOX_VIEWER_MAX_CONNECTIONS`, `NOX_VIEWER_MAX_PER_IP`, `NOX_VIEWER_DROP_OLDEST` |
| G12 | 🔴 High | next | `staged-G12/edits/src/lib/api/safe-error-message.ts` + `error-leak-fix.ts` | `NOX_ERROR_PASSTHROUGH` (DEV ONLY) |
| G13 | 🟡 Med  | P2.1 | `staged-G13/edits/src/lib/hooks/rate-limit-dryrun-fix.ts` | `NOX_HOOK_DRYRUN_RATE_LIMIT` |
| G14 | 🟡 Med  | L2.1 | `staged-G14/edits/migrations/v24-conflict-audit-ts-trigger.sql` | — |
| G15 | 🟡 Med  | L2.1 | `staged-G15/edits/src/lib/conflict/audit-fk-check.ts` | — |
| G16 | 🟡 Med  | A2.3 | `staged-G16/edits/src/lib/archive/export-locking.ts` | — |
| G17 | 🟡 Med  | P2.1 | `staged-G17/edits/src/lib/hooks/rate-limit-constant-time.ts` | `NOX_HOOK_EXPOSE_TOKENS` |

---

## G11 — SSE concurrent connection limit (🔴 High)

**Threat (THREAT-MODEL §7.5 T-P5-2, R-P5-2.1):** SSE handler tem zero limite
de conexões. Um atacante abre 10k clientes → exaustão de socket + memória
do ring buffer → DoS.

**Fix:**

- `openLimitedSseStream({ ip, ... })` envolve `openSseStream()` (P5 T3) com
  três níveis de controle:
  1. **Cap global** (`NOX_VIEWER_MAX_CONNECTIONS`, default 50) — rejeita
     503 + `Retry-After: 5` quando ultrapassado.
  2. **Cap por IP** (`NOX_VIEWER_MAX_PER_IP`, default 5) — rejeita 503 +
     `Retry-After: 10`. Sempre rejeita (nunca evicta), pra evitar que um
     único IP elimine outros tenants.
  3. **Drop-oldest** (`NOX_VIEWER_DROP_OLDEST=1`) — opcional, fecha a
     conexão mais antiga ao invés de rejeitar nova. Útil pra ops com
     "newest wins".

- Tracker singleton (`getSseTracker()`) cobre todo o processo. Reset via
  `setSseTracker()` em testes.

**Adoption (host wiring):**

```ts
const result = openLimitedSseStream({
  broadcaster,
  clientId,
  ip: req.headers["x-forwarded-for"]?.toString().split(",")[0]?.trim() ?? req.socket.remoteAddress ?? "unknown",
});
if (result.rejected) {
  const http = rejectionToHttp(result);
  res.writeHead(http.status, http.headers);
  return res.end(JSON.stringify(http.body));
}
res.writeHead(200, result.stream.headers);
// ... existing SSE pump
```

**Backward compat:** defaults generosos; sem mudança em uso interativo.

**Tests:** 14 cases — env parsing, tracker, accept path, global cap, per-IP
cap, drop-oldest, close lifecycle.

---

## G12 — Error path leak strip (🔴 High)

**Threat (THREAT-MODEL §7.7 R-P2-5):** `/api/hooks/recent` retorna
`{ error: (e as Error).message }` em 500-path. Quando o erro vem do SQLite
ou ORM, mensagem traz **path absoluto do DB** + às vezes trecho de SQL +
em alguns casos valores de env var dumped por ORMs estritos.

**Fix:**

- `safeErrorMessage(e)` strippa antes de expor:
  - paths absolutos: `/Users/...`, `/root/...`, `/var/...`, `/opt/...`,
    `/tmp/...`, `/home/...` com `:line:col` opcional
  - connection strings: `sqlite://...`, `file://...`
  - env-assigns: `FOO=value` (var em maiúsculas)
  - Bearer tokens + long opaque tokens (32+ chars)
  - stack frame fragments embedded em `Error.toString()`
- Retorna `{ message: sanitized, correlationId: uuid-v4 }`. Caller loga
  raw + correlationId server-side.
- Override DEV-only: `NOX_ERROR_PASSTHROUGH=1` (com boot WARN).

**Adoption helpers em `error-leak-fix.ts`:**

```ts
// staged-P2/edits/src/api/hooks.ts:99 (drop-in)
} catch (e) {
  return { status: 500, body: safeError500(e, { context: "hooks.recent" }) };
}

// staged-L2/edits/src/api/conflict.ts:181
} catch (err) {
  return { status: 409, body: safeConflict409(err, { context: "conflict.resolve" }) };
}

// staged-L3/edits/src/api/mark.ts (R-L3-3)
return { status: 500, body: safeMark500(e) };
```

**Complementa G5** (Wave F, stack-strip middleware) — aplica mesmo quando
stack já foi removido, pois `.message` continua leakeando.

**Tests:** 17 cases — strippers (paths/DB/env/bearer/token/frames), fallback,
cap, input shape, correlationId uniqueness, passthrough, boot check, adoption
helpers.

---

## G13 — Rate limit em `/api/hooks/dryrun` (🟡 Med)

**Threat (THREAT-MODEL §7.7 T-P2-2, R-P2-2.1):** `dryrun` endpoint bypassa
rate limit de capture (correto pra testing) mas permite probing ilimitado
do classifier (privacy filter, PII detection). Atacante fingerprintea
patterns A1 em velocidade arbitrária.

**Fix:**

- Token bucket por IP (`NOX_HOOK_DRYRUN_RATE_LIMIT`, default 10/min).
- Reabastece em `rate / 60` tokens/sec.
- Rejeita 429 + `Retry-After` + `{ error: "rate_limited", reason: "dryrun_per_ip" }`.
- Buckets process-local — single-tenant assumption (ver §12.1 do THREAT-MODEL).
- Não afeta capture rate limit (token bucket separado configurado via
  `HookConfig.rateLimitPerMin`).

**Adoption:**

```ts
// staged-P2/edits/src/api/hooks.ts dryrun branch
const limiter = createDryrunRateLimiter();  // singleton em prod
const gate = checkDryrunGate(limiter, req.ip);
if (!gate.allowed) {
  return { status: 429, body: gate.rejectResponse!.body };
}
// ... existing dryrun logic
```

**Tests:** 6 cases — env parsing, capacity burst, IP isolation, refill over
time, gate accept, gate reject 429.

---

## G14 — `conflict_audit.{ts, resolved_at}` server-managed (🟡 Med)

**Threat (THREAT-MODEL §7.6 T-L2-4, R-L2-4):** v21 `conflict_audit` aceita
INSERT com `ts` arbitrário (mesmo gap de G10/ran_at em `confidence_eval_log`).
Atacante forja evidência retroativa.

**Fix:** migration `v24-conflict-audit-ts-trigger.sql` com 3 triggers:

1. `trg_conflict_audit_ts_insert` — BEFORE INSERT, rejeita se `ts` divergir
   do server clock por mais de 60s (tolerância pra clock skew). App deve
   omitir o campo e deixar o DEFAULT do v21 atuar.
2. `trg_conflict_audit_resolved_at_on_terminal` — BEFORE UPDATE OF status
   na transição `open/reviewed` → terminal, mesma checagem em `resolved_at`.
3. `trg_conflict_audit_resolved_at_immutable` — depois de set, qualquer
   UPDATE que tente mudar `resolved_at` é abortado.

**Rollback:** `v24-rollback.sql` (DROP TRIGGER + restaura `user_version=23`).

**Idempotência:** todos os `CREATE` precedidos de `DROP IF EXISTS`. Safe
re-apply.

**Tests:** 8 cases — `user_version` bump, INSERT padrão, rejeição backdated
ts (>60s), aceitação dentro do skew, UPDATE com backdated `resolved_at`
rejeitado, UPDATE terminal sem `resolved_at` aceito, imutabilidade pós-set,
idempotência. Tests usam better-sqlite3 quando disponível (skip gracioso
quando não).

---

## G15 — `conflict_audit` FK validation (🟡 Med)

**Threat (THREAT-MODEL §7.6 T-L2-2, R-L2-2.1):** v21 explicitamente skipou
hard-FK em `target_relation_ids`/`subject_entity_id` pra migração barata.
INSERT aceita ids inexistentes → "dangling audit row" sem evidência
recuperável.

**Fix:** `validateConflictAuditFK(db, conflict)` que:

- Valida `subject_entity_id` existe em `kg_entities`
- Bulk-valida `target_relation_ids` via `json_each` (sem placeholder
  explosion)
- Valida `picked_relation_id` quando presente (resolution path)
- Retorna `{ valid, missingSubject, missingRelationIds, missingPicked }`

`assertConflictAuditFK` throws `ConflictAuditFKError` (caller mapeia pra
400/422).

**SQL addendum (opcional):** `JSON_SHAPE_CHECK_SQL` exportado como string —
v25 migration adiciona trigger BEFORE INSERT que valida `target_relation_ids`
parseia como array não-vazio de inteiros positivos. Existence check fica
em código (SQLite CHECK cross-table é frágil).

**Adoption (audit-writer.ts):**

```ts
// antes do INSERT_SQL.run(...)
assertConflictAuditFK(db, {
  subject_entity_id: conflict.subject_entity_id,
  target_relation_ids: conflict.target_relation_ids,
});
```

**Tests:** 8 cases — happy path, missing subject, partial target subset,
missing picked, null/undefined picked, empty array, throw vs no-throw.

---

## G16 — Export concurrent operations file lock (🟡 Med)

**Threat (THREAT-MODEL §7.8 T-A2-Orch-1, R-A2-Orch-1):** Duas execuções
concorrentes de `runExport()` pra mesmo path corrompem o archive E (pior)
podem reusar nonce GCM se compartilharem passphrase+salt — quebra
confidencialidade + autenticidade do AES-GCM.

**Fix:** lock file `<output>.lock` (mode 0600) com metadata
`{ pid, started_at_ms, hostname, op, v: 1 }`. Criado com `O_EXCL` no início
do export, removido no fim.

**Lock-breaking heurística:**

- Lock existente + PID vivo + idade <30 min → 409 Conflict
  (`ExportLockBusyError`).
- PID morto OU idade >30 min → log WARN, sobrescreve.
- JSON malformado → log WARN, sobrescreve.

**API:**

```ts
const result = await withExportLock(outputPath, () => runExport(req));
// ou
const handle = await acquireExportLock(outputPath);
try { ... } finally { await handle.release(); }
```

**Defesa em release:** verifica que o lock ainda é nosso (pid + started_at_ms
match) antes de unlink. Se outro caller quebrou + tomou, deixa quieto.

**Tests:** 11 cases — mode 0600, helpers, metadata, conflict 409, re-acquire
após release, stale por idade, stale por PID morto, alive+fresh rejeita,
JSON malformado, `withExportLock` happy path + throws cleanup, release
safety.

---

## G17 — `rateLimitTokens` oracle (🟡 Med)

**Threat (THREAT-MODEL §7.7 T-P2-3, R-P2-3):** `GET /api/hooks/status` expõe
`rateLimitTokens`. Atacante monitora o decremento pra inferir cadência de
captura do user — side-channel de atividade.

**Fix:**

- Default: `rateLimitTokens: null` sempre (campo presente, valor zerado —
  shape preservada, "constant-time").
- Opt-in `NOX_HOOK_EXPOSE_TOKENS=1` pra ops debugging (boot WARN).
- Helper `statusBodyWithSanitizedTokens()` é drop-in.

**Adoption (hooks.ts status branch):**

```ts
return {
  status: 200,
  body: statusBodyWithSanitizedTokens({
    config: ...,
    queueDepth: inspect.queueDepth,
    rateLimitTokens: inspect.rateLimitTokens,
  }),
};
```

**Tests:** 9 cases — env flag parsing, default null, opt-in passthrough,
boot WARN, body transform preserve-shape, other fields untouched.

---

## Migration v24 — apply / rollback

```sh
# Apply (production)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/data/nox-mem.db \
  < staged-G14/edits/migrations/v24-conflict-audit-ts-trigger.sql

# Rollback
sqlite3 /root/.openclaw/workspace/tools/nox-mem/data/nox-mem.db \
  < staged-G14/edits/migrations/v24-rollback.sql

# Verify
sqlite3 nox-mem.db "PRAGMA user_version;"  # should print 24 or 23
sqlite3 nox-mem.db "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='conflict_audit' ORDER BY name;"
```

Apply via `withOpAudit()` wrapper (CLAUDE.md regra #6) ou snapshot manual
em `/var/backups/nox-mem/pre-op/`.

---

## Env vars consolidados (Wave G)

Adicionados ao `.env.example` quando o bundle for adotado:

```env
# G11 — SSE limits
NOX_VIEWER_MAX_CONNECTIONS=50
NOX_VIEWER_MAX_PER_IP=5
# NOX_VIEWER_DROP_OLDEST=1     # opcional

# G12 — DEV ONLY (boot WARN se ativo)
# NOX_ERROR_PASSTHROUGH=1

# G13 — dryrun rate limit
NOX_HOOK_DRYRUN_RATE_LIMIT=10

# G17 — ops debugging only (boot WARN se ativo)
# NOX_HOOK_EXPOSE_TOKENS=1
```

---

## Cross-links

- THREAT-MODEL.md §7.5 (P5 SSE) — G11, G17 contexto
- THREAT-MODEL.md §7.6 (L2 conflict) — G14, G15 contexto
- THREAT-MODEL.md §7.7 (P2 hooks) — G12, G13, G17 contexto
- THREAT-MODEL.md §7.8 (A2 orchestrator) — G16 contexto
- THREAT-MODEL.md Appendix A — Gap registry com todos G11–G17
- THREAT-MODEL.md §10 — Recommendations 28–34, 41 (alinha com fixes acima)
- PR #58 — análise original que identificou os gaps
- Wave F bundle (PR após #58) — G4/G5/G6/G7/G8/G10; G12 complementa G5
- CLAUDE.md regra #6 — `withOpAudit()` mandatory pra v24 apply

---

## Test summary

| Gap | Test file | Cases |
|---|---|---|
| G11 | `staged-G11/.../events-stream-limited.test.ts` | 15 |
| G12 | `staged-G12/.../safe-error-message.test.ts` | 22 |
| G13 | `staged-G13/.../rate-limit-dryrun.test.ts` | 8 |
| G14 | `staged-G14/.../v24-triggers.test.ts` | 8 |
| G15 | `staged-G15/.../audit-fk-check.test.ts` | 8 |
| G16 | `staged-G16/.../export-locking.test.ts` | 12 |
| G17 | `staged-G17/.../rate-limit-constant-time.test.ts` | 10 |
| **Total** | | **83** |

Tests usam `node:test` + `node:assert/strict`. Sem dependência externa
exceto `better-sqlite3` (G14) que é skip-gracioso quando ausente — todos
os 8 tests passam contra SQLite real quando o driver está instalado
(verificado nessa wave).

### Resultado da execução (2026-05-18)

```
ℹ tests 83
ℹ suites 32
ℹ pass 83
ℹ fail 0
ℹ duration_ms 194
```

Comando: `tsx --test <todos os 7 test files>` em workspace com TypeScript
5.4 + Node 22+ + better-sqlite3 instalado. Validado em
`/tmp/wave-g-typecheck/` durante o Wave G build.
