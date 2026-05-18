# Integration patch — privacy filter into ingest-router.ts

**Target:** `/root/.openclaw/workspace/tools/nox-mem/src/lib/ingest-router.ts`
**Branch context:** overnight/2026-05-17/A1-privacy-filter

## What to add

### 1. Import (top of file, alongside existing imports)

```typescript
import { redact } from "../privacy/filter.js";
```

### 2. Hook in `ingestFile()` — BEFORE chunk insertion

Find the point in `ingestFile()` where `chunk_text` (or the raw file text) is
assembled but BEFORE the `INSERT INTO chunks` statement runs. Insert:

```typescript
// ── Privacy filter: redact secrets before storage ─────────────────────────
const { text: clean, redactionCount, kinds } = redact(rawChunkText);
if (redactionCount > 0) {
  console.warn(
    `[privacy-filter] redacted ${redactionCount} secret(s) from ${path.basename(filePath)} — kinds: ${kinds.join(", ")}`
  );
}
// Use `clean` in place of `rawChunkText` for chunk_text value below
```

Replace the variable used for `chunk_text` in the INSERT with `clean`.

### 3. Hook in `ingestEntityFile()` — same pattern

`ingestEntityFile()` produces N+2 chunks from 3 sections. The same filter must
be applied to EACH section text before chunking. Add the same `redact()` call
to each section string (compiled, frontmatter, timeline) before they are split
into chunk rows.

```typescript
// In each section processing block:
const { text: cleanSection, redactionCount: rc, kinds: k } = redact(rawSection);
if (rc > 0) console.warn(`[privacy-filter] redacted ${rc} secret(s) in ${sectionName} of ${filePath} — kinds: ${k.join(", ")}`);
// use cleanSection instead of rawSection
```

## Verification after deploy

```bash
# 1. Create a test file with a synthetic key
echo "ANTHROPIC_API_KEY=sk-ant-test-EXAMPLEKEY1234567890abcdefghij" > /tmp/test-secret.md

# 2. Ingest it
set -a; source /root/.openclaw/.env; set +a
nox-mem ingest /tmp/test-secret.md

# 3. Search for the key prefix — must return nothing or the redacted form
nox-mem search "sk-ant-test"

# 4. Confirm the stored chunk text is redacted
# sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
#   "SELECT chunk_text FROM chunks WHERE source_file LIKE '%test-secret%'"
# Expected: contains [REDACTED:env-secret] or [REDACTED:anthropic-key], NOT the raw key
```

## Why `ingest-router.ts` not `ingestFile()` directly

Per CONVENTIONS.md §"Ingest-router unified (Fase A2 v1.6)": **never** call
`ingestFile()` directly without going through router. The filter is applied at
the `ingestFile()` and `ingestEntityFile()` level (not at routeIngest()) because:

1. Both handlers share raw text → chunk text transformation
2. routeIngest() only dispatches — it doesn't see chunk_text
3. Applying at handler level gives per-chunk granularity and correct line numbers in warnings

## False positive rate check (pre-deploy)

Run against `/root/.openclaw/workspace/tools/nox-mem/memory/entities/` to verify
no legitimate content is incorrectly redacted:

```bash
cd /root/.openclaw/workspace/tools/nox-mem
node -e "
  const { redact } = await import('./dist/privacy/filter.js');
  const { readFileSync, readdirSync, statSync } = await import('fs');
  const { join } = await import('path');
  const base = './memory/entities';
  let total = 0, redacted = 0;
  function walk(dir) {
    for (const f of readdirSync(dir)) {
      const p = join(dir, f);
      if (statSync(p).isDirectory()) { walk(p); continue; }
      if (!f.endsWith('.md')) continue;
      total++;
      const { redactionCount } = redact(readFileSync(p, 'utf8'));
      if (redactionCount > 0) redacted++;
    }
  }
  walk(base);
  console.log('Files checked:', total);
  console.log('Files with redactions:', redacted);
  console.log('FP rate:', (redacted/total*100).toFixed(1) + '%');
" --input-type=module
```
