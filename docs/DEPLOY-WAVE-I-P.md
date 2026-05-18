# Deploy Wave I+P — Runbook

> **Wave I+P** cobre as ~25 staged dirs de segurança e observabilidade prontas pra ir pra VPS.
> Este runbook explica como usar `scripts/deploy-wave-i-p.sh` com segurança.

---

## TL;DR

```bash
# 1. Dry-run (ver o que vai mudar)
./scripts/deploy-wave-i-p.sh

# 2. Se o output parecer correto, aplicar
./scripts/deploy-wave-i-p.sh --apply

# 3. Validar o estado da VPS pós-deploy
./scripts/deploy-wave-i-p.sh --validate
```

---

## Três modos

| Modo | Comando | Efeito |
|---|---|---|
| **Dry-run** (padrão) | sem flags | `rsync -n` — só mostra o que mudaria, zero mutações |
| **Apply** | `--apply` | rsync real — cria snapshot antes, registra log na VPS |
| **Validate** | `--validate` | verifica saúde da VPS pós-deploy sem alterar nada |

O **apply** requer que o dry-run tenha sido rodado nos últimos **5 minutos** (lock file em `/tmp/nox-mem-wave-i-p-dryrun.lock`). Proteção contra aplicar sem revisar o preview.

---

## Pre-flight checks (automáticos)

O script verifica antes de qualquer ação (dry-run e apply):

1. **SSH connectivity** — `ssh root@187.77.234.79 echo OK`
2. **nox-mem API health** — `curl /api/health | jq .schemaVersion` via SSH
3. **Disco livre** — mínimo 5GB em `/var/backups` na VPS
4. **Snapshot existente** — aviso se não houver wave-i-p-deploy-*.db (apply cria um novo)

Se qualquer check falhar, o script aborta com mensagem clara.

---

## Dirs deployados (por prioridade)

### 1. Privacy (`staged-privacy`)
```
staged-privacy/edits/privacy/ → src/privacy/
```
Módulo de filtro de PII: `filter.ts`, `patterns.ts`, `tag-parser.ts` + testes.

### 2. CORS (`staged-cors`)
```
staged-cors/edits/src/api/cors.ts → src/api/cors.ts
staged-cors/edits/src/api/__tests__/cors.test.ts → src/api/__tests__/cors.test.ts
```
Middleware CORS configurável. Ver `staged-cors/edits/docs/CORS.md`.

### 3. Wire-up Adapters (`staged-wire-up-adapters`)

**src/api** — apenas arquivos novos (server-deps-*.ts + health-confidence-adapter.ts):
```
server-deps-a2.ts       server-deps-l2-l3.ts    server-deps-p1.ts
server-deps-p2.ts       server-deps-p5.ts       health-confidence-adapter.ts
```

**src/lib** — apenas dirs/files novos (modo `--ignore-existing` para libs existentes):
```
src/lib/deps/                          (novo dir completo)
src/lib/viewer/broadcast-singleton.ts
src/lib/confidence/db-shim-singleton.ts
src/lib/archive/server-deps.ts
src/lib/conflict/db-singleton.ts
src/lib/hooks/server-deps.ts
```

### 4. G4 — Input Validation
```
src/api/answer.ts  (update com validação)
src/api/answer.validate-patch.ts  (novo)
```

### 5. G5 — Error Sanitizer
```
src/lib/error-sanitizer/  (novo módulo completo)
scripts/audit-stack-leak.sh
```

### 6. G6 — Localhost Auth Guard
```
src/lib/auth/localhost-guard.ts  +  tests
```

### 7. G7 — Streaming Memory Unpack
```
src/lib/archive/unpack-streaming.ts
```

### 8. G8 — Audit DB Hardening Scripts
```
scripts/protect-audit-db.sh
scripts/verify-audit-hardening.sh
```
**Nota:** depois do deploy, rodar `scripts/protect-audit-db.sh` na VPS pra aplicar permissões.

### 9. G10 — Op-Audit Extension (ran-at guard)
```
src/lib/op-audit-extension/ran-at-guard.ts  +  tests
```
Migration SQL (`v23-audit-ran-at-trigger.sql`) **NÃO está incluída** — já aplicada.

### 10. G11 — Events Stream Limited
```
src/api/events-stream-limited.ts
src/lib/viewer/__tests__/events-stream-limited.test.ts
```

### 11. G12 — Safe Error Message
```
src/lib/api/safe-error-message.ts
src/lib/api/error-leak-fix.ts  +  tests
```

### 12. G13 — Rate-Limit Dry-Run Fix
```
src/lib/hooks/rate-limit-dryrun-fix.ts  +  test
```

### 13. G14 — v24 Triggers Test
```
__tests__/v24-triggers.test.ts
```
Migration SQL (`v24-conflict-audit-ts-trigger.sql`) **NÃO incluída** — já aplicada.

### 14. G15 — Conflict Audit FK Check
```
src/lib/conflict/audit-fk-check.ts  +  test
```

### 15. G16 — Export Locking
```
src/lib/archive/export-locking.ts  +  test
```

### 16. G17 — Rate-Limit Constant Time
```
src/lib/hooks/rate-limit-constant-time.ts  +  test
```

### 17. Prometheus (`staged-prometheus`)
```
staged-prometheus/edits/src/observability/ → src/observability/
```
Módulo completo de métricas: collectors, adapters, exporter, cardinality guard, privacy-guard.

---

## Dirs EXCLUÍDOS deste script

| Dir | Motivo |
|---|---|
| `staged-1.6/`, `staged-1.7a/`, `staged-1.8/` | apply LAST — wave separada com cuidado |
| `staged-migrations/` | v11/v23/v24 já aplicadas na VPS |
| `staged-P5/`, `staged-P3/`, `staged-P1/` | handlers já na VPS — só wire-up faltando |

---

## Snapshot automático

No `--apply`, o script cria um snapshot via `sqlite3 "VACUUM INTO"` antes de qualquer rsync:

```
/var/backups/nox-mem/pre-op/wave-i-p-deploy-<timestamp>-<pid>.db
```

- Permissões: `0600` (arquivo), diretório `0700`
- Retenção: 7 dias (cron existente)
- Recovery: usar `safeRestore()` em `src/lib/op-audit.ts` — **não** fazer `cp` direto

---

## Log na VPS

Cada entry deployada registra em `/var/log/nox-mem-deploy-wave-i-p.log`:

```
2026-05-18T14:23:01Z [wave-i-p] OK staged-privacy/edits/privacy → /root/.openclaw/.../src/privacy
2026-05-18T14:23:04Z [wave-i-p] OK staged-cors/edits/src/api/cors.ts → .../src/api/cors.ts
...
2026-05-18T14:24:10Z [wave-i-p] apply-done ok=42 skip=0 fail=0
```

Ver log na VPS:
```bash
ssh root@187.77.234.79 'tail -100 /var/log/nox-mem-deploy-wave-i-p.log'
```

---

## Validação pós-deploy

O modo `--validate` (também roda automaticamente após `--apply`) verifica:

| Check | Critério |
|---|---|
| API health | HTTP 200 + `schemaVersion=24` |
| privacy/filter.ts | arquivo existe na VPS |
| cors.ts | arquivo existe na VPS |
| Processo nox-mem | `pgrep -af "node.*api-server"` retorna PID |
| deps-registry.ts | novo módulo de DI existe |
| error-sanitizer | `sanitize.ts` existe |
| observability | `index.ts` existe |

---

## Troubleshooting

### "Dry-run lock is stale"
O dry-run foi há mais de 5 minutos. Rodar novamente sem `--apply`, revisar o output, e então `--apply`.

### "Cannot reach VPS via SSH"
Verificar VPN/firewall. Testar manualmente: `ssh root@187.77.234.79 echo OK`.

### "Insufficient disk space"
```bash
ssh root@187.77.234.79 'df -h /var/backups'
# Limpar snapshots antigos se necessário:
ssh root@187.77.234.79 'ls -lt /var/backups/nox-mem/pre-op/*.db | tail -20'
```

### rsync falha em alguma entry
O script continua (não aborta no primeiro erro). Verificar log na VPS e re-rodar `--apply` — idempotente.

### API não sobe após deploy
O deploy faz rsync de **source TypeScript** — se a VPS usa `dist/` compilado, fazer build após deploy:
```bash
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && npm run build'
systemctl restart nox-mem-api  # ou o serviço equivalente
```

---

## Pós-Wave I+P: próximos passos

1. Build na VPS: `npm run build` em `nox-mem/`
2. Restart da API: confirmar que process volta em <10s
3. Validar `GET /api/health` retorna `schemaVersion=24`
4. Rodar `scripts/protect-audit-db.sh` pra hardening de permissões (G8)
5. Wave seguinte: `staged-1.6/`, `staged-1.7a/`, `staged-1.8/` (separada, com cuidado)
