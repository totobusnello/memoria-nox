# P5a — Internal Event Bus (P5 SSE Prerequisite)

**Branch:** `overnight/2026-05-19/P5a-event-bus-refactor`
**Spec reference:** D41-bonus #1 (3-4h refactor, locked before P5 implementation)
**Files staged:** `staged-P5a/edits/src/lib/events/bus.ts` + tests

---

## What this delivers

Singleton `EventEmitter` that internal nox-mem-api modules publish to, and P5 SSE endpoint subscribes from.
All emits are **fire-forget** (via `setImmediate`) — listener failures never surface to caller.

---

## Event Kinds (9 total)

| Kind | Trigger site | Payload key fields |
|---|---|---|
| `chunk.created` | `routeIngest()` post-write | `chunk_id, source_file, type, section, token_count` |
| `chunk.deleted` | `trg_chunks_delete_cascade` callback | `chunk_id` |
| `kg.entity.created` | kg-extract success loop | `entity_id, name, entity_type` |
| `kg.relation.created` | kg-extract success loop | `relation_id, source_entity_id, target_entity_id, relation_type` |
| `search.executed` | hybrid search end (after RRF) | `query_hash, latency_ms, top_k, result_count, mode` |
| `provider.call` | Gemini embed/complete/extract complete | `provider, op_type, latency_ms, cost_usd, model, token_count` |
| `op_audit.started` | `withOpAudit()` entry | `op_id, op_type` |
| `op_audit.completed` | `withOpAudit()` exit (any status) | `op_id, op_type, status, duration_ms` |
| `health.warning` | any module detecting anomaly | `code, message, severity, context` |

---

## Integration Points (P5 implementation tasks)

### 1. `routeIngest()` → `chunk.created`

**File:** `src/lib/ingest-router.ts`
**Where:** after successful DB insert, before returning chunk ID.

```typescript
import { emit, EventKind } from './events/bus.js';

// After: const chunkId = insertChunk(db, ...);
emit(EventKind.CHUNK_CREATED, {
  chunk_id: chunkId,
  source_file: filePath,
  type: chunkType,
  section: section ?? undefined,
  token_count: tokenCount,
  ts: Date.now(),
});
```

---

### 2. Delete cascade → `chunk.deleted`

**File:** `src/lib/db.ts` (or wherever `chunks` DELETE fires)
**Where:** wrap the DELETE statement or add post-delete hook.

```typescript
// After bulk or single DELETE FROM chunks WHERE ...
const deletedIds: number[] = stmt.all().map((r: any) => r.chunk_id);
for (const chunk_id of deletedIds) {
  emit(EventKind.CHUNK_DELETED, { chunk_id, ts: Date.now() });
}
```

Note: The SQLite trigger `trg_chunks_delete_cascade` handles vec_chunks FK cleanup. The JS-side emit fires AFTER the DELETE, not inside the trigger (SQLite triggers cannot call JS).

---

### 3. kg-extract success → `kg.entity.created` + `kg.relation.created`

**File:** `src/commands/kg-extract.ts`
**Where:** inside the entity/relation save loop.

```typescript
import { emit, EventKind } from '../lib/events/bus.js';

// After entity upsert:
emit(EventKind.KG_ENTITY_CREATED, {
  entity_id: savedEntity.id,
  name: savedEntity.name,
  entity_type: savedEntity.entity_type,
  ts: Date.now(),
});

// After relation insert:
emit(EventKind.KG_RELATION_CREATED, {
  relation_id: savedRelation.id,
  source_entity_id: savedRelation.source_entity_id,
  target_entity_id: savedRelation.target_entity_id,
  relation_type: savedRelation.relation_type,
  ts: Date.now(),
});
```

---

### 4. Hybrid search end → `search.executed`

**File:** `src/lib/search.ts` (hybrid search orchestrator)
**Where:** after RRF reranking, before returning results.

```typescript
import { emit, EventKind } from './events/bus.js';
import { createHash } from 'crypto';

const queryHash = createHash('sha1').update(query).digest('hex').slice(0, 8);
emit(EventKind.SEARCH_EXECUTED, {
  query_hash: queryHash,
  latency_ms: Date.now() - searchStart,
  top_k: limit,
  result_count: results.length,
  mode: hybridEnabled ? 'hybrid' : 'fts',
  ts: Date.now(),
});
```

---

### 5. Provider complete/embed → `provider.call`

**File:** `src/lib/provider.ts` (or gemini client wrapper)
**Where:** after API call returns, before result is used.

```typescript
emit(EventKind.PROVIDER_CALL, {
  provider: 'gemini',
  op_type: 'embed',           // or 'complete' | 'extract'
  latency_ms: elapsed,
  cost_usd: estimateCost(tokenCount, model),
  model: modelId,
  token_count: tokenCount,
  ts: Date.now(),
});
```

---

### 6. `withOpAudit()` → `op_audit.started` + `op_audit.completed`

**File:** `src/lib/op-audit.ts`
**Where:** wrap existing `ops_audit` DB insert/update calls.

```typescript
import { emit, EventKind } from './events/bus.js';

// At op start (after DB insert):
emit(EventKind.OP_AUDIT_STARTED, { op_id: newOpId, op_type: opType, ts: Date.now() });

// At op end (after DB update with status):
emit(EventKind.OP_AUDIT_COMPLETED, {
  op_id: opId,
  op_type: opType,
  status: finalStatus,        // 'success' | 'failed' | 'crashed'
  duration_ms: Date.now() - opStart,
  ts: Date.now(),
});
```

---

## P5 SSE Endpoint Integration Pattern

```typescript
// src/routes/events-sse.ts (P5 implementation)
import { bus, EventKind, EventKindValue } from '../lib/events/bus.js';

app.get('/api/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const kinds = Object.values(EventKind) as EventKindValue[];
  const unsubscribers = kinds.map((kind) =>
    bus.subscribe(kind, (data) => {
      res.write(`event: ${kind}\ndata: ${JSON.stringify(data)}\n\n`);
    })
  );

  req.on('close', () => {
    unsubscribers.forEach((unsub) => unsub());
  });
});
```

---

## Performance Characteristics

- **Emit overhead:** scheduling-only (setImmediate enqueue), measured <1ms for 1000 calls
- **Listener dispatch:** async, off caller stack — listener exceptions isolated
- **Max listeners:** 50 (P5 viewer SSE connections + internal subscribers)
- **Memory:** no event queuing — fire-forget, no backpressure needed at this scale

---

## Running Tests

```bash
# From staged-P5a/edits/
npx tsx --test src/lib/events/__tests__/bus.test.ts
# or once copied to production src/:
node --test dist/lib/events/__tests__/bus.test.js
```

14 test cases across 3 suites: core (9), listener management (4), performance (1).

---

## Copy to production

When P5 implementation begins, copy staged files:
```bash
cp staged-P5a/edits/src/lib/events/bus.ts src/lib/events/bus.ts
cp staged-P5a/edits/src/lib/events/__tests__/bus.test.ts src/lib/events/__tests__/bus.test.ts
```

Then add integration calls per section above. No other src/ changes required from P5a.
