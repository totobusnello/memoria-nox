# nox-mem Python Client

Python 3.10+ client for the [nox-mem](https://github.com/totobusnello/memoria-nox) hybrid memory API.

## Install

```bash
# Vendor from repo (pre-publish)
pip install -e clients/python

# After PyPI publish
pip install nox-mem-client
```

## Quick start

```python
from nox_mem import NoxMemClient

# Default points to the public instance
client = NoxMemClient(base_url="http://187.77.234.79:18802")

# Check health
snap = client.health()
print(f"{snap.chunks_total} chunks, {snap.vec_coverage:.1%} vectorized")

# Hybrid search (BM25 + semantic + RRF)
results = client.search("pain-weighted retrieval", limit=5)
for r in results:
    print(f"[{r.score:.3f}] {r.source_file}: {r.snippet[:80]}")

# Grounded answer
resp = client.answer("What is the salience formula?")
print(resp.answer)
print(f"Latency: {resp.latency_ms}ms, {len(resp.citations)} citations")
```

Context manager form:

```python
with NoxMemClient() as c:
    entities = c.kg_search("nox-mem")
```

## API reference

| Method | Endpoint |
|---|---|
| `health()` | `GET /api/health` |
| `search(query, limit, user_id)` | `GET /api/search` |
| `answer(query, session_id, options)` | `POST /api/answer` |
| `kg_search(entity, limit)` | `GET /api/kg` |
| `kg_path(source, target)` | `GET /api/kg/path` |

Retries 5xx errors up to 3x with exponential backoff. Raises `NoxMemError` on failure.
