---
title: OpenAPI Spec
description: HTTP API reference — OpenAPI 3.1 specification for all endpoints.
sidebar:
  order: 1
---

Full spec: [`docs/openapi/openapi.yaml`](https://github.com/totobusnello/memoria-nox/blob/main/docs/openapi/openapi.yaml)

The HTTP API listens on `http://127.0.0.1:18802` by default (configured via `NOX_API_PORT`).

## Base URL

```
http://127.0.0.1:{NOX_API_PORT}
```

Default port: `18802`. Never use `18800` — Chrome uses that port.

## Endpoints

### GET /api/health

Full health check with corpus stats, vector coverage, salience, and opsAudit.

```bash
curl http://127.0.0.1:18802/api/health | jq .
```

```json
{
  "status": "ok",
  "chunks": 69298,
  "vectorCoverage": { "embedded": 69295, "total": 69298 },
  "kgEntities": 15646,
  "kgRelations": 21533,
  "sectionDistribution": { "compiled": 183, "frontmatter": 183, "timeline": 183 },
  "opsAudit": { "recentFailed": 0, "lastSuccess": "2026-05-18T02:00:00Z" },
  "salience": { "mode": "shadow", "exposed": true }
}
```

### POST /api/search

```bash
curl -X POST http://127.0.0.1:18802/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "salience formula", "limit": 10}'
```

Request body:

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | string | required | Search query |
| `limit` | number | 10 | Max results |
| `noHybrid` | boolean | false | FTS-only (skip vector layer) |
| `minScore` | number | 0 | Minimum RRF score threshold |

### POST /api/answer

```bash
curl -X POST http://127.0.0.1:18802/api/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "how does pain affect ranking?"}'
```

Returns grounded answer with source citations.

### GET /api/kg

List knowledge graph entities. Query params: `type`, `limit`, `offset`.

### GET /api/kg/path

Find path between two entities: `?from=memoria-nox&to=sqlite-vec`

### POST /api/reflect

Trigger memory reflection and consolidation.

### POST /api/crystallize

Crystallize raw memories into structured knowledge.

### POST /api/crystallize/validate

Preview crystallization without committing (dry run).

## Generating the OpenAPI spec

```bash
cd docs/openapi
npm run generate   # regenerate from source annotations
npm run validate   # validate spec against OpenAPI 3.1
```

See [`docs/openapi/README.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/openapi/README.md) for the full generation guide.
