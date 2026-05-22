# @noxmem/client

Node 20+ and browser client for the [nox-mem](https://github.com/totobusnello/memoria-nox) hybrid memory API. Uses native `fetch` — zero runtime dependencies.

## Install

```bash
# Vendor from repo (pre-publish)
npm install clients/javascript/

# After npm publish
npm install @noxmem/client
```

## Quick start

```js
import { NoxMemClient } from "@noxmem/client";

const client = new NoxMemClient({ baseUrl: "http://187.77.234.79:18802" });

// Health check
const snap = await client.health();
console.log(`${snap.chunksTotal} chunks, ${(snap.vecCoverage * 100).toFixed(1)}% vectorized`);

// Hybrid search (BM25 + semantic + RRF)
const results = await client.search("pain-weighted retrieval", { limit: 5 });
for (const r of results) {
  console.log(`[${r.score.toFixed(3)}] ${r.sourceFile}: ${r.snippet.slice(0, 80)}`);
}

// Grounded answer
const { answer, citations, latencyMs } = await client.answer("What is the salience formula?");
console.log(answer);
console.log(`Latency: ${latencyMs}ms, ${citations.length} citations`);
```

## API reference

| Method | Endpoint |
|---|---|
| `health()` | `GET /api/health` |
| `search(query, { limit, userId })` | `GET /api/search` |
| `answer(query, { sessionId, options })` | `POST /api/answer` |
| `kgSearch(entity, { limit })` | `GET /api/kg` |
| `kgPath(source, target)` | `GET /api/kg/path` |

Retries 5xx errors up to 3x with exponential backoff. Throws `NoxMemError` on failure. Full TypeScript declarations in `src/index.d.ts`.

## Tests

```bash
node --test src/index.test.js
```
