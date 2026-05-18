# G5 — Central error sanitizer middleware

> Closes Gap **G5** from `docs/security/THREAT-MODEL.md` (High, 2h estimated).

## What it does

One module to normalise every HTTP error response across Wave B/C/D handlers.
Strips stack traces, internal paths, secrets, env-var values. Maps known
error classes to HTTP status codes. Always emits `requestId` for support.

## File layout

```
staged-G5/edits/
├── src/lib/error-sanitizer/
│   ├── sanitize.ts          # core sanitizeErrorForHttp()
│   ├── middleware.ts        # express + framework-agnostic wrappers
│   └── __tests__/
│       └── sanitize.test.ts # 28 tests
├── src/api/
│   ├── answer.example.ts    # how to migrate staged-P1/answer.ts (not auto-applied)
│   └── export.example.ts    # how to migrate staged-A2/export.ts (not auto-applied)
├── scripts/
│   └── audit-stack-leak.sh  # `npm run audit:stack-leak` — detects unsanitized handlers
└── docs/
    └── ERROR-SANITIZER.md   # 250-line migration guide + status map
```

## Quick start

```typescript
import { sanitizeErrorForHttp } from "./lib/error-sanitizer/sanitize.js";
import { errorToResponse } from "./lib/error-sanitizer/middleware.js";

// In any HTTP handler with the {status, headers, body} return shape:
try {
  // … happy path …
} catch (err) {
  return errorToResponse(err, { requestId });
}
```

## Test summary

```
$ npm test --prefix staged-G5
# sanitize.test.ts → 28 tests across 3 suites
# - sanitizeErrorForHttp        21 tests
# - middleware integration       4 tests
# - ERROR_STATUS_MAP integrity   3 tests
```

## Migration scope

Not auto-applied. See `docs/ERROR-SANITIZER.md` for the per-handler migration
list. Wave G will land the real edits into staged-P1/A2/L2/L3/P2/P5.

## Detect leaks pre-commit

```bash
npm run audit:stack-leak --prefix staged-G5
# scans staged-*/edits/src/**/*.ts for known leak patterns
```

Wire into pre-commit hook OR `.github/workflows/security.yml`.

## Threat-model traceability

- THREAT-MODEL.md §6.2 T-A3-1.1 (stack-trace stripping inconsistente)
- High-priority follow-up #2 (2h estimate)
- Gap row G5 in Appendix A
