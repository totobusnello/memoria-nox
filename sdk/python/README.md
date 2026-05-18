# nox-mem-client (Python)

Async Python client for the [memoria-nox](https://github.com/totobusnello/memoria-nox) HTTP API.

Generated from the OpenAPI 3.1 spec at `docs/openapi/openapi.yaml` (version `1.0.0-wave-d`).
Uses `httpx` for async HTTP and `pydantic` for type-safe models.

## Install

```bash
pip install nox-mem-client
```

## Quick start

```python
import asyncio
from nox_mem_client import NoxMemClient

async def main():
    async with NoxMemClient() as client:
        results = await client.search("Gemini quota exceeded")
        for r in results:
            print(r.content, r.score)

asyncio.run(main())
```

## Configuration

```python
client = NoxMemClient(
    base_url="http://127.0.0.1:18802",   # default
    auth_token="your-token",              # sent as Authorization: Bearer
    timeout=30.0,                         # seconds, default 30
)
# Use as context manager for automatic cleanup
async with client:
    ...
# Or close manually
await client.aclose()
```

## Methods

### Core

```python
# System health
health = await client.health()
print(health.vector_coverage.embedded, "/", health.vector_coverage.total)
print(health.knowledge_graph.entities)

# Agent profiles
agents = await client.agents()

# Memory reflection
insight = await client.reflect("recurring production incidents")

# Procedures
procedures = await client.procedures()

# Crystallize a new procedure
result = await client.crystallize(CrystallizeRequest(
    title="Reapply monkey-patch after OpenClaw upgrade",
    steps=["SSH into VPS as root", "Run /root/reapply-monkey-patch.sh", "Verify"],
    agent="forge",
    tags=["openclaw", "maintenance"],
))
print(result["id"])

# Record outcome
await client.crystallize_validate(result["id"], CrystallizeValidateRequest(
    outcome="success",
    notes="Ran cleanly in 4 minutes",
))
```

### Search

```python
# GET (most common)
results = await client.search("Gemini quota limits", limit=5)

# POST with temporal filters (P3)
from nox_mem_client.models import SearchRequest
results = await client.search_post(SearchRequest(
    q="how to reapply monkey-patch",
    limit=8,
    as_of="2026-05-10",
    changed_since="2026-05-01",
))
```

### Knowledge Graph

```python
kg = await client.kg()
for entity in (kg.entities or []):
    print(entity.name, entity.mentions)

# Shortest path
path = await client.kg_path("nox-mem-api", "gemini-embedding-001")
# ["nox-mem-api", "vectorize", "gemini-embedding-001"] or None

# Cross-agent merged KG
cross = await client.cross_kg()
```

### Answer (P1) — requires `NOX_ANSWER_ENABLED=1`

```python
ans = await client.answer(
    "What is the correct Gemini daily quota?",
    top_k=8,
    model="gemini-2.5-flash-lite",
)
print(ans.answer)           # inline [chunk_N] markers
print(ans.metadata.model)   # actual model used
for c in ans.citations:
    print(f"  [{c.marker_id}] {c.snippet}")
```

### Export / Import (A2) — requires `NOX_ARCHIVE_ENABLED=1`

```python
# Export
archive_bytes = await client.export(ExportRequest(
    project="granix",
    format="tar",
    exclude_embeddings=False,
))
with open("backup-2026-05-18.tar.gz", "wb") as f:
    f.write(archive_bytes)

# Import
with open("backup-2026-05-18.tar.gz", "rb") as f:
    archive = f.read()
result = await client.import_archive(archive, mode="merge", dry_run=True)
print("Would insert:", result.chunks_inserted, "chunks")
```

### Viewer / SSE (P5) — requires `NOX_VIEWER_ENABLED=1`

```python
# Async iterator — yields ViewerEvent
async for event in client.stream_events():
    print(event.kind.value, event.ts, event.payload)
    # kinds: chunk.created | chunk.deleted | kg.entity.created |
    #        kg.relation.created | search.executed | provider.call |
    #        op_audit.started | op_audit.completed | health.warning
```

### Conflict Detection (L2) — requires `NOX_KG_CONFLICTS_ENABLED=1`

```python
from nox_mem_client.models import ConflictStatus

result = await client.list_conflicts(status=ConflictStatus.unresolved)
print(result["total"], "conflicts")

# Trigger scan
scan = await client.scan_conflicts()
print(f"Found {scan['detected']} conflicts in {scan['duration_ms']}ms")

# Detail with evidence
detail = await client.get_conflict(result["conflicts"][0].id)
print(detail.evidence_snippets)

# Resolve
await client.resolve_conflict(detail.id, keep_relation_id=42, notes="Keeping 2026 entry")

# Or dismiss
await client.dismiss_conflict(detail.id, notes="Not a real conflict")
```

### Confidence / Marking (L3)

```python
from nox_mem_client import MarkKind, SupersedeReason

# Mark canonical (confidence → 0.95)
result = await client.mark_chunk(41203, MarkKind.canonical, "Verified 2026-05-18")
print(result.applied.confidence)  # 0.95

# Mark refuted
await client.mark_chunk(41203, MarkKind.refuted)

# Supersede
await client.supersede_chunk(
    40123, 41203,
    reason=SupersedeReason.manual_resolution,
    notes="Newer decision supersedes this",
)
```

### Hooks (P2) — requires `NOX_HOOKS_ENABLED=1`

```python
# Pipeline config + queue depth
status = await client.hook_status()
print(status.config.pii_policy, status.queue_depth)

# Recent events (no payloads)
recent = await client.hook_recent(20)
for ev in recent:
    print(ev.kind, ev.timestamp, ev.redaction_count)

# Dry-run
from nox_mem_client import HooksDryrunRequest
dryrun = await client.hook_dryrun(HooksDryrunRequest(
    text="John Smith from Nuvini called about Q2 board meeting"
))
print(dryrun.result)   # redacted output
print(dryrun.trace)    # per-layer trace
```

## Error handling

All methods raise `NoxMemApiError` on non-2xx responses.

```python
from nox_mem_client import NoxMemClient, NoxMemApiError

try:
    ans = await client.answer("...")
except NoxMemApiError as e:
    print(e.status_code)        # HTTP status
    print(e.body)               # Parsed response body
    print(e.is_feature_disabled)  # True if NOX_*_ENABLED not set
    print(e.is_unauthorized)    # True on 401
```

## Development

```bash
cd sdk/python
pip install -e ".[dev]"
pytest tests/
```
