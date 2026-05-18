# G5 — Central error sanitizer middleware

> Closes Gap **G5** from `docs/security/THREAT-MODEL.md`: "Stack trace stripping
> inconsistente cross-endpoint" (2h, next sprint).

## Por que isso existe

A2 (export/import) + Wave B (P1 answer, L3 mark) + Wave C (L2 conflict,
L3 confidence) + Wave D (P5 viewer SSE, P2 hooks) cada um implementa o próprio
bloco `catch (err) { return jsonResponse(500, { error: err.message }) }`.

Os problemas recorrentes que o sanitizer resolve:

1. **`err.message` cru vaza paths internos** (`/Users/lab/Claude/...`,
   `/root/.openclaw/.env`) — útil pra um atacante mapear o fs.
2. **Stack trace sai no body em alguns handlers** quando `JSON.stringify(err)`
   é usado em vez de `err.message`. (Pattern flagged por `audit:stack-leak`).
3. **Secrets (API keys) chegam ao client** quando provider lança
   `Error: HTTP 401 {"key": "AIzaSyXX..."}`. T-A3-1 já mitiga isso no provider
   layer com `redactSecrets()`, mas o sanitizer é uma rede de segurança extra.
4. **Status code inconsistente** — `BadPassphraseError` retornava 500 em
   `/api/export` e 400 em `/api/import`. O sanitizer centraliza o mapeamento.
5. **`requestId` ausente** — quando o cliente reporta "deu 500 na minha
   request", você não tem como achar a linha de log correspondente.

## API

### Função pura — `sanitizeErrorForHttp(err, opts)`

```typescript
import { sanitizeErrorForHttp } from "./lib/error-sanitizer/sanitize.js";

const { status, body } = sanitizeErrorForHttp(err, {
  requestId: req.headers["x-request-id"],  // optional; auto-uuid se ausente
  exposeStack: process.env.NODE_ENV !== "production",
  log: pino.error.bind(pino),
});
```

Retorna sempre:

```typescript
{
  status: number;          // mapped via ERROR_STATUS_MAP, default 500
  body: {
    error: string;         // user-safe; ≤200 chars; sem paths/secrets/newlines
    code: string;          // ex: "WEAK_PASSPHRASE", "INTERNAL_ERROR"
    requestId: string;     // sempre presente
    details?: unknown;     // sanitizada — drop forbidden keys (stack, env, __proto__)
    stack?: string;        // SÓ se exposeStack=true E NODE_ENV !== production
  }
}
```

### Middleware Express — `expressErrorMiddleware(opts)`

Drop-in `(err, req, res, next)`:

```typescript
import express from "express";
import { expressErrorMiddleware } from "./lib/error-sanitizer/middleware.js";

const app = express();

app.post("/api/answer", asyncHandler(handleAnswerRequest));
app.use(expressErrorMiddleware({
  exposeStack: process.env.NODE_ENV !== "production",
  log: (line) => pino.info(line),
}));
```

### Wrapper framework-agnostic — `sanitizerWrap(handler, opts)`

Para handlers no padrão nox-mem que retornam `{ status, headers, body }`:

```typescript
import { sanitizerWrap } from "./lib/error-sanitizer/middleware.js";

export const wrappedAnswer = sanitizerWrap(handleAnswerRequest);
// chama wrappedAnswer({ body, headers, ... }) — qualquer throw vira resposta sanitizada
```

### Helper "single-shot" — `errorToResponse(err, opts)`

Para handlers que já têm seu próprio `try/catch` e só querem trocar a linha
de retorno do `catch`:

```typescript
} catch (err) {
  return errorToResponse(err, { requestId });
}
```

## Status-code map

O `ERROR_STATUS_MAP` é a tabela canônica. Adicionar uma entrada quando uma nova
classe de Error virar parte da superfície HTTP pública.

| Error.name | Status | Code |
|---|---|---|
| `ValidationError` | 400 | `VALIDATION_ERROR` |
| `InvalidBodyError` | 400 | `INVALID_BODY` |
| `WeakPassphraseError` (A2.1) | 400 | `WEAK_PASSPHRASE` |
| `UnauthorizedError` | 401 | `UNAUTHORIZED` |
| `ForbiddenError` | 403 | `FORBIDDEN` |
| `NotFoundError` | 404 | `NOT_FOUND` |
| `ConflictError` | 409 | `CONFLICT` |
| `PayloadTooLargeError` | 413 | `PAYLOAD_TOO_LARGE` |
| `BadPassphraseError` (A2) | 422 | `BAD_PASSPHRASE` |
| `TamperedArchiveError` (A2) | 422 | `TAMPERED_ARCHIVE` |
| `MissingAADError` (A2) | 422 | `MISSING_AAD` |
| `SchemaVersionError` (A2) | 422 | `SCHEMA_VERSION_MISMATCH` |
| `ManifestError` (A2) | 422 | `MANIFEST_ERROR` |
| `ArchiveFormatError` (A2) | 422 | `ARCHIVE_FORMAT_ERROR` |
| `HallucinationError` (P1) | 422 | `HALLUCINATION_AFTER_RETRY` |
| `RateLimitError` | 429 | `RATE_LIMITED` |
| `CostCapExceededError` (A3) | 429 | `COST_CAP_EXCEEDED` |
| `LLMUnreachableError` (P1) | 502 | `LLM_UNREACHABLE` |
| `RetrievalEmptyError` (P1) | 503 | `RETRIEVAL_EMPTY` |
| `LLMTimeoutError` (P1) | 504 | `LLM_TIMEOUT` |
| (unknown) | 500 | `INTERNAL_ERROR` |

## Patterns que o sanitizer detecta

### Internal paths — message é substituída por `"request failed (details redacted)"`

```
/Users/lab/...     → drop
/home/foo/...      → drop
/root/...          → drop
/var/... /etc/...  → drop
/tmp/... /opt/...  → drop
C:\Users\...       → drop
(node:1234)        → drop
```

### Secrets — substituídos por `[REDACTED]`

```
AIza[20+]                   → [REDACTED]  (Google API)
sk-[20+]                    → [REDACTED]  (OpenAI / Stripe-style)
Bearer [20+]                → [REDACTED]
eyJ[...].[...].[...]        → [REDACTED]  (JWT)
xox[bps]-[20+]              → [REDACTED]  (Slack)
ghp_[20+]                   → [REDACTED]  (GitHub PAT)
key=[16+] / token=[16+]     → [REDACTED]
password=... / passphrase=… → [REDACTED]
```

### Env-style — redacted

```
NOX_*=...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
AWS_*=...
```

### Forbidden top-level keys em `details`

Drop direto: `stack`, `cause`, `env`, `process`, `__proto__`.

## Migration guide — quem precisa do wire-up

| Handler | Status | Migration step |
|---|---|---|
| `staged-P1/edits/src/api/answer.ts` | Has own catch w/ AnswerError mapping. Migrate to `errorToResponse(err, { requestId })` in the catch. | 5 lines |
| `staged-A2/edits/src/api/export.ts` | Has 500-catch with raw `err.message`. **LEAKS PATHS**. Migrate. | 8 lines |
| `staged-A2/edits/src/api/import.ts` | Same as export.ts. Migrate. | 8 lines |
| `staged-L3/edits/src/api/mark.ts` | TODO — confidence/mark endpoint, raw `err.message` leak in 500 path. | 5 lines |
| `staged-L2/edits/src/api/conflict.ts` | TODO — Wave C, untested for stack leak. | unknown |
| `staged-P2/edits/src/api/hooks.ts` | TODO — Wave D hooks autocapture. | unknown |
| `staged-P5/edits/src/api/viewer.ts` | TODO — SSE stream needs sanitizer for error frames. | unknown |
| Lib answer.ts internal AnswerError throw → handler | Already mapped status; can drop manual mapping after migration. | -10 lines net |

Wave G (next) tracks the actual code edits. This package only ships:
1. The sanitizer lib + tests.
2. Example refactors (`src/api/answer.example.ts`, `src/api/export.example.ts`).
3. The audit script `scripts/audit-stack-leak.sh`.

## Detect-and-correct: `npm run audit:stack-leak`

The script greps for known leak patterns across all `staged-*/edits/src/**`:

```bash
$ npm run audit:stack-leak --prefix staged-G5
[audit] scanning for stack-leak patterns…
[audit] FOUND  staged-A2/edits/src/api/export.ts:92  jsonResponse(500, { error: msg })
[audit] FOUND  staged-A2/edits/src/api/import.ts:88  err.message in 500 path
[audit] PASS   staged-P1/edits/src/api/answer.ts (handles AnswerError before raw catch)
[audit] FAIL   2 leaks detected — see docs/ERROR-SANITIZER.md migration guide
```

Patterns detected:

- `JSON\.stringify\(err\)` — almost always leaks stack via Error JSON serialization quirks.
- `err\.stack` em response body.
- `(err as Error)\.message` em 500 path sem sanitizer.
- `\b500.*\.message\b` em jsonResponse-style helpers.

False positives possíveis em catch blocks que já delegam pro sanitizer. O script
warna mas não falha — review manual ainda recomendado.

## Threat-model traceability

- Section 6.2 T-A3-1.1 "Stack trace stripping inconsistente"
- Recommendation #2 (next sprint, 2h)
- Gap row G5 (Appendix A)

## Decisões locked

1. **Não-Error inputs (string, null, undefined) viram `new Error()`** — never throw on coerce.
2. **`stack` SEMPRE strippado em `NODE_ENV=production`** — mesmo se caller pedir `exposeStack: true`.
   Production é o branch-protector final.
3. **`error.message` para 5xx NUNCA é ecoado** — sempre `"internal error"`.
   Para 4xx que não tem `safeMsg` mapeado, escrubada (paths/secrets/newlines).
4. **`requestId` SEMPRE gerado** — mesmo no fallback de erro do sanitizer.
   Logs precisam de uma chave correlacional sempre.
5. **`details` é opt-in pela classe Error** — sanitizer só passa adiante se `err.details`
   existir. Default omit.

## Não faz parte do escopo

- Async iterator / SSE stream sanitization (P5 viewer) — Wave G.
- Per-tenant requestId rotation policy — out of scope, deploy concern.
- Sentry / external observability hooks — caller wires via `opts.log`.
- I18n nas mensagens canned — Wave H (PT-BR support).
