---
title: TypeScript SDK
description: Official TypeScript/JavaScript client for memoria-nox.
sidebar:
  order: 2
---

Source: [`sdk/typescript/`](https://github.com/totobusnello/memoria-nox/tree/main/sdk/typescript)

## Install

```bash
npm install @memoria-nox/sdk
```

## Basic usage

```typescript
import { NoxMemClient } from '@memoria-nox/sdk';

const client = new NoxMemClient({
  baseUrl: 'http://127.0.0.1:18802',
});

// Hybrid search
const results = await client.search('salience formula', { limit: 10 });
for (const r of results) {
  console.log(r.score, r.content.slice(0, 120));
}

// Grounded answer
const answer = await client.answer('how does pain affect ranking?');
console.log(answer.text);
console.log('Sources:', answer.sources.map(s => s.source));

// Corpus stats
const stats = await client.stats();
console.log(`chunks: ${stats.totalChunks}, coverage: ${stats.vectorCoverage}`);
```

## Ingest

```typescript
// Ingest a single markdown string
await client.ingest({
  content: '# My Note\n\nThis is a memory.',
  source: 'manual/my-note.md',
  type: 'markdown',
});

// Ingest a file path (server-side read)
await client.ingestFile('/path/to/my-note.md');
```

## Knowledge graph

```typescript
// Get entities
const entities = await client.kg.listEntities({ type: 'project' });

// Path query
const path = await client.kg.findPath('memoria-nox', 'sqlite-vec');
```

## MCP integration

The TypeScript SDK includes a pre-wired MCP adapter. In your agent configuration:

```typescript
import { NoxMemMCPServer } from '@memoria-nox/sdk/mcp';

const server = new NoxMemMCPServer({
  baseUrl: 'http://127.0.0.1:18802',
});
await server.start();
```

This exposes all 16 MCP tools to compatible agent runtimes.

## TypeScript types

```typescript
interface SearchResult {
  chunkId: number;
  score: number;
  content: string;
  source: string;
  section: 'compiled' | 'frontmatter' | 'timeline' | null;
  pain: number;
}

interface AnswerResult {
  text: string;
  sources: Array<{ chunkId: number; source: string; score: number }>;
  model: string;
}
```
