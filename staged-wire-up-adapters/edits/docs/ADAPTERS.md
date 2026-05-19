# ADAPTERS — Wire-up runtime bindings (Wave O)

> **Pain-weighted hybrid memory with shadow discipline — yours by design.** (D45 tagline — D40 superseded.)
>
> Este PR fecha o gap pós-#92: a wire-up.ts registra 14 rotas Wave A→K, mas
> 12 delas respondem 503 `not_implemented` porque os módulos de runtime que
> conectam handler ↔ DB ↔ event-bus não estavam deployados. Adapters fecham
> isso.

---

## 1. O que esse PR entrega

Cinco módulos `server-deps-*.ts` em `src/api/` + 4 sidecars em `src/lib/*/`:

| Adapter | Pilar | Endpoints destravados | Deps que injeta |
|---|---|---|---|
| `server-deps-p1.ts`        | P1 | `POST /api/answer` | TelemetryStore (sqlite) + sessionId |
| `server-deps-a2.ts`        | A2 | `POST /api/export`, `POST /api/import` | dbReader, loadExisting, persist, multipart parser |
| `server-deps-p5.ts`        | P5 | `GET /api/events/stream`, `GET /viewer/*` | Broadcaster singleton + redaction + viewer root |
| `server-deps-l2-l3.ts`     | L2+L3 | `GET /api/conflict`, `GET /api/conflict/:id`, `POST /api/conflict/:id/resolve`, `POST /api/chunk/:id/mark`, `POST /api/chunk/:id/supersede`, `GET /api/health/confidence` | L2 + L3 DB singletons + schema readiness probe |
| `server-deps-p2.ts`        | P2 | `GET /api/hooks/status`, `GET /api/hooks/recent`, `POST /api/hooks/dryrun` | HooksApiDeps (readRecent, inspectQueue, telemetry sink, dryRunHook) |

Mais o **central singleton resolver** em `src/lib/deps/deps-registry.ts` — uma
única conexão `better-sqlite3` compartilhada pelos cinco adapters (regra de
ouro #2).

---

## 2. Como adapters conectam handlers ao runtime

Cada handler Wave A→K (P1/A2/L2/L3/P2/P5) foi escrito framework-agnostic. Ele
recebe deps via parâmetro:

```ts
// staged-A2/edits/src/api/export.ts
export async function handleExport(
  body: HttpExportBody,
  deps: HttpExportDeps,    // ← injetado pelo adapter
): Promise<HttpResponse>
```

O wire-up.ts (#92) é o roteador. Ele faz lazy-import do adapter:

```ts
// staged-wire-up/edits/src/api/wire-up.ts (linha 254)
const depsMod = await tryImport("../lib/archive/server-deps.js");
if (!depsMod?.buildExportDeps) {
  writeJson(res, { error: "not_implemented", ... }, 503);
  return;
}
const out = await handleExport(body, await depsMod.buildExportDeps());
```

Antes desse PR, `lib/archive/server-deps.js` não existia → 503 fixo. Agora
existe (`staged-wire-up-adapters/edits/src/lib/archive/server-deps.ts`) →
rota retorna 200 com o archive real.

**Fluxo end-to-end por request:**

```
HTTP request
   │
   ▼
src/api-server.ts (host)                ← inalterado
   │
   ▼
wire-up.ts::registerWireUpRoutes()       ← #92 (já merged)
   │  await import("./lib/.../server-deps.js")
   ▼
server-deps-<pillar>.ts (este PR)
   │  buildXxxDeps() / handleXxx()
   ▼
deps-registry.ts::getDb() singleton
   │
   ▼
better-sqlite3 (uma só conexão por processo)
```

---

## 3. Dependências por pilar

### 3.1 P1 (answer) — `server-deps-p1.ts`

- **Lê:** `answer_telemetry` (schema v11) — verifica via `sqlite_master` antes
  de prepare.
- **Escreve:** INSERT `answer_telemetry` (privacy: só `sha256(question)[:16]`,
  nunca raw text).
- **Headers:** extrai `X-Session-Id` p/ telemetria.
- **Falha:** quando DB indisponível, retorna no-op store (privacy rule —
  telemetria nunca quebra answer path).

### 3.2 A2 (export/import) — `server-deps-a2.ts` + `lib/archive/server-deps.ts`

- **Export:** `dbReader()` lê `chunks` + `kg_entities` + `kg_relations` +
  `ops_audit` + embeddings (`vec_chunk_map` + `vec_chunks` via float32 LE).
- **Import:** `loadExisting()` simétrico + `persist()` com transaction
  (chunks upsert por id, kg_entities upsert por slug, kg_relations
  INSERT OR IGNORE, ops_audit INSERT OR IGNORE — append-only).
- **Streaming:** `writeExportResponse()` usa Transfer-Encoding chunked acima
  de 16 MiB, cedendo loop a cada 1 MiB.
- **Multipart:** `parseMultipartFirstFile()` aceita `multipart/form-data`
  para uploads diretos via curl `--data-binary @file.tgz` (alternativa ao
  JSON `archive_b64`).
- **Buffer pool aliasing:** `readEmbeddings()` copia float32 via
  `new Float32Array(f32)` — evita Buffer pool aliasing (memória feedback
  `buffer_pool_aliasing_in_typed_arrays`).

### 3.3 P5 (SSE + viewer) — `server-deps-p5.ts` + `lib/viewer/broadcast-singleton.ts`

- **Broadcaster:** `getBroadcaster()` sync (top-level await resolve `Broadcaster`
  class no module load). Wire-up.ts depende de chamada SYNC.
- **Redaction:** `redactEnvelope()` mascara `query_text` → `[redacted]` e
  trunca `content` em 40 chars + ellipsis. Bypass via `NOX_VIEWER_SHOW_QUERY=1`.
  Default-deny (transparência opt-in).
- **Viewer root:** `resolveViewerRoot()` honra `NOX_VIEWER_ROOT`,
  fallback `<cwd>/dist/viewer/`.
- **SSE pump:** `pumpSseToResponse()` drena async iterable em ServerResponse
  com backpressure (await `drain`).

### 3.4 L2+L3 — `server-deps-l2-l3.ts` + dois sidecars

- **L2 DB singleton:** `lib/conflict/db-singleton.ts::getConflictDb()` sync.
  Wire-up usa via `dbMod.getConflictDb()`.
- **L3 DB singleton:** `lib/confidence/db-shim-singleton.ts::getConfidenceDb()`
  sync. Same pattern.
- **L3 health wrapper:** `api/health-confidence-adapter.ts::handleHealthConfidence()`
  faz `{status, body}` arg-free wrapping de `computeConfidenceHealth(db)`.
- **Schema readiness:** `probeSchemaReadiness()` verifica:
  - L2 → tabela `conflict_audit` existe (migração v18)
  - L3 → colunas `chunks.confidence`, `chunks.provenance_kind`,
    `chunks.superseded_by` existem (migração v19)
  Quando o DB está atrasado, retorna `l2_ready=false / l3_ready=false`. Caller
  pode degradar pra read-only ou expor warning.

### 3.5 P2 (hooks) — `server-deps-p2.ts` + `lib/hooks/server-deps.ts`

- **Lê:** `agent_events` (schema v11, WHERE captured=1) — sanitiza p/ metadata
  only (drop `payload_json`).
- **Queue inspector:** tenta lazy-load `lib/hooks/worker.js::inspectQueue()`;
  fallback `{queueDepth: 0}` quando worker não tá rodando (CLI-only deploy).
- **Dryrun:** `dryRunHook(text, role, source)` força `dryRun=true` e
  `allowedSources` inclui api+cli, retorna trace per-layer.

---

## 4. Deploy — passo a passo

> Pré-req: regra crítica #1. `set -a; source /root/.openclaw/.env; set +a`.

### 4.1 Rsync para a VPS

```bash
NM=/root/.openclaw/workspace/tools/nox-mem

# Adapter modules (5 + 4 sidecars + registry)
rsync -avh staged-wire-up-adapters/edits/src/lib/deps/deps-registry.ts \
  root@${VPS}:${NM}/src/lib/deps/deps-registry.ts
rsync -avh staged-wire-up-adapters/edits/src/api/server-deps-p1.ts \
  root@${VPS}:${NM}/src/api/server-deps-p1.ts
rsync -avh staged-wire-up-adapters/edits/src/api/server-deps-a2.ts \
  root@${VPS}:${NM}/src/api/server-deps-a2.ts
rsync -avh staged-wire-up-adapters/edits/src/api/server-deps-p5.ts \
  root@${VPS}:${NM}/src/api/server-deps-p5.ts
rsync -avh staged-wire-up-adapters/edits/src/api/server-deps-l2-l3.ts \
  root@${VPS}:${NM}/src/api/server-deps-l2-l3.ts
rsync -avh staged-wire-up-adapters/edits/src/api/server-deps-p2.ts \
  root@${VPS}:${NM}/src/api/server-deps-p2.ts
rsync -avh staged-wire-up-adapters/edits/src/api/health-confidence-adapter.ts \
  root@${VPS}:${NM}/src/api/health-confidence-adapter.ts

# Sidecars (the wire-up.ts dynamically imports these specifiers)
rsync -avh staged-wire-up-adapters/edits/src/lib/archive/server-deps.ts \
  root@${VPS}:${NM}/src/lib/archive/server-deps.ts
rsync -avh staged-wire-up-adapters/edits/src/lib/hooks/server-deps.ts \
  root@${VPS}:${NM}/src/lib/hooks/server-deps.ts
rsync -avh staged-wire-up-adapters/edits/src/lib/conflict/db-singleton.ts \
  root@${VPS}:${NM}/src/lib/conflict/db-singleton.ts
rsync -avh staged-wire-up-adapters/edits/src/lib/confidence/db-shim-singleton.ts \
  root@${VPS}:${NM}/src/lib/confidence/db-shim-singleton.ts
rsync -avh staged-wire-up-adapters/edits/src/lib/viewer/broadcast-singleton.ts \
  root@${VPS}:${NM}/src/lib/viewer/broadcast-singleton.ts

# Docs
rsync -avh staged-wire-up-adapters/edits/docs/ADAPTERS.md \
  root@${VPS}:${NM}/docs/ADAPTERS.md
```

### 4.2 Append re-exports nos arquivos staged-P5 / L2 / L3 / health-confidence

Três arquivos das waves anteriores precisam de UMA linha extra para que o
wire-up encontre os símbolos via lazy-import:

```bash
# staged-P5 broadcast.ts → ganha getBroadcaster
echo 'export { getBroadcaster, resetBroadcasterForTests } from "./broadcast-singleton.js";' \
  >> ${NM}/src/lib/viewer/broadcast.ts

# staged-L2 db.ts → ganha getConflictDb
echo 'export { getConflictDb, ensureConflictDb, resetConflictDbForTests, __setConflictDbForTests } from "./db-singleton.js";' \
  >> ${NM}/src/lib/conflict/db.ts

# staged-L3 db-shim.ts → ganha getConfidenceDb
echo 'export { getConfidenceDb, ensureConfidenceDb, resetConfidenceDbForTests, __setConfidenceDbForTests } from "./db-shim-singleton.js";' \
  >> ${NM}/src/lib/confidence/db-shim.ts

# staged-L3 health-confidence.ts → ganha handleHealthConfidence
echo 'export { handleHealthConfidence } from "./health-confidence-adapter.js";' \
  >> ${NM}/src/api/health-confidence.ts
```

### 4.3 Rebuild + restart

```bash
cd ${NM}
npm run build
systemctl restart nox-mem-api
sleep 2
curl -sf http://127.0.0.1:18802/api/health | jq .chunks.total
```

### 4.4 Smoke-test cada rota destravada

```bash
# P1 — agora retorna 200 (ou 503 retrieval_empty se chunks vazio)
curl -s -X POST http://127.0.0.1:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"smoke"}' -w '\n%{http_code}\n'

# A2 export — agora retorna 200 + binary archive
curl -s -X POST http://127.0.0.1:18802/api/export \
  -H 'Content-Type: application/json' \
  -d '{"unencrypted":true}' -o /tmp/export-smoke.tgz -w '%{http_code}\n'
file /tmp/export-smoke.tgz  # esperado: "gzip compressed data"

# L2 — agora retorna 200 com {count, rows}
curl -sf "http://127.0.0.1:18802/api/conflict?status=open&limit=5" | jq .count

# L3 health — agora retorna 200
curl -sf http://127.0.0.1:18802/api/health/confidence | jq .confidence.provenance

# P2 — agora retorna 200 com config + queueDepth
curl -sf http://127.0.0.1:18802/api/hooks/status | jq .config.enabled

# P5 SSE — agora abre stream real (3s timeout)
timeout 3 curl -sN http://127.0.0.1:18802/api/events/stream || true
```

503 com `"reason": "X deps not deployed"` significa que o sidecar (sigla X)
falhou ao rsync — re-rodar a Section 4.1 pra esse pilar.

---

## 5. Testing strategy

### 5.1 Unit tests (este PR)

53 testes em 4 arquivos sob `edits/src/api/__tests__/`:

| Arquivo | Cobertura | Testes |
|---|---|---|
| `server-deps-p1.test.ts` | telemetry store, sessionId, 503 fallback | 6 |
| `server-deps-a2.test.ts` | export/import deps, streaming, multipart parser | 11 |
| `server-deps-p5.test.ts` | redaction, viewer root, SSE pump, degraded path | 14 |
| `server-deps-l2-l3.test.ts` | L2+L3 singletons, schema readiness probe | 18 |
| `server-deps-p2.test.ts` | hooks deps, queue probe, dryrun degraded | 9 |
| **TOTAL** | | **53** (alvo: 32-42, ship: 53) |

Rode com:

```bash
cd staged-wire-up-adapters
npm install
npm test
```

### 5.2 Integration tests (post-deploy)

Wire-up.test.ts (do #92) já cobre route matching. Após rsync, rode os
smokes da Section 4.4 — eles confirmam que o adapter está RECEIVED pelo
dispatcher e que o handler responde 200 ao invés de 503.

### 5.3 Regression budget

Endpoints v1.6 (`/api/health`, `/api/search`, `/api/kg`, etc.) continuam
inalterados — adapters só atuam nas rotas Wave A→K que o wire-up.ts intercepta.

---

## 6. Decisões intencionais

- **Singleton DB, NÃO connection-per-pillar.** Cinco WAL writers concorrentes
  causariam race em FTS5 + sqlite-vec. `deps-registry.getDb()` retorna a
  mesma handle pra L2/L3/P1/A2/P2.
- **String indirection nos dynamic imports.** Os sidecars (broadcast.js,
  worker.js, etc.) vivem nas staged dirs Wave B/C, não no
  `staged-wire-up-adapters/`. Const string + `await import(spec)` impede
  o TS de tentar resolver no compile-time — runtime-only.
- **503 ainda existe.** Quando DB tá ausente OU staged-X não foi rsync,
  adapter retorna 503 + reason. Wire-up.ts surface unchanged. Defesa em
  camadas: adapter degrada, wire-up degrada, host não cai.
- **Privacy padrão restritivo.** P5 viewer redacted by default
  (NOX_VIEWER_SHOW_QUERY=0). P2 hooks recent rows sanitizados (drop
  payload_json). P1 telemetry hashea question. Não muda quando adapter
  está ausente — ainda é seguro.
- **Não modifica wire-up.ts** (regra de ouro #5). Adapters são módulos
  independentes; wire-up.ts continua o único arquivo de roteamento.

---

## 7. Arquivos desse PR

| Arquivo | Linhas |
|---|---|
| `staged-wire-up-adapters/edits/src/lib/deps/deps-registry.ts` | ~230 |
| `staged-wire-up-adapters/edits/src/api/server-deps-p1.ts` | ~190 |
| `staged-wire-up-adapters/edits/src/api/server-deps-a2.ts` | ~155 |
| `staged-wire-up-adapters/edits/src/lib/archive/server-deps.ts` | ~340 |
| `staged-wire-up-adapters/edits/src/api/server-deps-p5.ts` | ~140 |
| `staged-wire-up-adapters/edits/src/lib/viewer/broadcast-singleton.ts` | ~50 |
| `staged-wire-up-adapters/edits/src/api/server-deps-l2-l3.ts` | ~125 |
| `staged-wire-up-adapters/edits/src/lib/conflict/db-singleton.ts` | ~55 |
| `staged-wire-up-adapters/edits/src/lib/confidence/db-shim-singleton.ts` | ~35 |
| `staged-wire-up-adapters/edits/src/api/health-confidence-adapter.ts` | ~60 |
| `staged-wire-up-adapters/edits/src/api/server-deps-p2.ts` | ~90 |
| `staged-wire-up-adapters/edits/src/lib/hooks/server-deps.ts` | ~115 |
| `staged-wire-up-adapters/edits/src/api/__tests__/*.test.ts` (5 arquivos) | ~620 |
| `staged-wire-up-adapters/edits/docs/ADAPTERS.md` | este arquivo (~200) |
| `staged-wire-up-adapters/package.json` + `tsconfig.json` | ~30 |

Total: ~2400 linhas (~1100 prod, ~620 tests, ~250 docs, ~30 config).

---

## 8. Follow-up (não nesse PR)

- **Métrica `nox_adapter_deps_ready{pillar}` (Prometheus)** — expor
  `probeSchemaReadiness()` no `/metrics` endpoint pra alertar quando o
  schema fica atrás da expectativa do adapter.
- **Bench p99 export real** — depois do deploy, medir `POST /api/export` com
  62.9k chunks + 99.97% embeddings. Esperado <2s no DB atual; >5s vira
  spec pra streaming serializer (T10/T11 da A2 já flagged).
- **Adaptive degradation no wire-up.ts** — quando `probeSchemaReadiness()`
  reporta L2 not ready, wire-up poderia retornar 503 com `Retry-After: 60`
  ao invés do genérico `not_implemented`. Fora de escopo aqui.
