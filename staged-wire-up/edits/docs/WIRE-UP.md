# WIRE-UP — Registro de rotas Wave A→K em `src/api-server.ts`

> *Pain-weighted hybrid memory with shadow discipline — yours by design.* (D45 tagline — D40 superseded.)
>
> Este patch fecha o gap pós-deploy: 319 arquivos TS sincronizados para a VPS, mas o roteador de `src/api-server.ts` (native `http`, switch/case) nunca foi atualizado para conhecer os novos handlers. Resultado: cada endpoint Wave A→K respondia 404.

---

## 1. O que esse PR faz

Adiciona dois artefatos sem mexer em código de prod:

1. `staged-wire-up/edits/src/api/wire-up.ts` — roteador único que mapeia 14 rotas Wave A→K para os handlers framework-agnostic já implantados.
2. `staged-wire-up/edits/src/api-server.patch.md` — patch instruction para `src/api-server.ts`: 1 `import` + 3 linhas dentro do `handleRequest()`.

Após aplicar o patch e reiniciar `nox-mem-api`, os endpoints abaixo passam a responder:

| Wave | Método + path | Handler-fonte |
|---|---|---|
| P1 | POST `/api/answer` | `src/api/answer.ts::handleAnswerRequest` |
| A2 | POST `/api/export` | `src/api/export.ts::handleExport` |
| A2 | POST `/api/import` | `src/api/import.ts::handleImport` |
| P5 | GET `/api/events/stream` | `src/api/events-stream.ts::openSseStream` |
| P5 | GET `/viewer/*` | `src/api/viewer-static.ts::serveViewerFile` |
| L2 | GET `/api/conflict` | `src/api/conflict.ts::dispatchConflictApi` |
| L2 | GET `/api/conflict/:id` | idem |
| L2 | POST `/api/conflict/:id/resolve` | idem |
| L3 | POST `/api/chunk/:id/mark` | `src/api/mark.ts::handleMarkRequest` |
| L3 | POST `/api/chunk/:id/supersede` | `src/api/mark.ts::handleSupersedeRequest` |
| L3 | GET `/api/health/confidence` | `src/api/health-confidence.ts::handleHealthConfidence` |
| P2 | GET `/api/hooks/status` | `src/api/hooks.ts::handleHooksRequest` |
| P2 | GET `/api/hooks/recent` | idem |
| P2 | POST `/api/hooks/dryrun` | idem |

Total: **14 endpoints registrados**.

---

## 2. Por que existe um arquivo separado em vez de inline em `api-server.ts`

Três razões — pode pular se você só quer aplicar o patch.

1. **Separação de eras.** `api-server.ts` é o roteador v1.6 (linha estável, mudou poucas vezes desde 2026-04). Wave A→K adiciona 14 rotas vindas de 7 staged dirs diferentes (P1, A2, P5, L2, L3, P2 + futuro). Inline ia 5× o tamanho do arquivo e gerar merge conflict toda wave nova.
2. **Imports lazy.** O wire-up usa `await import(...)` em `tryImport()`. Se uma dependência de wave (ex.: `lib/conflict/db.js` da L2) não foi rsync'd ainda, a rota responde 503 `not_implemented` com `reason` e `hint` — o servidor não trava no boot. Inline `import` no topo de `api-server.ts` faria o processo quebrar antes do `listen()`.
3. **Superfície única de testes.** `wire-up.test.ts` cobre todas as 14 rotas sem subir o servidor real. Roda em <2s, valida route table + guards + sanitizer.

---

## 3. Como deployar (mesmo padrão de `DEPLOY-WAVE-B.md`)

> Pré-requisitos: você está no host VPS com `set -a; source /root/.openclaw/.env; set +a` rodado (regra #1).

### 3.1 Rsync os novos arquivos

Do **repo local** (com o branch `wire-up/2026-05-18/api-routes` checkado out):

```bash
NM=/root/.openclaw/workspace/tools/nox-mem
rsync -avh staged-wire-up/edits/src/api/wire-up.ts \
  root@${VPS}:${NM}/src/api/wire-up.ts
rsync -avh staged-wire-up/edits/src/api/__tests__/wire-up.test.ts \
  root@${VPS}:${NM}/src/api/__tests__/wire-up.test.ts
rsync -avh staged-wire-up/edits/docs/WIRE-UP.md \
  root@${VPS}:${NM}/docs/WIRE-UP.md
```

### 3.2 Aplicar o patch em `src/api-server.ts`

Siga o passo a passo de `staged-wire-up/edits/src/api-server.patch.md`. Resumo:

1. Adicione `import { registerWireUpRoutes } from "./api/wire-up.js";` perto dos imports top do arquivo.
2. Converta o `default:` do switch em bloco e chame o wire-up **antes** do 404:
   ```ts
   default: {
     if (await registerWireUpRoutes(req, res)) break;
     json(res, { error: "Not found", endpoints: [...] }, 404);
   }
   ```

### 3.3 Rebuild + restart

```bash
cd ${NM}
npm run build
systemctl restart nox-mem-api
sleep 2
curl -sf http://127.0.0.1:18802/api/health | jq .chunks.total
```

### 3.4 Smoke-test cada wave

```bash
# P1
curl -sf -X POST http://127.0.0.1:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"smoke"}' | jq .

# A2 (precisa lib/archive/server-deps.js)
curl -s -X POST http://127.0.0.1:18802/api/export \
  -H 'Content-Type: application/json' \
  -d '{"unencrypted":true}' -o /tmp/export-smoke.tgz -w '%{http_code}\n'

# L2
curl -sf "http://127.0.0.1:18802/api/conflict?status=open&limit=5" | jq .count

# L3
curl -sf http://127.0.0.1:18802/api/health/confidence | jq .

# P2
curl -sf http://127.0.0.1:18802/api/hooks/status | jq .config.enabled

# P5 (SSE — connect 3s then quit)
timeout 3 curl -sN http://127.0.0.1:18802/api/events/stream || true
```

503 com `"reason": "<wave> deps not deployed"` significa que a wire-up está OK, mas a wave em si ainda não tem os deps de runtime (ex.: builder de DB). Isso é tratado em PR separado por wave.

---

## 4. Plano de teste

1. **Unit (este PR):** `node --test staged-wire-up/edits/src/api/__tests__/wire-up.test.ts`
   - 20+ casos cobrindo route matching, dispatch, G6 guard, CORS, traversal.
2. **Smoke (pós-deploy):** seção 3.4 acima.
3. **Regression:** os endpoints v1.6 (`/api/health`, `/api/kg`, `/api/search`, etc.) continuam respondendo idênticos — wire-up só intercepta paths que `matchesWireUpRoute` reconhece.
4. **Security:**
   - `POST /api/import`, `POST /api/conflict/:id/resolve`, `POST /api/chunk/:id/mark`, `POST /api/chunk/:id/supersede`, `POST /api/hooks/dryrun` exigem requisição vinda de `127.0.0.1` (ou Bearer válido se `NOX_API_BEARER_TOKEN` setado) — coberto por `localhost-guard.ts`.
   - 500s nunca vazam stack/path: passam por `sanitizeErrorForHttp` (G5).

---

## 5. Rollback

Se algo der errado pós-deploy, dois passos:

1. `git revert <commit-do-patch-api-server>` no repo, rsync `src/api-server.ts` antigo de volta, `npm run build`, `systemctl restart nox-mem-api`.
2. Como alternativa zero-touch: o `wire-up.ts` é **idempotente para paths que não conhece**. Mesmo se ficar instalado, ele só intercepta as 14 rotas Wave A→K. Para "desligar sem reverter", basta comentar o `if (await registerWireUpRoutes(req, res)) break;` dentro do `default:` e reiniciar.

Os endpoints existentes (`/api/health`, etc.) ficam intactos em qualquer dos cenários.

---

## 6. Decisões intencionais (vale revisar)

- **Native http, não Express.** Match com o pattern existente. Adicionar Express custaria 1 dep + boot extra; o ganho seria sintaxe ligeiramente mais curta. Não vale.
- **503 em vez de 500 quando a wave não tem deps.** "Not implemented" é uma mensagem honesta: a wave foi rsync'd, mas o adapter de DB ainda não. 500 era impreciso (não é um crash) e poluiria logs.
- **CORS aberto (`*`).** Paridade com `api-server.ts::json`. A API está atrás de bind localhost por padrão (G6); CORS aberto não muda postura de segurança quando a porta não está exposta.
- **Body limit 64 MiB.** Apenas `/api/import` recebe payload grande (archive_b64). Outros endpoints raramente passam de 4 KiB; o limite alto não cria risco DoS porque `localhost-guard` já bloqueia origem remota nesse endpoint.

---

## 7. Trabalho follow-up (não nesse PR)

- `src/lib/archive/server-deps.ts` (A2): adapter que entrega `dbReader` + `loadExisting` + `persist` para o handler de export/import. Atualmente as rotas respondem 503.
- `src/lib/conflict/db.ts::getConflictDb` (L2): singleton DB handle. Idem.
- `src/lib/confidence/db-shim.ts::getConfidenceDb` (L3): idem.
- `src/lib/hooks/server-deps.ts` (P2): idem.
- `src/lib/viewer/broadcast.ts::getBroadcaster` (P5): singleton broadcaster para SSE.

Cada um vira PR isolado depois — quando o adapter chegar, a rota correspondente passa de 503 para 200 sem mexer no wire-up.

---

## 8. Arquivos desse PR

| Arquivo | Linhas |
|---|---|
| `staged-wire-up/edits/src/api/wire-up.ts` | ~400 |
| `staged-wire-up/edits/src/api/__tests__/wire-up.test.ts` | ~280 |
| `staged-wire-up/edits/src/api-server.patch.md` | ~80 |
| `staged-wire-up/edits/docs/WIRE-UP.md` | este arquivo |

Total: 4 arquivos, ~800 linhas. Zero mudança em código de prod até o operador rodar o patch da seção 3.2 manualmente.
