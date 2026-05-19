# Deploy steps — audit #20 gaps (defense-in-depth)

Branch: `fix/audit20-gaps-defense-in-depth`
Audit ref: audit #20 (PR não criado, output em task notif). 4 gaps mapeados:

| # | Tool | Severidade | Defesa adicionada |
|---|------|------------|-------------------|
| 1 | graphify-ingest | HIGH | `checkLargeDbIngestGuard` + `withOpAudit` wrap |
| 2 | watch | MEDIUM | `checkLargeDbIngestGuard` at boot |
| 3 | kg-merge | MEDIUM | `withOpAudit` wrap + `--dry-run` flag |
| 4 | ingest-entity | MEDIUM | `checkLargeDbIngestGuard` no head do `ingestEntityFile()` |

LOW gaps (kg-prune, vectorize) **NÃO** foram fix nesta PR — Toto rejeitou no audit.

---

## Pré-deploy

1. Confirm DB snapshot recente: `ls /var/backups/nox-mem/pre-op/ | tail -5`
2. Build local TS: `cd /Users/lab/Claude/Projetos/memoria-nox && npx tsc -p tsconfig.json --noEmit`
3. Tests pass: `node --test staged-1.7a/tests/audit20-*.test.ts`
4. Verify `withOpAudit` symbol exists on VPS:
   `ssh vps "grep -n 'export.*withOpAudit' /root/.openclaw/workspace/tools/nox-mem/src/lib/op-audit.ts"`

## Deploy (scp por arquivo)

> ⚠️ Toto revisa o PR antes do deploy. Não rodar até merge.

### Fix 1 — graphify-ingest.ts

```bash
scp staged-graphify-ingest/graphify-ingest.ts vps:/root/.openclaw/workspace/tools/nox-mem/src/graphify-ingest.ts
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc -p tsconfig.json"
# Verify build:
ssh vps "test -f /root/.openclaw/workspace/tools/nox-mem/dist/graphify-ingest.js && echo OK"
```

### Fix 2 — watch boot guard (via index.ts)

Already wired in `staged-1.7a/edits/index.ts` (kg-merge + watch updated).

```bash
scp staged-1.7a/edits/index.ts vps:/root/.openclaw/workspace/tools/nox-mem/src/index.ts
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc -p tsconfig.json && systemctl restart nox-mem-api"
```

### Fix 3 — kg-merge --dry-run + previewMergeEntities

Apply `staged-1.7a/edits/knowledge-graph.patch.ts` as a manual append to the
existing `knowledge-graph.ts`:

```bash
# 1. Read the patch
cat staged-1.7a/edits/knowledge-graph.patch.ts

# 2. Append previewMergeEntities + canonicalize to VPS file
#    (Do this manually — never sed on production .ts; verify edit via grep)
ssh vps "vim /root/.openclaw/workspace/tools/nox-mem/src/knowledge-graph.ts"
# Add `export function previewMergeEntities(): MergePreview { ... }` near
# the existing mergeEntities function.

# 3. Rebuild
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc -p tsconfig.json"

# 4. Verify subcommand
ssh vps "nox-mem kg-merge --dry-run | head -20"
```

### Fix 4 — ingest-entity guard

Apply `staged-1.7a/edits/ingest-entity.patch.ts` as a manual append:

```bash
# 1. Read the patch
cat staged-1.7a/edits/ingest-entity.patch.ts

# 2. Add `import { checkLargeDbIngestGuard } from "./db.js";` to imports
#    Add `checkLargeDbIngestGuard(db, "ingest-entity");` at top of
#    ingestEntityFile() — right after `const db = externalDb ?? getDb();`
ssh vps "vim /root/.openclaw/workspace/tools/nox-mem/src/ingest-entity.ts"

# 3. Rebuild
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc -p tsconfig.json"

# 4. Verify on prod DB without override (should ABORT)
ssh vps "nox-mem ingest-entity /tmp/test-entity.md 2>&1 | grep -i 'ingest guard'"

# 5. Verify with override (should pass)
ssh vps "NOX_ALLOW_PROD_INGEST=1 nox-mem ingest-entity /tmp/test-entity.md"
```

## Post-deploy validation

```bash
# 1. Guard fires on prod-scale DB (negative test — must abort)
ssh vps "nox-mem watch 2>&1 | head -10 | grep -i 'ingest guard'"
ssh vps "nox-mem ingest-entity memory/entities/person/toto.md 2>&1 | head -10 | grep -i 'ingest guard'"

# 2. Guard bypassed with override (positive test — must pass)
ssh vps "NOX_ALLOW_PROD_INGEST=1 timeout 2 nox-mem watch 2>&1 | head -5"

# 3. kg-merge dry-run (must return JSON preview, no mutation)
ssh vps "nox-mem kg-merge --dry-run | jq '.would_merge'"
# Then verify count UNCHANGED:
ssh vps "sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db 'SELECT COUNT(*) FROM kg_entities'"

# 4. ops_audit log entries (withOpAudit verification — graphify + kg-merge)
ssh vps "sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  \"SELECT op_type, status, started_at FROM ops_audit WHERE op_type IN ('graphify-ingest', 'kg-merge') ORDER BY started_at DESC LIMIT 5\""

# 5. /api/health snapshot — sectionDistribution + opsAudit
ssh vps "curl -s http://127.0.0.1:18802/api/health | jq '.sectionDistribution, .opsAudit'"
```

## Rollback plan

If any deployed file misbehaves:

```bash
# Restore from pre-op snapshot (most recent)
ssh vps "ls -lt /var/backups/nox-mem/pre-op/ | head -3"
# Use safeRestore() from src/lib/op-audit.ts (validates user_version match):
ssh vps "node -e \"
  import('./dist/lib/op-audit.js').then(({ safeRestore }) =>
    safeRestore('/var/backups/nox-mem/pre-op/<latest>.db')
  )
\""

# For code rollback:
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && git diff HEAD~1 src/ | head -50"
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && git checkout HEAD~1 -- src/{graphify-ingest,index,knowledge-graph,ingest-entity}.ts"
ssh vps "cd /root/.openclaw/workspace/tools/nox-mem && npx tsc -p tsconfig.json && systemctl restart nox-mem-api"
```

## Files modified

- `staged-graphify-ingest/graphify-ingest.ts` — Fix 1 inline
- `staged-1.7a/edits/index.ts` — Fix 2 + Fix 3 (watch + kg-merge commands)
- `staged-1.7a/edits/knowledge-graph.patch.ts` — Fix 3 (`previewMergeEntities`) NEW
- `staged-1.7a/edits/ingest-entity.patch.ts` — Fix 4 (guard at head) NEW
- `staged-1.7a/tests/audit20-graphify-ingest-guard.test.ts` — NEW
- `staged-1.7a/tests/audit20-watch-guard.test.ts` — NEW
- `staged-1.7a/tests/audit20-kg-merge-withopaudit.test.ts` — NEW
- `staged-1.7a/tests/audit20-ingest-entity-guard.test.ts` — NEW

## Backward compatibility

- **Default behavior unchanged**: guards only abort on prod-scale DBs
  (>10k chunks). Eval/dev DBs unaffected.
- **Override path stable**: `NOX_ALLOW_PROD_INGEST=1` or `--allow-prod` flag
  (matches PR #145 contract).
- **No schema migration** required.
- **No new runtime deps** added.
