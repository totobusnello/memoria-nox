# @nox-mem/client

Type-safe TypeScript client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API.

Generated from the OpenAPI 3.1 spec at `docs/openapi/openapi.yaml` (version `1.0.0-wave-d`).

## Install

```bash
npm install @nox-mem/client
```

## Quick start

```typescript
import { NoxMemClient } from "@nox-mem/client";

const client = new NoxMemClient({
  baseUrl: "http://127.0.0.1:18802",  // default
  authToken: process.env.NOX_API_TOKEN, // optional
});

// Hybrid search
const results = await client.search("Gemini quota exceeded");
console.log(results[0].content, results[0].score);

// RAG answer with citations (requires NOX_ANSWER_ENABLED=1)
const { answer, citations } = await client.answer(
  "How do I reapply the monkey-patch after upgrading OpenClaw?",
  { top_k: 8 }
);
console.log(answer);
citations.forEach(c => console.log(`  [${c.marker_id}] ${c.snippet}`));
```

## Configuration

```typescript
const client = new NoxMemClient({
  baseUrl: "http://127.0.0.1:18802",   // default
  authToken: "your-token",              // sent as Authorization: Bearer
  timeoutMs: 30_000,                   // per-request timeout (ms), default 30s
});
```

## Methods

### Core

```typescript
// System health, stats, vector coverage
const health = await client.health();
console.log(health.vectorCoverage?.embedded, "/", health.vectorCoverage?.total);

// Agent profiles from cross-agent KG
const agents = await client.agents();

// Memory reflection synthesis
const insight = await client.reflect("recurring production incidents");

// List crystallized procedures
const procedures = await client.procedures();

// Store a new procedure
const { id } = await client.crystallize({
  title: "Reapply monkey-patch after OpenClaw upgrade",
  steps: ["SSH into VPS as root", "Run /root/reapply-monkey-patch.sh", "Verify no fratricide loop"],
  agent: "forge",
  tags: ["openclaw", "maintenance"],
});

// Record execution outcome
await client.crystallizeValidate(id, { outcome: "success", notes: "Ran in 4 minutes" });
```

### Search

```typescript
// GET variant (most common)
const results = await client.search("Gemini quota limits", { limit: 5 });

// POST variant (for long queries or programmatic use)
const results = await client.searchPost({
  q: "how to reapply monkey-patch",
  limit: 8,
  as_of: "2026-05-10",         // P3: temporal filter
  changed_since: "2026-05-01",
});
```

### Knowledge Graph

```typescript
// KG snapshot
const kg = await client.kg();
kg.entities?.forEach(e => console.log(e.name, e.mentions));

// Shortest path between two entities
const path = await client.kgPath("nox-mem-api", "gemini-embedding-001");
// ["nox-mem-api", "vectorize", "gemini-embedding-001"] or null

// Cross-agent merged KG
const crossKg = await client.crossKg();
```

### Answer (P1) — requires `NOX_ANSWER_ENABLED=1`

```typescript
const { answer, citations, metadata, trace_id } = await client.answer(
  "What is the Gemini daily quota limit?",
  {
    top_k: 8,
    model: "gemini-2.5-flash-lite",
    no_citations: false,
  }
);

// Answer has inline [chunk_N] markers
console.log(answer);         // "The daily limit is 3M tokens [chunk_1]..."
console.log(metadata.model); // "gemini-2.5-flash-lite"
console.log(metadata.latency_ms);
```

### Export / Import (A2) — requires `NOX_ARCHIVE_ENABLED=1`

```typescript
import { writeFileSync, readFileSync } from "node:fs";

// Export to file
const archive = await client.export({
  project: "granix",
  format: "tar",
  exclude_embeddings: false,
  encrypt: false,
});
writeFileSync("backup-2026-05-18.tar.gz", Buffer.from(await archive.arrayBuffer()));

// Import from file
const archiveData = readFileSync("backup-2026-05-18.tar.gz");
const result = await client.import(archiveData, { mode: "merge", dry_run: true });
console.log("Would insert:", result.chunks_inserted, "chunks");
```

### Viewer / SSE (P5) — requires `NOX_VIEWER_ENABLED=1`

```typescript
// Async iterable SSE stream
const controller = new AbortController();

for await (const event of client.streamEvents(controller.signal)) {
  console.log(event.kind, event.ts, event.payload);
  if (someCondition) controller.abort(); // stop listening
}

// Event kinds: "chunk.created" | "chunk.deleted" | "kg.entity.created" |
//              "kg.relation.created" | "search.executed" | "provider.call" |
//              "op_audit.started" | "op_audit.completed" | "health.warning"
```

### Conflict Detection (L2) — requires `NOX_KG_CONFLICTS_ENABLED=1`

```typescript
// List unresolved conflicts
const { conflicts, total } = await client.listConflicts({ status: "unresolved" });

// Trigger a scan
const scan = await client.scanConflicts();
console.log(`Detected ${scan.detected} conflicts in ${scan.duration_ms}ms`);

// Get detail with evidence
const detail = await client.getConflict(conflicts[0].id!);
console.log(detail.evidence_snippets);

// Resolve by choosing which relation to keep
await client.resolveConflict(detail.id!, keepRelationId, "Keeping the 2026 entry");

// Or dismiss
await client.dismissConflict(detail.id!, "Not a real conflict");
```

### Confidence / Marking (L3)

```typescript
// Mark a chunk as canonical (confidence → 0.95)
const result = await client.markChunk(41203, "canonical", "Verified on 2026-05-18");
console.log(result.applied.confidence); // 0.95

// Mark as refuted (confidence → 0.05)
await client.markChunk(41203, "refuted");

// Supersede an old chunk with a newer one
await client.supersedeChunk(40123, 41203, {
  reason: "manual_resolution",
  notes: "Newer decision from 2026-04-22 supersedes this",
});
```

### Hooks (P2) — requires `NOX_HOOKS_ENABLED=1`

```typescript
// Pipeline config + queue depth
const status = await client.hookStatus();
console.log(status.config?.pii_policy, status.queueDepth);

// Recent event metadata (no payloads)
const recent = await client.hookRecent(20);
recent.forEach(e => console.log(e.kind, e.timestamp, e.redaction_count));

// Dry-run to preview PII redaction
const dryrun = await client.hookDryrun({
  text: "John Smith from Nuvini called about the Q2 board meeting",
  source: "api",
});
console.log(dryrun.result);  // redacted text
console.log(dryrun.trace);   // per-layer trace
```

## Error handling

All methods throw `NoxMemApiError` on non-2xx responses.

```typescript
import { NoxMemClient, NoxMemApiError } from "@nox-mem/client";

try {
  const result = await client.answer("...");
} catch (e) {
  if (e instanceof NoxMemApiError) {
    console.log(e.status);             // HTTP status code
    console.log(e.body);               // Parsed response body
    console.log(e.isFeatureDisabled);  // true if NOX_*_ENABLED not set
    console.log(e.isUnauthorized);     // true on 401
  }
}
```

## TypeScript inference

All method return types are inferred from the generated `types.ts`:

```typescript
import type { SearchResult, AnswerSuccess, MarkResult, ViewerEvent } from "@nox-mem/client";

// Full inference without explicit type annotations
const results = await client.search("query");
//    ^? SearchResult[]

const answer = await client.answer("question");
//    ^? AnswerSuccess

for await (const event of client.streamEvents()) {
  event.kind;    // SseEventKind — union of all event kinds
  event.payload; // Record<string, unknown>
}
```

## React hook example

See `sdk/examples/react-hook.tsx`.

## Build

```bash
cd sdk/typescript
npm install
npm run generate   # regenerate types from openapi.yaml
npm run build      # compile to dist/
npm test           # run tests
```
