# Diagnóstico: /api/answer 500 + /api/conflict 503 — Wire-up Routes

**Data:** 2026-05-18 19:24 BRT  
**Deploy:** staged-wire-up-adapters (PR Wave O) + staged-wire-up (PR #92)  
**Sintomas:** `POST /api/answer` → 500 corpo vazio; `GET /api/conflict` → 503 corpo vazio

---

## TL;DR

Ambos os endpoints falharam **antes de produzir resposta** porque os dist files
dos adapters e/ou dos singletons de banco de dados **não estão em disco na VPS**
(ou não foram compilados via `npm run build` pós-rsync). Isso causa um `throw`
não capturado ou um `null`-check que o corpo vazio confirma.

---

## 1. POST /api/answer — Causa Raiz: 500 com Corpo Vazio

### Fluxo de execução esperado

```
wire-up.ts:233     POST /api/answer
  → safeHandle(fn)
  → readJsonBody(req)
  → import("./answer.js")          ← staged-P1 handler
  → mod.handleAnswerRequest({body, headers})
  → writeJson(res, out.body, ...)
```

### Onde quebra

**`answer.ts` tem imports estáticos top-level que falham antes de qualquer try/catch:**

```ts
// staged-P1/edits/src/api/answer.ts — linhas 31-36
import { answer as defaultAnswer, AnswerError } from "../lib/answer/index.js";
import type { AnswerOpts, AnswerResult } from "../lib/answer/index.js";
import {
  recordAnswer,
  type TelemetryStore,
} from "../lib/answer/telemetry.js";
```

Quando o `import("./answer.js")` na wire-up (linha 237) ocorre em runtime, o
módulo `answer.js` tenta resolver seus imports estáticos — `../lib/answer/index.js`
e `../lib/answer/telemetry.js`. Se esses arquivos **não existem em `dist/`**,
o dynamic import **lança um `ERR_MODULE_NOT_FOUND`** que escapa do
`safeHandle()`.

### Por que o corpo fica vazio (não 503)

`safeHandle()` em `wire-up.ts` (linhas 177–190) captura erros e chama
`sanitizeErrorForHttp()`. Mas se `getSanitizer()` em si lançar (porque
`../lib/error-sanitizer/sanitize.js` também não existe em dist), a chain de
catch falha e o `ServerResponse` encerra sem chamar `writeHead`. Resultado:
conexão fecha com status 500 HTTP default (definido pelo Node antes de
`writeHead` explícito) e **corpo vazio** — exatamente o sintoma observado.

### Linha de código incriminada

`staged-P1/edits/src/api/answer.ts`, linha 31:
```ts
import { answer as defaultAnswer, AnswerError } from "../lib/answer/index.js";
```

Esse import estático faz o `await import("./answer.js")` na wire-up
propagar um erro em vez de retornar o módulo.

### Fix

**Opção A (recomendada) — verificar que `dist/lib/answer/index.js` e
`dist/lib/answer/telemetry.js` existem na VPS:**

```bash
ls -la /root/.openclaw/workspace/tools/nox-mem/dist/lib/answer/
```

Se ausentes, o staged-P1 não foi buildado corretamente:

```bash
cd /root/.openclaw/workspace/tools/nox-mem
npm run build 2>&1 | tail -20
```

**Opção B — inspecionar o `lib/answer/index.ts` para confirmar que o módulo
existe no source da VPS (não só nos staged dirs locais):**

```bash
ls /root/.openclaw/workspace/tools/nox-mem/src/lib/answer/
```

**Opção C (alternativa se answer lib não deployada) — a wire-up deveria envolver
o import de `answer.js` com `tryImport` e retornar 503 em vez de deixar
propagar.** Atualmente o import de `answer.js` é `await import("./answer.js")`
direto (linha 237), sem `tryImport`. Quando `answer.js` não existe em dist ou
quebra por import estático, o throw escapa para o `safeHandle`, mas se o
próprio sanitizer também falhar o corpo fica vazio. A correção defensiva seria:

```ts
// wire-up.ts linha 237 — trocar de:
const mod: any = await import("./answer.js");
// para:
const mod: any = await tryImport("./answer.js");
if (!mod || typeof mod.handleAnswerRequest !== "function") {
  writeJson(res, { error: "not_implemented", reason: "P1 answer not deployed" }, 503);
  return;
}
```

Isso garante que mesmo com `lib/answer/index.js` ausente, o endpoint retorna
503 com corpo JSON ao invés de 500 vazio.

---

## 2. GET /api/conflict — Causa Raiz: 503 com Corpo Vazio

### Fluxo de execução esperado

```
wire-up.ts:343     GET /api/conflict
  → safeHandle(fn)
  → import("./conflict.js")           ← staged-L2 handler
  → tryImport("../lib/conflict/db.js") ← L2 DB singleton
  → se null → writeJson(503 "L2 db not deployed")
  → se ok   → mod.dispatchConflictApi(db, {...})
```

### Por que o 503 tem corpo vazio

O 503 é esperado pela lógica — o `tryImport` de `../lib/conflict/db.js`
retorna `null` quando o arquivo não existe (linha 347–349 do wire-up). Nesse
caso **o código chama `writeJson(res, {...}, 503)` corretamente**. Mas o corpo
está vazio. Isso indica que `writeJson` está sendo chamado mas **o response já
foi encerrado antes**.

Causa provável: `import("./conflict.js")` na linha 346 do wire-up **lança** ao
tentar resolver os imports estáticos de `conflict.ts`:

```ts
// staged-L2/edits/src/api/conflict.ts — linhas 17-27
import type { DBHandle } from "../lib/conflict/db.js";
import {
  getConflictById,
  listConflicts,
  updateConflictStatus,
} from "../lib/conflict/audit-writer.js";
import { collectEvidence } from "../lib/conflict/evidence.js";
import type {
  ConflictStatus,
  ResolutionInput,
  ResolutionKind,
} from "../lib/conflict/types.js";
```

Se `dist/lib/conflict/audit-writer.js` ou `dist/lib/conflict/evidence.js` não
existem, o `await import("./conflict.js")` joga antes do `tryImport` do db.
O `safeHandle` captura o erro, mas se o sanitizer falhou (mesma chain do P1),
a resposta fica vazia com status padrão — mas o Node já pode ter enviado o
status 200 antes de `writeHead` ser chamado, resultando em **503 sem corpo**
(o status vem do Content-Length/chunked não iniciado).

### Verificação alternativa: `getConflictDb()` retorna null por race condition

O `db-singleton.ts` (linhas 37–44) tem um padrão sync/async problemático:

```ts
export function getConflictDb(): DBHandle | null {
  if (_override !== null) return _override;
  if (_cached !== undefined) return _cached ?? null;
  void warmup();     // ← inicia async sem await
  return _cached ?? null;  // ← retorna undefined/null na primeira chamada
}
```

Na primeira chamada, `_cached` é `undefined`, então `getConflictDb()` retorna
`null` enquanto o warmup está pendente. O wire-up interpreta `null` como "L2 db
not deployed" e emite 503. **Mas `ensureConflictDb()` nunca é chamado no boot
da API** — o ADAPTERS.md (seção 4.3) exige `ensureConflictDb()` no boot
sequence, o que não foi adicionado ao `api-server.ts`.

O corpo vazio sugere que `conflict.js` ou seus imports também estão ausentes
em dist, fazendo o throw escapar antes de chegar no `tryImport` do db.

### Fix

**Fix principal — verificar dist dos módulos L2:**

```bash
ls /root/.openclaw/workspace/tools/nox-mem/dist/lib/conflict/
# esperado: audit-writer.js, db.js, evidence.js, types.js, db-singleton.js
```

**Fix secundário — adicionar `ensureConflictDb()` no boot (api-server.ts):**

```ts
// src/api-server.ts — no boot sequence, após o server start:
import { ensureConflictDb } from "./lib/conflict/db.js";
await ensureConflictDb(); // warm-up singleton antes da 1a request
```

Sem isso, qualquer request que chega antes do warmup retorna 503 spuriously.

**Fix terciário — mesma mudança defensiva do P1 no wire-up para conflict.js:**

```ts
// wire-up.ts linha 346 — trocar de:
const mod: any = await import("./conflict.js");
// para:
const mod: any = await tryImport("./conflict.js");
if (!mod || typeof mod.dispatchConflictApi !== "function") {
  writeJson(res, { error: "not_implemented", reason: "L2 conflict handler not deployed" }, 503);
  return;
}
```

---

## 3. Dist Files que Precisam Existir na VPS

Path base: `/root/.openclaw/workspace/tools/nox-mem/dist/`

### Obrigatórios para os dois endpoints falhando

| Dist File | Pilar | Status presumido |
|---|---|---|
| `dist/api/answer.js` | P1 | AUSENTE ou com import quebrado |
| `dist/api/conflict.js` | L2 | AUSENTE ou com import quebrado |
| `dist/lib/answer/index.js` | P1 | AUSENTE (import estático de answer.js) |
| `dist/lib/answer/telemetry.js` | P1 | AUSENTE (import estático de answer.js) |
| `dist/lib/conflict/audit-writer.js` | L2 | AUSENTE (import estático de conflict.js) |
| `dist/lib/conflict/evidence.js` | L2 | AUSENTE (import estático de conflict.js) |
| `dist/lib/conflict/types.js` | L2 | AUSENTE (import estático de conflict.js) |
| `dist/lib/conflict/db-singleton.js` | L2 | Não buildado pós-rsync |
| `dist/lib/deps/deps-registry.js` | todos | Ausente = cascade total |

### Obrigatórios para os demais adapters (contexto completo)

| Dist File | Pilar |
|---|---|
| `dist/api/wire-up.js` | router |
| `dist/api/server-deps-p1.js` | P1 adapter |
| `dist/api/server-deps-a2.js` | A2 adapter |
| `dist/api/server-deps-p5.js` | P5 adapter |
| `dist/api/server-deps-l2-l3.js` | L2+L3 adapter |
| `dist/api/server-deps-p2.js` | P2 adapter |
| `dist/api/health-confidence-adapter.js` | L3 health |
| `dist/lib/archive/server-deps.js` | A2 sidecar |
| `dist/lib/confidence/db-shim-singleton.js` | L3 sidecar |
| `dist/lib/hooks/server-deps.js` | P2 sidecar |
| `dist/lib/viewer/broadcast-singleton.js` | P5 sidecar |

---

## 4. Verificação Rápida (sem SSH, inferência)

Os staged dirs têm `tsconfig.json` em `staged-wire-up-adapters/tsconfig.json`.
O build precisa ser rodado **na VPS** após rsync de todos os `.ts`. Se qualquer
arquivo depender de outro staged dir que não foi rsynced (ex: `answer.ts` usa
`lib/answer/index.ts` que vem do staged-P1 e não do core), o `tsc` vai compilar
mas o runtime vai quebrar nos imports dinâmicos.

---

## 5. Próximos Passos para Desbloquear

1. **Verificar o `npm run build` log na VPS** — procurar erros TypeScript de
   módulos não encontrados. Rodar:
   ```bash
   cd /root/.openclaw/workspace/tools/nox-mem && npm run build 2>&1 | grep -E "error TS|Cannot find"
   ```

2. **Confirmar que `dist/lib/answer/` existe e tem `index.js` + `telemetry.js`**
   — esses são os imports estáticos que quebram o dynamic import de `answer.js`
   e causam o 500 com corpo vazio.

3. **Aplicar o fix defensivo no wire-up.ts**: trocar os dois `await import()`
   diretos (linhas 237 e 346) por `tryImport()` com check de null + 503 JSON
   explícito. Isso garante que falhas de import geram 503 com corpo legível,
   não 500 vazio. O PR atual de wire-up.ts **já usa `tryImport` para todas as
   rotas exceto `/api/answer` e `/api/conflict`** — inconsistência que precisa
   ser corrigida.

4. **Adicionar `await ensureConflictDb()` no boot da api-server.ts** — evita
   race condition onde a primeira request retorna 503 por warmup pendente.

5. **Após fix + build, smoke test:**
   ```bash
   curl -s -X POST http://127.0.0.1:18802/api/answer \
     -H 'Content-Type: application/json' \
     -d '{"question":"smoke"}' | jq .trace_id
   curl -sf http://127.0.0.1:18802/api/conflict | jq .count
   ```
   Esperado: `/api/answer` retorna 200 ou 503 com `{error, reason, trace_id}`;
   `/api/conflict` retorna `{count, rows}` ou 503 com `{error, reason}` legível.
