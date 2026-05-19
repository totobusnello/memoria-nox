# Integration patch — privacy filter applied 2026-05-18 BRT

**Target (REAL apply target — corrigido):** `/root/.openclaw/workspace/tools/nox-mem/src/ingest.ts` (NÃO `ingest-router.ts` como a versão anterior assumia)

**Status:** ✅ APLICADO em prod VPS 2026-05-18 ~21:30 BRT.

**Validação real:**
```
$ nox-mem ingest /tmp/privacy-test.md
[privacy-filter] redacted 2 secret(s) in ../../../tmp/privacy-test.md — kinds: anthropic-key, env-secret
[INFO] Ingested /tmp/privacy-test.md: 1 chunks
```

---

## Por que `ingest.ts` e não `ingest-router.ts`

A versão original do patch.md apontava pra `src/lib/ingest-router.ts`, mas esse arquivo é um **dispatcher** (route entity vs markdown), não o handler real. O INSERT INTO chunks acontece em:

- `src/ingest.ts::ingestFile()` (linha 154) — markdown puro
- `src/ingest-entity.ts::ingestEntityFile()` (linha 171) — entity files com 3 sections

O hook precisa ir ANTES do INSERT em ambos. Tonight apliquei só em `ingest.ts` (cobre 99% do volume). `ingest-entity.ts` é follow-up (~5min) — mesmo padrão.

---

## Mudanças aplicadas em `src/ingest.ts`

### 1. Import (após last existing import)

```typescript
import { redact } from "./privacy/filter.js";
```

### 2. Hook após `sanitizeUtf8(content)` (line 129, BEFORE chunking)

Aplicar à `content` inteiro (não por chunk) preserva chunk boundaries enquanto redaciona em todo o documento:

```typescript
  content = sanitizeUtf8(content);

  // Privacy filter: redact secrets/PII before storage (staged-privacy)
  const _r = redact(content);
  content = _r.text;
  if (_r.redactionCount > 0) {
    console.warn(`[privacy-filter] redacted ${_r.redactionCount} secret(s) in ${relPath} — kinds: ${_r.kinds.join(", ")}`);
  }
```

### 3. Verificação pós-deploy

```bash
ssh root@VPS
cd /root/.openclaw/workspace/tools/nox-mem

# Confirma a CLI carrega
nox-mem ingest --help

# Test synthetic secret (CRIA test markdown isolado, ingest em DB temp)
cat > /tmp/privacy-test.md << EOF
# Test
ANTHROPIC_API_KEY=sk-ant-test-EXAMPLEKEY...
SOME_VAR=secret123
EOF

NOX_DB_PATH=/var/backups/nox-mem/pre-op/privacy-test.db nox-mem ingest /tmp/privacy-test.md
# Expected: "[privacy-filter] redacted N secret(s) ... — kinds: ..."

rm /tmp/privacy-test.md /var/backups/nox-mem/pre-op/privacy-test.db
```

---

## Pendente follow-up

### ingest-entity.ts — apply same pattern

Em `src/ingest-entity.ts`, há 3 sections (compiled, frontmatter, timeline) que vão pra `INSERT INTO chunks` com section_boost. Cada section text precisa do mesmo `redact()` antes do chunk row.

Estimated time: ~15 min. Status: import já adicionado (`_redactPrivacy` alias pra evitar conflito), só falta hook chamadas.

### Rollback procedure

Se redação causar problemas:

```bash
cp $NM/src/ingest.ts.bak-pre-privacy-* $NM/src/ingest.ts
cd $NM && npm run build && systemctl restart nox-mem-api
```

Backup automaticamente criado no apply step.

---

**Cross-links:**
- `staged-privacy/edits/privacy/filter.ts` — implementation
- `staged-privacy/edits/privacy/patterns.ts` — regex patterns (anthropic-key, openai-key, env-secret, etc)
- VPS path: `/root/.openclaw/workspace/tools/nox-mem/src/ingest.ts` (live)
- Backup: `/root/.openclaw/workspace/tools/nox-mem/src/ingest.ts.bak-pre-privacy-*`
