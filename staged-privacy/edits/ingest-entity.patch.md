# Integration patch — privacy hook em ingest-entity.ts (follow-up Wave Q)

**Target:** `/root/.openclaw/workspace/tools/nox-mem/src/ingest-entity.ts`

**Status:** Pendente deploy — PR `feat/privacy-ingest-entity-hook` aguarda revisão.

**Contexto:**
- `src/ingest.ts` já tem o hook desde 2026-05-18 (ver `ingest-router.patch.md`)
- `src/ingest-entity.ts` processa entity files com 3 sections independentes (frontmatter, compiled, timeline)
- Cada section vira N chunks com `section_boost` via `INSERT INTO chunks`
- O hook precisa ir em cada section text, antes do INSERT, espelhando o padrão de `ingest.ts`

---

## Mudanças a aplicar em `src/ingest-entity.ts`

### 1. Import (adicionar após last existing import, antes da primeira declaração)

```typescript
import { redact } from "./privacy/filter.js";
```

> Nota: o patch.md original de Wave Q mencionava alias `_redactPrivacy` pra evitar conflito.
> Verificar se `redact` já está importado no arquivo — se sim, usar alias:
> `import { redact as _redactPrivacy } from "./privacy/filter.js";`
> e adaptar as chamadas abaixo com `_redactPrivacy(...)`.

---

### 2. Hook em cada section text (antes do INSERT)

O padrão exato de `ingest.ts` (linha 44-48 do `ingest-router.patch.md`):

```typescript
const _r = redact(sectionText);
sectionText = _r.text;
if (_r.redactionCount > 0) {
  console.warn(
    `[privacy-filter] redacted ${_r.redactionCount} secret(s) in entity section — kinds: ${_r.kinds.join(", ")}`
  );
}
```

Aplicar em **3 lugares** dentro de `ingestEntityFile()`:

#### a) Section: frontmatter (antes do INSERT com `section: "frontmatter"`)

Localizar o bloco onde `frontmatterText` (ou nome equivalente) é preparado para INSERT.
Inserir imediatamente antes do `db.prepare(...).run(...)`:

```typescript
// Privacy filter: redact before INSERT (staged-privacy follow-up)
const _rFm = redact(frontmatterText);
frontmatterText = _rFm.text;
if (_rFm.redactionCount > 0) {
  console.warn(
    `[privacy-filter] redacted ${_rFm.redactionCount} secret(s) in frontmatter — kinds: ${_rFm.kinds.join(", ")}`
  );
}
```

#### b) Section: compiled (antes do INSERT com `section: "compiled"`)

```typescript
// Privacy filter: redact before INSERT (staged-privacy follow-up)
const _rCo = redact(compiledText);
compiledText = _rCo.text;
if (_rCo.redactionCount > 0) {
  console.warn(
    `[privacy-filter] redacted ${_rCo.redactionCount} secret(s) in compiled — kinds: ${_rCo.kinds.join(", ")}`
  );
}
```

#### c) Section: timeline (antes do INSERT com `section: "timeline"`)

```typescript
// Privacy filter: redact before INSERT (staged-privacy follow-up)
const _rTl = redact(timelineText);
timelineText = _rTl.text;
if (_rTl.redactionCount > 0) {
  console.warn(
    `[privacy-filter] redacted ${_rTl.redactionCount} secret(s) in timeline — kinds: ${_rTl.kinds.join(", ")}`
  );
}
```

---

### 3. Variante: aplicar em nível de chunk (se a função gera chunks antes do INSERT)

Se `ingestEntityFile()` iterar sobre chunks (array de `{ text, section, section_boost }`) antes
do INSERT em vez de ter 3 blocos separados, usar a variante:

```typescript
for (const chunk of chunks) {
  const _r = redact(chunk.text);
  if (_r.redactionCount > 0) {
    console.warn(
      `[privacy-filter] redacted ${_r.redactionCount} secret(s) in entity chunk (section=${chunk.section}) — kinds: ${_r.kinds.join(", ")}`
    );
  }
  chunk.text = _r.text;
}
```

---

## Verificação pós-deploy

```bash
ssh root@VPS
cd /root/.openclaw/workspace/tools/nox-mem

# Cria entity fixture com fake key
cat > /tmp/test-entity-privacy.md << 'EOF'
---
type: test
slug: privacy-test-entity
---

## Compiled

ANTHROPIC_API_KEY=sk-ant-oat-FAKEKEY00000000000000000000000000000000

## Timeline

### 2026-05-19
- Created for privacy test.
EOF

# Ingest em DB temporário
NOX_DB_PATH=/var/backups/nox-mem/pre-op/entity-privacy-test.db \
  nox-mem ingest-entity /tmp/test-entity-privacy.md

# Expected output deve conter:
# [privacy-filter] redacted N secret(s) in ... — kinds: ...

# Verificar que a chave NÃO ficou no DB
sqlite3 /var/backups/nox-mem/pre-op/entity-privacy-test.db \
  "SELECT text FROM chunks WHERE text LIKE '%sk-ant-oat-FAKEKEY%'" \
  | wc -l
# Esperado: 0 (zero rows com a chave raw)

# Cleanup
rm /tmp/test-entity-privacy.md
rm -f /var/backups/nox-mem/pre-op/entity-privacy-test.db
```

---

## Rollback

```bash
cp $NM/src/ingest-entity.ts.bak-pre-privacy-* $NM/src/ingest-entity.ts
cd $NM && npm run build && systemctl restart nox-mem-api
```

---

## Cross-links

- `staged-privacy/edits/privacy/filter.ts` — implementação `redact()`
- `staged-privacy/edits/privacy/patterns.ts` — regex patterns
- `staged-privacy/edits/ingest-router.patch.md` — padrão exato aplicado em `ingest.ts`
- `staged-privacy/edits/privacy/__tests__/ingest-entity-privacy.test.ts` — testes deste follow-up
- VPS path: `/root/.openclaw/workspace/tools/nox-mem/src/ingest-entity.ts`
