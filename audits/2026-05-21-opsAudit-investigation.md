# opsAudit Investigation — 2026-05-21 manhã

> **Status:** ⚠️ 3 issues identificados, 1 prod risk + 2 metric noise. Recommendation: fix #2 (vec0 reindex failure) com prioridade; #1 e #3 são metric hygiene.

## Contexto

`/api/health.opsAudit.total_24h` reporta 48 ops em 24h com 10 failed + 12 crashed em `db_source=unknown`. Investigação mostra que MAJORITY são rows antigas (até 2026-04-27) que passam o filter por type confusion + 1 issue REAL recente (reindex falhou 6× em 2026-05-20).

---

## Issue #1 — `started_at` type chaos (metric noise, no prod impact)

### Diagnóstico

```sql
SELECT typeof(started_at), status, COUNT(*) FROM ops_audit GROUP BY 1, 2;
```

| typeof | status | count |
|---|---|---|
| text | crashed | 12 |
| text | failed | 16 |
| text | success | 28 |

**TODAS as 56 rows que vejo têm `started_at` como TEXT**, mas com 3 formatos misturados:
- `"1779242511707.0"` (epoch ms format float-as-text, sem cast pra INT)
- `"2026-04-27 02:00:03"` (ISO datetime TEXT)
- INT epoch ms (esperado — fix do trigger PR pré-existente)

### Root cause

`/api/health` filter usa `started_at > strftime("%s", "now", "-24 hours") * 1000` mas SQLite compara TEXT/INT com cast lexicográfico que falha silenciosamente. Filter retorna rows muito antigas como se fossem "24h".

### Impact

- **Falsa percepção de health degradado.** Health endpoint mostra "12 crashed last 24h" mas são rows de Abril/Maio retidas por filter bug.
- **Zero impact em prod runtime** — só o dashboard mente.

### Fix proposto

1. **Migration data normalization** (one-time):
   ```sql
   UPDATE ops_audit SET started_at =
     CASE
       WHEN typeof(started_at) = 'integer' THEN started_at
       WHEN started_at LIKE '_____-__-__%' THEN strftime('%s', started_at) * 1000
       ELSE CAST(started_at AS INTEGER)
     END;
   ```
2. **Schema constraint** `CHECK(typeof(started_at) = 'integer')` pra prevent futuras inserts TEXT
3. **Health endpoint defensive cast** `CAST(started_at AS INTEGER) > ?`

---

## Issue #2 — Reindex `no such module: vec0` (PROD RISK — investigar)

### Diagnóstico

6× sequencial em 2026-05-20 02:00:05 → 02:01:51 UTC (~23:00-23:01 BRT):

```
reindex | failed | SqliteError: no such module: vec0
    at Database.<some-stack>
```

Todos com mesma error message — sqlite-vec extension não foi carregada quando o reindex tentou rodar.

### Root cause hipóteses

a. **Cron job rodando sem env adequado** — sqlite-vec extension path não no LD_LIBRARY_PATH ou Node.js env
b. **Race condition** — 6 tentativas em 1 minuto sugere retry loop, não cron schedule
c. **Patch incompleto** — memory `feedback_eod_cron_reindex_was_the_real_trigger.md` diz "patched 2026-04-25 to use consolidate instead". Patch pode não ter sido aplicado consistentemente

### Mitigação atual

`/api/health` mostra `vectorCoverage: {embedded: 68995, total: 68995, orphans: 0}` — vetores estão OK no DB porque:
- Daily-main às 06:00 UTC roda OK (não usa o code path quebrado)
- Insert/update normal não chama reindex

Mas **se algum cron/manual reindex disparar pra preencher vetores faltantes, vai falhar** → vec coverage drift potencial.

### Action items

1. **SSH na VPS, replicar o reindex manualmente** com `set -a; source /root/.openclaw/.env; set +a; nox-mem reindex --dry-run`
2. Se replicar → debug sqlite-vec extension loading
3. Se não replicar → identificar quem disparou esses 6 retries (cron, manual, OR bug em retry logic)
4. **Confirm `consolidate` patch foi deployado** — verificar que o cron 22:00 BRT usa consolidate, não reindex

---

## Issue #3 — Test ops + `db_source` NULL pollute métricas

### Diagnóstico

11 das 12 "crashed" rows no health 24h são test ops + ocr-batch-cloud kills legítimos:

| op_name | reason |
|---|---|
| `test-bad-fn` (4×) | intentional test contract violation |
| `test-failure` (4×) | intentional e2e failure marker |
| `test-b2-regression` (4×) | test reaper |
| `test-success` (mixed) | test marker |
| `ocr-batch-test-stale` | test marker |
| `ocr-batch-cloud` (7×) | legitimate kills (manual deploy, OOM, timeout) |
| `ocr-batch-test-stale` | watchdog reaped stale test |

### Root cause

Test fixtures que invocam `withOpAudit()` populating real `ops_audit` table without isolation. `db_source` field não é preenchido → defaults to `NULL` → bucketed como `"unknown"`.

### Fix proposto

1. **Test ops MUST be filtered** — em `/api/health` query exclude `op_name LIKE 'test-%'`
2. **Test ops MUST set `db_source='test'`** — withOpAudit signature should require explicit `db_source`
3. **Cleanup historical test rows** — `DELETE FROM ops_audit WHERE op_name LIKE 'test-%'` (one-time, won't affect prod)

---

## Recommendation summary

| Issue | Severity | Effort | Priority |
|---|---|---|---|
| #2 vec0 reindex failure | 🔴 PROD RISK (potential vec drift) | ~1h debug | **HIGH — investigate next session** |
| #1 type chaos in started_at | 🟡 Metric noise | ~30min migration + 15min health fix | MEDIUM |
| #3 test ops pollute metrics | 🟡 Metric noise | ~15min filter | LOW (related to #1) |

## Veredicto investigation

**Sistema OK em runtime** — vetores intactos, prod features working. Mas health dashboard mente sobre 24h crashed/failed e tem 1 issue real (vec0) que pode escalar.

## Action items

1. ✅ Audit documented (este file)
2. ✅ Memory cravada (`[[opsaudit-investigation-2026-05-21]]`)
3. **Decidir com Toto:** fix #2 agora OR parking lot
4. **Issues #1+#3:** podem ir pra próxima janela de housekeeping

## Cross-links

- `[[withopaudit-trigger-raise-ignore-swallows-insert]]` — trigger fix anterior
- `[[eod-cron-reindex-was-the-real-trigger]]` — patch 2026-04-25 (validate aplicado)
- `[[validate-features-with-db-not-logs]]` — ironicamente, este case é o OPOSTO (DB diz uma coisa, dashboard diz outra)
