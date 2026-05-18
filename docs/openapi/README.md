# memoria-nox OpenAPI spec

`openapi.yaml` — OpenAPI 3.1 spec for all nox-mem HTTP API endpoints.

Covers: Core (Wave 1.6) + P3 temporal search + P1 answer + A2 export/import +
P5 realtime viewer + L2 conflict detection + L3 confidence/mark + P2 hooks.

Port: `18802` (default, `NOX_API_PORT` overrides).

---

## View the spec

### Swagger UI (quickest)

```bash
npx --yes @redocly/cli preview-docs docs/openapi/openapi.yaml
# opens http://127.0.0.1:8080
```

### Redoc (read-only, clean)

```bash
npx --yes @redocly/cli build-docs docs/openapi/openapi.yaml --output /tmp/redoc.html
open /tmp/redoc.html
```

### Swagger Editor (online)

1. Open https://editor.swagger.io
2. File → Import File → select `docs/openapi/openapi.yaml`

---

## Validate

```bash
# Option A — @apidevtools/swagger-cli
npx @apidevtools/swagger-cli validate docs/openapi/openapi.yaml

# Option B — redocly (stricter, checks for unused schemas)
npx @redocly/cli lint docs/openapi/openapi.yaml

# Option C — pure Node (syntax only, no semantic checks)
node -e "
  const yaml = require('js-yaml');
  const fs = require('fs');
  const doc = yaml.load(fs.readFileSync('docs/openapi/openapi.yaml', 'utf8'));
  console.log('YAML parse OK — openapi:', doc.openapi, '  paths:', Object.keys(doc.paths).length);
"
```

---

## Generate TypeScript client

Using `openapi-typescript` (zero-runtime, type-only):

```bash
npx openapi-typescript docs/openapi/openapi.yaml --output src/types/api.d.ts
```

Then use with `openapi-fetch`:

```ts
import createClient from "openapi-fetch";
import type { paths } from "./types/api.js";

const client = createClient<paths>({ baseUrl: "http://127.0.0.1:18802" });

// Fully typed — intellisense on request body + response
const { data, error } = await client.POST("/api/answer", {
  body: { question: "Why does the monkey-patch need reapplying after upgrade?" },
});
```

---

## Keeping the spec in sync

Each endpoint cross-references its implementation file in the `description`
field. When you modify an endpoint, update the matching path block:

| Endpoint | Implementation |
|----------|---------------|
| `/api/health`, `/api/search`, `/api/kg*`, `/api/reflect`, `/api/procedures`, `/api/crystallize*`, `/api/agents`, `/api/cross-kg` | `staged-1.6/edits/api-server.ts` |
| `/api/search` (temporal params) | `staged-P3/edits/api-server.ts` |
| `/api/answer` | `staged-P1/edits/src/api/answer.ts` |
| `/api/export`, `/api/import` | `staged-A2/edits/src/lib/archive/` |
| `/api/events/stream` | `staged-P5/edits/src/api/events-stream.ts` |
| `/viewer/{file}` | `staged-P5/edits/src/api/viewer-static.ts` |
| `/api/kg/conflicts*` | spec: `specs/2026-05-17-L2-conflict-detection.md §5.2` |
| `/api/chunk/{id}/mark`, `/api/chunk/{id}/supersede` | `staged-L3/edits/src/api/mark.ts` |
| `/api/hooks/*` | `.claude/worktrees/agent-a21b345bc854329aa/staged-P2/edits/src/api/hooks.ts` |

---

## Endpoint inventory

| Path | Method | Wave | Gate env var |
|------|--------|------|-------------|
| `/api/health` | GET | Core | — |
| `/api/search` | GET, POST | Core + P3 | — |
| `/api/agents` | GET | Core | — |
| `/api/kg` | GET | Core | — |
| `/api/kg/path` | GET | Core | — |
| `/api/cross-kg` | GET | Core | — |
| `/api/reflect` | GET | Core | — |
| `/api/procedures` | GET | Core | — |
| `/api/crystallize` | POST | Core | — |
| `/api/crystallize/validate` | POST | Core | — |
| `/api/answer` | POST | P1 | `NOX_ANSWER_ENABLED=1` |
| `/api/export` | POST | A2 | `NOX_ARCHIVE_ENABLED=1` |
| `/api/import` | POST | A2 | `NOX_ARCHIVE_ENABLED=1` |
| `/api/events/stream` | GET | P5 | `NOX_VIEWER_ENABLED=1` |
| `/viewer/{file}` | GET | P5 | `NOX_VIEWER_ENABLED=1` |
| `/api/kg/conflicts` | GET | L2 | `NOX_KG_CONFLICTS_ENABLED=1` |
| `/api/kg/conflicts/scan` | POST | L2 | `NOX_KG_CONFLICTS_ENABLED=1` |
| `/api/kg/conflicts/{id}` | GET | L2 | `NOX_KG_CONFLICTS_ENABLED=1` |
| `/api/kg/conflicts/{id}/resolve` | POST | L2 | `NOX_KG_CONFLICTS_ENABLED=1` |
| `/api/kg/conflicts/{id}/dismiss` | POST | L2 | `NOX_KG_CONFLICTS_ENABLED=1` |
| `/api/chunk/{id}/mark` | POST | L3 | — |
| `/api/chunk/{id}/supersede` | POST | L3 | — |
| `/api/hooks/status` | GET | P2 | `NOX_HOOKS_ENABLED=1` |
| `/api/hooks/recent` | GET | P2 | `NOX_HOOKS_ENABLED=1` |
| `/api/hooks/dryrun` | POST | P2 | `NOX_HOOKS_ENABLED=1` |

Total: **26 paths / 28 operations** documented.
