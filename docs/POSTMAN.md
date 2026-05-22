# Postman / Insomnia / Bruno collection

Import `docs/nox-mem.postman_collection.json` into any REST client:

- **Postman**: File → Import → drag the file (or paste path)
- **Insomnia**: Application → Import/Export → Import Data → From File
- **Bruno**: open collection folder → Import → Postman → select file

The `base_url` variable defaults to the public read-only demo at `http://187.77.234.79:18802`.

Override to your local instance:
- **Postman**: Collections → nox-mem API → Variables tab → set `base_url` to `http://localhost:18802`
- **Insomnia**: Environment → set `base_url`
- **Bruno**: `.env` or collection variables → `base_url = http://localhost:18802`

## Examples included

| Folder | Requests | Notes |
|--------|----------|-------|
| **Core** | Health, Search hybrid, Answer (flagship) | Start here — all 3 work against the public demo |
| **Knowledge Graph** | KG search, KG path | Search entities and traverse the relation graph |
| **Multi-agent** | Agents, Cross-KG | Persona registry and cross-agent KG merge stats |
| **Operations** | Reflect, Procedures, Crystallize, Crystallize validate | Destructive ops use `dry_run: true` by default in examples |
| **Observability** | Obs Health, Obs Recent Ops, Obs Canary Tail, Obs Evals | F10 Phase A+B dashboard endpoints |

Total: **15 requests** in 5 folders.

### Gated endpoints

Some endpoints require server-side env vars and return `503 Service Unavailable` when not enabled:

| Endpoint | Required env var |
|----------|-----------------|
| `POST /api/answer` | `NOX_ANSWER_ENABLED=1` |
| `POST /api/reflect` | always enabled |
| `POST /api/crystallize` | always enabled (use `dry_run: true`) |

The public demo has `answer` enabled. Crystallize/reflect are write ops — use your own instance.

### Auth

If `NOX_API_TOKEN` is set on the server, add an Authorization header:

```
Authorization: Bearer <token>
```

In Postman: Collections → Authorization tab → Bearer Token.

## See also

- `docs/openapi.yaml` — machine-readable OpenAPI 3.1 spec
- `docs/api-reference.md` — API quick reference with curl examples
- `examples/` — runnable curl and Python scripts
