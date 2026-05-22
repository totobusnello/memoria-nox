# nox-mem API Reference

> **Version:** 1.0.0-rc1 · **Base URL:** `http://localhost:18802` (default) · **Spec:** [`docs/openapi.yaml`](openapi.yaml)

nox-mem exposes a JSON HTTP API on port 18802 (`NOX_API_PORT`). All endpoints are read-only by default; write endpoints (`/api/crystallize`, `/api/answer`, `/api/import`) are trusted-localhost in v1 — no TLS or auth required unless you set `NOX_API_TOKEN`.

---

## Quick start

```bash
# Health check
curl http://localhost:18802/api/health | jq .vectorCoverage

# Hybrid search
curl "http://localhost:18802/api/search?q=pain-weighted+memory&limit=5" | jq '.[].content'

# RAG answer (requires NOX_ANSWER_ENABLED=1)
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is the conditional hard mutex?"}'
```

---

## Endpoint groups

| Tag | Endpoints | Notes |
|-----|-----------|-------|
| **Core** | `GET /api/health`, `GET /api/search`, `POST /api/search`, `GET /api/agents`, `GET /api/reflect`, `GET /api/procedures`, `POST /api/crystallize`, `POST /api/crystallize/validate` | Always available |
| **Answer (P1)** | `POST /api/answer` | Gated: `NOX_ANSWER_ENABLED=1` |
| **Knowledge Graph** | `GET /api/kg`, `GET /api/kg/path`, `GET /api/cross-kg` | Always available |
| **Export/Import (A2)** | `POST /api/export`, `POST /api/import` | Gated: `NOX_ARCHIVE_ENABLED=1` |
| **Viewer (P5)** | `GET /api/events/stream`, `GET /viewer/{file}` | Gated: `NOX_VIEWER_ENABLED=1` |
| **Conflict Detection (L2)** | `GET /api/kg/conflicts`, `POST /api/kg/conflicts/scan`, etc. | Gated: `NOX_KG_CONFLICTS_ENABLED=1` |
| **Confidence (L3)** | `POST /api/chunk/{id}/mark`, `POST /api/chunk/{id}/supersede` | Always available |
| **Hooks (P2)** | `GET /api/hooks/status`, `GET /api/hooks/recent`, `POST /api/hooks/dryrun` | Gated: `NOX_HOOKS_ENABLED=1` |
| **Observability (F10)** | `GET /api/observability/health`, `/recent-ops`, `/canary-tail`, `/evals` | Always available, read-only |

---

## Public demo

`http://187.77.234.79:18802` — read-only endpoints (`/api/health`, `/api/search`) are publicly accessible. Write and gated endpoints are not exposed externally.

---

## Authentication

Set `NOX_API_TOKEN` in the server `.env` to require `Authorization: Bearer <token>` on all routes. Without the env var, all calls from localhost are allowed. The `/api/export` and `/api/import` endpoints always enforce auth when any token is configured.

---

## Browsing the spec

The full OpenAPI 3.1 spec is at [`docs/openapi.yaml`](openapi.yaml). To browse it interactively:

**Swagger UI (local):**
```bash
npx @stoplight/prism-cli mock docs/openapi.yaml
# or
docker run -p 8080:8080 -e SWAGGER_JSON=/spec/openapi.yaml \
  -v $(pwd)/docs:/spec swaggerapi/swagger-ui
```

**Online viewers:**
- Paste the raw URL into [editor.swagger.io](https://editor.swagger.io)
- Import into [Insomnia](https://insomnia.rest) or [Postman](https://www.postman.com) via "Import → OpenAPI"
- Publish to [ReadMe.io](https://readme.com) for hosted developer docs

**Validation:**
```bash
python3 -c "import yaml; yaml.safe_load(open('docs/openapi.yaml'))" && echo "YAML valid"
# For deep OpenAPI lint:
npx @stoplight/spectral-cli lint docs/openapi.yaml
```

---

## Key response shapes

**`GET /api/health`** — returns chunk counts, vector coverage, KG stats, salience mode, uptime. Use `curl .../api/health | jq .vectorCoverage` as the canonical prod-state check.

**`GET /api/search?q=…`** — returns an array of `SearchResult` objects ranked by RRF fused score (FTS5 BM25 + Gemini 3072d cosine). Typical p50 latency ~940 ms (Gemini embed dominates).

**`POST /api/answer`** — returns `{answer, citations, metadata, trace_id}`. Each citation includes `chunk_id`, `file_path`, `snippet`, and inline `[chunk_N]` markers in the answer text.

**`GET /api/observability/health`** — pre-computed health snapshot with `delta_24h` traffic-light indicators; safe to poll without DB load.

---

## Further reading

- Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Configuration reference: [`docs/CONFIGURATION.md`](CONFIGURATION.md)
- Retrieval pipeline detail: `docs/ARCHITECTURE.md §4`
- Eval gate history: `http://localhost:18802/observability/evals.html`
- Security model: `docs/ARCHITECTURE.md §10`
