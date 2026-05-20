# staged-observability — Deploy Instructions

Fix: TS5097 errors em `src/observability/__tests__/` — imports com `.ts` → `.js`

## Errors antes do fix

```
src/observability/__tests__/adapters.test.ts(16,22): error TS5097: An import path can only end with a '.ts' extension when 'allowImportingTsExtensions' is enabled.
src/observability/__tests__/adapters.test.ts(17,32): error TS5097: ...
src/observability/__tests__/adapters.test.ts(21,3): error TS5097: ...
src/observability/__tests__/adapters.test.ts(26,3): error TS5097: ...
src/observability/__tests__/cardinality.test.ts(9,3): error TS5097: ...
src/observability/__tests__/collectors.test.ts(19,3): error TS5097: ...
src/observability/__tests__/collectors.test.ts(20,28): error TS5097: ...
src/observability/__tests__/collectors.test.ts(23,3): error TS5097: ...
src/observability/__tests__/collectors.test.ts(27,3): error TS5097: ...
src/observability/__tests__/collectors.test.ts(32,3): error TS5097: ...
src/observability/__tests__/exporter.test.ts(11,3): error TS5097: ...
src/observability/__tests__/exporter.test.ts(12,28): error TS5097: ...
src/observability/__tests__/exporter.test.ts(14,3): error TS5097: ...
src/observability/__tests__/privacy-guard.test.ts(10,3): error TS5097: ...
src/observability/__tests__/privacy-guard.test.ts(12,42): error TS5097: ...
src/observability/__tests__/record.test.ts(21,3): error TS5097: ...
src/observability/__tests__/record.test.ts(37,3): error TS5097: ...
```

## Fix aplicado

Todos os imports nos 6 files alterados de `.ts` → `.js` (convenção ESM após compilação).

## Arquivos modificados

- `src/observability/__tests__/adapters.test.ts`
- `src/observability/__tests__/cardinality.test.ts`
- `src/observability/__tests__/collectors.test.ts`
- `src/observability/__tests__/exporter.test.ts`
- `src/observability/__tests__/privacy-guard.test.ts`
- `src/observability/__tests__/record.test.ts`

## Deploy na VPS

```bash
# 1. Copiar os 6 files para a VPS
scp staged-observability/edits/src/observability/__tests__/adapters.test.ts \
    staged-observability/edits/src/observability/__tests__/cardinality.test.ts \
    staged-observability/edits/src/observability/__tests__/collectors.test.ts \
    staged-observability/edits/src/observability/__tests__/exporter.test.ts \
    staged-observability/edits/src/observability/__tests__/privacy-guard.test.ts \
    staged-observability/edits/src/observability/__tests__/record.test.ts \
    root@187.77.234.79:/root/.openclaw/workspace/tools/nox-mem/src/observability/__tests__/

# 2. Verificar zero TS5097 errors nos test files
ssh root@187.77.234.79 '
  cd /root/.openclaw/workspace/tools/nox-mem
  npx tsc --noEmit --allowImportingTsExtensions false 2>&1 | grep "__tests__" | grep TS5097 | wc -l
  # Expected: 0
'

# 3. Rebuild para confirmar build clean
ssh root@187.77.234.79 '
  cd /root/.openclaw/workspace/tools/nox-mem
  npm run build 2>&1 | grep -E "^src/observability/__tests__" | wc -l
  # Expected: 0
'
```

## Rollback

Não há risco: apenas import paths mudaram, comportamento idêntico. Em caso de problema:
```bash
ssh root@187.77.234.79 '
  cd /root/.openclaw/workspace/tools/nox-mem
  git diff HEAD -- src/observability/__tests__/
'
```
