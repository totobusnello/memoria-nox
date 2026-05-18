---
title: SDK Overview
description: Official client libraries for memoria-nox across TypeScript, Python, Rust, Go, Java, and .NET.
sidebar:
  order: 1
---

Full SDK source: [`sdk/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk)

## Available SDKs

| Language | Status | Package |
|---|---|---|
| TypeScript | Available | `sdk/typescript/` |
| Python | Available | `sdk/python/` |
| Rust | Available | `sdk/rust/` |
| Go | Available | `sdk/go/` |
| Java | Available | `sdk/java/` |
| .NET (C#) | Available | `sdk/dotnet/` |

All SDKs wrap the [HTTP API](/memoria-nox/api/openapi-spec) and implement the same core interface:

```
search(query, options) → SearchResult[]
answer(question, options) → AnswerResult
ingest(content, options) → IngestResult
stats() → CorpusStats
```

## Quick comparison

| Feature | TypeScript | Python | Rust | Go |
|---|---|---|---|---|
| Async/await | Native | asyncio | tokio | goroutines |
| Type safety | Full | Pydantic | Strong | Moderate |
| MCP integration | Native | Planned | — | — |
| Streaming | Yes | Yes | Yes | Yes |

## Connecting to the HTTP API

All SDKs connect to the local HTTP API. The default address is `http://127.0.0.1:18802`.

If you change the port via `NOX_API_PORT`, update the SDK base URL accordingly:

```typescript
const client = new NoxMemClient({ baseUrl: 'http://127.0.0.1:18802' });
```

## Examples directory

Complete runnable examples in [`sdk/examples/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk/examples).
