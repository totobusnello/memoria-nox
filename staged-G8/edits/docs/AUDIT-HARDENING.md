# AUDIT-HARDENING.md — nox-mem Audit DB File-Level Protection

> **Ref:** THREAT-MODEL.md §8 / G8 (audit deletion vulnerability).
> **Status:** Implemented — Wave F, 2026-05-18.
> **Script:** `staged-G8/edits/scripts/protect-audit-db.sh`.
> **Verification:** `staged-G8/edits/scripts/verify-audit-hardening.sh`.

---

## 1. O problema (G8)

Os SQL triggers bloqueiam `DELETE FROM ops_audit` e `UPDATE` em rows com
status terminal. Isso protege contra adulteração **dentro do SQLite**. Mas:

```bash
rm /root/.openclaw/workspace/tools/nox-mem/nox-mem.db  # bypass completo
sed -i 's/failed/success/' nox-mem.db                  # corrompe page boundaries
```

Qualquer processo com permissão de escrita no arquivo pode destruir o audit log
inteiro, mesmo que os triggers estejam corretos. Lição documentada: **2026-05-01
— sed -i em SQLite corrompe page boundaries** (`CLAUDE.md` regra #7).

---

## 2. Solução implementada

### 2.1 audit.db separado

`ops_audit` e `confidence_eval_log` são movidos para um arquivo dedicado
`audit.db`, **separado de `nox-mem.db`**. Isso permite:

- Aplicar `chattr +i` (imutável) apenas em `audit.db` sem bloquear o DB principal.
- `nox-mem.db` continua gravável (ingest, reindex, search — todas as operações normais).
- Backups podem restaurar `nox-mem.db` sem afetar o audit trail.

```
/root/.openclaw/workspace/tools/nox-mem/
├── nox-mem.db        ← gravável, 0600, SEM chattr +i
└── audit.db          ← append-only, 0600, COM chattr +i (imutável)
```

### 2.2 chattr +i em audit.db

```bash
chattr +i /root/.openclaw/workspace/tools/nox-mem/audit.db
```

Com `+i` ativo:
- `rm audit.db` → `Operation not permitted` (mesmo como root)
- `sed -i '...' audit.db` → `Operation not permitted`
- `truncate audit.db` → `Operation not permitted`
- `echo "" > audit.db` → `Operation not permitted`

Apenas `chattr -i` (que requer `CAP_LINUX_IMMUTABLE`) pode remover a proteção.

### 2.3 Permissões 0600

Ambos os DBs têm `chmod 0600 root:root`. Isso garante:
- Apenas root pode ler/gravar.
- Outros usuários e processos sem privilégio não têm acesso.

---

## 3. Instalação

```bash
# Aplicar hardening completo
/root/.openclaw/workspace/tools/nox-mem/staged-G8/edits/scripts/protect-audit-db.sh harden

# Verificar
/root/.openclaw/workspace/tools/nox-mem/staged-G8/edits/scripts/verify-audit-hardening.sh
```

Saída esperada:
```
=== G8: Audit DB Hardening Verification ===
  [PASS] Step 1: audit.db exists
  [PASS] Step 2: audit.db has chattr +i (immutable)
  [PASS] Step 3: nox-mem.db has 0600 perms
  [PASS] Step 3: audit.db has 0600 perms
  [PASS] Step 4: ops_audit append-only triggers present (2 triggers)
  [PASS] Step 5: rm of audit.db is blocked by chattr +i

=== Results: 6 passed, 0 failed ===
All checks passed. Audit DB hardening is active.
```

---

## 4. Procedure de backup

`chattr +i` bloqueia VACUUM INTO e SQLite hot backup. Para backup seguro:

```bash
# Passo 1: Remover imutabilidade temporariamente
/root/.openclaw/workspace/tools/nox-mem/staged-G8/edits/scripts/protect-audit-db.sh unprotect

# Passo 2: Fazer backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=/var/backups/nox-mem
cp /root/.openclaw/workspace/tools/nox-mem/audit.db \
   "${BACKUP_DIR}/audit-${TIMESTAMP}.db"
chmod 0600 "${BACKUP_DIR}/audit-${TIMESTAMP}.db"

# Passo 3: Re-aplicar imutabilidade
/root/.openclaw/workspace/tools/nox-mem/staged-G8/edits/scripts/protect-audit-db.sh reprotect

# Verificar
lsattr /root/.openclaw/workspace/tools/nox-mem/audit.db
# Esperado: ----i--------e-- audit.db
```

**Tempo máximo sem proteção:** o menor possível. Não deixar `unprotect` ativo
por mais de 5 minutos.

### Integração com backup-all.sh

O `backup-all.sh` (02:00 BRT) deve incluir a sequência `unprotect → backup → reprotect`.
Editar `/root/.openclaw/workspace/tools/nox-mem/scripts/backup-all.sh` e adicionar:

```bash
# Antes do backup de audit.db:
/path/to/protect-audit-db.sh unprotect
sqlite3 /path/to/audit.db ".backup $BACKUP_PATH/audit-$(date +%Y%m%d).db"
/path/to/protect-audit-db.sh reprotect
```

---

## 5. Recovery

Se `audit.db` for perdido ou corrompido (ex: falha de disco antes de `reprotect`):

1. **Confirmar perda:**
   ```bash
   sqlite3 /root/.openclaw/workspace/tools/nox-mem/audit.db "PRAGMA integrity_check;"
   ```

2. **Restaurar do backup mais recente:**
   ```bash
   # SÓ se audit.db está corrompido/ausente
   protect-audit-db.sh unprotect 2>/dev/null || true  # remove +i se presente
   cp /var/backups/nox-mem/audit-YYYYMMDD.db \
      /root/.openclaw/workspace/tools/nox-mem/audit.db
   chmod 0600 /root/.openclaw/workspace/tools/nox-mem/audit.db
   protect-audit-db.sh reprotect
   ```

3. **NÃO use `cp backup.db audit.db` diretamente se audit.db ainda existe
   com +i** — o `cp` falhará. Primeiro remova com `protect-audit-db.sh unprotect`.

4. **NÃO use `safeRestore()` de `op-audit.ts`** para audit.db — essa função
   é para `nox-mem.db` principal. audit.db tem recovery manual.

---

## 6. Gaps residuais

| Gap | Severidade | Status |
|---|---|---|
| chattr +i não funciona em filesystems Docker/tmpfs | Baixo | Fora de escopo — VPS usa ext4 nativo |
| audit.db backup window (~segundos) sem +i | Baixo | Mitigado por janela mínima + cron isolado |
| ATTACH nox-mem.db → audit.db migration não automatizada | Médio | TODO: migration script em Wave G |
| Off-site backup rejeitado (F09) | N/A | User decision — documentado em DECISIONS.md |

---

## 7. Integração com DEPLOY-WAVE-B.md

Adicionar ao final do deployment guide:

```markdown
## Phase G8 — Audit DB Hardening (after all Wave B endpoints deployed)

1. Run: `protect-audit-db.sh harden`
2. Verify: `verify-audit-hardening.sh` (all 6 checks must pass)
3. Add unprotect/reprotect hooks to backup-all.sh (see AUDIT-HARDENING.md §4)
4. Commit to runbook: `docs/RUNBOOKS.md#audit-db-hardening`
```

---

*Ref: THREAT-MODEL.md §8. CLAUDE.md regra #6 (withOpAudit) + regra #7 (sed em .db).*
*Incident 2026-05-01: sed -i corrompeu 1GB nox-mem.db + 8 backups.*
